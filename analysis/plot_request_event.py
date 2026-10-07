"""Request-level events, transition widths, edge comparison, and plots."""

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
from analysis.exact_ensemble import reconstruct_exact_states
from analysis.io import load_sweep
from analysis.order_sensitivity import ORDER_MODES, reorder_within_requests
from analysis.request_event import (
    build_request_transitions,
    extract_request_events,
    require_request_measurements,
    summarize_request_events,
)
from analysis.transition_width import (
    calculate_transition_widths,
    summarize_transition_widths,
)
from analysis.validation import validate_sweep


def analyze_request_events(
    manifest_path: str | Path,
    output_directory: str | Path | None = None,
    *,
    include_edge_comparison: bool = True,
) -> list[Path]:
    started = time.perf_counter()
    manifest, results = load_sweep(manifest_path)
    require_request_measurements(manifest)
    validation = validate_sweep(manifest, results)
    transitions = build_request_transitions(results)
    request_events = extract_request_events(transitions)
    request_summary = summarize_request_events(request_events)
    widths = calculate_transition_widths(results)
    width_summary = summarize_transition_widths(widths)

    edge_events = pd.DataFrame()
    comparison = pd.DataFrame()
    if include_edge_comparison:
        source_trace = read_edge_traces(manifest)
        validate_trace_against_results(manifest, results, source_trace)
        event_frames: list[pd.DataFrame] = []
        for order_mode in ORDER_MODES:
            trace = reorder_within_requests(source_trace, order_mode)
            exact_states = reconstruct_exact_states(manifest, trace)
            events = extract_event_peaks(exact_states, trace)
            events["order_mode"] = order_mode
            event_frames.append(events)
        edge_events = pd.concat(event_frames, ignore_index=True)
        comparison = compare_request_and_edge_events(request_summary, edge_events)
        _assert_c1_request_edge_equality(comparison)

    manifest_file = Path(manifest.attrs["manifest_path"])
    root = (
        Path(output_directory)
        if output_directory is not None
        else manifest_file.parent.parent / "request-analysis"
    ).resolve()
    figure_directory = root / "figures"
    figure_directory.mkdir(parents=True, exist_ok=True)
    request_events.to_csv(root / "request_event_runs.csv", index=False, encoding="utf-8")
    request_summary.to_csv(
        root / "request_event_summary.csv", index=False, encoding="utf-8"
    )
    widths.to_csv(root / "transition_width_runs.csv", index=False, encoding="utf-8")
    width_summary.to_csv(
        root / "transition_width_summary.csv", index=False, encoding="utf-8"
    )
    if include_edge_comparison:
        comparison.to_csv(
            root / "request_vs_edge_event_comparison.csv",
            index=False,
            encoding="utf-8",
        )
    generated = _plot_request_analysis(
        manifest,
        request_events,
        widths,
        edge_events,
        figure_directory,
    )
    elapsed = time.perf_counter() - started
    print(
        "Request-level validation succeeded: "
        f"conditions={validation.condition_count}, runs={validation.run_count}, "
        f"request_events={len(request_events)}, elapsed_seconds={elapsed:.3f}"
    )
    print(request_summary.to_string(index=False))
    print(width_summary.to_string(index=False))
    if include_edge_comparison:
        print(comparison.to_string(index=False))
    for path in generated:
        print(f"wrote {path} ({path.stat().st_size} bytes)")
    return generated


def compare_request_and_edge_events(
    request_summary: pd.DataFrame, edge_events: pd.DataFrame
) -> pd.DataFrame:
    edge_summary = (
        edge_events.groupby(
            ["condition_index", "L", "C", "budget_mode", "order_mode"],
            sort=True,
        )
        .agg(
            edge_event_p_after_mean=("p_after", "mean"),
            edge_event_delta_P_mean=("delta_P_max", "mean"),
        )
        .reset_index()
    )
    p_pivot = edge_summary.pivot(
        index=["condition_index", "L", "C", "budget_mode"],
        columns="order_mode",
        values="edge_event_p_after_mean",
    )
    delta_pivot = edge_summary.pivot(
        index=["condition_index", "L", "C", "budget_mode"],
        columns="order_mode",
        values="edge_event_delta_P_mean",
    )
    p_pivot.columns = [f"edge_event_p_after_mean_{column}" for column in p_pivot.columns]
    delta_pivot.columns = [f"edge_event_delta_P_mean_{column}" for column in delta_pivot.columns]
    edge_wide = p_pivot.join(delta_pivot).reset_index()
    comparison = request_summary[
        [
            "condition_index",
            "L",
            "C",
            "budget_mode",
            "event_p_after_mean",
            "delta_P_request_mean",
        ]
    ].merge(
        edge_wide,
        on=["condition_index", "L", "C", "budget_mode"],
        validate="one_to_one",
    )
    return comparison.rename(
        columns={
            "event_p_after_mean": "request_event_p_after_mean",
            "delta_P_request_mean": "request_event_delta_P_mean",
        }
    )


