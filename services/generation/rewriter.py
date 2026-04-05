"""LLM rewrite service with retry/backoff."""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

from data.schemas.config import Settings

settings = Settings()

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0


@dataclass
class RewriteResult:
    text: str
    quality_score: float
    model_version: str
    variant_id: str


async def rewrite(
    raw_message: str,
    prompt_template,
    applicant_segment: str | None = None,
    channel: str | None = None,
    locale: str = "en",
) -> RewriteResult:
    prompt = prompt_template.template.format(
        raw_message=raw_message,
        applicant_segment=applicant_segment or "general",
        channel=channel or "email",
        locale=locale,
    )

    text = await _call_llm_with_retry(prompt)

    from services.classifier.inference import predict
    clf = predict(text)

    return RewriteResult(
        text=text,
        quality_score=clf.score,
        model_version=clf.model_version,
        variant_id=str(uuid.uuid4())[:8],
    )


async def _call_llm_with_retry(prompt: str) -> str:
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            return await _call_llm(prompt)
        except Exception as exc:
            last_exc = exc
            await asyncio.sleep(RETRY_BASE_DELAY * (2 ** attempt))
    raise RuntimeError(f"LLM call failed after {MAX_RETRIES} retries: {last_exc}")


async def _call_llm(prompt: str) -> str:
    if not settings.openai_api_key:
        # Offline fallback — echo with prefix for testing
        return f"[Rewritten] {prompt.split('Original message:')[-1].split('Applicant segment:')[0].strip()}"

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500,
    )
    return (response.choices[0].message.content or "").strip()
