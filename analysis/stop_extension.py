"""Diagnostics comparing the legacy 1/L and extended multiplier/L stop positions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.request_event import build_request_transitions, extract_request_events
from analysis.transition_width import calculate_transition_widths


def analyze_stop_extension(
    results: pd.DataFrame, *, extended_multiplier: float = 0.5
) -> pd.DataFrame:
    """Compare threshold positions within one extended ACCEPTED_REQUEST data set.

    Missing threshold crossings remain NaN and are exposed through explicit boolean
    columns. The input frame is never modified.
    """

    if results is None:
        raise ValueError("results must not be None")
    if not np.isfinite(extended_multiplier) or extended_multiplier <= 0.0:
        raise ValueError("extended_multiplier must be finite and positive")

    transitions = build_request_transitions(results)
    events = extract_request_events(transitions) if not transitions.empty else pd.DataFrame()
    full_widths = calculate_transition_widths(results)
    rows: list[dict[str, object]] = []

    for (condition_index, run), group in results.groupby(
        ["condition_index", "run"], sort=True
    ):
        ordered = group.sort_values("step").reset_index(drop=True)
        first = ordered.iloc[0]
        L = int(first["L"])
        old_position = _first_position_at_or_below(ordered, 1.0 / L)
        extended_position = _first_position_at_or_below(
            ordered, extended_multiplier / L
        )
        old_reached = old_position is not None
        extended_reached = extended_position is not None

        row: dict[str, object] = {
            "condition_index": int(condition_index),
            "run": int(run),
            "L": L,
            "C": int(first["C"]),
            "budget_mode": str(first["budget_mode"]),
            "old_threshold": 1.0 / L,
            "extended_threshold": extended_multiplier / L,
            "old_threshold_reached": old_reached,
            "extended_threshold_reached": extended_reached,
        }
        for prefix, position in (
            ("old_threshold", old_position),
            ("extended_threshold", extended_position),
        ):
            selected = ordered.iloc[position] if position is not None else None
            row[f"{prefix}_step"] = (
                int(selected["step"]) if selected is not None else np.nan
            )
            row[f"{prefix}_p"] = (
                float(selected["removed_edge_fraction"])
                if selected is not None
                else np.nan
            )
            row[f"{prefix}_P"] = (
                float(selected["largest_cluster_fraction"])
                if selected is not None
                else np.nan
            )

        if old_reached and extended_reached:
            old = ordered.iloc[old_position]
            extended = ordered.iloc[extended_position]
            row["additional_steps"] = int(extended["step"] - old["step"])
            row["additional_accepted_requests"] = int(
                extended["accepted_requests"] - old["accepted_requests"]
            )
            row["additional_removed_edges"] = int(
                extended["removed_edges"] - old["removed_edges"]
            )
            row["additional_rows"] = int(extended_position - old_position)
            row["extended_to_old_step_ratio"] = (
                float(extended["step"]) / float(old["step"])
                if float(old["step"]) > 0.0
                else np.nan
            )
            row["extended_to_old_rows_ratio"] = (
                float(extended_position + 1) / float(old_position + 1)
            )

            maximum_s = float(ordered["mean_cluster_size"].max())
            first_s_peak = int(
                np.flatnonzero(
                    np.isclose(
                        ordered["mean_cluster_size"].to_numpy(float),
                        maximum_s,
                        rtol=1.0e-12,
                        atol=1.0e-12,
                    )
                )[0]
            )
            row["S_peak_after_old"] = first_s_peak > old_position
            row["post_request_conventional_peak_after_old"] = (
                first_s_peak > old_position
            )

            matching_event = events.loc[
                (events["condition_index"] == condition_index)
                & (events["run"] == run)
            ]
            row["request_event_after_old"] = (
                not matching_event.empty
                and int(matching_event.iloc[0]["step"]) > int(old["step"])
            )

            truncated = ordered.iloc[: old_position + 1].copy()
            truncated_width = calculate_transition_widths(truncated).iloc[0]
            full_width = full_widths.loc[
                (full_widths["condition_index"] == condition_index)
                & (full_widths["run"] == run)
            ].iloc[0]
            row["transition_width_changed"] = not _same_width(
                truncated_width, full_width
            )
        else:
            for column in (
                "additional_steps",
                "additional_accepted_requests",
                "additional_removed_edges",
                "additional_rows",
                "extended_to_old_step_ratio",
                "extended_to_old_rows_ratio",
            ):
                row[column] = np.nan
            row["S_peak_after_old"] = pd.NA
            row["post_request_conventional_peak_after_old"] = pd.NA
            row["request_event_after_old"] = pd.NA
            row["transition_width_changed"] = pd.NA
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_stop_extension(runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate extension cost and late-event diagnostics by condition."""

    keys = ["condition_index", "L", "C", "budget_mode"]
    rows: list[dict[str, object]] = []
    for key_values, group in runs.groupby(keys, sort=True):
        condition_index, L, C, budget_mode = key_values
        valid = group.loc[
            group["old_threshold_reached"] & group["extended_threshold_reached"]
        ]
        row: dict[str, object] = {
            "condition_index": int(condition_index),
            "L": int(L),
            "C": int(C),
            "budget_mode": str(budget_mode),
            "runs": len(group),
            "valid_runs": len(valid),
            "missing_old_threshold_runs": int(
                (~group["old_threshold_reached"]).sum()
            ),
            "missing_extended_threshold_runs": int(
                (~group["extended_threshold_reached"]).sum()
            ),
            "S_peak_after_old_runs": int(
                valid["S_peak_after_old"].astype(bool).sum()
            ),
            "request_event_after_old_runs": int(
                valid["request_event_after_old"].astype(bool).sum()
            ),
            "transition_width_changed_runs": int(
                valid["transition_width_changed"].astype(bool).sum()
            ),
        }
        for column in ("additional_steps", "additional_rows"):
            row[f"{column}_mean"] = valid[column].mean()
            row[f"{column}_median"] = valid[column].median()
            row[f"{column}_max"] = valid[column].max()
        row["additional_accepted_requests_mean"] = valid[
            "additional_accepted_requests"
        ].mean()
        row["additional_removed_edges_mean"] = valid[
            "additional_removed_edges"
        ].mean()
        row["old_final_p_mean"] = valid["old_threshold_p"].mean()
        row["extended_final_p_mean"] = valid["extended_threshold_p"].mean()
        row["extended_to_old_step_ratio_mean"] = valid[
            "extended_to_old_step_ratio"
        ].mean()
        row["extended_to_old_rows_ratio_mean"] = valid[
            "extended_to_old_rows_ratio"
        ].mean()
        rows.append(row)
    return pd.DataFrame(rows)


def _first_position_at_or_below(
    ordered: pd.DataFrame, threshold: float
) -> int | None:
    positions = np.flatnonzero(
        ordered["largest_cluster_fraction"].to_numpy(float) <= threshold
    )
    return int(positions[0]) if len(positions) else None


def _same_width(first: pd.Series, second: pd.Series) -> bool:
    for column in ("p1", "p2", "delta_p", "t1", "t2", "delta_t"):
        first_value = float(first[column])
        second_value = float(second[column])
        if np.isnan(first_value) and np.isnan(second_value):
            continue
        if not np.isclose(first_value, second_value, rtol=1.0e-12, atol=1.0e-12):
            return False
    return True
