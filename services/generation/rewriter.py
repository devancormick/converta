"""LLM rewrite service — Groq primary, OpenRouter fallback, offline last resort."""
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

    text, model_used = await _call_with_fallback(prompt)

    from services.classifier.inference import predict
    clf = predict(text)

    return RewriteResult(
        text=text,
        quality_score=clf.score,
        model_version=model_used,
        variant_id=str(uuid.uuid4())[:8],
    )


async def _call_with_fallback(prompt: str) -> tuple[str, str]:
    # 1. Groq (fast, generous free tier)
    if settings.groq_api_key:
        try:
            text = await _call_openai_compat(
                prompt,
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
                model=settings.groq_model,
            )
            return text, f"groq/{settings.groq_model}"
        except Exception as e:
            print(f"[rewriter] Groq failed: {e} — trying OpenRouter")

    # 2. OpenRouter fallback
    if settings.openrouter_api_key:
        try:
            text = await _call_openai_compat(
                prompt,
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                model=settings.openrouter_model,
                extra_headers={"HTTP-Referer": "https://github.com/converta"},
            )
            return text, f"openrouter/{settings.openrouter_model}"
        except Exception as e:
            print(f"[rewriter] OpenRouter failed: {e} — using offline fallback")

    # 3. OpenAI fallback
    if settings.openai_api_key:
        try:
            text = await _call_openai_compat(
                prompt,
                api_key=settings.openai_api_key,
                base_url="https://api.openai.com/v1",
                model="gpt-4o-mini",
            )
            return text, "openai/gpt-4o-mini"
        except Exception as e:
            print(f"[rewriter] OpenAI failed: {e} — using offline fallback")

    # 4. Offline echo (no API keys)
    raw = prompt.split("Original message:")[-1].split("Applicant segment:")[0].strip()
    return f"[Dev fallback — no LLM key] {raw}", "offline/fallback"


async def _call_openai_compat(
    prompt: str,
    api_key: str,
    base_url: str,
    model: str,
    extra_headers: dict | None = None,
) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        default_headers=extra_headers or {},
        timeout=30.0,
    )

    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BASE_DELAY * (2 ** attempt))

    raise RuntimeError(f"LLM call failed after {MAX_RETRIES} retries: {last_exc}")
