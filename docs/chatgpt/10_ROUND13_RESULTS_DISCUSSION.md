# Round 13 brief — Results/Discussion prose and claims audit

**Repo:** https://github.com/Coucou2016/river-carbon-transport (branch `main`)
**Paper text below is extracted from `paper.md` (current `main` after Rounds 10–11).** Sections 3.1–3.6, 4.1–4.4 verbatim, plus Tables 2, 3, 5, 6, 7, 8, 9 for claims checking.

## What we ask of ChatGPT

You are reviewing ONLY Results and Discussion of an EMS-targeted manuscript. Do not change science, numbers, or conclusions. Answer Q13.1–Q13.5 in English. No em-dashes, no bold in proposed prose.

### Q13.1 Claims-vs-tables audit
For every quantitative claim in Sections 3 and 4, verify it against the tables below. Report each claim, the table cell that supports it (or the mismatch), and whether the claim is exactly supported, under-claimed, or over-claimed.

### Q13.2 Over/under-claiming
Flag any sentence that over-claims (asserts more than the evidence) or under-claims (weakens a result the evidence supports). Give the corrected sentence for each.

### Q13.3 Hedging calibration
Check hedging verbs (show/indicate/suggest/consistent with). Where a strong verb is used for weak evidence, or a weak verb for strong evidence, propose the calibration. Keep the paper's cautious stance: the main inference is practical equifinality of S_sgs and k under concentration-only East River observations, nothing stronger.

### Q13.4 Transitions
Identify abrupt jumps between subsections and between paragraphs. Where a Phrasebank-style transition sentence would help, give the exact sentence (e.g. "Having established ..., we next ...", "This result contrasts with ..."). Do not add filler.

### Q13.5 Integrity check
State whether anything in Sections 3–4 could look like data borrowed from the reference papers (Saccardi & Winnick 2021; Raymond et al. 2012). The expected answer is none: all metrics were self-computed from public East River observations; see docs/RESEARCH_INTEGRITY_AUDIT.md. If you see any sentence that could be misread as borrowed, propose a provenance clarification.

---

## Frozen facts (never alter)
n=120 samples, 2019-08-02 to 11; reaches R001=1, R002=3, R003=15, R004=24, R005=17, R006=1, R007=1, R008=58; LOO-reach transport-coupled C_aq RMSE Baseline 0.0284, MLP 0.0573, RF 0.0745, k-correction 0.0244, sparse Π 0.0506; k-correction median k_eff/k_emp ≈ 3.35e-4, ΣF_CO2 3.24 → 0.031; filter mean |S_sgs| 1.916 (Δx≈838 m) → 1.000 (study reach, 7 cells, 6 with samples); sparse law S*_z ≈ 1.059 + 1.536 Fr − 1.669 Slope − 2.179 h/W; in-sample R²≈0.997 appendix-only; F_CO2 is a model diagnostic, not a measured flux.

---

## Results section text

### 3.1 Residual closures do not improve held-out concentration prediction

The primary result is negative. Under leave-one-reach-out transport-coupled evaluation, neither residual closure improves on the Baseline (Tables 2 and 3; Figure 3). The held-out C_aq RMSE is 0.0284 mol m-3 for the Baseline, 0.0573 for the Residual-AI multilayer perceptron, and 0.0745 for the random forest. The corresponding MAE values are 0.0132, 0.0326, and 0.0301, and the residual closures show positive concentration bias (0.0177 and 0.0180) where the Baseline bias is -0.0132. The date-grouped sensitivity gives the same ordering (0.0284, 0.0591, and 0.0747).

The subgroup decomposition locates the error (Table 5; Figures 4 and S1). On the mainstem reach R008, both residual closures are slightly better than the Baseline: RMSE is 0.0121 for the MLP and 0.0087 for the random forest against 0.0136 for the Baseline. On the multi-sample tributaries the pattern reverses: RMSE is 0.0381 for the Baseline, 0.0808 for the MLP, and 0.1058 for the random forest. The pooled degradation is concentrated in reaches with moderate sample support, where training data for the residual are sparse and heterogeneous. The holdout scatter (Figure 4) shows the same structure: mainstem predictions cluster near the observations while tributary predictions spread widely.

### 3.2 A corrected gas-transfer velocity lowers concentration error

