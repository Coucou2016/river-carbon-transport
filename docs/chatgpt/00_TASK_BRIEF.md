# Task brief — ChatGPT advisor (Round 7+)

**Date:** 2026-08-17  
**Public repo:** https://github.com/Coucou2016/river-carbon-transport  
**This folder:** https://github.com/Coucou2016/river-carbon-transport/tree/main/docs/chatgpt/  
**Prior dialog (preferred reuse):** https://chatgpt.com/c/6a818974-cd6c-83ea-8241-812dc9fd2598  
**Executor:** Cursor (sole local implementer). ChatGPT = external text advisor only (browse GitHub Markdown; no file uploads).

---

## Roles

| Role | Responsibility |
|------|----------------|
| **ChatGPT** | Critique manuscript quality; propose EMS-style Abstract/Intro/Discussion prose; flag unreal claims and paper↔report leakage; web search ON for writing craft / exemplar papers |
| **Cursor** | Independently verify every claim against frozen metrics + `src/`; implement accepted edits; regenerate `paper.html`/`paper.md`/`report.*`; commit+push |

## Goals (this turn)

1. Mature the EMS methods/diagnostics manuscript toward submission-ready English prose (Markovich / Bennett / Vilas structural imitation).
2. **Strict paper vs research-report separation.**
3. Audit missing pieces, fabricated/unreal claims, inconsistencies vs immutable metrics.
4. Keep the **negative Residual-AI result** prominent and honest.

## Paper vs research report (immutable rule)

| Artifact | Allowed | Forbidden |
|----------|---------|-----------|
| **Paper** (`paper.html` / academic body from `scripts/generate_paper.py`) | Equations, HydroShare/USGS/NHD citations, frozen metrics, Methods disclosure of evaluation boundaries in academic language | Absolute Windows paths (`D:\…`, `C:\Users\…`), `.venv`, pipeline script filenames as process narrative (`src/03_….py`, `scripts/build_paper_tables.py`), engineering diary tone, “教学式” teaching digressions as main caption voice |
| **Research report** (`report.html` / `report.md`) | Local paths, stage script names, machine workflow, teaching five-part figure notes | Contradicting frozen metrics; inventing data |

## Immutable scientific facts (never invent / never invert)

Leave-one-reach-out grouped transport-coupled evaluation (**not** “nested CV” unless an inner hyperparameter nest is declared), **n=120** real HydroShare:

| Scheme | Held-out C_aq RMSE | Notes |
|--------|-------------------|--------|
| Baseline | **0.0284** | F_CO2 diagnostic total ≈ **3.24** |
| Residual-AI MLP | **0.0573** | **WORSE** than Baseline |
| Residual-AI RF | **0.0745** | WORSE |
| k-correction | **0.0244** | F_CO2 collapses **3.24 → ~0.03**; median k_eff/k_emp ≈ **3.4×10⁻⁴** |
| Sparse Π | **≈0.051** (0.0506) | Interpretable; still worse than Baseline |

- In-sample R²≈0.997 = **overfit; appendix only**
- Sparse Π form: S*_z ≈ 1.059 + 1.536 Fr − 1.669 Slope − 2.179 h/W
- Filter |S_sgs|: **1.92** (Δx≈838 m) → **1.00** (~26 km); study-reach sample cells = **6**
- Reach n: R001=1, R002=3, R003=15, R004=24, R005=17, R006=1, R007=1, R008=58
- F_CO2 = **model flux diagnostic**; cross-sections idealized, **not ADCP**
- Real data only; mark genuine gaps as **待补充** (authors, Gao DOI, Alk/N/P/PAR, WQP 0/120, StreamPULSE, width sensitivity, etc.)

## Acceptance criteria for ChatGPT advice

Cursor will **ACCEPT** advice that:
- Improves EMS voice / structure without inventing numbers
- Removes paper↔report leakage
- Clarifies limitations already evidenced in code/docs
- Strengthens negative-result + equifinality framing

Cursor will **REJECT** advice that:
- Claims Residual-AI beats Baseline
- Promotes in-sample R² as skill
- Treats F_CO2 as independently validated flux
- Invents DOIs, authors, Alk/N/P/PAR coverage, WQP merges, StreamPULSE sites
- Requires re-running Stage 12/13 with changed protocol that would silently rewrite frozen metrics this turn

## Companion briefs in this folder

1. `01_PAPER_CURRENT.md` — current Abstract/Intro/Methods/Results claims (no local paths)
2. `02_REPORT_VS_PAPER_AUDIT.md` — leakage findings
3. `03_DATA_INTEGRITY_CHECKLIST.md` — real vs 待补充 vs risk
4. `04_QUESTIONS_FOR_CHATGPT.md` — numbered questions for this round

Also read: `../PAPER_FRAMEWORK.md`, `../ENGINEERING_NOTES.md`, `../REVIEW_ROUNDS.md`, repo root `paper.md`, `REAL_DATA_AUDIT.md`.
