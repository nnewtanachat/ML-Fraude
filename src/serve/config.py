from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Model loading — supports 2 modes:
    # Mode 1 (file): MODEL_PATH="model/fraud_pipeline.pkl"
    # Mode 2 (MLflow): MODEL_PATH="models:/fraud_detector/Production"
    MODEL_PATH: str = "model/fraud_pipeline.pkl"
    MLFLOW_TRACKING_URI: str = "http://mlflow.fraud-detection.svc:5000"

    API_KEY: str  # Required — ต้องตั้งค่าใน .env หรือ environment variable
    FRAUD_THRESHOLD: float = 0.5
    APP_NAME: str = "Fraud Detection API"
    APP_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
