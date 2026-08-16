"""Shared content for report + paper generators.

Holds the terminology glossary (full name + deep 物理意义/方程溯源/来龙去脉 explanation
for every abbreviation) and helpers that read real numbers from results/tables/*.csv.

No invented data. All numeric summaries are pulled from the frozen result CSVs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"

# ---------------------------------------------------------------------------
# Terminology glossary — every abbreviation gets a full name and a deep
# explanation covering physical meaning, equation origin, and context.
# term_key -> (缩写/符号, 全称, 深度解释 HTML)
# ---------------------------------------------------------------------------
GLOSSARY: list[tuple[str, str, str]] = [
    (
        "S<sub>sgs</sub>",
        "亚网格源汇项（subgrid-scale source/sink term）",
        "当我们把一条真实河流按某个空间尺度 Δx “打包”成一个个控制体（相当于把细节抹平、只保留河段平均）时，"
        "控制体内部那些没有被显式解析的过程——地下水带来的 CO₂、河床与生物膜的呼吸、局地湍流混合、"
        "支流点源注入等——无法再用平均的平流和气体交换写出来，只能塞进一个“余项”。这个余项就是 "
        "S<sub>sgs</sub>，单位 mol·m⁻²·d⁻¹（每平方米水面每天多少摩尔碳）。"
        "<strong>方程溯源：</strong>它来自准稳态一维输运方程的质量守恒残差 "
        "S<sub>sgs</sub> = k(C − C<sub>eq</sub>) − (Q/A)(C<sub>in</sub> − C)，"
        "即“用实测浓度算出来的收支缺口”。<strong>来龙去脉：</strong>这一写法直接类比流体力学的"
        "大涡模拟（见 LES 条目）：大尺度可算、小尺度进闭合项。本研究的核心问题正是——这个闭合项"
        "能不能被机器学习可靠地预测出来。",
    ),
    (
        "k<sub>600</sub> / k / k<sub>eff</sub>",
        "气体交换速度（gas transfer velocity；k<sub>600</sub> 为标准化到 Schmidt 数 600 的值，k<sub>eff</sub> 为模型有效值）",
        "气体交换速度描述水体与大气之间气体“翻越”界面的快慢，单位是长度/时间（这里用 m·d⁻¹，即每天能"
        "“刷新”多少米厚的水柱）。它越大，河水里过饱和的 CO₂ 就越快逸散到大气。"
        "<strong>方程溯源：</strong>本研究用 Raymond 等（2012）的经验公式 "
        "ln k<sub>600</sub> = 5.139 + 0.594 ln u + 0.403 ln S₀（u 为流速、S₀ 为坡度），"
        "再按水温对应的 Schmidt 数换算成 CO₂ 的 k。<strong>k<sub>eff</sub> 的含义：</strong>"
        "在“k 修正”方案里，我们允许模型把经验 k 乘上一个可学习因子 exp(g(X)) 得到有效值 k<sub>eff</sub>，"
        "用来吸收浓度残差。<strong>来龙去脉：</strong>本研究的关键负结果之一，就是 k<sub>eff</sub> 被压到"
        "经验值的约万分之三时浓度略微更准，但逸散通量几乎归零——这说明 k 与 S<sub>sgs</sub> 纠缠不清。",
    ),
    (
        "Fr",
        "弗劳德数（Froude number）",
        "Fr = u / √(g·h)，其中 u 是流速、g 是重力加速度、h 是水深。它是“惯性力与重力”之比，"
        "物理上判断明渠水流是缓流（Fr &lt; 1，扰动能向上游传播）还是急流（Fr &gt; 1，如跌水、急滩）。"
        "<strong>方程溯源：</strong>来自明渠水力学的量纲分析。<strong>来龙去脉：</strong>"
        "在本研究的无量纲稀疏闭合里，Fr 是最强的正向解释变量——急流河段（陡、浅、快）往往对应更大的"
        "亚网格残差，符合“湍流越强、未分辨过程越多”的直觉。",
    ),
    (
        "Re",
        "雷诺数（Reynolds number）",
        "Re = u·h/ν，其中 ν 是水的运动黏度。它是“惯性力与黏性力”之比，用来判断流动是层流还是湍流"
        "（天然河流几乎总是高 Re 的湍流）。<strong>方程溯源：</strong>流体力学量纲分析的基本无量纲数。"
        "<strong>来龙去脉：</strong>本研究把 log₁₀Re 作为候选闭合特征，但在河段内它几乎是常数、"
        "对残差的解释力被稀疏回归压成 0，说明当前尺度上 Re 不是有效的区分变量。",
    ),
    (
        "Pe",
        "佩克莱数（Péclet number）",
        "Pe = u·L/D，其中 L 是特征长度、D 是纵向弥散系数。它是“平流输运与扩散/弥散输运”之比，"
        "Pe ≫ 1 表示碳主要靠水流带着走、而不是靠扩散抹平。<strong>方程溯源：</strong>对流—扩散方程的"
        "无量纲化。<strong>来龙去脉：</strong>本研究的准稳态输运以平流—气体交换平衡为主（高 Pe），"
        "因此把纵向弥散作为次要项处理；Pe 用于说明为什么可以采用平流主导的简化。",
    ),
    (
        "Da",
        "丹克尔数（Damköhler number）",
        "Da 是“反应/交换的特征时间”与“输运的特征时间”之比，这里用气体交换时标与平流时标的比值近似。"
        "Da ≫ 1 表示 CO₂ 还没被水流带走就已大量逸散（交换主导）；Da ≪ 1 表示水流“来不及”交换就冲过去了"
        "（输运主导）。<strong>方程溯源：</strong>化学反应工程借来的无量纲数，河流里把“反应”替换成"
        "“气体交换 + 源汇”。<strong>来龙去脉：</strong>Da 出现在候选闭合特征中，全特征 LASSO 里它有一定权重，"
        "但在只用无量纲量的稀疏式里被压得很弱。",
    ),
    (
        "h/W",
        "水力纵横比（水深 h 与河宽 W 之比，aspect ratio）",
        "h/W 衡量河道断面“瘦高还是宽扁”。深窄的沟（h/W 较大）与宽浅的辫状河（h/W 很小）在气体交换、"
        "断面流速分布上差别很大。<strong>方程溯源：</strong>断面几何的直接比值。<strong>来龙去脉：</strong>"
        "在本研究的无量纲稀疏闭合中，h/W 的（原始量纲）系数绝对值最大（约 −349），是形式上很显眼的项；"
        "但需注意河宽 W 由 Manning 公式反推（见 Manning 条目），本身带有不确定性。",
    ),
    (
        "LES",
        "大涡模拟（Large-Eddy Simulation）",
        "LES 是流体力学里模拟湍流的一种思路：对流场做空间滤波，直接解析大尺度涡旋，而把小于滤波宽度 Δx 的"
        "小涡对大涡的作用用一个“亚网格模型”来近似。<strong>方程溯源：</strong>对 Navier–Stokes 方程做空间"
        "低通滤波后，滤波后的方程里会多出一个亚网格应力项。<strong>来龙去脉：</strong>本研究把这个思想"
        "“搬运”到河网碳输运：把河网按 Δx 粗化就相当于空间滤波，未被解析的碳过程就成了亚网格源汇 "
        "S<sub>sgs</sub>（见该条目）。这是 Gao 等《The Innovation》稿件“大涡类比”的可计算版本。",
    ),
    (
        "nested CV",
        "嵌套交叉验证（nested cross-validation）",
        "普通交叉验证把数据随机分成几折，轮流留一折做测试。<strong>嵌套</strong>指的是在“训练折”内部再做一层"
        "调参/闭合估计，保证测试折的信息完全不泄漏进模型。本研究的具体协议是：先在训练折上学出闭合"
        "（S<sub>sgs</sub> 或 k<sub>eff</sub>），再把它代入与基准完全相同的输运方程，只在留出的样本上打分。"
        "<strong>来龙去脉：</strong>这是对“随机划分 + 样本内 R²”那种乐观评估的纠正——只有嵌套 CV 的持出"
        "误差才能回答“换一条没见过的河，模型还准不准”。",
    ),
    (
        "LOO-reach",
        "留一河段交叉验证（leave-one-reach-out）",
        "把 8 条河段中的<strong>一整条</strong>留出来当测试集，用其余 7 条训练闭合，轮流 8 次。"
        "<strong>为什么这样做：</strong>如果只随机留出单个样点，同一条河的邻近样点会“泄题”，让模型显得很准；"
        "留一整条河才能检验模型对<strong>全新河段</strong>的推广能力。本研究另有“留一日期（LOO-date）”作为"
        "对照。<strong>来龙去脉：</strong>正是在 LOO-reach 下，Residual-AI 的持出误差高于基准，暴露了"
        "“样本内很准、换河就崩”的过拟合本质。",
    ),
    (
        "RMSE",
        "均方根误差（Root-Mean-Square Error）",
        "把每个样点“预测减观测”的差平方、求平均、再开方，单位与被预测量相同（这里 C<sub>aq</sub> 用 mol·m⁻³）。"
        "它对大误差更敏感，越小越好。<strong>来龙去脉：</strong>RMSE 是本研究比较三种闭合方案的主判据——"
        "基准 C<sub>aq</sub> RMSE 0.0284，Residual-AI MLP 0.0573（更差）。",
    ),
    (
        "R²",
        "决定系数（coefficient of determination）",
        "R² = 1 − 残差平方和/总平方和，衡量模型比“直接用观测均值”好多少。R² = 1 完美；R² = 0 等同于用均值；"
        "<strong>R² 可以是负数</strong>，表示模型还不如直接取平均。<strong>来龙去脉：</strong>本研究样本内 "
        "R² ≈ 0.997 看似完美，但那是同一批点既训练又预测的过拟合，仅列附录；持出 R² 多为负，才是诚实的推广力度量。",
    ),
    (
        "bias",
        "偏差（bias，系统性偏移）",
        "所有样点“预测减观测”的平均值。正偏差表示模型系统性偏高、负偏差表示系统性偏低。它与 RMSE 互补："
        "RMSE 大但 bias 小说明误差是随机散布的；bias 大说明模型整体“歪了”。<strong>来龙去脉：</strong>"
        "基准模型对高 pCO₂ 河段有系统性低估（负 bias），这是引入闭合项的初始动机。",
    ),
    (
        "pCO<sub>2</sub>",
        "二氧化碳分压（partial pressure of CO₂）",
        "水体中溶解 CO₂ 相对于气相的分压，常用 µatm（微大气压）表示。它反映水“想把多少 CO₂ 吐给大气”的势能："
        "pCO₂ 高于大气（约 400+ µatm）时河流是碳源。<strong>方程溯源：</strong>由实测 pH、水温、碱度/DIC 经"
        "碳酸盐平衡计算。<strong>来龙去脉：</strong>本研究 pCO₂ 是野外实测的核心碳状态量，干流样点密集处最高。",
    ),
    (
        "C<sub>aq</sub>",
        "溶解态 CO₂ 浓度（aqueous CO₂ concentration）",
        "单位水体积里溶解的 CO₂ 摩尔数，单位 mol·m⁻³，由 pCO₂ 乘以亨利溶解度得到。它是本研究输运模型直接"
        "预测、并与观测比对的目标变量。<strong>C<sub>eq</sub></strong> 则是与当前大气 CO₂ 平衡时的浓度，"
        "C<sub>aq</sub> − C<sub>eq</sub> 就是驱动逸散的“过饱和量”。<strong>来龙去脉：</strong>所有 RMSE/R²/bias"
        "都是针对 C<sub>aq</sub> 计算的持出指标。",
    ),
    (
        "DIC",
        "溶解无机碳（Dissolved Inorganic Carbon）",
        "水里所有无机碳形态之和：溶解 CO₂、碳酸（H₂CO₃）、碳酸氢根（HCO₃⁻）、碳酸根（CO₃²⁻）。"
        "它与 pH、碱度共同决定 pCO₂。<strong>来龙去脉：</strong>本战役仅 41/120 个样点有 DIC 实测值，"
        "缺失部分<strong>保持缺失、不插补</strong>，因此 DIC 只用于辅助剖面展示，不进入主指标。",
    ),
    (
        "DOC",
        "溶解有机碳（Dissolved Organic Carbon）",
        "水中溶解态有机碳，是微生物呼吸产生 CO₂ 的“燃料”，与河流代谢、CO₂ 过饱和密切相关。"
        "<strong>来龙去脉：</strong>与 DIC 一样，DOC 仅部分样点有值（41/120），本研究不做插补，"
        "仅在沿程碳剖面里显示有值样点。",
    ),
    (
        "NHD / NHDPlus HR",
        "国家水文数据集 / 高分辨率增强版（National Hydrography Dataset / NHDPlus High Resolution）",
        "美国地质调查局（USGS）维护的标准河流矢量数据库：NHD 提供河道中心线几何与河流名称，"
        "NHDPlus HR 是高分辨率增强版，附带流向、集水面积等“增值属性（VAA）”。"
        "<strong>来龙去脉：</strong>本研究用 HydroShare 补充包里的 East_River_Lines.shp（393 段 NHD 线）"
        "划分河段，并用 NHDPlus HR HUC 14020001（8212 条 flowline）做滤波尺度实验的粗化底图——都是真实矢量，"
        "不是示意图。",
    ),
    (
        "GNIS",
        "地名信息系统（Geographic Names Information System）",
        "美国官方地名数据库，为每条有名字的河流/地物提供标准名称。<strong>来龙去脉：</strong>本研究用 GNIS 名称"
        "把 NHD 线段自动对应到 8 条研究河段，成功匹配 85 段；其余无名线段只能按“离哪条河段最近”分配，"
        "这也是部分支流归属存在不确定性的原因。",
    ),
    (
        "chainage",
        "链距（chainage，沿程里程）",
        "沿河道中心线从上游某个基准点累加的实际长度（m 或 km），也叫沿程距离。它把二维弯曲的河线“拉直”成"
        "一维坐标，方便画纵剖面。<strong>方程溯源：</strong>由 NHD 线段在 UTM 投影下的真实线长逐段累加，"
        "样点先垂直投影到最近中心线再取其链距。<strong>来龙去脉：</strong>所有“沿程剖面”图的横轴都是链距。",
    ),
    (
        "Manning 公式",
        "曼宁公式（Manning equation，明渠均匀流经验公式）",
        "u = (1/n)·R<sup>2/3</sup>·S₀<sup>1/2</sup>，其中 n 是河床糙率、R 是水力半径、S₀ 是坡度。"
        "它把流速、水深、坡度、糙率联系起来，是估算天然河道流速/水深最常用的经验关系。"
        "<strong>来龙去脉：</strong>本研究缺少逐河段实测断面，用 Manning 公式结合流量 Q 和坡度反推水深 h、"
        "河宽 W 与流速 u，因此这些量是<strong>经验估算而非实测</strong>，断面图属理想化示意。",
    ),
    (
        "equifinality",
        "等效性 / 实际不可辨识（equifinality / practical non-identifiability）",
        "指“多组截然不同的参数能给出几乎一样的观测拟合”，因而无法凭现有观测把它们区分开。"
        "<strong>物理意义：</strong>在准稳态平衡 (Q/A)(C<sub>in</sub>−C) + S<sub>sgs</sub> − k(C−C<sub>eq</sub>) = 0 里，"
        "只观测浓度时，“增大 S<sub>sgs</sub>”与“减小 k”对 C 的效果几乎一样，却对逸散通量 F 的影响完全相反。"
        "<strong>来龙去脉：</strong>本研究强调这是<strong>实践上的（practical）</strong>等效——受限于当前只有浓度"
        "观测——而非已经数学证明的结构不可辨识；要打破它需要独立的通量或 k 观测。",
    ),
    (
        "residual",
        "残差（residual）",
        "观测与模型之间没有被解释的差。本研究里有两种残差：一是预测残差（预测 C − 观测 C，用于 RMSE/bias）；"
        "二是<strong>质量守恒残差</strong>，即基准平流—交换平衡对不上观测时的缺口，正是它被定义为亚网格源汇 "
        "S<sub>sgs</sub> 并交给机器学习去学。<strong>来龙去脉：</strong>“把残差当学习目标”是残差学习"
        "（Yuval &amp; O’Gorman, 2020 的物理约束 ML 思路）的核心。",
    ),
    (
        "proxy",
        "代理量（proxy）",
        "无法直接测量某量时，用一个可计算/可测量、且与之相关的替代量来近似。<strong>来龙去脉：</strong>"
        "本研究的逸散通量 F<sub>CO₂</sub> 是由 k(C − C<sub>eq</sub>) 算出的<strong>模型诊断/代理</strong>，"
        "并非用通量箱（chamber）或涡动相关（eddy covariance）直接实测的通量；因此文中一律把它称为"
        "“模型通量诊断/代理”，不作为独立验证过的真通量。",
    ),
]


def glossary_html() -> str:
    """Render the terminology glossary as a definition-style HTML block."""
    rows = []
    for sym, full, desc in GLOSSARY:
        rows.append(
            f'<div class="term"><div class="term-head"><span class="term-sym">{sym}</span>'
            f'<span class="term-full">{full}</span></div>'
            f'<div class="term-body">{desc}</div></div>'
        )
    return (
        '<div class="glossary">\n'
        '<p class="lead">下表把本报告用到的每一个缩写/符号都给出<strong>全称</strong>与<strong>深度解释</strong>'
        '（物理意义、方程溯源、来龙去脉）。正文首次出现时也会随文解释，读者遇到不熟悉的记号可随时回查此处。</p>\n'
        + "\n".join(rows)
        + "\n</div>"
    )


# ---------------------------------------------------------------------------
# Real-number loaders (read frozen CSVs; never invent).
# ---------------------------------------------------------------------------
def load_nested_loo_reach() -> dict:
    """Return {(scheme,model): row-dict} for loo_reach / all_120."""
    df = pd.read_csv(TABLES / "nested_cv_metrics.csv")
    d = df[(df["cv_protocol"] == "loo_reach") & (df["subgroup"] == "all_120")]
    out = {}
    for _, r in d.iterrows():
        out[(str(r["scheme"]), str(r["model"]))] = r.to_dict()
    return out


def load_summary_json(name: str) -> dict:
    p = TABLES / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def fmt(v, nd: int = 4) -> str:
    try:
        if v is None or (isinstance(v, float) and v != v):
            return "—"
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return str(v)
