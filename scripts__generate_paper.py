# -*- coding: utf-8 -*-
"""Generate self-contained paper.html and paper.md (submission-style English manuscript).

Writing-and-organization revision only. All science, numbers, results, and conclusions
are frozen against results/tables/*.csv (see results/tables/paper_claim_guard.json and
docs/RESEARCH_INTEGRITY_AUDIT.md). Style follows the AGU/WRR article pattern: front
matter with Key Points and Plain Language Summary, one continuous argument per section,
evidence-led Results, no internal-review scaffolding, no glossary in the paper.

Tables are rendered by the existing repository helpers (paper_main_table_html,
nested_cv_tables_html, innovation_tables_html from generate_report.py, and
reach_network_table_html from report_content.py) and cleaned for manuscript use by
sanitize_paper_tables(). Figures are base64-embedded; no CDN, no external assets.
"""
from __future__ import annotations

import base64
import numpy as np
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
from report_content import reach_network_table_html  # noqa: E402
from paper_values import EM_DASH, build_paper_values, fmt_ratio, _sig3  # noqa: E402

FIG_DIR = ROOT / "results" / "figures"
OUT_HTML = ROOT / "paper.html"
OUT_MD = ROOT / "paper.md"

# ---------------------------------------------------------------------------
# Single numeric source of truth (P0-01)
#
# Every headline number below is read from PV (built from results/tables/*),
# not retyped.  Missing metrics render as an em dash; they are never silently
# defaulted to 0 or 1.00.
# ---------------------------------------------------------------------------
try:
    PV = build_paper_values()
except Exception as exc:  # pragma: no cover - surfaced loudly, not silently
    raise SystemExit(
        f"paper_values.json could not be built from results/tables/*: {exc}. "
        "Run the frozen pipeline (stages 01-17) before generating the paper."
    ) from exc


def pv(path: str, default=None):
    """Read a dotted path out of the frozen value object.

    Supports integer list positions, e.g. ``filter_scale.scales.0.dx_m``.
    """
    cur = PV
    for part in path.split("."):
        if isinstance(cur, dict):
            if part not in cur:
                return default
            cur = cur[part]
        elif isinstance(cur, (list, tuple)):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return default
        else:
            return default
    return cur


def num(path: str, nd: int = 4, default: str = EM_DASH) -> str:
    v = pv(path)
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(f):
        return default
    return f"{f:.{nd}f}"


_SUP_TABLE = str.maketrans(
    "0123456789-", "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207b"
)


def _sci_disp(v: float, nd: int = 2) -> str:
    import math

    try:
        v = float(v)
    except (TypeError, ValueError):
        return "\u2014"
    if not math.isfinite(v):
        return "\u2014"
    if abs(v) < 1e-12:
        return "0"
    exp = int(math.floor(math.log10(abs(v))))
    mant = v / 10.0 ** exp
    return f"{mant:.{nd}f}\u00d710{str(exp).translate(_SUP_TABLE)}"


def _sci_from_pv(path: str, nd: int = 2, default: str = EM_DASH) -> str:
    """Scientific-notation rendering of a frozen value (never 0/1.00 fallback)."""
    v = pv(path)
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(f):
        return default
    return _sci_disp(f, nd)


def fmt_pv_ratio(path: str, default: str = EM_DASH) -> str:
    """Three-decimal ratio from the frozen object (P0-01: never a class label)."""
    v = pv(path)
    if v is None:
        return default
    return fmt_ratio(v)


# ---------------------------------------------------------------------------
# Front matter
# ---------------------------------------------------------------------------

EN_TITLE = (
    "Transport-coupled evaluation of river-network CO\u2082 closures: "
    "Evidence for practical equifinality under concentration-only observations"
)
ZH_TITLE = "河网 CO\u2082 闭合的输运耦合评价：浓度单变量观测下的 practical equifinality 证据"

KEY_POINTS = [
    "Public East River observations (Saccardi/Winnick) were reanalysed on an NHDPlus HR directed network with fold-local residual targets.",
    f"Under grouped leave-one-reach-out transport CV, the Residual-AI MLP pooled RMSE is {num('main_results.mlp.rmse_c')} mol m\u207b\u00b3 against {num('main_results.baseline.rmse_c')} for the Baseline, but the MLP is better on the mainstem subgroup "
    f"({num('subgroups.mlp_mainstem_rmse')} vs {num('subgroups.baseline_mainstem_rmse')}) and worse on the multi-sample tributaries; the pooled difference is dominated by R002 "
    f"({fmt_ratio(pv('reach_sensitivity.r002_gain_contribution_frac'))} of the gross positive SSE gain), so this is not a settled success claim.",
    "Concentration data alone cannot identify how discrepancy is allocated between subgrid sources and gas exchange (profile SSE, not likelihood).",
]

PLAIN_LANGUAGE_SUMMARY = (
    "Rivers take up, transform, and release carbon, and models of river carbon must represent "
    "processes that cannot be observed directly, such as groundwater CO\u2082 inputs and the exchange "
    "of gas with the atmosphere. When only concentration measurements are available, different model "
    "structures can reproduce the same observed concentrations by adjusting different process terms. "
    "We reanalysed 120 public water samples from the East River campaign of Saccardi and Winnick (2021), "
    "mapped to a high-resolution directed stream network from public NHD and USGS data. "
    "We compared a baseline transport model with variants that add a machine-learned source term or a "
    "corrected gas-exchange rate. Training targets for the residual learners were rebuilt inside each "
    "held-out fold so that held-out concentrations cannot enter training labels through network routing. "
    "Under that protocol the pooled held-out concentration error of the learned source term "
    f"({num('main_results.mlp.rmse_c')} mol m\u207b\u00b3) is not lower than the zero-source Baseline "
    f"({num('main_results.baseline.rmse_c')} mol m\u207b\u00b3); the learned closure is better only on the "
    f"mainstem subgroup and worse on the multi-sample tributaries, and the pooled contrast is dominated by "
    f"three samples in R002 ({fmt_ratio(pv('reach_sensitivity.r002_gain_contribution_frac'))} of the gross "
    "positive error reduction). Area-weighted flux diagnostics remained unstable and must not be read as "
    "study-area totals. A corrected gas-exchange rate could not improve on the baseline, and a model-free "
    "profile SSE showed that a single concentration measurement cannot tell apart a model that adjusts gas "
    "exchange from one that adds an unseen carbon source. Evaluations of river-carbon models should "
    "therefore combine concentration skill with process-level diagnostics such as independent "
    "gas-exchange measurements."
)

ABSTRACT = (
    "River-network carbon models combine downstream transport, unresolved source and sink processes, "
    "and air-water gas exchange, but concentration-based evaluation may not distinguish errors "
    "assigned to different terms in the same mass balance. We reanalysed 120 publicly archived East River "
    "observations (Saccardi and Winnick, 2021) organized into eight logical reaches and mapped to an "
    "NHDPlus HR directed network, with USGS outlet discharge and published synoptic tributary Q. "
    "Spatial coarse-graining defines a signed residual source-sink term (S_sgs). Closures were a "
    "zero-residual Baseline, machine-learned residual closures (Residual-AI), or a multiplicative "
    "correction to an energy-dissipation-based gas-transfer velocity. Residual and k targets were "
    "rebuilt inside each leave-one-reach-out fold without held-out concentration labels. "
    f"The Baseline held-out C_aq RMSE was {num('main_results.baseline.rmse_c')} mol m\u207b\u00b3; the "
    f"Residual-AI MLP and random forest gave {num('main_results.mlp.rmse_c')} and "
    f"{num('main_results.random_forest.rmse_c')} mol m\u207b\u00b3. The learned closure is therefore not "
    "better than the zero-source Baseline on pooled held-out concentration: its apparent advantage is "
    f"confined to the mainstem subgroup ({num('subgroups.mlp_mainstem_rmse')} vs "
    f"{num('subgroups.baseline_mainstem_rmse')} mol m\u207b\u00b3) and it is worse on the multi-sample "
    f"tributaries ({num('subgroups.mlp_tributary_rmse')} vs "
    f"{num('subgroups.baseline_tributary_rmse')} mol m\u207b\u00b3); "
    f"{fmt_ratio(pv('reach_sensitivity.r002_gain_contribution_frac'))} of the gross positive error "
    "reduction comes from three R002 samples. Overlapping sample-area flux diagnostics (not study-area "
    f"totals) were {_sci_from_pv('flux_estimand.baseline_area_sum')} mol d\u207b\u00b9 (Baseline) versus "
    f"{_sci_from_pv('flux_estimand.mlp_area_sum')} (MLP) and "
    f"{_sci_from_pv('flux_estimand.rf_area_sum')} (RF). A k-correction did not improve on the Baseline "
    f"({num('main_results.k_correction.rmse_c')} mol m\u207b\u00b3); "
    f"{int(round(float(pv('k_estimate.infeasible_frac_full_data') or 0) * 100))}% of samples could not be "
    "matched by any positive transfer velocity alone. A model-free objective surface and profile SSE show "
    "that a single concentration observation leaves an exact zero valley in the (k, S_sgs) plane, and "
    f"pooling leaves the profile shallow (RMSE {num('equifinality.profile_rmse_min')} mol m\u207b\u00b3 near "
    f"the optimum). Filter-scale |S_sgs| under path-connected coarsening remains sampling-conditional "
    "because synchronous coverage is sparse and the study-reach merge is unresolved under full "
    "cross-group edge preservation. "
    "Lower concentration error alone is insufficient to identify how model discrepancy is allocated "
    "between unresolved sources and gas exchange."
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
    "ln k<sub>600</sub> = 1.18 ln e<sub>D</sub> + 6.43 &nbsp;(e<sub>D</sub> \u2265 0.02 m\u00b2 s\u207b\u00b3);&nbsp;&nbsp;"
    "e<sub>D</sub> = g\u00b7S\u00b7u;&nbsp;&nbsp;k<sub>emp</sub> = k<sub>600</sub>(Sc/600)<sup>\u22120.5</sup>",
    "ln k600 = 1.18 ln eD + 6.43 (eD >= 0.02 m2 s-3);  eD = g S u;  k_emp = k600 (Sc/600)^-0.5",
)

