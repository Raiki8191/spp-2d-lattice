from pathlib import Path

import pandas as pd
import pytest

from analysis.unbounded_l320_preregistration import MODELS, generate


def test_real_v5_preregistration_is_complete_and_reproducible(tmp_path: Path):
    first = generate(tmp_path / "first.csv", forbid_l320=tmp_path / "absent")
    second = generate(tmp_path / "second.csv", forbid_l320=tmp_path / "absent")
    assert len(first) == 24
    assert set(first.model) == set(MODELS)
    assert set(first.target_L) == {320}
    assert first.groupby("observable").size().eq(4).all()
    stable = [column for column in first if column != "generation_timestamp_utc"]
    pd.testing.assert_frame_equal(first[stable], second[stable])


def test_refuses_to_preregister_after_l320_output_exists(tmp_path: Path):
    observed = tmp_path / "unbounded-l320"
    observed.mkdir()
    with pytest.raises(RuntimeError, match="must precede observation"):
        generate(tmp_path / "predictions.csv", forbid_l320=observed)
