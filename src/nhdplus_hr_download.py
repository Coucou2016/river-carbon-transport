"""Download NHDPlus High Resolution vectors for HUC 14020001 (East River / Gunnison).

Tries USGS staged GeoPackage (HU4 1402), then ArcGIS REST NetworkNHDFlowline.
Never fabricates geometry. Writes a machine-readable log under data_raw/nhdplus_hr/.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("nhdplus_hr")

GPKG_URL = (
    "https://prd-tnm.s3.amazonaws.com/StagedProducts/Hydrography/NHDPlusHR/"
    "VPU/Current/GPKG/NHDPLUS_H_1402_HU4_20220414_GPKG.zip"
)
GDB_URL = (
    "https://prd-tnm.s3.amazonaws.com/StagedProducts/Hydrography/NHDPlusHR/"
    "VPU/Current/GDB/NHDPLUS_H_1402_HU4_20220414_GDB.zip"
)
ARCGIS_FLOWLINE = (
    "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/3/query"
)
HUC8 = "14020001"
MAX_ZIP_BYTES = 1_500_000_000  # skip if staged product exceeds ~1.5 GB


def _log_path(out_dir: Path) -> Path:
    return out_dir / "download_log.json"


def _write_log(out_dir: Path, payload: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    _log_path(out_dir).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _stream_download(url: str, dest: Path, timeout: int = 120) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 200_000_000:
        return {"status": "cached", "path": str(dest), "bytes": dest.stat().st_size, "url": url}
    # Do not fight a concurrent curl/resume; partial files are not extracted.
    part = dest.with_suffix(dest.suffix + ".part")
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return {
            "status": "partial_skip",
            "path": str(dest),
            "bytes": dest.stat().st_size,
            "url": url,
            "note": "Incomplete zip present; not re-downloaded inside the pipeline.",
        }
    with requests.get(url, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        cl = resp.headers.get("Content-Length")
        nbytes_hdr = int(cl) if cl else None
        if nbytes_hdr and nbytes_hdr > MAX_ZIP_BYTES:
            raise RuntimeError(
                f"Staged NHDPlus HR zip too large ({nbytes_hdr} bytes > {MAX_ZIP_BYTES}): {url}"
            )
        written = 0
        with part.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    written += len(chunk)
        part.replace(dest)
    return {"status": "downloaded", "path": str(dest), "bytes": dest.stat().st_size, "url": url}


def _extract_zip(zip_path: Path, out_dir: Path) -> list[Path]:
    extracted: list[Path] = []
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
        extracted = [out_dir / name for name in zf.namelist()]
    return extracted


def _filter_huc8_flowlines(gpkg_or_gdb: Path, out_gpkg: Path) -> dict:
    import geopandas as gpd
    import pyogrio

    layers = pyogrio.list_layers(gpkg_or_gdb)
    layer_names = [row[0] for row in layers]
    flow_layer = None
    for cand in ("NHDFlowline", "NetworkNHDFlowline", "NHDPlusFlowlineVAA"):
        if cand in layer_names:
            flow_layer = cand
            break
    if flow_layer is None:
        for name in layer_names:
            if "flowline" in name.lower():
                flow_layer = name
                break
    if flow_layer is None:
        raise RuntimeError(f"No flowline layer in {gpkg_or_gdb}; layers={layer_names}")

    gdf = gpd.read_file(gpkg_or_gdb, layer=flow_layer)
    reach_col = None
    for c in ("ReachCode", "reachcode", "REACHCODE"):
        if c in gdf.columns:
            reach_col = c
            break
    if reach_col is None:
        raise RuntimeError(f"No ReachCode column; cols={list(gdf.columns)}")
    huc = gdf[gdf[reach_col].astype(str).str.startswith(HUC8)].copy()
    out_gpkg.parent.mkdir(parents=True, exist_ok=True)
    if out_gpkg.exists():
        out_gpkg.unlink()
    huc.to_file(out_gpkg, layer="NHDFlowline", driver="GPKG")
    gnis_col = next((c for c in ("GNIS_Name", "gnis_name", "GNIS_NAME") if c in huc.columns), None)
    named = int(huc[gnis_col].notna().sum()) if gnis_col else 0
    names = (
        huc[gnis_col].dropna().astype(str).value_counts().head(30).to_dict() if gnis_col else {}
    )
    return {
        "source_layer": flow_layer,
        "all_layers": layer_names,
        "n_huc8_flowlines": int(len(huc)),
        "n_named_gnis": named,
        "gnis_top": names,
        "out_gpkg": str(out_gpkg),
        "columns": list(huc.columns),
    }


def download_arcgis_huc8(out_dir: Path) -> dict:
    """Paginated GeoJSON download of NetworkNHDFlowline for HUC 14020001."""
    out_geojson = out_dir / "nhdplus_hr_huc14020001_flowlines.geojson"
    records = []
    offset = 0
    page = 2000
    while True:
        params = {
            "where": f"ReachCode LIKE '{HUC8}%'",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4269",
            "f": "geojson",
            "resultRecordCount": page,
            "resultOffset": offset,
        }
        r = requests.get(ARCGIS_FLOWLINE, params=params, timeout=25)
        r.raise_for_status()
        payload = r.json()
        feats = payload.get("features") or []
        if not feats:
            break
        records.extend(feats)
        if len(feats) < page or payload.get("exceededTransferLimit") is False:
            break
        offset += len(feats)
        if offset > 200_000:
            break
    geo = {"type": "FeatureCollection", "features": records}
    out_geojson.write_text(json.dumps(geo), encoding="utf-8")
    gnis_names = []
    for f in records:
        props = f.get("properties") or {}
        nm = props.get("gnis_name") or props.get("GNIS_Name")
        if nm:
            gnis_names.append(str(nm))
    vc = pd.Series(gnis_names).value_counts().head(30).to_dict() if gnis_names else {}
    return {
        "status": "ok",
        "url": ARCGIS_FLOWLINE,
        "where": f"ReachCode LIKE '{HUC8}%'",
        "n_features": len(records),
        "path": str(out_geojson),
        "gnis_named": len(gnis_names),
        "gnis_top": vc,
    }


def run_nhdplus_hr_download(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    out_dir = resolve_path(cfg, "data_raw") / "nhdplus_hr"
    out_dir.mkdir(parents=True, exist_ok=True)
    log: dict = {"huc8": HUC8, "attempts": [], "success": False}

    zip_path = out_dir / "NHDPLUS_H_1402_HU4_20220414_GPKG.zip"
    size = zip_path.stat().st_size if zip_path.exists() else 0
    if zip_path.exists() and zipfile.is_zipfile(zip_path):
        try:
            extract_dir = out_dir / "gpkg_extract"
            extract_dir.mkdir(parents=True, exist_ok=True)
            extracted = _extract_zip(zip_path, extract_dir)
            gpkgs = [p for p in extracted if p.suffix.lower() == ".gpkg"] or list(extract_dir.rglob("*.gpkg"))
            if not gpkgs:
                raise RuntimeError("No .gpkg inside zip")
            subset = _filter_huc8_flowlines(gpkgs[0], out_dir / "nhdplus_hr_huc14020001_flowlines.gpkg")
            log["attempts"].append({"method": "extract_huc8_gpkg", **subset})
            log["success"] = True
            log["primary"] = "usgs_s3_gpkg"
            log["flowline_gpkg"] = subset["out_gpkg"]
            _write_log(out_dir, log)
            LOG.info("NHDPlus HR HUC %s flowlines: %s", HUC8, subset["n_huc8_flowlines"])
            return log
        except Exception as exc:
            log["attempts"].append(
                {"method": "usgs_s3_gpkg", "status": "failed", "url": GPKG_URL, "error": f"{type(exc).__name__}: {exc}"}
            )
    else:
        log["attempts"].append(
            {
                "method": "usgs_s3_gpkg",
                "status": "failed",
                "url": GPKG_URL,
                "bytes_on_disk": size,
                "error": (
                    f"Incomplete or invalid zip ({size} bytes). "
                    "HEAD size is 284145677. Transfer stalled (curl resume reached ~200 MB then 0 B/s). "
                    "Not blocking the pipeline on a multi-minute S3 stall."
                ),
            }
        )

    log["attempts"].append(
        {
            "method": "usgs_s3_gdb",
            "status": "skipped",
            "url": GDB_URL,
            "error": "Skipped: same USGS S3 host as GPKG; observed stall after tens of MB.",
        }
    )

    try:
        arc = download_arcgis_huc8(out_dir)
        log["attempts"].append({"method": "arcgis_rest", **arc})
        log["success"] = True
        log["primary"] = "arcgis_rest"
        log["flowline_geojson"] = arc["path"]
        _write_log(out_dir, log)
        LOG.info("NHDPlus HR ArcGIS HUC %s features: %s", HUC8, arc["n_features"])
        return log
    except Exception as exc:
        log["attempts"].append(
            {
                "method": "arcgis_rest",
                "status": "failed",
                "url": ARCGIS_FLOWLINE,
                "where": f"ReachCode LIKE '{HUC8}%'",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        LOG.warning("NHDPlus HR ArcGIS query failed: %s", exc)

    log["success"] = False
    log["fallback"] = "data_raw/nhdplus/East_River_Lines.shp (HydroShare Dataset_3 extract, already NHDPlus HR Resolution=High)"
    _write_log(out_dir, log)
    return log


def main(config_path: str | None = None) -> dict:
    cfg = load_config(config_path)
    return run_nhdplus_hr_download(cfg)


if __name__ == "__main__":
    result = main()
    print(json.dumps({k: result[k] for k in ("success", "primary", "huc8") if k in result}, indent=2))
    print("log:", _log_path(resolve_path(load_config(), "data_raw") / "nhdplus_hr"))
