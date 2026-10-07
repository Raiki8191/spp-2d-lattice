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

# Keep the historical v3 point-estimator specification separate from v4-v7.
# In particular, these starts and the fitter's default maxfev=5_000 must also
# be used for every v3 UNBOUNDED bootstrap sample.
UNBOUNDED_MODEL_SPECS = {
    "zero_power": (pure_power, tuple((1, q) for q in (.05, .2, .5, 1, 2)),
                   ((1e-12, .001), (10, 5)), ("amplitude", "decay_exponent")),
    "finite_power": (constant_power,
                     tuple((limit, 1, q) for limit in (0, .1, .3) for q in (.05, .2, .5, 1)),
                     ((0, 1e-12, .001), (1, 10, 5)), ("limit", "amplitude", "decay_exponent")),
    "zero_log": (logarithmic_zero, tuple((1, q) for q in (.1, .5, 1, 2, 4)),
                 ((1e-12, .001), (10, 10)), ("amplitude", "decay_exponent")),
    "finite_log": (logarithmic_limit,
                   tuple((limit, 1, q) for limit in (0, .1, .3) for q in (.1, .5, 1, 2)),
                   ((0, 1e-12, .001), (1, 10, 10)), ("limit", "amplitude", "decay_exponent")),
}


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
                fit = fit_corrected_shift_fixed_omega(x, y, label=label, omega=omega)
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



def fit_corrected_shift_fixed_omega(
    L: np.ndarray, y: np.ndarray, *, label: str, omega: float,
) -> dict[str, object]:
    """Use the point-estimator specification for fixed-omega shift fits."""
    if label == "C=1":
        function = lambda L, a, q, b: corrected_shift(L, .5, a, q, b, omega)
        fit = fit_bounded_multistart(
            function, L, y,
            ((a, q, b) for a in (-.5, .5) for q in (.5, .75, 1) for b in (-1, 1)),
            ((-10, .05, -20), (10, 4, 20)),
            ("amplitude", "inverse_nu", "correction"),
            model=f"corrected_shift_pc_0.5_omega_{omega:g}",
        )
        fit.update(pc=.5, omega=omega)
    elif label == "C=2":
        function = lambda L, pc, a, q, b: corrected_shift(L, pc, a, q, b, omega)
        fit = fit_bounded_multistart(
            function, L, y,
            ((pc, a, q, b) for pc in (.45, .5, .55) for a in (-.5, .5)
             for q in (.5, .75, 1) for b in (-1, 1)),
            ((0, -10, .05, -20), (1, 10, 4, 20)),
            ("pc", "amplitude", "inverse_nu", "correction"),
            model=f"corrected_shift_free_pc_omega_{omega:g}",
        )
        fit["omega"] = omega
    else:
        raise ValueError("fixed-omega finite shift requires C=1 or C=2")
    return fit

def fit_unbounded_models(L: np.ndarray, y: np.ndarray) -> list[dict[str, object]]:
    """Apply the unchanged v3 original-scale bounded multistart estimator."""
    return [
        fit_bounded_multistart(function, L, y, starts, bounds, names, model=model)
        for model, (function, starts, bounds, names) in UNBOUNDED_MODEL_SPECS.items()
    ]


