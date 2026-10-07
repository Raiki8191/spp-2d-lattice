"""Scientific plot coverage: independent exponents and selected theory curves."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from analysis.scaling_v3 import _plot_finite_point_curves, _plot_shared_exponent_series


def _points():
    return pd.DataFrame([
        dict(model="U1_independent", L_min=8, scaling_exponent=np.nan,
             scaling_exponent_c1=.16, scaling_exponent_c2=.10),
        dict(model="U1_independent", L_min=16, scaling_exponent=np.nan,
             scaling_exponent_c1=.15, scaling_exponent_c2=.11),
        dict(model="U2_shared_exponent", L_min=8, scaling_exponent=.104),
        dict(model="U2_shared_exponent", L_min=16, scaling_exponent=.107),
        dict(model="U3_shared_exponent_omega_1", L_min=8, scaling_exponent=.106),
        dict(model="U3_shared_exponent_omega_1", L_min=16, scaling_exponent=.108),
    ])


def test_u1_renders_both_finite_independent_exponent_series():
    figure, axis = plt.subplots()
    try:
        _plot_shared_exponent_series(axis, _points().query("model == 'U1_independent'"))
        lines = {line.get_label(): line for line in axis.lines}
        assert set(lines) == {"U1_independent C=1", "U1_independent C=2"}
        np.testing.assert_array_equal(lines["U1_independent C=1"].get_ydata(), [.16, .15])
        np.testing.assert_array_equal(lines["U1_independent C=2"].get_ydata(), [.10, .11])
        assert all(np.isfinite(line.get_ydata()).all() for line in lines.values())
    finally:
        plt.close(figure)


def test_all_models_preserve_shared_values_labels_and_markers():
    figure, axis = plt.subplots()
    try:
        _plot_shared_exponent_series(axis, _points())
        lines = {line.get_label(): line for line in axis.lines}
        assert len(lines) == 4
        for label, expected in (("U2_shared_exponent", [.104, .107]),
                                ("U3_shared_exponent_omega_1", [.106, .108])):
            np.testing.assert_array_equal(lines[label].get_ydata(), expected)
            np.testing.assert_array_equal(lines[label].get_xdata(), [8, 16])
            assert lines[label].get_marker() == "o"
        assert all(np.isfinite(line.get_ydata()).all() for line in lines.values())
    finally:
        plt.close(figure)


def test_u1_available_sizes_are_selected_independently_for_each_condition():
    frame = _points().query("model == 'U1_independent'").copy()
    frame.loc[frame.L_min == 16, "scaling_exponent_c1"] = np.nan
    frame.loc[frame.L_min == 8, "scaling_exponent_c2"] = np.nan
    figure, axis = plt.subplots()
    try:
        _plot_shared_exponent_series(axis, frame)
        lines = {line.get_label(): line for line in axis.lines}
        np.testing.assert_array_equal(lines["U1_independent C=1"].get_xdata(), [8])
        np.testing.assert_array_equal(lines["U1_independent C=2"].get_xdata(), [16])
    finally:
        plt.close(figure)


def test_selected_theory_fixed_simple_curve_is_rendered():
    candidates = pd.DataFrame([
        dict(model="simple_power_fixed_exponent", amplitude=.9, exponent=-5/48),
        dict(model="simple_power", amplitude=.95, exponent=-.12),
    ])
    figure, axis = plt.subplots()
    try:
        _plot_finite_point_curves(axis, candidates, "C=1")
        lines = {line.get_label(): line for line in axis.lines}
        assert set(lines) == {"C=1 simple_power_fixed_exponent", "C=1 simple_power"}
        for label, amplitude, exponent in (("C=1 simple_power_fixed_exponent", .9, -5/48),
                                           ("C=1 simple_power", .95, -.12)):
            x = lines[label].get_xdata()
            np.testing.assert_array_equal(lines[label].get_ydata(), amplitude*x**exponent)
            assert len(x) == 200 and x[0] == 8 and x[-1] == 128
    finally:
        plt.close(figure)


def test_existing_corrected_curve_keeps_its_selected_coefficients():
    candidates = pd.DataFrame([
        dict(model="corrected_power_omega_2", amplitude=.8, exponent=-.1,
             correction=.3, omega=2),
    ])
    figure, axis = plt.subplots()
    try:
        _plot_finite_point_curves(axis, candidates, "C=2")
        assert len(axis.lines) == 1
        line = axis.lines[0]
        x = line.get_xdata()
        np.testing.assert_array_equal(line.get_ydata(), .8*x**-.1*(1+.3*x**-2))
        assert line.get_label() == "C=2 corrected_power_omega_2"
    finally:
        plt.close(figure)
