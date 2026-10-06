# Pipeline contract and regeneration

Date: 2026-09-27
Repo: `D:\Projects\20260611-river-carbon-transport`
Frozen run id: **`20260919_remediation`**
Base commit: `3b47b241900a9f89292c65e0c8170c3e346d6241` (branch `main`, tree dirty by design)

This document is the contract for *how to rebuild every committed artifact*. It
exists because three artifact sets previously had no documented regeneration
command, and because the run id that the documents print is not the run id that
`run_pipeline.py --run-id` accepts.

---

## 1. Environment

| Item | Value |
|---|---|
| Interpreter | CPython **3.12.10** (MSC v.1943, 64 bit, AMD64) |
| Platform | Windows-10-10.0.19045-SP0 |
| Runtime pins | `requirements.txt` |
| Dev/test pins | `requirements-dev.txt` (`pytest==9.1.1`) |
| Test config | `pytest.ini` (`testpaths = tests`, `-p no:cacheprovider`) |
| Python entry point | `.\.venv\Scripts\python.exe` |

```powershell
# one-time setup
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

`results/tables/artifact_manifest.json` records, at write time: the command line,
`sys.version`, `platform.platform()`, and the git HEAD / branch / dirty flag.

---

## 2. Run-id inconsistency (known, flagged)

**Flagged, not silently fixed.**

* `scripts/generate_report.py` (`RUN_ID`), `scripts/build_paper_tables.py`,
  `scripts/build_figure_sidecars.py` (`RUN_ID`), `src/13_filter_scale_sgs.py`
  (`SIDECAR_RUN_ID`) and the sidecar `run_id` fields all **hard-code**
  `"20260919_remediation"`. This is the id that `paper.md` / `paper.html` /
  `report.md` / `report.html` and every sidecar print, and it is the value
  `scripts/report_shared.py` reads back from `paper_claim_guard.json`.
* `run_pipeline.py --run-id <id>` does **not** feed any of those. It only creates
  and tags `runs/<run_id>/` for that execution.

Consequences and guard rails:

* Passing `--run-id something_else` will leave every document and sidecar still
  reporting `20260919_remediation`. Do not treat that as the frozen-run id.
* Each hard-coded site now carries a `TODO(P2-09)` comment pointing here.
* `results/tables/artifact_manifest.json.regeneration` records the same note
  machine-readably under `run_id_printed_by_documents` and
  `run_id_flag_is_not_that_id`.
* `tests/test_remediation_20260927.py` asserts the glossary run id
  (`_GLOSSARY_RUN_ID`) equals the run id in `paper_claim_guard.json`, so the two
  hard-coded copies cannot drift apart silently.

---

## 3. End-to-end command sequence

```powershell
# 1. pipeline: stages 1-15 + 16 equifinality + 17 holdout figures
#    + 18 sidecars/index/archive-manifest + 19 paper tables + 20 paper_values.json
.\.venv\Scripts\python.exe run_pipeline.py
# targeted re-run of just the frozen stages (+ the trailing provenance stages)
.\.venv\Scripts\python.exe run_pipeline.py --from-stage 13

# 2. documents (generated outside the stage graph)
.\.venv\Scripts\python.exe scripts\generate_paper.py
.\.venv\Scripts\python.exe scripts\generate_report.py

# 3. optional PDF via Playwright (report.pdf is gitignored)
.\.venv\Scripts\python.exe scripts\export_pdf.py

