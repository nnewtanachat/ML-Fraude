# ML-Fraud — Architecture & File Summary

## 1. Project Overview

End-to-end fraud detection ML pipeline:
- Train model → Deploy API → Real-time scoring → Batch prediction → Drift monitoring

---

## 2. Architecture (Production — Cloud)

```
┌──────────────────────────────────────────────────────────────────┐
│                         Cloud (GCP/AWS)                            │
│                                                                    │
│  Users/Clients                                                     │
│       │                                                            │
│       ▼ HTTPS                                                      │
│  ┌──────────────┐                                                  │
│  │ WAF + LB     │ ← DDoS protection, IP whitelist, rate limit     │
│  └──────┬───────┘                                                  │
│         │                                                          │
│  ┌──────▼────────────── K8s Cluster (Private) ──────────────────┐ │
│  │                                                                │ │
│  │  ┌─────────────────── App Layer ───────────────────────────┐  │ │
│  │  │                                                          │  │ │
│  │  │  fraud-api (2+ pods, auto-scale)                         │  │ │
│  │  │     ├── POST /predict (real-time scoring)                │  │ │
│  │  │     ├── GET /health                                      │  │ │
│  │  │     └── GET /metrics (Prometheus)                        │  │ │
│  │  │                                                          │  │ │
│  │  │  fraud-producer (1 pod)                                  │  │ │
│  │  │     └── Poll DB → send to Kafka                          │  │ │
│  │  │                                                          │  │ │
│  │  │  fraud-scorer (2 pods)                                   │  │ │
│  │  │     └── Listen Kafka → predict → save to DB              │  │ │
│  │  │                                                          │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  │                                                                │ │
│  │  ┌─────────────────── MLOps Tools ─────────────────────────┐  │ │
│  │  │  MLflow (experiment tracking, model registry)            │  │ │
│  │  │  Airflow (training pipeline orchestration)               │  │ │
│  │  │  Grafana (monitoring dashboard)                          │  │ │
│  │  │  pgAdmin (DB query UI for analysts)                      │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  │                                                                │ │
│  │  ┌─────────────────── Scheduled Jobs ──────────────────────┐  │ │
│  │  │  CronJob: batch-predict (ทุกวัน 6 โมง)                   │  │ │
│  │  │  CronJob: drift-monitor (ทุกวัน 7 โมง)                   │  │ │
│  │  │  CronJob: db-backup (ทุกวัน ตี 3)                        │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  │                                                                │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌─────────────────── Managed Services ───────────────────────┐   │
│  │  PostgreSQL (Cloud SQL / RDS) — private IP, encrypted       │   │
│  │  Kafka (Pub/Sub / MSK) — streaming                          │   │
│  │  Redis (Memorystore / ElastiCache) — cache (optional)       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                    │
│  ┌─────────────────── Security Layer ─────────────────────────┐   │
│  │  Secret Manager — passwords, API keys                       │   │
│  │  KMS — encryption at rest                                   │   │
│  │  Audit Logs — ทุก action ถูก log                            │   │
│  │  IAM / Workload Identity — pod-level permissions            │   │
│  │  Network Policy — firewall ระหว่าง pods                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                    │
│  ┌─────────────────── CI/CD Pipeline ─────────────────────────┐   │
│  │  Push → Lint → Test → SAST → Build → Scan → Deploy → DAST  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. File Structure & What Each File Does

### Python Source Code (`src/`)

```
src/
├── serve/
│   ├── main.py              → FastAPI app: /predict, /health, /metrics
│   │                           Prometheus metrics + structured JSON logging
│   ├── config.py            → Settings from env vars (pydantic-settings)
│   ├── security.py          → API key authentication (X-API-Key header)
│   ├── schemas.py           → Request/response validation (Pydantic)
│   └── logging_config.py    → JSON log formatter for production
│
├── db/
│   ├── models.py            → SQLAlchemy table definitions
│   ├── connection.py        → DB engine with connection pooling
│   └── load_data.py         → One-time CSV → DB loader
│
├── preprocess.py            → Feature engineering + sklearn pipeline
├── train.py                 → Train model (reads best_params.json) + MLflow tracking
├── tune.py                  → Hyperparameter tuning (Optuna + cross-validation)
├── kafka_producer.py        → Poll DB for new transactions → send to Kafka
├── kafka_consumer.py        → Listen Kafka → predict → save to predictions table
├── batch_prediction.py      → Batch score transactions not yet predicted
└── drift_monitor.py         → Check data drift + prediction drift (Evidently)
```

### Kubernetes (`k8s/`)

```
k8s/
├── namespace.yaml              → สร้าง namespace "fraud-detection"
├── configmap.yaml              → Config ที่ไม่ sensitive (MODEL_PATH, THRESHOLD, etc.)
├── secret.yaml                 → Passwords, API keys (ห้าม commit ค่าจริง!)
├── service-account.yaml        → Pod identity (fraud-api-sa, fraud-worker-sa)
│
├── api-deployment.yaml         → API: 2 replicas, rolling update, 3 probes,
│                                  security (non-root, read-only fs, drop caps)
├── api-service.yaml            → Expose API (ClusterIP, port 80 → 8000)
├── producer-deployment.yaml    → Kafka producer: 1 replica
├── scorer-deployment.yaml      → Kafka consumer: 2 replicas
│
├── hpa.yaml                    → Auto-scale API: 2→10 pods (CPU>70% / mem>80%)
├── pdb.yaml                    → ป้องกัน downtime: min 1 pod available always
├── network-policy.yaml         → Firewall: default deny + explicit allow
├── resource-quota.yaml         → จำกัด resource ของ namespace (4 CPU, 8Gi RAM)
│
├── ingress.yaml                → API: HTTPS + rate limit + IP whitelist (GCP nginx)
├── pgadmin-deployment.yaml     → pgAdmin UI (query DB)
├── pgadmin-service.yaml        → Expose pgAdmin (ClusterIP)
├── pgadmin-configmap.yaml      → Auto-connect DB config (servers.json)
├── pgadmin-ingress.yaml        → pgAdmin: HTTPS + IP whitelist (GCP)
├── pgadmin-ingress-aws.yaml    → pgAdmin: ALB + WAF (AWS)
│
├── mlflow-deployment.yaml      → MLflow tracking server (experiments, model registry)
├── mlops-ingress.yaml          → Route: pgAdmin + MLflow + Grafana + Airflow (1 ingress)
├── cert-issuer.yaml            → Let's Encrypt auto-cert (HTTPS ฟรี)
│
├── migration-job.yaml          → Run Alembic migration (one-time before deploy)
├── batch-predict-cronjob.yaml  → ทุกวัน 6 โมง: score transactions ที่ตกหล่น
├── drift-monitor-cronjob.yaml  → ทุกวัน 7 โมง: ตรวจ model drift
├── backup-cronjob.yaml         → ทุกวัน ตี 3: backup DB
│
├── postgres-init-configmap.yaml → SQL script สร้าง DB users (auto run ครั้งแรก)
├── postgres-values.yaml        → Helm config สำหรับ PostgreSQL
├── kafka-values.yaml           → Helm config สำหรับ Kafka
└── airflow-values.yaml         → Helm config สำหรับ Airflow
```

### Airflow DAGs (`dags/`)

```
dags/
├── fraud_pipeline_dag.py       → Weekly: tune → train → batch_predict
├── daily_batch_predict_dag.py  → Daily: batch predict ที่ตกหล่น
└── drift_monitor_dag.py        → Daily: check drift → retrain ถ้าจำเป็น
```

### Database Migrations (`migrations/`)

```
migrations/
├── env.py                      → Alembic runtime config
├── script.py.mako              → Template สำหรับ migration ใหม่
└── versions/
    ├── 001_create_tables.py    → Create tables + indexes + users
    └── 002_create_drift_reports.py → Create drift_reports table
