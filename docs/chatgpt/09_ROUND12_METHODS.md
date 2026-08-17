# Round 12 brief — Methods clarity and notation/units check

**Repo:** https://github.com/Coucou2016/river-carbon-transport (branch `main`)
**Paper text below is extracted from `paper.md` (current `main`).** Sections 2.1–2.8 verbatim. Equations are rendered in plain-text form (subscripts with `_`).

## What we ask of ChatGPT

You are reviewing ONLY the Methods section of an EMS-targeted manuscript. Do not change science, numbers, or conclusions. Answer Q12.1–Q12.4 in English.

Constraints:
- Frozen facts: n=120 samples, 2019-08-02 to 11; reaches R001=1, R002=3, R003=15, R004=24, R005=17, R006=1, R007=1, R008=58; LOO-reach transport-coupled C_aq RMSE Baseline 0.0284, MLP 0.0573, RF 0.0745, k-correction 0.0244, sparse Π 0.0506; k-correction median k_eff/k_emp ≈ 3.35e-4, ΣF_CO2 3.24 → 0.031; filter mean |S_sgs| 1.916 (Δx≈838 m) → 1.000 (study reach, 7 cells, 6 with samples); sparse law S*_z ≈ 1.059 + 1.536 Fr − 1.669 Slope − 2.179 h/W; in-sample R²≈0.997 is appendix-only; F_CO2 is a model diagnostic, not a measured flux; cross-sections are idealized display products.
- Known honest gaps (待补充, do not invent): authors, Gao DOI, alkalinity/N/P/PAR covariates, width-sensitivity table, fold-level RMSE, C_eq appendix.
- No em-dashes, no bold in proposed replacement prose.

### Q12.1 Under-explanation audit
Identify every place where OUR method is under-explained for a reader who has not seen our code. For each: location (subsection), what is missing, and a concrete sentence or two to add or replace. Priorities: (a) how the filter cells are actually built and how Δx≈838 m and the study-reach scale are obtained; (b) what the learners receive as inputs and how reinsertion works mechanically; (c) how the k-correction factor is trained and applied per fold; (d) how the sparse Π coefficients were obtained (standardized space, per-fold selection, median law).

### Q12.2 Notation and unit consistency
Check Eq. (1), Eq. (4), Eq. (2), Eq. (5), Eq. (6), and the k600 relation for symbol/unit consistency: Q (m3 s-1), tau_d (s d-1), A_s (m2), q_A (m d-1), k and k600 and k_emp (m d-1), S_sgs and F_CO2 (mol m-2 d-1), C, C_in, C_eq (mol m-3). Flag any symbol that appears with two meanings or any term whose units do not close. Give minimal fixes.

### Q12.3 Clarity rewrites
For each Methods subsection, propose at most one paragraph-level clarity rewrite (not a full rewrite of the section) if you judge it would materially improve reproducibility. Mark each proposal KEEP/REPLACE/ADD and give the exact text.

### Q12.4 Reviewer friction points
List up to five places where a WRR/EMS reviewer would likely ask "how exactly was this done?" and give the one-sentence answer we should insert.

---

## Methods section text (verbatim from paper.md)

### 2.1 Study data and river-network representation

The study uses public observations from the upper East River watershed near Almont, Colorado (HUC 14020001). The water-chemistry data come from the field campaign of Saccardi and Winnick (2021), which comprises 120 samples collected between 2 and 11 August 2019. Samples are assigned to eight logical reaches, R001 through R008, with counts of 1, 3, 15, 24, 17, 1, 1, and 58, respectively (Table 1). Three reaches (R001, R006, R007) contain a single sample and are treated as schematic: they enter the network bookkeeping but do not carry the same evidence weight as the mainstem reach R008. The logical reaches form a fixed upstream-to-downstream chain that provides reproducible control volumes for the closure experiment. They are not intended to replace the full directed NHDPlus topology.

The river-network representation combines three public sources. The HydroShare supplement of Saccardi and Winnick (2021) provides 393 NHD centerline segments for the study corridor. An extract of the NHDPlus HR product for HUC 14020001 contributes 8212 flowlines used for corridor-level filtering. Reach-to-line matching identified 85 segments through GNIS name matching and assigned the remainder by proximity to campaign coordinates; the median sample-to-centerline snap distance is 8.5 m. Discharge for the mainstem reach comes from USGS gage 09112500 (East River at Almont) on the sample dates. Tributary discharges are the published synoptic values from the campaign supplement, with no gage-ratio scaling applied.