def unbounded_fits(combined: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ub = combined.loc[combined["condition_label"] == "UNBOUNDED"].sort_values("L")
    rows, loo_rows, predictions = [], [], []
    for observable, column in (("delta_P_request", "delta_P_max_mean"), ("transition_delta_p", "delta_p_mean")):
        for L_min in (8, 16, 32):
            subset = ub.loc[(ub["L"] >= L_min) & (ub[column] > 0)]
            for fit in fit_unbounded_models(subset["L"], subset[column]):
                rows.append(_fit_row(fit, condition_label="UNBOUNDED", observable=observable,
                                     source_column=column, exponent_sign=1, L_min=L_min, used_L=_used_l(subset)))
        full = ub.loc[ub[column] > 0]
        for omitted in full["L"]:
            subset = full.loc[full["L"] != omitted]
            for fit in fit_unbounded_models(subset["L"], subset[column]):
                function, _, _, names = UNBOUNDED_MODEL_SPECS[fit["model"]]
                prediction = function(np.array([omitted], float), *[fit.get(name, np.nan) for name in names])[0] if fit["converged"] else np.nan
                loo_rows.append({**_fit_row(fit, observable=observable, source_column=column,
                                            exponent_sign=1, L_min=int(subset["L"].min()), used_L=_used_l(subset)),
                                 "omitted_L": int(omitted), "observed": float(full.loc[full["L"] == omitted, column].iloc[0]),
                                 "predicted": prediction, "prediction_error": prediction - float(full.loc[full["L"] == omitted, column].iloc[0])})
        for fit in fit_unbounded_models(full["L"], full[column]):
            model = fit["model"]
            function, _, _, names = UNBOUNDED_MODEL_SPECS[model]
            for target in (160, 192, 256):
                value = function(np.array([target], float), *[fit.get(name, np.nan) for name in names])[0] if fit["converged"] else np.nan
                predictions.append({"observable": observable, "model": model, "target_L": target,
                                    "prediction": value, "largest_observed_L": int(full["L"].max()),
                                    "extrapolation_ratio": target / float(full["L"].max()),
                                    "warning": "extrapolation beyond observed L; not an observation"})
    return pd.DataFrame(rows), pd.DataFrame(loo_rows), pd.DataFrame(predictions)


def bootstrap_primary(events: pd.DataFrame, widths: pd.DataFrame, corrections: pd.DataFrame,
                      combined: pd.DataFrame, *, samples: int, seed: int,
                      unbounded_only: bool = False,
                      finite_primary_only: bool = False) -> pd.DataFrame:
    """Bootstrap primary L_min=8 fits from run-level observations.

    Finite-condition bootstrap fits deliberately call the same bounded,
    original-scale estimators as :func:`finite_correction_fits`.  Earlier v3
    output used log-log OLS for the bootstrap ``simple_power`` rows while the
    point estimate used original-scale nonlinear least squares.  Giving those
    different estimators the same label produced incomparable point estimates
    and confidence intervals.  The UNBOUNDED branch likewise calls the exact
    estimator used by :func:`unbounded_fits`.

    ``unbounded_only`` skips finite-condition fits, but still consumes their
    original bootstrap draws in their original order.  It can therefore
    produce separate UNBOUNDED corrections without changing their samples or
    regenerating the already corrected finite-C products.
    finite_primary_only emits finite-condition fits with their unchanged draws,
    omitting UNBOUNDED and joint/shift fits for an affected-only correction.
    """
    if unbounded_only and finite_primary_only:
        raise ValueError("unbounded_only and finite_primary_only are mutually exclusive")
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    metrics = {"P_before": (events, "P_before", -1), "P_after": (events, "P_after", -1),
               "S_before": (events, "S_before", 1), "S_after": (events, "S_after", 1),
               "std_p_mid": (events, "p_mid", -1), "delta_P_request": (events, "delta_P_max", -1),
               "transition_delta_p": (widths, "delta_p", -1)}
    for label in ("C=1", "C=2", "UNBOUNDED"):
        if finite_primary_only and label == "UNBOUNDED":
            continue
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
                if unbounded_only and label != "UNBOUNDED":
                    continue
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
                    row = {"sample": sample, "condition_label": label, "observable": observable,
                                 "source_column": column,
                                 "estimator": _bootstrap_estimator_name(label, observable),
                                 "L_min": int(np.min(Ls)), "used_L": ";".join(str(int(value)) for value in Ls),
                                 "bootstrap_seed": seed, "model": fit["model"],
                                 "converged": bool(fit["converged"]),
                                 "failure": fit.get("failure", ""), "exponent": reported_exponent,
                                 "limit": fit.get("limit", 0.0), "amplitude": fit.get("amplitude", np.nan),
                                 "omega": fit.get("omega", np.nan), "correction": fit.get("correction", np.nan),
                                  "boundary_solution": fit["boundary_solution"]}
                    if label == "UNBOUNDED":
                        for diagnostic in (
                            "covariance_ok", "admissible", "rss", "aicc", "bic",
                            "start_count", "converged_start_count", "point_count", "parameter_count",
                            "max_parameter_correlation", "amplitude_standard_error",
                            "decay_exponent_standard_error", "limit_standard_error",
                        ):
                            row[diagnostic] = fit.get(diagnostic, np.nan)
                        row["zero_limit_boundary"] = (
                            fit["converged"] and fit["model"].startswith("finite_")
                            and fit.get("limit", np.inf) <= 1e-8
                        )
                    rows.append(row)
    if not (unbounded_only or finite_primary_only):
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
        if "converged" in samples:
            samples = samples.loc[samples["converged"].astype(bool)]
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
        aggregates: dict[int, pd.DataFrame] = {}
        for C in (1, 2):
            pieces = []
            for L, group in finite.loc[finite["C"] == C].groupby("L", sort=True):
                pieces.append(group.iloc[rng.integers(0, len(group), len(group))].assign(_L=L))
            aggregates[C] = pd.concat(pieces, ignore_index=True)
        rows.extend(fit_joint_shift_statistics(joint_shift_statistics(aggregates), sample=sample))
    return rows


def joint_shift_statistics(
    aggregates: dict[int, pd.DataFrame],
) -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
    """Aggregate the original joint run draws without changing their pairing."""
    statistics = {}
    for observable, column in (("P_before", "P_before"), ("P_after", "P_after"),
                               ("S_before", "S_before"), ("S_after", "S_after"),
                               ("std_p_mid", "p_mid"), ("p_mid_shift", "p_mid")):
        series = []
        for C in (1, 2):
            grouped = aggregates[C].groupby("_L")[column]
            values = grouped.std(ddof=1) if observable == "std_p_mid" else grouped.mean()
            series.append((values.index.to_numpy(float), values.to_numpy(float)))
        statistics[observable] = series
    return statistics


def fit_joint_shift_statistics(
    statistics: dict[str, list[tuple[np.ndarray, np.ndarray]]], *, sample: int,
) -> list[dict[str, object]]:
    """Refit joint/shift samples with the identical bounded point estimators.

    Historical bootstrap labels are retained for comparison. U1_C1 and U1_C2
    report the two exponents from U1_independent; U2 reports the shared exponent
    with independent free correction exponents; U3 has fixed omega=1.
    """
    rows = []
    selected = {"U1_independent", "U2_shared_exponent", "U3_shared_exponent_omega_1"}
    for observable, sign in (("P_before", -1), ("P_after", -1), ("S_before", 1),
                             ("S_after", 1), ("std_p_mid", -1)):
        series = statistics[observable]
        fits = {fit["model"]: fit for fit in fit_universality_models(
            *series[0], *series[1], fixed_omegas=(1.0,), include_models=selected,
        )}
        for model, source, parameter in (
            ("U1_C1", "U1_independent", "exponent_c1"),
            ("U1_C2", "U1_independent", "exponent_c2"),
            ("U2_shared_exponent", "U2_shared_exponent", "exponent"),
            ("U3_shared_exponent_omega_fixed_1", "U3_shared_exponent_omega_1", "exponent"),
        ):
            fit = fits[source]
            rows.append(_joint_shift_bootstrap_row(
                fit, sample=sample, label="C1+C2", observable=observable,
                model=model, exponent=sign*fit.get(parameter, np.nan), limit=np.nan,
                used_L=";".join(str(int(L)) for L in series[0][0]),
            ))
    for C, (L, y) in enumerate(statistics["p_mid_shift"], start=1):
        fit = fit_corrected_shift_fixed_omega(L, y, label=f"C={C}", omega=1.0)
        rows.append(_joint_shift_bootstrap_row(
            fit, sample=sample, label=f"C={C}", observable="p_mid_shift",
            model="corrected_shift_omega_fixed_1",
            exponent=fit.get("inverse_nu", np.nan), limit=fit.get("pc", np.nan),
            used_L=";".join(str(int(size)) for size in L),
        ))
    return rows


def _joint_shift_bootstrap_row(
    fit: dict[str, object], *, sample: int, label: str, observable: str,
    model: str, exponent: float, limit: float, used_L: str,
) -> dict[str, object]:
    row = {key: value for key, value in fit.items()
           if key not in ("covariance", "prediction", "residuals")}
    row.update(sample=sample, condition_label=label, observable=observable,
               model=model, source_point_model=fit["model"], exponent=exponent,
               limit=limit, estimator="bounded_original_scale_nonlinear_least_squares",
               L_min=int(used_L.split(";")[0]), used_L=used_L)
    return row


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
    """Use the point estimator, including its bounds and fit diagnostics."""
    return fit_unbounded_models(L, y)


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
        return "bounded_nonlinear_least_squares_original_scale"
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


def _plot_shared_exponent_series(axis: plt.Axes, data: pd.DataFrame) -> None:
    """Draw both independent U1 exponents and each shared-exponent series."""
    for model, group in data.groupby("model"):
        if model == "U1_independent":
            for suffix, label in (("c1", "C=1"), ("c2", "C=2")):
                column = f"scaling_exponent_{suffix}"
                available = group.loc[group[column].notna()]
                axis.plot(available["L_min"], available[column], marker="o",
                          label=f"{model} {label}")
        else:
            axis.plot(group["L_min"], group["scaling_exponent"], marker="o", label=model)


def _plot_finite_point_curves(axis: plt.Axes, candidates: pd.DataFrame, label: str) -> None:
    """Render selected simple (including fixed-exponent) and correction fits."""
    for _, fit in candidates.iterrows():
        grid = np.geomspace(8, 128, 200)
        if fit["model"].startswith("simple_power"):
            prediction = simple_power(grid, fit["amplitude"], fit["exponent"])
        elif "omega" in fit["model"]:
            prediction = corrected_power(grid, fit["amplitude"], fit["exponent"],
                                         fit["correction"], fit["omega"])
        else:
            continue
        axis.plot(grid, prediction, label=f"{label} {fit['model']}")


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
            _plot_finite_point_curves(ax, candidates.head(2), label)
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
    _plot_shared_exponent_series(ax, data)
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
