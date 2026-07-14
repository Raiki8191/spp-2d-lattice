import math

import numpy as np
import pandas as pd

from analysis.ensemble import aggregate_ensemble


def test_n_eff_mean_std_and_sem_match_hand_calculation_with_missing_values():
    resampled = pd.DataFrame(
        {
            "condition_index": [0] * 6,
            "L": [2] * 6,
            "C": [1] * 6,
            "budget_mode": ["FINITE"] * 6,
            "runs": [2] * 6,
            "run": [0, 1, 0, 1, 0, 1],
            "k": [0, 0, 1, 1, 2, 2],
            "p": [0.0, 0.0, 0.25, 0.25, 0.5, 0.5],
            "largest_cluster_fraction": [1.0, 1.0, 0.5, 0.75, 0.25, np.nan],
            "mean_cluster_size": [0.0, 0.0, 2.0, 4.0, 6.0, np.nan],
            "second_largest_cluster_size": [0.0, 0.0, 1.0, 3.0, 2.0, np.nan],
        }
    )

    summary = aggregate_ensemble(resampled)
    k1 = summary.loc[summary["k"] == 1].iloc[0]
    k2 = summary.loc[summary["k"] == 2].iloc[0]

    assert k1["n_eff"] == 2
    assert k1["mean_cluster_size_mean"] == 3.0
    assert math.isclose(k1["mean_cluster_size_std"], math.sqrt(2.0))
    assert math.isclose(k1["mean_cluster_size_sem"], 1.0)
    assert k1["second_largest_cluster_size_mean"] == 2.0
    assert k2["n_eff"] == 1
    assert k2["mean_cluster_size_mean"] == 6.0
    assert math.isnan(k2["mean_cluster_size_std"])
    assert math.isnan(k2["mean_cluster_size_sem"])
