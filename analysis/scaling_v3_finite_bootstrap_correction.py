"""Generate separate formal finite-C scaling-v3 bootstrap correction artifacts.

Reuses production bootstrap_primary and preserves the original finite-condition
run draws. Never simulates or overwrites a completed output directory.
"""
from __future__ import annotations
import argparse,hashlib,json,math,platform,time
from pathlib import Path
import numpy as np
import pandas as pd
import scipy
from analysis.correction_fitting import power_model_fits
from analysis.scaling_v3 import FINITE_OBSERVABLES,OBSERVABLES,_selected_omega,bootstrap_primary,summarize_bootstrap

DEFAULT_SOURCE_V2="app/out/scaling-v2-analysis"
DEFAULT_SOURCE_V3="app/out/scaling-v3-analysis"
DEFAULT_AUDIT="app/out/scaling-v3-s-after-audit"
DEFAULT_OUTPUT="app/out/scaling-v3-finite-bootstrap-corrected"
BOOTSTRAP_SAMPLES=500
BOOTSTRAP_SEED=20260720
L_MIN=8

def sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):digest.update(block)
    return digest.hexdigest()

def load_inputs(source_v2: Path,source_v3: Path) -> tuple[pd.DataFrame,...]:
    """Match production CSV parser and input row order exactly."""
    request=pd.read_csv(source_v2/"request_event_summary.csv")
    transition=pd.read_csv(source_v2/"transition_width_summary.csv")
    events=pd.read_csv(source_v2/"request_event_runs.csv")
    widths=pd.read_csv(source_v2/"transition_width_runs.csv")
    correction=pd.read_csv(source_v3/"finite_correction_fits.csv")
    scaling=pd.read_csv(source_v2/"finite_scaling_fits.csv")
    combined=request.merge(transition[["condition_index","delta_p_mean","delta_t_normalized_mean"]],on="condition_index",validate="one_to_one")
    combined["condition_label"]=combined.apply(lambda row:"UNBOUNDED" if row["budget_mode"]=="UNBOUNDED" else f"C={int(row['C'])}",axis=1)
    return events,widths,correction,combined,scaling

def verify_points(corrections: pd.DataFrame,combined: pd.DataFrame,scaling: pd.DataFrame) -> pd.DataFrame:
    """Refit the existing selected primary point estimators, with their original bounds."""
    rows=[]
    for label in ("C=1","C=2"):
        group=combined.loc[combined["condition_label"]==label].sort_values("L")
        for observable,(column,sign) in FINITE_OBSERVABLES.items():
            data=group.loc[(group["L"]>=L_MIN)&(group[column]>0)]
            omega=_selected_omega(corrections,label,observable)
            for fit in power_model_fits(data["L"],data[column],fixed_omegas=(omega,),include_free_omega=False):
                stored=corrections.loc[(corrections["condition_label"]==label)&(corrections["observable"]==observable)&(corrections["L_min"]==L_MIN)&(corrections["model"]==fit["model"])]
                if "theory_fixed" in stored:stored=stored.loc[~stored["theory_fixed"].fillna(False).astype(bool)]
                if len(stored)!=1:raise ValueError(f"Expected one primary point row: {label}/{observable}/{fit['model']}")
                point=stored.iloc[0]
                if not fit["converged"]:raise ValueError(f"Primary point failed: {label}/{observable}/{fit['model']}")
                for key in ("scaling_exponent","rss","aicc","bic"):
                    actual=sign*fit["exponent"] if key=="scaling_exponent" else fit[key]
                    expected=float(point[key])
                    if not math.isclose(float(actual),expected,rel_tol=2e-7,abs_tol=2e-7):
                        raise ValueError(f"Point estimator drift {label}/{observable}/{fit['model']}/{key}: {actual} != {expected}")
                corrected=fit["model"].startswith("corrected_")
                rows.append(dict(condition_label=label,observable=observable,source_column=column,model=fit["model"],
                    L_min=L_MIN,used_L=";".join(str(int(x)) for x in data["L"]),estimator="bounded_nonlinear_least_squares_original_scale",
                    point_exponent=float(point["scaling_exponent"]),recomputed_exponent=sign*float(fit["exponent"]),
                    point_rss=float(point["rss"]),recomputed_rss=fit["rss"],point_aicc=float(point["aicc"]),recomputed_aicc=fit["aicc"],
                    point_bic=float(point["bic"]),recomputed_bic=fit["bic"],selected_omega=omega if corrected else np.nan,
                    parameter_count=fit["parameter_count"],start_count=fit["start_count"],amplitude_lower=1e-12,amplitude_upper=1e6,
                    raw_exponent_lower=-5.,raw_exponent_upper=5.,correction_lower=-20. if corrected else np.nan,
                    correction_upper=20. if corrected else np.nan,point_boundary_solution=bool(fit["boundary_solution"]),
                    point_max_parameter_correlation=fit["max_parameter_correlation"]))
        for observable in ("delta_P_request","transition_delta_p"):
            old_name="delta_P_max" if observable=="delta_P_request" else observable
            stored=scaling.loc[(scaling["condition_label"]==label)&(scaling["observable"]==old_name)&(scaling["L_min"]==L_MIN)]
            if len(stored)!=1:raise ValueError(f"Expected one scaling-v2 OLS point row: {label}/{old_name}")
            point=stored.iloc[0];column,sign=OBSERVABLES[observable]
            data=group.loc[(group["L"]>=L_MIN)&(group[column]>0)]
            exponent=sign*float(np.polyfit(np.log(data["L"]),np.log(data[column]),1)[0])
            if not math.isclose(exponent,float(point["exponent"]),rel_tol=2e-12,abs_tol=2e-12):raise ValueError(f"OLS point drift: {label}/{observable}")
            rows.append(dict(condition_label=label,observable=observable,source_column=column,model="simple_power",L_min=L_MIN,
                used_L=point["used_L"],estimator="log_log_ordinary_least_squares",point_exponent=float(point["exponent"]),
                recomputed_exponent=exponent,point_rss=point["rss"],point_aicc=point["aicc"],point_bic=point["bic"],
                parameter_count=2,point_boundary_solution=False))
    return pd.DataFrame(rows)


