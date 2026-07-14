from pathlib import Path

from analysis.plot_ensemble import analyze_and_plot


def test_writes_ensemble_outputs_and_two_figures_per_l(tmp_path, make_sweep):
    manifest_path = make_sweep(tmp_path, runs=2)

    figures = analyze_and_plot(manifest_path)

    analysis_directory = Path(tmp_path) / "analysis"
    assert len(figures) == 2
    assert all(path.is_file() and path.stat().st_size > 0 for path in figures)
    assert (analysis_directory / "ensemble_summary.csv").is_file()
    assert (analysis_directory / "pseudocritical_conventional.csv").is_file()
    assert (analysis_directory / "pseudocritical_runs.csv").is_file()
    assert (analysis_directory / "pseudocritical_summary.csv").is_file()
