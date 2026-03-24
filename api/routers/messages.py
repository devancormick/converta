import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_settings
from data.schemas.config import Settings
from data.schemas.models import Message
from data.schemas.pydantic_models import RewriteRequest, RewriteResponse

router = APIRouter(prefix="/v1/messages", tags=["messages"])


@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_message(
    payload: RewriteRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    from services.generation.guardrails import run_pre_guardrails, run_post_guardrails
    from services.generation.rewriter import rewrite
    from services.generation.prompt_registry import get_active_prompt

    start = time.monotonic()

    pre_result = run_pre_guardrails(payload.raw_message)
    if not pre_result.ok:
        raise HTTPException(status_code=422, detail=f"Pre-guardrail failure: {pre_result.reason}")

    prompt = get_active_prompt(payload.strategy or "tone")
    result = await rewrite(
        raw_message=payload.raw_message,
        prompt_template=prompt,
        applicant_segment=payload.applicant_segment,
        channel=payload.channel,
        locale=payload.locale,
    )

    post_result = run_post_guardrails(result.text, settings)
    passed = post_result.ok and result.quality_score >= settings.classifier_threshold

    latency_ms = int((time.monotonic() - start) * 1000)

    msg = Message(
        raw_text=payload.raw_message,
        rewritten_text=result.text if passed else None,
        prompt_version=prompt.semver,
        model_version=result.model_version,
        applicant_segment=payload.applicant_segment,
        channel=payload.channel,
        locale=payload.locale,
        campaign_id=payload.campaign_id,
        quality_score=result.quality_score,
        passed_gate=passed,
        latency_ms=latency_ms,
        variant_id=result.variant_id,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    if not passed:
        reason = post_result.reason if not post_result.ok else "quality score below threshold"
        raise HTTPException(status_code=422, detail=f"Post-guardrail failure: {reason}")

    # Trigger async evaluation
    from services.evaluation.pipeline import run_evaluation_task
    run_evaluation_task.delay(msg.id, payload.raw_message, result.text)

    return RewriteResponse(
        message_id=msg.id,
        rewritten_message=result.text,
        quality_score=result.quality_score,
        passed_gate=passed,
        variant_id=result.variant_id,
        prompt_version=prompt.semver,
        model_version=result.model_version,
        latency_ms=latency_ms,
    )
