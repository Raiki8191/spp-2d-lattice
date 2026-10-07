"""Regression coverage for the historical v3 UNBOUNDED estimator contract."""

import numpy as np
import pandas as pd
import pytest

import analysis.scaling_v3 as v3


SIZES = np.array([8, 12, 16, 24, 32, 48], dtype=float)


def run_data():
    events, widths = [], []
    for mode, C in (("FINITE", 1), ("FINITE", 2), ("UNBOUNDED", 0)):
        for L in SIZES:
            for run, factor in enumerate((.97, 1.0, 1.03)):
                events.append({
                    "L": L, "C": C, "budget_mode": mode, "run": run,
                    "P_before": factor * L**-.1, "P_after": factor * L**-.15,
                    "S_before": factor * L**1.7, "S_after": factor * L**1.8,
                    "p_mid": .5 + .03 * (run - 1) * L**-.4,
                    "delta_P_max": factor * (.02 + .6 * L**-.2),
                })
                widths.append({"L": L, "C": C, "budget_mode": mode, "run": run,
                               "delta_p": factor * .32 * L**-.025})
    return pd.DataFrame(events), pd.DataFrame(widths)


def test_v3_keeps_its_original_starts_bounds_and_default_optimizer_budget(monkeypatch):
    calls = []

    def record(function, L, y, starts, bounds, names, *, model, **kwargs):
        calls.append((model, tuple(starts), bounds, names, kwargs))
        return {"model": model}

    monkeypatch.setattr(v3, "fit_bounded_multistart", record)
    v3.fit_unbounded_models(SIZES, .5 * SIZES**-.2)
    expected = {
        "zero_power": (tuple((1, q) for q in (.05, .2, .5, 1, 2)),
                       ((1e-12, .001), (10, 5))),
        "finite_power": (tuple((c, 1, q) for c in (0, .1, .3) for q in (.05, .2, .5, 1)),
                         ((0, 1e-12, .001), (1, 10, 5))),
        "zero_log": (tuple((1, q) for q in (.1, .5, 1, 2, 4)),
                     ((1e-12, .001), (10, 10))),
        "finite_log": (tuple((c, 1, q) for c in (0, .1, .3) for q in (.1, .5, 1, 2)),
                       ((0, 1e-12, .001), (1, 10, 10))),
    }
    for model, starts, bounds, names, kwargs in calls:
        assert (starts, bounds) == expected[model]
        assert names == (("limit", "amplitude", "decay_exponent")
                         if model.startswith("finite_") else ("amplitude", "decay_exponent"))
        assert kwargs == {}  # Retain the fitter's original maxfev=5_000 default.


def test_bootstrap_wrapper_uses_the_single_point_estimator(monkeypatch):
    marker = [{"model": model} for model in v3.UNBOUNDED_MODEL_SPECS]
    seen = []

    def estimator(L, y):
        seen.append((L, y))
        return marker

    monkeypatch.setattr(v3, "fit_unbounded_models", estimator)
    values = .5 * SIZES**-.2
    assert v3._bootstrap_ub_models(SIZES, values) is marker
    assert len(seen) == 1
    assert seen[0][0] is SIZES and seen[0][1] is values


@pytest.mark.parametrize("model", tuple(v3.UNBOUNDED_MODEL_SPECS))
def test_identity_resampling_matches_primary_fit_and_diagnostics(monkeypatch, model):
    class IdentityRng:
        def integers(self, low, high, size):
            assert low == 0 and size == high
            return np.arange(size)

    events, widths = run_data()
    monkeypatch.setattr(v3.np.random, "default_rng", lambda seed: IdentityRng())
    actual = v3.bootstrap_primary(events, widths, pd.DataFrame(), pd.DataFrame(),
                                  samples=1, seed=19, unbounded_only=True)
    for observable, frame, column in (
        ("delta_P_request", events, "delta_P_max"),
        ("transition_delta_p", widths, "delta_p"),
    ):
        grouped = frame.loc[frame.budget_mode == "UNBOUNDED"].groupby("L", sort=True)
        # Use the exact aggregation performed by bootstrap_primary.  Pandas
        # group.mean has a different summation path; sub-ulp input changes can
        # change log(RSS) substantially for nearly exact synthetic fits.
        values = np.array([np.nanmean(group[column].to_numpy(float)) for _, group in grouped])
        expected = next(fit for fit in v3.fit_unbounded_models(SIZES, values) if fit["model"] == model)
        row = actual.loc[(actual.observable == observable) & (actual.model == model)].iloc[0]
        for column_name, key in (("exponent", "decay_exponent"), ("amplitude", "amplitude"),
                                 ("rss", "rss"), ("aicc", "aicc"), ("bic", "bic")):
            assert row[column_name] == pytest.approx(expected[key], rel=1e-9, abs=1e-10)
        assert row["limit"] == pytest.approx(expected.get("limit", 0.0), abs=1e-9)
        for key in ("converged", "covariance_ok", "boundary_solution", "start_count",
                    "converged_start_count", "point_count", "parameter_count"):
            assert row[key] == expected[key]


