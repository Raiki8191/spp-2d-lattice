import numpy as np
import pandas as pd
from analysis import scaling_v2
from analysis.model_fitting import fit_power_models

def test_unbounded_bootstrap_fit_is_point_estimator():
    L = np.array([8,12,16,24,32,48,64,96,128],float)
    y = .17 + .2*L**-.35 + np.array([0,.002,-.001,.001,0,-.001,.002,0,-.002])
    expected = fit_power_models(L,y)[1]
    observed = scaling_v2._bootstrap_finite_power_fit(L,y)
    np.testing.assert_array_equal(observed["parameters"],expected["parameters"])
    assert observed["rss"] == expected["rss"]
    assert observed["aicc"] == expected["aicc"]
    assert observed["bic"] == expected["bic"]

def test_unbounded_bootstrap_failure_retained(monkeypatch):
    def fail(*args,**kwargs):
        raise RuntimeError("deliberate failed multistart")
    monkeypatch.setattr(scaling_v2,"_bootstrap_finite_power_fit",fail)
    sizes = [8,12,16,24,32]
    events=pd.DataFrame([{"L":L,"budget_mode":"UNBOUNDED","delta_P_max":.3,"run":r} for L in sizes for r in range(3)])
    request=pd.DataFrame({"L":sizes,"condition_index":range(5),"budget_mode":["UNBOUNDED"]*5,
        **{c:[.3]*5 for c in ["delta_P_max_mean","P_before_mean","P_after_mean"]}})
    widths=pd.DataFrame({"condition_index":range(5),"delta_p_mean":[.1]*5})
    _,boot,_=scaling_v2._unbounded_models(events,widths,request,widths,bootstrap_samples=2,bootstrap_seed=9)
    assert len(boot)>0
    assert not boot["converged"].any()
    assert boot["limit"].isna().all()
