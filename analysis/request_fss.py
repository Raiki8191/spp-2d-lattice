"""Request-level finite-size-scaling summaries and run bootstrap intervals."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from analysis.request_event import build_request_transitions, extract_request_events
from analysis.transition_width import calculate_transition_widths, summarize_transition_widths


EVENT_METRICS = (
    "p_before",
    "p_after",
    "p_mid",
    "delta_p_request",
    "P_before",
    "P_after",
    "delta_P_max",
    "S_before",
    "S_after",
    "path_length",
    "step",
)
BOOTSTRAP_METRICS = (
    "p_mid",
    "delta_P_max",
    "P_before",
    "P_after",
    "S_before",
    "S_after",
)
BOOTSTRAP_SEED = 20260715


def prepare_request_events(results: pd.DataFrame) -> pd.DataFrame:
    """Extract one maximum whole-request event for each condition and run."""

    if results is None:
        raise ValueError("results must not be None")
    transitions = build_request_transitions(results)
    events = extract_request_events(transitions).copy()
    events["p_mid"] = (events["p_before"] + events["p_after"]) / 2.0
    events["delta_P_max"] = events["delta_P_request"]
    columns = [
        "condition_index",
        "run",
        "L",
        "C",
        "budget_mode",
        *EVENT_METRICS,
    ]
    return events.loc[:, columns]


def summarize_request_fss(
    events: pd.DataFrame,
    *,
    bootstrap_samples: int = 2000,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> pd.DataFrame:
    """Summarize events and bootstrap run means independently per condition."""

    if events is None:
        raise ValueError("events must not be None")
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be positive")
    keys = ["condition_index", "L", "C", "budget_mode"]
    rows: list[dict[str, object]] = []
    for key_values, group in events.groupby(keys, sort=True):
        condition_index, L, C, budget_mode = key_values
        row: dict[str, object] = {
            "condition_index": int(condition_index),
            "L": int(L),
            "C": int(C),
            "budget_mode": str(budget_mode),
            "run_count": len(group),
            "bootstrap_samples": bootstrap_samples,
            "bootstrap_seed": bootstrap_seed,
        }
        for metric in EVENT_METRICS:
            values = group[metric].to_numpy(float)
            row[f"{metric}_mean"] = float(np.mean(values))
            row[f"{metric}_std"] = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
            row[f"{metric}_sem"] = row[f"{metric}_std"] / np.sqrt(len(values))
            row[f"{metric}_median"] = float(np.median(values))

        rng = np.random.default_rng(
            np.random.SeedSequence([bootstrap_seed, int(condition_index)])
        )
        indices = rng.integers(0, len(group), size=(bootstrap_samples, len(group)))
        for metric in BOOTSTRAP_METRICS:
            values = group[metric].to_numpy(float)
            bootstrap_means = values[indices].mean(axis=1)
            low, high = np.percentile(bootstrap_means, [2.5, 97.5])
            row[f"{metric}_bootstrap_low"] = float(low)
            row[f"{metric}_bootstrap_high"] = float(high)
        rows.append(row)
    return pd.DataFrame(rows)


def prepare_transition_width_summary(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    widths = calculate_transition_widths(results)
    return widths, summarize_transition_widths(widths)


def transition_completion_diagnostics(results: pd.DataFrame) -> pd.DataFrame:
    """Return per-run diagnostics for the requested transition window."""

    widths = calculate_transition_widths(results)
    events = prepare_request_events(results)
    event_keys = set(zip(events["condition_index"], events["run"]))
    rows: list[dict[str, object]] = []
    for (condition_index, run), group in results.groupby(
        ["condition_index", "run"], sort=True
    ):
        ordered = group.sort_values("step")
        final = ordered.iloc[-1]
        maximum_s = float(ordered["mean_cluster_size"].max())
        earlier = ordered.iloc[:-1]["mean_cluster_size"].to_numpy(float)
        width = widths.loc[
            (widths["condition_index"] == condition_index) & (widths["run"] == run)
        ].iloc[0]
        rows.append(
            {
                "condition_index": int(condition_index),
                "run": int(run),
                "L": int(final["L"]),
                "C": int(final["C"]),
                "budget_mode": str(final["budget_mode"]),
                "final_step": int(final["step"]),
                "final_P": float(final["largest_cluster_fraction"]),
                "transition_stop_present": float(final["largest_cluster_fraction"])
                <= 1.0 / int(final["L"]),
                "thresholds_crossed": bool(width["thresholds_crossed"]),
                "request_event_present": (condition_index, run) in event_keys,
                "S_max_before_final": bool(
                    np.isclose(earlier, maximum_s, atol=1.0e-12).any()
                ),
            }
        )
    return pd.DataFrame(rows)


def validate_transition_complete_results(results: pd.DataFrame) -> pd.DataFrame:
    """Require stop/event/threshold completeness and retain S-peak diagnostics."""

    diagnostics = transition_completion_diagnostics(results)
    for column, message in (
        ("transition_stop_present", "transition stop state is missing"),
        ("thresholds_crossed", "transition thresholds are incomplete"),
        ("request_event_present", "request-level event is missing"),
    ):
        invalid = diagnostics.loc[~diagnostics[column]]
        if not invalid.empty:
            row = invalid.iloc[0]
            raise ValueError(
                f"{message} at condition={int(row['condition_index'])}, "
                f"run={int(row['run'])}, step={int(row['final_step'])}"
            )
    return diagnostics


def write_fss_summaries(
    results: pd.DataFrame,
    output_directory: str | Path,
    *,
    bootstrap_samples: int = 2000,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)
    diagnostics = validate_transition_complete_results(results)
    events = prepare_request_events(results)
    request_summary = summarize_request_fss(
        events,
        bootstrap_samples=bootstrap_samples,
        bootstrap_seed=bootstrap_seed,
    )
    _, transition_summary = prepare_transition_width_summary(results)
    events.to_csv(root / "request_event_runs.csv", index=False, encoding="utf-8")
    request_summary.to_csv(
        root / "request_event_fss_summary.csv", index=False, encoding="utf-8"
    )
    transition_summary.to_csv(
        root / "transition_width_fss_summary.csv", index=False, encoding="utf-8"
    )
    diagnostics.to_csv(
        root / "transition_completion_diagnostics.csv", index=False, encoding="utf-8"
    )
    return events, request_summary, transition_summary
