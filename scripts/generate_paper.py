# -*- coding: utf-8 -*-
"""Generate self-contained paper.html and paper.md (submission-style English manuscript).

Writing-and-organization revision only. All science, numbers, results, and conclusions
are frozen against results/tables/*.csv (see results/tables/paper_claim_guard.json and
docs/RESEARCH_INTEGRITY_AUDIT.md). Style follows the AGU/WRR article pattern: front
matter with Key Points and Plain Language Summary, one continuous argument per section,
evidence-led Results, no internal-review scaffolding, no glossary in the paper.

Tables are rendered by the existing repository helpers (paper_main_table_html,
nested_cv_tables_html, innovation_tables_html from generate_report.py, and
REACH_NETWORK_TABLE_HTML from report_content.py) and cleaned for manuscript use by
sanitize_paper_tables(). Figures are base64-embedded; no CDN, no external assets.
"""
from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_report import (  # noqa: E402
    innovation_tables_html,
    nested_cv_tables_html,
    paper_main_table_html,
)
from report_content import REACH_NETWORK_TABLE_HTML  # noqa: E402

FIG_DIR = ROOT / "results" / "figures"
OUT_HTML = ROOT / "paper.html"
OUT_MD = ROOT / "paper.md"

# ---------------------------------------------------------------------------
# Front matter
# ---------------------------------------------------------------------------

EN_TITLE = (
    "Transport-coupled evaluation of river-network CO\u2082 closures: "
    "Evidence for practical equifinality under concentration-only observations"
)
ZH_TITLE = "河网 CO\u2082 闭合的输运耦合评价：浓度单变量观测下的 practical equifinality 证据"

KEY_POINTS = [
    "A spatial filter turns the reach-scale CO\u2082 balance into a diagnosable subgrid residual term.",
    "The implemented residual learners do not beat the zero-residual Baseline under reach-grouped evaluation.",
    "Lower concentration error coincides with collapse of the model-derived CO\u2082 flux diagnostic.",
]

PLAIN_LANGUAGE_SUMMARY = (
    "Rivers take up, transform, and release carbon, and models of river carbon must represent "
    "processes that cannot be observed directly, such as groundwater CO\u2082 inputs and the exchange "
    "of gas with the atmosphere. When only concentration measurements are available, different model "
    "structures can reproduce the same observed concentrations by adjusting different process terms. "
    "Using 120 public water samples from the East River in Colorado, we compared a baseline transport "
    "model with variants that add a machine-learned source term or a corrected gas-exchange rate. The "
    "machine-learned term did not improve predictions for river reaches that were held out of training. "
    "The corrected gas-exchange variant fitted the concentrations slightly better but sharply "
    "reduced the model-derived CO\u2082 flux diagnostic. In this East River experiment, concentration data alone "
    "provided limited discrimination between alternative allocations of model discrepancy. Evaluations "
    "of river-carbon models should combine concentration skill with process-level diagnostics."
)

ABSTRACT = (
    "River-network carbon models combine downstream transport, unresolved source and sink processes, "
    "and air-water gas exchange, but concentration-based evaluation may not distinguish errors "
    "assigned to different terms in the same mass balance. Existing process-based models provide a "
     "basis for predicting stream CO\u2082, yet the consequences of alternative unresolved-process closures "
    "under held-out evaluation remain unclear. We developed a transport-coupled diagnostic framework "
    "for 120 public East River observations organized into eight logical reaches. Spatial "
    "coarse-graining defines a residual source-sink term (S_sgs), which was represented by a "
    "zero-residual Baseline, machine-learned residual closures (Residual-AI), or a multiplicative "
    "correction to empirical gas-transfer velocity. Each closure was evaluated by leaving one reach "
    "out and reinserting the predicted closure into the quasi-steady transport balance before scoring "
    "concentration under partially observed upstream boundary conditioning. For the implemented "
    "Residual-AI target, the C_aq root-mean-square error (RMSE) was 0.0573 mol m\u207b\u00b3 for "
    "the multilayer perceptron (MLP) and 0.0745 mol m\u207b\u00b3 for the random forest, compared with "
    "0.0284 for the Baseline; because this training target is not dimensionally identical to the "
    "diagnosed residual, the negative result applies to the tested target formulation rather than to "
    "residual closure learning in general. The k-correction reduced RMSE to 0.0244, but the median "
    "effective-to-empirical transfer-velocity ratio, k_eff/k_emp, was 3.35e-4 and the "
    "sample-summed model flux diagnostic decreased from 3.24 to 0.031 mol m\u207b\u00b2 d\u207b\u00b9. A sparse closure "
    "gave RMSE 0.0506. Mean |S_sgs| decreased from 1.916 to 1.000 as filter width increased from about "
    "838 m to the study-reach scale. These results indicate practical equifinality between S_sgs and "
    "k under concentration-only East River observations, so lower concentration error alone is "
    "insufficient to identify how model discrepancy is allocated between unresolved sources and gas "
    "exchange."
)

KEYWORDS = (
    "river carbon cycling; environmental model evaluation; subgrid closure; gas-transfer velocity; "
    "grouped cross-validation; practical equifinality"
)

# ---------------------------------------------------------------------------
# Equations (frozen; identical to previous manuscript versions)
# ---------------------------------------------------------------------------

# number -> (html, plain); numbered sequentially in order of appearance
EQUATIONS: dict[int, tuple[str, str]] = {
    1: (
        "Q(C<sub>in</sub> \u2212 C) + (A<sub>s</sub>/\u03c4<sub>d</sub>)[S<sub>sgs</sub> \u2212 k(C \u2212 C<sub>eq</sub>)] = 0",
        "Q(C_in - C) + (A_s/tau_d)[S_sgs - k(C - C_eq)] = 0",
    ),
    2: (
        "q<sub>A</sub>(C<sub>in</sub> \u2212 C) + S<sub>sgs</sub> \u2212 k(C \u2212 C<sub>eq</sub>) = 0",
        "q_A(C_in - C) + S_sgs - k(C - C_eq) = 0",
    ),
    3: ("F<sub>CO\u2082</sub> = k(C \u2212 C<sub>eq</sub>)", "F_CO2 = k(C - C_eq)"),
    4: (
        "S<sub>sgs</sub> = k(C \u2212 C<sub>eq</sub>) \u2212 q<sub>A</sub>(C<sub>in</sub> \u2212 C)",
        "S_sgs = k(C - C_eq) - q_A(C_in - C)",
    ),
    5: (
        "S<sub>implied</sub> = (k<sub>emp</sub> \u2212 k<sub>eff</sub>)(C \u2212 C<sub>eq</sub>)",
        "S_implied = (k_emp - k_eff)(C - C_eq)",
    ),
}

K600_EQ = (
    "ln k<sub>600</sub> = 5.139 + 0.594 ln u + 0.403 ln slope,&nbsp;&nbsp;&nbsp;"
    "k<sub>emp</sub> = k<sub>600</sub>(Sc/600)<sup>\u22120.5</sup>",
    "ln k600 = 5.139 + 0.594 ln u + 0.403 ln slope;  k_emp = k600 (Sc/600)^-0.5",
)

SPARSE_EQ = (
    "S* \u2248 1.059 + 1.536\u00b7Fr<sub>z</sub> \u2212 1.669\u00b7Slope<sub>z</sub> \u2212 2.179\u00b7(h/W)<sub>z</sub>",
    "S* ~= 1.059 + 1.536*Fr_z - 1.669*Slope_z - 2.179*(h/W)_z",
)

# ---------------------------------------------------------------------------
# Figures (11 files after merging Figs 2a/2b and combining S2/S3; captions in journal style)
# ---------------------------------------------------------------------------

FIG_CAPTIONS: dict[str, str] = {
    "les_filter_conceptual.png": (
        "<strong>Figure 1.</strong> Conceptual representation of spatial coarse-graining of the river "
        "CO\u2082 balance. Left: native NHDPlus HR segments and sample locations within short control "
        "volumes. Right: merged filter cells at larger \u0394x, for which unresolved contributions to "
        "the filtered mass balance are represented by S<sub>sgs</sub>."
    ),
    "figure2_reach_assignment_and_samples.png": (
        "<strong>Figure 2.</strong> (a) Logical reach assignment on the NHDPlus HR network: segments "
        "were assigned to the logical study-reach labels by GNIS name matching and proximity to "
        "campaign coordinates; colors indicate reach assignment, and the single-sample reach R001 "
        "receives no assigned segment in this rendering. (b) Locations of the 120 campaign samples; "
        "point colors denote logical reaches R001\u2013R008 and R008 contains 58 samples. The "
        "background provides spatial context only and is not used in the assignment."
    ),
    "nested_cv_rmse_bar.png": (
        "<strong>Figure 3.</strong> Leave-one-reach-out grouped cross-validation with transport "
        "coupling (n=120): held-out C<sub>aq</sub> RMSE for the Baseline, Residual-AI (MLP and random "
        "forest), and k-correction closures (primary comparison)."
    ),
    "nested_cv_scatter_holdout.png": (
        "<strong>Figure 4.</strong> Observed versus transport-predicted held-out C<sub>aq</sub> for the "
        "Residual-AI (MLP) closure under leave-one-reach-out grouped evaluation (n=120). Colors denote "
        "logical reaches; the dashed line indicates 1:1 agreement."
    ),
    "identifiability_k_vs_sgs.png": (
        "<strong>Figure 5.</strong> Closure-compensation diagnostics under leave-one-reach-out grouped "
        "evaluation (n=120). (a) Implied source adjustment S<sub>implied</sub> versus the effective "
        "gas-transfer velocity k<sub>eff</sub> for the k-correction. (b) S<sub>implied</sub> versus the "
        "Residual-AI held-out source prediction; the dashed line indicates 1:1 agreement and the "
        "annotated Spearman \u03c1 is \u22120.57."
    ),
    "filter_scale_sgs.png": (
        "<strong>Figure 6.</strong> Filter-scale dependence of the diagnosed residual for the 120 "
        "sample records. Left: mean |S<sub>sgs</sub>|. Right: variance of S<sub>sgs</sub>. Filter "
        "width \u0394x is the mean length of sampled filter cells; the coarsest study-reach scale "
        "contains six sampled cells."
    ),
    "dimensionless_coefficients.png": (
        "<strong>Figure 7.</strong> Standardized LASSO coefficients for the sparse dimensionless "
        "closure. Nonzero coefficients are retained for Fr<sub>z</sub>, Slope<sub>z</sub>, and "
        "(h/W)<sub>z</sub>; the displayed relation is S* \u2248 1.059 + 1.536 Fr<sub>z</sub> \u2212 "
        "1.669 Slope<sub>z</sub> \u2212 2.179 (h/W)<sub>z</sub>. Leave-one-reach R\u00b2 for S* is "
        "\u22122.743 (n=120)."
    ),
    "subgroup_rmse_r008_vs_trib.png": (
        "<strong>Figure S1.</strong> Subgroup C<sub>aq</sub> RMSE for the Baseline, Residual-AI (MLP), "
        "and k-correction. R008 contains 58 samples; the multi-sample tributary group R002\u2013R005 "
        "contains 59 samples; R001, R006, and R007 are single-sample logical reaches."
    ),
    "supp_flux_diagnostics.png": (
        "<strong>Figure S2.</strong> Model F<sub>CO\u2082</sub> diagnostics for the Baseline, "
        "Residual-AI (MLP), and k-correction under leave-one-reach-out grouped evaluation (n=120). "
        "(a) Sample-summed model flux diagnostic. (b) Flux-diagnostic RMSE relative to the empirical "
        "comparison proxy. (c) Sample-level k<sub>eff</sub>/k<sub>emp</sub> versus the k-correction "
        "model flux diagnostic. These quantities are model diagnostics and are not independently "
        "validated evasion measurements."
    ),
    "filter_scale_sgs_box.png": (
        "<strong>Figure S3.</strong> Distribution of |S<sub>sgs</sub>| across the 120 sample records "
        "at each implemented filter scale. Boxes summarize the distributions and individual points "
        "show sample-level values; the final category is the study-reach scale."
    ),
    "obs_vs_model_scatter_large.png": (
        "<strong>Figure A1.</strong> In-sample observed versus predicted C<sub>aq</sub> for the "
        "Baseline and Residual-AI (MLP) using the same 120 observations for fitting and evaluation. "
        "Circles denote the Baseline and triangles denote Residual-AI. The in-sample R\u00b2 \u2248 "
        "0.997 is reported only as an overfitting diagnostic and is not a held-out skill metric."
    ),
}

