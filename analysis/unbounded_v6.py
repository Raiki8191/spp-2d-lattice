"""UNBOUNDED v6 integration with preregistered L=320 prediction scoring."""

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
    bootstrap_models, fit_models, leave_one_size_out, predict,
    prediction_table, summarize_bootstrap,
)
from analysis.unbounded_v4 import load_stage_runs, stage_quality, stop_audit_report
from analysis.unbounded_v5 import (
    MODEL_OBSERVABLES, load_v5_run_metrics, metric_summary, lmin_fits,
    summarize_loo,
)


L320_ROOT = Path("app/out/unbounded-l320")
L320_MANIFESTS = [L320_ROOT / "benchmark/manifest.csv", L320_ROOT / "pilot/manifest.csv"]
PREREGISTRATION = Path("analysis/reference/unbounded_l320_preregistered_predictions.csv")
OUTPUT_ROOT = Path("app/out/unbounded-v6")


def load_v6_run_metrics() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    events, widths, peaks = load_v5_run_metrics()
    _, events320, widths320 = load_stage_runs(L320_MANIFESTS)
    events = pd.concat([events, events320], ignore_index=True, sort=False)
    widths = pd.concat([widths, widths320], ignore_index=True, sort=False)
    peak_rows = []
    offset = 0
    for manifest_path in L320_MANIFESTS:
        manifest = read_manifest(manifest_path)
        condition = manifest.iloc[0]
        data = pd.read_csv(condition.result_path, usecols=["run", "mean_cluster_size"])
        for run, value in data.groupby("run").mean_cluster_size.max().items():
            peak_rows.append({"L": 320, "run": offset + int(run), "S_peak": float(value)})
        offset += int(condition.runs)
    peaks = pd.concat([peaks, pd.DataFrame(peak_rows)], ignore_index=True)
    return events, widths, peaks


def size_observations(events: pd.DataFrame, widths: pd.DataFrame, peaks: pd.DataFrame,
                      *, L: int, samples: int = 5000, seed: int = 20260720) -> pd.DataFrame:
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
        if not len(values):
            raise ValueError(f"no L={L} values for {observable}")
        estimate = float(np.mean(values) if aggregation == "mean" else np.std(values, ddof=1))
        draws = []
        for _ in range(samples):
            draw = values[rng.integers(0, len(values), len(values))]
            draws.append(float(np.mean(draw) if aggregation == "mean" else np.std(draw, ddof=1)))
        rows.append({
            "observable": observable, "L": L, "run_count": len(values),
            "mean_or_estimate": estimate, "sample_std": float(np.std(values, ddof=1)),
            "sem": (float(np.std(draws, ddof=1)) if aggregation == "std"
                    else float(np.std(values, ddof=1) / np.sqrt(len(values)))),
            "median": float(np.median(values)), "q1": float(np.percentile(values, 25)),
            "q3": float(np.percentile(values, 75)), "minimum": float(np.min(values)),
            "maximum": float(np.max(values)), "bootstrap_ci95_low": float(np.percentile(draws, 2.5)),
            "bootstrap_ci95_high": float(np.percentile(draws, 97.5)),
        })
    return pd.DataFrame(rows)


def score_preregistered(predictions: pd.DataFrame, observations: pd.DataFrame) -> pd.DataFrame:
    scored = predictions.merge(
        observations[["observable", "mean_or_estimate", "sem", "bootstrap_ci95_low", "bootstrap_ci95_high"]],
        on="observable", validate="many_to_one",
    ).rename(columns={"mean_or_estimate": "observed"})
    scored["signed_error"] = scored.observed - scored.prediction
    scored["absolute_error"] = scored.signed_error.abs()
    scored["relative_error"] = scored.absolute_error / scored.observed.abs()
    scored["standardized_error"] = scored.signed_error / scored["sem"]
    scored["squared_error"] = scored.signed_error ** 2
    scored["observed_inside_prediction_interval"] = (
        (scored.observed >= scored.prediction_interval95_low)
        & (scored.observed <= scored.prediction_interval95_high)
    )
    scored["bootstrap_prediction_overlap"] = (
        (scored.bootstrap_ci95_low <= scored.prediction_interval95_high)
        & (scored.bootstrap_ci95_high >= scored.prediction_interval95_low)
    )
    scored["best_absolute_error"] = scored.absolute_error == scored.groupby("observable").absolute_error.transform("min")
    return scored


