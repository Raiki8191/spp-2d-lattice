from __future__ import annotations

import math

import numpy as np
import pandas as pd

from analysis.request_fss import (
    prepare_request_events,
    summarize_request_fss,
    transition_completion_diagnostics,
    validate_transition_complete_results,
)


def test_event_fields_and_bootstrap_are_reproducible() -> None:
    results = _results(two_runs=True)
    original = results.copy(deep=True)

    events = prepare_request_events(results)
    first = summarize_request_fss(events, bootstrap_samples=100, bootstrap_seed=7)
    second = summarize_request_fss(events, bootstrap_samples=100, bootstrap_seed=7)

    assert events["p_mid"].tolist() == [0.375, 0.375]
    assert events["delta_P_max"].tolist() == [0.5, 0.5]
    assert events["path_length"].tolist() == [1, 1]
    pd.testing.assert_frame_equal(first, second)
    pd.testing.assert_frame_equal(results, original)
    assert first.iloc[0]["p_mid_bootstrap_low"] == 0.375
    assert first.iloc[0]["p_mid_bootstrap_high"] == 0.375


def test_transition_validation_accepts_complete_window() -> None:
    validate_transition_complete_results(_results(two_runs=False))


def test_terminal_s_peak_is_reported_without_changing_stop_semantics() -> None:
    results = _results(two_runs=False).iloc[:-1].copy()

    diagnostics = transition_completion_diagnostics(results)

    assert diagnostics.iloc[0]["transition_stop_present"]
    assert not diagnostics.iloc[0]["S_max_before_final"]


def test_transition_validation_rejects_missing_terminal_threshold() -> None:
    results = _results(two_runs=False).iloc[:-2].copy()
    try:
        validate_transition_complete_results(results)
    except ValueError as error:
        assert "threshold" in str(error) or "stop state" in str(error)
    else:
        raise AssertionError("missing transition window was accepted")


def test_truncation_preserves_request_event_and_transition_width() -> None:
    truncated = _results(two_runs=False)
    full = pd.concat(
        [
            truncated,
            pd.DataFrame(
                [
                    {
                        **truncated.iloc[-1].to_dict(),
                        "step": 4,
                        "removed_edges": 4,
                        "removed_edge_fraction": 1.0,
                        "mean_cluster_size": 0.0,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    truncated_event = prepare_request_events(truncated)
    full_event = prepare_request_events(full)

    pd.testing.assert_frame_equal(truncated_event, full_event)
    from analysis.transition_width import calculate_transition_widths

    pd.testing.assert_frame_equal(
        calculate_transition_widths(truncated), calculate_transition_widths(full)
    )


def _results(two_runs: bool) -> pd.DataFrame:
    rows = []
    run_count = 2 if two_runs else 1
    for run in range(run_count):
        for step, removed, P, S in (
            (0, 0, 1.0, 0.0),
            (1, 1, 0.75, 1.0),
            (2, 2, 0.25, 3.0),
            (3, 3, 0.0, 1.0),
        ):
            rows.append(
                {
                    "condition_index": 0,
                    "run": run,
                    "L": 2,
                    "C": 1,
                    "budget_mode": "FINITE",
                    "step": step,
                    "removed_edges": removed,
                    "removed_edge_fraction": removed / 4,
                    "largest_cluster_size": round(P * 4),
                    "largest_cluster_fraction": P,
                    "mean_cluster_size": S,
                }
            )
    return pd.DataFrame(rows)
