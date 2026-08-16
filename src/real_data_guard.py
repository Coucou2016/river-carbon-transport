"""Enforce real-data-only policy across the pipeline."""

from __future__ import annotations

from pathlib import Path

from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("real_data_guard")


class RealDataRequiredError(RuntimeError):
    """Raised when real observations or downloads are missing."""


def real_data_only(cfg: dict | None = None) -> bool:
    """Return True when config enforces real data (default: True)."""
    if cfg is None:
        cfg = load_config()
    policy = cfg.get("data_policy", {})
    if policy.get("real_data_only", True):
        return True
    return not cfg.get("synthetic", {}).get("enabled", False)


def require_real_data(cfg: dict | None = None, context: str = "pipeline") -> None:
    """Fail loudly if synthetic/demo mode is requested."""
    if cfg is None:
        cfg = load_config()
    if not real_data_only(cfg):
        raise RealDataRequiredError(
            f"{context}: synthetic/demo mode is disabled. "
            "Set data_policy.real_data_only: false only for explicit offline testing."
        )


def require_file(path: Path, label: str) -> Path:
    """Require a real data file to exist."""
    if not path.exists() or path.stat().st_size == 0:
        raise RealDataRequiredError(
            f"Missing required real data: {label} ({path}). "
            "Download the source file and re-run stage 01."
        )
    return path


def assert_no_synthetic_provenance(proc_dir: Path) -> None:
    """Reject data_proc provenance that marks synthetic fallback."""
    prov_path = proc_dir / "data_provenance.csv"
    if not prov_path.exists():
        raise RealDataRequiredError(f"Missing data provenance: {prov_path}")
    import pandas as pd

    prov = pd.read_csv(prov_path)
    if "synthetic_fallback" in prov.columns and prov["synthetic_fallback"].astype(bool).any():
        bad = prov[prov["synthetic_fallback"].astype(bool)]
        raise RealDataRequiredError(
            "Provenance marks synthetic fallback for: "
            + ", ".join(bad["component"].astype(str).tolist())
        )
    if "source" in prov.columns and prov["source"].astype(str).str.contains("synthetic", case=False).any():
        raise RealDataRequiredError("Provenance contains synthetic source labels.")


def validate_processed_observations(obs_path: Path, min_rows: int = 1) -> int:
    """Ensure observation table exists and uses campaign samples only."""
    require_file(obs_path, "reach observations")
    import pandas as pd

    obs = pd.read_csv(obs_path, parse_dates=["date"])
    if len(obs) < min_rows:
        raise RealDataRequiredError(f"Too few observation rows ({len(obs)} < {min_rows}).")
    if "is_campaign_sample" in obs.columns and not obs["is_campaign_sample"].all():
        raise RealDataRequiredError(
            "Observation table contains non-campaign (interpolated) rows; "
            "forward-fill is not permitted in real-data-only mode."
        )
    return len(obs)
