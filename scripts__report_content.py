"""Chinese report prose, river-network table, and figure manifest for generate_report.py."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"

# Eight logical reaches mapped onto the directed NHDPlus HR tree.
# Upstream/Downstream columns are NOT a serial chain: each tributary joins a
# mainstem segment (R008_S1–S6). See data_proc/network_segments.csv.
#
# P1-08 / reviewer R3-m6: the word "segment" previously denoted four different
# objects.  Table 1 now reports them as four explicitly named estimands, and
# every number is injected from the machine tables at build time (no literals):
#
#   raw corridor flowline    features of data_raw/nhdplus/East_River_Lines.shp
#   assigned corridor line   rows of data_proc/gis_reach_line_mapping.csv
#   logical routing segment   rows of data_proc/network_segments.csv
#   sampled control volume    unique physical_cell_id sample-support cells
#
# The legacy hand-written "NHD segments" column (a GNIS-only tally) and the
# uncertified legacy "reported channel length" field are both removed.
TABLE1_COLUMN_DEFS = [
    ("已分配走廊线", "gis_reach_line_mapping.csv 行数：NHDPlus HR 走廊线上归属到该河段的线段，含 nearest_campaign_sample 分配"),
    ("·GNIS 匹配", "上述已分配走廊线中由 GNIS 名称匹配得到的条数"),
    ("·最近样点", "上述已分配走廊线中由最近战役 GPS 样点分配得到的条数（非质心回退）"),
    ("逻辑路由段", "network_segments.csv 中的路由节点数（7 个支流节点 + 6 个干流节点），不是河道线"),
    ("采样控制体", "reach_daily_observations.csv 中唯一 physical_cell_id 数：实际支撑样本的控制体"),
    ("战役样点", "战役观测行数（分组交叉验证的持出单元）"),
    ("控制体域长 (km)", "length_conservation.csv 的固定控制体域长 domain_length_m；替代无可核验来源的旧“报告河长”字段"),
]

# Reach notes (labels only — no numbers injected here).
REACH_NOTES_ZH = {
    "R001": "支流源头，n=1 仅作示意",
    "R002": "草甸河段，连接 Bradley 与 Rock",
    "R003": "Rock 溪，多样本支流",
    "R004": "Copper 溪，走廊线最多",
    "R005": "Gothic 支流，多样本",
    "R006": "单样本，仅作示意",
    "R007": "单样本，仅作示意",
    "R008": "干流 Almont 上游，样点最密",
}


def load_table1() -> dict:
    """Table 1 numbers from the single numeric source (paper_values.json)."""
    path = TABLES / "paper_values.json"
    if not path.exists():
        return {}
    try:
        return (json.loads(path.read_text(encoding="utf-8")) or {}).get("table1", {}) or {}
    except Exception:  # noqa: BLE001 - a broken cache must not crash the build
        return {}


def reach_network_table_html(table1: dict | None = None) -> str:
    """Render Table 1 with every count injected from the machine tables.

    ``table1`` defaults to ``paper_values.json``; generators that already hold
    the frozen object pass it in so the HTML and the numeric source cannot drift.
    """
    t1 = table1 if table1 is not None else load_table1()
    rows = t1.get("rows") or []
    raw_pool = t1.get("raw_corridor_pool_n")
    raw_unassigned = t1.get("raw_corridor_unassigned_n")

    body = []
    for r in rows:
        rid = str(r.get("reach_id", ""))
        dom = r.get("domain_length_km")
        dom_s = "—" if dom is None else f"{float(dom):.3f}"
        dagger = "" if r.get("domain_consistent") else " †"
        joins = str(r.get("joins_mainstem", "—"))
        role = str(r.get("role", ""))
        role_s = "Mainstem (S1–S6)" if role == "Mainstem" else role
        body.append(
            f'    <tr><td>{rid}</td><td class="left">{r.get("stream_name", "")}</td>'
            f'<td>{role_s}</td><td>{joins}</td>'
            f'<td>{dom_s}{dagger}</td>'
            f'<td>{r.get("assigned_flowlines", "")}</td>'
            f'<td>{r.get("assigned_gnis_match", "")}</td>'
            f'<td>{r.get("assigned_nearest_sample", "")}</td>'
            f'<td>{r.get("routing_segments", "")}</td>'
            f'<td>{r.get("sampled_cells", "")}</td>'
            f'<td>{r.get("campaign_samples", "")}</td>'
            f'<td class="left">{REACH_NOTES_ZH.get(rid, "")}</td></tr>'
        )
    totals = t1.get("totals") or {}
    if totals:
        body.append(
            f'    <tr class="totals"><td>合计</td><td class="left">8 条逻辑河段</td><td>—</td>'
            f'<td>—</td><td>—</td>'
            f'<td>{totals.get("assigned_flowlines", "")}</td>'
            f'<td>{totals.get("assigned_gnis_match", "")}</td>'
            f'<td>{totals.get("assigned_nearest_sample", "")}</td>'
            f'<td>{totals.get("routing_segments", "")}</td>'
            f'<td>{totals.get("sampled_cells", "")}</td>'
            f'<td>{totals.get("campaign_samples", "")}</td>'
            f'<td class="left">—</td></tr>'
        )

    return (
        "\n<table>\n"
        "  <caption>表 2 East River 研究河网：8 条逻辑河段与四种互不相同的估计量"
        "（原始走廊线 / 已分配走廊线 / 逻辑路由段 / 采样控制体），数字全部由机器表动态生成</caption>\n"
        "  <thead>\n"
        "    <tr>\n"
        "      <th>河段编号</th><th>河流名称</th><th>角色</th><th>汇入干流段</th>\n"
        "      <th>控制体域长 (km)</th><th>已分配走廊线</th><th>·GNIS 匹配</th><th>·最近样点</th>\n"
        "      <th>逻辑路由段</th><th>采样控制体</th><th>战役样点</th><th>说明</th>\n"
        "    </tr>\n"
        "  </thead>\n"
        "  <tbody>\n" + "\n".join(body) + "\n"
        "  </tbody>\n"
        "</table>\n"
        "<p class=\"lead\">表 2 的四种计数<strong>不是同一个对象</strong>，不得混用："
        "<strong>原始走廊线</strong>（East_River_Lines.shp 要素，全研究走廊共 "
        f"{raw_pool if raw_pool is not None else '—'} 条，其中未被归属 {raw_unassigned if raw_unassigned is not None else '—'} 条）；"
        "<strong>已分配走廊线</strong>（按河段归属，含最近样点分配）；<strong>逻辑路由段</strong>"
        "（network_segments.csv 的 13 个报告/路由节点）；<strong>采样控制体</strong>"
        "（唯一 physical_cell_id，实际支撑样本）。原表“NHD 线段数”是仅按 GNIS 统计的旧口径，"
        "已删除。原表“河长”字段无可核验机器来源，已替换为固定控制体域长；"
        "标 <strong>†</strong> 者表示该河段 recorded support 尚未通过域一致性核验，其域长不得用于反推面积。</p>\n"
        "<p class=\"lead\">读图前请先理解这张表：七条支流各自汇入 East River 干流分段（R008_S1–S6）。"
        "干流分段按汇流点链距划分并串成 S1→Sn，是<strong>逻辑报告 / 简化路由树</strong>，"
        "<strong>不是</strong>“真实 NHD 有向拓扑压缩”的正式证明。细尺度滤波实验使用 NHDPlus HR 端点匹配有向图；"
        "二者不可混称。浓度在汇合处以流量加权混合。平面 GIS 图中的彩色河线来自 HydroShare 补充包与"
        "NHDPlus HR（HUC 14020001）。</p>\n"
    )

READING_GUIDE_HTML = """
<div class="reading-guide">
  <h3>如何阅读本报告（建议顺序）</h3>
  <ol>
    <li><strong>先看表 2</strong>：弄清 8 条河段谁是支流、谁是干流（R008）；干流分段是逻辑简化树，不是已核验的 NHD 压缩。</li>
    <li><strong>再看第四节 A 组图（图 1–5）</strong>：在河网线上看样点分布、流量与流速箭头——建立空间概念。</li>
    <li><strong>然后看 B 组（图 6–11）</strong>：水动力沿河道如何变化；图 9 是理想化断面内的流速分布示意。</li>
    <li><strong>接着看 C、D 组</strong>：pCO₂、CO₂ 通量在空间和时间上如何分布；Baseline 与 AI 方法差在哪里。</li>
    <li><strong>最后看分组交叉验证图与主表</strong>：论文主指标是<strong>留一河段后的 C<sub>aq</sub></strong>（分组 CV，无内层调参），通量列为重叠样点面积诊断，不是研究区总量。单样本河段只作示意。</li>
    <li><strong>再看创新实验图</strong>：滤波仅报告 native/2×/4×（study_reach 因收缩成环已排除）；可辨识性为 profile SSE，不是似然。</li>
  </ol>
  <p>全文为对 Saccardi &amp; Winnick (2021) HydroShare 公开观测 + 公共 NHD/USGS 的<strong>再分析</strong>
  （冻结 run <code>20260919_remediation</code>），<strong>不是自采数据</strong>；未使用合成观测。</p>
