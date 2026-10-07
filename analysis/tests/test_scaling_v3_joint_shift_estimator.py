from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from analysis import scaling_v3 as v3
from analysis.correction_fitting import corrected_shift, fit_bounded_multistart
from analysis.scaling_v3_joint_shift_correction import advance_primary_draws, draw_joint_statistics, run_correction
from analysis.universality_fitting import fit_universality_models


def _events():
    rows = []
    for C in (1, 2):
        for L in (8, 12, 16, 24):
            for run in range(5):
                rows.append(dict(budget_mode="FINITE", C=C, L=L, run_index=run,
                                 P_before=.6-.01*run, P_after=.5-.01*run,
                                 S_before=float(L+run), S_after=float(L+2*run),
                                 p_mid=.4+.001*run, delta_P_max=.1))
    for L in (8, 12, 16, 24):
        for run in range(5):
            rows.append(dict(budget_mode="UNBOUNDED", C=0, L=L, run_index=run,
                             P_before=.6-.01*run, P_after=.4-.01*run,
                             S_before=float(L+run), S_after=float(L+2*run),
                             p_mid=.3+.001*run, delta_P_max=.2))
    return pd.DataFrame(rows)


def _statistics():
    L=np.array([8, 12, 16, 24, 32, 48, 64, 96, 128], float)
    return {name:[(L,.5*L**-.1),(L,.6*L**-.1)]
            for name in ("P_before","P_after","S_before","S_after","std_p_mid","p_mid_shift")}


def _fake_fit(model, **parameters):
    return dict(model=model, converged=True, admissible=False,
                boundary_solution=True, covariance_ok=True, start_count=4,
                converged_start_count=4, parameter_count=8, point_count=18,
                rss=1.25, aicc=2.0, bic=3.0, failure="", **parameters)


def test_model_filter_returns_identical_actual_point_fits():
    L=np.array([8,12,16,24,32,48,64,96,128],float)
    y1=.6*L**-.11*(1+.7/L)
    y2=.7*L**-.11*(1-.4/L)
    full=fit_universality_models(L,y1,L,y2,fixed_omegas=(1.,))
    selected={"U1_independent","U2_shared_exponent","U3_shared_exponent_omega_1"}
    subset=fit_universality_models(L,y1,L,y2,fixed_omegas=(1.,),include_models=selected)
    assert {fit["model"] for fit in subset} == selected
    for fit in subset:
        original=next(row for row in full if row["model"]==fit["model"])
        for key in ("rss","aicc","bic","start_count","converged_start_count","parameter_count"):
            assert fit[key] == original[key]
        np.testing.assert_array_equal(fit["prediction"],original["prediction"])


@pytest.mark.parametrize("C",[1,2])
def test_fixed_shift_helper_uses_actual_point_bounds_starts_and_objective(C):
    L=np.array([8,12,16,24,32,48,64,96,128],float)
    y=corrected_shift(L,.5,-.08,.6,4.,1.)
    if C==1:
        expected=fit_bounded_multistart(
            lambda L,a,q,b:corrected_shift(L,.5,a,q,b,1.),L,y,
            ((a,q,b) for a in(-.5,.5) for q in(.5,.75,1) for b in(-1,1)),
            ((-10,.05,-20),(10,4,20)),("amplitude","inverse_nu","correction"),
            model="corrected_shift_pc_0.5_omega_1")
    else:
        expected=fit_bounded_multistart(
            lambda L,pc,a,q,b:corrected_shift(L,pc,a,q,b,1.),L,y,
            ((pc,a,q,b) for pc in(.45,.5,.55) for a in(-.5,.5)
             for q in(.5,.75,1) for b in(-1,1)),
            ((0,-10,.05,-20),(1,10,4,20)),("pc","amplitude","inverse_nu","correction"),
            model="corrected_shift_free_pc_omega_1")
    actual=v3.fit_corrected_shift_fixed_omega(L,y,label=f"C={C}",omega=1.)
    for key in ("inverse_nu","amplitude","correction","rss","aicc","bic","start_count",
                "converged_start_count","boundary_solution","parameter_count"):
        assert actual[key] == expected[key]
    assert .05 <= actual["inverse_nu"] <= 4
    assert -10 <= actual["amplitude"] <= 10
    assert -20 <= actual["correction"] <= 20
    assert 0 <= actual["pc"] <= 1


def test_joint_bootstrap_calls_actual_model_specs_and_maps_exponents(monkeypatch):
    called=[]
    def fit_models(*args,**kwargs):
        called.append(kwargs)
        return [_fake_fit("U1_independent",exponent_c1=-.1,exponent_c2=-.2),
                _fake_fit("U2_shared_exponent",exponent=-.15),
                _fake_fit("U3_shared_exponent_omega_1",exponent=-.16,omega=1.)]
    monkeypatch.setattr(v3,"fit_universality_models",fit_models)
    monkeypatch.setattr(v3,"fit_corrected_shift_fixed_omega",
        lambda *a,**k:_fake_fit("point_shift",pc=.5,inverse_nu=.75,amplitude=-.1,correction=2.,omega=1.))
    rows=v3.fit_joint_shift_statistics(_statistics(),sample=7)
    assert len(rows)==22
    assert len(called)==5
    for call in called:
        assert call["fixed_omegas"]==(1.,)
        assert call["include_models"]=={"U1_independent","U2_shared_exponent","U3_shared_exponent_omega_1"}
    group={row["model"]:row for row in rows if row["observable"]=="P_after"}
    assert group["U1_C1"]["exponent"]==.1
    assert group["U1_C2"]["exponent"]==.2
    assert group["U2_shared_exponent"]["exponent"]==.15
    assert group["U3_shared_exponent_omega_fixed_1"]["exponent"]==.16
    assert all(row["sample"]==7 and row["rss"]==1.25 and row["boundary_solution"] for row in rows)
    assert group["U1_C1"]["source_point_model"]=="U1_independent"


