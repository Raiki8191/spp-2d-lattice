from pathlib import Path

import pandas as pd

from analysis.pilot_report import create_pilot_summary


def test_summarizes_valid_pilot_condition(tmp_path, make_sweep):
    manifest_path = make_sweep(tmp_path, runs=2)
    manifest = pd.read_csv(manifest_path)
    manifest["max_steps"] = 1
    manifest.to_csv(manifest_path, index=False)
    pd.DataFrame(
        [
            {
                "condition_index": 0,
                "L": 2,
                "C": 1,
                "budget_mode": "FINITE",
                "max_steps": 1,
                "elapsed_ms": 17,
            }
        ]
    ).to_csv(Path(tmp_path) / "execution_times.csv", index=False)

    summary = create_pilot_summary(manifest_path)

    assert len(summary) == 1
    assert summary.loc[0, "elapsed_ms"] == 17
    assert summary.loc[0, "data_rows"] == 4
    assert summary.loc[0, "final_steps"] == "1;1"
    assert summary.loc[0, "invariants_valid"]
    assert (Path(tmp_path) / "pilot_summary.csv").is_file()
