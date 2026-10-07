"""Correct only the scaling-v3 joint/shift bootstrap products.

Existing completed outputs remain historical evidence. This command requires a
new directory and reproduces the original run draws and fixed seed.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import time

for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_name] = "1"

import numpy as np
import pandas as pd
from analysis import scaling_v3 as v3

METRICS = ("P_before", "P_after", "S_before", "S_after", "std_p_mid",
           "delta_P_request", "transition_delta_p")


def advance_primary_draws(
    events: pd.DataFrame, widths: pd.DataFrame, *, samples: int, seed: int,
) -> np.random.Generator:
    """Consume precisely the draws that precede the historical joint branch."""
    rng = np.random.default_rng(seed)
    for label in ("C=1", "C=2", "UNBOUNDED"):
        for observable in METRICS:
            frame = widths if observable == "transition_delta_p" else events
            source = frame.loc[
                (frame["budget_mode"] == "UNBOUNDED") if label == "UNBOUNDED"
                else ((frame["budget_mode"] == "FINITE") & (frame["C"] == int(label[-1])))
            ]
            if source.empty:
                continue
            counts = [len(group) for _, group in source.groupby("L", sort=True)]
            for _ in range(samples):
                for count in counts:
                    rng.integers(0, count, count)
    return rng


def draw_joint_statistics(
    events: pd.DataFrame, *, samples: int, rng: np.random.Generator,
) -> list[dict[str, list[tuple[np.ndarray, np.ndarray]]]]:
    finite = events.loc[(events["budget_mode"] == "FINITE") & events["C"].isin([1, 2])]
    statistics = []
    for _ in range(samples):
        aggregates = {}
        for C in (1, 2):
            pieces = []
            for L, group in finite.loc[finite["C"] == C].groupby("L", sort=True):
                pieces.append(group.iloc[rng.integers(0, len(group), len(group))].assign(_L=L))
            aggregates[C] = pd.concat(pieces, ignore_index=True)
        statistics.append(v3.joint_shift_statistics(aggregates))
    return statistics


def _fit_sample(item: tuple[int, dict]) -> list[dict[str, object]]:
    sample, statistics = item
    return v3.fit_joint_shift_statistics(statistics, sample=sample)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_correction(
    source: Path, output: Path, *, samples: int = 500, seed: int = 20260720,
    workers: int = 4,
) -> None:
    if output.exists():
        raise FileExistsError(f"correction output must not exist: {output}")
    if samples < 1 or not 1 <= workers <= 4:
        raise ValueError("positive samples and one to four workers required")
    started = time.monotonic()
    inputs = [source / "request_event_runs.csv", source / "transition_width_runs.csv"]
    original_dir = source.parent / "scaling-v3-analysis"
    for name in ("universality_model_fits.csv", "pseudocritical_shift_corrections.csv",
                 "bootstrap_distributions.csv", "bootstrap_intervals.csv"):
        if (original_dir / name).exists():
            inputs.append(original_dir / name)
    hashes = {str(path): _sha(path) for path in inputs}
    events = pd.read_csv(source / "request_event_runs.csv")
    widths = pd.read_csv(source / "transition_width_runs.csv")
    statistics = draw_joint_statistics(
        events, samples=samples,
        rng=advance_primary_draws(events, widths, samples=samples, seed=seed),
    )
    output.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256()
    for item in statistics:
        for observable in item:
            for L, y in item[observable]:
                digest.update(L.tobytes()); digest.update(y.tobytes())
    chunks = []
    jobs = list(enumerate(statistics))
    if workers == 1:
        iterator = map(_fit_sample, jobs)
        for sample, rows in enumerate(iterator):
            chunks.extend(rows)
            if (sample+1) % 10 == 0 or sample+1 == samples:
                pd.DataFrame(chunks).to_csv(output / "bootstrap_distributions_partial.csv", index=False)
                print(f"joint/shift completed {sample+1}/{samples}, elapsed={time.monotonic()-started:.1f}s", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for sample, rows in enumerate(pool.map(_fit_sample, jobs, chunksize=1)):
                chunks.extend(rows)
                if (sample+1) % 10 == 0 or sample+1 == samples:
                    pd.DataFrame(chunks).to_csv(output / "bootstrap_distributions_partial.csv", index=False)
                    print(f"joint/shift completed {sample+1}/{samples}, elapsed={time.monotonic()-started:.1f}s", flush=True)
    corrected = pd.DataFrame(chunks)
    corrected["bootstrap_seed"] = seed
    corrected.to_csv(output / "bootstrap_distributions.csv", index=False)
    intervals = v3.summarize_bootstrap(corrected)
    intervals.to_csv(output / "bootstrap_intervals.csv", index=False)
    if (original_dir / "bootstrap_intervals.csv").exists():
        old = pd.read_csv(original_dir / "bootstrap_intervals.csv")
        keys = ["condition_label", "observable", "model", "parameter"]
        comparison = intervals.merge(old, on=keys, how="left", suffixes=("_corrected", "_superseded"),
                                     validate="one_to_one")
        comparison.to_csv(output / "interval_comparison.csv", index=False)
    if hashes != {str(path): _sha(path) for path in inputs}:
        raise RuntimeError("an input changed during bootstrap correction")
    provenance = {
        "status": "CORRECTED", "source": str(source), "samples": samples,
        "seed": seed, "workers": workers, "elapsed_seconds": time.monotonic()-started,
        "source_hashes": hashes, "draw_statistics_sha256": digest.hexdigest(),
        "model_mapping": {"U1_C1": "U1_independent/exponent_c1",
                          "U1_C2": "U1_independent/exponent_c2",
                          "U2_shared_exponent": "U2_shared_exponent/exponent",
                          "U3_shared_exponent_omega_fixed_1": "U3_shared_exponent_omega_1/exponent",
                          "C=1 corrected_shift_omega_fixed_1": "corrected_shift_pc_0.5_omega_1",
                          "C=2 corrected_shift_omega_fixed_1": "corrected_shift_free_pc_omega_1"},
        "estimator": "same bounded original-scale multistart as corresponding point estimator",
        "interval": "2.5/97.5 percentiles among converged samples; boundaries retained",
        "resampling": "condition/L run draws; the same joint draw used for all observables",
        "unchanged": "raw data, preregistration, point fits, finite-primary intervals, UNBOUNDED corrected products",
        "superseded": "only joint and corrected-shift rows in scaling-v3-analysis/bootstrap_{distributions,intervals}.csv",
    }
    (output / "correction_provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf8")
    print(f"joint/shift corrected rows={len(corrected)}, failures={int((~corrected.converged).sum())}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("app/out/scaling-v2-analysis"))
    parser.add_argument("--output", type=Path, default=Path("app/out/scaling-v3-joint-shift-bootstrap-corrected"))
    parser.add_argument("--bootstrap-samples", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260720)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    run_correction(args.source, args.output, samples=args.bootstrap_samples, seed=args.seed, workers=args.workers)


if __name__ == "__main__":
    main()
