# Runbook: p95 Latency > 3s

**Alert:** API p95 latency exceeded 3 seconds  
**Severity:** Slack alert

## Investigation Steps

1. Check Grafana → System Health → p95 latency panel for trend
2. Check if LLM provider (OpenAI/Bedrock) is experiencing degraded performance
3. Check Celery worker queue depth — is the evaluation pipeline backed up?
4. Check PostgreSQL slow queries via CloudWatch RDS metrics
5. Check Redis latency — assignment endpoint depends on Redis cache

## Remediation

- LLM provider slow: check provider status page; consider switching to fallback model
- DB slow: check for missing indexes; check connection pool exhaustion
- Redis slow: check memory usage; restart Redis if needed
- Scale up ECS tasks if throughput is near capacity

## Prevention

- Ensure LLM calls have a 5s timeout configured
- Redis cache for experiment assignments reduces DB load significantly
