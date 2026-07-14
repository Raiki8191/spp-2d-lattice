"""Sensitivity of exact SPP observables to edge order within accepted paths."""

from __future__ import annotations

import argparse
import os
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "spp-matplotlib-cache")
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analysis.edge_trace import read_edge_traces, validate_trace_against_results
from analysis.event_ensemble import extract_event_peaks
from analysis.exact_ensemble import aggregate_exact_ensemble, reconstruct_exact_states
from analysis.io import load_sweep
from analysis.pseudocritical import extract_conventional_peaks
from analysis.validation import validate_sweep


SOURCE_TO_TARGET = "SOURCE_TO_TARGET"
TARGET_TO_SOURCE = "TARGET_TO_SOURCE"
DETERMINISTIC_SHUFFLE = "DETERMINISTIC_SHUFFLE"
ORDER_MODES = (SOURCE_TO_TARGET, TARGET_TO_SOURCE, DETERMINISTIC_SHUFFLE)

_MASK_64 = (1 << 64) - 1
_SHUFFLE_STREAM_CONSTANT = 0xD1B54A32D192ED03
_SPLITMIX_GAMMA = 0x9E3779B97F4A7C15


def reorder_within_requests(traces: pd.DataFrame, order_mode: str) -> pd.DataFrame:
    """Return a reordered copy while preserving request order and every edge set."""

    if traces is None:
        raise ValueError("traces must not be None")
    if order_mode not in ORDER_MODES:
        raise ValueError(f"unknown order_mode: {order_mode}")
    if traces.empty:
        return traces.copy(deep=True)

    frames: list[pd.DataFrame] = []
    for (_, run), run_trace in traces.groupby(
        ["condition_index", "run"], sort=True, dropna=False
    ):
        requests: list[pd.DataFrame] = []
        ordered_run = run_trace.sort_values("edge_order")
        for step, request in ordered_run.groupby("step", sort=False):
            request = request.sort_values("edge_index_in_request").copy()
            if order_mode == TARGET_TO_SOURCE:
                request = request.iloc[::-1].copy()
            elif order_mode == DETERMINISTIC_SHUFFLE:
                seed = int(request.iloc[0]["seed"])
                permutation = _deterministic_permutation(len(request), seed, int(step))
                request = request.iloc[permutation].copy()
            request["edge_index_in_request"] = np.arange(len(request), dtype=np.int64)
            requests.append(request)
        reordered_run = pd.concat(requests, ignore_index=True)
        reordered_run["edge_order"] = np.arange(len(reordered_run), dtype=np.int64)
        frames.append(reordered_run)
    return pd.concat(frames, ignore_index=True).loc[:, traces.columns]


def analyze_order_sensitivity(
    manifest_path: str | Path, output_directory: str | Path | None = None
) -> list[Path]:
    started = time.perf_counter()
    manifest, results = load_sweep(manifest_path)
    validation = validate_sweep(manifest, results)
    source_trace = read_edge_traces(manifest)
    validate_trace_against_results(manifest, results, source_trace)

    conventional_frames: list[pd.DataFrame] = []
    event_frames: list[pd.DataFrame] = []
    ensembles: dict[str, pd.DataFrame] = {}
    for order_mode in ORDER_MODES:
        trace = reorder_within_requests(source_trace, order_mode)
        exact_states = reconstruct_exact_states(manifest, trace)
        ensemble = aggregate_exact_ensemble(exact_states)
        conventional = extract_conventional_peaks(ensemble)
        conventional.insert(4, "order_mode", order_mode)
        events = extract_event_peaks(exact_states, trace)
        events.insert(5, "order_mode", order_mode)
        conventional_frames.append(conventional)
        event_frames.append(events)
        ensembles[order_mode] = ensemble

    conventional_all = pd.concat(conventional_frames, ignore_index=True)
    events_all = pd.concat(event_frames, ignore_index=True)
    event_summary = _summarize_events(events_all)
    comparison = _comparison(conventional_all, event_summary)
    _assert_c1_invariance(comparison)

    root = (
        Path(output_directory)
        if output_directory is not None
        else Path(manifest.attrs["manifest_path"]).parent / "order-sensitivity"
    )
    figure_directory = root / "figures"
    figure_directory.mkdir(parents=True, exist_ok=True)
    conventional_all.to_csv(
        root / "order_sensitivity_conventional.csv", index=False, encoding="utf-8"
    )
    event_summary.to_csv(
        root / "order_sensitivity_event.csv", index=False, encoding="utf-8"
    )
    comparison.to_csv(
        root / "order_sensitivity_comparison.csv", index=False, encoding="utf-8"
    )
    generated = _plot_comparisons(
        manifest, ensembles, events_all, figure_directory
    )
    elapsed = time.perf_counter() - started
    print(
        "Order-sensitivity validation succeeded: "
        f"conditions={validation.condition_count}, runs={validation.run_count}, "
        f"trace_rows={len(source_trace)}, elapsed_seconds={elapsed:.3f}"
    )
    print(conventional_all.to_string(index=False))
    print(event_summary.to_string(index=False))
    print(comparison.to_string(index=False))
    for path in generated:
        print(f"wrote {path} ({path.stat().st_size} bytes)")
    return generated


