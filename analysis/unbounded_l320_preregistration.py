"""Freeze L=320 predictions before any L=320 simulation output exists."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from analysis.unbounded_v5 import load_s_peaks


SOURCE = Path("app/out/unbounded-v5")
DEFAULT_OUTPUT = Path("analysis/reference/unbounded_l320_preregistered_predictions.csv")
MODELS = ("zero_power", "finite_power", "zero_log", "finite_log")
TARGET_L = 320


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _predict(model: str, L: float, limit: float, amplitude: float, exponent: float) -> float:
    basis = math.log(L) ** -exponent if "log" in model else L ** -exponent
    return limit + amplitude * basis


def _fit_s_peak(summary: pd.DataFrame, target_L: int = TARGET_L) -> pd.DataFrame:
    data = summary.loc[summary.observable == "S_peak"].sort_values("L")
    x, y = data.L.to_numpy(float), data.value.to_numpy(float)
    rows = []
    for model in MODELS:
        finite = model.startswith("finite")
        use_log = "log" in model

        def function(L, *parameters):
            if finite:
                limit, amplitude, exponent = parameters
            else:
                amplitude, exponent = parameters
                limit = 0.0
            basis = np.log(L) ** -exponent if use_log else L ** -exponent
            return limit + amplitude * basis

        if finite:
            starts = ((20_000.0, -20_000.0, q) for q in (.05, .2, .5, 1.0, 2.0))
            bounds = ((0.0, -1e8, .001), (1e8, 1e8, 10.0 if use_log else 5.0))
        else:
            starts = ((1.0, q) for q in (-3.0, -1.0, -.2, .2, 1.0))
            bounds = ((1e-12, -5.0), (1e8, 5.0))
        best = None
        converged = 0
        for start in starts:
            try:
                params, covariance = curve_fit(function, x, y, p0=start, bounds=bounds, maxfev=50_000)
                residuals = y - function(x, *params)
                candidate = (float(np.sum(residuals ** 2)), params, covariance, residuals)
                converged += 1
                if best is None or candidate[0] < best[0]:
                    best = candidate
            except (RuntimeError, ValueError, FloatingPointError):
                pass
        if best is None:
            raise RuntimeError(f"S_peak preregistration fit failed: {model}")
        rss, params, covariance, residuals = best
        if finite:
            limit, amplitude, exponent = map(float, params)
        else:
            limit, (amplitude, exponent) = 0.0, map(float, params)
        point = _predict(model, target_L, limit, amplitude, exponent)
        residual_rms = float(np.sqrt(np.mean(residuals ** 2)))
        parameter_vector = np.asarray(params, float)
        steps = np.maximum(np.abs(parameter_vector) * 1e-6, 1e-6)
        gradient = []
        for index, step in enumerate(steps):
            upper_parameters = parameter_vector.copy(); upper_parameters[index] += step
            lower_parameters = parameter_vector.copy(); lower_parameters[index] -= step
            gradient.append((float(function(np.asarray([target_L]), *upper_parameters)[0])
                             - float(function(np.asarray([target_L]), *lower_parameters)[0])) / (2 * step))
        prediction_se = float(np.sqrt(max(np.asarray(gradient) @ covariance @ np.asarray(gradient), 0.0)))
        confidence_half = 1.96 * prediction_se
        predictive_half = 1.96 * math.sqrt(prediction_se ** 2 + residual_rms ** 2)
        rows.append({
            "observable": "S_peak", "model": model, "target_L": target_L,
            "prediction": point, "prediction_ci95_low": point - confidence_half,
            "prediction_ci95_high": point + confidence_half,
            "prediction_interval95_low": point - predictive_half,
            "prediction_interval95_high": point + predictive_half,
            "limit": limit, "amplitude": amplitude, "decay_exponent": exponent,
            "residual_rms": residual_rms, "fit_converged": True,
            "fit_failure": "", "boundary_solution": bool(
                (finite and (limit <= 1e-6 or limit >= 1e8 - 1 or exponent <= .00101))
                or (not finite and (exponent <= -4.99999 or exponent >= 4.99999))
            ), "max_parameter_correlation": _max_correlation(covariance),
            "fit_parameter_bounds": json.dumps(bounds),
            "fit_note": "signed-exponent/signed-amplitude extension for increasing S_peak",
        })
    return pd.DataFrame(rows)


def _max_correlation(covariance: np.ndarray) -> float:
    std = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    denominator = np.outer(std, std)
    correlation = np.divide(covariance, denominator, out=np.zeros_like(covariance), where=denominator > 0)
    np.fill_diagonal(correlation, 0.0)
    return float(np.max(np.abs(correlation)))


def generate(
    output: str | Path = DEFAULT_OUTPUT, *, source: str | Path = SOURCE,
    forbid_l320: str | Path = "app/out/unbounded-l320",
) -> pd.DataFrame:
    if Path(forbid_l320).exists():
        raise RuntimeError("L=320 output already exists; preregistration must precede observation")
    source, output = Path(source), Path(output)
    predictions_path = source / "unbounded_predictions.csv"
    fits_path = source / "unbounded_model_fits.csv"
    bootstrap_path = source / "unbounded_bootstrap_samples.csv"
    summary_path = source / "unbounded_size_summary.csv"
    predictions = pd.read_csv(predictions_path)
    fits = pd.read_csv(fits_path)
    selected = predictions.loc[predictions.target_L == TARGET_L].merge(
        fits[["observable", "model", "limit", "amplitude", "decay_exponent",
              "residual_rms", "converged", "failure", "boundary_solution",
              "max_parameter_correlation", "L_min", "L_max", "used_L"]],
        on=["observable", "model"], how="left", validate="one_to_one",
    )
    selected = selected.rename(columns={"converged": "fit_converged", "failure": "fit_failure"})
    half_confidence = (selected.prediction_ci95_high - selected.prediction_ci95_low) / 2
    predictive_half = 1.96 * np.sqrt((half_confidence / 1.96) ** 2 + selected.residual_rms ** 2)
    selected["prediction_interval95_low"] = selected.prediction - predictive_half
    selected["prediction_interval95_high"] = selected.prediction + predictive_half
    selected["fit_parameter_bounds"] = "standard v5 bounds: limit[0,1], amplitude>0, exponent bounded"
    selected["fit_note"] = "unchanged v5 fit; L=320 excluded"
    peaks = _fit_s_peak(pd.read_csv(summary_path))
    peaks["L_min"], peaks["L_max"] = 8, 256
    peaks["used_L"] = "8;12;16;24;32;48;64;96;128;192;256"
    combined = pd.concat([selected, peaks], ignore_index=True, sort=False)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    generated = pd.Timestamp.now(tz="UTC").isoformat()
    combined["largest_observed_L"] = 256
    combined["extrapolation_ratio"] = TARGET_L / 256
    combined["bootstrap_samples"] = np.where(combined.observable == "S_peak", 0, 500)
    combined["bootstrap_seed"] = 20260720
    combined["generation_timestamp_utc"] = generated
    combined["input_predictions_sha256"] = sha256(predictions_path)
    combined["input_fits_sha256"] = sha256(fits_path)
    combined["input_bootstrap_sha256"] = sha256(bootstrap_path)
    combined["input_summary_sha256"] = sha256(summary_path)
    combined["analysis_source_commit"] = commit
    combined["preregistration_status"] = "fixed before L=320 simulation"
    columns = [
        "observable", "model", "target_L", "prediction", "prediction_ci95_low",
        "prediction_ci95_high", "prediction_interval95_low", "prediction_interval95_high",
        "L_min", "L_max", "used_L", "limit", "amplitude", "decay_exponent",
        "residual_rms", "fit_converged", "fit_failure", "boundary_solution",
        "max_parameter_correlation", "fit_parameter_bounds", "fit_note",
        "bootstrap_samples", "bootstrap_seed", "largest_observed_L", "extrapolation_ratio",
        "generation_timestamp_utc", "input_predictions_sha256", "input_fits_sha256",
        "input_bootstrap_sha256", "input_summary_sha256", "analysis_source_commit",
        "preregistration_status",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    combined[columns].sort_values(["observable", "model"]).to_csv(output, index=False)
    return combined[columns].sort_values(["observable", "model"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    frame = generate(args.output)
    print(f"preregistered L=320 predictions: rows={len(frame)} output={args.output}")


if __name__ == "__main__":
    main()
