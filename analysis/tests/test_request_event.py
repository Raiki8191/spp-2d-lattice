from __future__ import annotations

import math

import numpy as np
import pandas as pd

from analysis.edge_trace import edge_endpoints
from analysis.event_ensemble import extract_event_peaks
from analysis.exact_ensemble import reconstruct_exact_states
from analysis.plot_request_event import compare_request_and_edge_events
from analysis.request_event import (
    build_request_transitions,
    extract_request_events,
    summarize_request_events,
)
from analysis.transition_width import calculate_transition_widths


def test_request_transition_path_length_delta_and_input_immutability() -> None:
    results = results_frame(
        removed=[0, 2, 3],
        p=[0.0, 0.5, 0.75],
        P=[1.0, 0.75, 0.25],
        S=[0.0, 2.0, 1.0],
        steps=[0, 2, 5],
    )
    original = results.copy(deep=True)

    transitions = build_request_transitions(results)

    assert transitions["path_length"].tolist() == [2, 1]
    assert transitions["delta_P_request"].tolist() == [0.25, 0.5]
    assert transitions["delta_p_request"].tolist() == [0.5, 0.25]
    pd.testing.assert_frame_equal(results, original)


def test_request_event_tie_breaks_by_p_then_step() -> None:
    transitions = pd.DataFrame(
        {
            "condition_index": [0, 0, 0],
            "run": [0, 0, 0],
            "L": [2, 2, 2],
            "C": [2, 2, 2],
            "budget_mode": ["FINITE"] * 3,
            "step": [7, 3, 5],
            "p_after": [0.5, 0.25, 0.25],
            "delta_P_request": [0.2, 0.2, 0.2],
            "delta_largest_cluster_size": [2, 2, 2],
        }
    )

    event = extract_request_events(transitions).iloc[0]

    assert event["p_after"] == 0.25
    assert event["step"] == 3


def test_c1_request_and_edge_events_match() -> None:
    results = results_frame(
        removed=[0, 1, 2, 3, 4],
        p=[0.0, 0.25, 0.5, 0.75, 1.0],
        P=[1.0, 1.0, 0.75, 0.5, 0.25],
        S=[0.0, 0.0, 1.0, 1.5, 1.0],
        steps=[0, 1, 2, 3, 4],
    )
    request_events = extract_request_events(build_request_transitions(results))
    request_summary = summarize_request_events(request_events)
    manifest = manifest_frame()
    traces = trace_frame([0, 3, 1, 2])
    exact = reconstruct_exact_states(manifest, traces)
    edge_events = extract_event_peaks(exact, traces)
    edge_events["order_mode"] = "SOURCE_TO_TARGET"
    comparison = compare_request_and_edge_events(request_summary, edge_events).iloc[0]

    assert comparison["request_event_p_after_mean"] == comparison[
        "edge_event_p_after_mean_SOURCE_TO_TARGET"
    ]
    assert comparison["request_event_delta_P_mean"] == comparison[
        "edge_event_delta_P_mean_SOURCE_TO_TARGET"
    ]


def test_transition_thresholds_and_normalization() -> None:
    results = results_frame(
        removed=[0, 2, 4, 6],
        p=[0.0, 0.1, 0.2, 0.3],
        P=[1.0, 0.6, 0.4, 0.2],
        S=[0.0, 1.0, 2.0, 1.0],
        steps=[0, 10, 30, 70],
        L=4,
    )

    width = calculate_transition_widths(results).iloc[0]

    assert width["lower_threshold"] == 1 / math.sqrt(4**2) == 1 / 4
    assert width["p2"] == 0.1
    assert width["p1"] == 0.2
    assert math.isclose(width["delta_p"], 0.1)
    assert width["t2"] == 10
    assert width["t1"] == 30
    assert width["delta_t"] == 20
    assert math.isclose(width["delta_t_normalized"], 20 / (16**2))


