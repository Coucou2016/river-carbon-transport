"""Check StreamPULSE for East River / Gothic / Coal Creek sites. Real data only — no imputation."""

from __future__ import annotations

import json
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("streampulse")

DOWNLOAD_PAGE = "https://data.streampulse.org/download"
QUERY_URL = "https://data.streampulse.org/query_available_data"
KEYWORDS = ("east river", "gothic", "coal creek", "crested butte", "gunnison", "almont")


def _parse_sites_from_html(html: str) -> list[str]:
    # Option values look like: CO - Alpine2
    sites = re.findall(r">([A-Z]{2} - [^<]+)<", html)
    if not sites:
        sites = re.findall(r"([A-Z]{2} - [A-Za-z0-9 ,.'()/-]+)", html)
    # de-duplicate preserving order
    seen = set()
    out = []
    for s in sites:
        s = re.sub(r"\s+", " ", s).strip()
        if s not in seen and " - " in s:
            seen.add(s)
            out.append(s)
    return out


def search_streampulse(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    out_dir = resolve_path(cfg, "data_raw") / "streampulse"
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "download_page": DOWNLOAD_PAGE,
        "query_url": QUERY_URL,
        "keywords": list(KEYWORDS),
        "matched_sites": [],
        "co_sites": [],
        "n_sites_parsed": 0,
        "found": False,
        "errors": [],
    }

    try:
        r = requests.get(QUERY_URL, params={"type": "site_data"}, timeout=60)
        report["query_status"] = r.status_code
        if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
            payload = r.json()
            (out_dir / "query_available_data.json").write_text(
                json.dumps(payload, indent=2, default=str)[:2_000_000], encoding="utf-8"
            )
        else:
            report["errors"].append(
                f"GET {QUERY_URL}?type=site_data -> HTTP {r.status_code}: {r.text[:400]}"
            )
    except Exception as exc:
        report["errors"].append(f"GET {QUERY_URL}: {type(exc).__name__}: {exc}")

    html = ""
    try:
        r = requests.get(DOWNLOAD_PAGE, timeout=60)
        r.raise_for_status()
        html = r.text
        (out_dir / "download_page.html").write_text(html, encoding="utf-8")
    except Exception as exc:
        report["errors"].append(f"GET {DOWNLOAD_PAGE}: {type(exc).__name__}: {exc}")
        (out_dir / "streampulse_site_search.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        return report

    sites = _parse_sites_from_html(html)
    report["n_sites_parsed"] = len(sites)
    co = [s for s in sites if s.startswith("CO - ")]
    report["co_sites"] = co
    matched = []
    for s in sites:
        low = s.lower()
        if any(k in low for k in KEYWORDS):
            matched.append(s)
    report["matched_sites"] = matched
    report["found"] = bool(matched)
    if not matched:
        report["conclusion"] = (
            "No StreamPULSE sites matching East River / Gothic / Coal Creek / Crested Butte / "
            "Gunnison / Almont. Colorado sites on the portal do not include this campaign watershed. "
            "No StreamPULSE time series downloaded."
        )
    else:
        report["conclusion"] = f"Matched {len(matched)} site(s); download those series next."

    (out_dir / "streampulse_site_search.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    LOG.info("StreamPULSE: parsed %d sites, CO=%d, matches=%s", len(sites), len(co), matched)
    return report


def main(config_path: str | None = None) -> dict:
    return search_streampulse(load_config(config_path))


if __name__ == "__main__":
    print(json.dumps(main(), indent=2)[:4000])
