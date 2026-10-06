# Transport-coupled evaluation of river-network CO₂ closures: Evidence for practical equifinality under concentration-only observations

**Authors:** To be completed (待补充)  
**Affiliations:** To be completed (待补充)

## Key Points

- Public East River observations (Saccardi/Winnick) were reanalysed on an NHDPlus HR directed network with fold-local residual targets.
- Under grouped leave-one-reach-out transport CV, the Residual-AI MLP pooled RMSE is 0.0507 mol m⁻³ against 0.0485 for the Baseline, but the MLP is better on the mainstem subgroup (0.0233 vs 0.0278) and worse on the multi-sample tributaries; the pooled difference is dominated by R002 (0.833 of the gross positive SSE gain), so this is not a settled success claim.
- Concentration data alone cannot identify how discrepancy is allocated between subgrid sources and gas exchange (profile SSE, not likelihood).

## Plain Language Summary

Rivers take up, transform, and release carbon, and models of river carbon must represent processes that cannot be observed directly, such as groundwater CO₂ inputs and the exchange of gas with the atmosphere. When only concentration measurements are available, different model structures can reproduce the same observed concentrations by adjusting different process terms. We reanalysed 120 public water samples from the East River campaign of Saccardi and Winnick (2021), mapped to a high-resolution directed stream network from public NHD and USGS data. We compared a baseline transport model with variants that add a machine-learned source term or a corrected gas-exchange rate. Training targets for the residual learners were rebuilt inside each held-out fold so that held-out concentrations cannot enter training labels through network routing. Under that protocol the pooled held-out concentration error of the learned source term (0.0507 mol m⁻³) is not lower than the zero-source Baseline (0.0485 mol m⁻³); the learned closure is better only on the mainstem subgroup and worse on the multi-sample tributaries, and the pooled contrast is dominated by three samples in R002 (0.833 of the gross positive error reduction). Area-weighted flux diagnostics remained unstable and must not be read as study-area totals. A corrected gas-exchange rate could not improve on the baseline, and a model-free profile SSE showed that a single concentration measurement cannot tell apart a model that adjusts gas exchange from one that adds an unseen carbon source. Evaluations of river-carbon models should therefore combine concentration skill with process-level diagnostics such as independent gas-exchange measurements.

## Abstract

River-network carbon models combine downstream transport, unresolved source and sink processes, and air-water gas exchange, but concentration-based evaluation may not distinguish errors assigned to different terms in the same mass balance. We reanalysed 120 publicly archived East River observations (Saccardi and Winnick, 2021) organized into eight logical reaches and mapped to an NHDPlus HR directed network, with USGS outlet discharge and published synoptic tributary Q. Spatial coarse-graining defines a signed residual source-sink term (S_sgs). Closures were a zero-residual Baseline, machine-learned residual closures (Residual-AI), or a multiplicative correction to an energy-dissipation-based gas-transfer velocity. Residual and k targets were rebuilt inside each leave-one-reach-out fold without held-out concentration labels. The Baseline held-out C_aq RMSE was 0.0485 mol m⁻³; the Residual-AI MLP and random forest gave 0.0507 and 0.0557 mol m⁻³. The learned closure is therefore not better than the zero-source Baseline on pooled held-out concentration: its apparent advantage is confined to the mainstem subgroup (0.0233 vs 0.0278 mol m⁻³) and it is worse on the multi-sample tributaries (0.0685 vs 0.0634 mol m⁻³); 0.833 of the gross positive error reduction comes from three R002 samples. Overlapping sample-area flux diagnostics (not study-area totals) were 7.96×10² mol d⁻¹ (Baseline) versus 3.26×10⁶ (MLP) and 1.64×10⁶ (RF). A k-correction did not improve on the Baseline (0.0485 mol m⁻³); 55% of samples could not be matched by any positive transfer velocity alone. A model-free objective surface and profile SSE show that a single concentration observation leaves an exact zero valley in the (k, S_sgs) plane, and pooling leaves the profile shallow (RMSE 0.0343 mol m⁻³ near the optimum). Filter-scale |S_sgs| under path-connected coarsening remains sampling-conditional because synchronous coverage is sparse and the study-reach merge is unresolved under full cross-group edge preservation. Lower concentration error alone is insufficient to identify how model discrepancy is allocated between unresolved sources and gas exchange.

**Keywords:** river carbon cycling; environmental model evaluation; subgrid closure; gas-transfer velocity; grouped cross-validation; practical equifinality


## 1. Introduction

Rivers link terrestrial, aquatic, and atmospheric carbon cycling by transporting dissolved carbon, transforming it through biological and biogeochemical processes, and exchanging CO₂ with the atmosphere. Riverine CO₂ evasion is a substantial component of inland-water carbon budgets, but both the magnitude and dominant controls of that flux vary across river networks and over time (Hotchkiss et al., 2015; Gómez-Gener et al., 2021; Battin et al., 2023). Predictive models must therefore represent several processes that operate simultaneously: downstream advection, lateral and internal carbon inputs, in-stream transformation, and air-water gas exchange. At the reach scale, however, observations and model states average over spatial heterogeneity that may occur over much shorter distances. A reach-scale model can consequently reproduce concentration while compensating for unresolved source or sink processes through another term in the mass balance. This possibility matters whenever model performance is judged mainly from concentration observations.

The East River watershed provides a useful setting in which to examine this problem because a process-based stream-network CO₂ model has already been developed for the system. Saccardi and Winnick (2021) represented downstream transport together with CO₂ sources and atmospheric exchange to predict spatial variation in stream CO₂ concentrations and fluxes. Their work illustrates how several process terms jointly determine the same downstream concentration state. Gas exchange is commonly represented through an empirical transfer velocity, and Raymond et al. (2012) related gas-transfer velocity to hydraulic properties of streams and small rivers. Such parameterizations make gas exchange operational at network scale, but they do not remove uncertainty in the other terms of the carbon balance. Groundwater inputs, lateral inflows, metabolic heterogeneity, and other sub-reach processes may remain incompletely observed or resolved. Errors in these processes and errors in gas exchange can therefore enter the same concentration equation and potentially offset one another.

This compensation complicates model evaluation because different process allocations can produce similar concentration responses. Bennett et al. (2013) argued that environmental-model performance should be characterized using evidence appropriate to model purpose rather than a single goodness-of-fit statistic. Vilas et al. (2023) likewise treated model-data discrepancy as information that may arise from the model, the observations, or their interaction, while Markovich et al. (2022) evaluated alternative methods explicitly in the presence of model error. For river-carbon transport, these considerations imply that a lower concentration error is not necessarily sufficient to identify which process representation is better supported. If an unresolved source-sink correction and the gas-transfer velocity can both alter the same predicted concentration, optimizing either term may reduce residual error. The relevant test is whether their effects remain distinguishable when each candidate closure is coupled back to the transport model and evaluated under reach-grouped transport coupling, subject to the boundary-conditioning and target-construction limitations described below.