def cumulative_comparison(fits: pd.DataFrame, loo: pd.DataFrame,
                          intervals: pd.DataFrame) -> pd.DataFrame:
    versions = {
        "v4": Path("app/out/unbounded-v4/main50"),
        "v5": Path("app/out/unbounded-v5"),
    }
    fit_tables = {name: pd.read_csv(path / "unbounded_model_fits.csv") for name, path in versions.items()}
    fit_tables["v6"] = fits
    loo_tables = {
        "v4": summarize_loo(pd.read_csv(versions["v4"] / "unbounded_leave_one_size_out.csv")),
        "v5": pd.read_csv(versions["v5"] / "unbounded_loo_summary.csv"),
        "v6": loo,
    }
    interval_tables = {
        "v4": pd.read_csv(corrected_unbounded_intervals("v4")),
        "v5": pd.read_csv(corrected_unbounded_intervals("v5")),
        "v6": intervals,
    }
    rows = []
    for version in ("v4", "v5", "v6"):
        table = fit_tables[version]
        for fit in table.to_dict("records"):
            item = {"version": version, **fit}
            match = loo_tables[version].loc[
                (loo_tables[version].observable == fit["observable"])
                & (loo_tables[version].model == fit["model"])]
            if not match.empty:
                item.update(match.iloc[0][["loo_mae", "loo_rmse"]].to_dict())
            ci = interval_tables[version].loc[
                (interval_tables[version].observable == fit["observable"])
                & (interval_tables[version].model == fit["model"])
                & (interval_tables[version].parameter == "limit")]
            item["limit_ci95_low"] = float(ci.ci95_low.iloc[0]) if not ci.empty else np.nan
            item["limit_ci95_high"] = float(ci.ci95_high.iloc[0]) if not ci.empty else np.nan
            rows.append(item)
    result = pd.DataFrame(rows)
    result["aicc_rank"] = result.groupby(["version", "observable"]).aicc.rank(method="min")
    result["bic_rank"] = result.groupby(["version", "observable"]).bic.rank(method="min")
    return result


def sequential_prediction_performance(scored320: pd.DataFrame) -> pd.DataFrame:
    v3v4 = pd.read_csv("app/out/unbounded-v4/main50/v3_v4_information_gain.csv")
    rows = []
    for row in v3v4.loc[v3v4.observable == "maximum_request_jump"].itertuples():
        rows.append({"target_L": 192, "model": row.model, "observed": row.L192_observed,
                     "prediction": row.v3_L192_prediction, "error": -row.v3_prediction_error,
                     "absolute_error": abs(row.v3_prediction_error), "status": "reconstructed pre-L192 prediction"})
    prior256 = pd.read_csv("app/out/unbounded-v5/l256_prior_prediction_check.csv")
    for row in prior256.itertuples():
        rows.append({"target_L": 256, "model": row.model, "observed": row.L256_observed_mean,
                     "prediction": row.v4_prior_prediction, "error": -row.prior_prediction_error,
                     "absolute_error": row.absolute_prior_prediction_error, "status": "fixed v4 prediction"})
    for row in scored320.loc[scored320.observable == "maximum_request_jump"].itertuples():
        rows.append({"target_L": 320, "model": row.model, "observed": row.observed,
                     "prediction": row.prediction, "error": row.signed_error,
                     "absolute_error": row.absolute_error, "status": "preregistered before simulation"})
    result = pd.DataFrame(rows)
    result["rank"] = result.groupby("target_L").absolute_error.rank(method="min")
    result["cumulative_absolute_error"] = result.sort_values("target_L").groupby("model").absolute_error.cumsum()
    return result


def seed_audit() -> pd.DataFrame:
    """Verify that L=192, 256 and 320 production stages use disjoint run seeds."""

    roots = {
        192: (Path("app/out/unbounded-l192"), ("benchmark", "pilot", "main")),
        256: (Path("app/out/unbounded-l256"), ("benchmark", "pilot")),
        320: (L320_ROOT, ("benchmark", "pilot")),
    }
    rows = []
    sets: dict[int, set[int]] = {}
    for L, (root, stages) in roots.items():
        values: list[int] = []
        for stage in stages:
            values.extend(pd.read_csv(root / stage / "run_metadata.csv").run_seed.astype(int))
        sets[L] = set(values)
        rows.append({
            "scope": f"L={L}", "run_count": len(values),
            "unique_run_seed_count": len(sets[L]),
            "duplicate_count": len(values) - len(sets[L]),
            "overlap_count": 0,
        })
    for left, right in ((192, 256), (192, 320), (256, 320)):
        rows.append({
            "scope": f"L={left} vs L={right}", "run_count": np.nan,
            "unique_run_seed_count": np.nan, "duplicate_count": np.nan,
            "overlap_count": len(sets[left].intersection(sets[right])),
        })
    return pd.DataFrame(rows)


