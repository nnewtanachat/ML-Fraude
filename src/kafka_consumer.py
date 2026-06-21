import os
import json
import logging
from datetime import datetime

import joblib
import pandas as pd
from dotenv import load_dotenv
from kafka import KafkaConsumer
from sqlalchemy import create_engine

from src.preprocess import FEATURE_COLS

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
MODEL_PATH = os.getenv("MODEL_PATH")
THRESHOLD = float(os.getenv("FRAUD_THRESHOLD"))
KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
MODEL_VERSION = "v1"
TOPIC = "transactions"


def load_model():
    logger.info(f"Loading model from {MODEL_PATH}")
    return joblib.load(MODEL_PATH)

def create_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
        group_id="fraud-scorer",
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


def main():
    pipeline = load_model()
    engine = create_engine(DATABASE_URL)
    consumer = create_consumer()

    logger.info(f"Listening to Kafka topic '{TOPIC}' for new transactions...")

    for message in consumer:
        txn = message.value
        try:
            result = score_transaction(pipeline, txn)

            pd.DataFrame([result]).to_sql(
                "predictions", engine, if_exists="append", index=False
            )
            if result["predicted_fraud"]:
                logger.warning(
                    f"FRAUD DETECTED id={result['transaction_id']} "
                    f"proba={result['fraud_probability']}"
                )
            else:
                logger.info(
                    f"OK id={result['transaction_id']} "
                    f"proba={result['fraud_probability']}"
                )
        except Exception as e:
            logger.error(f"Failed to score transaction id={txn.get('id')}: {e}")


if __name__ == "__main__":
    main()
