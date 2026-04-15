"""Slack and PagerDuty alerting."""
from __future__ import annotations

import httpx

from data.schemas.config import Settings

settings = Settings()


async def send_slack_alert(message: str) -> None:
    if not settings.slack_webhook_url:
        print(f"[SLACK ALERT] {message}")
        return
    async with httpx.AsyncClient() as client:
        try:
            await client.post(settings.slack_webhook_url, json={"text": message}, timeout=5.0)
        except Exception as e:
            print(f"Slack alert failed: {e}")


async def send_pagerduty_alert(summary: str, severity: str = "critical", source: str = "converta") -> None:
    if not settings.pagerduty_api_key:
        print(f"[PAGERDUTY ALERT] [{severity}] {summary}")
        return
    payload = {
        "routing_key": settings.pagerduty_api_key,
        "event_action": "trigger",
        "payload": {
            "summary": summary,
            "severity": severity,
            "source": source,
        },
    }
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
                timeout=5.0,
            )
        except Exception as e:
            print(f"PagerDuty alert failed: {e}")


async def check_guardrail_breach(experiment_id: int, metric: str, value: float, threshold: float):
    """Auto-pause experiment and page on guardrail breach."""
    if value > threshold:
        from api.dependencies import AsyncSessionLocal
        from sqlalchemy import select
        from data.schemas.models import Experiment
        from datetime import datetime, timezone

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
            exp = result.scalars().first()
            if exp and exp.status == "RUNNING":
                exp.status = "PAUSED"
                exp.audit_log = (exp.audit_log or []) + [{
                    "action": "auto-paused",
                    "reason": f"guardrail breach: {metric}={value:.4f} > threshold {threshold}",
                    "at": datetime.now(timezone.utc).isoformat(),
                }]
                await db.commit()

        await send_pagerduty_alert(
            f"Experiment {experiment_id} auto-paused: guardrail breach {metric}={value:.4f} (threshold={threshold})",
            severity="critical",
        )
        await send_slack_alert(
            f":rotating_light: Experiment `{experiment_id}` auto-paused — "
            f"guardrail breach: `{metric}={value:.4f}` exceeds `{threshold}`"
        )
