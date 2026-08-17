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
    "Learned residual closures do not beat a zero-residual baseline on held-out reaches.",
    "Lower concentration error coincides with collapse of the model CO\u2082 flux diagnostic.",
]

PLAIN_LANGUAGE_SUMMARY = (
    "Rivers take up, transform, and release carbon, and models of river carbon must represent "
    "processes that cannot be observed directly, such as groundwater CO\u2082 inputs and the exchange "
    "of gas with the atmosphere. When only concentration measurements are available, different model "
    "structures can reproduce the same observed concentrations by adjusting different process terms. "
    "Using 120 public water samples from the East River in Colorado, we compared a baseline transport "
    "model with variants that add a machine-learned source term or a corrected gas-exchange rate. The "
    "machine-learned term did not improve predictions for river reaches that were held out of training. "
    "The corrected gas-exchange rate fitted the concentrations slightly better, but only by reducing the "
    "modeled CO\u2082 release to nearly zero. Concentration data alone therefore cannot determine where "
    "model error should be assigned. Evaluations of river-carbon models should combine concentration "
    "skill with process-level diagnostics."
)

ABSTRACT = (
    "Evaluating environmental models against a single observed state can conceal compensating errors "
    "among process terms. River-network CO\u2082 models are exposed to this problem because unresolved "
    "source-sink processes and gas exchange act on the same concentration balance. We develop a "
    "transport-coupled diagnostic framework and apply it to 120 public campaign samples from the East "
    "River, Colorado, organized into eight logical reaches. Spatial coarse-graining of the reach-scale "
    "mass balance defines a subgrid residual term S_sgs, which is then closed in three ways: a "
    "zero-residual Baseline, machine-learned residual closures, and a multiplicative correction to the "
    "empirical gas-transfer velocity. Each closure is trained with one reach held out and reinserted "
    "into the quasi-steady balance before held-out concentrations are scored. The residual closures do "
    "not improve held-out prediction: C_aq RMSE is 0.0573 mol/m^3 for a multilayer perceptron and 0.0745 "
    "for a random forest, compared with 0.0284 for the Baseline. The k-correction reduces RMSE to "
    "0.0244, but the gain coincides with a median effective velocity 3.35e-4 times the empirical value "
    "and with a collapse of the sample-summed model flux diagnostic from 3.24 to 0.031 mol/m^2/day. The "
    "diagnosed residual also depends on filter scale: mean |S_sgs| falls from 1.92 to 1.00 as the filter "
    "width grows from about 838 m to the study-reach scale. Lower concentration error therefore does not "
    "uniquely identify how model discrepancy is allocated between unresolved sources and gas exchange. "
    "The contribution is methodological: an operable filter definition, a transport-coupled grouped "
    "evaluation protocol, and evidence consistent with practical equifinality under concentration-only "
    "observations."
)

KEYWORDS = (
    "river carbon cycling; environmental model evaluation; subgrid closure; gas-transfer velocity; "
    "grouped cross-validation; practical equifinality"
)

# ---------------------------------------------------------------------------
# Equations (frozen; identical to previous manuscript versions)
# ---------------------------------------------------------------------------

