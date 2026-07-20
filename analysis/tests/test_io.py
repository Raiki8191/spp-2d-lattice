from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from analysis.io import load_sweep, read_manifest, read_results


def test_loads_and_combines_valid_manifest_and_results(tmp_path, make_sweep):
    manifest_path = make_sweep(tmp_path)

    manifest, results = load_sweep(manifest_path)

    assert len(manifest) == 1
    assert len(results) == 2
    assert set(("condition_index", "budget_mode", "result_path")) <= set(results.columns)
    resolved = Path(manifest.loc[0, "result_path"])
    assert resolved.is_absolute()
    assert resolved == (tmp_path / "L=2/C=1/results.csv").resolve()
    assert set(results["result_path"]) == {str(resolved)}


@pytest.mark.parametrize("target", ["manifest", "results"])
def test_rejects_missing_required_columns(tmp_path, make_sweep, target):
    manifest_path = make_sweep(tmp_path)
    if target == "manifest":
        frame = pd.read_csv(manifest_path).drop(columns=["budget_mode"])
        frame.to_csv(manifest_path, index=False)
        with pytest.raises(ValueError, match="missing required columns.*budget_mode"):
            read_manifest(manifest_path)
    else:
        manifest = read_manifest(manifest_path)
        result_path = Path(manifest.loc[0, "result_path"])
        frame = pd.read_csv(result_path).drop(columns=["step"])
        frame.to_csv(result_path, index=False)
        with pytest.raises(ValueError, match="missing required columns.*step"):
            read_results(manifest)


def test_rejects_manifest_results_l_c_mismatch(tmp_path, make_sweep):
    manifest_path = make_sweep(tmp_path)
    manifest = read_manifest(manifest_path)
    result_path = Path(manifest.loc[0, "result_path"])
    frame = pd.read_csv(result_path)
    frame.loc[1, "C"] = 99
    frame.to_csv(result_path, index=False)

    with pytest.raises(ValueError, match=r"condition=0, run=0, step=1"):
        read_results(manifest)


def test_combines_multiple_conditions_and_runs(tmp_path, make_sweep):
    manifest_path = make_sweep(
        tmp_path,
        conditions=[
            {"condition_index": 0, "L": 2, "C": 1, "budget_mode": "FINITE"},
            {"condition_index": 1, "L": 3, "C": 9, "budget_mode": "UNBOUNDED"},
        ],
        runs=2,
    )

    manifest, results = load_sweep(manifest_path)

    assert len(manifest) == 2
    assert len(results) == 8
    assert results.groupby(["condition_index", "run"]).ngroups == 4
    assert set(results["budget_mode"]) == {"FINITE", "UNBOUNDED"}


def test_rejects_duplicate_condition_invalid_mode_and_missing_result(tmp_path, make_sweep):
    manifest_path = make_sweep(
        tmp_path,
        conditions=[
            {"condition_index": 0, "L": 2, "C": 1, "budget_mode": "FINITE"},
            {"condition_index": 1, "L": 3, "C": 2, "budget_mode": "FINITE"},
        ],
    )
    frame = pd.read_csv(manifest_path)
    frame.loc[1, "condition_index"] = 0
    frame.to_csv(manifest_path, index=False)
    with pytest.raises(ValueError, match="duplicate condition_index=0"):
        read_manifest(manifest_path)

    frame.loc[1, "condition_index"] = 1
    frame.loc[1, "budget_mode"] = "OTHER"
    frame.to_csv(manifest_path, index=False)
    with pytest.raises(ValueError, match="invalid budget_mode"):
        read_manifest(manifest_path)

    frame.loc[1, "budget_mode"] = "FINITE"
    frame.loc[1, "result_path"] = "missing/results.csv"
    frame.to_csv(manifest_path, index=False)
    with pytest.raises(FileNotFoundError, match="condition=1"):
        read_manifest(manifest_path)


def test_preserves_stage_and_resolves_optional_run_metadata(tmp_path, make_sweep):
    manifest_path = make_sweep(tmp_path)
    metadata_path = tmp_path / "run_metadata.csv"
    metadata_path.write_text("run,run_seed\n0,123\n", encoding="utf-8")
    frame = pd.read_csv(manifest_path)
    frame["stage"] = "unbounded-l192-benchmark"
    frame["run_metadata_path"] = "run_metadata.csv"
    frame.to_csv(manifest_path, index=False)

    manifest = read_manifest(manifest_path)

    assert manifest.loc[0, "stage"] == "unbounded-l192-benchmark"
    assert Path(manifest.loc[0, "run_metadata_path"]) == metadata_path.resolve()
