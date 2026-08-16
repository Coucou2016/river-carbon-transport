"""Generate self-contained report.html and report.md with curated embedded figures."""
from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from figure_explanations import get_teach  # noqa: E402
from report_content import (  # noqa: E402
    READING_GUIDE_HTML,
    REACH_NETWORK_TABLE_HTML,
    SECTION_INTROS,
)
from report_shared import glossary_html  # noqa: E402

FIG_DIR = ROOT / "results" / "figures"
OUT_HTML = ROOT / "report.html"
OUT_MD = ROOT / "report.md"

# Curated manifest (~23 figures) in narrative order — no point-centroid network_map_*.
FIGURE_MANIFEST: list[tuple[str, str, str, str]] = [
    # (filename, caption HTML, section key, analysis HTML)
    # --- A: Study area & network ---
    (
        "gis_reach_assignment_map.png",
        "<strong>图 1</strong> 研究河段 R001–R008 与 NHD 河网矢量线的对应关系（393 段真实线几何）。",
        "network",
        "<p><strong>这张图在说明什么？</strong>彩色细线是 East River 流域的国家水文数据库（NHD）河道中心线，"
        "来自 HydroShare 补充包 <code>East_River_Lines.shp</code>，不是示意图上的几个点。"
        "8 种颜色代表我们划分的 8 条研究河段（见表 2）：例如绿色可能是 Copper Creek（R004），"
        "最粗/最集中的干流段通常是 East River（R008）。</p>"
        "<p><strong>为什么有的支流颜色分得不太准？</strong>393 段 NHD 线里只有 75 段能通过河流名称（GNIS）"
        "自动对应到研究河段；其余 318 段没有标准名称，只能按“离哪个河段中心最近”来分配，"
        "所以 Bradley、Rock、Gothic 等支流的不确定性会高一些——这在讨论部分会再次说明。</p>",
    ),
    (
        "gis_samples_on_network.png",
        "<strong>图 2</strong> 战役样点（n=120）叠加于 NHD 河网线。",
        "network",
        "<p>样点沿 East River 干流 R008 最密（58 点），支流稀疏；样点为真实 GPS 坐标，未插补。"
        "白边圆点标记样点位置，灰色线为 NHD 中心线，底色为本地地形渐变（无 CDN 瓦片）。</p>",
    ),
    (
        "sample_snap_centerline.png",
        "<strong>图 2b</strong> 120 个 GPS 样点捕捉到最近 NHD 中心线（圆点=野外坐标，叉号=线上投影）。",
        "network",
        "<p>每个水样按最近距离落到一条真实河线，再沿该线计算链距。中位捕捉距离见标题。"
        "若某点离河网很远，说明坐标或河线匹配仍有不确定性，不作插补。</p>",
    ),
    (
        "gis_flow_quiver_Q.png",
        "<strong>图 3</strong> 平面流量场 quiver 图：箭头指向下游，颜色/长度 ∝ Q。",
        "network",
        "<p>箭头方向由 NHD 线段链距拓扑确定（沿 R001→R008 下游序）；"
        "流量 Q 来自战役样点河段均值（支流为文献回归+USGS 干流比值缩放）。"
        "干流 R008 箭头最长、颜色最深，反映最大流量。</p>",
    ),
    (
        "gis_flow_quiver_u.png",
        "<strong>图 4</strong> 平面流速场 quiver 图：箭头指向下游，颜色/长度 ∝ u。",
        "network",
        "<p>流速 u 由 Q、W、h（Manning 公式）推导。高坡度、窄河道河段 u 偏大。"
        "此为河段平均值的平面示意，非 ADCP 瞬时场——详见图 12 断面 u(y,z)。</p>",
    ),
    (
        "gis_streamtube_QW_u.png",
        "<strong>图 5</strong> streamtube 示意：线宽 ∝ Q，颜色 ∝ u（NHD 真实线几何）。",
        "network",
        "<p>类似 streamtube 可视化：粗线表示大流量河段，暖色表示高流速。"
        "East River 干流段线宽最粗，直观展示水力汇流格局。</p>",
    ),
    # --- B: Hydrodynamics ---
    (
        "gis_network_map_Q.png",
        "<strong>图 6</strong> GIS 河网线图：河段平均流量 Q（m³/s），线宽 ∝ Q。",
        "hydro",
        "<p>相较已废弃的质心散点图，线图真实反映河道蜿蜒形态与空间展布。"
        "R008 干流 Q 最大（USGS 09112500）；支流 Q 取补充包公开的战役期同步流量，未用干流日比值缩放。</p>",
    ),
    (
        "gis_network_map_u.png",
        "<strong>图 7</strong> GIS 河网线图：流速 u（m/s）。",
        "hydro",
        "<p>展示水力梯度沿网分布。Rustlers Gulch（R007）与 East River 干流段 u 较高，"
        "与坡度、河道宽度相关。</p>",
    ),
    (
        "longitudinal_profile_hydraulics.png",
        "<strong>图 8</strong> 沿程水动力剖面（链距 km）：h、u、Q。",
        "hydro",
        "<p>链距由 NHD 线段在 UTM 下的<strong>真实线长</strong>累加，样点捕捉到最近中心线后再沿该段投影。"
        "散点为 120 战役样点，阶梯线为河段均值。干流下游 h、Q 增大趋势明显。</p>",
    ),
    (
        "cross_section_u_field_panel.png",
        "<strong>图 9</strong> 各河段理想化 u(y,z) 场（梯形断面，抛物线垂向分布）。",
        "hydro",
        "<p>假设：底宽 W、水深 h 来自战役样点河段均值；边坡 1:1；"
        "u(z)=1.5ū(2ζ−ζ²)（开渠湍流近似），横向均匀。无实测断面处标注<strong>待补充</strong>。</p>",
    ),
    (
        "planview_velocity_network.png",
        "<strong>图 10</strong> 平面流速分布：线宽 ∝ Q，颜色 ∝ |u|。",
        "hydro",
        "<p>与 quiver 图互补的 streamtube 风格展示。数值均来自真实战役观测与 Manning 估算，"
        "非合成场。</p>",
    ),
    (
        "temporal_hydraulics.png",
        "<strong>图 11</strong> 战役期流域平均水动力时间序列（Q、u）。",
        "hydro",
        "<p>2019-08-02 至 08-11 共 10 天融雪后基流阶段。Q、u 变化相对平缓，"
        "反映战役期水文条件稳定。年度季节分析<strong>待补充</strong>。</p>",
    ),
    # --- C: Carbon ---
    (
        "gis_network_map_pCO2.png",
        "<strong>图 12</strong> GIS 河网线图：pCO₂（µatm）空间格局。",
        "carbon",
        "<p>高 pCO₂ 区集中于 East River 干流样点密集段，与土壤 CO₂ 输入及"
        "有机质分解一致。R008 变异最大（样点 n=58）。</p>",
    ),
    (
        "carbon_heatmap_pCO2.png",
        "<strong>图 13</strong> pCO₂ 河段 × 日期热图（战役期 10 天）。",
        "carbon",
        "<p>揭示干流 R008 在 8 月 5–8 日 pCO₂ 峰值。时间分辨率受战役采样限制。</p>",
    ),
    (
        "carbon_heatmap_C_aq.png",
        "<strong>图 14</strong> 观测 C<sub>aq</sub> 河段 × 日期热图。",
        "carbon",
        "<p>溶解 CO₂ 浓度时空异质性。AI 闭合目标变量，Baseline 系统性低估高 pCO₂ 河段 C<sub>aq</sub>。</p>",
    ),
    (
        "longitudinal_profile_carbon.png",
        "<strong>图 15</strong> 沿程碳状态剖面：pCO₂、C<sub>aq</sub>、DIC、DOC。",
        "carbon",
        "<p>DIC/DOC 仅显示 41/120 有值样点，缺失未插补。沿程 pCO₂ 在干流下游升高趋势与"
        "碳源输入一致。</p>",
    ),
    (
        "carbon_heatmap_F_CO2_ai.png",
        "<strong>图 16</strong> AI 耦合 F<sub>CO₂</sub> 河段 × 日期热图。",
        "carbon",
        "<p>亚网格闭合后干流逸散通量显著抬升。通量由 Raymond (2012) k<sub>600</sub> 与"
        "pCO₂ 梯度计算。</p>",
    ),
    # --- D: Baseline vs AI ---
    (
        "gis_network_map_F_CO2_comparison.png",
        "<strong>图 17</strong> Baseline vs AI F<sub>CO₂</sub> 并列 GIS 对比（统一色标）。",
        "comparison",
        "<p>色标统一便于识别 AI 修正的空间热点。干流 R008 AI 通量远高于 Baseline，"
        "反映 S<sub>sgs</sub> 闭合对高 pCO₂ 河段的修正。</p>",
    ),
    (
        "compare_F_CO2_baseline_vs_ai.png",
        "<strong>图 18</strong> 各河段 F<sub>CO₂</sub>：Baseline vs AI 并列柱图。",
        "comparison",
        "<p>量化各河段 AI 闭合对 CO₂ 逸散通量的抬升幅度。R008 差异最大。</p>",
    ),
    (
        "difference_F_CO2_ai_minus_baseline.png",
        "<strong>图 19</strong> AI − Baseline CO₂ 通量差值（按河段）。",
        "comparison",
        "<p>正值（红色）表示 AI 抬升通量。所有河段均为正差，干流贡献主导总通量变化。</p>",
    ),
    (
        "temporal_baseline_vs_ai_flux.png",
        "<strong>图 20</strong> 战役期日均 CO₂ 通量演化：Baseline vs AI。",
        "comparison",
        "<p>逐日对比显示 AI 通量在各采样日均高于 Baseline 一个数量级以上。</p>",
    ),
    # --- Nested CV (paper metrics) ---
    (
        "nested_cv_rmse_bar.png",
        "<strong>图 N1</strong> 嵌套交叉验证：Baseline / Residual-AI / k 修正的持出样本 C<sub>aq</sub> RMSE（论文主图）。",
        "nestedcv",
        "<p><strong>先读负结果：</strong>Residual-AI 柱高于 Baseline（0.057 vs 0.028）即<strong>未改善</strong>持出浓度。"
        "k 修正柱略短，须与图 N4 / I3b 的通量诊断崩溃一并读，不能单独当“更好的物理模型”。</p>",
    ),
    (
        "nested_cv_scatter_holdout.png",
        "<strong>图 N2</strong> 留一河段持出：观测 vs 预测 C<sub>aq</sub>（Residual-AI，大圆点按河段着色）。",
        "nestedcv",
        "<p>与附录里几乎贴在 1:1 线上的样本内三角图对比：这里的点是模型从未用该河段训练时的预测。"
        "干流 R008 点最多，对总误差贡献最大；单样本河段上的单点不能当独立证据。</p>",
    ),
    (
        "subgroup_rmse_r008_vs_trib.png",
        "<strong>图 N3</strong> 子组误差：R008 干流 vs 多样本支流 vs 单样本河段（示意）。",
        "nestedcv",
        "<p>不把 1 个点的支流和 58 个点的干流当成同等证据。单样本河段柱状图仅作示意，不进入与干流对等的结论。</p>",
    ),
    (
        "ablation_flux_comparison.png",
        "<strong>图 N4</strong> 三种闭合的持出样本 F<sub>CO₂</sub> 合计与通量 RMSE（模型通量诊断）。",
        "nestedcv",
        "<p>左图是持出样本上模型逸散通量诊断合计；右图是相对“经验 k × 观测浓度”代理通量的 RMSE。"
        "无独立腔室/涡动通量验证。k 修正使合计接近 0，且与略降的 C RMSE <strong>共现</strong>（coincided with），构成 practical equifinality 证据，而非已证明的唯一因果路径。</p>",
    ),
    # --- Paper innovation experiments ---
    (
        "les_filter_conceptual.png",
        "<strong>图 I1</strong> LES 类比过滤概念：细 NHD 线段 → 滤波窗 Δx → 粗控制体上的 S<sub>sgs</sub>。",
        "innovation",
        "<p>左图：样点捕捉到较短的原生河网线段，局地平流梯度还可以写进质量守恒。"
        "右图：合并线段后，多样点落入同一控制体，未分辨过程只能进闭合项 S<sub>sgs</sub>(Δx)。"
        "“LES-analog”仅指 coarse-graining 的算子类比，不暗示 Navier–Stokes 湍流闭合；S<sub>sgs</sub> 是 filter-induced residual。"
        "这是 Gao 等 Innovation 稿件中“大涡类比”的可计算版本，不是精度宣言。</p>",
    ),
    (
        "filter_scale_sgs.png",
        "<strong>图 I2</strong> 滤波尺度实验：平均 |S<sub>sgs</sub>| 与方差随 Δx（真实样点捕捉到粗化 NHDPlus HR 线）。",
        "innovation",
        "<p>四个尺度：原生 HR 线段、约 2× 合并、约 4× 合并、研究河段。"
        "残差全部由 120 个真实水样重算，无合成观测。若细网格上 |S| 更大，说明局地平流不匹配被粗化平均掉；"
        "这与“闭合在观测尺度上更平滑、更易与 k 混淆”相一致，不能解读为 AI 精度提高。</p>",
    ),
    (
        "filter_scale_sgs_box.png",
        "<strong>图 I2b</strong> 各滤波尺度上 120 个真实样点的 |S<sub>sgs</sub>| 分布。",
        "innovation",
        "<p>箱线显示中位数与四分位，散点为单个样点。干流高残差点会拉高均值；读图时与表 4 的嵌套 CV 一起看，"
        "不要把细尺度上更大的残差当成“更需要 AI”。</p>",
    ),
    (
        "identifiability_k_vs_sgs.png",
        "<strong>图 I3</strong> 可辨识性：k<sub>eff</sub> 与隐含 S<sub>sgs</sub>，以及 Residual-AI 持出源项对照。",
        "innovation",
        "<p>准稳态下增大 S<sub>sgs</sub> 与减小 k 对浓度几乎等价：S<sub>implied</sub>=(k<sub>emp</sub>−k<sub>eff</sub>)(C−C<sub>eq</sub>)。"
        "k 修正把 k<sub>eff</sub> 压到经验 k 的约千分之一；浓度 RMSE 略降<strong>伴随</strong>逸散通量崩溃（共现诊断）。"
        "持出 Residual-AI 的 S<sub>sgs</sub> 并不等于这条隐含源项——两种闭合都不是成功的联合辨识；证据支持 practical equifinality，而非 formal structural non-identifiability。</p>",
    ),
    (
        "identifiability_tradeoff.png",
        "<strong>图 I3b</strong> 浓度–通量权衡：k<sub>eff</sub>/k<sub>emp</sub> 与三种闭合的持出 RMSE / 通量合计。",
        "innovation",
        "<p>左图：k 比值远小于 1 时 F<sub>CO₂</sub> 接近 0。右图：k 修正的 C RMSE 略低于 Baseline，"
        "但通量合计几乎消失。Residual-AI 的 C RMSE 高于 Baseline。没有一种方案同时改进浓度与物理一致的逸散。</p>",
    ),
    (
        "dimensionless_coefficients.png",
        "<strong>图 I4</strong> 无量纲 Π 群稀疏闭合系数（标准化 LASSO；PySINDy 未安装）。",
        "innovation",
        "<p>仅用 Fr、Slope、h/W、log<sub>10</sub>Re、log<sub>10</sub>Da。"
        "系数图给出可解释形式；留一河段对 S<sub>sgs</sub> 的 R² 为负、代入输运后的 C RMSE 仍高于 Baseline。"
        "<strong>发表点是表达式，不是精度金牌。</strong></p>",
    ),
    # --- E: Validation & statistics ---
    (
        "obs_vs_model_scatter_large.png",
        "<strong>图 21</strong> 验证散点总览（大图）：圆点 = Baseline，三角 = AI；颜色区分河段（n=120）。",
        "validation",
        "<p><strong>怎么读这张图？</strong>横轴是野外实测的溶解 CO₂ 浓度，纵轴是模型算出来的浓度。"
        "黑色虚线是“预测完全正确”的 1:1 线——点越靠近这条线越好。"
        "圆点是<strong>不加 AI 闭合</strong>的基准模型（Baseline），三角是<strong>加入亚网格闭合</strong>后的 AI 模型。"
        "不同颜色代表不同河段（R001–R008），可以看出干流 R008（点最多）上的拟合改善最明显。</p>"
        "<p><strong>注意：</strong>三角几乎落在 1:1 线上，说明在<strong>同一批 120 个样点上</strong> AI 拟合很好；"
        "但这不等于换一条没见过的河也能预测准——表 4 的留一河段交叉验证才是更严格的考验。</p>",
    ),
    (
        "obs_vs_model_scatter.png",
        "<strong>图 22</strong> 分模型验证散点：左 Baseline，右 AI（分河段着色，附 RMSE 与 R²）。",
        "validation",
        "<p>左右两幅分开对比更清楚：左图 Baseline 系统性偏离 1:1 线（多数点在对角线下方，说明模型偏低）；"
        "右图 AI 在样本内几乎贴合观测。每幅图左上角标注了 RMSE 和 R²，便于与表 3 对照。</p>",
    ),
    (
        "obs_vs_model_by_reach.png",
        "<strong>图 23</strong> 八个河段各自的验证小图：每格对应表 2 中的一条河。",
        "validation",
        "<p>把总散点拆成 8 张，便于逐河查看。R008 干流格子里点最多（n=58），Baseline 偏离最明显；"
        "R001、R006、R007 等仅 1 个样点的河段，单点无法判断趋势，统计上也不稳定。"
        "读图时请结合表 2 的样点数列，避免对样点极少的河段过度解读。</p>",
    ),
    (
        "flux_by_reach.png",
        "<strong>图 24</strong> 各河段平均 CO₂ 向大气释放通量 F<sub>CO₂</sub>（Baseline vs AI 柱图）。",
        "validation",
        "<p>通量是浓度与气体交换系数综合的结果。AI 闭合后，各河段通量均高于 Baseline，"
        "干流 R008 抬升幅度最大——这与干流 pCO₂ 高、样点密集、S<sub>sgs</sub> 残差大相一致。"
        "通量绝对值对 k 公式敏感，解释时需注意经验参数不确定性。</p>",
    ),
    (
        "seasonal_rmse.png",
        "<strong>图 25</strong> 战役期逐日预测误差 RMSE（C<sub>aq</sub>）：Baseline vs AI。",
        "validation",
        "<p>横轴为 8 月 2–11 日各采样日。AI 在各日 RMSE 均低于 Baseline，说明在战役窗口内拟合稳定。"
        "仅 10 天数据，<strong>不能</strong>代表全年季节变化——融雪期、枯水期表现<strong>待补充</strong>。</p>",
    ),
    (
        "sgs_residual_by_reach.png",
        "<strong>图 26</strong> 亚网格残差 S<sub>sgs</sub> 各河段分布（AI 需要学习的“缺口”）。",
        "validation",
        "<p>S<sub>sgs</sub> = 观测与 Baseline 之间的质量守恒残差，是 AI 的训练目标。"
        "R008 残差最大，说明干流上有 Baseline 未解释的碳源/汇过程最多。"
        "表 4 显示：把某条河留出做验证时（LOO-reach），MLP 的 R² 仍为负——"
        "说明 120 个样点尚不足以让 AI 可靠推广到<strong>未参与训练的河段</strong>。</p>",
    ),
]

