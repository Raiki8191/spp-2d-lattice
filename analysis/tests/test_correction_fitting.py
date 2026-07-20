import numpy as np
import pytest

from analysis.correction_fitting import (
    corrected_power, fit_bounded_multistart, logarithmic_limit, power_model_fits,
)


SIZES = np.array([8, 12, 16, 24, 32, 48, 64, 96, 128], float)


def test_corrected_power_recovers_artificial_parameters_without_mutation():
    values = corrected_power(SIZES, 1.7, -0.2, 0.8, 1.0)
    original = values.copy()
    fits = power_model_fits(SIZES, values)
    free = next(fit for fit in fits if fit["model"] == "corrected_power_free_omega")
    assert free["converged"]
    assert free["amplitude"] == pytest.approx(1.7, rel=1e-3)
    assert free["exponent"] == pytest.approx(-0.2, rel=1e-3)
    assert free["omega"] == pytest.approx(1.0, rel=2e-2)
    assert np.array_equal(values, original)


def test_theory_fixed_exponent_is_preserved_and_compared_at_multiple_omega():
    theory = -5 / 48
    values = corrected_power(SIZES, 0.9, theory, -0.5, 0.75)
    fits = power_model_fits(SIZES, values, fixed_exponent=theory)
    assert {fit.get("omega") for fit in fits if "omega" in fit["model"]} == {0.5, 0.75, 1.0, 1.5, 2.0}
    assert all(fit["exponent"] == theory for fit in fits)


def test_too_many_parameters_are_explicitly_inadmissible():
    result = fit_bounded_multistart(
        lambda x, a, b, c: a + b * x + c * x**2,
        [1, 2, 3, 4], [1, 2, 3, 4], [[1, 1, 1]],
        ([-10, -10, -10], [10, 10, 10]), ["a", "b", "c"], model="quadratic",
    )
    assert not result["converged"]
    assert "insufficient points" in result["failure"]


def test_logarithmic_limit_model_and_boundary_diagnostics():
    values = logarithmic_limit(SIZES, 0.2, 0.7, 1.1)
    result = fit_bounded_multistart(
        logarithmic_limit, SIZES, values,
        [(0.0, 1, .5), (.2, .7, 1.1)], ((0, 0, .001), (1, 10, 10)),
        ("limit", "amplitude", "decay_exponent"), model="finite_log",
    )
    assert result["parameters"] if "parameters" in result else result["converged"]
    assert result["limit"] == pytest.approx(.2, rel=1e-4)
    assert result["aicc"] < np.inf