The k-correction is the only configuration that reduces held-out concentration error below the Baseline. Its C_aq RMSE is 0.0244 mol m-3 against 0.0284 for the Baseline, and MAE falls from 0.0132 to 0.0046 (Tables 2 and 3). The improvement is achieved entirely through the transfer velocity. The median effective velocity is 0.0329 m d-1, compared with a median empirical value of 98.1 m d-1; the median ratio k_eff/k_emp is 3.35×10^-4 (Table 7; Figure 5). Under this correction, gas exchange is reduced to nearly zero rather than fine-tuned.

### 3.3 The concentration gain coincides with collapse of the flux diagnostic

The flux diagnostic separates the closures. The sample-summed model flux ΣF_CO2 is 3.24 mol m-2 d-1 for the Baseline and 0.031 for the k-correction (Table 7; Figure S2). The concentration improvement of the k-correction coincides with a collapse of the modeled CO2 release by roughly two orders of magnitude. The Residual-AI configuration moves in the opposite direction, with ΣF_CO2 of 69.5, because its predicted sources add to the balance while k remains at k_emp.

No independent evasion observations are available for this campaign, so these values do not show that the Baseline flux is correct or that the corrected flux is wrong. They show that concentration performance alone can favor a markedly different allocation of the model balance. The implied-source diagnostic makes the compensation explicit. At fixed concentrations, the mean implied adjustment S_implied is 1.00 mol m-2 d-1, the mean Residual-AI prediction is 0.56, and the two are anti-correlated across samples (Spearman -0.57; Table 7; Figure S3). A positive source term and a reduced transfer velocity act on the concentration balance in compensating directions, and the held-out concentration metric provides limited discrimination between them.

### 3.4 The diagnosed residual depends on filter scale

The magnitude of the diagnosed residual varies systematically with the filter width (Table 6; Figure 6). Mean |S_sgs| is 1.916 mol m-2 d-1 at the native NHD resolution (Deltax ≈ 838 m), decreases to 1.120 and 1.050 at successive merging levels, and reaches 1.000 at the study-reach scale (Deltax ≈ 26,086 m; 7 cells, of which 6 contain samples). The variance of S_sgs falls from 22.4 to 2.20 over the same range (Figure S4). The result indicates that the diagnosed closure residual depends on the spatial representation used to separate resolved from unresolved contributions. It is an empirical scale dependence for the implemented reach-local operator, not a universal scaling law.

### 3.5 A sparse dimensionless closure is compact but not predictive

The standardized LASSO retains three of the five candidate Pi terms (Table 8; Figure 7). In standardized space the closure is

S*_z ~= 1.059 + 1.536*Fr - 1.669*Slope - 2.179*h/W

with Froude number the positive contributor and slope and relative depth the negative contributors. Under the same leave-one-reach-out transport-coupled protocol, the sparse closure gives a held-out C_aq RMSE of 0.0506 mol m-3, above the Baseline value of 0.0284 (Table 9). The leave-one-reach R2 for S* itself is -2.74. The sparse form is therefore useful as a compact diagnostic description of the residual but does not recover predictive skill on held-out reaches.

### 3.6 In-sample fit (appendix)

The in-sample fit of the residual model is reported in the appendix (Table 4; Figure A1), with R2 ≈ 0.997 and RMSE 0.00127 mol m-3 computed on the same 120 rows used for training. The value describes the capacity of the learner to memorize the sample rather than its generalization, and it is not used as a paper metric.

## Discussion section text

### 4.1 Failed generalization of residual closures is a modelling diagnosis

The residual closures reproduce the observations well in-sample but degrade held-out concentration prediction relative to a zero-residual Baseline. This pattern suggests that the residual diagnosed from the present resolved model, predictors, spatial representation, and sampling design does not carry enough transferable structure to improve predictions after transport coupling. In the evaluation logic of Bennett et al. (2013) and Vilas et al. (2023), the discrepancy is itself diagnostic: it separates apparent learnability from held-out usefulness. The subgroup evidence points to where the transfer fails. Tributary reaches with moderate sample counts carry heterogeneous residual behaviour, and learners trained across reaches do not extrapolate there; the mainstem reach, with 58 samples, is the only subgroup where the residual closures are competitive. For model evaluation, this implies that learned residual closures for river networks need reach-level diagnostics and balanced sampling before pooled metrics can be interpreted.

