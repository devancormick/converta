from __future__ import annotations

import asyncio

from services.celery_app import app as celery_app

EVALUATOR_VERSION = "1.0.0"


@celery_app.task(name="services.evaluation.pipeline.run_evaluation_task", bind=True, max_retries=3)
def run_evaluation_task(self, message_id: int, original: str, rewritten: str):
    try:
        asyncio.get_event_loop().run_until_complete(_run(message_id, original, rewritten))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


async def _run(message_id: int, original: str, rewritten: str):
    from services.evaluation.metrics import compute_all
    from services.evaluation.llm_judge import llm_judge
    from services.classifier.inference import predict
    from data.schemas.models import EvalResult
    from api.dependencies import AsyncSessionLocal

    metrics = compute_all(original, rewritten)
    judge = await llm_judge(original, rewritten)
    clf_result = predict(rewritten)

    pass_fail = (
        metrics.rouge1 >= 0.1
        and metrics.bertscore_f1 >= 0.5
        and judge.score >= 3.0
        and clf_result.label == "pass"
    )

    async with AsyncSessionLocal() as db:
        row = EvalResult(
            message_id=message_id,
            rouge1=metrics.rouge1,
            rouge_l=metrics.rouge_l,
            bertscore_f1=metrics.bertscore_f1,
            perplexity=metrics.perplexity,
            llm_judge_score=judge.score,
            llm_judge_reasoning=judge.reasoning,
            llm_judge_dimensions=judge.dimension_scores,
            classifier_score=clf_result.score,
            pass_fail=pass_fail,
            evaluator_version=EVALUATOR_VERSION,
        )
        db.add(row)
        await db.commit()
