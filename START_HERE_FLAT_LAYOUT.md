# START HERE — why this repository has no subfolders

**This repository is a deliberately flattened, single-directory mirror of the
`river-carbon-transport` project.** There are no subdirectories under the
repository root, and that is intentional. Every source file, document, figure,
table, model and review record sits side by side in one flat namespace so that
an automated reader — a browsing LLM, another coding agent, a script, or a
human — can enumerate and fetch the *entire* project without walking a tree,
guessing paths, or being silently blocked by directory-level access limits.

If you are an automated reviewer (ChatGPT, another agent, a crawler), the useful
pattern is: read this file, then `FILE_INDEX.md` for the complete inventory, then
the files you need by their flat name.

---

## 1. How the flat names encode provenance

Because there are no folders, the original directory is encoded in each
filename as an ASCII prefix. Nothing about where a file came from is lost — it
is in the name.

| Flat prefix | Original location | Contents |
|---|---|---|
| *(none)* | repository root | Canonical entry points: `paper.md`, `paper.html`, `report.md`, `report.html`, `report.pdf`, `README.md`, `REAL_DATA_AUDIT.md`, `requirements*.txt`, `run_pipeline.py`, `setup_env.*`, `pytest.ini` |
| `src__` | `src/` | Pipeline stages (numbered), plus shared modules |
| `scripts__` | `scripts/` | Paper/report/table generators, verification gate |
| `tests__` | `tests/` | Test suite |
| `table__` | `results/tables/` | Machine result tables (CSV/JSON) and `paper_values.json` |
| `figure__` | `results/figures/paper/` | Published figures (PNG) referenced by the paper/report |
| `figure_sidecar__` | `results/figures/sidecars/` | Per-figure provenance sidecars |
| `figure_manifest__` | `results/figures/` | Figure manifests incl. the Figure 2 satellite-basemap record |
| `dataproc__` | `data_proc/` | Processed (small) data tables |
| `model__` | `data_proc/models/` | Trained model binaries + training metrics |
| `docs__` | `docs/` | Engineering notes, status docs, pipeline/regeneration guide |
| `chatgpt__` | `docs/chatgpt/` | The ChatGPT review-round briefs and audits |
| `notebooks__` | `notebooks/` | Reproduction / analysis notebooks |
| `configs__` | `configs/` | Configuration |
| `paperver_vN__` | `paper_versions/vN_*/` | Historical paper drafts (superseded; kept for audit) |
| `review__` | the Chinese-named review directory | External review rounds (2026-08-27, 2026-09-19, 2026-09-27), including reviewer reports, evidence JSON, and the author's revised draft |

Sub-paths that contained a further directory are joined with `__`
(e.g. `review__20260927__revised_draft__paper_revised.md`). All names have been
transliterated to plain ASCII so no reader is tripped up by CJK filenames.

## 2. What is included, and what is deliberately not

**Included (~309 files, ~114 MB):** all pipeline source, the full test suite,
all machine tables, the published figures plus their provenance sidecars, the
processed small-data tables and trained models, every engineering/status
document, the ChatGPT review rounds, the external referee rounds, all historical
paper drafts, and the current paper/report in Markdown, HTML and PDF.

**Excluded, on purpose:**

- `data_raw/` — ~2.0 GB of third-party raw data (HydroShare Excel, NHDPlus HR
  archives, USGS gauges, WQP extracts). It is *not* redistributed here because
  (a) it is third-party material with its own terms, and (b) it contains files
  far above GitHub's 100 MB per-file limit (e.g. a 551 MB `.gpkg`, 271 MB `.zip`).
  `REAL_DATA_AUDIT.md` and `dataproc__data_provenance.csv` record exactly where
  every raw input came from and how to obtain it.
- `tmp/`, `patches/`, `__pycache__/`, `.venv/` — scratch, agent working files,
  build caches and the virtual environment; none are pipeline inputs or outputs.

Nothing in the excluded set is needed to *read* the science; it is needed only to
re-execute stage 1 from raw. The regeneration path is documented in
`docs__PIPELINE_AND_REGENERATION.md`.

## 3. What this project actually claims (read before auditing)

This is a **public-data reanalysis**. The temperature, pCO₂, DO, DOC and DIC
observations originate from Saccardi & Winnick's published dataset (HydroShare);
the river network is public NHDPlus HR; discharge is public USGS; hydraulic
geometry and gas-transfer coefficients are published empirical relations.
**The observations here are not self-collected, and this repository does not
claim otherwise.** What is this project's own work: the control-volume
construction, the closure-target construction, the grouped held-out transport
evaluation, and the cross-checks among them.

The headline result is a **non-result, stated as such**: under grouped
leave-one-reach-out evaluation the residual-AI closure does **not** beat the
baseline (MLP 0.050704 vs baseline 0.048499 mol m⁻³ RMSE), and part of the
apparent gain traces to a small number of samples in one reach. The manuscript
is written to that result; it is not written as a success claim.

## 4. Verification state

- `test__`… — see `tests__*.py`; the suite passes (102 tests).
- `scripts__verify_paper.py` runs in two modes. `--mode development` and
  `--mode submission` both pass with zero warnings on the frozen run.
- Numbers in the paper and report are **generated**, not typed: they are read
  from `table__paper_values.json`, which is built from the machine tables. A
  claim guard fails closed if prose drifts from the tables.

## 5. Regenerating everything

The full chain, the frozen run id, the environment, and the artifact→command
matrix are recorded in `docs__PIPELINE_AND_REGENERATION.md` and
`table__artifact_manifest.json`. In short:

```
python run_pipeline.py
python src/17_regenerate_holdout_figures.py
python scripts/build_figure_sidecars.py
python scripts/paper_values.py
python scripts/generate_paper.py
python scripts/generate_report.py
python scripts/export_pdf.py
python scripts/verify_paper.py --mode submission
```

## 6. Why flattening is worth the odd filenames

The cost is cosmetic — paths are lost from the names. The benefit is that the
whole deliverable is a flat, greppable corpus: a single `ls` or directory
listing is a complete manifest, an agent can be handed the repo and read it
exhaustively, and there is no depth at which retrieval quietly stops. This
layout exists specifically to make independent cross-review easy. If you are
automating a review, start with `FILE_INDEX.md`.