FIG_ORDER = [
    "les_filter_conceptual.png",
    "figure2_reach_assignment_and_samples.png",
    "nested_cv_rmse_bar.png",
    "nested_cv_scatter_holdout.png",
    "identifiability_k_vs_sgs.png",
    "filter_scale_sgs.png",
    "dimensionless_coefficients.png",
    "subgroup_rmse_r008_vs_trib.png",
    "supp_flux_diagnostics.png",
    "filter_scale_sgs_box.png",
    "obs_vs_model_scatter_large.png",
]

# ---------------------------------------------------------------------------
# Manuscript content (block list shared by the HTML and Markdown renderers)
# Block kinds: h2, h3, p, eq(number), eqline((html, plain)), fig(filename),
# raw("REACH_TABLE" | "NESTED_TABLES" | "INNOVATION_TABLES").
# ---------------------------------------------------------------------------

CONTENT: list[tuple] = [
    ("h2", "1. Introduction"),
    ("p",
     "Rivers link terrestrial, aquatic, and atmospheric carbon cycling by transporting dissolved carbon, "
     "transforming it through biological and biogeochemical processes, and exchanging CO\u2082 with the "
     "atmosphere. Riverine CO\u2082 evasion is a substantial component of inland-water carbon budgets, "
     "but both the magnitude and dominant controls of that flux vary across river networks and over time "
     "(Hotchkiss et al., 2015; G\u00f3mez-Gener et al., 2021; Battin et al., 2023). Predictive models "
     "must therefore represent several processes that operate simultaneously: downstream advection, "
     "lateral and internal carbon inputs, in-stream transformation, and air-water gas exchange. At the "
     "reach scale, however, observations and model states average over spatial heterogeneity that may "
     "occur over much shorter distances. A reach-scale model can consequently reproduce concentration "
     "while compensating for unresolved source or sink processes through another term in the mass "
     "balance. This possibility matters whenever model performance is judged mainly from concentration "
     "observations."),
    ("p",
     "The East River watershed provides a useful setting in which to examine this problem because a "
     "process-based stream-network CO\u2082 model has already been developed for the system. Saccardi "
     "and Winnick (2021) represented downstream transport together with CO\u2082 sources and atmospheric "
     "exchange to predict spatial variation in stream CO\u2082 concentrations and fluxes. Their work "
     "illustrates how several process terms jointly determine the same downstream concentration state. "
     "Gas exchange is commonly represented through an empirical transfer velocity, and Raymond et al. "
     "(2012) related gas-transfer velocity to hydraulic properties of streams and small rivers. Such "
     "parameterizations make gas exchange operational at network scale, but they do not remove "
     "uncertainty in the other terms of the carbon balance. Groundwater inputs, lateral inflows, "
     "metabolic heterogeneity, and other sub-reach processes may remain incompletely observed or "
     "resolved. Errors in these processes and errors in gas exchange can therefore enter the same "
     "concentration equation and potentially offset one another."),
    ("p",
     "This compensation complicates model evaluation because different process allocations can "
     "produce similar concentration responses. Bennett et al. (2013) argued that environmental-model "
     "performance should be "
     "characterized using evidence appropriate to model purpose rather than a single goodness-of-fit "
     "statistic. Vilas et al. (2023) likewise treated model-data discrepancy as information that may "
     "arise from the model, the observations, or their interaction, while Markovich et al. (2022) "
     "evaluated alternative methods explicitly in the presence of model error. For river-carbon "
     "transport, these considerations imply that a lower concentration error is not necessarily "
     "sufficient to identify which process representation is better supported. If an unresolved "
     "source-sink correction and the gas-transfer velocity can both alter the same predicted "
     "concentration, optimizing either term may reduce residual error. The relevant test is whether "
     "their effects remain distinguishable when each candidate closure is coupled back to the transport "
     "model and evaluated under reach-grouped transport coupling, subject to the boundary-conditioning "
     "and target-construction limitations described below."),
    ("p",
     "Machine learning provides one possible representation of unresolved process terms. In climate "
     "modeling, for example, spatial coarse-graining has been used to define unresolved tendencies and "
     "to train data-driven subgrid parameterizations, including models tested across resolutions (Yuval "
     "&amp; O\u2019Gorman, 2020). Related work on data-driven closure of river-carbon transport is also "
     "in preparation (Gao et al., manuscript in preparation). The central difficulty is not whether a "
     "flexible model can fit a diagnosed residual in the data used for training, but whether that "
     "residual representation remains useful after transfer to a new spatial group and reinsertion into "
     "the governing balance. A residual may encode repeatable unresolved dynamics, but it may also "
     "absorb errors in hydraulic representation, boundary conditions, observations, or other model "
     "components. Strong in-sample fit therefore provides limited evidence for a closure unless its "
     "effect is evaluated through the coupled model under held-out conditions."),
    ("p",
     "Here we examine that question using 120 public East River campaign observations organized into "
     "eight logical reaches and mapped to a National Hydrography Dataset Plus High Resolution "
    "(NHDPlus HR) representation. We spatially coarse-grain the "
     "reach-scale mass balance to diagnose a residual source-sink term, S<sub>sgs</sub>, and compare "
     "three closure strategies: a zero-residual Baseline, machine-learned residual closures, and a "
     "multiplicative correction to the empirical gas-transfer velocity. Evaluation is grouped by reach "
     "and transport-coupled, so the closure predicted for a held-out reach is reinserted into the "
     "quasi-steady mass balance before C<sub>aq</sub> is scored. We also examine how the diagnosed "
     "residual changes with filter scale and whether a sparse dimensionless representation retains "
     "held-out predictive value. Several boundaries constrain the interpretation. Upstream concentration is "
     "partially observed because the solver uses observed C<sub>aq</sub> as a fallback when an upstream "
     "state is unavailable, reach support is strongly unequal, channel geometry is idealized, and the "
     "spatial ordering includes a coordinate-based fallback rather than a complete directed network "
     "topology. Within these constraints, the test is whether concentration-only observations can "
     "distinguish discrepancy assigned to S<sub>sgs</sub> from discrepancy assigned to k when both "
     "closures are evaluated through the same transport calculation."),

    ("h2", "2. Methods"),

    ("h3", "2.1 Study data and river-network representation"),
    ("p",
     "The study uses public observations from the upper East River watershed near Almont, Colorado "
     "(hydrologic unit code (HUC) 14020001). The water-chemistry data come from the field campaign of "
     "Saccardi and Winnick "
     "(2021), which comprises 120 samples collected between 2 and 11 August 2019. Samples are assigned "
     "to eight logical reaches, R001 through R008, with counts of 1, 3, 15, 24, 17, 1, 1, and 58, "
     "respectively (Table 1). Three reaches (R001, R006, R007) contain a single sample and are treated "
     "as schematic: they enter the network bookkeeping but do not carry the same evidence weight as the "
     "mainstem reach R008. The logical reaches form a fixed upstream-to-downstream chain that provides "
     "reproducible control volumes for the closure experiment. They are not intended to replace the full "
     "directed NHDPlus topology."),
    ("p",
     "The river-network representation combines three public sources. The HydroShare supplement of "
     "Saccardi and Winnick (2021) provides 393 NHD centerline segments for the study corridor. An "
     "extract of the NHDPlus HR product for HUC 14020001 contributes 8212 flowlines used for "
     "corridor-level filtering. Reach-to-line matching identified 85 segments through Geographic Names "
     "Information System (GNIS) name matching "
     "and assigned the remainder by proximity to campaign coordinates; the median sample-to-centerline "
     "snap distance is 8.5 m. Discharge for the mainstem reach comes from USGS gage 09112500 (East "
     "River at Almont) on the sample dates. Tributary discharges are the published synoptic values from "
     "the campaign supplement, with no gage-ratio scaling applied."),
    ("p",
     "Channel width is not measured along the corridor. For reaches containing at least two samples, "
     "the width proxy is the longitudinal sample-coordinate span converted to metres and divided by "
     "the number of samples, then clipped to 2\u201315 m; single-sample reaches are assigned "
     "W = 5 m. Water depth is estimated from the wide-channel Manning relation "
     "h = [Qn/(W S<sup>0.5</sup>)]<sup>0.6</sup> with roughness n = 0.035, and bulk velocity is "
     "u = Q/(Wh). Width, depth, and velocity are therefore model-derived hydraulic inputs rather than "
     "measured cross-section properties, and the width enters water depth, flow velocity, "
     "k<sub>600</sub>, and the water-surface area A<sub>s</sub> = L\u00b7W. Sensitivity to this width "
     "proxy has not been quantified, so all hydraulic and gas-exchange results are conditional on the "
     "adopted width representation. Biogeochemical covariates are likewise "
     "incomplete: dissolved inorganic carbon (DIC) and dissolved organic carbon (DOC) are available "
     "for 41 of the 120 samples, and alkalinity, nitrogen, "
     "phosphorus, and photosynthetically active radiation were not available for this campaign. A "
     "same-day merge against the Water Quality Portal returned no matching samples (0 of 120), and "
     "the StreamPULSE database contains no East River sites. These gaps constrain the covariate set "
     "available to the closures. Figure 2 shows the logical-reach assignment and the "
     "distribution of the 120 campaign samples on the river network."),
    ("raw", "REACH_TABLE"),
    ("fig", "figure2_reach_assignment_and_samples.png"),

    ("h3", "2.2 Quasi-steady CO\u2082 mass balance and gas exchange"),
    ("p",
     "Each sample is associated with a control volume defined by its reach length L and computed width "
     "W. Carbon mass in the control volume is closed under a quasi-steady assumption at a daily time "
     "step: advective exchange with the upstream reach, source-sink inputs, and atmospheric gas exchange "
     "balance one another,"),
    ("eq", 1),
    ("p",
     "where Q is discharge (m\u00b3 s\u207b\u00b9), C<sub>in</sub> and C are the upstream and reach "
     "concentrations (mol m\u207b\u00b3), k is the gas-transfer velocity (m d\u207b\u00b9), "
     "S<sub>sgs</sub> is the areal source-sink term (mol m\u207b\u00b2 d\u207b\u00b9), "
     "C<sub>eq</sub> is the equilibrium concentration with the atmosphere, A<sub>s</sub> = L\u00b7W is "
     "the water-surface planform area (m\u00b2), and \u03c4<sub>d</sub> = 86400 s d\u207b\u00b9 converts "
     "the daily areal flux into mol s\u207b\u00b9. The planform area A<sub>s</sub> is not the hydraulic "
     "cross-section area; the bulk velocity used below is u = Q/A<sub>c</sub> with A<sub>c</sub> the "
     "cross-section area. For residual diagnosis, C is the observed concentration and "
     "S<sub>sgs</sub> is inferred from the observations; for forward simulation, C is solved from the "
     "balance and the closure supplies the source term. Writing the balance explicitly on a daily areal basis avoids mixing "
     "time bases. Dividing Eq. (1) by A<sub>s</sub>/\u03c4<sub>d</sub> gives the equivalent form"),
    ("eq", 2),
    ("p",
     "in which q<sub>A</sub> = \u03c4<sub>d</sub>\u00b7Q/A<sub>s</sub> (m d\u207b\u00b9) is a daily "
     "area-normalized discharge and every term has units mol m\u207b\u00b2 d\u207b\u00b9."),
    ("p",
     "All closures are inserted into this same balance: a closure configuration is defined entirely by "
     "how it supplies S<sub>sgs</sub> and k, and every configuration is scored after the identical "
     "transport calculation is re-solved. Because the transport numerics are held fixed, differences "
     "among configurations arise from their closure specification and the resulting allocation of "
     "model discrepancy."),
    ("p",
     "Gas exchange is summarized by the model flux density"),
    ("eq", 3),
    ("p",
     "The reported flux totals are sample sums of F<sub>CO\u2082</sub>. They compare how each closure "
     "allocates the model balance; they are neither independently observed evasion fluxes nor spatially "
     "integrated watershed fluxes."),
    ("p",
     "The empirical transfer velocity follows Raymond et al. (2012). The velocity normalized to a "
     "Schmidt number of 600 is estimated from velocity u (m s\u207b\u00b9) and slope (m m\u207b\u00b9), "
     "and the CO\u2082-specific velocity is obtained by Schmidt-number scaling:"),
    ("eqline", K600_EQ),
    ("p",
     "We distinguish the Schmidt-600-normalized velocity k<sub>600</sub> from the "
     "CO\u2082-specific empirical velocity k<sub>emp</sub>. The empirical "
     "relation is evaluated with u in m s\u207b\u00b9 and slope in m m\u207b\u00b9, yielding "
     "k<sub>600</sub> in m d\u207b\u00b9; the CO\u2082 Schmidt number is dimensionless and is "
     "evaluated at the sample water temperature. The equilibrium concentration C<sub>eq</sub> is "
     "computed from Henry\u2019s law as C<sub>eq</sub> = K<sub>H</sub>\u00b7pCO\u2082,atm, "
     "with K<sub>H</sub> = 0.033 mol L\u207b\u00b9 atm\u207b\u00b9 at the ~10 \u00b0C reference "
     "temperature, atmospheric pCO\u2082 of 400 \u00b5atm, and the \u00b5atm-to-atm conversion "
     "(10\u207b\u2076), giving C<sub>eq</sub> = 0.0132 mol m\u207b\u00b3; the same constant applies "
     "to every sample."),
    ("p",
     "Cross-section visualizations used elsewhere in this work are idealized trapezoids, and the "
     "vertical velocity profile is a schematic parabola rather than an ADCP measurement. These "
     "representations are display products and are not used as measurements in the metrics below."),

    ("h3", "2.3 Spatial filtering and diagnosis of the subgrid residual"),
    ("p",
     "Reach-scale transport formulations average over heterogeneity within each reach, and the "
     "unresolved contributions appear formally as a residual source-sink term. Studying that term "
     "requires an operable definition of the filter width \u0394x rather than a qualitative notion of "
     "subgrid structure."),
    ("p",
     "We perform reach-local spatial coarse-graining within each logical reach. Native segments are "
     "ordered by chainage along each reach and grouped into filter cells as individual segments, "
     "consecutive pairs, consecutive groups of four, or one whole-reach cell, giving four discrete "
     "filter operators. Where a fully directed chainage ordering is not available, segments are first "
     "ordered by midpoint Y coordinate and then X coordinate before cumulative segment length is "
     "assigned, so the resulting filter represents the implemented reach-local ordering rather than a "
     "fully directed network topology. Each campaign observation is snapped to its nearest cell at each "
     "scale. The reported \u0394x is the arithmetic mean of the cell lengths associated with the "
     "sample records at that scale, so cells containing multiple samples receive corresponding "
     "weight; this gives \u0394x \u2248 838 m for the native operator. At the coarsest study-reach "
     "operator, all segments assigned to a represented reach are merged into one cell, producing "
     "seven cells in the spatial lattice, six of which contain campaign samples. Figure 1 summarizes "
     "the reach-local filtering construction."),
    ("p",
     "For each date and filter scale, C<sub>in</sub> is taken from the nearest sampled cell upstream "
     "within the same represented reach; when no upstream sampled cell is available, the current "
     "observation is used as the fallback C<sub>in</sub>."),
    ("p",
     "At the operator level the construction parallels the coarse-graining used in large-eddy simulation "
     "and in learned subgrid parameterization studies (Yuval &amp; O\u2019Gorman, 2020); the analogy is "
     "limited to spatial filtering, and S<sub>sgs</sub> denotes the residual of the filtered river "
     "CO\u2082 balance at the chosen scale. Once resolved transport and gas exchange are recomputed on "
     "the filtered balance, the residual implied by the observations is"),
    ("eq", 4),
    ("p",
     "S<sub>sgs</sub> is a filter-induced closure residual. It can absorb measurement error, errors "
     "from the simplified transport representation, and genuinely unresolved processes. It is not a "
     "direct measurement of a single unresolved biogeochemical flux. Its magnitude, structure, and "
     "learnability are evaluated below as the aggregation scale changes."),
    ("fig", "les_filter_conceptual.png"),

    ("h3", "2.4 Alternative unresolved-process closures"),
    ("p",
     "Three closure configurations are compared. They differ only in how S<sub>sgs</sub> and k are "
     "supplied to Eq. (1)."),
    ("p",
     "The Baseline retains the transport and hydraulic formulation of the other configurations while "
     "setting S<sub>sgs</sub> = 0 and using the Raymond-type empirical velocity k<sub>emp</sub>. It "
     "serves as the zero-residual reference for comparison with the alternative closure "
     "formulations."),
    ("p",
     "The Residual-AI configuration learns S<sub>sgs</sub> from hydraulic and water-quality covariates. "
     "Two learners are trained with a fixed seed (42): a multilayer perceptron and a random forest. "
     "The candidate predictor pool comprises discharge, velocity, depth, width, slope, temperature, "
     "the available carbon chemistry (dissolved organic carbon for 41 of the 120 samples), and the "
     "derived dimensionless quantities; fields that are entirely absent from the campaign table are "
     "excluded, and missing retained predictors are imputed with medians calculated from the training "
     "reaches of each fold. The multilayer perceptron uses hidden layers of 64, 32, and 16 units with "
     "learning rate 0.001, early stopping, and fold-specific predictor standardization, and its "
     "predicted residual is constrained to be non-negative. The random forest uses 200 trees with "
     "maximum depth 12 and no predictor standardization."),
    ("p",
     "The k-correction configuration leaves S<sub>sgs</sub> at zero and multiplies the empirical "
     "velocity by a learned factor, k<sub>eff</sub> = k<sub>emp</sub>\u00b7exp(g<sub>\u03b8</sub>(X)), "
     "where g<sub>\u03b8</sub> is a dimensionless correction predicted by a gradient-boosting model "
     "(XGBoost; 300 trees, maximum depth 6, learning rate 0.05, seed 42). The training target is "
     "constructed by first solving the balance for the transfer velocity k<sub>need</sub> required to "
     "reproduce the observed concentration with S<sub>sgs</sub> = 0, then setting "
     "g = ln(k<sub>need</sub>/k<sub>emp</sub>); the predicted correction is applied as "
     "k<sub>eff</sub> = k<sub>emp</sub>\u00b7exp(g<sub>\u03b8</sub>(X)) before the transport balance is "
     "re-solved. Because k<sub>need</sub> is constructed from the observations before the fold loop, "
     "a training-row target can draw on an observed upstream concentration from the reach that is "
     "subsequently held out; the k-correction is therefore not fully fold-isolated at the level of "
     "target construction, a broader information path than the C<sub>in</sub> fallback disclosed in "
     "Section 2.5. The median ratio k<sub>eff</sub>/k<sub>emp</sub> under grouped evaluation is "
     "reported as a diagnostic of how the correction achieves its fit."),
    ("p",
     "The training target for the residual learners is the diagnosed residual constructed from the "
     "observations and the baseline model output: an evasion term evaluated at the observed "
     "concentration is combined with a depth-normalized concentration deficit. Because these terms "
     "carry different units in the current implementation, the Residual-AI training target does not "
     "coincide exactly with Eq. (4). The Residual-AI results below therefore characterize the "
     "implemented target rather than a dimensionally consistent closure of Eq. (4)."),

    ("h3", "2.5 Leave-one-reach-out transport-coupled evaluation"),
    ("p",
     "Closure generalization is evaluated by leaving one logical reach out at a time across the eight "
     "logical reaches. Each reach is held out once. For each fold, missing predictors are imputed "
     "with medians from the training reaches; predictor standardization is fitted on the training "
     "data only for the models that use it, specifically the multilayer perceptron and the sparse "
     "model described in Section 2.8. The "
     "closure is fitted on the training-reach targets and then used to generate closure values for "
     "the full network state required by the transport calculation; the complete quasi-steady network "
     "is re-solved with those closure values, and only then are the predictions belonging to the "
     "held-out reach retained and scored against observed C<sub>aq</sub>. No inner "
     "hyperparameter-selection loop is used, so we refer to the procedure as grouped "
     "cross-validation rather than nested cross-validation."),
    ("p",
     "When an upstream concentration state is unavailable, the solver uses the observed C<sub>aq</sub> "
     "at the current sample as the fallback boundary value C<sub>in</sub>; the experiment therefore "
     "evaluates closure generalization under partially observed boundary conditioning rather than fully "
     "target-blind forecasting. Sampling is also strongly imbalanced among reaches: R008 contributes 58 "
     "of the 120 samples, while three reaches contribute one each, so pooled errors are read together "
     "with reach-level evidence weights (Table 5). A date-grouped variant is reported as a "
     "time-sensitivity analysis and is not nested inside the reach split."),

    ("h3", "2.6 Metrics and flux diagnostic"),
    ("p",
     "The primary metric is the held-out C<sub>aq</sub> RMSE in mol m\u207b\u00b3. The secondary "
     "diagnostic is the sample-summed model flux \u03a3F<sub>CO\u2082</sub> in mol m\u207b\u00b2 "
     "d\u207b\u00b9, computed from Eq. (3) with the transport-predicted concentration and the transfer "
     "velocity of each configuration: k<sub>emp</sub> for the Baseline and Residual-AI, and "
     "k<sub>eff</sub> for the k-correction. An observation-based proxy flux uses k<sub>emp</sub> with "
     "observed concentrations. Differences in \u03a3F<sub>CO\u2082</sub> across closures indicate how "
     "each configuration allocates the balance between sources and gas exchange."),

    ("h3", "2.7 Practical equifinality diagnostic"),
    ("p",
     "To characterize compensation between source terms and gas exchange, we define the implied source "
     "adjustment"),
    ("eq", 5),
    ("p",
     "At fixed concentration and resolved transport state, S<sub>implied</sub> is the source-sink "
     "adjustment that makes a model retaining k<sub>emp</sub> locally equivalent to a model that uses "
     "k<sub>eff</sub> and no additional source term. In Eq. (5), C is the observed aqueous "
     "concentration at the sample, so the two process allocations are compared at a common observed "
     "concentration rather than at their respective forward-model concentrations. A large "
     "S<sub>implied</sub> together with a small change in concentration error indicates that the "
     "observations provide limited discrimination between the two allocations; we refer to this "
     "compensating closure behaviour as practical equifinality. The diagnostic is algebraic and "
     "empirical rather than a formal structural-identifiability analysis."),

    ("h3", "2.8 Sparse dimensionless closure"),
    ("p",
     "A final experiment asks whether the residual admits a compact dimensionless representation. The "
     "dimensionless response is defined as S* = S<sub>sgs</sub>/(k<sub>emp</sub>C<sub>eq</sub>), with "
     "Froude number Fr, slope, relative depth h/W, and the base-10 logarithm of the Reynolds number "
     "as candidate nondimensional features, together with an implemented Damköhler candidate whose "
     "time-base inconsistency is described below. Sparse selection "
     "follows the spirit of sparse discovery methods (Xie et al., 2022), implemented with a "
     "least absolute shrinkage and selection operator (LASSO). Within each "
     "leave-one-reach-out fold, missing predictors are imputed from the training reaches, the "
     "predictors are standardized using training-fold statistics, and a LASSO with fixed penalty "
     "\u03b1 = 0.05 is fitted on the dimensional residual; the predicted S<sub>sgs</sub> is "
     "reinserted into the transport calculation and scored only on the held-out reach. For "
     "descriptive reporting, the same LASSO specification is fitted once to the full dataset against "
     "the dimensionless response S*; the sparse relation reported below comes from that full-data "
     "refit and is therefore a descriptive coefficient summary rather than a coefficient vector "
     "applied unchanged across the holdout folds. The Damk\u00f6hler number is constructed as "
     "k\u03c4/h with \u03c4 = L/u; as implemented, \u03c4 in seconds is multiplied by k in "
     "m d\u207b\u00b9, so this candidate feature is not strictly dimensionless. Selection drops the "
     "term, and the retained predictors (Fr, slope, h/W) are unaffected. Compactness is tested "
     "against predictive utility; the two are not assumed to coincide."),

    ("h2", "3. Results"),

    ("h3", "3.1 Residual closures do not improve held-out concentration prediction"),
    ("p",
     "Under leave-one-reach-out transport-coupled evaluation, neither "
     "residual closure improves on the Baseline (Tables 2 and 3; Figure 3). The held-out "
     "C<sub>aq</sub> RMSE is 0.0284 mol m\u207b\u00b3 for the Baseline, 0.0573 for the Residual-AI "
     "multilayer perceptron, and 0.0745 for the random forest. The corresponding mean absolute error "
     "(MAE) values are 0.0132, "
     "0.0326, and 0.0301, and the residual closures show positive concentration bias (0.0177 and "
     "0.0180) where the Baseline bias is \u22120.0132. The date-grouped sensitivity analysis gives "
     "the same ordering (0.0284, 0.0591, and 0.0747), with the date-grouped evaluation outputs "
     "archived in the public repository cited in Section 6."),
    ("p",
     "The subgroup decomposition locates the error (Table 5; Figures 4 and S1). On the mainstem reach "
     "R008, both residual closures are slightly better than the Baseline: RMSE is 0.0121 for the MLP "
     "and 0.0087 for the random forest against 0.0136 for the Baseline. On the multi-sample "
     "tributaries the pattern reverses: RMSE is 0.0381 for the Baseline, 0.0808 for the MLP, and "
     "0.1058 for the random forest. Table 5 reports the primary MLP closure; the corresponding "
     "random-forest subgroup values are available with the archived evaluation outputs cited in "
     "Section 6. The pooled degradation is concentrated in the multi-sample tributaries "
     "R002\u2013R005, where held-out errors are substantially larger than on the mainstem. The "
     "holdout scatter (Figure 4) shows the same structure: mainstem predictions cluster near the "
     "observations while tributary predictions spread widely."),
    ("raw", "NESTED_TABLES"),
    ("fig", "nested_cv_rmse_bar.png"),
    ("fig", "nested_cv_scatter_holdout.png"),
    ("fig", "subgroup_rmse_r008_vs_trib.png"),

    ("h3", "3.2 A corrected gas-transfer velocity lowers concentration error"),
    ("p",
     "The k-correction is the only configuration that reduces held-out concentration error below the "
     "Baseline. Its C<sub>aq</sub> RMSE is 0.0244 mol m\u207b\u00b3 against 0.0284 for the Baseline, "
     "and MAE falls from 0.0132 to 0.0046 (Tables 2 and 3). In this configuration, the learned "
     "correction acts only through the transfer velocity. The median effective velocity is "
     "0.0329 m d\u207b\u00b9, compared with the median Raymond-type empirical value computed for the "
     "present samples, 98.1 m d\u207b\u00b9; the median ratio k<sub>eff</sub>/k<sub>emp</sub> is "
     "3.35\u00d710\u207b\u2074 (Table 7; Figure 5). Under this correction, the median effective "
     "transfer velocity is reduced by roughly three orders of magnitude relative to "
     "k<sub>emp</sub>. This comparison remains conditional on the partially observed boundary "
     "construction and the pre-fold construction of k<sub>need</sub> described in Sections 2.4 and "
     "2.5; it is therefore not a fully target-blind out-of-sample estimate."),
    ("fig", "identifiability_k_vs_sgs.png"),
    ("p",
     "The lower concentration error alone does not establish whether the altered process allocation "
     "remains plausible; the associated model flux diagnostic is examined next."),

    ("h3", "3.3 The concentration gain coincides with collapse of the flux diagnostic"),
    ("p",
     "The flux diagnostic reveals substantially different process allocations among the closures. The "
     "sample-summed model flux \u03a3F<sub>CO\u2082</sub> is 3.24 mol m\u207b\u00b2 d\u207b\u00b9 for "
     "the Baseline and 0.031 for the k-correction (Tables 2 and 7; Figure S2). The concentration "
     "improvement of the k-correction coincides with a collapse of the modeled CO\u2082 release by "
     "roughly two orders of magnitude. The Residual-AI configuration moves in the opposite direction, "
     "with \u03a3F<sub>CO\u2082</sub> of 69.5, because its predicted sources add to the balance while "
     "k remains at k<sub>emp</sub>."),
    ("p",
     "No independent evasion observations are available for this campaign, so these values do not show "
     "that the Baseline flux is correct or that the corrected flux is wrong. They show that "
     "concentration performance alone can favor a markedly different allocation of the model balance. "
     "The implied-source diagnostic makes the compensation explicit. At fixed concentrations, the mean "
     "implied adjustment S<sub>implied</sub> is 1.00 mol m\u207b\u00b2 d\u207b\u00b9, the mean "
     "Residual-AI prediction is 0.56, and the two are anti-correlated across samples (Spearman "
     "\u22120.57; Figure 5). A positive source term and a reduced transfer velocity act on the "
     "concentration balance in compensating directions, and the held-out concentration metric provides "
     "limited discrimination between them. Figure S2(c) shows the corresponding sample-level relation "
     "between k<sub>eff</sub>/k<sub>emp</sub> and the k-correction flux diagnostic."),
    ("raw", "INNOVATION_TABLES"),
    ("fig", "supp_flux_diagnostics.png"),

    ("h3", "3.4 The diagnosed residual depends on filter scale"),
    ("p",
     "The magnitude of the diagnosed residual varies systematically with the filter width (Table 6; "
     "Figure 6). Mean |S<sub>sgs</sub>| is 1.916 mol m\u207b\u00b2 d\u207b\u00b9 at the native NHD "
     "resolution (\u0394x \u2248 838 m), decreases to 1.120 and 1.050 at successive merging levels, and "
     "reaches 1.000 at the study-reach scale (\u0394x \u2248 26,086 m; 7 cells, of which 6 contain "
     "samples). The variance of S<sub>sgs</sub> falls from 22.4 to 2.20 over the same range (Figure "
     "S3). The result indicates that the diagnosed closure residual depends on the spatial "
     "representation used to separate resolved from unresolved contributions. It is an empirical scale "
     "dependence for the implemented reach-local operator, not a universal scaling law."),
    ("fig", "filter_scale_sgs.png"),
    ("fig", "filter_scale_sgs_box.png"),

    ("h3", "3.5 A sparse dimensionless closure is compact but not predictive"),
    ("p",
     "The full-data LASSO refit on the dimensionless response retains three of the five candidate "
     "\u03a0 terms (Table 8; Figure 7). With subscript z denoting predictors standardized to "
     "zero mean and unit variance, the closure is"),
    ("eqline", SPARSE_EQ),
    ("p",
     "The fitted coefficients are positive for Froude number and negative for slope and relative "
     "depth. Because this relation is a descriptive full-data summary (Section 2.8), it is not "
     "itself scored as a held-out law; the leave-one-reach R\u00b2 for reconstructing the "
     "dimensionless response S* is \u22122.743. Under the same leave-one-reach-out transport-coupled protocol, in "
     "which the scaler and LASSO are refitted within each fold, the sparse closure gives a held-out "
     "C<sub>aq</sub> RMSE of 0.0506 mol m\u207b\u00b3, above the Baseline value of 0.0284 (Table 9). "
     "The sparse form is therefore useful as a compact diagnostic description of the residual but "
     "does not recover predictive skill on held-out reaches."),
    ("fig", "dimensionless_coefficients.png"),

    ("h3", "3.6 In-sample fit (appendix)"),
    ("p",
     "The in-sample fit of the residual model is reported in the appendix (Table 4; Figure A1), with "
     "R\u00b2 \u2248 0.997 and RMSE 0.0013 mol m\u207b\u00b3 computed on the same 120 rows used for "
     "training. This optimistic in-sample fit is reported only as an overfitting diagnostic and is not "
     "used as evidence of generalization."),
    ("fig", "obs_vs_model_scatter_large.png"),

    ("h2", "4. Discussion"),

    ("h3", "4.1 Failed generalization of residual closures is a modelling diagnosis"),
    ("p",
     "The residual closures reproduce the observations well in-sample but degrade held-out "
     "concentration prediction relative to a zero-residual Baseline. This pattern suggests that the "
     "residual diagnosed from the present resolved model, predictors, spatial representation, and "
     "sampling design does not carry enough transferable structure to improve predictions after "
     "transport coupling. In the evaluation logic of Bennett et al. (2013) and Vilas et al. (2023), the "
     "discrepancy is itself diagnostic: it separates apparent learnability from held-out usefulness. The "
     "subgroup evidence points to where the transfer fails. Errors increase most clearly in the pooled "
     "multi-sample tributaries R002\u2013R005, whereas performance on individual tributary subsets is "
     "less uniform; the mainstem reach, with 58 samples, is one subgroup where the residual closure "
     "remains competitive with the Baseline. These results support reporting reach-level diagnostics "
     "alongside pooled metrics, particularly when sampling support is strongly imbalanced. Because the "
     "training target does not coincide dimensionally with Eq. (4), this failure characterizes the "
     "present implementation rather than the general learnability of a dimensionally consistent "
     "S<sub>sgs</sub> closure."),
    ("p",
     "The failure of residual closures to generalize does not, however, imply that concentration error "
     "uniquely favors the Baseline, as shown by the contrasting k-correction result."),

    ("h3", "4.2 Process allocation and practical equifinality"),
    ("p",
     "The k-correction achieves the lowest concentration error of any configuration, and it does so by "
     "reducing the effective transfer velocity by roughly three orders of magnitude. Because "
     "S<sub>sgs</sub> and k(C \u2212 C<sub>eq</sub>) enter the same balance with opposing signs, "
     "reducing k can compensate for a different source allocation while retaining a similar "
     "concentration fit. The collapse of \u03a3F<sub>CO\u2082</sub> from 3.24 to 0.031 shows what "
     "this fit implies for the process budget. Without independent evasion measurements, the data "
     "cannot adjudicate between the Baseline and corrected allocations; the lower RMSE is evidence of "
     "improved concentration fit, not independent evidence of improved process fidelity."),
    ("p",
     "Here, practical equifinality refers to the compensation between S<sub>sgs</sub> and k represented "
     "by Eq. (5). The Baseline/k-correction contrast indicates that this compensation direction is "
     "consequential in the present experiment: the Baseline and k-correction both yield relatively low "
     "concentration errors while producing markedly different transfer velocities and flux "
     "diagnostics. This empirical comparison does not constitute a structural-identifiability "
     "analysis or establish statistical equivalence between the competing predictions. "
     "The degraded RMSE of the MLP, random forest, and sparse closures is likewise not equifinality "
     "evidence; it shows that closure choice matters and that flexible residual learning did not "
     "generalize here. Within those boundaries, the results suggest that concentration-dominated "
     "evaluation does not uniquely constrain how discrepancy is allocated between S<sub>sgs</sub> and "
     "k in this configuration."),
    ("p",
     "This process-allocation ambiguity concerns the closure form; the filtering experiment addresses "
     "a related but distinct source of variability in the diagnosed residual."),

    ("h3", "4.3 What filtering and sparse representation reveal about the residual"),
    ("p",
     "The filter-scale results show that the diagnosed residual changes with the implemented spatial "
     "filter. Its magnitude changes as the filter width changes, because the split between resolved "
     "and unresolved contributions is defined by the filter. This interpretation is bounded by the "
     "implemented operator, which uses reach-local merging and a coordinate-ordering fallback rather "
     "than a fully directed network filter. Within those boundaries, the result is consistent with the "
     "coarse-graining logic used elsewhere for learned subgrid terms (Yuval &amp; O\u2019Gorman, 2020): "
     "the statistics of the unresolved term depend on resolution."),
    ("p",
     "The sparse closure retains only Froude number, slope, and relative depth, but its compact form "
     "does not improve held-out prediction: RMSE remains above the "
     "Baseline and the S* reconstruction fails under reach holdout. Compact forms are therefore not "
     "automatically validated or predictive. Under the present protocol, the tested sparse "
     "\u03a0-group representation does not provide cross-reach predictive utility; it remains useful "
     "as a diagnostic simplification."),

    ("h3", "4.4 Implications for environmental-model evaluation"),
    ("p",
     "These findings suggest that concentration RMSE should be interpreted together with diagnostics of "
     "gas exchange and unresolved source allocation. When observations constrain only concentration, "
     "lower RMSE should be interpreted alongside diagnostics of the process terms that produced it."),
    ("p",
     "The present conclusions are bounded by partially observed upstream conditioning, strongly unequal "
     "reach support, the coordinate-based ordering fallback, idealized hydraulic geometry, incomplete "
     "covariates (alkalinity, nitrogen, phosphorus, photosynthetically active radiation), and the "
     "absence of independent evasion measurements. The Water Quality Portal merge and the StreamPULSE "
     "search returned no usable additional constraints for this campaign. These limitations restrict "
     "inference to the East River experiment, and they also identify the observations that would most "
     "help to discriminate closures: improved upstream boundary information, better-resolved channel "
     "geometry, more balanced reach sampling, and independent constraints on gas exchange. The central "
     "implication is that lower concentration error alone is insufficient to determine which allocation "
     "of unresolved processes is better supported."),

    ("h2", "5. Conclusions"),
    ("p",
     "Under leave-one-reach-out transport-coupled evaluation, the implemented Residual-AI closures did "
     "not improve concentration prediction relative to the Baseline (Residual-AI RMSE 0.0573 mol "
     "m\u207b\u00b3 for the MLP against 0.0284 for the Baseline), while the k-correction "
     "lowered RMSE to 0.0244 only as the sample-summed model flux diagnostic fell from 3.24 to 0.031 "
     "mol m\u207b\u00b2 d\u207b\u00b9 and the median k<sub>eff</sub>/k<sub>emp</sub> reached "
     "3.35\u00d710\u207b\u2074. Concentration-only observations therefore provide limited "
     "discrimination between discrepancy assigned to the source term S<sub>sgs</sub> and discrepancy "
     "assigned to the transfer velocity k."),
    ("p",
     "The framework combines an explicit spatial filter, transport-coupled grouped evaluation, and an "
     "algebraic closure-compensation diagnostic. Within the East River experiment, the framework "
     "provides a diagnostic comparison of alternative closure allocations; the flux values remain model "
     "diagnostics, and transfer to other basins has not been tested. The results therefore support "
     "transport-coupled, process-aware evaluation of alternative closure allocations when concentration "
     "is the primary observational constraint."),

    ("h2", "6. Data availability"),
    ("p",
     "The East River water-chemistry and pCO\u2082 data are publicly available through HydroShare "
     "(resource 9f907b46baa848e180c49339d605bf31; Saccardi &amp; Winnick, 2021). The DIC supplement, "
     "network shapefiles, and hydraulic tables are in HydroShare resource "
     "2a2132999fb84214aad0596783812db2. Mainstem discharge is from USGS gage 09112500. River-network "
     "geometry uses NHDPlus HR flowlines for HUC 14020001. Processed tables, figures, and the analysis "
     "code are maintained in the public repository "
     "(https://github.com/Coucou2016/river-carbon-transport); a version-specific release or immutable "
     "commit should be cited alongside the mutable repository state at submission."),
]

