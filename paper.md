# Transport-coupled evaluation of river-network CO₂ closures: Evidence for practical equifinality under concentration-only observations

**Chinese title (metadata only):** 河网 CO₂ 闭合的输运耦合评价：浓度单变量观测下的 practical equifinality 证据

**Authors:** To be completed (待补充)  
**Affiliations:** To be completed (待补充)  
**Date:** 2026-08-17  
**Figures:** 13 embedded in paper.html

## Key Points

- A spatial filter turns the reach-scale CO₂ balance into a diagnosable subgrid residual term.
- Learned residual closures do not beat a zero-residual baseline on held-out reaches.
- Lower concentration error coincides with collapse of the model-derived CO₂ flux diagnostic.

## Plain Language Summary

Rivers take up, transform, and release carbon, and models of river carbon must represent processes that cannot be observed directly, such as groundwater CO₂ inputs and the exchange of gas with the atmosphere. When only concentration measurements are available, different model structures can reproduce the same observed concentrations by adjusting different process terms. Using 120 public water samples from the East River in Colorado, we compared a baseline transport model with variants that add a machine-learned source term or a corrected gas-exchange rate. The machine-learned term did not improve predictions for river reaches that were held out of training. The corrected gas-exchange rate fitted the concentrations slightly better, while the modeled CO₂ release was reduced to nearly zero. Concentration data alone therefore cannot determine where model error should be assigned. Evaluations of river-carbon models should combine concentration skill with process-level diagnostics.

## Abstract

River-network carbon models combine downstream transport, unresolved source and sink processes, and air-water gas exchange, but concentration-based evaluation may not distinguish errors assigned to different terms in the same mass balance. Existing process-based models provide a basis for predicting stream CO2, yet the consequences of alternative unresolved-process closures under held-out evaluation remain unclear. We developed a transport-coupled diagnostic framework for 120 public East River observations organized into eight logical reaches. Spatial coarse-graining defines a residual source-sink term, S_sgs, which was represented by a zero-residual Baseline, machine-learned residual closures, or a multiplicative correction to empirical gas-transfer velocity. Each closure was evaluated by leaving one reach out and reinserting the predicted closure into the quasi-steady transport balance before scoring concentration. Residual-AI performed worse than the Baseline: C_aq RMSE was 0.0573 mol/m^3 for the multilayer perceptron and 0.0745 for the random forest, compared with 0.0284 for the Baseline. The k-correction reduced RMSE to 0.0244, but median k_eff/k_emp was 3.35e-4 and the sample-summed model flux diagnostic decreased from 3.24 to 0.031 mol/m^2/day. A sparse closure gave RMSE 0.0506. Mean |S_sgs| decreased from 1.92 to 1.00 as filter width increased from about 838 m to the study-reach scale. These results indicate practical equifinality between S_sgs and k under concentration-only East River observations, so lower concentration error alone is insufficient to identify how model discrepancy is allocated between unresolved sources and gas exchange.

**Keywords:** river carbon cycling; environmental model evaluation; subgrid closure; gas-transfer velocity; grouped cross-validation; practical equifinality


## 1. Introduction

Rivers link terrestrial, aquatic, and atmospheric carbon cycling by transporting dissolved carbon, transforming it through biological and biogeochemical processes, and exchanging CO2 with the atmosphere. Riverine CO2 evasion is a substantial component of inland-water carbon budgets, but both the magnitude and dominant controls of that flux vary across river networks and over time (Hotchkiss et al., 2015; Gómez-Gener et al., 2021; Battin et al., 2023). Predictive models must therefore represent several processes that operate simultaneously: downstream advection, lateral and internal carbon inputs, in-stream transformation, and air-water gas exchange. At the reach scale, however, observations and model states average over spatial heterogeneity that may occur over much shorter distances. A reach-scale model can consequently reproduce concentration while compensating for unresolved source or sink processes through another term in the mass balance. This possibility matters whenever model performance is judged mainly from concentration observations.

The East River watershed provides a useful setting in which to examine this problem because a process-based stream-network CO2 model has already been developed for the system. Saccardi and Winnick (2021) represented downstream transport together with CO2 sources and atmospheric exchange to predict spatial variation in stream CO2 concentrations and fluxes. Their work illustrates how several process terms jointly determine the same downstream concentration state. Gas exchange is commonly represented through an empirical transfer velocity, and Raymond et al. (2012) related gas-transfer velocity to hydraulic properties of streams and small rivers. Such parameterizations make gas exchange operational at network scale, but they do not remove uncertainty in the other terms of the carbon balance. Groundwater inputs, lateral inflows, metabolic heterogeneity, and other sub-reach processes may remain incompletely observed or resolved. Errors in these processes and errors in gas exchange can therefore enter the same concentration equation and potentially offset one another.