def summarize_with_failures(samples: pd.DataFrame) -> pd.DataFrame:
    """Keep groups with no converged fits as undefined intervals, never as zero."""
    intervals=summarize_bootstrap(samples)
    additions=[]
    existing=set(map(tuple,intervals[["condition_label","observable","model","parameter"]].to_numpy())) if len(intervals) else set()
    for keys,group in samples.groupby(["condition_label","observable","model"],sort=True):
        converged=group["converged"].astype(bool)
        for parameter in ("exponent","limit"):
            if (*keys,parameter) in existing:
                continue
            additions.append(dict(condition_label=keys[0],observable=keys[1],model=keys[2],parameter=parameter,
                samples=0,requested_samples=int(group["sample"].nunique()),fit_failures=int((~converged).sum()),
                mean=np.nan,median=np.nan,ci95_low=np.nan,ci95_high=np.nan,
                boundary_frequency=float(group["boundary_solution"].mean())))
    if additions:intervals=pd.concat([intervals,pd.DataFrame(additions)],ignore_index=True)
    return intervals

def bootstrap_diagnostics(samples: pd.DataFrame) -> pd.DataFrame:
    """Expose requested/converged denominators and failure reasons for every model."""
    rows=[]
    for keys,group in samples.groupby(["condition_label","observable","model"],sort=True):
        converged=group["converged"].astype(bool)
        values=group.loc[converged,"exponent"].dropna()
        failed=group.loc[~converged,"failure"].fillna("unspecified").value_counts().to_dict()
        rows.append(dict(condition_label=keys[0],observable=keys[1],model=keys[2],
            requested_samples=int(group["sample"].nunique()),converged_fits=int(converged.sum()),
            failed_fits=int((~converged).sum()),failure_frequency=float((~converged).mean()),
            exponent_values=len(values),ci_defined=bool(len(values)),
            boundary_frequency_requested=float(group["boundary_solution"].mean()),
            boundary_frequency_converged=float(group.loc[converged,"boundary_solution"].mean()) if converged.any() else np.nan,
            failure_reasons=json.dumps(failed,sort_keys=True)))
    return pd.DataFrame(rows)

