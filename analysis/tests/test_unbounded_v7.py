import pandas as pd
import pytest

from analysis.unbounded_v7 import (
    compare_l320_l384, experiment_options, local_effective_exponents, parametric_identification,
    score_l384_preregistration, thesis_tables,
)
from analysis.unbounded_model_comparison import fit_models


def test_size_comparison_is_deterministic_and_does_not_mutate():
    events=pd.DataFrame({"L":[320]*3+[384]*3,"delta_P_request":[.3,.2,.25,.2,.15,.1]})
    original=events.copy(deep=True)
    first=compare_l320_l384(events,samples=100,seed=7); second=compare_l320_l384(events,samples=100,seed=7)
    pd.testing.assert_frame_equal(first,second); pd.testing.assert_frame_equal(events,original)
    assert first.loc[0,"mean_difference_right_minus_left"]==pytest.approx(-.1)


def test_local_effective_exponents_are_exact_for_power_law():
    summary=pd.DataFrame({"observable":["maximum_request_jump"]*3,"L":[2,4,8],"value":[.5,.25,.125]})
    result=local_effective_exponents(summary)
    assert list(result.power_effective_exponent)==pytest.approx([1.,1.])


def test_parametric_identification_is_reproducible():
    sizes=pd.Series([8,16,32,64,128,256,384])
    values=1/sizes**.1
    summary=pd.DataFrame({"observable":"maximum_request_jump","L":sizes,"value":values,"sample_sem":.002})
    fits=fit_models(sizes,values,observable="maximum_request_jump")
    first=parametric_identification(summary,fits,samples=10,seed=3); second=parametric_identification(summary,fits,samples=10,seed=3)
    pd.testing.assert_frame_equal(first,second)
    assert first.groupby("true_model").selection_rate.sum().eq(1).all()


def test_scoring_adds_predictive_density_without_mutation():
    predictions=pd.DataFrame({"observable":["maximum_request_jump"],"model":["zero_power"],"prediction":[.2],"prediction_interval95_low":[.1],"prediction_interval95_high":[.3],"prediction_ci95_low":[.15],"prediction_ci95_high":[.25]})
    observations=pd.DataFrame({"observable":["maximum_request_jump"],"mean_or_estimate":[.22],"sem":[.01],"bootstrap_ci95_low":[.2],"bootstrap_ci95_high":[.24]})
    original=predictions.copy(deep=True); result=score_l384_preregistration(predictions,observations)
    assert result.predictive_log_density.notna().all(); pd.testing.assert_frame_equal(predictions,original)


def test_thesis_summary_uses_reproducible_bootstrap_interval():
    events=pd.DataFrame({"L":[8]*4,"delta_P_request":[.1,.2,.3,.4],"p_after":[.2,.3,.4,.5],"p_mid":[.15,.25,.35,.45]})
    widths=pd.DataFrame({"L":[8]*4,"delta_p":[.1]*4,"delta_t_normalized":[.01]*4})
    peaks=pd.DataFrame({"L":[8]*4,"S_peak":[2.,3.,4.,5.]})
    history=pd.DataFrame({"observable":["maximum_request_jump"],"version":["v7"],"L_max":[8],"model":["zero_power"],"aicc":[1.],"bic":[2.],"loo_mae":[.1],"loo_rmse":[.2],"limit":[0.],"ci95_low":[0.],"ci95_high":[0.],"max_parameter_correlation":[.5],"boundary_solution":[False]})
    first,_=thesis_tables(pd.DataFrame(),history,events,widths,peaks)
    second,_=thesis_tables(pd.DataFrame(),history,events,widths,peaks)
    pd.testing.assert_frame_equal(first,second)
    assert first.maximum_request_jump_bootstrap_ci95_low.iloc[0] <= .25
    assert first.maximum_request_jump_bootstrap_ci95_high.iloc[0] >= .25


def test_experiment_options_reports_runs_needed_for_model_range():
    metadata=pd.DataFrame({"elapsed_milliseconds":[1000,1200],"results_bytes":[100,120]})
    observations=pd.DataFrame({"observable":["maximum_request_jump"],"sample_std":[.06],"sem":[.01]})
    predictions=pd.DataFrame({"observable":["maximum_request_jump"]*2,"target_L":[512,512],"prediction":[.25,.26]})
    result=experiment_options(metadata,observations,predictions)
    row=result.loc[result.option.eq("A L384 total50")].iloc[0]
    assert row.required_sem_to_resolve_range==pytest.approx(.005)
    assert row.estimated_runs_for_required_sem==144
