"""Safety and input-provenance checks for retrospective correction generation."""

import numpy as np
import pandas as pd
import pytest

from analysis import unbounded_bootstrap_correction as correction


def test_existing_destination_is_rejected_before_input_read(tmp_path, monkeypatch):
    output = tmp_path / "completed"
    output.mkdir()
    marker = output / "research.csv"
    marker.write_bytes(b"original research data\n")
    monkeypatch.setattr(correction, "load_run_metrics",
                        lambda *_: pytest.fail("must reject before loading data"))
    with pytest.raises(FileExistsError):
        correction.run_correction("v7", output, samples=1)
    assert marker.read_bytes() == b"original research data\n"


def test_v3_existing_destination_is_also_preserved(tmp_path):
    output = tmp_path / "completed-v3"
    output.mkdir()
    marker = output / "finite_s_after.csv"
    marker.write_bytes(b"preserve finite-C products\n")
    with pytest.raises(FileExistsError):
        correction.run_v3_correction(output, samples=1)
    assert marker.read_bytes() == b"preserve finite-C products\n"


def test_loader_chain_preserves_original_stage_order(monkeypatch):
    calls = []

    def first(paths):
        calls.append([path.as_posix() for path in paths])
        return pd.DataFrame({"L": [8, 192], "marker": [1, 2]}), pd.DataFrame({"L": [8, 192]})

    def later(paths):
        calls.append([path.as_posix() for path in paths])
        size = int(paths[0].parts[-3].removeprefix("unbounded-l"))
        return None, pd.DataFrame({"L": [size], "marker": [size]}), pd.DataFrame({"L": [size]})

    monkeypatch.setattr(correction, "load_all_run_metrics", first)
    monkeypatch.setattr(correction, "load_stage_runs", later)
    events, widths, manifests = correction.load_run_metrics("v7")
    assert events.L.tolist() == [8, 192, 256, 320, 384]
    assert widths.L.tolist() == events.L.tolist()
    assert [len(paths) for paths in calls] == [3, 2, 2, 2]
    assert len(manifests) == 9
    assert calls[0][-1].endswith("unbounded-l192/main/manifest.csv")


def test_summary_preflight_detects_missing_run_and_changed_value():
    original = pd.DataFrame({"observable": ["jump"], "L": [8], "run_count": [3], "value": [.3]})
    correction.validate_summary(original, original)
    for column, replacement in [("run_count", 2), ("value", .31)]:
        changed = original.copy()
        changed[column] = replacement
        with pytest.raises(ValueError):
            correction.validate_summary(changed, original)
    with pytest.raises(ValueError):
        correction.validate_summary(original, original.iloc[:0])


def test_std_metric_uses_runs_and_ddof_one():
    events = pd.DataFrame({"L": [8, 8, 8], "delta_P_request": [.1, .2, .3],
                           "p_mid": [.2, .3, .6], "p_after": [.3, .4, .7]})
    widths = pd.DataFrame({"L": [8, 8, 8], "delta_p": [.01, .02, .03],
                           "delta_t_normalized": [.04, .05, .06]})
    summary = correction.summarize_run_metrics("v7", events, widths)
    dispersion = summary.loc[summary.observable == "request_event_p_dispersion"].iloc[0]
    assert dispersion.value == pytest.approx(np.std(events.p_mid, ddof=1))
    assert dispersion.run_count == 3
    assert "request_event_p_after" in set(summary.observable)
    v4 = correction.summarize_run_metrics("v4", events, widths)
    assert "request_event_p_after" not in set(v4.observable)


def test_worker_calls_production_bootstrap_with_original_seed_and_runs(monkeypatch):
    runs = pd.DataFrame({"L": [8, 8], "jump": [.1, .2]})
    captured = {}

    def production(data, **kwargs):
        captured.update(kwargs)
        assert data is runs
        return pd.DataFrame({"sample": [0]})

    monkeypatch.setattr(correction, "bootstrap_models", production)
    result = correction._bootstrap_task(("maximum_request_jump", "jump", "mean", runs, 500, 20260720))
    assert captured == {"value_column": "jump", "aggregation": "mean",
                        "observable": "maximum_request_jump", "samples": 500, "seed": 20260720}
    assert result["sample"].tolist() == [0]


def test_corrected_only_amplitude_ci_is_retained_in_comparison():
    keys = {"observable": ["jump"], "model": ["zero_power"]}
    old = pd.DataFrame({**keys, "parameter": ["decay_exponent"],
                        "median": [.2], "ci95_low": [.1], "ci95_high": [.3]})
    corrected = pd.DataFrame({"observable": ["jump", "jump"], "model": ["zero_power", "zero_power"],
                              "parameter": ["decay_exponent", "amplitude"], "median": [.2, .7],
                              "ci95_low": [.1, .6], "ci95_high": [.3, .8]})
    comparison = correction.interval_comparison(old, corrected)
    amplitude = comparison.loc[comparison.parameter == "amplitude"].iloc[0]
    assert np.isnan(amplitude.ci95_low_historical)
    assert amplitude.ci95_low_corrected == .6


def test_retrospective_score_preserves_frozen_point_and_original_pi_formula(monkeypatch):
    frozen = pd.DataFrame({"observable": ["maximum_request_jump"], "model": ["zero_power"],
                           "target_L": [320], "prediction": [.4],
                           "prediction_ci95_low": [.35], "prediction_ci95_high": [.45],
                           "prediction_interval95_low": [.2], "prediction_interval95_high": [.6]})
    observed = pd.DataFrame({"observable": ["maximum_request_jump"], "mean_or_estimate": [.45]})
    _, frozen_path, observation_path = correction.retrospective_sources("v5")

    def read(path, **_):
        if path == frozen_path:
            return frozen.copy()
        assert path == observation_path
        return observed.copy()

    monkeypatch.setattr(correction.pd, "read_csv", read)
    corrected = pd.DataFrame({"observable": ["maximum_request_jump"], "model": ["zero_power"],
                              "target_L": [320], "prediction": [.4000000001],
                              "prediction_ci95_low": [.35], "prediction_ci95_high": [.47]})
    fits = pd.DataFrame({"observable": ["maximum_request_jump"], "model": ["zero_power"],
                        "residual_rms": [.02]})
    score = correction.retrospective_scores("v5", corrected, fits).iloc[0]
    # Independent equivalent: variances add in the original scale, retaining
    # the fixed point as PI centre.  An asymmetric bootstrap CI is intentional.
    half = np.hypot(.06, 1.96 * .02)
    assert score.fixed_point_prediction == .4
    assert score.point_prediction_error == pytest.approx(-.05)
    assert score.corrected_interval_low == pytest.approx(.4 - half)
    assert score.corrected_interval_high == pytest.approx(.4 + half)
    assert score.historical_interval_low == .2
    assert score.historical_interval_high == .6
    assert "retrospective" in score.analysis_status
