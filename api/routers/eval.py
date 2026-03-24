from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from data.schemas.models import EvalResult
from data.schemas.pydantic_models import EvalResultResponse, HumanLabelRequest

router = APIRouter(prefix="/v1/eval", tags=["evaluation"])


@router.get("/{message_id}", response_model=list[EvalResultResponse])
async def get_eval_results(message_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EvalResult).where(EvalResult.message_id == message_id).order_by(EvalResult.created_at.desc())
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="No eval results found for this message")
    return rows


@router.post("/label")
async def submit_human_label(payload: HumanLabelRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EvalResult).where(EvalResult.message_id == payload.message_id).order_by(EvalResult.created_at.desc())
    )
    row = result.scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="No eval result found")
    row.human_label = payload.label
    await db.commit()
    return {"ok": True, "message_id": payload.message_id, "label": payload.label}