This compensation creates an evaluation problem rather than simply a parameter-estimation problem. Bennett et al. (2013) argued that environmental-model performance should be characterized using evidence appropriate to model purpose rather than a single goodness-of-fit statistic. Vilas et al. (2023) likewise treated model-data discrepancy as information that may arise from the model, the observations, or their interaction, while Markovich et al. (2022) evaluated alternative methods explicitly in the presence of model error. For river-carbon transport, these considerations imply that a lower concentration error is not necessarily sufficient to identify which process representation is better supported. If an unresolved source-sink correction and the gas-transfer velocity can both alter the same predicted concentration, optimizing either term may reduce residual error. The relevant test is whether their effects remain distinguishable when each candidate closure is coupled back to the transport model and evaluated on observations that were not used to fit that closure.

Machine learning provides one possible representation of unresolved process terms. In climate modeling, for example, spatial coarse-graining has been used to define unresolved tendencies and to train data-driven subgrid parameterizations, including models tested across resolutions (Yuval & O’Gorman, 2020). Related work on data-driven closure of river-carbon transport is also in preparation (Gao et al., manuscript in preparation). The central difficulty is not whether a flexible model can fit a diagnosed residual in the data used for training, but whether that residual representation remains useful after transfer to a new spatial group and reinsertion into the governing balance. A residual may encode repeatable unresolved dynamics, but it may also absorb errors in hydraulic representation, boundary conditions, observations, or other model components. Strong in-sample fit therefore provides limited evidence for a closure unless its effect is evaluated through the coupled model under held-out conditions.

Here we examine that question using 120 public East River campaign observations organized into eight logical reaches and mapped to an NHDPlus HR representation. We spatially coarse-grain the reach-scale mass balance to diagnose a residual source-sink term, S_sgs, and compare three closure strategies: a zero-residual Baseline, machine-learned residual closures, and a multiplicative correction to the empirical gas-transfer velocity. Evaluation is grouped by reach and transport-coupled, so the closure predicted for a held-out reach is reinserted into the quasi-steady mass balance before C_aq is scored. We also examine how the diagnosed residual changes with filter scale and whether a sparse dimensionless representation retains held-out predictive value. The experiment has deliberate boundaries. Upstream concentration is partially observed because the solver uses observed C_aq as a fallback when an upstream state is unavailable, reach support is strongly unequal, channel geometry is idealized, and the spatial ordering includes a coordinate-based fallback rather than a complete directed network topology. Within these constraints, the test is whether concentration-only observations can distinguish discrepancy assigned to S_sgs from discrepancy assigned to k when both closures are evaluated through the same transport calculation.


## 2. Methods


### 2.1 Study data and river-network representation

The study uses public observations from the upper East River watershed near Almont, Colorado (HUC 14020001). The water-chemistry data come from the field campaign of Saccardi and Winnick (2021), which comprises 120 samples collected between 2 and 11 August 2019. Samples are assigned to eight logical reaches, R001 through R008, with counts of 1, 3, 15, 24, 17, 1, 1, and 58, respectively (Table 1). Three reaches (R001, R006, R007) contain a single sample and are treated as schematic: they enter the network bookkeeping but do not carry the same evidence weight as the mainstem reach R008. The logical reaches form a fixed upstream-to-downstream chain that provides reproducible control volumes for the closure experiment. They are not intended to replace the full directed NHDPlus topology.

The river-network representation combines three public sources. The HydroShare supplement of Saccardi and Winnick (2021) provides 393 NHD centerline segments for the study corridor. An extract of the NHDPlus HR product for HUC 14020001 contributes 8212 flowlines used for corridor-level filtering. Reach-to-line matching identified 85 segments through GNIS name matching and assigned the remainder by proximity to campaign coordinates; the median sample-to-centerline snap distance is 8.5 m. Discharge for the mainstem reach comes from USGS gage 09112500 (East River at Almont) on the sample dates. Tributary discharges are the published synoptic values from the campaign supplement, with no gage-ratio scaling applied.

Channel width is not measured along the corridor. Computed widths come from a coordinate-based widening proxy, with clipping, for multi-sample reaches, and from a fallback width for single-sample reaches; the width enters water depth, flow velocity, k_600, and the water-surface area A_s = L·W. Sensitivity of the results to this width proxy remains to be tabulated. Biogeochemical covariates are likewise incomplete: DIC and DOC are available for 41 of the 120 samples, and alkalinity, nitrogen, phosphorus, and photosynthetically active radiation were not available for this campaign. A same-day merge against the Water Quality Portal returned no matching samples (0 of 120), and the StreamPULSE database contains no East River sites. These gaps constrain the covariate set available to the closures.

*(Tables 1–9 are rendered below.)*

