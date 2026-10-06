# Method Recalculation — Provenance & Decision Record

> **SUPERSEDED — NOT FOR SUBMISSION (2026-08-27).**  
> Blocking defects (P0-01 … P0-06) were identified in
> `审查文档/审查文档_严格审稿与真实性证据审计_20260827.md`.  
> Numbers below are historical development results only. See
> `docs/SUPERSEDED_NOTICE.md`.

Date: 2026-08-18 (audit following external formal review)

This document records (1) the verified provenance of every physical relationship
used in the recalculation, (2) the defects found in the prior implementation, and
(3) the fix applied to each. It is the evidence base for "data/methods are
truthful, accurate, and complete."

---

## 1. Verified physical relationships (with sources)

### 1.1 Gas transfer velocity k600

**Primary — Ulseth et al. (2019), *Nature Geoscience* 12:259–263, DOI 10.1038/s41561-019-0324-8.**

Piecewise power law on energy dissipation rate eD = g·S·u (m² s⁻³), where
g = gravity (9.81 m s⁻²), S = stream slope (m m⁻¹), u = mean velocity (m s⁻¹):

- eD ≥ 0.02 :  ln(k600) = 1.18·ln(eD) + 6.43
- eD < 0.02 :  ln(k600) = 0.35·ln(eD) + 3.10

k600 in m d⁻¹. Valid only for eD ≤ 1.052 m² s⁻³ (upper boundary of the fitted data).
This is the formulation used by the original East River model
(Saccardi & Winnick 2021, GBC) — confirmed via Horgby et al. (2019, *Nat. Commun.*
10:4175, DOI 10.1038/s41467-019-12905-z), which states Ulseth's relationship
"accounts for the high turbulence owing to steep-channel slopes and elevated
streambed roughness of mountain streams."

**Sensitivity — Raymond et al. (2012), *Limnol. Oceanogr.: Fluids Environ.* 2:41–53,
DOI 10.1215/21573689-1597669.**

Slope–velocity power laws (k600 in m d⁻¹, V in m s⁻¹, S unitless):

- Model 3:  k600 = 1162 · S^0.77 · V^0.85
- Model 4:  k600 = 951.5 · (V·S)^0.76

The journal is *LOFE*, **not** Nature Geoscience. The prior implementation's
claim `ln(k600) = 5.139 + 0.594·ln(u) + 0.403·ln(slope)` "Raymond 2012 Nature
Geoscience" is **not** found in Raymond et al. (2012) Table 2 and is removed.

### 1.2 Hydraulic geometry (width / depth / velocity from discharge)

**Raymond et al. (2012)** (1026 paired measurements; exponents b=0.29, d=0.42,
f=0.29; coefficients a=0.4, c=12.88, e=0.19):

- depth   D = 0.4 · Q^0.29   (m)
- width   W = 12.88 · Q^0.42 (m)
- velocity V = 0.19 · Q^0.29 (m s⁻¹)

The prior "width = lon-span / n_samples clip(2,15)" is a sampling-spacing proxy,
not a channel width, and is removed. Width now follows hydraulic geometry with an
NHDPlus HR cross-check and a systematic three-way sensitivity.

### 1.3 Henry's law for CO2 (temperature-dependent)

**NIST Chemistry WebBook (Rolf Sander compilation), CO2 in water:**

- k°H(298.15 K) = 0.035 mol kg⁻¹ bar⁻¹ (representative)
- d(ln kH)/d(1/T) = 2400 K

kH(T) = k°H · exp( 2400 · (1/T − 1/298.15) ), then C_aq = kH(T) · pCO2(atm) · ρ_water.

The prior implementation fixed kH = 0.033 mol L⁻¹ atm⁻¹ regardless of temperature
(the `temp_c` argument was unused). 0.033 is closer to the 25 °C value than 10 °C.
Each sample now uses its own temperature.

### 1.4 Schmidt number

Wanninkhof (1992): Sc_CO2 = 1911 − 118.11·T + 3.4537·T² − 0.04132·T³ (T in °C),
then k_CO2 = k600 · (Sc/600)^−0.5. (Unchanged; already correct.)

---

## 2. Defects confirmed in the prior implementation