Machine learning provides one possible representation of unresolved process terms. In climate modeling, for example, spatial coarse-graining has been used to define unresolved tendencies and to train data-driven subgrid parameterizations, including models tested across resolutions (Yuval & O’Gorman, 2020). Related work on data-driven closure of river-carbon transport is also in preparation (Gao et al., manuscript in preparation). The central difficulty is not whether a flexible model can fit a diagnosed residual in the data used for training, but whether that residual representation remains useful after transfer to a new spatial group and reinsertion into the governing balance. A residual may encode repeatable unresolved dynamics, but it may also absorb errors in hydraulic representation, boundary conditions, observations, or other model components. Strong in-sample fit therefore provides limited evidence for a closure unless its effect is evaluated through the coupled model under held-out conditions.

Here we examine that question using 120 public East River campaign observations organized into eight logical reaches and mapped to a National Hydrography Dataset Plus High Resolution (NHDPlus HR) representation. We spatially coarse-grain the reach-scale mass balance to diagnose a residual source-sink term, S_sgs, and compare three closure strategies: a zero-residual Baseline, machine-learned residual closures, and a multiplicative correction to the empirical gas-transfer velocity. Evaluation is grouped by reach and transport-coupled, so the closure predicted for a held-out reach is reinserted into the quasi-steady mass balance before C_aq is scored. We also examine how the diagnosed residual changes with filter scale and whether a sparse dimensionless representation retains held-out predictive value. Several boundaries constrain the interpretation. Reach support is strongly unequal, channel geometry follows a published hydraulic-geometry relation rather than direct measurement, and no independent evasion observations are available. Within these constraints, the test is whether concentration-only observations can distinguish discrepancy assigned to S_sgs from discrepancy assigned to k when both closures are evaluated through the same transport calculation. Figure 1 states the two spatial-aggregation rules used throughout, and the sections below follow the logical order of the analysis: study data and network representation (Section 2.1), the mass balance and gas exchange (Section 2.2), the filtering operator and the diagnosed residual (Section 2.3), the competing closures (Section 2.4), and the evaluation protocol (Sections 2.5–2.8).

![Figure 1. Schematic of the two aggregation rules used by the cell-DAG operator, drawn side by side. (a) Serial contraction along one channel: cells share a single discharge, so Q is constant downstream and &Sigma;QC is accumulated along the chain rather than re-averaged. (b) Parallel confluence at a junction: Q_out = Q_1 + Q_2 and C_out is flow-weighted, not an arithmetic mean, while areas add and repeated observations in one cell add no area. Both panels are schematic and not to scale; the figure states the operator rules and is not evidence that conservation was achieved in a particular run.](results/figures/les_filter_conceptual.png)


## 2. Methods


### 2.1 Study data and river-network representation

The study uses public observations from the upper East River watershed near Almont, Colorado (hydrologic unit code (HUC) 14020001). The water-chemistry data come from the field campaign of Saccardi and Winnick (2021), which comprises 120 samples collected between 2 and 11 August 2019. Samples are assigned to eight logical reaches, R001 through R008, with counts of 1, 3, 15, 24, 17, 1, 1, and 58, respectively (Table 1). Three reaches (R001, R006, R007) contain a single sample and are treated as schematic: they enter the network bookkeeping but do not carry the same evidence weight as the mainstem reach R008. The eight reaches serve as cross-validation groups and reporting units. Corridor-level transport and filter experiments use the directed NHDPlus HR topology. The mainstem East River is subdivided into six ordered segments (R008_S1 through R008_S6) by confluence northing thresholds into a logical reporting / verified-simplified routing tree—not a fully verified path-compressed NHD directed compression—and the seven tributaries join at their mapped confluences through flow-weighted mixing (Section 2.2).

The river-network representation combines three public sources. The HydroShare supplement of Saccardi and Winnick (2021) provides the campaign observations and the synoptic tributary discharges. An extract of the NHDPlus HR product for HUC 14020001 provides the flowlines used for the corridor-level filter lattice; these flowlines are ordered into a directed acyclic topology by endpoint matching and the NHD flow-direction attribute, so concentration is routed strictly upstream to downstream rather than by geographic coordinates. The mainstem East River (reach R008) reporting segments R008_S1–S6 follow the logical y-threshold tree above; each tributary reach (R001–R007) joins that tree at a mapped confluence. Discharge for the mainstem comes from USGS gage 09112500 (East River at Almont) on the sample dates; tributary discharges are the published synoptic values from the campaign supplement, with no gage-ratio scaling applied.

Channel width and depth are not measured along the corridor, so both are estimated from the hydraulic-geometry relations of Raymond et al. (2012), fitted to 1026 paired measurements in streams and small rivers: width W = 12.88·Q^0.42 (m), depth h = 0.4·Q^0.29 (m), and bulk velocity u = 0.19·Q^0.29 (m s⁻¹), with discharge Q in m^3 s^-1. These are model-derived hydraulic inputs rather than measured cross-section properties, and the width enters velocity, k_600, and the water-surface area A_s = L·W. All hydraulic and gas-exchange quantities are conditional on this adopted geometry; no independent cross-section survey is available for this corridor. Because the three relations were fitted separately, they are not exactly mutually consistent: together they imply u·W·h = 0.97888·Q, so the continuity identity u = Q/(W·h) closes only to 2.112%. We retain the published regression for u rather than substituting the continuity-derived velocity, because replacing it would require recomputing k_600, the Reynolds, Froude and Damköhler numbers and every downstream residual; the 2.112% closure deviation is therefore carried as a stated systematic of the adopted geometry rather than silently absorbed. Biogeochemical covariates are likewise incomplete: dissolved inorganic carbon (DIC) and dissolved organic carbon (DOC) are available for 41 of the 120 samples, and alkalinity, nitrogen, phosphorus, and photosynthetically active radiation were not available for this campaign. A same-day merge against the Water Quality Portal returned no matching samples (0 of 120), and the StreamPULSE database contains no East River sites. These gaps constrain the covariate set available to the closures. Figure 2 shows the logical-reach assignment and the distribution of the 120 campaign samples on the river network.

![Figure 2. (a) Logical reach assignment on the NHDPlus HR network over an Esri World Imagery satellite basemap: segments were assigned to the logical study-reach labels by GNIS name matching and proximity to campaign coordinates; colors indicate reach assignment, and the single-sample reach R001 receives no assigned segment in this rendering. (b) Locations of the 120 campaign samples on the same basemap; point colors denote logical reaches R001–R008, with 58 samples on R008. Thin arrows show the digitized flow direction only, so the map is a location reference and is not a flow-validity test. Both panels are drawn in Web Mercator (EPSG:3857) with a metric scale bar and a north arrow; basemap tiles are cached locally with recorded provenance and hashes (see the figure sidecar).](results/figures/figure2_reach_assignment_and_samples.png)


### 2.2 Quasi-steady CO₂ mass balance and gas exchange

Each sample is associated with a control volume defined by its reach length L and computed width W. Carbon mass in the control volume is closed under a quasi-steady assumption at a daily time step: advective exchange with the upstream reach, source-sink inputs, and atmospheric gas exchange balance one another,

> Eq. (1):  Q(C_in - C) + (A_s/tau_d)[S_sgs - k(C - C_eq)] = 0

