# Fraud Detection ML Pipeline

End-to-end machine learning pipeline สำหรับตรวจจับธุรกรรมที่เป็นการฉ้อโกง (fraud detection) ครอบคลุมตั้งแต่การเก็บข้อมูลใน database, การ train model, จนถึงการ serve เป็น REST API พร้อม experiment tracking และ automated testing

## Architecture

```
                  ┌──────────────┐
   fraud.csv ───► │  PostgreSQL  │ ◄── docker-compose
                  └──────┬───────┘
                         │ (read)
                         ▼
                  ┌──────────────┐      ┌──────────┐
                  │  train.py    │ ───► │  MLflow  │  (track params/metrics)
                  │ (preprocess  │      └──────────┘
                  │  + XGBoost)  │
                  └──────┬───────┘
                         │ (save .pkl)
                         ▼
                  ┌──────────────┐
                  │  FastAPI     │  /predict, /health
                  │  (serve)     │  + API key auth
                  └──────────────┘
```

## Tech Stack

| ส่วน | เครื่องมือ |
|------|-----------|
| Data storage | PostgreSQL (SQLAlchemy ORM) |
| ML | scikit-learn, XGBoost, imbalanced-learn |
| Experiment tracking | MLflow |
| Serving | FastAPI, Pydantic, Uvicorn |
| Containerization | Docker, docker-compose |
| Testing | pytest |
| CI | GitHub Actions |

## Project Structure

```
ML-Fraud/
├── data/                   # ข้อมูลดิบ (fraud.csv)
├── notebook/               # EDA
│   └── eda.ipynb
├── src/
│   ├── db/                 # database layer
│   │   ├── models.py       # SQLAlchemy schema
│   │   ├── connection.py   # engine + session
│   │   └── load_data.py    # โหลด CSV เข้า DB
│   ├── serve/              # FastAPI app
│   │   ├── main.py         # endpoints
│   │   ├── config.py       # settings (pydantic-settings)
│   │   ├── schemas.py      # request/response models
│   │   └── security.py     # API key auth
│   ├── preprocess.py       # preprocessing pipeline
│   └── train.py            # training + MLflow tracking
├── tests/                  # pytest
├── model/                  # trained model (.pkl)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Dataset

ข้อมูลธุรกรรม 7,000 รายการ มี 12 features (transaction_amount, customer_age, distance_from_home, velocity_score ฯลฯ) และ target `is_fraud`

- Class distribution: fraud ~10.3% (721 / 7000) — imbalanced
- มี missing values ในเกือบทุก column (2-15%) จัดการด้วย median/mode imputation

## Setup

### 1. Clone + สร้าง virtual environment

```bash
git clone <repo-url>
cd ML-Fraud
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. ตั้งค่า environment variables

สร้างไฟล์ `.env` (ดูตัวอย่างด้านล่าง):

```
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_password
POSTGRES_DB=fraud_detection
DATABASE_URL=postgresql://admin:your_password@localhost:5432/fraud_detection
MODEL_PATH=model/fraud_pipeline.pkl
API_KEY=your_secret_api_key
FRAUD_THRESHOLD=0.5
```

> สร้าง API key ด้วย: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### 3. เปิด PostgreSQL + โหลดข้อมูล

```bash
docker compose up -d db
python src/db/load_data.py
```

## Usage

### Train model

```bash
python -m src.train
```

ดูผลการทดลองใน MLflow:

```bash
mlflow ui
# เปิด http://localhost:5000
```

### รัน API

```bash
uvicorn src.serve.main:app --reload
# เปิด http://localhost:8000/docs
```

หรือรันทั้งระบบ (API + DB) ด้วย Docker:

```bash
docker compose up -d --build
```

### เรียก API

```bash
curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: your_secret_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_amount": 150.0, "hour_of_day": 2.0, "is_weekend": 0.0,
    "num_items": 3.0, "customer_age": 35.0, "prev_transactions": 5.0,
    "distance_from_home": 20.0, "device_type": 1.0, "network_quality": 75.0,
    "is_first_transaction": 0.0, "store_type": 0.0, "velocity_score": 5.0
  }'
```

Response:

```json
{
  "fraud_probability": 0.1234,
  "is_fraud": false,
  "threshold": 0.5
}
```

## API Endpoints

| Method | Path | คำอธิบาย | Auth |
|--------|------|----------|------|
| GET | `/health` | เช็คสถานะ service | ไม่ต้อง |
| POST | `/predict` | ทำนาย fraud | ต้องมี API key |
| GET | `/docs` | Swagger UI | ไม่ต้อง |

## Testing

```bash
python -m pytest -v
```

- `test_preprocess.py` — preprocessing (impute, scale, shape)
- `test_schemas.py` — input validation
- `test_api.py` — API endpoints + auth

## Model

ใช้ XGBoost จัดการ class imbalance ด้วย `scale_pos_weight`

Metrics ที่ใช้ประเมิน (เหมาะกับ imbalanced data): ROC-AUC, PR-AUC, Precision, Recall, F1

> หมายเหตุ: dataset ที่ใช้เป็นข้อมูล synthetic ที่ features มีความสัมพันธ์กับ target ต่ำ ทำให้ ROC-AUC อยู่ที่ประมาณ 0.5 โปรเจคนี้เน้นการสร้าง production ML pipeline ที่สมบูรณ์มากกว่าผลลัพธ์ของ model

## Notes

- `.env` ไม่ถูก commit ขึ้น git (อยู่ใน `.gitignore`) — เก็บ credentials ไว้ในเครื่อง
- API ใช้ API key authentication ผ่าน header `X-API-Key`
- ก่อน deploy production จริง ควรเปลี่ยนเป็น HTTPS และใช้ secret manager