def experiment_options(metadata: pd.DataFrame, observations: pd.DataFrame) -> pd.DataFrame:
    seconds = float(metadata.elapsed_milliseconds.median() / 1000)
    jump = observations.loc[observations.observable == "maximum_request_jump"].iloc[0]
    bytes_per_run = float(metadata.results_bytes.mean())
    rows = []
    for label, L, runs in (("A L320 total50",320,50),("B L320 total100",320,100),
                           ("C L384 benchmark",384,3),("C L384 pilot",384,20),
                           ("D L256 total50",256,50),("D L256 total100",256,100),("E stop",320,20)):
        scale = (L/320) ** 4
        rows.append({"option":label,"L":L,"runs":runs,
                     "estimated_total_seconds":0 if label.startswith("E") else seconds*scale*runs,
                     "estimated_results_bytes":0 if label.startswith("E") else bytes_per_run*scale*runs,
                     "estimated_jump_sem":jump.sample_std/math.sqrt(runs) if L==320 else np.nan,
                     "information_value":"new size leverage" if L>320 else "reduces same-size sampling error" if L==320 and runs>20 else "comparison/stop",
                     "warning":"empirical scaling estimate, not an observation"})
    return pd.DataFrame(rows)


def summarize_extrapolations(predictions: pd.DataFrame) -> pd.DataFrame:
    """Summarize v6 extrapolation spread relative to the observed L=320 frontier."""

    rows = []
    for (observable, target_L), group in predictions.groupby(["observable", "target_L"], sort=True):
        rows.append({
            "observable": observable, "target_L": int(target_L),
            "model_prediction_min": float(group.prediction.min()),
            "model_prediction_max": float(group.prediction.max()),
            "between_model_range": float(group.prediction.max() - group.prediction.min()),
            "all_intervals_overlap": bool(
                group.prediction_ci95_low.max() <= group.prediction_ci95_high.min()),
            "distance_from_largest_observed_L": float(target_L / group.largest_observed_L.iloc[0]),
            "warning": "model extrapolation beyond L=320; not an observation",
        })
    return pd.DataFrame(rows)


def run_analysis(output: str | Path = OUTPUT_ROOT, *, bootstrap_samples: int = 500,
                 seed: int = 20260720) -> list[Path]:
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    events, widths, peaks = load_v6_run_metrics()
    summary = metric_summary(events, widths, peaks)
    sources = {"maximum_request_jump":events,"request_event_p_dispersion":events,
               "request_event_p_after":events,"transition_delta_p":widths,
               "transition_delta_t_normalized":widths}
    fits_parts=[]; loo_parts=[]; boot_parts=[]
    for index,(observable,(column,aggregation)) in enumerate(MODEL_OBSERVABLES.items()):
        subset=summary.loc[summary.observable==observable]
        fits_parts.append(fit_models(subset.L,subset.value,observable=observable))
        loo_parts.append(leave_one_size_out(subset,"value",observable))
        boot_parts.append(bootstrap_models(sources[observable],value_column=column,aggregation=aggregation,
                                           observable=observable,samples=bootstrap_samples,seed=seed+index))
    fits=pd.concat(fits_parts,ignore_index=True); loo_raw=pd.concat(loo_parts,ignore_index=True)
    bootstrap=pd.concat(boot_parts,ignore_index=True); intervals=summarize_bootstrap(bootstrap)
    loo=summarize_loo(loo_raw); predictions=prediction_table(fits,bootstrap,targets=(320,384,512,768,1024))
    observations=size_observations(events,widths,peaks,L=320,samples=5000,seed=seed)
    prereg=pd.read_csv(PREREGISTRATION); scored=score_preregistered(prereg,observations)
    cumulative=cumulative_comparison(fits,loo,intervals)
    sequential=sequential_prediction_performance(scored)
    quality=stage_quality(L320_MANIFESTS)
    audit=stop_audit_report(stage_root=L320_ROOT,benchmark_name="benchmark/manifest.csv",audit_name="stop-audit/manifest.csv")
    metadata=pd.concat([pd.read_csv(L320_ROOT/"benchmark/run_metadata.csv"),pd.read_csv(L320_ROOT/"pilot/run_metadata.csv")],ignore_index=True)
    options=experiment_options(metadata,observations)
    seeds=seed_audit()
    tables={"unbounded_size_summary.csv":summary,"unbounded_model_fits.csv":fits,
            "unbounded_leave_one_size_out.csv":loo_raw,"unbounded_loo_summary.csv":loo,
            "unbounded_bootstrap_samples.csv":bootstrap,"unbounded_bootstrap_intervals.csv":intervals,
            "unbounded_predictions.csv":predictions,"unbounded_lmin_dependence.csv":lmin_fits(summary),
            "l320_observations.csv":observations,"l320_preregistered_prediction_scores.csv":scored,
            "v4_v5_v6_model_comparison.csv":cumulative,"sequential_prediction_performance.csv":sequential,
            "stage_data_quality.csv":quality,"stop_audit.csv":audit,"experiment_options.csv":options,
            "seed_audit.csv":seeds,
            "extrapolation_ranges.csv":summarize_extrapolations(predictions)}
    for name,frame in tables.items(): frame.to_csv(output/name,index=False)
    figures=create_figures(summary,fits,loo_raw,bootstrap,tables["unbounded_lmin_dependence.csv"],predictions,scored,sequential,options,output/"figures")
    print(f"unbounded-v6: L320_runs={int(observations.run_count.max())} bootstrap_samples={bootstrap_samples} outputs={len(tables)+len(figures)}")
    return [output/name for name in tables]+figures


