"""Run-ensemble statistics on the exact common removed-edge grid."""

from __future__ import annotations

import numpy as np
import pandas as pd


def aggregate_ensemble(resampled: pd.DataFrame) -> pd.DataFrame:
    """Aggregate means, sample standard deviations, and standard errors by grid point."""

    if resampled is None:
        raise ValueError("resampled must not be None")
    required = {
        "condition_index",
        "L",
        "C",
        "budget_mode",
        "runs",
        "k",
        "p",
        "largest_cluster_fraction",
        "mean_cluster_size",
        "second_largest_cluster_size",
    }
    missing = sorted(required.difference(resampled.columns))
    if missing:
        raise ValueError(f"resampled is missing columns: {', '.join(missing)}")

    keys = ["condition_index", "L", "C", "budget_mode", "runs", "k", "p"]
    grouped = resampled.groupby(keys, sort=True, dropna=False)
    summary = grouped.agg(
        n_eff=("largest_cluster_fraction", "count"),
        largest_cluster_fraction_mean=("largest_cluster_fraction", "mean"),
        largest_cluster_fraction_std=("largest_cluster_fraction", "std"),
        mean_cluster_size_mean=("mean_cluster_size", "mean"),
        mean_cluster_size_std=("mean_cluster_size", "std"),
        second_largest_cluster_size_mean=("second_largest_cluster_size", "mean"),
    ).reset_index()
    summary["largest_cluster_fraction_sem"] = (
        summary["largest_cluster_fraction_std"] / np.sqrt(summary["n_eff"])
    )
    summary["mean_cluster_size_sem"] = (
        summary["mean_cluster_size_std"] / np.sqrt(summary["n_eff"])
    )
    return summary[
        keys
        + [
            "n_eff",
            "largest_cluster_fraction_mean",
            "largest_cluster_fraction_std",
            "largest_cluster_fraction_sem",
            "mean_cluster_size_mean",
            "mean_cluster_size_std",
            "mean_cluster_size_sem",
            "second_largest_cluster_size_mean",
        ]
    ]
