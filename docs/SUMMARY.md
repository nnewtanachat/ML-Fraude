# ML-Fraud Project — สรุปทั้งหมดที่ทำ

## 1. Production Improvements ที่ทำไปแล้ว

### 1.1 CI/CD Enhancement (`.github/workflows/ci.yml`)

| สิ่งที่เพิ่ม | ทำอะไร |
|-------------|--------|
| **Ruff Lint** | ตรวจ code quality + format ก่อน test |
| **Image Tagging** | tag ด้วย `latest` + `git SHA` + `timestamp` (rollback ได้) |
| **Build Cache** | ใช้ GitHub Actions cache → build เร็วขึ้น |
| **Trivy Scan** | scan Docker image หา vulnerability CRITICAL/HIGH |

**Flow:** `Lint → Test → Build → Push → Scan`

---

### 1.2 Dockerfile Security

| สิ่งที่เพิ่ม | ทำอะไร |
|-------------|--------|
| **Non-root user** | สร้าง `appuser` ไม่ให้ container run as root |
| **HEALTHCHECK** | Docker/K8s ตรวจว่า app ยังทำงานอยู่ |
| **EXPOSE 8000** | ประกาศ port ชัดเจน |

---

### 1.3 Structured Logging + Prometheus Metrics

| ไฟล์ | ทำอะไร |
|------|--------|
| `src/serve/logging_config.py` | JSON formatter → log เป็น structured format |
| `src/serve/main.py` | เพิ่ม Prometheus metrics + `/metrics` endpoint |
| `src/serve/config.py` | เพิ่ม `LOG_LEVEL` setting |

**Metrics ที่เก็บ:**
- `http_requests_total` — นับ request (method/endpoint/status)
- `http_request_duration_seconds` — latency
- `predictions_total` — นับ prediction (fraud/legit)
- `prediction_probability` — distribution ของ probability
- `model_loaded` — model พร้อมหรือไม่ (1/0)

---

### 1.4 Docker Compose Enhancement

| สิ่งที่เพิ่ม | ทำอะไร |
|-------------|--------|
| **Resource limits** | จำกัด memory/cpu ทุก service |
| **Kafka healthcheck** | เช็คว่า Kafka พร้อมก่อน start consumer |
| **`condition: service_healthy`** | รอ DB/Kafka healthy จริงก่อน start service อื่น |
| **LOG_LEVEL env** | ปรับ log level ได้โดยไม่ rebuild |

---

### 1.5 Linter Config (`ruff.toml`)

- Target Python 3.12
- Line length 120
- Rules: pycodestyle, pyflakes, isort, bugbear, bandit (security), pyupgrade
- Ignore FastAPI patterns (Depends in defaults)

---

## 2. Kubernetes Deployment (`k8s/`)

### ไฟล์ที่สร้าง:

| ไฟล์ | ทำอะไร |
|------|--------|
| `namespace.yaml` | แยก project เป็น namespace `fraud-detection` |
| `configmap.yaml` | config ที่ไม่ sensitive (MODEL_PATH, THRESHOLD, etc.) |
| `secret.yaml` | passwords, API keys (ห้าม commit ค่าจริง) |
| `api-deployment.yaml` | API pods: 2 replicas, rolling update, probes |
| `api-service.yaml` | Expose API ภายใน cluster (ClusterIP) |
| `producer-deployment.yaml` | Kafka producer: 1 replica |
| `scorer-deployment.yaml` | Kafka consumer: 2 replicas |
| `hpa.yaml` | Auto-scale API: 2→10 pods ตาม CPU/memory |
| `network-policy.yaml` | Default deny + explicit allow (security) |
| `ingress.yaml` | HTTPS + rate limit + IP whitelist (optional) |
| `pgadmin-deployment.yaml` | Web UI สำหรับ query DB |

### Security Best Practices ใน K8s:

- ✅ Non-root containers (runAsUser: 1000)
- ✅ Network Policy (default deny)
- ✅ Secrets แยกจาก config
- ✅ Resource limits ทุก pod
- ✅ Rolling update (zero downtime)
- ✅ Health checks (readiness + liveness + startup)
- ✅ Rate limiting (Ingress)
- ✅ IP Whitelist (Ingress)
- ✅ TLS/HTTPS (cert-manager)
- ✅ Topology spread (pods กระจายหลาย node)

---

## 3. Concepts ที่อธิบายไป

### 3.1 Docker/Container

| Concept | สรุป |
|---------|------|
| `0.0.0.0` | ฟังทุก network interface (จำเป็นใน container) |
| `HEALTHCHECK` | Docker/K8s เช็คว่า app ยังมีชีวิต |
| Multi-stage build | แยก build/runtime → image เล็กลง |
| Non-root user | ป้องกัน privilege escalation |
| Retry loop (pip install) | ถ้า success → break, ถ้า fail → retry |

### 3.2 Kafka 3 Ports

| Port | ใคร | ทำอะไร |
|------|-----|--------|
| 9092 | Container ใน Docker | Producer/Consumer คุยกับ Kafka |
| 9093 | Kafka internal | KRaft protocol (แทน ZooKeeper) |
| 9094 | เครื่อง host (dev) | Debug จากเครื่องตัวเอง |

### 3.3 Network (Production)

| Layer | ทำอะไร |
|-------|--------|
| **VPC** | Network ส่วนตัวบน cloud |
| **Public Subnet** | API + Load Balancer (รับ internet) |
| **Private Subnet** | DB, Kafka, internal services (ไม่มี public IP) |
| **Firewall/Network Policy** | กำหนดว่าใครคุยกับใครได้ |
| **Load Balancer** | SSL termination + กระจาย traffic |

### 3.4 Python/FastAPI

| Concept | สรุป |
|---------|------|
| `@asynccontextmanager` | Startup (ก่อน yield) → App ทำงาน → Shutdown (หลัง yield) |
| `lifespan` | โหลด model ก่อน serve, ล้าง memory ตอนปิด |
| `MODEL_LOADED.set(1)` | Prometheus gauge บอกว่า model พร้อม |
| Middleware | ดักทุก request → จับเวลา + นับ → บันทึก metrics |
| `depends_on: condition: service_healthy` | รอ service จริงๆ healthy ก่อน start |

### 3.5 CI/CD Pipeline

```
Push code → Lint (ruff) → Test (pytest) → Build image → Push registry → Trivy scan
```

- PR: รัน lint + test เท่านั้น
- Push main: รัน lint + test + build + push + scan

---

## 4. Deploy ขึ้น GCP (Google Cloud)

### คำสั่งเรียงลำดับ:

```bash
# 1. Setup project
gcloud config set project ml-fraud-prod
gcloud services enable container.googleapis.com artifactregistry.googleapis.com sqladmin.googleapis.com

# 2. สร้าง Image Registry
gcloud artifacts repositories create ml-fraud --repository-format=docker --location=asia-southeast1
gcloud auth configure-docker asia-southeast1-docker.pkg.dev

# 3. Build + Push image
docker build -t asia-southeast1-docker.pkg.dev/ml-fraud-prod/ml-fraud/api:v1.0.0 .
docker push asia-southeast1-docker.pkg.dev/ml-fraud-prod/ml-fraud/api:v1.0.0

# 4. สร้าง GKE cluster
gcloud container clusters create fraud-cluster --zone=asia-southeast1-a --num-nodes=2 --machine-type=e2-medium
gcloud container clusters get-credentials fraud-cluster --zone=asia-southeast1-a

# 5. สร้าง Cloud SQL (managed DB)
gcloud sql instances create fraud-db --database-version=POSTGRES_16 --tier=db-f1-micro --region=asia-southeast1

# 6. Deploy K8s
kubectl apply -f k8s/

# 7. ตรวจสอบ
kubectl get pods -n fraud-detection
```

### Mapping: Docker Compose → Cloud

| Local | Cloud |
|-------|-------|
| `db` container | Cloud SQL |
| `kafka` container | Pub/Sub / Confluent Cloud |
| `api` container | Cloud Run / GKE |
| `scorer` container | Cloud Run / GKE |
| `.env` file | Secret Manager |
| `docker-compose.yml` | K8s YAML / Terraform |

