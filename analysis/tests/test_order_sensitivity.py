from __future__ import annotations

import pandas as pd

from analysis.order_sensitivity import (
    DETERMINISTIC_SHUFFLE,
    SOURCE_TO_TARGET,
    TARGET_TO_SOURCE,
    reorder_within_requests,
)


def test_length_one_is_unchanged_for_all_orders() -> None:
    trace = sample_trace(path_lengths=(1, 1, 1))
    for mode in (SOURCE_TO_TARGET, TARGET_TO_SOURCE, DETERMINISTIC_SHUFFLE):
        reordered = reorder_within_requests(trace, mode)
        assert reordered["edge_id"].tolist() == trace["edge_id"].tolist()


def test_reverse_twice_restores_source_order() -> None:
    trace = sample_trace()
    reversed_once = reorder_within_requests(trace, TARGET_TO_SOURCE)
    reversed_twice = reorder_within_requests(reversed_once, TARGET_TO_SOURCE)
    assert reversed_twice["edge_id"].tolist() == trace["edge_id"].tolist()
    assert reversed_twice["step"].tolist() == trace["step"].tolist()


def test_deterministic_shuffle_is_reproducible() -> None:
    trace = sample_trace(path_lengths=(4, 2))
    first = reorder_within_requests(trace, DETERMINISTIC_SHUFFLE)
    second = reorder_within_requests(trace, DETERMINISTIC_SHUFFLE)
    pd.testing.assert_frame_equal(first, second)


def test_request_order_and_edge_multiset_are_preserved_without_mutating_input() -> None:
    trace = sample_trace(path_lengths=(3, 2, 1))
    original = trace.copy(deep=True)

    reordered = reorder_within_requests(trace, DETERMINISTIC_SHUFFLE)

    assert reordered["step"].drop_duplicates().tolist() == [1, 4, 8]
    assert sorted(reordered["edge_id"].tolist()) == sorted(trace["edge_id"].tolist())
    assert len(reordered) == len(trace)
    assert reordered["edge_order"].tolist() == list(range(len(trace)))
    pd.testing.assert_frame_equal(trace, original)


def test_c1_trace_is_identical_for_all_order_modes() -> None:
    trace = sample_trace(path_lengths=(1, 1, 1, 1))
    source = reorder_within_requests(trace, SOURCE_TO_TARGET)
    for mode in (TARGET_TO_SOURCE, DETERMINISTIC_SHUFFLE):
        pd.testing.assert_frame_equal(source, reorder_within_requests(trace, mode))


def sample_trace(path_lengths: tuple[int, ...] = (3, 2)) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    edge_id = 0
    edge_order = 0
    steps = [1, 4, 8, 11]
    for request_index, path_length in enumerate(path_lengths):
        for edge_index in range(path_length):
            rows.append(
                {
                    "run": 0,
                    "edge_order": edge_order,
                    "step": steps[request_index],
                    "edge_index_in_request": edge_index,
                    "path_length": path_length,
                    "edge_id": edge_id,
                    "source": 0,
                    "target": 8,
                    "seed": 42,
                    "condition_index": 0,
                    "L": 3,
                    "C": 9,
                    "budget_mode": "UNBOUNDED",
                    "runs": 1,
                    "edge_trace_path": "unused.csv",
                }
            )
            edge_id += 1
            edge_order += 1
    return pd.DataFrame(rows)
