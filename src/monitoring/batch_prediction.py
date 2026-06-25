import os
import logging
from datetime import datetime

import joblib
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from src.pipeline.preprocess import FEATURE_COLS

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
MODEL_PATH = os.getenv("MODEL_PATH", "model/fraud_pipeline.pkl")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow.fraud-detection.svc:5000")
THRESHOLD = float(os.getenv("FRAUD_THRESHOLD", "0.5"))
MODEL_VERSION = os.getenv("APP_VERSION", "v1")
BATCH_SIZE = 1000  # process ทีละ 1000 rows ป้องกัน memory spike


def get_new_data(engine) -> pd.DataFrame:
    """ดึง transactions ที่ยังไม่ถูก predict."""
    query = f"""
        SELECT * FROM transactions
        WHERE id NOT IN (SELECT transaction_id FROM predictions)
        LIMIT {BATCH_SIZE}
    """
    return pd.read_sql(query, engine)


def predict_batch(pipeline, df: pd.DataFrame) -> pd.DataFrame:
    """Predict fraud probability for a batch of transactions."""
    X = df[FEATURE_COLS]
    probas = pipeline.predict_proba(X)[:, 1]

    return pd.DataFrame({
        "transaction_id": df["id"],
        "fraud_probability": probas.round(4),
        "predicted_fraud": (probas >= THRESHOLD),
        "threshold": THRESHOLD,
        "model_version": MODEL_VERSION,
        "predicted_at": datetime.now(),
    })


def save_results(results: pd.DataFrame, engine) -> None:
    """บันทึกผลลง predictions table."""
    results.to_sql("predictions", engine, if_exists="append", index=False)


def main():
    engine = create_engine(
        DATABASE_URL,
        pool_size=3,
        pool_recycle=3600,
        pool_pre_ping=True,
    )

    # 1. โหลด model
    if MODEL_PATH.startswith("models:/"):
        import mlflow

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        logger.info("Loading model from MLflow Registry: %s", MODEL_PATH)
        pipeline = mlflow.sklearn.load_model(MODEL_PATH)
    else:
        logger.info("Loading model from file: %s", MODEL_PATH)
        pipeline = joblib.load(MODEL_PATH)
    logger.info("Model loaded: %s", MODEL_VERSION)

    # 2. ดึงข้อมูลใหม่
    df = get_new_data(engine)
    if df.empty:
        logger.info("No new data to predict")
        return
    logger.info("New data: %d rows", len(df))

    # 3. Predict
    results = predict_batch(pipeline, df)

    # 4. บันทึก
    save_results(results, engine)

    # 5. Log สรุป
    n_fraud = int(results["predicted_fraud"].sum())
    total = len(results)
    fraud_pct = (n_fraud / total * 100) if total > 0 else 0.0
    logger.info(
        "Results: %d fraud / %d total (%.1f%%)",
        n_fraud, total, fraud_pct,
    )


if __name__ == "__main__":
    main()