---

## 5. Airflow (Orchestration)

### 2 DAGs ที่ออกแบบ:

| DAG | Schedule | ทำอะไร |
|-----|----------|--------|
| `fraud_ml_pipeline` | ทุกอาทิตย์ ตี 2 | load data → tune → validate → train → batch predict |
| `daily_batch_predict` | ทุกวัน 6 โมง | score transactions ที่ตกหล่น |

### Airflow vs Kafka:

| | Airflow | Kafka |
|--|---------|-------|
| แบบ | Batch (ตามเวลา) | Streaming (real-time) |
| ใช้ตอน | Retrain, batch predict | Score ทันทีเมื่อ transaction เข้ามา |
| แทนกันได้ไหม | ❌ ทำงานเสริมกัน | ❌ ทำงานเสริมกัน |

---

## 6. Security Best Practices

### Priority (เรียงตาม impact):

| # | Practice | สถานะ |
|---|----------|-------|
| 1 | Non-root container | ✅ ทำแล้ว |
| 2 | Image vulnerability scan | ✅ ทำแล้ว |
| 3 | API Key auth | ✅ มีอยู่แล้ว |
| 4 | Network Policy (K8s) | ✅ ทำแล้ว |
| 5 | Secrets ใน K8s Secret | ✅ ทำแล้ว |
| 6 | Input validation | ✅ มีอยู่แล้ว (Pydantic) |
| 7 | Rate limiting | ✅ Ingress annotation |
| 8 | IP Whitelist | ✅ Ingress annotation |
| 9 | TLS/HTTPS | ✅ cert-manager |
| 10 | Pin dependency versions | ⚠️ ยังใช้ `>=` |
| 11 | DB least privilege user | ⚠️ ยังไม่แยก user |
| 12 | Secret Manager (cloud) | ⚠️ ยังใช้ K8s Secret |

---

## 7. คำสั่งที่ใช้บ่อย

### Local Development:

```bash
docker compose up -d --build     # เปิดทุก service
docker compose logs -f api       # ดู API logs
docker compose down              # ปิดทุกอย่าง
python -m src.pipeline.tune               # หา best hyperparameters
python -m src.pipeline.train              # train model
pytest -v                        # run tests
```

### Kubernetes:

```bash
kubectl apply -f k8s/                           # deploy ทั้งหมด
kubectl get pods -n fraud-detection             # ดู status
kubectl logs -f deployment/fraud-api -n fraud-detection  # ดู logs
kubectl port-forward svc/pgadmin 8080:80 -n fraud-detection  # เข้า pgAdmin
kubectl get hpa -n fraud-detection              # ดู auto-scale status
```

---

## 8. โครงสร้างไฟล์ปัจจุบัน

```
ML-Fraud/
├── .github/workflows/ci.yml     # CI/CD pipeline
├── k8s/                         # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── api-deployment.yaml
│   ├── api-service.yaml
│   ├── producer-deployment.yaml
│   ├── scorer-deployment.yaml
│   ├── hpa.yaml
│   ├── network-policy.yaml
│   ├── ingress.yaml
│   ├── pgadmin-deployment.yaml
│   └── README.md
├── src/
│   ├── serve/                   # FastAPI + metrics + logging
│   ├── db/                      # Database models + connection
│   ├── preprocess.py            # Feature engineering
│   ├── train.py                 # Model training
│   ├── tune.py                  # Hyperparameter tuning
│   ├── kafka_producer.py        # Stream producer
│   ├── kafka_consumer.py        # Stream consumer (scorer)
│   └── batch_prediction.py      # Batch scoring
├── model/                       # Trained pipeline (.pkl)
├── data/                        # Raw data (CSV)
├── Dockerfile                   # Production-ready (non-root, healthcheck)
├── docker-compose.yml           # Local dev environment
├── ruff.toml                    # Linter config
├── requirements.txt             # Dependencies
└── .env.example                 # Environment variables template
```
