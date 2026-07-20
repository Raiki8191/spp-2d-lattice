"""Auditable asymptotic model comparison for UNBOUNDED observables."""

from __future__ import annotations

from collections.abc import Iterable
import math

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from analysis.correction_fitting import (
    fit_bounded_multistart,
    logarithmic_limit,
    logarithmic_zero,
)
from analysis.model_fitting import constant_power, pure_power


MODEL_SPECS = {
    "zero_power": (
        pure_power,
        tuple((1.0, q) for q in (0.02, 0.08, 0.2, 0.5, 1.0, 2.0)),
        ((1e-12, 0.001), (10.0, 5.0)),
        ("amplitude", "decay_exponent"),
    ),
    "finite_power": (
        constant_power,
        tuple((limit, 1.0, q) for limit in (0.0, 0.1, 0.3)
              for q in (0.02, 0.08, 0.2, 0.5, 1.0)),
        ((0.0, 1e-12, 0.001), (1.0, 10.0, 5.0)),
        ("limit", "amplitude", "decay_exponent"),
    ),
    "zero_log": (
        logarithmic_zero,
        tuple((1.0, q) for q in (0.05, 0.2, 0.5, 1.0, 2.0, 4.0)),
        ((1e-12, 0.001), (10.0, 10.0)),
        ("amplitude", "decay_exponent"),
    ),
    "finite_log": (
        logarithmic_limit,
        tuple((limit, 1.0, q) for limit in (0.0, 0.1, 0.3)
              for q in (0.05, 0.2, 0.5, 1.0, 2.0)),
        ((0.0, 1e-12, 0.001), (1.0, 10.0, 10.0)),
        ("limit", "amplitude", "decay_exponent"),
    ),
}


def fit_models(
    sizes: Iterable[float], values: Iterable[float], *, observable: str = ""
) -> pd.DataFrame:
    """Fit all four declared models, retaining failures and diagnostics."""

    x, y = np.asarray(tuple(sizes), float), np.asarray(tuple(values), float)
    rows: list[dict[str, object]] = []
    for name, (function, starts, bounds, parameters) in MODEL_SPECS.items():
        fit = fit_bounded_multistart(
            function, x, y, starts, bounds, parameters, model=name, maxfev=20_000
        )
        fit["observable"] = observable
        fit["L_min"] = int(np.min(x)) if len(x) else np.nan
        fit["L_max"] = int(np.max(x)) if len(x) else np.nan
        fit["used_L"] = ";".join(str(int(value)) for value in x)
        fit["limit"] = float(fit.get("limit", 0.0))
        fit["limit_standard_error"] = float(
            fit.get("limit_standard_error", 0.0 if name.startswith("zero") else np.nan)
        )
        fit["residual_rms"] = (
            float(np.sqrt(np.mean(np.square(fit["residuals"]))))
            if fit.get("converged") else np.nan
        )
        rows.append(_serializable(fit))
    return pd.DataFrame(rows)


def leave_one_size_out(summary: pd.DataFrame, value_column: str, observable: str) -> pd.DataFrame:
    """Refit after omitting each L and report the held-out prediction error."""

    rows: list[dict[str, object]] = []
    ordered = summary.sort_values("L")
    for omitted in ordered["L"]:
        training = ordered.loc[ordered["L"] != omitted]
        observed = float(ordered.loc[ordered["L"] == omitted, value_column].iloc[0])
        fits = fit_models(training["L"], training[value_column], observable=observable)
        for fit in fits.to_dict("records"):
            prediction = predict(fit, float(omitted)) if fit["converged"] else np.nan
            rows.append({
                **fit,
                "omitted_L": int(omitted),
                "observed": observed,
                "predicted": prediction,
                "prediction_error": prediction - observed,
                "absolute_prediction_error": abs(prediction - observed),
            })
    return pd.DataFrame(rows)


def bootstrap_models(
    run_data: pd.DataFrame,
    *, value_column: str,
    aggregation: str,
    observable: str,
    samples: int,
    seed: int,
) -> pd.DataFrame:
    """Run-stratified bootstrap; each L is resampled at its own run count."""

    if aggregation not in {"mean", "std"}:
        raise ValueError("aggregation must be mean or std")
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    groups = [(int(L), group[value_column].dropna().to_numpy(float))
              for L, group in run_data.groupby("L", sort=True)]
    for sample in range(samples):
        points = []
        for L, values in groups:
            draw = values[rng.integers(0, len(values), len(values))]
            estimate = float(np.mean(draw) if aggregation == "mean" else np.std(draw, ddof=1))
            points.append((L, estimate))
        sizes, values = map(np.asarray, zip(*points))
        for fit in _quick_models(sizes, values):
            rows.append({
                "sample": sample,
                "observable": observable,
                "model": fit["model"],
                "converged": fit["converged"],
                "boundary_solution": fit["boundary_solution"],
                "covariance_ok": fit["covariance_ok"],
                "limit": fit.get("limit", np.nan),
                "amplitude": fit.get("amplitude", np.nan),
                "decay_exponent": fit.get("decay_exponent", np.nan),
            })
    return pd.DataFrame(rows)


