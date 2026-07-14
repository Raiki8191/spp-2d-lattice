"""Build common-grid ensemble summaries, pseudocritical candidates, and pilot plots."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "spp-matplotlib-cache")
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analysis.ensemble import aggregate_ensemble
from analysis.io import load_sweep
from analysis.pseudocritical import (
    extract_conventional_peaks,
    extract_run_peaks,
    summarize_run_peaks,
)
from analysis.resampling import resample_common_p_grid
from analysis.validation import validate_sweep


def analyze_and_plot(manifest_path: str | Path) -> list[Path]:
    manifest, results = load_sweep(manifest_path)
    validation = validate_sweep(manifest, results)
    resampled = resample_common_p_grid(results, manifest)
    ensemble = aggregate_ensemble(resampled)
    conventional = extract_conventional_peaks(ensemble)
    run_peaks = extract_run_peaks(results)
    run_summary = summarize_run_peaks(run_peaks)

    root = Path(manifest.attrs["manifest_path"]).parent / "analysis"
    figure_directory = root / "figures"
    figure_directory.mkdir(parents=True, exist_ok=True)
    ensemble.to_csv(root / "ensemble_summary.csv", index=False, encoding="utf-8")
    conventional.to_csv(
        root / "pseudocritical_conventional.csv", index=False, encoding="utf-8"
    )
    run_peaks.to_csv(root / "pseudocritical_runs.csv", index=False, encoding="utf-8")
    run_summary.to_csv(
        root / "pseudocritical_summary.csv", index=False, encoding="utf-8"
    )

    generated: list[Path] = []
    for lattice_size in sorted(ensemble["L"].unique()):
        lattice = ensemble.loc[ensemble["L"] == lattice_size]
        condition_indices = sorted(lattice["condition_index"].unique())
        colors = plt.get_cmap("tab10")
        condition_colors = {
            condition_index: colors(index % 10)
            for index, condition_index in enumerate(condition_indices)
        }
        generated.append(
            _plot_observable(
                lattice,
                conventional,
                int(lattice_size),
                "largest_cluster_fraction_mean",
                "largest_cluster_fraction_sem",
                "Mean largest-cluster fraction P",
                figure_directory / f"L={int(lattice_size)}_ensemble_mean_P_vs_p.png",
                condition_colors,
                mark_peak=False,
            )
        )
        generated.append(
            _plot_observable(
                lattice,
                conventional,
                int(lattice_size),
                "mean_cluster_size_mean",
                "mean_cluster_size_sem",
                "Mean finite-cluster size S",
                figure_directory / f"L={int(lattice_size)}_ensemble_mean_S_vs_p.png",
                condition_colors,
                mark_peak=True,
            )
        )

    print(
        "Validation succeeded: "
        f"conditions={validation.condition_count}, rows={validation.row_count}, "
        f"condition_runs={validation.run_count}, grid_rows={len(ensemble)}"
    )
    print(conventional.to_string(index=False))
    print(run_summary.to_string(index=False))
    for path in generated:
        print(f"wrote {path} ({path.stat().st_size} bytes)")
    return generated


def _plot_observable(
    lattice,
    conventional,
    lattice_size,
    mean_column,
    sem_column,
    y_label,
    output_path,
    condition_colors,
    *,
    mark_peak,
):
    figure, axes = plt.subplots(figsize=(10, 6))
    for condition_index, condition in lattice.groupby("condition_index", sort=True):
        complete = condition.loc[condition["n_eff"] == condition["runs"]]
        if complete.empty:
            continue
        first = complete.iloc[0]
        label = (
            "UNBOUNDED"
            if first["budget_mode"] == "UNBOUNDED"
            else f"C={int(first['C'])}"
        )
        color = condition_colors[int(condition_index)]
        x = complete["p"].to_numpy(dtype=float)
        mean = complete[mean_column].to_numpy(dtype=float)
        sem = complete[sem_column].fillna(0.0).to_numpy(dtype=float)
        axes.plot(
            x,
            mean,
            color=color,
            linewidth=2.5,
            drawstyle="steps-post",
            label=f"{label} (n={int(first['runs'])})",
        )
        axes.fill_between(
            x, mean - sem, mean + sem, step="post", color=color, alpha=0.2
        )
        if mark_peak:
            peak = conventional.loc[
                conventional["condition_index"] == condition_index
            ].iloc[0]
            axes.scatter(
                peak["pseudocritical_p_conventional"],
                peak["peak_mean_cluster_size"],
                color=color,
                edgecolor="black",
                s=65,
                zorder=5,
            )

    axes.set_title(f"L={lattice_size}: {y_label} on the complete-run p grid")
    axes.set_xlabel("Removed edge fraction p")
    axes.set_ylabel(y_label)
    axes.grid(True, alpha=0.3)
    axes.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    arguments = parser.parse_args()
    analyze_and_plot(arguments.manifest)


if __name__ == "__main__":
    main()
