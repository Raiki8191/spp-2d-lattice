from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from analysis.edge_trace import EDGE_TRACE_COLUMNS, read_edge_traces
from analysis.event_ensemble import extract_event_peaks
from analysis.exact_ensemble import (
    aggregate_exact_ensemble,
    compare_resampling_methods,
    reconstruct_exact_states,
)


def test_reverse_union_find_matches_forward_deletion_at_every_k() -> None:
    manifest = manifest_frame(L=2, runs=1)
    traces = trace_frame([0, 3, 1, 2], L=2)
    original_manifest = manifest.copy(deep=True)
    original_traces = traces.copy(deep=True)

    exact = reconstruct_exact_states(manifest, traces)

    assert exact["k"].tolist() == [0, 1, 2, 3, 4]
    for row in exact.itertuples(index=False):
        largest, mean_cluster = brute_force_stats(2, [0, 3, 1, 2][: row.k])
        assert row.largest_cluster_size == largest
        assert row.largest_cluster_fraction == largest / 4
        assert row.mean_cluster_size == mean_cluster
    assert exact.iloc[0]["largest_cluster_size"] == 4
    assert exact.iloc[-1]["largest_cluster_size"] == 1
    pd.testing.assert_frame_equal(manifest, original_manifest)
    pd.testing.assert_frame_equal(traces, original_traces)


def test_multi_edge_request_still_reconstructs_every_k() -> None:
    manifest = manifest_frame(L=2, runs=1)
    traces = trace_frame([0, 3, 1], L=2, path_lengths=[2, 2, 1])
    traces.loc[0:1, "step"] = 1
    traces.loc[0:1, "edge_index_in_request"] = [0, 1]
    traces.loc[2, "step"] = 2

    exact = reconstruct_exact_states(manifest, traces)

    assert exact["k"].tolist() == [0, 1, 2, 3]


def test_l3_reverse_reconstruction_matches_forward_deletion() -> None:
    removal_order = [0, 7, 3, 10, 1, 8]
    manifest = manifest_frame(L=3, runs=1)
    traces = trace_frame(removal_order, L=3)

    exact = reconstruct_exact_states(manifest, traces)

    for row in exact.itertuples(index=False):
        largest, mean_cluster = brute_force_stats(3, removal_order[: row.k])
        assert row.largest_cluster_size == largest
        assert row.largest_cluster_fraction == largest / 9
        assert row.mean_cluster_size == mean_cluster


def test_exact_aggregation_has_correct_mean_std_sem_and_missing_runs() -> None:
    manifest = manifest_frame(L=2, runs=2)
    traces = pd.concat(
        [trace_frame([0, 3], L=2, run=0), trace_frame([0], L=2, run=1)],
        ignore_index=True,
    )
    exact = reconstruct_exact_states(manifest, traces)
    summary = aggregate_exact_ensemble(exact)

    k1 = summary.loc[summary["k"] == 1].iloc[0]
    k2 = summary.loc[summary["k"] == 2].iloc[0]
    values = exact.loc[exact["k"] == 1, "mean_cluster_size"]
    assert k1["n_eff"] == 2
    assert math.isclose(k1["mean_cluster_size_mean"], values.mean())
    assert math.isclose(k1["mean_cluster_size_std"], values.std())
    assert math.isclose(k1["mean_cluster_size_sem"], values.std() / math.sqrt(2))
    assert k2["n_eff"] == 1


def test_event_peak_and_tie_break_choose_smallest_k() -> None:
    exact = pd.DataFrame(
        {
            "condition_index": [0, 0, 0],
            "run": [0, 0, 0],
            "L": [2, 2, 2],
            "C": [1, 1, 1],
            "budget_mode": ["FINITE"] * 3,
            "k": [0, 1, 2],
            "p": [0.0, 0.25, 0.5],
            "largest_cluster_size": [4, 3, 2],
            "largest_cluster_fraction": [1.0, 0.75, 0.5],
            "mean_cluster_size": [0.0, 1.0, 2.0],
        }
    )
    traces = trace_frame([0, 1], L=2)

    event = extract_event_peaks(exact, traces).iloc[0]

    assert event["k_before"] == 0
    assert event["k_after"] == 1
    assert event["edge_id"] == 0
    assert event["delta_P_max"] == 0.25


