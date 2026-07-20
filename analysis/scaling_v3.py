"""Finite-size correction analysis for the completed scaling-v2 data.

This command reads existing aggregated/run-level products only.  It never
regenerates or edits simulation data below ``app/out``; all v3 products are
written to a separate output directory.
"""

from __future__ import annotations

import argparse
import math
import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "spp-matplotlib-cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from analysis.correction_fitting import (
    OMEGA_FIXED_VALUES, corrected_power, corrected_shift, fit_bounded_multistart,
    logarithmic_limit, logarithmic_zero, power_model_fits, simple_power,
)
from analysis.model_fitting import constant_power, pure_power
from analysis.universality_fitting import fit_universality_models


L_MINS = (8, 12, 16, 24, 32, 48)
THEORY_BETA_OVER_NU = 5.0 / 48.0
THEORY_INVERSE_NU = 3.0 / 4.0
OBSERVABLES = {
    "P_before": ("P_before_mean", -1), "P_after": ("P_after_mean", -1),
    "S_before": ("S_before_mean", 1), "S_after": ("S_after_mean", 1),
    "std_p_mid": ("p_mid_std", -1),
    "delta_P_request": ("delta_P_max_mean", -1),
    "transition_delta_p": ("delta_p_mean", -1),
    "transition_delta_t_normalized": ("delta_t_normalized_mean", -1),
}
FINITE_OBSERVABLES = {key: OBSERVABLES[key] for key in
                      ("P_before", "P_after", "S_before", "S_after", "std_p_mid")}


def run_analysis(
    source: str | Path = "app/out/scaling-v2-analysis",
    output: str | Path = "app/out/scaling-v3-analysis",
    *, bootstrap_samples: int = 500, seed: int = 20260720,
) -> list[Path]:
    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    request = pd.read_csv(source / "request_event_summary.csv")
    transition = pd.read_csv(source / "transition_width_summary.csv")
    event_runs = pd.read_csv(source / "request_event_runs.csv")
    width_runs = pd.read_csv(source / "transition_width_runs.csv")
    combined = request.merge(
        transition[["condition_index", "delta_p_mean", "delta_t_normalized_mean"]],
        on="condition_index", validate="one_to_one",
    )
    combined["condition_label"] = combined.apply(
        lambda row: "UNBOUNDED" if row["budget_mode"] == "UNBOUNDED" else f"C={int(row['C'])}", axis=1
    )

    correction = finite_correction_fits(combined)
    correction.to_csv(output / "finite_correction_fits.csv", index=False)
    hyperscaling = hyperscaling_summary(correction)
    hyperscaling.to_csv(output / "hyperscaling_corrections.csv", index=False)
    universality = universality_fits(combined)
    universality.to_csv(output / "universality_model_fits.csv", index=False)
    shifts = shift_fits(combined)
    shifts.to_csv(output / "pseudocritical_shift_corrections.csv", index=False)
    unbounded, loo, extrapolation = unbounded_fits(combined)
    unbounded.to_csv(output / "unbounded_asymptotic_fits.csv", index=False)
    loo.to_csv(output / "unbounded_leave_one_size_out.csv", index=False)

    bootstrap = bootstrap_primary(
        event_runs, width_runs, correction, combined,
        samples=bootstrap_samples, seed=seed,
    )
    extrapolation = attach_prediction_intervals(extrapolation, bootstrap)
    extrapolation.to_csv(output / "unbounded_extrapolations.csv", index=False)
    size_assessment = additional_size_assessment(extrapolation)
    size_assessment.to_csv(output / "additional_size_assessment.csv", index=False)
    bootstrap.to_csv(output / "bootstrap_distributions.csv", index=False)
    bootstrap_summary = summarize_bootstrap(bootstrap)
    bootstrap_summary.to_csv(output / "bootstrap_intervals.csv", index=False)
    runtimes = runtime_forecasts(source.parent / "scaling-v2-main", samples=bootstrap_samples, seed=seed)
    runtimes.to_csv(output / "runtime_forecasts.csv", index=False)
    stability = fit_stability_summary(correction, universality, shifts, unbounded)
    stability.to_csv(output / "fit_stability_summary.csv", index=False)
    figures = create_figures(combined, correction, universality, shifts, unbounded, loo,
                             extrapolation, bootstrap, runtimes, output / "figures")
    paths = [output / name for name in (
        "finite_correction_fits.csv", "universality_model_fits.csv",
        "hyperscaling_corrections.csv",
        "pseudocritical_shift_corrections.csv", "unbounded_asymptotic_fits.csv",
        "unbounded_leave_one_size_out.csv", "unbounded_extrapolations.csv",
        "bootstrap_distributions.csv", "bootstrap_intervals.csv", "runtime_forecasts.csv",
        "fit_stability_summary.csv",
        "additional_size_assessment.csv",
    )] + figures
    print(f"scaling-v3: conditions={len(combined)}, bootstrap_samples={bootstrap_samples}, outputs={len(paths)}")
    return paths


