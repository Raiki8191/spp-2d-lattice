from __future__ import annotations

import pandas as pd

from analysis.scaling_v2_benchmark import _runtime_projections


def test_runtime_projection_uses_five_run_linear_scaling(tmp_path) -> None:
    summary = pd.DataFrame(
        [
            {
                "L": 96,
                "C": 1,
                "budget_mode": "FINITE",
                "runs": 5,
                "java_elapsed_seconds": 10.0,
                "results_bytes": 100,
                "results_dataframe_bytes": 40,
                "request_transition_dataframe_bytes": 20,
            }
        ]
    )
    v1 = tmp_path / "execution_times.csv"
    pd.DataFrame(
        [
            {
                "condition_index": 0,
                "L": 8,
                "C": 1,
                "budget_mode": "FINITE",
                "max_steps": 10,
                "elapsed_ms": 1000,
            }
        ]
    ).to_csv(v1, index=False)

    projected = _runtime_projections(summary, v1)
    condition = projected.loc[
        (projected["record_type"] == "CONDITION")
        & (projected["target_runs"] == 200)
    ].iloc[0]
    candidate_a = projected.loc[
        projected["scenario"] == "SCALING_V2_A"
    ].iloc[0]
    candidate_b = projected.loc[
        projected["scenario"] == "SCALING_V2_B"
    ].iloc[0]

    assert condition["estimated_java_seconds"] == 400.0
    assert condition["estimated_results_bytes"] == 4000
    assert condition["estimated_analysis_memory_bytes"] == 2400
    assert candidate_a["estimated_java_seconds"] == 401.0
    assert candidate_b["estimated_java_seconds"] == 802.0
