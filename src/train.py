import os
import logging
import joblib
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    ConfusionMatrixDisplay,
)
from xgboost import XGBClassifier

import mlflow
import mlflow.sklearn

from src.preprocess import build_preprocessor, FEATURE_COLS, TARGET_COL

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:1234@localhost:5432/fraud_detection")
MODEL_PATH = os.getenv("MODEL_PATH", "model/fraud_pipeline.pkl")
MLFLOW_EXPERIMENT = "fraud_detection"
RANDOM_STATE = 42

PARAMS = {
    "n_estimators": 200,
    "max_depth": 5,
    "learning_rate": 0.1,
    "random_state": RANDOM_STATE,
    "eval_metric": "aucpr",
}

def load_data() -> pd.DataFrame:
    engine = create_engine(DATABASE_URL)
    df = pd.read_sql("SELECT * FROM transactions", engine)
    logger.info(f"Loaded {len(df)} rows from database")
    return df


def build_model(scale_pos_weight: float) -> Pipeline:
    return Pipeline([
        ("preprocessor", build_preprocessor()),
        ("model", XGBClassifier(scale_pos_weight=scale_pos_weight, **PARAMS)),
    ])


def evaluate(pipeline: Pipeline, X_test, y_test) -> dict:
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    metrics = {
        "roc_auc": roc_auc_score(y_test, y_proba),
        "pr_auc": average_precision_score(y_test, y_proba),
        "f1": f1_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred),
    }

    logger.info("\n" + classification_report(y_test, y_pred))
    logger.info(f"Confusion matrix:\n{confusion_matrix(y_test, y_pred)}")
    ConfusionMatrixDisplay.from_predictions(y_test, y_pred)
    plt.savefig("confusion_matrix.png")
    plt.close()
    mlflow.log_artifact("confusion_matrix.png")
    for name, value in metrics.items():
        logger.info(f"{name}: {value:.4f}")

    return metrics


def main():
    df = load_data()
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")

    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    logger.info(f"scale_pos_weight: {scale_pos_weight:.2f}")

    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    with mlflow.start_run(run_name = "xgboost_baseline"):
        mlflow.set_tags({"model_type": "xgboost", "dataset": "fraud_v1"})
        mlflow.log_params(PARAMS)
        mlflow.log_param("scale_pos_weight", round(scale_pos_weight, 2))
        mlflow.log_param("n_features", len(FEATURE_COLS))

        pipeline = build_model(scale_pos_weight)
        pipeline.fit(X_train, y_train)

        metrics = evaluate(pipeline, X_test, y_test)

        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(pipeline, "model",registered_model_name="fraud_detector",)

        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(pipeline, MODEL_PATH)
        logger.info(f"Saved model to {MODEL_PATH}")

if __name__ == "__main__":
    main()
