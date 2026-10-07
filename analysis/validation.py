"""Numerical and ordering validation for combined SPP sweep results."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from analysis.io import MANIFEST_COLUMNS, RESULT_COLUMNS


@dataclass(frozen=True)
class ValidationSummary:
    condition_count: int
    row_count: int
    run_count: int


def validate_sweep(
    manifest: pd.DataFrame,
    results: pd.DataFrame,
    *,
    rtol: float = 1.0e-9,
    atol: float = 1.0e-12,
) -> ValidationSummary:
    """Validate invariants and monotonicity, raising at the first bad row."""

    if manifest is None or results is None:
        raise ValueError("manifest and results must not be None")
    _require_columns(manifest, MANIFEST_COLUMNS, "manifest")
    _require_columns(
        results,
        RESULT_COLUMNS + ("condition_index", "budget_mode", "result_path"),
        "results",
    )

    _fail_first(
        results,
        ~np.isfinite(results.loc[:, RESULT_COLUMNS].to_numpy(float)).all(axis=1),
        "results contains a non-finite numeric value",
    )

    metadata = manifest.set_index("condition_index", drop=False)
    condition_ids = results["condition_index"]
    expected_L = condition_ids.map(metadata["L"])
    _fail_first(results, expected_L.isna(), "condition is not present in manifest")
    expected_C = condition_ids.map(metadata["C"])
    _fail_first(
        results,
        (results["L"] != expected_L) | (results["C"] != expected_C),
        "results L/C does not match manifest",
    )
    expected_runs = condition_ids.map(metadata["runs"])
    _fail_first(
        results,
        (results["run"] < 0) | (results["run"] >= expected_runs),
        "run is outside the manifest range",
    )
    _fail_first(
        results,
        results["accepted_requests"] + results["rejected_requests"] != results["step"],
        "accepted_requests + rejected_requests != step",
    )

    initial_edges = 2 * results["L"] * (results["L"] - 1)
    _fail_first(
        results,
        results["removed_edges"] + results["remaining_edges"] != initial_edges,
        "removed_edges + remaining_edges != 2L(L-1)",
    )
    expected_removed_fraction = np.divide(
        results["removed_edges"].to_numpy(float),
        initial_edges.to_numpy(float),
        out=np.zeros(len(results), dtype=float),
        where=initial_edges.to_numpy() != 0,
    )
    _fail_first(
        results,
        ~np.isclose(
            results["removed_edge_fraction"].to_numpy(float),
            expected_removed_fraction,
            rtol=rtol,
            atol=atol,
        ),
        "removed_edge_fraction does not match removed_edges / M0",
    )
    expected_largest_fraction = results["largest_cluster_size"] / (results["L"] ** 2)
    _fail_first(
        results,
        ~np.isclose(
            results["largest_cluster_fraction"].to_numpy(float),
            expected_largest_fraction.to_numpy(float),
            rtol=rtol,
            atol=atol,
        ),
        "largest_cluster_fraction does not match largest_cluster_size / L^2",
    )
    _fail_first(
        results,
        ~results["removed_edge_fraction"].between(0.0, 1.0),
        "removed_edge_fraction is outside [0, 1]",
    )
    _fail_first(
        results,
        ~results["largest_cluster_fraction"].between(0.0, 1.0),
        "largest_cluster_fraction is outside [0, 1]",
    )

    grouped = results.groupby(["condition_index", "run"], sort=False, dropna=False)
    for (condition_index, run), group in grouped:
        first = group.iloc[0]
        if int(first["step"]) != 0:
            _fail(first, "initial step 0 measurement is missing")
        if (
            int(first["removed_edges"]) != 0
            or int(first["accepted_requests"]) != 0
            or int(first["rejected_requests"]) != 0
            or int(first["largest_cluster_size"]) != int(first["L"]) ** 2
            or int(first["second_largest_cluster_size"]) != 0
            or float(first["mean_cluster_size"]) != 0.0
        ):
            _fail(first, "initial graph state does not match the intact lattice")
        _fail_first(group, group["seed"] != first["seed"], "seed changed within run")
        steps = group["step"].to_numpy(dtype=np.int64)
        if len(steps) > 1:
            bad = np.flatnonzero(np.diff(steps) <= 0)
            if bad.size:
                _fail(group.iloc[int(bad[0]) + 1], "step is not strictly increasing")

            removed = group["removed_edges"].to_numpy(dtype=np.int64)
            bad = np.flatnonzero(np.diff(removed) < 0)
            if bad.size:
                _fail(group.iloc[int(bad[0]) + 1], "removed_edges decreased")

            largest = group["largest_cluster_size"].to_numpy(dtype=np.int64)
            bad = np.flatnonzero(np.diff(largest) > 0)
            if bad.size:
                _fail(group.iloc[int(bad[0]) + 1], "largest_cluster_size increased")

            mode = str(metadata.loc[int(condition_index), "measurement_mode"])
            if mode == "ACCEPTED_REQUEST" and len(removed) > 2:
                # The last row may be an unchanged final snapshot after a rejected request.
                bad = np.flatnonzero(np.diff(removed)[:-1] <= 0)
                if bad.size:
                    _fail(
                        group.iloc[int(bad[0]) + 1],
                        "ACCEPTED_REQUEST measurement did not increase removed_edges",
                    )

    vertex_count = results["L"] ** 2
    largest = results["largest_cluster_size"]
    second = results["second_largest_cluster_size"]
    connected = largest == vertex_count
    _fail_first(
        results,
        (largest < 1) | (largest > vertex_count) | (second < 0)
        | (second > largest) | (largest + second > vertex_count)
        | (connected & (second != 0)) | (~connected & (second < 1)),
        "impossible cluster sizes",
    )
    mean = results["mean_cluster_size"]
    _fail_first(
        results,
        (mean < 0.0) | (connected & ~np.isclose(mean, 0.0, rtol=rtol, atol=atol))
        | (~connected & ((mean < 1.0 - atol) | (mean > second + atol))),
        "mean_cluster_size is inconsistent with finite cluster size bounds",
    )
    for condition in manifest.itertuples(index=False):
        data = results.loc[results["condition_index"] == condition.condition_index]
        actual = set(int(value) for value in data["run"].unique())
        expected = set(range(int(condition.runs)))
        if actual != expected:
            raise ValueError(
                f"run IDs do not match manifest at condition={int(condition.condition_index)}: "
                f"expected {sorted(expected)}, observed {sorted(actual)}"
            )
        starts = data.groupby("run", sort=True).first()
        if starts["seed"].duplicated().any():
            raise ValueError(
                f"duplicate run seed at condition={int(condition.condition_index)}"
            )

    return ValidationSummary(
        condition_count=int(results["condition_index"].nunique()),
        row_count=len(results),
        run_count=int(grouped.ngroups),
    )


def _require_columns(frame: pd.DataFrame, required: tuple[str, ...], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(missing)}")


def _fail(row: object, message: str) -> None:
    def value(name: str) -> object:
        if isinstance(row, pd.Series):
            return row[name]
        return getattr(row, name)

    raise ValueError(
        f"{message} at condition={int(value('condition_index'))}, "
        f"run={int(value('run'))}, step={int(value('step'))}"
    )


def _fail_first(results: pd.DataFrame, mask: object, message: str) -> None:
    bad = np.flatnonzero(np.asarray(mask, dtype=bool))
    if bad.size:
        _fail(results.iloc[int(bad[0])], message)