def b64_img(name: str) -> str:
    p = FIG_DIR / name
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode("ascii")


def _fmt(v, nd=4):
    try:
        if v is None or (isinstance(v, float) and (v != v)):
            return "—"
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return str(v)


def paper_main_table_html() -> str:
    """Consolidated manuscript table from paper_main_results.csv if present."""
    import pandas as pd

    p = ROOT / "results" / "tables" / "paper_main_results.csv"
    if not p.exists():
        return ""
    df = pd.read_csv(p)
    df = df[df["scheme"].isin(["baseline", "residual_ai", "k_correction", "sparse_pi"])]
    rows = []
    for _, r in df.iterrows():
        beats = r.get("beats_baseline_c")
        if pd.isna(beats):
            beat_s = "—"
        else:
            beat_s = "否" if (beats is False or str(beats).lower() == "false") else "是"
        k_ratio = r.get("k_ratio_median")
        rows.append(
            "<tr>"
            f"<td class=\"left\">{r.get('scheme','')} / {r.get('model','')}</td>"
            f"<td>{_fmt(r.get('rmse_c'))}</td>"
            f"<td>{_fmt(r.get('flux_total_mol_m2d'), 2)}</td>"
            f"<td>{_fmt(k_ratio, 5) if k_ratio == k_ratio else '—'}</td>"
            f"<td>{beat_s}</td>"
            f"<td class=\"left\">{r.get('notes','')}</td>"
            "</tr>"
        )
    return f"""
  <table>
    <caption>表 M 论文主结果一览（留一河段嵌套 CV；F<sub>CO₂</sub> 为模型导出通量诊断/代理，非腔室验证）</caption>
    <thead>
      <tr>
        <th>方案 / 模型</th><th>C RMSE</th><th>F 合计</th><th>k<sub>eff</sub>/k<sub>emp</sub></th>
        <th>C 优于 Baseline？</th><th class="left">读表要点</th>
      </tr>
    </thead>
    <tbody>
{''.join(rows)}
    </tbody>
  </table>
  <p class="lead">表 M 由 <code>scripts/build_paper_tables.py</code> 从嵌套 CV / 可辨识性汇总；数字与表 4 一致。
  Residual-AI 与稀疏 Π <strong>均未</strong>优于 Baseline；k 修正略降 C 但通量崩溃 → practical equifinality。</p>
"""