def _deterministic_permutation(length: int, run_seed: int, step: int) -> list[int]:
    permutation = list(range(length))
    state = _mix64(
        (run_seed & _MASK_64)
        ^ (step & _MASK_64)
        ^ _SHUFFLE_STREAM_CONSTANT
    )
    for index in range(length - 1, 0, -1):
        state = (state + _SPLITMIX_GAMMA) & _MASK_64
        draw = _mix64(state)
        selected = draw % (index + 1)
        permutation[index], permutation[selected] = (
            permutation[selected],
            permutation[index],
        )
    return permutation


def _mix64(value: int) -> int:
    value &= _MASK_64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK_64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK_64
    return (value ^ (value >> 31)) & _MASK_64


def _summarize_events(events: pd.DataFrame) -> pd.DataFrame:
    keys = ["condition_index", "L", "C", "budget_mode", "order_mode"]
    summary = (
        events.groupby(keys, sort=True)
        .agg(
            event_run_count=("run", "count"),
            event_p_after_mean=("p_after", "mean"),
            event_p_after_std=("p_after", "std"),
            event_delta_P_max_mean=("delta_P_max", "mean"),
            event_delta_P_max_std=("delta_P_max", "std"),
        )
        .reset_index()
    )
    summary["event_p_after_sem"] = summary["event_p_after_std"] / np.sqrt(
        summary["event_run_count"]
    )
    return summary


def _comparison(
    conventional: pd.DataFrame, event_summary: pd.DataFrame
) -> pd.DataFrame:
    metrics = conventional.merge(
        event_summary,
        on=["condition_index", "L", "C", "budget_mode", "order_mode"],
        validate="one_to_one",
    )
    rows: list[dict[str, object]] = []
    for keys, condition in metrics.groupby(
        ["condition_index", "L", "C", "budget_mode"], sort=True
    ):
        condition_index, L, C, budget_mode = keys
        rows.append(
            {
                "condition_index": int(condition_index),
                "L": int(L),
                "C": int(C),
                "budget_mode": str(budget_mode),
                "conventional_p_range": _range(
                    condition["pseudocritical_p_conventional"]
                ),
                "peak_mean_S_relative_range": _relative_range(
                    condition["peak_mean_cluster_size"]
                ),
                "mean_P_at_peak_range": _range(
                    condition["largest_cluster_fraction_at_peak"]
                ),
                "event_p_mean_range": _range(condition["event_p_after_mean"]),
                "event_delta_P_max_mean_range": _range(
                    condition["event_delta_P_max_mean"]
                ),
            }
        )
    return pd.DataFrame(rows)


def _range(values: pd.Series) -> float:
    return float(values.max() - values.min())


