"""Nightly batch feature computation pipeline."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from services.celery_app import app as celery_app

FEATURE_OUTPUT_DIR = Path("data/features")


def compute_behavioral_features(events_df: pd.DataFrame) -> pd.DataFrame:
    return (
        events_df.groupby("applicant_id")
        .agg(
            time_on_page_seconds=("time_on_page", "mean"),
            click_count=("clicks", "sum"),
            return_visits=("session_id", pd.Series.nunique),
            session_count=("session_id", "count"),
        )
        .reset_index()
        .rename(columns={"applicant_id": "applicant_id"})
    )


def compute_text_features(messages_df: pd.DataFrame) -> pd.DataFrame:
    try:
        import textstat
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        vader = SentimentIntensityAnalyzer()
    except ImportError:
        textstat = None
        vader = None

    rows = []
    for _, row in messages_df.iterrows():
        text = str(row.get("rewritten_text") or row.get("raw_text", ""))
        rows.append({
            "applicant_id": row["applicant_id"],
            "message_length": len(text.split()),
            "readability_score": textstat.flesch_kincaid_grade(text) if textstat else 0.0,
            "sentiment_score": vader.polarity_scores(text)["compound"] if vader else 0.0,
            "urgency_keyword_count": sum(1 for kw in ["urgent", "act now", "expires", "limited"] if kw in text.lower()),
            "embedding_dim0": 0.0,
            "event_timestamp": row.get("created_at", datetime.now(timezone.utc)),
        })
    return pd.DataFrame(rows)


def compute_historical_features(applications_df: pd.DataFrame) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    return (
        applications_df.groupby("applicant_id")
        .agg(
            past_application_count=("id", "count"),
            prior_engagement_rate=("converted", "mean"),
            loan_segment=("loan_segment", "last"),
        )
        .reset_index()
        .assign(
            days_since_last_application=lambda df: (
                now - pd.to_datetime(applications_df.groupby("applicant_id")["created_at"].max())
            ).dt.days,
            event_timestamp=now,
        )
    )


def run_pipeline():
    FEATURE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for subdir in ["behavioral", "text", "contextual", "historical"]:
        (FEATURE_OUTPUT_DIR / subdir).mkdir(parents=True, exist_ok=True)

    # In production these DataFrames are loaded from S3/RDS
    empty_behavioral = pd.DataFrame(columns=[
        "applicant_id", "event_timestamp", "time_on_page_seconds",
        "click_count", "return_visits", "session_count", "device_type",
    ])
    empty_text = pd.DataFrame(columns=[
        "applicant_id", "event_timestamp", "message_length", "readability_score",
        "sentiment_score", "urgency_keyword_count", "embedding_dim0",
    ])

    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    empty_behavioral.to_parquet(FEATURE_OUTPUT_DIR / "behavioral" / f"{ts}.parquet", index=False)
    empty_text.to_parquet(FEATURE_OUTPUT_DIR / "text" / f"{ts}.parquet", index=False)

    from features.pipelines.validation import validate_features
    validate_features(empty_behavioral, "behavioral")
    validate_features(empty_text, "text")


@celery_app.task(name="features.pipelines.batch_features.run_batch_pipeline")
def run_batch_pipeline():
    run_pipeline()