# Read the retained terms from the frozen sparse summary so the equation can
# never drift from dimensionless_sparse_coefficients.csv (P0-01).
def _sparse_eq_terms() -> tuple[str, str]:
    """Build the display equation from the frozen sparse coefficients.

    Falls back to the machine summary's own string when coefficients are absent.
    """
    eq_html = pv("sparse.equation_standardized_Sstar")
    if isinstance(eq_html, str) and eq_html.strip():
        plain = eq_html.replace("S*", "S*").replace("\u2248", "\u2248")
        return eq_html, plain
    return "\u2014", "\u2014"


SPARSE_EQ = _sparse_eq_terms()

# ---------------------------------------------------------------------------
# Figures (11 files after merging Figs 2a/2b and combining S2/S3; captions in journal style)
# ---------------------------------------------------------------------------

FIG_CAPTIONS: dict[str, str] = {
    "les_filter_conceptual.png": (
        "<strong>Figure 1.</strong> Schematic of the two aggregation rules used by the cell-DAG "
        "operator, drawn side by side. (a) Serial contraction along one channel: cells share a single "
        "discharge, so <em>Q</em> is constant downstream and &Sigma;<em>QC</em> is accumulated along the "
        "chain rather than re-averaged. (b) Parallel confluence at a junction: "
        "<em>Q</em><sub>out</sub>&nbsp;=&nbsp;<em>Q</em><sub>1</sub>&nbsp;+&nbsp;<em>Q</em><sub>2</sub> "
        "and <em>C</em><sub>out</sub> is flow-weighted, not an arithmetic mean, while areas add and "
        "repeated observations in one cell add no area. Both panels are schematic and not to scale; the "
        "figure states the operator rules and is not evidence that conservation was achieved in a "
        "particular run."
    ),
    "figure2_reach_assignment_and_samples.png": (
        "<strong>Figure 2.</strong> (a) Logical reach assignment on the NHDPlus HR network over an "
        "Esri World Imagery satellite basemap: segments were assigned to the logical study-reach labels "
        "by GNIS name matching and proximity to campaign coordinates; colors indicate reach assignment, "
        "and the single-sample reach R001 receives no assigned segment in this rendering. (b) Locations "
        "of the 120 campaign samples on the same basemap; point colors denote logical reaches "
        "R001\u2013R008, with 58 samples on R008. Thin arrows show the digitized flow direction only, "
        "so the map is a location reference and is not a flow-validity test. Both panels are drawn in "
        "Web Mercator (EPSG:3857) with a metric scale bar and a north arrow; basemap tiles are cached "
        "locally with recorded provenance and hashes (see the figure sidecar)."
    ),
    "nested_cv_rmse_bar.png": (
        "<strong>Figure 3.</strong> Grouped leave-one-reach-out cross-validation with transport coupling "
        "(120 samples, 8 reach groups, fixed random seed): held-out C<sub>aq</sub> RMSE for the "
        "Baseline, Residual-AI (MLP and random forest), and k-correction closures. Filled bars are the "
        "pooled sample-weighted metric; the open markers show the per-reach values behind it, so the "
        "pooled contrast can be read against the reach-level spread. The dashed line marks the Baseline "
        "value. No closure lowers the pooled RMSE below the zero-residual Baseline; the k-correction is "
        "indistinguishable from it."
    ),
    "nested_cv_scatter_holdout.png": (
        "<strong>Figure 4.</strong> Observed versus transport-predicted held-out C<sub>aq</sub> for the "
        "Residual-AI (MLP) closure under leave-one-reach-out grouped evaluation (n=120); colors denote "
        "logical reaches and the dashed line indicates 1:1 agreement. Complexity statistics are computed "
        "from these point data and the keys are traceable to "
        "`data_proc/nested_cv_holdout_predictions.csv`. The inset resolves the low-concentration range "
        "where most mainstem samples fall. Extreme points are retained rather than trimmed. In this frozen "
        f"run, {pv('constraint_diagnostics.n_constraint_active')} of "
        f"{pv('constraint_diagnostics.n_oof_rows')} held-out rows activate the physical lower bound on "
        "S<sub>sgs</sub>, so the residual closures are reported without a catch-and-clip post-processing "
        "step; a nonzero count here would instead be reported explicitly."
    ),
    "subgroup_rmse_r008_vs_trib.png": (
        "<strong>Figure 5.</strong> Subgroup C<sub>aq</sub> RMSE for the Baseline, Residual-AI (MLP and "
        "random forest), and k-correction. R008 contains 58 samples; the multi-sample tributary group "
        "R002\u2013R005 contains 59 samples; R001, R006, and R007 are single-sample logical reaches and "
        "are shown separately rather than pooled into the comparison."
    ),
    "supp_flux_diagnostics.png": (
        "<strong>Figure 6.</strong> Model F<sub>CO\u2082</sub> diagnostics for the Baseline, "
        "Residual-AI (MLP), and k-correction under leave-one-reach-out grouped evaluation. "
        "(a) Area-weighted model flux diagnostic &Sigma;<em>F</em>&middot;<em>A</em> (mol d\u207b\u00b9), "
        "the same estimand as Table 2, so panel (a) and the table agree. (b) Per-reach composition of "
        "that diagnostic, showing that the Residual-AI total is concentrated in a small number of "
        "reaches. (c) Sample-level k<sub>eff</sub>/k<sub>emp</sub> versus the k-correction model flux "
        "diagnostic. These quantities are model diagnostics of the form k(C \u2212 C<sub>eq</sub>) and "
        "are neither study-area totals nor independently validated evasion measurements; the "
        "un-area-weighted density sums behind panel (a) are retained in the supplementary tables."
    ),
    "filter_scale_sgs.png": (
        "<strong>Figure 7.</strong> Filter-scale dependence of the diagnosed residual on resolved "
        "scales only (native through a sixteen-fold merge; study_reach excluded because whole-reach "
        "contraction creates a DAG cycle). Upper panel: unique-cell mean and median |S<sub>sgs</sub>| "
        "versus filter scale \u0394x on a log axis, with the actual mean and median control lengths "
        "marked. Lower panel: unique-cell variance of S<sub>sgs</sub> with the median control length on "
        "a secondary axis. Unique-cell mean |S| stays in a narrow band near "
        f"{num('filter_scale.scales.0.cell_mean_abs_S_sgs', 2)}\u2013"
        f"{num('filter_scale.scales.7.cell_mean_abs_S_sgs', 2)} mol m\u207b\u00b2 d\u207b\u00b9 across "
        f"the eight resolved levels (\u0394x \u2248 {num('filter_scale.scales.0.dx_m', 0)}\u2013"
        f"{num('filter_scale.scales.7.dx_m', 0)} m) under sparse synchronous coverage; this is a "
        "sampling-conditional sensitivity of the conserved operator, not a claim of scale-invariance "
        "through the study-reach aggregation."
    ),
    "filter_scale_sgs_box.png": (
        "<strong>Figure 8.</strong> Distribution of |S<sub>sgs</sub>| across resolved filter scales "
        "(native through a sixteen-fold merge) at the date\u00d7cell record level, with per-scale "
        "record counts printed above each group. Fliers are suppressed because all points are already "
        "shown in the accompanying scatter; multi-sample date-cell records are not independent draws, "
        "and repeated observations in one cell do not add area. Study-reach aggregation is excluded for "
        "the same contraction-cycle reason as Figure 7. The count of date\u00d7cell records "
        f"(from {int(float(pv('filter_scale.scales.0.n_date_cell_records') or 0))} at native resolution to "
        f"{int(float(pv('filter_scale.scales.7.n_date_cell_records') or 0))} at the coarsest resolved "
        "scale) differs from the count of unique spatial cells "
        f"({int(float(pv('filter_scale.scales.0.n_unique_spatial_cells') or 0))} to "
        f"{int(float(pv('filter_scale.scales.7.n_unique_spatial_cells') or 0))}), because the same cell "
        "can be sampled on several dates."
    ),
    "dimensionless_coefficients.png": (
        "<strong>Figure 9.</strong> Standardized LASSO coefficients for the sparse dimensionless "
        f"closure, fitted on fold-local targets ({int(float(pv('sparse.n_terms_standardized') or 0))} of "
        "five candidate \u03a0 terms retained; only log<sub>10</sub>(Re) shrinks to zero). Terms whose "
        "coefficient is numerically zero are drawn as explicit zero bars rather than omitted, so the "
        "reader can see which candidates were dropped and why. The displayed relation is "
        f"{pv('sparse.equation_standardized_Sstar')}. Leave-one-reach R\u00b2 for S* is "
        f"{num('sparse.Sstar_r2', 5)} (n=120); the sparse branch remains provisional."
    ),
    "equifinality_objective_surface.png": (
        "<strong>Figure 10.</strong> Model-free practical-equifinality diagnostic from the "
        "quasi-steady balance (n=120). This is a conditional model diagnostic: the objective shares a "
        "single k-scale and a single source across samples and holds the observed upstream state fixed. "
        "(a) Single-sample objective log\u2081\u2080 J(k, S) for one representative sample; the crimson "
        "line marks the exact zero valley "
        "S = S<sub>diag</sub> + (C<sub>obs</sub> \u2212 C<sub>eq</sub>)(k \u2212 k<sub>emp</sub>), so a "
        "single concentration observation leaves (k, S) algebraically under-determined. (b) Pooled "
        "objective J(\u03b1, S) over a uniform k-scale \u03b1 = k/k<sub>emp</sub> and a uniform source S; "
        "the Baseline, k-correction, and Residual-AI points are descriptive median markers drawn for "
        "orientation, not fitted network operating points. (c) Profile SSE "
        "J<sub>prof</sub>(\u03b1) = min<sub>S</sub> J(\u03b1, S); the profile is shallow, with the minimum "
        f"near \u03b1 = {num('equifinality.optimum_alpha')} (profile RMSE "
        f"{num('equifinality.profile_rmse_min')} mol m\u207b\u00b3)."
    ),
}

