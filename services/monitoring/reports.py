"""Monthly monitoring report generator (HTML + PDF)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Template

from services.celery_app import app as celery_app

REPORT_DIR = Path("reports")

REPORT_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <title>Converta Monthly Report — {{ month }}</title>
  <style>
    body { font-family: sans-serif; max-width: 900px; margin: auto; padding: 2rem; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
    th { background: #f5f5f5; }
    .good { color: green; } .warn { color: orange; } .bad { color: red; }
  </style>
</head>
<body>
  <h1>Converta Monthly Performance Report</h1>
  <p><strong>Period:</strong> {{ month }}</p>
  <p><strong>Generated:</strong> {{ generated_at }}</p>

  <h2>Message Generation</h2>
  <table>
    <tr><th>Metric</th><th>Value</th></tr>
    <tr><td>Total messages rewritten</td><td>{{ stats.total_messages }}</td></tr>
    <tr><td>Pass rate</td><td>{{ stats.pass_rate }}</td></tr>
    <tr><td>Avg quality score</td><td>{{ stats.avg_quality_score }}</td></tr>
    <tr><td>Avg latency (ms)</td><td>{{ stats.avg_latency_ms }}</td></tr>
  </table>

  <h2>Evaluation Metrics</h2>
  <table>
    <tr><th>Metric</th><th>Avg</th></tr>
    <tr><td>ROUGE-1</td><td>{{ stats.avg_rouge1 }}</td></tr>
    <tr><td>BERTScore F1</td><td>{{ stats.avg_bertscore }}</td></tr>
    <tr><td>LLM Judge Score</td><td>{{ stats.avg_judge_score }}</td></tr>
  </table>

  <h2>Drift Summary</h2>
  <p>PSI scores for key features: {{ stats.drift_summary }}</p>

  <h2>Active Experiments</h2>
  <p>{{ stats.active_experiments }} experiment(s) running this period.</p>
</body>
</html>"""


async def _collect_stats() -> dict:
    from api.dependencies import AsyncSessionLocal
    from sqlalchemy import func, select
    from data.schemas.models import EvalResult, Experiment, Message

    async with AsyncSessionLocal() as db:
        total = await db.scalar(select(func.count()).select_from(Message)) or 0
        pass_count = await db.scalar(
            select(func.count()).select_from(Message).where(Message.passed_gate.is_(True))
        ) or 0
        avg_quality = await db.scalar(select(func.avg(Message.quality_score))) or 0.0
        avg_latency = await db.scalar(select(func.avg(Message.latency_ms))) or 0.0
        avg_rouge1 = await db.scalar(select(func.avg(EvalResult.rouge1))) or 0.0
        avg_bert = await db.scalar(select(func.avg(EvalResult.bertscore_f1))) or 0.0
        avg_judge = await db.scalar(select(func.avg(EvalResult.llm_judge_score))) or 0.0
        active_exp = await db.scalar(
            select(func.count()).select_from(Experiment).where(Experiment.status == "RUNNING")
        ) or 0

    pass_rate = f"{(pass_count / max(total, 1)):.1%}"
    return {
        "total_messages": total,
        "pass_rate": pass_rate,
        "avg_quality_score": f"{avg_quality:.3f}",
        "avg_latency_ms": f"{avg_latency:.0f}",
        "avg_rouge1": f"{avg_rouge1:.3f}",
        "avg_bertscore": f"{avg_bert:.3f}",
        "avg_judge_score": f"{avg_judge:.2f}",
        "drift_summary": "See Grafana dashboard for PSI trends.",
        "active_experiments": active_exp,
    }


async def generate_report():
    import asyncio
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stats = await _collect_stats()
    now = datetime.now(timezone.utc)
    month = now.strftime("%B %Y")
    html = Template(REPORT_TEMPLATE).render(
        month=month,
        generated_at=now.isoformat(),
        stats=stats,
    )
    filename = REPORT_DIR / f"report_{now.strftime('%Y_%m')}.html"
    filename.write_text(html)

    try:
        import weasyprint
        pdf_path = filename.with_suffix(".pdf")
        weasyprint.HTML(string=html).write_pdf(str(pdf_path))
    except Exception:
        pass

    return str(filename)


@celery_app.task(name="services.monitoring.reports.generate_monthly_report")
def generate_monthly_report():
    import asyncio
    asyncio.get_event_loop().run_until_complete(generate_report())
