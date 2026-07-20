"""Audit scaling-v3 point/bootstrap estimator consistency without new runs.

The audit reads the frozen scaling-v2/v3 CSV products and writes only to a
separate directory.  It reproduces the legacy log-log bootstrap and compares
it with a bootstrap using the estimator associated with each reported point
estimate.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.correction_fitting import power_model_fits


BOOTSTRAP_SEED = 20260720
BOOTSTRAP_SAMPLES = 500
L_MIN = 8
METRICS = {
    "P_before": ("events", "P_before", -1, "nonlinear"),
    "P_after": ("events", "P_after", -1, "nonlinear"),
    "S_before": ("events", "S_before", 1, "nonlinear"),
    "S_after": ("events", "S_after", 1, "nonlinear"),
    "std_p_mid": ("events", "p_mid", -1, "nonlinear"),
    "transition_delta_p": ("widths", "delta_p", -1, "log_ols"),
    "delta_P_max": ("events", "delta_P_max", -1, "log_ols"),
}
# Preserve the insertion order used by the original scaling-v3 bootstrap.
LEGACY_ORDER = (
    "P_before", "P_after", "S_before", "S_after", "std_p_mid",
    "delta_P_max", "transition_delta_p",
)


def run_audit(
    source_v2: str | Path = "app/out/scaling-v2-analysis",
    source_v3: str | Path = "app/out/scaling-v3-analysis",
    output: str | Path = "app/out/scaling-v3-s-after-audit",
    *, samples: int = BOOTSTRAP_SAMPLES, seed: int = BOOTSTRAP_SEED,
) -> list[Path]:
    v2, v3, destination = Path(source_v2), Path(source_v3), Path(output)
    destination.mkdir(parents=True, exist_ok=True)
    events = pd.read_csv(v2 / "request_event_runs.csv")
    widths = pd.read_csv(v2 / "transition_width_runs.csv")
    correction = pd.read_csv(v3 / "finite_correction_fits.csv")
    scaling = pd.read_csv(v2 / "finite_scaling_fits.csv")
    old_intervals = pd.read_csv(v3 / "bootstrap_intervals.csv")

    distributions = audit_bootstrap_distributions(
        events, widths, samples=samples, seed=seed
    )
    consistency = estimator_consistency_table(
        events, widths, correction, scaling, old_intervals, distributions,
        samples=samples, seed=seed,
    )
    consistency_path = destination / "estimator_consistency_audit.csv"
    s_after_path = destination / "s_after_bootstrap_audit.csv"
    consistency.to_csv(consistency_path, index=False, encoding="utf-8")
    distributions.loc[
        (distributions["condition_label"] == "C=1")
        & (distributions["observable"] == "S_after")
    ].to_csv(s_after_path, index=False, encoding="utf-8")

    old_files = [
        v2 / "request_event_runs.csv", v2 / "transition_width_runs.csv",
        v2 / "request_event_summary.csv", v3 / "finite_correction_fits.csv",
        v3 / "bootstrap_distributions.csv", v3 / "bootstrap_intervals.csv",
    ]
    summary_path = destination / "audit_summary.md"
    summary_path.write_text(
        _summary_markdown(consistency, old_files, [consistency_path, s_after_path], samples, seed),
        encoding="utf-8",
    )
    return [consistency_path, s_after_path, summary_path]


def audit_bootstrap_distributions(
    events: pd.DataFrame, widths: pd.DataFrame, *, samples: int, seed: int,
) -> pd.DataFrame:
    """Reproduce legacy draws and fit both legacy and aligned estimators."""
    event_copy, width_copy = events.copy(deep=True), widths.copy(deep=True)
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    frames = {"events": events, "widths": widths}
    for condition_label, C in (("C=1", 1), ("C=2", 2)):
        for observable in LEGACY_ORDER:
            frame_name, column, sign, aligned_kind = METRICS[observable]
            source = frames[frame_name]
            source = source.loc[
                (source["budget_mode"] == "FINITE") & (source["C"] == C)
                & (source["L"] >= L_MIN)
            ]
            used_l = ";".join(str(int(value)) for value in sorted(source["L"].unique()))
            run_counts = ";".join(
                f"{int(L)}:{len(group)}" for L, group in source.groupby("L", sort=True)
            )
            for sample in range(samples):
                aggregates = []
                for L, group in source.groupby("L", sort=True):
                    draw = group.iloc[rng.integers(0, len(group), len(group))][column].to_numpy(float)
                    value = (float(np.std(draw, ddof=1)) if observable == "std_p_mid"
                             else float(np.nanmean(draw)))
                    aggregates.append((float(L), value))
                sizes, values = map(np.asarray, zip(*aggregates))
                legacy = _log_ols_fit(sizes, values, sign)
                aligned = (_nonlinear_fit(sizes, values, sign)
                           if aligned_kind == "nonlinear" else legacy.copy())
                rows.append({
                    "sample": sample, "condition_label": condition_label,
                    "observable": observable, "source_frame": frame_name,
                    "source_column": column, "L_min": L_MIN, "used_L": used_l,
                    "run_counts": run_counts, "bootstrap_seed": seed,
                    "legacy_estimator": "log_log_ordinary_least_squares",
                    "legacy_exponent": legacy["exponent"],
                    "legacy_converged": legacy["converged"],
                    "legacy_failure": legacy["failure"],
                    "aligned_estimator": _estimator_name(aligned_kind),
                    "aligned_exponent": aligned["exponent"],
                    "aligned_converged": aligned["converged"],
                    "aligned_failure": aligned["failure"],
                })
    assert events.equals(event_copy) and widths.equals(width_copy)
    return pd.DataFrame(rows)


def estimator_consistency_table(
    events: pd.DataFrame, widths: pd.DataFrame, correction: pd.DataFrame,
    scaling: pd.DataFrame, old_intervals: pd.DataFrame, distributions: pd.DataFrame,
    *, samples: int, seed: int,
) -> pd.DataFrame:
    rows = []
    frames = {"events": events, "widths": widths}
    for condition_label, C in (("C=1", 1), ("C=2", 2)):
        for observable, (frame_name, column, sign, estimator_kind) in METRICS.items():
            source = frames[frame_name].loc[
                (frames[frame_name]["budget_mode"] == "FINITE")
                & (frames[frame_name]["C"] == C) & (frames[frame_name]["L"] >= L_MIN)
            ]
            values = []
            for L, group in source.groupby("L", sort=True):
                aggregate = (float(group[column].std(ddof=1)) if observable == "std_p_mid"
                             else float(group[column].mean()))
                values.append((float(L), aggregate))
            sizes, aggregates = map(np.asarray, zip(*values))
            point = (_nonlinear_fit(sizes, aggregates, sign) if estimator_kind == "nonlinear"
                     else _log_ols_fit(sizes, aggregates, sign))
            reported = _reported_point(correction, scaling, condition_label, observable)
            boot = distributions.loc[
                (distributions["condition_label"] == condition_label)
                & (distributions["observable"] == observable)
            ]
            legacy = boot.loc[boot["legacy_converged"], "legacy_exponent"].to_numpy(float)
            aligned = boot.loc[boot["aligned_converged"], "aligned_exponent"].to_numpy(float)
            old_name = "delta_P_request" if observable == "delta_P_max" else observable
            old = old_intervals.loc[
                (old_intervals["condition_label"] == condition_label)
                & (old_intervals["observable"] == old_name)
                & (old_intervals["model"] == "simple_power")
                & (old_intervals["parameter"] == "exponent")
            ]
            old_low = float(old.iloc[0]["ci95_low"]) if len(old) else np.nan
            old_high = float(old.iloc[0]["ci95_high"]) if len(old) else np.nan
            low, high = np.percentile(aligned, [2.5, 97.5])
            rows.append({
                "condition_label": condition_label, "observable": observable,
                "source_frame": frame_name, "source_column": column,
                "point_estimator": _estimator_name(estimator_kind),
                "bootstrap_estimator_before": "log_log_ordinary_least_squares",
                "bootstrap_estimator_after": _estimator_name(estimator_kind),
                "model": "simple_power", "L_min": L_MIN,
                "used_L": ";".join(str(int(value)) for value in sizes),
                "run_counts": ";".join(
                    f"{int(L)}:{len(group)}" for L, group in source.groupby("L", sort=True)
                ),
                "point_estimate_reported": reported,
                "point_estimate_recomputed": point["exponent"],
                "old_bootstrap_mean": float(np.mean(legacy)),
                "old_bootstrap_median": float(np.median(legacy)),
                "old_ci95_low_recomputed": float(np.percentile(legacy, 2.5)),
                "old_ci95_high_recomputed": float(np.percentile(legacy, 97.5)),
                "old_ci95_low_csv": old_low, "old_ci95_high_csv": old_high,
                "point_in_old_ci": bool(old_low <= reported <= old_high),
                "aligned_bootstrap_mean": float(np.mean(aligned)),
                "aligned_bootstrap_median": float(np.median(aligned)),
                "aligned_ci95_low": float(low), "aligned_ci95_high": float(high),
                "point_in_aligned_ci": bool(low <= reported <= high),
                "bootstrap_samples_requested": samples,
                "aligned_fit_failures": int((~boot["aligned_converged"]).sum()),
                "bootstrap_seed": seed,
            })
    return pd.DataFrame(rows)


def _reported_point(
    correction: pd.DataFrame, scaling: pd.DataFrame, condition: str, observable: str,
) -> float:
    if observable in {"P_before", "P_after", "S_before", "S_after", "std_p_mid"}:
        rows = correction.loc[
            (correction["condition_label"] == condition)
            & (correction["observable"] == observable)
            & (correction["model"] == "simple_power") & (correction["L_min"] == L_MIN)
        ]
        return float(rows.iloc[0]["scaling_exponent"])
    scaling_name = "delta_P_max" if observable == "delta_P_max" else observable
    rows = scaling.loc[
        (scaling["condition_label"] == condition)
        & (scaling["observable"] == scaling_name) & (scaling["L_min"] == L_MIN)
    ]
    return float(rows.iloc[0]["exponent"])


def _nonlinear_fit(sizes: np.ndarray, values: np.ndarray, sign: int) -> dict[str, object]:
    fit = power_model_fits(sizes, values, fixed_omegas=(), include_free_omega=False)[0]
    exponent = fit.get("exponent", np.nan)
    return {"exponent": sign * exponent if np.isfinite(exponent) else np.nan,
            "converged": bool(fit["converged"]), "failure": fit.get("failure", "")}


def _log_ols_fit(sizes: np.ndarray, values: np.ndarray, sign: int) -> dict[str, object]:
    if np.any(values <= 0) or not np.all(np.isfinite(values)):
        return {"exponent": np.nan, "converged": False, "failure": "non-positive observation"}
    slope = float(np.polyfit(np.log(sizes), np.log(values), 1)[0])
    return {"exponent": sign * slope, "converged": True, "failure": ""}


def _estimator_name(kind: str) -> str:
    return ("bounded_nonlinear_least_squares_original_scale" if kind == "nonlinear"
            else "log_log_ordinary_least_squares")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _summary_markdown(
    audit: pd.DataFrame, old_files: list[Path], new_files: list[Path], samples: int, seed: int,
) -> str:
    s_after = audit.loc[(audit["condition_label"] == "C=1") & (audit["observable"] == "S_after")].iloc[0]
    outside_old = int((~audit["point_in_old_ci"]).sum())
    outside_new = int((~audit["point_in_aligned_ci"]).sum())
    lines = [
        "# scaling-v3 S_after estimator audit", "",
        f"- bootstrap samples: {samples}", f"- bootstrap seed: {seed}",
        "- resampling unit: runs independently within each L", "- L_min: 8", "",
        "## C=1 S_after", "",
        f"- point estimate (original-scale nonlinear least squares): {s_after.point_estimate_reported:.12f}",
        f"- legacy log-log bootstrap 95% CI: [{s_after.old_ci95_low_recomputed:.12f}, {s_after.old_ci95_high_recomputed:.12f}]",
        f"- aligned bootstrap mean / median: {s_after.aligned_bootstrap_mean:.12f} / {s_after.aligned_bootstrap_median:.12f}",
        f"- aligned bootstrap 95% CI: [{s_after.aligned_ci95_low:.12f}, {s_after.aligned_ci95_high:.12f}]",
        f"- aligned fit failures: {int(s_after.aligned_fit_failures)}", "",
        "## Classification", "",
        "Classification A: the point estimate and bootstrap shared a model label but minimized residuals on different scales. The simulation data are unchanged.",
        f"Across the 14 audited condition/observable pairs, point estimates outside the legacy/aligned intervals were {outside_old}/{outside_new}.", "",
        "## SHA-256 of frozen inputs", "",
    ]
    lines.extend(f"- `{path.as_posix()}`: `{_sha256(path)}`" for path in old_files)
    lines.extend(["", "## SHA-256 of new CSV products", ""])
    lines.extend(f"- `{path.as_posix()}`: `{_sha256(path)}`" for path in new_files)
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-v2", default="app/out/scaling-v2-analysis")
    parser.add_argument("--source-v3", default="app/out/scaling-v3-analysis")
    parser.add_argument("--output", default="app/out/scaling-v3-s-after-audit")
    parser.add_argument("--bootstrap-samples", type=int, default=BOOTSTRAP_SAMPLES)
    parser.add_argument("--seed", type=int, default=BOOTSTRAP_SEED)
    args = parser.parse_args()
    paths = run_audit(args.source_v2, args.source_v3, args.output,
                      samples=args.bootstrap_samples, seed=args.seed)
    print(f"scaling-v3 S_after audit: outputs={len(paths)}")


if __name__ == "__main__":
    main()
