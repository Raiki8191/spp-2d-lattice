from pathlib import Path

from analysis.plot_smoke import PLOTS, create_plots


def test_creates_three_raw_run_plots_per_lattice_size(tmp_path, make_sweep):
    manifest_path = make_sweep(
        tmp_path,
        conditions=[
            {"condition_index": 0, "L": 2, "C": 1, "budget_mode": "FINITE"},
            {"condition_index": 1, "L": 3, "C": 1, "budget_mode": "FINITE"},
        ],
        runs=2,
    )

    generated = create_plots(manifest_path)

    assert len(generated) == 6
    assert {path.name.split("_")[0] for path in generated} == {"L=2", "L=3"}
    assert all(path.is_file() and path.stat().st_size > 0 for path in generated)
    assert all(path.parent == Path(tmp_path) / "figures" for path in generated)


def test_step_plot_uses_steps_post_and_p_plots_keep_markers():
    assert PLOTS[0].marker == "o"
    assert PLOTS[1].marker == "o"
    assert PLOTS[2].drawstyle == "steps-post"