def _quick_models(sizes: np.ndarray, values: np.ndarray) -> list[dict[str, object]]:
    """Fast bootstrap fits; full reported fits still use bounded multi-start."""

    log_slope, log_amplitude = np.polyfit(np.log(sizes), np.log(values), 1)
    loglog_slope, loglog_amplitude = np.polyfit(np.log(np.log(sizes)), np.log(values), 1)
    rows = [
        {"model": "zero_power", "converged": True, "boundary_solution": False,
         "covariance_ok": True, "limit": 0.0, "amplitude": math.exp(log_amplitude),
         "decay_exponent": -float(log_slope)},
        {"model": "zero_log", "converged": True, "boundary_solution": False,
         "covariance_ok": True, "limit": 0.0, "amplitude": math.exp(loglog_amplitude),
         "decay_exponent": -float(loglog_slope)},
    ]
    for model, basis, upper in (
        ("finite_power", lambda q: sizes ** -q, 5.0),
        ("finite_log", lambda q: np.log(sizes) ** -q, 10.0),
    ):
        def solve(q: float) -> tuple[float, np.ndarray]:
            design = np.column_stack((np.ones(len(sizes)), basis(q)))
            coefficients = np.linalg.lstsq(design, values, rcond=None)[0]
            penalty = 1e8 * min(float(coefficients[0]), 0.0) ** 2
            return float(np.sum((values - design @ coefficients) ** 2) + penalty), coefficients
        optimized = minimize_scalar(lambda q: solve(q)[0], bounds=(.001, upper), method="bounded")
        _, coefficients = solve(float(optimized.x))
        limit = max(float(coefficients[0]), 0.0)
        rows.append({
            "model": model, "converged": bool(optimized.success),
            "boundary_solution": bool(limit <= 1e-10 or optimized.x <= .00101
                                      or optimized.x >= upper - 1e-5),
            "covariance_ok": True, "limit": limit,
            "amplitude": float(coefficients[1]), "decay_exponent": float(optimized.x),
        })
    return rows


def summarize_bootstrap(bootstrap: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (observable, model), group in bootstrap.groupby(["observable", "model"], sort=True):
        converged = group.loc[group["converged"]]
        for parameter in ("limit", "decay_exponent"):
            values = converged[parameter].dropna().to_numpy(float)
            if not len(values):
                continue
            rows.append({
                "observable": observable,
                "model": model,
                "parameter": parameter,
                "sample_count": len(group),
                "converged_count": len(converged),
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
                "ci95_low": float(np.percentile(values, 2.5)),
                "ci95_high": float(np.percentile(values, 97.5)),
                "zero_in_ci95": bool(
                    float(np.percentile(values, 2.5)) <= 0.0
                    <= float(np.percentile(values, 97.5))
                ),
                "boundary_frequency": float(group["boundary_solution"].mean()),
                "fit_failure_frequency": float((~group["converged"]).mean()),
                "covariance_failure_frequency": float((~group["covariance_ok"]).mean()),
            })
    return pd.DataFrame(rows)


def prediction_table(fits: pd.DataFrame, bootstrap: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for fit in fits.to_dict("records"):
        for target in (192, 256, 384, 512):
            value = predict(fit, target) if fit["converged"] else np.nan
            boot = bootstrap.loc[
                (bootstrap["observable"] == fit["observable"])
                & (bootstrap["model"] == fit["model"])
                & bootstrap["converged"]
            ]
            samples = np.array([predict(row, target) for row in boot.to_dict("records")], float)
            samples = samples[np.isfinite(samples)]
            low, high = (np.percentile(samples, [2.5, 97.5])
                         if len(samples) else (np.nan, np.nan))
            rows.append({
                "observable": fit["observable"],
                "model": fit["model"],
                "target_L": target,
                "prediction": value,
                "prediction_ci95_low": low,
                "prediction_ci95_high": high,
                "largest_observed_L": int(fit["L_max"]),
                "extrapolation_ratio": target / float(fit["L_max"]),
                "warning": "model extrapolation, not an observation",
            })
    return pd.DataFrame(rows)


def predict(fit: dict[str, object] | pd.Series, size: float) -> float:
    model = str(fit["model"])
    amplitude = float(fit["amplitude"])
    exponent = float(fit["decay_exponent"])
    limit = float(fit.get("limit", 0.0))
    decaying = math.log(size) ** -exponent if "log" in model else size ** -exponent
    return limit + amplitude * decaying


def _serializable(fit: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in fit.items()
            if key not in {"residuals", "prediction", "covariance"}}
