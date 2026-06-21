import os
import json
import logging

import pandas as pd
import numpy as np
import optuna
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from xgboost import XGBClassifier

from src.preprocess import build_preprocessor, add_features, FEATURE_COLS, TARGET_COL

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
RANDOM_STATE = 42
N_TRIALS = 50
PARAMS_PATH = "model/best_params.json"
TEST_SIZE = 0.2


def load_data():
    engine = create_engine(DATABASE_URL)
    df = pd.read_sql("SELECT * FROM transactions", engine)
    X = df[FEATURE_COLS].copy()
    X["is_weekend"] = X["is_weekend"].astype(float)
    X["is_first_transaction"] = X["is_first_transaction"].astype(float)
    y = df[TARGET_COL]
    return X, y


def main():
    X, y = load_data()
    logger.info(f"Data: {len(X)} rows, {len(FEATURE_COLS)} features")

    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    logger.info(f"Train+Val: {len(X_trainval)}, Test (held-out): {len(X_test)}")

    scale_pos_weight = (y_trainval == 0).sum() / (y_trainval == 1).sum()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma": trial.suggest_float("gamma", 0, 5),
            "reg_alpha": trial.suggest_float("reg_alpha", 0, 5),
            "reg_lambda": trial.suggest_float("reg_lambda", 0, 5),
            "scale_pos_weight": scale_pos_weight,
            "random_state": RANDOM_STATE,
            "eval_metric": "aucpr",
        }

        pipeline = Pipeline([
            ("preprocessor", build_preprocessor()),
            ("feature_eng", FunctionTransformer(add_features, validate=False)),
            ("model", XGBClassifier(**params)),
        ])

        scores = cross_val_score(
            pipeline, X_trainval, y_trainval, cv=cv, scoring="roc_auc", n_jobs=-1
        )
        return scores.mean()

    # Run tuning
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=True)

    # Save best params + metadata
    best_params = study.best_params
    best_params["scale_pos_weight"] = round(scale_pos_weight, 2)
    best_params["random_state"] = RANDOM_STATE
    best_params["eval_metric"] = "aucpr"

    output = {
        "params": best_params,
        "best_cv_roc_auc": round(study.best_value, 4),
        "n_trials": N_TRIALS,
        "test_size": TEST_SIZE,
        "random_state": RANDOM_STATE,
    }

    os.makedirs(os.path.dirname(PARAMS_PATH), exist_ok=True)
    with open(PARAMS_PATH, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(f"Best CV ROC-AUC: {study.best_value:.4f}")
    logger.info(f"Best params saved to {PARAMS_PATH}")
    logger.info(f"Params: {json.dumps(best_params, indent=2)}")


if __name__ == "__main__":
    main()
