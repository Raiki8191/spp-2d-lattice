import pandas as pd

from analysis.scaling_v2 import _bootstrap_summary


def test_bootstrap_is_reproducible_and_uses_actual_run_count():
    events = pd.DataFrame({
        "condition_index": [0, 0, 0], "run": [0, 1, 2], "L": [8]*3, "C": [1]*3,
        "budget_mode": ["FINITE"]*3,
        "p_before": [.4,.5,.6], "p_after": [.41,.51,.61], "p_mid": [.405,.505,.605],
        "delta_p_request": [.01]*3, "P_before": [.6,.5,.4], "P_after": [.5,.4,.3],
        "delta_P_max": [.1]*3, "S_before": [2.,3.,4.], "S_after": [3.,4.,5.],
        "path_length": [1.,1.,1.],
    })
    widths = pd.DataFrame({
        "condition_index": [0,0,0], "run": [0,1,2], "L": [8]*3, "C": [1]*3,
        "budget_mode": ["FINITE"]*3, "delta_p": [.1,.2,.3],
        "delta_t_normalized": [.01,.02,.03],
    })
    first = _bootstrap_summary(events, widths, bootstrap_samples=100, bootstrap_seed=9)
    second = _bootstrap_summary(events, widths, bootstrap_samples=100, bootstrap_seed=9)
    pd.testing.assert_frame_equal(first, second)
    assert set(first["run_count"]) == {3}
