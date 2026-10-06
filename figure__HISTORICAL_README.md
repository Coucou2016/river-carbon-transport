# HISTORICAL — the pre-2026-08-27 render of this directory

This note applies to the **pre-2026-08-27** generation of `results/figures/paper/`.
Those PNGs belonged to a superseded result generation, disagreed with the
current development tables after the blocking audit
(`审查文档/审查文档_严格审稿与真实性证据审计_20260827.md`), and were not to be
cited as current pipeline output.

- Do **not** cite a pre-2026-08-27 PNG as the current pipeline output.
- Do **not** sync a pre-2026-08-27 PNG into `paper.md` / `paper.html`.
- Regenerate figures only after P0 control-volume, routing, k-correction,
  flux-estimand and filter-scale fixes are closed and a new
  `results/tables/artifact_manifest.json` is written.

## Status update (2026-09-27): this directory is now a live, verified mirror

The superseded renders were **replaced in place** by stage 19
(`scripts/build_figure_sidecars.py`), so the PNGs in this directory are now
byte-identical to the live figures in `results/figures/` that `paper.md`,
`paper.html`, `report.md` and `report.html` embed. This directory is no longer
historical output — it is the version-controlled mirror of the published
figures, so a reader browsing the repo sees exactly what the documents show.

- Machine-checkable record: `derived_archive_manifest.json`
  (`figures[*].matches_canonical` must be true for every entry).
- The 11 replaced renders are **not deleted**; each SHA-256 is recorded, with a
  `git show HEAD:...` recovery command, in
  `results/tables/superseded_figures.json`.
- `scripts/verify_paper.py` fails closed if this directory stops being a
  byte-exact mirror (including if the manifest itself is edited).

Earlier status pointer (historical context): `docs/ACTIVE_FIX_STATUS_20260828.md`.
Current status pointer: `docs/ACTIVE_FIX_STATUS_20260927.md` and
`docs/PIPELINE_AND_REGENERATION.md`.