![Figure 2a. Study river network: correspondence between the eight logical reaches (R001–R008) and the NHD vector centerlines.](results/figures/gis_reach_assignment_map.png)

![Figure 2b. The 120 campaign samples overlaid on the NHD river network. The mainstem reach R008 contributes 58 samples.](results/figures/gis_samples_on_network.png)


### 2.2 Quasi-steady CO₂ mass balance and gas exchange

Each sample is associated with a control volume defined by its reach length L and computed width W. Carbon mass in the control volume is closed under a quasi-steady assumption at a daily time step: advective exchange with the upstream reach, source-sink inputs, and atmospheric gas exchange balance one another,

> Eq. (1):  Q(C_in - C) + (A_s/tau_d)[S_sgs - k(C - C_eq)] = 0

where Q is discharge (m3 s-¹), C_in and C are the upstream and reach concentrations (mol m-3), k is the gas-transfer velocity (m d-¹), S_sgs is the areal source-sink term (mol m-2 d-¹), C_eq is the equilibrium concentration with the atmosphere, A_s = L·W is the water-surface planform area (m2), and tau_d = 86400 s d-¹ converts the daily areal flux into mol s-¹. The planform area A_s is not the hydraulic cross-section area; if a bulk velocity is required, U = Q/A_c with A_c the cross-section area. Writing the balance explicitly on a daily areal basis avoids mixing time bases. Dividing Eq. (1) by A_s/tau_d gives the equivalent form

> Eq. (4):  q_A(C_in - C) + S_sgs - k(C - C_eq) = 0

in which q_A = tau_d·Q/A_s (m d-¹) is a daily area-normalized discharge and every term has units mol m-2 d-¹.

All closures are inserted into this same balance: a closure configuration is defined entirely by how it supplies S_sgs and k, and every configuration is scored after the identical transport calculation is re-solved. Differences between configurations therefore reflect the allocation of model discrepancy rather than differences in transport numerics.

Gas exchange is summarized by the model flux density

> Eq. (2):  F_CO2 = k(C - C_eq)

The reported flux totals are sample sums of F_CO2. They compare how each closure allocates the model balance; they are neither independently observed evasion fluxes nor spatially integrated watershed fluxes.

The empirical transfer velocity follows Raymond et al. (2012). The velocity normalized to a Schmidt number of 600 is estimated from velocity u (m s-¹) and slope (m m-¹), and the CO2-specific velocity is obtained by Schmidt-number scaling:

> ln k600 = 5.139 + 0.594 ln u + 0.403 ln slope;  k_emp = k600 (Sc/600)^-0.5

Symbolically, k_600 and k_emp are distinct quantities. The equilibrium concentration C_eq is taken from the preprocessed campaign table, following Henry’s law with atmospheric pCO2 and water temperature; the full derivation will be given in a supporting appendix.

Cross-section visualizations used elsewhere in this work are idealized trapezoids, and the vertical velocity profile is a schematic parabola rather than an ADCP measurement. These representations are display products and are not used as measurements in the metrics below.


### 2.3 Spatial filtering and diagnosis of the subgrid residual

Reach-scale transport formulations average over heterogeneity within each reach, and the unresolved contributions appear formally as a residual source-sink term. Studying that term requires an operable definition of the filter width Deltax rather than a qualitative notion of subgrid structure.

We perform reach-local spatial coarse-graining within each logical reach. Native NHDPlus segments are merged along the network chainage into filter cells, and Deltax is defined as the mean length of the filter cells, with sampled cells reported separately. Where a fully directed network ordering is not available, the implementation falls back to a midpoint Y-then-X coordinate ordering. This fallback is disclosed as an operator boundary; it does not change the definition of the diagnosed residual.

At the operator level the construction parallels the coarse-graining used in large-eddy simulation and in learned subgrid parameterization studies (Yuval & O’Gorman, 2020); the analogy is limited to spatial filtering, and S_sgs denotes the residual of the filtered river CO2 balance at the chosen scale. Once resolved transport and gas exchange are recomputed on the filtered balance, the residual implied by the observations is

> Eq. (5):  S_sgs = k(C - C_eq) - q_A(C_in - C)

S_sgs is a filter-induced closure residual. It can absorb measurement error, errors from the simplified transport representation, and genuinely unresolved processes. It is not a direct measurement of a single unresolved biogeochemical flux. Its magnitude, structure, and learnability are evaluated below as the aggregation scale changes.

![Figure 1. Conceptual representation of the spatial filter. Fine NHD flowline segments are merged into filter windows of width Deltax, and the filtered mass balance on the coarse control volume defines the subgrid residual term S_sgs.](results/figures/les_filter_conceptual.png)


### 2.4 Alternative unresolved-process closures

Three closure configurations are compared. They differ only in how S_sgs and k are supplied to Eq. (1).

