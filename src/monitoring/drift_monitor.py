"""Model Drift Monitor — ตรวจ data drift + prediction drift ทุกวัน."""

import os
import json
import logging
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset
from evidently.metrics import (
    DatasetDriftMetric,
    DataDriftTable,
    ColumnDriftMetric,
)

from src.pipeline.preprocess import FEATURE_COLS

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
DRIFT_THRESHOLD = float(os.getenv("DRIFT_THRESHOLD", "0.3"))
PREDICTION_DRIFT_THRESHOLD = float(os.getenv("PREDICTION_DRIFT_THRESHOLD", "0.1"))
LOOKBACK_DAYS = int(os.getenv("DRIFT_LOOKBACK_DAYS", "7"))


def get_reference_data(engine) -> pd.DataFrame:
    """ดึง data ที่ใช้ train model (เป็น baseline)."""
    query = """
        SELECT * FROM transactions
        ORDER BY id ASC
        LIMIT 5000
    """
    return pd.read_sql(query, engine)


def get_current_data(engine, days: int = 7) -> pd.DataFrame:
    """ดึง data ล่าสุด (production)."""
    query = f"""
        SELECT t.*, p.fraud_probability, p.predicted_fraud
        FROM transactions t
        LEFT JOIN predictions p ON t.id = p.transaction_id
        WHERE p.predicted_at >= NOW() - INTERVAL '{days} days'
        ORDER BY p.predicted_at DESC
        LIMIT 5000
    """
    return pd.read_sql(query, engine)


def check_data_drift(reference: pd.DataFrame, current: pd.DataFrame) -> dict:
    """ตรวจ data drift — feature distributions เปลี่ยนไปไหม."""
    report = Report(metrics=[
        DatasetDriftMetric(),
        DataDriftTable(),
    ])

    report.run(
        reference_data=reference[FEATURE_COLS],
        current_data=current[FEATURE_COLS],
    )

    result = report.as_dict()
    metrics = result["metrics"]

    # Extract drift results
    dataset_drift = metrics[0]["result"]
    drift_detected = dataset_drift["dataset_drift"]
    drift_share = dataset_drift["share_of_drifted_columns"]
    n_drifted = dataset_drift["number_of_drifted_columns"]

    return {
        "dataset_drift_detected": drift_detected,
        "drift_share": round(drift_share, 4),
        "n_drifted_columns": n_drifted,
        "n_total_columns": len(FEATURE_COLS),
    }


def check_prediction_drift(reference: pd.DataFrame, current: pd.DataFrame) -> dict:
    """ตรวจ prediction drift — model output เปลี่ยนไปไหม."""
    if "fraud_probability" not in current.columns:
        return {"prediction_drift_detected": False, "message": "No predictions yet"}

    ref_fraud_rate = reference["is_fraud"].mean()
    cur_fraud_rate = current["predicted_fraud"].mean() if "predicted_fraud" in current.columns else 0

    drift_diff = abs(cur_fraud_rate - ref_fraud_rate)
    drift_detected = drift_diff > PREDICTION_DRIFT_THRESHOLD

    return {
        "prediction_drift_detected": drift_detected,
        "reference_fraud_rate": round(ref_fraud_rate, 4),
        "current_fraud_rate": round(cur_fraud_rate, 4),
        "drift_diff": round(drift_diff, 4),
        "threshold": PREDICTION_DRIFT_THRESHOLD,
    }


def save_drift_report(data_drift: dict, prediction_drift: dict, engine) -> None:
    """บันทึก drift results ลง DB."""
    report = pd.DataFrame([{
        "check_date": datetime.now(),
        "data_drift_detected": data_drift["dataset_drift_detected"],
        "drift_share": data_drift["drift_share"],
        "n_drifted_columns": data_drift["n_drifted_columns"],
        "prediction_drift_detected": prediction_drift["prediction_drift_detected"],
        "reference_fraud_rate": prediction_drift.get("reference_fraud_rate", 0),
        "current_fraud_rate": prediction_drift.get("current_fraud_rate", 0),
    }])

    report.to_sql("drift_reports", engine, if_exists="append", index=False)


def main():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    # 1. ดึง data
    reference = get_reference_data(engine)
    current = get_current_data(engine, days=LOOKBACK_DAYS)

    if reference.empty:
        logger.warning("No reference data found — skipping drift check")
        return

    if current.empty:
        logger.warning("No current data found — skipping drift check")
        return

    logger.info(
        "Checking drift: reference=%d rows, current=%d rows, lookback=%d days",
        len(reference), len(current), LOOKBACK_DAYS,
    )

    # 2. ตรวจ data drift
    data_drift = check_data_drift(reference, current)
    logger.info("Data drift result: %s", json.dumps(data_drift))

    # 3. ตรวจ prediction drift
    prediction_drift = check_prediction_drift(reference, current)
    logger.info("Prediction drift result: %s", json.dumps(prediction_drift))

    # 4. บันทึก
    try:
        save_drift_report(data_drift, prediction_drift, engine)
        logger.info("Drift report saved to DB")
    except Exception as e:
        logger.warning("Could not save drift report to DB: %s", e)

    # 5. Alert ถ้า drift เกิน threshold
    if data_drift["dataset_drift_detected"]:
        logger.warning(
            "DATA DRIFT DETECTED! %.0f%% of features drifted (%d/%d)",
            data_drift["drift_share"] * 100,
            data_drift["n_drifted_columns"],
            data_drift["n_total_columns"],
        )

    if prediction_drift.get("prediction_drift_detected"):
        logger.warning(
            "PREDICTION DRIFT DETECTED! Fraud rate changed: %.2f%% → %.2f%% (diff=%.2f%%)",
            prediction_drift["reference_fraud_rate"] * 100,
            prediction_drift["current_fraud_rate"] * 100,
            prediction_drift["drift_diff"] * 100,
        )

    # 6. สรุป
    needs_retrain = data_drift["dataset_drift_detected"] or prediction_drift.get("prediction_drift_detected", False)
    if needs_retrain:
        logger.warning("RECOMMENDATION: Model should be retrained!")
    else:
        logger.info("No significant drift detected — model is healthy")

    return {
        "data_drift": data_drift,
        "prediction_drift": prediction_drift,
        "needs_retrain": needs_retrain,
    }


if __name__ == "__main__":
    main()
