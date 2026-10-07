"""The affected-only producer must retain undefined inference on failed fits."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analysis import scaling_v2_bootstrap_correction as correction


class InlinePool:
    """Keep synthetic producer tests local; production retains its process pool."""
    def __init__(self, *, max_workers):
        self.max_workers = max_workers

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def map(self, fn, tasks):
        return map(fn, tasks)


def _synthetic_source(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    sizes = [8, 12, 16, 24]
    runs = pd.DataFrame([
        {"budget_mode": "UNBOUNDED", "L": size,
         "delta_P_max": .2 + .01 * run + 1 / size}
        for size in sizes for run in range(3)
    ])
    runs.to_csv(source / "request_event_runs.csv", index=False)
    runs.groupby(["budget_mode", "L"], as_index=False).delta_P_max.mean().rename(
        columns={"delta_P_max": "delta_P_max_mean"}
    ).to_csv(source / "request_event_summary.csv", index=False)
    pd.DataFrame([{"L_min": 8, "bootstrap_low": .1,
                   "bootstrap_high": .3}]).to_csv(
        source / "unbounded_model_bootstrap.csv", index=False
    )
    pd.DataFrame([{"L_min": 8, "model": "finite_power"}]).to_csv(
        source / "unbounded_model_fits.csv", index=False
    )
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in source.iterdir()}
    return source, hashes, runs


@pytest.mark.parametrize("limit", [None, 0.0, .2])
def test_generator_failed_interval_is_undefined_and_valid_flags_preserved(
    tmp_path, monkeypatch, limit
):
    source, hashes, runs = _synthetic_source(tmp_path)
    seen = []

    def synthetic_fit(L, y):
        seen.append((L.copy(), y.copy()))
        if limit is None:
            raise RuntimeError("deliberate all-starts failure")
        return {"parameters": np.array([limit, .2, .7]),
                "rss": .001, "aicc": 2.0, "bic": 3.0}

    monkeypatch.setattr(correction, "L_MINS", [8])
    monkeypatch.setattr(correction, "ProcessPoolExecutor", InlinePool)
    monkeypatch.setattr(correction, "_bootstrap_finite_power_fit", synthetic_fit)
    output = tmp_path / "corrected"
    boot = correction.regenerate(source, output, samples=2, seed=9, workers=1)
    persisted = pd.read_csv(output / "unbounded_model_bootstrap.csv")
    comparison = pd.read_csv(output / "bootstrap_correction_comparison.csv")
    assert boot["sample"].tolist() == [0, 1]
    assert len(seen) == 2
    rng = np.random.default_rng(np.random.SeedSequence([9, 8, 991]))
    sizes = np.array([8, 12, 16, 24], float)
    groups = {int(L): g.delta_P_max.to_numpy(float)
              for L, g in runs.groupby("L")}
    for L, y in seen:
        expected = [rng.choice(groups[int(k)], len(groups[int(k)]),
                               replace=True).mean() for k in sizes]
        np.testing.assert_array_equal(L, sizes)
        np.testing.assert_allclose(y, expected, rtol=0, atol=1e-15)
    if limit is None:
        assert not boot["converged"].any()
        assert boot["failure"].eq("deliberate all-starts failure").all()
        assert boot[["limit", "bootstrap_low", "bootstrap_high",
                     "interval_includes_zero"]].isna().all().all()
        assert persisted[["limit", "bootstrap_low", "bootstrap_high",
                          "interval_includes_zero"]].isna().all().all()
        assert comparison.loc[0, "converged"] == 0
        assert comparison[["ci95_low", "ci95_high",
                           "zero_boundary_frequency"]].isna().all().all()
    else:
        assert boot["converged"].all()
        assert boot["interval_includes_zero"].eq(limit == 0).all()
        assert persisted["interval_includes_zero"].eq(limit == 0).all()
        np.testing.assert_array_equal(boot["bootstrap_low"], [limit, limit])
        np.testing.assert_array_equal(boot["bootstrap_high"], [limit, limit])
    for name, expected_hash in hashes.items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected_hash
    provenance = json.loads((output / "correction_provenance.json").read_text())
    assert provenance["input_sha256"] == hashes
    assert provenance["seed"] == 9
    assert provenance["samples"] == 2


def test_generator_refuses_to_overwrite_completed_output(tmp_path):
    output = tmp_path / "completed"
    output.mkdir()
    sentinel = output / "data.csv"
    sentinel.write_text("completed research data\n")
    with pytest.raises(FileExistsError):
        correction.regenerate(tmp_path / "missing_source", output, samples=2)
    assert sentinel.read_text() == "completed research data\n"