The Baseline retains the transport and hydraulic formulation of the other configurations while setting S_sgs = 0 and using the Raymond-type empirical velocity k_emp. It therefore serves as the zero-residual reference against which closure form and evaluation protocol are compared.

The Residual-AI configuration learns S_sgs from hydraulic and water-quality covariates. Two learners are trained with a fixed seed (42): a multilayer perceptron and a random forest. The inputs include discharge, velocity, depth, width, slope, temperature, and the available carbon chemistry, as implemented in the open-source pipeline.

The k-correction configuration leaves S_sgs at zero and multiplies the empirical velocity by a learned factor, k_eff = k_emp·exp(g_θ(X)), where g_θ is a dimensionless correction predicted by a gradient-boosting model (XGBoost). The median ratio k_eff/k_emp under grouped evaluation is reported as a diagnostic of how the correction achieves its fit.


### 2.5 Leave-one-reach-out transport-coupled evaluation

Closure generalization is evaluated with leave-one-reach-out grouped cross-validation across the eight logical reaches. Each reach is held out once. Missing-value imputation and feature scaling are fitted on the training reaches only and then applied to the held-out reach. The closure is predicted for the held-out samples, reinserted into the quasi-steady balance, and only then scored against observed C_aq. No inner hyperparameter-selection loop is used, so we refer to the procedure as grouped cross-validation rather than nested cross-validation.

When an upstream concentration state is unavailable, the solver uses the observed C_aq at the current sample as the fallback boundary value c_in; the experiment therefore evaluates closure generalization under partially observed boundary conditioning rather than fully target-blind forecasting. Sampling is also strongly imbalanced among reaches: R008 contributes 58 of the 120 samples, while three reaches contribute one each, so pooled errors are read together with reach-level evidence weights (Table 5). A date-grouped variant is reported as a time-sensitivity analysis and is not nested inside the reach split.


### 2.6 Metrics and flux diagnostic

The primary metric is the held-out C_aq RMSE in mol m-3. The secondary diagnostic is the sample-summed model flux ΣF_CO2 in mol m-2 d-¹, computed from Eq. (2) with the transport-predicted concentration and the transfer velocity of each configuration: k_emp for the Baseline and Residual-AI, and k_eff for the k-correction. An observation-based proxy flux uses k_emp with observed concentrations. Differences in ΣF_CO2 across closures indicate how each configuration allocates the balance between sources and gas exchange.


### 2.7 Practical equifinality diagnostic

To characterize compensation between source terms and gas exchange, we define the implied source adjustment

> Eq. (6):  S_implied = (k_emp - k_eff)(C - C_eq)

At fixed concentration and resolved transport state, S_implied is the source-sink adjustment that makes a model retaining k_emp locally equivalent to a model that uses k_eff and no additional source term. A large S_implied together with a small change in concentration error indicates that the observations provide limited discrimination between the two allocations; we refer to this compensating closure behaviour as practical equifinality. The diagnostic is algebraic and empirical rather than a formal structural-identifiability analysis.


### 2.8 Sparse dimensionless closure

A final experiment asks whether the residual admits a compact dimensionless representation. Candidate Pi-group features are assembled from the hydraulic state: Froude number Fr, slope, relative depth h/W, and the logarithms of the Reynolds and Damköhler numbers. A standardized LASSO selects terms within each cross-validation fold, following the spirit of sparse discovery methods (Xie et al., 2022), implemented with a scikit-learn LASSO. The resulting form is reported in standardized (z-score) space and reinserted into the transport calculation under the same leave-one-reach-out protocol as the other closures. Compactness is tested against predictive utility; the two are not assumed to coincide.


## 3. Results


### 3.1 Residual closures do not improve held-out concentration prediction

The primary result is negative. Under leave-one-reach-out transport-coupled evaluation, neither residual closure improves on the Baseline (Tables 2 and 3; Figure 3). The held-out C_aq RMSE is 0.0284 mol m-3 for the Baseline, 0.0573 for the Residual-AI multilayer perceptron, and 0.0745 for the random forest. The corresponding MAE values are 0.0132, 0.0326, and 0.0301, and the residual closures show positive concentration bias (0.0177 and 0.0180) where the Baseline bias is -0.0132. The date-grouped sensitivity gives the same ordering (0.0284, 0.0591, and 0.0747).

The subgroup decomposition locates the error (Table 5; Figures 4 and S1). On the mainstem reach R008, both residual closures are slightly better than the Baseline: RMSE is 0.0121 for the MLP and 0.0087 for the random forest against 0.0136 for the Baseline. On the multi-sample tributaries the pattern reverses: RMSE is 0.0381 for the Baseline, 0.0808 for the MLP, and 0.1058 for the random forest. The pooled degradation is concentrated in reaches with moderate sample support, where training data for the residual are sparse and heterogeneous. The holdout scatter (Figure 4) shows the same structure: mainstem predictions cluster near the observations while tributary predictions spread widely.