where Q is discharge (m³ s⁻¹), C_in and C are the upstream and reach concentrations (mol m⁻³), k is the gas-transfer velocity (m d⁻¹), S_sgs is the areal source-sink term (mol m⁻² d⁻¹), C_eq is the equilibrium concentration with the atmosphere, A_s = L·W is the water-surface planform area (m²), and tau_d = 86400 s d⁻¹ converts the daily areal flux into mol s⁻¹. The planform area A_s is not the hydraulic cross-section area; the bulk velocity used below is u = Q/A_c with A_c the cross-section area. For residual diagnosis, C is the observed concentration and S_sgs is inferred from the observations; for forward simulation, C is solved from the balance and the closure supplies the source term. Writing the balance explicitly on a daily areal basis avoids mixing time bases. Dividing Eq. (1) by A_s/tau_d gives the equivalent form

> Eq. (2):  q_A(C_in - C) + S_sgs - k(C - C_eq) = 0

in which q_A = tau_d·Q/A_s (m d⁻¹) is a daily area-normalized discharge and every term has units mol m⁻² d⁻¹.

All closures are inserted into this same balance: a closure configuration is defined entirely by how it supplies S_sgs and k, and every configuration is scored after the identical transport calculation is re-solved. Because the transport numerics are held fixed, differences among configurations arise from their closure specification and the resulting allocation of model discrepancy.

Gas exchange is summarized by the model flux density

> Eq. (3):  F_CO2 = k(C - C_eq)

The reported flux totals are area-weighted sums of F_CO₂ over the water-surface area A_s (mol d⁻¹). They compare how each closure allocates the model balance; they are neither independently observed evasion fluxes nor spatially integrated watershed fluxes.

The empirical transfer velocity follows the energy-dissipation parameterization of Ulseth et al. (2019), which was the formulation used by the original East River model (Saccardi & Winnick, 2021) and which accounts for the high turbulence of steep mountain streams. The Schmidt-600-normalized velocity k_600 is estimated from the stream energy-dissipation rate e_D = g·S·u, and the CO₂-specific velocity is obtained by Schmidt-number scaling:

> ln k600 = 1.18 ln eD + 6.43 (eD >= 0.02 m2 s-3);  eD = g S u;  k_emp = k600 (Sc/600)^-0.5

We distinguish the Schmidt-600-normalized velocity k_600 from the CO₂-specific empirical velocity k_emp. The high-energy branch (e_D ≥ 0.02 m² s⁻³) applies throughout the study corridor; the Schmidt number Sc is evaluated at the sample water temperature. Because the choice of k_600 parameterization affects every gas-exchange result, Raymond et al. (2012) Model-4 k_600 values are retained as a sensitivity column in the processed observation table (median k_600 ≈ 98 m d⁻¹ versus ≈ 268 m d⁻¹ for Ulseth); the primary evaluation below uses Ulseth throughout. The equilibrium concentration C_eq is computed from Henry’s law with a temperature-dependent solubility constant. The constant follows the NIST/Sander compilation for CO₂ in water, k^°_H(298.15 K) = 0.035 mol kg⁻¹ bar⁻¹ with a van ’t Hoff temperature dependence d(ln k_H)/d(1/T) = 2400 K, so C_eq = k_H(T)·pCO₂·ρ_water with the atmospheric pCO₂ fixed at 400 µatm. Colder water dissolves more CO₂, so C_eq now varies with each sample’s temperature rather than being held at a single constant.

Cross-section visualizations used elsewhere in this work are idealized trapezoids, and the vertical velocity profile is a schematic parabola rather than an ADCP measurement. These representations are display products and are not used as measurements in the metrics below.


### 2.3 Spatial filtering and diagnosis of the subgrid residual

Reach-scale transport formulations average over heterogeneity within each reach, and the unresolved contributions appear formally as a residual source-sink term. Studying that term requires an operable definition of the filter width Deltax rather than a qualitative notion of subgrid structure.

We perform spatial coarse-graining on the directed NHDPlus HR flowlines. Flowlines are first ordered by their directed topology (upstream to downstream, from endpoint matching and the NHD flow-direction attribute), then grouped into filter cells as individual flowlines, consecutive pairs, or consecutive groups of four (native, ~2×, and ~4× merges). A whole-reach (study_reach) contraction that preserves all cross-group fine edges produces a cyclic cell DAG and is therefore excluded from formal filter claims (no singleton fallback). Each campaign observation is snapped to its nearest cell at each resolved scale. The reported Deltax is the mean length of the unique spatial cells that contain samples at that scale, giving Deltax ≈ 587 m for the native operator. Figure 1 summarizes the filtering construction.

For each date and filter scale, the inflow concentration C_in to a headwater cell is the atmospheric-equilibrium concentration C_eq; downstream, C_in is the observed concentration of the nearest sampled cell upstream along the directed flow path. A sample’s own observed concentration is never used as its own upstream boundary, so the diagnosis is target-blind with respect to C_in. Because each cell contributes one mass-balance residual, metrics are computed over unique spatial cells rather than re-counting the 120 samples at every scale.

At the operator level the construction parallels the coarse-graining used in large-eddy simulation and in learned subgrid parameterization studies (Yuval & O’Gorman, 2020); the analogy is limited to spatial filtering, and S_sgs denotes the residual of the filtered river CO₂ balance at the chosen scale. Once resolved transport and gas exchange are recomputed on the filtered balance, the residual implied by the observations is

> Eq. (4):  S_sgs = k(C - C_eq) - q_A(C_in - C)

S_sgs is a filter-induced closure residual. It can absorb measurement error, errors from the simplified transport representation, and genuinely unresolved processes. It is not a direct measurement of a single unresolved biogeochemical flux. Its magnitude, structure, and learnability are evaluated below as the aggregation scale changes.


### 2.4 Alternative unresolved-process closures

Three closure configurations are compared. They differ only in how S_sgs and k are supplied to Eq. (1).

The Baseline retains the transport and hydraulic formulation of the other configurations while setting S_sgs = 0 and using the energy-dissipation empirical velocity k_emp (Ulseth et al., 2019). It serves as the zero-residual reference for comparison with the alternative closure formulations.

The Residual-AI configuration learns S_sgs from hydraulic and water-quality covariates. Two learners are trained with a fixed seed (42): a multilayer perceptron and a random forest. The candidate predictor pool comprises discharge, velocity, depth, width, slope, temperature, the available carbon chemistry (dissolved organic carbon for 41 of the 120 samples), and the derived dimensionless quantities; fields that are entirely absent from the campaign table are excluded, and missing retained predictors are imputed with medians calculated from the training reaches of each fold. The multilayer perceptron uses hidden layers of 64, 32, and 16 units with learning rate 0.001, early stopping, and fold-specific predictor standardization, and its predicted residual is signed, allowing both source and sink values. The random forest uses 200 trees with maximum depth 12 and no predictor standardization. The training target is the dimensionally consistent residual of Eq. (4), diagnosed from the observed concentrations routed through the directed network (Section 2.3).

The k-correction configuration leaves S_sgs at zero and multiplies the empirical velocity by a learned factor, k_eff = k_emp·exp(g_θ(X)), where g_θ is a dimensionless correction predicted by a gradient-boosting model (XGBoost; 300 trees, maximum depth 6, learning rate 0.05, seed 42). The training target is constructed within each fold by solving the balance for the transfer velocity k_need required to reproduce the observed concentration with S_sgs = 0, using the diagnosed upstream concentration C_in of the same fold; the predicted correction is then applied as k_eff = k_emp·exp(g_θ(X)) before the transport balance is re-solved. For 55% of the samples no positive k_need exists (a positive transfer velocity cannot reproduce the observed supersaturation with S_sgs = 0), and these rows are excluded from the k-correction target; the held-out saturation fraction at the imposed logarithmic lower bound (g = -12) is 0.000. The median ratio k_eff/k_emp under grouped evaluation is reported as a diagnostic of how the correction behaves.

