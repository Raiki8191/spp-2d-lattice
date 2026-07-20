from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.unbounded_model_comparison import (
    bootstrap_models,
    fit_models,
    leave_one_size_out,
    predict,
    summarize_bootstrap,
)
from analysis.unbounded_v4 import _prediction_intervals_overlap, metric_summary


def test_all_asymptotic_models_fit_and_predict_positive_values() -> None:
    sizes = np.array([8, 12, 16, 24, 32, 48, 64, 96, 128, 192], float)
    values = 0.2 + 0.8 * sizes ** -0.5
    fits = fit_models(sizes, values, observable="jump")
    assert set(fits.model) == {"zero_power", "finite_power", "zero_log", "finite_log"}
    assert fits.converged.all()
    finite = fits.loc[fits.model == "finite_power"].iloc[0].to_dict()
    assert abs(float(finite["limit"]) - 0.2) < 1e-5
    assert predict(finite, 256) > 0


def test_leave_one_size_out_reports_every_model_and_size() -> None:
    frame = pd.DataFrame({"L": [8, 12, 16, 24, 32, 48, 64],
                          "value": 0.5 * np.array([8, 12, 16, 24, 32, 48, 64]) ** -0.2})
    result = leave_one_size_out(frame, "value", "jump")
    assert len(result) == 4 * len(frame)
    assert set(result.omitted_L) == set(frame.L)
    assert result.prediction_error.notna().all()


def test_stratified_bootstrap_is_reproducible_and_reports_boundaries() -> None:
    rows = []
    for L in (8, 12, 16, 24, 32, 48, 64):
        for run in range(6):
            rows.append({"L": L, "run": run, "value": (1 + run / 20) * L ** -0.2})
    frame = pd.DataFrame(rows)
    first = bootstrap_models(frame, value_column="value", aggregation="mean",
                             observable="jump", samples=5, seed=7)
    second = bootstrap_models(frame, value_column="value", aggregation="mean",
                              observable="jump", samples=5, seed=7)
    pd.testing.assert_frame_equal(first, second)
    summary = summarize_bootstrap(first)
    assert {"boundary_frequency", "fit_failure_frequency", "ci95_low", "ci95_high"}.issubset(summary)


def test_metric_summary_uses_mean_and_run_dispersion_without_mutating_inputs() -> None:
    events = pd.DataFrame({
        "L": [8, 8, 12, 12], "delta_P_request": [.3, .5, .2, .4],
        "p_mid": [.4, .6, .5, .8],
    })
    widths = pd.DataFrame({
        "L": [8, 8, 12, 12], "delta_p": [.2, .4, .3, .5],
        "delta_t_normalized": [.1, .2, .2, .3],
    })
    events_before, widths_before = events.copy(deep=True), widths.copy(deep=True)
    summary = metric_summary(events, widths)
    assert summary.loc[(summary.observable == "maximum_request_jump") & (summary.L == 8), "value"].iloc[0] == .4
    assert np.isclose(summary.loc[(summary.observable == "request_event_p_dispersion") & (summary.L == 8), "value"].iloc[0], np.std([.4, .6], ddof=1))
    pd.testing.assert_frame_equal(events, events_before)
    pd.testing.assert_frame_equal(widths, widths_before)


def test_prediction_interval_overlap_is_computed_not_assumed() -> None:
    overlapping = pd.DataFrame({"prediction_ci95_low": [0.1, 0.2],
                                "prediction_ci95_high": [0.3, 0.4]})
    separated = pd.DataFrame({"prediction_ci95_low": [0.1, 0.4],
                              "prediction_ci95_high": [0.2, 0.5]})
    assert _prediction_intervals_overlap(overlapping)
    assert not _prediction_intervals_overlap(separated)
