"""Conventional ensemble and per-run pseudocritical-point candidates."""

from __future__ import annotations

import numpy as np
import pandas as pd


def extract_conventional_peaks(ensemble: pd.DataFrame) -> pd.DataFrame:
    """Select the full-ensemble mean-S maximum, breaking ties toward smaller p."""

    rows: list[pd.Series] = []
    for _, condition in ensemble.groupby("condition_index", sort=True):
        complete = condition.loc[condition["n_eff"] == condition["runs"]]
        complete = complete.dropna(subset=["mean_cluster_size_mean"])
        if complete.empty:
            raise ValueError(
                f"condition={int(condition['condition_index'].iloc[0])} "
                "has no grid point with all runs present"
            )
        selected = complete.sort_values(
            ["mean_cluster_size_mean", "p"], ascending=[False, True], kind="stable"
        ).iloc[0]
        rows.append(selected)

    peaks = pd.DataFrame(rows)
    return pd.DataFrame(
        {
            "condition_index": peaks["condition_index"].astype("int64"),
            "L": peaks["L"].astype("int64"),
            "C": peaks["C"].astype("int64"),
            "budget_mode": peaks["budget_mode"].to_numpy(),
            "pseudocritical_k": peaks["k"].astype("int64"),
            "pseudocritical_p_conventional": peaks["p"].to_numpy(),
            "peak_mean_cluster_size": peaks["mean_cluster_size_mean"].to_numpy(),
            "largest_cluster_fraction_at_peak": peaks[
                "largest_cluster_fraction_mean"
            ].to_numpy(),
            "n_eff": peaks["n_eff"].astype("int64"),
        }
    )


def extract_run_peaks(results: pd.DataFrame) -> pd.DataFrame:
    """Select each run's measured S maximum, breaking ties toward smaller p."""

    ordered = results.sort_values(
        [
            "condition_index",
            "run",
            "mean_cluster_size",
            "removed_edge_fraction",
            "step",
        ],
        ascending=[True, True, False, True, True],
        kind="stable",
    )
    peaks = ordered.groupby(["condition_index", "run"], sort=True).head(1)
    return pd.DataFrame(
        {
            "condition_index": peaks["condition_index"].astype("int64"),
            "run": peaks["run"].astype("int64"),
            "L": peaks["L"].astype("int64"),
            "C": peaks["C"].astype("int64"),
            "budget_mode": peaks["budget_mode"].to_numpy(),
            "pseudocritical_p_run": peaks["removed_edge_fraction"].to_numpy(),
            "peak_mean_cluster_size_run": peaks["mean_cluster_size"].to_numpy(),
            "largest_cluster_fraction_at_peak_run": peaks[
                "largest_cluster_fraction"
            ].to_numpy(),
            "step_at_peak": peaks["step"].astype("int64"),
            "removed_edges_at_peak": peaks["removed_edges"].astype("int64"),
        }
    ).reset_index(drop=True)


def summarize_run_peaks(run_peaks: pd.DataFrame) -> pd.DataFrame:
    """Summarize the distribution of per-run peak locations by condition.

    This distribution is not the same quantity as the conventional peak of the
    ensemble-mean S curve; both are retained and reported separately.
    """

    keys = ["condition_index", "L", "C", "budget_mode"]
    grouped = run_peaks.groupby(keys, sort=True)
    summary = grouped.agg(
        run_count=("pseudocritical_p_run", "count"),
        pseudocritical_p_run_mean=("pseudocritical_p_run", "mean"),
        pseudocritical_p_run_median=("pseudocritical_p_run", "median"),
        pseudocritical_p_run_std=("pseudocritical_p_run", "std"),
    ).reset_index()
    summary["pseudocritical_p_run_sem"] = (
        summary["pseudocritical_p_run_std"] / np.sqrt(summary["run_count"])
    )
    return summary
