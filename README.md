# Converta — LLM Message Optimization Platform

Production-grade platform that uses LLMs to rewrite consumer-facing short-term loan application messages, optimizing for conversion rate improvement.

## Architecture

- **Message Generation** — LLM rewrite with versioned prompt registry and guardrails
- **Quality Classifier** — XGBoost classifier gating every generated message (< 10ms)
- **Evaluation Pipeline** — ROUGE, BERTScore, LLM-as-Judge async evaluation via Celery
- **A/B Engine** — Deterministic user assignment, z-test + Bayesian analysis
- **Feature Store** — Feast offline (S3/Parquet) + online (Redis) feature serving
- **Monitoring** — Prometheus + Grafana, PSI drift detection, PagerDuty alerting

## Quickstart

```bash
cp .env.example .env        # fill in API keys and DB credentials
make build
make migrate
make dev                    # starts all services via Docker Compose
```

API available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

## Key Commands

```bash
make test          # run full test suite
make lint          # ruff + mypy
make train         # train quality classifier
make golden-eval   # run regression golden dataset (must pass ≥ 95%)
make rollback MODEL=<version>   # roll back champion model
```

## Tech Stack

Python 3.11 · FastAPI · PostgreSQL · Redis · Celery · MLflow · Feast · scikit-learn · XGBoost · OpenAI API · Prometheus · Grafana · AWS (ECS/RDS/S3/ElastiCache)

## Repository Structure

```
api/                  FastAPI app (routers, dependencies)
services/
  generation/         LLM rewrite, prompt registry, guardrails
  evaluation/         ROUGE, BERTScore, LLM-as-judge, human eval queue
  classifier/         Quality classifier training + inference
  experiments/        A/B assignment, stats engine, lifecycle
  monitoring/         Drift detection, alerting, reports
features/
  feature_repo/       Feast feature definitions
  pipelines/          Batch feature computation
data/
  schemas/            SQLAlchemy ORM + Pydantic models
  golden_datasets/    Regression test data
training/             Classifier training + evaluation scripts
tests/                unit / integration / regression
infra/
  docker/             Dockerfile + Docker Compose
  terraform/          AWS infrastructure (ECS, RDS, S3, ElastiCache)
docs/runbooks/        Alert runbooks
.github/workflows/    CI/CD pipelines
```