# number -> (html, plain)
EQUATIONS: dict[int, tuple[str, str]] = {
    1: (
        "Q(C<sub>in</sub> \u2212 C) + (A<sub>s</sub>/\u03c4<sub>d</sub>)[S<sub>sgs</sub> \u2212 k(C \u2212 C<sub>eq</sub>)] = 0",
        "Q(C_in - C) + (A_s/tau_d)[S_sgs - k(C - C_eq)] = 0",
    ),
    4: (
        "q<sub>A</sub>(C<sub>in</sub> \u2212 C) + S<sub>sgs</sub> \u2212 k(C \u2212 C<sub>eq</sub>) = 0",
        "q_A(C_in - C) + S_sgs - k(C - C_eq) = 0",
    ),
    2: ("F<sub>CO\u2082</sub> = k(C \u2212 C<sub>eq</sub>)", "F_CO2 = k(C - C_eq)"),
    5: (
        "S<sub>sgs</sub> = k(C \u2212 C<sub>eq</sub>) \u2212 q<sub>A</sub>(C<sub>in</sub> \u2212 C)",
        "S_sgs = k(C - C_eq) - q_A(C_in - C)",
    ),
    6: (
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
    "S*<sub>z</sub> \u2248 1.059 + 1.536\u00b7Fr \u2212 1.669\u00b7Slope \u2212 2.179\u00b7h/W",
    "S*_z ~= 1.059 + 1.536*Fr - 1.669*Slope - 2.179*h/W",
)

# ---------------------------------------------------------------------------
# Figures (same 13 files as before; captions rewritten as English journal captions)
# ---------------------------------------------------------------------------

FIG_CAPTIONS: dict[str, str] = {
    "les_filter_conceptual.png": (
        "<strong>Figure 1.</strong> Conceptual representation of the spatial filter. Fine NHD flowline "
        "segments are merged into filter windows of width \u0394x, and the filtered mass balance on the "
        "coarse control volume defines the subgrid residual term S<sub>sgs</sub>."
    ),
    "gis_reach_assignment_map.png": (
        "<strong>Figure 2a.</strong> Study river network: correspondence between the eight logical "
        "reaches (R001\u2013R008) and the NHD vector centerlines."
    ),
    "gis_samples_on_network.png": (
        "<strong>Figure 2b.</strong> The 120 campaign samples overlaid on the NHD river network. The "
        "mainstem reach R008 contributes 58 samples."
    ),
    "nested_cv_rmse_bar.png": (
        "<strong>Figure 3.</strong> Leave-one-reach-out grouped cross-validation with transport "
        "coupling: held-out C<sub>aq</sub> RMSE for the Baseline, Residual-AI, and k-correction "
        "closures (primary comparison)."
    ),
    "nested_cv_scatter_holdout.png": (
        "<strong>Figure 4.</strong> Observed versus transport-predicted held-out C<sub>aq</sub> for the "
        "Residual-AI (MLP) closure under the leave-one-reach-out protocol."
    ),
    "identifiability_k_vs_sgs.png": (
        "<strong>Figure 5.</strong> Identifiability diagnostics: effective gas-transfer velocity "
        "k<sub>eff</sub>, the implied source term S<sub>implied</sub>, and the Residual-AI held-out "
        "source predictions."
    ),
    "filter_scale_sgs.png": (
        "<strong>Figure 6.</strong> Filter-scale dependence: mean |S<sub>sgs</sub>| and variance of "
        "S<sub>sgs</sub> as functions of filter width \u0394x."
    ),
    "dimensionless_coefficients.png": (
        "<strong>Figure 7.</strong> Standardized LASSO coefficients of the sparse dimensionless "
        "(\u03a0-group) closure."
    ),
    "subgroup_rmse_r008_vs_trib.png": (
        "<strong>Figure S1.</strong> Subgroup errors: R008 mainstem versus multi-sample tributaries and "
        "single-sample schematic reaches."
    ),
    "ablation_flux_comparison.png": (
        "<strong>Figure S2.</strong> Sample-summed model F<sub>CO\u2082</sub> diagnostic and flux RMSE "
        "for the three closures. Model diagnostic only; no chamber validation."
    ),
    "identifiability_tradeoff.png": (
        "<strong>Figure S3.</strong> Concentration\u2013flux trade-off: k<sub>eff</sub>/k<sub>emp</sub> "
        "against held-out RMSE and the sample-summed flux diagnostic."
    ),
    "filter_scale_sgs_box.png": (
        "<strong>Figure S4.</strong> Distributions of |S<sub>sgs</sub>| for the 120 samples at each "
        "implemented filter scale."
    ),
    "obs_vs_model_scatter_large.png": (
        "<strong>Figure A1.</strong> In-sample observed-versus-predicted scatter (appendix only; "
        "in-sample R\u00b2 \u2248 0.997 reflects overfitting and is not a skill metric)."
    ),
}

FIG_ORDER = [
    "les_filter_conceptual.png",
    "gis_reach_assignment_map.png",
    "gis_samples_on_network.png",
    "nested_cv_rmse_bar.png",
    "nested_cv_scatter_holdout.png",
    "identifiability_k_vs_sgs.png",
    "filter_scale_sgs.png",
    "dimensionless_coefficients.png",
    "subgroup_rmse_r008_vs_trib.png",
    "ablation_flux_comparison.png",
    "identifiability_tradeoff.png",
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
     "Rivers are active reactors in the terrestrial carbon cycle. They transport dissolved carbon from "
     "landscapes toward the ocean, transform it through metabolism, and exchange CO\u2082 with the "
     "atmosphere along the entire network (Battin et al., 2023). Evasion of CO\u2082 from rivers and "
     "streams is a substantial component of inland-water carbon budgets, and emissions vary strongly "
     "with stream size and between day and night (Hotchkiss et al., 2015; G\u00f3mez-Gener et al., 2021). "
     "Predicting river CO\u2082 concentrations and fluxes therefore requires models that couple "
     "downstream transport, internal and external carbon sources, and atmospheric gas exchange."),
    ("p",
     "At the reach scale these processes are necessarily represented through aggregated state variables "
     "and parameterizations. Saccardi and Winnick (2021) developed a stream-network model for the East "
     "River watershed in Colorado in which advection, CO\u2082 sources, and gas exchange jointly "
     "determine downstream concentrations. Gas exchange is commonly represented through an empirical "
     "transfer velocity driven by hydraulic variables, for example the formulation of Raymond et al. "
     "(2012). Processes that remain unresolved at the reach scale, such as groundwater CO\u2082 inputs, "
     "lateral inflows, and sub-reach heterogeneity in metabolism, are difficult to observe directly. "
     "They must either be parameterized or neglected, and the resulting model error enters the same "
     "concentration balance as transport and gas exchange."),
    ("p",
     "This structure creates a specific evaluation problem. Environmental-model performance cannot be "
     "characterized by a single prediction-error statistic (Bennett et al., 2013). Discrepancies between "
     "models and observations can instead be treated as information about limitations in models, "
     "observations, or their interaction (Vilas et al., 2023), and alternative methods are best "
     "evaluated explicitly under model error (Markovich et al., 2022). For river-carbon models the "
     "practical question is the following. When several representations of unresolved processes can "
     "alter the same predicted CO\u2082 concentration, does lower concentration error identify a more "
     "credible closure? Because both an unresolved source-sink term and the gas-transfer velocity act on "
     "the same balance, their errors can compensate one another when concentrations provide the dominant "
     "observational constraint."),
    ("p",
     "Machine learning offers one route to representing unresolved terms. Learned subgrid "
     "parameterizations have been developed for climate models, where coarse-graining defines the "
     "separation between resolved and unresolved scales (Yuval &amp; O\u2019Gorman, 2020). Related work "
     "on river carbon transport is in preparation (Gao et al., manuscript in preparation). A central "
     "question for such closures is generalization. A residual can appear learnable in-sample and still "
     "fail when it is predicted for new locations, reinserted into the transport calculation, and scored "
     "against held-out observations."),
    ("p",
     "We examine this question with an explicit spatial coarse-graining experiment on public East River "
     "observations. The data consist of 120 campaign samples organized into eight logical reaches and "
     "mapped to an NHDPlus HR river-network representation. Filtering the reach-scale mass balance "
     "defines a residual source-sink term S<sub>sgs</sub>, which we close in three ways: a zero-residual "
     "Baseline, machine-learned residual closures, and a multiplicative correction to the empirical "
     "gas-transfer velocity. Evaluation is transport-coupled and grouped by reach: a closure predicted "
     "for a held-out reach is reinserted into the quasi-steady balance before concentrations are scored. "
     "The contribution is methodological rather than predictive. We provide an operable definition of a "
     "filter-induced residual, a grouped evaluation protocol that couples predicted closures back into "
     "transport, and a diagnostic for practical equifinality between source terms and gas exchange. "
     "Boundaries of the experiment, including partially observed upstream boundary conditions, strongly "
     "unequal reach support, and idealized channel geometry, are treated as part of the evaluation "
     "design."),

    ("h2", "2. Methods"),

    ("h3", "2.1 Study data and river-network representation"),
    ("p",
     "The study uses public observations from the upper East River watershed near Almont, Colorado "
     "(HUC 14020001). The water-chemistry data come from the field campaign of Saccardi and Winnick "
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
     "corridor-level filtering. Reach-to-line matching identified 85 segments through GNIS name matching "
     "and assigned the remainder by proximity to campaign coordinates; the median sample-to-centerline "
     "snap distance is 8.5 m. Discharge for the mainstem reach comes from USGS gage 09112500 (East "
     "River at Almont) on the sample dates. Tributary discharges are the published synoptic values from "
     "the campaign supplement, with no gage-ratio scaling applied."),
    ("p",
     "Two data boundaries shape the analysis. First, channel width is not measured along the corridor. "
     "Computed widths come from a coordinate-based widening proxy, with clipping, for multi-sample "
     "reaches, and from a fallback width for single-sample reaches; the width enters water depth, flow "
     "velocity, k<sub>600</sub>, and the water-surface area A<sub>s</sub> = L\u00b7W. Sensitivity of the "
     "results to this width proxy remains to be tabulated. Second, biogeochemical covariates are "
     "incomplete. DIC and DOC are available for 41 of the 120 samples, and alkalinity, nitrogen, "
     "phosphorus, and photosynthetically active radiation were not available for this campaign. A "
     "same-day merge against the Water Quality Portal returned no matching samples (0 of 120), and the "
     "StreamPULSE database contains no East River sites. These gaps constrain the covariate set "
     "available to the closures."),
    ("raw", "REACH_TABLE"),
    ("fig", "gis_reach_assignment_map.png"),
    ("fig", "gis_samples_on_network.png"),

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
     "cross-section area; if a bulk velocity is required, U = Q/A<sub>c</sub> with A<sub>c</sub> the "
     "cross-section area. Writing the balance explicitly on a daily areal basis avoids mixing time "
     "bases. Dividing Eq. (1) by A<sub>s</sub>/\u03c4<sub>d</sub> gives the equivalent form"),
    ("eq", 4),
    ("p",
     "in which q<sub>A</sub> = \u03c4<sub>d</sub>\u00b7Q/A<sub>s</sub> (m d\u207b\u00b9) is a daily "
     "area-normalized discharge and every term has units mol m\u207b\u00b2 d\u207b\u00b9."),
    ("p",
     "The role of Eq. (1) in the design is to provide one common balance into which every closure "
     "configuration is inserted. A closure is defined entirely by how it supplies S<sub>sgs</sub> and k, "
     "and all configurations are scored after the same balance is re-solved. The comparison therefore "
     "isolates the allocation of model discrepancy rather than differences in transport numerics."),
    ("p",
     "Gas exchange is summarized by the model flux density"),
    ("eq", 2),
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
     "Symbolically, k<sub>600</sub> and k<sub>emp</sub> are distinct quantities. The equilibrium "
     "concentration C<sub>eq</sub> is taken from the preprocessed campaign table, following Henry\u2019s "
     "law with atmospheric pCO\u2082 and water temperature; the full derivation will be given in a "
     "supporting appendix."),
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
     "We perform reach-local spatial coarse-graining within each logical reach. Native NHDPlus segments "
     "are merged along the network chainage into filter cells, and \u0394x is defined as the mean length "
     "of the filter cells, with sampled cells reported separately. Where a fully directed network "
     "ordering is not available, the implementation falls back to a midpoint Y-then-X coordinate "
     "ordering. This fallback is disclosed as an operator boundary; it does not change the definition of "
     "the diagnosed residual."),
    ("p",
     "The construction is analogous at the operator level to the coarse-graining used in large-eddy "
     "simulation and in learned subgrid parameterization studies (Yuval &amp; O\u2019Gorman, 2020): the "
     "filter separates resolved from unresolved contributions at a chosen scale. The analogy stops "
     "there. S<sub>sgs</sub> is not a turbulence closure and is not claimed to follow a universal "
     "river-network scaling law. Once resolved transport and gas exchange are recomputed on the filtered "
     "balance, the residual implied by the observations is"),
    ("eq", 5),
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
     "The Baseline sets S<sub>sgs</sub> = 0 and uses the Raymond-type empirical velocity "
     "k<sub>emp</sub>. It serves as a fair null closure rather than as a full independent hydrodynamic "
     "model. The comparison targets closure form and evaluation protocol, not an alternative hydraulic "
     "baseline."),
    ("p",
     "The Residual-AI configuration learns S<sub>sgs</sub> from hydraulic and water-quality covariates. "
     "Two learners are trained with a fixed seed (42): a multilayer perceptron and a random forest. The "
     "inputs include discharge, velocity, depth, width, slope, temperature, and the available carbon "
     "chemistry, as implemented in the open-source pipeline."),
    ("p",
     "The k-correction configuration leaves S<sub>sgs</sub> at zero and multiplies the empirical "
     "velocity by a learned factor, k<sub>eff</sub> = k<sub>emp</sub>\u00b7exp(g<sub>\u03b8</sub>(X)), "
     "where g<sub>\u03b8</sub> is a dimensionless correction predicted by a gradient-boosting model "
     "(XGBoost). The median ratio k<sub>eff</sub>/k<sub>emp</sub> under grouped evaluation is reported "
     "as a diagnostic of how the correction achieves its fit."),

    ("h3", "2.5 Leave-one-reach-out transport-coupled evaluation"),
    ("p",
     "Closure generalization is evaluated with leave-one-reach-out grouped cross-validation across the "
     "eight logical reaches. Each reach is held out once. Missing-value imputation and feature scaling "
     "are fitted on the training reaches only and then applied to the held-out reach. The closure is "
     "predicted for the held-out samples, reinserted into the quasi-steady balance, and only then scored "
     "against observed C<sub>aq</sub>. No inner hyperparameter-selection loop is used, so we refer to "
     "the procedure as grouped cross-validation rather than nested cross-validation."),
    ("p",
     "Two boundaries of the protocol are stated explicitly. First, when an upstream concentration state "
     "is unavailable, the solver uses the observed C<sub>aq</sub> at the current sample as a fallback "
     "boundary value c<sub>in</sub>. The experiment therefore evaluates closure generalization under "
     "partially observed boundary conditioning, not fully target-blind forecasting. Second, sampling is "
     "strongly imbalanced among reaches: R008 contributes 58 of the 120 samples, while three reaches "
     "contribute one each. Pooled errors are therefore read together with reach-level evidence weights "
     "(Table 5). A date-grouped variant is reported as a time-sensitivity analysis and is not nested "
     "inside the reach split."),

    ("h3", "2.6 Metrics and flux diagnostic"),
    ("p",
     "The primary metric is the held-out C<sub>aq</sub> RMSE in mol m\u207b\u00b3. The secondary "
     "diagnostic is the sample-summed model flux \u03a3F<sub>CO\u2082</sub> in mol m\u207b\u00b2 "
     "d\u207b\u00b9, computed from Eq. (2) with the transport-predicted concentration and the transfer "
     "velocity of each configuration: k<sub>emp</sub> for the Baseline and Residual-AI, and "
     "k<sub>eff</sub> for the k-correction. An observation-based proxy flux uses k<sub>emp</sub> with "
     "observed concentrations. Differences in \u03a3F<sub>CO\u2082</sub> across closures indicate how "
     "each configuration allocates the balance between sources and gas exchange."),

    ("h3", "2.7 Practical equifinality diagnostic"),
    ("p",
     "To characterize compensation between source terms and gas exchange, we define the implied source "
     "adjustment"),
    ("eq", 6),
    ("p",
     "At fixed concentration and resolved transport state, S<sub>implied</sub> is the source-sink "
     "adjustment that makes a model retaining k<sub>emp</sub> locally equivalent to a model that uses "
     "k<sub>eff</sub> and no additional source term. A large S<sub>implied</sub> together with a small "
     "change in concentration error indicates that the observations do not distinguish between the two "
     "allocations. We describe this behaviour as practical equifinality, or compensating closure "
     "behaviour. The diagnostic is algebraic and empirical; it is not a formal proof of structural "
     "non-identifiability."),

    ("h3", "2.8 Sparse dimensionless closure"),
    ("p",
     "A final experiment asks whether the residual admits a compact dimensionless representation. "
     "Candidate \u03a0-group features are assembled from the hydraulic state: Froude number Fr, slope, "
     "relative depth h/W, and the logarithms of the Reynolds and Damk\u00f6hler numbers. A standardized "
     "LASSO selects terms within each cross-validation fold, following the spirit of sparse discovery "
     "methods (Xie et al., 2022); PySINDy was not available in the environment, so the selection uses a "
     "scikit-learn LASSO middleware. The resulting form is reported in standardized (z-score) space and "
     "reinserted into the transport calculation under the same leave-one-reach-out protocol as the other "
     "closures. Compactness is tested against predictive utility; the two are not assumed to coincide."),

    ("h2", "3. Results"),
    ("p",
     "The results follow an evidence ladder. We first report the primary grouped evaluation of the three "
     "closures, then the concentration\u2013flux disagreement that motivates the equifinality "
     "diagnostic, then the filter-scale behaviour of the diagnosed residual, and finally the sparse "
     "dimensionless form. All metrics come from the repository evaluation tables."),

    ("h3", "3.1 Residual closures do not improve held-out concentration prediction"),
    ("p",
     "The primary result is negative. Under leave-one-reach-out transport-coupled evaluation, neither "
     "residual closure improves on the Baseline (Tables 2 and 3; Figure 3). The held-out "
     "C<sub>aq</sub> RMSE is 0.0284 mol m\u207b\u00b3 for the Baseline, 0.0573 for the Residual-AI "
     "multilayer perceptron, and 0.0745 for the random forest. The corresponding MAE values are 0.0132, "
     "0.0326, and 0.0301, and the residual closures show positive concentration bias (0.0177 and "
     "0.0180) where the Baseline bias is \u22120.0132. The date-grouped sensitivity gives the same "
     "ordering (0.0284, 0.0591, and 0.0747)."),
    ("p",
     "The subgroup decomposition locates the error (Table 5; Figures 4 and S1). On the mainstem reach "
     "R008, both residual closures are slightly better than the Baseline: RMSE is 0.0121 for the MLP and "
     "0.0087 for the random forest against 0.0136 for the Baseline. On the multi-sample tributaries the "
     "pattern reverses: RMSE is 0.0381 for the Baseline, 0.0808 for the MLP, and 0.1058 for the random "
     "forest. The pooled degradation is therefore driven by reaches with moderate sample support, where "
     "training data for the residual are sparse and heterogeneous. The holdout scatter (Figure 4) shows "
     "the same structure: mainstem predictions cluster near the observations while tributary predictions "
     "spread widely."),
    ("raw", "NESTED_TABLES"),
    ("fig", "nested_cv_rmse_bar.png"),
    ("fig", "nested_cv_scatter_holdout.png"),
    ("fig", "subgroup_rmse_r008_vs_trib.png"),

    ("h3", "3.2 A corrected gas-transfer velocity lowers concentration error"),
    ("p",
     "The k-correction is the only configuration that reduces held-out concentration error below the "
     "Baseline. Its C<sub>aq</sub> RMSE is 0.0244 mol m\u207b\u00b3 against 0.0284 for the Baseline, "
     "and MAE falls from 0.0132 to 0.0046 (Tables 2 and 3). The improvement is achieved entirely "
     "through the transfer velocity. The median effective velocity is 0.0329 m d\u207b\u00b9, compared "
     "with a median empirical value of 98.1 m d\u207b\u00b9; the median ratio "
     "k<sub>eff</sub>/k<sub>emp</sub> is 3.35\u00d710\u207b\u2074 (Table 7; Figure 5). The correction "
     "therefore does not fine-tune gas exchange. It switches gas exchange almost off."),
    ("fig", "identifiability_k_vs_sgs.png"),

    ("h3", "3.3 The concentration gain coincides with collapse of the flux diagnostic"),
    ("p",
     "The flux diagnostic separates the closures. The sample-summed model flux \u03a3F<sub>CO\u2082</sub> "
     "is 3.24 mol m\u207b\u00b2 d\u207b\u00b9 for the Baseline and 0.031 for the k-correction (Table 7; "
     "Figure S2). The concentration improvement of the k-correction coincides with a collapse of the "
     "modeled CO\u2082 release by roughly two orders of magnitude. The Residual-AI configuration moves "
     "in the opposite direction, with \u03a3F<sub>CO\u2082</sub> of 69.5, because its predicted sources "
     "add to the balance while k remains at k<sub>emp</sub>."),
    ("p",
     "No independent evasion observations are available for this campaign, so these values do not show "
     "that the Baseline flux is correct or that the corrected flux is wrong. They show that "
     "concentration performance alone can favor a markedly different allocation of the model balance. "
     "The implied-source diagnostic makes the compensation explicit. At fixed concentrations, the mean "
     "implied adjustment S<sub>implied</sub> is 1.00 mol m\u207b\u00b2 d\u207b\u00b9, the mean "
     "Residual-AI prediction is 0.56, and the two are anti-correlated across samples (Spearman "
     "\u22120.57; Table 7; Figure S3). A positive source term and a reduced transfer velocity act on the "
     "concentration balance in compensating directions, and the held-out concentration metric does not "
     "distinguish them."),
    ("raw", "INNOVATION_TABLES"),
    ("fig", "ablation_flux_comparison.png"),
    ("fig", "identifiability_tradeoff.png"),

    ("h3", "3.4 The diagnosed residual depends on filter scale"),
    ("p",
     "The magnitude of the diagnosed residual varies systematically with the filter width (Table 6; "
     "Figure 6). Mean |S<sub>sgs</sub>| is 1.916 mol m\u207b\u00b2 d\u207b\u00b9 at the native NHD "
     "resolution (\u0394x \u2248 838 m), decreases to 1.120 and 1.050 at successive merging levels, and "
     "reaches 1.000 at the study-reach scale (\u0394x \u2248 26,086 m; 7 cells, of which 6 contain "
     "samples). The variance of S<sub>sgs</sub> falls from 22.4 to 2.20 over the same range (Figure "
     "S4). The result indicates that the diagnosed closure residual depends on the spatial "
     "representation used to separate resolved from unresolved contributions. It is an empirical scale "
     "dependence for the implemented reach-local operator, not a universal scaling law."),
    ("fig", "filter_scale_sgs.png"),
    ("fig", "filter_scale_sgs_box.png"),

    ("h3", "3.5 A sparse dimensionless closure is compact but not predictive"),
    ("p",
     "The standardized LASSO retains three of the five candidate \u03a0 terms (Table 8; Figure 7). In "
     "standardized space the closure is"),
    ("eqline", SPARSE_EQ),
    ("p",
     "with Froude number the positive contributor and slope and relative depth the negative "
     "contributors. Under the same leave-one-reach-out transport-coupled protocol, the sparse closure "
     "gives a held-out C<sub>aq</sub> RMSE of 0.0506 mol m\u207b\u00b3, above the Baseline value of "
     "0.0284 (Table 9). The leave-one-reach R\u00b2 for S* itself is \u22122.74. The sparse form is "
     "therefore useful as a compact diagnostic description of the residual but does not recover "
     "predictive skill on held-out reaches."),
    ("fig", "dimensionless_coefficients.png"),

    ("h3", "3.6 In-sample fit (appendix)"),
    ("p",
     "For completeness, the in-sample fit of the residual model is reported in Table 4 and Figure A1, "
     "with R\u00b2 \u2248 0.997 and RMSE 0.00127 mol m\u207b\u00b3. The same 120 rows are used for "
     "training and prediction, so the value describes the capacity of the learner to memorize the sample "
     "rather than its generalization. It is not used as a paper metric."),
    ("fig", "obs_vs_model_scatter_large.png"),

    ("h2", "4. Discussion"),

    ("h3", "4.1 Failed generalization of residual closures is a modelling diagnosis"),
    ("p",
     "The most direct result is negative, and it is informative. The residual closures reproduce the "
     "observations well in-sample but degrade held-out concentration prediction relative to a "
     "zero-residual Baseline. This pattern indicates that the residual diagnosed from the present "
     "resolved model, predictors, spatial representation, and sampling design does not carry enough "
     "transferable structure to improve predictions after transport coupling. In the evaluation logic of "
     "Bennett et al. (2013) and Vilas et al. (2023), the discrepancy is itself diagnostic: it separates "
     "apparent learnability from held-out usefulness. The subgroup evidence points to where the transfer "
     "fails. Tributary reaches with moderate sample counts carry heterogeneous residual behaviour, and "
     "learners trained across reaches do not extrapolate there; the mainstem reach, with 58 samples, is "
     "the only subgroup where the residual closures are competitive. A practical implication is that "
     "learned residual closures for river networks need reach-level diagnostics and balanced sampling "
     "before pooled metrics can be interpreted."),

    ("h3", "4.2 Concentration skill does not uniquely determine process allocation"),
    ("p",
     "The k-correction provides the complementary result. It achieves the lowest concentration error of "
     "any configuration, and it does so by reducing the effective transfer velocity by roughly three "
     "orders of magnitude. Because both source terms and gas exchange act on the same balance, a "
     "near-zero k can be offset by the existing gradient (C \u2212 C<sub>eq</sub>) and still reproduce "
     "concentrations. The collapse of \u03a3F<sub>CO\u2082</sub> from 3.24 to 0.031 shows what this fit "
     "implies for the process budget. Without independent evasion measurements, the data cannot "
     "adjudicate between the Baseline and corrected allocations. The lower RMSE is evidence of improved "
     "concentration fit. It is not independent evidence of improved process fidelity."),

    ("h3", "4.3 Practical equifinality is restricted to a closure-compensation mode"),
    ("p",
     "We use practical equifinality in a deliberately restricted sense. Eq. (6) defines an algebraic "
     "direction along which a change in gas exchange can be compensated by an additional source-sink "
     "term at fixed concentration and transport state. The Baseline/k-correction contrast shows that "
     "this direction is consequential in the present experiment: similar concentration errors coexist "
     "with markedly different transfer velocities and flux diagnostics. This is not a formal "
     "structural-identifiability analysis, and it does not establish statistical equivalence between the "
     "competing predictions. It supports the narrower conclusion that concentration-dominated evaluation "
     "does not uniquely constrain how discrepancy is allocated between S<sub>sgs</sub> and k in this "
     "configuration. The degraded RMSE of the MLP, random forest, and sparse closures is not "
     "equifinality evidence. It shows that closure choice matters and that flexible residual learning "
     "did not generalize here."),

    ("h3", "4.4 Scale dependence belongs to the diagnosed residual"),
    ("p",
     "The filter-scale results show that the diagnosed residual is not a fixed property of the "
     "watershed. Its magnitude changes as the filter width changes, because the split between resolved "
     "and unresolved contributions is defined by the filter. This interpretation is bounded by the "
     "implemented operator, which uses reach-local merging and a coordinate-ordering fallback rather "
     "than a fully directed network filter. Within those boundaries, the result is consistent with the "
     "coarse-graining logic used elsewhere for learned subgrid terms (Yuval &amp; O\u2019Gorman, 2020): "
     "the statistics of the unresolved term depend on resolution. It does not support a universal "
     "scaling claim for river-network CO\u2082 sources."),

    ("h3", "4.5 Sparsity does not imply predictive sufficiency"),
    ("p",
     "The sparse dimensionless closure provides a counterpoint to the flexible learners. It identifies a "
     "limited set of candidate dependencies, with Froude number, slope, and relative depth surviving "
     "selection. Its compactness, however, does not transfer into held-out skill: RMSE remains above the "
     "Baseline and the S* reconstruction fails under reach holdout. Sparsity should therefore not be "
     "conflated with validated interpretability or with predictive sufficiency. In this experiment the "
     "\u03a0-group formulation is most useful as a diagnostic simplification: it asks whether the "
     "residual can be summarized compactly while retaining cross-reach utility, and the answer under the "
     "present protocol is negative."),

    ("h3", "4.6 Implications for environmental-model evaluation"),
    ("p",
     "Taken together, the results favor an evaluation strategy in which predictive error and "
     "process-sensitive diagnostics are considered jointly. A closure that lowers concentration error "
     "deserves scrutiny of the process allocation that produces the lowering, particularly when the "
     "observations constrain only concentrations."),
    ("p",
     "The present conclusions are bounded by partially observed upstream conditioning, strongly unequal "
     "reach support, the coordinate-based ordering fallback, idealized hydraulic geometry, incomplete "
     "covariates (alkalinity, nitrogen, phosphorus, photosynthetically active radiation), and the "
     "absence of independent evasion measurements. The Water Quality Portal merge and the StreamPULSE "
     "search returned no usable additional constraints for this campaign. These limitations restrict "
     "inference to the East River experiment. They also identify the observations that would most help "
     "to discriminate closures: improved upstream boundary information, better-resolved channel "
     "geometry, more balanced reach sampling, and independent constraints on gas exchange. The central "
     "implication is not that one closure should replace another. It is that lower concentration error "
     "alone is insufficient to determine which allocation of unresolved processes is better supported."),

    ("h2", "5. Conclusions"),
    ("p",
     "Three conclusions follow from the East River experiment. First, machine-learned residual closures "
     "do not improve held-out concentration prediction at the scale of these observations: the "
     "Residual-AI RMSE of 0.0573 mol m\u207b\u00b3 for the MLP exceeds the Baseline value of 0.0284. "
     "Second, under concentration-only observations, the source term S<sub>sgs</sub> and the transfer "
     "velocity k exhibit practical equifinality: the k-correction lowers concentration RMSE to 0.0244 "
     "while the sample-summed model flux diagnostic falls from 3.24 to 0.031 mol m\u207b\u00b2 "
     "d\u207b\u00b9. Third, the experiment demonstrates an operable diagnostic workflow, combining "
     "spatial aggregation, grouped reach holdout, and transport coupling, within which a sparse "
     "dimensionless closure is compact but does not recover Baseline generalization. The contribution is "
     "methodological: a filter definition, an evaluation protocol, and evidence of closure compensation. "
     "The conclusions are bounded accordingly: no accuracy gain is claimed, flux values are model "
     "diagnostics rather than validated evasion estimates, and transfer to other basins has not been "
     "tested."),

    ("h2", "6. Data availability"),
    ("p",
     "The East River water-chemistry and pCO\u2082 data are publicly available through HydroShare "
     "(resource 9f907b46baa848e180c49339d605bf31; Saccardi &amp; Winnick, 2021). The DIC supplement, "
     "network shapefiles, and hydraulic tables are in HydroShare resource "
     "2a2132999fb84214aad0596783812db2. Mainstem discharge is from USGS gage 09112500. River-network "
     "geometry uses NHDPlus HR flowlines for HUC 14020001. Processed tables, figures, and the analysis "
     "code are maintained in the public repository "
     "(https://github.com/Coucou2016/river-carbon-transport). A StreamPULSE search found no East River "
     "sites, and a same-day Water Quality Portal merge returned no samples for the 120 campaign records; "
     "both negative results are reported as resolved data-availability checks."),
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
    "assimilation approaches to cope with groundwater model error. <em>Environmental Modelling &amp; "
    "Software</em>, 158, 105498. https://doi.org/10.1016/j.envsoft.2022.105498",
    "Raymond, P. A., et al. (2012). Scaling the gas transfer velocity and hydraulic geometry in streams "
    "and small rivers. <em>Limnology and Oceanography: Fluids and Environments</em>, 2, 41\u201353. "
    "https://doi.org/10.1215/21573689-1597669",
    "Saccardi, B., &amp; Winnick, M. J. (2021). Improving predictions of stream CO\u2082 concentrations "
    "and fluxes using a stream network model. <em>Global Biogeochemical Cycles</em>, 35, "
    "e2021GB006972. https://doi.org/10.1029/2021GB006972",
    "Vilas, M. P., et al. (2023). TALKS: A systematic framework for resolving model-data discrepancies. "
    "<em>Environmental Modelling &amp; Software</em>, 166, 105668. "
    "https://doi.org/10.1016/j.envsoft.2023.105668",
    "Xie, X., Samaei, A., Guo, J., Liu, W. K., &amp; Gan, Z. (2022). Data-driven discovery of "
    "dimensionless numbers and governing laws from scarce measurements. <em>Nature Communications</em>, "
    "13, 7402. https://doi.org/10.1038/s41467-022-35084-w",
    "Yuval, J., &amp; O\u2019Gorman, P. A. (2020). Stable machine-learning parameterization of subgrid "
    "processes for climate modeling. <em>Nature Communications</em>, 11, 3710. "
    "https://doi.org/10.1038/s41467-020-17142-3",
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
         "<caption>Table 5. Subgroup metrics under leave-one-reach-out cross-validation. Mainstem and "
         "tributary reaches are not equally weighted.</caption>"),
        (r"<caption>表 6 滤波尺度实验.*?</caption>",
         "<caption>Table 6. Filter-scale experiment: S<sub>sgs</sub> diagnosed after snapping the 120 "
         "samples onto coarsened NHDPlus HR HUC 14020001 networks.</caption>"),
        (r"<caption>表 7 可辨识性.*?</caption>",
         "<caption>Table 7. Identifiability: trade-off between k and S<sub>sgs</sub> under the same "
         "leave-one-reach-out transport-coupled protocol.</caption>"),
        (r"<caption>表 8b 无量纲稀疏式代入输运后.*?</caption>",
         "<caption>Table 9. Sparse dimensionless closure inserted into transport under grouped "
         "cross-validation (compare the Baseline value of 0.0284 in Table 3).</caption>"),
        (r"<caption>表 8 无量纲稀疏闭合.*?</caption>",
         "<caption>Table 8. Sparse dimensionless closure (\u03a0-group LASSO; PySINDy not "
         "installed).</caption>"),
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
        ("<th>平均 |S|</th><th>Var(S)</th>", "<th>Mean |S|</th><th>Var(S)</th>"),
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
        ("标准化式", "Standardized form"),
        ("原始变量式", "Original-variable form"),
        ("主导项", "Dominant terms"),
        ("对 S* 的留一河段 R²", "Leave-one-reach R\u00b2 on S*"),
        ("<td>否</td>", "<td>No</td>"),
        ("<td>是</td>", "<td>Yes</td>"),
    ]
    for old, new in cell_map:
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
            kr_s = f"{kr:.5f}" if kr == kr else "\u2014"
            rows.append([f"{r['scheme']} / {r['model']}", f"{r['rmse_c']:.4f}",
                         f"{r['flux_total_mol_m2d']:.3f}", kr_s, beat_s])
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
        rows = [[f"{r['scheme']} / {r['model']}", f"{r['rmse_c']:.4f}", f"{r['mae_c']:.4f}",
                 f"{r['bias_c']:.4f}", f"{r['r2_c']:.3f}", f"{r['rmse_f']:.3f}",
                 f"{r['bias_f']:.3f}", f"{r['flux_total_mol_m2d']:.2f}", int(r["n"])]
                for _, r in loo.iterrows()]
        parts.append(
            "**Table 3.** Leave-one-reach-out grouped cross-validation: held-out C_aq and F_CO2 "
            "(primary metrics; F values are model flux diagnostics).\n\n" +
            _md_table(["Scheme / model", "C RMSE", "C MAE", "C Bias", "C R2", "F RMSE",
                       "F Bias", "F total", "n"], rows))
        ins = df[df["cv_protocol"] == "in_sample"]
        rows = [[f"{r['model']} (in-sample, optimistic)", f"{r['rmse_c']:.5f}",
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
        rows = [[r["scheme"],
                 str(r["subgroup_label"]).replace("（Copper + Quigley）", " (Copper + Quigley)"),
                 r["evidence_weight"], f"{r['rmse_c']:.4f}", f"{r['r2_c']:.3f}", int(r["n"])]
                for _, r in sub.iterrows()]
        parts.append(
            "**Table 5.** Subgroup metrics under leave-one-reach-out cross-validation.\n\n" +
            _md_table(["Scheme", "Subgroup", "Evidence weight", "C RMSE", "C R2", "n"], rows))

    # Table 6: filter scale
    p = tables_dir / "filter_scale_metrics.csv"
    if p.exists():
        fs = pd.read_csv(p)
        rows = [[r["dx_label"], f"{r['dx_m']:.0f}", int(r["n_cells_total"]),
                 int(r["n_cells_with_samples"]), int(r["n_samples"]),
                 f"{r['mean_abs_S_sgs']:.3f}", f"{r['var_S_sgs']:.3f}"]
                for _, r in fs.iterrows()]
        parts.append(
            "**Table 6.** Filter-scale experiment: S_sgs after snapping the 120 samples onto "
            "coarsened NHDPlus HR networks.\n\n" +
            _md_table(["Scale", "dx (m)", "Cells", "Sampled cells", "Samples",
                       "Mean |S|", "Var(S)"], rows))

    # Table 7: identifiability
    p = tables_dir / "identifiability_metrics.csv"
    if p.exists():
        idf = pd.read_csv(p)
        rows = [[r["scheme"], f"{r['rmse_c']:.4f}", f"{r['flux_total']:.2f}",
                 f"{r['k_eff_median']:.3f}", f"{r['k_ratio_median']:.5f}"]
                for _, r in idf.iterrows()]
        parts.append(
            "**Table 7.** Identifiability: k versus S_sgs under the same grouped protocol.\n\n" +
            _md_table(["Scheme", "C RMSE", "F total", "Median k", "k_eff/k_emp"], rows))

    # Tables 8 and 9: sparse closure
    p = tables_dir / "dimensionless_sparse_summary.json"
    if p.exists():
        sp = json.loads(p.read_text(encoding="utf-8"))
        rows = [
            ["Standardized form", sp.get("equation_standardized_Sstar", "")],
            ["Original-variable form", sp.get("equation_original_Sstar", "")],
            ["Dominant terms", sp.get("dominant_standardized", "")],
            ["Leave-one-reach R2 on S*",
             f"{sp.get('loo_reach_Sstar_r2', float('nan')):.3f} (negative = does not generalize)"],
        ]
        parts.append("**Table 8.** Sparse dimensionless closure (Pi-group LASSO).\n\n" +
                     _md_table(["Item", "Result"], rows))
        sp_cv = tables_dir / "sparse_pi_nested_cv.csv"
        if sp_cv.exists():
            r = pd.read_csv(sp_cv).iloc[0]
            rows = [["sparse_pi / lasso_pi (leave-one-reach)", f"{r['rmse_c']:.4f}",
                     f"{r['r2_c']:.3f}", f"{r['rmse_f']:.3f}", int(r["n"])]]
        else:
            rows = [["sparse_pi", f"{sp.get('nested_cv_transport_rmse_c', 0):.4f}",
                     f"{sp.get('nested_cv_transport_r2_c', 0):.3f}", "\u2014", 120]]
        parts.append(
            "**Table 9.** Sparse dimensionless closure inserted into transport under grouped "
            "cross-validation (compare Baseline 0.0284 in Table 3).\n\n" +
            _md_table(["Scheme", "C RMSE", "C R2", "F RMSE", "n"], rows))

    return "\n\n".join(parts)


def render_markdown(n_figs: int, missing: list[str]) -> str:
    lines: list[str] = [f"# {EN_TITLE}", ""]
    lines += [f"**Chinese title (metadata only):** {ZH_TITLE}", ""]
    lines += ["**Authors:** To be completed (待补充)  ",
              "**Affiliations:** To be completed (待补充)  ",
              f"**Date:** 2026-08-17  ",
              f"**Figures:** {n_figs} embedded in paper.html", ""]
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
            if not table_pending:
                lines += ["*(Tables 1\u20139 are rendered below.)*", ""]
                table_pending = True
    if table_pending:
        lines += ["## Tables", "", md_tables(), ""]

    lines += ["## References", ""]
    lines += [f"{i}. {strip_tags(ref)}" for i, ref in enumerate(REFERENCES, 1)]
    lines += ["", f"*Self-contained HTML with {n_figs} embedded figures: paper.html (no CDN).*"]
    if missing:
        lines.append(f"*Missing figures: {', '.join(missing)}*")
    return "\n".join(lines) + "\n"


# HTML version of the abstract with proper sub/superscripts (same content/numbers).
ABSTRACT_HTML = (
    "Evaluating environmental models against a single observed state can conceal compensating errors "
    "among process terms. River-network CO<sub>2</sub> models are exposed to this problem because "
    "unresolved source-sink processes and gas exchange act on the same concentration balance. We "
    "develop a transport-coupled diagnostic framework and apply it to 120 public campaign samples from "
    "the East River, Colorado, organized into eight logical reaches. Spatial coarse-graining of the "
    "reach-scale mass balance defines a subgrid residual term S<sub>sgs</sub>, which is then closed in "
    "three ways: a zero-residual Baseline, machine-learned residual closures, and a multiplicative "
    "correction to the empirical gas-transfer velocity. Each closure is trained with one reach held out "
    "and reinserted into the quasi-steady balance before held-out concentrations are scored. The "
    "residual closures do not improve held-out prediction: C<sub>aq</sub> RMSE is 0.0573 mol "
    "m<sup>\u22123</sup> for a multilayer perceptron and 0.0745 for a random forest, compared with "
    "0.0284 for the Baseline. The k-correction reduces RMSE to 0.0244, but the gain coincides with a "
    "median effective velocity 3.35\u00d710<sup>\u22124</sup> times the empirical value and with a "
    "collapse of the sample-summed model flux diagnostic from 3.24 to 0.031 mol m<sup>\u22122</sup> "
    "d<sup>\u22121</sup>. The diagnosed residual also depends on filter scale: mean "
    "|S<sub>sgs</sub>| falls from 1.92 to 1.00 as the filter width grows from about 838 m to the "
    "study-reach scale. Lower concentration error therefore does not uniquely identify how model "
    "discrepancy is allocated between unresolved sources and gas exchange. The contribution is "
    "methodological: an operable filter definition, a transport-coupled grouped evaluation protocol, "
    "and evidence consistent with practical equifinality under concentration-only observations."
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
    missing_note = f" &middot; missing figures: {', '.join(missing)}" if missing else ""

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
  <div class="affil" style="margin-top:0.6rem;">Target journals: Environmental Modelling &amp;
  Software / Water Resources Research &middot; Manuscript date: 2026-08-17 &middot;
  {n_figs} embedded figures</div>
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

<div class="footer">
  paper.html &middot; IMRaD methods paper &middot; {n_figs} figures base64-embedded &middot; no CDN
  &middot; Residual-AI does not beat Baseline{missing_note}
</div>
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
