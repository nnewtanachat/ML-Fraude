from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler,FunctionTransformer
import numpy as np
import pandas as pd

CONTINUOUS_COLS = [
    "transaction_amount",
    "customer_age",
    "distance_from_home",
    "network_quality",
    "prev_transactions",
    "velocity_score",
]

CATEGORICAL_COLS = [
    "hour_of_day",
    "device_type",
    "num_items",
    "store_type",
    "is_weekend",
    "is_first_transaction",
]

FEATURE_COLS = CONTINUOUS_COLS + CATEGORICAL_COLS

TARGET_COL = "is_fraud"

def add_features(X):
    """เพิ่ม feature ใหม่ — รับ numpy array หรือ DataFrame"""
    if isinstance(X, np.ndarray):
        df = pd.DataFrame(X, columns=FEATURE_COLS)
    else:
        df = X.copy()

    df["amount_per_item"] = df["transaction_amount"] / (df["num_items"] + 1)
    df["high_amount"] = (df["transaction_amount"] > 200).astype(int)
    df["distance_velocity_ratio"] = df["distance_from_home"] / (df["velocity_score"] + 1)
    df["is_young"] = (df["customer_age"] < 25).astype(int)
    return df.values

def build_preprocessor() -> ColumnTransformer:
    continuous_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
    ])

    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
    ])

    return ColumnTransformer([
        ("continuous", continuous_pipeline, CONTINUOUS_COLS),
        ("categorical", categorical_pipeline, CATEGORICAL_COLS),
    ])