@pytest.mark.parametrize(
    "edge_orders,edge_ids,message",
    [
        ([0, 2], [0, 1], "edge_order"),
        ([0, 1], [0, 0], "duplicate edge_id"),
        ([0], [4], "edge_id out of range"),
    ],
)
def test_invalid_trace_is_rejected(
    tmp_path: Path, edge_orders: list[int], edge_ids: list[int], message: str
) -> None:
    trace_path = tmp_path / "edge_removals.csv"
    trace = pd.DataFrame(
        {
            "run": [0] * len(edge_ids),
            "edge_order": edge_orders,
            "step": list(range(1, len(edge_ids) + 1)),
            "edge_index_in_request": [0] * len(edge_ids),
            "path_length": [1] * len(edge_ids),
            "edge_id": edge_ids,
            "source": [0] * len(edge_ids),
            "target": [1] * len(edge_ids),
            "seed": [42] * len(edge_ids),
        }
    )
    trace.to_csv(trace_path, index=False)
    manifest = manifest_frame(L=2, runs=1)
    manifest["edge_trace_path"] = str(trace_path)

    with pytest.raises(ValueError, match=message):
        read_edge_traces(manifest)


def test_c1_post_request_and_exact_conventional_match() -> None:
    manifest = manifest_frame(L=2, runs=1)
    traces = trace_frame([0, 3, 1, 2], L=2)
    exact = reconstruct_exact_states(manifest, traces)
    results = pd.DataFrame(
        {
            "condition_index": [0] * 5,
            "run": [0] * 5,
            "L": [2] * 5,
            "C": [1] * 5,
            "budget_mode": ["FINITE"] * 5,
            "step": [0, 1, 2, 3, 4],
            "removed_edges": [0, 1, 2, 3, 4],
            "largest_cluster_fraction": exact["largest_cluster_fraction"],
            "mean_cluster_size": exact["mean_cluster_size"],
            "second_largest_cluster_size": [0] * 5,
        }
    )
    exact_summary = aggregate_exact_ensemble(exact)
    from analysis.pseudocritical import extract_conventional_peaks

    exact_peak = extract_conventional_peaks(exact_summary)
    comparison = compare_resampling_methods(results, manifest, exact_peak).iloc[0]

    assert comparison["post_request_p"] == comparison["exact_edge_p"]
    assert comparison["post_request_peak_mean_S"] == comparison["exact_peak_mean_S"]
    assert comparison["post_request_mean_P_at_peak"] == comparison["exact_mean_P_at_peak"]


def manifest_frame(L: int, runs: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "condition_index": [0],
            "L": [L],
            "C": [1],
            "budget_mode": ["FINITE"],
            "runs": [runs],
            "max_steps": [10],
            "measurement_mode": ["ACCEPTED_REQUEST"],
            "measurement_interval": [1],
            "base_seed": [42],
            "result_path": ["unused.csv"],
        }
    )


def trace_frame(
    edge_ids: list[int],
    *,
    L: int,
    run: int = 0,
    path_lengths: list[int] | None = None,
) -> pd.DataFrame:
    count = len(edge_ids)
    frame = pd.DataFrame(
        {
            "run": [run] * count,
            "edge_order": list(range(count)),
            "step": list(range(1, count + 1)),
            "edge_index_in_request": [0] * count,
            "path_length": path_lengths or [1] * count,
            "edge_id": edge_ids,
            "source": [0] * count,
            "target": [1] * count,
            "seed": [42 + run] * count,
            "condition_index": [0] * count,
            "L": [L] * count,
            "C": [1] * count,
            "budget_mode": ["FINITE"] * count,
            "runs": [1] * count,
        }
    )
    return frame


def brute_force_stats(L: int, removed: list[int]) -> tuple[int, float]:
    vertex_count = L * L
    adjacency = [[] for _ in range(vertex_count)]
    removed_set = set(removed)
    edge_count = 2 * L * (L - 1)
    from analysis.edge_trace import edge_endpoints

    for edge_id in range(edge_count):
        if edge_id not in removed_set:
            first, second = edge_endpoints(L, edge_id)
            adjacency[first].append(second)
            adjacency[second].append(first)
    sizes: list[int] = []
    unseen = set(range(vertex_count))
    while unseen:
        start = unseen.pop()
        stack = [start]
        size = 0
        while stack:
            vertex = stack.pop()
            size += 1
            for neighbor in adjacency[vertex]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
        sizes.append(size)
    largest = max(sizes)
    sizes.remove(largest)
    denominator = sum(sizes)
    mean_cluster = 0.0 if denominator == 0 else sum(size**2 for size in sizes) / denominator
    return largest, mean_cluster
