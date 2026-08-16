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

from figure_explanations import get_teach  # noqa: E402
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
    parts: list[str] = []
    embedded: list[str] = []
    for fname, caption, _ in PAPER_FIGURES:
        data = b64_img(fname)
        if not data:
            continue
        embedded.append(fname)
        analysis = get_teach(fname, "")
        parts.append(
            f"""  <div class="figure-block">
    <img src="data:image/png;base64,{data}" alt="{fname}">
    <div class="fig-caption">{caption}</div>
    <div class="fig-analysis">{analysis}</div>
  </div>"""
        )
    return "\n".join(parts), embedded


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
    tables = paper_main_table_html() + nested_cv_tables_html() + innovation_tables_html()

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
  <h1>河网 CO₂ 输运的多尺度过滤与亚网格闭合可辨识性：East River 公开数据上的物理约束机器学习实验</h1>
  <div class="en-title">Transport-coupled evaluation of river-network CO₂ closures: Evidence for practical equifinality under concentration-only observations</div>
  <div class="authors">作者：待补充</div>
  <div class="affil">单位：待补充 · 通讯作者：待补充</div>
  <div class="affil" style="margin-top:0.6rem;">目标期刊：Environmental Modelling &amp; Software（方法/诊断）· 结构仿照 Markovich et al. (2022) EMS · 生成日期：2026-08-16 · 内嵌图 {n_figs} 幅</div>
</div>

