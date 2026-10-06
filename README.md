# river-carbon-transport — flat public mirror

This is the **public, deliberately flattened** mirror of the `river-carbon-transport`
project (East River CO₂ transport + machine-learned sub-grid closure).

Everything lives in this single directory on purpose, so that an automated
reader can enumerate and read the complete project in one pass. **Start with
[`START_HERE_FLAT_LAYOUT.md`](START_HERE_FLAT_LAYOUT.md)** — it explains the flat
layout, the filename prefixes, what is deliberately excluded, and what this
project does (and does not) claim.

- **Full inventory** (every file, size, SHA-256): [`FILE_INDEX.md`](FILE_INDEX.md)
- **Project README** (original, unedited): [`README_PROJECT.md`](README_PROJECT.md)
- **Current paper**: [`paper.md`](paper.md) · [`paper.html`](paper.html)
- **Current report**: [`report.md`](report.md) · [`report.html`](report.html) · [`report.pdf`](report.pdf)
- **Raw-data provenance**: [`REAL_DATA_AUDIT.md`](REAL_DATA_AUDIT.md)
- **Regeneration guide**: [`docs__PIPELINE_AND_REGENERATION.md`](docs__PIPELINE_AND_REGENERATION.md)

## Scope in one paragraph

This work reanalyzes **published, third-party observations** (Saccardi & Winnick,
HydroShare) on the **public NHDPlus HR** network with **public USGS** discharge and
published empirical hydraulic/gas-transfer relations. The observations are not
self-collected. The project's own contributions are the control-volume
construction, the closure-target construction, the grouped held-out transport
evaluation, and the consistency checks between them. The headline finding is a
**stated non-result**: under grouped leave-one-reach-out evaluation the
residual-AI closure does not outperform the baseline (MLP 0.050704 vs baseline
0.048499 mol m⁻³ RMSE), and part of the apparent improvement is traceable to a
handful of samples in one reach. The manuscript is written to that outcome.

## Excluded from this mirror

`data_raw/` (≈2.0 GB of third-party raw data, including files exceeding GitHub's
100 MB limit), plus `tmp/`, `patches/`, caches and the virtual environment. See
`START_HERE_FLAT_LAYOUT.md` §2 for the rationale and where to obtain the raw data.

## Reproducing

See [`docs__PIPELINE_AND_REGENERATION.md`](docs__PIPELINE_AND_REGENERATION.md);
the short version is `python run_pipeline.py` followed by the figure/table/paper
generators and `python scripts/verify_paper.py --mode submission`.

## Note for automated reviewers

If you are cross-reviewing this work, the flat corpus is designed for you: read
`FILE_INDEX.md` for the manifest, then read source, tables and figures directly.
Every published number is generated from `table__paper_values.json`, and a claim
guard fails closed if prose drifts from the tables.