| # | Defect | Location | Severity |
|---|--------|----------|----------|
| 1 | Real tributary network hardcoded as R001→…→R008 serial chain | `east_river_real_data.py:23-32,257-260` | Fatal |
| 2 | Held-out sample's own C_obs used as C_in when no upstream state | `03_baseline_transport.py:82-86` | Fatal |
| 3 | k-correction ratio clipped to exp(-8) lower bound (3.35e-4 = e^-8) | `12_nested_cv_transport.py:276` | Fatal |
| 4 | Residual target adds mol/m²/d (evasion) + mol/m³ (deficit/h) | `05_compute_residual_sgs.py:59-62` | Fatal |
| 5 | k_needed built once on ALL observations before CV (fold leakage) | `12_nested_cv_transport.py:609` | Major |
| 6 | "width" = longitude span / n_samples | `east_river_real_data.py:250-255` | Major |
| 7 | k600 formula mis-attributed to "Raymond 2012 Nature Geoscience" | `east_river_real_data.py:201-209`, `04_estimate_k.py:21-29` | Major |
| 8 | Henry constant fixed, temperature argument unused | `utils.py:59-67` | Major |
| 9 | filter-scale falls back to C_obs when no upstream cell | `13_filter_scale_sgs.py:220-224` | Major |
| 10 | flux "total" = Σ density (not Σ F·A) | `12_nested_cv_transport.py:144` | Major |
| 11 | filter-scale chainage sorted Y→X (not flow direction) | `13_filter_scale_sgs.py:140-153` | Major |
| 12 | Residual-AI target non-negative constraint (S_sgs should be signed) | `ml_models.py:36` | Major |

---

## 3. Fix plan (7 phases, matching external review)

1. **Physics**: real NHDPlus HR directed topology; independent boundary; hydraulic
   width; temperature-dependent Henry; Ulseth 2019 k600 (Raymond 2012 sensitivity).
2. **Evaluation**: no test-row C_obs can enter C_in.
3. **Closure target**: recompute dimensionally consistent S_sgs from conservation;
   Residual-AI signed.
4. **k-correction**: per-fold target construction, no lower-bound clip, report
   clipping saturation.
5. **filter-scale**: real flow direction; independent cells; no same-sample fallback.
6. **equifinality**: k–S objective surface / profile likelihood instead of a single
   XGBoost result.
7. **Regenerate** Figures 2–7, S1–S3, A1 and Tables 2–9, then paper.

---

## 4. Frozen-number policy after recalculation

Until all seven phases are rerun end-to-end, the prior frozen numbers
(0.0284, 0.0244, 3.35e-4, 3.24→0.031, 0.0573, 0.0745, 1.916→1.000) are **retired**.
They are arithmetic-consistent but structurally invalid. New numbers will be
reported only from the corrected pipeline.

---

## 5. Corrected results (stages 1–6 rerun, 2026-08-24)

Every number below comes from the corrected pipeline (real directed topology,
temperature-dependent Henry, Ulseth-2019 k600 primary, hydraulic-geometry width,
no C_obs leakage, dimensionally consistent signed S_sgs, no k-correction lower
clip, flow-directed cell-level filter-scale, model-free objective surface).

### 5.1 Evaluation (Stage 2)

| Metric | Prior (leaky) | Corrected |
|---|---|---|
| Baseline hold-out C RMSE (LOO-reach) | 0.0284 mol m⁻³ | **0.0485** mol m⁻³ |
| Baseline hold-out C RMSE (LOO-date) | 0.0284 | **0.0485** |

The corrected baseline is the honest difficulty of predicting observed
supersaturation from a no-source transport: with Ulseth-2019 k600 and the real
tree, the reach equilibrates toward C_eq, so C_obs (supersaturated) is underpredicted.

### 5.2 Closure target (Stage 3)

Diagnosed S_sgs (dimensionally consistent, signed):

| Statistic | Value |
|---|---|
| n | 120 |
| mean | 3.203 mol m⁻² d⁻¹ |
| median | 1.860 |
| min / max | 0.026 / 24.02 |
| variance | 17.18 |

S_sgs is positive for all 120 samples (a source), because the observed
supersaturation cannot be sustained without a subgrid source at the empirical k.

### 5.3 k-correction (Stage 4)

| Metric | Value |
|---|---|
| k_needed infeasible fraction (no positive k matches C_obs) | **61.7%** |
| k-correction saturation at g ≤ −12 floor | **18.8%** |
| k-correction C RMSE (LOO-reach) | 0.0486 (no improvement vs 0.0485) |
| Residual-AI MLP C RMSE | 0.0602 (worse than baseline) |
| Residual-AI RF C RMSE | 0.0750 |
| Baseline area-weighted flux | 4290.72 mol d⁻¹ |
| k-correction area-weighted flux | 598.81 mol d⁻¹ |
| k_eff median / min / max | 0.0066 / 0.000153 / 0.65 m d⁻¹ |

