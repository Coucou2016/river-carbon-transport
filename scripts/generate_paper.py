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
        "<strong>Fig. 3</strong> 嵌套交叉验证：Baseline / Residual-AI / k 修正的持出 C<sub>aq</sub> RMSE（主图）。",
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
  <div class="en-title">Multiscale filtering and identifiability of subgrid closures for river-network CO₂ transport: a physics-constrained machine-learning experiment on public East River data</div>
  <div class="authors">作者：待补充</div>
  <div class="affil">单位：待补充 · 通讯作者：待补充</div>
  <div class="affil" style="margin-top:0.6rem;">目标期刊：Environmental Modelling &amp; Software（方法/诊断）· 结构仿照 Markovich et al. (2022) EMS · 生成日期：2026-08-16 · 内嵌图 {n_figs} 幅</div>
</div>

<section id="abstract">
  <div class="abstract">
    <h2>摘要 / Abstract</h2>
    <p>河网碳模型在河段尺度平均掉湍流混合、地下水 CO₂ 与局地代谢等过程，需要亚网格源汇闭合。
    本文将大涡模拟（LES）式空间过滤显式写成河网 CO₂ 输运的亚网格源汇项 S<sub>sgs</sub>，
    在公开 East River 战役数据（HydroShare；n=120；8 逻辑河段）与 NHDPlus HR 河网上开展多滤波尺度实验，
    并用留一河段嵌套交叉验证比较三种闭合：Baseline（S<sub>sgs</sub>=0）、Residual-AI、k 修正。</p>
    <p><strong>主结果（负精度结果优先）：</strong>持出 C<sub>aq</sub> RMSE 为 Baseline 0.0284、Residual-AI MLP 0.0573、
    RF 0.0745；k 修正略降至 0.0244，并<strong>伴随</strong> k<sub>eff</sub>/k<sub>emp</sub>≈3.4×10<sup>−4</sup> 与模型通量诊断 F<sub>CO₂</sub>
    从约 3.24 塌缩到约 0.03（共现诊断，非已证明的唯一因果）。滤波尺度上 mean |S<sub>sgs</sub>| 从 1.92（Δx≈838 m）降至 1.00（研究河段≈26 km；有样点单元=6）。
    无量纲稀疏式 S*<sub>z</sub>≈1.059+1.536 Fr−1.669 Slope−2.179 h/W 可解释，但嵌套 CV C RMSE≈0.051 仍差于 Baseline。
    样本内 R²≈0.997 仅附录。</p>
    <p><strong>贡献：</strong>不是“AI 提高精度”，而是可计算的过滤定义、浓度观测下 S<sub>sgs</sub> 与 k 的 practical equifinality、
    以及分层嵌套交叉验证协议。机器学习闭合未能改善持出浓度——这一负结果界定了当前数据所能支持的方法边界。</p>
    <div class="kw"><strong>关键词：</strong>河网 CO₂ 输运；亚网格闭合；可辨识性；LES 过滤；嵌套交叉验证；物理约束机器学习；East River</div>
    <div class="kw"><strong>Keywords:</strong> river-network CO₂ transport; subgrid closure; identifiability; LES filtering; nested CV; physics-constrained ML; East River</div>
  </div>
</section>

<section id="glossary">
  <h2>术语表</h2>
  {glossary_html()}
</section>

<section id="intro">
  <h2>1. Introduction</h2>
  <p>河网是陆地–大气碳交换的活跃界面。现有流域模型在河段尺度平均掉湍流混合、地下水 CO₂、局地代谢，
  需要亚网格源汇。Gao 等提出 LES 类比 + AI 闭合；本文将它写成可计算的过滤算子，而不是精度宣言。</p>
  <p>East River 是理想的公开试验床：Saccardi &amp; Winnick (2021) 提供战役 pCO₂ 与河网几何；
  Raymond et al. (2012) 提供 k<sub>600</sub>；Yuval &amp; O’Gorman (2020) 代表物理约束 ML 残差学习先例。</p>
  <p><strong>科学问题：</strong>（i）S<sub>sgs</sub> 是否随 Δx 系统变化？（ii）S<sub>sgs</sub> 与 k 在浓度观测下能否辨识？
  （iii）无量纲稀疏式能否在嵌套 CV 下推广？</p>
  <div class="note"><strong>DO NOT CLAIM：</strong>本文不声称 Residual-AI 优于 Baseline；不把样本内 R²=0.997 当主结论；
  不把 F<sub>CO₂</sub> 当作腔室验证通量；不声称普适 SGS 定律或 CONUS 推广。</div>
</section>

