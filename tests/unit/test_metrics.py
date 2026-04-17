import pytest
from services.evaluation.metrics import compute_rouge


def test_rouge_identical():
    r1, rl = compute_rouge("hello world", "hello world")
    assert r1 == pytest.approx(1.0, abs=0.01)
    assert rl == pytest.approx(1.0, abs=0.01)


def test_rouge_different():
    r1, rl = compute_rouge("hello world", "goodbye moon")
    assert r1 < 0.5


def test_rouge_returns_floats():
    r1, rl = compute_rouge("test sentence", "another sentence here")
    assert isinstance(r1, float)
    assert isinstance(rl, float)
    assert 0.0 <= r1 <= 1.0
    assert 0.0 <= rl <= 1.0
