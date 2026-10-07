"""Resolve corrected uncertainty without silently falling back to superseded fits."""
from pathlib import Path

def corrected_unbounded_intervals(version: str, *, output_root: str | Path = "app/out") -> Path:
    if version not in {"v4","v5","v6","v7"}:
        raise ValueError("version must be v4, v5, v6, or v7")
    path = Path(output_root) / f"unbounded-{version}-bootstrap-corrected" / "unbounded_bootstrap_intervals.csv"
    if not path.is_file():
        raise FileNotFoundError(
            f"Corrected bootstrap required: {path}. Generate correction products; "
            "superseded quick-bootstrap intervals cannot be used as current uncertainty."
        )
    return path