<section id="methods">
  <h2>2. Methods</h2>
  <p class="lead"><em>English methods box (EMS-facing).</em>
  Task: diagnose whether residual or k-correction closures generalize under concentration-only observations.
  Protocol: define an LES-analog spatial filter → close the quasi-steady mass balance three ways → evaluate with
  <strong>transport-coupled nested leave-one-reach-out CV</strong> (predict closure on held-out reaches, then re-solve physics).
  Primary metric: held-out C<sub>aq</sub> RMSE. Secondary diagnostics: model F<sub>CO₂</sub> totals and
  S<sub>implied</sub>=(k<sub>emp</sub>−k<sub>eff</sub>)(C−C<sub>eq</sub>). Failure modes are reported, not discarded.</p>
  <h3>2.1 研究区与数据 / Study area and data</h3>
  <p>HUC 14020001；120 样点（2019-08-02–11）；8 逻辑河段（R001=1, R002=3, R003=15, R004=24, R005=17, R006=1, R007=1, R008=58）；
  NHD 393 / NHDPlus HR 8212 flowlines；USGS 09112500；GNIS 匹配 85；捕捉中位距离约 8.5 m。
  DIC/DOC 仅 41/120；Alk/N/P/PAR 缺失<strong>不插补</strong>；WQP 同日合并 0/120；StreamPULSE 无 East River 站点（待补充）。
  真实数据唯一；不合成样点。</p>
  {REACH_NETWORK_TABLE_HTML}
  <h3>2.2 过滤算子 / Spatial filter</h3>
  <p><strong>Motivation:</strong> 河段尺度输运方程隐式平均了未分辨混合与局地源汇，需要可计算的 Δx 定义而非口头“亚网格”。
  <strong>Mechanism:</strong> 将 NHDPlus HR 廊道线段按沿程链距在同一 reach_id 内每 N 段合并；Δx=有样点粗化单元平均长度；
  样点捕捉到粗化线后，按准稳态质量守恒重算 S<sub>sgs</sub>（单位 mol m<sup>−2</sup> d<sup>−1</sup>）。
  <strong>Role:</strong> 提供多尺度实验轴与 Fig.&nbsp;6 的 |S<sub>sgs</sub>|(Δx) 诊断。
  “LES-analog”仅指空间粗粒化引起的 resolved / unresolved 分离；<strong>不</strong>暗示 Navier–Stokes 湍流闭合。
  S<sub>sgs</sub> 解释为 <em>filter-induced subgrid source/sink residual</em>（可吸收测量误差、简化输运误差与遗漏过程），不是某一真实未解析生物地球化学通量的直接观测。</p>
  <h3>2.3 基准输运与三种闭合 / Closures</h3>
  <p>代码实现（与 <code>src/03_baseline_transport.py</code> 一致）采用水面面积 A<sub>s</sub>=L×W（m²；非横截面积）与 areal 通量：
  Q(C<sub>in</sub>−C) + (A<sub>s</sub>/86400)[S<sub>sgs</sub> − k(C−C<sub>eq</sub>)] = 0（Q: m³ s<sup>−1</sup>；C: mol m<sup>−3</sup>；k: m d<sup>−1</sup>；S<sub>sgs</sub>: mol m<sup>−2</sup> d<sup>−1</sup>）。
  文中简写 (Q/A)(C<sub>in</sub>−C)+S<sub>sgs</sub>−k(C−C<sub>eq</sub>)=0 时，A≡A<sub>s</sub> 且速率已换算到一致日尺度。
  (A) Baseline S=0，Raymond k；(B) Residual-AI 学习 S<sub>sgs</sub>（MLP / RF）；
  (C) k-correction k<sub>eff</sub>=k<sub>emp</sub> exp(g<sub>θ</sub>(X))（XGBoost）。
  Baseline 是公平对照，不是“弱模型稻草人”。比较目的是闭合形式在耦合输运后的行为，不是离线挑“最准算法”。</p>
  <h3>2.4 嵌套 CV、可辨识性与稀疏 Π / Evaluation</h3>
  <p>留一河段 / 留一日期：<strong>先预测闭合，再代入物理</strong>（transport-coupled）；分层报告（R008 主证据；单样本河段示意）。
  防泄漏协议：（i）outer fold = 8 逻辑河段留一；（ii）scaling / 特征与超参选择仅在 outer-training 内；
  （iii）held-out C<sub>aq</sub> 不得进入预测阶段的 X / 归一化 / closure 输入；（iv）主评价对象是耦合后 C<sub>aq</sub>，不是 closure 目标的离线拟合。
  可辨识性诊断（非结构可辨识性定理）：S<sub>implied</sub>=(k<sub>emp</sub>−k<sub>eff</sub>)(C−C<sub>eq</sub>)，表述为 compensating closure behaviour / practical equifinality。
  无量纲稀疏：仅 Π 特征；标准化 LASSO（PySINDy 未安装；稀疏式灵感见 Xie et al. 2022）。
  证伪检验：H1 held-out reach generalization of learned closures；H2 可补偿性；H3 过程一致性（通量是否与 C 改善共现塌缩）。
  表中 k<sub>eff</sub>/k<sub>emp</sub> 为 nested-CV <strong>median</strong>；F total 为持出样本模型逸散通量合计（mol m<sup>−2</sup> d<sup>−1</sup> 量级的样本加总诊断，非腔室验证）。</p>
  <div class="note">断面为理想化梯形 + 抛物线 u(z)，非 ADCP。F<sub>CO₂</sub> 为模型通量诊断/代理，非腔室验证。</div>
