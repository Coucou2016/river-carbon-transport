#!/usr/bin/env python3
"""Build JSON sidecars for the ten manuscript figures (2026-09-27 Part B item 11).

Each sidecar records ``figure_id, run_id, generator, source_table_sha256,
selected_rows, aggregation, units, n_definition, output_sha256`` so a reader (and
``scripts/verify_paper.py``) can trace every published figure back to the frozen
machine tables it was rendered from.

Figure-specific sidecars that need live in-memory values (e.g. Figure 10 from the
sparse branch, Figures 8/9 from the filter-scale run) are written by their own
generators; this script writes/refreshes the rest and is idempotent.

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\build_figure_sidecars.py
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.figure_sidecar import write_figure_sidecar  # noqa: E402
from src.utils import load_config, resolve_path  # noqa: E402

# TODO(P2-09): hard-coded and referenced by every sidecar; run_pipeline.py
# --run-id does NOT set this. See docs/PIPELINE_AND_REGENERATION.md.
RUN_ID = "20260919_remediation"

# Paths are resolved from the config (``paths.figures`` / ``paths.tables`` /
# ``paths.data_proc``) via src.utils.resolve_path rather than hard-coded off
# this file's location (P2-09): a re-rooted config must move every writer.
_CFG = load_config()
FIG_DIR = resolve_path(_CFG, "figures")
TABLES = resolve_path(_CFG, "tables")
DATA_PROC = resolve_path(_CFG, "data_proc")

# figures/paper/ is a frozen published copy of the manuscript PNGs, not the
# live output directory; see write_derived_archive_manifest().
PAPER_ARCHIVE_DIR = FIG_DIR / "paper"


def _counts() -> dict:
    pv = TABLES / "paper_values.json"
    if pv.exists():
        return json.loads(pv.read_text(encoding="utf-8")).get("counting", {})
    return {}


def sidecar_specs() -> dict[str, dict]:
    c = _counts()
    group_counts = c.get("group_counts", {})
    map_counts = c.get("group_mapping_counts", {})
    nested_metrics = "results/tables/nested_cv_metrics.csv"
    holdout = "data_proc/nested_cv_holdout_predictions.csv"
    subgroup = "results/tables/subgroup_metrics.csv"
    return {
        "les_filter_conceptual.png": {
            "figure_id": "fig1_cell_dag_rules_schematic",
            "run_id": RUN_ID,
            "generator": "src/13_filter_scale_sgs.py::plot_conceptual",
            "source_table": None,
            "selected_rows": {"panels": ["serial contraction", "parallel confluence"]},
            "aggregation": "schematic only (no run data plotted)",
            "units": "not applicable",
            "n_definition": "no sample rows; draws the cell-DAG aggregation rules",
            "notes": "schematic, not to scale; not evidence of conservation in any run",
        },
        "figure2_reach_assignment_and_samples.png": {
            "figure_id": "fig2_network_satellite_map",
            "run_id": RUN_ID,
            "generator": "src/10_gis_network_viz.py::plot_figure2_combined",
            "source_table": [
                "data_proc/gis_reach_line_mapping.csv",
                "data_proc/reach_daily_observations.csv",
                "data_proc/sample_snap_centerline.csv",
                "results/figures/figure2_basemap_manifest.json",
            ],
            "selected_rows": {
                "campaign_samples": int(c.get("n_campaign_samples", 0)),
                "assigned_nhd_flowlines_by_reach": map_counts,
                "sample_group_counts": group_counts,
            },
            "aggregation": "one marker per campaign sample; one polyline per assigned NHD flowline",
            "units": "Web Mercator (EPSG:3857); scale bar in m; coordinates WGS84 input",
            "n_definition": (
                "n=120 campaign samples (CSV keys date/reach_id/sample_id); mapping counts are "
                "assigned NHD flowlines per logical reach, a different estimand"
            ),
            "notes": (
                "basemap tiles cached locally with SHA-256 provenance in "
                "figure2_basemap_manifest.json; arrows show digitized flow direction only, "
                "so the map is not a flow-validity test"
            ),
        },
        "nested_cv_rmse_bar.png": {
            "figure_id": "fig3_nested_cv_rmse_bar",
            "run_id": RUN_ID,
            "generator": "src/12_nested_cv_transport.py::_plot_rmse_bar",
            "source_table": [nested_metrics, holdout],
            "selected_rows": {
                "cv_protocol": "loo_reach",
                "subgroup": "all_120",
                "schemes": ["baseline", "residual_ai(mlp)", "residual_ai(random_forest)", "k_correction"],
                "n_groups": int(c.get("n_cv_groups", 0)),
            },
            "aggregation": "pooled sample-weighted RMSE with per-reach open markers on the whiskers",
            "units": "C_aq RMSE in mol m^-3",
            "n_definition": "n=120 held-out samples over 8 leave-one-reach-out groups",
            "notes": "no closure lowers the pooled RMSE below the zero-residual Baseline",
        },
        "nested_cv_scatter_holdout.png": {
            "figure_id": "fig4_holdout_scatter_mlp",
            "run_id": RUN_ID,
            "generator": "src/17_regenerate_holdout_figures.py::_plot_scatter",
            "source_table": [holdout, "results/tables/nested_cv_summary.json"],
            "selected_rows": {"scheme": "residual_ai", "model": "mlp", "cv_protocol": "loo_reach", "n": 120},
            "aggregation": "one marker per held-out sample; RMSE/MAE/R2 from the plotted points",
            "units": "C_aq in mol m^-3",
            "n_definition": "n=120 held-out samples; extreme points retained; inset for C < 0.09",
            "notes": "lower-bound / zero-prediction rows are marked, not deleted",
        },
        "subgroup_rmse_r008_vs_trib.png": {
            "figure_id": "fig5_subgroup_rmse",
            "run_id": RUN_ID,
            "generator": "src/17_regenerate_holdout_figures.py::_plot_subgroup",
            "source_table": [subgroup, holdout],
            "selected_rows": {
                "subgroups": ["R008 mainstem", "multi-sample tributaries R002-R005", "single-sample reaches R001/R006/R007"],
                "subgroup_n": {"R008": 58, "tributaries": 59, "single_sample": 3},
            },
            "aggregation": "RMSE within each subgroup, equal weight per held-out sample",
            "units": "C_aq RMSE in mol m^-3",
            "n_definition": "subgroup sample counts printed on the axis; unequal evidence weight is visible",
            "notes": "single-sample reaches have no held-out spread and are shown for completeness only",
        },
        "supp_flux_diagnostics.png": {
            "figure_id": "fig6_flux_diagnostics",
            "run_id": RUN_ID,
            "generator": "src/14_identifiability_ksgs.py::plot_flux_diagnostics_combined",
            "source_table": [nested_metrics, "data_proc/identifiability_sample_table.csv"],
            "selected_rows": {
                "cv_protocol": "loo_reach",
                "subgroup": "all_120",
                "panels": ["Sigma F*A by closure", "flux-diagnostic RMSE", "k_eff/k_emp vs F_kcorr"],
            },
            "aggregation": "area-weighted model flux diagnostic Sigma(F*A) over overlapping sample areas",
            "units": "mol d^-1 (panel a); mol m^-2 d^-1 (panels b, c)",
            "n_definition": "n=120 held-out samples; sample-area diagnostic, not a study-area total",
            "notes": "un-area-weighted density sums are retained in the supplementary tables, not plotted",
        },
        "equifinality_objective_surface.png": {
            "figure_id": "fig7_equifinality_surface",
            "run_id": RUN_ID,
            "generator": "src/16_equifinality_surface.py::plot_surface",
            "source_table": ["results/tables/equifinality_summary.json", holdout],
            "selected_rows": {"n": 120, "grid": "alpha x S uniform grid"},
            "aggregation": "equal-weight 120-sample profile SSE with shared alpha and shared S",
            "units": "objective in RMSE-equivalent C_aq units (mol m^-3)",
            "n_definition": "n=120 samples; fixed observed upstream state; conditional model diagnostic",
            "notes": "not a likelihood, not a confidence interval, not network rerouting",
        },
        "filter_scale_sgs.png": {
            "figure_id": "fig8_filter_scale_sgs",
            "run_id": RUN_ID,
            "generator": "src/13_filter_scale_sgs.py::plot_filter_scale",
            "source_table": [
                "results/tables/filter_scale_metrics.csv",
                "data_proc/filter_scale_cell_residuals.csv",
            ],
            "selected_rows": {"formal_scales": 8, "excluded_scales": ["study_reach"]},
            "aggregation": "unique spatial cells (date-mean) for the mean/median/variance curves",
            "units": "|S_sgs| in mol m^-2 d^-1; dx in m (log axis)",
            "n_definition": "row unit = one date-cell record; unique cells and date-cell records reported separately",
            "notes": "sampling-conditional sensitivity of the conserved operator",
        },
        "filter_scale_sgs_box.png": {
            "figure_id": "fig9_filter_scale_box",
            "run_id": RUN_ID,
            "generator": "src/13_filter_scale_sgs.py::plot_filter_scale",
            "source_table": [
                "results/tables/filter_scale_metrics.csv",
                "data_proc/filter_scale_cell_residuals.csv",
            ],
            "selected_rows": {"scales": 8, "excluded_scales": ["study_reach"]},
            "aggregation": "distribution over date-cell records per scale (fliers suppressed; all points drawn)",
            "units": "|S_sgs| in mol m^-2 d^-1",
            "n_definition": "date-cell records, not independent spatial replicates",
            "notes": "diamonds are per-scale means",
        },
        "dimensionless_coefficients.png": {
            "figure_id": "fig10_dimensionless_coefficients",
            "run_id": RUN_ID,
            "generator": "src/15_dimensionless_sparse.py::plot_coefficients",
            "source_table": [
                "results/tables/dimensionless_sparse_coefficients.csv",
                "results/tables/dimensionless_sparse_summary.json",
                "data_proc/sgs_training_data.csv",
            ],
            "selected_rows": {
                "features": ["Fr", "Slope", "h_over_W", "log10_Re", "log10_Da"],
                "zeroed_by_lasso": ["log10_Re"],
                "n": 120,
            },
            "aggregation": "LASSO(alpha=0.05) on standardized dimensionless Pi features, fold-local targets",
            "units": "dimensionless (standardized coefficients)",
            "n_definition": "n=120 samples over 8 reach groups; equation is descriptive on S*",
            "notes": "zeroed terms are drawn explicitly as dropped, not omitted",
        },
    }


_FIG_TOKEN = re.compile(r"([A-Za-z0-9_]+\.png)")
# Documents whose rendered output shows figures to a reader.
_PUBLISHED_DOCS = ("paper.md", "paper.html", "report.md", "report.html")
# Kept out of the archive mirror on purpose: only the manuscript's ten figures
# plus the appendix figures the report already embedded. The report also
# mentions ~20 further live PNGs in prose whose bytes it does NOT embed; they
# are pipeline intermediates, so mirroring them would commit binaries the
# published documents never show.
_ARCHIVE_INTERMEDIATE_EXCLUSIONS: set[str] = set()

# The `results/figures/paper/` PNGs that were tracked before the 2026-09-27
# mirror ran predate the current figures and were therefore a stale published
# snapshot. Stage 19 mirrored the live renders over them (the live figures take
# primacy, and the documents embed the live bytes). Nothing is deleted: every
# superseded render stays byte-recoverable from git history, and its SHA-256 and
# size are recorded in `superseded_figures.json` so a reader can tell that
# `paper/` was refreshed rather than always having held these bytes.
#
# These constants are FROZEN deliberately. An earlier version re-derived them
# from `git cat-file HEAD:results/figures/paper/<name>`, which is only correct
# until the refresh is committed: afterwards HEAD holds the *new* bytes, so the
# next run would overwrite this historical record with the current hashes and
# silently destroy it. Stage 19 must be reproducible on a clean tree, so the
# values and the commit they are recoverable from are recorded literally.
_SUPERSEDED_ARCHIVE_COMMIT = "3b47b241900a9f89292c65e0c8170c3e346d6241"
_SUPERSEDED_ARCHIVE_RENDERS: dict[str, str] = {
    "dimensionless_coefficients.png": "4601193fb1cdd250fdd8d2e13089d70994cc7cdd3b0c8b8aa1e2347a590c9c59",
    "figure2_reach_assignment_and_samples.png": "f2242173b77d1af25c37c5a7e3e8ef0659bcd3f81f58d1c9785972e4417b2bdc",
    "filter_scale_sgs.png": "aaeb78f251ab63babbbd5b40fc8cb75961d57d3014cd7e67be6a9c568bf7cd59",
    "filter_scale_sgs_box.png": "d714fab68eb9238749a66ac7053ac113f5d6dbaadda7bd2f31635782199317eb",
    "identifiability_k_vs_sgs.png": "c61576faf8fcd059e38621422936576cff05ed4bc89e76ebb66ddfe02264f1c3",
    "les_filter_conceptual.png": "daf74d8f6b9d2b27bd1172ea93aa50796e69716328e1793adffacfbba1d111f3",
    "nested_cv_rmse_bar.png": "e102df6f4612ca0c98451be6f83c5557c165ca83f3669fce6bc6fb4ee301613c",
    "nested_cv_scatter_holdout.png": "a46a58842a95b0a3f0ce838d84c8c6e3d42a7cae4719fa660223b87dcdb712cc",
    "obs_vs_model_scatter_large.png": "dded6252ebb902f044647c07b1d99ea5b925367ca97692fabb3cc528a48d9647",
    "subgroup_rmse_r008_vs_trib.png": "9d6479e0072696412f0d9dfcf147eb3fdc02c310f66fe7d094229b45e7ac153f",
    "supp_flux_diagnostics.png": "6c375138d4d365349d615f4a8a24ac2a87c8d3727b6637115d7c585beb317df3",
}
_SUPERSEDED_ARCHIVE_SIZES: dict[str, int] = {
    "dimensionless_coefficients.png": 150549,
    "figure2_reach_assignment_and_samples.png": 408483,
    "filter_scale_sgs.png": 271252,
    "filter_scale_sgs_box.png": 261574,
    "identifiability_k_vs_sgs.png": 509320,
    "les_filter_conceptual.png": 359683,
    "nested_cv_rmse_bar.png": 152806,
    "nested_cv_scatter_holdout.png": 396798,
    "obs_vs_model_scatter_large.png": 258245,
    "subgroup_rmse_r008_vs_trib.png": 203403,
    "supp_flux_diagnostics.png": 408595,
}


def published_figure_names() -> set[str]:
    """Derive the published figure set programmatically (no fnmatch, no hard-coded list).

    A figure is *published* when both hold:
      * a live ``results/figures/<name>.png`` exists, **and**
      * ``<name>.png`` is either the figure of a sidecar (the provenance record
        for a manuscript figure) or an exact filename token that appears in a
        rendered document (``paper.md``/``paper.html``/``report.md``/
        ``report.html``).

    The token match is exact-filename, not fuzzy: ``nested_cv_rmse_bar.png``
    matches only itself.
    """
    live = {p.name for p in FIG_DIR.glob("*.png")}
    from_sidecars = {f"{p.stem}.png" for p in (FIG_DIR / "sidecars").glob("*.json")}
    tokens: set[str] = set()
    for name in _PUBLISHED_DOCS:
        doc = ROOT / name
        if doc.exists():
            tokens |= set(_FIG_TOKEN.findall(doc.read_text(encoding="utf-8", errors="replace")))
    published = (from_sidecars | tokens) & live
    return published - _ARCHIVE_INTERMEDIATE_EXCLUSIONS


def sync_paper_archive() -> tuple[list[str], list[str], list[str]]:
    """Mirror the published live figures into ``results/figures/paper/``.

    Returns ``(refreshed, already_current, historical_left_in_place)`` where
    ``refreshed`` are the PNGs rewritten, ``already_current`` are byte-identical
    already, and ``historical_left_in_place`` are archived PNGs that are no
    longer in the published set. Historical files are never deleted: they are
    left where they are and only annotated/downgraded in the manifest.
    """
    from src.figure_sidecar import sha256_file

    PAPER_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    published = published_figure_names()

    refreshed: list[str] = []
    current: list[str] = []
    for name in sorted(published):
        src = FIG_DIR / name
        dst = PAPER_ARCHIVE_DIR / name
        src_hash = sha256_file(src)
        if dst.exists() and sha256_file(dst) == src_hash:
            current.append(name)
            continue
        shutil.copyfile(src, dst)
        if sha256_file(dst) != src_hash:  # pragma: no cover - defensive
            raise RuntimeError(f"archive copy of {name} does not match its source byte-for-byte")
        refreshed.append(name)

    historical = sorted(
        p.name for p in PAPER_ARCHIVE_DIR.glob("*.png") if p.name not in published
    )
    return refreshed, current, historical


def write_derived_archive_manifest() -> Path:
    """Record how ``results/figures/paper/`` relates to the live figures (P2-09).

    ``results/figures/paper/`` is version-controlled because the project
    publishes those PNGs for external visual audit, but it is a **mirror** of
    the live output in ``results/figures/`` (which is gitignored apart from the
    provenance JSON). ``sync_paper_archive`` refreshes it, so for every current
    figure ``matches_canonical`` must be true; a false value means drift (or a
    hand-tampered archive) that the verify gate will report.
    """
    from src.figure_sidecar import sha256_file

    published = published_figure_names()
    entries: dict[str, dict] = {}
    for name in sorted(published):
        canonical = FIG_DIR / name
        archived = PAPER_ARCHIVE_DIR / name
        sidecar = FIG_DIR / "sidecars" / f"{Path(name).stem}.json"
        side = {}
        if sidecar.exists():
            side = json.loads(sidecar.read_text(encoding="utf-8"))
        live_hash = sha256_file(canonical)
        arch_hash = sha256_file(archived)
        entries[name] = {
            "figure_id": Path(name).stem,
            "archived_path": str(archived.relative_to(ROOT)),
            "archived_png_sha256": arch_hash,
            "canonical_source": str(canonical.relative_to(ROOT)),
            "canonical_png_sha256": live_hash,
            "matches_canonical": bool(live_hash is not None and live_hash == arch_hash),
            "manuscript_figure": name in {f"{s}.png" for s in (
                p.stem for p in (FIG_DIR / "sidecars").glob("*.json")
            )},
            "sidecar_output_sha256": side.get("output_sha256"),
            "regeneration": (
                "stage 19 re-run: scripts/build_figure_sidecars.py mirrors the live "
                f"PNG over paper/ and re-hashes it (live PNG produced by "
                f"{side.get('generator') or 'the figure generator'})"
            ),
        }

    historical = []
    for img in sorted(PAPER_ARCHIVE_DIR.glob("*.png")):
        if img.name in published:
            continue
        historical.append({
            "name": img.name,
            "archived_path": str(img.relative_to(ROOT)),
            "archived_png_sha256": sha256_file(img),
            "reason": "not in the current published figure set; superseded render",
            "action": "kept in place, annotated historical (not mirrored, never deleted)",
        })

    matching = sum(1 for e in entries.values() if e["matches_canonical"])
    payload = {
        "run_id": RUN_ID,
        "directory": str(PAPER_ARCHIVE_DIR.relative_to(ROOT)),
        "live_output_directory": str(FIG_DIR.relative_to(ROOT)),
        "purpose": (
            "Version-controlled mirror of every figure the published documents "
            "show, kept for external visual audit. Refreshed by stage 19 "
            "(scripts/build_figure_sidecars.py) so each archived PNG is "
            "byte-identical to the live PNG the manuscript/report embed. "
            "figures[*].matches_canonical must be true; a false value is drift or "
            "tampering and is reported by scripts/verify_paper.py."
        ),
        "counts": {
            "published_figures": len(entries),
            "matching": matching,
            "drifted": len(entries) - matching,
            "historical_left_in_place": len(historical),
        },
        "how_the_set_is_derived": (
            "programmatically: live results/figures/*.png intersected with "
            "(sidecar stems + exact .png filename tokens present in paper.md, "
            "paper.html, report.md, report.html). No filename globbing."
        ),
        "regeneration_command": (
            ".\\.venv\\Scripts\\python.exe scripts\\build_figure_sidecars.py "
            "(stage 19) after the live PNGs are regenerated by run_pipeline.py; "
            "it copies each published live PNG over results/figures/paper/ and "
            "re-hashes. See docs/PIPELINE_AND_REGENERATION.md."
        ),
        "figures": entries,
        "historical_figures": historical,
    }
    out = PAPER_ARCHIVE_DIR / "derived_archive_manifest.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Record the renders this mirror replaced so the refresh is auditable even
    # though the old bytes stay in git history. Values come from the frozen
    # constants above, never from a live `git show HEAD:` lookup: HEAD moves once
    # the refresh is committed, which would overwrite this history with the new
    # hashes and make the stage non-reproducible.
    sup_path = TABLES / "superseded_figures.json"
    sup_records = {}
    for name, full in sorted(_SUPERSEDED_ARCHIVE_RENDERS.items()):
        sup_records[name] = {
            "archived_path": f"results/figures/paper/{name}",
            "superseded_png_sha256": full,
            "superseded_size_bytes": _SUPERSEDED_ARCHIVE_SIZES[name],
            "sha256_prefix_checked_at_capture": full[:16],
            "recoverable_from": (
                f"git show {_SUPERSEDED_ARCHIVE_COMMIT}:results/figures/paper/{name}"
            ),
            "reason": (
                "pre-2026-09-27 render; the published documents embed the live "
                "figure bytes, so paper/ was refreshed to match (2026-09-27 mirror)"
            ),
        }
    sup_payload = {
        "run_id": RUN_ID,
        "note": (
            "Superseded results/figures/paper PNG renders replaced by the "
            "2026-09-27 archive mirror. Not deleted: each remains in git history; "
            f"recover it with the documented command against {_SUPERSEDED_ARCHIVE_COMMIT[:7]}."
        ),
        "count": len(sup_records),
        "figures": sup_records,
    }
    sup_path.write_text(json.dumps(sup_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Build/refresh figure JSON sidecars")
    ap.add_argument("--config", default=None, help="Path to YAML config (defaults to configs/east_river.yaml)")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Overwrite sidecars already written by a figure generator (default: keep the generator's live metadata).",
    )
    ap.add_argument(
        "--no-mirror",
        action="store_true",
        help="Do not refresh results/figures/paper/ from the live figures (manifest only).",
    )
    args = ap.parse_args()

    # Honour --config: run_pipeline.py forwards it to every script stage, and a
    # re-rooted config must move these writers (P2-09). The module-level paths are
    # bound from the default config at import time; re-bind them here so a caller
    # that supplies --config gets the same directories the rest of the pipeline
    # uses.
    global FIG_DIR, TABLES, DATA_PROC, PAPER_ARCHIVE_DIR
    if args.config:
        cfg = load_config(args.config)
        FIG_DIR = resolve_path(cfg, "figures")
        TABLES = resolve_path(cfg, "tables")
        DATA_PROC = resolve_path(cfg, "data_proc")
        PAPER_ARCHIVE_DIR = FIG_DIR / "paper"

    specs = sidecar_specs()
    written = 0
    kept = 0
    missing = []
    for name, meta in specs.items():
        img = FIG_DIR / name
        if not img.exists():
            missing.append(name)
            continue
        side = img.with_suffix(img.suffix + ".json")
        if side.exists() and not args.force:
            kept += 1
            continue
        write_figure_sidecar(img, meta)
        written += 1

    from src.figure_sidecar import sha256_file

    index = {name: {"image_sha256": sha256_file(FIG_DIR / name)} for name in specs}
    (TABLES / "figure_sidecar_index.json").write_text(
        json.dumps(index, indent=2) + "\n", encoding="utf-8"
    )
    archive = write_derived_archive_manifest()
    refreshed = current = historical = []
    if not args.no_mirror:
        refreshed, current, historical = sync_paper_archive()
        # Re-write now the archive has moved, so the recorded hashes are final.
        archive = write_derived_archive_manifest()
    print(f"Wrote {written} figure sidecars, kept {kept} generator-written (+index)")
    print(
        f"Archive mirror {PAPER_ARCHIVE_DIR.relative_to(ROOT)}: "
        f"{len(refreshed)} refreshed, {len(current)} already current, "
        f"{len(historical)} historical kept"
    )
    print(f"Wrote {archive.relative_to(ROOT)}")
    if historical:
        print(f"HISTORICAL (annotated in the manifest, not deleted): {historical}")
    if missing:
        print(f"MISSING figure files (sidecar skipped): {missing}")


if __name__ == "__main__":
    main()