def nested_cv_tables_html() -> str:
    """Main paper tables from nested_cv_metrics.csv / subgroup_metrics.csv."""
    import pandas as pd

    nested_p = ROOT / "results" / "tables" / "nested_cv_metrics.csv"
    sub_p = ROOT / "results" / "tables" / "subgroup_metrics.csv"
    if not nested_p.exists():
        return "<p class=\"tbd\">嵌套交叉验证表尚未生成（待补充）。</p>"

    nested = pd.read_csv(nested_p)
    loo = nested[(nested["cv_protocol"] == "loo_reach") & (nested["subgroup"] == "all_120")].copy()
    rows = []
    for _, r in loo.iterrows():
        rows.append(
            "<tr>"
            f"<td class=\"left\">{r.get('scheme','')} / {r.get('model','')}</td>"
            f"<td>{_fmt(r.get('rmse_c'))}</td>"
            f"<td>{_fmt(r.get('mae_c'))}</td>"
            f"<td>{_fmt(r.get('bias_c'))}</td>"
            f"<td>{_fmt(r.get('r2_c'), 3)}</td>"
            f"<td>{_fmt(r.get('rmse_f'), 3)}</td>"
            f"<td>{_fmt(r.get('bias_f'), 3)}</td>"
            f"<td>{_fmt(r.get('flux_total_mol_m2d'), 2)}</td>"
            f"<td>{int(r.get('n', 0))}</td>"
            "</tr>"
        )
    table_m = paper_main_table_html()
    table4 = f"""
  <table>
    <caption>表 4 嵌套交叉验证（留一河段）— 持出样本 C<sub>aq</sub> 与 F<sub>CO₂</sub>（论文主指标；F 为模型通量诊断）</caption>
    <thead>
      <tr>
        <th>方案 / 模型</th><th>C RMSE</th><th>C MAE</th><th>C Bias</th><th>C R²</th>
        <th>F RMSE</th><th>F Bias</th><th>F 合计</th><th>n</th>
      </tr>
    </thead>
    <tbody>
{''.join(rows)}
    </tbody>
  </table>
  <p class="lead">读表：只比较持出样本。若 Residual-AI 的 C RMSE 不低于 Baseline，则不能声称 AI 闭合改善了推广预测。
  F<sub>CO₂</sub> 合计是 k(C−C<sub>eq</sub>) 模型诊断，不是独立通量观测。</p>
"""
    table4 = table_m + table4
    appendix = nested[nested["cv_protocol"] == "in_sample"].copy()
    arows = []
    for _, r in appendix.iterrows():
        arows.append(
            "<tr>"
            f"<td class=\"left\">{r.get('model','')}（样本内，乐观）</td>"
            f"<td>{_fmt(r.get('rmse_c'))}</td>"
            f"<td>{_fmt(r.get('bias_c'))}</td>"
            f"<td>{_fmt(r.get('r2_c'), 3)}</td>"
            f"<td>{int(r.get('n', 0))}</td>"
            "</tr>"
        )
    table_app = f"""
  <table>
    <caption>表 4b 样本内指标（乐观附录，非论文主结论）</caption>
    <thead><tr><th>模型</th><th>C RMSE</th><th>C Bias</th><th>C R²</th><th>n</th></tr></thead>
    <tbody>
{''.join(arows) if arows else '<tr><td colspan="5">待补充</td></tr>'}
    </tbody>
  </table>
"""
    sub_html = ""
    if sub_p.exists():
        sub = pd.read_csv(sub_p)
        sub = sub[(sub["cv_protocol"] == "loo_reach") & (sub["model"].isin(["none", "mlp", "xgboost"]))]
        srows = []
        for _, r in sub.iterrows():
            srows.append(
                "<tr>"
                f"<td class=\"left\">{r.get('scheme','')}</td>"
                f"<td class=\"left\">{r.get('subgroup_label', r.get('subgroup',''))}</td>"
                f"<td>{r.get('evidence_weight','')}</td>"
                f"<td>{_fmt(r.get('rmse_c'))}</td>"
                f"<td>{_fmt(r.get('r2_c'), 3)}</td>"
                f"<td>{int(r.get('n', 0))}</td>"
                "</tr>"
            )
        sub_html = f"""
  <table>
    <caption>表 5 子组嵌套交叉验证（留一河段 C<sub>aq</sub>）— 干流与支流不等权重</caption>
    <thead>
      <tr><th>方案</th><th>子组</th><th>证据权重</th><th>C RMSE</th><th>C R²</th><th>n</th></tr>
    </thead>
    <tbody>
{''.join(srows)}
    </tbody>
  </table>
  <p class="lead">R008 有 58 个点；R004+R006 按计划列出（实际样点以流水线计数为准）；
  R001/R006/R007 为单样本河段，标记为 schematic，不与干流均等权重。</p>
"""
    return table4 + table_app + sub_html


