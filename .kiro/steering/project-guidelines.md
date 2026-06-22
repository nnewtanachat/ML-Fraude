# ML-Fraud Project Guidelines

## Project Overview
End-to-end fraud detection ML pipeline with real-time scoring capabilities.

## Architecture
- **Database**: PostgreSQL (SQLAlchemy ORM)
- **ML**: XGBoost with sklearn Pipeline (impute → feature eng → model)
- **Serving**: FastAPI + API key auth
- **Streaming**: Apache Kafka (producer → consumer)
- **Tracking**: MLflow
- **Containerization**: Docker + docker-compose
- **CI/CD**: GitHub Actions

## Key Conventions

### Code Style
- Use type hints for function signatures
- Logging with `logging` module (not print)
- Config from environment variables via pydantic-settings
- Keep business logic in `src/`, tests in `tests/`

### ML Pipeline
- Pipeline must include: preprocessor + add_features + model (full pipeline)
- Always save full pipeline (not just model) via joblib
- Tune with Optuna → save params to `model/best_params.json`
- Train reads params from json → save pipeline to `model/fraud_pipeline.pkl`
- No data leakage: split test set before tuning

### Database
- Schema defined in `src/db/models.py`
- Connection from `src/db/connection.py` (import engine, don't create new)
- Boolean columns must be cast to float before sklearn pipeline

### Kafka
- Producer polls DB for new transactions → sends to topic "transactions"
- Consumer listens → predict via pipeline → save to predictions table
- Internal (Docker): `kafka:9092`, External (host): `localhost:9094`

### Docker
- Single Dockerfile for api, scorer, producer (same image, different command)
- Environment variables via `.env` (docker-compose reads automatically)
- Never commit `.env` to git

### Testing
- `pytest` for unit tests
- CI runs: `test_schemas.py` + `test_preprocess.py`
- Use `with TestClient(app) as c:` for API tests (triggers lifespan)

### Deployment
- CI: test on every push/PR
- CD: build + push Docker image to Docker Hub (only on push to main)
- Secrets stored in GitHub Actions secrets

## File Structure
```
src/
├── db/              # database layer
├── serve/           # FastAPI API
├── preprocess.py    # preprocessing + feature engineering
├── train.py         # training (reads best_params.json)
├── tune.py          # hyperparameter tuning (Optuna + CV)
├── kafka_producer.py
├── kafka_consumer.py
└── batch_prediction.py
```

## Commands
```bash
python -m src.tune          # find best params
python -m src.train         # train model
python -m pytest -v         # run tests
docker compose up -d --build  # run everything
```