# 4. gates
.\.venv\Scripts\python.exe scripts\verify_paper.py --mode development   # PASS, 0 warnings
.\.venv\Scripts\python.exe scripts\verify_paper.py --mode submission    # FAIL: dirty tree only
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q             # 79 passed
```

The frozen run was produced as
`.venv\Scripts\python.exe run_pipeline.py --from-stage 13`.

The two document generators (`generate_paper.py`, `generate_report.py`) are
**not** stage-graph entries; run them after the pipeline.

### Stage graph

Stages are declared in `run_pipeline.STAGES` as
`(module_or_script, description, required_inputs, expected_outputs)`. Inputs are
checked *before* a stage runs and outputs *after*; any failure exits non-zero.
A stage whose name ends in `.py` is run as a subprocess with the active
`--config`; otherwise it is imported from `src/` and `main(config)` is called.
Script stages whose declared inputs are all older than their outputs report
`mode: "up-to-date"` and are skipped; stages with no declared inputs (e.g.
`build_paper_tables.py`, which reads many tables) always run.

| # | Stage | Produces |
|---|-------|----------|
| 1 | `01_fetch_water_quality` | `data_proc/reach_daily_observations.csv` |
| 2 | `02_build_network` | `data_proc/reach_attributes.csv` |
| 3 | `real_network` | segmented observations, `network_segments.csv`, `length_conservation.csv` |
| 4 | `03_baseline_transport` | *(legacy; skipped unless `--legacy`)* |
| 5 | `04_estimate_k` | `data_proc/k_estimates.csv` |
| 6 | `05_compute_residual_sgs` | `data_proc/sgs_training_data.csv` |
| 7 | `06_train_sgs_model` | `data_proc/models/training_metrics.json` |
| 8 | `07_coupled_prediction` | *(legacy; skipped unless `--legacy`)* |
| 9–12 | `08_validate_flux_budget`, `09_spatial_temporal_viz`, `10_gis_network_viz`, `11_cross_section_2d_viz` | figures; `gis_network_manifest.json`, **`figure2_basemap_manifest.json`**, `cross_section_manifest.json` |
| 13 | `12_nested_cv_transport` | `nested_cv_holdout_predictions.csv`, `nested_cv_metrics.csv`, `k_correction_saturation.json`, `nested_cv_rmse_bar.png`, **`per_reach_cv_metrics.csv`**, **`per_reach_paired_metrics.csv`**, **`reach_sensitivity.json`** |
| 14 | `13_filter_scale_sgs` | `filter_scale_metrics.csv`, `filter_scale_summary.json`, `filter_scale_sgs.png`, `filter_scale_sgs_box.png`, `les_filter_conceptual.png` |
| 15 | `14_identifiability_ksgs` | `supp_flux_diagnostics.png` |
| 16 | `15_dimensionless_sparse` | `dimensionless_sparse_coefficients.csv`, `dimensionless_sparse_summary.json`, `dimensionless_coefficients.png` |
| 17 | `16_equifinality_surface` | `equifinality_summary.json`, `equifinality_objective_surface.png` |
| 18 | `17_regenerate_holdout_figures` | `nested_cv_scatter_holdout.png`, `subgroup_rmse_r008_vs_trib.png` |
| 19 | `scripts/build_figure_sidecars.py` | `figure_sidecar_index.json`, `superseded_figures.json`, **`results/figures/paper/*.png` (mirror)** + `results/figures/paper/derived_archive_manifest.json` |
| 20 | `scripts/build_paper_tables.py` | `paper_main_results.csv`, `subgroup_metrics.csv`, `paper_filter_scale.csv`, `paper_claim_guard.json` |
| 21 | `scripts/paper_values.py` | `paper_values.json` |

Bold paths were the previously-undeclared outputs fixed in this pass.

---

## 4. Regeneration matrix

| Artifact | Regenerable? | Command | Notes |
|---|---|---|---|
| `data_proc/*`, stage tables/figures | Yes | `run_pipeline.py` | Needs `data_raw/` (HydroShare Excel + NHDPlus HR); raw data is gitignored and not published |
| `results/tables/per_reach_cv_metrics.csv` | Yes | `run_pipeline.py` (stage 13) | Written by `src/12_nested_cv_transport.py`; previously undeclared |
| `results/tables/per_reach_paired_metrics.csv` | Yes | `run_pipeline.py` (stage 13) | `_write_paired_reach_analysis`; previously undeclared |
| `results/tables/reach_sensitivity.json` | Yes | `run_pipeline.py` (stage 13) | Same stage; previously undeclared |
| `results/figures/*.png` (live) | Yes | `run_pipeline.py` (stages 11–18) | Per-figure generators are recorded in each sidecar's `generator` |
| `results/figures/sidecars/*.json` | Yes | `scripts\build_figure_sidecars.py` (stage 19) | Versionable since 2026-09-27 (see §6). `--force` overwrites generator-warmed sidecars |
| `results/tables/figure_sidecar_index.json` | Yes | `scripts\build_figure_sidecars.py` | |
| `results/figures/figure2_basemap_manifest.json` | Yes | `run_pipeline.py` (stage 10) | `src/10_gis_network_viz.py`; per-tile SHA-256 + attribution + licence |
| `results/figures/paper/*.png` | **Yes — mirrored in place** | `scripts\build_figure_sidecars.py` (stage 19) | Live-verified mirror (see §5); 40 figures, all `matches_canonical: true` as of this run. `--no-mirror` refreshes the manifest only |
| `results/figures/paper/derived_archive_manifest.json` | Yes | `scripts\build_figure_sidecars.py` | Records archive↔live hash equality per figure, plus the derived-set rule and historical entries |
| `results/tables/superseded_figures.json` | Yes | `scripts\build_figure_sidecars.py` | SHA-256 + size of the 11 pre-refresh renders, each with a `git show HEAD:…` recovery command |
| `results/tables/paper_values.json` | Yes | `scripts\paper_values.py` | Single numeric source of truth |
| `results/tables/paper_claim_guard.json`, `paper_main_results.csv`, `subgroup_metrics.csv`, `paper_filter_scale.csv` | Yes | `scripts\build_paper_tables.py` (stage 20) | |
| `results/tables/artifact_manifest.json` | Yes | `run_pipeline.py` | `--no-manifest` suppresses it |
| `paper.md`, `paper.html` | Yes | `scripts\generate_paper.py` | Outside the stage graph |
| `report.md`, `report.html` | Yes | `scripts\generate_report.py` | Outside the stage graph |
| `report.pdf` | Yes | `scripts\export_pdf.py` | Gitignored |
| `docs/*` status files | **No** | — | Hand-authored; no generator |
| `results/figures/gis_network_manifest.json`, `cross_section_manifest.json`, `spatial_temporal_manifest.json` | Yes | `run_pipeline.py` (stages 10–12) | Still gitignored; see §6 for why |

Document generators are **idempotent**: re-running `generate_paper.py` and
`generate_report.py` on the frozen run rewrites `paper.md`, `paper.html`,
`report.md`, `report.html` and `paper_values.json` byte-for-byte identically
(verified 2026-09-27).

---

## 5. `results/figures/paper/` is a verified mirror of the published figures

`results/figures/paper/` is **version-controlled** (`.gitignore` keeps
`!results/figures/paper/`) so a reader browsing the repo sees the same images the
documents show. It is not the live output directory — it is a **mirror** of it:

* the **live** figures are written to `results/figures/` by the stage-11…18
  generators and are gitignored except for the provenance JSON;
* **stage 19** (`scripts/build_figure_sidecars.py`) refreshes the mirror: it
  derives the published figure set programmatically, copies each live PNG over
  `results/figures/paper/<same-name>.png`, re-hashes it, and rewrites
  `derived_archive_manifest.json`. The archive keeps the project's existing
  `<stem>.png` naming — live and archived filenames already correspond 1:1.

### How the published set is derived (no hard-coded list, no fuzzy matching)

`published_figure_names()` returns

```
(live results/figures/*.png)
  ∩ ( sidecar stems  ∪  exact "<name>.png" tokens found in
        paper.md, paper.html, report.md, report.html )
```

Exact filename tokens only: `nested_cv_rmse_bar.png` matches itself, never a
prefix. On the frozen run this yields **40** figures: the manuscript's 10
(each with a sidecar) plus 30 appendix figures the report embeds. The report also
*mentions* ~20 further live PNGs in prose whose bytes it does not embed; those are
pipeline intermediates and are deliberately not mirrored (`results/figures/*.png`
stays gitignored for them).

### Current state (2026-09-27)

All **40** published figures were refreshed and are byte-identical to the live
figures (before: 0 of the 11 previously archived PNGs matched). The manifest
reports `counts: {published_figures: 40, matching: 40, drifted: 0}`.

Nothing was deleted. The 11 superseded renders are recorded in
`results/tables/superseded_figures.json` with their SHA-256, size and a recovery
command (`git show HEAD:results/figures/paper/<name>`); `HISTORICAL_README.md`
in this directory was updated to say the pre-2026-08-27 render is what it refers
to, and that the directory is now a live verified mirror.

### Repeating this (exact procedure for a maintainer)

```powershell
# 1. refresh the live PNGs and their sidecars
.\.venv\Scripts\python.exe run_pipeline.py
# 2. mirror them into results/figures/paper/ and rewrite the manifest
.\.venv\Scripts\python.exe scripts\build_figure_sidecars.py
#    -> prints "Archive mirror ...: N refreshed, M already current, K historical kept"
# 3. confirm the mirror is byte-exact (must report 0 problem(s))
.\.venv\Scripts\python.exe scripts\verify_paper.py --mode development
```

`--no-mirror` refreshes the manifest without copying (useful to inspect drift).
Stage 19 is idempotent: a second run reports `0 refreshed, 40 already current`.

`scripts/verify_paper.py` **fails closed** (both modes) if any published figure's
archived bytes differ from the live bytes, or if the manifest no longer describes
the bytes actually on disk — so tampering with either the PNG or the manifest is
detected. This is verified by
`test_regeneration_gate_fails_on_tampered_archived_png` and
`test_regeneration_gate_fails_when_archive_manifest_edited`, plus the standalone
`tmp/_tamper_proof.py` run.

---

## 6. Provenance and version control

Until 2026-09-27 `.gitignore` ignored `results/figures/*` wholesale, so the
sidecar JSON and the Figure 2 basemap manifest — the only record of how each
published figure was rendered, including the Esri World Imagery attribution,
licence note, source URL template and per-tile SHA-256 — could not be committed.
That undercut P2-09. The negation rules now are (surgical, metadata only):

```gitignore
results/figures/*
!results/figures/paper/
!results/figures/sidecars/
!results/figures/sidecars/*.json
!results/figures/figure2_basemap_manifest.json
```

Image binaries stay ignored: `results/figures/*.png` is still excluded, and so
are the sibling manifests `gis_network_manifest.json`,
`cross_section_manifest.json` and `spatial_temporal_manifest.json`, which
describe derived (non-published) figure sets. Widen those rules only if the
author wants them in-tree.

`tests/test_remediation_20260927.py` asserts both directions: that the sidecars,
the basemap manifest, `figure_sidecar_index.json`, `superseded_figures.json` and
`derived_archive_manifest.json` are **not** ignored, and that the bulky
`results/figures/*.png` (the live, non-`paper/` PNGs) and the sibling manifests
**are** still ignored. Note `results/figures/paper/*.png` *is* version-controlled
by the pre-existing `!results/figures/paper/` rule — that is the mirror of §5.

---

## 7. Regeneration verification gate

`scripts/verify_paper.py` runs `_check_regeneration_wiring` in both modes. It
imports `run_pipeline.STAGES` (read-only) and asserts that every provenance /
artifact view we commit deliberately is declared as an output of some stage:

* `paper_values.json`, `figure_sidecar_index.json`, `superseded_figures.json`,
  `per_reach_paired_metrics.csv`, `reach_sensitivity.json`;
* every `results/figures/<name>` for each `FIGURE_ORDER` entry that has a
  committed sidecar;
* `results/figures/figure2_basemap_manifest.json`,
  `results/figures/paper/derived_archive_manifest.json`.

An artifact that exists on disk but is declared by no stage is an orphan and
fails submission mode. The tamper proof is covered by
`test_regeneration_gate_fails_when_a_stage_output_is_dropped` and
`test_regeneration_gate_fails_when_a_figure_stage_output_is_dropped`.

The same function also enforces the archive mirror (§5): it recomputes the
SHA-256 of every archived PNG **and** of the corresponding live PNG from disk
(never trusting the manifest), fails if they differ, and fails if the manifest's
recorded hashes do not describe the bytes actually present. So neither editing
an archived PNG nor editing the manifest can hide drift. Covered by
`test_regeneration_gate_fails_on_tampered_archived_png` and
`test_regeneration_gate_fails_when_archive_manifest_edited`.

---

## 8. Captured hashes (frozen run, 2026-09-27)

```
paper.md                                                       340d5b47b9dfda5bca96d9240d34fe7ec4babcd65e068d3a71eee20145e5512e
paper.html                                                     ea6378aee7802c61519c4f4b90a313ec47e44465676580ff5f50286ee5ce5b93
report.md                                                      b798a10cf163ad36d0aaedf5a611fa02968f7289b69005ccd3c6cdd623ce0527
report.html                                                    8c9577d43496b2f691b15ea1081d7f4ffbbb8e8107a4f33290bb8e32c8275b87
results/tables/artifact_manifest.json                          8ba76315f2365c0bea6b97f150b40a18dd9b2c5729c530f64778854cd84ee512
results/tables/paper_values.json                               3df1a8eb0069966828515c7a725e6704d155678ba25c4823262519e010b447c4
results/tables/paper_claim_guard.json                          f41ed1d21601873ea7e083e3f63508368090dbe7d4c97b97320a7cbe06d8f0ca
results/tables/figure_sidecar_index.json                       8573f815ccc600d0c950e85573d929b705632f9be2fe9b1a55f5808b4eeb9803
results/tables/superseded_figures.json                         0d79891c1150d802c790b4f792c5054eef7f3828b68c9ad6acad57341d226660
results/tables/nested_cv_metrics.csv                           a787b6a3a095d89782c0fe3537877ac598f3f7c048c710f61a90c365b2a21a1a
results/tables/nested_cv_summary.json                          7a6caab3e4e0cf0df7eeb3c78b2df1acd62151cc8c549c58ba233c6278bec9ec
results/tables/k_correction_saturation.json                    ee0e027a0f618fcbb7194af9e2d5b9d444fa7c226348932602e27f35c558eaaa
results/tables/per_reach_paired_metrics.csv                    b313bfa99cb63e3f25642632834753ea8296097bf7cfe7c35cbe316080ef97fb
results/tables/reach_sensitivity.json                          1fc3608921854e1fc066c2274f977a00623deed8dc1390df77713b571d458962
results/tables/equifinality_summary.json                       e441a758a477f64cb416ff9b00443655623dbd83026597c691c5c7efb5390fba
results/tables/length_conservation.csv                         a246a838d3367481f870de218730b60cdd5eabcbd870dc7ae1b38a94de33a7dd
results/tables/domain_consistency_gate.csv                     f0e09b097e90b8d1b1c0d146d399720b28f8ed0dd81f6832230a88d6aff182d7
# archive mirror: each archived PNG == its live PNG (byte-identical by construction)
results/figures/paper/figure2_reach_assignment_and_samples.png  2562257ac073cd670d94e77519135c74379fdd6e3129bef72998b9242f25d202
results/figures/paper/nested_cv_scatter_holdout.png             007a894723e988e4ce3f3faa8711238e94ec1dfcdfbfb41a3d77da3395b1454a
results/figures/paper/equifinality_objective_surface.png        4907b6a9d1af414ec2abc2cfaae9ee1d9bbd86b16e1d8eab6974ce137a971d2c
results/figures/paper/identifiability_k_vs_sgs.png              9245557e5dc15a8e4a61887a7186ff1ad9054c2fa9b02d82502aee6a55b2807d
results/figures/figure2_basemap_manifest.json                  c53a1cd254a58c0d073ee4547f5cc3eab8078e91202bcf85c877c62b8692ece5
results/figures/paper/derived_archive_manifest.json            93397d649398df13e40c9a4d0570a59b132ddcb96f56a0ae1dd9d3fe224226d4
```

Headline values in `paper_values.json.main_results`: Baseline `0.048499`,
MLP `0.050704`, Random Forest `0.055661`, k-correction `0.048476`,
`mlp_rmse_lt_baseline = False`.

Patch/commit organisation for this pass: `patches/20260927/COMMIT_PLAN.md`.

---

## 9. Remaining open items

1. `verify_paper.py --mode submission` fails **only** on the dirty working tree
   (`git dirty=true`). Applying and committing the patches clears it.
2. **Resolved 2026-09-27:** `results/figures/paper/` is now a verified mirror of
   the live figures (§5) — all 40 published figures match byte-for-byte and stage
   19 refreshes them automatically. The 11 superseded renders are recorded in
   `results/tables/superseded_figures.json` and remain recoverable from git.
3. A human manuscript pass over residual wording is still recommended.
4. Verified path-domain table for R001/R002/R005/R006/R007 is still
   declared/provisional; the domain-consistency gate flags R002 (ΣL_control
   92.29 m vs recorded support 170.22 m) and four more reaches honestly.
5. The sparse dimensionless closure remains **provisional** (S* R² −2.583342).
