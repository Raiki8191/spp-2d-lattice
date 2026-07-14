"""Validate a sweep and save raw per-run smoke plots without interpolation."""

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

from analysis.io import load_sweep
from analysis.validation import validate_sweep


PLOTS = (
    (
        "removed_edge_fraction",
        "largest_cluster_fraction",
        "largest_cluster_fraction_vs_removed_edge_fraction.png",
        "Removed edge fraction p",
        "Largest cluster fraction P",
        "Largest cluster fraction vs removed edge fraction",
    ),
    (
        "removed_edge_fraction",
        "mean_cluster_size",
        "mean_cluster_size_vs_removed_edge_fraction.png",
        "Removed edge fraction p",
        "Mean finite-cluster size S",
        "Mean finite-cluster size vs removed edge fraction",
    ),
    (
        "step",
        "largest_cluster_fraction",
        "largest_cluster_fraction_vs_step.png",
        "Processed requests t",
        "Largest cluster fraction P",
        "Largest cluster fraction vs processed requests",
    ),
)


def create_plots(manifest_path: str | Path) -> list[Path]:
    manifest, results = load_sweep(manifest_path)
    summary = validate_sweep(manifest, results)
    output_directory = Path(manifest.attrs["manifest_path"]).parent / "figures"
    output_directory.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    for x_column, y_column, filename, x_label, y_label, title in PLOTS:
        figure, axes = plt.subplots(figsize=(10, 6))
        for (condition_index, run), group in results.groupby(
            ["condition_index", "run"], sort=True
        ):
            first = group.iloc[0]
            label = (
                f"L={int(first['L'])}, C={int(first['C'])}, "
                f"{first['budget_mode']}, run={int(run)}"
            )
            axes.plot(group[x_column], group[y_column], marker="o", markersize=3, label=label)
        axes.set_title(title)
        axes.set_xlabel(x_label)
        axes.set_ylabel(y_label)
        axes.grid(True, alpha=0.3)
        axes.legend(fontsize="small", ncol=2)
        figure.tight_layout()
        output_path = output_directory / filename
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
