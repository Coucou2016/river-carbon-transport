#!/usr/bin/env python3
"""Run full East River CO2 + AI subgrid pipeline end-to-end."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STAGES = [
    ("01_fetch_water_quality", "Fetch real East River data"),
    ("02_build_network", "Build network"),
    ("03_baseline_transport", "Baseline transport"),
    ("04_estimate_k", "Estimate k"),
    ("05_compute_residual_sgs", "Compute S_sgs residual"),
    ("06_train_sgs_model", "Train AI models"),
    ("07_coupled_prediction", "Coupled prediction"),
    ("08_validate_flux_budget", "Validate & figures"),
    ("09_spatial_temporal_viz", "Spatial & temporal viz"),
    ("10_gis_network_viz", "GIS network line maps"),
    ("11_cross_section_2d_viz", "2D cross-section profiles"),
    ("12_nested_cv_transport", "Nested CV coupled transport"),
    ("13_filter_scale_sgs", "LES filter-scale S_sgs"),
    ("14_identifiability_ksgs", "S_sgs vs k identifiability"),
    ("15_dimensionless_sparse", "Dimensionless sparse closure"),
]


def load_stage(module_name: str):
    path = ROOT / "src" / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(config: str | None = None, from_stage: int = 1) -> None:
    for i, (name, desc) in enumerate(STAGES, start=1):
        if i < from_stage:
            continue
        print(f"\n=== Stage {i}: {desc} ({name}) ===")
        mod = load_stage(name)
        if name == "01_fetch_water_quality":
            mod.main(config)
        elif name == "07_coupled_prediction":
            mod.main(config)
        else:
            mod.main(config)
    print("\nPipeline complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--from-stage", type=int, default=1)
    args = parser.parse_args()
    main(args.config, args.from_stage)
