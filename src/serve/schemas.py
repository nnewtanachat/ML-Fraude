from pydantic import BaseModel, Field

class Transaction(BaseModel):
    transaction_amount: float = Field(..., ge=0)
    hour_of_day: float = Field(..., ge=0, le=23)
    is_weekend: float = Field(..., ge=0, le=1)
    num_items: float = Field(..., ge=0)
    customer_age: float = Field(..., ge=0, le=120)
    prev_transactions: float = Field(..., ge=0)
    distance_from_home: float = Field(..., ge=0)
    device_type: float
    network_quality: float = Field(..., ge=0, le=100)
    is_first_transaction: float = Field(..., ge=0, le=1)
    store_type: float
    velocity_score: float

class PredictionResponse(BaseModel):
    fraud_probability: float
    is_fraud: bool
    threshold: float
