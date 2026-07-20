from __future__ import annotations

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from analysis.stop_extension import analyze_stop_extension, summarize_stop_extension


def test_extracts_thresholds_costs_and_late_peaks_without_mutating_input() -> None:
    results = _results(
        P=[1.0, 14 / 16, 12 / 16, 10 / 16, 8 / 16, 6 / 16, 5 / 16,
           4 / 16, 1 / 16],
        S=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 12.0],
        steps=[0, 2, 4, 6, 8, 10, 12, 20, 31],
    )
    original = results.copy(deep=True)

    runs = analyze_stop_extension(results, extended_multiplier=0.5)
    row = runs.iloc[0]

    assert row["old_threshold_step"] == 20
    assert row["extended_threshold_step"] == 31
    assert np.isclose(row["old_threshold_p"], 7 / 24)
    assert np.isclose(row["extended_threshold_p"], 8 / 24)
    assert row["additional_steps"] == 11
    assert row["additional_accepted_requests"] == 1
    assert row["additional_removed_edges"] == 1
    assert row["additional_rows"] == 1
    assert bool(row["S_peak_after_old"])
    assert bool(row["request_event_after_old"])
    assert not bool(row["transition_width_changed"])
    assert_frame_equal(results, original)


def test_reports_no_late_event_and_preserves_missing_thresholds() -> None:
    complete = _results(
        P=[1.0, 0.7, 0.2, 0.1],
        S=[0.0, 9.0, 4.0, 2.0],
        steps=[0, 1, 2, 3],
    )
    missing = _results(
        P=[1.0, 0.8, 0.6],
        S=[0.0, 2.0, 3.0],
        steps=[0, 1, 2],
        run=1,
    )
    runs = analyze_stop_extension(
        pd.concat([complete, missing], ignore_index=True), extended_multiplier=0.5
    )

    first = runs.loc[runs["run"] == 0].iloc[0]
    second = runs.loc[runs["run"] == 1].iloc[0]
    assert not bool(first["S_peak_after_old"])
    assert not bool(first["request_event_after_old"])
    assert not bool(second["old_threshold_reached"])
    assert not bool(second["extended_threshold_reached"])
    assert np.isnan(second["additional_steps"])

    summary = summarize_stop_extension(runs)
    assert summary.iloc[0]["runs"] == 2
    assert summary.iloc[0]["valid_runs"] == 1
    assert summary.iloc[0]["missing_old_threshold_runs"] == 1
    assert summary.iloc[0]["missing_extended_threshold_runs"] == 1


def _results(P, S, steps, run: int = 0) -> pd.DataFrame:
    length = len(P)
    removed = np.arange(length)
    L = 4
    M0 = 2 * L * (L - 1)
    return pd.DataFrame(
        {
            "condition_index": 0,
            "run": run,
            "L": L,
            "C": 2,
            "budget_mode": "FINITE",
            "step": steps,
            "removed_edges": removed,
            "remaining_edges": M0 - removed,
            "removed_edge_fraction": removed / M0,
            "largest_cluster_size": np.rint(np.asarray(P) * L * L).astype(int),
            "largest_cluster_fraction": P,
            "second_largest_cluster_size": 0,
            "mean_cluster_size": S,
            "accepted_requests": removed,
            "rejected_requests": np.asarray(steps) - removed,
            "seed": 42,
            "result_path": "results.csv",
        }
    )
