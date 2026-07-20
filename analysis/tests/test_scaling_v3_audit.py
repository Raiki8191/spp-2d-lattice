from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analysis.scaling_v3_audit import (
    _log_ols_fit, _nonlinear_fit, audit_bootstrap_distributions,
)


def _run_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    events, widths = [], []
    for C in (1, 2):
        for L in (8, 12, 16, 24, 32):
            for run in range(6):
                jitter = 1.0 + (run - 2.5) * 0.002
                events.append({
                    "condition_index": C * 100 + L, "run": run, "L": L, "C": C,
                    "budget_mode": "FINITE", "P_before": jitter * L ** -0.2,
                    "P_after": .8 * jitter * L ** -0.2,
                    "S_before": jitter * L ** 1.5,
                    "S_after": 1.2 * jitter * L ** 1.5,
                    "p_mid": .5 + jitter * L ** -.7,
                    "delta_P_max": jitter * L ** -.3,
                })
                widths.append({
                    "condition_index": C * 100 + L, "run": run, "L": L, "C": C,
                    "budget_mode": "FINITE", "delta_p": jitter * L ** -.4,
                })
    return pd.DataFrame(events), pd.DataFrame(widths)


def test_aligned_bootstrap_is_reproducible_records_metadata_and_does_not_mutate() -> None:
    events, widths = _run_data()
    original_events, original_widths = events.copy(deep=True), widths.copy(deep=True)
    first = audit_bootstrap_distributions(events, widths, samples=8, seed=17)
    second = audit_bootstrap_distributions(events, widths, samples=8, seed=17)

    pd.testing.assert_frame_equal(first, second)
    pd.testing.assert_frame_equal(events, original_events)
    pd.testing.assert_frame_equal(widths, original_widths)
    assert set(first["L_min"]) == {8}
    assert set(first["used_L"]) == {"8;12;16;24;32"}
    assert set(first["bootstrap_seed"]) == {17}
    assert {"P_before", "P_after", "S_before", "S_after", "p_mid",
            "delta_P_max", "delta_p"} == set(first["source_column"])
    assert set(first["aligned_estimator"]) == {
        "bounded_nonlinear_least_squares_original_scale",
        "log_log_ordinary_least_squares",
    }
    assert not first["aligned_failure"].astype(bool).any()


def test_point_and_bootstrap_fit_use_same_known_power_estimator() -> None:
    sizes = np.array([8, 12, 16, 24, 32], float)
    values = 2.5 * sizes ** 1.6
    point = _nonlinear_fit(sizes, values, 1)
    bootstrap_sample = _nonlinear_fit(sizes, values, 1)
    assert point["converged"] and bootstrap_sample["converged"]
    assert point["exponent"] == pytest.approx(1.6, rel=1e-7)
    assert bootstrap_sample["exponent"] == pytest.approx(point["exponent"])


def test_log_ols_sign_conversion_and_percentile_interval() -> None:
    sizes = np.array([8, 12, 16, 24, 32], float)
    fit = _log_ols_fit(sizes, 3.0 * sizes ** -0.75, -1)
    assert fit["exponent"] == pytest.approx(0.75)
    samples = np.array([1.0, 2.0, 3.0, 4.0])
    assert np.percentile(samples, [2.5, 97.5]) == pytest.approx([1.075, 3.925])
