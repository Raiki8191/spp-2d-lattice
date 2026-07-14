"""Run request-level FSS summaries, fits, and non-interactive scaling plots."""

from __future__ import annotations

import argparse
import os
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "spp-matplotlib-cache")
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analysis.io import load_sweep
from analysis.request_fss import write_fss_summaries
from analysis.scaling_fit import fit_scaling
from analysis.validation import validate_sweep


def analyze_scaling(
    manifest_path: str | Path,
    output_directory: str | Path | None = None,
    *,
    bootstrap_samples: int = 2000,
) -> list[Path]:
    started = time.perf_counter()
    manifest, results = load_sweep(manifest_path)
    validation = validate_sweep(manifest, results)
    root = (
        Path(output_directory)
        if output_directory is not None
        else Path(manifest.attrs["manifest_path"]).parent / "analysis"
    ).resolve()
    events, request_summary, transition_summary = write_fss_summaries(
        results, root, bootstrap_samples=bootstrap_samples
    )
    fits, effective = fit_scaling(request_summary, transition_summary)
    fits.to_csv(root / "scaling_fit_results.csv", index=False, encoding="utf-8")
    effective.to_csv(root / "effective_exponents.csv", index=False, encoding="utf-8")
    figures = _plot_all(request_summary, transition_summary, fits, effective, root / "figures")
    elapsed = time.perf_counter() - started
    print(
        "Scaling analysis succeeded: "
        f"conditions={validation.condition_count}, runs={validation.run_count}, "
        f"events={len(events)}, fits={len(fits)}, elapsed_seconds={elapsed:.3f}"
    )
    for path in figures:
        print(f"wrote {path} ({path.stat().st_size} bytes)")
    return figures


def _plot_all(
    request: pd.DataFrame,
    transition: pd.DataFrame,
    fits: pd.DataFrame,
    effective: pd.DataFrame,
    figure_directory: Path,
) -> list[Path]:
    figure_directory.mkdir(parents=True, exist_ok=True)
    combined = request.merge(
        transition[["condition_index", "delta_p_mean", "delta_t_normalized_mean"]],
        on="condition_index",
        validate="one_to_one",
    ).copy()
    combined["condition_label"] = combined.apply(
        lambda row: "UNBOUNDED"
        if row["budget_mode"] == "UNBOUNDED"
        else f"C={int(row['C'])}",
        axis=1,
    )
    generated: list[Path] = []
    for label, group in combined.groupby("condition_label", sort=True):
        ordered = group.sort_values("L")
        slug = label.replace("=", "-").lower()
        specs = (
            (("P_before_mean", "P before"), ("P_after_mean", "P after")),
            (("delta_P_max_mean", "delta P max"),),
            (("S_before_mean", "S before"), ("S_after_mean", "S after")),
            (("p_mid_std", "std(p mid)"),),
            (("delta_p_request_mean", "request delta p"),),
            (("delta_p_mean", "transition delta p"),),
            (("delta_t_normalized_mean", "transition delta t / N^2"),),
        )
        names = (
            "P-before-after",
            "delta-P-max",
            "S-before-after",
            "std-p-mid",
            "request-delta-p",
            "transition-delta-p",
            "transition-delta-t-normalized",
        )
        for series, name in zip(specs, names):
            output = figure_directory / f"{slug}-{name}.png"
            _loglog_plot(ordered, series, label, fits, output)
            generated.append(output)

        output = figure_directory / f"{slug}-p-location-vs-inverse-L.png"
        _inverse_size_plot(ordered, label, output)
        generated.append(output)

        output = figure_directory / f"{slug}-local-effective-exponents.png"
        _effective_plot(effective.loc[effective["condition_label"] == label], label, output)
        generated.append(output)
    return generated


def _loglog_plot(
    data: pd.DataFrame,
    series: tuple[tuple[str, str], ...],
    condition_label: str,
    fits: pd.DataFrame,
    output: Path,
) -> None:
    figure, axes = plt.subplots(figsize=(9, 6))
    for column, label in series:
        positive = data.loc[data[column] > 0]
        axes.loglog(positive["L"], positive[column], marker="o", linewidth=2, label=label)
        observable = _observable_for_column(column)
        fit = fits.loc[
            (fits["condition_label"] == condition_label)
            & (fits["observable"] == observable)
            & (fits["L_min"] == 16)
        ]
        if not fit.empty:
            row = fit.iloc[0]
            line_L = positive.loc[positive["L"] >= 16, "L"].to_numpy(float)
            line_y = np.exp(float(row["intercept"])) * line_L ** float(row["slope"])
            axes.loglog(line_L, line_y, linestyle="--", linewidth=1.4)
    axes.set_title(f"{condition_label}: finite-size scaling")
    axes.set_xlabel("Linear size L")
    axes.set_ylabel("Observable")
    axes.grid(True, which="both", alpha=0.3)
    axes.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def _inverse_size_plot(data: pd.DataFrame, condition_label: str, output: Path) -> None:
    figure, axes = plt.subplots(figsize=(9, 6))
    inverse_L = 1.0 / data["L"].to_numpy(float)
    for column, label in (
        ("p_before_mean", "p before"),
        ("p_after_mean", "p after"),
        ("p_mid_mean", "p mid"),
    ):
        axes.plot(inverse_L, data[column], marker="o", linewidth=2, label=label)
    axes.set_title(f"{condition_label}: pseudocritical location")
    axes.set_xlabel("1 / L")
    axes.set_ylabel("Removed edge fraction p")
    axes.grid(True, alpha=0.3)
    axes.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def _effective_plot(data: pd.DataFrame, condition_label: str, output: Path) -> None:
    figure, axes = plt.subplots(figsize=(10, 6))
    for observable, group in data.groupby("observable", sort=True):
        axes.plot(
            group["L_geometric_mean"],
            group["local_effective_exponent"],
            marker="o",
            linewidth=1.5,
            label=observable,
        )
    axes.set_xscale("log")
    axes.set_title(f"{condition_label}: local effective exponents")
    axes.set_xlabel("Geometric mean size")
    axes.set_ylabel("Local effective exponent")
    axes.grid(True, alpha=0.3)
    axes.legend(ncol=2)
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def _observable_for_column(column: str) -> str:
    mapping = {
        "P_before_mean": "P_before",
        "P_after_mean": "P_after",
        "delta_P_max_mean": "delta_P_max",
        "S_before_mean": "S_before",
        "S_after_mean": "S_after",
        "p_mid_std": "std_p_mid",
        "delta_p_request_mean": "delta_p_request",
        "delta_p_mean": "transition_delta_p",
    }
    return mapping.get(column, column)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    arguments = parser.parse_args()
    analyze_scaling(
        arguments.manifest,
        arguments.output,
        bootstrap_samples=arguments.bootstrap_samples,
    )


if __name__ == "__main__":
    main()
