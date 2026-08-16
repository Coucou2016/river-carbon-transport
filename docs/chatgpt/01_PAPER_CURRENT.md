# Current paper claims — excerpts for ChatGPT (no local paths)

**Source of truth for rendered HTML:** regenerated from `scripts/generate_paper.py` → `paper.html`  
**Thin outline twin:** `paper.md` (not a full manuscript dump)  
**Repo tip at brief creation:** verify on GitHub `main` after push.

Target journal: *Environmental Modelling & Software* (methods/diagnostics).  
Structural exemplars: Markovich et al. 2022; Bennett et al. 2013; Vilas et al. 2023.

---

## Title (EN)

Transport-coupled evaluation of river-network CO₂ closures: Evidence for practical equifinality under concentration-only observations

## Authors / affiliation

待补充

## Abstract (current EN/CN hybrid body — needs EMS-ready rewrite)

Environmental-model evaluation can favor a closure that reproduces concentration while distorting the underlying process partition. We develop a transport-coupled diagnostic framework for river-network CO₂ that combines an operational spatial filter, reach-held-out cross-validation, and comparison of alternative unresolved-process closures using public East River campaign data (HydroShare; n=120; 8 logical reaches) mapped to NHDPlus HR. The filter defines a residual source/sink term S_sgs without treating the problem as turbulence LES.

**Main held-out concentration results:** C_aq RMSE Baseline **0.0284**; Residual-AI MLP **0.0573**; RF **0.0745** — learned residual closures do **not** beat Baseline. k-correction lowers C_aq RMSE to **0.0244**, coinciding with k_eff/k_emp ≈ **3.4×10⁻⁴** and model flux diagnostic F_CO₂ from ~**3.24** to ~**0.03**. Filter-scale mean |S_sgs| from **1.92** (Δx≈838 m) to **1.00** (study reach; sampled cells = 6). Sparse dimensionless form S*_z ≈ 1.059 + 1.536 Fr − 1.669 Slope − 2.179 h/W has reach-held-out C RMSE ≈ **0.051**, still worse than Baseline. In-sample R²≈0.997 appendix only.

**Contribution:** methodological — operable spatial filter, transport-coupled validation protocol, and practical equifinality / closure compensation under concentration-only observations. Not “AI improves accuracy.”

### Highlights

1. Reach-held-out Residual-AI closures do not outperform the process Baseline (0.0573/0.0745 vs 0.0284).
2. Lower C_aq RMSE from k-correction coincides with model-flux collapse (~3.24→~0.03).
3. Spatial filtering exposes scale dependence and practical S_sgs–k equifinality.

---

## Introduction outline (current)

1. Evaluation ≠ minimize prediction error alone; compensation can hide in wrong process terms (Bennett 2013; Markovich 2022; Vilas 2023).
2. River-network CO₂: transport + sources/sinks + gas exchange (Saccardi & Winnick 2021; Raymond k).
3. Concentration mismatch can be assigned to S_sgs **or** k; concentration alone may not discriminate.
4. Spatial coarse-graining / filter-induced residual (LES-analog only at operator level; Yuval & O’Gorman 2020 analogy). Gao *Innovation* draft = 待补充 DOI only.
5. East River n=120; R008 n=58 vs n=1 schematic reaches; transport-coupled leave-one-reach-out; disclose c_in fallback to observed C_aq when upstream missing.
6. Questions: (i) |S_sgs|(Δx); (ii) distinguishability of S vs k; (iii) sparse Π generalization.
7. Contribution hierarchy: filter definition → protocol → practical equifinality. DO NOT CLAIM list present.

---

## Methods outline (2.1–2.8)

| § | Content |
|---|---------|
| 2.1 | HUC 14020001; 120 samples 2019-08-02–11; reach counts; NHD/HR; USGS 09112500; DIC/DOC ~41/120; Alk/N/P/PAR 待补充; WQP 0/120; StreamPULSE none; serial R001–R008 logical chain; width proxy disclosed |
| 2.2 | Eq. (1)/(4) mass balance with τ_d, A_s, q_A; F_CO₂ = k(C−C_eq); Raymond ln(k600); Sc correction; C_eq 待补充 full formula; idealized trapezoid cross-sections (not ADCP) |
| 2.3 | Reach-local filter; chainage with Y→X midpoint fallback (not full topology); S_sgs diagnosis Eq. (5) |
| 2.4 | Baseline / Residual-AI / k-correction closures |
| 2.5 | Leave-one-reach-out grouped transport-coupled CV; **not** called nested unless inner HP loop declared; c_in fallback disclosed |
| 2.6 | Primary: held-out C RMSE; secondary: sample-summed ΣF diagnostic |
| 2.7 | S_implied Eq. (6); practical equifinality language |
| 2.8 | Sparse Π LASSO form + weak predictive skill |

---

## Results claims (lead order)

1. Residual-AI does not beat Baseline (0.0573 / 0.0745 vs 0.0284).
2. Concentration vs flux diagnostics disagree for k-correction (0.0244 with flux collapse).
3. Practical S–k compensation (Eq. 6).
4. Filter-scale |S_sgs| 1.92→1.00.
5. Sparse Π compact but predictively insufficient (0.0506 > 0.0284).

Figures: Fig. 1–7 main; S1–S4 supporting; A1 in-sample appendix.

---

## Discussion / Conclusions (current stance)

- Failed residual generalization is a modelling diagnosis, not “ML always fails.”
- Lower C RMSE without process fidelity when flux diagnostic collapses.
- Practical equifinality in restricted sense (Baseline–k contrast is cleanest evidence).
- Filter/sparse diagnose; do not solve prediction.
- Limitations: c_in fallback; Y→X filter order; reach imbalance; F diagnostic; idealized geometry; covariate gaps.
- Conclusions restate three hard points; no CONUS/CH₄ completion claim.

---

## Known prose quality issues (for Round 7 critique)

- Abstract still CN/EN hybrid; needs clean ≤250-word EMS English (+ optional Chinese twin separately).
- Intro/Methods still mix bilingual fragments and engineering disclosure tone.
- `paper.md` is a stub outline, not submission prose.
- Figure blocks currently carry teaching-style five-part notes better suited to the **report**.
