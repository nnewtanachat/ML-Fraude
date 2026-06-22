from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MODEL_PATH: str = "model/fraud_pipeline.pkl"
    API_KEY: str = "Default"
    FRAUD_THRESHOLD: float = 0.5
    APP_NAME: str = "Fraud Detection API"
    APP_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
