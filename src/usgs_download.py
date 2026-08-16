"""Download and cache USGS discharge for East River study period."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils import resolve_path, setup_logging

LOG = setup_logging("usgs_download")

CFS_TO_M3S = 0.0283168

# Gages cited in Saccardi & Winnick (2021) East River work
USGS_GAGES = {
    "09112500": {
        "name": "East River at Almont, CO",
        "reaches": ["East River"],
    },
    "09111250": {
        "name": "Coal Creek near Crested Butte, CO",
        "reaches": [],  # auxiliary; not a modeled reach
    },
}


def _parse_nwis_daily(df: pd.DataFrame, site: str) -> pd.DataFrame:
    """Normalize NWIS daily discharge to date, Q_m3s."""
    if df.empty:
        return pd.DataFrame(columns=["date", "Q_m3s", "site_no"])
    out = df.reset_index()
    date_col = "datetime" if "datetime" in out.columns else out.columns[0]
    out["date"] = pd.to_datetime(out[date_col], utc=True).dt.tz_convert(None).dt.normalize()
    q_col = next((c for c in out.columns if c.startswith("00060")), None)
    if q_col is None:
        raise ValueError(f"No discharge column in NWIS response for {site}")
    out["Q_m3s"] = pd.to_numeric(out[q_col], errors="coerce") * CFS_TO_M3S
    out["site_no"] = site
    return out[["date", "Q_m3s", "site_no"]].dropna(subset=["Q_m3s"])


def download_usgs_daily(
    site: str,
    start: str,
    end: str,
    out_dir: Path,
) -> pd.DataFrame:
    """Fetch daily mean discharge via dataretrieval; cache CSV."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = out_dir / f"{site}_discharge_daily_{start[:4]}.csv"
    if cache.exists() and cache.stat().st_size > 0:
        q = pd.read_csv(cache, parse_dates=["date"])
        q["date"] = pd.to_datetime(q["date"], utc=True).dt.tz_convert(None).dt.normalize()
        LOG.info("Loaded cached USGS %s: %d days", site, len(q))
        return q

    try:
        from dataretrieval import nwis
    except ImportError as exc:
        raise RuntimeError("dataretrieval package required for USGS download") from exc

    LOG.info("Downloading USGS %s (%s to %s)", site, start, end)
    try:
        raw = nwis.get_record(
            sites=site,
            service="dv",
            start=start,
            end=end,
            parameterCd="00060",
        )
    except Exception as exc:
        raise RuntimeError(f"USGS download failed for {site}: {exc}") from exc

    q = _parse_nwis_daily(raw, site)
    if q.empty:
        raise RuntimeError(f"USGS returned no discharge for {site} ({start}–{end})")
    q.to_csv(cache, index=False)
    LOG.info("Saved USGS %s -> %s (%d rows)", site, cache, len(q))
    return q


def load_or_download_gage(
    cfg: dict,
    site: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Load cached USGS CSV or download."""
    usgs_dir = resolve_path(cfg, "data_raw") / "usgs"
    return download_usgs_daily(site, start, end, usgs_dir)


def q_on_date(q_daily: pd.DataFrame, date: pd.Timestamp) -> float | None:
    """Lookup discharge on a calendar date."""
    d = pd.Timestamp(date).normalize()
    match = q_daily[q_daily["date"] == d]
    if match.empty:
        return None
    return float(match["Q_m3s"].iloc[0])