Channel width is not measured along the corridor. Computed widths come from a coordinate-based widening proxy, with clipping, for multi-sample reaches, and from a fallback width for single-sample reaches; the width enters water depth, flow velocity, k_600, and the water-surface area A_s = L·W. Sensitivity of the results to this width proxy remains to be tabulated. Biogeochemical covariates are likewise incomplete: DIC and DOC are available for 41 of the 120 samples, and alkalinity, nitrogen, phosphorus, and photosynthetically active radiation were not available for this campaign. A same-day merge against the Water Quality Portal returned no matching samples (0 of 120), and the StreamPULSE database contains no East River sites. These gaps constrain the covariate set available to the closures.

### 2.2 Quasi-steady CO₂ mass balance and gas exchange

Each sample is associated with a control volume defined by its reach length L and computed width W. Carbon mass in the control volume is closed under a quasi-steady assumption at a daily time step: advective exchange with the upstream reach, source-sink inputs, and atmospheric gas exchange balance one another,

Eq. (1): Q(C_in - C) + (A_s/tau_d)[S_sgs - k(C - C_eq)] = 0

where Q is discharge (m3 s-1), C_in and C are the upstream and reach concentrations (mol m-3), k is the gas-transfer velocity (m d-1), S_sgs is the areal source-sink term (mol m-2 d-1), C_eq is the equilibrium concentration with the atmosphere, A_s = L·W is the water-surface planform area (m2), and tau_d = 86400 s d-1 converts the daily areal flux into mol s-1. The planform area A_s is not the hydraulic cross-section area; if a bulk velocity is required, U = Q/A_c with A_c the cross-section area. Writing the balance explicitly on a daily areal basis avoids mixing time bases. Dividing Eq. (1) by A_s/tau_d gives the equivalent form

Eq. (4): q_A(C_in - C) + S_sgs - k(C - C_eq) = 0

in which q_A = tau_d·Q/A_s (m d-1) is a daily area-normalized discharge and every term has units mol m-2 d-1.

All closures are inserted into this same balance: a closure configuration is defined entirely by how it supplies S_sgs and k, and every configuration is scored after the identical transport calculation is re-solved. Differences between configurations therefore reflect the allocation of model discrepancy rather than differences in transport numerics.

Gas exchange is summarized by the model flux density

Eq. (2): F_CO2 = k(C - C_eq)

The reported flux totals are sample sums of F_CO2. They compare how each closure allocates the model balance; they are neither independently observed evasion fluxes nor spatially integrated watershed fluxes.

The empirical transfer velocity follows Raymond et al. (2012). The velocity normalized to a Schmidt number of 600 is estimated from velocity u (m s-1) and slope (m m-1), and the CO2-specific velocity is obtained by Schmidt-number scaling:

ln k600 = 5.139 + 0.594 ln u + 0.403 ln slope; k_emp = k600 (Sc/600)^-0.5

Symbolically, k_600 and k_emp are distinct quantities. The equilibrium concentration C_eq is taken from the preprocessed campaign table, following Henry's law with atmospheric pCO2 and water temperature; the full derivation will be given in a supporting appendix.

Cross-section visualizations used elsewhere in this work are idealized trapezoids, and the vertical velocity profile is a schematic parabola rather than an ADCP measurement. These representations are display products and are not used as measurements in the metrics below.

### 2.3 Spatial filtering and diagnosis of the subgrid residual

Reach-scale transport formulations average over heterogeneity within each reach, and the unresolved contributions appear formally as a residual source-sink term. Studying that term requires an operable definition of the filter width Δx rather than a qualitative notion of subgrid structure.

We perform reach-local spatial coarse-graining within each logical reach. Native NHDPlus segments are merged along the network chainage into filter cells, and Δx is defined as the mean length of the filter cells, with sampled cells reported separately. Where a fully directed network ordering is not available, the implementation falls back to a midpoint Y-then-X coordinate ordering. This fallback is disclosed as an operator boundary; it does not change the definition of the diagnosed residual.

