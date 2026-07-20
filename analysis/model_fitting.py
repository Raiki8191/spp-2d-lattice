"""Constrained finite-size models and information criteria for scaling-v2."""

from __future__ import annotations

import math
from typing import Callable, Iterable

import numpy as np
from scipy.optimize import curve_fit


def information_criteria(rss: float, n: int, parameter_count: int) -> tuple[float, float]:
    if n < 1 or parameter_count < 1 or not np.isfinite(rss) or rss < 0:
        raise ValueError("valid rss, n, and parameter_count are required")
    safe_rss = max(float(rss), np.finfo(float).tiny)
    aic = n * math.log(safe_rss / n) + 2 * parameter_count
    aicc = (
        aic + 2 * parameter_count * (parameter_count + 1) / (n - parameter_count - 1)
        if n > parameter_count + 1
        else math.inf
    )
    bic = n * math.log(safe_rss / n) + parameter_count * math.log(n)
    return aicc, bic


def pure_power(L: np.ndarray, b: float, omega: float) -> np.ndarray:
    return b * np.power(L, -omega)


def constant_power(L: np.ndarray, limit: float, b: float, omega: float) -> np.ndarray:
    return limit + b * np.power(L, -omega)


def shift_model(L: np.ndarray, pc: float, a: float, inverse_nu: float) -> np.ndarray:
    return pc + a * np.power(L, -inverse_nu)


def shift_fixed_pc(L: np.ndarray, a: float, inverse_nu: float, *, pc: float = 0.5) -> np.ndarray:
    return pc + a * np.power(L, -inverse_nu)


def multistart_curve_fit(
    function: Callable[..., np.ndarray],
    x: Iterable[float],
    y: Iterable[float],
    starts: Iterable[Iterable[float]],
    bounds: tuple[Iterable[float], Iterable[float]],
    *,
    maxfev: int = 100_000,
) -> dict[str, object]:
    """Return the valid bounded least-squares solution with minimum RSS."""

    x_values = np.asarray(tuple(x), dtype=float)
    y_values = np.asarray(tuple(y), dtype=float)
    if x_values.shape != y_values.shape or x_values.ndim != 1 or len(x_values) < 3:
        raise ValueError("x and y must be one-dimensional arrays with at least three values")
    if not np.all(np.isfinite(x_values)) or not np.all(np.isfinite(y_values)):
        raise ValueError("x and y must be finite")
    best: dict[str, object] | None = None
    errors: list[str] = []
    for start in starts:
        try:
            parameters, covariance = curve_fit(
                function, x_values, y_values, p0=tuple(start), bounds=bounds,
                maxfev=maxfev,
            )
            prediction = function(x_values, *parameters)
            if not np.all(np.isfinite(parameters)) or not np.all(np.isfinite(prediction)):
                continue
            rss = float(np.sum((y_values - prediction) ** 2))
            if best is None or rss < float(best["rss"]):
                total = float(np.sum((y_values - y_values.mean()) ** 2))
                standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))
                aicc, bic = information_criteria(rss, len(x_values), len(parameters))
                best = {
                    "parameters": parameters,
                    "covariance": covariance,
                    "standard_errors": standard_errors,
                    "prediction": prediction,
                    "residuals": y_values - prediction,
                    "rss": rss,
                    "r_squared": 1.0 - rss / total if total > 0 else 1.0,
                    "aicc": aicc,
                    "bic": bic,
                    "converged": True,
                }
        except (RuntimeError, ValueError, FloatingPointError) as error:
            errors.append(str(error))
    if best is None:
        raise RuntimeError("nonlinear fit did not converge: " + "; ".join(errors[:3]))
    return best


def fit_power_models(L: Iterable[float], values: Iterable[float]) -> tuple[dict[str, object], dict[str, object]]:
    x = np.asarray(tuple(L), dtype=float)
    y = np.asarray(tuple(values), dtype=float)
    if np.any(y <= 0):
        raise ValueError("power-model observations must be positive")
    scale = float(max(y))
    model_a = multistart_curve_fit(
        pure_power, x, y,
        ((scale, exponent) for exponent in (0.05, 0.2, 0.5, 1.0, 2.0)),
        ((np.finfo(float).eps, np.finfo(float).eps), (np.inf, 10.0)),
    )
    starts = (
        (limit_fraction * float(min(y)), scale, exponent)
        for limit_fraction in (0.0, 0.25, 0.75)
        for exponent in (0.05, 0.2, 0.5, 1.0, 2.0)
    )
    model_b = multistart_curve_fit(
        constant_power, x, y, starts,
        ((0.0, np.finfo(float).eps, np.finfo(float).eps), (np.inf, np.inf, 10.0)),
    )
    return model_a, model_b


def fit_shift(L: Iterable[float], values: Iterable[float], *, fixed_pc: float | None = None) -> dict[str, object]:
    x = np.asarray(tuple(L), dtype=float)
    y = np.asarray(tuple(values), dtype=float)
    amplitude = float(y[0] - y[-1]) or 0.1
    if fixed_pc is not None:
        function = lambda sizes, a, inverse_nu: shift_fixed_pc(sizes, a, inverse_nu, pc=fixed_pc)
        return multistart_curve_fit(
            function, x, y,
            ((amplitude, exponent) for exponent in (0.25, 0.5, 0.75, 1.0, 1.5)),
            ((-10.0, np.finfo(float).eps), (10.0, 10.0)),
        )
    return multistart_curve_fit(
        shift_model, x, y,
        ((pc, amplitude, exponent) for pc in (0.3, 0.5, 0.7) for exponent in (0.25, 0.5, 0.75, 1.0, 1.5)),
        ((0.0, -10.0, np.finfo(float).eps), (1.0, 10.0, 10.0)),
    )
