from __future__ import annotations

import csv
from pathlib import Path

import pytest

from analysis.io import MANIFEST_COLUMNS, RESULT_COLUMNS


@pytest.fixture
def make_sweep():
    def create(
        root: Path,
        *,
        conditions: list[dict[str, object]] | None = None,
        runs: int = 1,
        measurement_mode: str = "STEP_INTERVAL",
    ) -> Path:
        definitions = conditions or [
            {"condition_index": 0, "L": 2, "C": 1, "budget_mode": "FINITE"}
        ]
        manifest_rows: list[dict[str, object]] = []
        for definition in definitions:
            condition_index = int(definition["condition_index"])
            lattice_size = int(definition["L"])
            budget = int(definition["C"])
            relative_path = f"L={lattice_size}/C={budget}/results.csv"
            manifest_rows.append(
                {
                    "condition_index": condition_index,
                    "L": lattice_size,
                    "C": budget,
                    "budget_mode": definition["budget_mode"],
                    "runs": runs,
                    "max_steps": 2,
                    "measurement_mode": measurement_mode,
                    "measurement_interval": 1,
                    "base_seed": 42,
                    "result_path": relative_path,
                }
            )
            initial_edges = 2 * lattice_size * (lattice_size - 1)
            vertex_count = lattice_size**2
            result_rows: list[dict[str, object]] = []
            for run in range(runs):
                result_rows.extend(
                    [
                        {
                            "run": run,
                            "L": lattice_size,
                            "C": budget,
                            "step": 0,
                            "removed_edges": 0,
                            "remaining_edges": initial_edges,
                            "removed_edge_fraction": 0.0,
                            "largest_cluster_size": vertex_count,
                            "largest_cluster_fraction": 1.0,
                            "second_largest_cluster_size": 0,
                            "mean_cluster_size": 0.0,
                            "accepted_requests": 0,
                            "rejected_requests": 0,
                            "seed": 100 + run,
                        },
                        {
                            "run": run,
                            "L": lattice_size,
                            "C": budget,
                            "step": 1,
                            "removed_edges": 1,
                            "remaining_edges": initial_edges - 1,
                            "removed_edge_fraction": 1 / initial_edges,
                            "largest_cluster_size": vertex_count,
                            "largest_cluster_fraction": 1.0,
                            "second_largest_cluster_size": 0,
                            "mean_cluster_size": 0.0,
                            "accepted_requests": 1,
                            "rejected_requests": 0,
                            "seed": 100 + run,
                        },
                    ]
                )
            _write_csv(root / relative_path, RESULT_COLUMNS, result_rows)

        manifest_path = root / "manifest.csv"
        _write_csv(manifest_path, MANIFEST_COLUMNS, manifest_rows)
        return manifest_path

    return create


def _write_csv(
    path: Path, columns: tuple[str, ...], rows: list[dict[str, object]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