At the operator level the construction parallels the coarse-graining used in large-eddy simulation and in learned subgrid parameterization studies (Yuval & O'Gorman, 2020); the analogy is limited to spatial filtering, and S_sgs denotes the residual of the filtered river CO2 balance at the chosen scale. Once resolved transport and gas exchange are recomputed on the filtered balance, the residual implied by the observations is

Eq. (5): S_sgs = k(C - C_eq) - q_A(C_in - C)

S_sgs is a filter-induced closure residual. It can absorb measurement error, errors from the simplified transport representation, and genuinely unresolved processes. It is not a direct measurement of a single unresolved biogeochemical flux. Its magnitude, structure, and learnability are evaluated below as the aggregation scale changes.

### 2.4 Alternative unresolved-process closures

Three closure configurations are compared. They differ only in how S_sgs and k are supplied to Eq. (1).

The Baseline retains the transport and hydraulic formulation of the other configurations while setting S_sgs = 0 and using the Raymond-type empirical velocity k_emp. It therefore serves as the zero-residual reference against which closure form and evaluation protocol are compared.

The Residual-AI configuration learns S_sgs from hydraulic and water-quality covariates. Two learners are trained with a fixed seed (42): a multilayer perceptron and a random forest. The inputs include discharge, velocity, depth, width, slope, temperature, and the available carbon chemistry, as implemented in the open-source pipeline.

The k-correction configuration leaves S_sgs at zero and multiplies the empirical velocity by a learned factor, k_eff = k_emp·exp(g_θ(X)), where g_θ is a dimensionless correction predicted by a gradient-boosting model (XGBoost). The median ratio k_eff/k_emp under grouped evaluation is reported as a diagnostic of how the correction achieves its fit.

### 2.5 Leave-one-reach-out transport-coupled evaluation

Closure generalization is evaluated with leave-one-reach-out grouped cross-validation across the eight logical reaches. Each reach is held out once. Missing-value imputation and feature scaling are fitted on the training reaches only and then applied to the held-out reach. The closure is predicted for the held-out samples, reinserted into the quasi-steady balance, and only then scored against observed C_aq. No inner hyperparameter-selection loop is used, so we refer to the procedure as grouped cross-validation rather than nested cross-validation.

When an upstream concentration state is unavailable, the solver uses the observed C_aq at the current sample as the fallback boundary value c_in; the experiment therefore evaluates closure generalization under partially observed boundary conditioning rather than fully target-blind forecasting. Sampling is also strongly imbalanced among reaches: R008 contributes 58 of the 120 samples, while three reaches contribute one each, so pooled errors are read together with reach-level evidence weights (Table 5). A date-grouped variant is reported as a time-sensitivity analysis and is not nested inside the reach split.

### 2.6 Metrics and flux diagnostic

The primary metric is the held-out C_aq RMSE in mol m-3. The secondary diagnostic is the sample-summed model flux ΣF_CO2 in mol m-2 d-1, computed from Eq. (2) with the transport-predicted concentration and the transfer velocity of each configuration: k_emp for the Baseline and Residual-AI, and k_eff for the k-correction. An observation-based proxy flux uses k_emp with observed concentrations. Differences in ΣF_CO2 across closures indicate how each configuration allocates the balance between sources and gas exchange.

### 2.7 Practical equifinality diagnostic

To characterize compensation between source terms and gas exchange, we define the implied source adjustment

Eq. (6): S_implied = (k_emp - k_eff)(C - C_eq)

At fixed concentration and resolved transport state, S_implied is the source-sink adjustment that makes a model retaining k_emp locally equivalent to a model that uses k_eff and no additional source term. A large S_implied together with a small change in concentration error indicates that the observations provide limited discrimination between the two allocations; we refer to this compensating closure behaviour as practical equifinality. The diagnostic is algebraic and empirical rather than a formal structural-identifiability analysis.

### 2.8 Sparse dimensionless closure

A final experiment asks whether the residual admits a compact dimensionless representation. Candidate Π-group features are assembled from the hydraulic state: Froude number Fr, slope, relative depth h/W, and the logarithms of the Reynolds and Damköhler numbers. A standardized LASSO selects terms within each cross-validation fold, following the spirit of sparse discovery methods (Xie et al., 2022), implemented with a scikit-learn LASSO. The resulting form is reported in standardized (z-score) space and reinserted into the transport calculation under the same leave-one-reach-out protocol as the other closures. Compactness is tested against predictive utility; the two are not assumed to coincide.
