from pathlib import Path

import pandas as pd
import pytest

from analysis.multi_manifest import iter_conditions, logical_manifest, read_condition


HEADER = "run,L,C,step,removed_edges,remaining_edges,removed_edge_fraction,largest_cluster_size,largest_cluster_fraction,second_largest_cluster_size,mean_cluster_size,accepted_requests,rejected_requests,seed\n"


def _sweep(root: Path, condition_index: int, L: int, C: int, runs: int) -> Path:
    result = root / f"L={L}" / f"C={C}" / "results.csv"
    result.parent.mkdir(parents=True)
    m0 = 2 * L * (L - 1)
    rows = []
    for run in range(runs):
        rows.append(f"{run},{L},{C},0,0,{m0},0.0,{L*L},1.0,0,0.0,0,0,{run+42}\n")
    result.write_text(HEADER + "".join(rows), encoding="utf-8")
    manifest = root / "manifest.csv"
    manifest.write_text(
        "condition_index,L,C,budget_mode,runs,max_steps,measurement_mode,measurement_interval,base_seed,result_path\n"
        f"{condition_index},{L},{C},FINITE,{runs},0,ACCEPTED_REQUEST,1,42,L={L}/C={C}/results.csv\n",
        encoding="utf-8",
    )
    return manifest


def test_repeated_local_condition_indices_receive_global_ids_and_unequal_runs(tmp_path: Path):
    first = _sweep(tmp_path / "v1", 0, 2, 1, 2)
    second = _sweep(tmp_path / "v2", 0, 3, 2, 4)
    metadata = logical_manifest([first, second])
    assert metadata["global_condition_id"].tolist() == [0, 1]
    assert metadata["source_condition_index"].tolist() == [0, 0]
    conditions = list(iter_conditions([first, second]))
    assert len(read_condition(conditions[0])) == 2
    assert len(read_condition(conditions[1])) == 4
    assert read_condition(conditions[1])["condition_index"].unique().tolist() == [1]


def test_duplicate_logical_condition_is_rejected(tmp_path: Path):
    first = _sweep(tmp_path / "a", 0, 2, 1, 1)
    second = _sweep(tmp_path / "b", 7, 2, 1, 1)
    with pytest.raises(ValueError, match="duplicate logical condition"):
        logical_manifest([first, second])
