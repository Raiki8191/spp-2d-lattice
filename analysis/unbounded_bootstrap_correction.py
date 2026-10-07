"""Generate separate, retrospective UNBOUNDED bootstrap correction products.

Uses existing request/run-level inputs and the production ``bootstrap_models``
estimator.  Historical outputs and fixed preregistration files are read-only.
The output directory must not exist, so a completed analysis cannot be replaced.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import scipy

from analysis.io import read_manifest
from analysis.unbounded_model_comparison import (
    MODEL_SPECS, bootstrap_models, fit_models, prediction_table,
    summarize_bootstrap,
)
from analysis.unbounded_v4 import OBSERVABLES, load_all_run_metrics, load_stage_runs
from analysis.unbounded_v5 import MODEL_OBSERVABLES


VERSIONS = {"v4": 192, "v5": 256, "v6": 320, "v7": 384}
PREREGISTRATION_FILES = (
    Path("docs/UNBOUNDED_L320_PREREGISTRATION.md"),
    Path("docs/UNBOUNDED_L384_PREREGISTRATION.md"),
    Path("analysis/reference/unbounded_l320_preregistered_predictions.csv"),
    Path("analysis/reference/unbounded_l384_preregistered_predictions.csv"),
)
LIMITATIONS = (
    "Retrospective correction, not a new preregistration or simulation.",
    "Resampling is stratified by L at the existing run count, independently across sizes.",
    "Intervals do not include model-form, size-selection, finite-size systematic, "
    "or cross-size common-seed covariance uncertainty.",
    "Finite-limit boundary concentration is not a proof of a zero asymptote.",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def historical_output(version: str) -> Path:
    if version not in VERSIONS:
        raise ValueError(f"unknown version: {version}")
    return Path("app/out/unbounded-v4/main50" if version == "v4"
                else f"app/out/unbounded-{version}")


def stage_manifests(size: int) -> list[Path]:
    stages = ("benchmark", "pilot", "main") if size == 192 else ("benchmark", "pilot")
    return [Path(f"app/out/unbounded-l{size}/{stage}/manifest.csv") for stage in stages]


def load_run_metrics(version: str) -> tuple[pd.DataFrame, pd.DataFrame, list[Path]]:
    """Follow the original loader chain without the unused S_peak scans."""

    largest = VERSIONS[version]
    manifests = stage_manifests(192)
    events, widths = load_all_run_metrics(manifests)
    for size in (256, 320, 384):
        if size > largest:
            break
        paths = stage_manifests(size)
        _, extra_events, extra_widths = load_stage_runs(paths)
        events = pd.concat([events, extra_events], ignore_index=True, sort=False)
        widths = pd.concat([widths, extra_widths], ignore_index=True, sort=False)
        manifests.extend(paths)
    return events, widths, manifests


def observable_definitions(version: str) -> dict[str, tuple[str, str]]:
    return OBSERVABLES if version == "v4" else MODEL_OBSERVABLES


def source_for(observable: str, events: pd.DataFrame, widths: pd.DataFrame) -> pd.DataFrame:
    return widths if observable.startswith("transition_") else events


def summarize_run_metrics(
    version: str, events: pd.DataFrame, widths: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for observable, (column, aggregation) in observable_definitions(version).items():
        data = source_for(observable, events, widths)
        for size, group in data.groupby("L", sort=True):
            values = group[column].dropna().to_numpy(float)
            rows.append({
                "observable": observable, "L": int(size), "run_count": len(values),
                "value": float(np.mean(values) if aggregation == "mean"
                               else np.std(values, ddof=1)),
                "sample_std": float(np.std(values, ddof=1)),
                "sample_sem": float(np.std(values, ddof=1) / np.sqrt(len(values))),
            })
    return pd.DataFrame(rows)


def validate_summary(summary: pd.DataFrame, historical: pd.DataFrame) -> pd.DataFrame:
    compared = summary.merge(historical, on=["observable", "L"],
                             suffixes=("_corrected", "_historical"), validate="one_to_one")
    if len(compared) != len(summary):
        raise ValueError("historical summary is missing an observable/size")
    if not (compared.run_count_corrected == compared.run_count_historical).all():
        raise ValueError("historical and corrected run counts differ")
    compared["value_difference"] = compared.value_corrected - compared.value_historical
    if not np.allclose(compared.value_corrected, compared.value_historical, rtol=0, atol=1e-12):
        raise ValueError("historical and freshly loaded run-level summaries differ")
    return compared


def input_paths(manifests: list[Path], old: Path) -> list[Path]:
    paths = set(manifests)
    paths.update(PREREGISTRATION_FILES)
    paths.update(Path("app/out/scaling-v2-analysis") / name for name in (
        "request_event_runs.csv", "transition_width_runs.csv"))
    # These raw inputs produced the cached older run-level metrics.
    parent_manifests = [Path("app/out/scaling-v1/manifest.csv"),
                        Path("app/out/scaling-v2-main/manifest.csv")]
    paths.update(parent_manifests)
    for path in [*parent_manifests, *manifests]:
        frame = read_manifest(path)
        for row in frame.loc[frame.budget_mode == "UNBOUNDED"].itertuples(index=False):
            paths.add(Path(row.result_path))
        for name in ("run_metadata.csv", "run_summary.csv"):
            candidate = path.parent / name
            if candidate.is_file():
                paths.add(candidate)
    paths.update(old / name for name in (
        "unbounded_size_summary.csv", "unbounded_model_fits.csv",
        "unbounded_bootstrap_samples.csv", "unbounded_bootstrap_intervals.csv",
        "unbounded_predictions.csv"))
    return sorted(paths)


def retrospective_sources(version: str) -> tuple[int, Path, Path] | None:
    mapping = {
        "v4": (256, Path("app/out/unbounded-v4/main50/unbounded_predictions.csv"),
               Path("app/out/unbounded-v5/l256_observations.csv")),
        "v5": (320, PREREGISTRATION_FILES[2], Path("app/out/unbounded-v6/l320_observations.csv")),
        "v6": (384, PREREGISTRATION_FILES[3], Path("app/out/unbounded-v7/l384_observations.csv")),
    }
    return mapping.get(version)


def retrospective_scores(version: str, predictions: pd.DataFrame, fits: pd.DataFrame) -> pd.DataFrame:
    """Keep frozen point predictions and the original CI/PI construction."""

    sources = retrospective_sources(version)
    if sources is None:
        return pd.DataFrame()
    target, frozen_path, observation_path = sources
    frozen = pd.read_csv(frozen_path, float_precision="round_trip")
    observed = pd.read_csv(observation_path, float_precision="round_trip")
    if "estimate" not in observed:
        observed = observed.rename(columns={"mean_or_estimate": "estimate"})
    frozen = frozen.loc[frozen.target_L == target]
    corrected = predictions.loc[predictions.target_L == target]
    joined = corrected.merge(frozen, on=["observable", "model", "target_L"],
                             suffixes=("_corrected", "_frozen"), validate="one_to_one")
    rows = []
    for item in joined.to_dict("records"):
        observation = observed.loc[observed.observable == item["observable"]].iloc[0]
        point = item["prediction_frozen"]
        if not np.isclose(point, item["prediction_corrected"], rtol=1e-8, atol=1e-8):
            raise ValueError("retrospective correction unexpectedly changed a fixed point prediction")
        low, high = item["prediction_ci95_low_corrected"], item["prediction_ci95_high_corrected"]
        if version == "v4":
            old_low, old_high = item["prediction_ci95_low_frozen"], item["prediction_ci95_high_frozen"]
            interval_kind = "bootstrap confidence interval; historical v4 construction"
        else:
            fit = fits.loc[(fits.observable == item["observable"]) & (fits.model == item["model"])].iloc[0]
            half = 1.96 * np.sqrt((((high - low) / 2) / 1.96) ** 2 + fit.residual_rms ** 2)
            low, high = point - half, point + half
            old_low, old_high = item["prediction_interval95_low"], item["prediction_interval95_high"]
            interval_kind = "predictive interval: 1.96*sqrt((bootstrap_half/1.96)^2+residual_rms^2)"
        error = point - float(observation.estimate)
        sigma = max((high - low) / 3.92, np.finfo(float).tiny)
        old_sigma = max((old_high - old_low) / 3.92, np.finfo(float).tiny)
        log_density = -.5 * (error / sigma) ** 2 - np.log(sigma * np.sqrt(2 * np.pi))
        old_log_density = -.5 * (error / old_sigma) ** 2 - np.log(old_sigma * np.sqrt(2 * np.pi))
        rows.append({
            "source_version": version, "target_L": target, "observable": item["observable"],
            "model": item["model"], "fixed_point_prediction": point,
            "observed_estimate": float(observation.estimate), "point_prediction_error": error,
            "absolute_point_prediction_error": abs(error), "interval_kind": interval_kind,
            "historical_interval_low": old_low, "historical_interval_high": old_high,
            "corrected_interval_low": low, "corrected_interval_high": high,
            "historical_covers_observation": bool(old_low <= observation.estimate <= old_high),
            "corrected_covers_observation": bool(low <= observation.estimate <= high),
            "historical_gaussian_log_density": float(old_log_density),
            "corrected_gaussian_log_density": float(log_density),
            "frozen_prediction_source": str(frozen_path), "observation_source": str(observation_path),
            "analysis_status": "retrospective correction; fixed preregistration files are unchanged",
            "calibration_note": "v4 CI and v5/v6 PI differ; pooled coverage is not a common 95% calibration test",
        })
    return pd.DataFrame(rows)


def _bootstrap_task(arguments: tuple) -> pd.DataFrame:
    observable, column, aggregation, data, samples, seed = arguments
    begin = time.perf_counter()
    result = bootstrap_models(data, value_column=column, aggregation=aggregation,
                              observable=observable, samples=samples, seed=seed)
    print(f"completed {observable}: {samples} draws, "
          f"{time.perf_counter() - begin:.1f} seconds", flush=True)
    return result


def interval_comparison(old: pd.DataFrame, corrected: pd.DataFrame) -> pd.DataFrame:
    keys = ["observable", "model", "parameter"]
    columns = [*keys, "median", "ci95_low", "ci95_high"]
    return old[columns].merge(corrected[columns], on=keys, how="outer",
                              suffixes=("_historical", "_corrected"), validate="one_to_one")


def correction_figures(
    fits: pd.DataFrame, bootstrap: pd.DataFrame, intervals: pd.DataFrame,
    predictions: pd.DataFrame, output: Path,
) -> list[Path]:
    """Plot corrected intervals only; keep every historical figure untouched."""

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output.mkdir(exist_ok=False)
    paths = []
    figure, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for axis, observable in zip(axes, ("maximum_request_jump", "transition_delta_p")):
        selected = bootstrap.loc[(bootstrap.observable == observable) & bootstrap.converged]
        for model in ("finite_power", "finite_log"):
            values = np.sort(selected.loc[selected.model == model, "limit"].dropna())
            if len(values):
                axis.step(values, np.arange(1, len(values) + 1) / len(values),
                          where="post", label=model)
        axis.set(xlabel="finite asymptote", ylabel="bootstrap empirical CDF", title=observable)
        axis.legend(fontsize=8)
    path = output / "corrected_finite_limit_distributions.png"
    figure.savefig(path, dpi=160)
    plt.close(figure)
    paths.append(path)

    selected = intervals.loc[intervals.parameter == "decay_exponent"].copy()
    selected = selected.merge(fits[["observable", "model", "decay_exponent"]],
                              on=["observable", "model"], validate="one_to_one")
    figure, axis = plt.subplots(figsize=(10, max(4, len(selected) * .25)), constrained_layout=True)
    positions = np.arange(len(selected))
    axis.errorbar(selected["median"], positions,
                  xerr=np.vstack([selected["median"] - selected.ci95_low,
                                  selected.ci95_high - selected["median"]]),
                  fmt="o", markersize=3, label="bootstrap median and 95% interval")
    axis.scatter(selected.decay_exponent, positions, marker="x", color="black",
                 label="primary point fit")
    axis.set(yticks=positions,
             yticklabels=[f"{row.observable}: {row.model}" for row in selected.itertuples()],
             xlabel="decay exponent", title="Corrected bootstrap exponent intervals")
    axis.tick_params(axis="y", labelsize=7)
    axis.legend(fontsize=8)
    path = output / "corrected_exponent_intervals.png"
    figure.savefig(path, dpi=160)
    plt.close(figure)
    paths.append(path)

    figure, axis = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    for model, group in predictions.loc[predictions.observable == "maximum_request_jump"].groupby("model"):
        group = group.sort_values("target_L")
        axis.plot(group.target_L, group.prediction, marker="o", label=model)
        axis.fill_between(group.target_L, group.prediction_ci95_low,
                          group.prediction_ci95_high, alpha=.15)
    axis.set(xlabel="target L", ylabel="maximum request jump", xscale="log",
             title="Retrospectively corrected model predictions and 95% bootstrap intervals")
    axis.legend(fontsize=8)
    path = output / "retrospective_corrected_predictions.png"
    figure.savefig(path, dpi=160)
    plt.close(figure)
    paths.append(path)
    return paths


def run_v3_correction(
    output: str | Path | None = None, *, samples: int = 500, seed: int = 20260720,
) -> list[Path]:
    """Recalculate only historical v3 UNBOUNDED products, preserving RNG draws."""

    from analysis import scaling_v3 as v3

    if samples < 1:
        raise ValueError("samples must be positive")
    output = Path(output or "app/out/scaling-v3-unbounded-bootstrap-corrected")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    begin = time.perf_counter()
    source = Path("app/out/scaling-v2-analysis")
    old = Path("app/out/scaling-v3-analysis")
    inputs = [source / name for name in ("request_event_summary.csv", "transition_width_summary.csv",
                                        "request_event_runs.csv", "transition_width_runs.csv")]
    inputs.extend(PREREGISTRATION_FILES)
    hashes = {str(path): sha256(path) for path in inputs}
    # Preserve the historical parser and all finite-condition rows: their draws
    # precede UNBOUNDED draws in the original RNG stream.
    request = pd.read_csv(source / "request_event_summary.csv")
    transition = pd.read_csv(source / "transition_width_summary.csv")
    events = pd.read_csv(source / "request_event_runs.csv")
    widths = pd.read_csv(source / "transition_width_runs.csv")
    combined = request.merge(transition[["condition_index", "delta_p_mean", "delta_t_normalized_mean"]],
                             on="condition_index", validate="one_to_one")
    combined["condition_label"] = combined.apply(
        lambda row: "UNBOUNDED" if row.budget_mode == "UNBOUNDED" else f"C={int(row.C)}", axis=1)
    fits, loo, point_predictions = v3.unbounded_fits(combined)
    old_fits = pd.read_csv(old / "unbounded_asymptotic_fits.csv")
    comparison = fits.merge(old_fits, on=["observable", "model", "L_min"],
                            suffixes=("_corrected", "_historical"), validate="one_to_one")
    for column in ("rss", "aicc", "bic"):
        if not np.allclose(comparison[column + "_corrected"], comparison[column + "_historical"],
                           rtol=1e-9, atol=1e-9, equal_nan=True):
            raise ValueError(f"v3 primary {column} unexpectedly changed")
    bootstrap = v3.bootstrap_primary(events, widths, pd.DataFrame(), combined,
                                     samples=samples, seed=seed, unbounded_only=True)
    if not bootstrap.converged.all():
        raise ValueError("v3 corrected bootstrap has failed fits")
    intervals = v3.summarize_bootstrap(bootstrap)
    predictions = v3.attach_prediction_intervals(point_predictions, bootstrap)
    predictions["analysis_status"] = "retrospective bootstrap correction; not a preregistration"
    assessment = v3.additional_size_assessment(predictions)
    if any(sha256(path) != hashes[str(path)] for path in inputs):
        raise ValueError("v3 read-only input changed during correction")
    output.mkdir(parents=True, exist_ok=False)
    tables = {"unbounded_asymptotic_fits.csv": fits, "unbounded_leave_one_size_out.csv": loo,
              "unbounded_extrapolations.csv": predictions, "additional_size_assessment.csv": assessment,
              "bootstrap_distributions.csv": bootstrap, "bootstrap_intervals.csv": intervals,
              "point_fit_comparison.csv": comparison}
    normalized_bootstrap = bootstrap.rename(columns={"exponent": "decay_exponent"}).copy()
    normalized_bootstrap["finite_limit_zero_boundary"] = normalized_bootstrap.zero_limit_boundary
    normalized_intervals = summarize_bootstrap(normalized_bootstrap)
    tables["unbounded_bootstrap_diagnostics.csv"] = normalized_intervals
    for name, frame in tables.items():
        frame.to_csv(output / name, index=False)
    metadata = {"version": "v3", "samples": samples, "seed": seed,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "command": [sys.executable, *sys.argv], "limitations": LIMITATIONS,
                "estimator": "analysis.scaling_v3.fit_unbounded_models; historical v3 specifications retained",
                "rng": "Historical finite draws consumed unchanged; finite fits and joint fits skipped",
                "input_sha256_before_and_after": hashes,
                "code_sha256": {str(path): sha256(path) for path in
                                (Path(__file__), Path("analysis/scaling_v3.py"), Path("analysis/correction_fitting.py"))},
                "elapsed_seconds": time.perf_counter() - begin}
    (output / "correction_provenance.json").write_text(json.dumps(metadata, indent=2), encoding="utf8")
    normalized_bootstrap["observable"] = normalized_bootstrap.observable.replace({"delta_P_request": "maximum_request_jump"})
    normalized_intervals["observable"] = normalized_intervals.observable.replace({"delta_P_request": "maximum_request_jump"})
    primary = fits.loc[fits.L_min == 8].rename(columns={"exponent": "decay_exponent"}).copy()
    primary["observable"] = primary.observable.replace({"delta_P_request": "maximum_request_jump"})
    plot_predictions = predictions.copy()
    plot_predictions["observable"] = plot_predictions.observable.replace({"delta_P_request": "maximum_request_jump"})
    figures = correction_figures(primary, normalized_bootstrap, normalized_intervals, plot_predictions,
                                 output / "figures")
    print(f"v3: correction completed in {metadata['elapsed_seconds']:.1f} seconds", flush=True)
    return [output / name for name in tables] + [output / "correction_provenance.json"] + figures


def run_correction(
    version: str, output: str | Path | None = None, *, samples: int = 500,
    seed: int = 20260720, workers: int = 4,
) -> list[Path]:
    """Refuse existing destinations; fit all original observables and 4 models."""

    if version not in VERSIONS:
        raise ValueError(f"unknown version: {version}")
    if samples < 1 or workers < 1 or workers > 4:
        raise ValueError("samples must be positive and workers must be in [1,4]")
    output = Path(output or f"app/out/unbounded-{version}-bootstrap-corrected")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    begin = time.perf_counter()
    old = historical_output(version)
    events, widths, manifests = load_run_metrics(version)
    summary = summarize_run_metrics(version, events, widths)
    check = validate_summary(summary, pd.read_csv(old / "unbounded_size_summary.csv",
                                               float_precision="round_trip"))
    sources = input_paths(manifests, old)
    retrospective_inputs = retrospective_sources(version)
    if retrospective_inputs is not None:
        sources = sorted(set(sources).union(retrospective_inputs[1:]))
    hashes_before = {str(path): sha256(path) for path in sources}
    fits = pd.concat([
        fit_models(group.L, group.value, observable=observable)
        for observable, group in summary.groupby("observable", sort=False)
    ], ignore_index=True)
    prior_fits = pd.read_csv(old / "unbounded_model_fits.csv", float_precision="round_trip")
    point_comparison = fits.merge(prior_fits, on=["observable", "model"],
                                 suffixes=("_corrected", "_historical"), validate="one_to_one")
    for column in ("rss", "aicc", "bic"):
        left, right = point_comparison[column + "_corrected"], point_comparison[column + "_historical"]
        if not np.allclose(left, right, rtol=1e-9, atol=1e-9, equal_nan=True):
            raise ValueError(f"primary {column} unexpectedly changed")
    jobs = [
        (observable, column, aggregation, source_for(observable, events, widths),
         samples, seed + index)
        for index, (observable, (column, aggregation)) in enumerate(observable_definitions(version).items())
    ]
    print(f"{version}: preflight passed; {len(jobs)} observables, {samples} draws", flush=True)
    if workers == 1:
        bootstrap = pd.concat([_bootstrap_task(job) for job in jobs], ignore_index=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            bootstrap = pd.concat(list(pool.map(_bootstrap_task, jobs)), ignore_index=True)
    if not bootstrap.converged.all():
        raise ValueError("corrected bootstrap has failed fits; inspect before publication")
    intervals = summarize_bootstrap(bootstrap)
    predictions = prediction_table(fits, bootstrap, targets=(192, 256, 320, 384, 512, 768, 1024, 1536))
    predictions["analysis_status"] = "retrospective bootstrap correction; not a preregistration"
    scores = retrospective_scores(version, predictions, fits)
    historical_intervals = pd.read_csv(old / "unbounded_bootstrap_intervals.csv",
                                       float_precision="round_trip")
    changed = [str(path) for path in sources if sha256(path) != hashes_before[str(path)]]
    if changed:
        raise ValueError(f"read-only input changed during analysis: {changed}")
    code_paths = [Path(__file__), Path("analysis/unbounded_model_comparison.py"),
                  Path("analysis/correction_fitting.py"), Path("analysis/model_fitting.py"),
                  Path("analysis/unbounded_v4.py"), Path("analysis/unbounded_v5.py")]
    metadata = {
        "version": version, "created_utc": datetime.now(timezone.utc).isoformat(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "command": [sys.executable, *sys.argv], "samples": samples, "seed": seed,
        "observable_seeds": {job[0]: job[-1] for job in jobs},
        "estimator": "analysis.unbounded_model_comparison.fit_models, used by bootstrap_models",
        "objective": "unweighted original-scale residual sum of squares",
        "optimizer": "bounded curve_fit TRF, declared multistart, maxfev=20000",
        "model_specs": {name: {"starts": starts, "bounds": bounds, "parameters": names}
                        for name, (_, starts, bounds, names) in MODEL_SPECS.items()},
        "python": sys.version, "platform": platform.platform(), "numpy": np.__version__,
        "pandas": pd.__version__, "scipy": scipy.__version__, "workers": workers,
        "native_thread_environment": {name: os.environ.get(name) for name in
                                     ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
        "limitations": LIMITATIONS, "historical_output": str(old),
        "input_sha256_before_and_after": hashes_before,
        "code_sha256": {str(path): sha256(path) for path in code_paths},
        "elapsed_seconds": time.perf_counter() - begin,
    }
    output.mkdir(parents=True, exist_ok=False)
    tables = {
        "request_event_runs.csv": events, "transition_width_runs.csv": widths,
        "unbounded_size_summary.csv": summary, "summary_preflight_comparison.csv": check,
        "unbounded_model_fits.csv": fits, "point_fit_comparison.csv": point_comparison,
        "unbounded_bootstrap_samples.csv": bootstrap, "unbounded_bootstrap_intervals.csv": intervals,
        "unbounded_predictions.csv": predictions,
        "historical_corrected_intervals.csv": interval_comparison(historical_intervals, intervals),
    }
    if not scores.empty:
        tables["retrospective_prediction_scores.csv"] = scores
    for name, frame in tables.items():
        frame.to_csv(output / name, index=False)
    (output / "correction_provenance.json").write_text(json.dumps(metadata, indent=2), encoding="utf8")
    print(f"{version}: correction completed in {metadata['elapsed_seconds']:.1f} seconds", flush=True)
    figures = correction_figures(fits, bootstrap, intervals, predictions, output / "figures")
    return [output / name for name in tables] + [output / "correction_provenance.json"] + figures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=("v3", *VERSIONS), required=True)
    parser.add_argument("--output")
    parser.add_argument("--samples", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260720)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.version == "v3":
        run_v3_correction(args.output, samples=args.samples, seed=args.seed)
    else:
        run_correction(args.version, args.output, samples=args.samples, seed=args.seed, workers=args.workers)


if __name__ == "__main__":
    main()
