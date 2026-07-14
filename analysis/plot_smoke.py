"""Validate a sweep and save raw per-run smoke plots without interpolation."""

from __future__ import annotations

import argparse
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "spp-matplotlib-cache")
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analysis.io import load_sweep
from analysis.validation import validate_sweep


@dataclass(frozen=True)
class PlotSpec:
    x_column: str
    y_column: str
    filename: str
    x_label: str
    y_label: str
    title: str
    marker: str | None
    drawstyle: str


PLOTS = (
    PlotSpec(
        "removed_edge_fraction",
        "largest_cluster_fraction",
        "largest_cluster_fraction_vs_removed_edge_fraction.png",
        "Removed edge fraction p",
        "Largest cluster fraction P",
        "Largest cluster fraction vs removed edge fraction",
        "o",
        "default",
    ),
    PlotSpec(
        "removed_edge_fraction",
        "mean_cluster_size",
        "mean_cluster_size_vs_removed_edge_fraction.png",
        "Removed edge fraction p",
        "Mean finite-cluster size S",
        "Mean finite-cluster size vs removed edge fraction",
        "o",
        "default",
    ),
    PlotSpec(
        "step",
        "largest_cluster_fraction",
        "largest_cluster_fraction_vs_step.png",
        "Processed requests t",
        "Largest cluster fraction P",
        "Largest cluster fraction vs processed requests",
        None,
        "steps-post",
    ),
)


def create_plots(manifest_path: str | Path) -> list[Path]:
    manifest, results = load_sweep(manifest_path)
    summary = validate_sweep(manifest, results)
    output_directory = Path(manifest.attrs["manifest_path"]).parent / "figures"
    output_directory.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    for lattice_size in sorted(results["L"].unique()):
        lattice_results = results.loc[results["L"] == lattice_size]
        condition_indices = sorted(lattice_results["condition_index"].unique())
        colors = plt.get_cmap("tab10")
        condition_colors = {
            condition_index: colors(index % 10)
            for index, condition_index in enumerate(condition_indices)
        }
        for spec in PLOTS:
            figure, axes = plt.subplots(figsize=(12, 7))
            for (condition_index, run), group in lattice_results.groupby(
                ["condition_index", "run"], sort=True
            ):
                first = group.iloc[0]
                budget_label = (
                    "UNBOUNDED"
                    if first["budget_mode"] == "UNBOUNDED"
                    else f"C={int(first['C'])}"
                )
                axes.plot(
                    group[spec.x_column],
                    group[spec.y_column],
                    color=condition_colors[int(condition_index)],
                    linestyle=("-", "--", ":", "-.")[int(run) % 4],
                    alpha=0.8,
                    marker=spec.marker,
                    markersize=3,
                    drawstyle=spec.drawstyle,
                    label=f"{budget_label}, run={int(run)}",
                )
            axes.set_title(f"L={int(lattice_size)}: {spec.title}")
            axes.set_xlabel(spec.x_label)
            axes.set_ylabel(spec.y_label)
            axes.grid(True, alpha=0.3)
            axes.legend(fontsize="x-small", ncol=3)
            figure.tight_layout()
            output_path = output_directory / f"L={int(lattice_size)}_{spec.filename}"
            figure.savefig(output_path, dpi=150)
            plt.close(figure)
            generated.append(output_path)

    # ACCEPTED_REQUEST runs generally have different p samples. Deliberately do not
    # average by row number; common-grid interpolation/binning belongs to a later stage.
    print(
        "Validation succeeded: "
        f"conditions={summary.condition_count}, rows={summary.row_count}, "
        f"condition_runs={summary.run_count}, run_ids={results['run'].nunique()}"
    )
    for path in generated:
        print(f"wrote {path} ({path.stat().st_size} bytes)")
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="path to manifest.csv")
    arguments = parser.parse_args()
    create_plots(arguments.manifest)


if __name__ == "__main__":
    main()
