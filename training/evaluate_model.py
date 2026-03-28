from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    classification_report,
    precision_recall_fscore_support,
    roc_auc_score,
)

COMPLIANCE_RISK_LABEL = "compliance_risk"
MIN_PRECISION_COMPLIANCE = 0.90
MIN_AUC = 0.0


def evaluate(model, X_test, y_test, label_names: list[str] | None = None):
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else None

    auc = float(roc_auc_score(y_test, y_proba)) if y_proba is not None else 0.0
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="binary")

    report = classification_report(y_test, y_pred, target_names=label_names or ["fail", "pass"])

    return {
        "auc": auc,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "report": report,
    }


def beats_champion(challenger_metrics: dict, champion_metrics: dict | None) -> bool:
    if champion_metrics is None:
        return True
    challenger_auc = challenger_metrics.get("auc", 0.0)
    champion_auc = champion_metrics.get("auc", 0.0)
    challenger_precision = challenger_metrics.get("precision", 0.0)
    return (
        challenger_auc >= champion_auc
        and challenger_precision >= MIN_PRECISION_COMPLIANCE
    )
