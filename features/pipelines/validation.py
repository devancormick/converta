"""Great Expectations feature validation suite."""
from __future__ import annotations

import pandas as pd


CRITICAL_EXPECTATIONS: dict[str, list[dict]] = {
    "behavioral": [
        {"column": "time_on_page_seconds", "max_null_pct": 0.10},
        {"column": "click_count", "max_null_pct": 0.10},
    ],
    "text": [
        {"column": "message_length", "max_null_pct": 0.05},
        {"column": "sentiment_score", "max_null_pct": 0.05},
    ],
    "contextual": [],
    "historical": [
        {"column": "past_application_count", "max_null_pct": 0.05},
    ],
}


class FeatureValidationError(Exception):
    pass


def validate_features(df: pd.DataFrame, feature_group: str) -> None:
    expectations = CRITICAL_EXPECTATIONS.get(feature_group, [])
    failures = []
    for exp in expectations:
        col = exp["column"]
        max_null = exp["max_null_pct"]
        if col not in df.columns:
            continue
        null_pct = df[col].isna().mean()
        if null_pct > max_null:
            failures.append(
                f"Column '{col}' null rate {null_pct:.1%} exceeds max {max_null:.1%}"
            )
    if failures:
        raise FeatureValidationError(
            f"Feature validation failed for '{feature_group}':\n" + "\n".join(failures)
        )
