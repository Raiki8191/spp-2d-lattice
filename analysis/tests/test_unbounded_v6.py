import pandas as pd
import pytest

from analysis.unbounded_v6 import (
    score_preregistered, sequential_prediction_performance,
    size_observations, summarize_extrapolations,
)


def test_preregistered_scoring_and_interval_flags_do_not_mutate_inputs():
    predictions=pd.DataFrame({"observable":["maximum_request_jump"],"model":["zero_log"],"prediction":[.28],"prediction_interval95_low":[.25],"prediction_interval95_high":[.31]})
    observations=pd.DataFrame({"observable":["maximum_request_jump"],"mean_or_estimate":[.29],"sem":[.01],"bootstrap_ci95_low":[.27],"bootstrap_ci95_high":[.30]})
    original=predictions.copy(deep=True); result=score_preregistered(predictions,observations)
    assert result.loc[0,"signed_error"]==pytest.approx(.01)
    assert result.loc[0,"standardized_error"]==pytest.approx(1.0)
    assert result.loc[0,"observed_inside_prediction_interval"]
    pd.testing.assert_frame_equal(predictions,original)


def test_size_observations_are_deterministic_and_include_all_metrics():
    events=pd.DataFrame({"L":[320]*3,"delta_P_request":[.2,.3,.4],"p_after":[.4,.5,.6],"p_mid":[.35,.45,.55]})
    widths=pd.DataFrame({"L":[320]*3,"delta_p":[.2,.25,.3],"delta_t_normalized":[.01,.02,.03]})
    peaks=pd.DataFrame({"L":[320]*3,"S_peak":[10.,12.,14.]})
    first=size_observations(events,widths,peaks,L=320,samples=100,seed=4)
    second=size_observations(events,widths,peaks,L=320,samples=100,seed=4)
    pd.testing.assert_frame_equal(first,second)
    assert len(first)==6
    assert set(first.run_count)=={3}


def test_extrapolation_summary_uses_v6_observed_frontier():
    predictions = pd.DataFrame({
        "observable": ["jump", "jump"], "target_L": [640, 640],
        "model": ["a", "b"], "prediction": [.2, .3],
        "prediction_ci95_low": [.1, .2], "prediction_ci95_high": [.25, .4],
        "largest_observed_L": [320, 320],
    })
    result = summarize_extrapolations(predictions)
    assert result.loc[0, "distance_from_largest_observed_L"] == 2.0
    assert result.loc[0, "between_model_range"] == pytest.approx(.1)
    assert result.loc[0, "all_intervals_overlap"]


def test_sequential_prediction_errors_are_observed_minus_prediction(monkeypatch):
    v3 = pd.DataFrame({
        "observable": ["maximum_request_jump"], "model": ["zero_log"],
        "L192_observed": [.30], "v3_L192_prediction": [.28],
        "v3_prediction_error": [-.02],
    })
    v5 = pd.DataFrame({
        "model": ["zero_log"], "L256_observed_mean": [.29],
        "v4_prior_prediction": [.285], "prior_prediction_error": [-.005],
        "absolute_prior_prediction_error": [.005],
    })
    original = pd.read_csv
    monkeypatch.setattr(pd, "read_csv", lambda path, *args, **kwargs:
                        v3 if "v3_v4" in str(path) else v5)
    scored = pd.DataFrame({
        "observable": ["maximum_request_jump"], "model": ["zero_log"],
        "observed": [.27], "prediction": [.28], "signed_error": [-.01],
        "absolute_error": [.01],
    })
    result = sequential_prediction_performance(scored)
    assert list(result.error) == pytest.approx([.02, .005, -.01])
    monkeypatch.setattr(pd, "read_csv", original)