def test_uncrossed_threshold_is_nan_not_zero() -> None:
    results = results_frame(
        removed=[0, 1, 2],
        p=[0.0, 0.1, 0.2],
        P=[1.0, 0.8, 0.6],
        S=[0.0, 1.0, 2.0],
        steps=[0, 1, 2],
        L=4,
    )

    width = calculate_transition_widths(results).iloc[0]

    assert not width["thresholds_crossed"]
    assert np.isnan(width["p2"])
    assert np.isnan(width["p1"])
    assert np.isnan(width["delta_p"])
    assert np.isnan(width["delta_t_normalized"])


def results_frame(removed, p, P, S, steps, L=2) -> pd.DataFrame:
    count = len(removed)
    return pd.DataFrame(
        {
            "condition_index": [0] * count,
            "run": [0] * count,
            "L": [L] * count,
            "C": [1] * count,
            "budget_mode": ["FINITE"] * count,
            "step": steps,
            "removed_edges": removed,
            "removed_edge_fraction": p,
            "largest_cluster_fraction": P,
            "largest_cluster_size": [round(value * L * L) for value in P],
            "mean_cluster_size": S,
        }
    )


def manifest_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "condition_index": [0],
            "L": [2],
            "C": [1],
            "budget_mode": ["FINITE"],
            "runs": [1],
            "max_steps": [10],
            "measurement_mode": ["ACCEPTED_REQUEST"],
            "measurement_interval": [1],
            "base_seed": [42],
            "result_path": ["unused.csv"],
        }
    )


def trace_frame(edge_ids: list[int]) -> pd.DataFrame:
    rows = []
    for edge_order, edge_id in enumerate(edge_ids):
        first, second = edge_endpoints(2, edge_id)
        rows.append(
            {
                "condition_index": 0,
                "run": 0,
                "L": 2,
                "C": 1,
                "budget_mode": "FINITE",
                "runs": 1,
                "edge_order": edge_order,
                "step": edge_order + 1,
                "edge_index_in_request": 0,
                "path_length": 1,
                "edge_id": edge_id,
                "source": first,
                "target": second,
                "seed": 42,
            }
        )
    return pd.DataFrame(rows)


def test_request_transitions_reject_sparse_multi_request_measurements() -> None:
    results = results_frame(
        removed=[0, 2, 5],
        p=[0.0, 0.1, 0.25],
        P=[1.0, 0.75, 0.25],
        S=[0.0, 1.0, 2.0],
        steps=[0, 5, 10],
        L=4,
    )
    results["accepted_requests"] = [0, 1, 3]

    import pytest

    with pytest.raises(ValueError, match="one accepted request"):
        build_request_transitions(results)


def test_request_transitions_reject_changed_counter_for_unchanged_state() -> None:
    results = results_frame(
        removed=[0, 1, 1],
        p=[0.0, 0.25, 0.25],
        P=[1.0, 0.75, 0.75],
        S=[0.0, 1.0, 1.0],
        steps=[0, 1, 5],
    )
    results["accepted_requests"] = [0, 1, 2]

    import pytest

    with pytest.raises(ValueError, match="unchanged state"):
        build_request_transitions(results)


def test_terminal_rejection_does_not_create_event_or_change_valid_width() -> None:
    results = results_frame(
        removed=[0, 1, 2, 3, 3],
        p=[0.0, 1 / 24, 2 / 24, 3 / 24, 3 / 24],
        P=[1.0, 10 / 16, 6 / 16, 3 / 16, 3 / 16],
        S=[0.0, 1.0, 2.0, 1.0, 1.0],
        steps=[0, 2, 10, 20, 50],
        L=4,
    )
    results["accepted_requests"] = [0, 1, 2, 3, 3]
    accepted_only = results.iloc[:-1].copy()

    pd.testing.assert_frame_equal(
        build_request_transitions(results), build_request_transitions(accepted_only)
    )
    pd.testing.assert_frame_equal(
        calculate_transition_widths(results), calculate_transition_widths(accepted_only)
    )
    assert len(build_request_transitions(results)) == 3


def test_request_measurement_requirement_rejects_interval_mode() -> None:
    from analysis.request_event import require_request_measurements
    import pytest

    manifest = manifest_frame()
    require_request_measurements(manifest)
    manifest.loc[0, "measurement_mode"] = "STEP_INTERVAL"

    with pytest.raises(ValueError, match="ACCEPTED_REQUEST"):
        require_request_measurements(manifest)
