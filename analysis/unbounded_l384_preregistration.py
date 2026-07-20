"""Freeze v6-only L=384 predictions before any L=384 simulation exists."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd

from analysis.unbounded_l320_preregistration import _fit_s_peak, sha256
from analysis.unbounded_model_comparison import predict


SOURCE = Path("app/out/unbounded-v6")
DEFAULT_OUTPUT = Path("analysis/reference/unbounded_l384_preregistered_predictions.csv")
TARGET_L = 384
MODELS = ("zero_power", "finite_power", "zero_log", "finite_log")
INPUT_MANIFESTS = (
    "app/out/scaling-v1/manifest.csv",
    "app/out/scaling-v2-main/manifest.csv",
    "app/out/unbounded-l192/benchmark/manifest.csv",
    "app/out/unbounded-l192/pilot/manifest.csv",
    "app/out/unbounded-l192/main/manifest.csv",
    "app/out/unbounded-l256/benchmark/manifest.csv",
    "app/out/unbounded-l256/pilot/manifest.csv",
    "app/out/unbounded-l320/benchmark/manifest.csv",
    "app/out/unbounded-l320/pilot/manifest.csv",
)


def _bootstrap_prediction(row: pd.Series, target_L: int) -> float:
    return predict(row.to_dict(), target_L)


def generate(
    output: str | Path = DEFAULT_OUTPUT, *, source: str | Path = SOURCE,
    forbid_l384: str | Path = "app/out/unbounded-l384",
) -> pd.DataFrame:
    """Generate an immutable preregistration table without reading L=384 data."""

    if Path(forbid_l384).exists():
        raise RuntimeError("L=384 output already exists; preregistration must precede observation")
    source, output = Path(source), Path(output)
    paths = {
        "predictions": source / "unbounded_predictions.csv",
        "fits": source / "unbounded_model_fits.csv",
        "bootstrap": source / "unbounded_bootstrap_samples.csv",
        "summary": source / "unbounded_size_summary.csv",
    }
    for label, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"missing v6 {label}: {path}")
    predictions = pd.read_csv(paths["predictions"])
    fits = pd.read_csv(paths["fits"])
    bootstrap = pd.read_csv(paths["bootstrap"])
    summary = pd.read_csv(paths["summary"])
    selected = predictions.loc[
        (predictions.target_L == TARGET_L) & predictions.model.isin(MODELS)
    ].copy()
    selected = selected.merge(
        fits[["observable", "model", "limit", "amplitude", "decay_exponent",
              "residual_rms", "converged", "failure", "boundary_solution",
              "max_parameter_correlation", "L_min", "L_max", "used_L"]],
        on=["observable", "model"], validate="one_to_one",
    ).rename(columns={"converged": "fit_converged", "failure": "fit_failure"})
    bootstrap_rows = []
    for (observable, model), group in bootstrap.groupby(["observable", "model"], sort=True):
        valid = group.loc[group.converged].copy()
        values = valid.apply(_bootstrap_prediction, axis=1, target_L=TARGET_L).to_numpy(float)
        bootstrap_rows.append({
            "observable": observable, "model": model,
            "bootstrap_median": float(np.median(values)),
            "bootstrap_samples": len(group),
            "fit_failure_rate": float((~group.converged).mean()),
            "boundary_rate": float(group.boundary_solution.mean()),
            "covariance_failure_rate": float((~group.covariance_ok).mean()),
        })
    selected = selected.merge(pd.DataFrame(bootstrap_rows), on=["observable", "model"],
                              validate="one_to_one")
    half_confidence = (selected.prediction_ci95_high - selected.prediction_ci95_low) / 2
    predictive_half = 1.96 * np.sqrt((half_confidence / 1.96) ** 2 + selected.residual_rms ** 2)
    selected["prediction_interval95_low"] = selected.prediction - predictive_half
    selected["prediction_interval95_high"] = selected.prediction + predictive_half
    selected["fit_parameter_bounds"] = "limit[0,1], amplitude[1e-12,10], power exponent[0.001,5], log exponent[0.001,10]"
    selected["fit_note"] = "unchanged v6 fit; L=384 excluded"

    peaks = _fit_s_peak(summary, TARGET_L)
    peaks["bootstrap_median"] = peaks.prediction
    peaks["bootstrap_samples"] = 0
    peaks["fit_failure_rate"] = 0.0
    peaks["boundary_rate"] = peaks.boundary_solution.astype(float)
    peaks["covariance_failure_rate"] = 0.0
    peaks["L_min"], peaks["L_max"] = 8, 320
    peaks["used_L"] = "8;12;16;24;32;48;64;96;128;192;256;320"
    combined = pd.concat([selected, peaks], ignore_index=True, sort=False)

    run_counts = summary.drop_duplicates(["L"])[["L", "run_count"]]
    combined["used_run_counts"] = ";".join(
        f"{int(row.L)}:{int(row.run_count)}" for row in run_counts.sort_values("L").itertuples())
    manifest_hashes = {path: sha256(Path(path)) for path in INPUT_MANIFESTS}
    input_hashes = {str(path): sha256(path) for path in paths.values()}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    generated = subprocess.check_output(
        ["git", "show", "-s", "--format=%cI", "HEAD"], text=True).strip()
    combined["largest_observed_L"] = 320
    combined["extrapolation_ratio"] = TARGET_L / 320
    combined["bootstrap_seed"] = 20260720
    combined["generation_timestamp_utc"] = generated
    combined["input_manifests"] = json.dumps(INPUT_MANIFESTS)
    combined["input_manifest_sha256"] = json.dumps(manifest_hashes, sort_keys=True)
    combined["input_file_sha256"] = json.dumps(input_hashes, sort_keys=True)
    combined["analysis_source_commit"] = commit
    combined["preregistration_status"] = "fixed before L=384 simulation"
    columns = [
        "observable", "model", "target_L", "prediction", "bootstrap_median",
        "prediction_ci95_low", "prediction_ci95_high", "prediction_interval95_low",
        "prediction_interval95_high", "L_min", "L_max", "used_L", "used_run_counts",
        "limit", "amplitude", "decay_exponent", "residual_rms", "fit_converged",
        "fit_failure", "fit_failure_rate", "boundary_solution", "boundary_rate",
        "covariance_failure_rate", "max_parameter_correlation", "fit_parameter_bounds",
        "fit_note", "bootstrap_samples", "bootstrap_seed", "largest_observed_L",
        "extrapolation_ratio", "generation_timestamp_utc", "input_manifests",
        "input_manifest_sha256", "input_file_sha256", "analysis_source_commit",
        "preregistration_status",
    ]
    result = combined[columns].sort_values(["observable", "model"]).reset_index(drop=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    frame = generate(args.output)
    print(f"preregistered L=384 predictions: rows={len(frame)} output={args.output}")


if __name__ == "__main__":
    main()