The diagnosed residual is positive for all 120 samples (a subgrid source; Section 3), yet the Residual-AI learners are left unbounded in prediction. The consequence of this signed, unbounded prediction is examined under held-out evaluation in Section 3.


### 2.5 Leave-one-reach-out transport-coupled evaluation

Closure generalization is evaluated by leaving one logical reach out at a time across the eight logical reaches. Each reach is held out once. For each fold, missing predictors are imputed with medians from the training reaches; predictor standardization is fitted on the training data only for the models that use it, specifically the multilayer perceptron and the sparse model described in Section 2.8. The closure is fitted on the training-reach targets and then used to generate closure values for the full network state required by the transport calculation; the complete quasi-steady network is re-solved with those closure values, and only then are the predictions belonging to the held-out reach retained and scored against observed C_aq. No inner hyperparameter-selection loop is used, so we refer to the procedure as grouped cross-validation rather than nested cross-validation.

The upstream boundary is fully independent of the sample being predicted: each headwater segment enters with the atmospheric-equilibrium concentration C_eq, and no observed C_aq is used as a fallback for the sample being scored, so the evaluation is target-blind with respect to upstream conditioning. Sampling is strongly imbalanced among reaches: R008 contributes 58 of the 120 samples, while three reaches contribute one each, so pooled errors are read together with reach-level evidence weights (Table 5). A date-grouped variant is reported as a time-sensitivity analysis and is not nested inside the reach split.


### 2.6 Metrics and flux diagnostic

The primary metric is the held-out C_aq RMSE in mol m⁻³. The secondary diagnostic is the area-weighted model flux Σ(F_CO₂·A_s) in mol d⁻¹, computed from Eq. (3) with the transport-predicted concentration and the transfer velocity of each configuration (k_emp for the Baseline and Residual-AI, k_eff for the k-correction), summed as an overlapping sample-area diagnostic (not a study-area total). An observation-based proxy uses k_emp with observed concentrations. Differences in this area-weighted total across closures indicate how each configuration allocates the balance between sources and gas exchange; the totals are model diagnostics, not independently validated evasion measurements.


### 2.7 Practical equifinality diagnostic

To characterize compensation between source terms and gas exchange, we define the implied source adjustment

> Eq. (5):  S_implied = (k_emp - k_eff)(C - C_eq)

At fixed concentration and resolved transport state, S_implied is the source-sink adjustment that makes a model retaining k_emp locally equivalent to a model that uses k_eff and no additional source term. In Eq. (5), C is the observed aqueous concentration at the sample, so the two process allocations are compared at a common observed concentration rather than at their respective forward-model concentrations. A large S_implied together with a small change in concentration error indicates that the observations provide limited discrimination between the two allocations; we refer to this compensating closure behaviour as practical equifinality.

We additionally quantify this trade-off model-free, without any machine-learned model in the loop. For a single sample, the objective J(k, S) = [C_obs - C_model(k, S)]² vanishes exactly on the line S = S_diag + (C_obs - C_eq)(k - k_emp), so one concentration observation cannot identify (k, S) jointly and the per-sample profile SSE is identically flat. Pooling the 120 samples with a uniform k-scale α = k/k_emp and a uniform source S gives a pooled objective J(α, S) and a profile J_prof(α) = min_S J(α, S); the flatness of J_prof over α quantifies how little the concentration data alone discriminate the two closures. This is reported as the primary equifinality evidence rather than a single fitted model.


### 2.8 Sparse dimensionless closure

A final experiment asks whether the residual admits a compact dimensionless representation. The dimensionless response is defined as S* = S_sgs/(k_empC_eq), with Froude number Fr, slope, relative depth h/W, and the base-10 logarithm of the Reynolds number as candidate nondimensional features, together with an implemented Damköhler candidate whose time-base inconsistency is described below. Sparse selection follows the spirit of sparse discovery methods (Xie et al., 2022), implemented with a least absolute shrinkage and selection operator (LASSO). Within each leave-one-reach-out fold, missing predictors are imputed from the training reaches, the predictors are standardized using training-fold statistics, and a LASSO with fixed penalty α = 0.05 is fitted on the dimensional residual; the predicted S_sgs is reinserted into the transport calculation and scored only on the held-out reach. For descriptive reporting, the same LASSO specification is fitted once to the full dataset against the dimensionless response S*; the sparse relation reported below comes from that full-data refit and is therefore a descriptive coefficient summary rather than a coefficient vector applied unchanged across the holdout folds. The Damköhler number is constructed as kτ/h with τ = L/u; as implemented, τ in seconds is multiplied by k in m d⁻¹, so this candidate feature is not strictly dimensionless. Selection drops the term, and the retained predictors (Fr, slope, h/W) are unaffected. Compactness is tested against predictive utility; the two are not assumed to coincide.


## 3. Results


### 3.1 Residual closures do not improve pooled held-out concentration prediction

Under leave-one-reach-out transport-coupled evaluation with independent upstream boundary conditioning, the pooled held-out C_aq RMSE of the Residual-AI MLP is 0.0507 mol m⁻³ against 0.0485 for the Baseline and 0.0557 for the random forest (Tables 2 and 3; Figure 3). The learned closures therefore do not lower pooled held-out concentration error relative to the zero-source Baseline. The corresponding mean absolute error (MAE) values are 0.0235, 0.0305, and 0.0309, and the residual closures show a positive concentration bias (0.0241 and 0.0203) where the Baseline bias is -0.0235. In-sample concentration metrics are not reported as a paper result: after recalculation the sole concentration skill metric is leave-one-reach-out transport-coupled C_aq. A date-grouped variant of the Baseline gives the same pooled RMSE, with the date-grouped evaluation outputs archived in the public repository cited in Section 6.

The subgroup decomposition locates both the apparent gain and its fragility (Table 5; Figures 4 and 5). On the mainstem reach R008, both residual closures are better than the Baseline: RMSE is 0.0233 for the MLP and 0.0159 for the random forest against 0.0278 for the Baseline. On the multi-sample tributaries (R002–R005) the pattern reverses: RMSE is 0.0634 for the Baseline, 0.0685 for the MLP, and 0.0777 for the random forest. The pooled contrast is dominated by a small number of points: three samples in R002 account for 0.833 of the gross positive error reduction, while the net MLP-minus-Baseline pooled SSE change is -0.026246 (a net worsening). Dropping R002 without retraining gives pooled RMSE of 0.0268 (Baseline) and 0.0405 (MLP). The equal-weight-reach MSE-then-square-root estimand is 0.0931 (Baseline) and 0.0785 (MLP), which is the unweighted mean of per-reach MSE followed by a square root, not the mean of per-reach RMSE. The holdout scatter (Figure 4) shows the same structure: mainstem predictions cluster near the observations while tributary predictions spread widely. With eight reaches and this sampling imbalance, these contrasts are descriptive of this campaign and do not support a general generalization inference.

