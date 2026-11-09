"""Scalar first-order uncertainty propagation with explicit distributions."""

from dataclasses import dataclass
from math import sqrt

import numpy as np


@dataclass(frozen=True)
class Component:
    name: str
    estimate: float
    standard_uncertainty: float
    evaluation: str
    distribution: str

    def __post_init__(self):
        if not np.isfinite([self.estimate, self.standard_uncertainty]).all():
            raise ValueError("estimates and uncertainties must be finite")
        if self.standard_uncertainty < 0:
            raise ValueError("standard uncertainty cannot be negative")
        if self.evaluation not in {"A", "B"} or self.distribution not in {"normal", "uniform"}:
            raise ValueError("evaluation must be A/B and distribution normal/uniform")


def type_a(name, observations):
    samples = np.asarray(observations, dtype=float)
    if samples.ndim != 1 or len(samples) < 2 or not np.isfinite(samples).all():
        raise ValueError("Type A mean needs at least two finite observations")
    return Component(name, float(samples.mean()), float(samples.std(ddof=1) / sqrt(len(samples))), "A", "normal")


def rectangular(name, estimate, half_width):
    if not np.isfinite(half_width) or half_width < 0:
        raise ValueError("half width must be finite and nonnegative")
    return Component(name, estimate, half_width / sqrt(3), "B", "uniform")


def covariance(components, correlation=None):
    count = len(components)
    if count == 0 or len({c.name for c in components}) != count:
        raise ValueError("components must be nonempty with unique names")
    coefficients = np.eye(count) if correlation is None else np.asarray(correlation, dtype=float)
    if coefficients.shape != (count, count) or not np.isfinite(coefficients).all():
        raise ValueError("correlation shape/values invalid")
    if not np.allclose(coefficients, coefficients.T, atol=1e-12, rtol=0):
        raise ValueError("correlation must be symmetric")
    if not np.allclose(np.diag(coefficients), 1, atol=1e-12, rtol=0):
        raise ValueError("correlation diagonal must be one")
    if np.linalg.eigvalsh(coefficients).min() < -1e-12:
        raise ValueError("correlation must be positive semidefinite")
    scales = np.array([c.standard_uncertainty for c in components])
    return coefficients * np.outer(scales, scales)


def sensitivity(model, estimates, uncertainty_scales):
    estimates = np.asarray(estimates, dtype=float)
    scales = np.maximum(np.abs(estimates), uncertainty_scales)
    # A one-unit floor changes physics when inputs are expressed in small SI units.
    steps = np.cbrt(np.finfo(float).eps) * np.where(scales > 0, scales, 1)
    derivatives = []
    for index, step in enumerate(steps):
        offset = np.zeros_like(estimates)
        offset[index] = step
        derivatives.append((model(estimates + offset) - model(estimates - offset)) / (2 * step))
    gradient = np.asarray(derivatives)
    if gradient.shape != estimates.shape or not np.isfinite(gradient).all():
        raise ValueError("model must produce one finite scalar")
    return gradient


def propagate(model, components, correlation=None, coverage_factor=2.0):
    if not np.isfinite(coverage_factor) or coverage_factor <= 0:
        raise ValueError("coverage factor must be finite and positive")
    input_covariance = covariance(components, correlation)
    estimates = np.array([c.estimate for c in components])
    gradient = sensitivity(model, estimates, [c.standard_uncertainty for c in components])
    prediction = float(model(estimates))
    if not np.isfinite(prediction):
        raise ValueError("model prediction must be finite")
    combined = sqrt(max(0.0, float(gradient @ input_covariance @ gradient)))
    return {"estimate": prediction, "standard_uncertainty": combined,
            "expanded_uncertainty": coverage_factor * combined, "coverage_factor": coverage_factor,
            "sensitivity": dict(zip((c.name for c in components), gradient.tolist())),
            "covariance": input_covariance.tolist()}


@dataclass(frozen=True)
class Sampling:
    count: int = 100000
    seed: int = 2026
    correlation: object = None


def input_samples(components, sampling):
    if sampling.count < 2:
        raise ValueError("Monte Carlo needs at least two samples")
    input_covariance = covariance(components, sampling.correlation)
    generator = np.random.default_rng(sampling.seed)
    estimates = np.array([c.estimate for c in components])
    if sampling.correlation is not None:
        if any(c.distribution != "normal" for c in components):
            raise ValueError("correlated Monte Carlo currently supports normal inputs only")
        return generator.multivariate_normal(estimates, input_covariance, sampling.count)
    columns = []
    for component in components:
        scale = component.standard_uncertainty
        draws = (generator.normal(0, scale, sampling.count) if component.distribution == "normal"
                 else generator.uniform(-sqrt(3) * scale, sqrt(3) * scale, sampling.count))
        columns.append(component.estimate + draws)
    return np.column_stack(columns)


def monte_carlo(model, components, sampling=Sampling()):
    predictions = np.asarray([model(row) for row in input_samples(components, sampling)], dtype=float)
    if predictions.ndim != 1 or not np.isfinite(predictions).all():
        raise ValueError("model must produce finite scalar Monte Carlo outputs")
    return {"mean": float(predictions.mean()), "standard_uncertainty": float(predictions.std(ddof=1)),
            "central_95_interval": np.quantile(predictions, [0.025, 0.975]).tolist(),
            "samples": sampling.count, "seed": sampling.seed}