def validate_samples(samples: pd.DataFrame,requested_samples: int,seed: int) -> dict[str,object]:
    """Validate dispatch/sample IDs and point-estimator parameter bounds; retain failures."""
    if samples.empty or not set(samples["condition_label"]).issubset({"C=1","C=2"}):raise ValueError("Empty or non-finite-condition samples")
    if not (samples["bootstrap_seed"]==seed).all():raise ValueError("Bootstrap seed metadata mismatch")
    if not (samples["L_min"]==L_MIN).all():raise ValueError("Primary bootstrap L_min mismatch")
    groups=samples.groupby(["condition_label","observable","model"],sort=True)
    if groups.ngroups!=24:raise ValueError(f"Expected 24 finite primary model groups; received {groups.ngroups}")
    for key,group in groups:
        if group["sample"].duplicated().any() or set(group["sample"])!=set(range(requested_samples)):raise ValueError(f"Missing or duplicated sample IDs: {key}")
    nonlinear=samples.loc[samples["observable"].isin(FINITE_OBSERVABLES)&samples["converged"].astype(bool)]
    for column in ("exponent","amplitude"):
        if not np.isfinite(nonlinear[column]).all():raise ValueError(f"Non-finite converged {column}")
    if not nonlinear["amplitude"].between(1e-12,1e6).all():raise ValueError("Nonlinear amplitude outside point-estimator bounds")
    if not nonlinear["exponent"].between(-5.,5.).all():raise ValueError("Nonlinear exponent outside point-estimator bounds")
    corrected=nonlinear.loc[nonlinear["model"].str.startswith("corrected_")]
    if not corrected["correction"].between(-20.,20.).all():raise ValueError("Correction outside point-estimator bounds")
    if not np.isfinite(corrected["omega"]).all():raise ValueError("Fixed omega missing")
    return dict(sample_rows=len(samples),model_groups=groups.ngroups,requested_samples_per_group=requested_samples,
        converged_fit_rows=int(samples["converged"].astype(bool).sum()),failed_fit_rows=int((~samples["converged"].astype(bool)).sum()),bounds_verified=True)

def compare_simple_intervals(intervals: pd.DataFrame,previous_audit: pd.DataFrame) -> pd.DataFrame:
    """Check the fourteen simple intervals against the existing aligned S_after audit."""
    simple=intervals.loc[(intervals["model"]=="simple_power")&(intervals["parameter"]=="exponent")].copy()
    audit=previous_audit.copy();audit["observable"]=audit["observable"].replace({"delta_P_max":"delta_P_request"})
    comparison=simple.merge(audit[["condition_label","observable","aligned_ci95_low","aligned_ci95_high","aligned_bootstrap_mean","aligned_bootstrap_median"]],on=["condition_label","observable"],validate="one_to_one")
    if len(comparison)!=14:raise ValueError(f"Expected fourteen simple interval matches; received {len(comparison)}")
    for current,old in (("ci95_low","aligned_ci95_low"),("ci95_high","aligned_ci95_high"),("mean","aligned_bootstrap_mean"),("median","aligned_bootstrap_median")):
        comparison[f"{current}_difference"]=comparison[current]-comparison[old]
        if not np.allclose(comparison[current],comparison[old],rtol=2e-12,atol=2e-12):raise ValueError(f"Simple bootstrap differs from aligned audit: {current}")
    return comparison

def corrected_table(points: pd.DataFrame,intervals: pd.DataFrame) -> pd.DataFrame:
    exponent=intervals.loc[intervals["parameter"]=="exponent"].copy()
    table=points.merge(exponent.drop(columns="parameter"),on=["condition_label","observable","model"],validate="one_to_one")
    if len(table)!=len(points):raise ValueError("Point/bootstrap model keys do not match")
    table["ci_available"]=table["ci95_low"].notna()&table["ci95_high"].notna()
    table["point_in_ci"]=table["ci_available"]&table["point_exponent"].between(table["ci95_low"],table["ci95_high"])
    table["artifact_status"]="CORRECTED"
    table["uncertainty_scope"]="run bootstrap conditional on fixed L_min and selected model/omega"
    return table

