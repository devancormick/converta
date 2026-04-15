"""Prometheus metrics — instrument FastAPI app and expose /metrics."""
from __future__ import annotations

import time

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# System metrics
REQUEST_LATENCY = Histogram(
    "converta_request_latency_seconds",
    "HTTP request latency",
    ["method", "endpoint", "status"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
)
REQUEST_COUNT = Counter(
    "converta_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
ERROR_COUNT = Counter("converta_errors_total", "Total errors", ["type"])

# Model metrics
CLASSIFIER_PASS_RATE = Gauge("converta_classifier_pass_rate", "Classifier pass rate (rolling)")
LLM_JUDGE_SCORE = Histogram(
    "converta_llm_judge_score",
    "LLM-as-Judge score distribution",
    buckets=[1.0, 2.0, 3.0, 4.0, 5.0],
)
TOKEN_USAGE = Counter("converta_llm_tokens_total", "LLM token usage", ["model", "type"])

# Experiment metrics
EXPERIMENT_ASSIGNMENTS = Counter(
    "converta_experiment_assignments_total",
    "Total experiment assignments",
    ["experiment_id", "variant_id"],
)

# Drift metrics
DRIFT_PSI = Gauge("converta_drift_psi", "Population Stability Index", ["feature"])


def instrument_app(app: FastAPI) -> None:
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        latency = time.monotonic() - start
        path = request.url.path
        status = str(response.status_code)
        REQUEST_LATENCY.labels(request.method, path, status).observe(latency)
        REQUEST_COUNT.labels(request.method, path, status).inc()
        return response

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
