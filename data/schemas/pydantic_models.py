from datetime import datetime

from pydantic import BaseModel, Field


# --- Message Generation ---

class RewriteRequest(BaseModel):
    raw_message: str = Field(..., min_length=1, max_length=5000)
    applicant_segment: str | None = None
    channel: str | None = Field(None, pattern="^(sms|email|push)$")
    locale: str = "en"
    campaign_id: str | None = None
    strategy: str | None = Field(None, pattern="^(tone|length|urgency|personalization)$")


class RewriteResponse(BaseModel):
    message_id: int
    rewritten_message: str
    quality_score: float
    passed_gate: bool
    variant_id: str
    prompt_version: str
    model_version: str
    latency_ms: int


# --- Evaluation ---

class EvalResultResponse(BaseModel):
    id: int
    message_id: int
    rouge1: float | None
    rouge_l: float | None
    bertscore_f1: float | None
    perplexity: float | None
    llm_judge_score: float | None
    llm_judge_reasoning: str | None
    llm_judge_dimensions: dict | None
    classifier_score: float | None
    pass_fail: bool | None
    evaluator_version: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class HumanLabelRequest(BaseModel):
    message_id: int
    label: str = Field(..., pattern="^(pass|fail|too_long|off_tone|compliance_risk|low_engagement|hallucination_flag)$")
    annotator: str


# --- Experiments ---

class ExperimentVariant(BaseModel):
    id: str
    name: str
    prompt_version: str | None = None
    description: str | None = None


class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    variants: list[ExperimentVariant] = Field(..., min_length=2, max_length=5)
    traffic_split: dict[str, float]
    target_metric: str
    guardrail_metrics: dict[str, float] = {}
    min_sample_size: int | None = None
    max_duration_days: int | None = None


class ExperimentResponse(BaseModel):
    id: int
    name: str
    status: str
    variants: list[dict]
    traffic_split: dict
    target_metric: str
    guardrail_metrics: dict
    started_at: datetime | None
    concluded_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AssignmentResponse(BaseModel):
    user_id: str
    experiment_id: int
    variant_id: str
    cached: bool


class ExperimentResultVariant(BaseModel):
    variant_id: str
    conversions: int
    total: int
    conversion_rate: float
    ci_lower: float
    ci_upper: float


class ExperimentResults(BaseModel):
    experiment_id: int
    status: str
    primary_metric: str
    variants: list[ExperimentResultVariant]
    p_value: float | None
    significant: bool | None
    recommendation: str
    bayesian_probability: float | None
    sample_sizes: dict[str, int]
    analysis_at: datetime


class ExperimentEventCreate(BaseModel):
    user_id: str
    variant_id: str
    event_type: str
    converted: bool = False
    funnel_step: str | None = None
