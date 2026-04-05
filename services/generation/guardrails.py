"""Pre- and post-generation guardrails."""
from __future__ import annotations

import re
from dataclasses import dataclass

from data.schemas.config import Settings

settings = Settings()

_PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),           # SSN
    re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),  # credit card
    re.compile(r"\bdate of birth\b", re.I),
    re.compile(r"\bDOB\b"),
]

_COMPLIANCE_PATTERNS = [
    re.compile(r"\bguaranteed\b", re.I),
    re.compile(r"\bno credit check\b", re.I),
    re.compile(r"\binstant approval\b", re.I),
    re.compile(r"\b100%\s+approved\b", re.I),
    re.compile(r"\bno questions asked\b", re.I),
]


@dataclass
class GuardrailResult:
    ok: bool
    reason: str = ""


def run_pre_guardrails(text: str) -> GuardrailResult:
    for pattern in _PII_PATTERNS:
        if pattern.search(text):
            return GuardrailResult(ok=False, reason=f"PII detected: pattern {pattern.pattern!r}")
    for kw in settings.pii_blocklist:
        if kw.lower() in text.lower():
            return GuardrailResult(ok=False, reason=f"Blocklisted PII keyword: {kw!r}")
    return GuardrailResult(ok=True)


def run_post_guardrails(text: str, cfg: Settings | None = None) -> GuardrailResult:
    cfg = cfg or settings
    for pattern in _COMPLIANCE_PATTERNS:
        if pattern.search(text):
            return GuardrailResult(ok=False, reason=f"Compliance violation: {pattern.pattern!r}")
    for kw in cfg.compliance_blocklist:
        if kw.lower() in text.lower():
            return GuardrailResult(ok=False, reason=f"Compliance keyword: {kw!r}")
    return GuardrailResult(ok=True)


def scrub_pii(text: str) -> str:
    for pattern in _PII_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text