</div>
"""

SECTION_INTROS = {
    "network": (
        "<h3>4.1 研究区河网：哪一段是哪条河？</h3>"
        "<p>本节回答三个问题：<strong>（1）河网在地图上长什么样？（2）8 条研究河段与 NHD 矢量线如何对应？（3）水流方向与流量大小如何直观展示？</strong>"
        "所有图均基于真实 Shapefile 线几何绘制，样点为野外 GPS 实测位置。</p>"
    ),
    "hydro": (
        "<h3>4.2 水动力：流量、流速沿河道如何分布？</h3>"
        "<p>本节展示战役期各河段的流量 Q、流速 u、水深 h 等水力变量。"
        "干流 R008 流量最大；平面箭头图表示<strong>沿河道指向下游</strong>的流动方向。"
        "断面图（图 9）在缺乏实测地形断面时，用<strong>梯形断面 + 抛物线流速分布</strong>做示意，并非现场 ADCP 测量结果。</p>"
    ),
    "carbon": (
        "<h3>4.3 碳状态与 CO₂ 通量：河水里有多少碳、向大气释放多少？</h3>"
        "<p>pCO₂ 与溶解 CO₂ 浓度 C<sub>aq</sub> 来自野外水样化验；CO₂ 逸散通量 F<sub>CO₂</sub> 由 Ulseth (2019) 能量耗散公式结合流速、坡度计算，"
        "Raymond (2012) 作为敏感性列存档。"
        "热图横轴为日期、纵轴为河段，颜色越深表示数值越高。</p>"
    ),
    "comparison": (
        "<h3>4.4 两种方法对比：不加 AI 闭合（Baseline）vs 加入亚网格闭合（AI）</h3>"
        "<p>Baseline 只用水动力输运和气体交换公式，不额外修正源汇项；AI 方法在 Baseline 基础上学习残差闭合项 S<sub>sgs</sub>，"
        "用来弥补小尺度过程（如地下水 CO₂ 输入、局地呼吸）在大尺度模型中被“平均掉”的部分。</p>"
    ),
    "nestedcv": (
        "<h3>4.5 分组交叉验证（论文主指标；无内层超参数循环）</h3>"
        "<p>把某一条河或某一天全部留出；残差 S<sub>sgs</sub> 与 k 目标在<strong>每一折内</strong>仅用训练河段观测重建"
        "（折外浓度标签不进入训练目标）。再代入与基准相同的输运方程，只对留出样本计分。"
        "三种闭合：① Baseline（S<sub>sgs</sub>=0）；② Residual-AI；③ k 修正。"
        "<strong>主文报告持出 C<sub>aq</sub>；通量列为重叠样点面积诊断，不是研究区总量。</strong>"
        "MLP 点估计可低于 Baseline，但 RF 更差、通量诊断不稳定——不作成功宣传。</p>"
    ),
    "innovation": (
        "<h3>4.6 创新实验：滤波尺度、可辨识性、无量纲稀疏式</h3>"
        "<p>本节<strong>不是</strong>精度竞赛。滤波正式尺度仅含 native / 2× / 4×；"
        "<strong>study_reach 因全边保留后出现收缩环而排除</strong>，不得据此声称“到研究河段尺度仍近似不变”。"
        "可辨识性图为条件 profile SSE（非统计似然）。稀疏 Π 式为解释性描述，不冒充折外成功规律。</p>"
    ),
    "validation": (
        "<h3>4.7 样本内散点（乐观附录，非主指标）</h3>"
        "<p>散点图横轴为观测值、纵轴为模型预测值；点越靠近对角线表示预测越准。"
        "圆点按河段着色。这些图展示的是<strong>样本内拟合</strong>，请与分组交叉验证对照阅读，不要把附录拟合写成论文结论。</p>"
    ),
}
