# Engineering notes — East River CO₂ + S_sgs methods paper

**Updated:** 2026-08-16  
**Policy:** real data only; no synthetic fallback; no claim that Residual-AI beats Baseline.

This file freezes architecture decisions and manuscript numbers so later edits do not silently rewrite the paper story.

---

## Contribution framing (accepted; ChatGPT Round 1)

**One-liner:** Transport-coupled, reach-held-out evaluation of river-network CO₂ closures on public East River data: filter-induced residual \(S_\mathrm{sgs}\), practical equifinality of \(S_\mathrm{sgs}\) versus \(k\) under concentration-only observations, and an operable multi-Δx filter definition (LES-analog = Methods coarse-graining language only).

**Not the story:** “AI improved \(p\mathrm{CO}_2\) / \(C_\mathrm{aq}\) prediction.”

## Evaluation boundaries disclosed after Round 1 audit

| Issue | Local evidence | Manuscript action |
|-------|----------------|-------------------|
| `c_in` fallback to current-row observed \(C_\mathrm{aq}\) when upstream state missing | `src/03_baseline_transport.py`; related paths in `src/12`, `src/13` | Methods limitation: not perfect holdout isolation for every sample |
| Filter ordering midpoint Y then X fallback | `src/13_filter_scale_sgs.py` | State as operator boundary; full directed-network filter deferred (would change frozen Δx metrics) |
| “Nested CV” naming | Outer `LeaveOneGroupOut` + fold-specific imputation/scaling; no explicit inner HP nest found | Prefer “outer leave-one-reach-out + fold-specific scaling”; keep transport-coupled scoring |
| Reach imbalance | R008 n=58; R001/R006/R007 n=1 | Report evidence weights; n=1 reaches schematic only |

**Results lead order (accepted):**

1. Negative accuracy: Residual-AI does not beat Baseline on held-out \(C_\mathrm{aq}\).
2. Filter-scale dependence of diagnosed \(|S_\mathrm{sgs}|\).
3. Sparse \(\Pi\) form (interpretable, weak nested CV).
4. \(k\)-correction: slightly lower C RMSE, flux collapse.
5. Integrated identifiability diagnosis (practical equifinality).

---

## Frozen primary numbers (loo-reach, n=120)

| Scheme | Model | C RMSE | F total (mol m⁻² d⁻¹) |
|--------|-------|--------|------------------------|
| Baseline | — | **0.0284** | **3.24** |
| Residual-AI | MLP | **0.0573** | 69.5 |
| Residual-AI | RF | **0.0745** | 143.3 |
| k-correction | XGBoost | **0.0244** | **0.031** |
| Sparse Π | LASSO | **0.0506** | 244.2 |

- \(k_\mathrm{eff}/k_\mathrm{emp}\) median (k-correction): **≈ 3.35×10⁻⁴**
- In-sample Residual-AI \(R^2\approx0.997\): **appendix only**
- Filter-scale mean \(|S_\mathrm{sgs}|\): native **1.92** → 2× **1.12** → 4× **1.05** → study-reach **1.00**

Source CSVs: `results/tables/nested_cv_metrics.csv`, `identifiability_summary.json`, `filter_scale_metrics.csv`, `sparse_pi_nested_cv.csv`.  
Paper-facing consolidation: `results/tables/paper_main_results.csv`, `paper_filter_scale.csv`, `paper_claim_guard.json` (built by `scripts/build_paper_tables.py`).

---

## CV design (do not weaken)

- **Unit of holdout:** reach (`loo_reach`) or date (`loo_date`); never random row split for main tables.
- **Protocol:** train closure on other groups → predict \(S_\mathrm{sgs}\) or \(k_\mathrm{eff}\) → plug into same quasi-steady transport as Baseline → score held-out \(C_\mathrm{aq}\) and model-derived \(F_{\mathrm{CO}_2}\).
- **Evidence weights:** R008 (n=58) primary; multi-sample tributaries secondary; R001/R006/R007 (n=1) schematic only.
- **Seeds:** RF/XGBoost/MLP `random_state=42` in `configs/east_river.yaml`.

---

## Manuscript vs appendix metrics

| Metric | Role |
|--------|------|
| Nested CV \(C_\mathrm{aq}\) / \(F_{\mathrm{CO}_2}\) (loo-reach) | **Manuscript main** |
| Subgroup RMSE (R008 vs trib) | Manuscript supporting |
| Filter-scale \(|S_\mathrm{sgs}|(\Delta x)\) | Manuscript methods result |
| Identifiability / flux tradeoff | Manuscript methods result |
| Sparse Π equation + nested CV | Form OK; prediction weak — report honestly |
| In-sample \(R^2\) | **Appendix only** |

---

## Flux language (reviewer risk)

\(F_{\mathrm{CO}_2}\) totals are **model-derived flux diagnostics / proxies** from \(k(C-C_\mathrm{eq})\), not chamber- or eddy-validated reach fluxes.

Use: “practical equifinality under concentration-only observations.”  
Avoid: “\(S_\mathrm{sgs}\) and \(k\) are fundamentally non-identifiable.”

---

## Failed / out-of-scope enrichments (do not revive as main path)

| Attempt | Status |
|---------|--------|
| WQP same-day merge | **0/120** |
| StreamPULSE East River / Gothic / Coal Creek | **0 sites** |
| PySINDy | install failed → LASSO only |
| CONUS_carbon continental rasters | structure clone only |
| CH₄ / GRiMeDB | out of scope for this paper |

---

## Pipeline stages that own the paper story

| Stage | Script | Role |
|-------|--------|------|
| 12 | `src/12_nested_cv_transport.py` | Main accuracy table |
| 13 | `src/13_filter_scale_sgs.py` | LES-analog \(\Delta x\) |
| 14 | `src/14_identifiability_ksgs.py` | \(S\)–\(k\) tradeoff |
| 15 | `src/15_dimensionless_sparse.py` | Sparse \(\Pi\) form |
| report | `scripts/generate_report.py` | HTML/MD delivery |
| tables | `scripts/build_paper_tables.py` | Paper CSV consolidation |

---

## ChatGPT Pro (advisor only)

Consultation URL (2026-08-16 literature + framing): https://chatgpt.com/c/6a815d47-94ec-83ea-90fc-f12041638002  
Earlier framing note: https://chatgpt.com/c/6a809d47-8f3c-83ea-af37-a6a1f643f726  

Accepted: contribution framing, Results lead with negative accuracy, EMS journal + Markovich et al. (2022) structure exemplar, H1/H2/H3 falsification tests, practical-equifinality wording, DO-NOT-CLAIM list.  
Rejected / deferred: inventing accuracy wins; claiming AI beats Baseline.


## Figure style (2026-08-16)
- SciencePlots 2.2.2 + `science`/`no-latex`; Times New Roman for Latin.
- Chinese axis labels removed from scientific figures (TNR missing CJK glyphs); Chinese retained in report/paper captions/body.
- FIG_DPI=300.