```

### DevOps Files (root)

```
├── Dockerfile                  → Multi-stage, non-root, 4 workers, healthcheck
├── docker-compose.yml          → Local dev (all services)
├── .github/workflows/ci.yml   → CI/CD: lint → test → build → scan → push
├── requirements.txt            → Pinned versions (==)
├── ruff.toml                   → Linter config
├── alembic.ini                 → DB migration config
├── .env.example                → Template for environment variables
└── .gitignore                  → Ignore secrets, model, cache
```

---

## 4. Data Flow

```
Transaction เข้าระบบ
    │
    ├── Real-time path:
    │   App → API /predict → model.predict_proba() → response ทันที
    │
    ├── Streaming path:
    │   DB → Producer → Kafka → Scorer → predict → save predictions table
    │
    └── Batch path (daily):
        CronJob → batch_prediction.py → query DB → predict → save predictions

Monitoring (daily):
    drift_monitor.py → เทียบ reference vs current data → alert if drift
```

---

## 5. Deploy Commands

### Local Dev:
```bash
docker compose up -d --build
```

### Minikube (test K8s):
```bash
minikube start
eval $(minikube docker-env)
docker build -t ml-fraud:v1 .
helm install postgres bitnami/postgresql -n fraud-detection -f k8s/postgres-values.yaml
kubectl apply -f k8s/
```

### Production (GCP):
```bash
gcloud container clusters create fraud-cluster ...
helm install postgres bitnami/postgresql -n fraud-detection -f k8s/postgres-values.yaml
helm install kafka bitnami/kafka -n fraud-detection -f k8s/kafka-values.yaml
helm install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace
helm install cert-manager jetstack/cert-manager -n cert-manager --create-namespace
kubectl apply -f k8s/
```

### Production (AWS):
```bash
eksctl create cluster --name fraud-cluster ...
helm install aws-load-balancer-controller eks/aws-load-balancer-controller ...
helm install postgres bitnami/postgresql -n fraud-detection -f k8s/postgres-values.yaml
kubectl apply -f k8s/
```

---

## 6. Security Summary (ISO 27001)

| Control | Implementation |
|---------|---------------|
| Access Control | API key + IAM + K8s RBAC + DB least privilege |
| Encryption | HTTPS (TLS) + DB encrypted at rest (KMS) |
| Logging | Structured JSON logs + Cloud Audit Logs |
| Vulnerability | Image scan (Trivy) + dependency pin + SAST |
| Network | VPC + private subnet + Network Policy + WAF |
| Business Continuity | Multi-AZ DB + backup CronJob + HPA |
| Change Management | CI/CD audit trail + Alembic migrations |
| Monitoring | Prometheus + Grafana + drift detection + alerts |