</section>

<section id="results">
  <h2>3. Results</h2>
  <p class="lead"><strong>结果顺序已冻结：先报告负精度（H1 失败）。</strong>
  Held-out C<sub>aq</sub> RMSE：Baseline 0.0284；Residual-AI MLP 0.0573；RF 0.0745
  （Residual-AI <em>does not</em> beat Baseline）。k-correction 略降至 0.0244，并<strong>coincided with</strong> F<sub>CO₂</sub> ~3.24→~0.03
  （H2 表面通过、H3 失败 → practical equifinality；共现而非已证唯一因果）。随后报告滤波尺度、稀疏 Π、可辨识性图。
  主表：<code>paper_main_results.csv</code> / <code>nested_cv_metrics.csv</code> /
  <code>paper_filter_scale.csv</code> / <code>subgroup_metrics.csv</code>。</p>
{tables}
  <h3>3.1–3.5 图件与讲解</h3>
  <p>下列图按论文计划编号。每图附教学式五段说明（背景、读法、子图、曲线含义、通俗结论）。</p>
{figs_html}
</section>

<section id="discussion">
  <h2>4. Discussion</h2>
  <p><strong>评价协议写成三条证伪检验：</strong>
  H1 held-out reach generalization——Residual-AI 是否优于 Baseline？（否：0.0573 vs 0.0284；限定于本数据与 leave-one-reach-out 协议）；
  H2 可补偿性——调整 k 能否压低浓度误差？（表面上是：0.0244）；
  H3 过程一致性——该改善是否与可信逸散通量并存？（否：F<sub>CO₂</sub> 约 3.24→0.03，与 C 改善共现）。
  负的嵌套 CV 结果因此是方法贡献，不是算法失败脚注。措辞上避免把共现写成已证明的唯一因果；亦不声称 formal structural non-identifiability。</p>
  <p>浓度精度不足以评价河网 CO₂ 闭合：持出 C 与模型通量诊断可背离。
  ML 不能推广的原因包括 n=120、R008 占 48%、单样本河段、无独立通量、Π 特征在河段内近乎常值。</p>
  <p>LES 类比仍贡献 Δx 定义、残差随尺度诊断、浓度等价参数化下的 practical equifinality。
  与 Saccardi &amp; Winnick (2021) 的关系是公开数据上的闭合可辨识性实验，不是重复其全部过程模块。</p>
  <p>要区分浓度等价参数化，下一步是独立 k 或通量观测，而不是加深网络。
  投稿定位见 <code>docs/PAPER_FRAMEWORK.md</code>（EMS；结构仿 Markovich et al. 2022）。</p>
</section>

<section id="conclusions">
  <h2>5. Conclusions</h2>
  <ol>
    <li>当前观测尺度上 Residual-AI 不能作为精度改进（MLP 0.0573 vs Baseline 0.0284）。</li>
    <li>仅有浓度观测时 S<sub>sgs</sub> 与 k 存在 practical equifinality（k 修正 C 略好、通量崩溃）。</li>
    <li>多尺度过滤 + 分层嵌套 CV 是可迁移的方法学；稀疏 Π 式形式可解释、持出弱。</li>
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
    <li>Raymond P.A., et al. Scaling the gas transfer velocity and hydraulic geometry in streams and small rivers. <em>Limnology and Oceanography: Fluids and Environments</em>, 2012. https://doi.org/10.1215/21573689-1597669</li>
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
        "**English title:** Multiscale filtering and identifiability of subgrid closures for river-network CO₂ transport: a physics-constrained machine-learning experiment on public East River data",
        "",
        "**Authors:** 待补充  ",
        "**Affiliation:** 待补充  ",
        "**Date:** 2026-08-16  ",
        f"**Figures in paper.html:** {n_figs}",
        "",
        "## Abstract",
        "",
        "本文将 LES 式空间过滤写成河网 CO₂ 输运的亚网格源汇 S_sgs，在公开 East River 数据（n=120）上做多 Δx 实验与嵌套交叉验证。",
        "主结果：Residual-AI **没有**优于 Baseline（MLP C RMSE 0.0573 vs 0.0284；RF 0.0745）。",
        "k 修正略降到 0.0244，并伴随 k_eff/k_emp≈3.4e-4 与 F_CO2 ~3.24→~0.03（共现诊断）。",
        "滤波 mean |S_sgs|：1.92→1.00（研究河段有样点单元=6）。稀疏 Π 式可解释，嵌套 CV C RMSE≈0.051 仍差于 Baseline。",
        "贡献是过滤定义、practical equifinality 与验证协议，不是精度提升。样本内 R²≈0.997 仅附录。",
        "",
        "## Keywords",
        "",
        "河网 CO₂ 输运；亚网格闭合；可辨识性；LES 过滤；嵌套交叉验证；物理约束机器学习；East River",
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