### 4.2 Process allocation and practical equifinality

The k-correction achieves the lowest concentration error of any configuration, and it does so by reducing the effective transfer velocity by roughly three orders of magnitude. Because both source terms and gas exchange act on the same balance, a near-zero k can be offset by the existing gradient (C - C_eq) and still reproduce concentrations. The collapse of ΣF_CO2 from 3.24 to 0.031 shows what this fit implies for the process budget. Without independent evasion measurements, the data cannot adjudicate between the Baseline and corrected allocations; the lower RMSE is evidence of improved concentration fit, not independent evidence of improved process fidelity.

Here, practical equifinality refers to the compensation between S_sgs and k represented by Eq. (6). The Baseline/k-correction contrast shows that this compensation direction is consequential in the present experiment: similar concentration errors coexist with markedly different transfer velocities and flux diagnostics. The argument is restricted in scope: it is not a formal structural-identifiability analysis, and it does not establish statistical equivalence between the competing predictions. The degraded RMSE of the MLP, random forest, and sparse closures is likewise not equifinality evidence; it shows that closure choice matters and that flexible residual learning did not generalize here. Within those boundaries, concentration-dominated evaluation does not uniquely constrain how discrepancy is allocated between S_sgs and k in this configuration.

### 4.3 What filtering and sparse representation reveal about the residual

