"""initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("rewritten_text", sa.Text()),
        sa.Column("prompt_version", sa.String(50)),
        sa.Column("model_version", sa.String(100)),
        sa.Column("applicant_segment", sa.String(100)),
        sa.Column("channel", sa.String(50)),
        sa.Column("locale", sa.String(10), server_default="en"),
        sa.Column("campaign_id", sa.String(100)),
        sa.Column("quality_score", sa.Float()),
        sa.Column("passed_gate", sa.Boolean()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("variant_id", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "eval_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("rouge1", sa.Float()),
        sa.Column("rouge_l", sa.Float()),
        sa.Column("bertscore_f1", sa.Float()),
        sa.Column("perplexity", sa.Float()),
        sa.Column("llm_judge_score", sa.Float()),
        sa.Column("llm_judge_reasoning", sa.Text()),
        sa.Column("llm_judge_dimensions", postgresql.JSONB()),
        sa.Column("classifier_score", sa.Float()),
        sa.Column("pass_fail", sa.Boolean()),
        sa.Column("evaluator_version", sa.String(50)),
        sa.Column("human_label", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(50), server_default="DRAFT"),
        sa.Column("variants", postgresql.JSONB(), nullable=False),
        sa.Column("traffic_split", postgresql.JSONB(), nullable=False),
        sa.Column("target_metric", sa.String(100), nullable=False),
        sa.Column("guardrail_metrics", postgresql.JSONB(), server_default="{}"),
        sa.Column("min_sample_size", sa.Integer()),
        sa.Column("max_duration_days", sa.Integer()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("concluded_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("audit_log", postgresql.JSONB(), server_default="[]"),
    )
    op.create_table(
        "experiment_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("experiment_id", sa.Integer(), sa.ForeignKey("experiments.id"), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("variant_id", sa.String(100), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_exp_assignments_lookup", "experiment_assignments", ["experiment_id", "user_id"])
    op.create_table(
        "experiment_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("experiment_id", sa.Integer(), sa.ForeignKey("experiments.id"), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("variant_id", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("converted", sa.Boolean(), server_default="false"),
        sa.Column("funnel_step", sa.String(100)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_exp_events_lookup", "experiment_events", ["experiment_id", "variant_id"])
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("mlflow_run_id", sa.String(255)),
        sa.Column("champion", sa.Boolean(), server_default="false"),
        sa.Column("deployed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("metrics", postgresql.JSONB(), server_default="{}"),
    )
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("semver", sa.String(50), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column("variables", postgresql.JSONB(), server_default="{}"),
        sa.Column("deployed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deprecated_at", sa.DateTime(timezone=True)),
        sa.Column("author", sa.String(255)),
    )


def downgrade() -> None:
    op.drop_table("prompt_versions")
    op.drop_table("model_versions")
    op.drop_table("experiment_events")
    op.drop_table("experiment_assignments")
    op.drop_table("experiments")
    op.drop_table("eval_results")
    op.drop_table("messages")