def _assert_c1_request_edge_equality(comparison: pd.DataFrame) -> None:
    c1 = comparison.loc[comparison["C"] == 1]
    p_columns = [
        column for column in comparison.columns if column.startswith("edge_event_p_after_mean_")
    ]
    delta_columns = [
        column for column in comparison.columns if column.startswith("edge_event_delta_P_mean_")
    ]
    for column in p_columns:
        if not np.allclose(c1[column], c1["request_event_p_after_mean"], atol=1.0e-12):
            raise ValueError(f"C=1 request/edge event p mismatch for {column}")
    for column in delta_columns:
        if not np.allclose(c1[column], c1["request_event_delta_P_mean"], atol=1.0e-12):
            raise ValueError(f"C=1 request/edge delta P mismatch for {column}")


def _plot_request_analysis(
    manifest: pd.DataFrame,
    request_events: pd.DataFrame,
    widths: pd.DataFrame,
    edge_events: pd.DataFrame,
    figure_directory: Path,
) -> list[Path]:
    generated: list[Path] = []
    for L in sorted(manifest["L"].unique()):
        condition_order = manifest.loc[manifest["L"] == L, "condition_index"].tolist()
        labels = []
        for condition_index in condition_order:
            condition = manifest.loc[manifest["condition_index"] == condition_index].iloc[0]
            labels.append(
                "UNBOUNDED"
                if condition["budget_mode"] == "UNBOUNDED"
                else f"C={int(condition['C'])}"
            )
        lattice_events = request_events.loc[request_events["L"] == L]
        lattice_widths = widths.loc[(widths["L"] == L) & widths["thresholds_crossed"]]
        generated.append(
            _distribution_plot(
                lattice_events,
                condition_order,
                labels,
                "p_after",
                f"L={L}: request-event locations",
                "Request event p after",
                figure_directory / f"L={L}_request_event_p_after.png",
            )
        )
        generated.append(
            _distribution_plot(
                lattice_events,
                condition_order,
                labels,
                "delta_P_request",
                f"L={L}: request-level largest-cluster drops",
                "Request delta P",
                figure_directory / f"L={L}_request_event_delta_P.png",
            )
        )
        generated.append(
            _distribution_plot(
                lattice_widths,
                condition_order,
                labels,
                "delta_p",
                f"L={L}: request-state transition widths",
                "Transition width delta p",
                figure_directory / f"L={L}_transition_delta_p.png",
            )
        )
        if not edge_events.empty:
            generated.append(
                _request_edge_plot(
                    lattice_events,
                    edge_events.loc[edge_events["L"] == L],
                    condition_order,
                    labels,
                    int(L),
                    figure_directory / f"L={L}_request_vs_edge_event_p.png",
                )
            )
    return generated


def _distribution_plot(
    data: pd.DataFrame,
    condition_order: list[int],
    labels: list[str],
    column: str,
    title: str,
    y_label: str,
    output: Path,
) -> Path:
    figure, axes = plt.subplots(figsize=(9, 6))
    for index, condition_index in enumerate(condition_order):
        values = data.loc[data["condition_index"] == condition_index, column].dropna().to_numpy(float)
        offsets = np.linspace(-0.12, 0.12, len(values)) if len(values) else np.array([])
        axes.scatter(np.full(len(values), index) + offsets, values, alpha=0.75)
        if len(values):
            axes.scatter(index, values.mean(), marker="D", color="black", zorder=5)
    axes.set_xticks(range(len(labels)), labels)
    axes.set_title(title)
    axes.set_xlabel("Budget condition")
    axes.set_ylabel(y_label)
    axes.grid(True, axis="y", alpha=0.3)
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)
    return output


def _request_edge_plot(
    request_events: pd.DataFrame,
    edge_events: pd.DataFrame,
    condition_order: list[int],
    labels: list[str],
    L: int,
    output: Path,
) -> Path:
    series = [("REQUEST", request_events.groupby("condition_index")["p_after"].mean())]
    for order_mode in ORDER_MODES:
        means = edge_events.loc[edge_events["order_mode"] == order_mode].groupby(
            "condition_index"
        )["p_after"].mean()
        series.append((order_mode, means))
    figure, axes = plt.subplots(figsize=(10, 6))
    x = np.arange(len(condition_order), dtype=float)
    offsets = np.linspace(-0.24, 0.24, len(series))
    markers = ("D", "o", "s", "^")
    for offset, marker, (name, means) in zip(offsets, markers, series):
        values = [means.loc[index] for index in condition_order]
        axes.scatter(x + offset, values, marker=marker, s=65, label=name)
    axes.set_xticks(x, labels)
    axes.set_title(f"L={L}: request-level and edge-level event locations")
    axes.set_xlabel("Budget condition")
    axes.set_ylabel("Mean event p after")
    axes.grid(True, axis="y", alpha=0.3)
    axes.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--request-only", action="store_true")
    arguments = parser.parse_args()
    analyze_request_events(
        arguments.manifest,
        arguments.output,
        include_edge_comparison=not arguments.request_only,
    )


if __name__ == "__main__":
    main()
