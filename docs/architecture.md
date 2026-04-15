# Converta — Architecture Overview

## System Design

Converta is a cloud-native platform that rewrites consumer-facing loan messages using LLMs, with full ML pipeline support: quality gating, A/B experimentation, feature engineering, and production monitoring.

## Request Flow

```
Client
  │
  ▼
POST /v1/messages/rewrite
  │
  ├─► Pre-guardrails (PII scrub, blocklist check)
  │
  ├─► Prompt Registry (load versioned YAML template)
  │
  ├─► LLM Rewriter (OpenAI/Bedrock, retry/backoff)
  │
  ├─► Quality Classifier (XGBoost, < 10ms, in-memory)
  │
  ├─► Post-guardrails (compliance regex check)
  │
  ├─► DB write (messages table) + S3 JSONL log
  │
  └─► Celery async eval task (ROUGE, BERTScore, LLM-as-Judge)
```

## Key Design Decisions

- **Sync quality gate**: classifier runs synchronously in the request path (< 10ms) to block bad messages before they're stored
- **Async full eval**: ROUGE, BERTScore, perplexity, and LLM-as-Judge run asynchronously via Celery — too slow for p95 SLA
- **Deterministic A/B assignment**: HMAC-SHA256 hash ensures the same user always gets the same variant, even across restarts
- **Immutable prompt versions**: prompt templates are versioned with semver; deployed versions are never mutated — only deprecated
- **Champion/challenger model**: new classifiers run in shadow mode before promotion; rollback is a single MLflow tag update

## Data Flow

```
Raw Events (S3) ──► Feast Offline Store (Parquet/S3)
                         │
                         ▼
                   Feast Online Store (Redis)
                         │
                         ▼
              Inference time feature retrieval
```

## Monitoring Architecture

- All services expose Prometheus metrics at `/metrics`
- Prometheus scrapes every 15s
- Grafana reads from Prometheus for dashboards
- Weekly Celery beat job computes PSI drift; alerts via Slack/PagerDuty
- Monthly report generated as HTML + PDF, stored in S3
