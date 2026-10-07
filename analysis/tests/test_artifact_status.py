from pathlib import Path
import pytest
from analysis.artifact_status import corrected_unbounded_intervals

def test_corrected_history_never_falls_back_to_old_intervals(tmp_path):
    legacy=tmp_path/"unbounded-v5";legacy.mkdir()
    (legacy/"unbounded_bootstrap_intervals.csv").write_text("old quick intervals")
    with pytest.raises(FileNotFoundError,match="Corrected bootstrap required"):
        corrected_unbounded_intervals("v5",output_root=tmp_path)

def test_corrected_history_selects_corrected_file_with_old_present(tmp_path):
    old=tmp_path/"unbounded-v4"/"main50";old.mkdir(parents=True)
    (old/"unbounded_bootstrap_intervals.csv").write_text("obsolete")
    new=tmp_path/"unbounded-v4-bootstrap-corrected";new.mkdir()
    target=new/"unbounded_bootstrap_intervals.csv";target.write_text("corrected")
    assert corrected_unbounded_intervals("v4",output_root=tmp_path)==target

def test_unknown_version_is_rejected():
    with pytest.raises(ValueError):
        corrected_unbounded_intervals("../raw")
