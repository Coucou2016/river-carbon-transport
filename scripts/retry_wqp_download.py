#!/usr/bin/env python3
"""Retry WQP per-site and USGS Samples downloads."""

from pathlib import Path

from src.utils import load_config, setup_logging
from src.wqp_download import run_wqp_usgs_downloads

LOG = setup_logging("retry_wqp_download")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    load_config()
    report = run_wqp_usgs_downloads(root)
    LOG.info("Download report: %s", report)
    print(report)


if __name__ == "__main__":
    main()
