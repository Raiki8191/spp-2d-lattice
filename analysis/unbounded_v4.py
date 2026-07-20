"""UNBOUNDED v4 analysis with staged L=192 data.

The command consumes existing scaling-v2 products and the new immutable stage
outputs.  It never regenerates or edits scaling-v2/scaling-v3 data.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "spp-matplotlib-cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.io import read_manifest, read_results
from analysis.request_event import build_request_transitions, extract_request_events
from analysis.transition_width import calculate_transition_widths
from analysis.unbounded_model_comparison import (
    bootstrap_models, fit_models, leave_one_size_out, predict,
    prediction_table, summarize_bootstrap,
)
from analysis.validation import validate_sweep


OBSERVABLES = {
    "maximum_request_jump": ("delta_P_request", "mean"),
    "transition_delta_p": ("delta_p", "mean"),
    "transition_delta_t_normalized": ("delta_t_normalized", "mean"),
    "request_event_p_dispersion": ("p_mid", "std"),
}
BASE_ANALYSIS = Path("app/out/scaling-v2-analysis")
STAGE_ROOT = Path("app/out/unbounded-l192")
OUTPUT_ROOT = Path("app/out/unbounded-v4")


def load_stage_runs(manifests: list[str | Path]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load, validate and combine stage results with globally unique runs."""

    results_parts, event_parts, width_parts = [], [], []
    run_offset, seen_seeds = 0, set()
    for path in manifests:
        manifest = read_manifest(path)
        results = read_results(manifest)
        validate_sweep(manifest, results)
        expected_runs = int(manifest.iloc[0]["runs"])
        actual_runs = sorted(results["run"].unique())
        if actual_runs != list(range(expected_runs)):
            raise ValueError(f"missing or duplicate run index in {path}: {actual_runs}")
        terminal = results.sort_values("step").groupby("run", sort=True).tail(1)
        if len(terminal) != expected_runs:
            raise ValueError(f"incomplete terminal rows in {path}")
        new_seeds = set(int(value) for value in terminal["seed"])
        overlap = seen_seeds.intersection(new_seeds)
        if overlap:
            raise ValueError(f"duplicate run seeds across stages: {sorted(overlap)[:3]}")
        seen_seeds.update(new_seeds)
        remapped = results.copy()
        remapped["run"] += run_offset
        remapped["condition_index"] = 192
        events = extract_request_events(build_request_transitions(remapped))
        widths = calculate_transition_widths(remapped)
        results_parts.append(remapped)
        event_parts.append(events)
        width_parts.append(widths)
        run_offset += expected_runs
    results = pd.concat(results_parts, ignore_index=True)
    events = pd.concat(event_parts, ignore_index=True)
    widths = pd.concat(width_parts, ignore_index=True)
    events["p_mid"] = (events["p_before"] + events["p_after"]) / 2.0
    if len(events) != run_offset or len(widths) != run_offset:
        raise ValueError("each staged run must produce one event and one transition width")
    if not widths["thresholds_crossed"].all():
        raise ValueError("a staged run did not complete the transition window")
    return results, events, widths


