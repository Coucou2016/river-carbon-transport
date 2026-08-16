"""Merge WQP / USGS water quality into campaign observations (exact date + site)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.utils import resolve_path, setup_logging

LOG = setup_logging("wqp_merge")

SITE_MATCH_MAX_M = 200.0

# WQP / USGS characteristic labels -> observation column
CHAR_TO_COL = {
    "ph": "pH",
    "temperature, water": "T_C",
    "dissolved oxygen": "DO_mgL",
    "oxygen": "DO_mgL",
    "alkalinity, total": "Alk_ueqL",
    "carbon, dissolved organic": "DOC_mgL",
    "organic carbon, dissolved": "DOC_mgL",
    "nitrogen": "N_uM",
    "inorganic nitrogen (nitrate and nitrite)": "N_uM",
    "nitrate": "N_uM",
    "phosphorus": "P_uM",
    "orthophosphate": "P_uM",
}


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dlon = np.radians(lon2 - lon1)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlon / 2) ** 2
    return float(2 * r * np.arcsin(np.sqrt(a)))


def _load_stations(cfg: dict) -> pd.DataFrame:
    path = resolve_path(cfg, "data_raw") / "wqp" / "wqp_stations_huc14020001.csv"
    if not path.exists():
        return pd.DataFrame()
    st = pd.read_csv(path)
    st["lat"] = pd.to_numeric(st["LatitudeMeasure"], errors="coerce")
    st["lon"] = pd.to_numeric(st["LongitudeMeasure"], errors="coerce")
    st["site_id"] = st["MonitoringLocationIdentifier"].astype(str)
    return st.dropna(subset=["lat", "lon"])


def _assign_sample_sites(obs: pd.DataFrame, stations: pd.DataFrame) -> pd.Series:
    """Nearest monitoring location within SITE_MATCH_MAX_M per sample."""
    site_for_row: list[str | None] = []
    for _, row in obs.iterrows():
        lat, lon = float(row["lat"]), float(row["lon"])
        dists = stations.apply(lambda s: _haversine_m(lat, lon, s["lat"], s["lon"]), axis=1)
        if dists.empty:
            site_for_row.append(None)
            continue
        j = dists.idxmin()
        if float(dists.loc[j]) <= SITE_MATCH_MAX_M:
            site_for_row.append(str(stations.loc[j, "site_id"]))
        else:
            site_for_row.append(None)
    return pd.Series(site_for_row, index=obs.index, name="wqp_site_id")


def _parse_wqp_results(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    if df.empty:
        return df
    date_col = "ActivityStartDate"
    if date_col not in df.columns:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()
    df["site_id"] = df.get("MonitoringLocationIdentifier", "").astype(str)
    df["char"] = df["CharacteristicName"].astype(str).str.strip().str.lower()
    val_col = "ResultMeasureValue"
    unit_col = "ResultMeasure/MeasureUnitCode"
    df["value"] = pd.to_numeric(df.get(val_col), errors="coerce")
    df["unit"] = df.get(unit_col, "").astype(str)
    df["source"] = "wqp"
    return df.dropna(subset=["date", "value"])


def _parse_usgs_samples(path: Path, site_no: str) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    if df.empty:
        return df
    date_col = "Activity_StartDate"
    if date_col not in df.columns:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()
    df["site_id"] = f"USGS-{site_no}"
    df["char"] = df["Result_Characteristic"].astype(str).str.strip().str.lower()
    df["value"] = pd.to_numeric(df["Result_Measure"], errors="coerce")
    df["unit"] = df.get("Result_MeasureUnit", "").astype(str)
    df["source"] = f"usgs_samples:{site_no}"
    return df.dropna(subset=["date", "value"])


def _convert_value(char: str, value: float, unit: str, col: str) -> float | None:
    u = (unit or "").lower()
    if col == "Alk_ueqL":
        if "ueq" in u or "eq" in u:
            return float(value) * (1e6 if "/l" in u and "ueq" not in u else 1.0)
        if "mg/l" in u and ("caco" in u or "ca co" in u or u == "mg/l"):
            return float(value) * 20.0
        if "mg/l" in u:
            return float(value) * 20.0
        return None
    if col == "N_uM":
        if "mg/l" in u or "mg/l as n" in u:
            return float(value) / 14.007 * 1000.0
        if "um" in u or "µm" in u:
            return float(value)
        return None
    if col == "P_uM":
        if "mg/l" in u:
            return float(value) / 30.974 * 1000.0
        if "um" in u:
            return float(value)
        return None
    if col == "DO_mgL" and "%" in u:
        return None
    return float(value)


def _pivot_site_day(long_df: pd.DataFrame) -> dict[tuple[str, pd.Timestamp], dict[str, float]]:
    out: dict[tuple[str, pd.Timestamp], dict[str, float]] = {}
    for _, row in long_df.iterrows():
        col = CHAR_TO_COL.get(row["char"])
        if not col:
            continue
        converted = _convert_value(row["char"], float(row["value"]), str(row["unit"]), col)
        if converted is None or np.isnan(converted):
            continue
        key = (str(row["site_id"]), pd.Timestamp(row["date"]).normalize())
        out.setdefault(key, {})
        if col not in out[key]:
            out[key][col] = converted
    return out


def merge_external_wq(obs: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    """Fill NaN chemistry fields where sample date matches assigned WQP/USGS site."""
    stats = {
        "samples_with_site_match": 0,
        "samples_enriched": 0,
        "fields_filled": {},
        "wqp_rows_loaded": 0,
        "usgs_rows_loaded": 0,
    }
    stations = _load_stations(cfg)
    if stations.empty:
        LOG.warning("No WQP station list; skip external WQ merge")
        return obs, stats

    raw_wqp = resolve_path(cfg, "data_raw") / "wqp"
    raw_usgs = resolve_path(cfg, "data_raw") / "usgs"
    long_parts: list[pd.DataFrame] = []

    wqp_path = raw_wqp / "wqp_site_results_20190801_20190815.csv"
    wqp_df = _parse_wqp_results(wqp_path)
    stats["wqp_rows_loaded"] = len(wqp_df)
    if not wqp_df.empty:
        long_parts.append(wqp_df)

    for site in ("09112500", "09111250"):
        usgs_path = raw_usgs / f"{site}_water_quality_samples_201908.csv"
        usg = _parse_usgs_samples(usgs_path, site)
        stats["usgs_rows_loaded"] += len(usg)
        if not usg.empty:
            long_parts.append(usg)

    if not long_parts:
        return obs, stats

    long_all = pd.concat(long_parts, ignore_index=True)
    site_day = _pivot_site_day(long_all)

    out = obs.copy()
    site_ids = _assign_sample_sites(out, stations)
    out["wqp_site_id"] = site_ids
    stats["samples_with_site_match"] = int(site_ids.notna().sum())

    fill_cols = ["Alk_ueqL", "N_uM", "P_uM", "DOC_mgL", "PAR_umolm2s", "DO_mgL", "pH", "T_C"]
    enriched = 0
    for idx, row in out.iterrows():
        sid = row.get("wqp_site_id")
        if pd.isna(sid) or not sid:
            continue
        key = (str(sid), pd.Timestamp(row["date"]).normalize())
        vals = site_day.get(key)
        if not vals:
            continue
        touched = False
        for col in fill_cols:
            if col not in out.columns:
                continue
            if pd.notna(row.get(col)):
                continue
            if col in vals and pd.notna(vals[col]):
                out.at[idx, col] = vals[col]
                stats["fields_filled"][col] = stats["fields_filled"].get(col, 0) + 1
                touched = True
        if touched:
            enriched += 1
            if "data_source" in out.columns:
                out.at[idx, "data_source"] = str(row.get("data_source", "")) + "+wqp_usgs_exact_site_day"

    stats["samples_enriched"] = enriched
    LOG.info("WQP/USGS merge: %s", stats)
    return out, stats

