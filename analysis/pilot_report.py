"""Validate pilot output and summarize each L/C condition without averaging trajectories."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from analysis.io import load_sweep
from analysis.validation import validate_sweep


TIMING_COLUMNS = (
    "condition_index",
    "L",
    "C",
    "budget_mode",
    "max_steps",
    "elapsed_ms",
)


def create_pilot_summary(manifest_path: str | Path) -> pd.DataFrame:
    manifest, results = load_sweep(manifest_path)
    validation = validate_sweep(manifest, results)
    root = Path(manifest.attrs["manifest_path"]).parent
    timing_path = root / "execution_times.csv"
    timings = pd.read_csv(timing_path, encoding="utf-8")
    missing = [column for column in TIMING_COLUMNS if column not in timings.columns]
    if missing:
        raise ValueError(f"execution_times.csv is missing columns: {', '.join(missing)}")

    rows: list[dict[str, object]] = []
    for condition in manifest.itertuples(index=False):
        condition_results = results.loc[
            results["condition_index"] == condition.condition_index
        ]
        final_rows = condition_results.groupby("run", sort=True).tail(1)
        if len(final_rows) != int(condition.runs):
            raise ValueError(
                f"condition={condition.condition_index} has {len(final_rows)} final runs; "
                f"expected {condition.runs}"
            )
        all_edges_removed = final_rows["remaining_edges"] == 0
        max_steps = (final_rows["step"] == int(condition.max_steps)) & ~all_edges_removed
        if int(all_edges_removed.sum() + max_steps.sum()) != len(final_rows):
            raise ValueError(f"condition={condition.condition_index} has an unknown termination")

        timing = timings.loc[
            timings["condition_index"] == condition.condition_index, "elapsed_ms"
        ]
        if len(timing) != 1:
            raise ValueError(
                f"condition={condition.condition_index} must have exactly one timing row"
            )

        peak_index = condition_results["mean_cluster_size"].idxmax()
        peak_row = condition_results.loc[peak_index]
        same_run = condition_results.loc[condition_results["run"] == peak_row["run"]]
        peak_passed = bool(
            peak_row["mean_cluster_size"] > 0
            and same_run["removed_edge_fraction"].max()
            > peak_row["removed_edge_fraction"]
        )
        rows.append(
            {
                "condition_index": int(condition.condition_index),
                "L": int(condition.L),
                "C": int(condition.C),
                "budget_mode": condition.budget_mode,
                "elapsed_ms": int(timing.iloc[0]),
                "data_rows": len(condition_results),
                "final_steps": ";".join(
                    str(int(step)) for step in final_rows.sort_values("run")["step"]
                ),
                "final_p_min": final_rows["removed_edge_fraction"].min(),
                "final_p_mean": final_rows["removed_edge_fraction"].mean(),
                "final_p_max": final_rows["removed_edge_fraction"].max(),
                "final_P_min": final_rows["largest_cluster_fraction"].min(),
                "final_P_mean": final_rows["largest_cluster_fraction"].mean(),
                "final_P_max": final_rows["largest_cluster_fraction"].max(),
                "max_mean_cluster_size": peak_row["mean_cluster_size"],
                "peak_removed_edge_fraction": peak_row["removed_edge_fraction"],
                "max_steps_runs": int(max_steps.sum()),
                "all_edges_removed_runs": int(all_edges_removed.sum()),
                "transition_peak_passed": peak_passed,
                "invariants_valid": True,
                "P_monotonic": True,
                "removed_edges_monotonic": True,
            }
        )

    summary = pd.DataFrame(rows)
    summary_path = root / "pilot_summary.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8")
    print(
        "Validation succeeded: "
        f"conditions={validation.condition_count}, rows={validation.row_count}, "
        f"condition_runs={validation.run_count}"
    )
    print(summary.to_string(index=False))
    print(f"wrote {summary_path}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    arguments = parser.parse_args()
    create_pilot_summary(arguments.manifest)


if __name__ == "__main__":
    main()