The residual closures are also unstable out of sample. Because the signed source prediction is unbounded, the MLP and random forest extrapolate to large sources on held-out reaches, driving the area-weighted model flux to 3.26×10⁶ and 1.64×10⁶ mol d⁻¹, respectively, against 7.96×10² mol d⁻¹ for the Baseline (Table 2). The tested target formulation is therefore not sufficient: flexible residual learning of a dimensionally consistent but unbounded S_sgs does not transfer to held-out reaches and produces unphysical source extrapolation.

![Figure 3. Grouped leave-one-reach-out cross-validation with transport coupling (120 samples, 8 reach groups, fixed random seed): held-out C_aq RMSE for the Baseline, Residual-AI (MLP and random forest), and k-correction closures. Filled bars are the pooled sample-weighted metric; the open markers show the per-reach values behind it, so the pooled contrast can be read against the reach-level spread. The dashed line marks the Baseline value. No closure lowers the pooled RMSE below the zero-residual Baseline; the k-correction is indistinguishable from it.](results/figures/nested_cv_rmse_bar.png)

![Figure 4. Observed versus transport-predicted held-out C_aq for the Residual-AI (MLP) closure under leave-one-reach-out grouped evaluation (n=120); colors denote logical reaches and the dashed line indicates 1:1 agreement. Complexity statistics are computed from these point data and the keys are traceable to `data_proc/nested_cv_holdout_predictions.csv`. The inset resolves the low-concentration range where most mainstem samples fall. Extreme points are retained rather than trimmed. In this frozen run, 0 of 480 held-out rows activate the physical lower bound on S_sgs, so the residual closures are reported without a catch-and-clip post-processing step; a nonzero count here would instead be reported explicitly.](results/figures/nested_cv_scatter_holdout.png)

![Figure 5. Subgroup C_aq RMSE for the Baseline, Residual-AI (MLP and random forest), and k-correction. R008 contains 58 samples; the multi-sample tributary group R002–R005 contains 59 samples; R001, R006, and R007 are single-sample logical reaches and are shown separately rather than pooled into the comparison.](results/figures/subgroup_rmse_r008_vs_trib.png)


### 3.2 A corrected gas-transfer velocity does not improve concentration error

The k-correction does not improve on the Baseline. Its C_aq RMSE is 0.0485 mol m⁻³ against 0.0485 for the Baseline (Tables 2 and 3). The correction acts only through the transfer velocity, and 55% of the samples cannot be matched by any positive transfer velocity with S_sgs = 0, so the k-only target is undefined for most of the data; 66 of 120 full-data rows are infeasible and are excluded from training rather than floor-clipped, and none of the held-out predictions saturate at the imposed logarithmic lower bound (g = -12; 0/120 at the floor). The median effective velocity is 5.3733 m d⁻¹ against a median empirical velocity of 194.0016 m d⁻¹, so the median ratio k_eff/k_emp is 0.094 (Table 7). The earlier impression that a k-correction lowered concentration error arose from using a sample’s own observed concentration as its upstream boundary and from clipping the correction to a fixed lower bound; both artifacts are removed here.

That concentration error does not discriminate the k-correction from the Baseline motivates the model-free objective surface examined in Section 3.6.


### 3.3 The residual closures allocate the balance to unphysical extremes

The area-weighted model flux reveals markedly different process allocations among the closures. The Baseline releases 7.96×10² mol d⁻¹ as an overlapping sample-area diagnostic; the k-correction gives -2.06×10³ mol d⁻¹ by driving k_eff toward zero, while the Residual-AI closures inflate it to 3.26×10⁶ (MLP) and 1.64×10⁶ (random forest) mol d⁻¹ (Table 2). Because no independent evasion observations are available for this campaign, these values show only that the three allocations are mutually incompatible; they do not establish which is physically correct.

The implied-source diagnostic makes the compensation explicit. The mean implied adjustment S_implied is 2.6123 mol m⁻² d⁻¹ and the mean Residual-AI prediction is 5.7371 mol m⁻² d⁻¹, with a Spearman correlation of 0.7085 between the two (Table 7). A positive source term and a reduced transfer velocity act on the concentration balance in compensating directions, and the held-out concentration metric provides limited discrimination between them. Figure 6(c) shows the corresponding sample-level relation between k_eff/k_emp and the k-correction flux diagnostic.

![Figure 6. Model F_CO₂ diagnostics for the Baseline, Residual-AI (MLP), and k-correction under leave-one-reach-out grouped evaluation. (a) Area-weighted model flux diagnostic &Sigma;F&middot;A (mol d⁻¹), the same estimand as Table 2, so panel (a) and the table agree. (b) Per-reach composition of that diagnostic, showing that the Residual-AI total is concentrated in a small number of reaches. (c) Sample-level k_eff/k_emp versus the k-correction model flux diagnostic. These quantities are model diagnostics of the form k(C - C_eq) and are neither study-area totals nor independently validated evasion measurements; the un-area-weighted density sums behind panel (a) are retained in the supplementary tables.](results/figures/supp_flux_diagnostics.png)


### 3.4 Filter-scale residual on resolved coarsenings

On the resolved path-connected coarsenings (native through a sixteen-fold merge), unique-cell mean |S_sgs| stays in a narrow band around 3.54–3.84 mol m⁻² d⁻¹ over Deltax ≈ 587–1615 m (eight resolved scale levels; Table 6; Figure 7). Cell-level variance rises only slowly, from about 18.0 to 23.8. A study-reach whole-reach merge is excluded: preserving all cross-group fine edges yields a cyclic contracted DAG, so the reach assignment is not a verified DAG compression of the fine NHD graph and cannot support a formal scale-invariance claim through that aggregation. Within the resolved scales the near-stability of |S| under sparse synchronous coverage is a sampling-conditional sensitivity of the conserved operator, not a universal scaling law. The unique spatial cell count falls from 39 at native resolution to 22 at the coarsest resolved scale, and the diagnosed-cell fraction is below 1% at every scale, so the curve is a sensitivity of a small synchronous subset rather than a complete spatial budget.

![Figure 7. Filter-scale dependence of the diagnosed residual on resolved scales only (native through a sixteen-fold merge; study_reach excluded because whole-reach contraction creates a DAG cycle). Upper panel: unique-cell mean and median |S_sgs| versus filter scale Deltax on a log axis, with the actual mean and median control lengths marked. Lower panel: unique-cell variance of S_sgs with the median control length on a secondary axis. Unique-cell mean |S| stays in a narrow band near 3.54–3.84 mol m⁻² d⁻¹ across the eight resolved levels (Deltax ≈ 587–1615 m) under sparse synchronous coverage; this is a sampling-conditional sensitivity of the conserved operator, not a claim of scale-invariance through the study-reach aggregation.](results/figures/filter_scale_sgs.png)

![Figure 8. Distribution of |S_sgs| across resolved filter scales (native through a sixteen-fold merge) at the date×cell record level, with per-scale record counts printed above each group. Fliers are suppressed because all points are already shown in the accompanying scatter; multi-sample date-cell records are not independent draws, and repeated observations in one cell do not add area. Study-reach aggregation is excluded for the same contraction-cycle reason as Figure 7. The count of date×cell records (from 43 at native resolution to 27 at the coarsest resolved scale) differs from the count of unique spatial cells (39 to 22), because the same cell can be sampled on several dates.](results/figures/filter_scale_sgs_box.png)