REFERENCES = [
    "Battin, T. J., et al. (2023). River ecosystem metabolism and carbon biogeochemistry in a changing "
    "world. <em>Nature</em>, 614, 676\u2013687. https://doi.org/10.1038/s41586-022-05500-8",
    "Bennett, N. D., et al. (2013). Characterising performance of environmental models. "
    "<em>Environmental Modelling &amp; Software</em>, 40, 1\u201320. "
    "https://doi.org/10.1016/j.envsoft.2012.09.011",
    "Gao, Y., et al. AI cross-fusion approach for river carbon transport. <em>The Innovation</em> "
    "(manuscript in preparation; DOI to be added).",
    "G\u00f3mez-Gener, L., Rocher-Ros, G., et al. (2021). Global carbon dioxide efflux from rivers "
    "enhanced by high nocturnal emissions. <em>Nature Geoscience</em>, 14, 647\u2013653. "
    "https://doi.org/10.1038/s41561-021-00722-3",
    "Hotchkiss, E. R., et al. (2015). Sources of and processes controlling CO\u2082 emissions change "
    "with the size of streams and rivers. <em>Nature Geoscience</em>, 8, 696\u2013699. "
    "https://doi.org/10.1038/ngeo2507",
    "Markovich, K. H., White, J. T., &amp; Knowling, M. J. (2022). Sequential and batch data "
    "assimilation approaches to cope with groundwater model error: An empirical evaluation. "
    "<em>Environmental Modelling &amp; Software</em>, 156, 105498. "
    "https://doi.org/10.1016/j.envsoft.2022.105498",
    "Raymond, P. A., et al. (2012). Scaling the gas transfer velocity and hydraulic geometry in streams "
    "and small rivers. <em>Limnology and Oceanography: Fluids and Environments</em>, 2, 41\u201353. "
    "https://doi.org/10.1215/21573689-1597669",
    "Saccardi, B., &amp; Winnick, M. J. (2021). Improving predictions of stream CO\u2082 concentrations "
    "and fluxes using a stream network model: A case study in the East River Watershed, CO, USA. "
    "<em>Global Biogeochemical Cycles</em>, 35, "
    "e2021GB006972. https://doi.org/10.1029/2021GB006972",
    "Vilas, M. P., et al. (2023). TALKS: A systematic framework for resolving model-data discrepancies. "
    "<em>Environmental Modelling &amp; Software</em>, 163, 105668. "
    "https://doi.org/10.1016/j.envsoft.2023.105668",
    "Xie, X., Samaei, A., Guo, J., Liu, W. K., &amp; Gan, Z. (2022). Data-driven discovery of "
    "dimensionless numbers and governing laws from scarce measurements. <em>Nature Communications</em>, "
    "13, 7562. https://doi.org/10.1038/s41467-022-35084-w",
    "Yuval, J., &amp; O\u2019Gorman, P. A. (2020). Stable machine-learning parameterization of subgrid "
    "processes for climate modeling at a range of resolutions. <em>Nature Communications</em>, 11, "
    "3295. https://doi.org/10.1038/s41467-020-17142-3",
]

