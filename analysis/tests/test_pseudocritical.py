import math

import pandas as pd

from analysis.pseudocritical import (
    extract_conventional_peaks,
    extract_run_peaks,
    summarize_run_peaks,
)


def test_conventional_peak_uses_complete_grid_and_smallest_p_on_tie():
    ensemble = pd.DataFrame(
        {
            "condition_index": [0, 0, 0],
            "L": [4, 4, 4],
            "C": [2, 2, 2],
            "budget_mode": ["FINITE"] * 3,
            "runs": [2, 2, 2],
            "k": [1, 2, 3],
            "p": [0.25, 0.5, 0.75],
            "n_eff": [2, 2, 1],
            "mean_cluster_size_mean": [5.0, 5.0, 99.0],
            "largest_cluster_fraction_mean": [0.8, 0.6, 0.4],
        }
    )

    peak = extract_conventional_peaks(ensemble).iloc[0]

    assert peak["pseudocritical_k"] == 1
    assert peak["pseudocritical_p_conventional"] == 0.25
    assert peak["peak_mean_cluster_size"] == 5.0
    assert peak["largest_cluster_fraction_at_peak"] == 0.8
    assert peak["n_eff"] == 2


def test_run_peaks_tie_break_and_summary_statistics():
    results = pd.DataFrame(
        {
            "condition_index": [0] * 5,
            "run": [0, 0, 0, 1, 1],
            "L": [4] * 5,
            "C": [2] * 5,
            "budget_mode": ["FINITE"] * 5,
            "removed_edge_fraction": [0.1, 0.3, 0.2, 0.1, 0.4],
            "mean_cluster_size": [0.0, 4.0, 4.0, 0.0, 5.0],
            "largest_cluster_fraction": [1.0, 0.6, 0.7, 1.0, 0.5],
            "step": [0, 3, 2, 0, 4],
            "removed_edges": [0, 3, 2, 0, 4],
        }
    )

    peaks = extract_run_peaks(results)
    summary = summarize_run_peaks(peaks).iloc[0]

    assert list(peaks["pseudocritical_p_run"]) == [0.2, 0.4]
    assert list(peaks["step_at_peak"]) == [2, 4]
    assert math.isclose(summary["pseudocritical_p_run_mean"], 0.3)
    assert math.isclose(summary["pseudocritical_p_run_median"], 0.3)
    assert math.isclose(summary["pseudocritical_p_run_std"], math.sqrt(0.02))
    assert math.isclose(summary["pseudocritical_p_run_sem"], 0.1)
