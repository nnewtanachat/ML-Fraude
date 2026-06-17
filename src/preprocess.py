from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

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

def build_preprocessor() -> ColumnTransformer:
    continuous_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
    ])

    return ColumnTransformer([
        ("continuous", continuous_pipeline, CONTINUOUS_COLS),
        ("categorical", categorical_pipeline, CATEGORICAL_COLS),
    ])