![Figure 3. Leave-one-reach-out grouped cross-validation with transport coupling: held-out C_aq RMSE for the Baseline, Residual-AI, and k-correction closures (primary comparison).](results/figures/nested_cv_rmse_bar.png)

![Figure 4. Observed versus transport-predicted held-out C_aq for the Residual-AI (MLP) closure under the leave-one-reach-out protocol.](results/figures/nested_cv_scatter_holdout.png)

![Figure S1. Subgroup errors: R008 mainstem versus multi-sample tributaries and single-sample schematic reaches.](results/figures/subgroup_rmse_r008_vs_trib.png)


### 3.2 A corrected gas-transfer velocity lowers concentration error

The k-correction is the only configuration that reduces held-out concentration error below the Baseline. Its C_aq RMSE is 0.0244 mol m-3 against 0.0284 for the Baseline, and MAE falls from 0.0132 to 0.0046 (Tables 2 and 3). The improvement is achieved entirely through the transfer velocity. The median effective velocity is 0.0329 m d-¹, compared with a median empirical value of 98.1 m d-¹; the median ratio k_eff/k_emp is 3.35×10-⁴ (Table 7; Figure 5). Under this correction, gas exchange is reduced to nearly zero rather than fine-tuned.

![Figure 5. Identifiability diagnostics: effective gas-transfer velocity k_eff, the implied source term S_implied, and the Residual-AI held-out source predictions.](results/figures/identifiability_k_vs_sgs.png)


### 3.3 The concentration gain coincides with collapse of the flux diagnostic

The flux diagnostic separates the closures. The sample-summed model flux ΣF_CO2 is 3.24 mol m-2 d-¹ for the Baseline and 0.031 for the k-correction (Table 7; Figure S2). The concentration improvement of the k-correction coincides with a collapse of the modeled CO2 release by roughly two orders of magnitude. The Residual-AI configuration moves in the opposite direction, with ΣF_CO2 of 69.5, because its predicted sources add to the balance while k remains at k_emp.

No independent evasion observations are available for this campaign, so these values do not show that the Baseline flux is correct or that the corrected flux is wrong. They show that concentration performance alone can favor a markedly different allocation of the model balance. The implied-source diagnostic makes the compensation explicit. At fixed concentrations, the mean implied adjustment S_implied is 1.00 mol m-2 d-¹, the mean Residual-AI prediction is 0.56, and the two are anti-correlated across samples (Spearman -0.57; Table 7; Figure S3). A positive source term and a reduced transfer velocity act on the concentration balance in compensating directions, and the held-out concentration metric provides limited discrimination between them.

![Figure S2. Sample-summed model F_CO2 diagnostic and flux RMSE for the three closures. Model diagnostic only; no chamber validation.](results/figures/ablation_flux_comparison.png)

![Figure S3. Concentration–flux trade-off: k_eff/k_emp against held-out RMSE and the sample-summed flux diagnostic.](results/figures/identifiability_tradeoff.png)


### 3.4 The diagnosed residual depends on filter scale

The magnitude of the diagnosed residual varies systematically with the filter width (Table 6; Figure 6). Mean |S_sgs| is 1.916 mol m-2 d-¹ at the native NHD resolution (Deltax ≈ 838 m), decreases to 1.120 and 1.050 at successive merging levels, and reaches 1.000 at the study-reach scale (Deltax ≈ 26,086 m; 7 cells, of which 6 contain samples). The variance of S_sgs falls from 22.4 to 2.20 over the same range (Figure S4). The result indicates that the diagnosed closure residual depends on the spatial representation used to separate resolved from unresolved contributions. It is an empirical scale dependence for the implemented reach-local operator, not a universal scaling law.

![Figure 6. Filter-scale dependence: mean |S_sgs| and variance of S_sgs as functions of filter width Deltax.](results/figures/filter_scale_sgs.png)

![Figure S4. Distributions of |S_sgs| for the 120 samples at each implemented filter scale.](results/figures/filter_scale_sgs_box.png)


### 3.5 A sparse dimensionless closure is compact but not predictive

The standardized LASSO retains three of the five candidate Pi terms (Table 8; Figure 7). In standardized space the closure is

> S*_z ~= 1.059 + 1.536*Fr - 1.669*Slope - 2.179*h/W

with Froude number the positive contributor and slope and relative depth the negative contributors. Under the same leave-one-reach-out transport-coupled protocol, the sparse closure gives a held-out C_aq RMSE of 0.0506 mol m-3, above the Baseline value of 0.0284 (Table 9). The leave-one-reach R2 for S* itself is -2.74. The sparse form is therefore useful as a compact diagnostic description of the residual but does not recover predictive skill on held-out reaches.