def _relative_range(values: pd.Series) -> float:
    mean = float(values.mean())
    return 0.0 if mean == 0.0 else _range(values) / mean


def _assert_c1_invariance(comparison: pd.DataFrame) -> None:
    c1 = comparison.loc[comparison["C"] == 1]
    metric_columns = [column for column in comparison.columns if column.endswith("range")]
    if not np.allclose(c1[metric_columns].to_numpy(float), 0.0, atol=1.0e-12):
        raise ValueError("C=1 order sensitivity must be zero within floating-point tolerance")


def _plot_comparisons(
    manifest: pd.DataFrame,
    ensembles: dict[str, pd.DataFrame],
    events: pd.DataFrame,
    figure_directory: Path,
) -> list[Path]:
    generated: list[Path] = []
    # C=1 is numerically identical by construction; prioritize the two cases
    # where within-path edge order can change intermediate states.
    selected = manifest.loc[manifest["C"] != 1]
    colors = {
        SOURCE_TO_TARGET: "tab:blue",
        TARGET_TO_SOURCE: "tab:orange",
        DETERMINISTIC_SHUFFLE: "tab:green",
    }
    for condition in selected.itertuples(index=False):
        condition_index = int(condition.condition_index)
        condition_name = (
            "UNBOUNDED" if condition.budget_mode == "UNBOUNDED" else f"C={condition.C}"
        )
        file_condition = "UNBOUNDED" if condition.budget_mode == "UNBOUNDED" else f"C={condition.C}"
        for mean_column, y_label, suffix in (
            ("mean_cluster_size_mean", "Mean finite-cluster size S", "mean_S_vs_p"),
            (
                "largest_cluster_fraction_mean",
                "Mean largest-cluster fraction P",
                "mean_P_vs_p",
            ),
        ):
            output = figure_directory / f"L={condition.L}_{file_condition}_{suffix}.png"
            figure, axes = plt.subplots(figsize=(10, 6))
            for order_mode in ORDER_MODES:
                ensemble = ensembles[order_mode]
                curve = ensemble.loc[
                    (ensemble["condition_index"] == condition_index)
                    & (ensemble["n_eff"] == ensemble["runs"])
                ]
                axes.plot(
                    curve["p"],
                    curve[mean_column],
                    linewidth=2.2,
                    color=colors[order_mode],
                    label=order_mode,
                )
            axes.set_title(f"L={condition.L}, {condition_name}: within-path order")
            axes.set_xlabel("Removed edge fraction p")
            axes.set_ylabel(y_label)
            axes.grid(True, alpha=0.3)
            axes.legend()
            figure.tight_layout()
            figure.savefig(output, dpi=150)
            plt.close(figure)
            generated.append(output)

        output = figure_directory / f"L={condition.L}_{file_condition}_event_p_after.png"
        figure, axes = plt.subplots(figsize=(9, 6))
        condition_events = events.loc[events["condition_index"] == condition_index]
        for index, order_mode in enumerate(ORDER_MODES):
            values = condition_events.loc[
                condition_events["order_mode"] == order_mode, "p_after"
            ].to_numpy(float)
            offsets = np.linspace(-0.12, 0.12, len(values))
            axes.scatter(
                np.full(len(values), index) + offsets,
                values,
                color=colors[order_mode],
                alpha=0.75,
            )
            axes.scatter(index, values.mean(), marker="D", color="black", zorder=5)
        axes.set_xticks(range(len(ORDER_MODES)), ORDER_MODES, rotation=10)
        axes.set_title(f"L={condition.L}, {condition_name}: event locations")
        axes.set_xlabel("Within-path order")
        axes.set_ylabel("Event p after deletion")
        axes.grid(True, axis="y", alpha=0.3)
        figure.tight_layout()
        figure.savefig(output, dpi=150)
        plt.close(figure)
        generated.append(output)
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    analyze_order_sensitivity(arguments.manifest, arguments.output)


if __name__ == "__main__":
    main()