### 3.5 A sparse dimensionless closure is compact but not predictive

The full-data LASSO refit on the dimensionless response retains 4 of the five candidate Pi terms (Table 8; Figure 9). With subscript z denoting predictors standardized to zero mean and unit variance, the closure is

> S* ≈ 1.386 − 4.777·Fr_z − 0.6142·Slope_z − 2.295·(h/W)_z − 2.75·log10(Da)_z

The retained coefficients are negative for Froude number, slope, relative depth, and the base-10 logarithm of the Damköhler number; only the Reynolds-number term shrinks to zero. Because this relation is a descriptive full-data summary (Section 2.8), it is not itself scored as a held-out law; the leave-one-reach R² for reconstructing the dimensionless response S* is -2.58334. Under the same leave-one-reach-out transport-coupled protocol, in which the scaler and LASSO are refitted within each fold, the sparse closure gives a held-out C_aq RMSE of 0.09387 mol m⁻³, above the Baseline value of 0.0485 (Table 9). This branch remains provisional: it is reported as a compact diagnostic description of the residual and does not recover predictive skill on held-out reaches.

![Figure 9. Standardized LASSO coefficients for the sparse dimensionless closure, fitted on fold-local targets (4 of five candidate Pi terms retained; only log_10(Re) shrinks to zero). Terms whose coefficient is numerically zero are drawn as explicit zero bars rather than omitted, so the reader can see which candidates were dropped and why. The displayed relation is S* ≈ 1.386 - 4.777·Fr_z - 0.6142·Slope_z - 2.295·(h/W)_z - 2.75·log10(Da)_z. Leave-one-reach R² for S* is -2.58334 (n=120); the sparse branch remains provisional.](results/figures/dimensionless_coefficients.png)


### 3.6 Model-free equifinality: objective surface and profile SSE

A model-free objective surface quantifies how weakly concentration data discriminate between a subgrid source and a gas-exchange correction (Figure 10). For a single sample, the objective J(k, S) = [C_obs - C_model(k, S)]² has an exact zero valley along S = S_diag + (C_obs - C_eq)(k - k_emp), so the per-sample profile SSE is identically flat and one concentration observation cannot identify (k, S) jointly. Pooling the 120 samples with a uniform k-scale α = k/k_emp and a uniform source S leaves the profile shallow: across the reported interval (rmse <= 1.10 * rmse_min over the alpha grid) the profile RMSE spans only 0.0343 to 0.0364 mol m⁻³, with the minimum at α = 0.1795 and S = 0.1214 mol m⁻² d⁻¹. These are equal-weight sample SSE diagnostics (not a likelihood or a confidence interval) with one shared k-scale and one shared source and the observed upstream state held fixed. Concentration data alone therefore weakly discriminate the two closures, in agreement with the grouped-evaluation result that the k-correction does not improve on the Baseline.

![Figure 10. Model-free practical-equifinality diagnostic from the quasi-steady balance (n=120). This is a conditional model diagnostic: the objective shares a single k-scale and a single source across samples and holds the observed upstream state fixed. (a) Single-sample objective log₁₀ J(k, S) for one representative sample; the crimson line marks the exact zero valley S = S_diag + (C_obs - C_eq)(k - k_emp), so a single concentration observation leaves (k, S) algebraically under-determined. (b) Pooled objective J(α, S) over a uniform k-scale α = k/k_emp and a uniform source S; the Baseline, k-correction, and Residual-AI points are descriptive median markers drawn for orientation, not fitted network operating points. (c) Profile SSE J_prof(α) = min_S J(α, S); the profile is shallow, with the minimum near α = 0.1795 (profile RMSE 0.0343 mol m⁻³).](results/figures/equifinality_objective_surface.png)


## 4. Discussion


### 4.1 Failed transfer of residual closures is a modelling diagnosis

Under fold-local targets the Residual-AI MLP does not lower pooled held-out concentration RMSE relative to a zero-residual Baseline, although it is better on the mainstem subgroup; the random forest is worse overall, and because source prediction is unbounded the residual learners extrapolate to unphysical sample-support fluxes on held-out reaches. That pattern separates apparent subgroup skill from settled predictive success. In the evaluation logic of Bennett et al. (2013) and Vilas et al. (2023), the discrepancy is itself diagnostic: it separates apparent learnability from held-out usefulness. The subgroup evidence points to where the transfer fails. Errors increase most clearly in the pooled multi-sample tributaries R002–R005, whereas the mainstem reach, with 58 samples, is one subgroup where the residual closure remains competitive with the Baseline; the pooled contrast is, however, dominated by three R002 samples that account for 0.833 of the gross positive error reduction rather than by a broad improvement. These results support reporting reach-level diagnostics alongside pooled metrics, particularly when sampling support is strongly imbalanced, and they show that a flexible residual learner is not sufficient for a stable closure: the target must be bounded or regularized against out-of-sample extrapolation.

The failure of residual closures to transfer does not imply that concentration error uniquely favors the Baseline; the model-free objective surface (Figure 10) shows instead that concentration data discriminate only weakly between a source allocation and a gas-exchange allocation.


### 4.2 Process allocation and practical equifinality

The k-correction cannot match most of the data with a single positive transfer velocity: 55% of the samples have no positive k_need under S_sgs = 0, and the retained predictions shrink far below the empirical velocity, so the correction does not improve on the Baseline. This sharpens the earlier result: the apparent superiority of a k-correction was an artifact of boundary leakage and clipping, and once both are removed the k-only closure is partly undefined rather than merely ineffective. Because S_sgs and k(C - C_eq) enter the same balance with opposing signs, a source allocation and a reduced transfer velocity act in compensating directions, and the held-out concentration metric provides limited discrimination between them.

Here, practical equifinality refers to the compensation between S_sgs and k, now quantified model-free. The objective surface (Figure 10) shows an exact zero valley for a single sample and a shallow pooled profile, so the concentration data alone constrain only weakly how discrepancy is allocated between a subgrid source and gas exchange. The single-sample result is an algebraic under-determination of one equation with fixed C_in and two unknowns; the pooled result is an equal-weight 120-sample SSE profile with a shared k-scale and a shared source. Neither is a profile likelihood, a confidence interval, or a network-rerouting experiment, and the markers drawn for orientation on the pooled plane are descriptive medians rather than fitted operating points. This does not constitute a formal structural-identifiability analysis, and the unstable out-of-sample fluxes of the MLP and random forest are themselves not equifinality evidence; they show that closure choice matters and that flexible residual learning did not yield a settled predictive success here. Within those boundaries, the results suggest that concentration-dominated evaluation does not uniquely constrain how discrepancy is allocated between S_sgs and k in this configuration.

This process-allocation ambiguity concerns the closure form; the filtering experiment addresses a related but distinct source of variability in the diagnosed residual.


### 4.3 What filtering and sparse representation reveal about the residual