The filter-scale results show that the diagnosed residual is not a fixed property of the watershed. Its magnitude changes as the filter width changes, because the split between resolved and unresolved contributions is defined by the filter. This interpretation is bounded by the implemented operator, which uses reach-local merging and a coordinate-ordering fallback rather than a fully directed network filter. Within those boundaries, the result is consistent with the coarse-graining logic used elsewhere for learned subgrid terms (Yuval & O'Gorman, 2020): the statistics of the unresolved term depend on resolution.

The sparse dimensionless closure provides a counterpoint to the flexible learners. It identifies a limited set of candidate dependencies, with Froude number, slope, and relative depth surviving selection, yet its compactness does not transfer into held-out skill: RMSE remains above the Baseline and the S* reconstruction fails under reach holdout. Compact forms are therefore not automatically validated or predictive. In this experiment the Pi-group formulation is most useful as a diagnostic simplification, and under the present protocol the residual does not admit a compact representation with cross-reach predictive utility.

### 4.4 Implications for environmental-model evaluation

These findings suggest that concentration RMSE should be interpreted together with diagnostics of gas exchange and unresolved source allocation. A closure that lowers concentration error deserves scrutiny of the process allocation that produces the lowering, particularly when the observations constrain only concentrations.

The present conclusions are bounded by partially observed upstream conditioning, strongly unequal reach support, the coordinate-based ordering fallback, idealized hydraulic geometry, incomplete covariates (alkalinity, nitrogen, phosphorus, photosynthetically active radiation), and the absence of independent evasion measurements. The Water Quality Portal merge and the StreamPULSE search returned no usable additional constraints for this campaign. These limitations restrict inference to the East River experiment, and they also identify the observations that would most help to discriminate closures: improved upstream boundary information, better-resolved channel geometry, more balanced reach sampling, and independent constraints on gas exchange. The central implication is that lower concentration error alone is insufficient to determine which allocation of unresolved processes is better supported.

---

## Tables for claims checking

### Table 2. Main results under leave-one-reach-out grouped cross-validation with transport coupling (flux totals are model diagnostics).

| Scheme / model | C RMSE | F total | k_eff/k_emp | Beats Baseline (C)? |
|---|---|---|---|---|
| baseline / none | 0.0284 | 3.244 | 1.00000 | — |
| k_correction / xgboost | 0.0244 | 0.031 | 0.00034 | Yes |
| residual_ai / mlp | 0.0573 | 69.507 | 1.00000 | No |
| residual_ai / random_forest | 0.0745 | 143.331 | 1.00000 | No |
| sparse_pi / lasso_pi | 0.0506 | 244.183 | — | No |

### Table 3. Leave-one-reach-out grouped cross-validation: held-out C_aq and F_CO2 (primary metrics; F values are model flux diagnostics).

| Scheme / model | C RMSE | C MAE | C Bias | C R2 | F RMSE | F Bias | F total | n |
|---|---|---|---|---|---|---|---|---|
| baseline / none | 0.0284 | 0.0132 | -0.0132 | -0.264 | 1.733 | -0.973 | 3.24 | 120 |
| k_correction / xgboost | 0.0244 | 0.0046 | -0.0046 | 0.061 | 1.783 | -1.000 | 0.03 | 120 |
| residual_ai / mlp | 0.0573 | 0.0326 | 0.0177 | -4.163 | 1.562 | -0.421 | 69.51 | 120 |
| residual_ai / random_forest | 0.0745 | 0.0301 | 0.0180 | -7.723 | 2.103 | 0.194 | 143.33 | 120 |

### Table 5. Subgroup metrics under leave-one-reach-out cross-validation.

| Scheme | Subgroup | Evidence weight | C RMSE | C R2 | n |
|---|---|---|---|---|---|
| baseline | All 120 samples | all | 0.0284 | -0.264 | 120 |
| baseline | R008 East River mainstem | mainstem | 0.0136 | -0.788 | 58 |
| baseline | R004+R006 (Copper + Quigley) | requested | 0.0069 | -2.984 | 25 |
| baseline | Multi-sample tribs R002–R005 | tributary | 0.0381 | -0.247 | 59 |
| baseline | One-sample reaches (schematic) R001/R006/R007 | schematic | 0.0041 | -37.475 | 3 |
| k_correction | All 120 samples | all | 0.0244 | 0.061 | 120 |
| k_correction | R008 East River mainstem | mainstem | 0.0006 | 0.996 | 58 |
| k_correction | R004+R006 (Copper + Quigley) | requested | 0.0010 | 0.912 | 25 |
| k_correction | Multi-sample tribs R002–R005 | tributary | 0.0348 | -0.041 | 59 |
| k_correction | One-sample reaches (schematic) R001/R006/R007 | schematic | 0.0006 | 0.118 | 3 |
| residual_ai | All 120 samples | all | 0.0573 | -4.163 | 120 |
| residual_ai | R008 East River mainstem | mainstem | 0.0121 | -0.408 | 58 |
| residual_ai | R004+R006 (Copper + Quigley) | requested | 0.0049 | -0.985 | 25 |
| residual_ai | Multi-sample tribs R002–R005 | tributary | 0.0808 | -4.603 | 59 |
| residual_ai | One-sample reaches (schematic) R001/R006/R007 | schematic | 0.0112 | -287.551 | 3 |

### Table 6. Filter-scale experiment: S_sgs after snapping the 120 samples onto coarsened NHDPlus HR networks.

| Scale | dx (m) | Cells | Sampled cells | Samples | Mean |S| | Var(S) |
|---|---|---|---|---|---|---|
| Native NHD | 838 | 536 | 39 | 120 | 1.916 | 22.405 |
| ~2× merge | 1183 | 270 | 30 | 120 | 1.120 | 3.467 |
| ~4× merge | 1949 | 137 | 24 | 120 | 1.050 | 2.894 |
| Study reaches (8) | 26086 | 7 | 6 | 120 | 1.000 | 2.197 |

### Table 7. Identifiability: k versus S_sgs under the same grouped protocol.

| Scheme | C RMSE | F total | Median k | k_eff/k_emp |
|---|---|---|---|---|
| baseline | 0.0284 | 3.24 | 98.096 | 1.00000 |
| residual_ai | 0.0573 | 69.51 | 98.096 | 1.00000 |
| k_correction | 0.0244 | 0.03 | 0.033 | 0.00034 |

### Table 8. Sparse dimensionless closure (Pi-group LASSO).

| Item | Result |
|---|---|
| Standardized form | S_sgs*_z ≈ + 1.059 + 1.536*Fr − 1.669*Slope − 2.179*h_over_W |
| Original-variable form | S_sgs* ≈ + 8.368 + 1.327*Fr − 38.8*Slope − 349*h_over_W |
| Dominant terms | -2.18*h_over_W + -1.67*Slope + +1.54*Fr |
| Leave-one-reach R2 on S* | -2.743 (negative = does not generalize) |

### Table 9. Sparse dimensionless closure inserted into transport under grouped cross-validation (compare Baseline 0.0284 in Table 3).

| Scheme | C RMSE | C R2 | F RMSE | n |
|---|---|---|---|---|
| sparse_pi / lasso_pi (leave-one-reach) | 0.0506 | -3.024 | 2.508 | 120 |
