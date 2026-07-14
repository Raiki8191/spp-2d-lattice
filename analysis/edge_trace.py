"""Loading and structural validation for exact edge-removal traces."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


EDGE_TRACE_COLUMNS = (
    "run",
    "edge_order",
    "step",
    "edge_index_in_request",
    "path_length",
    "edge_id",
    "source",
    "target",
    "seed",
)


def read_edge_traces(manifest: pd.DataFrame) -> pd.DataFrame:
    """Read all optional manifest edge traces and reject malformed deletion order."""

    if manifest is None:
        raise ValueError("manifest must not be None")
    if "edge_trace_path" not in manifest.columns:
        raise ValueError("manifest has no edge_trace_path column; regenerate the sweep")

    frames: list[pd.DataFrame] = []
    for condition in manifest.itertuples(index=False):
        path = Path(str(condition.edge_trace_path))
        if not path.is_file():
            raise FileNotFoundError(
                f"edge trace CSV does not exist for condition={condition.condition_index}: {path}"
            )
        trace = pd.read_csv(path, encoding="utf-8")
        missing = [column for column in EDGE_TRACE_COLUMNS if column not in trace.columns]
        if missing:
            raise ValueError(f"edge trace {path} is missing columns: {', '.join(missing)}")
        trace = trace.loc[:, EDGE_TRACE_COLUMNS].copy()
        for column in EDGE_TRACE_COLUMNS:
            numeric = pd.to_numeric(trace[column], errors="raise")
            if numeric.isna().any() or (numeric % 1 != 0).any():
                raise ValueError(f"edge trace column {column!r} must be integer-valued")
            trace[column] = numeric.astype("int64")
        trace["condition_index"] = int(condition.condition_index)
        trace["L"] = int(condition.L)
        trace["C"] = int(condition.C)
        trace["budget_mode"] = str(condition.budget_mode)
        trace["runs"] = int(condition.runs)
        trace["edge_trace_path"] = str(path.resolve())
        _validate_condition_trace(trace, condition)
        frames.append(trace)

    if not frames:
        return pd.DataFrame(columns=EDGE_TRACE_COLUMNS + ("condition_index",))
    return pd.concat(frames, ignore_index=True)


def validate_trace_against_results(
    manifest: pd.DataFrame, results: pd.DataFrame, traces: pd.DataFrame
) -> None:
    """Check final trace counts and seeds against the ordinary results CSV."""

    for condition in manifest.itertuples(index=False):
        condition_results = results.loc[
            results["condition_index"] == int(condition.condition_index)
        ]
        condition_trace = traces.loc[
            traces["condition_index"] == int(condition.condition_index)
        ]
        for run in range(int(condition.runs)):
            run_results = condition_results.loc[condition_results["run"] == run]
            if run_results.empty:
                raise ValueError(
                    f"results missing condition={condition.condition_index}, run={run}"
                )
            final_removed = int(run_results.sort_values("step").iloc[-1]["removed_edges"])
            run_trace = condition_trace.loc[condition_trace["run"] == run]
            if len(run_trace) != final_removed:
                raise ValueError(
                    "trace row count does not match final removed_edges at "
                    f"condition={condition.condition_index}, run={run}: "
                    f"trace={len(run_trace)}, removed_edges={final_removed}"
                )
            if not run_trace.empty:
                expected_seed = int(run_results.iloc[0]["seed"])
                if not (run_trace["seed"] == expected_seed).all():
                    raise ValueError(
                        f"trace seed mismatch at condition={condition.condition_index}, run={run}"
                    )


def edge_endpoints(lattice_size: int, edge_id: int) -> tuple[int, int]:
    """Return endpoints for Java's horizontal-first, row-major edge IDs."""

    edge_count = 2 * lattice_size * (lattice_size - 1)
    if not 0 <= edge_id < edge_count:
        raise ValueError(f"edge_id out of range for L={lattice_size}: {edge_id}")
    horizontal_count = lattice_size * (lattice_size - 1)
    if edge_id < horizontal_count:
        row, column = divmod(edge_id, lattice_size - 1)
        left = row * lattice_size + column
        return left, left + 1
    row, column = divmod(edge_id - horizontal_count, lattice_size)
    top = row * lattice_size + column
    return top, top + lattice_size


def _validate_condition_trace(trace: pd.DataFrame, condition: object) -> None:
    if trace.empty:
        return
    bad_run = ~trace["run"].between(0, int(condition.runs) - 1)
    if bad_run.any():
        raise ValueError(f"trace run out of range for condition={condition.condition_index}")
    maximum_edge_id = 2 * int(condition.L) * (int(condition.L) - 1) - 1
    bad_edge = ~trace["edge_id"].between(0, maximum_edge_id)
    if bad_edge.any():
        row = trace.loc[bad_edge].iloc[0]
        raise ValueError(
            f"edge_id out of range at condition={condition.condition_index}, "
            f"run={int(row['run'])}, edge_id={int(row['edge_id'])}"
        )
    for run, run_trace in trace.groupby("run", sort=False):
        ordered = run_trace.sort_values("edge_order")
        expected = np.arange(len(ordered), dtype=np.int64)
        if not np.array_equal(ordered["edge_order"].to_numpy(), expected):
            raise ValueError(
                f"edge_order must be contiguous from zero at condition={condition.condition_index}, run={run}"
            )
        if ordered["edge_id"].duplicated().any():
            raise ValueError(
                f"duplicate edge_id at condition={condition.condition_index}, run={run}"
            )
        for step, request in ordered.groupby("step", sort=False):
            lengths = request["path_length"].unique()
            if len(lengths) != 1 or int(lengths[0]) != len(request):
                raise ValueError(
                    f"path_length mismatch at condition={condition.condition_index}, run={run}, step={step}"
                )
            expected_indices = np.arange(len(request), dtype=np.int64)
            actual_indices = request.sort_values("edge_index_in_request")[
                "edge_index_in_request"
            ].to_numpy()
            if not np.array_equal(actual_indices, expected_indices):
                raise ValueError(
                    f"edge_index_in_request is invalid at condition={condition.condition_index}, run={run}, step={step}"
                )
