import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from analysis.resampling import resample_common_p_grid


def test_jump_reuses_post_request_state_and_does_not_fill_beyond_final():
    manifest = _manifest(runs=1)
    results = _results(
        removed=[0, 1, 3],
        largest=[1.0, 0.75, 0.25],
        cluster=[0.0, 2.0, 7.0],
    )
    resampled = resample_common_p_grid(results, manifest)

    assert list(resampled["k"]) == [0, 1, 2, 3, 4]
    assert list(resampled.loc[:3, "removed_edges"]) == [0.0, 1.0, 3.0, 3.0]
    assert list(resampled.loc[2:3, "mean_cluster_size"]) == [7.0, 7.0]
    assert resampled.loc[4, ["removed_edges", "mean_cluster_size"]].isna().all()


def test_c1_exact_states_match_k_and_input_is_not_modified():
    manifest = _manifest(runs=1)
    results = _results(
        removed=[0, 1, 2, 3, 4],
        largest=[1.0, 0.75, 0.5, 0.25, 0.25],
        cluster=[0.0, 1.0, 2.0, 1.5, 1.0],
    )
    original = results.copy(deep=True)

    resampled = resample_common_p_grid(results, manifest)

    assert np.array_equal(resampled["k"], resampled["removed_edges"])
    assert_frame_equal(results, original)


def _manifest(runs):
    return pd.DataFrame(
        [
            {
                "condition_index": 0,
                "L": 2,
                "C": 1,
                "budget_mode": "FINITE",
                "runs": runs,
            }
        ]
    )


def _results(removed, largest, cluster):
    return pd.DataFrame(
        {
            "condition_index": 0,
            "run": 0,
            "L": 2,
            "C": 1,
            "budget_mode": "FINITE",
            "step": range(len(removed)),
            "removed_edges": removed,
            "largest_cluster_fraction": largest,
            "mean_cluster_size": cluster,
            "second_largest_cluster_size": [0] * len(removed),
        }
    )