<section id="abstract">
  <div class="abstract">
    <h2>摘要 / Abstract</h2>
    <p>Environmental-model evaluation can favor a closure that reproduces concentration while distorting the underlying process partition.
    We develop a transport-coupled diagnostic framework for river-network CO<sub>2</sub> that combines an operational spatial filter,
    reach-held-out cross-validation, and comparison of alternative unresolved-process closures using public East River campaign data
    (HydroShare; n=120; 8 logical reaches) mapped to NHDPlus HR. The filter defines a residual source/sink term S<sub>sgs</sub>
    without treating the problem as turbulence LES.</p>
    <p><strong>主结果（留一河段持出浓度）：</strong>held-out C<sub>aq</sub> RMSE 为 Baseline 0.0284；Residual-AI MLP 0.0573；
    RF 0.0745；因此学习型残差闭合<strong>没有</strong>优于 Baseline。k-correction 将 C<sub>aq</sub> RMSE 降至 0.0244，但
    <strong>coincided with</strong> k<sub>eff</sub>/k<sub>emp</sub>≈3.4×10<sup>−4</sup> 与模型通量诊断 F<sub>CO₂</sub>
    由约 3.24 降至约 0.03（共现诊断，非唯一因果证明）。滤波尺度上 mean |S<sub>sgs</sub>| 由 1.92（Δx≈838 m）降至 1.00（研究河段；有样点单元=6）。
    稀疏无量纲式 S*<sub>z</sub>≈1.059+1.536 Fr−1.669 Slope−2.179 h/W 在 reach-held-out 下 C RMSE≈0.051 仍差于 Baseline。
    样本内 R<sup>2</sup>≈0.997 仅附录。</p>
    <p><strong>贡献：</strong>方法论而非预测性——可操作的空间过滤定义、输运耦合验证协议，以及浓度单变量约束下
    S<sub>sgs</sub> 与 k 的 practical equifinality / closure compensation 证据。不是“AI 提高精度”。</p>
    <div class="kw"><strong>Highlights:</strong>
      (1) Reach-held-out Residual-AI closures do not outperform the process Baseline (0.0573/0.0745 vs 0.0284).
      (2) Lower C<sub>aq</sub> RMSE from k-correction coincides with model-flux collapse (~3.24→~0.03).
      (3) Spatial filtering exposes scale dependence and practical S<sub>sgs</sub>–k equifinality.
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
  <p>Environmental-model evaluation is not solely a problem of minimizing prediction error.
  A model can reproduce an observed state variable while assigning error compensation to an incorrect process, parameter, or boundary term.
  <em>Environmental Modelling &amp; Software</em> has a methodological tradition of treating model error and model–data discrepancy as objects of diagnosis
  (Bennett et al., 2013; Markovich et al., 2022; Vilas et al., 2023).
  This motivates a specific question for river-carbon modelling: when several unresolved-process representations can alter the same predicted CO<sub>2</sub> concentration,
  does improved concentration fit identify a better closure, or merely a different compensation pathway?</p>
  <p>River-network CO<sub>2</sub> models jointly control downstream concentration via transport, internal sources/sinks, and air–water exchange.
  Saccardi &amp; Winnick (2021) developed a process-based East River stream-network CO<sub>2</sub> model that establishes the direct modelling context.
  Gas exchange is commonly represented through an empirical transfer velocity k (e.g. Raymond et al., 2012).
  At the reach scale, spatial aggregation mixes unresolved heterogeneity with resolved transport and exchange, so a concentration mismatch can be assigned either to an additional source/sink correction or to a modification of k.
  Concentration observations alone need not reveal which allocation is process-consistent.</p>
  <p>We examine this ambiguity with an explicit spatial coarse-graining experiment for river-network CO<sub>2</sub> mass balance.
  The approach is LES-analog <em>only at the operator level</em>: spatial filtering separates resolved terms from a residual contribution; no turbulence-LES interpretation is assumed
  (cf. coarse-graining mindset in Yuval &amp; O’Gorman, 2020).
  Filtering defines a residual source/sink S<sub>sgs</sub> required to close the filtered balance after resolved terms are recomputed—
  a <em>filter-induced closure residual</em>, not a direct measurement of a unique unresolved biogeochemical process.
  Unpublished draft inspirations (Gao et al., <em>The Innovation</em>) are <strong>待补充 DOI</strong> only and do not bound novelty.</p>
  <p>The framework uses public East River campaign observations (n=120; 8 logical reaches; R008 n=58 vs R001/R006/R007 n=1 schematic) mapped to NHDPlus HR.
  Closures are evaluated <strong>after</strong> insertion into the same quasi-steady transport calculation (transport-coupled),
  using outer leave-one-reach-out evaluation with fold-specific preprocessing—not in-sample fit to a diagnosed residual.
  Where an upstream concentration is unavailable, the implementation falls back to the current sample’s observed C<sub>aq</sub> as c<sub>in</sub>
  (<code>src/03_baseline_transport.py</code>); this conditioning is disclosed here and in Methods and limits interpretation as perfectly target-isolated forecasting.</p>
  <p><strong>科学问题：</strong>(i) diagnosed |S<sub>sgs</sub>| how varies with filter scale Δx；
  (ii) under concentration-only evaluation, to what extent corrections to S<sub>sgs</sub> and k remain empirically distinguishable after transport coupling；
  (iii) can a sparse dimensionless Π representation generalize across held-out reaches better than flexible residual learners or Baseline?</p>
  <p><strong>贡献层次：</strong>(1) operable spatial-filter definition；(2) transport-coupled reach-held-out protocol；(3) empirical practical equifinality / closure compensation under concentration-only observations.
  We do not claim universal SGS behaviour, independent validation of CO<sub>2</sub> evasion flux, ADCP geometry, or superior ML predictive skill.</p>
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
  DIC/DOC 约 41/120；Alk/N/P/PAR 缺失<strong>待补充</strong>；WQP 同日合并 0/120；StreamPULSE 无 East River 站点（已排除）。
  真实数据唯一；无合成样点。因河段样本极不均衡，pooled 误差须与 reach-level 证据权重一并解读；n=1 河段仅作示意。逻辑河段 R001–R008 按研究设定的 STREAM_NETWORK_ORDER 赋予上下游关系（顺序链），用于准稳态闭合实验的可重复控制体组织，<strong>不是</strong>完整 NHDPlus 物理拓扑的替代描述。计算宽度 W 来自多样点河段的坐标展宽代理（并裁剪）或单点河段回退宽度，进入水深/流速/k<sub>600</sub>/A<sub>s</sub>=L·W；故几何假设影响输运与诊断，须与“仅示意横断面”区分披露（详见 <code>src/02_build_network.py</code>）。定性结论对宽度敏感时应优先报告敏感性，而非为保数字而隐瞒（本轮冻结主表，几何审计<strong>待补充</strong>敏感性表）。</p>
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
  对比用的观测代理通量用 empirical k 与观测 C（见 <code>src/12_nested_cv_transport.py</code>）。</p>
  <p><strong>k<sub>600</sub>→k<sub>CO₂</sub>：</strong>Raymond et al. (2012) ln(k<sub>600</sub>)=5.139+0.594 ln(u)+0.403 ln(slope)
  （u: m s<sup>−1</sup>，slope: m/m）得 k<sub>600</sub> (m d<sup>−1</sup>)；再经
  k<sub>emp</sub>=k<sub>600</sub>(Sc(T)/600)<sup>−0.5</sup>（<code>src/utils.py</code> <code>k_from_k600</code>；Sc 为 CO₂ Schmidt number）进入 Eq. (1)。
  符号上 k<sub>600</sub> ≠ k<sub>emp</sub>。C<sub>eq</sub> 取预处理表中的 C_eq_mol_m3（Henry / 大气 pCO₂ / 温度路径以代码与 HydroShare 衍生字段为准；细节<strong>待补充</strong>完整公式附录）。
  横断面可视化为理想化梯形；Stage 11 竖直流速剖面采用抛物线剖面（非 ADCP；亦非声称的实测 log-law）。主文指标不把示意剖面当作测量产品。</p>

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
  <p>主分析：leave-one-reach-out grouped CV（8 逻辑河段互斥分组）。
  每一 held-out 河段：仅在其余河段上拟合缺失值填补与特征缩放 → 预测闭合 → 代回准稳态输运 → 评分 held-out C<sub>aq</sub> 与模型 F<sub>CO₂</sub>。
  另做 grouped-by-date 作为时间敏感性分析（非嵌套在 reach split 内）。
  <strong>不称 nested CV</strong>，除非另行声明内层超参搜索环。
  当上游浓度状态缺失时，输运求解将 c<sub>in</sub> 回退为当前样点观测 C<sub>aq</sub>
  （<code>src/03_baseline_transport.py</code>）——解释为“部分边界条件下的闭合跨河段泛化”，而非完美目标隔离预报。</p>

  <h3>2.6 Metrics and flux diagnostic</h3>
  <p>主指标：held-out C<sub>aq</sub> RMSE (mol m<sup>−3</sup>)。
  ∑F<sub>CO₂</sub> 为 sample-summed areal flux diagnostic（与 C RMSE 同级报告）。
  不做独立箱式/涡动通量验证。因无独立逃逸观测，通量诊断用于暴露模型过程分配变化，而非判定哪一种分配物理正确。</p>

  <h3>2.7 Practical equifinality diagnostic</h3>
  <p><strong>Eq. (6)</strong> S<sub>implied</sub>=(k<sub>emp</sub>−k<sub>eff</sub>)(C−C<sub>eq</sub>)：
  在固定 C 与 resolved transport 状态下，使保留 k<sub>emp</sub> 的模型与使用 k<sub>eff</sub>、无额外源汇的模型局部等价所需的源汇调整。
  语言：practical equifinality / compensating closure behaviour；<strong>不是</strong> formal structural non-identifiability 证明。</p>

  <h3>2.8 Sparse dimensionless closure</h3>
  <p>标准化 LASSO（PySINDy 未安装则用稀疏式中间件；思想参考 Xie et al. 2022）。
  展示式 S*<sub>z</sub>≈1.059+1.536 Fr−1.669 Slope−2.179 h/W 为 standardized-space 系数形式（下标 z 提示 z-score 空间；
  Fr、Slope、h/W 定义与 fold-training 标准化路径见 <code>src/15_dimensionless_sparse.py</code>）。
  Reach-held-out C RMSE≈0.0506（正文可写 ≈0.051），仍差于 Baseline 0.0284——贡献为紧凑诊断表示，非预测胜出。</p>

  <div class="note"><strong>Evaluation independence (Round-1/3 audit)：</strong>
  外层 leave-one-reach-out + fold-specific imputation/scaling；优先称 reach-held-out / grouped CV。
  c<sub>in</sub> 观测回退与 Y→X 过滤排序为已披露边界；本修订冻结 Δx / RMSE 数字不重跑。</div>
