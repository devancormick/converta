from __future__ import annotations

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

try:
    from xgboost import XGBClassifier
    _XGB_AVAILABLE = True
except ImportError:
    _XGB_AVAILABLE = False

from services.classifier.features import build_feature_pipeline


def build_baseline_pipeline() -> Pipeline:
    features = build_feature_pipeline()
    clf = LogisticRegression(max_iter=1000, class_weight="balanced", C=1.0)
    return Pipeline([("features", features), ("classifier", clf)])


def build_production_pipeline() -> Pipeline:
    features = build_feature_pipeline()
    if _XGB_AVAILABLE:
        clf = XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42,
        )
    else:
        clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    return Pipeline([("features", features), ("classifier", clf)])
