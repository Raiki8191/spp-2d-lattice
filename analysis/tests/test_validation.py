from __future__ import annotations

import pandas as pd
import pytest

from analysis.io import load_sweep
from analysis.validation import validate_sweep


def test_valid_sweep_reports_counts(tmp_path, make_sweep):
    manifest_path = make_sweep(
        tmp_path,
        conditions=[
            {"condition_index": 0, "L": 2, "C": 1, "budget_mode": "FINITE"},
            {"condition_index": 1, "L": 3, "C": 9, "budget_mode": "UNBOUNDED"},
        ],
        runs=2,
    )
    manifest, results = load_sweep(manifest_path)

    summary = validate_sweep(manifest, results)

    assert summary.condition_count == 2
    assert summary.row_count == 8
    assert summary.run_count == 4


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("rejected_requests", 1, r"accepted_requests \+ rejected_requests != step"),
        ("remaining_edges", 99, r"removed_edges \+ remaining_edges != 2L"),
    ],
)
def test_detects_row_invariant_violations(
    tmp_path, make_sweep, column, value, message
):
    manifest, results = load_sweep(make_sweep(tmp_path))
    results.loc[1, column] = value

    with pytest.raises(ValueError, match=message + r".*condition=0, run=0, step=1"):
        validate_sweep(manifest, results)


def test_detects_non_increasing_step(tmp_path, make_sweep):
    manifest, results = _three_rows(tmp_path, make_sweep)
    results.loc[2, "step"] = 1
    results.loc[2, "accepted_requests"] = 1
    results.loc[2, "rejected_requests"] = 0

    with pytest.raises(ValueError, match=r"step is not strictly increasing.*condition=0"):
        validate_sweep(manifest, results)


def test_detects_removed_edges_decrease(tmp_path, make_sweep):
    manifest, results = _three_rows(tmp_path, make_sweep)
    results.loc[2, "removed_edges"] = 0
    results.loc[2, "remaining_edges"] = 4
    results.loc[2, "removed_edge_fraction"] = 0.0

    with pytest.raises(ValueError, match=r"removed_edges decreased.*run=0, step=2"):
        validate_sweep(manifest, results)


def test_detects_largest_cluster_increase(tmp_path, make_sweep):
    manifest, results = _three_rows(tmp_path, make_sweep)
    results.loc[1, "largest_cluster_size"] = 3
    results.loc[1, "largest_cluster_fraction"] = 0.75
    results.loc[2, "largest_cluster_size"] = 4
    results.loc[2, "largest_cluster_fraction"] = 1.0

    with pytest.raises(ValueError, match=r"largest_cluster_size increased.*step=2"):
        validate_sweep(manifest, results)


def test_detects_unchanged_intermediate_accepted_event(tmp_path, make_sweep):
    manifest, results = _three_rows(
        tmp_path, make_sweep, measurement_mode="ACCEPTED_REQUEST"
    )
    results.loc[1, "removed_edges"] = 0
    results.loc[1, "remaining_edges"] = 4
    results.loc[1, "removed_edge_fraction"] = 0.0

    with pytest.raises(
        ValueError, match=r"ACCEPTED_REQUEST measurement did not increase.*step=1"
    ):
        validate_sweep(manifest, results)


def _three_rows(tmp_path, make_sweep, measurement_mode="STEP_INTERVAL"):
    manifest, results = load_sweep(
        make_sweep(tmp_path, measurement_mode=measurement_mode)
    )
    final = results.iloc[-1].copy()
    final["step"] = 2
    final["removed_edges"] = 2
    final["remaining_edges"] = 2
    final["removed_edge_fraction"] = 0.5
    final["largest_cluster_size"] = 3
    final["largest_cluster_fraction"] = 0.75
    final["second_largest_cluster_size"] = 1
    final["mean_cluster_size"] = 1.0
    final["accepted_requests"] = 2
    final["rejected_requests"] = 0
    results = pd.concat([results, final.to_frame().T], ignore_index=True)
    return manifest, results
