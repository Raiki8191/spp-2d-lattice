"""Exact edge-level reconstruction, ensembles, pseudocritical candidates, and plots."""

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

from analysis.edge_trace import (
    edge_endpoints,
    read_edge_traces,
    validate_trace_against_results,
)
from analysis.ensemble import aggregate_ensemble
from analysis.event_ensemble import extract_event_peaks, summarize_event_peaks
from analysis.io import load_sweep
from analysis.pseudocritical import extract_conventional_peaks
from analysis.resampling import resample_common_p_grid
from analysis.union_find import UnionFind
from analysis.validation import validate_sweep


def reconstruct_exact_states(
    manifest: pd.DataFrame, traces: pd.DataFrame
) -> pd.DataFrame:
    """Reconstruct every attained edge count by adding removed edges in reverse."""

    rows: list[dict[str, object]] = []
    for condition in manifest.itertuples(index=False):
        L = int(condition.L)
        vertex_count = L * L
        edge_count = 2 * L * (L - 1)
        condition_trace = traces.loc[
            traces["condition_index"] == int(condition.condition_index)
        ]
        for run in range(int(condition.runs)):
            run_trace = condition_trace.loc[condition_trace["run"] == run].sort_values(
                "edge_order"
            )
            removed_ids = set(run_trace["edge_id"].astype(int).tolist())
            union_find = UnionFind(vertex_count)
            for edge_id in range(edge_count):
                if edge_id not in removed_ids:
                    union_find.union(*edge_endpoints(L, edge_id))

            removed_count = len(run_trace)
            rows.append(
                _state_row(condition, run, removed_count, edge_count, union_find)
            )
            for edge in run_trace.iloc[::-1].itertuples(index=False):
                union_find.union(*edge_endpoints(L, int(edge.edge_id)))
                rows.append(
                    _state_row(
                        condition,
                        run,
                        int(edge.edge_order),
                        edge_count,
                        union_find,
                    )
                )
    return pd.DataFrame(rows).sort_values(
        ["condition_index", "run", "k"], ignore_index=True
    )


def aggregate_exact_ensemble(exact_states: pd.DataFrame) -> pd.DataFrame:
    keys = ["condition_index", "L", "C", "budget_mode", "runs", "k", "p"]
    summary = (
        exact_states.groupby(keys, sort=True)
        .agg(
            n_eff=("largest_cluster_fraction", "count"),
            largest_cluster_fraction_mean=("largest_cluster_fraction", "mean"),
            largest_cluster_fraction_std=("largest_cluster_fraction", "std"),
            mean_cluster_size_mean=("mean_cluster_size", "mean"),
            mean_cluster_size_std=("mean_cluster_size", "std"),
        )
        .reset_index()
    )
    summary["largest_cluster_fraction_sem"] = (
        summary["largest_cluster_fraction_std"] / np.sqrt(summary["n_eff"])
    )
    summary["mean_cluster_size_sem"] = summary["mean_cluster_size_std"] / np.sqrt(
        summary["n_eff"]
    )
    return summary


def compare_resampling_methods(
    results: pd.DataFrame,
    manifest: pd.DataFrame,
    exact_conventional: pd.DataFrame,
) -> pd.DataFrame:
    post_grid = resample_common_p_grid(results, manifest)
    post_ensemble = aggregate_ensemble(post_grid)
    post_peaks = extract_conventional_peaks(post_ensemble)
    comparison = post_peaks.merge(
        exact_conventional,
        on=["condition_index", "L", "C", "budget_mode"],
        suffixes=("_post_request", "_exact"),
        validate="one_to_one",
    )
    comparison = comparison.rename(
        columns={
            "pseudocritical_p_conventional_post_request": "post_request_p",
            "pseudocritical_p_conventional_exact": "exact_edge_p",
            "peak_mean_cluster_size_post_request": "post_request_peak_mean_S",
            "peak_mean_cluster_size_exact": "exact_peak_mean_S",
            "largest_cluster_fraction_at_peak_post_request": "post_request_mean_P_at_peak",
            "largest_cluster_fraction_at_peak_exact": "exact_mean_P_at_peak",
        }
    )
    comparison["p_difference_exact_minus_post"] = (
        comparison["exact_edge_p"] - comparison["post_request_p"]
    )
    comparison["peak_mean_S_difference_exact_minus_post"] = (
        comparison["exact_peak_mean_S"] - comparison["post_request_peak_mean_S"]
    )
    comparison["mean_P_at_peak_difference_exact_minus_post"] = (
        comparison["exact_mean_P_at_peak"]
        - comparison["post_request_mean_P_at_peak"]
    )
    return comparison[
        [
            "condition_index",
            "L",
            "C",
            "budget_mode",
            "post_request_p",
            "exact_edge_p",
            "p_difference_exact_minus_post",
            "post_request_peak_mean_S",
            "exact_peak_mean_S",
            "peak_mean_S_difference_exact_minus_post",
            "post_request_mean_P_at_peak",
            "exact_mean_P_at_peak",
            "mean_P_at_peak_difference_exact_minus_post",
        ]
    ]


