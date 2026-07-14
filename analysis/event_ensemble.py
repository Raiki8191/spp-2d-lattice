"""Single-edge maximum-drop event ensemble from exact reconstructed states.

ACCEPTED_REQUEST is only a measurement trigger after a whole path request.  It
is not the event-based ensemble defined here, which selects one deleted edge by
the largest single-edge drop of the largest-cluster fraction in each run.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def extract_event_peaks(exact_states: pd.DataFrame, traces: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (condition_index, run), states in exact_states.groupby(
        ["condition_index", "run"], sort=True
    ):
        ordered = states.sort_values("k").reset_index(drop=True)
        if len(ordered) < 2:
            continue
        # Largest-size drops are integers, so they provide an exact tie-break for
        # mathematically equal deltaP values without floating-point roundoff.
        size_drops = ordered["largest_cluster_size"].shift(1) - ordered[
            "largest_cluster_size"
        ]
        maximum_size_drop = size_drops.iloc[1:].max()
        peak_index = int(size_drops[size_drops == maximum_size_drop].index[0])
        before = ordered.iloc[peak_index - 1]
        after = ordered.iloc[peak_index]
        k_after = int(after["k"])
        trace = traces.loc[
            (traces["condition_index"] == condition_index)
            & (traces["run"] == run)
            & (traces["edge_order"] == k_after - 1)
        ]
        if len(trace) != 1:
            raise ValueError(
                f"missing event edge at condition={condition_index}, run={run}, k={k_after}"
            )
        edge = trace.iloc[0]
        rows.append(
            {
                "condition_index": int(condition_index),
                "run": int(run),
                "L": int(after["L"]),
                "C": int(after["C"]),
                "budget_mode": str(after["budget_mode"]),
                "p_before": float(before["p"]),
                "p_after": float(after["p"]),
                "k_before": int(before["k"]),
                "k_after": k_after,
                "delta_P_max": float(
                    before["largest_cluster_fraction"]
                    - after["largest_cluster_fraction"]
                ),
                "P_before": float(before["largest_cluster_fraction"]),
                "P_after": float(after["largest_cluster_fraction"]),
                "S_before": float(before["mean_cluster_size"]),
                "S_after": float(after["mean_cluster_size"]),
                "step": int(edge["step"]),
                "edge_id": int(edge["edge_id"]),
            }
        )
    return pd.DataFrame(rows)


def summarize_event_peaks(events: pd.DataFrame) -> pd.DataFrame:
    keys = ["condition_index", "L", "C", "budget_mode"]
    summary = (
        events.groupby(keys, sort=True)["p_after"]
        .agg(event_run_count="count", p_after_mean="mean", p_after_std="std")
        .reset_index()
    )
    summary["p_after_sem"] = summary["p_after_std"] / np.sqrt(
        summary["event_run_count"]
    )
    return summary
