import numpy as np
import pytest

from analysis.model_fitting import (
    constant_power,
    fit_power_models,
    fit_shift,
    information_criteria,
    multistart_curve_fit,
    pure_power,
)


def test_information_criteria_match_definitions():
    aicc, bic = information_criteria(2.0, 10, 2)
    aic = 10 * np.log(0.2) + 4
    assert aicc == pytest.approx(aic + 12 / 7)
    assert bic == pytest.approx(10 * np.log(0.2) + 2 * np.log(10))


def test_power_and_nonzero_limit_are_recovered_with_constraints():
    L = np.array([8, 12, 16, 24, 32, 48, 64, 96, 128], float)
    zero = pure_power(L, 0.7, 0.4)
    model_a, zero_model_b = fit_power_models(L, zero)
    assert model_a["parameters"] == pytest.approx([0.7, 0.4], rel=1e-5)
    assert zero_model_b["parameters"][0] < 1.0e-5
    nonzero = constant_power(L, 0.15, 0.8, 0.6)
    _, model_b = fit_power_models(L, nonzero)
    assert model_b["parameters"] == pytest.approx([0.15, 0.8, 0.6], rel=1e-4)
    assert np.all(np.asarray(model_b["parameters"]) >= 0)


def test_shift_fixed_and_free_recover_artificial_parameters():
    L = np.array([8, 12, 16, 24, 32, 48, 64, 96, 128], float)
    values = 0.5 + 0.3 * L ** -0.75
    fixed = fit_shift(L, values, fixed_pc=0.5)
    free = fit_shift(L, values)
    assert fixed["parameters"] == pytest.approx([0.3, 0.75], rel=1e-4)
    assert free["parameters"] == pytest.approx([0.5, 0.3, 0.75], rel=1e-3)


def test_nonconvergence_is_explicit_and_inputs_are_not_mutated():
    x = np.array([1.0, 2.0, 3.0])
    y = np.array([1.0, 2.0, 3.0])
    original = y.copy()
    with pytest.raises(RuntimeError, match="did not converge"):
        multistart_curve_fit(lambda x, a: np.full_like(x, np.nan), x, y, [[1]], ([0], [2]))
    assert np.array_equal(y, original)
