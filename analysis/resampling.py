"""Right-continuous resampling of measured SPP states onto exact edge-count grids."""

from __future__ import annotations

import numpy as np
import pandas as pd


STATE_COLUMNS = (
    "step",
    "removed_edges",
    "largest_cluster_fraction",
    "mean_cluster_size",
    "second_largest_cluster_size",
)


def resample_common_p_grid(
    results: pd.DataFrame, manifest: pd.DataFrame
) -> pd.DataFrame:
    """Map every run to k=0..M0 using the first measured state with removed_edges >= k.

    This is a post-request, right-continuous mapping. It performs no interpolation,
    never invents a cluster state, and leaves grid points beyond a run's final state NaN.
    The input DataFrames are not modified.
    """

    if results is None or manifest is None:
        raise ValueError("results and manifest must not be None")
    required_results = {
        "condition_index",
        "run",
        "L",
        "C",
        "budget_mode",
        *STATE_COLUMNS,
    }
    missing = sorted(required_results.difference(results.columns))
    if missing:
        raise ValueError(f"results is missing columns: {', '.join(missing)}")
    required_manifest = {"condition_index", "runs", "L", "C", "budget_mode"}
    missing = sorted(required_manifest.difference(manifest.columns))
    if missing:
        raise ValueError(f"manifest is missing columns: {', '.join(missing)}")

    frames: list[pd.DataFrame] = []
    metadata = manifest.set_index("condition_index", drop=False)
    for (condition_index, run), run_data in results.groupby(
        ["condition_index", "run"], sort=True
    ):
        condition = metadata.loc[int(condition_index)]
        lattice_size = int(condition["L"])
        initial_edges = 2 * lattice_size * (lattice_size - 1)
        grid_k = np.arange(initial_edges + 1, dtype=np.int64)

        measured = run_data.sort_values("step", kind="stable")
        removed = measured["removed_edges"].to_numpy(dtype=np.int64)
        indices = np.searchsorted(removed, grid_k, side="left")
        available = indices < len(measured)

        frame = pd.DataFrame(
            {
                "condition_index": int(condition_index),
                "run": int(run),
                "L": lattice_size,
                "C": int(condition["C"]),
                "budget_mode": str(condition["budget_mode"]),
                "runs": int(condition["runs"]),
                "k": grid_k,
                "p": grid_k / initial_edges if initial_edges else np.zeros_like(grid_k),
            }
        )
        for column in STATE_COLUMNS:
            values = np.full(len(grid_k), np.nan, dtype=float)
            source = measured[column].to_numpy(dtype=float)
            values[available] = source[indices[available]]
            frame[column] = values
        frames.append(frame)

    if not frames:
        raise ValueError("results contains no condition/run data")
    return pd.concat(frames, ignore_index=True)
