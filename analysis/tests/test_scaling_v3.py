import numpy as np
import pandas as pd
import pytest

from analysis.scaling_v3 import (
    hyperscaling_summary, runtime_forecasts, summarize_bootstrap, unbounded_fits,
)
from analysis.universality_fitting import fit_universality_models


def synthetic_summary():
    rows = []
    for label, C, budget in (("C=1", 1, "FINITE"), ("C=2", 2, "FINITE"), ("UNBOUNDED", 0, "UNBOUNDED")):
        for L in (8, 12, 16, 24, 32, 48, 64, 96, 128):
            x = -0.105 if label == "C=1" else -0.11
            rows.append({"condition_label": label, "condition_index": len(rows), "L": L, "C": C,
                         "budget_mode": budget, "P_before_mean": L**x * (1 + .4/L),
                         "P_after_mean": .8*L**x*(1+.2/L), "S_before_mean": L**1.7,
                         "S_after_mean": 1.2*L**1.7, "p_mid_std": .2*L**-.75,
                         "delta_P_max_mean": .4*L**(-.08) if budget == "UNBOUNDED" else .2*L**-.2,
                         "delta_p_mean": .3*L**(-.2), "delta_t_normalized_mean": .4*L**(-.3),
                         "p_mid_mean": .5 + .3*L**(-.75)})
    return pd.DataFrame(rows)


def test_finite_corrections_and_joint_models_cover_required_models():
    data = synthetic_summary()
    c1 = data.loc[data["condition_label"] == "C=1"]
    c2 = data.loc[data["condition_label"] == "C=2"]
    joint = fit_universality_models(c1["L"].to_numpy(float), c1["P_before_mean"].to_numpy(float),
                                    c2["L"].to_numpy(float), c2["P_before_mean"].to_numpy(float))
    assert {"U1_independent", "U2_shared_exponent", "U3_shared_exponent_omega",
            "U3_shared_exponent_omega_0.5", "U3_shared_exponent_omega_2"}.issubset(
                {fit["model"] for fit in joint})


def test_unbounded_comparison_has_power_log_loo_and_flagged_extrapolation():
    fits, loo, prediction = unbounded_fits(synthetic_summary())
    assert set(fits["model"]) == {"zero_power", "finite_power", "zero_log", "finite_log"}
    assert set(loo["omitted_L"]) == {8, 12, 16, 24, 32, 48, 64, 96, 128}
    assert set(prediction["target_L"]) == {160, 192, 256}
    assert prediction["warning"].str.contains("not an observation").all()


def test_bootstrap_summary_reports_interval_and_boundary_frequency():
    frame = pd.DataFrame({"condition_label": ["C=1"]*3, "observable": ["P_before"]*3,
                          "model": ["simple_power"]*3, "exponent": [.1, .2, .3],
                          "limit": [0., 0., 0.], "boundary_solution": [False, True, False]})
    result = summarize_bootstrap(frame)
    exponent = result.loc[result["parameter"] == "exponent"].iloc[0]
    assert exponent["median"] == pytest.approx(.2)
    assert exponent["boundary_frequency"] == pytest.approx(1/3)


def test_hyperscaling_combines_two_beta_over_nu_and_gamma_over_nu():
    fits = pd.DataFrame([
        {"condition_label": "C=1", "observable": "P_before", "L_min": 8, "model": "simple_power",
         "converged": True, "admissible": True, "theory_fixed": False, "aicc": 1, "scaling_exponent": .1},
        {"condition_label": "C=1", "observable": "S_before", "L_min": 8, "model": "simple_power",
         "converged": True, "admissible": True, "theory_fixed": False, "aicc": 1, "scaling_exponent": 1.8},
    ])
    result = hyperscaling_summary(fits)
    assert np.allclose(result["hyperscaling_sum"], 2.0)


def test_runtime_forecast_uses_measured_run_summaries(tmp_path):
    root = tmp_path / "scaling-v2-main"
    rows = []
    for index, (L, C, mode, values) in enumerate(((96, 1, "FINITE", [10, 12]), (128, 1, "FINITE", [20, 22]))):
        result_path = f"L={L}/C={C}/results.csv"
        directory = root / f"L={L}" / f"C={C}"
        directory.mkdir(parents=True)
        pd.DataFrame({"elapsed_milliseconds": np.array(values)*1000}).to_csv(directory / "run_summary.csv", index=False)
        rows.append({"condition_index": index, "L": L, "C": C, "budget_mode": mode, "result_path": result_path})
    pd.DataFrame(rows).to_csv(root / "manifest.csv", index=False)
    forecast = runtime_forecasts(root, samples=20, seed=1)
    assert len(forecast) == 12
    assert (forecast["seconds"] > 0).all()
    assert set(forecast["target_L"]) == {160, 192, 256}
