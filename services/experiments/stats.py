"""Statistical analysis engine: power analysis, z-test, Bayesian Beta-Binomial."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class PowerAnalysisResult:
    required_n_per_variant: int
    mde: float
    baseline_rate: float
    alpha: float
    power: float


@dataclass
class FrequentistResult:
    p_value: float
    significant: bool
    z_stat: float
    ci_lower_control: float
    ci_upper_control: float
    ci_lower_treatment: float
    ci_upper_treatment: float


@dataclass
class BayesianResult:
    probability_treatment_better: float
    expected_lift: float


def power_analysis(
    baseline_rate: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> PowerAnalysisResult:
    treatment_rate = baseline_rate + mde
    p_bar = (baseline_rate + treatment_rate) / 2
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    n = (
        (z_alpha * math.sqrt(2 * p_bar * (1 - p_bar)) + z_beta * math.sqrt(
            baseline_rate * (1 - baseline_rate) + treatment_rate * (1 - treatment_rate)
        )) ** 2
    ) / (mde ** 2)
    return PowerAnalysisResult(
        required_n_per_variant=math.ceil(n),
        mde=mde,
        baseline_rate=baseline_rate,
        alpha=alpha,
        power=power,
    )


def two_proportion_z_test(
    conversions_a: int,
    total_a: int,
    conversions_b: int,
    total_b: int,
    alpha: float = 0.05,
) -> FrequentistResult:
    p_a = conversions_a / max(total_a, 1)
    p_b = conversions_b / max(total_b, 1)
    p_pool = (conversions_a + conversions_b) / max(total_a + total_b, 1)

    se = math.sqrt(p_pool * (1 - p_pool) * (1 / max(total_a, 1) + 1 / max(total_b, 1)))
    z = (p_b - p_a) / max(se, 1e-10)
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    z_crit = stats.norm.ppf(1 - alpha / 2)
    se_a = math.sqrt(p_a * (1 - p_a) / max(total_a, 1))
    se_b = math.sqrt(p_b * (1 - p_b) / max(total_b, 1))

    return FrequentistResult(
        p_value=p_value,
        significant=p_value < alpha,
        z_stat=z,
        ci_lower_control=max(0.0, p_a - z_crit * se_a),
        ci_upper_control=min(1.0, p_a + z_crit * se_a),
        ci_lower_treatment=max(0.0, p_b - z_crit * se_b),
        ci_upper_treatment=min(1.0, p_b + z_crit * se_b),
    )


def holm_bonferroni_correction(p_values: list[float], alpha: float = 0.05) -> list[float]:
    """Return adjusted p-values using Holm-Bonferroni correction."""
    n = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * n
    for rank, (original_idx, p) in enumerate(indexed):
        adjusted[original_idx] = min(1.0, p * (n - rank))
    return adjusted


def bayesian_beta_binomial(
    conversions_a: int,
    total_a: int,
    conversions_b: int,
    total_b: int,
    n_samples: int = 10_000,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> BayesianResult:
    rng = np.random.default_rng(42)
    samples_a = rng.beta(prior_alpha + conversions_a, prior_beta + total_a - conversions_a, n_samples)
    samples_b = rng.beta(prior_alpha + conversions_b, prior_beta + total_b - conversions_b, n_samples)
    prob_b_better = float(np.mean(samples_b > samples_a))
    expected_lift = float(np.mean((samples_b - samples_a) / np.maximum(samples_a, 1e-10)))
    return BayesianResult(probability_treatment_better=prob_b_better, expected_lift=expected_lift)
