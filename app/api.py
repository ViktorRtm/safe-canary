"""Stateless inference API with readiness, version attribution, and redacted JSON logs."""
import json
import logging
import math
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, generate_latest

from app.model import Model

MODEL_VERSION = os.getenv("MODEL_VERSION", "v1")
MODEL_FILE = os.getenv("MODEL_FILE", "models/v1.json")
APP_VERSION = "1.0.0"
logger = logging.getLogger("inference")
logging.basicConfig(level=logging.INFO, format="%(message)s")
REQUESTS = Counter("inference_requests_total", "Inference requests", ["model_version", "status"])
DURATION = Histogram("inference_duration_seconds", "Inference latency", ["model_version"])
state = {"model": None, "ready": False}


@asynccontextmanager
async def lifespan(app: FastAPI):
    model = Model(MODEL_FILE, MODEL_VERSION)
    model.predict(0.0, 0.0)  # startup warm-up + compatibility check
    state["model"] = model
    state["ready"] = True
    logger.info(json.dumps({"event": "startup_complete", "model_version": MODEL_VERSION, "app_version": APP_VERSION}))
    yield
    state["ready"] = False
    state["model"] = None


app = FastAPI(lifespan=lifespan)


class PredictionRequest(BaseModel):
    x1: float = Field(ge=-100, le=100)
    x2: float = Field(ge=-100, le=100)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if not state["ready"] or state["model"] is None:
        raise HTTPException(status_code=503, detail="Model not ready")
    return {"status": "ready", "model_version": MODEL_VERSION}


@app.get("/version")
def version():
    return {"model_version": MODEL_VERSION, "app_version": APP_VERSION}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict")
def predict(payload: PredictionRequest, request: Request):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    started = time.perf_counter()
    status = "ok"
    try:
        if state["model"] is None or not state["ready"]:
            status = "not_ready"
            raise HTTPException(status_code=503, detail="Model not ready")
        if not all(math.isfinite(x) for x in [payload.x1, payload.x2]):
            status = "invalid_input"
            raise HTTPException(status_code=422, detail="Non-finite input")
        pred, confidence = state["model"].predict(payload.x1, payload.x2)
        return {
            "prediction": pred,
            "probability": round(confidence, 6),
            "model_version": MODEL_VERSION,
            "request_id": request_id,
        }
    except HTTPException:
        raise
    except Exception:
        status = "error"
        logger.error(json.dumps({"event": "inference_error", "request_id": request_id, "model_version": MODEL_VERSION}))
        raise HTTPException(status_code=500, detail="Inference failed")
    finally:
        duration = time.perf_counter() - started
        REQUESTS.labels(model_version=MODEL_VERSION, status=status).inc()
        DURATION.labels(model_version=MODEL_VERSION).observe(duration)
        logger.info(json.dumps({
            "event": "request_complete", "request_id": request_id,
            "model_version": MODEL_VERSION, "status": status,
            "latency_ms": round(duration * 1000, 2),
        }))
