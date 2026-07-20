"""Analyze the L=96,128 scaling-v2 transition-extension benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.io import load_sweep
from analysis.request_event import build_request_transitions
from analysis.request_fss import prepare_request_events
from analysis.stop_extension import analyze_stop_extension, summarize_stop_extension
from analysis.transition_width import calculate_transition_widths
from analysis.validation import validate_sweep


def analyze_benchmark(
    manifest_path: str | Path,
    output_directory: str | Path | None = None,
    *,
    scaling_v1_timing_path: str | Path | None = None,
) -> list[Path]:
    """Validate, summarize, project, and plot one scaling-v2 benchmark."""

    manifest, results = load_sweep(manifest_path)
    validation = validate_sweep(manifest, results)
    root = Path(manifest.attrs["manifest_path"]).parent
    output = Path(output_directory) if output_directory else root / "analysis"
    output.mkdir(parents=True, exist_ok=True)

    if "transition_threshold_multiplier" not in manifest.columns:
        raise ValueError("manifest is missing transition_threshold_multiplier")
    multipliers = manifest["transition_threshold_multiplier"].to_numpy(float)
    if not np.allclose(multipliers, 0.5, rtol=0.0, atol=0.0):
        raise ValueError("scaling-v2 benchmark requires threshold multiplier 0.5")

    timings = _read_timings(root / "execution_times.csv")
    run_summaries = _read_run_summaries(manifest)
    transitions = build_request_transitions(results)
    events = prepare_request_events(results)
    widths = calculate_transition_widths(results)
    extension_runs = analyze_stop_extension(results, extended_multiplier=0.5)
    extension_summary = summarize_stop_extension(extension_runs)
    condition_summary = _condition_summary(
        manifest,
        results,
        timings,
        run_summaries,
        transitions,
        events,
        widths,
    )

    v1_path = (
        Path(scaling_v1_timing_path)
        if scaling_v1_timing_path is not None
        else root.parent / "scaling-v1" / "execution_times.csv"
    )
    projections = _runtime_projections(condition_summary, v1_path)

    outputs = [
        output / "benchmark_condition_summary.csv",
        output / "benchmark_runtime_projection.csv",
        output / "stop_extension_runs.csv",
        output / "stop_extension_summary.csv",
    ]
    condition_summary.to_csv(outputs[0], index=False, encoding="utf-8")
    projections.to_csv(outputs[1], index=False, encoding="utf-8")
    extension_runs.to_csv(outputs[2], index=False, encoding="utf-8")
    extension_summary.to_csv(outputs[3], index=False, encoding="utf-8")
    outputs.extend(_plot_benchmark(results, events, extension_runs, output / "figures"))

    print(
        "Validation succeeded: "
        f"conditions={validation.condition_count}, rows={validation.row_count}, "
        f"condition_runs={validation.run_count}"
    )
    print(condition_summary.to_string(index=False))
    print(extension_summary.to_string(index=False))
    for path in outputs:
        print(f"wrote {path}")
    return outputs


def _condition_summary(
    manifest: pd.DataFrame,
    results: pd.DataFrame,
    timings: pd.DataFrame,
    run_summaries: pd.DataFrame,
    transitions: pd.DataFrame,
    events: pd.DataFrame,
    widths: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for condition in manifest.itertuples(index=False):
        condition_index = int(condition.condition_index)
        group = results.loc[results["condition_index"] == condition_index]
        final = group.sort_values(["run", "step"]).groupby("run", sort=True).tail(1)
        run_summary = run_summaries.loc[
            run_summaries["condition_index"] == condition_index
        ]
        event = events.loc[events["condition_index"] == condition_index]
        width = widths.loc[widths["condition_index"] == condition_index]
        transition = transitions.loc[
            transitions["condition_index"] == condition_index
        ]
        timing = timings.loc[timings["condition_index"] == condition_index]
        if len(timing) != 1 or len(run_summary) != int(condition.runs):
            raise ValueError(f"incomplete timing or run summary for condition={condition_index}")

        peak_candidates = group.sort_values(
            ["mean_cluster_size", "removed_edge_fraction"],
            ascending=[False, True],
        )
        peak = peak_candidates.iloc[0]
        result_path = Path(str(condition.result_path))
        summary_path = result_path.parent / "run_summary.csv"
        termination_counts = run_summary["termination_reason"].value_counts()
        row = {
            "condition_index": condition_index,
            "L": int(condition.L),
            "C": int(condition.C),
            "budget_mode": str(condition.budget_mode),
            "runs": int(condition.runs),
            "java_elapsed_seconds": float(timing.iloc[0]["elapsed_ms"]) / 1000.0,
            "run_elapsed_seconds_mean": run_summary["elapsed_milliseconds"].mean()
            / 1000.0,
            "run_elapsed_seconds_median": run_summary["elapsed_milliseconds"].median()
            / 1000.0,
            "run_elapsed_seconds_max": run_summary["elapsed_milliseconds"].max()
            / 1000.0,
            "termination_transition_window_complete": int(
                termination_counts.get("TRANSITION_WINDOW_COMPLETE", 0)
            ),
            "termination_max_steps": int(termination_counts.get("MAX_STEPS", 0)),
            "termination_all_edges_removed": int(
                termination_counts.get("ALL_EDGES_REMOVED", 0)
            ),
            "final_step_min": final["step"].min(),
            "final_step_mean": final["step"].mean(),
            "final_step_max": final["step"].max(),
            "final_p_min": final["removed_edge_fraction"].min(),
            "final_p_mean": final["removed_edge_fraction"].mean(),
            "final_p_max": final["removed_edge_fraction"].max(),
            "final_P_min": final["largest_cluster_fraction"].min(),
            "final_P_mean": final["largest_cluster_fraction"].mean(),
            "final_P_max": final["largest_cluster_fraction"].max(),
            "results_rows": len(group),
            "results_bytes": result_path.stat().st_size,
            "run_summary_bytes": summary_path.stat().st_size,
            "peak_mean_cluster_size": float(peak["mean_cluster_size"]),
            "peak_p": float(peak["removed_edge_fraction"]),
            "request_delta_P_mean": event["delta_P_max"].mean(),
            "request_p_mid_mean": event["p_mid"].mean(),
            "transition_delta_p_mean": width["delta_p"].mean(),
            "transition_delta_t_normalized_mean": width[
                "delta_t_normalized"
            ].mean(),
            "transition_valid_runs": int(width["thresholds_crossed"].sum()),
            "extended_threshold_reached_runs": int(
                (
                    final["largest_cluster_fraction"]
                    <= 0.5 / int(condition.L)
                ).sum()
            ),
            "results_dataframe_bytes": int(group.memory_usage(deep=True).sum()),
            "request_transition_dataframe_bytes": int(
                transition.memory_usage(deep=True).sum()
            ),
            "major_csv_bytes": result_path.stat().st_size + summary_path.stat().st_size,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def _runtime_projections(
    summary: pd.DataFrame, scaling_v1_timing_path: Path
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for item in summary.itertuples(index=False):
        for target_runs in (200, 400):
            factor = target_runs / int(item.runs)
            rows.append(
                {
                    "record_type": "CONDITION",
                    "scenario": f"{target_runs}_RUNS",
                    "L": int(item.L),
                    "C": int(item.C),
                    "budget_mode": str(item.budget_mode),
                    "target_runs": target_runs,
                    "basis_runs": int(item.runs),
                    "estimated_java_seconds": item.java_elapsed_seconds * factor,
                    "estimated_results_bytes": int(item.results_bytes * factor),
                    "estimated_analysis_memory_bytes": int(
                        (
                            item.results_dataframe_bytes
                            + item.request_transition_dataframe_bytes
                        )
                        * factor
                    ),
                    "projection_basis": "five-run linear scaling",
                }
            )

    if scaling_v1_timing_path.is_file():
        v1 = _read_timings(scaling_v1_timing_path)
        v1_seconds = float(v1["elapsed_ms"].sum()) / 1000.0
        v2_200 = sum(
            row["estimated_java_seconds"]
            for row in rows
            if row["record_type"] == "CONDITION" and row["target_runs"] == 200
        )
        for name, target_runs, total in (
            ("SCALING_V2_A", 200, v1_seconds + v2_200),
            ("SCALING_V2_B", 400, 2.0 * (v1_seconds + v2_200)),
        ):
            rows.append(
                {
                    "record_type": "CANDIDATE_TOTAL",
                    "scenario": name,
                    "L": pd.NA,
                    "C": pd.NA,
                    "budget_mode": "ALL",
                    "target_runs": target_runs,
                    "basis_runs": 5,
                    "estimated_java_seconds": total,
                    "estimated_results_bytes": pd.NA,
                    "estimated_analysis_memory_bytes": pd.NA,
                    "projection_basis": (
                        "scaling-v1 measured L<=64 plus five-run linear L=96,128"
                    ),
                }
            )
    return pd.DataFrame(rows)


def _read_timings(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"execution timing CSV does not exist: {path}")
    timing = pd.read_csv(path, encoding="utf-8")
    required = {"condition_index", "L", "C", "budget_mode", "max_steps", "elapsed_ms"}
    missing = sorted(required.difference(timing.columns))
    if missing:
        raise ValueError(f"timing CSV is missing columns: {', '.join(missing)}")
    return timing


def _read_run_summaries(manifest: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    required = {
        "run",
        "run_seed",
        "final_step",
        "final_removed_edges",
        "final_removed_edge_fraction",
        "final_largest_cluster_fraction",
        "termination_reason",
        "elapsed_milliseconds",
    }
    for condition in manifest.itertuples(index=False):
        path = Path(str(condition.result_path)).parent / "run_summary.csv"
        if not path.is_file():
            raise FileNotFoundError(
                f"run summary does not exist for condition={condition.condition_index}: {path}"
            )
        frame = pd.read_csv(path, encoding="utf-8")
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(f"run summary is missing columns: {', '.join(missing)}")
        frame = frame.copy()
        frame["condition_index"] = int(condition.condition_index)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def _plot_benchmark(
    results: pd.DataFrame,
    events: pd.DataFrame,
    extension_runs: pd.DataFrame,
    figure_directory: Path,
) -> list[Path]:
    figure_directory.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for L, size_group in results.groupby("L", sort=True):
        for observable, label, suffix in (
            ("largest_cluster_fraction", "P", "P_vs_p"),
            ("mean_cluster_size", "S", "S_vs_p"),
        ):
            figure, axis = plt.subplots(figsize=(8, 5))
            for (C, mode, run), group in size_group.groupby(
                ["C", "budget_mode", "run"], sort=True
            ):
                condition = "UNBOUNDED" if mode == "UNBOUNDED" else f"C={C}"
                axis.plot(
                    group["removed_edge_fraction"],
                    group[observable],
                    linewidth=0.9,
                    alpha=0.65,
                    label=f"{condition}, run={run}",
                )
            axis.set_xlabel("removed edge fraction p")
            axis.set_ylabel(label)
            axis.set_title(f"L={L}: raw {label}(p)")
            axis.legend(fontsize=6, ncol=2)
            axis.grid(alpha=0.25)
            figure.tight_layout()
            path = figure_directory / f"L={int(L)}_{suffix}.png"
            figure.savefig(path, dpi=160)
            plt.close(figure)
            outputs.append(path)

        figure, axis = plt.subplots(figsize=(8, 5))
        for (C, mode, run), group in size_group.groupby(
            ["C", "budget_mode", "run"], sort=True
        ):
            axis.plot(
                group["removed_edge_fraction"],
                group["largest_cluster_fraction"],
                linewidth=0.7,
                alpha=0.35,
            )
        stops = extension_runs.loc[extension_runs["L"] == L]
        axis.scatter(
            stops["old_threshold_p"],
            stops["old_threshold_P"],
            marker="o",
            s=25,
            label="first P <= 1/L",
        )
        axis.scatter(
            stops["extended_threshold_p"],
            stops["extended_threshold_P"],
            marker="x",
            s=30,
            label="first P <= 1/(2L)",
        )
        axis.axhline(1.0 / L, color="tab:orange", linestyle="--", linewidth=1)
        axis.axhline(0.5 / L, color="tab:red", linestyle=":", linewidth=1)
        axis.set_xlabel("removed edge fraction p")
        axis.set_ylabel("P")
        axis.set_title(f"L={L}: legacy and extended stop positions")
        axis.legend(fontsize=8)
        axis.grid(alpha=0.25)
        figure.tight_layout()
        path = figure_directory / f"L={int(L)}_stop_positions.png"
        figure.savefig(path, dpi=160)
        plt.close(figure)
        outputs.append(path)

        figure, axis = plt.subplots(figsize=(8, 5))
        event_group = events.loc[events["L"] == L]
        for (C, mode), group in event_group.groupby(["C", "budget_mode"], sort=True):
            label = "UNBOUNDED" if mode == "UNBOUNDED" else f"C={C}"
            axis.hist(
                group["delta_P_max"],
                bins=max(3, min(10, len(group))),
                histtype="step",
                linewidth=1.5,
                label=label,
            )
        axis.set_xlabel("request-level delta P")
        axis.set_ylabel("count")
        axis.set_title(f"L={L}: request-level P-drop distribution")
        axis.legend()
        axis.grid(alpha=0.25)
        figure.tight_layout()
        path = figure_directory / f"L={int(L)}_request_delta_P.png"
        figure.savefig(path, dpi=160)
        plt.close(figure)
        outputs.append(path)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--scaling-v1-timings", type=Path)
    arguments = parser.parse_args()
    analyze_benchmark(
        arguments.manifest,
        arguments.output,
        scaling_v1_timing_path=arguments.scaling_v1_timings,
    )


if __name__ == "__main__":
    main()
