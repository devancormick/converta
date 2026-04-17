import pytest
from services.experiments.stats import (
    bayesian_beta_binomial,
    holm_bonferroni_correction,
    power_analysis,
    two_proportion_z_test,
)


def test_power_analysis_returns_positive_n():
    result = power_analysis(baseline_rate=0.10, mde=0.02)
    assert result.required_n_per_variant > 0


def test_z_test_detects_significant_difference():
    result = two_proportion_z_test(
        conversions_a=50, total_a=1000,
        conversions_b=80, total_b=1000,
    )
    assert result.significant
    assert result.p_value < 0.05


def test_z_test_no_difference():
    result = two_proportion_z_test(
        conversions_a=100, total_a=1000,
        conversions_b=101, total_b=1000,
    )
    assert not result.significant
    assert result.p_value > 0.05


def test_holm_bonferroni_correction_length():
    p_values = [0.01, 0.04, 0.20]
    adjusted = holm_bonferroni_correction(p_values)
    assert len(adjusted) == len(p_values)


def test_bayesian_returns_valid_probability():
    result = bayesian_beta_binomial(50, 1000, 80, 1000)
    assert 0.0 <= result.probability_treatment_better <= 1.0


def test_bayesian_treatment_better_when_higher_conversions():
    result = bayesian_beta_binomial(100, 1000, 200, 1000)
    assert result.probability_treatment_better > 0.90
