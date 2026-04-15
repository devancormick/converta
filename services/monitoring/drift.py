"""PSI drift detection and KL-divergence on classifier output distribution."""
from __future__ import annotations

import numpy as np

from services.celery_app import app as celery_app
from services.monitoring.metrics import DRIFT_PSI

PSI_WARN_THRESHOLD = 0.20
PSI_CRITICAL_THRESHOLD = 0.25
N_BINS = 10


def compute_psi(expected: np.ndarray, actual: np.ndarray, n_bins: int = N_BINS) -> float:
    """Population Stability Index between two distributions."""
    bins = np.linspace(
        min(expected.min(), actual.min()),
        max(expected.max(), actual.max()) + 1e-10,
        n_bins + 1,
    )
    exp_counts, _ = np.histogram(expected, bins=bins)
    act_counts, _ = np.histogram(actual, bins=bins)

    exp_pct = np.maximum(exp_counts / len(expected), 1e-6)
    act_pct = np.maximum(act_counts / len(actual), 1e-6)

    psi = float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))
    return psi


def compute_kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """KL divergence D(P||Q)."""
    p = np.maximum(p, 1e-10)
    q = np.maximum(q, 1e-10)
    p = p / p.sum()
    q = q / q.sum()
    return float(np.sum(p * np.log(p / q)))


async def _get_feature_distributions() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Load reference vs current distributions from DB."""
    from api.dependencies import AsyncSessionLocal
    from sqlalchemy import func, select
    from data.schemas.models import EvalResult

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(EvalResult.classifier_score).where(EvalResult.classifier_score.isnot(None)).limit(10000)
        )
        scores = np.array([r[0] for r in result.all()], dtype=float)

    if len(scores) < 20:
        return {}

    mid = len(scores) // 2
    return {"classifier_score": (scores[:mid], scores[mid:])}


@celery_app.task(name="services.monitoring.drift.run_drift_check")
def run_drift_check():
    import asyncio
    asyncio.get_event_loop().run_until_complete(_check())


async def _check():
    from services.monitoring.alerts import send_slack_alert

    distributions = await _get_feature_distributions()
    for feature, (reference, current) in distributions.items():
        psi = compute_psi(reference, current)
        DRIFT_PSI.labels(feature=feature).set(psi)

        if psi > PSI_CRITICAL_THRESHOLD:
            await send_slack_alert(
                f":rotating_light: DRIFT CRITICAL: feature `{feature}` PSI={psi:.3f} > {PSI_CRITICAL_THRESHOLD}"
                f" — rollback candidate flagged."
            )
        elif psi > PSI_WARN_THRESHOLD:
            await send_slack_alert(
                f":warning: DRIFT WARNING: feature `{feature}` PSI={psi:.3f} > {PSI_WARN_THRESHOLD}"
                f" — investigate."
            )
