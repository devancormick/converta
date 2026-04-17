import pytest
from services.experiments.assignment import assign_variant

VARIANTS = [{"id": "control"}, {"id": "treatment"}]
SPLIT = {"control": 0.5, "treatment": 0.5}


def test_assignment_is_deterministic():
    v1 = assign_variant("user-123", "exp-1", VARIANTS, SPLIT)
    v2 = assign_variant("user-123", "exp-1", VARIANTS, SPLIT)
    assert v1 == v2


def test_assignment_respects_split():
    results = [assign_variant(f"user-{i}", "exp-1", VARIANTS, SPLIT) for i in range(1000)]
    control_pct = results.count("control") / len(results)
    assert 0.40 < control_pct < 0.60, f"Control pct {control_pct:.2%} out of expected range"


def test_assignment_different_users_differ():
    variants = [assign_variant(f"user-{i}", "exp-2", VARIANTS, SPLIT) for i in range(100)]
    assert len(set(variants)) > 1


def test_assignment_returns_valid_variant():
    variant = assign_variant("user-abc", "exp-1", VARIANTS, SPLIT)
    assert variant in {"control", "treatment"}
