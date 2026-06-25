import logging
import time
from contextlib import asynccontextmanager

import joblib
import pandas as pd
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from .config import Settings, get_settings
from .logging_config import setup_logging
from .schemas import Transaction, PredictionResponse
from .security import verify_api_key

# Initialize structured JSON logging
_settings = get_settings()
setup_logging(level=_settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# ===== Prometheus Metrics =====
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)
PREDICTION_COUNT = Counter(
    "predictions_total",
    "Total predictions made",
    ["is_fraud"],
)
PREDICTION_PROBABILITY = Histogram(
    "prediction_probability",
    "Distribution of fraud probability scores",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)
MODEL_LOADED = Gauge(
    "model_loaded",
    "Whether the ML model is loaded (1) or not (0)",
)

ml_models: dict = {}


def load_model(settings: Settings):
    """Load model from MLflow Registry or local file.

    Supports 2 modes:
    - MLflow: MODEL_PATH="models:/fraud_detector/Production"
    - File:   MODEL_PATH="model/fraud_pipeline.pkl"
    """
    model_path = settings.MODEL_PATH

    if model_path.startswith("models:/"):
        # ===== Mode: MLflow Model Registry (Production) =====
        import mlflow

        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        logger.info(
            "Loading model from MLflow Registry: %s (tracking: %s)",
            model_path, settings.MLFLOW_TRACKING_URI,
        )
        return mlflow.sklearn.load_model(model_path)

    else:
        # ===== Mode: Local file (dev / fallback) =====
        logger.info("Loading model from file: %s", model_path)
        return joblib.load(model_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    try:
        ml_models["pipeline"] = load_model(settings)
        MODEL_LOADED.set(1)
        logger.info("Model loaded successfully")
    except Exception as e:
        MODEL_LOADED.set(0)
        logger.error("Failed to load model: %s", str(e))
        raise
    yield
    ml_models.clear()
    MODEL_LOADED.set(0)


settings = get_settings()
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)


# ===== Middleware: Request metrics =====
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start_time

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(duration)

    return response


# ===== Endpoints =====
@app.get("/health")
def health():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post("/predict", response_model=PredictionResponse)
def predict(
    txn: Transaction,
    settings: Settings = Depends(get_settings),
    api_key: str = Depends(verify_api_key),
):
    df = pd.DataFrame([txn.model_dump()])

    proba = float(ml_models["pipeline"].predict_proba(df)[0, 1])
    is_fraud = proba >= settings.FRAUD_THRESHOLD

    # Record metrics
    PREDICTION_COUNT.labels(is_fraud=str(is_fraud)).inc()
    PREDICTION_PROBABILITY.observe(proba)

    logger.info(
        "Prediction completed: proba=%.4f, is_fraud=%s, threshold=%.2f",
        proba,
        is_fraud,
        settings.FRAUD_THRESHOLD,
    )

    return PredictionResponse(
        fraud_probability=round(proba, 4),
        is_fraud=is_fraud,
        threshold=settings.FRAUD_THRESHOLD,
    )