def test_joint_failed_fits_remain_visible_in_intervals(monkeypatch):
    def failed(*args,**kwargs):
        return [dict(model=name,converged=False,admissible=False,boundary_solution=False,
                     covariance_ok=False,failure="injected optimizer failure",
                     start_count=4,converged_start_count=0)
                for name in ("U1_independent","U2_shared_exponent","U3_shared_exponent_omega_1")]
    monkeypatch.setattr(v3,"fit_universality_models",failed)
    monkeypatch.setattr(v3,"fit_corrected_shift_fixed_omega",
        lambda *a,**k:_fake_fit("point_shift",pc=.5,inverse_nu=.75))
    rows=pd.DataFrame(v3.fit_joint_shift_statistics(_statistics(),sample=0))
    joint=rows.loc[rows.condition_label=="C1+C2"]
    assert len(joint)==20 and not joint.converged.any()
    assert joint.failure.str.contains("injected").all()
    assert joint.exponent.isna().all()
    assert v3.summarize_bootstrap(joint).empty


def test_primary_rng_advance_matches_production_draw_consumption(monkeypatch):
    events=_events(); widths=events.assign(delta_p=.1)
    captured=[]
    fake=dict(model="simple_power",converged=True,exponent=-.1,boundary_solution=False,amplitude=1.)
    monkeypatch.setattr(v3,"_selected_omega",lambda *a,**k:1.)
    monkeypatch.setattr(v3,"power_model_fits",lambda *a,**k:[fake,fake])
    monkeypatch.setattr(v3,"_quick_power_fit",lambda *a,**k:fake)
    monkeypatch.setattr(v3,"_bootstrap_ub_models",lambda *a,**k:[fake])
    monkeypatch.setattr(v3,"_bootstrap_joint_and_shift",
        lambda *a,**k:captured.append(k["rng"].integers(0,2**30,20)) or [])
    v3.bootstrap_primary(events,widths,pd.DataFrame(),pd.DataFrame(),samples=3,seed=37)
    rng=advance_primary_draws(events,widths,samples=3,seed=37)
    np.testing.assert_array_equal(captured[0],rng.integers(0,2**30,20))


def test_joint_draws_are_reproducible_and_keep_observable_pairing():
    events=_events(); before=events.copy(deep=True)
    left=draw_joint_statistics(events,samples=2,rng=np.random.default_rng(9))
    right=draw_joint_statistics(events,samples=2,rng=np.random.default_rng(9))
    for a,b in zip(left,right):
        for name in a:
            for x,y in zip(a[name],b[name]):
                np.testing.assert_array_equal(x[0],y[0])
                np.testing.assert_array_equal(x[1],y[1])
        for c in range(2):
            np.testing.assert_allclose(a["P_before"][c][1]-a["P_after"][c][1],.1,atol=1e-15)
    pd.testing.assert_frame_equal(events,before)


def test_correction_output_guard_precedes_input_read(tmp_path):
    output=tmp_path/"existing";output.mkdir()
    sentinel=output/"keep.txt";sentinel.write_text("unchanged")
    with pytest.raises(FileExistsError):
        run_correction(tmp_path/"missing-source",output,samples=1,workers=1)
    assert sentinel.read_text()=="unchanged"


def test_invalid_shift_condition_is_rejected():
    with pytest.raises(ValueError):
        v3.fit_corrected_shift_fixed_omega(np.arange(9)+8,np.ones(9),label="UNBOUNDED",omega=1.)


def test_finite_primary_only_preserves_default_finite_draws_and_rows(monkeypatch):
    events=_events(); widths=events.assign(delta_p=.1)
    calls=[]
    simple=dict(model="simple_power",converged=True,exponent=-.1,boundary_solution=False,amplitude=1.)
    corrected=dict(model="corrected_power_omega_1",converged=True,exponent=-.12,
                   boundary_solution=False,amplitude=1.,omega=1.,correction=2.)
    monkeypatch.setattr(v3,"_selected_omega",lambda *a,**k:1.)
    def fits(L,y,**kwargs):
        calls.append(np.asarray(y).copy())
        return [simple,corrected]
    monkeypatch.setattr(v3,"power_model_fits",fits)
    monkeypatch.setattr(v3,"_quick_power_fit",lambda *a,**k:simple)
    monkeypatch.setattr(v3,"_bootstrap_ub_models",lambda *a,**k:[simple])
    monkeypatch.setattr(v3,"_bootstrap_joint_and_shift",lambda *a,**k:[])
    full=v3.bootstrap_primary(events,widths,pd.DataFrame(),pd.DataFrame(),samples=3,seed=71)
    full_draws=[y.copy() for y in calls]
    calls.clear()
    partial=v3.bootstrap_primary(events,widths,pd.DataFrame(),pd.DataFrame(),samples=3,
                                 seed=71,finite_primary_only=True)
    expected=full.loc[full.condition_label!="UNBOUNDED"].reset_index(drop=True)
    pd.testing.assert_frame_equal(partial,expected[partial.columns])
    assert expected.drop(columns=partial.columns).isna().all().all()
    assert set(partial.condition_label)=={"C=1","C=2"}
    assert len(calls)==len(full_draws)
    for y,z in zip(calls,full_draws):np.testing.assert_array_equal(y,z)


def test_conflicting_bootstrap_only_modes_are_rejected():
    with pytest.raises(ValueError,match="mutually exclusive"):
        v3.bootstrap_primary(pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),
                             samples=1,seed=1,unbounded_only=True,finite_primary_only=True)
