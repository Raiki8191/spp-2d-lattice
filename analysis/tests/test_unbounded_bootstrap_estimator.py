"""Regression checks for the Phase 4 UNBOUNDED estimator mismatch."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import analysis.unbounded_model_comparison as comparison


SIZES = np.array([8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256, 320, 384])
# Historical summaries are copied here so these regressions do not require
# ignored experiment outputs or permit later output regeneration to redefine
# the fixture.  Source: unbounded-v7/unbounded_size_summary.csv, delta_t/N^2.
V7_DELTA_T = np.array([
    .019881591796875, .011978443287036985, .008641128540039062,
    .004992781274112604, .0030751323699950706, .001727314701786698,
    .001074438691139175, .00057526085111825, .00034824273549015225,
    .00018303294240692517, .00010925038950517773,
    7.547833442687989e-05, 5.7520436835877683e-05,
])
# Source: unbounded-v4/main50/unbounded_size_summary.csv, delta_p.
V4_DELTA_P = np.array([
    .27290178571428575, .28316287878787877, .29463541666666665,
    .3013269927536232, .3047379032258064, .2975975177304965,
    .2890426587301587, .2832517817982456, .27356060839074803,
    .26333387870855146,
])


class IdentityDraw:
    """Use each run once, preserving the data and its aggregation."""

    def integers(self, low: int, high: int, size: int) -> np.ndarray:
        assert low == 0 and high == size
        return np.arange(size)


def _identity_bootstrap(monkeypatch, frame, aggregation="mean"):
    monkeypatch.setattr(comparison.np.random, "default_rng", lambda seed: IdentityDraw())
    return comparison.bootstrap_models(
        frame, value_column="value", aggregation=aggregation,
        observable="regression", samples=1, seed=20260720,
    )


@pytest.mark.parametrize("aggregation", ["mean", "std"])
def test_identity_resampling_uses_exact_point_estimator_for_all_models(
    monkeypatch, aggregation,
):
    rows = [
        {"L": int(L), "value": (0.2 + 0.8 * L ** -.4) * factor}
        for L in SIZES[:8] for factor in (.8, 1.0, 1.2)
    ]
    frame = pd.DataFrame(rows)
    values = frame.groupby("L").value.agg(
        np.mean if aggregation == "mean" else lambda x: np.std(x, ddof=1)
    )
    point = comparison.fit_models(values.index, values, observable="regression")
    bootstrap = _identity_bootstrap(monkeypatch, frame, aggregation)
    assert set(point.model) == set(comparison.MODEL_SPECS)
    assert bootstrap.converged.all()
    # This compares every saved diagnostic, not only the fitted exponent.
    pd.testing.assert_frame_equal(bootstrap.loc[:, point.columns], point)


def test_declared_bounds_and_bootstrap_results_agree_for_all_parameters(monkeypatch):
    expected = {
        "zero_power": ((1e-12, .001), (10.0, 5.0)),
        "finite_power": ((0.0, 1e-12, .001), (1.0, 10.0, 5.0)),
        "zero_log": ((1e-12, .001), (10.0, 10.0)),
        "finite_log": ((0.0, 1e-12, .001), (1.0, 10.0, 10.0)),
    }
    frame = pd.DataFrame({"L": SIZES[:10], "value": V4_DELTA_P})
    bootstrap = _identity_bootstrap(monkeypatch, frame)
    assert bootstrap.converged.all()
    for fit in bootstrap.to_dict("records"):
        _, _, bounds, parameters = comparison.MODEL_SPECS[fit["model"]]
        assert bounds == expected[fit["model"]]
        for parameter, lower, upper in zip(parameters, *bounds):
            assert lower <= fit[parameter] <= upper
    # The old finite-power helper returned approximately -502.881 amplitude
    # on this fixture.  Both finite models must retain the positive constraint.
    assert bootstrap.loc[bootstrap.model.str.startswith("finite"), "amplitude"].gt(0).all()


def test_v7_delta_t_identity_uses_original_scale_estimator(monkeypatch):
    frame = pd.DataFrame({"L": SIZES, "value": V7_DELTA_T})
    point = comparison.fit_models(SIZES, V7_DELTA_T, observable="regression")
    bootstrap = _identity_bootstrap(monkeypatch, frame)
    pd.testing.assert_frame_equal(bootstrap.loc[:, point.columns], point)
    zero_power = bootstrap.loc[bootstrap.model == "zero_power"].iloc[0]
    zero_log = bootstrap.loc[bootstrap.model == "zero_log"].iloc[0]
    assert zero_power.decay_exponent == pytest.approx(1.2948665238, abs=1e-6)
    assert zero_log.decay_exponent == pytest.approx(3.5103198695, abs=1e-6)
    # An independent calculation documents the old, different log-scale
    # estimator.  It must not silently become the production estimator again.
    old_exponent = -np.polyfit(np.log(SIZES), np.log(V7_DELTA_T), 1)[0]
    assert old_exponent == pytest.approx(1.5407952590, abs=1e-9)
    prediction = comparison.predict(zero_power, SIZES)
    assert zero_power.rss == pytest.approx(np.sum((V7_DELTA_T - prediction) ** 2))


def test_fixed_seed_preserves_draws_and_shared_estimator_call(monkeypatch):
    seed = 20260720
    frame = pd.DataFrame([
        {"L": L, "value": value}
        for L, values in ((16, [3., 4., 5.]), (8, [1., 2.]))
        for value in values
    ])
    observed = []

    def recording_estimator(sizes, values, *, observable):
        observed.append((np.array(sizes), np.array(values), observable))
        return pd.DataFrame([
            {"model": model, "observable": observable, "converged": True,
             "limit": .1 if model.startswith("finite") else 0.,
             "amplitude": .5, "decay_exponent": .2,
             "boundary_solution": False, "covariance_ok": True,
             "failure": "", "start_count": 123}
            for model in comparison.MODEL_SPECS
        ])

    monkeypatch.setattr(comparison, "fit_models", recording_estimator)
    def forbidden_quick(*args, **kwargs):
        pytest.fail("the removed quick estimator was invoked")
    monkeypatch.setattr(comparison, "_quick_models", forbidden_quick, raising=False)
    kwargs = dict(value_column="value", aggregation="mean", observable="draws",
                  samples=3, seed=seed)
    first = comparison.bootstrap_models(frame, **kwargs)
    first_draws = observed.copy()
    observed.clear()
    second = comparison.bootstrap_models(frame, **kwargs)
    pd.testing.assert_frame_equal(first, second)
    rng = np.random.default_rng(seed)
    groups = [np.array([1., 2.]), np.array([3., 4., 5.])]
    for call, repeated_call in zip(first_draws, observed):
        expected = [np.mean(values[rng.integers(0, len(values), len(values))])
                    for values in groups]
        np.testing.assert_array_equal(call[0], [8, 16])
        np.testing.assert_array_equal(call[1], expected)
        np.testing.assert_array_equal(call[1], repeated_call[1])
        assert call[2] == "draws"
    assert first.start_count.eq(123).all()  # Shared diagnostics are retained.


def test_failed_shared_fits_are_retained_with_diagnostics():
    frame = pd.DataFrame({"L": [8, 12, 16], "value": [.4, .3, .2]})
    fits = comparison.bootstrap_models(
        frame, value_column="value", aggregation="mean", observable="failure",
        samples=1, seed=7,
    )
    assert set(fits.model) == set(comparison.MODEL_SPECS)
    assert not fits.converged.any()
    assert not fits.covariance_ok.any()
    assert not fits.finite_limit_zero_boundary.any()
    assert fits.failure.eq("insufficient points for finite AICc").all()
    assert fits.amplitude.isna().all() and fits.decay_exponent.isna().all()
    assert comparison.summarize_bootstrap(fits).empty


def test_summary_reports_amplitude_and_separate_zero_limit_diagnostics():
    fits = pd.DataFrame([
        {"observable": "jump", "model": "finite_power", "converged": True,
         "boundary_solution": True, "covariance_ok": True,
         "limit": 1e-12, "amplitude": .3, "decay_exponent": .2,
         "limit_decay_correlation": .95},
        {"observable": "jump", "model": "finite_power", "converged": True,
         "boundary_solution": True, "covariance_ok": True,
         "limit": .2, "amplitude": .8, "decay_exponent": .5,
         "limit_decay_correlation": .97},
    ])
    summary = comparison.summarize_bootstrap(fits)
    assert set(summary.parameter) == {"limit", "amplitude", "decay_exponent"}
    amplitude = summary.loc[summary.parameter == "amplitude"].iloc[0]
    assert amplitude.ci95_low == pytest.approx(.3125)
    assert amplitude.ci95_high == pytest.approx(.7875)
    assert amplitude.boundary_frequency == 1.
    assert amplitude.finite_limit_zero_boundary_frequency == .5
    assert amplitude.local_limit_decay_correlation_median == pytest.approx(.96)
    assert amplitude.bootstrap_limit_decay_correlation == pytest.approx(1.)
