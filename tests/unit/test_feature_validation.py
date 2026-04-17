import pandas as pd
import pytest
from features.pipelines.validation import FeatureValidationError, validate_features


def test_validation_passes_clean_data():
    df = pd.DataFrame({
        "applicant_id": ["a", "b"],
        "time_on_page_seconds": [30.0, 45.0],
        "click_count": [3, 5],
    })
    validate_features(df, "behavioral")


def test_validation_fails_high_null_rate():
    df = pd.DataFrame({
        "applicant_id": ["a", "b", "c", "d", "e"],
        "time_on_page_seconds": [None, None, None, None, 30.0],
        "click_count": [1, 2, 3, 4, 5],
    })
    with pytest.raises(FeatureValidationError):
        validate_features(df, "behavioral")


def test_validation_unknown_group_passes():
    df = pd.DataFrame({"x": [1, 2, 3]})
    validate_features(df, "unknown_group")
