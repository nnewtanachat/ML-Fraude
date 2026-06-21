import os
import logging
from datetime import datetime

import joblib
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from src.preprocess import FEATURE_COLS

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
MODEL_PATH = os.getenv("MODEL_PATH")
THRESHOLD = float(os.getenv("FRAUD_THRESHOLD"))
MODEL_VERSION = "xgboost_baseline_v1"


def get_new_data(engine) -> pd.DataFrame:
    query = """
        SELECT * FROM transactions
        WHERE id NOT IN (SELECT transaction_id FROM predictions)
    """
    try:
        return pd.read_sql(query, engine)
    except Exception:
        return pd.read_sql("SELECT * FROM transactions", engine)


def predict_batch(pipeline, df: pd.DataFrame) -> pd.DataFrame:
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


def save_results(results: pd.DataFrame, engine):
    """บันทึกผลลง predictions table"""
    results.to_sql("predictions", engine, if_exists="append", index=False)


def main():
    engine = create_engine(DATABASE_URL)

    # 1. โหลด model
    pipeline = joblib.load(MODEL_PATH)
    logger.info(f"Model loaded: {MODEL_VERSION}")

    # 2. ดึงข้อมูลใหม่
    df = get_new_data(engine)
    if df.empty:
        logger.info("No new data to predict")
        return
    logger.info(f"New data: {len(df)} rows")

    # 3. Predict
    results = predict_batch(pipeline, df)

    # 4. บันทึก
    save_results(results, engine)

    # 5. Log สรุป
    n_fraud = results["predicted_fraud"].sum()
    logger.info(f"Results: {n_fraud} fraud / {len(results)} total ({n_fraud/len(results)*100:.1f}%)")
    logger.info("Saved to predictions table")


if __name__ == "__main__":
    main()
