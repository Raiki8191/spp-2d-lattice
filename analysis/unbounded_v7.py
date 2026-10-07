"""UNBOUNDED v7 integration and preregistered L=384 prediction evaluation."""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "spp-matplotlib-cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.artifact_status import corrected_unbounded_intervals

from analysis.io import read_manifest
from analysis.unbounded_model_comparison import (
    bootstrap_models, fit_models, leave_one_size_out, predict, prediction_table,
    summarize_bootstrap,
)
from analysis.unbounded_v4 import load_stage_runs, stage_quality, stop_audit_report
from analysis.unbounded_v5 import MODEL_OBSERVABLES, lmin_fits, metric_summary, summarize_loo
from analysis.unbounded_v6 import load_v6_run_metrics, score_preregistered, seed_audit


L384_ROOT = Path("app/out/unbounded-l384")
L384_MANIFESTS = [L384_ROOT / "benchmark/manifest.csv", L384_ROOT / "pilot/manifest.csv"]
PREREGISTRATION = Path("analysis/reference/unbounded_l384_preregistered_predictions.csv")
OUTPUT_ROOT = Path("app/out/unbounded-v7")
TARGETS = (512, 768, 1024, 1536)


def load_v7_run_metrics() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    events, widths, peaks = load_v6_run_metrics()
    _, events384, widths384 = load_stage_runs(L384_MANIFESTS)
    events = pd.concat([events, events384], ignore_index=True, sort=False)
    widths = pd.concat([widths, widths384], ignore_index=True, sort=False)
    peak_rows, offset = [], 0
    for manifest_path in L384_MANIFESTS:
        manifest = read_manifest(manifest_path)
        condition = manifest.iloc[0]
        data = pd.read_csv(condition.result_path, usecols=["run", "mean_cluster_size"])
        for run, value in data.groupby("run").mean_cluster_size.max().items():
            peak_rows.append({"L": 384, "run": offset + int(run), "S_peak": float(value)})
        offset += int(condition.runs)
    peaks = pd.concat([peaks, pd.DataFrame(peak_rows)], ignore_index=True)
    return events, widths, peaks