![Figure 7. Standardized LASSO coefficients of the sparse dimensionless (Pi-group) closure.](results/figures/dimensionless_coefficients.png)


### 3.6 In-sample fit (appendix)

The in-sample fit of the residual model is reported in the appendix (Table 4; Figure A1), with R2 ≈ 0.997 and RMSE 0.00127 mol m-3 computed on the same 120 rows used for training. The value describes the capacity of the learner to memorize the sample rather than its generalization, and it is not used as a paper metric.

![Figure A1. In-sample observed-versus-predicted scatter (appendix only; in-sample R2 ≈ 0.997 reflects overfitting and is not a skill metric).](results/figures/obs_vs_model_scatter_large.png)


## 4. Discussion


### 4.1 Failed generalization of residual closures is a modelling diagnosis

The residual closures reproduce the observations well in-sample but degrade held-out concentration prediction relative to a zero-residual Baseline. This pattern suggests that the residual diagnosed from the present resolved model, predictors, spatial representation, and sampling design does not carry enough transferable structure to improve predictions after transport coupling. In the evaluation logic of Bennett et al. (2013) and Vilas et al. (2023), the discrepancy is itself diagnostic: it separates apparent learnability from held-out usefulness. The subgroup evidence points to where the transfer fails. Tributary reaches with moderate sample counts carry heterogeneous residual behaviour, and learners trained across reaches do not extrapolate there; the mainstem reach, with 58 samples, is the only subgroup where the residual closures are competitive. For model evaluation, this implies that learned residual closures for river networks need reach-level diagnostics and balanced sampling before pooled metrics can be interpreted.


### 4.2 Process allocation and practical equifinality

The k-correction achieves the lowest concentration error of any configuration, and it does so by reducing the effective transfer velocity by roughly three orders of magnitude. Because both source terms and gas exchange act on the same balance, a near-zero k can be offset by the existing gradient (C - C_eq) and still reproduce concentrations. The collapse of ΣF_CO2 from 3.24 to 0.031 shows what this fit implies for the process budget. Without independent evasion measurements, the data cannot adjudicate between the Baseline and corrected allocations; the lower RMSE is evidence of improved concentration fit, not independent evidence of improved process fidelity.

Here, practical equifinality refers to the compensation between S_sgs and k represented by Eq. (6). The Baseline/k-correction contrast shows that this compensation direction is consequential in the present experiment: similar concentration errors coexist with markedly different transfer velocities and flux diagnostics. The argument is restricted in scope: it is not a formal structural-identifiability analysis, and it does not establish statistical equivalence between the competing predictions. The degraded RMSE of the MLP, random forest, and sparse closures is likewise not equifinality evidence; it shows that closure choice matters and that flexible residual learning did not generalize here. Within those boundaries, concentration-dominated evaluation does not uniquely constrain how discrepancy is allocated between S_sgs and k in this configuration.


### 4.3 What filtering and sparse representation reveal about the residual

The filter-scale results show that the diagnosed residual is not a fixed property of the watershed. Its magnitude changes as the filter width changes, because the split between resolved and unresolved contributions is defined by the filter. This interpretation is bounded by the implemented operator, which uses reach-local merging and a coordinate-ordering fallback rather than a fully directed network filter. Within those boundaries, the result is consistent with the coarse-graining logic used elsewhere for learned subgrid terms (Yuval & O’Gorman, 2020): the statistics of the unresolved term depend on resolution.

The sparse dimensionless closure provides a counterpoint to the flexible learners. It identifies a limited set of candidate dependencies, with Froude number, slope, and relative depth surviving selection, yet its compactness does not transfer into held-out skill: RMSE remains above the Baseline and the S* reconstruction fails under reach holdout. Compact forms are therefore not automatically validated or predictive. In this experiment the Pi-group formulation is most useful as a diagnostic simplification, and under the present protocol the residual does not admit a compact representation with cross-reach predictive utility.


### 4.4 Implications for environmental-model evaluation

These findings suggest that concentration RMSE should be interpreted together with diagnostics of gas exchange and unresolved source allocation. A closure that lowers concentration error deserves scrutiny of the process allocation that produces the lowering, particularly when the observations constrain only concentrations.

The present conclusions are bounded by partially observed upstream conditioning, strongly unequal reach support, the coordinate-based ordering fallback, idealized hydraulic geometry, incomplete covariates (alkalinity, nitrogen, phosphorus, photosynthetically active radiation), and the absence of independent evasion measurements. The Water Quality Portal merge and the StreamPULSE search returned no usable additional constraints for this campaign. These limitations restrict inference to the East River experiment, and they also identify the observations that would most help to discriminate closures: improved upstream boundary information, better-resolved channel geometry, more balanced reach sampling, and independent constraints on gas exchange. The central implication is that lower concentration error alone is insufficient to determine which allocation of unresolved processes is better supported.


