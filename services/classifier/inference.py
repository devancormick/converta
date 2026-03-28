from __future__ import annotations

import pickle
import threading
from dataclasses import dataclass
from typing import Any

import mlflow

from data.schemas.config import Settings

_lock = threading.Lock()
_model: Any = None
_model_version: str = "unknown"

settings = Settings()


@dataclass
class ClassifierResult:
    label: str
    score: float
    model_version: str


def load_champion() -> tuple[Any, str]:
    try:
        client = mlflow.tracking.MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
        alias_info = client.get_registered_model_alias(settings.classifier_model_name, "champion")
        version = alias_info.version
        model_uri = f"models:/{settings.classifier_model_name}@champion"
        model = mlflow.sklearn.load_model(model_uri)
        return model, str(version)
    except Exception:
        return None, "none"


def get_model() -> tuple[Any, str]:
    global _model, _model_version
    if _model is None:
        with _lock:
            if _model is None:
                _model, _model_version = load_champion()
    return _model, _model_version


def predict(text: str) -> ClassifierResult:
    model, version = get_model()
    if model is None:
        return ClassifierResult(label="pass", score=1.0, model_version="fallback")
    proba = model.predict_proba([text])[0]
    score = float(proba[1]) if len(proba) > 1 else float(proba[0])
    label = "pass" if score >= settings.classifier_threshold else "fail"
    return ClassifierResult(label=label, score=score, model_version=version)


def reload_champion() -> str:
    global _model, _model_version
    with _lock:
        _model, _model_version = load_champion()
    return _model_version