# ---------------------------------------------------------------------------
# Table sanitization (report table helpers -> clean manuscript tables)
# ---------------------------------------------------------------------------

def sanitize_paper_tables(html: str) -> str:
    """Rewrite report-table captions, headers, and lead notes for the manuscript.

    Numbers are never touched; only presentation language is changed.
    """
    # --- Captions (specific before generic) ---
    caption_map = [
        (r"<caption>表 2 East River 研究河网.*?</caption>",
         "<caption>Table 1. East River study network: connectivity of the eight logical reaches, "
         "ordered upstream to downstream.</caption>"),
        (r"<caption>表 M 论文主结果一览.*?</caption>",
         "<caption>Table 2. Main results under leave-one-reach-out grouped cross-validation with "
         "transport coupling. Flux totals are model-derived diagnostics, not chamber-validated "
         "fluxes.</caption>"),
        (r"<caption>表 4b 样本内指标.*?</caption>",
         "<caption>Table 4. In-sample metrics (optimistic appendix; not a paper conclusion).</caption>"),
        (r"<caption>表 4 嵌套交叉验证.*?</caption>",
         "<caption>Table 3. Leave-one-reach-out grouped cross-validation: held-out "
         "C<sub>aq</sub> and F<sub>CO\u2082</sub> metrics (primary paper metrics; F values are model "
         "flux diagnostics).</caption>"),
        (r"<caption>表 5 子组嵌套交叉验证.*?</caption>",
         "<caption>Table 5. Subgroup metrics under leave-one-reach-out grouped cross-validation. Mainstem and "
         "tributary reaches are not equally weighted.</caption>"),
        (r"<caption>表 6 滤波尺度实验.*?</caption>",
         "<caption>Table 6. Filter-scale experiment: S<sub>sgs</sub> diagnosed after snapping the 120 "
         "samples onto coarsened NHDPlus HR HUC 14020001 networks.</caption>"),
        (r"<caption>表 7 可辨识性.*?</caption>",
         "<caption>Table 7. Practical-equifinality diagnostic: k and source-term compensation under "
         "the leave-one-reach-out grouped protocol.</caption>"),
        (r"<caption>表 8b 无量纲稀疏式代入输运后.*?</caption>",
         "<caption>Table 9. Sparse dimensionless closure inserted into transport under grouped "
         "cross-validation (compare the Baseline value of 0.0284 in Table 3).</caption>"),
        (r"<caption>表 8 无量纲稀疏闭合.*?</caption>",
         "<caption>Table 8. Sparse dimensionless closure (\u03a0-group LASSO).</caption>"),
    ]
    for pat, rep in caption_map:
        html = re.sub(pat, rep, html, flags=re.S)

    # --- Lead notes (diary/process language -> plain English notes) ---
    lead_map = [
        (r'<p class="lead">读图前请先理解这张表.*?</p>',
         "<p class=\"lead\">Water enters through the headwater tributary on the R001 side, passes "
         "R002\u2013R007 in sequence, and collects in the R008 East River mainstem. Transport, "
         "concentration, and CO\u2082 flux propagate along this chain from upstream to downstream. The "
         "network geometry is the published 393-segment NHD centerline set from the campaign "
         "supplement.</p>"),
        (r'<p class="lead">表 M 由.*?</p>',
         "<p class=\"lead\">Neither Residual-AI nor the sparse \u03a0 closure beats the Baseline on "
         "held-out concentration; the k-correction lowers concentration RMSE slightly while the flux "
         "diagnostic collapses, indicating practical equifinality.</p>"),
        (r'<p class="lead">读表：只比较持出样本.*?</p>',
         "<p class=\"lead\">Only held-out samples are compared. If a residual closure does not lower "
         "held-out C RMSE below the Baseline, it is not claimed to improve generalized prediction. The "
         "F<sub>CO\u2082</sub> totals are model diagnostics of the form k(C \u2212 C<sub>eq</sub>), not "
         "independent flux observations.</p>"),
        (r'<p class="lead">R008 有 58 个点.*?</p>',
         "<p class=\"lead\">R008 contributes 58 samples; R001, R006, and R007 are single-sample reaches "
         "marked schematic and are not weighted equally with the mainstem.</p>"),
        (r'<p class="lead">残差随粗化而变平滑.*?</p>',
         "<p class=\"lead\">The residual smooths as the network is coarsened: an empirical scale "
         "dependence for the East River/NHDPlus HR corridor, not a universal subgrid law and not an "
         "accuracy claim. Fewer than eight cells contain samples at the study-reach scale because the "
         "corridor assignment does not cover every logical reach.</p>"),
        (r'<p class="lead">稀疏式可解释.*?</p>',
         "<p class=\"lead\">The sparse form is interpretable, but its held-out C RMSE does not fall "
         "below the Baseline. It is reported as a closure-form diagnostic, not as an accuracy "
         "improvement.</p>"),
    ]
    for pat, rep in lead_map:
        html = re.sub(pat, rep, html, flags=re.S)

    # --- Header rows (specific first) ---
    header_map = [
        ("<th>河段编号</th><th>河流名称</th><th>上游河段</th><th>下游河段</th>",
         "<th>Reach</th><th>Stream name</th><th>Upstream</th><th>Downstream</th>"),
        ("<th>河长 (km)</th><th>NHD 线段数</th><th>样点数</th><th>说明</th>",
         "<th>Length (km)</th><th>NHD segments</th><th>Samples</th><th>Note</th>"),
        ("<th>方案 / 模型</th><th>C RMSE</th><th>F 合计</th><th>k<sub>eff</sub>/k<sub>emp</sub></th>",
         "<th>Scheme / model</th><th>C RMSE</th><th>F total</th><th>k<sub>eff</sub>/k<sub>emp</sub></th>"),
        ("<th>C 优于 Baseline？</th><th class=\"left\">读表要点</th>",
         "<th>Beats Baseline (C)?</th><th class=\"left\">Table note</th>"),
        ("<th>方案 / 模型</th><th>C RMSE</th><th>C MAE</th><th>C Bias</th><th>C R²</th>",
         "<th>Scheme / model</th><th>C RMSE</th><th>C MAE</th><th>C Bias</th><th>C R\u00b2</th>"),
        ("<th>F RMSE</th><th>F Bias</th><th>F 合计</th><th>n</th>",
         "<th>F RMSE</th><th>F Bias</th><th>F total</th><th>n</th>"),
        ("<th>模型</th><th>C RMSE</th><th>C Bias</th><th>C R²</th><th>n</th>",
         "<th>Model</th><th>C RMSE</th><th>C Bias</th><th>C R\u00b2</th><th>n</th>"),
        ("<th>方案</th><th>子组</th><th>证据权重</th><th>C RMSE</th><th>C R²</th><th>n</th>",
         "<th>Scheme</th><th>Subgroup</th><th>Evidence weight</th><th>C RMSE</th><th>C R\u00b2</th><th>n</th>"),
        ("<th>尺度</th><th>Δx (m)</th><th>单元总数</th><th>有样点单元</th><th>n 样点</th>",
         "<th>Scale</th><th>\u0394x (m)</th><th>Cells</th><th>Sampled cells</th><th>Samples</th>"),
        ("<th>平均 |S|</th><th>Var(S)</th>", "<th>Mean |S<sub>sgs</sub>|</th><th>Var(S<sub>sgs</sub>)</th>"),
        ("<th>方案</th><th>C RMSE</th><th>F 合计</th><th>k 中位数</th><th>k<sub>eff</sub>/k<sub>emp</sub></th>",
         "<th>Scheme</th><th>C RMSE</th><th>F total</th><th>Median k</th><th>k<sub>eff</sub>/k<sub>emp</sub></th>"),
        ("<th>项目</th><th colspan=\"4\" class=\"left\">结果</th>",
         "<th>Item</th><th colspan=\"4\" class=\"left\">Result</th>"),
        ("<th>方案</th><th>C RMSE</th><th>C R²</th><th>F RMSE</th><th>n</th>",
         "<th>Scheme</th><th>C RMSE</th><th>C R\u00b2</th><th>F RMSE</th><th>n</th>"),
    ]
    for old, new in header_map:
        html = html.replace(old, new)

    # --- Cell text ---
    cell_map = [
        ("支流源头，n=1 仅作示意", "Tributary headwater; n = 1, schematic only"),
        ("草甸河段，连接 Bradley 与 Rock", "Meadow reach connecting Bradley and Rock Creeks"),
        ("Rock 溪，多样本支流", "Rock Creek; multi-sample tributary"),
        ("NHD GNIS 匹配良好", "Good GNIS match against NHD"),
        ("Gothic 支流，多样本", "Gothic Creek; multi-sample tributary"),
        ("单样本，仅作示意", "Single sample; schematic only"),
        ("干流 Almont 上游，样点最密", "Mainstem above Almont; densest sampling"),
        ("East River 干流", "East River mainstem"),
        ("（样本内，乐观）", " (in-sample, optimistic)"),
        ("R004+R006（Copper + Quigley）", "R004+R006 (Copper + Quigley)"),
        ("（留一河段）", " (leave-one-reach)"),
        ("（负值 = 不能推广）", " (negative value = does not generalize)"),
        ("标准化式", "Standardized-predictor form"),
        ("原始变量式", "Original-variable form"),
        ("主导项", "Dominant terms"),
        ("对 S* 的留一河段 R²", "Leave-one-reach R\u00b2 for reconstructing S*"),
        ("<td>否</td>", "<td>No</td>"),
        ("<td>是</td>", "<td>Yes</td>"),
    ]
    for old, new in cell_map:
        html = html.replace(old, new)

    # Manuscript terminology for raw scheme identifiers (display labels only).
    scheme_label_map = [
        ("<td class=\"left\">baseline / none</td>", "<td class=\"left\">Baseline</td>"),
        ("<td class=\"left\">k_correction / xgboost</td>",
         "<td class=\"left\">k-correction / XGBoost</td>"),
        ("<td class=\"left\">residual_ai / mlp</td>", "<td class=\"left\">Residual-AI / MLP</td>"),
        ("<td class=\"left\">residual_ai / random_forest</td>",
         "<td class=\"left\">Residual-AI / random forest</td>"),
        ("<td class=\"left\">sparse_pi / lasso_pi", "<td class=\"left\">Sparse-\u03a0 / LASSO"),
        ("<td class=\"left\">baseline</td>", "<td class=\"left\">Baseline</td>"),
        ("<td class=\"left\">k_correction</td>", "<td class=\"left\">k-correction</td>"),
        ("<td class=\"left\">residual_ai</td>", "<td class=\"left\">Residual-AI</td>"),
        ("baseline_in_sample (in-sample, optimistic)", "Baseline (in-sample, optimistic)"),
        ("residual_ai_in_sample_optimistic (in-sample, optimistic)",
         "Residual-AI / MLP (in-sample, optimistic)"),
        ("<td class=\"left\">Native NHD</td>", "<td class=\"left\">Native NHDPlus HR</td>"),
    ]
    for old, new in scheme_label_map:
        html = html.replace(old, new)

    # One-metric-one-precision display pass (values rounded for display only).
    precision_map = [
        ("<td>69.51</td>", "<td>69.5</td>"),
        ("<td>69.507</td>", "<td>69.5</td>"),
        ("<td>143.33</td>", "<td>143.3</td>"),
        ("<td>244.18</td>", "<td>244.2</td>"),
        ("<td>0.0244</td><td>0.03</td>", "<td>0.0244</td><td>0.031</td>"),
        ("<td>-1.000</td><td>0.03</td>", "<td>-1.000</td><td>0.031</td>"),
        ("<td>0.033</td>", "<td>0.0329</td>"),
        ("<td>98.096</td>", "<td>98.1</td>"),
        ("<td>0.00034</td>", "<td>3.35\u00d710\u207b\u2074</td>"),
        ("<td>1.00000</td>", "<td>1.00</td>"),
        ("<code>S_sgs*_z \u2248 + 1.059 + 1.536*Fr \u2212 1.669*Slope \u2212 2.179*h_over_W</code>",
         "<code>S* \u2248 1.059 + 1.536\u00b7Fr_z \u2212 1.669\u00b7Slope_z \u2212 2.179\u00b7(h/W)_z</code>"),
    ]
    for old, new in precision_map:
        html = html.replace(old, new)

    # Residual script-name/path references, if any survive.
    html = re.sub(r"<code>scripts/[^<]+</code>", "the repository table builders", html)
    html = re.sub(r"<code>src/[^<]+</code>", "the open-source implementation", html)
    return html


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def b64_img(name: str) -> str:
    p = FIG_DIR / name
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode("ascii")


