"""Request-level pseudocritical events from ACCEPTED_REQUEST measurements."""

from __future__ import annotations

import numpy as np
import pandas as pd


def require_request_measurements(manifest: pd.DataFrame) -> None:
    """Reject sparse measurement modes before interpreting rows as requests."""

    if "measurement_mode" not in manifest.columns:
        raise ValueError("request analysis requires manifest measurement_mode")
    if (manifest["measurement_mode"] != "ACCEPTED_REQUEST").any():
        raise ValueError("request analysis requires ACCEPTED_REQUEST measurements")


def build_request_transitions(results: pd.DataFrame) -> pd.DataFrame:
    """Return graph-changing transitions between consecutive measured states."""

    if results is None:
        raise ValueError("results must not be None")
    required = {
        "condition_index",
        "run",
        "L",
        "C",
        "budget_mode",
        "step",
        "removed_edges",
        "removed_edge_fraction",
        "largest_cluster_size",
        "largest_cluster_fraction",
        "mean_cluster_size",
    }
    missing = sorted(required.difference(results.columns))
    if missing:
        raise ValueError(f"results is missing columns: {', '.join(missing)}")

    frames: list[pd.DataFrame] = []
    for (condition_index, run), group in results.groupby(
        ["condition_index", "run"], sort=True
    ):
        ordered = group.sort_values("step").reset_index(drop=True)
        before = ordered.shift(1)
        changing = ordered["removed_edges"] > before["removed_edges"]
        if "accepted_requests" in ordered.columns:
            increments = ordered["accepted_requests"] - before["accepted_requests"]
            if (changing & (increments != 1)).any():
                raise ValueError(
                    "request transitions require one accepted request per changed state "
                    f"at condition={int(condition_index)}, run={int(run)}"
                )
            unchanged = before["accepted_requests"].notna() & ~changing
            if (unchanged & (increments != 0)).any():
                raise ValueError(
                    "unchanged state has a nonzero accepted-request increment "
                    f"at condition={int(condition_index)}, run={int(run)}"
                )
        after_rows = ordered.loc[changing]
        before_rows = before.loc[changing]
        if after_rows.empty:
            continue
        frame = pd.DataFrame(
            {
                "condition_index": int(condition_index),
                "run": int(run),
                "L": after_rows["L"].astype("int64").to_numpy(),
                "C": after_rows["C"].astype("int64").to_numpy(),
                "budget_mode": after_rows["budget_mode"].astype(str).to_numpy(),
                "step": after_rows["step"].astype("int64").to_numpy(),
                "p_before": before_rows["removed_edge_fraction"].to_numpy(float),
                "p_after": after_rows["removed_edge_fraction"].to_numpy(float),
                "removed_edges_before": before_rows["removed_edges"]
                .astype("int64")
                .to_numpy(),
                "removed_edges_after": after_rows["removed_edges"]
                .astype("int64")
                .to_numpy(),
                "P_before": before_rows["largest_cluster_fraction"].to_numpy(float),
                "P_after": after_rows["largest_cluster_fraction"].to_numpy(float),
                "largest_cluster_size_before": before_rows["largest_cluster_size"]
                .astype("int64")
                .to_numpy(),
                "largest_cluster_size_after": after_rows["largest_cluster_size"]
                .astype("int64")
                .to_numpy(),
                "S_before": before_rows["mean_cluster_size"].to_numpy(float),
                "S_after": after_rows["mean_cluster_size"].to_numpy(float),
            }
        )
        frame["delta_p_request"] = frame["p_after"] - frame["p_before"]
        frame["path_length"] = (
            frame["removed_edges_after"] - frame["removed_edges_before"]
        )
        frame["delta_P_request"] = frame["P_before"] - frame["P_after"]
        frame["delta_largest_cluster_size"] = (
            frame["largest_cluster_size_before"]
            - frame["largest_cluster_size_after"]
        )
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def extract_request_events(transitions: pd.DataFrame) -> pd.DataFrame:
    """Select maximum request-level P drop, then smaller p_after and step."""

    rows: list[pd.Series] = []
    for _, group in transitions.groupby(["condition_index", "run"], sort=True):
        # The integer size drop is exactly proportional to delta P for one L and
        # avoids floating-point artifacts when mathematically equal drops tie.
        selected = group.sort_values(
            ["delta_largest_cluster_size", "p_after", "step"],
            ascending=[False, True, True],
        ).iloc[0]
        rows.append(selected)
    return pd.DataFrame(rows).reset_index(drop=True)


def summarize_request_events(events: pd.DataFrame) -> pd.DataFrame:
    keys = ["condition_index", "L", "C", "budget_mode"]
    summary = (
        events.groupby(keys, sort=True)
        .agg(
            event_run_count=("run", "count"),
            event_p_after_mean=("p_after", "mean"),
            event_p_after_std=("p_after", "std"),
            event_p_after_median=("p_after", "median"),
            event_p_before_mean=("p_before", "mean"),
            delta_P_request_mean=("delta_P_request", "mean"),
            delta_P_request_std=("delta_P_request", "std"),
            path_length_mean=("path_length", "mean"),
            path_length_std=("path_length", "std"),
            P_before_mean=("P_before", "mean"),
            P_after_mean=("P_after", "mean"),
            S_before_mean=("S_before", "mean"),
            S_after_mean=("S_after", "mean"),
        )
        .reset_index()
    )
    summary["event_p_after_sem"] = summary["event_p_after_std"] / np.sqrt(
        summary["event_run_count"]
    )
    return summary
