"""Human evaluation labeling queue — lightweight internal tool."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from data.schemas.models import EvalResult, Message

router = APIRouter(prefix="/v1/human-eval", tags=["human-eval"])


@router.get("/queue")
async def get_labeling_queue(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Return messages with no human label yet for spot-check labeling."""
    result = await db.execute(
        select(EvalResult, Message)
        .join(Message, EvalResult.message_id == Message.id)
        .where(EvalResult.human_label.is_(None))
        .order_by(EvalResult.created_at.desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "eval_id": ev.id,
            "message_id": ev.message_id,
            "raw_text": msg.raw_text,
            "rewritten_text": msg.rewritten_text,
            "llm_judge_score": ev.llm_judge_score,
            "classifier_score": ev.classifier_score,
            "pass_fail": ev.pass_fail,
        }
        for ev, msg in rows
    ]


@router.get("/stats")
async def labeling_stats(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    total = await db.scalar(select(func.count()).select_from(EvalResult))
    labeled = await db.scalar(select(func.count()).select_from(EvalResult).where(EvalResult.human_label.isnot(None)))
    return {"total": total, "labeled": labeled, "unlabeled": (total or 0) - (labeled or 0)}
