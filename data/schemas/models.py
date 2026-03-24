from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    rewritten_text: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    model_version: Mapped[str | None] = mapped_column(String(100))
    applicant_segment: Mapped[str | None] = mapped_column(String(100))
    channel: Mapped[str | None] = mapped_column(String(50))
    locale: Mapped[str] = mapped_column(String(10), default="en")
    campaign_id: Mapped[str | None] = mapped_column(String(100))
    quality_score: Mapped[float | None] = mapped_column(Float)
    passed_gate: Mapped[bool | None] = mapped_column(Boolean)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    variant_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    eval_results: Mapped[list["EvalResult"]] = relationship(back_populates="message")


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), nullable=False)
    rouge1: Mapped[float | None] = mapped_column(Float)
    rouge_l: Mapped[float | None] = mapped_column(Float)
    bertscore_f1: Mapped[float | None] = mapped_column(Float)
    perplexity: Mapped[float | None] = mapped_column(Float)
    llm_judge_score: Mapped[float | None] = mapped_column(Float)
    llm_judge_reasoning: Mapped[str | None] = mapped_column(Text)
    llm_judge_dimensions: Mapped[dict | None] = mapped_column(JSONB)
    classifier_score: Mapped[float | None] = mapped_column(Float)
    pass_fail: Mapped[bool | None] = mapped_column(Boolean)
    evaluator_version: Mapped[str | None] = mapped_column(String(50))
    human_label: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    message: Mapped["Message"] = relationship(back_populates="eval_results")


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")
    variants: Mapped[dict] = mapped_column(JSONB, nullable=False)
    traffic_split: Mapped[dict] = mapped_column(JSONB, nullable=False)
    target_metric: Mapped[str] = mapped_column(String(100), nullable=False)
    guardrail_metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    min_sample_size: Mapped[int | None] = mapped_column(Integer)
    max_duration_days: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    concluded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    audit_log: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    assignments: Mapped[list["ExperimentAssignment"]] = relationship(back_populates="experiment")
    events: Mapped[list["ExperimentEvent"]] = relationship(back_populates="experiment")


class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    experiment: Mapped["Experiment"] = relationship(back_populates="assignments")


class ExperimentEvent(Base):
    __tablename__ = "experiment_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    converted: Mapped[bool] = mapped_column(Boolean, default=False)
    funnel_step: Mapped[str | None] = mapped_column(String(100))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    experiment: Mapped["Experiment"] = relationship(back_populates="events")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(255))
    champion: Mapped[bool] = mapped_column(Boolean, default=False)
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    semver: Mapped[str] = mapped_column(String(50), nullable=False)
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[dict] = mapped_column(JSONB, default=dict)
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author: Mapped[str | None] = mapped_column(String(255))
