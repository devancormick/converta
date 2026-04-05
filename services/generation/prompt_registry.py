"""Versioned prompt template registry with hot-reload support."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

import yaml

TEMPLATES_DIR = Path("prompt-templates")
_lock = threading.RLock()
_registry: dict[str, "_PromptTemplate"] = {}


@dataclass
class _PromptTemplate:
    name: str
    semver: str
    strategy: str
    template: str
    variables: list[str]


def _load_all() -> dict[str, _PromptTemplate]:
    loaded = {}
    for path in TEMPLATES_DIR.glob("*.yaml"):
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            pt = _PromptTemplate(
                name=data["name"],
                semver=data["semver"],
                strategy=data["strategy"],
                template=data["template"],
                variables=data.get("variables", []),
            )
            loaded[pt.strategy] = pt
        except Exception:
            pass
    return loaded


def get_active_prompt(strategy: str = "tone") -> _PromptTemplate:
    with _lock:
        if not _registry:
            _registry.update(_load_all())
        prompt = _registry.get(strategy) or _registry.get("tone") or _get_default(strategy)
    return prompt


def reload_registry():
    with _lock:
        _registry.clear()
        _registry.update(_load_all())


def _get_default(strategy: str) -> _PromptTemplate:
    return _PromptTemplate(
        name="default",
        semver="1.0.0",
        strategy=strategy,
        template=(
            "You are an expert copywriter for consumer financial products. "
            "Rewrite the following loan application message to be clearer, more engaging, "
            "and professional. Preserve all factual content. "
            "Do not add false promises, guarantees, or regulatory violations.\n\n"
            "Original message:\n{raw_message}\n\n"
            "Applicant segment: {applicant_segment}\n"
            "Channel: {channel}\n"
            "Locale: {locale}\n\n"
            "Rewritten message:"
        ),
        variables=["raw_message", "applicant_segment", "channel", "locale"],
    )
