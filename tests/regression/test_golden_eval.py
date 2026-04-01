"""Golden dataset regression test — must pass ≥ 95% of cases."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.evaluation.metrics import compute_rouge

GOLDEN_PATH = Path("data/golden_datasets/eval_golden.jsonl")
PASS_THRESHOLD = 0.95


def load_golden() -> list[dict]:
    if not GOLDEN_PATH.exists():
        return []
    with open(GOLDEN_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


@pytest.mark.parametrize("case", load_golden() or [{"original": "test", "rewritten": "test", "min_rouge1": 0.0}])
def test_golden_rouge(case):
    rouge1, _ = compute_rouge(case["original"], case["rewritten"])
    assert rouge1 >= case.get("min_rouge1", 0.0), f"ROUGE-1 {rouge1:.3f} below min {case.get('min_rouge1', 0.0)}"


def test_golden_pass_rate():
    cases = load_golden()
    if not cases:
        pytest.skip("No golden dataset found")
    passed = 0
    for case in cases:
        rouge1, _ = compute_rouge(case["original"], case["rewritten"])
        if rouge1 >= case.get("min_rouge1", 0.0):
            passed += 1
    rate = passed / len(cases)
    assert rate >= PASS_THRESHOLD, f"Golden pass rate {rate:.2%} below required {PASS_THRESHOLD:.0%}"
