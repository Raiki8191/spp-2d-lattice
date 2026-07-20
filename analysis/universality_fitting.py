"""Joint correction-to-scaling fits for comparing finite C=1 and C=2."""

from __future__ import annotations

import numpy as np

from analysis.correction_fitting import OMEGA_FIXED_VALUES, fit_bounded_multistart


def fit_universality_models(
    L_c1: np.ndarray, y_c1: np.ndarray, L_c2: np.ndarray, y_c2: np.ndarray,
    *, fixed_omegas=OMEGA_FIXED_VALUES,
) -> list[dict[str, object]]:
    """Fit U1 independent, U2 shared x, and U3 shared x and omega models."""

    sizes = np.concatenate([np.asarray(L_c1, float), np.asarray(L_c2, float)])
    values = np.concatenate([np.asarray(y_c1, float), np.asarray(y_c2, float)])
    split = len(L_c1)

    def u1(x, a1, x1, b1, w1, a2, x2, b2, w2):
        out = np.empty_like(x)
        out[:split] = a1 * x[:split] ** x1 * (1 + b1 * x[:split] ** -w1)
        out[split:] = a2 * x[split:] ** x2 * (1 + b2 * x[split:] ** -w2)
        return out

    def u2(x, a1, b1, w1, a2, b2, w2, exponent):
        out = np.empty_like(x)
        out[:split] = a1 * x[:split] ** exponent * (1 + b1 * x[:split] ** -w1)
        out[split:] = a2 * x[split:] ** exponent * (1 + b2 * x[split:] ** -w2)
        return out

    def u3(x, a1, b1, a2, b2, exponent, omega):
        out = np.empty_like(x)
        out[:split] = a1 * x[:split] ** exponent * (1 + b1 * x[:split] ** -omega)
        out[split:] = a2 * x[split:] ** exponent * (1 + b2 * x[split:] ** -omega)
        return out

    scales = (max(float(y_c1[0]), 1e-9), max(float(y_c2[0]), 1e-9))
    common_bounds = (-20.0, 20.0)
    fits = [
        fit_bounded_multistart(
            u1, sizes, values,
            ((scales[0], exponent, b, omega, scales[1], exponent, -b, omega)
             for exponent in (-0.2, 1) for b in (-1, 1) for omega in (0.75,)),
            ((1e-12, -5, common_bounds[0], 0.05, 1e-12, -5, common_bounds[0], 0.05),
             (1e6, 5, common_bounds[1], 4, 1e6, 5, common_bounds[1], 4)),
            ("amplitude_c1", "exponent_c1", "correction_c1", "omega_c1",
             "amplitude_c2", "exponent_c2", "correction_c2", "omega_c2"), model="U1_independent",
        ),
        fit_bounded_multistart(
            u2, sizes, values,
            ((scales[0], b, omega, scales[1], -b, omega, exponent)
             for exponent in (-0.2, 1) for b in (-1, 1) for omega in (0.75,)),
            ((1e-12, -20, 0.05, 1e-12, -20, 0.05, -5),
             (1e6, 20, 4, 1e6, 20, 4, 5)),
            ("amplitude_c1", "correction_c1", "omega_c1", "amplitude_c2", "correction_c2", "omega_c2", "exponent"),
            model="U2_shared_exponent",
        ),
        fit_bounded_multistart(
            u3, sizes, values,
            ((scales[0], b, scales[1], -b, exponent, omega)
             for exponent in (-0.2, 1) for b in (-1, 1) for omega in (0.75,)),
            ((1e-12, -20, 1e-12, -20, -5, 0.05), (1e6, 20, 1e6, 20, 5, 4)),
            ("amplitude_c1", "correction_c1", "amplitude_c2", "correction_c2", "exponent", "omega"),
            model="U3_shared_exponent_omega",
        ),
    ]
    for fixed_omega in fixed_omegas:
        def u3_fixed(x, a1, b1, a2, b2, exponent, omega=fixed_omega):
            return u3(x, a1, b1, a2, b2, exponent, omega)
        fit = fit_bounded_multistart(
            u3_fixed, sizes, values,
            ((scales[0], b, scales[1], -b, exponent)
             for exponent in (-0.2, 1) for b in (-1, 1)),
            ((1e-12, -20, 1e-12, -20, -5), (1e6, 20, 1e6, 20, 5)),
            ("amplitude_c1", "correction_c1", "amplitude_c2", "correction_c2", "exponent"),
            model=f"U3_shared_exponent_omega_{fixed_omega:g}",
        )
        fit["omega"] = fixed_omega
        fits.append(fit)
    return fits
