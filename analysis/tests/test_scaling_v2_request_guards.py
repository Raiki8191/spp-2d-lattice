from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from analysis.scaling_v2 import analyze_manifests, audit_stops


def _paired_stop_inputs(tmp_path: Path, make_sweep) -> tuple[Path, Path]:
    paths = []
    for name, final_removed, multiplier in (("main", 3, 1.0), ("audit", 4, 0.5)):
        manifest_path = make_sweep(
            tmp_path / name, measurement_mode="ACCEPTED_REQUEST"
        )
        manifest = pd.read_csv(manifest_path)
        manifest["max_steps"] = 4
        manifest["transition_threshold_multiplier"] = multiplier
        manifest.to_csv(manifest_path, index=False)
        rows = []
        for removed, largest, second, mean in [
            (0, 4, 0, 0.0), (1, 4, 0, 0.0), (2, 3, 1, 1.0),
            (3, 2, 1, 1.0), (4, 1, 1, 1.0),
        ]:
            if removed > final_removed:
                break
            rows.append({
                "run": 0, "L": 2, "C": 1, "step": removed,
                "removed_edges": removed, "remaining_edges": 4 - removed,
                "removed_edge_fraction": removed / 4,
                "largest_cluster_size": largest,
                "largest_cluster_fraction": largest / 4,
                "second_largest_cluster_size": second, "mean_cluster_size": mean,
                "accepted_requests": removed, "rejected_requests": 0, "seed": 100,
            })
        result = manifest_path.parent / manifest.loc[0, "result_path"]
        pd.DataFrame(rows).to_csv(result, index=False)
        paths.append(manifest_path)
    return paths[0], paths[1]


def test_stop_audit_accepts_same_conditions_in_separate_manifests(tmp_path, make_sweep):
    main, audit = _paired_stop_inputs(tmp_path, make_sweep)

    runs, summary = audit_stops(main, audit, tmp_path / "output")

    assert len(runs) == 1
    assert runs.iloc[0]["main_prefix_identical"]
    assert runs.iloc[0]["additional_accepted_requests"] == 1
    assert summary.iloc[0]["main_prefix_identical_runs"] == 1


@pytest.mark.parametrize("interval_input", ["main", "audit"])
def test_stop_audit_rejects_interval_measurement_before_artifacts(
    tmp_path, make_sweep, interval_input
):
    main, audit = _paired_stop_inputs(tmp_path, make_sweep)
    path = main if interval_input == "main" else audit
    manifest = pd.read_csv(path)
    manifest["measurement_mode"] = "STEP_INTERVAL"
    manifest.to_csv(path, index=False)
    output = tmp_path / "output"

    with pytest.raises(ValueError, match="ACCEPTED_REQUEST"):
        audit_stops(main, audit, output)

    assert not list(output.rglob("*.csv"))


def test_scaling_analysis_rejects_interval_manifest_before_artifacts(
    tmp_path, make_sweep
):
    manifest = make_sweep(tmp_path / "data", measurement_mode="STEP_INTERVAL")
    output = tmp_path / "output"

    with pytest.raises(ValueError, match="ACCEPTED_REQUEST"):
        analyze_manifests([manifest], output)

    assert not list(output.rglob("*.csv"))
