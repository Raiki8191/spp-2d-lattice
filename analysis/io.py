"""UTF-8 CSV loading for Java-produced SPP parameter sweeps."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


MANIFEST_COLUMNS = (
    "condition_index",
    "L",
    "C",
    "budget_mode",
    "runs",
    "max_steps",
    "measurement_mode",
    "measurement_interval",
    "base_seed",
    "result_path",
)

RESULT_COLUMNS = (
    "run",
    "L",
    "C",
    "step",
    "removed_edges",
    "remaining_edges",
    "removed_edge_fraction",
    "largest_cluster_size",
    "largest_cluster_fraction",
    "second_largest_cluster_size",
    "mean_cluster_size",
    "accepted_requests",
    "rejected_requests",
    "seed",
)

_MANIFEST_INTEGER_COLUMNS = (
    "condition_index",
    "L",
    "C",
    "runs",
    "max_steps",
    "measurement_interval",
    "base_seed",
)

_RESULT_INTEGER_COLUMNS = (
    "run",
    "L",
    "C",
    "step",
    "removed_edges",
    "remaining_edges",
    "largest_cluster_size",
    "second_largest_cluster_size",
    "accepted_requests",
    "rejected_requests",
    "seed",
)


def read_manifest(path: str | Path) -> pd.DataFrame:
    """Read and structurally validate a sweep manifest.

    ``result_path`` is replaced with an absolute path resolved relative to the
    manifest directory. Missing result files are reported before any data load.
    """

    manifest_path = Path(path).expanduser().resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest CSV does not exist: {manifest_path}")

    manifest = pd.read_csv(manifest_path, encoding="utf-8")
    _require_columns(manifest, MANIFEST_COLUMNS, "manifest")
    _convert_integers(manifest, _MANIFEST_INTEGER_COLUMNS, "manifest")

    if manifest["condition_index"].duplicated().any():
        duplicate = int(
            manifest.loc[manifest["condition_index"].duplicated(), "condition_index"].iloc[0]
        )
        raise ValueError(f"manifest contains duplicate condition_index={duplicate}")

    valid_budget_modes = {"FINITE", "UNBOUNDED"}
    invalid_modes = ~manifest["budget_mode"].isin(valid_budget_modes)
    if invalid_modes.any():
        row = manifest.loc[invalid_modes].iloc[0]
        raise ValueError(
            "invalid budget_mode="
            f"{row['budget_mode']!r} for condition={int(row['condition_index'])}"
        )

    resolved_paths: list[str] = []
    for row in manifest.itertuples(index=False):
        raw_path = Path(str(row.result_path))
        result_path = (
            raw_path if raw_path.is_absolute() else manifest_path.parent / raw_path
        ).resolve()
        if not result_path.is_file():
            raise FileNotFoundError(
                "results CSV does not exist for "
                f"condition={row.condition_index}: {result_path}"
            )
        resolved_paths.append(str(result_path))

    manifest = manifest.loc[:, MANIFEST_COLUMNS].copy()
    manifest["result_path"] = resolved_paths
    manifest.attrs["manifest_path"] = str(manifest_path)
    return manifest


def read_results(manifest: pd.DataFrame) -> pd.DataFrame:
    """Load every results CSV and combine it into one DataFrame."""

    if manifest is None:
        raise ValueError("manifest must not be None")
    _require_columns(manifest, MANIFEST_COLUMNS, "manifest")

    frames: list[pd.DataFrame] = []
    for condition in manifest.itertuples(index=False):
        result_path = Path(str(condition.result_path))
        if not result_path.is_file():
            raise FileNotFoundError(
                "results CSV does not exist for "
                f"condition={condition.condition_index}: {result_path}"
            )
        result = pd.read_csv(result_path, encoding="utf-8")
        _require_columns(result, RESULT_COLUMNS, f"results {result_path}")
        _convert_integers(result, _RESULT_INTEGER_COLUMNS, f"results {result_path}")

        if result.empty:
            raise ValueError(
                f"results CSV is empty for condition={condition.condition_index}: {result_path}"
            )
        mismatch = (result["L"] != condition.L) | (result["C"] != condition.C)
        if mismatch.any():
            row = result.loc[mismatch].iloc[0]
            raise ValueError(
                "manifest/results L or C mismatch at "
                f"condition={condition.condition_index}, run={int(row['run'])}, "
                f"step={int(row['step'])}: manifest L={condition.L}, C={condition.C}; "
                f"results L={int(row['L'])}, C={int(row['C'])}"
            )

        result = result.loc[:, RESULT_COLUMNS].copy()
        result["condition_index"] = int(condition.condition_index)
        result["budget_mode"] = str(condition.budget_mode)
        result["result_path"] = str(result_path.resolve())
        frames.append(result)

    if not frames:
        raise ValueError("manifest contains no conditions")
    return pd.concat(frames, ignore_index=True)


def load_sweep(path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load a manifest and all referenced results without numerical validation."""

    manifest = read_manifest(path)
    return manifest, read_results(manifest)


def _require_columns(frame: pd.DataFrame, required: tuple[str, ...], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(missing)}")


def _convert_integers(
    frame: pd.DataFrame, columns: tuple[str, ...], label: str
) -> None:
    for column in columns:
        try:
            numeric = pd.to_numeric(frame[column], errors="raise")
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label} column {column!r} must be integer-valued") from error
        if numeric.isna().any() or (numeric % 1 != 0).any():
            raise ValueError(f"{label} column {column!r} must be integer-valued")
        frame[column] = numeric.astype("int64")

