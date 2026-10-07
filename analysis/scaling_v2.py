"""Streaming scaling-v2 integration, stop audit, FSS fits, bootstrap, and plots."""

from __future__ import annotations

import argparse
import gc
import math
import os
import tempfile
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "spp-matplotlib-cache")
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.model_fitting import constant_power, fit_power_models, fit_shift, pure_power
from analysis.multi_manifest import iter_conditions, logical_manifest, read_condition
from analysis.request_event import require_request_measurements
from analysis.request_fss import BOOTSTRAP_METRICS, prepare_request_events, summarize_request_fss
from analysis.scaling_fit import fit_scaling
from analysis.stop_extension import analyze_stop_extension, summarize_stop_extension
from analysis.transition_width import calculate_transition_widths, summarize_transition_widths


BOOTSTRAP_SAMPLES = 5000
BOOTSTRAP_SEED = 20260720
L_MINS = (8, 12, 16, 24, 32)


def analyze_manifests(
    manifest_paths: list[str | Path],
    output_directory: str | Path,
    *,
    bootstrap_samples: int = BOOTSTRAP_SAMPLES,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> list[Path]:
    """Process each condition independently and write the scaling-v2 products."""

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    event_frames: list[pd.DataFrame] = []
    width_frames: list[pd.DataFrame] = []
    peak_bytes = 0
    metadata = logical_manifest(manifest_paths)
    require_request_measurements(metadata)
    metadata.to_csv(output / "logical_manifest.csv", index=False, encoding="utf-8")

    for condition in iter_conditions(manifest_paths):
        results = read_condition(condition)
        peak_bytes = max(peak_bytes, int(results.memory_usage(deep=True).sum()))
        events = prepare_request_events(results)
        widths = calculate_transition_widths(results)
        expected_runs = int(condition.metadata["runs"])
        if len(events) != expected_runs or len(widths) != expected_runs:
            raise ValueError(
                f"incomplete run summaries for global_condition_id={condition.global_condition_id}: "
                f"events={len(events)}, widths={len(widths)}, expected={expected_runs}"
            )
        event_frames.append(events)
        widths["global_condition_id"] = condition.global_condition_id
        widths["source_condition_index"] = condition.source_condition_index
        widths["source_manifest"] = condition.source_manifest
        width_frames.append(widths)
        del results, events, widths
        gc.collect()

    events = pd.concat(event_frames, ignore_index=True)
    widths = pd.concat(width_frames, ignore_index=True)
    request_summary = summarize_request_fss(
        events, bootstrap_samples=bootstrap_samples, bootstrap_seed=bootstrap_seed
    )
    transition_summary = summarize_transition_widths(widths)
    request_summary = _attach_sources(request_summary, metadata)
    transition_summary = _attach_sources(transition_summary, metadata)
    bootstrap = _bootstrap_summary(
        events, widths, bootstrap_samples=bootstrap_samples, bootstrap_seed=bootstrap_seed
    )

    outputs = [
        output / "request_event_runs.csv",
        output / "request_event_summary.csv",
        output / "transition_width_runs.csv",
        output / "transition_width_summary.csv",
        output / "bootstrap_summary.csv",
    ]
    for frame, path in zip(
        (events, request_summary, widths, transition_summary, bootstrap), outputs
    ):
        frame.to_csv(path, index=False, encoding="utf-8")

    fits, effective = fit_scaling(request_summary, transition_summary)
    fits.to_csv(output / "finite_scaling_fits.csv", index=False, encoding="utf-8")
    effective.to_csv(output / "local_effective_exponents.csv", index=False, encoding="utf-8")
    comparisons = _scaling_comparisons(fits)
    comparisons.to_csv(output / "finite_scaling_comparisons.csv", index=False, encoding="utf-8")
    unbounded_fits, unbounded_bootstrap, unbounded_comparison = _unbounded_models(
        events, widths, request_summary, transition_summary,
        bootstrap_samples=bootstrap_samples, bootstrap_seed=bootstrap_seed,
    )
    for frame, name in (
        (unbounded_fits, "unbounded_model_fits.csv"),
        (unbounded_bootstrap, "unbounded_model_bootstrap.csv"),
        (unbounded_comparison, "unbounded_model_comparison.csv"),
    ):
        frame.to_csv(output / name, index=False, encoding="utf-8")
    shifts = _shift_fits(request_summary)
    shifts.to_csv(output / "pseudocritical_shift_fits.csv", index=False, encoding="utf-8")
    memory = pd.DataFrame([{
        "peak_condition_dataframe_bytes": peak_bytes,
        "retained_event_width_bytes": int(events.memory_usage(deep=True).sum() + widths.memory_usage(deep=True).sum()),
        "condition_count": len(metadata),
        "condition_run_count": len(events),
    }])
    memory.to_csv(output / "memory_summary.csv", index=False, encoding="utf-8")
    plot_paths = _plots(request_summary, transition_summary, fits, effective,
                        unbounded_fits, unbounded_bootstrap, output / "figures")
    outputs.extend([
        output / "finite_scaling_fits.csv",
        output / "local_effective_exponents.csv",
        output / "finite_scaling_comparisons.csv",
        output / "unbounded_model_fits.csv",
        output / "unbounded_model_bootstrap.csv",
        output / "unbounded_model_comparison.csv",
        output / "pseudocritical_shift_fits.csv",
        output / "memory_summary.csv",
        *plot_paths,
    ])
    print(f"Processed conditions={len(metadata)}, condition-runs={len(events)}, peak_dataframe_bytes={peak_bytes}")
    return outputs


def audit_stops(
    main_manifest: str | Path,
    audit_manifest: str | Path,
    output_directory: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Verify main prefixes and summarize whether diagnostics occur after 1/L."""

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    for manifest_path in (main_manifest, audit_manifest):
        require_request_measurements(logical_manifest([manifest_path]))
    main_conditions = {(c.metadata["L"], c.metadata["C"]): c for c in iter_conditions([main_manifest])}
    run_frames: list[pd.DataFrame] = []
    for audit_condition in iter_conditions([audit_manifest]):
        key = (audit_condition.metadata["L"], audit_condition.metadata["C"])
        if key not in main_conditions:
            raise ValueError(f"main manifest lacks audit condition L={key[0]}, C={key[1]}")
        audit = read_condition(audit_condition)
        main = read_condition(main_conditions[key])
        main = main.loc[main["run"] < int(audit_condition.metadata["runs"])].copy()
        _assert_main_prefix(main, audit)
        analyzed = analyze_stop_extension(audit, extended_multiplier=0.5)
        analyzed["main_prefix_identical"] = True
        events = prepare_request_events(audit)
        analyzed = analyzed.merge(
            events[["condition_index", "run", "p_before", "p_after", "step"]].rename(
                columns={"p_before": "request_event_p_before", "p_after": "request_event_p_after", "step": "request_event_step"}
            ), on=["condition_index", "run"], how="left", validate="one_to_one"
        )
        analyzed["request_event_endpoints_after_old"] = analyzed["request_event_step"] > analyzed["old_threshold_step"]
        run_frames.append(analyzed)
        del audit, main
        gc.collect()
    runs = pd.concat(run_frames, ignore_index=True)
    summary = summarize_stop_extension(runs)
    summary["main_prefix_identical_runs"] = summary["runs"]
    summary["request_event_endpoints_after_old_runs"] = runs.groupby(
        ["condition_index", "L", "C", "budget_mode"], sort=True
    )["request_event_endpoints_after_old"].sum().to_numpy()
    runs.to_csv(output / "stop_audit_runs.csv", index=False, encoding="utf-8")
    summary.to_csv(output / "stop_audit_summary.csv", index=False, encoding="utf-8")
    return runs, summary


def _assert_main_prefix(main: pd.DataFrame, audit: pd.DataFrame) -> None:
    columns = [
        "run", "L", "C", "step", "removed_edges", "remaining_edges",
        "removed_edge_fraction", "largest_cluster_size", "largest_cluster_fraction",
        "second_largest_cluster_size", "mean_cluster_size", "accepted_requests",
        "rejected_requests", "seed",
    ]
    for run, expected in main.groupby("run", sort=True):
        observed = audit.loc[(audit["run"] == run) & (audit["step"].isin(expected["step"]))]
        expected = expected.sort_values("step")[columns].reset_index(drop=True)
        observed = observed.sort_values("step")[columns].reset_index(drop=True)
        try:
            pd.testing.assert_frame_equal(expected, observed, check_exact=True)
        except AssertionError as error:
            raise ValueError(f"audit prefix differs for run={run}: {error}") from error


def _attach_sources(summary: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    lookup = metadata[["global_condition_id", "source_manifest", "source_condition_index"]].rename(
        columns={"global_condition_id": "condition_index"}
    )
    return summary.merge(lookup, on="condition_index", how="left", validate="one_to_one")


def _bootstrap_summary(
    events: pd.DataFrame,
    widths: pd.DataFrame,
    *, bootstrap_samples: int,
    bootstrap_seed: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    sources = [(events, BOOTSTRAP_METRICS), (widths, ("delta_p", "delta_t_normalized"))]
    for frame, metrics in sources:
        for condition, group in frame.groupby("condition_index", sort=True):
            first = group.iloc[0]
            rng = np.random.default_rng(np.random.SeedSequence([bootstrap_seed, int(condition)]))
            indices = rng.integers(0, len(group), size=(bootstrap_samples, len(group)))
            for metric in metrics:
                values = group[metric].to_numpy(float)
                values = values[np.isfinite(values)]
                if len(values) == 0:
                    low = high = np.nan
                else:
                    local_indices = rng.integers(0, len(values), size=(bootstrap_samples, len(values)))
                    means = values[local_indices].mean(axis=1)
                    low, high = np.percentile(means, [2.5, 97.5])
                rows.append({
                    "condition_index": int(condition), "L": int(first["L"]), "C": int(first["C"]),
                    "budget_mode": str(first["budget_mode"]), "metric": metric,
                    "run_count": len(values), "mean": float(np.mean(values)) if len(values) else np.nan,
                    "bootstrap_low": low, "bootstrap_high": high,
                    "bootstrap_samples": bootstrap_samples, "bootstrap_seed": bootstrap_seed,
                })
    return pd.DataFrame(rows)


def _scaling_comparisons(fits: pd.DataFrame) -> pd.DataFrame:
    theory = {"P_before": 5/48, "P_after": 5/48, "S_before": 43/24,
              "S_after": 43/24, "std_p_mid": 3/4}
    rows: list[dict[str, object]] = []
    for item in fits.itertuples(index=False):
        row = {"condition_label": item.condition_label, "observable": item.observable,
               "L_min": item.L_min, "exponent": item.exponent}
        if item.condition_label == "C=1" and item.observable in theory:
            row.update(reference="2D_percolation", reference_exponent=theory[item.observable],
                       exponent_difference=item.exponent-theory[item.observable])
            rows.append(row)
        if item.condition_label == "C=2":
            reference = fits.loc[(fits["condition_label"] == "C=1") &
                                 (fits["observable"] == item.observable) &
                                 (fits["L_min"] == item.L_min)]
            if not reference.empty:
                ref = float(reference.iloc[0]["exponent"])
                row.update(reference="C=1", reference_exponent=ref,
                           exponent_difference=item.exponent-ref)
                rows.append(row)
    for label in ("C=1", "C=2"):
        for L_min in sorted(fits["L_min"].unique()):
            group = fits.loc[(fits["condition_label"] == label) & (fits["L_min"] == L_min)]
            for suffix in ("before", "after"):
                p = group.loc[group["observable"] == f"P_{suffix}"]
                s = group.loc[group["observable"] == f"S_{suffix}"]
                if not p.empty and not s.empty:
                    rows.append({"condition_label": label, "observable": f"hyperscaling_{suffix}",
                                 "L_min": L_min, "exponent": 2*float(p.iloc[0]["exponent"])+float(s.iloc[0]["exponent"]),
                                 "reference": "dimension", "reference_exponent": 2.0,
                                 "exponent_difference": 2*float(p.iloc[0]["exponent"])+float(s.iloc[0]["exponent"])-2.0})
    return pd.DataFrame(rows)


def _fit_record(observable: str, model: str, L_min: int, L: np.ndarray,
                fit: dict[str, object]) -> dict[str, object]:
    parameters = np.asarray(fit["parameters"])
    errors = np.asarray(fit["standard_errors"])
    names = ("b", "exponent") if model == "A" else ("limit", "b", "exponent")
    row: dict[str, object] = {"observable": observable, "model": model, "L_min": L_min,
        "used_L": ";".join(str(int(x)) for x in L), "point_count": len(L),
        "rss": fit["rss"], "r_squared": fit["r_squared"], "aicc": fit["aicc"],
        "bic": fit["bic"], "converged": fit["converged"]}
    for index, name in enumerate(names):
        row[name] = parameters[index]; row[f"{name}_standard_error"] = errors[index]
        row[f"{name}_ci95_low"] = parameters[index]-1.96*errors[index]
        row[f"{name}_ci95_high"] = parameters[index]+1.96*errors[index]
    return row


def _bootstrap_finite_power_fit(L: np.ndarray, values: np.ndarray) -> dict[str, object]:
    """Apply the point estimator, including its bounded multistart policy."""
    return fit_power_models(L, values)[1]


def _unbounded_models(events: pd.DataFrame, widths: pd.DataFrame,
                      request_summary: pd.DataFrame, transition_summary: pd.DataFrame,
                      *, bootstrap_samples: int, bootstrap_seed: int):
    summary = request_summary.loc[request_summary["budget_mode"] == "UNBOUNDED"].merge(
        transition_summary[["condition_index", "delta_p_mean"]], on="condition_index", validate="one_to_one"
    ).sort_values("L")
    specs = {"delta_P_max": "delta_P_max_mean", "transition_delta_p": "delta_p_mean",
             "P_before": "P_before_mean", "P_after": "P_after_mean"}
    fit_rows: list[dict[str, object]] = []
    comparison_rows: list[dict[str, object]] = []
    bootstrap_rows: list[dict[str, object]] = []
    ub_events = events.loc[events["budget_mode"] == "UNBOUNDED"]
    for observable, column in specs.items():
        for L_min in L_MINS:
            subset = summary.loc[(summary["L"] >= L_min) & (summary[column] > 0)]
            if len(subset) < 4:
                continue
            L = subset["L"].to_numpy(float); values = subset[column].to_numpy(float)
            try:
                model_a, model_b = fit_power_models(L, values)
            except RuntimeError:
                continue
            a = _fit_record(observable, "A", L_min, L, model_a)
            b = _fit_record(observable, "B", L_min, L, model_b)
            fit_rows.extend((a, b))
            comparison_rows.append({"observable": observable, "L_min": L_min,
                "delta_aicc_B_minus_A": b["aicc"]-a["aicc"],
                "delta_bic_B_minus_A": b["bic"]-a["bic"],
                "preferred_by_aicc": "B" if b["aicc"] < a["aicc"] else "A",
                "preferred_by_bic": "B" if b["bic"] < a["bic"] else "A"})
            if observable == "delta_P_max":
                rng = np.random.default_rng(np.random.SeedSequence([bootstrap_seed, L_min, 991]))
                samples: list[float] = []
                groups = {int(size): group["delta_P_max"].to_numpy(float)
                          for size, group in ub_events.loc[ub_events["L"] >= L_min].groupby("L")}
                for sample in range(bootstrap_samples):
                    means = np.asarray([rng.choice(groups[int(size)], len(groups[int(size)]), replace=True).mean() for size in L])
                    try:
                        fit = _bootstrap_finite_power_fit(L, means)
                        samples.append(float(fit["parameters"][0]))
                    except (RuntimeError, ValueError):
                        samples.append(np.nan)
                valid = np.asarray(samples)[np.isfinite(samples)]
                low, high = np.percentile(valid, [2.5, 97.5]) if len(valid) else (np.nan, np.nan)
                for sample, value in enumerate(samples):
                    bootstrap_rows.append({"observable": observable, "L_min": L_min,
                        "sample": sample, "limit": value, "converged": np.isfinite(value),
                        "bootstrap_low": low, "bootstrap_high": high,
                        # Bounded optimization represents the boundary by tiny
                        # positive numbers, so numerical zero uses an explicit tolerance.
                        "interval_includes_zero": bool(low <= 1.0e-8 and high >= 0) if np.isfinite(low) else pd.NA})
                b["limit_bootstrap_low"] = low; b["limit_bootstrap_high"] = high
                b["limit_bootstrap_includes_zero"] = bool(low <= 1.0e-8 and high >= 0) if np.isfinite(low) else pd.NA
    return pd.DataFrame(fit_rows), pd.DataFrame(bootstrap_rows), pd.DataFrame(comparison_rows)


def _shift_fits(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for C in (1, 2):
        group = summary.loc[(summary["budget_mode"] == "FINITE") & (summary["C"] == C)].sort_values("L")
        for fixed_pc in ((0.5, None) if C == 1 else (None,)):
            fit = fit_shift(group["L"], group["p_mid_mean"], fixed_pc=fixed_pc)
            parameters = np.asarray(fit["parameters"]); errors = np.asarray(fit["standard_errors"])
            if fixed_pc is None:
                pc, amplitude, inverse_nu = parameters; pc_error, a_error, nu_error = errors
                mode = "FREE_PC"
            else:
                pc = fixed_pc; amplitude, inverse_nu = parameters; pc_error = 0.0; a_error, nu_error = errors
                mode = "FIXED_PC"
            rows.append({"C": C, "fit_mode": mode, "pc": pc, "pc_standard_error": pc_error,
                "a": amplitude, "a_standard_error": a_error, "inverse_nu": inverse_nu,
                "inverse_nu_standard_error": nu_error, "rss": fit["rss"], "r_squared": fit["r_squared"],
                "aicc": fit["aicc"], "bic": fit["bic"], "used_L": ";".join(map(str, group["L"].astype(int)))})
    return pd.DataFrame(rows)


def _plots(request: pd.DataFrame, transition: pd.DataFrame, fits: pd.DataFrame,
           effective: pd.DataFrame, ub_fits: pd.DataFrame, ub_bootstrap: pd.DataFrame,
           directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True); outputs: list[Path] = []
    request = request.copy(); request["label"] = request.apply(lambda r: "UNBOUNDED" if r.budget_mode == "UNBOUNDED" else f"C={int(r.C)}", axis=1)
    for metrics, ylabel, name in (
        (("P_before", "P_after"), "P", "finite_P_vs_L"),
        (("S_before", "S_after"), "S", "finite_S_vs_L"),
        (("p_before", "p_after", "p_mid"), "p", "pseudocritical_p_vs_inverse_L"),
        (("path_length", "delta_p_request"), "request size", "request_size_vs_L"),
    ):
        fig, ax = plt.subplots(figsize=(8, 5))
        for label, group in request.groupby("label", sort=True):
            for metric in metrics:
                x = 1/group["L"] if "inverse" in name else group["L"]
                ax.errorbar(x, group[f"{metric}_mean"], yerr=group[f"{metric}_sem"], marker="o", label=f"{label} {metric}")
        ax.set_xlabel("1/L" if "inverse" in name else "L"); ax.set_ylabel(ylabel); ax.legend(fontsize=7); ax.grid(alpha=.25); fig.tight_layout()
        path=directory/f"{name}.png"; fig.savefig(path,dpi=160); plt.close(fig); outputs.append(path)
    fig, ax = plt.subplots(figsize=(8, 5))
    for label, group in request.loc[request["label"].isin(["C=1", "C=2"])].groupby("label", sort=True):
        ax.errorbar(group["L"], group["p_mid_std"], marker="o", label=label)
    ax.set_xlabel("L"); ax.set_ylabel("std(p_mid)"); ax.set_xscale("log"); ax.set_yscale("log")
    ax.legend(); ax.grid(alpha=.25); fig.tight_layout(); path=directory/"finite_std_p_mid_vs_L.png"; fig.savefig(path,dpi=160); plt.close(fig); outputs.append(path)
    for observable, filename in (("delta_P_max", "unbounded_delta_P_models"), ("transition_delta_p", "unbounded_transition_width_models")):
        fig, ax=plt.subplots(figsize=(8,5)); source = request if observable=="delta_P_max" else transition
        ycol = "delta_P_max_mean" if observable=="delta_P_max" else "delta_p_mean"
        data=source.loc[source["budget_mode"]=="UNBOUNDED"].sort_values("L"); ax.plot(data["L"],data[ycol],"o",label="means")
        fitset=ub_fits.loc[(ub_fits["observable"]==observable)&(ub_fits["L_min"]==8)]
        grid=np.linspace(data["L"].min(),data["L"].max(),300)
        for item in fitset.itertuples():
            prediction=pure_power(grid,item.b,item.exponent) if item.model=="A" else constant_power(grid,item.limit,item.b,item.exponent)
            ax.plot(grid,prediction,label=f"model {item.model}")
        ax.set_xlabel("L"); ax.set_ylabel(observable); ax.legend(); ax.grid(alpha=.25); fig.tight_layout(); path=directory/f"{filename}.png"; fig.savefig(path,dpi=160); plt.close(fig); outputs.append(path)
        fig, ax = plt.subplots(figsize=(8, 4))
        for item in fitset.itertuples():
            prediction=pure_power(data["L"].to_numpy(float),item.b,item.exponent) if item.model=="A" else constant_power(data["L"].to_numpy(float),item.limit,item.b,item.exponent)
            ax.plot(data["L"], data[ycol].to_numpy(float)-prediction, marker="o", label=f"model {item.model}")
        ax.axhline(0,color="black",linewidth=.8); ax.set_xlabel("L"); ax.set_ylabel("residual")
        ax.legend(); ax.grid(alpha=.25); fig.tight_layout(); path=directory/f"{filename}_residuals.png"; fig.savefig(path,dpi=160); plt.close(fig); outputs.append(path)
    if not ub_bootstrap.empty:
        fig,ax=plt.subplots(figsize=(8,5)); data=ub_bootstrap.loc[(ub_bootstrap["L_min"]==8)&ub_bootstrap["converged"],"limit"]
        ax.hist(data,bins=50); ax.set_xlabel("delta_P_infinity"); ax.set_ylabel("bootstrap count"); fig.tight_layout(); path=directory/"unbounded_delta_P_infinity_bootstrap.png"; fig.savefig(path,dpi=160); plt.close(fig); outputs.append(path)
    for name, frame, x, y in (("hyperscaling_vs_Lmin", _scaling_comparisons(fits), "L_min", "exponent"), ("local_effective_exponents", effective, "L_geometric_mean", "local_effective_exponent")):
        fig,ax=plt.subplots(figsize=(8,5))
        for key,group in frame.groupby([c for c in ("condition_label","observable") if c in frame.columns],sort=True): ax.plot(group[x],group[y],marker="o",label=str(key))
        ax.set_xlabel(x);ax.set_ylabel(y);ax.legend(fontsize=6);ax.grid(alpha=.25);fig.tight_layout();path=directory/f"{name}.png";fig.savefig(path,dpi=160);plt.close(fig);outputs.append(path)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze"); analyze.add_argument("manifests", nargs="+", type=Path); analyze.add_argument("--output", type=Path, required=True); analyze.add_argument("--bootstrap-samples", type=int, default=BOOTSTRAP_SAMPLES)
    audit = sub.add_parser("stop-audit"); audit.add_argument("main_manifest", type=Path); audit.add_argument("audit_manifest", type=Path); audit.add_argument("--output", type=Path, required=True)
    args=parser.parse_args()
    if args.command=="analyze": analyze_manifests(args.manifests,args.output,bootstrap_samples=args.bootstrap_samples)
    else: audit_stops(args.main_manifest,args.audit_manifest,args.output)


if __name__ == "__main__":
    main()
