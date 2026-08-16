#!/usr/bin/env python3
"""
Fetch East River / WQP water quality data.

REAL DATA ONLY: requires Saccardi_and_Winnick_Data.xlsx; fails if missing.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import requests

from src.east_river_real_data import real_data_available, write_real_dataset
from src.real_data_guard import RealDataRequiredError, require_real_data
from src.usgs_download import load_or_download_gage
from src.utils import ensure_dirs, load_config, resolve_path, setup_logging

LOG = setup_logging("fetch_wq")

HYDROSHARE_RESOURCES = {
    "east_river": "9f907b46baa848e180c49339d605bf31",
    "dic_supplement": "2a2132999fb84214aad0596783812db2",
}


def download_hydroshare_resource(resource_id: str, out_dir: Path) -> list[Path]:
    """Download all public files for a HydroShare resource via hsapi."""
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    api = f"https://www.hydroshare.org/hsapi/resource/{resource_id}/files/"
    try:
        resp = requests.get(api, timeout=120)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        LOG.warning("HydroShare file list failed for %s: %s", resource_id, exc)
        return saved
    for item in payload.get("results", []):
        fname = item.get("file_name")
        url = item.get("url")
        if not fname or not url:
            continue
        dest = out_dir / fname
        if dest.exists() and dest.stat().st_size > 0:
            saved.append(dest)
            continue
        try:
            dl_url = url if url.startswith("http") else f"https://www.hydroshare.org{url}"
            r = requests.get(dl_url, timeout=600)
            r.raise_for_status()
            dest.write_bytes(r.content)
            saved.append(dest)
            LOG.info("Downloaded HydroShare file: %s (%d bytes)", dest, dest.stat().st_size)
        except requests.RequestException as exc:
            LOG.warning("Failed to download %s: %s", fname, exc)
    return saved


def fetch_hydroshare_metadata(resource_id: str, out_dir: Path) -> bool:
    """Download resource landing page metadata (full bagit requires HS auth)."""
    url = f"https://www.hydroshare.org/resource/{resource_id}/"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        meta_path = out_dir / f"hydroshare_{resource_id}_landing.html"
        meta_path.write_text(resp.text[:50000], encoding="utf-8")
        LOG.info("Saved HydroShare landing page metadata: %s", meta_path)
        return True
    except requests.RequestException as exc:
        LOG.warning("HydroShare fetch failed for %s: %s", resource_id, exc)
        return False


def fetch_wqp_documentation(out_dir: Path) -> None:
    """Document WQP query; existing HUC download used if present."""
    template = pd.DataFrame(
        [
            {
                "api": "https://www.waterqualitydata.us/data/Result/search",
                "characteristicName": "pH,Dissolved oxygen,Temperature,DOC,Alkalinity",
                "huc": "14020001",
                "mimeType": "csv",
                "note": "Download lacks lat/lon; site filter requires MonitoringLocation export",
            }
        ]
    )
    template.to_csv(out_dir / "wqp_query_template.csv", index=False)


def prefetch_usgs(cfg: dict) -> None:
    """Ensure USGS East River gage covers campaign window."""
    from src.east_river_real_data import load_hydroshare_samples

    samples = load_hydroshare_samples(cfg)
    dmin = samples["date"].min().strftime("%Y-%m-%d")
    dmax = samples["date"].max().strftime("%Y-%m-%d")
    site = cfg.get("usgs", {}).get("east_river_gage", "09112500")
    load_or_download_gage(cfg, site, dmin, dmax)


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    require_real_data(cfg, "01_fetch_water_quality")
    ensure_dirs(cfg)
    raw_er = resolve_path(cfg, "data_raw") / "east_river"
    raw_wqp = resolve_path(cfg, "data_raw") / "wqp"

    for name, rid in HYDROSHARE_RESOURCES.items():
        sub = raw_er / ("east_river" if name == "east_river" else "dic_supplement")
        sub.mkdir(parents=True, exist_ok=True)
        download_hydroshare_resource(rid, sub)
        fetch_hydroshare_metadata(rid, sub)

    fetch_wqp_documentation(raw_wqp)

    if not real_data_available(cfg):
        raise RealDataRequiredError(
            "Saccardi_and_Winnick_Data.xlsx not found. "
            "Download from https://www.hydroshare.org/resource/9f907b46baa848e180c49339d605bf31/ "
            "and place under data_raw/east_river/."
        )

    prefetch_usgs(cfg)
    paths = write_real_dataset(cfg)
    LOG.info("Real HydroShare campaign dataset: %s", paths["observations"])
    LOG.info("Provenance: %s", paths["provenance"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch water quality / East River data (real only)")
    parser.add_argument("--config", default=None, help="Path to YAML config")
    args = parser.parse_args()
    main(args.config)
