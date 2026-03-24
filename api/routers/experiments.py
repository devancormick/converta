from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_redis
from data.schemas.models import Experiment, ExperimentAssignment, ExperimentEvent
from data.schemas.pydantic_models import (
    AssignmentResponse,
    ExperimentCreate,
    ExperimentEventCreate,
    ExperimentResponse,
    ExperimentResults,
)

router = APIRouter(prefix="/v1/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentResponse, status_code=201)
async def create_experiment(payload: ExperimentCreate, db: AsyncSession = Depends(get_db)):
    split_sum = sum(payload.traffic_split.values())
    if abs(split_sum - 1.0) > 0.01:
        raise HTTPException(status_code=422, detail="traffic_split must sum to 1.0")

    exp = Experiment(
        name=payload.name,
        status="DRAFT",
        variants=[v.model_dump() for v in payload.variants],
        traffic_split=payload.traffic_split,
        target_metric=payload.target_metric,
        guardrail_metrics=payload.guardrail_metrics,
        min_sample_size=payload.min_sample_size,
        max_duration_days=payload.max_duration_days,
        audit_log=[{"action": "created", "at": datetime.now(timezone.utc).isoformat()}],
    )
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    return exp


@router.post("/{experiment_id}/start", response_model=ExperimentResponse)
async def start_experiment(experiment_id: int, db: AsyncSession = Depends(get_db)):
    exp = await _get_experiment(experiment_id, db)
    if exp.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Only DRAFT experiments can be started")
    exp.status = "RUNNING"
    exp.started_at = datetime.now(timezone.utc)
    exp.audit_log = (exp.audit_log or []) + [{"action": "started", "at": datetime.now(timezone.utc).isoformat()}]
    await db.commit()
    await db.refresh(exp)
    return exp


@router.post("/{experiment_id}/pause", response_model=ExperimentResponse)
async def pause_experiment(experiment_id: int, db: AsyncSession = Depends(get_db)):
    exp = await _get_experiment(experiment_id, db)
    if exp.status != "RUNNING":
        raise HTTPException(status_code=409, detail="Only RUNNING experiments can be paused")
    exp.status = "PAUSED"
    exp.audit_log = (exp.audit_log or []) + [{"action": "paused", "at": datetime.now(timezone.utc).isoformat()}]
    await db.commit()
    await db.refresh(exp)
    return exp


@router.post("/{experiment_id}/conclude", response_model=ExperimentResponse)
async def conclude_experiment(experiment_id: int, db: AsyncSession = Depends(get_db)):
    exp = await _get_experiment(experiment_id, db)
    exp.status = "CONCLUDED"
    exp.concluded_at = datetime.now(timezone.utc)
    exp.audit_log = (exp.audit_log or []) + [{"action": "concluded", "at": datetime.now(timezone.utc).isoformat()}]
    await db.commit()
    await db.refresh(exp)
    return exp


@router.get("/assign", response_model=AssignmentResponse)
async def assign_user(
    user_id: str,
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    from services.experiments.assignment import assign_variant

    cache_key = f"assign:{experiment_id}:{user_id}"
    cached = await redis.get(cache_key)
    if cached:
        return AssignmentResponse(user_id=user_id, experiment_id=experiment_id, variant_id=cached, cached=True)

    exp = await _get_experiment(experiment_id, db)
    if exp.status != "RUNNING":
        raise HTTPException(status_code=409, detail="Experiment is not RUNNING")

    variant_id = assign_variant(user_id, str(experiment_id), exp.variants, exp.traffic_split)

    existing = await db.execute(
        select(ExperimentAssignment).where(
            ExperimentAssignment.experiment_id == experiment_id,
            ExperimentAssignment.user_id == user_id,
        )
    )
    if not existing.scalars().first():
        db.add(ExperimentAssignment(experiment_id=experiment_id, user_id=user_id, variant_id=variant_id))
        await db.commit()

    await redis.set(cache_key, variant_id, ex=86400)
    return AssignmentResponse(user_id=user_id, experiment_id=experiment_id, variant_id=variant_id, cached=False)


@router.post("/{experiment_id}/events", status_code=201)
async def record_event(
    experiment_id: int,
    payload: ExperimentEventCreate,
    db: AsyncSession = Depends(get_db),
):
    await _get_experiment(experiment_id, db)
    event = ExperimentEvent(
        experiment_id=experiment_id,
        user_id=payload.user_id,
        variant_id=payload.variant_id,
        event_type=payload.event_type,
        converted=payload.converted,
        funnel_step=payload.funnel_step,
    )
    db.add(event)
    await db.commit()
    return {"ok": True}


@router.get("/{experiment_id}/results", response_model=ExperimentResults)
async def get_results(experiment_id: int, db: AsyncSession = Depends(get_db)):
    from services.experiments.analysis import compute_results
    exp = await _get_experiment(experiment_id, db)
    return await compute_results(exp, db)


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: int, db: AsyncSession = Depends(get_db)):
    return await _get_experiment(experiment_id, db)


async def _get_experiment(experiment_id: int, db: AsyncSession) -> Experiment:
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    exp = result.scalars().first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp
