import pytest
from pydantic import ValidationError

from src.serve.schemas import Transaction


# ข้อมูลถูกต้อง ไว้ใช้เป็นฐาน
VALID_DATA = {
    "transaction_amount": 150.0,
    "hour_of_day": 2.0,
    "is_weekend": 0.0,
    "num_items": 3.0,
    "customer_age": 35.0,
    "prev_transactions": 5.0,
    "distance_from_home": 20.0,
    "device_type": 1.0,
    "network_quality": 75.0,
    "is_first_transaction": 0.0,
    "store_type": 0.0,
    "velocity_score": 5.0,
}


def test_valid_transaction():
    """ข้อมูลถูกต้อง → สร้างได้"""
    txn = Transaction(**VALID_DATA)
    assert txn.transaction_amount == 150.0


def test_negative_amount_rejected():
    """amount ติดลบ → ต้อง error (ge=0)"""
    data = VALID_DATA.copy()
    data["transaction_amount"] = -10.0
    with pytest.raises(ValidationError):
        Transaction(**data)


def test_hour_out_of_range_rejected():
    """hour_of_day=25 เกิน le=23 → ต้อง error"""
    data = VALID_DATA.copy()
    data["hour_of_day"] = 25.0
    with pytest.raises(ValidationError):
        Transaction(**data)


def test_age_over_limit_rejected():
    """อายุเกิน 120 → ต้อง error"""
    data = VALID_DATA.copy()
    data["customer_age"] = 200.0
    with pytest.raises(ValidationError):
        Transaction(**data)


def test_missing_field_rejected():
    """ขาด field บังคับ → ต้อง error"""
    data = VALID_DATA.copy()
    del data["transaction_amount"]
    with pytest.raises(ValidationError):
        Transaction(**data)