</section>

<section id="results">
  <h2>3. Results</h2>
  <p class="lead"><strong>结果顺序（Round-4 接受）：</strong>
  (3.1) Residual closures do not generalize better than Baseline —
  held-out C<sub>aq</sub> RMSE (mol m<sup>−3</sup>) Baseline 0.0284；Residual-AI MLP 0.0573；RF 0.0745
  （Residual-AI <em>does not</em> beat Baseline；限定 leave-one-reach-out + 部分边界条件）。
  (3.2) Concentration vs model-flux diagnostics rank closures differently —
  k-correction 降至 0.0244，但 <strong>coincided with</strong> median k<sub>eff</sub>/k<sub>emp</sub>≈3.35×10<sup>−4</sup>
  与 sample-summed ΣF<sub>CO₂</sub> ~3.24→~0.031（模型通量诊断塌缩，非独立通量“预测失败”）。
  (3.3) Practical S<sub>sgs</sub>–k compensation（Eq. 6 + Baseline–k 对比）。
  (3.4) Diagnosed |S<sub>sgs</sub>| depends on filter scale（1.92→1.00）。
  (3.5) Sparse Π compact but predictively insufficient（0.0506&gt;0.0284）。
  源表：<code>paper_main_results.csv</code> / <code>nested_cv_metrics.csv</code> /
  <code>paper_filter_scale.csv</code> / <code>subgroup_metrics.csv</code>。</p>
{tables}
  <h3>3.1–3.5 图件与讲解</h3>
  <p>下列图按论文计划编号。每图附教学式五段说明（背景、读法、子图、曲线含义、通俗结论）。</p>
{figs_html}
</section>

