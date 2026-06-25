import os
import json
import logging
from datetime import datetime

import joblib
import pandas as pd
from dotenv import load_dotenv
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from sqlalchemy import create_engine

from src.pipeline.preprocess import FEATURE_COLS

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
MODEL_PATH = os.getenv("MODEL_PATH", "model/fraud_pipeline.pkl")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow.fraud-detection.svc:5000")
THRESHOLD = float(os.getenv("FRAUD_THRESHOLD", "0.5"))
KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
MODEL_VERSION = os.getenv("APP_VERSION", "v1")
TOPIC = "transactions"
MAX_RETRIES = 3


def load_model():
    """Load model from MLflow Registry or local file."""
    if MODEL_PATH.startswith("models:/"):
        import mlflow

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        logger.info("Loading model from MLflow Registry: %s", MODEL_PATH)
        return mlflow.sklearn.load_model(MODEL_PATH)
    else:
        logger.info("Loading model from file: %s", MODEL_PATH)
        return joblib.load(MODEL_PATH)


def create_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        group_id="fraud-scorer",
        enable_auto_commit=True,
        auto_commit_interval_ms=5000,
        max_poll_interval_ms=300000,
    )


def score_transaction(pipeline, txn: dict) -> dict:
    df = pd.DataFrame([txn])
    X = df[FEATURE_COLS]
    proba = float(pipeline.predict_proba(X)[0, 1])
    return {
        "transaction_id": txn.get("id"),
        "fraud_probability": round(proba, 4),
        "predicted_fraud": proba >= THRESHOLD,
        "threshold": THRESHOLD,
        "model_version": MODEL_VERSION,
        "predicted_at": datetime.now(),
    }


def save_prediction(result: dict, engine) -> None:
    """Save prediction to DB with retry."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            pd.DataFrame([result]).to_sql(
                "predictions", engine, if_exists="append", index=False
            )
            return
        except Exception as e:
            logger.warning(
                "Failed to save prediction (attempt %d/%d): %s",
                attempt, MAX_RETRIES, e,
            )
            if attempt == MAX_RETRIES:
                raise


def main():
    pipeline = load_model()
    engine = create_engine(
        DATABASE_URL,
        pool_size=3,
        pool_recycle=3600,
        pool_pre_ping=True,
    )
    consumer = create_consumer()

    logger.info("Listening to Kafka topic '%s' for new transactions...", TOPIC)

    for message in consumer:
        txn = message.value
        txn_id = txn.get("id", "unknown")

        try:
            result = score_transaction(pipeline, txn)
            save_prediction(result, engine)

            if result["predicted_fraud"]:
                logger.warning(
                    "FRAUD DETECTED id=%s proba=%.4f",
                    txn_id, result["fraud_probability"],
                )
            else:
                logger.info(
                    "OK id=%s proba=%.4f",
                    txn_id, result["fraud_probability"],
                )
        except Exception as e:
            # Log error แต่ไม่หยุด consumer — ไป message ถัดไป
            logger.error(
                "Failed to process transaction id=%s: %s", txn_id, e,
                exc_info=True,
            )


if __name__ == "__main__":
    main()
