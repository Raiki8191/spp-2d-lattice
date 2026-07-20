"""Logical, condition-at-a-time access to multiple SPP sweep manifests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

import pandas as pd

from analysis.io import MANIFEST_COLUMNS, read_manifest, read_results
from analysis.validation import validate_sweep


@dataclass(frozen=True)
class ManifestCondition:
    global_condition_id: int
    source_manifest: str
    source_condition_index: int
    metadata: pd.Series


def logical_manifest(paths: Sequence[str | Path]) -> pd.DataFrame:
    """Combine only manifest metadata and assign stable global condition IDs."""

    if not paths:
        raise ValueError("at least one manifest path is required")
    rows: list[dict[str, object]] = []
    seen: set[tuple[int, int, str]] = set()
    for path in paths:
        manifest = read_manifest(path)
        source = str(Path(manifest.attrs["manifest_path"]).resolve())
        for item in manifest.to_dict("records"):
            key = (int(item["L"]), int(item["C"]), str(item["budget_mode"]))
            if key in seen:
                raise ValueError(f"duplicate logical condition L={key[0]}, C={key[1]}, mode={key[2]}")
            seen.add(key)
            item["source_manifest"] = source
            item["source_condition_index"] = int(item["condition_index"])
            item["global_condition_id"] = len(rows)
            rows.append(item)
    return pd.DataFrame(rows)


def iter_conditions(paths: Sequence[str | Path]) -> Iterator[ManifestCondition]:
    metadata = logical_manifest(paths)
    for _, row in metadata.iterrows():
        yield ManifestCondition(
            int(row["global_condition_id"]),
            str(row["source_manifest"]),
            int(row["source_condition_index"]),
            row.copy(),
        )


def read_condition(condition: ManifestCondition, *, validate: bool = True) -> pd.DataFrame:
    """Read one results CSV, validate it, and replace local with global ID."""

    row = condition.metadata.copy()
    row["condition_index"] = condition.source_condition_index
    columns = [column for column in row.index if column in MANIFEST_COLUMNS or column in (
        "stop_mode", "transition_threshold_multiplier", "edge_trace_path"
    )]
    one = pd.DataFrame([{column: row[column] for column in columns}])
    one.attrs["manifest_path"] = condition.source_manifest
    results = read_results(one)
    if validate:
        validate_sweep(one, results)
    results = results.copy()
    results["condition_index"] = condition.global_condition_id
    results["global_condition_id"] = condition.global_condition_id
    results["source_condition_index"] = condition.source_condition_index
    results["source_manifest"] = condition.source_manifest
    return results
