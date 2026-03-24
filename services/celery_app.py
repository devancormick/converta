from celery import Celery
from celery.schedules import crontab

from data.schemas.config import Settings

settings = Settings()

app = Celery(
    "converta",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "services.evaluation.pipeline",
        "services.experiments.analysis",
        "services.monitoring.drift",
        "services.monitoring.reports",
        "features.pipelines.batch_features",
        "training.train_classifier",
    ],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

app.conf.beat_schedule = {
    "nightly-experiment-analysis": {
        "task": "services.experiments.analysis.run_nightly_analysis",
        "schedule": crontab(hour=2, minute=0),
    },
    "weekly-drift-check": {
        "task": "services.monitoring.drift.run_drift_check",
        "schedule": crontab(day_of_week=1, hour=3, minute=0),
    },
    "nightly-feature-batch": {
        "task": "features.pipelines.batch_features.run_batch_pipeline",
        "schedule": crontab(hour=1, minute=0),
    },
    "monthly-report": {
        "task": "services.monitoring.reports.generate_monthly_report",
        "schedule": crontab(day_of_month=1, hour=4, minute=0),
    },
    "weekly-retrain": {
        "task": "training.train_classifier.retrain_task",
        "schedule": crontab(day_of_week=0, hour=5, minute=0),
    },
}
