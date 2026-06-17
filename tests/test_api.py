import pytest
from fastapi.testclient import TestClient

from src.serve.main import app
from src.serve.config import get_settings

@pytest.fixture
def client():
    # with ครอบ → trigger lifespan → โหลด model
    with TestClient(app) as c:
        yield c


VALID_PAYLOAD = {
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


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predict_without_api_key(client):
    """ไม่แนบ key → 401"""
    response = client.post("/predict", json=VALID_PAYLOAD)
    assert response.status_code == 401


def test_predict_with_valid_key(client):
    """แนบ key ถูก → 200 + มี fraud_probability"""
    api_key = get_settings().API_KEY
    response = client.post(
        "/predict",
        json=VALID_PAYLOAD,
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert "fraud_probability" in body
    assert "is_fraud" in body


def test_predict_invalid_input(client):
    """ส่งข้อมูลผิด (hour=25) + key ถูก → 422"""
    api_key = get_settings().API_KEY
    data = VALID_PAYLOAD.copy()
    data["hour_of_day"] = 25.0
    response = client.post(
        "/predict",
        json=data,
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 422
