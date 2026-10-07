from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from analysis import scaling_v3_finite_bootstrap_correction as correction


def sample_frame(count: int = 2) -> pd.DataFrame:
    rows=[]
    for label in ("C=1","C=2"):
        for observable in list(correction.FINITE_OBSERVABLES)+["delta_P_request","transition_delta_p"]:
            models=["simple_power"]
            if observable in correction.FINITE_OBSERVABLES:models.append("corrected_power_omega_1")
            for model in models:
                for sample in range(count):
                    rows.append(dict(sample=sample,condition_label=label,observable=observable,model=model,
                        bootstrap_seed=17,L_min=8,used_L="8;16;32;64",converged=True,failure="",
                        exponent=.1+.02*sample,amplitude=.8,limit=0.,omega=1.,correction=.2,boundary_solution=False))
    return pd.DataFrame(rows)


def test_existing_destination_rejected_before_input_loading(tmp_path: Path,monkeypatch) -> None:
    destination=tmp_path/"existing";destination.mkdir()
    def forbidden(*args,**kwargs):
        raise AssertionError("An existing output must be rejected before reading inputs.")
    monkeypatch.setattr(correction,"load_inputs",forbidden)
    with pytest.raises(FileExistsError,match="Refusing to overwrite"):
        correction.run_correction(tmp_path/"absent",output=destination)


@pytest.mark.parametrize("column,value,message",[
    ("amplitude",-1.,"amplitude"),("exponent",5.01,"exponent"),("correction",20.01,"Correction"),
])
def test_point_estimator_bounds_are_enforced(column: str,value: float,message: str) -> None:
    frame=sample_frame()
    index=frame.loc[(frame.observable=="S_after")&(frame.model=="corrected_power_omega_1")].index[0]
    frame.loc[index,column]=value
    with pytest.raises(ValueError,match=message):
        correction.validate_samples(frame,2,17)


def test_failed_fit_rows_remain_counted_and_do_not_pollute_percentiles() -> None:
    frame=sample_frame()
    index=frame.loc[(frame.condition_label=="C=1")&(frame.observable=="S_after")&(frame.model=="simple_power")].index[0]
    frame.loc[index,["converged","exponent","amplitude"]]=[False,np.nan,np.nan]
    frame.loc[index,"failure"]="synthetic optimizer failure"
    validation=correction.validate_samples(frame,2,17)
    assert validation["failed_fit_rows"]==1 and len(frame)==48
    intervals=correction.summarize_bootstrap(frame)
    row=intervals.loc[(intervals.condition_label=="C=1")&(intervals.observable=="S_after")&(intervals.model=="simple_power")&(intervals.parameter=="exponent")].iloc[0]
    assert row["fit_failures"]==1 and row["requested_samples"]==2 and row["samples"]==1
    assert row["ci95_low"]==row["ci95_high"]==pytest.approx(.12)


def test_simple_comparison_renames_delta_P_max_and_detects_interval_drift() -> None:
    intervals=correction.summarize_bootstrap(sample_frame())
    simple=intervals.loc[(intervals.model=="simple_power")&(intervals.parameter=="exponent")]
    audit=simple[["condition_label","observable","ci95_low","ci95_high","mean","median"]].rename(columns={
        "ci95_low":"aligned_ci95_low","ci95_high":"aligned_ci95_high","mean":"aligned_bootstrap_mean","median":"aligned_bootstrap_median"})
    audit["observable"]=audit.observable.replace({"delta_P_request":"delta_P_max"})
    comparison=correction.compare_simple_intervals(intervals,audit)
    assert len(comparison)==14
    assert np.allclose(comparison["ci95_low_difference"],0)
    audit.loc[audit.index[0],"aligned_ci95_high"]+=.001
    with pytest.raises(ValueError,match="differs from aligned audit"):
        correction.compare_simple_intervals(intervals,audit)


def test_point_outside_interval_is_reported_without_changing_interval() -> None:
    intervals=correction.summarize_bootstrap(sample_frame())
    points=sample_frame().drop_duplicates(["condition_label","observable","model"])[["condition_label","observable","model"]].copy()
    points["point_exponent"]=.5
    original=intervals.copy(deep=True)
    table=correction.corrected_table(points,intervals)
    assert not table["point_in_ci"].any()
    assert (table["ci95_high"]<.5).all()
    pd.testing.assert_frame_equal(intervals,original)