def test_decreasing_width_cannot_return_the_old_negative_amplitude_solution():
    values = .3 * SIZES**-.015
    for fit in v3._bootstrap_ub_models(SIZES, values):
        assert fit["converged"]
        assert 1e-12 <= fit["amplitude"] <= 10
        assert .001 <= fit["decay_exponent"] <= (10 if "log" in fit["model"] else 5)
        if fit["model"].startswith("finite_"):
            assert 0 <= fit["limit"] <= 1
        function, _, _, names = v3.UNBOUNDED_MODEL_SPECS[fit["model"]]
        residuals = values - function(SIZES, *[fit[name] for name in names])
        assert fit["rss"] == pytest.approx(np.sum(residuals**2), rel=1e-12, abs=1e-20)


def test_unbounded_only_keeps_original_draws_and_fixed_seed(monkeypatch):
    events, widths = run_data()

    def stub_power(L, y, **kwargs):
        return [{"model": "simple_power", "converged": True, "exponent": -.2,
                 "amplitude": 1.0, "boundary_solution": False}]

    monkeypatch.setattr(v3, "power_model_fits", stub_power)
    monkeypatch.setattr(v3, "_selected_omega", lambda *args: 1.0)
    monkeypatch.setattr(v3, "_bootstrap_joint_and_shift", lambda *args, **kwargs: [])
    full = v3.bootstrap_primary(events, widths, pd.DataFrame(), pd.DataFrame(), samples=2, seed=101)
    ub_only = v3.bootstrap_primary(events, widths, pd.DataFrame(), pd.DataFrame(),
                                   samples=2, seed=101, unbounded_only=True)
    repeat = v3.bootstrap_primary(events, widths, pd.DataFrame(), pd.DataFrame(),
                                  samples=2, seed=101, unbounded_only=True)
    expected = full.loc[full.condition_label == "UNBOUNDED"].reset_index(drop=True)
    # The mixed-condition table infers object/float columns where finite rows
    # have no UNBOUNDED diagnostics.  Compare the extracted UB table using the
    # UB-only schema, with the same values and strict numeric equality.
    expected = expected.astype(ub_only.dtypes.to_dict())
    pd.testing.assert_frame_equal(ub_only, expected)
    pd.testing.assert_frame_equal(ub_only, repeat)


def test_failures_retain_common_diagnostics_and_are_not_used_for_prediction_intervals():
    fits = v3._bootstrap_ub_models(np.array([8., 16., 32.]), np.array([.4, .3, .2]))
    assert all(not fit["converged"] for fit in fits)
    assert all(fit["failure"] == "insufficient points for finite AICc" for fit in fits)
    predictions = pd.DataFrame([{"observable": "delta_P_request", "model": "zero_power",
                                 "target_L": 192, "prediction": .2}])
    bootstrap = pd.DataFrame([
        {"condition_label": "UNBOUNDED", "observable": "delta_P_request", "model": "zero_power",
         "converged": False, "exponent": 100., "amplitude": 999., "limit": 999.},
        {"condition_label": "UNBOUNDED", "observable": "delta_P_request", "model": "zero_power",
         "converged": True, "exponent": .2, "amplitude": .6, "limit": 0.},
    ])
    result = v3.attach_prediction_intervals(predictions, bootstrap).iloc[0]
    assert result["prediction_ci95_low"] == pytest.approx(.6 * 192**-.2)
    assert result["prediction_ci95_high"] == pytest.approx(.6 * 192**-.2)
