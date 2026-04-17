import numpy as np
import pytest
from services.monitoring.drift import compute_kl_divergence, compute_psi


def test_psi_zero_for_identical_distributions():
    dist = np.random.default_rng(42).normal(0, 1, 1000)
    psi = compute_psi(dist, dist)
    assert psi < 0.05


def test_psi_high_for_different_distributions():
    ref = np.random.default_rng(0).normal(0, 1, 1000)
    cur = np.random.default_rng(1).normal(3, 1, 1000)
    psi = compute_psi(ref, cur)
    assert psi > 0.20


def test_kl_divergence_symmetric_near_zero():
    p = np.array([0.25, 0.25, 0.25, 0.25])
    q = np.array([0.25, 0.25, 0.25, 0.25])
    assert compute_kl_divergence(p, q) < 0.01


def test_kl_divergence_positive_for_different():
    p = np.array([0.9, 0.1])
    q = np.array([0.1, 0.9])
    assert compute_kl_divergence(p, q) > 1.0
