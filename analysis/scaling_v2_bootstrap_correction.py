"""Regenerate only scaling-v2 finite-limit bootstrap with the point estimator."""
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np,pandas as pd
from analysis.scaling_v2 import L_MINS,_bootstrap_finite_power_fit
from analysis.model_fitting import fit_power_models

def _fit_chunk(task):
    lm,L,means,offset=task
    rows=[]
    for j,y in enumerate(means):
        try:
            fit=_bootstrap_finite_power_fit(L,y)
            c,a,q=map(float,fit["parameters"])
            rows.append(dict(observable="delta_P_max",L_min=lm,sample=offset+j,limit=c,
                 amplitude=a,decay_exponent=q,rss=fit["rss"],aicc=fit["aicc"],bic=fit["bic"],
                 converged=True,estimator="bounded_original_scale_multistart"))
        except (RuntimeError,ValueError) as error:
            rows.append(dict(observable="delta_P_max",L_min=lm,sample=offset+j,limit=np.nan,
                 converged=False,failure=str(error),estimator="bounded_original_scale_multistart"))
    return rows

def regenerate(source:Path,output:Path,*,samples:int=5000,seed:int=20260720,workers:int=2):
    if output.exists():raise FileExistsError(output)
    input_paths=[source/"request_event_runs.csv",source/"request_event_summary.csv",source/"unbounded_model_bootstrap.csv",source/"unbounded_model_fits.csv"]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in input_paths}
    e=pd.read_csv(input_paths[0]);e=e[e.budget_mode=="UNBOUNDED"]
    s=pd.read_csv(input_paths[1]);s=s[s.budget_mode=="UNBOUNDED"].sort_values("L")
    tasks=[]
    for lm in L_MINS:
        sub=s[(s.L>=lm)&(s.delta_P_max_mean>0)]
        if len(sub)<4:continue
        L=sub.L.to_numpy(float)
        rng=np.random.default_rng(np.random.SeedSequence([seed,lm,991]))
        groups={int(k):g.delta_P_max.to_numpy(float) for k,g in e[e.L>=lm].groupby("L")}
        means=np.array([[rng.choice(groups[int(k)],len(groups[int(k)]),replace=True).mean() for k in L] for _ in range(samples)])
        for offset in range(0,samples,100):tasks.append((lm,L,means[offset:offset+100],offset))
    output.mkdir(parents=True)
    rows=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for chunk in pool.map(_fit_chunk,tasks):
            rows.extend(chunk);print(f"completed={len(rows)}/{len(L_MINS)*samples}",flush=True)
    boot=pd.DataFrame(rows).sort_values(["L_min","sample"])
    intervals=[]
    for lm,g in boot.groupby("L_min"):
        vals=g.loc[g.converged,"limit"].to_numpy()
        low,high=np.percentile(vals,[2.5,97.5]) if len(vals) else (np.nan,np.nan)
        boot.loc[g.index,"bootstrap_low"]=low;boot.loc[g.index,"bootstrap_high"]=high
        boot.loc[g.index,"interval_includes_zero"]=bool(low<=1e-8 and high>=0) if np.isfinite(low) else pd.NA
        old=pd.read_csv(input_paths[2]);old=old[old.L_min==lm]
        intervals.append(dict(L_min=int(lm),samples=len(g),converged=int(g.converged.sum()),
                 ci95_low=low,ci95_high=high,old_ci95_low=old.bootstrap_low.iloc[0],
                 old_ci95_high=old.bootstrap_high.iloc[0],zero_boundary_frequency=float((vals<=1e-8).mean()) if len(vals) else np.nan))
    boot.to_csv(output/"unbounded_model_bootstrap.csv",index=False)
    pd.DataFrame(intervals).to_csv(output/"bootstrap_correction_comparison.csv",index=False)
    for p in input_paths:
        if hashlib.sha256(p.read_bytes()).hexdigest()!=hashes[str(p)]:raise RuntimeError("input changed")
    (output/"correction_provenance.json").write_text(json.dumps(dict(source=str(source),samples=samples,seed=seed,workers=workers,input_sha256=hashes,method="same fit_power_models as point estimator; original per-Lmin draw order"),indent=2))
    print(pd.DataFrame(intervals).to_string(index=False),flush=True)
    return boot

def main():
    p=argparse.ArgumentParser();p.add_argument("--source",type=Path,default=Path("app/out/scaling-v2-analysis"))
    p.add_argument("--output",type=Path,required=True);p.add_argument("--samples",type=int,default=5000);p.add_argument("--workers",type=int,default=2)
    a=p.parse_args();regenerate(a.source,a.output,samples=a.samples,workers=a.workers)
if __name__=="__main__":main()