def create_ci_figure(table: pd.DataFrame,destination: Path,*,samples: int,seed: int) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    observables=list(FINITE_OBSERVABLES)+["delta_P_request","transition_delta_p"]
    figure,axes=plt.subplots(2,4,figsize=(15,8))
    colors={"C=1":"tab:blue","C=2":"tab:orange"}
    for axis,observable in zip(axes.flat,observables):
        for row in table.loc[table["observable"]==observable].itertuples(index=False):
            x=0 if row.condition_label=="C=1" else 1;corrected=row.model!="simple_power";x+=.1 if corrected else -.1;color=colors[row.condition_label]
            if getattr(row,"ci_available",True):
                axis.vlines(x,row.ci95_low,row.ci95_high,color=color,linewidth=1.7)
                axis.hlines([row.ci95_low,row.ci95_high],x-.04,x+.04,color=color,linewidth=1.4)
            else:
                axis.text(x,.03,"CI unavailable",transform=axis.get_xaxis_transform(),color=color,rotation=90,fontsize=8)
            axis.plot(x,row.point_exponent,marker="s" if corrected else "o",color=color,markersize=6)
        axis.set_xticks([0,1],["C=1","C=2"]);axis.set_title(observable);axis.set_ylabel("Scaling exponent");axis.grid(axis="y",alpha=.2)
    axes.flat[-1].axis("off")
    axes.flat[-1].text(.02,.85,
        "Point estimator and run bootstrap matched\n\n"
        "o  Simple model\ns  Selected fixed-omega correction\n\n"
        "Bars: percentile 95% bootstrap intervals\n"
        f"L_min = 8; {samples} samples; seed = {seed}\n\n"
        "Model selection and finite-size uncertainty\nare not included in these intervals.",va="top",fontsize=11)
    figure.tight_layout();figure.savefig(destination,dpi=180);plt.close(figure)
    return destination

