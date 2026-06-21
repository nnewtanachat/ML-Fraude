import logging
from contextlib import asynccontextmanager
import joblib
import pandas as pd
from fastapi import FastAPI, Depends
from .config import Settings, get_settings
from .schemas import Transaction, PredictionResponse
from .security import verify_api_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"loading model from path : {settings.MODEL_PATH}")
    ml_models["pipeline"] = joblib.load(settings.MODEL_PATH)
    logger.info("Loaded Model")
    yield
    ml_models.clear()

settings = get_settings()
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok", "version": settings.APP_VERSION}

@app.post("/predict", response_model=PredictionResponse)
def predict(txn: Transaction,settings: Settings = Depends(get_settings),api_key: str = Depends(verify_api_key),):

    df = pd.DataFrame([txn.model_dump()])

    proba = float(ml_models["pipeline"].predict_proba(df)[0, 1])

    is_fraud = proba >= settings.FRAUD_THRESHOLD

    logger.info(f"Prediction: proba={proba:.4f}, is_fraud={is_fraud}")

    return PredictionResponse(
        fraud_probability=round(proba, 4),
        is_fraud=is_fraud,
        threshold=settings.FRAUD_THRESHOLD,
    )