## 5. Conclusions

Under leave-one-reach-out transport-coupled evaluation, machine-learned residual closures did not improve held-out concentration prediction (Residual-AI RMSE 0.0573 mol m-3 for the MLP against 0.0284 for the Baseline), while the k-correction lowered RMSE to 0.0244 only as the sample-summed model flux diagnostic fell from 3.24 to 0.031 mol m-2 d-¹ and the median k_eff/k_emp reached 3.35×10-⁴. Concentration-only observations therefore provide limited discrimination between discrepancy assigned to the source term S_sgs and discrepancy assigned to the transfer velocity k.

Methodologically, the experiment establishes an operable filter definition, a grouped evaluation protocol that couples predicted closures back into transport, and an algebraic diagnostic of closure compensation. No accuracy gain is claimed, flux values are model diagnostics rather than validated evasion estimates, and transfer to other basins has not been tested.


## 6. Data availability

The East River water-chemistry and pCO2 data are publicly available through HydroShare (resource 9f907b46baa848e180c49339d605bf31; Saccardi & Winnick, 2021). The DIC supplement, network shapefiles, and hydraulic tables are in HydroShare resource 2a2132999fb84214aad0596783812db2. Mainstem discharge is from USGS gage 09112500. River-network geometry uses NHDPlus HR flowlines for HUC 14020001. Processed tables, figures, and the analysis code are maintained in the public repository (https://github.com/Coucou2016/river-carbon-transport).

## Tables

**Table 1.** East River study network, ordered upstream to downstream.

| Reach | Stream name | Upstream | Downstream | Length (km) | NHD segments | Samples | Note |
|---|---|---|---|---|---|---|---|
| R001 | Bradley Creek | — | R002 | 12.6 | 0 | 1 | Tributary headwater; n = 1, schematic only |
| R002 | Bradley Meadow | R001 | R003 | 12.5 | 0 | 3 | Meadow reach connecting Bradley and Rock Creeks |
| R003 | Rock Creek | R002 | R004 | 6.1 | 0 | 15 | Rock Creek; multi-sample tributary |
| R004 | Copper Creek | R003 | R005 | 9.9 | 23 | 24 | Good GNIS match against NHD |
| R005 | Gothic Creek | R004 | R006 | 4.8 | 0 | 17 | Gothic Creek; multi-sample tributary |
| R006 | Quigley Creek | R005 | R007 | 2.8 | 6 | 1 | Single sample; schematic only |
| R007 | Rustlers Gulch | R006 | R008 | 23.5 | 0 | 1 | Single sample; schematic only |
| R008 | East River mainstem | R007 | — | 20.2 | 46 | 58 | Mainstem above Almont; densest sampling |

**Table 2.** Main results under leave-one-reach-out grouped cross-validation with transport coupling (flux totals are model diagnostics).

| Scheme / model | C RMSE | F total | k_eff/k_emp | Beats Baseline (C)? |
|---|---|---|---|---|
| baseline / none | 0.0284 | 3.244 | 1.00000 | — |
| k_correction / xgboost | 0.0244 | 0.031 | 0.00034 | Yes |
| residual_ai / mlp | 0.0573 | 69.507 | 1.00000 | No |
| residual_ai / random_forest | 0.0745 | 143.331 | 1.00000 | No |
| sparse_pi / lasso_pi | 0.0506 | 244.183 | — | No |

**Table 3.** Leave-one-reach-out grouped cross-validation: held-out C_aq and F_CO2 (primary metrics; F values are model flux diagnostics).

| Scheme / model | C RMSE | C MAE | C Bias | C R2 | F RMSE | F Bias | F total | n |
|---|---|---|---|---|---|---|---|---|
| baseline / none | 0.0284 | 0.0132 | -0.0132 | -0.264 | 1.733 | -0.973 | 3.24 | 120 |
| k_correction / xgboost | 0.0244 | 0.0046 | -0.0046 | 0.061 | 1.783 | -1.000 | 0.03 | 120 |
| residual_ai / mlp | 0.0573 | 0.0326 | 0.0177 | -4.163 | 1.562 | -0.421 | 69.51 | 120 |
| residual_ai / random_forest | 0.0745 | 0.0301 | 0.0180 | -7.723 | 2.103 | 0.194 | 143.33 | 120 |

**Table 4.** In-sample metrics (optimistic appendix; not a paper conclusion).

| Model | C RMSE | C Bias | C R2 | n |
|---|---|---|---|---|
| baseline_in_sample (in-sample, optimistic) | 0.02836 | -0.0132 | -0.264 | 120 |
| residual_ai_in_sample_optimistic (in-sample, optimistic) | 0.00127 | 0.0005 | 0.997 | 120 |

**Table 5.** Subgroup metrics under leave-one-reach-out cross-validation.

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

**Table 6.** Filter-scale experiment: S_sgs after snapping the 120 samples onto coarsened NHDPlus HR networks.

| Scale | dx (m) | Cells | Sampled cells | Samples | Mean |S| | Var(S) |
|---|---|---|---|---|---|---|
| Native NHD | 838 | 536 | 39 | 120 | 1.916 | 22.405 |
| ~2× merge | 1183 | 270 | 30 | 120 | 1.120 | 3.467 |
| ~4× merge | 1949 | 137 | 24 | 120 | 1.050 | 2.894 |
| Study reaches (8) | 26086 | 7 | 6 | 120 | 1.000 | 2.197 |

**Table 7.** Identifiability: k versus S_sgs under the same grouped protocol.

| Scheme | C RMSE | F total | Median k | k_eff/k_emp |
|---|---|---|---|---|
| baseline | 0.0284 | 3.24 | 98.096 | 1.00000 |
| residual_ai | 0.0573 | 69.51 | 98.096 | 1.00000 |
| k_correction | 0.0244 | 0.03 | 0.033 | 0.00034 |

**Table 8.** Sparse dimensionless closure (Pi-group LASSO).

| Item | Result |
|---|---|
| Standardized form | S_sgs*_z ≈ + 1.059 + 1.536*Fr − 1.669*Slope − 2.179*h_over_W |
| Original-variable form | S_sgs* ≈ + 8.368 + 1.327*Fr − 38.8*Slope − 349*h_over_W |
| Dominant terms | -2.18*h_over_W + -1.67*Slope + +1.54*Fr |
| Leave-one-reach R2 on S* | -2.743 (negative = does not generalize) |

**Table 9.** Sparse dimensionless closure inserted into transport under grouped cross-validation (compare Baseline 0.0284 in Table 3).

| Scheme | C RMSE | C R2 | F RMSE | n |
|---|---|---|---|---|
| sparse_pi / lasso_pi (leave-one-reach) | 0.0506 | -3.024 | 2.508 | 120 |

## References

1. Battin, T. J., et al. (2023). River ecosystem metabolism and carbon biogeochemistry in a changing world. Nature, 614, 676–687. https://doi.org/10.1038/s41586-022-05500-8
2. Bennett, N. D., et al. (2013). Characterising performance of environmental models. Environmental Modelling & Software, 40, 1–20. https://doi.org/10.1016/j.envsoft.2012.09.011
3. Gao, Y., et al. AI cross-fusion approach for river carbon transport. The Innovation (manuscript in preparation; DOI to be added).
4. Gómez-Gener, L., Rocher-Ros, G., et al. (2021). Global carbon dioxide efflux from rivers enhanced by high nocturnal emissions. Nature Geoscience, 14, 647–653. https://doi.org/10.1038/s41561-021-00722-3
5. Hotchkiss, E. R., et al. (2015). Sources of and processes controlling CO2 emissions change with the size of streams and rivers. Nature Geoscience, 8, 696–699. https://doi.org/10.1038/ngeo2507
6. Markovich, K. H., White, J. T., & Knowling, M. J. (2022). Sequential and batch data assimilation approaches to cope with groundwater model error. Environmental Modelling & Software, 158, 105498. https://doi.org/10.1016/j.envsoft.2022.105498
7. Raymond, P. A., et al. (2012). Scaling the gas transfer velocity and hydraulic geometry in streams and small rivers. Limnology and Oceanography: Fluids and Environments, 2, 41–53. https://doi.org/10.1215/21573689-1597669
8. Saccardi, B., & Winnick, M. J. (2021). Improving predictions of stream CO2 concentrations and fluxes using a stream network model. Global Biogeochemical Cycles, 35, e2021GB006972. https://doi.org/10.1029/2021GB006972
9. Vilas, M. P., et al. (2023). TALKS: A systematic framework for resolving model-data discrepancies. Environmental Modelling & Software, 166, 105668. https://doi.org/10.1016/j.envsoft.2023.105668
10. Xie, X., Samaei, A., Guo, J., Liu, W. K., & Gan, Z. (2022). Data-driven discovery of dimensionless numbers and governing laws from scarce measurements. Nature Communications, 13, 7402. https://doi.org/10.1038/s41467-022-35084-w
11. Yuval, J., & O’Gorman, P. A. (2020). Stable machine-learning parameterization of subgrid processes for climate modeling. Nature Communications, 11, 3710. https://doi.org/10.1038/s41467-020-17142-3

*Self-contained HTML with 13 embedded figures: paper.html (no CDN).*
