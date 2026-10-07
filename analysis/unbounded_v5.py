"""UNBOUNDED v5 integration of the staged L=256 pilot.

The v4 and scaling-v2/v3 products are read-only inputs.  All generated tables
and figures are written below ``app/out/unbounded-v5``.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "spp-matplotlib-cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.artifact_status import corrected_unbounded_intervals

from analysis.io import read_manifest
from analysis.unbounded_model_comparison import (
    bootstrap_models, fit_models, leave_one_size_out, predict,
    prediction_table, summarize_bootstrap,
)
from analysis.unbounded_v4 import (
    BASE_ANALYSIS, OBSERVABLES as V4_OBSERVABLES, STAGE_ROOT as L192_ROOT,
    load_all_run_metrics, load_stage_runs, stage_quality, stop_audit_report,
)


L256_ROOT = Path("app/out/unbounded-l256")
OUTPUT_ROOT = Path("app/out/unbounded-v5")
L256_MANIFESTS = [L256_ROOT / "benchmark/manifest.csv", L256_ROOT / "pilot/manifest.csv"]
MODEL_OBSERVABLES = {
    **V4_OBSERVABLES,
    "request_event_p_after": ("p_after", "mean"),
}


def load_v5_run_metrics() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    events, widths = load_all_run_metrics([
        L192_ROOT / "benchmark/manifest.csv", L192_ROOT / "pilot/manifest.csv",
        L192_ROOT / "main/manifest.csv",
    ])
    _, events256, widths256 = load_stage_runs(L256_MANIFESTS)
    events = pd.concat([events, events256], ignore_index=True, sort=False)
    widths = pd.concat([widths, widths256], ignore_index=True, sort=False)
    peaks = load_s_peaks()
    return events, widths, peaks


def load_s_peaks() -> pd.DataFrame:
    """Stream each UNBOUNDED results file and retain one S peak per run."""

    rows: list[dict[str, object]] = []
    sources = [Path("app/out/scaling-v1/manifest.csv"),
               Path("app/out/scaling-v2-main/manifest.csv"),
               L192_ROOT / "benchmark/manifest.csv", L192_ROOT / "pilot/manifest.csv",
               L192_ROOT / "main/manifest.csv", *L256_MANIFESTS]
    offsets: dict[int, int] = {}
    for source in sources:
        manifest = read_manifest(source)
        for condition in manifest.loc[manifest.budget_mode == "UNBOUNDED"].itertuples(index=False):
            data = pd.read_csv(condition.result_path, usecols=["run", "L", "mean_cluster_size"])
            L = int(data.L.iloc[0])
            offset = offsets.get(L, 0)
            peaks = data.groupby("run", sort=True).mean_cluster_size.max()
            for run, value in peaks.items():
                rows.append({"L": L, "run": offset + int(run), "S_peak": float(value)})
            offsets[L] = offset + int(condition.runs)
    return pd.DataFrame(rows)


def metric_summary(events: pd.DataFrame, widths: pd.DataFrame, peaks: pd.DataFrame) -> pd.DataFrame:
    sources = {
        "maximum_request_jump": events,
        "request_event_p_dispersion": events,
        "request_event_p_after": events,
        "transition_delta_p": widths,
        "transition_delta_t_normalized": widths,
        "S_peak": peaks,
    }
    definitions = {**MODEL_OBSERVABLES, "S_peak": ("S_peak", "mean")}
    rows = []
    for observable, (column, aggregation) in definitions.items():
        for L, group in sources[observable].groupby("L", sort=True):
            values = group[column].dropna().to_numpy(float)
            value = float(np.mean(values) if aggregation == "mean" else np.std(values, ddof=1))
            rows.append({
                "observable": observable, "L": int(L), "run_count": len(values),
                "value": value, "sample_std": float(np.std(values, ddof=1)),
                "sample_sem": float(np.std(values, ddof=1) / np.sqrt(len(values))),
            })
    return pd.DataFrame(rows)


def run_analysis(
    output: str | Path = OUTPUT_ROOT,
    *, bootstrap_samples: int = 500, seed: int = 20260720,
) -> list[Path]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    events, widths, peaks = load_v5_run_metrics()
    summary = metric_summary(events, widths, peaks)
    summary.to_csv(output / "unbounded_size_summary.csv", index=False)

    fits_parts, loo_parts, boot_parts = [], [], []
    source_map = {
        "maximum_request_jump": events,
        "request_event_p_dispersion": events,
        "request_event_p_after": events,
        "transition_delta_p": widths,
        "transition_delta_t_normalized": widths,
    }
    for index, (observable, (column, aggregation)) in enumerate(MODEL_OBSERVABLES.items()):
        subset = summary.loc[summary.observable == observable]
        fits_parts.append(fit_models(subset.L, subset.value, observable=observable))
        loo_parts.append(leave_one_size_out(subset, "value", observable))
        boot_parts.append(bootstrap_models(
            source_map[observable], value_column=column, aggregation=aggregation,
            observable=observable, samples=bootstrap_samples, seed=seed + index,
        ))
    fits = pd.concat(fits_parts, ignore_index=True)
    loo = pd.concat(loo_parts, ignore_index=True)
    bootstrap = pd.concat(boot_parts, ignore_index=True)
    intervals = summarize_bootstrap(bootstrap)
    predictions = prediction_table(
        fits, bootstrap, targets=(256, 320, 384, 512, 768)
    )
    lmin = lmin_fits(summary)
    loo_summary = summarize_loo(loo)
    l256 = l256_observations(events, widths, peaks, samples=5_000, seed=seed)
    prior = prior_prediction_check(l256)
    comparison = compare_v4_v5(fits, loo_summary, intervals, predictions)
    quality = stage_quality(L256_MANIFESTS)
    seeds = seed_audit()
    audit = stop_audit_report(
        stage_root=L256_ROOT,
        benchmark_name="benchmark/manifest.csv",
        audit_name="stop-audit/manifest.csv",
    )
    options = experiment_options(l256)
    extrapolation_ranges = summarize_extrapolations(predictions)

    tables = {
        "unbounded_model_fits.csv": fits,
        "unbounded_leave_one_size_out.csv": loo,
        "unbounded_loo_summary.csv": loo_summary,
        "unbounded_bootstrap_samples.csv": bootstrap,
        "unbounded_bootstrap_intervals.csv": intervals,
        "unbounded_predictions.csv": predictions,
        "unbounded_lmin_dependence.csv": lmin,
        "l256_observations.csv": l256,
        "l256_prior_prediction_check.csv": prior,
        "v4_v5_model_comparison.csv": comparison,
        "stage_data_quality.csv": quality,
        "seed_audit.csv": seeds,
        "stop_audit.csv": audit,
        "experiment_options.csv": options,
        "extrapolation_ranges.csv": extrapolation_ranges,
    }
    for name, frame in tables.items():
        frame.to_csv(output / name, index=False)
    figures = create_figures(
        summary, fits, loo, bootstrap, lmin, predictions, prior, options,
        output / "figures",
    )
    print(f"unbounded-v5: L256_runs={int(l256.run_count.max())} "
          f"bootstrap_samples={bootstrap_samples} outputs={len(tables) + len(figures)}")
    return [output / name for name in tables] + figures


def seed_audit() -> pd.DataFrame:
    """Check that the staged L=256 seed namespace is internally unique and new."""

    metadata_paths = [
        L192_ROOT / "benchmark/run_metadata.csv", L192_ROOT / "pilot/run_metadata.csv",
        L192_ROOT / "main/run_metadata.csv", L256_ROOT / "benchmark/run_metadata.csv",
        L256_ROOT / "pilot/run_metadata.csv",
    ]
    frames = []
    for path in metadata_paths:
        frame = pd.read_csv(path, usecols=["run", "run_seed"])
        frame["source"] = str(path.parent)
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)
    l256 = combined.loc[combined.source.str.contains("unbounded-l256")]
    l192 = combined.loc[combined.source.str.contains("unbounded-l192")]
    return pd.DataFrame([{
        "l256_run_count": len(l256),
        "l256_unique_run_seed_count": l256.run_seed.nunique(),
        "l256_internal_duplicate": bool(l256.run_seed.duplicated().any()),
        "l192_l256_overlap_count": len(set(l192.run_seed).intersection(l256.run_seed)),
        "benchmark_pilot_overlap_count": len(set(frames[-2].run_seed).intersection(frames[-1].run_seed)),
        "input_seed_range_l256": "2560000-2560019",
        "note": "scaling experiments intentionally reuse base seeds across C; L256 uses a separate namespace",
    }])


def lmin_fits(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for observable in MODEL_OBSERVABLES:
        group = summary.loc[summary.observable == observable]
        for L_min in (8, 12, 16, 24, 32, 48, 64, 96):
            subset = group.loc[group.L >= L_min]
            if len(subset) < 5:
                continue
            fitted = fit_models(subset.L, subset.value, observable=observable)
            fitted["requested_L_min"] = L_min
            rows.extend(fitted.to_dict("records"))
    return pd.DataFrame(rows)


def summarize_loo(loo: pd.DataFrame) -> pd.DataFrame:
    return (loo.groupby(["observable", "model"], sort=True)
            .agg(loo_mae=("absolute_prediction_error", "mean"),
                 loo_rmse=("prediction_error", lambda values: float(np.sqrt(np.mean(np.square(values))))),
                 largest_error=("absolute_prediction_error", "max"))
            .reset_index())


def l256_observations(
    events: pd.DataFrame, widths: pd.DataFrame, peaks: pd.DataFrame,
    *, samples: int, seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    definitions = {
        "maximum_request_jump": (events.loc[events.L == 256, "delta_P_request"], "mean"),
        "transition_delta_p": (widths.loc[widths.L == 256, "delta_p"], "mean"),
        "transition_delta_t_normalized": (widths.loc[widths.L == 256, "delta_t_normalized"], "mean"),
        "request_event_p_after": (events.loc[events.L == 256, "p_after"], "mean"),
        "request_event_p_dispersion": (events.loc[events.L == 256, "p_mid"], "std"),
        "S_peak": (peaks.loc[peaks.L == 256, "S_peak"], "mean"),
    }
    rows = []
    for observable, (series, aggregation) in definitions.items():
        values = series.dropna().to_numpy(float)
        estimate = float(np.mean(values) if aggregation == "mean" else np.std(values, ddof=1))
        draws = []
        for _ in range(samples):
            sample = values[rng.integers(0, len(values), len(values))]
            draws.append(float(np.mean(sample) if aggregation == "mean" else np.std(sample, ddof=1)))
        estimator_sem = (float(np.std(draws, ddof=1)) if aggregation == "std"
                         else float(np.std(values, ddof=1) / np.sqrt(len(values))))
        rows.append({
            "observable": observable, "L": 256, "run_count": len(values),
            "estimate": estimate, "sample_std": float(np.std(values, ddof=1)),
            "sem": estimator_sem,
            "bootstrap_ci95_low": float(np.percentile(draws, 2.5)),
            "bootstrap_ci95_high": float(np.percentile(draws, 97.5)),
        })
    return pd.DataFrame(rows)


def prior_prediction_check(l256: pd.DataFrame) -> pd.DataFrame:
    prior = pd.read_csv("app/out/unbounded-v4/main50/unbounded_predictions.csv")
    observed = l256.loc[l256.observable == "maximum_request_jump"].iloc[0]
    rows = []
    for item in prior.loc[(prior.observable == "maximum_request_jump")
                          & (prior.target_L == 256)].itertuples(index=False):
        rows.append({
            "model": item.model, "L256_observed_mean": observed.estimate,
            "L256_observed_sem": observed["sem"],
            "L256_observed_bootstrap_low": observed.bootstrap_ci95_low,
            "L256_observed_bootstrap_high": observed.bootstrap_ci95_high,
            "v4_prior_prediction": item.prediction,
            "prior_prediction_error": item.prediction - observed.estimate,
            "absolute_prior_prediction_error": abs(item.prediction - observed.estimate),
            "v4_prediction_interval_low": item.prediction_ci95_low,
            "v4_prediction_interval_high": item.prediction_ci95_high,
            "observation_inside_v4_interval": bool(
                item.prediction_ci95_low <= observed.estimate <= item.prediction_ci95_high
            ),
            "comparison_type": "out-of-sample v4 prediction versus new L=256 observation",
        })
    result = pd.DataFrame(rows)
    result["smallest_absolute_error"] = (
        result.absolute_prior_prediction_error == result.absolute_prior_prediction_error.min()
    )
    return result


def compare_v4_v5(
    fits: pd.DataFrame, loo: pd.DataFrame, intervals: pd.DataFrame,
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    old_fits = pd.read_csv("app/out/unbounded-v4/main50/unbounded_model_fits.csv")
    old_loo_raw = pd.read_csv("app/out/unbounded-v4/main50/unbounded_leave_one_size_out.csv")
    old_loo = summarize_loo(old_loo_raw)
    old_intervals = pd.read_csv(corrected_unbounded_intervals("v4"))
    old_predictions = pd.read_csv("app/out/unbounded-v4/main50/unbounded_predictions.csv")
    rows = []
    common = sorted(set(old_fits.observable).intersection(fits.observable))
    for observable in common:
        for model in ("zero_power", "finite_power", "zero_log", "finite_log"):
            before = old_fits.loc[(old_fits.observable == observable) & (old_fits.model == model)].iloc[0]
            after = fits.loc[(fits.observable == observable) & (fits.model == model)].iloc[0]
            before_loo = old_loo.loc[(old_loo.observable == observable) & (old_loo.model == model)].iloc[0]
            after_loo = loo.loc[(loo.observable == observable) & (loo.model == model)].iloc[0]
            before_ci = old_intervals.loc[(old_intervals.observable == observable)
                                          & (old_intervals.model == model)
                                          & (old_intervals.parameter == "limit")]
            after_ci = intervals.loc[(intervals.observable == observable)
                                     & (intervals.model == model)
                                     & (intervals.parameter == "limit")]
            rows.append({
                "observable": observable, "model": model,
                "aicc_v4": before.aicc, "aicc_v5": after.aicc,
                "bic_v4": before.bic, "bic_v5": after.bic,
                "loo_mae_v4": before_loo.loo_mae, "loo_mae_v5": after_loo.loo_mae,
                "loo_rmse_v4": before_loo.loo_rmse, "loo_rmse_v5": after_loo.loo_rmse,
                "limit_v4": before.limit, "limit_v5": after.limit,
                "limit_ci_width_v4": (_ci_width(before_ci)),
                "limit_ci_width_v5": (_ci_width(after_ci)),
                "boundary_v4": before.boundary_solution,
                "boundary_v5": after.boundary_solution,
                "max_parameter_correlation_v4": before.max_parameter_correlation,
                "max_parameter_correlation_v5": after.max_parameter_correlation,
                "limit_decay_correlation_v5": after.limit_decay_correlation,
                "fit_failed_v5": not bool(after.converged),
            })
    result = pd.DataFrame(rows)
    for version in ("v4", "v5"):
        result[f"aicc_rank_{version}"] = result.groupby("observable")[f"aicc_{version}"].rank(method="min")
        result[f"bic_rank_{version}"] = result.groupby("observable")[f"bic_{version}"].rank(method="min")
    return result


def _ci_width(frame: pd.DataFrame) -> float:
    return (float(frame.iloc[0].ci95_high - frame.iloc[0].ci95_low)
            if not frame.empty else np.nan)


def summarize_extrapolations(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (observable, target), group in predictions.groupby(["observable", "target_L"], sort=True):
        intervals = group[["prediction_ci95_low", "prediction_ci95_high"]].dropna()
        rows.append({
            "observable": observable, "target_L": int(target),
            "model_prediction_min": float(group.prediction.min()),
            "model_prediction_max": float(group.prediction.max()),
            "between_model_range": float(group.prediction.max() - group.prediction.min()),
            "all_intervals_overlap": bool(
                intervals.empty or intervals.prediction_ci95_low.max()
                <= intervals.prediction_ci95_high.min()
            ),
            "distance_from_L256": target / 256.0,
            "warning": "extrapolation beyond observed L=256; not an observation",
        })
    return pd.DataFrame(rows)


def experiment_options(l256: pd.DataFrame) -> pd.DataFrame:
    metadata = pd.concat([
        pd.read_csv(L256_ROOT / "benchmark/run_metadata.csv"),
        pd.read_csv(L256_ROOT / "pilot/run_metadata.csv"),
    ], ignore_index=True)
    median_time = float(metadata.elapsed_milliseconds.median() / 1000)
    bytes_per_run = float(metadata.results_bytes.mean())
    heap = int(metadata.observed_heap_used_bytes.max())
    jump = l256.loc[l256.observable == "maximum_request_jump"].iloc[0]
    # Empirical L=192-to-256 exponent; intended only for capacity planning.
    metadata192 = pd.concat([
        pd.read_csv(L192_ROOT / "benchmark/run_metadata.csv"),
        pd.read_csv(L192_ROOT / "pilot/run_metadata.csv"),
        pd.read_csv(L192_ROOT / "main/run_metadata.csv"),
    ], ignore_index=True)
    exponent = math.log(median_time / (metadata192.elapsed_milliseconds.median() / 1000)) / math.log(256 / 192)
    rows = []
    for label, size, runs in (
        ("A: L256 total 50", 256, 50), ("B: L256 total 100", 256, 100),
        ("C: L320 pilot", 320, 20), ("C: L384 pilot", 384, 20),
        ("D: stop", 256, 20),
    ):
        time_per_run = median_time * (size / 256) ** exponent
        rows.append({
            "option": label, "L": size, "runs": runs,
            "estimated_jump_sem": (jump.sample_std / math.sqrt(runs) if size == 256 else np.nan),
            "estimated_total_seconds": (0.0 if label.startswith("D") else time_per_run * runs),
            "estimated_results_bytes": (0.0 if label.startswith("D") else bytes_per_run * runs * (size / 256) ** 2),
            "observed_or_reference_heap_bytes": heap,
            "information_value": ("reduces one-size sampling error" if size == 256 and runs > 20 else
                                  "adds size leverage for asymptotic-model discrimination" if size > 256 else
                                  "accepts unresolved asymptotics"),
            "risk": ("systematic size ambiguity remains" if size == 256 and runs > 20 else
                     "runtime/memory are extrapolated" if size > 256 else
                     "transition order remains unclassified"),
            "implementation": "reuse staged runner with new size configuration" if size > 256 else "configuration-only or none",
            "estimate_warning": "empirical extrapolation; not a guarantee",
        })
    return pd.DataFrame(rows)


def create_figures(
    summary: pd.DataFrame, fits: pd.DataFrame, loo: pd.DataFrame,
    bootstrap: pd.DataFrame, lmin: pd.DataFrame, predictions: pd.DataFrame,
    prior: pd.DataFrame, options: pd.DataFrame, directory: Path,
) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    primary = ("maximum_request_jump", "transition_delta_p", "transition_delta_t_normalized")
    for observable in primary:
        paths.append(_plot_size_models(summary, fits, observable,
                                       directory / f"{observable}_size_dependence.png"))

    # v4/v5 fit comparison.
    old = pd.read_csv("app/out/unbounded-v4/main50/unbounded_model_fits.csv")
    data = summary.loc[summary.observable == "maximum_request_jump"].sort_values("L")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    grid = np.geomspace(8, 256, 250)
    for ax, table, title in ((axes[0], old, "v4: L≤192"), (axes[1], fits, "v5: L≤256")):
        ax.scatter(data.L, data.value, label="observed means")
        for row in table.loc[table.observable == "maximum_request_jump"].to_dict("records"):
            ax.plot(grid, [predict(row, x) for x in grid], label=row["model"])
        ax.set(xscale="log", xlabel="linear size L", ylabel="maximum request jump", title=title)
        ax.legend(fontsize=7)
    paths.append(_save(fig, directory / "maximum_jump_v4_v5_fit_comparison.png"))

    for family in ("power", "log"):
        fig, ax = plt.subplots(figsize=(7.2, 5), constrained_layout=True)
        ax.errorbar(data.L, data.value, yerr=data.sample_sem, fmt="o", label="observed mean ± SEM")
        for row in fits.loc[(fits.observable == "maximum_request_jump")
                            & fits.model.str.contains(family)].to_dict("records"):
            ax.plot(grid, [predict(row, x) for x in grid], label=row["model"])
        ax.set(xscale="log", xlabel="linear size L", ylabel="maximum request jump",
               title=f"Zero versus finite {family} asymptotics")
        ax.legend()
        paths.append(_save(fig, directory / f"maximum_jump_{family}_zero_finite.png"))

    # Standardized residuals.
    fig, ax = plt.subplots(figsize=(7.2, 5), constrained_layout=True)
    for row in fits.loc[fits.observable == "maximum_request_jump"].to_dict("records"):
        residual = data.value.to_numpy() - np.array([predict(row, x) for x in data.L])
        ax.plot(data.L, residual / data.sample_sem.to_numpy(), marker="o", label=row["model"])
    ax.axhline(0, color="black", linewidth=.8)
    ax.set(xlabel="linear size L", ylabel="standardized residual", title="Maximum-jump fit residuals")
    ax.legend(fontsize=7)
    paths.append(_save(fig, directory / "maximum_jump_standardized_residuals.png"))

    # LOO.
    fig, ax = plt.subplots(figsize=(7.2, 5), constrained_layout=True)
    for model, group in loo.loc[loo.observable == "maximum_request_jump"].groupby("model"):
        ax.plot(group.omitted_L, group.prediction_error, marker="o", label=model)
    ax.axhline(0, color="black", linewidth=.8)
    ax.set(xlabel="omitted linear size L", ylabel="held-out prediction error", title="Leave-one-size-out comparison")
    ax.legend(fontsize=7)
    paths.append(_save(fig, directory / "maximum_jump_leave_one_size_out.png"))

    # Bootstrap limit and exponents.
    for parameter, filename, xlabel in (
        ("limit", "finite_limit_bootstrap.png", r"asymptotic limit $Y_\infty$"),
        ("decay_exponent", "decay_exponent_bootstrap.png", "decay/log exponent"),
    ):
        fig, ax = plt.subplots(figsize=(7.2, 5), constrained_layout=True)
        subset = bootstrap.loc[(bootstrap.observable == "maximum_request_jump") & bootstrap.converged]
        for model, group in subset.groupby("model"):
            if parameter != "limit" or model.startswith("finite"):
                ax.hist(group[parameter], bins=30, alpha=.45, label=model)
        ax.set(xlabel=xlabel, ylabel="bootstrap count", title="Run-stratified bootstrap")
        ax.legend(fontsize=7)
        paths.append(_save(fig, directory / filename))

    # Lmin.
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    subset = lmin.loc[lmin.observable == "maximum_request_jump"]
    for model, group in subset.groupby("model"):
        axes[0].plot(group.requested_L_min, group.decay_exponent, marker="o", label=model)
        if model.startswith("finite"):
            axes[1].plot(group.requested_L_min, group.limit, marker="o", label=model)
    axes[0].set(xlabel=r"minimum size $L_{min}$", ylabel="decay exponent", title="Exponent stability")
    axes[1].set(xlabel=r"minimum size $L_{min}$", ylabel=r"$Y_\infty$", title="Finite-limit stability")
    for ax in axes: ax.legend(fontsize=7)
    paths.append(_save(fig, directory / "maximum_jump_lmin_dependence.png"))

    # Prior prediction.
    fig, ax = plt.subplots(figsize=(7.2, 5), constrained_layout=True)
    x = np.arange(len(prior))
    center = prior.L256_observed_mean.iloc[0]
    ax.axhspan(prior.L256_observed_bootstrap_low.iloc[0], prior.L256_observed_bootstrap_high.iloc[0],
               color="0.85", label="L=256 observed bootstrap 95% CI")
    ax.axhline(center, color="black", label="L=256 observed mean")
    ax.errorbar(x, prior.v4_prior_prediction,
                yerr=[prior.v4_prior_prediction-prior.v4_prediction_interval_low,
                      prior.v4_prediction_interval_high-prior.v4_prior_prediction], fmt="o")
    ax.set_xticks(x, prior.model, rotation=25)
    ax.set(ylabel="maximum request jump", title="V4 out-of-sample predictions versus L=256")
    ax.legend(fontsize=8)
    paths.append(_save(fig, directory / "l256_prior_prediction_check.png"))

    # Extrapolation and interval overlap.
    pred = predictions.loc[predictions.observable == "maximum_request_jump"]
    for with_interval, name in ((False, "maximum_jump_extrapolations.png"),
                                (True, "maximum_jump_prediction_intervals.png")):
        fig, ax = plt.subplots(figsize=(7.2, 5), constrained_layout=True)
        for model, group in pred.groupby("model"):
            ax.plot(group.target_L, group.prediction, marker="o", label=model)
            if with_interval:
                ax.fill_between(group.target_L, group.prediction_ci95_low,
                                group.prediction_ci95_high, alpha=.15)
        ax.axvline(256, color="black", linestyle=":", label="largest observed L")
        ax.set(xlabel="target linear size L", ylabel="predicted maximum request jump",
               title="Model extrapolations (not observations)")
        ax.legend(fontsize=7)
        paths.append(_save(fig, directory / name))

    # Cost-effectiveness.
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.scatter(options.estimated_total_seconds, options.estimated_jump_sem)
    for row in options.itertuples():
        ax.annotate(row.option, (row.estimated_total_seconds, row.estimated_jump_sem), fontsize=7)
    ax.set(xlabel="estimated total runtime (s)", ylabel="estimated L=256 jump SEM",
           title="Run count / next-size cost-effectiveness (estimates)")
    paths.append(_save(fig, directory / "experiment_cost_effectiveness.png"))

    # Request-event and S peak sizes.
    for observable in ("request_event_p_after", "S_peak"):
        group = summary.loc[summary.observable == observable]
        fig, ax = plt.subplots(figsize=(7.2, 5), constrained_layout=True)
        ax.errorbar(group.L, group.value, yerr=group.sample_sem, fmt="o-")
        ax.set(xscale="log", xlabel="linear size L", ylabel=observable,
               title=f"UNBOUNDED {observable}: observed run summaries")
        paths.append(_save(fig, directory / f"{observable}_size_dependence.png"))
    return paths


def _plot_size_models(summary: pd.DataFrame, fits: pd.DataFrame, observable: str, path: Path) -> Path:
    data = summary.loc[summary.observable == observable].sort_values("L")
    grid = np.geomspace(data.L.min(), 768, 300)
    fig, ax = plt.subplots(figsize=(7.2, 5), constrained_layout=True)
    ax.errorbar(data.L, data.value, yerr=data.sample_sem, fmt="o", label="observed mean ± SEM")
    for row in fits.loc[fits.observable == observable].to_dict("records"):
        ax.plot(grid, [predict(row, x) for x in grid], label=row["model"])
    ax.axvline(256, color="black", linestyle=":", label="largest observed L")
    ax.set(xscale="log", xlabel="linear size L", ylabel=observable,
           title=f"UNBOUNDED size dependence: {observable}")
    ax.legend(fontsize=7)
    return _save(fig, path)


def _save(fig: plt.Figure, path: Path) -> Path:
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT_ROOT))
    parser.add_argument("--bootstrap-samples", type=int, default=500)
    args = parser.parse_args()
    run_analysis(args.output, bootstrap_samples=args.bootstrap_samples)


if __name__ == "__main__":
    main()