def create_figures(summary,fits,loo,bootstrap,lmin,predictions,scored,sequential,options,directory:Path):
    directory.mkdir(parents=True,exist_ok=True); paths=[]
    for observable in ("maximum_request_jump","transition_delta_p","transition_delta_t_normalized"):
        data=summary.loc[summary.observable==observable].sort_values("L"); grid=np.geomspace(8,1024,300)
        fig,ax=plt.subplots(figsize=(7.2,5)); ax.errorbar(data.L,data.value,yerr=data.sample_sem,fmt="o",label="observed mean ± SEM")
        for row in fits.loc[fits.observable==observable].to_dict("records"): ax.plot(grid,[predict(row,L) for L in grid],label=row["model"])
        ax.axvline(320,color="black",linestyle=":",label="largest observed L"); ax.set(xscale="log",xlabel="linear size L",ylabel=observable,title=f"UNBOUNDED v6: {observable}"); ax.legend(fontsize=7); paths.append(_save(fig,directory/f"{observable}_size_dependence.png"))
    for observable in ("maximum_request_jump","transition_delta_p"):
        for family in ("power","log"):
            data=summary.loc[summary.observable==observable].sort_values("L"); grid=np.geomspace(8,320,200); fig,ax=plt.subplots(figsize=(7.2,5)); ax.plot(data.L,data.value,"o")
            for row in fits.loc[(fits.observable==observable)&fits.model.str.contains(family)].to_dict("records"): ax.plot(grid,[predict(row,L) for L in grid],label=row["model"])
            ax.set(xscale="log",xlabel="L",ylabel=observable,title=f"Zero/finite {family} comparison"); ax.legend(); paths.append(_save(fig,directory/f"{observable}_{family}_comparison.png"))
    # Preregistered errors, sequential performance, ranks, residuals, Lmin, bootstrap, extrapolation and costs.
    specs=[]
    fig,ax=plt.subplots(figsize=(8,5)); jump=scored.loc[scored.observable=="maximum_request_jump"]; ax.bar(jump.model,jump.signed_error); ax.axhline(0,color="black"); ax.set(ylabel="observed - preregistered prediction",title="L=320 preregistered prediction errors"); specs.append((fig,"l320_preregistered_prediction_errors.png"))
    fig,ax=plt.subplots(figsize=(8,5)); jump=jump.reset_index(drop=True); positions=np.arange(len(jump))
    prediction_errors=np.vstack((jump.prediction-jump.prediction_interval95_low,
                                 jump.prediction_interval95_high-jump.prediction))
    ax.errorbar(positions,jump.prediction,yerr=prediction_errors,fmt="o",capsize=4,
                label="preregistered prediction and 95% PI")
    observed=float(jump.observed.iloc[0]); obs_low=float(jump.bootstrap_ci95_low.iloc[0]); obs_high=float(jump.bootstrap_ci95_high.iloc[0])
    ax.axhspan(obs_low,obs_high,color="tab:green",alpha=.18,label="observed bootstrap 95% CI")
    ax.axhline(observed,color="tab:green",label="observed mean")
    ax.set_xticks(positions,jump.model,rotation=20); ax.set(ylabel="maximum request jump",title="L=320 preregistered prediction intervals"); ax.legend(fontsize=8); specs.append((fig,"l320_preregistered_prediction_intervals.png"))
    fig,ax=plt.subplots(figsize=(8,5));
    for model,g in sequential.groupby("model"): ax.plot(g.target_L,g.absolute_error,marker="o",label=model)
    ax.set(xlabel="target L",ylabel="absolute out-of-sample error",title="Sequential prediction performance"); ax.legend(); specs.append((fig,"sequential_prediction_performance.png"))
    fig,ax=plt.subplots(figsize=(8,5));
    comparison=cumulative_comparison(fits,summarize_loo(loo),summarize_bootstrap(bootstrap)); sub=comparison.loc[comparison.observable=="maximum_request_jump"]
    for model,g in sub.groupby("model"): ax.plot(g.version,g.aicc_rank,marker="o",label=model)
    ax.invert_yaxis(); ax.set(ylabel="AICc rank",title="Model-rank migration v4-v6"); ax.legend(); specs.append((fig,"model_rank_migration.png"))
    fig,ax=plt.subplots(figsize=(8,5)); data=summary.loc[summary.observable=="maximum_request_jump"].sort_values("L")
    scale=data.sample_sem.replace(0,np.nan).to_numpy(float)
    for row in fits.loc[fits.observable=="maximum_request_jump"].to_dict("records"): ax.plot(data.L,(data.value-[predict(row,L) for L in data.L])/scale,marker="o",label=row["model"])
    ax.axhline(0,color="black"); ax.set(xlabel="L",ylabel="standardized residual (residual / SEM)",title="Maximum-jump standardized residuals"); ax.legend(); specs.append((fig,"maximum_jump_standardized_residuals.png"))
    fig,ax=plt.subplots(figsize=(8,5));
    for model,g in loo.loc[loo.observable=="maximum_request_jump"].groupby("model"): ax.plot(g.omitted_L,g.prediction_error,marker="o",label=model)
    ax.axhline(0,color="black"); ax.set(xlabel="omitted L",ylabel="LOO error",title="Leave-one-size-out errors"); ax.legend(); specs.append((fig,"maximum_jump_loo.png"))
    fig,ax=plt.subplots(figsize=(8,5)); sub=lmin.loc[lmin.observable=="maximum_request_jump"]
    for model,g in sub.groupby("model"): ax.plot(g.requested_L_min,g.decay_exponent,marker="o",label=model)
    ax.set(xlabel="L_min",ylabel="decay exponent",title="L_min dependence"); ax.legend(); specs.append((fig,"maximum_jump_lmin.png"))
    for parameter,name in (("limit","finite_limit_bootstrap.png"),("decay_exponent","decay_exponent_bootstrap.png")):
        fig,ax=plt.subplots(figsize=(8,5)); sub=bootstrap.loc[(bootstrap.observable=="maximum_request_jump")&bootstrap.converged]
        for model,g in sub.groupby("model"):
            if parameter!="limit" or model.startswith("finite"): ax.hist(g[parameter],bins=30,alpha=.4,label=model)
        ax.set(xlabel=parameter,ylabel="bootstrap count",title="Run-stratified bootstrap"); ax.legend(); specs.append((fig,name))
    fig,ax=plt.subplots(figsize=(8,5)); sub=predictions.loc[predictions.observable=="maximum_request_jump"]
    for model,g in sub.groupby("model"): ax.plot(g.target_L,g.prediction,marker="o",label=model); ax.fill_between(g.target_L,g.prediction_ci95_low,g.prediction_ci95_high,alpha=.12)
    ax.axvline(320,color="black",linestyle=":"); ax.set(xlabel="target L",ylabel="predicted jump",title="Extrapolations beyond L=320"); ax.legend(); specs.append((fig,"maximum_jump_extrapolations.png"))
    fig,ax=plt.subplots(figsize=(8,5)); ax.scatter(options.estimated_total_seconds,options.estimated_jump_sem)
    for row in options.itertuples():
        if np.isfinite(row.estimated_jump_sem): ax.annotate(row.option,(row.estimated_total_seconds,row.estimated_jump_sem),fontsize=7)
    ax.set(xlabel="estimated total seconds",ylabel="estimated L=320 jump SEM",title="Next-experiment cost effectiveness"); specs.append((fig,"experiment_cost_effectiveness.png"))
    for fig,name in specs: paths.append(_save(fig,directory/name))
    return paths


def _save(fig,path): fig.tight_layout(); fig.savefig(path,dpi=180); plt.close(fig); return path


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",default=str(OUTPUT_ROOT)); parser.add_argument("--bootstrap-samples",type=int,default=500); args=parser.parse_args(); run_analysis(args.output,bootstrap_samples=args.bootstrap_samples)


if __name__=="__main__": main()