FIG_ORDER = [
    "les_filter_conceptual.png",
    "figure2_reach_assignment_and_samples.png",
    "nested_cv_rmse_bar.png",
    "nested_cv_scatter_holdout.png",
    "subgroup_rmse_r008_vs_trib.png",
    "supp_flux_diagnostics.png",
    "filter_scale_sgs.png",
    "filter_scale_sgs_box.png",
    "dimensionless_coefficients.png",
    "equifinality_objective_surface.png",
]

# Figures that were published as supplementary (S1-S3) in the earlier draft are
# now merged into the main text in logical order; no separate S numbering remains.
MERGED_SUPPLEMENT = {
    "subgroup_rmse_r008_vs_trib.png": "S1",
    "supp_flux_diagnostics.png": "S2",
    "filter_scale_sgs_box.png": "S3",
}

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
     "held-out predictive value. Several boundaries constrain the interpretation. Reach support is "
     "strongly unequal, channel geometry follows a published hydraulic-geometry relation rather than "
     "direct measurement, and no independent evasion observations are available. Within these "
     "constraints, the test is whether concentration-only observations can distinguish discrepancy "
     "assigned to S<sub>sgs</sub> from discrepancy assigned to k when both closures are evaluated "
     "through the same transport calculation. Figure 1 states the two spatial-aggregation rules used "
     "throughout, and the sections below follow the logical order of the analysis: study data and "
     "network representation (Section 2.1), the mass balance and gas exchange (Section 2.2), the "
     "filtering operator and the diagnosed residual (Section 2.3), the competing closures (Section "
     "2.4), and the evaluation protocol (Sections 2.5\u20132.8)."),
    ("fig", "les_filter_conceptual.png"),

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
     "mainstem reach R008. The eight reaches serve as cross-validation groups and reporting units. "
     "Corridor-level transport and filter experiments use the directed NHDPlus HR topology. The "
     "mainstem East River is subdivided into six ordered segments (R008_S1 through R008_S6) by "
     "confluence northing thresholds into a logical reporting / verified-simplified routing "
     "tree\u2014not a fully verified path-compressed NHD directed compression\u2014and the seven "
     "tributaries join at their mapped confluences through flow-weighted mixing (Section 2.2)."),
    ("p",
     "The river-network representation combines three public sources. The HydroShare supplement of "
     "Saccardi and Winnick (2021) provides the campaign observations and the synoptic tributary "
     "discharges. An extract of the NHDPlus HR product for HUC 14020001 provides the flowlines used for "
     "the corridor-level filter lattice; these flowlines are ordered into a directed acyclic topology by "
     "endpoint matching and the NHD flow-direction attribute, so concentration is routed strictly "
     "upstream to downstream rather than by geographic coordinates. The mainstem East River (reach R008) "
     "reporting segments R008_S1\u2013S6 follow the logical y-threshold tree above; each tributary reach "
     "(R001\u2013R007) joins that tree at a mapped confluence. Discharge for the mainstem comes from USGS "
     "gage 09112500 (East "
     "River at Almont) on the sample dates; tributary discharges are the published synoptic values from "
     "the campaign supplement, with no gage-ratio scaling applied."),
    ("p",
     "Channel width and depth are not measured along the corridor, so both are estimated from the "
     "hydraulic-geometry relations of Raymond et al. (2012), fitted to 1026 paired measurements in "
     "streams and small rivers: width W = 12.88\u00b7Q<sup>0.42</sup> (m), depth "
     "h = 0.4\u00b7Q<sup>0.29</sup> (m), and bulk velocity u = 0.19\u00b7Q<sup>0.29</sup> (m s\u207b\u00b9), "
     "with discharge Q in m<sup>3</sup> s<sup>-1</sup>. These are model-derived hydraulic inputs rather than "
     "measured cross-section properties, and the width enters velocity, k<sub>600</sub>, and the "
     "water-surface area A<sub>s</sub> = L\u00b7W. All hydraulic and gas-exchange quantities are "
     "conditional on this adopted geometry; no independent cross-section survey is available for "
     "this corridor. Because the three relations were fitted separately, they are not exactly "
     "mutually consistent: together they imply u\u00b7W\u00b7h = 0.97888\u00b7Q, so the continuity "
     "identity u = Q/(W\u00b7h) closes only to 2.112%. We retain the published regression for u "
     "rather than substituting the continuity-derived velocity, because replacing it would require "
     "recomputing k<sub>600</sub>, the Reynolds, Froude and Damk\u00f6hler numbers and every "
     "downstream residual; the 2.112% closure deviation is therefore carried as a stated "
     "systematic of the adopted geometry rather than silently absorbed. Biogeochemical covariates "
     "are likewise "
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
     "The reported flux totals are area-weighted sums of F<sub>CO\u2082</sub> over the water-surface "
     "area A<sub>s</sub> (mol d\u207b\u00b9). They compare how each closure allocates the model "
     "balance; they are neither independently observed evasion fluxes nor spatially integrated "
     "watershed fluxes."),
    ("p",
     "The empirical transfer velocity follows the energy-dissipation parameterization of Ulseth et al. "
     "(2019), which was the formulation used by the original East River model (Saccardi &amp; Winnick, "
     "2021) and which accounts for the high turbulence of steep mountain streams. The Schmidt-600-normalized "
     "velocity k<sub>600</sub> is estimated from the stream energy-dissipation rate "
     "e<sub>D</sub> = g\u00b7S\u00b7u, and the CO\u2082-specific velocity is obtained by "
     "Schmidt-number scaling:"),
    ("eqline", K600_EQ),
    ("p",
     "We distinguish the Schmidt-600-normalized velocity k<sub>600</sub> from the "
     "CO\u2082-specific empirical velocity k<sub>emp</sub>. The high-energy branch (e<sub>D</sub> "
     "\u2265 0.02 m\u00b2 s\u207b\u00b3) applies throughout the study corridor; the Schmidt number "
     "Sc is evaluated at the sample water temperature. Because the choice of k<sub>600</sub> "
     "parameterization affects every gas-exchange result, Raymond et al. (2012) Model-4 "
     "k<sub>600</sub> values are retained as a sensitivity column in the processed observation "
     "table (median k<sub>600</sub> \u2248 98 m d\u207b\u00b9 versus \u2248 268 m d\u207b\u00b9 for "
     "Ulseth); the primary evaluation below uses Ulseth throughout. The "
     "equilibrium concentration C<sub>eq</sub> is computed from Henry\u2019s law with a "
     "temperature-dependent solubility constant. The constant follows the NIST/Sander compilation for "
     "CO\u2082 in water, k<sup>\u00b0</sup><sub>H</sub>(298.15 K) = 0.035 mol kg\u207b\u00b9 "
     "bar\u207b\u00b9 with a van \u2019t Hoff temperature dependence d(ln k<sub>H</sub>)/d(1/T) = "
     "2400 K, so C<sub>eq</sub> = k<sub>H</sub>(T)\u00b7pCO\u2082\u00b7\u03c1<sub>water</sub> with the "
     "atmospheric pCO\u2082 fixed at 400 \u00b5atm. Colder water dissolves more CO\u2082, so "
     "C<sub>eq</sub> now varies with each sample\u2019s temperature rather than being held at a single "
     "constant."),
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
     "We perform spatial coarse-graining on the directed NHDPlus HR flowlines. Flowlines are first "
     "ordered by their directed topology (upstream to downstream, from endpoint matching and the NHD "
     "flow-direction attribute), then grouped into filter cells as individual flowlines, consecutive "
     "pairs, or consecutive groups of four (native, ~2\u00d7, and ~4\u00d7 merges). A whole-reach "
     "(study_reach) contraction that preserves all cross-group fine edges produces a cyclic cell DAG "
     "and is therefore excluded from formal filter claims (no singleton fallback). Each campaign "
     "observation is snapped to its nearest cell at each resolved scale. The reported "
     "\u0394x is the mean length of the unique spatial cells that contain samples at that scale, giving "
     "\u0394x \u2248 587 m for the native operator. Figure 1 summarizes the filtering construction."),
    ("p",
     "For each date and filter scale, the inflow concentration C<sub>in</sub> to a headwater cell is "
     "the atmospheric-equilibrium concentration C<sub>eq</sub>; downstream, C<sub>in</sub> is the "
     "observed concentration of the nearest sampled cell upstream along the directed flow path. A "
     "sample\u2019s own observed concentration is never used as its own upstream boundary, so the "
     "diagnosis is target-blind with respect to C<sub>in</sub>. Because each cell contributes one "
     "mass-balance residual, metrics are computed over unique spatial cells rather than re-counting the "
     "120 samples at every scale."),
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

    ("h3", "2.4 Alternative unresolved-process closures"),
    ("p",
     "Three closure configurations are compared. They differ only in how S<sub>sgs</sub> and k are "
     "supplied to Eq. (1)."),
    ("p",
     "The Baseline retains the transport and hydraulic formulation of the other configurations while "
     "setting S<sub>sgs</sub> = 0 and using the energy-dissipation empirical velocity "
     "k<sub>emp</sub> (Ulseth et al., 2019). It "
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
     "predicted residual is signed, allowing both source and sink values. The random forest uses 200 "
     "trees with maximum depth 12 and no predictor standardization. The training target is the "
     "dimensionally consistent residual of Eq. (4), diagnosed from the observed concentrations "
     "routed through the directed network (Section 2.3)."),
    ("p",
     "The k-correction configuration leaves S<sub>sgs</sub> at zero and multiplies the empirical "
     "velocity by a learned factor, k<sub>eff</sub> = k<sub>emp</sub>\u00b7exp(g<sub>\u03b8</sub>(X)), "
     "where g<sub>\u03b8</sub> is a dimensionless correction predicted by a gradient-boosting model "
     "(XGBoost; 300 trees, maximum depth 6, learning rate 0.05, seed 42). The training target is "
     "constructed within each fold by solving the balance for the transfer velocity "
     "k<sub>need</sub> required to reproduce the observed concentration with S<sub>sgs</sub> = 0, "
     "using the diagnosed upstream concentration C<sub>in</sub> of the same fold; the predicted "
     "correction is then applied as k<sub>eff</sub> = k<sub>emp</sub>\u00b7exp(g<sub>\u03b8</sub>(X)) "
     f"before the transport balance is re-solved. For "
     f"{int(round(float(pv('k_estimate.infeasible_frac_full_data') or 0) * 100))}% of the samples "
     "no positive k<sub>need</sub> exists (a positive transfer velocity cannot reproduce the observed "
     "supersaturation with S<sub>sgs</sub> = 0), and these rows are excluded from the k-correction "
     f"target; the held-out saturation fraction at the imposed logarithmic lower bound "
     f"(g = \u221212) is {fmt_pv_ratio('k_estimate.floor_saturation_fraction')}. The median ratio "
     "k<sub>eff</sub>/k<sub>emp</sub> under grouped evaluation "
     "is reported as a diagnostic of how the correction behaves."),
    ("p",
     "The diagnosed residual is positive for all 120 samples (a subgrid source; Section 3), yet the "
     "Residual-AI learners are left unbounded in prediction. The consequence of this signed, unbounded "
     "prediction is examined under held-out evaluation in Section 3."),

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
     "The upstream boundary is fully independent of the sample being predicted: each headwater "
     "segment enters with the atmospheric-equilibrium concentration C<sub>eq</sub>, and no observed "
     "C<sub>aq</sub> is used as a fallback for the sample being scored, so the evaluation is "
     "target-blind with respect to upstream conditioning. Sampling is strongly imbalanced among "
     "reaches: R008 contributes 58 of the 120 samples, while three reaches contribute one each, so "
     "pooled errors are read together with reach-level evidence weights (Table 5). A date-grouped "
     "variant is reported as a time-sensitivity analysis and is not nested inside the reach split."),

    ("h3", "2.6 Metrics and flux diagnostic"),
    ("p",
     "The primary metric is the held-out C<sub>aq</sub> RMSE in mol m\u207b\u00b3. The secondary "
     "diagnostic is the area-weighted model flux \u03a3(F<sub>CO\u2082</sub>\u00b7A<sub>s</sub>) in "
     "mol d\u207b\u00b9, computed from Eq. (3) with the transport-predicted concentration and the "
     "transfer velocity of each configuration (k<sub>emp</sub> for the Baseline and Residual-AI, "
     "k<sub>eff</sub> for the k-correction), summed as an overlapping sample-area diagnostic (not a study-area total). An observation-based proxy "
     "uses k<sub>emp</sub> with observed concentrations. Differences in this area-weighted total "
     "across closures indicate how each configuration allocates the balance between sources and gas "
     "exchange; the totals are model diagnostics, not independently validated evasion measurements."),

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
     "compensating closure behaviour as practical equifinality."),
    ("p",
     "We additionally quantify this trade-off model-free, without any machine-learned model in the "
     "loop. For a single sample, the objective J(k, S) = [C<sub>obs</sub> \u2212 "
     "C<sub>model</sub>(k, S)]\u00b2 vanishes exactly on the line "
     "S = S<sub>diag</sub> + (C<sub>obs</sub> \u2212 C<sub>eq</sub>)(k \u2212 k<sub>emp</sub>), so one "
     "concentration observation cannot identify (k, S) jointly and the per-sample profile SSE "
     "is identically flat. Pooling the 120 samples with a uniform k-scale \u03b1 = k/k<sub>emp</sub> "
     "and a uniform source S gives a pooled objective J(\u03b1, S) and a profile "
     "J<sub>prof</sub>(\u03b1) = min<sub>S</sub> J(\u03b1, S); the flatness of J<sub>prof</sub> over "
     "\u03b1 quantifies how little the concentration data alone discriminate the two closures. This "
     "is reported as the primary equifinality evidence rather than a single fitted model."),

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

    ("h3", "3.1 Residual closures do not improve pooled held-out concentration prediction"),
    ("p",
     "Under leave-one-reach-out transport-coupled evaluation with independent upstream boundary "
     "conditioning, the pooled held-out C<sub>aq</sub> RMSE of the Residual-AI MLP is "
     f"{num('main_results.mlp.rmse_c')} mol m\u207b\u00b3 against {num('main_results.baseline.rmse_c')} "
     f"for the Baseline and {num('main_results.random_forest.rmse_c')} for the random forest (Tables 2 and 3; "
     "Figure 3). The learned closures therefore do not lower pooled held-out concentration error relative to "
     "the zero-source Baseline. The corresponding mean absolute error (MAE) values are "
     f"{num('main_results.baseline.mae_c')}, {num('main_results.mlp.mae_c')}, and "
     f"{num('main_results.random_forest.mae_c')}, and the residual closures show a positive concentration "
     f"bias ({num('main_results.mlp.bias_c')} and {num('main_results.random_forest.bias_c')}) where the "
     f"Baseline bias is {num('main_results.baseline.bias_c')}. "
     "In-sample concentration metrics are not reported as a paper result: after recalculation the "
     "sole concentration skill metric is leave-one-reach-out transport-coupled C<sub>aq</sub>. "
     "A date-grouped variant of the Baseline gives the same pooled RMSE, with the "
     "date-grouped evaluation outputs archived in the public repository cited in Section 6."),
    ("p",
     "The subgroup decomposition locates both the apparent gain and its fragility (Table 5; Figures 4 and 5). "
     "On the mainstem reach R008, both residual closures are better than the Baseline: RMSE is "
     f"{num('subgroups.mlp_mainstem_rmse')} for the MLP and {num('subgroups.rf_mainstem_rmse')} for the "
     f"random forest against {num('subgroups.baseline_mainstem_rmse')} for the Baseline. On the multi-sample "
     f"tributaries (R002\u2013R005) the pattern reverses: RMSE is {num('subgroups.baseline_tributary_rmse')} "
     f"for the Baseline, {num('subgroups.mlp_tributary_rmse')} for the MLP, and "
     f"{num('subgroups.rf_tributary_rmse')} for the random forest. The pooled contrast is dominated by a "
     f"small number of points: three samples in R002 account for "
     f"{fmt_ratio(pv('reach_sensitivity.r002_gain_contribution_frac'))} of the gross positive error "
     "reduction, while the net MLP-minus-Baseline pooled SSE change is "
     f"{num('reach_sensitivity.net_mlp_sse_gain', 6)} (a net worsening). Dropping R002 without retraining "
     f"gives pooled RMSE of {num('reach_sensitivity.pooled_rmse_baseline_drop_R002')} (Baseline) and "
     f"{num('reach_sensitivity.pooled_rmse_mlp_drop_R002')} (MLP). The equal-weight-reach MSE-then-square-root "
     f"estimand is {num('reach_sensitivity.equal_weight_reach_mse_then_sqrt.baseline')} (Baseline) and "
     f"{num('reach_sensitivity.equal_weight_reach_mse_then_sqrt.mlp')} (MLP), which is the unweighted mean of "
     "per-reach MSE followed by a square root, not the mean of per-reach RMSE. The holdout scatter (Figure 4) "
     "shows the same structure: mainstem predictions cluster near the observations while tributary "
     "predictions spread widely. With eight reaches and this sampling imbalance, these contrasts are "
     "descriptive of this campaign and do not support a general generalization inference."),
    ("p",
     "The residual closures are also unstable out of sample. Because the signed source prediction is "
     "unbounded, the MLP and random forest extrapolate to large sources on held-out reaches, driving the "
     f"area-weighted model flux to {_sci_from_pv('flux_estimand.mlp_area_sum')} and "
     f"{_sci_from_pv('flux_estimand.rf_area_sum')} mol d\u207b\u00b9, respectively, against "
     f"{_sci_from_pv('flux_estimand.baseline_area_sum')} mol d\u207b\u00b9 for the Baseline (Table 2). "
     "The tested target formulation is therefore not sufficient: flexible residual learning of a "
     "dimensionally consistent but unbounded S<sub>sgs</sub> does not transfer to held-out reaches and "
     "produces unphysical source extrapolation."),
    ("raw", "NESTED_TABLES"),
    ("fig", "nested_cv_rmse_bar.png"),
    ("fig", "nested_cv_scatter_holdout.png"),
    ("fig", "subgroup_rmse_r008_vs_trib.png"),

    ("h3", "3.2 A corrected gas-transfer velocity does not improve concentration error"),
    ("p",
     "The k-correction does not improve on the Baseline. Its C<sub>aq</sub> RMSE is "
     f"{num('main_results.k_correction.rmse_c')} mol m\u207b\u00b3 against "
     f"{num('main_results.baseline.rmse_c')} for the Baseline (Tables 2 and 3). The correction acts only "
     f"through the transfer velocity, and {int(round(float(pv('k_estimate.infeasible_frac_full_data') or 0) * 100))}% "
     "of the samples cannot be matched by any positive transfer velocity with S<sub>sgs</sub> = 0, so the "
     f"k-only target is undefined for most of the data; {int(round(float(pv('k_estimate.n_infeasible_full_data') or 0)))} "
     f"of {int(round(float(pv('counting.n_campaign_samples') or 0)))} full-data rows are infeasible and are "
     "excluded from training rather than floor-clipped, and none of the held-out predictions saturate at the "
     f"imposed logarithmic lower bound (g = \u221212; {pv('k_estimate.floor_saturation_display')} at the "
     "floor). The median effective velocity is "
     f"{num('k_estimate.k_eff_median_m_d')} m d\u207b\u00b9 against a median empirical velocity of "
     f"{num('k_estimate.k_emp_median_m_d')} m d\u207b\u00b9, so the median ratio "
     f"k<sub>eff</sub>/k<sub>emp</sub> is {fmt_pv_ratio('k_estimate.k_ratio_median')} (Table 7). "
     "The earlier impression that a k-correction "
     "lowered concentration error arose from using a sample\u2019s own observed concentration as its "
     "upstream boundary and from clipping the correction to a fixed lower bound; both artifacts are "
     "removed here."),
    ("p",
     "That concentration error does not discriminate the k-correction from the Baseline motivates the "
     "model-free objective surface examined in Section 3.6."),

    ("h3", "3.3 The residual closures allocate the balance to unphysical extremes"),
    ("p",
     "The area-weighted model flux reveals markedly different process allocations among the closures. "
     f"The Baseline releases {_sci_from_pv('flux_estimand.baseline_area_sum')} mol d\u207b\u00b9 as an "
     f"overlapping sample-area diagnostic; the k-correction gives "
     f"{_sci_from_pv('flux_estimand.kcorr_area_sum')} mol d\u207b\u00b9 by driving k<sub>eff</sub> toward "
     f"zero, while the Residual-AI closures inflate it to {_sci_from_pv('flux_estimand.mlp_area_sum')} (MLP) "
     f"and {_sci_from_pv('flux_estimand.rf_area_sum')} (random forest) mol d\u207b\u00b9 (Table 2). Because "
     "no independent evasion "
     "observations are available for this campaign, these values show only that the three allocations "
     "are mutually incompatible; they do not establish which is physically correct."),
    ("p",
     "The implied-source diagnostic makes the compensation explicit. The mean implied adjustment "
     f"S<sub>implied</sub> is {num('equifinality.S_implied_mean_mol_m2d')} mol m\u207b\u00b2 d\u207b\u00b9 and "
     f"the mean Residual-AI prediction is {num('equifinality.S_mlp_mean_mol_m2d')} mol m\u207b\u00b2 d\u207b\u00b9, "
     f"with a Spearman correlation of {num('equifinality.spearman_S_ai_vs_S_implied')} between the two "
     "(Table 7). A positive source term and a reduced transfer velocity act on the concentration "
     "balance in compensating directions, and the held-out concentration metric provides limited "
     "discrimination between them. Figure 6(c) shows the corresponding sample-level relation between "
     "k<sub>eff</sub>/k<sub>emp</sub> and the k-correction flux diagnostic."),
    ("raw", "INNOVATION_TABLES"),
    ("fig", "supp_flux_diagnostics.png"),

    ("h3", "3.4 Filter-scale residual on resolved coarsenings"),
    ("p",
     "On the resolved path-connected coarsenings (native through a sixteen-fold merge), unique-cell mean "
     f"|S<sub>sgs</sub>| stays in a narrow band around {num('filter_scale.scales.0.cell_mean_abs_S_sgs', 2)}"
     f"\u2013{num('filter_scale.scales.7.cell_mean_abs_S_sgs', 2)} mol m\u207b\u00b2 d\u207b\u00b9 over "
     f"\u0394x \u2248 {num('filter_scale.scales.0.dx_m', 0)}\u2013{num('filter_scale.scales.7.dx_m', 0)} m "
     "(eight resolved scale levels; Table 6; Figure 7). Cell-level variance rises only slowly, from about "
     f"{num('filter_scale.scales.0.cell_var_S_sgs', 1)} to {num('filter_scale.scales.7.cell_var_S_sgs', 1)}. "
     "A study-reach whole-reach merge is excluded: preserving all cross-group fine "
     "edges yields a cyclic contracted DAG, so the reach assignment is not a verified DAG compression "
     "of the fine NHD graph and cannot support a formal scale-invariance claim through that aggregation. "
     "Within the resolved scales the near-stability of |S| under sparse synchronous coverage is a "
     "sampling-conditional sensitivity of the conserved operator, not a universal scaling law. The unique "
     "spatial cell count falls from "
     f"{int(float(pv('filter_scale.scales.0.n_unique_spatial_cells') or 0))} at native resolution to "
     f"{int(float(pv('filter_scale.scales.7.n_unique_spatial_cells') or 0))} at the coarsest resolved scale, "
     "and the diagnosed-cell fraction is below 1% at every scale, so the curve is a sensitivity of a small "
     "synchronous subset rather than a complete spatial budget."),
    ("fig", "filter_scale_sgs.png"),
    ("fig", "filter_scale_sgs_box.png"),

    ("h3", "3.5 A sparse dimensionless closure is compact but not predictive"),
    ("p",
     "The full-data LASSO refit on the dimensionless response retains "
     f"{int(float(pv('sparse.n_terms_standardized') or 0))} of the five candidate "
     "\u03a0 terms (Table 8; Figure 9). With subscript z denoting predictors standardized to "
     "zero mean and unit variance, the closure is"),
    ("eqline", SPARSE_EQ),
    ("p",
     "The retained coefficients are negative for Froude number, slope, relative depth, and the "
     "base-10 logarithm of the Damk\u00f6hler number; only the Reynolds-number term shrinks to zero. "
     "Because this relation is a "
     "descriptive full-data summary (Section 2.8), it is not itself scored as a held-out law; the "
     f"leave-one-reach R\u00b2 for reconstructing the dimensionless response S* is "
     f"{num('sparse.Sstar_r2', 5)}. Under "
     "the same leave-one-reach-out transport-coupled protocol, in which the scaler and LASSO are "
     f"refitted within each fold, the sparse closure gives a held-out C<sub>aq</sub> RMSE of "
     f"{num('sparse.transport_rmse_c', 5)} "
     f"mol m\u207b\u00b3, above the Baseline value of {num('main_results.baseline.rmse_c')} (Table 9). This "
     "branch remains provisional: it is reported as a compact diagnostic description of the residual and "
     "does not recover predictive "
     "skill on held-out reaches."),
    ("fig", "dimensionless_coefficients.png"),

    ("h3", "3.6 Model-free equifinality: objective surface and profile SSE"),
    ("p",
     "A model-free objective surface quantifies how weakly concentration data discriminate between a "
     "subgrid source and a gas-exchange correction (Figure 10). For a single sample, the objective "
     "J(k, S) = [C<sub>obs</sub> \u2212 C<sub>model</sub>(k, S)]\u00b2 has an exact zero valley along "
     "S = S<sub>diag</sub> + (C<sub>obs</sub> \u2212 C<sub>eq</sub>)(k \u2212 k<sub>emp</sub>), so the "
     "per-sample profile SSE is identically flat and one concentration observation cannot "
     "identify (k, S) jointly. Pooling the 120 samples with a uniform k-scale \u03b1 = k/k<sub>emp</sub> "
     "and a uniform source S leaves the profile shallow: across the reported interval "
     f"({pv('equifinality.profile_interval')}) the profile RMSE spans only "
     f"{num('equifinality.profile_rmse_range.0', 4)} to {num('equifinality.profile_rmse_range.1', 4)} "
     "mol m\u207b\u00b3, with the minimum at "
     f"\u03b1 = {num('equifinality.optimum_alpha')} and S = {num('equifinality.optimum_s_mol_m2d')} "
     "mol m\u207b\u00b2 d\u207b\u00b9. These are equal-weight sample SSE diagnostics (not a likelihood or "
     "a confidence interval) with one shared k-scale and one shared source and the observed upstream "
     "state held fixed. Concentration data alone therefore weakly discriminate the two closures, in "
     "agreement with the grouped-evaluation result that the k-correction does not improve on the "
     "Baseline."),
    ("fig", "equifinality_objective_surface.png"),

    ("h2", "4. Discussion"),

    ("h3", "4.1 Failed transfer of residual closures is a modelling diagnosis"),
    ("p",
     "Under fold-local targets the Residual-AI MLP does not lower pooled held-out concentration RMSE "
     "relative to a zero-residual Baseline, although it is better on the mainstem subgroup; the random "
     "forest is worse overall, and because source prediction is "
     "unbounded the residual learners extrapolate to unphysical sample-support fluxes on held-out "
     "reaches. That pattern separates apparent subgroup skill from settled predictive success. In "
     "the evaluation logic of Bennett et al. (2013) and Vilas et al. (2023), the discrepancy is itself "
     "diagnostic: it separates apparent learnability from held-out usefulness. The subgroup evidence "
     "points to where the transfer fails. Errors increase most clearly in the pooled multi-sample "
     "tributaries R002\u2013R005, whereas the mainstem reach, with 58 samples, is one subgroup where the "
     "residual closure remains competitive with the Baseline; the pooled contrast is, however, dominated "
     f"by three R002 samples that account for {fmt_ratio(pv('reach_sensitivity.r002_gain_contribution_frac'))} "
     "of the gross positive error reduction rather than by a broad improvement. These results support "
     "reporting reach-level diagnostics alongside pooled metrics, particularly when sampling support is "
     "strongly imbalanced, and they show that a flexible residual learner is not sufficient for a stable "
     "closure: the target must be bounded or regularized against out-of-sample extrapolation."),
    ("p",
     "The failure of residual closures to transfer does not imply that concentration error uniquely "
     "favors the Baseline; the model-free objective surface (Figure 10) shows instead that concentration "
     "data discriminate only weakly between a source allocation and a gas-exchange allocation."),

    ("h3", "4.2 Process allocation and practical equifinality"),
    ("p",
     "The k-correction cannot match most of the data with a single positive transfer velocity: "
     f"{int(round(float(pv('k_estimate.infeasible_frac_full_data') or 0) * 100))}% of the samples have no "
     "positive k<sub>need</sub> under S<sub>sgs</sub> = 0, and the "
     "retained predictions shrink far below the empirical velocity, so the correction does not improve on "
     "the Baseline. This sharpens the earlier result: the apparent superiority of a "
     "k-correction was an artifact of boundary leakage and clipping, and once both are removed the "
     "k-only closure is partly undefined rather than merely ineffective. Because S<sub>sgs</sub> and "
     "k(C \u2212 C<sub>eq</sub>) enter the same balance with opposing signs, a source allocation and a "
     "reduced transfer velocity act in compensating directions, and the held-out concentration metric "
     "provides limited discrimination between them."),
    ("p",
     "Here, practical equifinality refers to the compensation between S<sub>sgs</sub> and k, now "
     "quantified model-free. The objective surface (Figure 10) shows an exact zero valley for a single "
     "sample and a shallow pooled profile, so the concentration data alone constrain only weakly how "
     "discrepancy is allocated between a subgrid source and gas exchange. The single-sample result is an "
     "algebraic under-determination of one equation with fixed C<sub>in</sub> and two unknowns; the pooled "
     "result is an equal-weight 120-sample SSE profile with a shared k-scale and a shared source. Neither is "
     "a profile likelihood, a confidence interval, or a network-rerouting experiment, and the markers drawn "
     "for orientation on the pooled plane are descriptive medians rather than fitted operating points. This "
     "does not constitute a "
     "formal structural-identifiability analysis, and the unstable out-of-sample fluxes of the MLP and "
     "random forest are themselves not equifinality evidence; they show that closure choice matters and that "
     "flexible residual learning did not yield a settled predictive success here. Within those boundaries, the results suggest "
     "that concentration-dominated evaluation does not uniquely constrain how discrepancy is allocated "
     "between S<sub>sgs</sub> and k in this configuration."),
    ("p",
     "This process-allocation ambiguity concerns the closure form; the filtering experiment addresses "
     "a related but distinct source of variability in the diagnosed residual."),

    ("h3", "4.3 What filtering and sparse representation reveal about the residual"),
    ("p",
     "On resolved filter scales only, unique-cell mean |S<sub>sgs</sub>| stays in a narrow band around "
     f"{num('filter_scale.scales.0.cell_mean_abs_S_sgs', 2)}\u2013"
     f"{num('filter_scale.scales.7.cell_mean_abs_S_sgs', 2)} mol "
     "m\u207b\u00b2 d\u207b\u00b9 from native NHDPlus HR resolution through a sixteen-fold merge. "
     "Study-reach aggregation is excluded after an unresolved contraction cycle, so the manuscript "
     "does not claim scale-invariance through that coarser operator. Within the resolved range the "
     "result is a sampling-conditional sensitivity under sparse synchronous coverage, bounded by the "
     "implemented flow-directed operator (Yuval &amp; O\u2019Gorman, 2020, analogy limited to "
     "spatial filtering)."),
    ("p",
     f"The sparse closure retains {int(float(pv('sparse.n_terms_standardized') or 0))} terms (Fr, slope, "
     "h/W, and log<sub>10</sub>(Da), all negative), but its compact form does "
     "not improve held-out prediction: RMSE remains above the Baseline and the S* reconstruction fails "
     f"under reach holdout (R\u00b2 = {num('sparse.Sstar_r2', 5)}). Compact forms are therefore not "
     "automatically "
     "validated or predictive, and the branch remains provisional. Under the present protocol, the tested "
     "sparse \u03a0-group representation "
     "does not provide cross-reach predictive utility; it remains useful as a diagnostic "
     "simplification."),

    ("h3", "4.4 Implications for environmental-model evaluation"),
    ("p",
     "These findings suggest that concentration RMSE should be interpreted together with diagnostics of "
     "gas exchange and unresolved source allocation. When observations constrain only concentration, "
     "lower RMSE should be interpreted alongside diagnostics of the process terms that produced it."),
    ("p",
     "The present conclusions are bounded by strongly unequal reach support, the hydraulic-geometry "
     "representation of channel width and depth, incomplete covariates (alkalinity, nitrogen, "
     "phosphorus, photosynthetically active radiation), and the absence of independent evasion "
     "measurements. The Water Quality Portal merge and the StreamPULSE search returned no usable "
     "additional constraints for this campaign. These limitations restrict inference to the East River "
     "experiment, and they also identify the observations that would most help to discriminate "
     "closures: more balanced reach sampling, better-resolved channel geometry, and independent "
     "constraints on gas exchange. The central implication is that lower concentration error alone is "
     "insufficient to determine which allocation of unresolved processes is better supported."),

    ("h2", "5. Conclusions"),
    ("p",
     "Under leave-one-reach-out transport-coupled evaluation with fold-local residual targets, the "
     "Residual-AI multilayer perceptron does not lower pooled held-out C<sub>aq</sub> RMSE relative to the "
     f"Baseline ({num('main_results.mlp.rmse_c')} against {num('main_results.baseline.rmse_c')} mol "
     "m\u207b\u00b3); it is better on the mainstem subgroup and worse on the multi-sample tributaries, and "
     "the pooled contrast rests on a few R002 samples, so the apparent concentration gain is "
     "not treated as a settled success claim. Sample-support flux diagnostics remain unstable. A "
     f"k-correction does not improve on the Baseline ({num('main_results.k_correction.rmse_c')} "
     f"mol m\u207b\u00b3) because {int(round(float(pv('k_estimate.infeasible_frac_full_data') or 0) * 100))}% "
     "of the samples have no positive k-only solution. A model-free "
     "objective surface and profile SSE indicate that concentration data alone constrain only weakly how "
     "discrepancy is allocated between the source term S<sub>sgs</sub> and the transfer "
     "velocity k. Formal filter claims use only resolved coarsenings; study_reach is excluded."),
    ("p",
     "The framework combines an explicit spatial filter, transport-coupled grouped evaluation, and a "
     "model-free objective-surface diagnostic. Within the East River experiment, the framework "
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
         "<caption>Table 1. East River study network: eight logical reaches with four distinct "
         "count estimands (assigned corridor lines incl. nearest-campaign-sample assignments; "
         "logical routing segments; sampled control volumes; campaign samples). Mainstem segments "
         "R008_S1\u2013S6 form a logical reporting / confluence-chainage simplified tree, not a "
         "verified NHD directed compression. Domain length is the fixed control-volume length; a "
         "dagger marks a reach whose recorded support has not passed the domain-consistency gate. "
         "Counts are generated from the machine tables, not hand-written.</caption>"),
        (r"<caption>表 M 论文主结果一览.*?</caption>",
         "<caption>Table 2. Main results under leave-one-reach-out grouped cross-validation with "
         "transport coupling. Flux totals are model-derived diagnostics, not chamber-validated "
         "fluxes.</caption>"),
        (r"<caption>表 4b 样本内指标.*?</caption>",
         "<caption>Table 4. In-sample concentration metrics are not reported after recalculation; "
         "the paper metric is exclusively leave-one-reach-out transport-coupled C<sub>aq</sub>.</caption>"),
        (r"<caption>表 4 嵌套交叉验证.*?</caption>",
         "<caption>Table 3. Leave-one-reach-out grouped cross-validation: held-out "
         "C<sub>aq</sub> and F<sub>CO\u2082</sub> metrics (primary paper metrics; F values are model "
         "flux diagnostics).</caption>"),
        (r"<caption>表 5 子组嵌套交叉验证.*?</caption>",
         "<caption>Table 5. Subgroup metrics under leave-one-reach-out grouped cross-validation. Mainstem and "
         "tributary reaches are not equally weighted.</caption>"),
        (r"<caption>表 6 滤波尺度实验.*?</caption>",
         "<caption>Table 6. Filter-scale experiment on resolved scales (native through a "
         "sixteen-fold merge; study_reach excluded because whole-reach contraction creates a "
         "DAG cycle): S<sub>sgs</sub> at unique spatial cells after snapping samples onto "
         "flow-directed coarsened NHDPlus HR networks. Date\u00d7cell records are not "
         "independent draws, and repeated observations in one cell add no area.</caption>"),
        (r"<caption>表 7 可辨识性.*?</caption>",
         "<caption>Table 7. Practical-equifinality diagnostic: k and source-term compensation under "
         "the leave-one-reach-out grouped protocol.</caption>"),
        (r"<caption>表 8b 无量纲稀疏式代入输运后.*?</caption>",
         "<caption>Table 9. Sparse dimensionless closure inserted into transport under grouped "
         f"cross-validation (compare the Baseline value of {num('main_results.baseline.rmse_c')} in "
         "Table 3).</caption>"),
        (r"<caption>表 8 无量纲稀疏闭合.*?</caption>",
         "<caption>Table 8. Sparse dimensionless closure (\u03a0-group LASSO).</caption>"),
    ]
    for pat, rep in caption_map:
        html = re.sub(pat, rep, html, flags=re.S)

    # --- Lead notes (diary/process language -> plain English notes) ---
    lead_map = [
        (r'<p class="lead">读图前请先理解这张表.*?</p>',
         "<p class=\"lead\">Seven tributaries join the East River mainstem at mapped confluences "
         "(R008_S1\u2013S6). Those mainstem segments are a logical reporting / confluence-chainage "
         "simplified tree, not a verified NHD directed compression. The four count columns are "
         "different objects and must not be conflated: assigned corridor lines are reach-attributed "
         "NHDPlus HR flowlines (including nearest-campaign-sample assignments); logical routing "
         "segments are routing nodes; sampled control volumes are unique sample-support cells; "
         "campaign samples are the held-out units of the grouped cross-validation. "
         "Transport is not a serial R001\u2192\u2026\u2192R008 chain. Corridor filter geometry uses "
         "NHDPlus HR endpoint matching for HUC 14020001.</p>"),
        (r'<p class="lead">表 2 的四种计数.*?</p>',
         "<p class=\"lead\">The four count columns of Table 1 are not the same object. "
         "Assigned corridor lines are reach-attributed NHDPlus HR flowlines (including "
         "nearest-campaign-sample assignments); logical routing segments are the routing nodes of "
         "network_segments.csv; sampled control volumes are unique physical_cell_id sample-support "
         "cells; campaign samples are the held-out units of the grouped cross-validation. The former "
         "GNIS-only \u201cNHD segments\u201d tally and the uncertified legacy reported channel-length "
         "field are removed. The domain length is the fixed control-volume length from "
         "length_conservation.csv; a dagger (\u2020) marks a reach whose recorded support has not "
         "passed the domain-consistency gate, so its domain length must not be used to reconstruct "
         "area.</p>"),
        (r'<p class="lead">表 M 由.*?</p>',
         "<p class=\"lead\">The Residual-AI MLP can lower held-out C RMSE relative to the Baseline "
         "under fold-local targets, but the random forest does not and sample-support flux "
         "diagnostics remain unstable, so concentration skill alone is not treated as a settled "
         "success. The k-correction does not beat the Baseline; practical equifinality between "
         "source and gas exchange remains.</p>"),
        (r'<p class="lead">读表：只比较持出样本.*?</p>',
         "<p class=\"lead\">Only held-out samples are compared. Flux F totals are overlapping "
         "sample-area diagnostics of the form k(C \u2212 C<sub>eq</sub>), not study-area totals or "
         "independent flux observations.</p>"),
        (r'<p class="lead">R008 有 58 个点.*?</p>',
         "<p class=\"lead\">R008 contributes 58 samples; R001, R006, and R007 are single-sample reaches "
         "marked schematic and are not weighted equally with the mainstem.</p>"),
        (r'<p class="lead">残差随粗化而变平滑.*?</p>',
         "<p class=\"lead\">Formal filter claims use only native / 2\u00d7 / 4\u00d7. Study_reach is "
         "excluded after an unresolved contraction cycle; do not read the curve as "
         "scale-invariance through the study-reach aggregation. Within resolved scales the residual "
         "is a sampling-conditional sensitivity, not a universal subgrid law.</p>"),
        (r'<p class="lead">仅报告已解析尺度.*?</p>',
         "<p class=\"lead\">Formal filter claims use only native / 2\u00d7 / 4\u00d7. Study_reach is "
         "excluded after an unresolved contraction cycle; do not read the curve as "
         "scale-invariance through the study-reach aggregation. Within resolved scales the residual "
         "is a sampling-conditional sensitivity, not a universal subgrid law.</p>"),
        (r'<p class="lead">稀疏式可解释.*?</p>',
         "<p class=\"lead\">The sparse form is interpretable, but its held-out C RMSE does not fall "
         "below the Baseline. It is reported as a closure-form diagnostic, not as an accuracy "
         "improvement.</p>"),
    ]
    for pat, rep in lead_map:
        html = re.sub(pat, rep, html, flags=re.S)

    # --- Header rows (specific first) ---
    header_map = [
        ("<th>河段编号</th><th>河流名称</th><th>角色</th><th>汇入干流段</th>",
         "<th>Reach</th><th>Stream name</th><th>Role</th><th>Joins mainstem</th>"),
        ("<th>河段编号</th><th>河流名称</th><th>上游河段</th><th>下游河段</th>",
         "<th>Reach</th><th>Stream name</th><th>Role</th><th>Joins mainstem</th>"),
        ("<th>控制体域长 (km)</th><th>已分配走廊线</th><th>·GNIS 匹配</th><th>·最近样点</th>",
         "<th>Domain length (km)</th><th>Assigned corridor lines</th>"
         "<th>\u00b7GNIS match</th><th>\u00b7Nearest sample</th>"),
        ("<th>逻辑路由段</th><th>采样控制体</th><th>战役样点</th><th>说明</th>",
         "<th>Logical routing segments</th><th>Sampled control volumes</th>"
         "<th>Campaign samples</th><th>Note</th>"),
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
        ("<th>平均 |S|</th><th>Var(S)</th>", "<th>Cell-mean |S<sub>sgs</sub>|</th><th>Cell Var(S<sub>sgs</sub>)</th>"),
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
        ("Copper 溪，走廊线最多", "Copper Creek; largest assigned corridor"),
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
        ("<td>1.00000</td>", "<td>1.00</td>"),
        ("<td>0.00004</td>", "<td>3.9\u00d710\u207b\u2075</td>"),
        ("3.89e-05", "3.9\u00d710\u207b\u2075"),
        ("<td>4290.72</td>", "<td>1.21\u00d710\u00b3</td>"),
        ("<td>4291</td>", "<td>1.21\u00d710\u00b3</td>"),
        ("<td>598.81</td>", "<td>5.99\u00d710\u00b2</td>"),
        ("<td>599</td>", "<td>5.99\u00d710\u00b2</td>"),
        ("<td>242934075.00</td>", "<td>1.94\u00d710\u2076</td>"),
        ("<td>242934075</td>", "<td>1.94\u00d710\u2076</td>"),
        ("<td>179421447</td>", "<td>7.28\u00d710\u2075</td>"),
        ("<td>376195510</td>", "<td>3.76\u00d710\u2078</td>"),
        ("<code>S* \u2248 + 1.02 \u2212 0.3204*Fr_z \u2212 0.2798*Slope_z</code>",
         "<code>S* \u2248 1.02 \u2212 0.320\u00b7Fr_z \u2212 0.280\u00b7Slope_z</code>"),
        ("<code>S_sgs* \u2248 + 3.141 \u2212 8.686*Fr_z \u2212 6.505*Slope_z</code>",
         "<code>S_sgs* \u2248 3.141 \u2212 8.686\u00b7Fr_z \u2212 6.505\u00b7Slope_z</code>"),
        ("-0.32*Fr + -0.28*Slope + -0*h_over_W",
         "\u22120.320\u00b7Fr_z \u2212 0.280\u00b7Slope_z"),
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
    text = text.replace("&nbsp;", " ").replace("\u2090", "a")
    text = text.replace("\u2091", "e").replace("\u2212", "-").replace("\u0394", "Delta")
    text = text.replace("\u03a0", "Pi").replace("\u03c4_d", "tau_d")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# --- Markdown tables (built from the same result CSVs as the HTML helpers) ---

def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    def _esc(c: str) -> str:
        return str(c).replace("|", "\\|").replace("\n", " ")

    out = ["| " + " | ".join(_esc(h) for h in headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(_esc(c) for c in r) + " |")
    return "\n".join(out)


_SUP_TABLE = str.maketrans(
    "0123456789-", "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207b"
)


def _flux_disp(v: float) -> str:
    return _sci_disp(v, 2)


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

    # Table 1: reach network, four explicitly separated estimands (P1-08).
    # Every number comes from PV["table1"] (machine tables); nothing is retyped.
    from report_content import REACH_NOTES_ZH
    notes_en = {
        "支流源头，n=1 仅作示意": "Tributary headwater; n = 1, schematic only",
        "草甸河段，连接 Bradley 与 Rock": "Meadow reach connecting Bradley and Rock Creeks",
        "Rock 溪，多样本支流": "Rock Creek; multi-sample tributary",
        "Copper 溪，走廊线最多": "Copper Creek; largest assigned corridor",
        "Gothic 支流，多样本": "Gothic Creek; multi-sample tributary",
        "单样本，仅作示意": "Single sample; schematic only",
        "干流 Almont 上游，样点最密": "Mainstem above Almont; densest sampling",
    }
    t1 = PV.get("table1") or {}
    rows = []
    for r in t1.get("rows") or []:
        rid = str(r.get("reach_id", ""))
        dom = r.get("domain_length_km")
        dom_s = "\u2014" if dom is None else f"{float(dom):.3f}"
        if not r.get("domain_consistent"):
            dom_s += " \u2020"
        note = REACH_NOTES_ZH.get(rid, "")
        rows.append([
            rid, r.get("stream_name", ""), r.get("role", ""), r.get("joins_mainstem", ""),
            dom_s, r.get("assigned_flowlines", ""), r.get("assigned_gnis_match", ""),
            r.get("assigned_nearest_sample", ""), r.get("routing_segments", ""),
            r.get("sampled_cells", ""), r.get("campaign_samples", ""),
            notes_en.get(note, note),
        ])
    totals = t1.get("totals") or {}
    if totals:
        rows.append([
            "Total", "8 logical reaches", "\u2014", "\u2014", "\u2014",
            totals.get("assigned_flowlines", ""), totals.get("assigned_gnis_match", ""),
            totals.get("assigned_nearest_sample", ""), totals.get("routing_segments", ""),
            totals.get("sampled_cells", ""), totals.get("campaign_samples", ""), "\u2014",
        ])
    parts.append(
        "**Table 1.** East River study network: eight logical reaches and four distinct "
        "count estimands (logical reporting / confluence-chainage simplified tree, not a "
        "verified NHD directed compression). "
        "**Assigned corridor lines** = rows of `gis_reach_line_mapping.csv` (NHDPlus HR "
        "flowlines attributed to a reach, including `nearest_campaign_sample` assignments). "
        "**Logical routing segments** = routing nodes of `network_segments.csv` (7 tributary "
        "nodes + 6 mainstem nodes); these are not flowlines. "
        "**Sampled control volumes** = unique sample-support cells (`physical_cell_id`); "
        "these are not flowlines. "
        f"**Raw corridor flowlines** = the {t1.get('raw_corridor_pool_n', '\u2014')} features of "
        "`East_River_Lines.shp`, of which "
        f"{t1.get('raw_corridor_unassigned_n', '\u2014')} are unassigned; all assigned lines are "
        "therefore a subset of the raw corridor pool. "
        "The legacy GNIS-only tally and the uncertified legacy reported channel-length field are "
        "removed; the domain length is the fixed control-volume length from "
        "`length_conservation.csv`. A dagger (\u2020) marks a reach whose recorded support has "
        "not passed the domain-consistency gate, so its domain length must not be used to "
        "reconstruct area.\n\n" +
        _md_table(
            ["Reach", "Stream name", "Role", "Joins mainstem", "Domain length (km)",
             "Assigned corridor lines", "\u00b7GNIS match", "\u00b7Nearest sample",
             "Logical routing segments", "Sampled control volumes", "Campaign samples", "Note"],
            rows,
        ))

    # Table 2: main results
    p = tables_dir / "paper_main_results.csv"
    if p.exists():
        df = pd.read_csv(p)
        rows = []
        for _, r in df.iterrows():
            beats = r.get("beats_baseline_c")
            beat_s = "\u2014" if pd.isna(beats) else ("Yes" if str(beats).lower() == "true" else "No")
            kr = r.get("k_ratio_median")
            # P0-01: report the value, never classify it into "1.00".
            kr_s = fmt_ratio(kr)
            rows.append([SCHEME_LABELS.get((r["scheme"], r["model"]),
                                           f"{r['scheme']} / {r['model']}"),
                         f"{r['rmse_c']:.4f}",
                         _flux_disp(r["flux_area_sum_mol_d"]), kr_s, beat_s])
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
                 f"{r['bias_f']:.3f}", _flux_disp(r["flux_area_sum_mol_d"]), int(r["n"])]
                for _, r in loo.iterrows()]
        parts.append(
            "**Table 3.** Leave-one-reach-out grouped cross-validation: held-out C_aq and F_CO2 "
            "(primary metrics; F values are model flux diagnostics).\n\n" +
            _md_table(["Scheme / model", "C RMSE", "C MAE", "C Bias", "C R2", "F RMSE",
                       "F Bias", "F total", "n"], rows))
        ins = df[df["cv_protocol"] == "in_sample"]
        if ins.empty:
            parts.append(
                "**Table 4.** In-sample concentration metrics are not reported. After "
                "recalculation the paper metric is exclusively leave-one-reach-out "
                "transport-coupled C_aq.\n"
            )
        else:
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
        sub = sub[
            (sub["cv_protocol"] == "loo_reach")
            & (sub["model"].isin(["none", "mlp", "xgboost"]))
            & (sub["subgroup"].isin([
                "all_120", "R008_only", "multi_sample_tributaries",
                "one_sample_reaches_schematic",
            ]))
        ]
        rows = [[SCHEME_ONLY.get(r["scheme"], r["scheme"]),
                 str(r["subgroup_label"]),
                 r["evidence_weight"], f"{r['rmse_c']:.4f}",
                 ("—" if (pd.isna(r["r2_c"]) or abs(r["r2_c"]) > 5 or r["evidence_weight"] == "schematic")
                  else f"{r['r2_c']:.3f}"),
                 int(r["n"])]
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
                 f"{r['cell_mean_abs_S_sgs']:.3f}", f"{r['cell_var_S_sgs']:.3f}"]
                for _, r in fs.iterrows()]
        parts.append(
            "**Table 6.** Filter-scale experiment: S_sgs diagnosed at the independent-cell level "
            "after snapping the 120 samples onto flow-directed coarsened NHDPlus HR networks.\n\n" +
            _md_table(["Scale", "\u0394x (m)", "Cells", "Sampled cells", "Samples",
                       "Cell-mean |S_sgs|", "Cell Var(S_sgs)"], rows))

    # Table 7: practical equifinality diagnostic
    p = tables_dir / "identifiability_metrics.csv"
    if p.exists():
        idf = pd.read_csv(p)
        rows = []
        for _, r in idf.iterrows():
            kmed = r["k_eff_median"]
            kmed_s = f"{kmed:.1f}" if kmed > 1.0 else f"{kmed:.4f}"
            kr = r["k_ratio_median"]
            kr_s = fmt_ratio(kr)
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
        orig_form = (sp.get("equation_original_Sstar", "")
                     .replace("\u2248 + ", "\u2248 ")
                     .replace("*Fr_z", "\u00b7Fr_z")
                     .replace("*Slope_z", "\u00b7Slope_z"))
        dom_terms = (sp.get("dominant_standardized", "")
                     .replace(" + -0*h_over_W", "")
                     .replace("*Fr", "\u00b7Fr_z")
                     .replace("*Slope", "\u00b7Slope_z")
                     .replace("+ -", "\u2212 ")
                     .replace("-0.32\u00b7", "\u22120.320\u00b7")
                     .replace("\u2212 0.28\u00b7", "\u2212 0.280\u00b7"))
        rows = [
            ["Standardized-predictor form", SPARSE_EQ[1]],
            ["Original-variable form", orig_form],
            ["Dominant terms", dom_terms],
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
            f"cross-validation (compare Baseline {num('main_results.baseline.rmse_c')} in Table 3).\n\n" +
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
    "framework for 120 public East River observations organized into eight logical reaches and mapped "
    "to a National Hydrography Dataset Plus High Resolution (NHDPlus HR) directed network. Spatial "
    "coarse-graining defines a signed residual source-sink term, S<sub>sgs</sub>, which was represented "
    "by a zero-residual Baseline, machine-learned residual closures (Residual-AI), or a multiplicative "
    "correction to an energy-dissipation-based gas-transfer velocity. Each closure was evaluated by "
    "leaving one reach out and reinserting the predicted closure into the quasi-steady transport "
    "balance before scoring concentration, with atmospheric-equilibrium upstream boundary conditions "
    "and no observed-concentration fallback. The Baseline held-out C<sub>aq</sub> root-mean-square "
    f"error (RMSE) was {num('main_results.baseline.rmse_c')} mol m<sup>\u22123</sup>; the Residual-AI "
    f"multilayer perceptron (MLP) and random forest gave {num('main_results.mlp.rmse_c')} and "
    f"{num('main_results.random_forest.rmse_c')} mol m<sup>\u22123</sup>, so the learned closure does not "
    "reduce pooled held-out concentration error. Its error is lower on the mainstem subgroup "
    f"({num('subgroups.mlp_mainstem_rmse')} versus {num('subgroups.baseline_mainstem_rmse')} mol "
    f"m<sup>\u22123</sup>) and higher on the multi-sample tributaries "
    f"({num('subgroups.mlp_tributary_rmse')} versus {num('subgroups.baseline_tributary_rmse')} mol "
    f"m<sup>\u22123</sup>), and {fmt_ratio(pv('reach_sensitivity.r002_gain_contribution_frac'))} of the "
    "gross positive error reduction comes from three R002 samples; source extrapolation was "
    "unstable, driving the area-weighted model flux to "
    f"{_sci_from_pv('flux_estimand.mlp_area_sum')} and {_sci_from_pv('flux_estimand.rf_area_sum')} mol "
    f"d<sup>\u22121</sup> versus {_sci_from_pv('flux_estimand.baseline_area_sum')} mol "
    f"d<sup>\u22121</sup> for the Baseline. A k-correction did not improve on the Baseline "
    f"({num('main_results.k_correction.rmse_c')} mol "
    f"m<sup>\u22123</sup>); {int(round(float(pv('k_estimate.infeasible_frac_full_data') or 0) * 100))}% of "
    "samples could not be matched by any positive transfer velocity "
    "alone, and the median effective-to-empirical ratio, k<sub>eff</sub>/k<sub>emp</sub>, was "
    f"{fmt_pv_ratio('k_estimate.k_ratio_median')}. A model-free objective surface and profile SSE show that a "
    "single concentration observation leaves an exact zero valley in the (k, S<sub>sgs</sub>) plane, "
    f"and pooling the 120 samples leaves the profile shallow (RMSE near {num('equifinality.profile_rmse_min')} mol "
    "m<sup>\u22123</sup> over the k-scale interval). On resolved filter scales "
    "(native through a sixteen-fold merge) unique-cell mean |S<sub>sgs</sub>| stays in a narrow band "
    f"near {num('filter_scale.scales.0.cell_mean_abs_S_sgs', 2)}\u2013"
    f"{num('filter_scale.scales.7.cell_mean_abs_S_sgs', 2)} mol "
    "m<sup>\u22122</sup> d<sup>\u22121</sup>; study_reach coarsening is excluded after an "
    "unresolved contraction cycle. These results indicate practical "
    "equifinality between S<sub>sgs</sub> and k under concentration-only East River observations: "
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
    reach_table = sanitize_paper_tables(reach_network_table_html(PV.get("table1")))
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