def innovation_tables_html() -> str:
    """Filter-scale, identifiability, and dimensionless sparse tables."""
    import json
    import pandas as pd

    parts = []
    fs_p = ROOT / "results" / "tables" / "filter_scale_metrics.csv"
    if fs_p.exists():
        fs = pd.read_csv(fs_p)
        rows = []
        for _, r in fs.iterrows():
            rows.append(
                "<tr>"
                f"<td class=\"left\">{r.get('dx_label', r.get('scale_id',''))}</td>"
                f"<td>{_fmt(r.get('dx_m'), 0)}</td>"
                f"<td>{int(r.get('n_cells_total', 0))}</td>"
                f"<td>{int(r.get('n_cells_with_samples', 0))}</td>"
                f"<td>{int(r.get('n_samples', 0))}</td>"
                f"<td>{_fmt(r.get('mean_abs_S_sgs'), 3)}</td>"
                f"<td>{_fmt(r.get('var_S_sgs'), 3)}</td>"
                "</tr>"
            )
        src = str(fs["lattice_source"].iloc[0]) if "lattice_source" in fs.columns and len(fs) else ""
        parts.append(
            f"""
  <table>
    <caption>表 6 滤波尺度实验：真实样点捕捉到粗化河网后的 S<sub>sgs</sub>（{src}）</caption>
    <thead>
      <tr>
        <th>尺度</th><th>Δx (m)</th><th>单元总数</th><th>有样点单元</th><th>n 样点</th>
        <th>平均 |S|</th><th>Var(S)</th>
      </tr>
    </thead>
    <tbody>
{''.join(rows)}
    </tbody>
  </table>
  <p class="lead">残差随粗化而变平滑，这是 East River/NHDPlus-HR 廊道上的<strong>经验尺度依赖</strong>，
  不是普适 SGS 定律，也不能解释为预测精度提高。研究河段尺度上有样点单元数可能少于 8，
  因为 NHDPlus HR 廊道赋值未覆盖全部逻辑河段——如实列出。</p>
"""
        )

    id_p = ROOT / "results" / "tables" / "identifiability_metrics.csv"
    id_j = ROOT / "results" / "tables" / "identifiability_summary.json"
    if id_p.exists():
        idf = pd.read_csv(id_p)
        rows = []
        for _, r in idf.iterrows():
            rows.append(
                "<tr>"
                f"<td class=\"left\">{r.get('scheme','')}</td>"
                f"<td>{_fmt(r.get('rmse_c'))}</td>"
                f"<td>{_fmt(r.get('flux_total'), 2)}</td>"
                f"<td>{_fmt(r.get('k_eff_median'), 3)}</td>"
                f"<td>{_fmt(r.get('k_ratio_median'), 5)}</td>"
                "</tr>"
            )
        finding = ""
        if id_j.exists():
            finding = json.loads(id_j.read_text(encoding="utf-8")).get("finding", "")
        parts.append(
            f"""
  <table>
    <caption>表 7 可辨识性：同一嵌套 CV 持出协议下 k 与 S<sub>sgs</sub> 的权衡</caption>
    <thead>
      <tr><th>方案</th><th>C RMSE</th><th>F 合计</th><th>k 中位数</th><th>k<sub>eff</sub>/k<sub>emp</sub></th></tr>
    </thead>
    <tbody>
{''.join(rows)}
    </tbody>
  </table>
  <p class="lead">{finding}</p>
"""
        )

    sp_j = ROOT / "results" / "tables" / "dimensionless_sparse_summary.json"
    sp_cv = ROOT / "results" / "tables" / "sparse_pi_nested_cv.csv"
    if sp_j.exists():
        sp = json.loads(sp_j.read_text(encoding="utf-8"))
        eq = sp.get("equation_standardized_Sstar", "")
        eq_x = sp.get("equation_original_Sstar", "")
        ncv_rmse = sp.get("nested_cv_transport_rmse_c")
        ncv_r2 = sp.get("nested_cv_transport_r2_c")
        s_r2 = sp.get("loo_reach_Sstar_r2")
        extra = ""
        if sp_cv.exists():
            scv = pd.read_csv(sp_cv)
            if len(scv):
                extra = (
                    f"<tr><td class=\"left\">sparse_pi / lasso_pi（留一河段）</td>"
                    f"<td>{_fmt(scv.iloc[0].get('rmse_c'))}</td>"
                    f"<td>{_fmt(scv.iloc[0].get('r2_c'), 3)}</td>"
                    f"<td>{_fmt(scv.iloc[0].get('rmse_f'), 3)}</td>"
                    f"<td>{int(scv.iloc[0].get('n', 0))}</td></tr>"
                )
        parts.append(
            f"""
  <table>
    <caption>表 8 无量纲稀疏闭合（Π 群 LASSO；PySINDy 未安装）</caption>
    <thead>
      <tr><th>项目</th><th colspan="4" class="left">结果</th></tr>
    </thead>
    <tbody>
      <tr><td class="left">标准化式</td><td colspan="4" class="left"><code>{eq}</code></td></tr>
      <tr><td class="left">原始变量式</td><td colspan="4" class="left"><code>{eq_x}</code></td></tr>
      <tr><td class="left">主导项</td><td colspan="4" class="left">{sp.get('dominant_standardized','')}</td></tr>
      <tr><td class="left">对 S* 的留一河段 R²</td><td colspan="4">{_fmt(s_r2, 3)}（负值 = 不能推广）</td></tr>
    </tbody>
  </table>
  <table>
    <caption>表 8b 无量纲稀疏式代入输运后的嵌套 CV（对照表 4 的 Baseline 0.028）</caption>
    <thead>
      <tr><th>方案</th><th>C RMSE</th><th>C R²</th><th>F RMSE</th><th>n</th></tr>
    </thead>
    <tbody>
{extra if extra else f'<tr><td class="left">sparse_pi</td><td>{_fmt(ncv_rmse)}</td><td>{_fmt(ncv_r2, 3)}</td><td>—</td><td>120</td></tr>'}
    </tbody>
  </table>
  <p class="lead">稀疏式可解释，但持出 C RMSE 不低于 Baseline。这不是精度创新，而是闭合形式创新。</p>
"""
        )
    return "\n".join(parts)


