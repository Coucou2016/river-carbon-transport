#!/usr/bin/env python3
"""Run full East River CO2 + AI subgrid pipeline end-to-end.

Updated 2026-08-28 (audit P0-05): stage I/O existence checks, non-zero exit on
failure, optional --clean, and artifact_manifest.json with SHA-256 hashes.
Any stage failure raises and exits non-zero.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ordered stages: (module, description, required_inputs, expected_outputs)
# Inputs/outputs are paths relative to repo root (or absolute via resolve after load).
STAGES = [
    (
        "01_fetch_water_quality",
        "Fetch real East River data",
        [],
        ["data_proc/reach_daily_observations.csv"],
    ),
    (
        "02_build_network",
        "Build network",
        ["data_proc/reach_daily_observations.csv"],
        ["data_proc/reach_attributes.csv"],
    ),
    (
        "real_network",
        "Directed tree + segmented observations + corrected baseline",
        ["data_proc/reach_daily_observations.csv"],
        [
            "data_proc/reach_daily_observations_segmented.csv",
            "data_proc/network_segments.csv",
            "data_proc/baseline_model_output.csv",
            "results/tables/length_conservation.csv",
        ],
    ),
    ("03_baseline_transport", "Baseline transport (legacy serial; superseded by real_network)", [], []),
    (
        "04_estimate_k",
        "Estimate k",
        ["data_proc/reach_daily_observations.csv"],
        ["data_proc/k_estimates.csv"],
    ),
    (
        "05_compute_residual_sgs",
        "Compute S_sgs residual",
        [
            "data_proc/reach_daily_observations.csv",
            "data_proc/reach_daily_observations_segmented.csv",
            "data_proc/network_segments.csv",
        ],
        ["data_proc/sgs_training_data.csv"],
    ),
    (
        "06_train_sgs_model",
        "Train AI models",
        ["data_proc/sgs_training_data.csv"],
        ["data_proc/models/training_metrics.json"],
    ),
    ("07_coupled_prediction", "Coupled prediction", ["data_proc/sgs_training_data.csv"], []),
    ("08_validate_flux_budget", "Validate & figures", [], []),
    ("09_spatial_temporal_viz", "Spatial & temporal viz", [], []),
    (
        "10_gis_network_viz",
        "GIS network line maps",
        [],
        [
            "results/figures/figure2_reach_assignment_and_samples.png",
            "results/figures/gis_network_manifest.json",
            # Provenance for the Esri World Imagery basemap (versionable, P2-09);
            # written by src/10_gis_network_viz.py.
            "results/figures/figure2_basemap_manifest.json",
        ],
    ),
    (
        "11_cross_section_2d_viz",
        "2D cross-section profiles",
        [],
        [
            "results/figures/cross_section_trapezoid_panel.png",
            "results/figures/cross_section_u_field_panel.png",
            "results/figures/cross_section_manifest.json",
        ],
    ),
    (
        "12_nested_cv_transport",
        "Grouped leave-one-reach-out transport CV",
        [
            "data_proc/reach_daily_observations.csv",
            "data_proc/reach_daily_observations_segmented.csv",
            "data_proc/network_segments.csv",
            "data_proc/sgs_training_data.csv",
        ],
        [
            "data_proc/nested_cv_holdout_predictions.csv",
            "results/tables/nested_cv_metrics.csv",
            "results/tables/k_correction_saturation.json",
            "results/figures/nested_cv_rmse_bar.png",
            # P1-07 per-reach statistics (previously undeclared outputs).
            "results/tables/per_reach_cv_metrics.csv",
            "results/tables/per_reach_paired_metrics.csv",
            "results/tables/reach_sensitivity.json",
        ],
    ),
    (
        "13_filter_scale_sgs",
        "Spatial rebinning sensitivity for S_sgs (not DAG mass filter)",
        ["data_proc/reach_daily_observations.csv"],
        [
            "results/tables/filter_scale_metrics.csv",
            "results/tables/filter_scale_summary.json",
            "results/figures/filter_scale_sgs.png",
            "results/figures/filter_scale_sgs_box.png",
            "results/figures/les_filter_conceptual.png",
        ],
    ),
    (
        "14_identifiability_ksgs",
        "S_sgs vs k diagnostics",
        ["data_proc/nested_cv_holdout_predictions.csv"],
        ["results/figures/supp_flux_diagnostics.png"],
    ),
    (
        "15_dimensionless_sparse",
        "Dimensionless sparse closure",
        ["data_proc/sgs_training_data.csv"],
        [
            "results/tables/dimensionless_sparse_coefficients.csv",
            "results/tables/dimensionless_sparse_summary.json",
            "results/figures/dimensionless_coefficients.png",
        ],
    ),
    (
        "16_equifinality_surface",
        "Model-free k-S objective surface",
        [],
        [
            "results/tables/equifinality_summary.json",
            "results/figures/equifinality_objective_surface.png",
        ],
    ),
    (
        "17_regenerate_holdout_figures",
        "Regenerate holdout figures",
        ["data_proc/nested_cv_holdout_predictions.csv"],
        [
            "results/figures/nested_cv_scatter_holdout.png",
            "results/figures/subgroup_rmse_r008_vs_trib.png",
        ],
    ),
    # Script stages (not importable src/ modules).  Staleness is decided by
    # content hash (see _stage_is_current): a glob keeps the derived published
    # set from being hard-coded (P2-09).  A stage with no declared inputs always
    # runs, because freshness cannot be proven by hash.
    (
        "scripts/build_figure_sidecars.py",
        "Figure sidecars + index + figures/paper mirror + archive manifest (provenance)",
        [
            # Every live figure: stage 19 mirrors the whole published set, and
            # published_figure_names() derives that set from the live PNGs. A
            # glob (not a literal list) keeps it derived; the old mtime check
            # skipped .png inputs entirely, so a regenerated figure left this
            # stage reporting "up-to-date" and the mirror stale.
            "results/figures/*.png",
            # published_figure_names() also reads exact <name>.png tokens out of
            # the rendered documents, so a document that gains/loses a figure
            # reference must re-run this stage.
            "paper.md",
            "paper.html",
            "report.md",
            "report.html",
        ],
        [
            # Every sidecar: this stage is the single authority for their schema.
            "results/figures/sidecars/*.json",
            "results/tables/figure_sidecar_index.json",
            "results/tables/superseded_figures.json",
            # The 40 mirrored paper/*.png are enumerated (with SHA-256) inside
            # derived_archive_manifest.json, which is declared here and verified
            # byte-for-byte against the live figures by verify_paper.py. Listing
            # them statically would hard-code the published set, which stage 19
            # derives programmatically (P2-09).
            "results/figures/paper/derived_archive_manifest.json",
        ],
    ),
    (
        "scripts/build_paper_tables.py",
        "Manuscript-facing summary tables + claim guard",
        [],
        [
            "results/tables/paper_main_results.csv",
            "results/tables/subgroup_metrics.csv",
            "results/tables/paper_filter_scale.csv",
            "results/tables/paper_claim_guard.json",
        ],
    ),
    (
        "scripts/paper_values.py",
        "Single numeric source of truth for the documents",
        [],
        ["results/tables/paper_values.json"],
    ),
]


def _expand_paths(rels: list[str]) -> list[str]:
    """Expand glob patterns to concrete relative paths (sorted, deterministic).

    Stage 19 mirrors *every* published live figure and rewrites every sidecar, so
    its staleness must react to any of them changing -- and the set must stay
    derived rather than hard-coded, which the P2-09 review required. Globs for
    both inputs (``results/figures/*.png``) and outputs
    (``results/figures/sidecars/*.json``) allow that.
    """
    out: list[str] = []
    for rel in rels:
        if any(ch in rel for ch in "*?["):
            out.extend(sorted(str(p.relative_to(ROOT)) for p in ROOT.glob(rel) if p.is_file()))
        else:
            out.append(rel)
    return out


# Content-hash stamps that let a re-run skip a stage only when the bytes prove
# it is up to date. This is a build cache, not evidence: it is git-ignored (see
# .gitignore) so regenerating it never dirties the tree, and a missing cache
# simply makes every stage run.
STAGE_STATE_PATH = ROOT / "results" / "tables" / "stage_state.json"


def stage_io(declared_inputs: list[str], declared_outputs: list[str]) -> tuple[list[str], list[str]]:
    """Expand one stage's declared inputs/outputs (glob-aware).

    Evaluated per stage, at the moment that stage is reached, so a glob input
    (e.g. stage 19's ``results/figures/*.png``) sees the figures earlier stages
    produced in this run rather than a stale pre-run snapshot. Exposed as its own
    function so the whole stage graph can be exercised without running anything.
    """
    return _expand_paths(list(declared_inputs)), _expand_paths(list(declared_outputs))


def _fingerprint(rels: list[str]) -> dict[str, str | None]:
    """SHA-256 of each path (``None`` when it is missing), as a content stamp."""
    fp: dict[str, str | None] = {}
    for rel in rels:
        p = ROOT / rel
        fp[rel] = _sha256(p) if p.is_file() else None
    return fp


def load_stage_state() -> dict:
    if not STAGE_STATE_PATH.exists():
        return {}
    try:
        data = json.loads(STAGE_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - a corrupt cache must not break the run
        return {}
    return data.get("stages", {}) if isinstance(data, dict) else {}


def save_stage_state(state: dict) -> None:
    STAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "note": (
            "Build cache: content-hash stamps used to skip a stage only when its "
            "declared inputs and outputs are provably unchanged. Git-ignored; "
            "delete it to force every stage to re-run."
        ),
        "stages": state,
    }
    STAGE_STATE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _stage_is_current(key: str, inputs: list[str], outputs: list[str], state: dict) -> bool:
    """True when a recorded content stamp proves the stage is up to date.

    Staleness is decided by **content hash**, never mtime: the recorded input and
    output digests must still match the bytes on disk. This closes two silent-skip
    bugs:
      * the old mtime check skipped ``.png`` inputs entirely, so regenerating a
        figure left ``scripts/build_figure_sidecars.py`` reporting "up-to-date"
        and the ``results/figures/paper/`` mirror stale;
      * a stage declaring no inputs was reported "up-to-date" once its outputs
        existed, contradicting STAGES' documented intent that such stages always
        run so a missing shell/gate input is never silently skipped.
    """
    rec = state.get(key)
    if not rec:
        return False
    if not inputs:
        # No declared inputs: freshness cannot be proven by hash, so never skip.
        return False
    if any(not (ROOT / rel).is_file() for rel in outputs):
        return False
    try:
        if rec.get("inputs") != _fingerprint(inputs):
            return False
        if rec.get("outputs") != _fingerprint(outputs):
            return False
    except OSError:
        return False
    return True


def run_script_stage(
    name: str,
    config: str | None,
    inputs: list[str],
    outputs: list[str],
    *,
    key: str | None = None,
    state: dict | None = None,
) -> str:
    """Run a ``scripts/*.py`` stage as a subprocess, honouring a --config."""
    if key is not None and state is not None and _stage_is_current(key, inputs, outputs, state):
        return "up-to-date"
    cmd = [sys.executable, str(ROOT / name)]
    if config:
        cmd += ["--config", config]
    print(f"  $ {' '.join(cmd[1:])}")
    subprocess.run(cmd, cwd=ROOT, check=True)
    return "ran"


def load_stage(module_name: str):
    path = ROOT / "src" / f"{module_name}.py"
    if not path.exists():
        raise FileNotFoundError(f"Stage module missing: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def run_src_stage(name: str, config: str | None) -> str:
    """Run one ``src/`` stage in its own interpreter (isolated process).

    The figure stages set a *global* matplotlib style at import time
    (``sns.set_theme`` + ``apply_plot_style``, plus ``plt.rcParams[...]``).
    Importing them all into one interpreter let that state -- and the resolved
    font manager -- leak into later stages, so ``10_gis_network_viz`` produced
    different bytes depending on whether stages 8/9 had run before it in the same
    process.  That made a figure's bytes depend on the *invocation path*
    (``run_pipeline.py`` vs ``--from-stage 10``) instead of only on the stage's
    own code and declared inputs.

    A fresh interpreter per stage removes that coupling and makes every stage's
    output identical to running it standalone, so the documented command
    reproduces the committed figures.  This mirrors :func:`run_script_stage`,
    which already runs ``scripts/*.py`` stages as subprocesses for the same
    reason.
    """
    cmd = [sys.executable, str(ROOT / "run_pipeline.py"), "--exec-stage-module", name]
    if config:
        cmd += ["--config", config]
    print(f"  $ {' '.join(cmd[1:])}")
    subprocess.run(cmd, cwd=ROOT, check=True)
    return "ran"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_meta() -> dict:
    meta = {"commit": None, "dirty": None, "branch": None}
    try:
        meta["commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
        meta["branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
        st = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        )
        meta["dirty"] = bool(st.strip())
    except Exception:
        pass
    return meta


def _check_paths(label: str, rels: list[str], *, must_exist: bool) -> None:
    missing = [rel for rel in rels if not (ROOT / rel).exists()]
    if missing and must_exist:
        raise FileNotFoundError(f"{label}: missing path(s): {missing}")


def write_artifact_manifest(stage_records: list[dict], command: list[str]) -> Path:
    out_dir = ROOT / "results" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    for rel in sorted(
        {
            *(o for rec in stage_records for o in rec.get("outputs", [])),
            "results/tables/nested_cv_summary.json",
            "results/tables/paper_claim_guard.json",
        }
    ):
        p = ROOT / rel
        if p.exists() and p.is_file():
            artifacts[rel] = {"sha256": _sha256(p), "size_bytes": p.stat().st_size}

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "python": sys.version,
        "platform": platform.platform(),
        "git": _git_meta(),
        "stages": stage_records,
        "artifacts": artifacts,
        "note": (
            "Post-fix development manifest. Headline scientific claims remain "
            "blocked until full recalculation after P0 closure."
        ),
        "regeneration": {
            "run_id_printed_by_documents": "20260919_remediation",
            "run_id_flag_is_not_that_id": (
                "run_pipeline.py --run-id only tags runs/<run_id>/; the documents "
                "print the module constant RUN_ID in scripts/generate_report.py, "
                "scripts/build_paper_tables.py, scripts/build_figure_sidecars.py "
                "and the sidecars written by src/13_filter_scale_sgs.py. These are "
                "not derived from --run-id (see docs/PIPELINE_AND_REGENERATION.md)."
            ),
            "full_sequence": (
                ".\\.venv\\Scripts\\python.exe run_pipeline.py "
                "&& .\\.venv\\Scripts\\python.exe scripts\\generate_paper.py "
                "&& .\\.venv\\Scripts\\python.exe scripts\\generate_report.py "
                "&& .\\.venv\\Scripts\\python.exe scripts\\verify_paper.py --mode development"
            ),
            "documents_are_not_stages": (
                "paper.md/paper.html/report.md/report.html are generated outside "
                "the stage graph by the two document generators."
            ),
        },
    }
    path = out_dir / "artifact_manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def clean_proc_outputs() -> None:
    """Remove regenerated proc/result artifacts (keeps raw data)."""
    targets = [
        ROOT / "data_proc" / "reach_daily_observations_segmented.csv",
        ROOT / "data_proc" / "network_segments.csv",
        ROOT / "data_proc" / "baseline_model_output.csv",
        ROOT / "data_proc" / "nested_cv_holdout_predictions.csv",
        ROOT / "data_proc" / "sgs_training_data.csv",
        ROOT / "results" / "tables" / "nested_cv_metrics.csv",
        ROOT / "results" / "tables" / "k_correction_saturation.json",
        ROOT / "results" / "tables" / "artifact_manifest.json",
        ROOT / "results" / "tables" / "length_conservation.csv",
        # P1-07 per-reach statistics and the provenance/derived views rebuilt by
        # the trailing script stages (18-20).
        ROOT / "results" / "tables" / "per_reach_cv_metrics.csv",
        ROOT / "results" / "tables" / "per_reach_paired_metrics.csv",
        ROOT / "results" / "tables" / "reach_sensitivity.json",
        ROOT / "results" / "tables" / "figure_sidecar_index.json",
        ROOT / "results" / "tables" / "paper_values.json",
        ROOT / "results" / "figures" / "paper" / "derived_archive_manifest.json",
    ]
    for p in targets:
        if p.exists():
            p.unlink()
            print(f"  cleaned {p.relative_to(ROOT)}")


def main(
    config: str | None = None,
    from_stage: int = 1,
    skip_legacy_baseline: bool = True,
    skip_legacy_coupled: bool = True,
    clean: bool = False,
    write_manifest: bool = True,
    run_id: str | None = None,
) -> None:
    if clean:
        print("=== --clean: removing selected regenerated artifacts ===")
        clean_proc_outputs()

    if run_id:
        run_dir = ROOT / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        print(f"=== run_id={run_id} → {run_dir} ===")

    legacy_skip = set()
    if skip_legacy_baseline:
        legacy_skip.add("03_baseline_transport")
    if skip_legacy_coupled:
        # T10: default path must not mix legacy C_obs-fallback coupled solver
        legacy_skip.add("07_coupled_prediction")

    stage_records: list[dict] = []
    state = load_stage_state()
    new_state: dict = {}
    for i, (name, desc, declared_inputs, declared_outputs) in enumerate(STAGES, start=1):
        if i < from_stage:
            continue
        inputs, outputs = stage_io(declared_inputs, declared_outputs)
        if name in legacy_skip:
            print(f"\n=== Stage {i}: SKIP {desc} ({name}) — legacy; use --legacy to enable ===")
            stage_records.append(
                {
                    "index": i,
                    "name": name,
                    "description": desc,
                    "skipped": True,
                    "reason": "legacy_default_skip_T10",
                }
            )
            continue
        print(f"\n=== Stage {i}: {desc} ({name}) ===")
        if inputs:
            _check_paths(f"Stage {i} ({name}) preflight", inputs, must_exist=True)

        key = f"{i:02d}:{name}"
        if name.endswith(".py"):
            mode = run_script_stage(name, config, inputs, outputs, key=key, state=state)
        else:
            mode = run_src_stage(name, config)

        if outputs:
            _check_paths(f"Stage {i} ({name}) postflight", outputs, must_exist=True)
        new_state[key] = {"inputs": _fingerprint(inputs), "outputs": _fingerprint(outputs)}
        stage_records.append(
            {"index": i, "name": name, "description": desc, "mode": mode,
             "inputs": inputs, "outputs": outputs}
        )

    if write_manifest:
        cmd = [sys.executable, str(ROOT / "run_pipeline.py")] + sys.argv[1:]
        path = write_artifact_manifest(stage_records, cmd)
        print(f"\nWrote {path.relative_to(ROOT)}")
    save_stage_state({**state, **new_state})
    print("\nPipeline complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--from-stage", type=int, default=1)
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Also run legacy 03 baseline + 07 coupled (C_obs-fallback) stages.",
    )
    parser.add_argument(
        "--include-legacy-baseline",
        action="store_true",
        help="Deprecated alias: also run src/03_baseline_transport.py.",
    )
    parser.add_argument("--run-id", default=None, help="Optional runs/<run_id>/ tag for this execution.")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete selected regenerated proc/table artifacts before running.",
    )
    parser.add_argument(
        "--no-manifest",
        action="store_true",
        help="Skip writing results/tables/artifact_manifest.json.",
    )
    parser.add_argument(
        "--exec-stage-module",
        default=None,
        help=(
            "Internal: load one src/ stage module, call its main(config) in this "
            "fresh interpreter, and exit. Used by run_src_stage() to isolate each "
            "stage's import-time matplotlib/seaborn global state."
        ),
    )
    args = parser.parse_args()

    if args.exec_stage_module:
        # Child entry point for run_src_stage(): execute exactly one src/ stage
        # in a dedicated interpreter, then exit. A non-zero exit propagates
        # through the parent's subprocess.run(check=True) exactly like a
        # scripts/*.py stage, so a failure still fails the pipeline.
        try:
            mod = load_stage(args.exec_stage_module)
            if not hasattr(mod, "main"):
                raise AttributeError(f"{args.exec_stage_module} has no main()")
            mod.main(args.config)
        except Exception as exc:
            print(f"\nStage {args.exec_stage_module} FAILED: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        raise SystemExit(0)

    try:
        use_legacy = bool(args.legacy or args.include_legacy_baseline)
        main(
            args.config,
            args.from_stage,
            skip_legacy_baseline=not use_legacy,
            skip_legacy_coupled=not args.legacy,
            clean=args.clean,
            write_manifest=not args.no_manifest,
            run_id=args.run_id,
        )
    except Exception as exc:
        print(f"\nPipeline FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
