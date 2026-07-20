from pathlib import Path

import pandas as pd
import pytest

from analysis.unbounded_l384_preregistration import generate


def test_preregistration_is_reproducible_and_excludes_l384(tmp_path):
    first = generate(tmp_path / "first.csv", forbid_l384=tmp_path / "absent")
    second = generate(tmp_path / "second.csv", forbid_l384=tmp_path / "absent")
    pd.testing.assert_frame_equal(first, second)
    assert set(first.target_L) == {384}
    assert first.used_L.str.split(";").apply(lambda values: max(map(int, values))).max() == 320
    assert (first.largest_observed_L == 320).all()
    assert set(first.model) == {"zero_power", "finite_power", "zero_log", "finite_log"}


def test_preregistration_refuses_observed_l384(tmp_path):
    observed = tmp_path / "unbounded-l384"
    observed.mkdir()
    with pytest.raises(RuntimeError, match="must precede observation"):
        generate(tmp_path / "forbidden.csv", forbid_l384=observed)
    assert not (tmp_path / "forbidden.csv").exists()