def load_all_run_metrics(stage_manifests: list[str | Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    old_events = pd.read_csv(BASE_ANALYSIS / "request_event_runs.csv")
    old_widths = pd.read_csv(BASE_ANALYSIS / "transition_width_runs.csv")
    old_events = old_events.loc[old_events["budget_mode"] == "UNBOUNDED"].copy()
    old_widths = old_widths.loc[old_widths["budget_mode"] == "UNBOUNDED"].copy()
    old_events["delta_P_request"] = old_events["delta_P_max"]
    if "p_mid" not in old_events:
        old_events["p_mid"] = (old_events["p_before"] + old_events["p_after"]) / 2.0
    _, new_events, new_widths = load_stage_runs(stage_manifests)
    event_columns = sorted(set(old_events.columns).intersection(new_events.columns))
    width_columns = sorted(set(old_widths.columns).intersection(new_widths.columns))
    events = pd.concat([old_events[event_columns], new_events[event_columns]], ignore_index=True)
    widths = pd.concat([old_widths[width_columns], new_widths[width_columns]], ignore_index=True)
    return events, widths


def metric_summary(events: pd.DataFrame, widths: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sources = {
        "maximum_request_jump": events,
        "request_event_p_dispersion": events,
        "transition_delta_p": widths,
        "transition_delta_t_normalized": widths,
    }
    for observable, (column, aggregation) in OBSERVABLES.items():
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
    stage_manifests: list[str | Path], output: str | Path,
    *, bootstrap_samples: int = 500, seed: int = 20260720,
) -> list[Path]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    events, widths = load_all_run_metrics(stage_manifests)
    summary = metric_summary(events, widths)
    summary.to_csv(output / "unbounded_size_summary.csv", index=False)

    fit_parts, loo_parts, bootstrap_parts = [], [], []
    for index, (observable, (column, aggregation)) in enumerate(OBSERVABLES.items()):
        subset = summary.loc[summary["observable"] == observable]
        fits = fit_models(subset["L"], subset["value"], observable=observable)
        fit_parts.append(fits)
        loo_parts.append(leave_one_size_out(subset, "value", observable))
        source = events if observable in {"maximum_request_jump", "request_event_p_dispersion"} else widths
        bootstrap_parts.append(bootstrap_models(
            source, value_column=column, aggregation=aggregation, observable=observable,
            samples=bootstrap_samples, seed=seed + index,
        ))
    fits = pd.concat(fit_parts, ignore_index=True)
    loo = pd.concat(loo_parts, ignore_index=True)
    bootstrap = pd.concat(bootstrap_parts, ignore_index=True)
    intervals = summarize_bootstrap(bootstrap)
    predictions = prediction_table(fits, bootstrap)
    lmin = lmin_fits(summary)
    information = compare_with_v3(summary, fits, loo, intervals, predictions)
    quality = stage_quality(stage_manifests)
    audit = stop_audit_report()
    decision = run_count_decision(summary, stage_manifests)
    next_size = next_size_assessment(predictions, stage_manifests)
    fits.to_csv(output / "unbounded_model_fits.csv", index=False)
    loo.to_csv(output / "unbounded_leave_one_size_out.csv", index=False)
    bootstrap.to_csv(output / "unbounded_bootstrap_samples.csv", index=False)
    intervals.to_csv(output / "unbounded_bootstrap_intervals.csv", index=False)
    predictions.to_csv(output / "unbounded_predictions.csv", index=False)
    lmin.to_csv(output / "unbounded_lmin_dependence.csv", index=False)
    information.to_csv(output / "v3_v4_information_gain.csv", index=False)
    quality.to_csv(output / "stage_data_quality.csv", index=False)
    audit.to_csv(output / "stop_audit.csv", index=False)
    decision.to_csv(output / "run_count_decision.csv", index=False)
    next_size.to_csv(output / "next_size_assessment.csv", index=False)
    figures = create_figures(summary, fits, loo, bootstrap, lmin, output / "figures")
    paths = [output / name for name in (
        "unbounded_size_summary.csv", "unbounded_model_fits.csv",
        "unbounded_leave_one_size_out.csv", "unbounded_bootstrap_samples.csv",
        "unbounded_bootstrap_intervals.csv", "unbounded_predictions.csv",
        "unbounded_lmin_dependence.csv", "v3_v4_information_gain.csv",
        "stage_data_quality.csv",
        "stop_audit.csv", "run_count_decision.csv", "next_size_assessment.csv",
    )] + figures
    print(f"unbounded-v4: L192_runs={int(summary.loc[summary.L == 192, 'run_count'].max())} "
          f"bootstrap_samples={bootstrap_samples} outputs={len(paths)}")
    return paths


def lmin_fits(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for observable, group in summary.groupby("observable", sort=True):
        for L_min in (8, 12, 16, 24, 32, 48, 64):
            subset = group.loc[group["L"] >= L_min]
            if len(subset) < 5:
                continue
            fit = fit_models(subset["L"], subset["value"], observable=observable)
            fit["requested_L_min"] = L_min
            rows.extend(fit.to_dict("records"))
    return pd.DataFrame(rows)


def stop_audit_report() -> pd.DataFrame:
    benchmark = STAGE_ROOT / "benchmark/manifest.csv"
    audit = STAGE_ROOT / "stop-audit/manifest.csv"
    if not audit.is_file():
        return pd.DataFrame()
    main_manifest = read_manifest(benchmark)
    audit_manifest = read_manifest(audit)
    main = read_results(main_manifest)
    extended = read_results(audit_manifest)
    validate_sweep(main_manifest, main)
    validate_sweep(audit_manifest, extended)
    rows = []
    for run in sorted(main.run.unique()):
        original = main.loc[main.run == run].sort_values("step").reset_index(drop=True)
        longer = extended.loc[extended.run == run].sort_values("step").reset_index(drop=True)
        prefix = longer.loc[longer.step <= original.step.max()].reset_index(drop=True)
        compare_columns = [column for column in original.columns
                           if column not in {"result_path"}]
        prefix_equal = original[compare_columns].equals(prefix[compare_columns])
        original_event = extract_request_events(build_request_transitions(original.assign(condition_index=0)))
        audit_event = extract_request_events(build_request_transitions(longer.assign(condition_index=0)))
        original_width = calculate_transition_widths(original.assign(condition_index=0)).iloc[0]
        audit_width = calculate_transition_widths(longer.assign(condition_index=0)).iloc[0]
        rows.append({
            "run": int(run), "seed": int(original.seed.iloc[0]),
            "prefix_exact_match": prefix_equal,
            "original_final_step": int(original.step.max()),
            "audit_final_step": int(longer.step.max()),
            "original_event_delta_P": float(original_event.delta_P_request.iloc[0]),
            "audit_event_delta_P": float(audit_event.delta_P_request.iloc[0]),
            "event_unchanged": bool(np.isclose(original_event.delta_P_request.iloc[0], audit_event.delta_P_request.iloc[0])),
            "transition_delta_p_original": float(original_width.delta_p),
            "transition_delta_p_audit": float(audit_width.delta_p),
            "transition_width_unchanged": bool(np.isclose(original_width.delta_p, audit_width.delta_p)),
            "S_peak_original": float(original.mean_cluster_size.max()),
            "S_peak_audit": float(longer.mean_cluster_size.max()),
            "S_peak_unchanged": bool(np.isclose(original.mean_cluster_size.max(), longer.mean_cluster_size.max())),
        })
    return pd.DataFrame(rows)


def run_count_decision(summary: pd.DataFrame, manifests: list[str | Path]) -> pd.DataFrame:
    rows = []
    metadata = pd.concat([pd.read_csv(Path(path).parent / "run_metadata.csv") for path in manifests],
                         ignore_index=True)
    milliseconds = metadata.elapsed_milliseconds.to_numpy(float)
    bytes_per_run = metadata.results_bytes.to_numpy(float)
    for observable in OBSERVABLES:
        row = summary.loc[(summary.observable == observable) & (summary.L == 192)].iloc[0]
        for target_runs in (20, 50, 100):
            rows.append({
                "observable": observable, "current_runs": int(row.run_count),
                "target_runs": target_runs,
                "estimated_sem_from_current_std": float(row.sample_std / np.sqrt(target_runs)),
                "estimated_total_runtime_seconds": float(np.median(milliseconds) * target_runs / 1000),
                "estimated_results_bytes": float(np.mean(bytes_per_run) * target_runs),
                "decision": ("completed" if target_runs <= row.run_count else
                             "not run: marginal replication cannot resolve size-range model ambiguity"),
                "estimate_warning": "median/mean benchmark extrapolation; not a guarantee",
            })
    return pd.DataFrame(rows)


def next_size_assessment(predictions: pd.DataFrame, manifests: list[str | Path]) -> pd.DataFrame:
    metadata = pd.concat([pd.read_csv(Path(path).parent / "run_metadata.csv") for path in manifests],
                         ignore_index=True)
    median_192 = float(metadata.elapsed_milliseconds.median() / 1000)
    # Empirical scaling from the existing v3 96/128 forecast is intentionally retained.
    forecast = pd.read_csv("app/out/scaling-v3-analysis/runtime_forecasts.csv")
    row = forecast.loc[(forecast.condition_label == "UNBOUNDED") &
                       (forecast.target_L == 256) & (forecast.runs == 1)].iloc[0]
    rows = []
    for observable, group in predictions.loc[predictions.target_L == 256].groupby("observable"):
        low = group.prediction_ci95_low.min()
        high = group.prediction_ci95_high.max()
        rows.append({
            "observable": observable, "target_L": 256,
            "between_model_prediction_range": float(group.prediction.max() - group.prediction.min()),
            "combined_prediction_interval_low": float(low),
            "combined_prediction_interval_high": float(high),
            "estimated_seconds_per_run_v3": float(row.seconds),
            "L192_observed_median_seconds_per_run": median_192,
            "recommendation": "do not auto-run; L=256 pilot is potentially more informative than 50 extra L=192 replicates",
            "warning": "prediction and runtime are extrapolations, not observations",
        })
    return pd.DataFrame(rows)


def compare_with_v3(
    summary: pd.DataFrame, fits: pd.DataFrame, loo: pd.DataFrame,
    intervals: pd.DataFrame, predictions: pd.DataFrame,
) -> pd.DataFrame:
    v3_fits = pd.read_csv("app/out/scaling-v3-analysis/unbounded_asymptotic_fits.csv")
    v3_loo = pd.read_csv("app/out/scaling-v3-analysis/unbounded_leave_one_size_out.csv")
    v3_pred = pd.read_csv("app/out/scaling-v3-analysis/unbounded_extrapolations.csv")
    mapping = {"delta_P_request": "maximum_request_jump", "transition_delta_p": "transition_delta_p"}
    rows = []
    for old_observable, observable in mapping.items():
        observed = float(summary.loc[(summary.observable == observable) & (summary.L == 192), "value"].iloc[0])
        for model in ("zero_power", "finite_power", "zero_log", "finite_log"):
            old = v3_fits.loc[(v3_fits.observable == old_observable) & (v3_fits.L_min == 8)
                              & (v3_fits.model == model)]
            new = fits.loc[(fits.observable == observable) & (fits.model == model)]
            prior = v3_pred.loc[(v3_pred.observable == old_observable) & (v3_pred.model == model)
                                & (v3_pred.target_L == 192)]
            if old.empty or new.empty:
                continue
            old_row, new_row = old.iloc[0], new.iloc[0]
            prior_prediction = float(prior.iloc[0]["prediction"]) if not prior.empty else np.nan
            new_loo = loo.loc[(loo.observable == observable) & (loo.model == model)]
            old_loo = v3_loo.loc[(v3_loo.observable == old_observable) & (v3_loo.model == model)]
            limit_ci = intervals.loc[(intervals.observable == observable) & (intervals.model == model)
                                     & (intervals.parameter == "limit")]
            rows.append({
                "observable": observable, "model": model,
                "L192_observed": observed, "v3_L192_prediction": prior_prediction,
                "v3_prediction_error": prior_prediction - observed,
                "aicc_v3": old_row.aicc, "aicc_v4": new_row.aicc,
                "bic_v3": old_row.bic, "bic_v4": new_row.bic,
                "loo_mae_v3": old_loo.absolute_prediction_error.mean() if "absolute_prediction_error" in old_loo else old_loo.prediction_error.abs().mean(),
                "loo_mae_v4": new_loo.absolute_prediction_error.mean(),
                "limit_ci95_low_v4": limit_ci.iloc[0].ci95_low if not limit_ci.empty else np.nan,
                "limit_ci95_high_v4": limit_ci.iloc[0].ci95_high if not limit_ci.empty else np.nan,
                "model_prediction_interval_overlap_remains": _prediction_intervals_overlap(
                    predictions.loc[(predictions.observable == observable)
                                    & (predictions.target_L == 256)]
                ),
            })
    return pd.DataFrame(rows)


def _prediction_intervals_overlap(group: pd.DataFrame) -> bool:
    valid = group[["prediction_ci95_low", "prediction_ci95_high"]].dropna()
    return bool(valid.empty or valid.prediction_ci95_low.max()
                <= valid.prediction_ci95_high.min())


def stage_quality(manifests: list[str | Path]) -> pd.DataFrame:
    rows, seeds = [], set()
    for path in manifests:
        manifest = read_manifest(path)
        results = read_results(manifest)
        terminal = results.sort_values("step").groupby("run", sort=True).tail(1)
        summary_path = Path(manifest.iloc[0].result_path).parent / "run_summary.csv"
        run_summary = pd.read_csv(summary_path)
        duplicate_seed = any(int(seed) in seeds for seed in terminal.seed)
        seeds.update(int(seed) for seed in terminal.seed)
        rows.append({
            "manifest": str(Path(path).resolve()), "runs": len(terminal),
            "result_rows": len(results), "result_bytes": Path(manifest.iloc[0].result_path).stat().st_size,
            "all_transition_window_complete": bool((run_summary.termination_reason == "TRANSITION_WINDOW_COMPLETE").all()),
            "duplicate_seed": duplicate_seed, "missing_values": int(results.isna().sum().sum()),
            "step_strictly_increasing": bool(results.groupby("run").step.apply(lambda x: x.is_monotonic_increasing and x.is_unique).all()),
            "removed_edges_monotone": bool(results.groupby("run").removed_edges.apply(lambda x: x.is_monotonic_increasing).all()),
        })
    return pd.DataFrame(rows)


def create_figures(
    summary: pd.DataFrame, fits: pd.DataFrame, loo: pd.DataFrame,
    bootstrap: pd.DataFrame, lmin: pd.DataFrame, directory: Path,
) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for observable in OBSERVABLES:
        data = summary.loc[summary.observable == observable].sort_values("L")
        selected = fits.loc[(fits.observable == observable) & fits.converged]
        grid = np.geomspace(data.L.min(), 512, 300)
        fig, ax = plt.subplots(figsize=(7.2, 5.0), constrained_layout=True)
        ax.errorbar(data.L, data.value, yerr=data.sample_sem, fmt="o", label="observed mean")
        for row in selected.to_dict("records"):
            ax.plot(grid, [predict(row, value) for value in grid], label=row["model"])
        ax.axvline(192, color="0.5", linestyle=":", label="largest observed L")
        ax.set(xscale="log", xlabel="linear size L", ylabel=observable,
               title=f"UNBOUNDED asymptotic models: {observable}")
        ax.legend(fontsize=7)
        paths.append(_save(fig, directory / f"{observable}_model_comparison.png"))

        fig, ax = plt.subplots(figsize=(7.2, 4.8), constrained_layout=True)
        for row in selected.to_dict("records"):
            residual = data.value.to_numpy(float) - np.array([predict(row, x) for x in data.L])
            scale = data.sample_sem.replace(0, np.nan).to_numpy(float)
            ax.plot(data.L, residual / scale, marker="o", label=row["model"])
        ax.axhline(0, color="black", linewidth=.8)
        ax.set(xlabel="linear size L", ylabel="standardized residual",
               title=f"Fit residuals: {observable}")
        ax.legend(fontsize=7)
        paths.append(_save(fig, directory / f"{observable}_standardized_residuals.png"))

        fig, ax = plt.subplots(figsize=(7.2, 4.8), constrained_layout=True)
        subset = lmin.loc[(lmin.observable == observable) & lmin.converged]
        for model, group in subset.groupby("model", sort=True):
            ax.plot(group.requested_L_min, group.decay_exponent, marker="o", label=model)
        ax.set(xlabel=r"minimum size $L_{min}$", ylabel="decay exponent",
               title=f"L_min sensitivity: {observable}")
        ax.legend(fontsize=7)
        paths.append(_save(fig, directory / f"{observable}_lmin_dependence.png"))

    fig, ax = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)
    for (observable, model), group in fits.groupby(["observable", "model"]):
        ax.scatter([f"{observable}\n{model}"], group.aicc.iloc[0])
    ax.tick_params(axis="x", rotation=90, labelsize=6)
    ax.set(ylabel="AICc", title="UNBOUNDED model information criteria")
    paths.append(_save(fig, directory / "model_aicc_comparison.png"))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    for ax, observable in zip(axes, ("maximum_request_jump", "transition_delta_p")):
        data = bootstrap.loc[(bootstrap.observable == observable) & bootstrap.converged]
        for model, group in data.groupby("model"):
            if model.startswith("finite"):
                ax.hist(group.limit, bins=30, alpha=.45, label=model)
        ax.set(xlabel=r"asymptotic limit $Y_\infty$", ylabel="bootstrap count", title=observable)
        ax.legend(fontsize=7)
    paths.append(_save(fig, directory / "finite_limit_bootstrap_distributions.png"))

    fig, ax = plt.subplots(figsize=(7.2, 4.8), constrained_layout=True)
    for model, group in loo.loc[loo.observable == "maximum_request_jump"].groupby("model"):
        ax.plot(group.omitted_L, group.prediction_error, marker="o", label=model)
    ax.axhline(0, color="black", linewidth=.8)
    ax.set(xlabel="omitted linear size L", ylabel="held-out prediction error",
           title="Leave-one-size-out: maximum request jump")
    ax.legend(fontsize=7)
    paths.append(_save(fig, directory / "leave_one_size_out_request_jump.png"))
    return paths


def _save(fig: plt.Figure, path: Path) -> Path:
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("pilot", "main"), default="main")
    parser.add_argument("--bootstrap-samples", type=int, default=500)
    args = parser.parse_args()
    manifests = [STAGE_ROOT / "benchmark/manifest.csv", STAGE_ROOT / "pilot/manifest.csv"]
    if args.stage == "main":
        manifests.append(STAGE_ROOT / "main/manifest.csv")
    run_analysis(manifests, OUTPUT_ROOT / ("pilot20" if args.stage == "pilot" else "main50"),
                 bootstrap_samples=args.bootstrap_samples)


if __name__ == "__main__":
    main()