The prior k_eff/k_emp = 3.35e-4 = e⁻⁸ was the clipping lower bound; k_eff now has
a genuine distribution and is no longer pinned to a single value. The k-correction
no longer beats Baseline on C RMSE: its apparent superiority was boundary leakage
plus the clip floor.

### 5.4 Filter scale (Stage 5)

Cell-level, flow-directed, C_eq headwater (no sample fallback):

| Scale | Δx (m) | independent cells | cell-mean \|S_sgs\| | cell-Var(S_sgs) |
|---|---|---|---|---|
| Native NHDPlus HR | 591 | 39 | 3.720 | 17.47 |
| ~2× merge | 1100 | 30 | 3.667 | 15.06 |
| ~4× merge | 1924 | 24 | 3.864 | 16.60 |
| Study-reach | 73109 | 6 | 3.932 | 11.96 |

The prior monotone decrease (1.916 → 1.000) was an artifact of the Y→X sort and
own-C_obs fallback. The corrected magnitude is approximately scale-invariant
(3.7–3.9 mol m⁻² d⁻¹); only the variance declines modestly at the study-reach
scale. This indicates the residual is dominated by a genuine unresolved process
rather than a pure resolution truncation.

### 5.5 Equifinality (Stage 6)

Model-free k–S objective surface / profile likelihood (no ML model in the loop):

- Single sample: J(k,S) = (C_obs − C_model(k,S))² has an **exact zero valley**
  S = S_diag + (C_obs − C_eq)(k − k_emp); the per-sample profile likelihood is
  identically flat, so one concentration observation cannot identify (k, S) jointly.
- Pooled (uniform k-scale α, uniform source S): profile RMSE changes only
  0.0409 (α = 0.019) → 0.0465 (α = 1) across the k-scale interval [0.01, 1],
  i.e. concentration data alone weakly discriminate the two closures.

### 5.6 Consequence

The three central claims survive the recalc but with corrected magnitudes and
wording: (1) a no-source Baseline underpredicts supersaturation (RMSE 0.0485);
(2) the Residual-AI closure does not improve held-out C (0.0602 vs 0.0485) and,
unbounded, produces unphysical source extrapolation; (3) k-correction and
subgrid-source closures are practically equifinal — k-only cannot even match 61.7%
of samples, and the objective surface has a flat valley. The prior quantitative
anchors (0.0284, 0.0244, 3.35e-4, 1.916→1.000) are superseded by the values above.

### 5.7 Sparse dimensionless closure (Stage 7 prep, rerun 2026-08-24)

S* ≈ 1.02 − 0.320 Fr_z − 0.280 Slope_z (h/W, log10 Re, log10 Da shrink to zero).
LOO-reach R²(S*) = −1.55; coupled transport RMSE_C = 0.0588 (vs Baseline 0.0485).
The prior coefficient anchor (1.059 + 1.536 Fr − 1.669 Slope − 2.179 h/W) is
retired: the Fr sign flips to negative and h/W vanishes under the corrected
dimensionally-consistent target.

### 5.8 Residual-AI source extrapolation (honest negative result)

The signed MLP predicts S_sgs without a physical bound; on held-out reaches it
extrapolates to large sources, so the coupled area-weighted flux reaches
2.43e8 mol d⁻¹ (MLP) / 1.79e8 (RF) versus 4291 mol d⁻¹ for Baseline. The
Residual-AI closure is therefore not merely weak (C RMSE 0.0602 > 0.0485) but
unstable out-of-sample — a finding to state plainly rather than mask.

### 5.9 Identifiability diagnostics (rerun 2026-08-24)

With corrected data, k_eff median = 0.0066 m d⁻¹ (k_eff/k_emp ≈ 3.9e-5, no longer
pinned to e⁻⁸), S_implied mean 3.20 vs S_ai mean 3.40 mol m⁻² d⁻¹, Spearman
S_ai–S_implied = +0.24 (the prior −0.57 anti-correlation is gone). The
model-free objective surface (Section 5.5) is the primary equifinality evidence;
these per-model diagnostics are reported only as supporting values.


