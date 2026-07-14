from __future__ import annotations

import math

import pandas as pd

from analysis.scaling_fit import fit_scaling


def test_loglog_fit_recovers_known_powers_and_effective_exponents() -> None:
    request_rows = []
    transition_rows = []
    for index, L in enumerate((8, 12, 16, 24, 32, 48, 64)):
        request_rows.append(
            {
                "condition_index": index,
                "L": L,
                "C": 1,
                "budget_mode": "FINITE",
                "P_before_mean": L ** -0.25,
                "P_after_mean": 2 * L ** -0.25,
                "delta_P_max_mean": L ** -0.5,
                "S_before_mean": L ** 1.5,
                "S_after_mean": 2 * L ** 1.5,
                "p_mid_std": L ** -0.75,
                "delta_p_request_mean": L ** -1.0,
            }
        )
        transition_rows.append(
            {
                "condition_index": index,
                "delta_p_mean": L ** -0.6,
                "delta_t_normalized_mean": L ** -0.2,
            }
        )

    fits, effective = fit_scaling(
        pd.DataFrame(request_rows), pd.DataFrame(transition_rows)
    )

    selected = fits.loc[(fits["L_min"] == 8)].set_index("observable")
    assert math.isclose(selected.loc["P_before", "exponent"], 0.25, abs_tol=1e-12)
    assert math.isclose(selected.loc["S_before", "exponent"], 1.5, abs_tol=1e-12)
    assert math.isclose(selected.loc["std_p_mid", "exponent"], 0.75, abs_tol=1e-12)
    assert math.isclose(
        selected.loc["transition_delta_p", "exponent"], 0.6, abs_tol=1e-12
    )
    assert (fits["point_count"] >= 4).all()
    assert not effective.empty


def test_nonpositive_values_are_excluded_from_log_fit() -> None:
    request = pd.DataFrame(
        {
            "condition_index": range(7),
            "L": [8, 12, 16, 24, 32, 48, 64],
            "C": [1] * 7,
            "budget_mode": ["FINITE"] * 7,
            "P_before_mean": [1.0] * 7,
            "P_after_mean": [1.0] * 7,
            "delta_P_max_mean": [1.0] * 7,
            "S_before_mean": [1.0] * 7,
            "S_after_mean": [1.0] * 7,
            "p_mid_std": [0.0, -1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
            "delta_p_request_mean": [1.0] * 7,
        }
    )
    transition = pd.DataFrame(
        {
            "condition_index": range(7),
            "delta_p_mean": [1.0] * 7,
            "delta_t_normalized_mean": [1.0] * 7,
        }
    )

    fits, _ = fit_scaling(request, transition)

    row = fits.loc[(fits["observable"] == "std_p_mid") & (fits["L_min"] == 8)].iloc[0]
    assert row["point_count"] == 5
    assert row["used_L"] == "16;24;32;48;64"