def analyze_exact(manifest_path: str | Path) -> list[Path]:
    started = time.perf_counter()
    manifest, results = load_sweep(manifest_path)
    validation = validate_sweep(manifest, results)
    traces = read_edge_traces(manifest)
    validate_trace_against_results(manifest, results, traces)
    exact_states = reconstruct_exact_states(manifest, traces)
    exact_ensemble = aggregate_exact_ensemble(exact_states)
    exact_conventional = extract_conventional_peaks(exact_ensemble)
    events = extract_event_peaks(exact_states, traces)
    event_summary = summarize_event_peaks(events)
    comparison = compare_resampling_methods(results, manifest, exact_conventional)

    root = Path(manifest.attrs["manifest_path"]).parent / "analysis-exact"
    figures = root / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    exact_ensemble.to_csv(root / "exact_ensemble_summary.csv", index=False)
    exact_conventional.to_csv(
        root / "exact_pseudocritical_conventional.csv", index=False
    )
    events.to_csv(root / "event_pseudocritical_runs.csv", index=False)
    event_summary.to_csv(root / "event_pseudocritical_summary.csv", index=False)
    comparison.to_csv(root / "resampling_method_comparison.csv", index=False)

    generated = _plot_exact(exact_ensemble, exact_conventional, events, figures)
    elapsed = time.perf_counter() - started
    print(
        "Exact validation succeeded: "
        f"conditions={validation.condition_count}, runs={validation.run_count}, "
        f"trace_rows={len(traces)}, exact_rows={len(exact_states)}, "
        f"elapsed_seconds={elapsed:.3f}"
    )
    print(exact_conventional.to_string(index=False))
    print(event_summary.to_string(index=False))
    print(comparison.to_string(index=False))
    for path in generated:
        print(f"wrote {path} ({path.stat().st_size} bytes)")
    return generated


def _state_row(
    condition: object,
    run: int,
    k: int,
    edge_count: int,
    union_find: UnionFind,
) -> dict[str, object]:
    vertex_count = int(condition.L) ** 2
    return {
        "condition_index": int(condition.condition_index),
        "run": run,
        "L": int(condition.L),
        "C": int(condition.C),
        "budget_mode": str(condition.budget_mode),
        "runs": int(condition.runs),
        "k": k,
        "removed_edges": k,
        "p": 0.0 if edge_count == 0 else k / edge_count,
        "removed_edge_fraction": 0.0 if edge_count == 0 else k / edge_count,
        "largest_cluster_size": union_find.largest_size,
        "largest_cluster_fraction": union_find.largest_size / vertex_count,
        "mean_cluster_size": union_find.mean_finite_cluster_size(),
    }


def _plot_exact(
    ensemble: pd.DataFrame,
    conventional: pd.DataFrame,
    events: pd.DataFrame,
    figure_directory: Path,
) -> list[Path]:
    generated: list[Path] = []
    for L in sorted(ensemble["L"].unique()):
        lattice = ensemble.loc[ensemble["L"] == L]
        colors = plt.get_cmap("tab10")
        color_by_condition = {
            condition: colors(index)
            for index, condition in enumerate(sorted(lattice["condition_index"].unique()))
        }
        for observable, sem, label, filename, mark_peak in (
            (
                "largest_cluster_fraction_mean",
                "largest_cluster_fraction_sem",
                "Mean largest-cluster fraction P",
                f"L={L}_exact_mean_P_vs_p.png",
                False,
            ),
            (
                "mean_cluster_size_mean",
                "mean_cluster_size_sem",
                "Mean finite-cluster size S",
                f"L={L}_exact_mean_S_vs_p.png",
                True,
            ),
        ):
            output = figure_directory / filename
            figure, axes = plt.subplots(figsize=(10, 6))
            for condition_index, condition in lattice.groupby("condition_index"):
                complete = condition.loc[condition["n_eff"] == condition["runs"]]
                first = complete.iloc[0]
                name = (
                    "UNBOUNDED"
                    if first["budget_mode"] == "UNBOUNDED"
                    else f"C={int(first['C'])}"
                )
                color = color_by_condition[condition_index]
                x = complete["p"].to_numpy(float)
                mean = complete[observable].to_numpy(float)
                error = complete[sem].fillna(0.0).to_numpy(float)
                axes.plot(x, mean, linewidth=2.4, color=color, label=name)
                axes.fill_between(x, mean - error, mean + error, color=color, alpha=0.2)
                if mark_peak:
                    peak = conventional.loc[
                        conventional["condition_index"] == condition_index
                    ].iloc[0]
                    axes.scatter(
                        peak["pseudocritical_p_conventional"],
                        peak["peak_mean_cluster_size"],
                        color=color,
                        edgecolor="black",
                        zorder=5,
                    )
            axes.set_title(f"L={L}: exact edge-level {label}")
            axes.set_xlabel("Removed edge fraction p")
            axes.set_ylabel(label)
            axes.grid(True, alpha=0.3)
            axes.legend()
            figure.tight_layout()
            figure.savefig(output, dpi=150)
            plt.close(figure)
            generated.append(output)

        output = figure_directory / f"L={L}_event_p_after.png"
        figure, axes = plt.subplots(figsize=(9, 6))
        lattice_events = events.loc[events["L"] == L]
        for index, (condition_index, condition) in enumerate(
            lattice_events.groupby("condition_index")
        ):
            first = condition.iloc[0]
            name = (
                "UNBOUNDED"
                if first["budget_mode"] == "UNBOUNDED"
                else f"C={int(first['C'])}"
            )
            offsets = np.linspace(-0.12, 0.12, len(condition))
            axes.scatter(
                np.full(len(condition), index) + offsets,
                condition["p_after"],
                alpha=0.75,
                label=name,
            )
            axes.scatter(index, condition["p_after"].mean(), marker="D", color="black")
        axes.set_xticks(range(lattice_events["condition_index"].nunique()))
        axes.set_xticklabels(
            [
                "UNBOUNDED" if group.iloc[0]["budget_mode"] == "UNBOUNDED" else f"C={int(group.iloc[0]['C'])}"
                for _, group in lattice_events.groupby("condition_index")
            ]
        )
        axes.set_title(f"L={L}: maximum single-edge-drop event locations")
        axes.set_xlabel("Budget condition")
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
    arguments = parser.parse_args()
    analyze_exact(arguments.manifest)


if __name__ == "__main__":
    main()