def descriptive_observations(
    events: pd.DataFrame, widths: pd.DataFrame, peaks: pd.DataFrame, *, L: int,
    samples: int = 5000, seed: int = 20260720,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    definitions = {
        "maximum_request_jump": (events.loc[events.L == L, "delta_P_request"], "mean"),
        "transition_delta_p": (widths.loc[widths.L == L, "delta_p"], "mean"),
        "transition_delta_t_normalized": (widths.loc[widths.L == L, "delta_t_normalized"], "mean"),
        "request_event_p_after": (events.loc[events.L == L, "p_after"], "mean"),
        "request_event_p_dispersion": (events.loc[events.L == L, "p_mid"], "std"),
        "S_peak": (peaks.loc[peaks.L == L, "S_peak"], "mean"),
    }
    rows = []
    for observable, (series, aggregation) in definitions.items():
        values = series.dropna().to_numpy(float)
        draws = np.empty(samples)
        for index in range(samples):
            draw = values[rng.integers(0, len(values), len(values))]
            draws[index] = np.mean(draw) if aggregation == "mean" else np.std(draw, ddof=1)
        estimate = np.mean(values) if aggregation == "mean" else np.std(values, ddof=1)
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1
        rows.append({
            "observable": observable, "L": L, "run_count": len(values),
            "mean_or_estimate": float(estimate), "sample_std": float(np.std(values, ddof=1)),
            "sem": float(np.std(values, ddof=1) / np.sqrt(len(values))) if aggregation == "mean" else float(np.std(draws, ddof=1)),
            "median": float(np.median(values)), "q1": float(q1), "q3": float(q3),
            "minimum": float(np.min(values)), "maximum": float(np.max(values)),
            "tukey_outlier_count": int(np.sum((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr))),
            "bootstrap_ci95_low": float(np.percentile(draws, 2.5)),
            "bootstrap_ci95_high": float(np.percentile(draws, 97.5)),
        })
    return pd.DataFrame(rows)


def compare_l320_l384(events: pd.DataFrame, *, samples: int = 20_000,
                      seed: int = 20260720) -> pd.DataFrame:
    """Independent-sample bootstrap comparison without mutating run data."""
    rng = np.random.default_rng(seed)
    left = events.loc[events.L == 320, "delta_P_request"].dropna().to_numpy(float)
    right = events.loc[events.L == 384, "delta_P_request"].dropna().to_numpy(float)
    differences = np.empty(samples)
    for index in range(samples):
        differences[index] = (
            np.mean(right[rng.integers(0, len(right), len(right))])
            - np.mean(left[rng.integers(0, len(left), len(left))]))
    pooled = math.sqrt(((len(left)-1)*np.var(left,ddof=1)+(len(right)-1)*np.var(right,ddof=1))
                       / (len(left)+len(right)-2))
    difference = float(np.mean(right)-np.mean(left))
    return pd.DataFrame([{
        "L_left": 320, "L_right": 384, "mean_left": float(np.mean(left)),
        "sem_left": float(np.std(left,ddof=1)/np.sqrt(len(left))),
        "mean_right": float(np.mean(right)), "sem_right": float(np.std(right,ddof=1)/np.sqrt(len(right))),
        "mean_difference_right_minus_left": difference,
        "combined_sem": float(np.sqrt(np.var(left,ddof=1)/len(left)+np.var(right,ddof=1)/len(right))),
        "standardized_difference": float(difference/np.sqrt(np.var(left,ddof=1)/len(left)+np.var(right,ddof=1)/len(right))),
        "cohen_d": float(difference/pooled),
        "bootstrap_difference_ci95_low": float(np.percentile(differences,2.5)),
        "bootstrap_difference_ci95_high": float(np.percentile(differences,97.5)),
        "bootstrap_probability_L384_lower": float(np.mean(differences < 0)),
    }])


def score_l384_preregistration(predictions: pd.DataFrame,
                               observations: pd.DataFrame) -> pd.DataFrame:
    scored = score_preregistered(predictions, observations)
    predictive_sigma = ((scored.prediction_interval95_high - scored.prediction_interval95_low)
                        / (2 * 1.96)).clip(lower=np.finfo(float).eps)
    scored["predictive_log_density"] = (-.5*np.log(2*np.pi*predictive_sigma**2)
                                         -.5*(scored.signed_error/predictive_sigma)**2)
    return scored


def sequential_prediction_performance(scored384: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    prior256 = pd.read_csv("app/out/unbounded-v5/l256_prior_prediction_check.csv")
    for row in prior256.itertuples():
        rows.append({"target_L":256,"model":row.model,"observed":row.L256_observed_mean,
                     "prediction":row.v4_prior_prediction,"error":row.L256_observed_mean-row.v4_prior_prediction,
                     "prediction_interval_covered":bool(row.observation_inside_v4_interval),
                     "status":"fixed v4 prediction"})
    scored320 = pd.read_csv("app/out/unbounded-v6/l320_preregistered_prediction_scores.csv")
    for row in scored320.loc[scored320.observable=="maximum_request_jump"].itertuples():
        rows.append({"target_L":320,"model":row.model,"observed":row.observed,
                     "prediction":row.prediction,"error":row.signed_error,
                     "prediction_interval_covered":bool(row.observed_inside_prediction_interval),
                     "status":"preregistered before L=320"})
    for row in scored384.loc[scored384.observable=="maximum_request_jump"].itertuples():
        rows.append({"target_L":384,"model":row.model,"observed":row.observed,
                     "prediction":row.prediction,"error":row.signed_error,
                     "prediction_interval_covered":bool(row.observed_inside_prediction_interval),
                     "status":"preregistered before L=384"})
    detail = pd.DataFrame(rows)
    detail["absolute_error"] = detail.error.abs()
    detail["squared_error"] = detail.error**2
    detail["rank_at_size"] = detail.groupby("target_L").absolute_error.rank(method="min")
    summary = detail.groupby("model",sort=True).agg(
        sequential_mae=("absolute_error","mean"), sequential_rmse=("squared_error",lambda x: math.sqrt(x.mean())),
        prediction_interval_coverage=("prediction_interval_covered","mean"),
        cumulative_squared_error=("squared_error","sum"), mean_rank=("rank_at_size","mean"),
    ).reset_index()
    summary["mae_rank"] = summary.sequential_mae.rank(method="min")
    summary["rmse_rank"] = summary.sequential_rmse.rank(method="min")
    return detail, summary


def local_effective_exponents(summary: pd.DataFrame) -> pd.DataFrame:
    data = summary.loc[summary.observable=="maximum_request_jump"].sort_values("L")
    rows=[]
    for left,right in zip(data.itertuples(),data.iloc[1:].itertuples()):
        ratio=right.value/left.value
        rows.append({"L_left":int(left.L),"L_right":int(right.L),"L_mid":math.sqrt(left.L*right.L),
                     "power_effective_exponent":-math.log(ratio)/math.log(right.L/left.L),
                     "log_effective_exponent":-math.log(ratio)/math.log(math.log(right.L)/math.log(left.L))})
    return pd.DataFrame(rows)


def parametric_identification(summary: pd.DataFrame, fits: pd.DataFrame, *, samples: int = 500,
                              seed: int = 20260720) -> pd.DataFrame:
    data=summary.loc[summary.observable=="maximum_request_jump"].sort_values("L")
    rng=np.random.default_rng(seed); rows=[]
    for true_model in ("zero_power","zero_log"):
        truth=fits.loc[(fits.observable=="maximum_request_jump")&(fits.model==true_model)].iloc[0].to_dict()
        means=np.array([predict(truth,L) for L in data.L]); scales=data.sample_sem.to_numpy(float)
        selected=[]
        for sample in range(samples):
            synthetic=np.maximum(rng.normal(means,scales),np.finfo(float).eps)
            refit=fit_models(data.L,synthetic,observable="maximum_request_jump")
            zero=refit.loc[refit.model.isin(["zero_power","zero_log"])]
            choice=zero.sort_values(["aicc","model"]).iloc[0].model
            selected.append(choice)
        for model in ("zero_power","zero_log"):
            rows.append({"true_model":true_model,"selected_model":model,"samples":samples,
                         "selection_count":selected.count(model),"selection_rate":selected.count(model)/samples})
    return pd.DataFrame(rows)


def model_history(fits: pd.DataFrame, loo: pd.DataFrame, intervals: pd.DataFrame) -> pd.DataFrame:
    roots={"v4":Path("app/out/unbounded-v4/main50"),"v5":Path("app/out/unbounded-v5"),"v6":Path("app/out/unbounded-v6")}
    tables=[]
    for version,root in roots.items():
        f=pd.read_csv(root/"unbounded_model_fits.csv")
        ls=(pd.read_csv(root/"unbounded_loo_summary.csv") if (root/"unbounded_loo_summary.csv").is_file()
            else summarize_loo(pd.read_csv(root/"unbounded_leave_one_size_out.csv")))
        ci=pd.read_csv(corrected_unbounded_intervals(version))
        tables.append(_history_rows(version,f,ls,ci))
    tables.append(_history_rows("v7",fits,loo,intervals))
    result=pd.concat(tables,ignore_index=True)
    result["aicc_rank"]=result.groupby(["version","observable"]).aicc.rank(method="min")
    result["bic_rank"]=result.groupby(["version","observable"]).bic.rank(method="min")
    return result


def _history_rows(version,fits,loo,intervals):
    result=fits.merge(loo[["observable","model","loo_mae","loo_rmse"]],on=["observable","model"],how="left")
    ci=intervals.loc[intervals.parameter=="limit",["observable","model","ci95_low","ci95_high","boundary_frequency","fit_failure_frequency"]]
    result=result.merge(ci,on=["observable","model"],how="left").copy(); result.insert(0,"version",version)
    return result


def seed_audit_v7() -> pd.DataFrame:
    prior=seed_audit(); frames=[]
    for stage in ("benchmark","pilot"):
        frame=pd.read_csv(L384_ROOT/stage/"run_metadata.csv",usecols=["run_seed"]); frame["stage"]=stage; frames.append(frame)
    l384=pd.concat(frames,ignore_index=True)
    old=[]
    for root,stages in ((Path("app/out/unbounded-l192"),("benchmark","pilot","main")),
                        (Path("app/out/unbounded-l256"),("benchmark","pilot")),
                        (Path("app/out/unbounded-l320"),("benchmark","pilot"))):
        for stage in stages: old.extend(pd.read_csv(root/stage/"run_metadata.csv").run_seed.astype(int))
    extra=pd.DataFrame([{"scope":"L=384","run_count":len(l384),"unique_run_seed_count":l384.run_seed.nunique(),
                         "duplicate_count":int(l384.run_seed.duplicated().sum()),"overlap_count":len(set(old)&set(l384.run_seed))},
                        {"scope":"L=384 benchmark vs pilot","run_count":np.nan,"unique_run_seed_count":np.nan,
                         "duplicate_count":np.nan,"overlap_count":len(set(frames[0].run_seed)&set(frames[1].run_seed))}])
    return pd.concat([prior,extra],ignore_index=True)


def add_prediction_intervals(predictions: pd.DataFrame, fits: pd.DataFrame) -> pd.DataFrame:
    result=predictions.merge(fits[["observable","model","residual_rms"]],on=["observable","model"],how="left")
    half=(result.prediction_ci95_high-result.prediction_ci95_low)/2
    predictive=1.96*np.sqrt((half/1.96)**2+result.residual_rms**2)
    result["prediction_interval95_low"]=result.prediction-predictive
    result["prediction_interval95_high"]=result.prediction+predictive
    result["required_sem_to_separate_models"]=result.groupby(["observable","target_L"]).prediction.transform(lambda x:x.max()-x.min())/2
    return result


def experiment_options(metadata: pd.DataFrame, observation: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    seconds=float(metadata.elapsed_milliseconds.median()/1000); bytes_per=float(metadata.results_bytes.mean()); sd=float(observation.loc[observation.observable=="maximum_request_jump","sample_std"].iloc[0])
    rows=[]
    for option,L,runs in (("A L384 total50",384,50),("B L384 total100",384,100),("C L512 benchmark",512,3),("C L512 pilot",512,20),("D L320 total50",320,50),("E stop and write thesis",384,20)):
        scale=(L/384)**4; no_run=option.startswith("E")
        target=predictions.loc[(predictions.observable=="maximum_request_jump")&(predictions.target_L==max(L,512))]
        model_range=float(target.prediction.max()-target.prediction.min()) if not target.empty else np.nan
        required_sem=model_range/2 if np.isfinite(model_range) else np.nan
        rows.append({"option":option,"L":L,"runs":runs,"estimated_total_seconds":0 if no_run else seconds*scale*runs,
                     "estimated_results_bytes":0 if no_run else bytes_per*scale*runs,"estimated_sem":sd/math.sqrt(runs) if L==384 else np.nan,
                     "model_prediction_range":model_range,"required_sem_to_resolve_range":required_sem,
                     "estimated_runs_for_required_sem":math.ceil((sd/required_sem)**2) if L==384 and required_sem>0 else np.nan,
                     "information_value":"new curvature leverage" if L>384 else "same-size precision" if not no_run else "writing and synthesis",
                     "automatic_execution":"not authorized","warning":"empirical extrapolation, not an observation"})
    return pd.DataFrame(rows)


def thesis_tables(summary: pd.DataFrame, history: pd.DataFrame, events: pd.DataFrame,
                  widths: pd.DataFrame, peaks: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    rows=[]
    for L in sorted(events.L.unique()):
        event=events.loc[events.L==L]; width=widths.loc[widths.L==L]; peak=peaks.loc[peaks.L==L]
        values=event.delta_P_request.to_numpy(float); sem=np.std(values,ddof=1)/math.sqrt(len(values))
        # Use the same fixed bootstrap stream as the primary jump description so
        # the lightweight thesis table and the detailed v7 table agree exactly.
        rng=np.random.default_rng(20260720)
        bootstrap_means=rng.choice(values,size=(5000,len(values)),replace=True).mean(axis=1)
        rows.append({"L":int(L),"runs":len(values),"maximum_request_jump_mean":np.mean(values),"maximum_request_jump_sd":np.std(values,ddof=1),"maximum_request_jump_sem":sem,
                     "maximum_request_jump_bootstrap_ci95_low":np.percentile(bootstrap_means,2.5),"maximum_request_jump_bootstrap_ci95_high":np.percentile(bootstrap_means,97.5),
                     "transition_delta_p":width.delta_p.mean(),"transition_delta_t_normalized":width.delta_t_normalized.mean(),"request_event_p_after":event.p_after.mean(),
                     "std_p_mid":event.p_mid.std(ddof=1),"S_peak":peak.S_peak.mean(),"analysis_version":"v7",
                     "source":"scaling-v2/v4/v5/v6/v7 integrated manifests"})
    summary_table=pd.DataFrame(rows)
    model_table=history.loc[history.observable=="maximum_request_jump",["version","L_max","model","aicc","bic","loo_mae","loo_rmse","limit","ci95_low","ci95_high","max_parameter_correlation","boundary_solution"]].copy()
    model_table["aicc_rank"]=model_table.groupby("version").aicc.rank(method="min").astype(int)
    model_table["conclusion_classification"]=np.where(model_table.version=="v7","v7 classification in UNBOUNDED_V7_RESULTS.md","historical fit")
    return summary_table,model_table


def run_analysis(output: str|Path=OUTPUT_ROOT, *, bootstrap_samples:int=500,
                 identification_samples:int=500, seed:int=20260720,
                 docs_tables: str|Path|None=None) -> list[Path]:
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    events,widths,peaks=load_v7_run_metrics(); summary=metric_summary(events,widths,peaks)
    sources={"maximum_request_jump":events,"request_event_p_dispersion":events,"request_event_p_after":events,
             "transition_delta_p":widths,"transition_delta_t_normalized":widths}
    fit_parts=[]; loo_parts=[]; boot_parts=[]
    for index,(observable,(column,aggregation)) in enumerate(MODEL_OBSERVABLES.items()):
        subset=summary.loc[summary.observable==observable]; fit_parts.append(fit_models(subset.L,subset.value,observable=observable)); loo_parts.append(leave_one_size_out(subset,"value",observable)); boot_parts.append(bootstrap_models(sources[observable],value_column=column,aggregation=aggregation,observable=observable,samples=bootstrap_samples,seed=seed+index))
    fits=pd.concat(fit_parts,ignore_index=True); loo_raw=pd.concat(loo_parts,ignore_index=True); loo=summarize_loo(loo_raw); bootstrap=pd.concat(boot_parts,ignore_index=True); intervals=summarize_bootstrap(bootstrap)
    predictions=add_prediction_intervals(prediction_table(fits,bootstrap,targets=TARGETS),fits)
    observations=descriptive_observations(events,widths,peaks,L=384,samples=5000,seed=seed)
    prereg=pd.read_csv(PREREGISTRATION); scored=score_l384_preregistration(prereg,observations)
    sequential_detail,sequential_summary=sequential_prediction_performance(scored)
    comparison=compare_l320_l384(events,seed=seed); local=local_effective_exponents(summary)
    identification=parametric_identification(summary,fits,samples=identification_samples,seed=seed)
    history=model_history(fits,loo,intervals); quality=stage_quality(L384_MANIFESTS)
    audit=stop_audit_report(stage_root=L384_ROOT,benchmark_name="benchmark/manifest.csv",audit_name="stop-audit/manifest.csv")
    metadata=pd.concat([pd.read_csv(L384_ROOT/"benchmark/run_metadata.csv"),pd.read_csv(L384_ROOT/"pilot/run_metadata.csv")],ignore_index=True)
    options=experiment_options(metadata,observations,predictions); seeds=seed_audit_v7()
    tables={"unbounded_size_summary.csv":summary,"unbounded_model_fits.csv":fits,"unbounded_leave_one_size_out.csv":loo_raw,"unbounded_loo_summary.csv":loo,
            "unbounded_bootstrap_samples.csv":bootstrap,"unbounded_bootstrap_intervals.csv":intervals,"unbounded_predictions.csv":predictions,"unbounded_lmin_dependence.csv":lmin_fits(summary),
            "l384_observations.csv":observations,"l320_l384_comparison.csv":comparison,"l384_preregistered_prediction_scores.csv":scored,
            "sequential_prediction_detail.csv":sequential_detail,"sequential_prediction_summary.csv":sequential_summary,"local_effective_exponents.csv":local,
            "parametric_model_identification.csv":identification,"v4_v5_v6_v7_model_history.csv":history,"stage_data_quality.csv":quality,"stop_audit.csv":audit,"seed_audit.csv":seeds,"experiment_options.csv":options}
    captions=create_figures(summary,fits,loo_raw,bootstrap,tables["unbounded_lmin_dependence.csv"],predictions,scored,sequential_detail,history,local,identification,options,output/"figures")
    tables["figure_captions.csv"]=captions
    for name,frame in tables.items(): frame.to_csv(output/name,index=False)
    if docs_tables is not None:
        docs=Path(docs_tables); docs.mkdir(parents=True,exist_ok=True); first,second=thesis_tables(summary,history,events,widths,peaks); first.to_csv(docs/"UNBOUNDED_SUMMARY.csv",index=False); second.to_csv(docs/"UNBOUNDED_MODEL_HISTORY.csv",index=False)
    print(f"unbounded-v7: L384_runs={int(observations.run_count.max())} bootstrap_samples={bootstrap_samples} identification_samples={identification_samples} outputs={len(tables)+len(captions)}")
    return [output/name for name in tables]+[output/"figures"/name for name in captions.filename]


def create_figures(summary,fits,loo,bootstrap,lmin,predictions,scored,sequential,history,local,identification,options,directory):
    directory.mkdir(parents=True,exist_ok=True); rows=[]
    def save(fig,name,caption): fig.tight_layout(); fig.savefig(directory/name,dpi=180); plt.close(fig); rows.append({"filename":name,"caption_candidate":caption})
    labels={"maximum_request_jump":"Maximum request jump","transition_delta_p":r"Transition width $\Delta p$","transition_delta_t_normalized":r"Normalized request width $\Delta t/N^2$"}
    for observable in labels:
        data=summary.loc[summary.observable==observable].sort_values("L"); grid=np.geomspace(8,1536,300); fig,ax=plt.subplots(figsize=(7.4,5.1)); ax.errorbar(data.L,data.value,yerr=data.sample_sem,fmt="o",label="observed mean ± SEM")
        for row in fits.loc[fits.observable==observable].to_dict("records"): ax.plot(grid,[predict(row,L) for L in grid],label=row["model"].replace("_","-"))
        ax.axvline(384,color="black",ls=":",label="largest observed L"); ax.set(xscale="log",xlabel="Linear size L",ylabel=labels[observable],title=f"UNBOUNDED v7: {labels[observable]}"); ax.legend(fontsize=7); save(fig,f"{observable}_size_dependence.png",f"{labels[observable]}のサイズ依存性。点はrun平均±SEM、線はL≤384の4モデルfit。")
    jump=scored.loc[scored.observable=="maximum_request_jump"].reset_index(drop=True); x=np.arange(len(jump)); fig,ax=plt.subplots(figsize=(8,5)); err=np.vstack((jump.prediction-jump.prediction_interval95_low,jump.prediction_interval95_high-jump.prediction)); ax.errorbar(x,jump.prediction,yerr=err,fmt="o",capsize=4,label="preregistered prediction ±95% PI"); ax.axhspan(jump.bootstrap_ci95_low.iloc[0],jump.bootstrap_ci95_high.iloc[0],alpha=.2,color="green",label="observed bootstrap 95% CI"); ax.axhline(jump.observed.iloc[0],color="green"); ax.set_xticks(x,jump.model.str.replace("_","-"),rotation=20); ax.set(ylabel="Maximum request jump",title="L=384 preregistered predictions vs observation"); ax.legend(fontsize=8); save(fig,"l384_preregistered_prediction_intervals.png","L=384最大request jumpの事前予測区間と観測bootstrap区間。")
    fig,ax=plt.subplots(figsize=(8,5));
    for model,g in sequential.groupby("model"): ax.plot(g.target_L,g.absolute_error,marker="o",label=model.replace("_","-"))
    ax.set(xlabel="Target size L",ylabel="Absolute out-of-sample error",title="Sequential prediction errors"); ax.legend(); save(fig,"sequential_prediction_errors.png","L=256,320,384への固定予測の絶対誤差。")
    fig,ax=plt.subplots(figsize=(8,5)); sub=history.loc[history.observable=="maximum_request_jump"]
    for model,g in sub.groupby("model"): ax.plot(g.version,g.aicc_rank,marker="o",label=model.replace("_","-"))
    ax.invert_yaxis(); ax.set(ylabel="AICc rank (1=best)",title="Model-rank migration v4–v7"); ax.legend(); save(fig,"model_rank_migration.png","最大request jumpのAICc順位が追加サイズごとにどう変化したか。")
    data=summary.loc[summary.observable=="maximum_request_jump"].sort_values("L"); grid=np.geomspace(8,1536,300)
    for names,file,title in [(("zero_power","zero_log"),"zero_power_vs_zero_log.png","Zero-asymptote models"),(("zero_power","finite_power"),"zero_vs_finite_power.png","Power models"),(("zero_log","finite_log"),"zero_vs_finite_log.png","Log models")]:
        fig,ax=plt.subplots(figsize=(7.4,5)); ax.errorbar(data.L,data.value,yerr=data.sample_sem,fmt="o",label="observed")
        for row in fits.loc[(fits.observable=="maximum_request_jump")&fits.model.isin(names)].to_dict("records"): ax.plot(grid,[predict(row,L) for L in grid],label=row["model"].replace("_","-"))
        ax.set(xscale="log",xlabel="L",ylabel="Maximum request jump",title=title); ax.legend(); save(fig,file,f"{title}のL≤384 fit直接比較。")
    fig,ax=plt.subplots(figsize=(7.4,5)); scale=data.sample_sem.replace(0,np.nan).to_numpy(float)
    for row in fits.loc[fits.observable=="maximum_request_jump"].to_dict("records"): ax.plot(data.L,(data.value-[predict(row,L) for L in data.L])/scale,marker="o",label=row["model"].replace("_","-"))
    ax.axhline(0,color="black"); ax.set(xlabel="L",ylabel="Residual / SEM",title="Standardized residuals"); ax.legend(); save(fig,"maximum_jump_standardized_residuals.png","最大request jumpの各モデル標準化残差。")
    fig,ax=plt.subplots(figsize=(7.4,5));
    for model,g in loo.loc[loo.observable=="maximum_request_jump"].groupby("model"): ax.plot(g.omitted_L,g.prediction_error,marker="o",label=model.replace("_","-"))
    ax.axhline(0,color="black"); ax.set(xlabel="Omitted L",ylabel="Prediction error",title="Leave-one-size-out errors"); ax.legend(); save(fig,"maximum_jump_loo.png","各サイズを除外したLOO予測誤差。")
    for parameter,name,title in (("limit","finite_limit_bootstrap.png",r"Bootstrap $Y_\infty$"),("decay_exponent","decay_exponent_bootstrap.png","Bootstrap decay exponent")):
        fig,ax=plt.subplots(figsize=(7.4,5)); subb=bootstrap.loc[(bootstrap.observable=="maximum_request_jump")&bootstrap.converged]
        for model,g in subb.groupby("model"):
            if parameter!="limit" or model.startswith("finite"): ax.hist(g[parameter],bins=30,alpha=.4,label=model.replace("_","-"))
        ax.set(xlabel=parameter,ylabel="Bootstrap count",title=title); ax.legend(); save(fig,name,f"run層別bootstrapによる{parameter}分布。")
    fig,ax=plt.subplots(figsize=(7.4,5)); subl=lmin.loc[lmin.observable=="maximum_request_jump"]
    for model,g in subl.groupby("model"): ax.plot(g.requested_L_min,g.decay_exponent,marker="o",label=model.replace("_","-"))
    ax.set(xlabel=r"Minimum size $L_{min}$",ylabel="Decay exponent",title=r"$L_{min}$ sensitivity"); ax.legend(); save(fig,"maximum_jump_lmin.png","fit下限サイズを変えた減衰指数の安定性。")
    fig,ax=plt.subplots(figsize=(7.4,5)); ax.plot(local.L_mid,local.power_effective_exponent,marker="o",label="power effective exponent"); ax.plot(local.L_mid,local.log_effective_exponent,marker="s",label="log effective exponent"); ax.set(xscale="log",xlabel="Geometric midpoint L",ylabel="Local effective exponent",title="Local effective decay"); ax.legend(); save(fig,"local_effective_exponents.png","隣接サイズ対から計算したpower/log局所有効指数。")
    fig,ax=plt.subplots(figsize=(7.4,5)); pivot=identification.pivot(index="true_model",columns="selected_model",values="selection_rate"); pivot.plot.bar(ax=ax); ax.set(ylabel="Selection rate",title="Parametric-bootstrap model identification"); ax.legend(title="AICc-selected model"); save(fig,"parametric_model_identification.png","zero-powerまたはzero-logを真としたparametric bootstrapのAICc選択率。")
    fig,ax=plt.subplots(figsize=(7.4,5)); subp=predictions.loc[predictions.observable=="maximum_request_jump"]
    for model,g in subp.groupby("model"): ax.plot(g.target_L,g.prediction,marker="o",label=model.replace("_","-")); ax.fill_between(g.target_L,g.prediction_interval95_low,g.prediction_interval95_high,alpha=.1)
    ax.axvline(384,color="black",ls=":"); ax.set(xlabel="Unobserved target L",ylabel="Predicted maximum jump",title="Extrapolations beyond L=384"); ax.legend(); save(fig,"maximum_jump_extrapolations.png","未観測L=512–1536への点予測と95%予測区間。")
    fig,ax=plt.subplots(figsize=(7.4,5)); ranges=subp.groupby("target_L").agg(low=("prediction_interval95_low","max"),high=("prediction_interval95_high","min"),minimum=("prediction","min"),maximum=("prediction","max")).reset_index(); ax.plot(ranges.target_L,ranges.maximum-ranges.minimum,marker="o",label="point-prediction range"); ax.plot(ranges.target_L,ranges.high-ranges.low,marker="s",label="common PI overlap width"); ax.axhline(0,color="black"); ax.set(xlabel="Target L",ylabel="Width",title="Prediction separation and interval overlap"); ax.legend(); save(fig,"prediction_interval_overlap.png","モデル間点予測差と予測区間共通部分の幅。")
    fig,ax=plt.subplots(figsize=(8,5)); ax.scatter(options.estimated_total_seconds,options.estimated_sem)
    for row in options.itertuples():
        if np.isfinite(row.estimated_sem): ax.annotate(row.option,(row.estimated_total_seconds,row.estimated_sem),fontsize=7)
    ax.set(xlabel="Estimated total runtime (s)",ylabel="Estimated L=384 jump SEM",title="Cost-effectiveness of next options"); save(fig,"experiment_cost_effectiveness.png","追加run・次サイズ・終了案の実測外挿費用対効果。")
    # Before/after v6-v7 comparison and four-model panel complete the requested figure set.
    fig,ax=plt.subplots(figsize=(7.4,5));
    for version,root,style in (("v6",Path("app/out/unbounded-v6"),"--"),("v7",None,"-")):
        source=fits if root is None else pd.read_csv(root/"unbounded_model_fits.csv")
        for row in source.loc[source.observable=="maximum_request_jump"].to_dict("records"): ax.plot(grid,[predict(row,L) for L in grid],ls=style,label=f"{version} {row['model']}")
    ax.set(xscale="log",xlabel="L",ylabel="Maximum request jump",title="Fits before and after L=384"); ax.legend(fontsize=6,ncol=2); save(fig,"v6_v7_fit_comparison.png","L=384追加前後の4モデルfit比較。")
    fig,ax=plt.subplots(figsize=(8,5)); jump.plot.bar(x="model",y="signed_error",ax=ax,legend=False); ax.axhline(0,color="black"); ax.set(ylabel="Observed - preregistered",title="L=384 preregistered prediction errors"); save(fig,"l384_prediction_errors.png","L=384事前予測の符号付き誤差。")
    return pd.DataFrame(rows)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",default=str(OUTPUT_ROOT)); parser.add_argument("--bootstrap-samples",type=int,default=500); parser.add_argument("--identification-samples",type=int,default=500); parser.add_argument("--docs-tables",default="docs/tables"); args=parser.parse_args(); run_analysis(args.output,bootstrap_samples=args.bootstrap_samples,identification_samples=args.identification_samples,docs_tables=args.docs_tables)


if __name__=="__main__": main()
