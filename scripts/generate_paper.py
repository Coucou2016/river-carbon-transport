# -*- coding: utf-8 -*-
"""Generate self-contained paper.html and paper.md (IMRaD methods paper).

Framing follows docs/PAPER_PLAN.md: methods & diagnostics, NOT "AI improves accuracy".
Real numbers only from results/tables/*.csv. Figures base64-embedded.
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
from report_shared import glossary_html  # noqa: E402

FIG_DIR = ROOT / "results" / "figures"
OUT_HTML = ROOT / "paper.html"
OUT_MD = ROOT / "paper.md"

# Paper figure set (PAPER_PLAN §4.6) — caption, short label for MD
PAPER_FIGURES: list[tuple[str, str, str]] = [
    (
        "les_filter_conceptual.png",
        "<strong>Fig. 1</strong> LES 类比过滤概念：细 NHD 线段 → 滤波窗 Δx → 粗控制体上的 S<sub>sgs</sub>。",
        "Fig. 1 LES filter conceptual",
    ),
    (
        "gis_reach_assignment_map.png",
        "<strong>Fig. 2a</strong> GIS 河网：研究河段 R001–R008 与 NHD 矢量线对应。",
        "Fig. 2a Reach assignment map",
    ),
    (
        "gis_samples_on_network.png",
        "<strong>Fig. 2b</strong> 120 个战役样点叠加于 NHD 河网（R008 n=58 主导）。",
        "Fig. 2b Samples on network",
    ),
    (
        "nested_cv_rmse_bar.png",
        "<strong>Fig. 3</strong> reach-held-out 分组交叉验证：Baseline / Residual-AI / k 修正的持出 C<sub>aq</sub> RMSE（主图）。",
        "Fig. 3 Nested-CV RMSE bar",
    ),
    (
        "nested_cv_scatter_holdout.png",
        "<strong>Fig. 4</strong> 留一河段持出：观测 vs 预测 C<sub>aq</sub>（Residual-AI MLP）。",
        "Fig. 4 Holdout scatter",
    ),
    (
        "identifiability_k_vs_sgs.png",
        "<strong>Fig. 5</strong> 可辨识性：k<sub>eff</sub> 与隐含 S<sub>sgs</sub>，及 Residual-AI 持出源项对照。",
        "Fig. 5 Identifiability k vs S",
    ),
    (
        "filter_scale_sgs.png",
        "<strong>Fig. 6</strong> 滤波尺度：平均 |S<sub>sgs</sub>| 与方差随 Δx。",
        "Fig. 6 Filter-scale S_sgs",
    ),
    (
        "dimensionless_coefficients.png",
        "<strong>Fig. 7</strong> 无量纲 Π 群稀疏闭合系数（标准化 LASSO）。",
        "Fig. 7 Dimensionless sparse coefficients",
    ),
    (
        "subgroup_rmse_r008_vs_trib.png",
        "<strong>Fig. S1</strong> 子组误差：R008 vs 多样本支流 vs 单样本示意河段。",
        "Fig. S1 Subgroup RMSE",
    ),
    (
        "ablation_flux_comparison.png",
        "<strong>Fig. S2</strong> 三种闭合的持出 F<sub>CO₂</sub> 合计与通量 RMSE（模型诊断）。",
        "Fig. S2 Flux ablation",
    ),
    (
        "identifiability_tradeoff.png",
        "<strong>Fig. S3</strong> 浓度–通量权衡：k<sub>eff</sub>/k<sub>emp</sub> 与持出 RMSE / 通量合计。",
        "Fig. S3 Identifiability tradeoff",
    ),
    (
        "filter_scale_sgs_box.png",
        "<strong>Fig. S4</strong> 各滤波尺度上 120 样点 |S<sub>sgs</sub>| 分布。",
        "Fig. S4 Filter-scale box",
    ),
    (
        "obs_vs_model_scatter_large.png",
        "<strong>Fig. A1</strong> 样本内散点（附录；R²≈0.997 为过拟合肖像，非主结论）。",
        "Fig. A1 In-sample scatter (appendix)",
    ),
]


def b64_img(name: str) -> str:
    p = FIG_DIR / name
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode("ascii")


def figure_blocks() -> tuple[str, list[str]]:
    """Embed figures with journal-style captions only (no teaching digressions)."""
    parts: list[str] = []
    embedded: list[str] = []
    for fname, caption, _ in PAPER_FIGURES:
        data = b64_img(fname)
        if not data:
            continue
        embedded.append(fname)
        parts.append(
            f"""  <div class="figure-block">
    <img src="data:image/png;base64,{data}" alt="{fname}">
    <div class="fig-caption">{caption}</div>
  </div>"""
        )
    return "\n".join(parts), embedded


def sanitize_paper_tables(html: str) -> str:
    """Strip report/process diary language from shared table HTML helpers."""
    html = re.sub(
        r"<p class=\"lead\">表 M 由 <code>scripts/build_paper_tables\.py</code>.*?</p>",
        "<p class=\"lead\">表 M：留一河段持出输运耦合评价主结果。"
        "Residual-AI 与稀疏 Π <strong>均未</strong>优于 Baseline；"
        "k 修正略降 C 但模型通量诊断崩溃 → practical equifinality。</p>",
        html,
        flags=re.S,
    )
    html = re.sub(r"<code>scripts/[^<]+</code>", "repository table builders", html)
    html = re.sub(r"<code>src/[^<]+</code>", "the accompanying open-source implementation", html)
    return html


def strip_tags(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def main() -> None:
    figs_html, embedded = figure_blocks()
    n_figs = len(embedded)
    missing = [f for f, _, _ in PAPER_FIGURES if f not in embedded]
    tables = sanitize_paper_tables(
        paper_main_table_html() + nested_cv_tables_html() + innovation_tables_html()
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>河网 CO₂ 输运的多尺度过滤与亚网格闭合可辨识性 — East River 公开数据实验</title>
<style>
:root {{
  --primary: #1a3a5c;
  --accent: #2c6e8a;
  --bg: #f7f8fa;
  --text: #222;
  --muted: #555;
  --border: #d0d7de;
  --table-head: #e8eef3;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: "Times New Roman", "Songti SC", "SimSun", "Noto Serif SC", serif;
  font-size: 17px;
  line-height: 1.8;
  color: var(--text);
  background: var(--bg);
}}
.container {{ max-width: 920px; margin: 0 auto; padding: 2rem 1.5rem 4rem; }}
.header {{ text-align: center; margin-bottom: 2rem; padding-bottom: 1.5rem; border-bottom: 2px solid var(--primary); }}
.header h1 {{ font-size: 1.55rem; color: var(--primary); line-height: 1.45; margin-bottom: 0.75rem; }}
.header .en-title {{ font-size: 1.05rem; color: var(--accent); font-style: italic; margin-bottom: 1rem; }}
.header .authors {{ color: var(--muted); margin: 0.5rem 0; }}
.header .affil {{ font-size: 0.92rem; color: var(--muted); }}
.abstract {{
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 1.25rem 1.5rem;
  margin: 1.5rem 0;
}}
.abstract h2 {{ font-size: 1.1rem; margin-bottom: 0.75rem; color: var(--primary); border: none; padding: 0; }}
.kw {{ margin-top: 0.85rem; font-size: 0.92rem; color: var(--muted); }}
.lead {{ margin: 0.85rem 0 1.1rem; }}
section {{ margin-bottom: 2rem; }}
h2 {{
  font-size: 1.35rem;
  color: var(--primary);
  border-left: 4px solid var(--accent);
  padding-left: 0.7rem;
  margin: 1.75rem 0 0.9rem;
}}
h3 {{ font-size: 1.12rem; color: var(--accent); margin: 1.25rem 0 0.7rem; }}
p {{ margin-bottom: 0.9rem; text-align: justify; }}
ul, ol {{ margin: 0.5rem 0 1rem 1.5rem; }}
li {{ margin: 0.25rem 0; }}
table {{
  width: 100%;
  border-collapse: collapse;
  margin: 1.1rem 0 1.5rem;
  font-size: 0.92rem;
  background: #fff;
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}}
th, td {{ border: 1px solid var(--border); padding: 0.55rem 0.65rem; text-align: center; }}
th {{ background: var(--table-head); color: var(--primary); font-weight: 600; }}
td.left {{ text-align: left; }}
caption {{
  caption-side: top;
  text-align: left;
  font-weight: 600;
  color: var(--primary);
  padding: 0.45rem 0;
  font-size: 0.92rem;
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}}
.figure-block {{
  margin: 1.75rem 0 2.1rem;
  text-align: center;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.1rem 1.1rem 1.35rem;
}}
.figure-block img {{ max-width: 100%; height: auto; display: block; margin: 0 auto; }}
.fig-caption {{
  text-align: left;
  font-size: 0.98rem;
  color: var(--primary);
  margin-top: 0.85rem;
  line-height: 1.65;
  font-weight: 600;
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}}
.fig-analysis {{
  text-align: left;
  font-size: 0.95rem;
  color: var(--text);
  margin-top: 0.65rem;
  padding: 0.9rem 1rem;
  background: #f8fafb;
  border-left: 4px solid var(--accent);
  line-height: 1.8;
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}}
.fig-analysis p {{ margin-bottom: 0.65rem; }}
.glossary {{
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.1rem 1.3rem;
  margin: 1.25rem 0;
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}}
.term {{ margin: 1rem 0 1.2rem; padding-bottom: 0.85rem; border-bottom: 1px dashed var(--border); }}
.term:last-child {{ border-bottom: none; }}
.term-sym {{ font-weight: 700; color: var(--primary); margin-right: 0.5rem; }}
.term-full {{ color: var(--accent); font-weight: 600; }}
.term-body {{ font-size: 0.95em; line-height: 1.8; text-align: justify; }}
.note {{
  background: #fff8e6;
  border: 1px solid #f0d78c;
  border-radius: 4px;
  padding: 0.7rem 1rem;
  font-size: 0.9rem;
  margin: 1rem 0;
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}}
.tbd {{ color: #c0392b; font-style: italic; }}
.footer {{
  margin-top: 2.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  font-size: 0.85rem;
  color: var(--muted);
  text-align: center;
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}}
@media print {{
  body {{ font-size: 11pt; }}
  .figure-block {{ break-inside: avoid; }}
}}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>河网 CO₂ 闭合的输运耦合评价：浓度单变量观测下的 practical equifinality 证据</h1>
  <div class="en-title">Transport-coupled evaluation of river-network CO₂ closures: Evidence for practical equifinality under concentration-only observations</div>
  <div class="authors">作者：待补充</div>
  <div class="affil">单位：待补充 · 通讯作者：待补充</div>
  <div class="affil" style="margin-top:0.6rem;">目标期刊：Environmental Modelling &amp; Software（方法/诊断）· 结构仿照 Markovich et al. (2022) EMS · 文稿日期：2026-08-17 · 内嵌图 {n_figs} 幅</div>
</div>

<section id="abstract">
  <div class="abstract">
    <h2>Abstract</h2>
    <p>Environmental-model evaluation can favor a closure that reproduces an observed state while assigning model discrepancy to a different process term.
    We develop a transport-coupled diagnostic framework for river-network CO<sub>2</sub> using public East River observations (n=120; eight logical reaches),
    spatial coarse-graining, and leave-one-reach-out grouped evaluation. The filter defines a residual source/sink term S<sub>sgs</sub>
    that represents unresolved contributions to the filtered mass balance.
    Residual-AI did not improve held-out concentration prediction: C<sub>aq</sub> RMSE was 0.0573 for an MLP and 0.0745 for a random forest,
    compared with 0.0284 for the process Baseline. A k-correction reduced C<sub>aq</sub> RMSE to 0.0244, but this coincided with median
    k<sub>eff</sub>/k<sub>emp</sub>≈3.35×10<sup>−4</sup> and a decrease in the sample-summed model-derived F<sub>CO₂</sub> diagnostic from ~3.24 to ~0.03.
    Across the implemented filter scales, mean |S<sub>sgs</sub>| decreased from 1.92 at Δx≈838&nbsp;m to 1.00 at the study-reach scale.
    A sparse dimensionless closure remained less accurate than the Baseline under reach-held-out evaluation (RMSE 0.0506).
    These results show that lower concentration error need not uniquely support a particular allocation of model discrepancy between unresolved
    source/sink processes and gas exchange. The contribution is therefore methodological rather than predictive: an operable filtering definition,
    a transport-coupled grouped evaluation protocol, and empirical evidence consistent with practical closure compensation under concentration-only observations.</p>
    <p><strong>中文摘要（非投稿主摘要）：</strong>环境模型即使能够较好再现浓度，也可能将模型偏差补偿到不同的过程项中。
    本文基于 East River 公开观测（n=120；8 逻辑河段）构建空间粗粒化与输运耦合评价框架。
    Residual-AI 未提高持出浓度预测（MLP 0.0573、RF 0.0745 vs Baseline 0.0284）；
    k 修正降至 0.0244，但伴随 k<sub>eff</sub>/k<sub>emp</sub>≈3.35×10<sup>−4</sup> 与模型 F<sub>CO₂</sub> 诊断由 ~3.24 降至 ~0.03。
    贡献不是证明机器学习提高精度，而是诊断协议与 practical closure compensation 证据。</p>
    <div class="kw"><strong>Highlights:</strong>
      (1) Residual-AI closures do not outperform the process Baseline on held-out reaches (0.0573/0.0745 vs 0.0284).
      (2) Lower concentration RMSE coincides with collapse of a model-derived flux diagnostic (~3.24→~0.03).
      (3) Transport-coupled evaluation exposes practical closure compensation under concentration-only observations.
    </div>
    <div class="kw"><strong>关键词：</strong>河网 CO₂ 输运；亚网格闭合；practical equifinality；空间过滤；reach-held-out CV；输运耦合机器学习；East River</div>
    <div class="kw"><strong>Keywords:</strong> River carbon cycling; environmental model evaluation; transport-coupled validation; spatial coarse-graining; subgrid residual; gas-transfer velocity; practical equifinality; grouped cross-validation</div>
  </div>
</section>

<section id="glossary">
  <h2>术语表</h2>
  {glossary_html()}
</section>

<section id="intro">
  <h2>1. Introduction</h2>
  <p>Environmental-model evaluation is not equivalent to minimizing a single prediction-error metric.
  A model may reproduce an observed state while compensating for structural error through parameters or process terms that are only weakly constrained by the available observations.
  Bennett et al. (2013) therefore argue for model-performance characterization that reflects modelling purpose, data limitations, graphical and numerical diagnostics, and systematic model–data divergence rather than relying on a single statistic.
  Markovich et al. (2022) similarly evaluate alternative methods explicitly under model error, while Vilas et al. (2023) treat model–data discrepancy as information that can reveal limitations in models, observations, or their interaction.
  For river-carbon models, this raises a practical evaluation question: when several unresolved-process representations can alter the same predicted CO<sub>2</sub> concentration,
  does lower concentration error identify a more credible closure, or can it arise through compensation among process terms?</p>
  <p>River networks are active components of the terrestrial carbon cycle, transporting dissolved carbon while exchanging CO<sub>2</sub> with the atmosphere and receiving spatially heterogeneous internal and external inputs.
  At reach scale, these processes are necessarily represented through aggregated state variables and parameterizations.
  Saccardi and Winnick (2021) demonstrated a stream-network CO<sub>2</sub> modelling framework for the East River watershed in which downstream transport, CO<sub>2</sub> sources, and atmospheric exchange jointly determine concentration.
  Gas exchange is commonly represented through an empirical transfer velocity, with hydraulic formulations such as those developed by Raymond et al. (2012).
  Because both unresolved source/sink terms and gas exchange influence the same concentration balance, errors attributed to either component may compensate one another when concentration provides the dominant observational constraint.</p>
  <p>We examine this issue by defining an explicit spatial coarse-graining experiment.
  Filtering the reach-scale mass balance produces a residual source/sink term S<sub>sgs</sub>, defined as the contribution required to close the filtered balance after resolved transport and gas exchange are recomputed.
  This construction is analogous at the operator level to coarse-graining approaches used to diagnose unresolved terms in other modelling domains, including learned subgrid parameterization studies such as Yuval and O’Gorman (2020).
  Here, however, S<sub>sgs</sub> is not interpreted as a turbulence closure or as a direct measurement of a unique unresolved biogeochemical process.
  It is a filter-induced model residual whose magnitude and learnability can be evaluated explicitly as spatial aggregation changes.
  Unpublished draft inspirations (Gao et al., <em>The Innovation</em>) are <strong>待补充 DOI</strong> only and do not bound novelty.</p>
  <p>The framework is tested using 120 public East River observations organized into eight logical reaches and mapped to an NHDPlus HR representation.
  We compare a process Baseline with S<sub>sgs</sub>=0, Residual-AI closures that predict S<sub>sgs</sub>, and a multiplicative correction to the empirical gas-transfer coefficient.
  Evaluation is transport-coupled: a closure predicted for a held-out reach is reinserted into the quasi-steady mass balance before C<sub>aq</sub> is scored.
  The primary split is leave-one-reach-out grouped evaluation with fold-specific preprocessing.
  This experiment evaluates closure behaviour across held-out logical reaches rather than fully independent forecasting:
  when an upstream concentration state is unavailable, the implemented solver uses observed C<sub>aq</sub> as a fallback boundary condition.
  Sampling is also strongly imbalanced among the logical reaches (R008 n=58 vs R001/R006/R007 n=1 schematic),
  and the spatial-filter implementation includes a coordinate-ordering fallback rather than a fully directed network-topological operator.
  These boundaries are treated as part of the evaluation design rather than hidden implementation details.</p>
  <p>Three questions organize the study. First, how does the diagnosed magnitude of S<sub>sgs</sub> vary under the implemented spatial coarse-graining?
  Second, can corrections assigned to S<sub>sgs</sub> and gas exchange be distinguished by concentration-dominated evaluation once both are coupled to the same transport balance?
  Third, does a compact dimensionless representation of S<sub>sgs</sub> retain predictive utility across held-out reaches?
  The contribution is methodological rather than an accuracy claim: we provide an operable definition of a filter-induced residual,
  evaluate alternative closures through transport-coupled grouped holdout tests, and use the disagreement between concentration and model-process diagnostics to examine practical closure compensation.
  We do not claim that machine learning improves prediction, that the inferred CO<sub>2</sub> flux is independently validated, or that the resulting closure relationships are universal across river networks.</p>
  <div class="note"><strong>DO NOT CLAIM：</strong>Residual-AI beats Baseline；in-sample R<sup>2</sup>=0.997 as skill；
  F<sub>CO₂</sub> independently validated；structural non-identifiability proved；fully topology-aware network filter；CONUS / CH₄ / StreamPULSE coverage.</div>
</section>

<section id="methods">
  <h2>2. Methods</h2>
  <p class="lead"><em>English methods box (EMS-facing).</em>
  Task: diagnose whether residual or k-correction closures generalize under concentration-only observations.
  Protocol: define an operational spatial filter → close the quasi-steady mass balance three ways → evaluate with
  <strong>leave-one-reach-out grouped, transport-coupled cross-validation</strong>
  (predict closure on held-out reaches, then re-solve physics). Primary metric: held-out C<sub>aq</sub> RMSE (mol m<sup>−3</sup>).
  Secondary: sample-summed model flux diagnostic ∑F<sub>CO₂</sub> (mol m<sup>−2</sup> d<sup>−1</sup>).
  Failure modes are reported, not discarded.</p>

  <h3>2.1 Study data and river-network representation</h3>
  <p>HUC 14020001；120 样点（2019-08-02–11）；8 逻辑河段（R001=1, R002=3, R003=15, R004=24, R005=17, R006=1, R007=1, R008=58）；
  NHD 393 / NHDPlus HR 8212 flowlines；USGS 09112500；GNIS 匹配 85；捕捉中位距离约 8.5 m。
  DIC/DOC 约 41/120；Alk/N/P/PAR 缺失<strong>待补充</strong>；WQP 同日合并检索失败（0/120）；StreamPULSE 检索无 East River 站点（已排除）。
  真实数据唯一；无合成样点。因河段样本极不均衡，pooled 误差须与 reach-level 证据权重一并解读；n=1 河段仅作示意。逻辑河段 R001–R008 按研究设定的 STREAM_NETWORK_ORDER 赋予上下游关系（顺序链），用于准稳态闭合实验的可重复控制体组织，<strong>不是</strong>完整 NHDPlus 物理拓扑的替代描述。计算宽度 W 来自多样点河段的坐标展宽代理（并裁剪）或单点河段回退宽度，进入水深/流速/k<sub>600</sub>/A<sub>s</sub>=L·W；故几何假设影响输运与诊断，须与“仅示意横断面”区分披露。定性结论对宽度敏感时应优先报告敏感性，而非为保数字而隐瞒（本轮冻结主表，几何审计<strong>待补充</strong>敏感性表）。</p>
  {REACH_NETWORK_TABLE_HTML}

  <h3>2.2 Quasi-steady CO₂ transport and gas exchange</h3>
  <p><strong>Eq. (1) mass balance (mol s<sup>−1</sup>):</strong>
  Q(C<sub>in</sub>−C) + (A<sub>s</sub>/τ<sub>d</sub>)[S<sub>sgs</sub> − k(C−C<sub>eq</sub>)] = 0，
  其中 τ<sub>d</sub>=86400 s d<sup>−1</sup>，A<sub>s</sub>=L·W 为水面平面面积 (m<sup>2</sup>)，
  Q: m<sup>3</sup> s<sup>−1</sup>，C: mol m<sup>−3</sup>，k: m d<sup>−1</sup>，S<sub>sgs</sub>: mol m<sup>−2</sup> d<sup>−1</sup>。
  定义日尺度面积归一化流量 q<sub>A</sub>=τ<sub>d</sub>·Q/A<sub>s</sub> (m d<sup>−1</sup>)，则等价形式
  <strong>Eq. (4)</strong> q<sub>A</sub>(C<sub>in</sub>−C)+S<sub>sgs</sub>−k(C−C<sub>eq</sub>)=0 各项均为 mol m<sup>−2</sup> d<sup>−1</sup>。
  <strong>禁止</strong>裸写 (Q/A) 而不显式换算时间基准。A<sub>s</sub> ≠ 水力横断面积 A<sub>c</sub>；若需 bulk velocity，U=Q/A<sub>c</sub>。</p>
  <p><strong>Eq. (2) 模型通量密度：</strong>F<sub>CO₂</sub>=k(C−C<sub>eq</sub>) (mol m<sup>−2</sup> d<sup>−1</sup>)；
  表中 “F total” = ∑<sub>i</sub> F<sub>CO₂,i</sub>（sample-summed model flux diagnostic），非流域积分通量。
  嵌套/分组评价中，模型 F 使用 transport-predicted C 与当时方案的 k（Baseline/Residual-AI 用 k<sub>emp</sub>；k-correction 用 k<sub>eff</sub>）；
  对比用的观测代理通量用 empirical k 与观测 C（见开源实现中的输运耦合评分程序）。</p>
  <p><strong>k<sub>600</sub>→k<sub>CO₂</sub>：</strong>Raymond et al. (2012) ln(k<sub>600</sub>)=5.139+0.594 ln(u)+0.403 ln(slope)
  （u: m s<sup>−1</sup>，slope: m/m）得 k<sub>600</sub> (m d<sup>−1</sup>)；再经
  k<sub>emp</sub>=k<sub>600</sub>(Sc(T)/600)<sup>−0.5</sup>（Sc 为 CO₂ Schmidt number）进入 Eq. (1)。
  符号上 k<sub>600</sub> ≠ k<sub>emp</sub>。C<sub>eq</sub> 取预处理表中的 C_eq_mol_m3（Henry / 大气 pCO₂ / 温度路径以开源代码与 HydroShare 衍生字段为准；细节<strong>待补充</strong>完整公式附录）。
  横断面可视化为理想化梯形；竖直流速剖面采用抛物线剖面（非 ADCP；亦非声称的实测 log-law）。主文指标不把示意剖面当作测量产品。</p>

  <h3>2.3 Spatial filtering and S<sub>sgs</sub> diagnosis</h3>
  <p><strong>Motivation / Mechanism / Role：</strong>河段尺度输运方程形式平均后，未分辨贡献进入残差源汇，需要可操作的 Δx 定义而非口号式“亚网格”。
  在同一 logical reach 内做 reach-local 空间粗粒化：按沿程 chainage（回退为中点 Y→X）累积原生 NHDPlus 段长并合并；Δx = 滤波单元平均长度（有样点单元另行报告）。
  排序回退为中点 Y→X（非完整有向河网拓扑）——作为算子边界披露，本修订不重算冻结指标。
  诊断残差 <strong>Eq. (5)</strong> S<sub>sgs</sub>=k(C−C<sub>eq</sub>)−q<sub>A</sub>(C<sub>in</sub>−C)。
  “LES-analog”仅指本实现算子下的 resolved/unresolved 分离，不表示 Navier–Stokes 湍流闭合，亦不声称普适河网 SGS 标度律。
  S<sub>sgs</sub> = filter-induced closure residual（可吸收测量误差、简化输运误差、遗漏过程），非某一真实未测通量的直接观测。</p>

  <h3>2.4 Alternative unresolved-process closures</h3>
  <p>(A) Baseline：S<sub>sgs</sub>=0，Raymond 型 k<sub>emp</sub>。
  (B) Residual-AI：学习 S<sub>sgs</sub>（MLP / RF；seed=42）。
  (C) k-correction：k<sub>eff</sub>=k<sub>emp</sub> exp(g<sub>θ</sub>(X))（XGBoost；g<sub>θ</sub> 无量纲）；
  文中报告 nested-CV <strong>median</strong> k<sub>eff</sub>/k<sub>emp</sub>≈3.4×10<sup>−4</sup>。
  Baseline 是公平空闭合，不是“物理模型的输运”。比较目标是闭合形式与验证协议，而非另写一套基准水动力。</p>

  <h3>2.5 Grouped transport-coupled cross-validation</h3>
  <p>Closure generalization was evaluated using leave-one-reach-out grouped cross-validation across the eight logical reaches.
  Missing-value imputation and feature scaling were fitted using the training reaches only and then applied to the held-out reach.
  No inner hyperparameter-selection loop is implied by this terminology; accordingly, we refer to the procedure as
  <strong>grouped cross-validation</strong> rather than nested cross-validation.
  Predicted closures were subsequently coupled back to the quasi-steady transport calculation before C<sub>aq</sub> was scored.
  When an upstream concentration state was unavailable, the observed C<sub>aq</sub> at the current sample was used as a fallback c<sub>in</sub>.
  The experiment therefore evaluates closure generalization under partially observed boundary conditioning rather than fully target-blind concentration forecasting.
  Grouped-by-date evaluation is reported as a time sensitivity analysis (not nested inside the reach split).</p>

  <h3>2.6 Metrics and flux diagnostic</h3>
  <p>Primary metric: held-out C<sub>aq</sub> RMSE (mol m<sup>−3</sup>).
  Gas exchange was summarized using the model-derived flux-density diagnostic F<sub>CO₂</sub>=k(C−C<sub>eq</sub>),
  evaluated using the transport-predicted concentration for each closure configuration.
  For model comparison we report the sample-summed diagnostic ΣF<sub>CO₂</sub>.
  This quantity compares changes in inferred model process allocation across closures; it is neither an independently observed evasion flux nor a spatially integrated watershed CO<sub>2</sub> flux.</p>

  <h3>2.7 Practical equifinality diagnostic</h3>
  <p><strong>Eq. (6)</strong> S<sub>implied</sub>=(k<sub>emp</sub>−k<sub>eff</sub>)(C−C<sub>eq</sub>)：
  在固定 C 与 resolved transport 状态下，使保留 k<sub>emp</sub> 的模型与使用 k<sub>eff</sub>、无额外源汇的模型局部等价所需的源汇调整。
  语言：practical equifinality / compensating closure behaviour；<strong>不是</strong> formal structural non-identifiability 证明。</p>

  <h3>2.8 Sparse dimensionless closure</h3>
  <p>标准化 LASSO（PySINDy 未安装则用稀疏式中间件；思想参考 Xie et al. 2022）。
  展示式 S*<sub>z</sub>≈1.059+1.536 Fr−1.669 Slope−2.179 h/W 为 standardized-space 系数形式（下标 z 提示 z-score 空间；
  Fr、Slope、h/W 定义与 fold-training 标准化路径见开源实现）。
  Reach-held-out C RMSE≈0.0506（正文可写 ≈0.051），仍差于 Baseline 0.0284——贡献为紧凑诊断表示，非预测胜出。</p>

  <div class="note"><strong>Evaluation independence (Round-1/3 audit)：</strong>
  外层 leave-one-reach-out + fold-specific imputation/scaling；优先称 reach-held-out / grouped CV。
  c<sub>in</sub> 观测回退与 Y→X 过滤排序为已披露边界；本修订冻结 Δx / RMSE 数字不重跑。</div>
</section>

<section id="results">
  <h2>3. Results</h2>
  <p class="lead"><strong>Results lead (H1→H2→H3 falsification, Round 9):</strong>
  (3.1) H1 — Residual closures do not improve reach-held-out concentration prediction
  (Baseline 0.0284; Residual-AI MLP 0.0573; RF 0.0745).
  (3.2) H2 — k-correction lowers C<sub>aq</sub> RMSE to 0.0244 (concentration-metric only).
  (3.3) H3 — that gain coincides with median k<sub>eff</sub>/k<sub>emp</sub>≈3.35×10<sup>−4</sup>
  and sample-summed model-derived ΣF<sub>CO₂</sub> ~3.24→~0.031.
  (3.4) Practical S<sub>sgs</sub>–k compensation (Eq. 6).
  (3.5) Filter-scale |S<sub>sgs</sub>| 1.92→1.00 (supporting).
  (3.6) Sparse Π compact but predictively insufficient (0.0506&gt;0.0284; supporting).
  Metrics are from repository-derived evaluation tables.</p>
{tables}
  <h3>3.1–3.5 图件</h3>
  <p>下列图按论文计划编号；图注为期刊体例。教学式逐步读图说明保留在研究验证报告中，不进入本稿正文。</p>
{figs_html}
</section>

<section id="discussion">
  <h2>4. Discussion</h2>
  <h3>4.1 Residual-closure generalization failure is a modelling diagnosis</h3>
  <p>The most direct result is negative: Residual-AI did not outperform the process Baseline under leave-one-reach-out grouped evaluation.
  The MLP and random-forest closures produced C<sub>aq</sub> RMSE values of 0.0573 and 0.0745, respectively, compared with 0.0284 for the Baseline.
  This result should not be interpreted as evidence that machine-learning closures are generally unsuitable for river-carbon modelling.
  Rather, it shows that a residual diagnosed from the present resolved model, predictors, spatial representation, and sampling design did not retain sufficient transferable information to improve concentration prediction after transport coupling.
  In the evaluation logic of Bennett et al. (2013) and Vilas et al. (2023), this discrepancy is itself diagnostic because it identifies a mismatch between apparent learnability of the residual and usefulness of that representation under held-out application.</p>

  <h3>4.2 Concentration skill does not uniquely determine process allocation</h3>
  <p>The k-correction provides the complementary result. Its C<sub>aq</sub> RMSE of 0.0244 is lower than the Baseline value of 0.0284,
  but this reduction coincides with median k<sub>eff</sub>/k<sub>emp</sub>≈3.35×10<sup>−4</sup> and a decrease in the sample-summed model-derived F<sub>CO₂</sub> diagnostic from 3.24 to 0.031.
  Because no independent evasion observations are available, these values do not demonstrate that the Baseline flux is correct or that the corrected flux is wrong.
  They instead show that concentration performance alone can favor a substantially different allocation of the model balance.
  The lower RMSE therefore provides evidence of improved concentration fit, but not independent evidence of improved process fidelity.</p>

  <h3>4.3 Practical equifinality is restricted to a closure-compensation mode</h3>
  <p>We use practical equifinality in a deliberately restricted sense.
  At fixed concentration and resolved transport state, S<sub>implied</sub>=(k<sub>emp</sub>−k<sub>eff</sub>)(C−C<sub>eq</sub>) defines an algebraic direction along which a change in gas exchange can be compensated by an additional source/sink contribution.
  The empirical Baseline–k-correction contrast shows that this compensation direction is consequential in the present experiment:
  relatively low concentration errors coexist with markedly different gas-transfer coefficients and model-derived flux diagnostics.
  This does not constitute a formal structural-identifiability analysis, nor does it establish statistical equivalence between competing predictions.
  It supports the narrower conclusion that concentration-dominated evaluation does not uniquely constrain how discrepancy is allocated between S<sub>sgs</sub> and k in this model configuration.
  MLP/RF/Sparse-Π worse RMSEs are <strong>not</strong> used as equifinality evidence—they show closure choice matters and flexible residual learning did not generalize.</p>

  <h3>4.4 Filter-scale dependence belongs to the diagnosed residual, not a universal SGS law</h3>
  <p>Mean |S<sub>sgs</sub>| decreases from 1.92 at the native Δx≈838&nbsp;m scale to 1.00 at the study-reach scale,
  showing that the diagnosed closure residual depends on the spatial representation used to define resolved and unresolved contributions.
  This result should be interpreted for the implemented reach-local coarse-graining operator, which includes an ordering fallback and is not a fully directed network-topological filter.
  It therefore demonstrates scale dependence of the diagnosed residual within this experiment, not a universal scaling law for river-network CO<sub>2</sub> sources or a turbulence-style LES closure.</p>

  <h3>4.5 Sparse structure does not imply predictive sufficiency</h3>
  <p>The sparse dimensionless representation provides a useful counterpoint to the more flexible Residual-AI models.
  Its compact form identifies a limited set of candidate dependencies, but its reach-held-out C<sub>aq</sub> RMSE of 0.0506 remains above the Baseline value of 0.0284.
  Sparsity should therefore not be conflated with validated physical interpretability or transferable predictive skill.
  In this study, the Π-based formulation is most useful as a diagnostic simplification:
  it asks whether the residual can be summarized compactly while retaining cross-reach utility, and the present evaluation indicates that compactness alone is insufficient.</p>

  <h3>4.6 Implications for environmental-model evaluation</h3>
  <p>Taken together, the experiments favor an evaluation strategy in which predictive error and process-sensitive diagnostics are considered jointly.
  The present conclusions are bounded by partially observed upstream conditioning, strongly unequal reach support, coordinate-based fallback ordering in the spatial filter,
  idealized hydraulic geometry, incomplete biogeochemical covariates (Alk/N/P/PAR <strong>待补充</strong>; WQP 0/120; StreamPULSE 0 sites), and the absence of independent CO<sub>2</sub>-evasion measurements.
  These limitations constrain inference to the current East River experiment but also identify the observations and model structure most useful for discriminating alternative closures:
  improved upstream boundary information, better-resolved network and channel geometry, more balanced reach sampling, and independent constraints on gas exchange or evasion.
  The central methodological implication is not that one closure should replace another, but that a lower concentration error alone is insufficient to determine which unresolved-process allocation is better supported by the available evidence.
  Cross-sections remain idealized trapezoids, not ADCP. Relationship to Saccardi &amp; Winnick (2021) is a closure-evaluation experiment on their public East River setting, not a replacement full-process network model.</p>
</section>

<section id="conclusions">
  <h2>5. Conclusions</h2>
  <ol>
    <li>当前观测尺度上 Residual-AI 不能作为精度改进（MLP 0.0573 vs Baseline 0.0284）。</li>
    <li>仅有浓度观测时 S<sub>sgs</sub> 与 k 存在 practical equifinality（k 修正 C 略好、通量崩溃）。</li>
    <li>East River 实验演示可操作的诊断工作流（空间聚合 + 分组持出）；稀疏 Π 紧凑但未恢复 Baseline 泛化。</li>
  </ol>
  <p>不写 CONUS / CH₄ 已完成。不声称方法已在其他流域完成迁移验证。</p>
</section>

<section id="data">
  <h2>6. Data availability</h2>
  <p>East River 水化学 / pCO₂：HydroShare <code>9f907b46baa848e180c49339d605bf31</code>。
  DIC 补充包：HydroShare <code>2a2132999fb84214aad0596783812db2</code>。
  干流流量：USGS 09112500。NHDPlus HR：HUC 14020001。
  本仓库处理表与图见公开 GitHub 仓库的 results/tables 与 results/figures。
  StreamPULSE East River：检索无站点（resolved negative availability）。WQP 同日合并：检索失败 0/120。</p>
</section>

<section id="references">
  <h2>7. References</h2>
  <ol style="font-size:0.9rem;">
    <li>Saccardi B., Winnick M.J. Improving predictions of stream CO₂ concentrations and fluxes using a stream network model. <em>Global Biogeochemical Cycles</em>, 2021. https://doi.org/10.1029/2021GB006972</li>
    <li>Raymond P.A., et al. Scaling the gas transfer velocity and hydraulic geometry in streams and small rivers. <em>Limnology and Oceanography: Fluids and Environments</em>, 2012, 2, 41–53. https://doi.org/10.1215/21573689-1597669</li>
    <li>Yuval J., O’Gorman P.A. Stable machine-learning parameterization of subgrid processes for climate modeling. <em>Nature Communications</em>, 2020. https://doi.org/10.1038/s41467-020-17142-3</li>
    <li>Battin T.J., et al. River ecosystem metabolism and carbon biogeochemistry in a changing world. <em>Nature</em>, 2023. https://doi.org/10.1038/s41586-022-05500-8</li>
    <li>Gómez-Gener L., Rocher-Ros G., et al. Global carbon dioxide efflux from rivers enhanced by high nocturnal emissions. <em>Nature Geoscience</em>, 2021. https://doi.org/10.1038/s41561-021-00722-3</li>
    <li>Markovich K.H., White J.T., Knowling M.J. Sequential and batch data assimilation approaches to cope with groundwater model error. <em>Environmental Modelling &amp; Software</em>, 2022. https://doi.org/10.1016/j.envsoft.2022.105498</li>
    <li>Bennett N.D., et al. Characterising performance of environmental models. <em>Environmental Modelling &amp; Software</em>, 2013. https://doi.org/10.1016/j.envsoft.2012.09.011</li>
    <li>Vilas M.P., et al. TALKS: A systematic framework for resolving model-data discrepancies. <em>Environmental Modelling &amp; Software</em>, 2023. https://doi.org/10.1016/j.envsoft.2023.105668</li>
    <li>Hotchkiss E.R., et al. Sources of and processes controlling CO₂ emissions change with the size of streams and rivers. <em>Nature Geoscience</em>, 2015. https://doi.org/10.1038/ngeo2507</li>
    <li>Xie X., Samaei A., Guo J., Liu W.K., Gan Z. Data-driven discovery of dimensionless numbers and governing laws from scarce measurements. <em>Nature Communications</em>, 2022. https://doi.org/10.1038/s41467-022-35084-w</li>
    <li>Gao Y., et al. AI cross-fusion approach for river carbon transport. <em>The Innovation</em> (draft / 待补充 DOI).</li>
  </ol>
</section>

<div class="footer">
  paper.html · IMRaD methods paper · {n_figs} figures base64-embedded · no CDN · Residual-AI does not beat Baseline
  {f" · missing: {', '.join(missing)}" if missing else ""}
</div>
</div>
</body>
</html>"""

    OUT_HTML.write_text(html, encoding="utf-8")
    size_mb = OUT_HTML.stat().st_size / 1024 / 1024
    print(f"HTML: {OUT_HTML} ({size_mb:.2f} MB, {n_figs} figures)")
    if missing:
        print(f"  Missing: {missing}")

    md_lines = [
        "# Transport-coupled evaluation of river-network CO₂ closures",
        "",
        "**English title:** Transport-coupled evaluation of river-network CO₂ closures: Evidence for practical equifinality under concentration-only observations",
        "",
        "**Chinese title:** 河网 CO₂ 闭合的输运耦合评价：浓度单变量观测下的 practical equifinality 证据",
        "",
        "**Authors:** 待补充  ",
        "**Affiliation:** 待补充  ",
        "**Date:** 2026-08-17  ",
        f"**Figures in paper.html:** {n_figs}",
        "",
        "## Abstract (English)",
        "",
        "Environmental-model evaluation can favor a closure that reproduces concentration while distorting the underlying process partition.",
        "We develop a transport-coupled diagnostic framework for river-network CO₂ using public East River campaign data (HydroShare; n=120; 8 logical reaches).",
        "Leave-one-reach-out held-out C_aq RMSE: Baseline **0.0284**; Residual-AI MLP **0.0573**; RF **0.0745** — residual learners do **not** beat Baseline.",
        "k-correction reaches **0.0244** but coincides with k_eff/k_emp≈3.4e-4 and model flux diagnostic F_CO2 ~3.24→~0.03.",
        "Filter mean |S_sgs|: 1.92→1.00 (sampled cells=6). Sparse Π C RMSE≈0.051 still worse than Baseline.",
        "In-sample R²≈0.997 is appendix-only. Contribution = filter + protocol + practical equifinality evidence, not AI accuracy gains.",
        "",
        "## Highlights",
        "",
        "1. Reach-held-out Residual-AI does not outperform Baseline (0.0573/0.0745 vs 0.0284).",
        "2. Lower C RMSE from k-correction coincides with model-flux collapse (~3.24→~0.03).",
        "3. Spatial filtering exposes scale dependence and practical S_sgs–k equifinality.",
        "",
        "## Keywords",
        "",
        "River carbon cycling; environmental model evaluation; transport-coupled validation; spatial coarse-graining; subgrid residual; gas-transfer velocity; practical equifinality; grouped cross-validation",
        "",
        "## Paper vs report",
        "",
        "This manuscript uses academic EMS language only. Absolute local paths, virtual-environment setup notes, and pipeline script filenames as process narrative belong in the research report, not here.",
        "",
        "## IMRaD outline",
        "",
        "1. Introduction — evaluation gap; concentration vs process allocation; East River setting",
        "2. Methods — data; quasi-steady transport; filter-induced S_sgs; three closures; leave-one-reach-out CV; equifinality diagnostic; sparse Π",
        "3. Results — negative Residual-AI; concentration–flux disagreement; filter scale; sparse Π",
        "4. Discussion — failed generalization; practical equifinality; limitations",
        "5. Conclusions — three hard points",
        "6. Data availability",
        "7. References",
        "",
        "## Paper figures",
        "",
    ]
    for fname, caption, short in PAPER_FIGURES:
        if (FIG_DIR / fname).exists():
            plain = strip_tags(caption)
            md_lines.append(f"- `{fname}` — {plain}")
    md_lines += [
        "",
        "## Tables (see paper.html)",
        "",
        "- Table M / Table 4: leave-one-reach-out main metrics",
        "- Table 5: subgroup metrics",
        "- Table 6: filter scale",
        "- Tables 7–8: identifiability + sparse Π",
        "",
        "## DO NOT CLAIM",
        "",
        "- Residual-AI beats Baseline on held-out C_aq",
        "- in-sample R²=0.997 as skill",
        "- F_CO2 independently validated",
        "- universal SGS law / CONUS / CH4 / StreamPULSE / SINDy",
        "",
        "*Full self-contained HTML: paper.html*",
    ]
    OUT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"MD: {OUT_MD} ({OUT_MD.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