def run_correction(source_v2: str|Path=DEFAULT_SOURCE_V2,source_v3: str|Path=DEFAULT_SOURCE_V3,
    audit_source: str|Path=DEFAULT_AUDIT,output: str|Path=DEFAULT_OUTPUT,*,samples: int=BOOTSTRAP_SAMPLES,seed: int=BOOTSTRAP_SEED) -> list[Path]:
    v2,v3,audit,destination=map(Path,(source_v2,source_v3,audit_source,output))
    if destination.exists():raise FileExistsError(f"Refusing to overwrite existing output: {destination}")
    if samples<1:raise ValueError("samples must be positive")
    started=time.perf_counter()
    files=[v2/"request_event_runs.csv",v2/"transition_width_runs.csv",v2/"request_event_summary.csv",v2/"transition_width_summary.csv",
        v2/"finite_scaling_fits.csv",v3/"finite_correction_fits.csv",v3/"bootstrap_distributions.csv",v3/"bootstrap_intervals.csv",audit/"estimator_consistency_audit.csv"]
    before={str(path.resolve()):sha256(path) for path in files}
    events,widths,corrections,combined,scaling=load_inputs(v2,v3)
    points=verify_points(corrections,combined,scaling)
    distributions=bootstrap_primary(events,widths,corrections,combined,samples=samples,seed=seed,finite_primary_only=True)
    validation=validate_samples(distributions,samples,seed)
    destination.mkdir(parents=True,exist_ok=False)
    checkpoint=destination/"bootstrap_distributions.csv"
    distributions.to_csv(checkpoint,index=False,encoding="utf-8")
    diagnostics=bootstrap_diagnostics(distributions)
    diagnostic_path=destination/"bootstrap_diagnostics.csv"
    diagnostics.to_csv(diagnostic_path,index=False,encoding="utf-8")
    checkpoint_record=destination/"bootstrap_checkpoint.json"
    checkpoint_record.write_text(json.dumps(dict(status="BOOTSTRAP CHECKPOINT",validation=validation,
        bootstrap_seed=seed,input_hashes_before=before,distribution_sha256=sha256(checkpoint)),indent=2),encoding="utf-8")
    outputs=[checkpoint,diagnostic_path,checkpoint_record]
    intervals=summarize_with_failures(distributions)
    comparison=None
    if samples==BOOTSTRAP_SAMPLES and seed==BOOTSTRAP_SEED:comparison=compare_simple_intervals(intervals,pd.read_csv(audit/"estimator_consistency_audit.csv"))
    table=corrected_table(points,intervals)
    after={str(path.resolve()):sha256(path) for path in files}
    if before!=after:raise RuntimeError("Protected inputs changed during correction")
    for filename,frame in (("bootstrap_intervals.csv",intervals),("finite_primary_corrected_table.csv",table),("selected_point_estimator_verification.csv",points)):
        path=destination/filename;frame.to_csv(path,index=False,encoding="utf-8");outputs.append(path)
    if comparison is not None:
        path=destination/"simple_interval_audit_comparison.csv";comparison.to_csv(path,index=False,encoding="utf-8");outputs.append(path)
    outputs.append(create_ci_figure(table,destination/"finite_primary_bootstrap_ci.png",samples=samples,seed=seed))
    source_files=[Path(__file__),Path(__file__).with_name("scaling_v3.py"),Path(__file__).with_name("correction_fitting.py")]
    provenance=dict(status="CORRECTED",scope="finite-C primary scaling-v3 bootstrap only",bootstrap_samples=samples,bootstrap_seed=seed,
        resampling_unit="runs independently within each L",random_draw_order="original C=1 then C=2, metric/sample/L loops and input row order",
        ci_construction="2.5/97.5 percentiles of converged fits; boundary fits retained",selected_model_policy="original _selected_omega fixed before bootstrap; no re-selection",
        failed_fits_retained=True,input_hashes_before=before,input_hashes_after=after,inputs_unchanged=True,
        source_hashes={str(path.resolve()):sha256(path) for path in source_files},
        versions=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__),
        validation=validation,simple_audit_comparison_rows=len(comparison) if comparison is not None else None,
        undefined_ci_groups=table.loc[~table["ci_available"],["condition_label","observable","model","requested_samples","fit_failures"]].to_dict("records"),
        boundary_frequency_denominator="original summary uses all requested fits; diagnostics also reports converged-fit denominator",
        point_outside_interval_rows=table.loc[table["ci_available"]&~table["point_in_ci"],["condition_label","observable","model","point_exponent","ci95_low","ci95_high"]].to_dict("records"),
        elapsed_seconds=time.perf_counter()-started,preserved_historical_directory=str(v3.resolve()),
        legacy_simple_interval_status="SUPERSEDED by aligned simple intervals",
        limits=["No model-form, L_min-selection, omega-selection or finite-size-systematic uncertainty included.",
            "Same base seeds across L retained; independent-L bootstrap omits cross-size covariance.",
            "Request-level observables remain primary; no edge-level replacement.",
            "UNBOUNDED and joint/shift corrections are separate artifacts."])
    provenance["output_hashes"]={path.name:sha256(path) for path in outputs}
    path=destination/"correction_provenance.json";path.write_text(json.dumps(provenance,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8");outputs.append(path)
    readme=destination/"README.md"
    readme.write_text("# CORRECTED scaling-v3 finite primary bootstrap\n\n"
        f"Run bootstrap: {samples} samples, seed {seed}, L_min={L_MIN}.\n\n"
        "Use finite_primary_corrected_table.csv for point/95% interval pairs. Original scaling-v3-analysis products remain historical evidence. "
        "Simple primary intervals match scaling-v3-s-after-audit at the formal defaults. Fixed-omega correction intervals condition on original selected omega.\n\n"
        "No raw simulation, metadata, manifest, seed, preregistration, or historical output changed. UNBOUNDED and shared-exponent/shift corrections are separate.\n",encoding="utf-8")
    outputs.append(readme)
    print(f"finite bootstrap correction: rows={len(distributions)}, failures={validation['failed_fit_rows']}, output={destination}",flush=True)
    return outputs

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-v2",default=DEFAULT_SOURCE_V2);parser.add_argument("--source-v3",default=DEFAULT_SOURCE_V3)
    parser.add_argument("--audit-source",default=DEFAULT_AUDIT);parser.add_argument("--output",default=DEFAULT_OUTPUT)
    parser.add_argument("--bootstrap-samples",type=int,default=BOOTSTRAP_SAMPLES);parser.add_argument("--seed",type=int,default=BOOTSTRAP_SEED)
    args=parser.parse_args()
    run_correction(args.source_v2,args.source_v3,args.audit_source,args.output,samples=args.bootstrap_samples,seed=args.seed)

if __name__=="__main__":main()
