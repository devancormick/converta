from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://converta:converta@localhost:5432/converta"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    openai_api_key: str = ""
    anthropic_api_key: str = ""

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"

    mlflow_tracking_uri: str = "http://localhost:5001"
    s3_bucket: str = "llm-msgopt-prod"
    aws_region: str = "us-east-1"

    classifier_model_name: str = "quality-classifier"
    classifier_threshold: float = 0.5

    pii_blocklist: list[str] = ["ssn", "social security", "date of birth"]
    compliance_blocklist: list[str] = ["guaranteed", "no credit check", "instant approval"]

    slack_webhook_url: str = ""
    pagerduty_api_key: str = ""

    environment: str = "development"
    log_level: str = "INFO"