@pytest.mark.parametrize("abort_after_checkpoint",[False,True])
def test_production_dispatch_preserves_inputs_and_new_output_provenance(tmp_path: Path,monkeypatch,abort_after_checkpoint: bool) -> None:
    v2=tmp_path/"v2";v3=tmp_path/"v3";audit=tmp_path/"audit"
    for directory in (v2,v3,audit):directory.mkdir()
    for name in ("request_event_runs.csv","transition_width_runs.csv","request_event_summary.csv","transition_width_summary.csv","finite_scaling_fits.csv"):
        (v2/name).write_text("protected v2 input\n")
    for name in ("finite_correction_fits.csv","bootstrap_distributions.csv","bootstrap_intervals.csv"):
        (v3/name).write_text("protected historical input\n")
    (audit/"estimator_consistency_audit.csv").write_text("protected aligned audit\n")
    events=pd.DataFrame({"sentinel":[3,1,2]});widths=pd.DataFrame({"sentinel":[7,5,6]})
    corrections=pd.DataFrame({"fixed":[1]});combined=pd.DataFrame({"condition_label":["C=1"]});scaling=pd.DataFrame({"ols":[2]})
    monkeypatch.setattr(correction,"load_inputs",lambda a,b:(events,widths,corrections,combined,scaling))
    points=sample_frame().drop_duplicates(["condition_label","observable","model"])[["condition_label","observable","model"]].copy()
    points["point_exponent"]=.11
    monkeypatch.setattr(correction,"verify_points",lambda *args:points)
    def production(e,w,c,b,*,samples,seed,finite_primary_only):
        assert e is events and w is widths and c is corrections and b is combined
        assert e.sentinel.tolist()==[3,1,2] and w.sentinel.tolist()==[7,5,6]
        assert samples==2 and seed==17 and finite_primary_only is True
        return sample_frame()
    monkeypatch.setattr(correction,"bootstrap_primary",production)
    def figure(table,path,*,samples,seed):
        path.write_bytes(b"synthetic test figure")
        return path
    monkeypatch.setattr(correction,"create_ci_figure",figure)
    output=tmp_path/"new"
    if abort_after_checkpoint:
        def abort(*args):raise ValueError("synthetic table failure")
        monkeypatch.setattr(correction,"corrected_table",abort)
        with pytest.raises(ValueError,match="synthetic table failure"):
            correction.run_correction(v2,v3,audit,output,samples=2,seed=17)
        assert len(pd.read_csv(output/"bootstrap_distributions.csv"))==48
        checkpoint=json.loads((output/"bootstrap_checkpoint.json").read_text())
        assert checkpoint["status"]=="BOOTSTRAP CHECKPOINT"
        assert (output/"bootstrap_diagnostics.csv").is_file()
        assert not (output/"correction_provenance.json").exists()
        return
    paths=correction.run_correction(v2,v3,audit,output,samples=2,seed=17)
    record=json.loads((output/"correction_provenance.json").read_text())
    assert record["inputs_unchanged"] is True
    assert record["input_hashes_before"]==record["input_hashes_after"]
    assert record["validation"]["sample_rows"]==48
    assert record["validation"]["model_groups"]==24
    assert all(path.exists() for path in paths)
    assert not (output/"simple_interval_audit_comparison.csv").exists()
    assert (v3/"bootstrap_intervals.csv").read_text()=="protected historical input\n"


def test_all_failed_group_retains_undefined_CI_and_requested_denominator() -> None:
    frame=sample_frame()
    selection=(frame.condition_label=="C=1")&(frame.observable=="S_before")&(frame.model=="corrected_power_omega_1")
    frame.loc[selection,["converged","exponent","amplitude"]]=[False,np.nan,np.nan]
    frame.loc[selection,"failure"]="all starts invalid"
    intervals=correction.summarize_with_failures(frame)
    missing=intervals.loc[(intervals.condition_label=="C=1")&(intervals.observable=="S_before")&(intervals.model=="corrected_power_omega_1")&(intervals.parameter=="exponent")].iloc[0]
    assert missing["samples"]==0 and missing["requested_samples"]==2 and missing["fit_failures"]==2
    assert pd.isna(missing["ci95_low"]) and pd.isna(missing["ci95_high"])
    diagnostics=correction.bootstrap_diagnostics(frame)
    row=diagnostics.loc[(diagnostics.condition_label=="C=1")&(diagnostics.observable=="S_before")&(diagnostics.model=="corrected_power_omega_1")].iloc[0]
    assert row["ci_defined"]==False and row["failed_fits"]==2 and row["failure_frequency"]==1.
    assert pd.isna(row["boundary_frequency_converged"])
    points=frame.drop_duplicates(["condition_label","observable","model"])[["condition_label","observable","model"]].copy()
    points["point_exponent"]=.11
    table=correction.corrected_table(points,intervals)
    assert len(table)==24 and table["ci_available"].sum()==23