<section id="discussion">
  <h2>4. Discussion</h2>
  <h3>4.1 Failed residual generalization is a modelling result</h3>
  <p>Under leave-one-reach-out grouped evaluation with partially observed boundary conditioning,
  MLP and RF residual closures did not outperform the Baseline on held-out C<sub>aq</sub>
  (0.0573 and 0.0745 versus 0.0284). This is a modelling diagnosis of non-transfer of a residual learned from diagnosed unresolved terms after transport coupling—not a claim that “ML always fails.”
  Plausible contributors include imbalanced reach support, distribution shift, partial boundary conditioning, omitted covariates, and imperfect S<sub>sgs</sub> definition; we do not elevate one as proven cause.</p>

  <h3>4.2 Concentration skill and process allocation disagree</h3>
  <p>The k-correction attained a lower concentration RMSE (0.0244) that did <strong>not</strong> constitute evidence of improved process fidelity,
  because it coincided with median k<sub>eff</sub>/k<sub>emp</sub>≈3.35×10<sup>−4</sup> and ΣF<sub>CO₂</sub>=0.031 versus Baseline ≈3.24.
  We report a severe collapse/divergence of the <em>model-derived</em> flux diagnostic relative to Baseline—not an independently observed flux-prediction failure
  (F<sub>CO₂</sub> has no chamber/eddy validation here).</p>

  <h3>4.3 Practical closure equifinality (restricted sense)</h3>
  <p>Following Beven-style environmental-modelling vocabulary of alternative acceptable representations, we use <em>practical equifinality</em> in a restricted sense
  (not Beven’s full thesis; not Raue/Villaverde formal structural identifiability).
  Eq. (6) identifies an algebraic compensation direction between an additional source/sink and gas exchange at fixed C and resolved transport.
  Empirically, Baseline and k-correction attained similarly low concentration errors while implying markedly different process partitions.
  Results are consistent with a practical closure-compensation mode under concentration-dominated evaluation: allocation of discrepancy between S<sub>sgs</sub> and k is not uniquely constrained in this experiment.
  MLP/RF/Sparse-Π worse RMSEs are <strong>not</strong> used as equifinality evidence—they show closure choice matters and flexible residual learning did not generalize.
  The Baseline–k contrast is the cleanest equifinality evidence.</p>

  <h3>4.4 Filtering and sparse closure diagnose but do not solve prediction</h3>
  <p>Filter-scale dependence of mean |S<sub>sgs</sub>| (1.92→1.00) establishes operator dependence of the diagnosed residual within the implemented coarse-graining experiment.
  The sparse dimensionless form remains compact but did not recover Baseline generalization (0.0506&gt;0.0284); coefficients are descriptive of this experiment, not a transferable universal law.</p>

  <h3>4.5 Implications and information needed to discriminate closures</h3>
  <p>Independent gas-evasion constraints, better upstream boundary states, more balanced reach sampling, topology-aware filtering, measured cross-sections, and missing biogeochemical drivers
  (Alk/N/P/PAR；StreamPULSE/WQP gaps) would reduce closure ambiguity—stated as observational requirements, not promises of lower RMSE.
  Relationship to Saccardi &amp; Winnick (2021) is a closure-identifiability experiment on their public East River setting, not a replacement full-process network model.
  Journal target: EMS (Markovich et al. 2022 structure; Bennett 2013 multi-metric evaluation; Vilas 2023 discrepancy-as-diagnosis).</p>

  <h3>4.6 Limitations</h3>
  <p>Several limitations bound interpretation. First, leave-one-reach-out is not fully target-blind because unavailable upstream states fall back to the current sample’s observed C<sub>aq</sub> as c<sub>in</sub>.
  Second, spatial ordering falls back to midpoint Y→X and is not a fully directed network-topological filter.
  Third, reach support is strongly imbalanced (R001–R008: n=1,3,15,24,17,1,1,58), so eight folds are not equally informative replicates.
  Fourth, F<sub>CO₂</sub> is a transport-model-derived, sample-summed flux diagnostic without independent evasion validation.
  Fifth, cross-sections are idealized trapezoids, not ADCP.
  Finally, Alk/N/P/PAR gaps and StreamPULSE/WQP non-coverage remain <strong>待补充</strong>.
  Inference is restricted to the present East River dataset, filtering implementation, predictors, and concentration-dominated evaluation—no universal SGS law and no independently validated flux partition.</p>
