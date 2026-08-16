"""WQP per-site download with retries and USGS Samples API."""

from __future__ import annotations

import io
import json
import time
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils import setup_logging

LOG = setup_logging("wqp_download")

WQP_RESULT_URL = "https://www.waterqualitydata.us/data/Result/search"
WQP_START = "08-01-2019"
WQP_END = "08-15-2019"

WQP_CHARACTERISTICS = [
    "pH",
    "Temperature, water",
    "Dissolved oxygen",
    "Alkalinity, total",
    "Nitrogen",
    "Phosphorus",
    "Carbon, dissolved organic",
    "Organic carbon",
]

USGS_SAMPLE_SITES = ("09112500", "09111250")


def _session(max_retries: int = 3) -> requests.Session:
    sess = requests.Session()
    retry = Retry(
        total=max_retries,
        connect=max_retries,
        read=max_retries,
        backoff_factor=2.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    return sess


def _request_with_manual_retry(
    sess: requests.Session,
    url: str,
    params: dict | list,
    *,
    max_attempts: int = 3,
    timeout: float = 180.0,
    pause_s: float = 2.0,
) -> tuple[int | None, bytes, str | None]:
    last_err: str | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = sess.get(url, params=params, timeout=timeout)
            if resp.status_code == 200 and resp.content:
                return resp.status_code, resp.content, None
            if resp.status_code == 200 and not resp.content:
                return resp.status_code, b"", None
            last_err = f"HTTP {resp.status_code}"
        except requests.RequestException as exc:
            last_err = f"{type(exc).__name__}: {exc}"
        if attempt < max_attempts:
            time.sleep(pause_s * attempt)
    return None, b"", last_err


def download_wqp_site(
    sess: requests.Session,
    site_id: str,
    *,
    use_characteristics: bool = False,
) -> tuple[pd.DataFrame, str | None]:
    """Fetch WQP Result rows for one MonitoringLocationIdentifier."""
    if use_characteristics:
        frames: list[pd.DataFrame] = []
        for ch in WQP_CHARACTERISTICS:
            params = [
                ("mimeType", "csv"),
                ("zip", "no"),
                ("siteid", site_id),
                ("startDateLo", WQP_START),
                ("startDateHi", WQP_END),
                ("characteristicName", ch),
            ]
            _, body, err = _request_with_manual_retry(sess, WQP_RESULT_URL, params)
            if err:
                continue
            if not body.strip():
                continue
            try:
                df = pd.read_csv(io.BytesIO(body))
            except pd.errors.EmptyDataError:
                continue
            if not df.empty:
                frames.append(df)
        if not frames:
            return pd.DataFrame(), None
        return pd.concat(frames, ignore_index=True), None

    params = {
        "mimeType": "csv",
        "zip": "no",
        "siteid": site_id,
        "startDateLo": WQP_START,
        "startDateHi": WQP_END,
    }
    _, body, err = _request_with_manual_retry(sess, WQP_RESULT_URL, params)
    if err:
        return pd.DataFrame(), err
    if not body.strip():
        return pd.DataFrame(), None
    try:
        df = pd.read_csv(io.BytesIO(body))
    except pd.errors.EmptyDataError:
        return pd.DataFrame(), None
    return df, None


def download_all_wqp_sites(
    station_csv: Path,
    out_csv: Path,
    errors_json: Path,
    *,
    max_sites: int | None = None,
    site_pause_s: float = 0.25,
) -> dict:
    stations = pd.read_csv(station_csv)
    site_ids = stations["MonitoringLocationIdentifier"].dropna().astype(str).unique().tolist()
    if max_sites:
        site_ids = site_ids[:max_sites]

    sess = _session()
    frames: list[pd.DataFrame] = []
    errors: list[dict] = []
    n_ok = 0
    n_rows = 0

    station_lat = stations.set_index("MonitoringLocationIdentifier")["LatitudeMeasure"].to_dict()
    station_lon = stations.set_index("MonitoringLocationIdentifier")["LongitudeMeasure"].to_dict()

    for i, site_id in enumerate(site_ids, start=1):
        df, err = download_wqp_site(sess, site_id)
        if err:
            errors.append({"site_id": site_id, "error": err})
            LOG.warning("WQP %s failed: %s", site_id, err)
        elif not df.empty:
            df["MonitoringLocationIdentifier"] = site_id
            df["station_lat"] = station_lat.get(site_id)
            df["station_lon"] = station_lon.get(site_id)
            frames.append(df)
            n_ok += 1
            n_rows += len(df)
        if i % 25 == 0:
            LOG.info("WQP progress %d/%d sites (%d rows)", i, len(site_ids), n_rows)
        time.sleep(site_pause_s)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        combined.to_csv(out_csv, index=False)
    else:
        out_csv.write_text("", encoding="utf-8")

    errors_json.write_text(json.dumps(errors, indent=2), encoding="utf-8")
    summary = {
        "sites_queried": len(site_ids),
        "sites_with_data": n_ok,
        "result_rows": n_rows,
        "errors": len(errors),
        "out_csv": str(out_csv),
    }
    LOG.info("WQP download summary: %s", summary)
    return summary


def download_usgs_samples(
    site: str,
    out_csv: Path,
    *,
    start: str = "2019-08-01",
    end: str = "2019-08-15",
    max_attempts: int = 3,
) -> tuple[pd.DataFrame, str | None]:
    """USGS Samples API via dataretrieval.waterdata.get_samples."""
    try:
        from dataretrieval import waterdata
    except ImportError as exc:
        return pd.DataFrame(), f"ImportError: {exc}"

    mid = f"USGS-{site}"
    last_err: str | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            df, _meta = waterdata.get_samples(
                monitoringLocationIdentifier=mid,
                activityStartDateLower=start,
                activityStartDateUpper=end,
            )
            out_csv.parent.mkdir(parents=True, exist_ok=True)
            if not df.empty:
                df.to_csv(out_csv, index=False)
            else:
                pd.DataFrame().to_csv(out_csv, index=False)
            return df, None
        except Exception as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            time.sleep(2.0 * attempt)
    return pd.DataFrame(), last_err


def run_wqp_usgs_downloads(project_root: Path) -> dict:
    wqp_dir = project_root / "data_raw" / "wqp"
    usgs_dir = project_root / "data_raw" / "usgs"
    station_csv = wqp_dir / "wqp_stations_huc14020001.csv"
    out_csv = wqp_dir / "wqp_site_results_20190801_20190815.csv"
    errors_json = wqp_dir / "wqp_site_download_errors.json"

    report: dict = {"wqp": {}, "usgs_samples": {}}
    if station_csv.exists():
        report["wqp"] = download_all_wqp_sites(station_csv, out_csv, errors_json)
    else:
        report["wqp"] = {"error": f"missing {station_csv}"}

    for site in USGS_SAMPLE_SITES:
        path = usgs_dir / f"{site}_water_quality_samples_201908.csv"
        df, err = download_usgs_samples(site, path)
        report["usgs_samples"][site] = {
            "rows": len(df),
            "path": str(path),
            "error": err,
        }
    return report
