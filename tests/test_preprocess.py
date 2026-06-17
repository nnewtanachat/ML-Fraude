import numpy as np
import pandas as pd
import pytest

from src.preprocess import (
    build_preprocessor,
    FEATURE_COLS,
    CONTINUOUS_COLS,
    CATEGORICAL_COLS,
)


# ===== Fixture: สร้างข้อมูลปลอมไว้ใช้ซ้ำหลาย test =====
@pytest.fixture
def sample_data():
    """ข้อมูลปลอม 5 แถว จงใจใส่ NaN เพื่อเทส imputer"""
    data = {
        "transaction_amount": [100.0, np.nan, 200.0, 150.0, 80.0],
        "customer_age": [25.0, 30.0, np.nan, 40.0, 35.0],
        "distance_from_home": [10.0, 20.0, 30.0, np.nan, 5.0],
        "network_quality": [50.0, 60.0, 70.0, 80.0, np.nan],
        "prev_transactions": [1.0, np.nan, 3.0, 4.0, 2.0],
        "velocity_score": [5.0, 4.0, np.nan, 6.0, 3.0],
        "hour_of_day": [2.0, 1.0, 3.0, np.nan, 2.0],
        "device_type": [1.0, 0.0, np.nan, 2.0, 1.0],
        "num_items": [3.0, 2.0, 4.0, 1.0, np.nan],
        "store_type": [0.0, 1.0, np.nan, 0.0, 1.0],
        "is_weekend": [0.0, 1.0, 0.0, np.nan, 1.0],
        "is_first_transaction": [0.0, np.nan, 1.0, 0.0, 0.0],
    }
    return pd.DataFrame(data)


# ===== Test 1: สร้าง preprocessor ได้ =====
def test_build_preprocessor_returns_object():
    preprocessor = build_preprocessor()
    assert preprocessor is not None


# ===== Test 2: ไม่มี NaN หลัง transform (สำคัญสุด) =====
def test_no_nan_after_transform(sample_data):
    preprocessor = build_preprocessor()
    result = preprocessor.fit_transform(sample_data)
    assert not np.isnan(result).any(), "ต้องไม่มี NaN หลัง impute"


# ===== Test 3: จำนวนแถวไม่เปลี่ยน =====
def test_row_count_unchanged(sample_data):
    preprocessor = build_preprocessor()
    result = preprocessor.fit_transform(sample_data)
    assert result.shape[0] == len(sample_data)


# ===== Test 4: จำนวน column ถูกต้อง =====
def test_column_count(sample_data):
    preprocessor = build_preprocessor()
    result = preprocessor.fit_transform(sample_data)
    assert result.shape[1] == len(FEATURE_COLS)


# ===== Test 5: continuous columns ถูก scale (mean ใกล้ 0) =====
def test_continuous_scaled(sample_data):
    preprocessor = build_preprocessor()
    result = preprocessor.fit_transform(sample_data)
    # 6 column แรกคือ continuous (ตามลำดับใน ColumnTransformer)
    continuous_part = result[:, :len(CONTINUOUS_COLS)]
    means = continuous_part.mean(axis=0)
    assert np.allclose(means, 0, atol=1e-6), "continuous ควร scale ให้ mean=0"