def build_figure_sections() -> tuple[str, list[str]]:
    """Return HTML blocks and list of embedded figure filenames (manifest only)."""
    sections: dict[str, list[str]] = {k: [] for k in SECTION_INTROS}
    embedded: list[str] = []

    for fname, caption, section, short_analysis in FIGURE_MANIFEST:
        data = b64_img(fname)
        if not data:
            continue
        embedded.append(fname)
        # Prefer long teaching-style explanation; fall back to short caption analysis.
        analysis = get_teach(fname, short_analysis)
        large_cls = " figure-large" if ("scatter" in fname or "nested_cv" in fname or "identifiability" in fname or "filter_scale" in fname) else ""
        block = f"""  <div class="figure-block{large_cls}">
    <img src="data:image/png;base64,{data}" alt="{fname}">
    <div class="fig-caption">{caption}</div>
    <div class="fig-analysis">{analysis}</div>
  </div>"""
        sections[section].append(block)

    html_parts = []
    for key in ["network", "hydro", "carbon", "comparison", "nestedcv", "innovation", "validation"]:
        if sections.get(key):
            html_parts.append(SECTION_INTROS[key])
            html_parts.extend(sections[key])

    return "\n".join(html_parts), embedded


def main() -> None:
    figure_html, embedded = build_figure_sections()
    n_figs = len(embedded)
    missing = [f for f, _, _, _ in FIGURE_MANIFEST if f not in embedded]
    nested_tables = nested_cv_tables_html()
    innovation_tables = innovation_tables_html()

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>基于物理约束机器学习的河网 CO₂ 输运亚网格参数化研究 — East River 案例报告</title>
<style>
:root {{
  --primary: #1a3a5c;
  --accent: #2c6e8a;
  --bg: #fafbfc;
  --text: #222;
  --muted: #555;
  --border: #d0d7de;
  --table-head: #e8eef3;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif;
  font-size: 18px;
  line-height: 1.85;
  color: var(--text);
  background: var(--bg);
}}
.container {{ max-width: 1100px; margin: 0 auto; padding: 2rem 1.75rem 4rem; }}
.lead {{ font-size: 1.05em; line-height: 1.9; margin: 1rem 0 1.25rem; }}
.reading-guide {{
  background: #eef6fa;
  border: 1px solid #b8d4e3;
  border-radius: 8px;
  padding: 1.25rem 1.5rem;
  margin: 1.5rem 0 2rem;
  font-size: 1.02em;
}}
.reading-guide h3 {{ margin-top: 0; font-size: 1.2em; }}
.cover {{
  min-height: 90vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  page-break-after: always;
  border-bottom: 3px solid var(--primary);
  margin-bottom: 2rem;
  padding: 3rem 1rem;
}}
.cover .org {{ font-size: 0.95rem; color: var(--muted); margin-bottom: 2rem; }}
.cover h1 {{
  font-size: 2rem;
  color: var(--primary);
  font-weight: 700;
  line-height: 1.4;
  max-width: 800px;
  margin-bottom: 1rem;
}}
.cover .subtitle {{ font-size: 1.1rem; color: var(--accent); margin-bottom: 2.5rem; }}
.cover .meta {{ font-size: 0.9rem; color: var(--muted); line-height: 2; }}
.cover .date {{ margin-top: 3rem; font-size: 0.95rem; }}
.toc {{ background: #fff; border: 1px solid var(--border); border-radius: 6px; padding: 1.5rem 2rem; margin-bottom: 2.5rem; }}
.toc h2 {{ font-size: 1.2rem; color: var(--primary); margin-bottom: 1rem; border: none; }}
.toc ol {{ padding-left: 1.5rem; }}
.toc li {{ margin: 0.4rem 0; }}
.toc a {{ color: var(--accent); text-decoration: none; }}
.toc a:hover {{ text-decoration: underline; }}
section {{ margin-bottom: 2.5rem; }}
h2 {{
  font-size: 1.55rem;
  color: var(--primary);
  border-left: 4px solid var(--accent);
  padding-left: 0.75rem;
  margin: 2rem 0 1rem;
}}
h3 {{ font-size: 1.25rem; color: var(--accent); margin: 1.5rem 0 0.85rem; }}
p {{ margin-bottom: 1rem; text-align: justify; }}
ul, ol {{ margin: 0.5rem 0 1rem 1.5rem; }}
li {{ margin: 0.3rem 0; }}
.abstract {{
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
}}
.abstract .kw {{ margin-top: 0.75rem; font-size: 0.9rem; color: var(--muted); }}
table {{
  width: 100%;
  border-collapse: collapse;
  margin: 1.25rem 0 1.75rem;
  font-size: 1rem;
  background: #fff;
}}
th, td {{ border: 1px solid var(--border); padding: 0.65rem 0.8rem; text-align: center; }}
th {{ background: var(--table-head); color: var(--primary); font-weight: 600; }}
td.left {{ text-align: left; }}
caption {{
  caption-side: top;
  text-align: left;
  font-weight: 600;
  color: var(--primary);
  padding: 0.5rem 0;
  font-size: 0.92rem;
}}
.figure-block {{
  margin: 2rem 0 2.5rem;
  text-align: center;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.25rem 1.25rem 1.5rem;
}}
.figure-block img {{ max-width: 100%; height: auto; display: block; margin: 0 auto; }}
.figure-block.figure-large img {{ max-width: 100%; min-height: 320px; }}
.fig-caption {{
  text-align: left;
  font-size: 1.05rem;
  color: var(--primary);
  margin-top: 1rem;
  line-height: 1.75;
  font-weight: 500;
}}
.fig-caption strong {{ color: var(--primary); font-size: 1.08rem; }}
.fig-analysis {{
  text-align: left;
  font-size: 1rem;
  color: var(--text);
  margin-top: 0.75rem;
  padding: 1rem 1.1rem;
  background: #f8fafb;
  border-left: 4px solid var(--accent);
  line-height: 1.85;
}}
.fig-analysis p {{ margin-bottom: 0.75rem; }}
.glossary {{
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.25rem 1.5rem;
  margin: 1.5rem 0 2rem;
}}
.term {{
  margin: 1.1rem 0 1.35rem;
  padding-bottom: 1rem;
  border-bottom: 1px dashed var(--border);
}}
.term:last-child {{ border-bottom: none; }}
.term-head {{ margin-bottom: 0.45rem; }}
.term-sym {{
  display: inline-block;
  font-weight: 700;
  color: var(--primary);
  margin-right: 0.6rem;
  font-size: 1.05em;
}}
.term-full {{ color: var(--accent); font-weight: 600; }}
.term-body {{ font-size: 0.98em; line-height: 1.85; text-align: justify; }}
.note {{
  background: #fff8e6;
  border: 1px solid #f0d78c;
  border-radius: 4px;
  padding: 0.75rem 1rem;
  font-size: 0.9rem;
  margin: 1rem 0;
}}
.tbd {{ color: #c0392b; font-style: italic; }}
.footer {{
  margin-top: 3rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  font-size: 0.85rem;
  color: var(--muted);
  text-align: center;
}}
@media print {{
  .cover {{ min-height: auto; page-break-after: always; }}
  body {{ font-size: 12pt; }}
  .figure-block {{ break-inside: avoid; }}
}}
</style>
</head>
<body>
<div class="container">

<div class="cover" id="cover">
  <div class="org">河流碳输运与 AI 亚网格闭合 — 科研实施报告</div>
  <h1>基于物理约束机器学习的河网 CO₂ 输运<br>亚网格参数化研究</h1>
  <div class="subtitle">East River 流域案例：真实数据驱动的多尺度过滤、可辨识性与嵌套交叉验证</div>
  <div class="meta">
    研究框架来源：Gao et al., <em>The Innovation</em>（AI cross-fusion approach for river carbon transport）<br>
    案例基准：Saccardi &amp; Winnick (2021), <em>Global Biogeochemical Cycles</em><br>
    报告类型：正式研究报告（封面 · 目录 · 摘要 · 背景 · 方法 · 过程 · 结果 · 讨论 · 结论 · 展望）<br>
    研究区域：美国科罗拉多州 East River 流域（HUC 14020001）<br>
    内嵌图表：{n_figs} 幅（精选流水线产出，base64 内嵌，无外部 CDN / 无文件路径图片）
  </div>
  <div class="date">报告生成日期：2026 年 8 月 16 日</div>
</div>

<nav class="toc" id="toc">
  <h2>目 录</h2>
  <ol>
    <li><a href="#abstract">摘要</a></li>
    <li><a href="#glossary">术语表（缩写全称与深度解释）</a></li>
    <li><a href="#background">一、研究背景与目的</a></li>
    <li><a href="#methods">二、数据与方法</a></li>
    <li><a href="#process">三、研究过程</a></li>
    <li><a href="#results">四、结果展示</a></li>
    <li><a href="#discussion">五、分析与讨论</a></li>
    <li><a href="#conclusions">六、主要结论</a></li>
    <li><a href="#outlook">七、不足与展望</a></li>
    <li><a href="#references">参考文献</a></li>
  </ol>
</nav>

<section id="abstract">
  <h2>摘要</h2>
  <div class="abstract">
    <p>本报告像一堂循序渐进的课：用美国科罗拉多州 East River 流域 2019 年 8 月战役的
    <strong>120 个真实水样</strong>（HydroShare 公开数据），检验“河网碳输运基准模型 + AI 亚网格闭合”
    这条技术路线，并把大涡模拟（LES，Large-Eddy Simulation）式空间过滤、
    亚网格源汇项 S<sub>sgs</sub> 与气体交换速度 k 的实际等效（practical equifinality）、
    以及无量纲稀疏闭合写成可计算实验。全程<strong>未使用合成观测</strong>。</p>
    <p>请先抓住主结论，再读细节：在留一河段嵌套交叉验证（nested CV / LOO-reach，n=120）下，
    基准模型（Baseline，S<sub>sgs</sub>=0）的溶解 CO₂ 浓度 C<sub>aq</sub> 均方根误差（RMSE）为
    <strong>0.0284</strong>；残差学习式 Residual-AI（多层感知机 MLP）为 <strong>0.0573</strong>（更差）；
    随机森林为 0.0745（更差）；k 修正虽把 RMSE 略降到 0.0244，却把有效气体交换速度压到经验值的约
    3.4×10<sup>−4</sup>，使模型逸散通量诊断 F<sub>CO₂</sub> 从约 3.24 塌缩到约 0.03。
    样本内 R²≈0.997 仅能进附录，属于过拟合肖像。</p>
    <p>因此本报告的叙事不是“AI 提高了精度”，而是：如何定义滤波尺度 Δx、如何证明在仅有浓度观测时
    S<sub>sgs</sub> 与 k 实践上不可联合辨识、以及如何用分层嵌套交叉验证诚实报告方法边界。
    下文每张图都附“背景—读法—子图—曲线含义—通俗结论”五段讲解；缩写首次出现时给出全称与物理来龙去脉，
    亦可随时查阅术语表。报告内嵌 {n_figs} 幅精选图。</p>
    <div class="kw"><strong>关键词：</strong>河网碳输运；CO₂ 逸散；亚网格闭合；可辨识性；LES 过滤；嵌套交叉验证；物理约束机器学习；East River；真实数据验证</div>
  </div>
</section>

<section id="glossary">
  <h2>术语表（缩写全称与深度解释）</h2>
  {glossary_html()}
</section>

<section id="background">
  <h2>一、研究背景与目的</h2>
  <h3>1.1 为什么要做这项研究？</h3>
  <p>河流像一条条“管道”，把陆地上的碳输送到湖泊和海洋，同时向大气释放 CO₂ 等温室气体。
  全球河流释放的 CO₂ 量级很大，但现有模型往往把整个河网当成一个“黑箱”，看不清河段内部的水动力、
  水质和碳过程如何在空间上变化。</p>
  <p>Gao 等（<em>The Innovation</em>）提出借鉴流体力学中“大涡模拟”的思路：大尺度上算清河水输运和
  气体交换，小尺度上未能直接算出的过程（如湍流混合、局地呼吸、地下水输入）交给 AI 来学习一个
  “亚网格闭合项” S<sub>sgs</sub>。本报告的工作，是在美国科罗拉多州 <strong>East River 真实流域</strong>上，
  把这套思路做成可运行的程序，并用 2019 年野外实测数据检验效果。</p>
  <h3>1.2 研究区域与河网结构</h3>
  <p>East River 位于 Gunnison 县，属 Upper Colorado 流域（水文单元 HUC 14020001），是 DOE 支持的
  高海拔生态水文试验流域。我们把河网自上而下划分为 <strong>8 条河段 R001–R008</strong>（见第四节表 2）：
  上游是 Bradley Creek、Rock Creek 等支流，下游汇入主河道 East River（R008）。</p>
  <p>野外采样在 <strong>2019 年 8 月 2 日至 11 日</strong>进行，共 <strong>120 个水样</strong>，每个样点有 GPS 坐标、
  pH、温度、溶解氧、pCO₂ 等实测值。数据全部来自 HydroShare 公开数据集（Saccardi &amp; Winnick, 2021），
  本项目中<strong>未使用任何合成或模拟观测数据</strong>。</p>
</section>

<section id="methods">
  <h2>二、数据与方法</h2>
  <h3>2.1 数据来源</h3>
  <table>
    <caption>表 1 数据来源与使用状态汇总</caption>
    <thead>
      <tr><th>数据类型</th><th>来源</th><th>状态</th><th>用途</th></tr>
    </thead>
    <tbody>
      <tr><td class="left">野外水化学与 pCO₂</td><td class="left">HydroShare 9f907b46…</td><td>已下载</td><td class="left">120 样点</td></tr>
      <tr><td class="left">河网几何与坡度</td><td class="left">East_River_Lines.shp + stream_reach.csv</td><td>已下载</td><td class="left">393 NHD 线段</td></tr>
      <tr><td class="left">干流流量</td><td class="left">USGS 09112500</td><td>已下载</td><td class="left">样点日期日流量</td></tr>
      <tr><td class="left">支流流量</td><td class="left">Q elivation regreshion.csv 同步 Q</td><td>已用战役期公开值</td><td class="left">无支流日过程，<span class="tbd">待补充测站</span></td></tr>
      <tr><td class="left">NHDPlus HR HUC 14020001</td><td class="left">USGS staged GPKG / ArcGIS</td><td>见 REAL_DATA_AUDIT</td><td class="left">河线命名与 VAA</td></tr>
      <tr><td class="left">StreamPULSE</td><td class="left">data.streampulse.org</td><td>无 East River / Gothic / Coal Creek 站点</td><td class="left">未下载时间序列</td></tr>
      <tr><td class="left">CONUS_carbon 仓库</td><td class="left">GitHub Fluvial-UMass/CONUS_carbon</td><td>已克隆结构；输入栅格不在该仓</td><td class="left">结构对照，非第二场采样</td></tr>
      <tr><td class="left">碱度、营养盐、PAR</td><td class="left">—</td><td>缺失</td><td class="left">保持 NaN，<span class="tbd">待补充</span></td></tr>
    </tbody>
  </table>
  <h3>2.2 流场可视化方法</h3>
  <div class="note">
    <strong>平面 quiver：</strong>箭头方向由 NHD 线段链距拓扑（R001→R008 下游序）确定；颜色/长度 ∝ Q 或 u（河段战役均值）。<br>
    <strong>streamtube：</strong>线宽 ∝ Q，颜色 ∝ u，基于真实 LineString 几何。<br>
    <strong>2D 断面 u(y,z)：</strong>理想化梯形（边坡 1:1），u(z)=1.5ū(2ζ−ζ²)，W/h 来自 Manning 估算——非 ADCP 实测，标注<strong>待补充</strong>处需未来断面数据。
  </div>
  <h3>2.3 数据完整性政策</h3>
  <div class="note">
    <strong>真实数据唯一原则：</strong>data_policy.real_data_only: true；allow_synthetic_fallback: false。
    嵌套交叉验证是论文主指标；样本内 R² 仅作附录。NHD 河段映射：GNIS 优先，其余按最近战役 GPS 样点分配。
  </div>
</section>

<section id="process">
  <h2>三、研究过程</h2>
  <p>十五阶段流水线（run_pipeline.py）：数据获取 → 河网构建 → 基准输运 → 气体交换 → 残差 → 模型训练 → 耦合预测 → 验证 → 空间—时间图 → GIS 矢量河网 + quiver → 2D 断面与中心线捕捉 → <strong>嵌套交叉验证输运消融</strong>（12）→ <strong>滤波尺度 S<sub>sgs</sub></strong>（13）→ <strong>k–S 可辨识性</strong>（14）→ <strong>无量纲稀疏闭合</strong>（15）。</p>
</section>

<section id="results">
  <h2>四、结果展示</h2>
  {READING_GUIDE_HTML}
  <h3>4.0 河网结构：先弄清“哪一段是哪条河”</h3>
  {REACH_NETWORK_TABLE_HTML}
  <h3>4.0b 样本与模型性能概览</h3>
  <table>
    <caption>表 3 验证数据集基本统计</caption>
    <thead><tr><th>指标</th><th>数值</th></tr></thead>
    <tbody>
      <tr><td class="left">有效样点数 n</td><td>120（真实战役样点，无合成）</td></tr>
      <tr><td class="left">河段数</td><td>8（R001–R008）；干流 R008 n=58；单样本河段 R001/R006/R007</td></tr>
      <tr><td class="left">论文主指标</td><td>嵌套 CV 持出样本的 C<sub>aq</sub> / F<sub>CO₂</sub>（表 4）</td></tr>
      <tr><td class="left">采样日期</td><td>2019-08-02 至 2019-08-11（10 天）</td></tr>
      <tr><td class="left">报告内嵌图数</td><td>{n_figs}（精选，含嵌套 CV 与论文创新实验图）</td></tr>
    </tbody>
  </table>
{nested_tables}
{innovation_tables}

{figure_html}
</section>

<section id="discussion">
  <h2>五、分析与讨论</h2>
  <h3>5.1 河网图到底在说什么？</h3>
  <p>读者最容易困惑的是“R001–R008 和地图上弯弯曲曲的河线是什么关系”。简言之：
  <strong>表 2 的 8 行是研究者按流域功能划分的 8 段“逻辑河段”</strong>；<strong>图 1 的 393 条彩色细线是国家标准 NHD 河道矢量</strong>。
  一条逻辑河段往往对应多条 NHD 线段。干流 East River（R008）样点最多，所以碳通量、模型验证的结论主要由 R008 驱动。
  支流样点很少（有的河只有 1 个点），对这些河的结论只能谨慎表述。</p>
  <h3>5.2 水动力与 2D 断面示意</h3>
  <p>平面 quiver 图（图 3–4）用箭头示意水往哪里流、流量/流速有多大，数值来自 USGS 干流测站与文献回归，
  不是每个支流都有独立测站。断面 u(y,z) 图（图 9）在缺少实测地形断面时，用梯形槽假设和经典流速分布公式画出示意图，
  目的是帮助理解“河水在断面内如何分布”，<strong>不能当作现场 ADCP 测量结果</strong>。</p>
  <h3>5.3 Baseline 与 AI：嵌套交叉验证怎么说？</h3>
  <p>Baseline 只用传统水动力 + 气体交换公式，不显式包含地下水 CO₂、局地有机质分解等过程。
  Residual-AI 学习的是 Baseline “算不准的那一块”（S<sub>sgs</sub>）；k 修正则试图用可变气体交换系数吸收同样的残差。
  样本内可以把浓度贴回观测（附录 R² 很高），但那是同一批 120 个点既训练又预测。
  <strong>主文只看表 4 的持出样本 C<sub>aq</sub> / F<sub>CO₂</sub>。</strong>
  本次结果：Residual-AI 的持出 C RMSE <strong>高于</strong> Baseline（未能推广）；
  k 修正把 C RMSE 略降，但靠的是把 k 压得很小、模型通量诊断 F<sub>CO₂</sub> 合计接近 0——这不是成功的通量闭合。
  没有一种方案在持出样本上同时改进浓度与物理一致的逸散通量诊断。</p>
  <h3>5.3b 滤波、可辨识性与无量纲式说明了什么？</h3>
  <p>把 NHDPlus HR 廊道线段粗化后，质量守恒残差的幅度与方差随 Δx 增大而下降：细网格上局地平流不匹配更尖锐，
  粗网格把它平均掉。这支持把嵌套 CV 失败读成“当前观测尺度下闭合难以推广 / 与参数化权衡纠缠”，而不是“MLP 没调好”。</p>
  <p>可辨识性图把同一套持出预测写成 k<sub>eff</sub> 与隐含 S<sub>sgs</sub> 的权衡：
  k<sub>eff</sub>/k<sub>emp</sub> 中位数约 3×10<sup>−4</sup>，浓度略好、通量诊断崩溃。
  在<strong>仅有浓度观测</strong>时，这是 <strong>practical equifinality</strong>（实践上的参数等价），
  不是已证明的形式化结构不可辨识；也没有独立通量告诉我们哪一个 F 正确。
  Residual-AI 保持经验 k，但持出 S<sub>sgs</sub> 并不能替代这条隐含源项。</p>
  <p>无量纲 LASSO 给出以 Fr、Slope、h/W 为主的可解释式（log Re / log Da 被稀疏掉或极弱）。
  该式代入输运后的持出 C RMSE 仍高于 Baseline。论文贡献是形式与协议，不是精度。</p>
  <h3>5.4 数据与方法的诚实限制</h3>
  <ul>
    <li>仅 10 天战役观测，无法代表全年；融雪期、枯水期<strong>待补充</strong>。</li>
    <li>支流流量取公开同步 Q，没有支流日过程测站。</li>
    <li>未命名 NHD 线段改按最近 GPS 样点分配，仍可能错分无名支流。</li>
    <li>DIC/DOC 仅部分样点有值；碱度、营养盐未观测，未做任何插补。</li>
    <li>StreamPULSE 门户无 East River / Gothic / Coal Creek 站点，未并入代谢时间序列。</li>
    <li>单样本河段（R001、R006、R007）只作示意，不与 R008 的 58 个点均等权重。</li>
  </ul>
</section>

<section id="conclusions">
  <h2>六、主要结论</h2>
  <ol>
    <li>论文主指标是嵌套交叉验证下的 C<sub>aq</sub> 与模型通量诊断 F<sub>CO₂</sub>；Residual-AI <strong>没有</strong>优于 Baseline（MLP RMSE 0.0573 vs Baseline 0.0284；RF 0.0745）。</li>
    <li>k 修正略降浓度误差（0.0244），但通过把 k<sub>eff</sub>/k<sub>emp</sub> 压到约 3.4×10<sup>−4</sup> 使通量诊断从约 3.24 崩溃到约 0.03——在仅有浓度观测时 S<sub>sgs</sub> 与 k 存在 practical equifinality。</li>
    <li>LES 式多 Δx 过滤给出 East River 廊道残差随尺度变化的经验诊断（mean |S|：1.92→1.00；研究河段有样点单元=6；非普适律）；无量纲稀疏式以 Fr / Slope / h/W 为主，形式可解释、持出预测弱（C RMSE≈0.051）。</li>
    <li>干流 R008（n=58）与多样本支流分开报告；单样本河段仅作示意；样本内 R²≈0.997 只作附录。</li>
  </ol>
</section>

<section id="outlook">
  <h2>七、不足与展望</h2>
  <p>CH₄ / GRiMeDB、StreamPULSE <strong>其他</strong>流域、CONUS 产品对照、单河段 TELEMAC、PINN Saint-Venant 均属论文之后的拓展，不进入本篇主创新。
  已克隆 Fluvial-UMass/CONUS_carbon 仓库结构（查找表，无大陆输入栅格），仅作结构对照，<strong>不是</strong>第二场 East River 野外战役。
  StreamPULSE East River 仍为 0 站点，不重试为主路径。符号回归在 PySINDy 安装失败后改用 LASSO。
  当前 GIS 底图为本地地形渐变，非卫星瓦片。WQP 同日合并仍为 0/120。</p>
</section>

<section id="references">
  <h2>参考文献</h2>
  <ol style="font-size:0.88rem;">
    <li>Gao Y., et al. AI cross-fusion approach for river carbon transport. <em>The Innovation</em>.</li>
    <li>Saccardi B., Winnick M.J. Improving predictions of stream CO₂. <em>Global Biogeochemical Cycles</em>, 2021.</li>
    <li>Raymond P.A., et al. Scaling gas transfer velocity. <em>Nature Geoscience</em>, 2012.</li>
    <li>Yuval J., O’Gorman P.A. Stable machine-learning parameterization of subgrid processes. <em>Nature Communications</em>, 2020.</li>
    <li>Battin T.J., et al. River ecosystem metabolism and carbon biogeochemistry. <em>Nature</em>, 2023.</li>
  </ol>
</section>

<div class="footer">
  本报告由河流碳输运 AI 亚网格项目自动生成 · 数据审计见 REAL_DATA_AUDIT.md · {n_figs} 幅精选图 base64 内嵌 · 无外部 CDN
  · Residual-AI 未优于 Baseline（诚实负结果贯穿全文）
  {f" · 缺失图：{', '.join(missing)}" if missing else ""}
</div>

</div>
</body>
</html>"""

    OUT_HTML.write_text(html, encoding="utf-8")
    size_mb = OUT_HTML.stat().st_size / 1024 / 1024
    print(f"HTML: {OUT_HTML} ({size_mb:.2f} MB, {n_figs} figures)")
    if missing:
        print(f"  Missing from manifest: {missing}")

    md = f"""# East River CO₂ 河网碳输运 — 真实数据验证报告

**报告日期：** 2026 年 8 月 16 日  
**内嵌图表：** {n_figs} 幅（精选，见 report.html；每图附五段教学讲解）  
**阅读建议：** 术语表 → 表 2（8 条河段）→ 表 M / 表 4 与嵌套 CV 图 N1–N4（论文主指标）→ 滤波 / 可辨识性 / 无量纲式 → 附录样本内散点（乐观，勿当结论）

## 摘要

本报告用美国 East River 流域 2019 年 8 月 **120 个真实野外水样**，检验河网 CO₂ 输运基准模型、AI 亚网格闭合、LES 滤波尺度与 k–S practical equifinality。
嵌套 CV 显示 Residual-AI **没有**优于 Baseline（C RMSE 0.0573 vs 0.0284；RF 0.0745）。k 修正略降到 0.0244 但通量从 ~3.24 塌到 ~0.03。全文加大字号；数据来自 HydroShare，未使用合成观测。

## 河网 8 段（上游→下游）

| 编号 | 河流 | 下游 | 样点数 |
|------|------|------|--------|
| R001 | Bradley Creek | R002 | 1（示意） |
| R002 | Bradley Meadow | R003 | 3 |
| R003 | Rock Creek | R004 | 15 |
| R004 | Copper Creek | R005 | 24 |
| R005 | Gothic Creek | R006 | 17 |
| R006 | Quigley Creek | R007 | 1（示意） |
| R007 | Rustlers Gulch | R008 | 1（示意） |
| R008 | East River 干流 | — | 58 |

## 图表清单（精选 {n_figs} 幅）

"""
    for fname, caption, section, _ in FIGURE_MANIFEST:
        if (FIG_DIR / fname).exists():
            plain = caption.replace("<strong>", "**").replace("</strong>", "**")
            plain = plain.replace("<sub>", "").replace("</sub>", "")
            md += f"- [{section}] `{fname}` — {plain}\n"

    md += """
## 已移除

- `network_map_*.png` — reach 质心散点图（由 GIS 线图 + quiver 替代）

## 数据限制

- 战役 10 天（无全年季节覆盖）
- GNIS 85/393 + 最近 GPS 样点分配（非质心回退）
- DIC/DOC 41/120 非空；Alk/N/P 缺失；WQP 同日合并 0/120
- 支流 Q 为公开同步值（无日过程；无 gage-ratio 虚构过程线）
- F_CO₂ 为模型通量诊断/代理，非腔室验证
- Residual-AI 嵌套 CV 未优于 Baseline；勿声称精度胜利

*完整自包含 HTML：report.html*  
*架构冻结：docs/ENGINEERING_NOTES.md；论文主表：results/tables/paper_main_results.csv*
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(f"MD: {OUT_MD} ({OUT_MD.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
