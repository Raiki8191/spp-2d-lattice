"""Bounded, multi-start finite-size fits with explicit diagnostics.

The functions in this module deliberately return failed/under-determined fits as
records.  This keeps numerical instability visible in the research products.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
import math

import numpy as np
from scipy.optimize import curve_fit

from analysis.model_fitting import information_criteria


OMEGA_FIXED_VALUES = (0.5, 0.75, 1.0, 1.5, 2.0)


def simple_power(L: np.ndarray, amplitude: float, exponent: float) -> np.ndarray:
    return amplitude * np.power(L, exponent)


def corrected_power(
    L: np.ndarray, amplitude: float, exponent: float, correction: float, omega: float
) -> np.ndarray:
    return amplitude * np.power(L, exponent) * (1.0 + correction * np.power(L, -omega))


def corrected_power_fixed_omega(
    L: np.ndarray,
    amplitude: float,
    exponent: float,
    correction: float,
    *,
    omega: float,
) -> np.ndarray:
    return corrected_power(L, amplitude, exponent, correction, omega)


def corrected_shift(
    L: np.ndarray,
    pc: float,
    amplitude: float,
    inverse_nu: float,
    correction: float,
    omega: float,
) -> np.ndarray:
    return pc + amplitude * np.power(L, -inverse_nu) * (
        1.0 + correction * np.power(L, -omega)
    )


def corrected_shift_fixed_pc(
    L: np.ndarray,
    amplitude: float,
    inverse_nu: float,
    correction: float,
    omega: float,
    *,
    pc: float,
) -> np.ndarray:
    return corrected_shift(L, pc, amplitude, inverse_nu, correction, omega)


def logarithmic_zero(L: np.ndarray, amplitude: float, exponent: float) -> np.ndarray:
    return amplitude * np.power(np.log(L), -exponent)


def logarithmic_limit(
    L: np.ndarray, limit: float, amplitude: float, exponent: float
) -> np.ndarray:
    return limit + logarithmic_zero(L, amplitude, exponent)


def fit_bounded_multistart(
    function: Callable[..., np.ndarray],
    L: Iterable[float],
    values: Iterable[float],
    starts: Iterable[Iterable[float]],
    bounds: tuple[Iterable[float], Iterable[float]],
    parameter_names: Iterable[str],
    *,
    model: str,
    maxfev: int = 5_000,
) -> dict[str, object]:
    """Fit all starts and retain the lowest RSS, with auditable diagnostics."""

    x = np.asarray(tuple(L), dtype=float)
    y = np.asarray(tuple(values), dtype=float)
    names = tuple(parameter_names)
    lower = np.asarray(tuple(bounds[0]), dtype=float)
    upper = np.asarray(tuple(bounds[1]), dtype=float)
    starts = tuple(tuple(start) for start in starts)
    base = {
        "model": model,
        "point_count": len(x),
        "parameter_count": len(names),
        "converged": False,
        "admissible": False,
        "boundary_solution": False,
        "covariance_ok": False,
        "start_count": len(starts),
        "converged_start_count": 0,
        "failure": "",
    }
    if x.ndim != 1 or x.shape != y.shape or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        return {**base, "failure": "non-finite or mismatched one-dimensional input"}
    if len(x) <= len(names) + 1:
        return {**base, "failure": "insufficient points for finite AICc"}
    if np.any(y <= 0) and "shift" not in model:
        return {**base, "failure": "non-positive observation"}

    solutions: list[tuple[float, np.ndarray, np.ndarray, np.ndarray]] = []
    errors: list[str] = []
    for start in starts:
        try:
            parameters, covariance = curve_fit(
                function, x, y, p0=start, bounds=(lower, upper), maxfev=maxfev
            )
            prediction = function(x, *parameters)
            if not np.all(np.isfinite(parameters)) or not np.all(np.isfinite(prediction)):
                continue
            if "shift" not in model and np.any(prediction <= 0):
                continue
            solutions.append((float(np.sum((y - prediction) ** 2)), parameters, covariance, prediction))
        except (RuntimeError, ValueError, FloatingPointError) as error:
            errors.append(str(error))
    if not solutions:
        return {**base, "failure": "; ".join(errors[:3]) or "all starts invalid"}

    rss, parameters, covariance, prediction = min(solutions, key=lambda item: item[0])
    finite_lower = np.isfinite(lower)
    finite_upper = np.isfinite(upper)
    lower_scale = np.maximum(np.where(finite_upper, upper-lower, np.maximum(np.abs(lower), 1.0)), 1.0)
    upper_scale = np.maximum(np.where(finite_lower, upper-lower, np.maximum(np.abs(upper), 1.0)), 1.0)
    boundary = bool(
        np.any(finite_lower & ((parameters-lower) <= 1.0e-8*lower_scale))
        or np.any(finite_upper & ((upper-parameters) <= 1.0e-8*upper_scale))
    )
    covariance_ok = bool(np.all(np.isfinite(covariance)) and np.all(np.diag(covariance) >= 0))
    aicc, bic = information_criteria(rss, len(x), len(names))
    result: dict[str, object] = {
        **base,
        "converged": True,
        "admissible": not boundary and covariance_ok and math.isfinite(aicc),
        "boundary_solution": boundary,
        "covariance_ok": covariance_ok,
        "converged_start_count": len(solutions),
        "rss": rss,
        "aicc": aicc,
        "bic": bic,
        "residuals": y - prediction,
        "prediction": prediction,
        "covariance": covariance,
        "max_parameter_correlation": _max_correlation(covariance),
    }
    errors_std = np.sqrt(np.maximum(np.diag(covariance), 0.0)) if covariance_ok else np.full(len(names), np.nan)
    for name, value, error in zip(names, parameters, errors_std):
        result[name] = float(value)
        result[f"{name}_standard_error"] = float(error)
    return result


def power_model_fits(
    L: Iterable[float], values: Iterable[float], *, fixed_exponent: float | None = None,
    fixed_omegas: Iterable[float] = OMEGA_FIXED_VALUES, include_free_omega: bool = True,
) -> list[dict[str, object]]:
    x = np.asarray(tuple(L), float)
    y = np.asarray(tuple(values), float)
    amplitude = float(np.median(y / np.power(x, fixed_exponent))) if fixed_exponent is not None else float(y[0])
    fits: list[dict[str, object]] = []
    if fixed_exponent is None:
        fits.append(fit_bounded_multistart(
            simple_power, x, y,
            ((max(amplitude, 1e-9), exponent) for exponent in (-1, -0.2, 0.2, 1)),
            ((1e-12, -5.0), (1e6, 5.0)), ("amplitude", "exponent"), model="simple_power",
        ))
    else:
        function = lambda size, a: simple_power(size, a, fixed_exponent)
        fit = fit_bounded_multistart(function, x, y, ((max(amplitude, 1e-9),),),
                                     ((1e-12,), (1e6,)), ("amplitude",), model="simple_power_fixed_exponent")
        fit["exponent"] = fixed_exponent
        fits.append(fit)

    for omega in fixed_omegas:
        if fixed_exponent is None:
            function = lambda size, a, exponent, b, w=omega: corrected_power(size, a, exponent, b, w)
            names = ("amplitude", "exponent", "correction")
            starts = ((max(amplitude, 1e-9), exponent, b) for exponent in (-0.2, 1) for b in (-1, 1))
            bounds = ((1e-12, -5.0, -20.0), (1e6, 5.0, 20.0))
        else:
            function = lambda size, a, b, w=omega: corrected_power(size, a, fixed_exponent, b, w)
            names = ("amplitude", "correction")
            starts = ((max(amplitude, 1e-9), b) for b in (-1, 1))
            bounds = ((1e-12, -20.0), (1e6, 20.0))
        fit = fit_bounded_multistart(function, x, y, starts, bounds, names, model=f"corrected_power_omega_{omega:g}")
        fit.update(omega=omega, exponent=fixed_exponent if fixed_exponent is not None else fit.get("exponent", np.nan))
        fits.append(fit)

    if fixed_exponent is None and include_free_omega:
        fit = fit_bounded_multistart(
            corrected_power, x, y,
            ((max(amplitude, 1e-9), exponent, b, omega) for exponent in (-0.2, 1)
             for b in (-1, 1) for omega in (0.5, 1.5)),
            ((1e-12, -5.0, -20.0, 0.05), (1e6, 5.0, 20.0, 4.0)),
            ("amplitude", "exponent", "correction", "omega"), model="corrected_power_free_omega",
        )
        fits.append(fit)
    return fits


def _max_correlation(covariance: np.ndarray) -> float:
    if covariance.ndim != 2 or not np.all(np.isfinite(covariance)):
        return math.nan
    standard = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    denominator = np.outer(standard, standard)
    correlation = np.divide(covariance, denominator, out=np.zeros_like(covariance), where=denominator > 0)
    np.fill_diagonal(correlation, 0.0)
    return float(np.max(np.abs(correlation)))
