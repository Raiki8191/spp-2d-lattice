"""Request-state transition widths without interpolation."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_transition_widths(results: pd.DataFrame) -> pd.DataFrame:
    """Calculate p/step widths, leaving uncrossed thresholds as NaN."""

    if results is None:
        raise ValueError("results must not be None")
    rows: list[dict[str, object]] = []
    for (condition_index, run), group in results.groupby(
        ["condition_index", "run"], sort=True
    ):
        ordered = group.sort_values("step")
        first = ordered.iloc[0]
        L = int(first["L"])
        p2, t2 = _last_above_if_crossed(ordered, 0.5)
        p1, t1 = _last_above_if_crossed(ordered, 1.0 / L)
        valid = not any(np.isnan(value) for value in (p2, t2, p1, t1))
        delta_p = p1 - p2 if valid else np.nan
        delta_t = t1 - t2 if valid else np.nan
        rows.append(
            {
                "condition_index": int(condition_index),
                "run": int(run),
                "L": L,
                "C": int(first["C"]),
                "budget_mode": str(first["budget_mode"]),
                "lower_threshold": 1.0 / L,
                "p2": p2,
                "p1": p1,
                "delta_p": delta_p,
                "t2": t2,
                "t1": t1,
                "delta_t": delta_t,
                "delta_t_normalized": delta_t / (L**4) if valid else np.nan,
                "thresholds_crossed": valid,
            }
        )
    return pd.DataFrame(rows)


def summarize_transition_widths(widths: pd.DataFrame) -> pd.DataFrame:
    keys = ["condition_index", "L", "C", "budget_mode"]
    rows: list[dict[str, object]] = []
    for key_values, group in widths.groupby(keys, sort=True):
        condition_index, L, C, budget_mode = key_values
        valid = group.loc[group["thresholds_crossed"]]
        row: dict[str, object] = {
            "condition_index": int(condition_index),
            "L": int(L),
            "C": int(C),
            "budget_mode": str(budget_mode),
            "run_count": len(group),
            "valid_run_count": len(valid),
            "missing_run_count": len(group) - len(valid),
        }
        for column in ("delta_p", "delta_t", "delta_t_normalized"):
            row[f"{column}_mean"] = valid[column].mean()
            row[f"{column}_std"] = valid[column].std()
            row[f"{column}_sem"] = valid[column].sem()
            if column != "delta_t_normalized":
                row[f"{column}_median"] = valid[column].median()
        rows.append(row)
    return pd.DataFrame(rows)


def _last_above_if_crossed(
    ordered: pd.DataFrame, threshold: float
) -> tuple[float, float]:
    above = ordered["largest_cluster_fraction"] > threshold
    if not above.any() or not (~above).any():
        return np.nan, np.nan
    first_not_above_position = int(np.flatnonzero((~above).to_numpy())[0])
    candidates = ordered.iloc[:first_not_above_position].loc[above.iloc[:first_not_above_position]]
    if candidates.empty:
        return np.nan, np.nan
    selected = candidates.iloc[-1]
    return float(selected["removed_edge_fraction"]), float(selected["step"])
