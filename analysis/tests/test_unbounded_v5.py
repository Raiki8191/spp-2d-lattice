from __future__ import annotations

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from analysis.unbounded_model_comparison import fit_models, prediction_table
from analysis.unbounded_v5 import l256_observations, metric_summary, prior_prediction_check, summarize_loo


def _run_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    events = pd.DataFrame({
        "L": [256, 256, 256],
        "delta_P_request": [0.2, 0.3, 0.4],
        "p_after": [0.4, 0.5, 0.6],
        "p_mid": [0.35, 0.45, 0.55],
    })
    widths = pd.DataFrame({
        "L": [256, 256, 256],
        "delta_p": [0.20, 0.25, 0.30],
        "delta_t_normalized": [0.01, 0.02, 0.03],
    })
    peaks = pd.DataFrame({"L": [256, 256, 256], "S_peak": [10.0, 12.0, 14.0]})
    return events, widths, peaks


def test_metric_summary_is_correct_and_does_not_mutate_inputs():
    events, widths, peaks = _run_frames()
    originals = tuple(frame.copy(deep=True) for frame in (events, widths, peaks))

    result = metric_summary(events, widths, peaks)

    jump = result.loc[result.observable == "maximum_request_jump"].iloc[0]
    assert jump.value == 0.3
    assert np.isclose(jump.sample_std, 0.1)
    assert np.isclose(jump.sample_sem, 0.1 / np.sqrt(3))
    dispersion = result.loc[result.observable == "request_event_p_dispersion"].iloc[0]
    assert np.isclose(dispersion.value, 0.1)
    for actual, expected in zip((events, widths, peaks), originals):
        assert_frame_equal(actual, expected)


def test_l256_observations_are_reproducible_and_use_bootstrap_sem_for_dispersion():
    events, widths, peaks = _run_frames()
    first = l256_observations(events, widths, peaks, samples=200, seed=42)
    second = l256_observations(events, widths, peaks, samples=200, seed=42)

    assert_frame_equal(first, second)
    dispersion = first.loc[first.observable == "request_event_p_dispersion"].iloc[0]
    assert dispersion["sem"] > 0
    assert dispersion.bootstrap_ci95_low <= dispersion.estimate <= dispersion.bootstrap_ci95_high


def test_loo_summary_matches_hand_calculation():
    loo = pd.DataFrame({
        "observable": ["jump"] * 2,
        "model": ["zero_power"] * 2,
        "prediction_error": [3.0, 4.0],
        "absolute_prediction_error": [3.0, 4.0],
    })
    result = summarize_loo(loo).iloc[0]
    assert result.loo_mae == 3.5
    assert np.isclose(result.loo_rmse, np.sqrt(12.5))
    assert result.largest_error == 4.0


def test_model_outputs_include_aic_correlation_and_requested_prediction_targets():
    sizes = pd.Series([8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256])
    values = pd.Series(0.2 + 0.8 * sizes.to_numpy() ** -0.5)
    fits = fit_models(sizes, values, observable="jump")
    assert {"aic", "aicc", "bic", "limit_decay_correlation"} <= set(fits.columns)

    empty_bootstrap = pd.DataFrame(columns=["observable", "model", "converged"])
    predictions = prediction_table(fits, empty_bootstrap, targets=(320, 768))
    assert set(predictions.target_L) == {320, 768}


def test_prior_prediction_uses_numeric_observed_sem(monkeypatch):
    prior = pd.DataFrame({
        "observable": ["maximum_request_jump"], "target_L": [256],
        "model": ["zero_power"], "prediction": [0.28],
        "prediction_ci95_low": [0.25], "prediction_ci95_high": [0.31],
    })
    monkeypatch.setattr(pd, "read_csv", lambda *_args, **_kwargs: prior.copy())
    l256 = pd.DataFrame({
        "observable": ["maximum_request_jump"], "estimate": [0.281],
        "sem": [0.015], "bootstrap_ci95_low": [0.25],
        "bootstrap_ci95_high": [0.31],
    })
    result = prior_prediction_check(l256)
    assert result.loc[0, "L256_observed_sem"] == 0.015