def finite_correction_fits(combined: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for label in ("C=1", "C=2"):
        group = combined.loc[combined["condition_label"] == label].sort_values("L")
        for observable, (column, sign) in FINITE_OBSERVABLES.items():
            for L_min in L_MINS:
                subset = group.loc[(group["L"] >= L_min) & (group[column] > 0)]
                if len(subset) < 3:
                    continue
                fixed_omegas = OMEGA_FIXED_VALUES if L_min == 8 else ()
                for fit in power_model_fits(subset["L"], subset[column], fixed_omegas=fixed_omegas):
                    rows.append(_fit_row(fit, condition_label=label, observable=observable,
                                         source_column=column, exponent_sign=sign, L_min=L_min,
                                         used_L=_used_l(subset)))
                if label == "C=1" and observable in ("P_before", "P_after"):
                    for fit in power_model_fits(subset["L"], subset[column], fixed_exponent=-THEORY_BETA_OVER_NU,
                                                fixed_omegas=fixed_omegas, include_free_omega=False):
                        rows.append(_fit_row(fit, condition_label=label, observable=observable,
                                             source_column=column, exponent_sign=sign, L_min=L_min,
                                             used_L=_used_l(subset), theory_fixed=True))
    return pd.DataFrame(rows)


def universality_fits(combined: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for observable, (column, sign) in FINITE_OBSERVABLES.items():
        for L_min in (8, 16, 32):
            c1 = combined.loc[(combined["condition_label"] == "C=1") & (combined["L"] >= L_min)].sort_values("L")
            c2 = combined.loc[(combined["condition_label"] == "C=2") & (combined["L"] >= L_min)].sort_values("L")
            if len(c1) != len(c2) or len(c1) < 4 or np.any(c1[column] <= 0) or np.any(c2[column] <= 0):
                continue
            fixed_omegas = OMEGA_FIXED_VALUES if L_min == 8 else ()
            for fit in fit_universality_models(c1["L"].to_numpy(float), c1[column].to_numpy(float),
                                               c2["L"].to_numpy(float), c2[column].to_numpy(float),
                                               fixed_omegas=fixed_omegas):
                row = _fit_row(fit, observable=observable, source_column=column,
                               exponent_sign=sign, L_min=L_min, used_L=_used_l(c1))
                for key in ("exponent", "exponent_c1", "exponent_c2"):
                    if key in row and np.isfinite(row[key]):
                        row[f"scaling_{key}"] = sign * row[key]
                rows.append(row)
    return pd.DataFrame(rows)


def hyperscaling_summary(corrections: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label in ("C=1", "C=2"):
        for L_min in L_MINS:
            for endpoint in ("before", "after"):
                for selection in ("simple", "best_admissible"):
                    chosen = []
                    for observable in (f"P_{endpoint}", f"S_{endpoint}"):
                        candidates = corrections.loc[(corrections["condition_label"] == label) &
                                                     (corrections["observable"] == observable) &
                                                     (corrections["L_min"] == L_min) & corrections["converged"] &
                                                     (~corrections["theory_fixed"])]
                        if selection == "simple":
                            candidates = candidates.loc[candidates["model"] == "simple_power"]
                        else:
                            candidates = candidates.loc[candidates["admissible"]].sort_values("aicc")
                        if candidates.empty:
                            break
                        chosen.append(candidates.iloc[0])
                    if len(chosen) == 2:
                        value = 2*float(chosen[0]["scaling_exponent"])+float(chosen[1]["scaling_exponent"])
                        rows.append({"condition_label": label, "endpoint": endpoint, "L_min": L_min,
                                     "selection": selection, "P_model": chosen[0]["model"],
                                     "S_model": chosen[1]["model"], "hyperscaling_sum": value,
                                     "dimension_reference": 2.0, "difference_from_two": value-2.0})
    return pd.DataFrame(rows)


def shift_fits(combined: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for label in ("C=1", "C=2"):
        group = combined.loc[combined["condition_label"] == label].sort_values("L")
        for L_min in L_MINS:
            subset = group.loc[group["L"] >= L_min]
            if len(subset) < 4:
                continue
            x, y = subset["L"].to_numpy(float), subset["p_mid_mean"].to_numpy(float)
            specifications: list[tuple[str, object, tuple, tuple, tuple]] = []
            if label == "C=1":
                specifications.extend([
                    ("shift_pc_0.5_free_invnu", lambda L, a, q: .5 + a * L ** -q,
                     ((a, q) for a in (-.5, .5) for q in (.4, .75, 1.2)), ((-10, .05), (10, 4)), ("amplitude", "inverse_nu")),
                    ("shift_pc_0.5_invnu_0.75", lambda L, a: .5 + a * L ** -THEORY_INVERSE_NU,
                     ((-.5,), (.5,)), ((-10,), (10,)), ("amplitude",)),
                ])
            specifications.append(("shift_free_pc", lambda L, pc, a, q: pc + a * L ** -q,
                                   ((pc, a, q) for pc in (.45, .5, .55) for a in (-.5, .5) for q in (.4, .75, 1.2)),
                                   ((0, -10, .05), (1, 10, 4)), ("pc", "amplitude", "inverse_nu")))
            for model, function, starts, bounds, names in specifications:
                fit = fit_bounded_multistart(function, x, y, starts, bounds, names, model=model)
                if model.startswith("shift_pc_0.5"):
                    fit["pc"] = 0.5
                if model.endswith("invnu_0.75"):
                    fit["inverse_nu"] = THEORY_INVERSE_NU
                rows.append(_fit_row(fit, condition_label=label, observable="p_mid",
                                     source_column="p_mid_mean", exponent_sign=1, L_min=L_min,
                                     used_L=_used_l(subset), theory_fixed="invnu_0.75" in model))
            # The fully corrected shift is intentionally only accepted when AICc is defined.
            if L_min != 8:
                continue
            for omega in OMEGA_FIXED_VALUES:
                if label == "C=1":
                    function = lambda L, a, q, b, w=omega: corrected_shift(L, .5, a, q, b, w)
                    fit = fit_bounded_multistart(
                        function, x, y,
                        ((a, q, b) for a in (-.5, .5) for q in (.5, .75, 1) for b in (-1, 1)),
                        ((-10, .05, -20), (10, 4, 20)),
                        ("amplitude", "inverse_nu", "correction"),
                        model=f"corrected_shift_pc_0.5_omega_{omega:g}",
                    )
                    fit.update(pc=.5, omega=omega)
                else:
                    function = lambda L, pc, a, q, b, w=omega: corrected_shift(L, pc, a, q, b, w)
                    fit = fit_bounded_multistart(
                        function, x, y,
                        ((pc, a, q, b) for pc in (.45, .5, .55) for a in (-.5, .5)
                         for q in (.5, .75, 1) for b in (-1, 1)),
                        ((0, -10, .05, -20), (1, 10, 4, 20)),
                        ("pc", "amplitude", "inverse_nu", "correction"),
                        model=f"corrected_shift_free_pc_omega_{omega:g}",
                    )
                    fit["omega"] = omega
                rows.append(_fit_row(fit, condition_label=label, observable="p_mid",
                                     source_column="p_mid_mean", exponent_sign=1, L_min=L_min,
                                     used_L=_used_l(subset)))
            for fixed_pc in ((0.5,) if label == "C=1" else ()) + (None,):
                if fixed_pc is None:
                    function = corrected_shift
                    names = ("pc", "amplitude", "inverse_nu", "correction", "omega")
                    starts = ((pc, a, q, b, w) for pc in (.45, .5, .55) for a in (-.5, .5)
                              for q in (.5, .75, 1) for b in (-1, 1) for w in (.5, 1, 2))
                    bounds = ((0, -10, .05, -20, .05), (1, 10, 4, 20, 4))
                    model = "corrected_shift_free_pc_omega"
                else:
                    function = lambda L, a, q, b, w, pc=fixed_pc: corrected_shift(L, pc, a, q, b, w)
                    names = ("amplitude", "inverse_nu", "correction", "omega")
                    starts = ((a, q, b, w) for a in (-.5, .5) for q in (.5, .75, 1)
                              for b in (-1, 1) for w in (.5, 1, 2))
                    bounds = ((-10, .05, -20, .05), (10, 4, 20, 4))
                    model = "corrected_shift_pc_0.5_free_omega"
                fit = fit_bounded_multistart(function, x, y, starts, bounds, names, model=model)
                if fixed_pc is not None:
                    fit["pc"] = fixed_pc
                rows.append(_fit_row(fit, condition_label=label, observable="p_mid",
                                     source_column="p_mid_mean", exponent_sign=1, L_min=L_min,
                                     used_L=_used_l(subset)))
    return pd.DataFrame(rows)


def unbounded_fits(combined: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ub = combined.loc[combined["condition_label"] == "UNBOUNDED"].sort_values("L")
    rows, loo_rows, predictions = [], [], []
    specs = {
        "zero_power": (pure_power, tuple((1, q) for q in (.05, .2, .5, 1, 2)), ((1e-12, .001), (10, 5)), ("amplitude", "decay_exponent")),
        "finite_power": (constant_power, tuple((limit, 1, q) for limit in (0, .1, .3) for q in (.05, .2, .5, 1)), ((0, 1e-12, .001), (1, 10, 5)), ("limit", "amplitude", "decay_exponent")),
        "zero_log": (logarithmic_zero, tuple((1, q) for q in (.1, .5, 1, 2, 4)), ((1e-12, .001), (10, 10)), ("amplitude", "decay_exponent")),
        "finite_log": (logarithmic_limit, tuple((limit, 1, q) for limit in (0, .1, .3) for q in (.1, .5, 1, 2)), ((0, 1e-12, .001), (1, 10, 10)), ("limit", "amplitude", "decay_exponent")),
    }
    for observable, column in (("delta_P_request", "delta_P_max_mean"), ("transition_delta_p", "delta_p_mean")):
        for L_min in (8, 16, 32):
            subset = ub.loc[(ub["L"] >= L_min) & (ub[column] > 0)]
            for model, (function, starts, bounds, names) in specs.items():
                fit = fit_bounded_multistart(function, subset["L"], subset[column], starts, bounds, names, model=model)
                rows.append(_fit_row(fit, condition_label="UNBOUNDED", observable=observable,
                                     source_column=column, exponent_sign=1, L_min=L_min, used_L=_used_l(subset)))
        full = ub.loc[ub[column] > 0]
        for omitted in full["L"]:
            subset = full.loc[full["L"] != omitted]
            for model, (function, starts, bounds, names) in specs.items():
                fit = fit_bounded_multistart(function, subset["L"], subset[column], starts, bounds, names, model=model)
                prediction = function(np.array([omitted], float), *[fit.get(name, np.nan) for name in names])[0] if fit["converged"] else np.nan
                loo_rows.append({**_fit_row(fit, observable=observable, source_column=column,
                                            exponent_sign=1, L_min=int(subset["L"].min()), used_L=_used_l(subset)),
                                 "omitted_L": int(omitted), "observed": float(full.loc[full["L"] == omitted, column].iloc[0]),
                                 "predicted": prediction, "prediction_error": prediction - float(full.loc[full["L"] == omitted, column].iloc[0])})
        for model, (function, starts, bounds, names) in specs.items():
            fit = fit_bounded_multistart(function, full["L"], full[column], starts, bounds, names, model=model)
            for target in (160, 192, 256):
                value = function(np.array([target], float), *[fit.get(name, np.nan) for name in names])[0] if fit["converged"] else np.nan
                predictions.append({"observable": observable, "model": model, "target_L": target,
                                    "prediction": value, "largest_observed_L": int(full["L"].max()),
                                    "extrapolation_ratio": target / float(full["L"].max()),
                                    "warning": "extrapolation beyond observed L; not an observation"})
    return pd.DataFrame(rows), pd.DataFrame(loo_rows), pd.DataFrame(predictions)


def bootstrap_primary(events: pd.DataFrame, widths: pd.DataFrame, corrections: pd.DataFrame,
                      combined: pd.DataFrame, *, samples: int, seed: int) -> pd.DataFrame:
    """Bootstrap primary L_min=8 fits from run-level observations.

    Finite-condition bootstrap fits deliberately call the same bounded,
    original-scale estimators as :func:`finite_correction_fits`.  Earlier v3
    output used log-log OLS for the bootstrap ``simple_power`` rows while the
    point estimate used original-scale nonlinear least squares.  Giving those
    different estimators the same label produced incomparable point estimates
    and confidence intervals.
    """
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    metrics = {"P_before": (events, "P_before", -1), "P_after": (events, "P_after", -1),
               "S_before": (events, "S_before", 1), "S_after": (events, "S_after", 1),
               "std_p_mid": (events, "p_mid", -1), "delta_P_request": (events, "delta_P_max", -1),
               "transition_delta_p": (widths, "delta_p", -1)}
    for label in ("C=1", "C=2", "UNBOUNDED"):
        for observable, (frame, column, sign) in metrics.items():
            source = frame.loc[((frame["budget_mode"] == "UNBOUNDED") if label == "UNBOUNDED" else
                                ((frame["budget_mode"] == "FINITE") & (frame["C"] == int(label[-1]))))]
            if source.empty:
                continue
            for sample in range(samples):
                values = []
                for L, group in source.groupby("L", sort=True):
                    draw = group.iloc[rng.integers(0, len(group), len(group))][column].to_numpy(float)
                    value = float(np.std(draw, ddof=1)) if observable == "std_p_mid" else float(np.nanmean(draw))
                    values.append((L, value))
                Ls, ys = map(np.asarray, zip(*values))
                if label == "UNBOUNDED" and observable in ("delta_P_request", "transition_delta_p"):
                    models = _bootstrap_ub_models(Ls, ys)
                elif label != "UNBOUNDED":
                    if observable in FINITE_OBSERVABLES:
                        omega = _selected_omega(corrections, label, observable)
                        fitted = power_model_fits(
                            Ls, ys, fixed_omegas=(omega,), include_free_omega=False
                        )
                        models = fitted[:2]
                    else:
                        # These observables retain the scaling-v2 log-log OLS
                        # point estimator rather than the v3 correction fitter.
                        models = [_quick_power_fit(Ls, ys)]
                else:
                    continue
                for fit in models:
                    exponent = fit.get("exponent", fit.get("decay_exponent", np.nan))
                    reported_exponent = exponent if label == "UNBOUNDED" else sign * exponent
                    rows.append({"sample": sample, "condition_label": label, "observable": observable,
                                 "source_column": column,
                                 "estimator": _bootstrap_estimator_name(label, observable),
                                 "L_min": int(np.min(Ls)), "used_L": ";".join(str(int(value)) for value in Ls),
                                 "bootstrap_seed": seed, "model": fit["model"],
                                 "converged": bool(fit["converged"]),
                                 "failure": fit.get("failure", ""), "exponent": reported_exponent,
                                 "limit": fit.get("limit", 0.0), "amplitude": fit.get("amplitude", np.nan),
                                 "omega": fit.get("omega", np.nan), "correction": fit.get("correction", np.nan),
                                 "boundary_solution": fit["boundary_solution"]})
    rows.extend(_bootstrap_joint_and_shift(events, samples=samples, rng=rng))
    return pd.DataFrame(rows)


def attach_prediction_intervals(predictions: pd.DataFrame, bootstrap: pd.DataFrame) -> pd.DataFrame:
    result = predictions.copy()
    result["prediction_ci95_low"] = np.nan
    result["prediction_ci95_high"] = np.nan
    for index, row in result.iterrows():
        samples = bootstrap.loc[(bootstrap["condition_label"] == "UNBOUNDED") &
                                (bootstrap["observable"] == row["observable"]) &
                                (bootstrap["model"] == row["model"])]
        if samples.empty:
            continue
        L = float(row["target_L"]); exponent = samples["exponent"].to_numpy(float)
        amplitude = samples["amplitude"].to_numpy(float); limit = samples["limit"].to_numpy(float)
        values = limit + amplitude * (np.log(L) ** -exponent if "log" in row["model"] else L ** -exponent)
        result.loc[index, ["prediction_ci95_low", "prediction_ci95_high"]] = np.percentile(values, [2.5, 97.5])
    return result


def additional_size_assessment(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (observable, target), group in predictions.groupby(["observable", "target_L"], sort=True):
        spread = float(group["prediction"].max()-group["prediction"].min())
        intervals = group[["prediction_ci95_low", "prediction_ci95_high"]].dropna()
        overlap = (float(intervals["prediction_ci95_low"].max()) <=
                   float(intervals["prediction_ci95_high"].min())) if not intervals.empty else True
        rows.append({"observable": observable, "target_L": target,
                     "between_model_prediction_range": spread,
                     "bootstrap_intervals_overlap": overlap,
                     "assessment": ("insufficient for model discrimination" if overlap else
                                    "potentially informative, subject to extrapolation error"),
                     "suggested_design": "UNBOUNDED at L with at least 50-100 runs; reassess before larger L"})
    return pd.DataFrame(rows)


def _bootstrap_joint_and_shift(events: pd.DataFrame, *, samples: int,
                               rng: np.random.Generator) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    finite = events.loc[(events["budget_mode"] == "FINITE") & events["C"].isin([1, 2])]
    for sample in range(samples):
        aggregates: dict[tuple[int, int], pd.DataFrame] = {}
        for C in (1, 2):
            pieces = []
            for L, group in finite.loc[finite["C"] == C].groupby("L", sort=True):
                pieces.append(group.iloc[rng.integers(0, len(group), len(group))].assign(_L=L))
            aggregates[(C, sample)] = pd.concat(pieces, ignore_index=True)
        for observable, column, sign in (("P_before", "P_before", -1), ("P_after", "P_after", -1),
                                          ("S_before", "S_before", 1), ("S_after", "S_after", 1),
                                          ("std_p_mid", "p_mid", -1)):
            series = []
            for C in (1, 2):
                grouped = aggregates[(C, sample)].groupby("_L")[column]
                values = grouped.std(ddof=1) if observable == "std_p_mid" else grouped.mean()
                series.append((values.index.to_numpy(float), values.to_numpy(float)))
            independent = [_quick_power_fit(*item)["exponent"] for item in series]
            log_L = np.log(np.concatenate([series[0][0], series[1][0]]))
            log_y = np.log(np.concatenate([series[0][1], series[1][1]]))
            indicator = np.concatenate([np.zeros(len(series[0][0])), np.ones(len(series[1][0]))])
            design = np.column_stack((np.ones(len(log_L)), indicator, log_L))
            shared = float(np.linalg.lstsq(design, log_y, rcond=None)[0][2])
            corrected = _quick_joint_corrected_exponent(series, omega=1.0)
            for model, exponent in (("U1_C1", independent[0]), ("U1_C2", independent[1]),
                                    ("U2_shared_exponent", shared),
                                    ("U3_shared_exponent_omega_fixed_1", corrected)):
                rows.append({"sample": sample, "condition_label": "C1+C2", "observable": observable,
                             "model": model, "exponent": sign * exponent, "limit": np.nan,
                             "amplitude": np.nan, "omega": np.nan, "correction": np.nan,
                             "boundary_solution": abs(exponent) > 4.999})
        for C in (1, 2):
            grouped = aggregates[(C, sample)].groupby("_L")["p_mid"].mean()
            L, y = grouped.index.to_numpy(float), grouped.to_numpy(float)
            pc_fixed = .5 if C == 1 else None
            q, pc = _quick_corrected_shift(L, y, omega=1.0, fixed_pc=pc_fixed)
            rows.append({"sample": sample, "condition_label": f"C={C}", "observable": "p_mid_shift",
                         "model": "corrected_shift_omega_fixed_1", "exponent": q, "limit": pc,
                         "amplitude": np.nan, "omega": 1.0, "correction": np.nan,
                         "boundary_solution": q < .0011 or q > 3.999})
    return rows


def _quick_joint_corrected_exponent(series: list[tuple[np.ndarray, np.ndarray]], omega: float) -> float:
    all_L = np.concatenate([item[0] for item in series])
    all_y = np.concatenate([item[1] for item in series])
    condition = np.concatenate([np.full(len(item[0]), index) for index, item in enumerate(series)])
    log_design = np.column_stack((np.ones(len(all_L)), condition, np.log(all_L)))
    simple = float(np.linalg.lstsq(log_design, np.log(all_y), rcond=None)[0][-1])
    def rss(exponent: float) -> float:
        total = 0.0
        for L, y in series:
            design = np.column_stack((L**exponent, L**(exponent-omega)))
            coefficients = np.linalg.lstsq(design, y, rcond=None)[0]
            prediction = design @ coefficients
            correction = coefficients[1]/coefficients[0] if coefficients[0] else np.inf
            invalid = coefficients[0] <= 0 or abs(correction) > 20 or np.any(prediction <= 0)
            total += float(np.sum((y-prediction)**2) + (1e6 if invalid else 0))
        return total
    lower, upper = max(-5.0, simple-.75), min(5.0, simple+.75)
    grid = np.linspace(lower, upper, 121); best = int(np.argmin([rss(value) for value in grid]))
    return float(minimize_scalar(rss, bounds=(grid[max(0,best-1)], grid[min(120,best+1)]), method="bounded").x)


def _quick_corrected_shift(L: np.ndarray, y: np.ndarray, *, omega: float,
                           fixed_pc: float | None) -> tuple[float, float]:
    def solve(q: float) -> tuple[float, np.ndarray]:
        columns = [L**-q, L**(-q-omega)]
        if fixed_pc is None:
            design = np.column_stack((np.ones(len(L)), *columns)); target = y
        else:
            design = np.column_stack(columns); target = y-fixed_pc
        coefficients = np.linalg.lstsq(design, target, rcond=None)[0]
        return float(np.sum((target-design @ coefficients)**2)), coefficients
    optimized = minimize_scalar(lambda q: solve(q)[0], bounds=(.001, 4), method="bounded")
    _, coefficients = solve(float(optimized.x))
    pc = float(coefficients[0]) if fixed_pc is None else fixed_pc
    return float(optimized.x), pc


def _selected_omega(corrections: pd.DataFrame, label: str, observable: str) -> float:
    candidates = corrections.loc[(corrections["condition_label"] == label) &
                                 (corrections["observable"] == observable) &
                                 (corrections["L_min"] == 8) & corrections["converged"] &
                                 corrections["model"].str.startswith("corrected_power_omega_")]
    return float(candidates.sort_values("aicc").iloc[0]["omega"]) if not candidates.empty else 1.0


def _quick_power_fit(L: np.ndarray, y: np.ndarray) -> dict[str, object]:
    exponent, log_amplitude = np.polyfit(np.log(L), np.log(y), 1)
    return {"model": "simple_power", "converged": True, "exponent": exponent,
            "boundary_solution": False, "amplitude": math.exp(log_amplitude)}


def _bootstrap_ub_models(L: np.ndarray, y: np.ndarray) -> list[dict[str, object]]:
    log_slope, log_amplitude = np.polyfit(np.log(L), np.log(y), 1)
    loglog_slope, loglog_amplitude = np.polyfit(np.log(np.log(L)), np.log(y), 1)
    output = [
        {"model": "zero_power", "converged": True, "amplitude": math.exp(log_amplitude),
         "decay_exponent": -log_slope, "limit": 0.0, "boundary_solution": False},
        {"model": "zero_log", "converged": True, "amplitude": math.exp(loglog_amplitude),
         "decay_exponent": -loglog_slope, "limit": 0.0, "boundary_solution": False},
    ]
    for model, basis in (("finite_power", lambda q: L**-q),
                         ("finite_log", lambda q: np.log(L)**-q)):
        def solve(q: float) -> tuple[float, np.ndarray]:
            design = np.column_stack((np.ones(len(L)), basis(q)))
            coefficients = np.linalg.lstsq(design, y, rcond=None)[0]
            penalty = 1e6 * min(coefficients[0], 0) ** 2
            return float(np.sum((y-design @ coefficients)**2) + penalty), coefficients
        optimized = minimize_scalar(lambda q: solve(q)[0], bounds=(.001, 10), method="bounded")
        _, coefficients = solve(float(optimized.x))
        output.append({"model": model, "converged": optimized.success,
                       "limit": max(float(coefficients[0]), 0.0), "amplitude": float(coefficients[1]),
                       "decay_exponent": float(optimized.x),
                       "boundary_solution": float(coefficients[0]) <= 1e-8})
    return output


def summarize_bootstrap(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in frame.groupby(["condition_label", "observable", "model"], sort=True):
        converged = (group["converged"].astype(bool) if "converged" in group
                     else pd.Series(True, index=group.index))
        for parameter in ("exponent", "limit"):
            values = group.loc[converged, parameter].dropna().to_numpy(float)
            if not len(values):
                continue
            rows.append({"condition_label": keys[0], "observable": keys[1], "model": keys[2],
                         "parameter": parameter, "samples": len(values),
                         "requested_samples": int(group["sample"].nunique()) if "sample" in group else len(group),
                         "fit_failures": int((~converged).sum()), "mean": np.mean(values),
                         "median": np.median(values), "ci95_low": np.percentile(values, 2.5),
                         "ci95_high": np.percentile(values, 97.5),
                         "boundary_frequency": float(group["boundary_solution"].mean())})
    return pd.DataFrame(rows)


def _bootstrap_estimator_name(condition_label: str, observable: str) -> str:
    if condition_label == "UNBOUNDED":
        return "legacy_unbounded_profile_fit"
    if observable in FINITE_OBSERVABLES:
        return "bounded_nonlinear_least_squares_original_scale"
    return "log_log_ordinary_least_squares"


def runtime_forecasts(main_directory: Path, *, samples: int, seed: int) -> pd.DataFrame:
    manifest = pd.read_csv(main_directory / "manifest.csv")
    raw: dict[str, dict[int, np.ndarray]] = {}
    for item in manifest.itertuples(index=False):
        label = "UNBOUNDED" if item.budget_mode == "UNBOUNDED" else f"C={item.C}"
        summary = pd.read_csv(main_directory / Path(item.result_path).parent / "run_summary.csv")
        raw.setdefault(label, {})[int(item.L)] = summary["elapsed_milliseconds"].to_numpy(float) / 1000.0
    rng, rows = np.random.default_rng(seed), []
    for label, by_size in raw.items():
        sizes = np.array(sorted(by_size), float)
        means = np.array([np.mean(by_size[int(L)]) for L in sizes])
        exponent = math.log(means[1] / means[0]) / math.log(sizes[1] / sizes[0])
        amplitude = means[0] / sizes[0] ** exponent
        boot = []
        for _ in range(samples):
            sampled = np.array([np.mean(v[rng.integers(0, len(v), len(v))]) for _, v in sorted(by_size.items())])
            q = math.log(sampled[1] / sampled[0]) / math.log(sizes[1] / sizes[0])
            boot.append((sampled[0] / sizes[0] ** q, q))
        for target in (160, 192, 256):
            predictions = np.array([a * target ** q for a, q in boot])
            for runs in (1, 20, 50, 100):
                rows.append({"condition_label": label, "target_L": target, "runs": runs,
                             "seconds": amplitude * target ** exponent * runs,
                             "ci95_low_seconds": np.percentile(predictions, 2.5) * runs,
                             "ci95_high_seconds": np.percentile(predictions, 97.5) * runs,
                             "runtime_exponent": exponent, "source_L": "96;128",
                             "warning": "two-size empirical extrapolation; uncertainty excludes machine/systematic scaling changes"})
    return pd.DataFrame(rows)


def fit_stability_summary(*tables: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for table in tables:
        if table.empty:
            continue
        for model, group in table.groupby("model", sort=True):
            rows.append({"model": model, "fit_count": len(group), "converged_count": int(group["converged"].sum()),
                         "admissible_count": int(group["admissible"].sum()),
                         "boundary_count": int(group["boundary_solution"].sum()),
                         "covariance_failure_count": int((~group["covariance_ok"]).sum()),
                         "failure_examples": "; ".join(group.loc[group["failure"].astype(str) != "", "failure"].astype(str).unique()[:3])})
    return pd.DataFrame(rows)


def create_figures(combined: pd.DataFrame, correction: pd.DataFrame, universality: pd.DataFrame,
                   shifts: pd.DataFrame, unbounded: pd.DataFrame, loo: pd.DataFrame,
                   extrapolation: pd.DataFrame, bootstrap: pd.DataFrame,
                   runtimes: pd.DataFrame, directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    # L_min dependence.
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    for ax, observable in zip(axes.flat, ("P_before", "P_after", "S_before", "S_after")):
        data = correction.loc[(correction["model"] == "simple_power") & (correction["observable"] == observable) & correction["converged"]]
        for label, group in data.groupby("condition_label"):
            ax.plot(group["L_min"], group["scaling_exponent"], marker="o", label=label)
        ax.set(title=observable, xlabel=r"minimum size $L_{min}$", ylabel="effective exponent ratio")
        ax.legend()
    paths.append(_save(fig, directory / "exponent_lmin_dependence.png"))
    # Simple vs corrected P/S.
    for observable in ("P_before", "S_before"):
        column = OBSERVABLES[observable][0]
        fig, ax = plt.subplots(figsize=(7.2, 5.0), constrained_layout=True)
        for label in ("C=1", "C=2"):
            data = combined.loc[combined["condition_label"] == label].sort_values("L")
            ax.scatter(data["L"], data[column], label=f"{label} data")
            candidates = correction.loc[(correction["condition_label"] == label) & (correction["observable"] == observable) &
                                        (correction["L_min"] == 8) & correction["converged"]].sort_values("aicc")
            for _, fit in candidates.head(2).iterrows():
                grid = np.geomspace(8, 128, 200)
                if fit["model"] == "simple_power": pred = simple_power(grid, fit["amplitude"], fit["exponent"])
                elif "omega" in fit["model"]: pred = corrected_power(grid, fit["amplitude"], fit["exponent"], fit["correction"], fit["omega"])
                else: continue
                ax.plot(grid, pred, label=f"{label} {fit['model']}")
        ax.set(xscale="log", yscale="log", xlabel="linear size L", ylabel=observable,
               title=f"Simple and correction-to-scaling fits: {observable}")
        ax.legend(fontsize=7)
        paths.append(_save(fig, directory / f"simple_vs_corrected_{observable}.png"))
    # Theory-fixed C=1 residuals.
    fig, ax = plt.subplots(figsize=(7.2, 4.8), constrained_layout=True)
    for observable in ("P_before", "P_after"):
        row = correction.loc[(correction["condition_label"] == "C=1") & (correction["observable"] == observable) &
                             (correction["L_min"] == 8) & correction["theory_fixed"] & correction["converged"]].sort_values("aicc").iloc[0]
        data = combined.loc[combined["condition_label"] == "C=1"].sort_values("L")
        pred = simple_power(data["L"].to_numpy(float), row["amplitude"], -THEORY_BETA_OVER_NU) if row["model"].startswith("simple") else corrected_power(data["L"].to_numpy(float), row["amplitude"], -THEORY_BETA_OVER_NU, row["correction"], row["omega"])
        ax.axhline(0, color="black", linewidth=.8); ax.plot(data["L"], data[OBSERVABLES[observable][0]] - pred, marker="o", label=observable)
    ax.set(xlabel="linear size L", ylabel="observed - fitted P", title=r"C=1 residuals with $\beta/\nu=5/48$")
    ax.legend(); paths.append(_save(fig, directory / "c1_theory_fixed_residuals.png"))
    # Shared universality exponent.
    fig, ax = plt.subplots(figsize=(7.2, 4.8), constrained_layout=True)
    data = universality.loc[(universality["observable"] == "P_before") & universality["converged"]]
    for model, group in data.groupby("model"):
        column = "scaling_exponent" if "scaling_exponent" in group else "scaling_exponent_c1"
        if column in group: ax.plot(group["L_min"], group[column], marker="o", label=model)
    ax.axhline(THEORY_BETA_OVER_NU, color="black", linestyle="--", label="5/48")
    ax.set(xlabel=r"minimum size $L_{min}$", ylabel=r"$\beta/\nu$", title="C=1/C=2 joint P_before fits")
    ax.legend(fontsize=7); paths.append(_save(fig, directory / "c1_c2_shared_exponent.png"))
    # Residuals for the three universality hypotheses at L_min=8.
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), constrained_layout=True, sharey=True)
    joint = universality.loc[(universality["observable"] == "P_before") &
                            (universality["L_min"] == 8) &
                            universality["model"].isin(["U1_independent", "U2_shared_exponent",
                                                       "U3_shared_exponent_omega"]) & universality["converged"]]
    for ax, (_, fit) in zip(axes, joint.iterrows()):
        for label, suffix in (("C=1", "c1"), ("C=2", "c2")):
            observed = combined.loc[combined["condition_label"] == label].sort_values("L")
            L = observed["L"].to_numpy(float)
            if fit["model"] == "U1_independent":
                prediction = corrected_power(L, fit[f"amplitude_{suffix}"], fit[f"exponent_{suffix}"],
                                             fit[f"correction_{suffix}"], fit[f"omega_{suffix}"])
            elif fit["model"] == "U2_shared_exponent":
                prediction = corrected_power(L, fit[f"amplitude_{suffix}"], fit["exponent"],
                                             fit[f"correction_{suffix}"], fit[f"omega_{suffix}"])
            else:
                prediction = corrected_power(L, fit[f"amplitude_{suffix}"], fit["exponent"],
                                             fit[f"correction_{suffix}"], fit["omega"])
            ax.plot(L, observed["P_before_mean"]-prediction, marker="o", label=label)
        ax.axhline(0, color="black", linewidth=.8)
        ax.set(title=fit["model"], xlabel="linear size L")
    axes[0].set_ylabel("observed - fitted P_before")
    axes[-1].legend(); paths.append(_save(fig, directory / "universality_P_before_residuals.png"))
    # Shift correction comparison.
    fig, ax = plt.subplots(figsize=(7.2, 5), constrained_layout=True)
    for label in ("C=1", "C=2"):
        data = combined.loc[combined["condition_label"] == label].sort_values("L")
        ax.plot(data["L"], data["p_mid_mean"], marker="o", label=f"{label} observed")
        candidates = shifts.loc[(shifts["condition_label"] == label) & (shifts["L_min"] == 8) & shifts["converged"]].sort_values("aicc")
        grid = np.geomspace(8, 128, 200)
        for _, fit in candidates.head(2).iterrows():
            if fit["model"] == "shift_pc_0.5_invnu_0.75":
                pred = .5 + fit["amplitude"]*grid**-THEORY_INVERSE_NU
            elif fit["model"] == "shift_pc_0.5_free_invnu":
                pred = .5 + fit["amplitude"]*grid**-fit["inverse_nu"]
            elif fit["model"] == "shift_free_pc":
                pred = fit["pc"] + fit["amplitude"]*grid**-fit["inverse_nu"]
            else:
                pred = corrected_shift(grid, fit["pc"], fit["amplitude"], fit["inverse_nu"],
                                       fit["correction"], fit["omega"])
            ax.plot(grid, pred, linestyle="--", label=f"{label} {fit['model']}")
    ax.axhline(.5, color="black", linestyle="--", label=r"$p_c=0.5$")
    ax.set(xlabel="linear size L", ylabel="mean request-event midpoint p", title="Pseudocritical shift and finite-size corrections")
    ax.legend(); paths.append(_save(fig, directory / "pseudocritical_shift_corrections.png"))
    # UB models and extrapolations.
    fig, ax = plt.subplots(figsize=(7.2, 5), constrained_layout=True)
    data = combined.loc[combined["condition_label"] == "UNBOUNDED"].sort_values("L")
    ax.scatter(data["L"], data["delta_P_max_mean"], color="black", label="observed request jump")
    for _, fit in unbounded.loc[(unbounded["observable"] == "delta_P_request") & (unbounded["L_min"] == 8) & unbounded["converged"]].iterrows():
        grid = np.geomspace(8, 256, 250); model = fit["model"]
        if model == "zero_power": pred = pure_power(grid, fit["amplitude"], fit["decay_exponent"])
        elif model == "finite_power": pred = constant_power(grid, fit["limit"], fit["amplitude"], fit["decay_exponent"])
        elif model == "zero_log": pred = logarithmic_zero(grid, fit["amplitude"], fit["decay_exponent"])
        else: pred = logarithmic_limit(grid, fit["limit"], fit["amplitude"], fit["decay_exponent"])
        ax.plot(grid, pred, label=model)
    ax.axvspan(128, 256, color="grey", alpha=.12, label="extrapolation")
    ax.set(xscale="log", xlabel="linear size L", ylabel="mean maximum request jump ΔP", title="UNBOUNDED asymptotic model comparison")
    ax.legend(fontsize=7); paths.append(_save(fig, directory / "unbounded_asymptotic_models.png"))
    # LOO.
    fig, ax = plt.subplots(figsize=(7.2, 5), constrained_layout=True)
    part = loo.loc[loo["observable"] == "delta_P_request"]
    for model, group in part.groupby("model"):
        ax.plot(group["omitted_L"], group["prediction_error"], marker="o", label=model)
    ax.axhline(0, color="black", linewidth=.8); ax.set(xlabel="omitted size L", ylabel="prediction error", title="UNBOUNDED leave-one-size-out diagnostics")
    ax.legend(fontsize=7); paths.append(_save(fig, directory / "unbounded_leave_one_size_out.png"))
    # Bootstrap.
    fig, ax = plt.subplots(figsize=(7.2, 5), constrained_layout=True)
    part = bootstrap.loc[(bootstrap["observable"] == "P_before") & bootstrap["condition_label"].isin(["C=1", "C=2"])]
    for (label, model), group in part.groupby(["condition_label", "model"]):
        ax.hist(group["exponent"], bins=30, alpha=.4, label=f"{label} {model}")
    ax.axvline(THEORY_BETA_OVER_NU, color="black", linestyle="--", label="5/48")
    ax.set(xlabel=r"bootstrap $\beta/\nu$", ylabel="frequency", title="Bootstrap distributions for P_before")
    ax.legend(fontsize=7); paths.append(_save(fig, directory / "bootstrap_exponent_distributions.png"))
    # Runtime.
    fig, ax = plt.subplots(figsize=(7.2, 5), constrained_layout=True)
    for label, group in runtimes.loc[runtimes["runs"] == 1].groupby("condition_label"):
        ax.plot(group["target_L"], group["seconds"], marker="o", label=label)
        ax.fill_between(group["target_L"], group["ci95_low_seconds"], group["ci95_high_seconds"], alpha=.2)
    ax.set(yscale="log", xlabel="projected linear size L", ylabel="seconds per run", title="Runtime projection from measured L=96 and 128")
    ax.legend(); paths.append(_save(fig, directory / "runtime_predictions.png"))
    return paths


def _fit_row(fit: dict[str, object], *, exponent_sign: int, **metadata: object) -> dict[str, object]:
    excluded = {"prediction", "residuals", "covariance"}
    row = {**metadata, **{key: value for key, value in fit.items() if key not in excluded}}
    row.setdefault("theory_fixed", False)
    exponent = row.get("exponent", np.nan)
    row["scaling_exponent"] = exponent_sign * exponent if np.isfinite(exponent) else np.nan
    return row


def _used_l(frame: pd.DataFrame) -> str:
    return ";".join(str(int(value)) for value in frame["L"])


def _save(figure: plt.Figure, path: Path) -> Path:
    figure.savefig(path, dpi=180); plt.close(figure); return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="app/out/scaling-v2-analysis")
    parser.add_argument("--output", default="app/out/scaling-v3-analysis")
    parser.add_argument("--bootstrap-samples", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260720)
    args = parser.parse_args()
    run_analysis(args.source, args.output, bootstrap_samples=args.bootstrap_samples, seed=args.seed)


if __name__ == "__main__":
    main()
