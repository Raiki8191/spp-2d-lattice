"""Log-log finite-size fits without fixed critical exponents."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


L_MIN_VALUES = (8, 12, 16, 24, 32, 48)
FIT_SPECS = {
    "P_before": ("P_before_mean", -1),
    "P_after": ("P_after_mean", -1),
    "delta_P_max": ("delta_P_max_mean", -1),
    "S_before": ("S_before_mean", 1),
    "S_after": ("S_after_mean", 1),
    "std_p_mid": ("p_mid_std", -1),
    "delta_p_request": ("delta_p_request_mean", -1),
    "transition_delta_p": ("delta_p_mean", -1),
}
_T_975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571}


def fit_scaling(
    request_summary: pd.DataFrame, transition_summary: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    combined = request_summary.merge(
        transition_summary[
            ["condition_index", "delta_p_mean", "delta_t_normalized_mean"]
        ],
        on="condition_index",
        validate="one_to_one",
    ).copy()
    combined["condition_label"] = combined.apply(_condition_label, axis=1)
    fit_rows: list[dict[str, object]] = []
    exponent_rows: list[dict[str, object]] = []
    for condition_label, group in combined.groupby("condition_label", sort=True):
        ordered = group.sort_values("L")
        for observable, (column, exponent_sign) in FIT_SPECS.items():
            for L_min in L_MIN_VALUES:
                subset = ordered.loc[(ordered["L"] >= L_min) & (ordered[column] > 0)]
                # Four points keep AICc defined for the two-parameter log fit.
                if len(subset) < 4:
                    continue
                fit_rows.append(
                    _fit_row(
                        condition_label,
                        observable,
                        column,
                        exponent_sign,
                        L_min,
                        subset,
                    )
                )
            values = ordered.loc[ordered[column] > 0, ["L", column]]
            for index in range(1, len(values)):
                previous = values.iloc[index - 1]
                current = values.iloc[index]
                slope = math.log(float(current[column]) / float(previous[column])) / math.log(
                    float(current["L"]) / float(previous["L"])
                )
                exponent_rows.append(
                    {
                        "condition_label": condition_label,
                        "observable": observable,
                        "L_low": int(previous["L"]),
                        "L_high": int(current["L"]),
                        "L_geometric_mean": math.sqrt(
                            float(previous["L"]) * float(current["L"])
                        ),
                        "local_slope": slope,
                        "local_effective_exponent": exponent_sign * slope,
                    }
                )
    return pd.DataFrame(fit_rows), pd.DataFrame(exponent_rows)


def _fit_row(
    condition_label: str,
    observable: str,
    column: str,
    exponent_sign: int,
    L_min: int,
    subset: pd.DataFrame,
) -> dict[str, object]:
    x = np.log(subset["L"].to_numpy(float))
    y = np.log(subset[column].to_numpy(float))
    design = np.column_stack([x, np.ones(len(x))])
    slope, intercept = np.linalg.lstsq(design, y, rcond=None)[0]
    prediction = slope * x + intercept
    residual = y - prediction
    residual_sum = float(np.sum(residual**2))
    total_sum = float(np.sum((y - y.mean()) ** 2))
    degrees_freedom = len(x) - 2
    slope_standard_error = math.sqrt(
        (residual_sum / degrees_freedom) / float(np.sum((x - x.mean()) ** 2))
    )
    t_critical = _T_975.get(degrees_freedom, 1.96)
    slope_low = slope - t_critical * slope_standard_error
    slope_high = slope + t_critical * slope_standard_error
    parameter_count = 2
    safe_rss = max(residual_sum, np.finfo(float).tiny)
    aic = len(x) * math.log(safe_rss / len(x)) + 2 * parameter_count
    aicc = (
        aic + 2 * parameter_count * (parameter_count + 1) / (len(x) - parameter_count - 1)
        if len(x) > parameter_count + 1
        else math.inf
    )
    bic = len(x) * math.log(safe_rss / len(x)) + parameter_count * math.log(len(x))
    return {
        "condition_label": condition_label,
        "observable": observable,
        "source_column": column,
        "L_min": L_min,
        "point_count": len(subset),
        "used_L": ";".join(str(int(value)) for value in subset["L"]),
        "slope": slope,
        "exponent": exponent_sign * slope,
        "intercept": intercept,
        "slope_standard_error": slope_standard_error,
        "slope_ci95_low": slope_low,
        "slope_ci95_high": slope_high,
        "exponent_ci95_low": min(exponent_sign * slope_low, exponent_sign * slope_high),
        "exponent_ci95_high": max(exponent_sign * slope_low, exponent_sign * slope_high),
        "r_squared": 1.0 - residual_sum / total_sum if total_sum > 0 else 1.0,
        "rss": residual_sum,
        "aicc": aicc,
        "bic": bic,
    }


def _condition_label(row: pd.Series) -> str:
    return "UNBOUNDED" if row["budget_mode"] == "UNBOUNDED" else f"C={int(row['C'])}"