On resolved filter scales only, unique-cell mean |S_sgs| stays in a narrow band around 3.54–3.84 mol m⁻² d⁻¹ from native NHDPlus HR resolution through a sixteen-fold merge. Study-reach aggregation is excluded after an unresolved contraction cycle, so the manuscript does not claim scale-invariance through that coarser operator. Within the resolved range the result is a sampling-conditional sensitivity under sparse synchronous coverage, bounded by the implemented flow-directed operator (Yuval & O’Gorman, 2020, analogy limited to spatial filtering).

The sparse closure retains 4 terms (Fr, slope, h/W, and log_10(Da), all negative), but its compact form does not improve held-out prediction: RMSE remains above the Baseline and the S* reconstruction fails under reach holdout (R² = -2.58334). Compact forms are therefore not automatically validated or predictive, and the branch remains provisional. Under the present protocol, the tested sparse Pi-group representation does not provide cross-reach predictive utility; it remains useful as a diagnostic simplification.


### 4.4 Implications for environmental-model evaluation

These findings suggest that concentration RMSE should be interpreted together with diagnostics of gas exchange and unresolved source allocation. When observations constrain only concentration, lower RMSE should be interpreted alongside diagnostics of the process terms that produced it.

The present conclusions are bounded by strongly unequal reach support, the hydraulic-geometry representation of channel width and depth, incomplete covariates (alkalinity, nitrogen, phosphorus, photosynthetically active radiation), and the absence of independent evasion measurements. The Water Quality Portal merge and the StreamPULSE search returned no usable additional constraints for this campaign. These limitations restrict inference to the East River experiment, and they also identify the observations that would most help to discriminate closures: more balanced reach sampling, better-resolved channel geometry, and independent constraints on gas exchange. The central implication is that lower concentration error alone is insufficient to determine which allocation of unresolved processes is better supported.


## 5. Conclusions

Under leave-one-reach-out transport-coupled evaluation with fold-local residual targets, the Residual-AI multilayer perceptron does not lower pooled held-out C_aq RMSE relative to the Baseline (0.0507 against 0.0485 mol m⁻³); it is better on the mainstem subgroup and worse on the multi-sample tributaries, and the pooled contrast rests on a few R002 samples, so the apparent concentration gain is not treated as a settled success claim. Sample-support flux diagnostics remain unstable. A k-correction does not improve on the Baseline (0.0485 mol m⁻³) because 55% of the samples have no positive k-only solution. A model-free objective surface and profile SSE indicate that concentration data alone constrain only weakly how discrepancy is allocated between the source term S_sgs and the transfer velocity k. Formal filter claims use only resolved coarsenings; study_reach is excluded.

The framework combines an explicit spatial filter, transport-coupled grouped evaluation, and a model-free objective-surface diagnostic. Within the East River experiment, the framework provides a diagnostic comparison of alternative closure allocations; the flux values remain model diagnostics, and transfer to other basins has not been tested. The results therefore support transport-coupled, process-aware evaluation of alternative closure allocations when concentration is the primary observational constraint.


## 6. Data availability