</section>

<section id="conclusions">
  <h2>5. Conclusions</h2>
  <ol>
    <li>当前观测尺度上 Residual-AI 不能作为精度改进（MLP 0.0573 vs Baseline 0.0284）。</li>
    <li>仅有浓度观测时 S<sub>sgs</sub> 与 k 存在 practical equifinality（k 修正 C 略好、通量崩溃）。</li>
    <li>East River 实验演示可操作的诊断工作流（空间聚合 + 分组持出）；稀疏 Π 紧凑但未恢复 Baseline 泛化</li>
  </ol>
  <p>不写 CONUS / CH₄ 已完成。</p>
</section>

<section id="data">
  <h2>6. Data availability</h2>
  <p>East River 水化学 / pCO₂：HydroShare <code>9f907b46baa848e180c49339d605bf31</code>。
  DIC 补充包：HydroShare <code>2a2132999fb84214aad0596783812db2</code>。
  干流流量：USGS 09112500。NHDPlus HR：HUC 14020001。
  本仓库处理表与图：<code>results/tables/</code>、<code>results/figures/</code>。
  StreamPULSE East River：无站点（待补充）。WQP 同日合并：0/120。</p>
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
        "# 河网 CO₂ 输运的多尺度过滤与亚网格闭合可辨识性",
        "",
        "**English title:** Transport-coupled evaluation of river-network CO₂ closures: Evidence for practical equifinality under concentration-only observations",
        "",
        "**Authors:** 待补充  ",
        "**Affiliation:** 待补充  ",
        "**Date:** 2026-08-16  ",
        f"**Figures in paper.html:** {n_figs}",
        "",
        "## Abstract",
        "",
        "环境模型可能通过过程补偿得到相近浓度误差。本文构建河网 CO₂ 空间过滤与输运耦合评价框架（East River，n=120；reach-held-out）。",
        "主结果：Residual-AI **没有**优于 Baseline（MLP 0.0573 / RF 0.0745 vs Baseline 0.0284）。",
        "k 修正略降到 0.0244，并伴随 k_eff/k_emp≈3.4e-4 与 F_CO2 ~3.24→~0.03（共现诊断）。",
        "滤波 mean |S_sgs|：1.92→1.00（研究河段有样点单元=6）。稀疏 Π 式可解释，嵌套 CV C RMSE≈0.051 仍差于 Baseline。",
        "贡献是可操作过滤定义、输运耦合协议与 practical equifinality 诊断，不是精度提升。样本内 R²≈0.997 仅附录。",
        "",
        "## Keywords",
        "",
        "河网 CO₂ 输运；亚网格闭合；可辨识性；LES 过滤；reach-held-out 分组交叉验证；物理约束机器学习；East River",
        "",
        "## IMRaD outline",
        "",
        "1. Introduction — 科学问题与负结果框架",
        "2. Methods — 数据、过滤、三种闭合、嵌套 CV、可辨识性、稀疏 Π",
        "3. Results — 先负精度，再滤波 / 稀疏式 / k–S 权衡（见表与图）",
        "4. Discussion — 浓度不足以评价闭合；需要独立通量",
        "5. Conclusions — 三条硬结论",
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
        "## Tables (see paper.html for full HTML tables)",
        "",
        "- Table M / Table 4: nested CV main metrics (`paper_main_results.csv`, `nested_cv_metrics.csv`)",
        "- Table 5: subgroup metrics (`subgroup_metrics.csv`)",
        "- Table 6: filter scale (`paper_filter_scale.csv`)",
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
