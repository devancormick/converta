from __future__ import annotations

import json
from dataclasses import dataclass

from data.schemas.config import Settings

settings = Settings()

JUDGE_PROMPT = """You are an expert evaluator of consumer-facing loan application messages.

Evaluate the following rewritten message on these dimensions (each scored 1-5):
- fluency: Is the text grammatically correct and natural?
- clarity: Is the message clear and easy to understand?
- engagement: Is the message likely to motivate the reader to take action?
- compliance: Does the message avoid misleading or deceptive language?
- tone: Is the tone appropriate — professional, empathetic, and non-threatening?

Original message: {original}
Rewritten message: {rewritten}

Respond ONLY with valid JSON in this exact format:
{{
  "score": <overall 1-5 float>,
  "dimension_scores": {{
    "fluency": <1-5>,
    "clarity": <1-5>,
    "engagement": <1-5>,
    "compliance": <1-5>,
    "tone": <1-5>
  }},
  "reasoning": "<one sentence explaining the score>"
}}"""


@dataclass
class JudgeResult:
    score: float
    dimension_scores: dict[str, float]
    reasoning: str


async def llm_judge(original: str, rewritten: str) -> JudgeResult:
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt = JUDGE_PROMPT.format(original=original, rewritten=rewritten)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        return JudgeResult(
            score=float(data.get("score", 3.0)),
            dimension_scores=data.get("dimension_scores", {}),
            reasoning=data.get("reasoning", ""),
        )
    except Exception as e:
        return JudgeResult(score=3.0, dimension_scores={}, reasoning=f"Judge unavailable: {e}")
