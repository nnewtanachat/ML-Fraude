# ML-Fraud Project Guidelines

## Project Overview
End-to-end fraud detection ML pipeline: real-time scoring, batch prediction, drift monitoring, deployed on Kubernetes.

## Architecture
- **Database**: PostgreSQL (SQLAlchemy ORM, connection pooling)
- **ML**: XGBoost with sklearn Pipeline (impute → feature eng → model)
- **Serving**: FastAPI + API key auth + Prometheus metrics
- **Streaming**: Apache Kafka (producer → consumer)
- **Tracking**: MLflow (experiment tracking + model registry)
- **Monitoring**: Prometheus + Grafana + Evidently (drift detection)
- **Orchestration**: Airflow (DAGs for retrain, batch predict, drift check)
- **Containerization**: Docker (multi-stage, non-root, 4 workers)
- **Deployment**: Kubernetes (GKE/EKS)
- **CI/CD**: GitHub Actions (lint → test → SAST → build → scan → deploy → smoke test)

## Code Style
- Use type hints for function signatures
- Logging with `logging` module using `%s` format (not f-strings, not print)
- Config from environment variables via pydantic-settings
- Business logic in `src/`, tests in `tests/`
- Lint with ruff (check + format)

## Project Structure
```
src/
├── serve/              # FastAPI API + metrics + auth
├── db/                 # Database layer (connection, models)
├── pipeline/           # ML pipeline (preprocess, train, tune)
├── streaming/          # Kafka producer + consumer
└── monitoring/         # Batch prediction + drift detection

k8s/
├── base/               # Core K8s resources (all environments)
├── overlays/dev/       # Dev-specific (minikube, test secrets)
├── overlays/prod/      # Prod-specific (ingress, cert, real secrets)
├── tools/              # Internal tools (pgAdmin, MLflow)
├── jobs/               # Jobs + CronJobs (migration, batch, drift, backup)
└── helm-values/        # Helm configs (PostgreSQL, Kafka, Airflow)

dags/                   # Airflow DAGs
migrations/             # Alembic DB migrations
docs/                   # Documentation
tests/                  # Unit tests
```

## ML Pipeline
- Pipeline: preprocessor + add_features + model (full sklearn Pipeline)
- Save model to MLflow Registry (production) or joblib file (dev)
- Load model: `models:/fraud_detector/Production` (MLflow) or file path
- Tune with Optuna → save params to `model/best_params.json`
- Train reads params → logs to MLflow → registers model
- No data leakage: split test set before tuning

## Database
- Schema in `src/db/models.py`
- Connection from `src/db/connection.py` (pool_size=5, pool_pre_ping=True)
- Boolean columns cast to float before sklearn pipeline
- Migrations via Alembic (`migrations/versions/`)
- Separate DB users: admin, api_user, scorer_user, analyst (least privilege)

## Kafka / Streaming
- Producer: `src/streaming/producer.py` — polls DB → sends to "transactions" topic
- Consumer: `src/streaming/consumer.py` — listens → predict → save to predictions
- Config: `KAFKA_BOOTSTRAP_SERVERS` env var
- Producer: acks=all, batch flush, error callback
- Consumer: retry on DB save, continue on error

## Docker
- Single Dockerfile (multi-stage) for api, scorer, producer (same image, different command)
- Commands:
  - API: default CMD (uvicorn)
  - Producer: `python -m src.streaming.producer`
  - Scorer: `python -m src.streaming.consumer`
- Non-root user (appuser), read-only filesystem, 4 workers
- Never commit `.env` to git

## Kubernetes
- Namespace: `fraud-detection`
- Deploy: `kubectl apply -f k8s/base/` + `kubectl apply -f k8s/overlays/dev/` or `/prod/`
- Managed services via Helm: PostgreSQL, Kafka, Airflow
- Security: non-root, drop ALL caps, read-only fs, network policy, seccomp
- Model loaded from MLflow (no rebuild needed for model changes)

## CI/CD
- Lint (ruff) → Test (pytest) → SAST (bandit, pip-audit) → Build → Trivy scan → Deploy → Smoke test
- Auto-rollback on failure
- Image tag: git SHA
- Secrets in GitHub Actions secrets
- Production environment requires approval

## Commands
```bash
# ML Pipeline
python -m src.pipeline.tune                    # find best params
python -m src.pipeline.train                   # train model

# Batch / Monitoring
python -m src.monitoring.batch_prediction      # batch predict
python -m src.monitoring.drift_monitor         # check drift

# Streaming
python -m src.streaming.producer               # start producer
python -m src.streaming.consumer               # start consumer

# Testing
pytest -v                                       # run tests
ruff check src/ tests/                         # lint
ruff format src/ tests/                        # format

# Docker (local dev)
docker compose up -d --build                   # run everything

# Kubernetes (minikube)
kubectl apply -f k8s/base/                     # deploy core
kubectl apply -f k8s/overlays/dev/             # dev config
kubectl apply -f k8s/tools/                    # pgAdmin, MLflow
kubectl apply -f k8s/jobs/                     # CronJobs

# Kubernetes (production)
kubectl apply -f k8s/base/                     # deploy core
kubectl apply -f k8s/overlays/prod/            # prod config (ingress, cert)
```
