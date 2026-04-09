"""Experiment result computation and nightly Celery analysis job."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from data.schemas.models import Experiment, ExperimentEvent
from data.schemas.pydantic_models import ExperimentResults, ExperimentResultVariant
from services.celery_app import app as celery_app
from services.experiments.stats import (
    bayesian_beta_binomial,
    holm_bonferroni_correction,
    two_proportion_z_test,
)


async def compute_results(exp: Experiment, db: AsyncSession) -> ExperimentResults:
    variants = exp.variants if isinstance(exp.variants, list) else []
    variant_ids = [v["id"] for v in variants]

    result = await db.execute(
        select(
            ExperimentEvent.variant_id,
            func.count().label("total"),
            func.sum(func.cast(ExperimentEvent.converted, type_=func.Integer())).label("conversions"),
        )
        .where(ExperimentEvent.experiment_id == exp.id)
        .group_by(ExperimentEvent.variant_id)
    )
    rows = {r.variant_id: r for r in result.all()}

    variant_stats = []
    for vid in variant_ids:
        row = rows.get(vid)
        total = int(row.total) if row else 0
        conversions = int(row.conversions or 0) if row else 0
        rate = conversions / max(total, 1)
        variant_stats.append({"id": vid, "total": total, "conversions": conversions, "rate": rate})

    # Frequentist z-test (control vs each treatment; Holm-Bonferroni correction)
    control = variant_stats[0]
    treatments = variant_stats[1:]

    p_values = []
    freq_results = []
    for t in treatments:
        fr = two_proportion_z_test(
            control["conversions"], control["total"],
            t["conversions"], t["total"],
        )
        p_values.append(fr.p_value)
        freq_results.append(fr)

    adjusted_p = holm_bonferroni_correction(p_values) if p_values else []
    any_significant = any(p < 0.05 for p in adjusted_p)
    best_p = min(adjusted_p) if adjusted_p else 1.0

    # Bayesian (first pair)
    bayes_prob = None
    if treatments:
        br = bayesian_beta_binomial(
            control["conversions"], control["total"],
            treatments[0]["conversions"], treatments[0]["total"],
        )
        bayes_prob = br.probability_treatment_better

    # Recommendation
    if not freq_results:
        recommendation = "Insufficient data — no treatment variants."
    elif any_significant:
        best_idx = adjusted_p.index(min(adjusted_p))
        best = treatments[best_idx]
        direction = "higher" if best["rate"] > control["rate"] else "lower"
        recommendation = f"Variant '{best['id']}' shows statistically significant {direction} conversion rate."
    else:
        recommendation = "No statistically significant difference detected. Continue collecting data."

    result_variants = []
    for i, vs in enumerate(variant_stats):
        if i == 0:
            fr_used = freq_results[0] if freq_results else None
            ci_lo = fr_used.ci_lower_control if fr_used else 0.0
            ci_hi = fr_used.ci_upper_control if fr_used else 1.0
        else:
            fr_used = freq_results[i - 1] if i - 1 < len(freq_results) else None
            ci_lo = fr_used.ci_lower_treatment if fr_used else 0.0
            ci_hi = fr_used.ci_upper_treatment if fr_used else 1.0
        result_variants.append(ExperimentResultVariant(
            variant_id=vs["id"],
            conversions=vs["conversions"],
            total=vs["total"],
            conversion_rate=vs["rate"],
            ci_lower=ci_lo,
            ci_upper=ci_hi,
        ))

    return ExperimentResults(
        experiment_id=exp.id,
        status=exp.status,
        primary_metric=exp.target_metric,
        variants=result_variants,
        p_value=best_p,
        significant=any_significant,
        recommendation=recommendation,
        bayesian_probability=bayes_prob,
        sample_sizes={vs["id"]: vs["total"] for vs in variant_stats},
        analysis_at=datetime.now(timezone.utc),
    )


@celery_app.task(name="services.experiments.analysis.run_nightly_analysis")
def run_nightly_analysis():
    import asyncio
    asyncio.get_event_loop().run_until_complete(_nightly())


async def _nightly():
    from sqlalchemy import select
    from api.dependencies import AsyncSessionLocal
    from data.schemas.models import Experiment

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Experiment).where(Experiment.status == "RUNNING"))
        experiments = result.scalars().all()
        for exp in experiments:
            await compute_results(exp, db)