def figure_block(fname: str) -> str:
    data = b64_img(fname)
    if not data:
        return ""
    caption = FIG_CAPTIONS[fname]
    return (
        '  <div class="figure-block">\n'
        f'    <img src="data:image/png;base64,{data}" alt="{fname}">\n'
        f'    <div class="fig-caption">{caption}</div>\n'
        "  </div>"
    )


def equation_block(expr_html: str, number: str) -> str:
    num = f'<span class="eq-num">({number})</span>' if number else ""
    return f'<div class="equation">{expr_html} {num}</div>'


def references_html() -> str:
    items = "\n".join(f"    <li>{ref}</li>" for ref in REFERENCES)
    return f'  <ol class="references">\n{items}\n  </ol>'


def strip_tags(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<sub>", "_", text)
    text = re.sub(r"</sub>", "", text)
    text = re.sub(r"<sup>\s*−?0?5\s*</sup>", "^-0.5", text)
    text = re.sub(r"<sup>([^<]*)</sup>", r"^\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ").replace("\u00b2", "2").replace("\u00b3", "3")
    text = text.replace("\u207b", "-").replace("\u2082", "2").replace("\u2090", "a")
    text = text.replace("\u2091", "e").replace("\u2212", "-").replace("\u0394", "Delta")
    text = text.replace("\u03a0", "Pi").replace("\u03c4_d", "tau_d")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# --- Markdown tables (built from the same result CSVs as the HTML helpers) ---

def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def _flux_disp(v: float) -> str:
    if v < 1.0:
        return f"{v:.3f}"
    if v < 10.0:
        return f"{v:.2f}"
    return f"{v:.1f}"


SCHEME_LABELS = {
    ("baseline", "none"): "Baseline",
    ("k_correction", "xgboost"): "k-correction / XGBoost",
    ("residual_ai", "mlp"): "Residual-AI / MLP",
    ("residual_ai", "random_forest"): "Residual-AI / random forest",
    ("sparse_pi", "lasso_pi"): "Sparse-\u03a0 / LASSO",
}
SCHEME_ONLY = {
    "baseline": "Baseline",
    "k_correction": "k-correction",
    "residual_ai": "Residual-AI",
}
IN_SAMPLE_LABELS = {
    "baseline_in_sample": "Baseline",
    "residual_ai_in_sample_optimistic": "Residual-AI / MLP",
}


def md_tables() -> str:
    import json
    import pandas as pd

    tables_dir = ROOT / "results" / "tables"
    parts: list[str] = []

    # Table 1: reach network
    from report_content import REACH_NETWORK_ROWS
    notes_en = {
        "支流源头，n=1 仅作示意": "Tributary headwater; n = 1, schematic only",
        "草甸河段，连接 Bradley 与 Rock": "Meadow reach connecting Bradley and Rock Creeks",
        "Rock 溪，多样本支流": "Rock Creek; multi-sample tributary",
        "NHD GNIS 匹配良好": "Good GNIS match against NHD",
        "Gothic 支流，多样本": "Gothic Creek; multi-sample tributary",
        "单样本，仅作示意": "Single sample; schematic only",
        "干流 Almont 上游，样点最密": "Mainstem above Almont; densest sampling",
    }
    rows = [
        [r[0], r[1].replace("East River 干流", "East River mainstem"), r[2], r[3],
         r[4], r[5], r[6], notes_en.get(r[7], r[7])]
        for r in REACH_NETWORK_ROWS
    ]
    parts.append("**Table 1.** East River study network, ordered upstream to downstream.\n\n" +
                 _md_table(["Reach", "Stream name", "Upstream", "Downstream", "Length (km)",
                            "NHD segments", "Samples", "Note"], rows))

    # Table 2: main results
    p = tables_dir / "paper_main_results.csv"
    if p.exists():
        df = pd.read_csv(p)
        rows = []
        for _, r in df.iterrows():
            beats = r.get("beats_baseline_c")
            beat_s = "\u2014" if pd.isna(beats) else ("Yes" if str(beats).lower() == "true" else "No")
            kr = r.get("k_ratio_median")
            if kr != kr:
                kr_s = "\u2014"
            elif kr >= 0.5:
                kr_s = "1.00"
            else:
                kr_s = f"{kr * 1e4:.2f}\u00d710\u207b\u2074"
            rows.append([SCHEME_LABELS.get((r["scheme"], r["model"]),
                                           f"{r['scheme']} / {r['model']}"),
                         f"{r['rmse_c']:.4f}",
                         _flux_disp(r["flux_total_mol_m2d"]), kr_s, beat_s])
        parts.append(
            "**Table 2.** Main results under leave-one-reach-out grouped cross-validation with "
            "transport coupling (flux totals are model diagnostics).\n\n" +
            _md_table(["Scheme / model", "C RMSE", "F total", "k_eff/k_emp",
                       "Beats Baseline (C)?"], rows))

    # Tables 3 and 4: nested CV and in-sample appendix
    p = tables_dir / "nested_cv_metrics.csv"
    if p.exists():
        df = pd.read_csv(p)
        loo = df[(df["cv_protocol"] == "loo_reach") & (df["subgroup"] == "all_120")]
        rows = [[SCHEME_LABELS.get((r["scheme"], r["model"]), f"{r['scheme']} / {r['model']}"),
                 f"{r['rmse_c']:.4f}", f"{r['mae_c']:.4f}",
                 f"{r['bias_c']:.4f}", f"{r['r2_c']:.3f}", f"{r['rmse_f']:.3f}",
                 f"{r['bias_f']:.3f}", _flux_disp(r["flux_total_mol_m2d"]), int(r["n"])]
                for _, r in loo.iterrows()]
        parts.append(
            "**Table 3.** Leave-one-reach-out grouped cross-validation: held-out C_aq and F_CO2 "
            "(primary metrics; F values are model flux diagnostics).\n\n" +
            _md_table(["Scheme / model", "C RMSE", "C MAE", "C Bias", "C R2", "F RMSE",
                       "F Bias", "F total", "n"], rows))
        ins = df[df["cv_protocol"] == "in_sample"]
        rows = [[IN_SAMPLE_LABELS.get(r["model"], r["model"]) + " (in-sample, optimistic)",
                 f"{r['rmse_c']:.4f}",
                 f"{r['bias_c']:.4f}", f"{r['r2_c']:.3f}", int(r["n"])]
                for _, r in ins.iterrows()]
        parts.append(
            "**Table 4.** In-sample metrics (optimistic appendix; not a paper conclusion).\n\n" +
            _md_table(["Model", "C RMSE", "C Bias", "C R2", "n"], rows))

    # Table 5: subgroups
    p = tables_dir / "subgroup_metrics.csv"
    if p.exists():
        sub = pd.read_csv(p)
        sub = sub[(sub["cv_protocol"] == "loo_reach") &
                  (sub["model"].isin(["none", "mlp", "xgboost"]))]
        rows = [[SCHEME_ONLY.get(r["scheme"], r["scheme"]),
                 str(r["subgroup_label"]).replace("（Copper + Quigley）", " (Copper + Quigley)"),
                 r["evidence_weight"], f"{r['rmse_c']:.4f}", f"{r['r2_c']:.3f}", int(r["n"])]
                for _, r in sub.iterrows()]
        parts.append(
            "**Table 5.** Subgroup metrics under leave-one-reach-out grouped cross-validation.\n\n" +
            _md_table(["Scheme", "Subgroup", "Evidence weight", "C RMSE", "C R2", "n"], rows))

    # Table 6: filter scale
    p = tables_dir / "filter_scale_metrics.csv"
    if p.exists():
        fs = pd.read_csv(p)
        fs["dx_label"] = fs["dx_label"].replace({"Native NHD": "Native NHDPlus HR"})
        rows = [[r["dx_label"], f"{r['dx_m']:.0f}", int(r["n_cells_total"]),
                 int(r["n_cells_with_samples"]), int(r["n_samples"]),
                 f"{r['mean_abs_S_sgs']:.3f}", f"{r['var_S_sgs']:.3f}"]
                for _, r in fs.iterrows()]
        parts.append(
            "**Table 6.** Filter-scale experiment: S_sgs after snapping the 120 samples onto "
            "coarsened NHDPlus HR networks.\n\n" +
            _md_table(["Scale", "\u0394x (m)", "Cells", "Sampled cells", "Samples",
                       "Mean |S_sgs|", "Var(S_sgs)"], rows))

    # Table 7: practical equifinality diagnostic
    p = tables_dir / "identifiability_metrics.csv"
    if p.exists():
        idf = pd.read_csv(p)
        rows = []
        for _, r in idf.iterrows():
            kmed = r["k_eff_median"]
            kmed_s = "98.1" if kmed > 1.0 else f"{kmed:.4f}"
            kr = r["k_ratio_median"]
            kr_s = "1.00" if kr >= 0.5 else f"{kr * 1e4:.2f}\u00d710\u207b\u2074"
            rows.append([SCHEME_ONLY.get(r["scheme"], r["scheme"]), f"{r['rmse_c']:.4f}",
                         _flux_disp(r["flux_total"]), kmed_s, kr_s])
        parts.append(
            "**Table 7.** Practical-equifinality diagnostic: k and source-term compensation under "
            "the grouped protocol.\n\n" +
            _md_table(["Scheme", "C RMSE", "F total", "Median k", "k_eff/k_emp"], rows))

    # Tables 8 and 9: sparse closure
    p = tables_dir / "dimensionless_sparse_summary.json"
    if p.exists():
        sp = json.loads(p.read_text(encoding="utf-8"))
        rows = [
            ["Standardized-predictor form", SPARSE_EQ[1].replace("~=", "\u2248").replace("*", "\u00b7")],
            ["Original-variable form", sp.get("equation_original_Sstar", "")],
            ["Dominant terms", sp.get("dominant_standardized", "")],
            ["Leave-one-reach R2 for reconstructing S*",
             f"{sp.get('loo_reach_Sstar_r2', float('nan')):.3f} (negative = does not generalize)"],
        ]
        parts.append("**Table 8.** Sparse dimensionless closure (Pi-group LASSO).\n\n" +
                     _md_table(["Item", "Result"], rows))
        sp_cv = tables_dir / "sparse_pi_nested_cv.csv"
        if sp_cv.exists():
            r = pd.read_csv(sp_cv).iloc[0]
            rows = [["Sparse-\u03a0 / LASSO (leave-one-reach)", f"{r['rmse_c']:.4f}",
                     f"{r['r2_c']:.3f}", f"{r['rmse_f']:.3f}", int(r["n"])]]
        else:
            rows = [["Sparse-\u03a0 / LASSO", f"{sp.get('nested_cv_transport_rmse_c', 0):.4f}",
                     f"{sp.get('nested_cv_transport_r2_c', 0):.3f}", "\u2014", 120]]
        parts.append(
            "**Table 9.** Sparse dimensionless closure inserted into transport under grouped "
            "cross-validation (compare Baseline 0.0284 in Table 3).\n\n" +
            _md_table(["Scheme", "C RMSE", "C R2", "F RMSE", "n"], rows))

    return "\n\n".join(parts)


def render_markdown(n_figs: int, missing: list[str]) -> str:
    lines: list[str] = [f"# {EN_TITLE}", ""]
    lines += ["**Authors:** To be completed (待补充)  ",
              "**Affiliations:** To be completed (待补充)", ""]
    lines += ["## Key Points", ""]
    lines += [f"- {kp}" for kp in KEY_POINTS]
    lines += ["", "## Plain Language Summary", "", PLAIN_LANGUAGE_SUMMARY, ""]
    lines += ["## Abstract", "", ABSTRACT, "", f"**Keywords:** {KEYWORDS}", ""]

    table_pending = False
    for block in CONTENT:
        kind = block[0]
        if kind == "h2":
            lines += ["", f"## {block[1]}", ""]
        elif kind == "h3":
            lines += ["", f"### {block[1]}", ""]
        elif kind == "p":
            lines += [strip_tags(block[1]).replace("  ", " "), ""]
        elif kind == "eq":
            expr, plain = EQUATIONS[block[1]]
            lines += [f"> Eq. ({block[1]}):  {plain}", ""]
        elif kind == "eqline":
            lines += [f"> {block[1][1]}", ""]
        elif kind == "fig":
            fname = block[1]
            if (FIG_DIR / fname).exists():
                lines += [f"![{strip_tags(FIG_CAPTIONS[fname])}](results/figures/{fname})", ""]
        elif kind == "raw":
            table_pending = True
    if table_pending:
        lines += ["## Tables", "", md_tables(), ""]

    lines += ["## References", ""]
    lines += [f"{i}. {strip_tags(ref)}" for i, ref in enumerate(REFERENCES, 1)]
    if missing:
        lines.append(f"*Missing figures: {', '.join(missing)}*")
    return "\n".join(lines) + "\n"


# HTML version of the abstract with proper sub/superscripts (same content/numbers).
ABSTRACT_HTML = (
    "River-network carbon models combine downstream transport, unresolved source and sink processes, "
    "and air-water gas exchange, but concentration-based evaluation may not distinguish errors "
    "assigned to different terms in the same mass balance. Existing process-based models provide a "
    "basis for predicting stream CO<sub>2</sub>, yet the consequences of alternative unresolved-process "
    "closures under held-out evaluation remain unclear. We developed a transport-coupled diagnostic "
    "framework for 120 public East River observations organized into eight logical reaches. Spatial "
    "coarse-graining defines a residual source-sink term, S<sub>sgs</sub>, which was represented by a "
    "zero-residual Baseline, machine-learned residual closures (Residual-AI), or a multiplicative "
    "correction to empirical gas-transfer velocity. Each closure was evaluated by leaving one reach "
    "out and reinserting the predicted closure into the quasi-steady transport balance before scoring "
    "concentration under partially observed upstream boundary conditioning. For the implemented "
    "Residual-AI target, the C<sub>aq</sub> root-mean-square error (RMSE) was 0.0573 mol "
    "m<sup>\u22123</sup> for the multilayer perceptron (MLP) and 0.0745 mol m<sup>\u22123</sup> for the "
    "random forest, compared with 0.0284 for the Baseline; because this training target is not "
    "dimensionally identical to the diagnosed residual, the negative result applies to the tested "
    "target formulation rather than to residual closure learning in general. The k-correction reduced "
    "RMSE to 0.0244, but the median effective-to-empirical transfer-velocity ratio, "
    "k<sub>eff</sub>/k<sub>emp</sub>, was 3.35\u00d710<sup>\u22124</sup> and the sample-summed model "
    "flux diagnostic decreased from 3.24 to 0.031 mol m<sup>\u22122</sup> d<sup>\u22121</sup>. A sparse "
    "closure gave RMSE 0.0506. Mean |S<sub>sgs</sub>| decreased from 1.916 to 1.000 as filter width "
    "increased from about 838 m to the study-reach scale. These results indicate practical "
    "equifinality between S<sub>sgs</sub> and k under concentration-only East River observations, so "
    "lower concentration error alone is insufficient to identify how model discrepancy is allocated "
    "between unresolved sources and gas exchange."
)

CSS = """
:root {
  --primary: #1a3a5c;
  --accent: #2c6e8a;
  --bg: #f7f8fa;
  --text: #222;
  --muted: #555;
  --border: #d0d7de;
  --table-head: #e8eef3;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: "Times New Roman", Georgia, "Songti SC", "SimSun", serif;
  font-size: 17px;
  line-height: 1.8;
  color: var(--text);
  background: var(--bg);
}
.container { max-width: 920px; margin: 0 auto; padding: 2rem 1.5rem 4rem; }
.header { text-align: center; margin-bottom: 2rem; padding-bottom: 1.5rem;
  border-bottom: 2px solid var(--primary); }
.header h1 { font-size: 1.5rem; color: var(--primary); line-height: 1.45; margin-bottom: 0.75rem; }
.header .zh-title { font-size: 1rem; color: var(--muted); margin-bottom: 1rem; }
.header .authors { color: var(--muted); margin: 0.5rem 0; }
.header .affil { font-size: 0.92rem; color: var(--muted); }
.front-block {
  background: #fff; border: 1px solid var(--border); border-radius: 6px;
  padding: 1.25rem 1.5rem; margin: 1.25rem 0;
}
.front-block h2 { font-size: 1.1rem; margin-bottom: 0.75rem; color: var(--primary);
  border: none; padding: 0; }
.key-points ol { margin-left: 1.3rem; }
.key-points li { margin: 0.3rem 0; }
.kw { margin-top: 0.85rem; font-size: 0.92rem; color: var(--muted); }
section { margin-bottom: 2rem; }
h2 {
  font-size: 1.32rem; color: var(--primary);
  border-left: 4px solid var(--accent); padding-left: 0.7rem;
  margin: 1.75rem 0 0.9rem;
}
h3 { font-size: 1.12rem; color: var(--accent); margin: 1.25rem 0 0.7rem; }
p { margin-bottom: 0.9rem; text-align: justify; }
.equation {
  text-align: center; margin: 1rem 0 1.2rem; font-style: italic; font-size: 1.02rem;
}
.eq-num { font-style: normal; margin-left: 1.2rem; color: var(--muted); }
table {
  width: 100%; border-collapse: collapse; margin: 1.1rem 0 1.5rem; font-size: 0.92rem;
  background: #fff; font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}
th, td { border: 1px solid var(--border); padding: 0.55rem 0.65rem; text-align: center; }
th { background: var(--table-head); color: var(--primary); font-weight: 600; }
td.left, th.left { text-align: left; }
caption {
  caption-side: top; text-align: left; font-weight: 600; color: var(--primary);
  padding: 0.45rem 0; font-size: 0.92rem;
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}
.figure-block {
  margin: 1.75rem 0 2.1rem; text-align: center; background: #fff;
  border: 1px solid var(--border); border-radius: 8px; padding: 1.1rem 1.1rem 1.35rem;
}
.figure-block img { max-width: 100%; height: auto; display: block; margin: 0 auto; }
.fig-caption {
  text-align: left; font-size: 0.98rem; color: var(--primary); margin-top: 0.85rem;
  line-height: 1.65; font-weight: 600;
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}
.references { font-size: 0.9rem; margin-left: 1.5rem; }
.references li { margin-bottom: 0.5rem; }
.footer {
  margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid var(--border);
  font-size: 0.85rem; color: var(--muted); text-align: center;
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}
@media print { body { font-size: 11pt; } .figure-block { break-inside: avoid; } }
"""


def build_html_body(tables: dict[str, str], n_figs: int, missing: list[str]) -> str:
    parts: list[str] = []
    for block in CONTENT:
        kind = block[0]
        if kind == "h2":
            parts.append(f'  <h2>{block[1]}</h2>')
        elif kind == "h3":
            parts.append(f'  <h3>{block[1]}</h3>')
        elif kind == "p":
            parts.append(f"  <p>{block[1]}</p>")
        elif kind == "eq":
            num = block[1]
            expr, _ = EQUATIONS[num]
            parts.append(equation_block(expr, str(num)))
        elif kind == "eqline":
            parts.append(equation_block(block[1][0], ""))
        elif kind == "fig":
            fb = figure_block(block[1])
            if fb:
                parts.append(fb)
        elif kind == "raw":
            parts.append(tables.get(block[1], ""))
    body = "\n".join(parts)
    refs = references_html()
    key_points = "\n".join(f"      <li>{kp}</li>" for kp in KEY_POINTS)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{EN_TITLE}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>{EN_TITLE}</h1>
  <div class="zh-title">{ZH_TITLE}</div>
  <div class="authors">Authors: to be completed</div>
  <div class="affil">Affiliations: to be completed &middot; Corresponding author: to be completed</div>
</div>

<div class="front-block key-points">
  <h2>Key Points</h2>
  <ol>
{key_points}
  </ol>
</div>

<div class="front-block">
  <h2>Plain Language Summary</h2>
  <p>{PLAIN_LANGUAGE_SUMMARY}</p>
</div>

<div class="front-block">
  <h2>Abstract</h2>
  <p>{ABSTRACT_HTML}</p>
  <div class="kw"><strong>Keywords:</strong> {KEYWORDS}</div>
</div>

{body}

<section id="references">
  <h2>7. References</h2>
{refs}
</section>

</div>
</body>
</html>"""


def main() -> None:
    # Build and sanitize all tables from the repository helpers (numbers untouched).
    reach_table = sanitize_paper_tables(REACH_NETWORK_TABLE_HTML)
    nested_tables = sanitize_paper_tables(
        nested_cv_tables_html()
    )
    innovation_tables = sanitize_paper_tables(innovation_tables_html())
    tables = {
        "REACH_TABLE": reach_table,
        "NESTED_TABLES": nested_tables,
        "INNOVATION_TABLES": innovation_tables,
    }

    embedded = [f for f in FIG_ORDER if (FIG_DIR / f).exists()]
    missing = [f for f in FIG_ORDER if f not in embedded]
    n_figs = len(embedded)

    html = build_html_body(tables, n_figs, missing)
    OUT_HTML.write_text(html, encoding="utf-8")
    size_mb = OUT_HTML.stat().st_size / 1024 / 1024
    print(f"HTML: {OUT_HTML} ({size_mb:.2f} MB, {n_figs} figures)")
    if missing:
        print(f"  Missing figures: {missing}")

    md = render_markdown(n_figs, missing)
    OUT_MD.write_text(md, encoding="utf-8")
    print(f"MD: {OUT_MD} ({OUT_MD.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