The East River water-chemistry and pCO₂ data are publicly available through HydroShare (resource 9f907b46baa848e180c49339d605bf31; Saccardi & Winnick, 2021). The DIC supplement, network shapefiles, and hydraulic tables are in HydroShare resource 2a2132999fb84214aad0596783812db2. Mainstem discharge is from USGS gage 09112500. River-network geometry uses NHDPlus HR flowlines for HUC 14020001. Processed tables, figures, and the analysis code are maintained in the public repository (https://github.com/Coucou2016/river-carbon-transport); a version-specific release or immutable commit should be cited alongside the mutable repository state at submission.

## Tables

**Table 1.** East River study network: eight logical reaches and four distinct count estimands (logical reporting / confluence-chainage simplified tree, not a verified NHD directed compression). **Assigned corridor lines** = rows of `gis_reach_line_mapping.csv` (NHDPlus HR flowlines attributed to a reach, including `nearest_campaign_sample` assignments). **Logical routing segments** = routing nodes of `network_segments.csv` (7 tributary nodes + 6 mainstem nodes); these are not flowlines. **Sampled control volumes** = unique sample-support cells (`physical_cell_id`); these are not flowlines. **Raw corridor flowlines** = the 393 features of `East_River_Lines.shp`, of which 0 are unassigned; all assigned lines are therefore a subset of the raw corridor pool. The legacy GNIS-only tally and the uncertified legacy reported channel-length field are removed; the domain length is the fixed control-volume length from `length_conservation.csv`. A dagger (†) marks a reach whose recorded support has not passed the domain-consistency gate, so its domain length must not be used to reconstruct area.

| Reach | Stream name | Role | Joins mainstem | Domain length (km) | Assigned corridor lines | ·GNIS match | ·Nearest sample | Logical routing segments | Sampled control volumes | Campaign samples | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R001 | Bradley Creek | Tributary | R008_S4 | 0.100 † | 0 | 0 | 0 | 1 | 1 | 1 | Tributary headwater; n = 1, schematic only |
| R002 | Bradley Meadow | Tributary | R008_S4 | 0.092 † | 15 | 0 | 15 | 1 | 3 | 3 | Meadow reach connecting Bradley and Rock Creeks |
| R003 | Rock Creek | Tributary | R008_S5 | 4.145 | 29 | 10 | 19 | 1 | 15 | 15 | Rock Creek; multi-sample tributary |
| R004 | Copper Creek | Tributary | R008_S6 | 3.568 | 140 | 23 | 117 | 1 | 24 | 24 | Copper Creek; largest assigned corridor |
| R005 | Gothic Creek | Tributary | R008_S5 | 2.504 † | 6 | 0 | 6 | 1 | 17 | 17 | Gothic Creek; multi-sample tributary |
| R006 | Quigley Creek | Tributary | R008_S2 | 0.069 † | 8 | 6 | 2 | 1 | 1 | 1 | Single sample; schematic only |
| R007 | Rustlers Gulch | Tributary | R008_S3 | 0.050 † | 2 | 0 | 2 | 1 | 1 | 1 | Single sample; schematic only |
| R008 | East River | Mainstem | outlet | 11.313 | 193 | 46 | 147 | 6 | 58 | 58 | Mainstem above Almont; densest sampling |
| Total | 8 logical reaches | — | — | — | 393 | 85 | 308 | 13 | 120 | 120 | — |

**Table 2.** Main results under leave-one-reach-out grouped cross-validation with transport coupling (flux totals are model diagnostics).

| Scheme / model | C RMSE | F total | k_eff/k_emp | Beats Baseline (C)? |
|---|---|---|---|---|
| Baseline | 0.0485 | 7.96×10² | 1.000 | — |
| k-correction / XGBoost | 0.0485 | -2.06×10³ | 0.094 | Yes |
| Residual-AI / MLP | 0.0507 | 3.26×10⁶ | 1.000 | No |
| Residual-AI / random forest | 0.0557 | 1.64×10⁶ | 1.000 | No |
| Sparse-Π / LASSO | 0.0939 | 4.72×10⁶ | — | No |

**Table 3.** Leave-one-reach-out grouped cross-validation: held-out C_aq and F_CO2 (primary metrics; F values are model flux diagnostics).

| Scheme / model | C RMSE | C MAE | C Bias | C R2 | F RMSE | F Bias | F total | n |
|---|---|---|---|---|---|---|---|---|
| Baseline | 0.0485 | 0.0235 | -0.0235 | -0.302 | 5.234 | -3.205 | 7.96×10² | 120 |
| k-correction / XGBoost | 0.0485 | 0.0235 | -0.0235 | -0.301 | 5.225 | -3.206 | -2.06×10³ | 120 |
| Residual-AI / MLP | 0.0507 | 0.0305 | 0.0241 | -0.423 | 4.441 | 1.618 | 3.26×10⁶ | 120 |
| Residual-AI / random forest | 0.0557 | 0.0309 | 0.0203 | -0.715 | 3.435 | 0.640 | 1.64×10⁶ | 120 |

**Table 4.** In-sample concentration metrics are not reported. After recalculation the paper metric is exclusively leave-one-reach-out transport-coupled C_aq.


**Table 5.** Subgroup metrics under leave-one-reach-out grouped cross-validation.

| Scheme | Subgroup | Evidence weight | C RMSE | C R2 | n |
|---|---|---|---|---|---|
| Baseline | All 120 samples | all | 0.0485 | -0.302 | 120 |
| Baseline | R008 East River mainstem | mainstem | 0.0278 | -0.746 | 58 |
| Baseline | Multi-sample tribs R002-R005 | tributary | 0.0634 | -0.267 | 59 |
| Baseline | One-sample reaches (schematic) R001/R006/R007 | schematic | 0.0071 | — | 3 |
| k-correction | All 120 samples | all | 0.0485 | -0.301 | 120 |
| k-correction | R008 East River mainstem | mainstem | 0.0279 | -0.754 | 58 |
| k-correction | Multi-sample tribs R002-R005 | tributary | 0.0634 | -0.264 | 59 |
| k-correction | One-sample reaches (schematic) R001/R006/R007 | schematic | 0.0071 | — | 3 |
| Residual-AI | All 120 samples | all | 0.0507 | -0.423 | 120 |
| Residual-AI | R008 East River mainstem | mainstem | 0.0233 | -0.231 | 58 |
| Residual-AI | Multi-sample tribs R002-R005 | tributary | 0.0685 | -0.478 | 59 |
| Residual-AI | One-sample reaches (schematic) R001/R006/R007 | schematic | 0.0055 | — | 3 |

**Table 6.** Filter-scale experiment: S_sgs diagnosed at the independent-cell level after snapping the 120 samples onto flow-directed coarsened NHDPlus HR networks.

| Scale | Δx (m) | Cells | Sampled cells | Samples | Cell-mean \|S_sgs\| | Cell Var(S_sgs) |
|---|---|---|---|---|---|---|
| Native NHDPlus HR | 587 | 536 | 39 | 120 | 3.541 | 18.015 |
| ~2× merge | 764 | 502 | 32 | 120 | 3.311 | 17.494 |
| ~3× merge | 873 | 493 | 29 | 120 | 3.450 | 18.773 |
| ~4× merge | 1010 | 486 | 27 | 120 | 3.573 | 19.831 |
| ~6× merge | 1208 | 481 | 25 | 120 | 3.669 | 21.237 |
| ~8× merge | 1259 | 479 | 24 | 120 | 3.738 | 21.864 |
| ~12× merge | 1373 | 477 | 22 | 120 | 3.862 | 23.774 |
| ~16× merge | 1615 | 476 | 22 | 120 | 3.841 | 23.783 |

**Table 7.** Practical-equifinality diagnostic: k and source-term compensation under the grouped protocol.

| Scheme | C RMSE | F total | Median k | k_eff/k_emp |
|---|---|---|---|---|
| Baseline | 0.0485 | 7.96×10² | 194.0 | 1.000 |
| Residual-AI | 0.0507 | 3.26×10⁶ | 194.0 | 1.000 |
| k-correction | 0.0485 | -2.06×10³ | 5.4 | 0.094 |

**Table 8.** Sparse dimensionless closure (Pi-group LASSO).

| Item | Result |
|---|---|
| Standardized-predictor form | S* ≈ 1.386 − 4.777·Fr_z − 0.6142·Slope_z − 2.295·(h/W)_z − 2.75·log10(Da)_z |
| Original-variable form | S_sgs* ≈ 25.99 − 129.5·Fr − 14.28·Slope − 175.8·h/W − 6.284·log10(Da) |
| Dominant terms | − 4.78·Fr_z − 2.75·log10(Da)_z − 2.29·(h/W)_z |
| Leave-one-reach R2 for reconstructing S* | -2.583 (negative = does not generalize) |

**Table 9.** Sparse dimensionless closure inserted into transport under grouped cross-validation (compare Baseline 0.0485 in Table 3).

| Scheme | C RMSE | C R2 | F RMSE | n |
|---|---|---|---|---|
| Sparse-Π / LASSO (leave-one-reach) | 0.0939 | -3.877 | 8.473 | 120 |

## References

1. Battin, T. J., et al. (2023). River ecosystem metabolism and carbon biogeochemistry in a changing world. Nature, 614, 676–687. https://doi.org/10.1038/s41586-022-05500-8
2. Bennett, N. D., et al. (2013). Characterising performance of environmental models. Environmental Modelling & Software, 40, 1–20. https://doi.org/10.1016/j.envsoft.2012.09.011
3. Gao, Y., et al. AI cross-fusion approach for river carbon transport. The Innovation (manuscript in preparation; DOI to be added).
4. Gómez-Gener, L., Rocher-Ros, G., et al. (2021). Global carbon dioxide efflux from rivers enhanced by high nocturnal emissions. Nature Geoscience, 14, 647–653. https://doi.org/10.1038/s41561-021-00722-3
5. Hotchkiss, E. R., et al. (2015). Sources of and processes controlling CO₂ emissions change with the size of streams and rivers. Nature Geoscience, 8, 696–699. https://doi.org/10.1038/ngeo2507
6. Markovich, K. H., White, J. T., & Knowling, M. J. (2022). Sequential and batch data assimilation approaches to cope with groundwater model error: An empirical evaluation. Environmental Modelling & Software, 156, 105498. https://doi.org/10.1016/j.envsoft.2022.105498
7. Raymond, P. A., et al. (2012). Scaling the gas transfer velocity and hydraulic geometry in streams and small rivers. Limnology and Oceanography: Fluids and Environments, 2, 41–53. https://doi.org/10.1215/21573689-1597669
8. Saccardi, B., & Winnick, M. J. (2021). Improving predictions of stream CO₂ concentrations and fluxes using a stream network model: A case study in the East River Watershed, CO, USA. Global Biogeochemical Cycles, 35, e2021GB006972. https://doi.org/10.1029/2021GB006972
9. Vilas, M. P., et al. (2023). TALKS: A systematic framework for resolving model-data discrepancies. Environmental Modelling & Software, 163, 105668. https://doi.org/10.1016/j.envsoft.2023.105668
10. Xie, X., Samaei, A., Guo, J., Liu, W. K., & Gan, Z. (2022). Data-driven discovery of dimensionless numbers and governing laws from scarce measurements. Nature Communications, 13, 7562. https://doi.org/10.1038/s41467-022-35084-w
11. Yuval, J., & O’Gorman, P. A. (2020). Stable machine-learning parameterization of subgrid processes for climate modeling at a range of resolutions. Nature Communications, 11, 3295. https://doi.org/10.1038/s41467-020-17142-3
