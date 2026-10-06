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
    REACH_NOTES_ZH,
    SECTION_INTROS,
    load_table1,
    reach_network_table_html,
)
from report_shared import glossary_html  # noqa: E402

FIG_DIR = ROOT / "results" / "figures"
OUT_HTML = ROOT / "report.html"
OUT_MD = ROOT / "report.md"
TABLES = ROOT / "results" / "tables"
# TODO(P2-09): this run id is hard-coded and is what the documents print;
# run_pipeline.py --run-id only tags runs/<run_id>/ and does NOT feed this
# constant. See docs/PIPELINE_AND_REGENERATION.md before changing either.
RUN_ID = "20260919_remediation"


def _report_date_zh() -> str:
    """Report date, derived from the frozen run's artifact manifest.

    Keeping this dynamic (rather than a hand-typed literal) prevents the report
    from advertising an older generation date than the tables/figures it embeds
    (2026-09-27 review, P0-01 single source of truth).
    """
    import datetime as _dt
    import json

    manifest = TABLES / "artifact_manifest.json"
    if manifest.exists():
        try:
            stamp = json.loads(manifest.read_text(encoding="utf-8")).get("generated_at_utc")
            if stamp:
                dt = _dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
                dt = dt.astimezone(_dt.timezone(_dt.timedelta(hours=8)))
                return f"{dt.year} 年 {dt.month} 月 {dt.day} 日"
        except Exception:  # noqa: BLE001 - fall back to today, never crash the build
            pass
    today = _dt.date.today()
    return f"{today.year} 年 {today.month} 月 {today.day} 日"


REPORT_DATE_ZH = _report_date_zh()


def load_frozen_report_metrics() -> dict:
    """Load OOF metrics from the frozen run (single source: paper_values.json).

    The Chinese report must not carry its own copies of the headline numbers;
    it reads the same ``results/tables/paper_values.json`` object the paper
    consumes, so report and paper cannot drift apart.
    """
    import json

    import pandas as pd

    out: dict = {
        "run_id": RUN_ID,
        "baseline_rmse": None,
        "mlp_rmse": None,
        "rf_rmse": None,
        "kcorr_rmse": None,
        "baseline_flux": None,
        "mlp_flux": None,
        "rf_flux": None,
        "kcorr_flux": None,
        "k_infeasible_frac": None,
        "eq_rmse_lo": None,
        "eq_rmse_hi": None,
        "q_a_median": None,
        "filter_scales": "native / 2\u00d7 / 4\u00d7",
        "study_reach_excluded": True,
        "sparse_rmse": None,
        "sparse_r2": None,
        "n_campaign": None,
        "constraint_active": None,
        "n_oof_rows": None,
        "r002_gain_frac": None,
        "per_reach_paired": [],
        "subgroup_mlp_mainstem_rmse": None,
        "subgroup_mlp_tributary_rmse": None,
        "subgroup_baseline_mainstem_rmse": None,
        "subgroup_baseline_tributary_rmse": None,
        "subgroup_rf_mainstem_rmse": None,
        "subgroup_rf_tributary_rmse": None,
        "k_eff_median": None,
        "k_emp_median": None,
        "kcorr_ratio_display": None,
        "runner_up": None,
    }
    pv_p = TABLES / "paper_values.json"
    if pv_p.exists():
        pv = json.loads(pv_p.read_text(encoding="utf-8"))
        mr = pv.get("main_results", {})
        out["baseline_rmse"] = mr.get("baseline", {}).get("rmse_c")
        out["mlp_rmse"] = mr.get("mlp", {}).get("rmse_c")
        out["rf_rmse"] = mr.get("random_forest", {}).get("rmse_c")
        out["kcorr_rmse"] = mr.get("k_correction", {}).get("rmse_c")
        fe = pv.get("flux_estimand", {})
        out["baseline_flux"] = fe.get("baseline_area_sum")
        out["mlp_flux"] = fe.get("mlp_area_sum")
        out["rf_flux"] = fe.get("rf_area_sum")
        out["kcorr_flux"] = fe.get("kcorr_area_sum")
        ke = pv.get("k_estimate", {})
        out["k_infeasible_frac"] = ke.get("infeasible_frac_full_data")
        ksum = ke.get("k_estimate_summary") or {}
        if ksum.get("k_correction_median") is not None:
            out["k_correction_median"] = float(ksum["k_correction_median"])
        eq = pv.get("equifinality", {})
        rng = eq.get("profile_rmse_range") or [None, None]
        out["eq_rmse_lo"], out["eq_rmse_hi"] = rng[0], rng[1]
        out["q_a_median"] = eq.get("q_A_median_m_d")
        out["sparse_rmse"] = pv.get("sparse", {}).get("transport_rmse_c")
        out["sparse_r2"] = pv.get("sparse", {}).get("Sstar_r2")
        out["n_campaign"] = pv.get("counting", {}).get("n_campaign_samples")
        cd = pv.get("constraint_diagnostics", {})
        out["constraint_active"] = cd.get("n_constraint_active")
        out["n_oof_rows"] = cd.get("n_oof_rows")
        sens = pv.get("reach_sensitivity", {})
        out["r002_gain_frac"] = sens.get("r002_gain_contribution_frac")
        sg = pv.get("subgroups", {})
        out["subgroup_mlp_mainstem_rmse"] = sg.get("mlp_mainstem_rmse")
        out["subgroup_mlp_tributary_rmse"] = sg.get("mlp_tributary_rmse")
        out["subgroup_baseline_mainstem_rmse"] = sg.get("baseline_mainstem_rmse")
        out["subgroup_baseline_tributary_rmse"] = sg.get("baseline_tributary_rmse")
        out["subgroup_rf_mainstem_rmse"] = sg.get("rf_mainstem_rmse")
        out["subgroup_rf_tributary_rmse"] = sg.get("rf_tributary_rmse")
        ke2 = pv.get("k_estimate", {})
        out["k_eff_median"] = ke2.get("k_eff_median_m_d")
        out["k_emp_median"] = ke2.get("k_emp_median_m_d")
        out["kcorr_ratio_display"] = ke2.get("k_ratio_median_display")
        out["per_reach_paired"] = pv.get("per_reach_paired") or []
        out["pooled_rmse_mlp_drop_R002"] = sens.get("pooled_rmse_mlp_drop_R002")
        out["pooled_rmse_baseline_drop_R002"] = sens.get("pooled_rmse_baseline_drop_R002")
    fs_sum = TABLES / "filter_scale_summary.json"
    if fs_sum.exists():
        fs = json.loads(fs_sum.read_text(encoding="utf-8"))
        ids = [s["scale_id"] for s in fs.get("scales", [])]
        out["filter_scales"] = " / ".join(ids) if ids else out["filter_scales"]
        out["study_reach_excluded"] = any(
            e.get("scale_id") == "study_reach" for e in fs.get("excluded_scales", [])
        )
    return out

# ---------------------------------------------------------------------------
# Figure set parity with the paper (Part C).
#
# The paper numbers exactly ten figures by first mention.  The Chinese report
# carries a much larger teaching atlas, so it is split into two clearly
# separated sequences:
#
#   * 图 1–10  — the ten paper figures, in the paper's own order and with the
#                paper's own estimands, so any ``图 N`` in this report means the
#                same object as ``Figure N`` in the manuscript.
#   * 附录图 A1… — the remaining teaching figures, renumbered and never
#                referred to as ``图 N``.
#
# Nothing is dropped: this only changes numbering and order, never content.
# ---------------------------------------------------------------------------

PAPER_FIGURE_ORDER: list[tuple[str, str, str]] = [
    # (filename, chinese caption, source note)
    (
        "les_filter_conceptual.png",
        "<strong>图 1</strong> 单元 DAG 算子两条聚合规则的并排示意："
        "（a）同一河道上的串行收缩，Q 沿链恒定、ΣQC 沿链累加而非重新平均；"
        "（b）汇流口的并行汇合，Q<sub>out</sub>=Q<sub>1</sub>+Q<sub>2</sub>、"
        "C<sub>out</sub> 按流量加权（非算术平均），面积相加、同一单元内重复观测不增加面积。"
        "两幅均为<strong>示意、非按比例</strong>，仅陈述算子规则，<strong>不作为</strong>某次运行已实现守恒的证据。",
        "与论文 Figure 1 同源",
    ),
    (
        "figure2_reach_assignment_and_samples.png",
        "<strong>图 2</strong> （a）逻辑河段指派：NHDPlus HR 河线按 GNIS 名称匹配与" "样点邻近度归入 R001–R008（R001 在本渲染中无指派线段）；"
        "（b）120 个战役样点在同一位底图上的位置，颜色表示逻辑河段，R008 有 58 点。"
        "细箭头仅表示数字化流向，故本图是<strong>位置参照</strong>、<strong>不是</strong>流向有效性检验。"
        "两幅均为 Web Mercator（EPSG:3857），含比例尺与指北针；底图为 Esri World Imagery 卫星瓦片，"
        "瓦片本地缓存并记录来源与哈希（见图旁 JSON 清单）。",
        "与论文 Figure 2 同源",
    ),
    (
        "nested_cv_rmse_bar.png",
        "<strong>图 3</strong> 分组留一河段 + 输运耦合交叉验证（120 样点、8 个河段组、固定随机种子）："
        "Baseline、Residual-AI（MLP / random forest）与 k 修正的持出 C<sub>aq</sub> RMSE。"
        "实心柱为按样点加权的合并指标，空心标记为背后的各河段值，可对照河段离散度阅读；"
        "虚线为 Baseline 水平。没有任何闭合把合并 RMSE 降到零残差 Baseline 之下。",
        "与论文 Figure 3 同源",
    ),
    (
        "nested_cv_scatter_holdout.png",
        "<strong>图 4</strong> 留一河段分组评估下 Residual-AI（MLP）的观测 vs 输运预测持出 C<sub>aq</sub>（n=120）；"
        "颜色表示逻辑河段，虚线为 1:1。统计量由这些点直接计算，键可追溯至 "
        "`data_proc/nested_cv_holdout_predictions.csv`。内嵌小图放大低浓度区间（多数干流样点所在）；"
        "极端点保留、不作剔除。本冻结运行中 480 行持出预测<strong>全部</strong>未激活 S<sub>sgs</sub> 物理下界，"
        "故残差闭合不含裁剪后处理；若该计数非零将显式报告。",
        "与论文 Figure 4 同源",
    ),
    (
        "subgroup_rmse_r008_vs_trib.png",
        "<strong>图 5</strong> 子组 C<sub>aq</sub> RMSE：Baseline、Residual-AI（MLP 与 random forest）与 k 修正。"
        "R008 含 58 个样点；多样本支流组 R002–R005 含 59 个样点；R001、R006、R007 为单样本逻辑河段，"
        "单独展示而不并入比较。",
        "与论文 Figure 5 同源",
    ),
    (
        "supp_flux_diagnostics.png",
        "<strong>图 6</strong> 分组留一河段评估下 Baseline、Residual-AI（MLP）与 k 修正的模型 F<sub>CO₂</sub> 诊断。"
        "（a）面积加权模型通量诊断 ΣF·A（mol d<sup>−1</sup>），与表 2 同一估计量，故二者一致；"
        "（b）该诊断的各河段构成，显示残差闭合总量集中在少数河段；"
        "（c）样点级 k<sub>eff</sub>/k<sub>emp</sub> 与 k 修正模型通量诊断的关系。"
        "这些量是 k(C−C<sub>eq</sub>) 形式的<strong>模型诊断</strong>，既非研究区总量、也非独立验证的逸散观测；"
        "面板（a）背后的未面积加权密度和在补充表中保留。",
        "与论文 Figure 6 同源",
    ),
    (
        "filter_scale_sgs.png",
        "<strong>图 7</strong> 仅限已解析尺度（native 至 16× 合并；study_reach 因整河段收缩形成 DAG 环而排除）的"
        "滤波尺度依赖。上panel：唯一单元平均与中位 |S<sub>sgs</sub>| 对滤波尺度 Δx（对数轴），并标出实际平均与中位控制长度；"
        "下panel：S<sub>sgs</sub> 的单元级方差，次轴为中位控制长度。八个已解析尺度上（Δx ≈ 587–1615 m）"
        "唯一单元平均 |S| 稳定在 3.54–3.84 mol m<sup>−2</sup> d<sup>−1</sup> 的窄带内；"
        "这是稀疏同步覆盖下守恒算子的<strong>采样条件敏感性</strong>，不是经 study_reach 聚合的尺度不变性主张。",
        "与论文 Figure 7 同源",
    ),
    (
        "filter_scale_sgs_box.png",
        "<strong>图 8</strong> 日期×单元记录层级上、各已解析滤波尺度（native 至 16× 合并）的 |S<sub>sgs</sub>| 分布，"
        "每组上方标注记录数。散点已展示全部点，故不再显示 flier；多样本日期-单元记录不是独立抽样，"
        "同一单元内重复观测不增加面积。study_reach 聚合因与图 7 相同的收缩环原因排除。"
        "日期×单元记录数（native 的 43 至最粗尺度的 27）与唯一空间单元数（39 至 22）不同，"
        "因为同一单元可在多日内被采样。",
        "与论文 Figure 8 同源",
    ),
    (
        "dimensionless_coefficients.png",
        "<strong>图 9</strong> 稀疏无量纲闭合的标准化 LASSO 系数，目标在折内重建"
        "（五个候选 Π 项保留四个；仅 log₁₀(Re) 收缩至零）。系数数值为零的项画成<strong>显式零柱</strong>而非省略，"
        "便于读者看到哪些候选被丢弃及其原因。所示关系为 "
        "S* ≈ 1.386 − 4.777·Fr_z − 0.6142·Slope_z − 2.295·(h/W)_z − 2.75·log10(Da)_z。"
        "S* 的留一河段 R² 为 −2.58334（n=120）；稀疏分支仍为<strong>临时性</strong>结论。",
        "与论文 Figure 9 同源",
    ),
    (
        "equifinality_objective_surface.png",
        "<strong>图 10</strong> 准稳态平衡的模型无关实践等终性诊断（n=120）。这是条件模型诊断："
        "目标函数在所有样点间共享单一 k 尺度与单一源项，并固定观测上游状态。"
        "（a）单个代表性样点的单样本目标函数 log₁₀ J(k, S)；深红线为精确零谷 "
        "S = S_diag + (C_obs − C_eq)(k − k_emp)，故单一浓度观测使 (k, S) 代数上欠定。"
        "（b）在均匀 k 尺度 α = k/k_emp 与均匀源项 S 上的合并目标函数 J(α, S)；"
        "Baseline、k 修正与 Residual-AI 点为描述性中位标记，仅用于定位，非拟合的河网运行点。"
        "（c）轮廓 SSE J_prof(α) = min_S J(α, S)；轮廓平坦，最小值在 α ≈ 0.1795 附近"
        "（轮廓 RMSE 0.0343 mol m<sup>−3</sup>）。",
        "与论文 Figure 10 同源",
    ),
]

PAPER_FIGURE_FILES = [f for f, _, _ in PAPER_FIGURE_ORDER]


def _strip_fig_prefix(caption: str) -> str:
    """Remove a leading ``<strong>图 ...</strong>`` token from a manifest caption."""
    import re

    return re.sub(r"^\s*<strong>图[^<]*</strong>\s*", "", caption, count=1)


# Curated teaching manifest in narrative order — no point-centroid network_map_*.
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
        "白边圆点标记样点位置，灰色线为 NHD 中心线，底色为本地地形渐变（此附录图仍不使用 CDN 瓦片；"
        "带卫星底图的论文图 2 见 4.8 节）。</p>",
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
        "<strong>图 N1</strong> 分组 LOO-reach 交叉验证：Baseline / Residual-AI / k 修正的持出样本 C<sub>aq</sub> RMSE（论文主图）。",
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
        "<p>箱线显示中位数与四分位，散点为单个样点。干流高残差点会拉高均值；读图时与表 4 的分组 LOO-reach 一起看，"
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


_M_CACHE: dict | None = None


def _m() -> dict:
    """Process-wide cached frozen-metric object (single numeric source of truth)."""
    global _M_CACHE
    if _M_CACHE is None:
        _M_CACHE = load_frozen_report_metrics()
    return _M_CACHE


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
            f"<td>{_fmt(r.get('flux_area_sum_mol_d'), 0)}</td>"
            f"<td>{_fmt(k_ratio, 5) if k_ratio == k_ratio else '—'}</td>"
            f"<td>{beat_s}</td>"
            f"<td class=\"left\">{r.get('notes','')}</td>"
            "</tr>"
        )
    M = _m()
    return f"""
  <table>
    <caption>表 M 论文主结果一览（分组留一河段；F 为重叠样点面积通量诊断，非研究区总量 / 非腔室验证）</caption>
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
  <p class="lead">表 M 由冻结 run 的分组留一河段 CV / claim-guard 汇总；数字与表 4 一致。
  MLP 浓度 RMSE 为 {_fmt(M['mlp_rmse'])}，<strong>高于</strong> Baseline 的 {_fmt(M['baseline_rmse'])}，
  随机森林 {_fmt(M['rf_rmse'])} 更高；样点支撑通量诊断在残差闭合下出现数量级放大，
  因此<strong>不构成预测成功主张</strong>。k 修正未优于 Baseline；通量列为样点支撑诊断。</p>
"""


def nested_cv_tables_html() -> str:
    """Main paper tables from nested_cv_metrics.csv / subgroup_metrics.csv."""
    import pandas as pd

    nested_p = ROOT / "results" / "tables" / "nested_cv_metrics.csv"
    sub_p = ROOT / "results" / "tables" / "subgroup_metrics.csv"
    if not nested_p.exists():
        return "<p class=\"tbd\">分组留一河段交叉验证表尚未生成（待补充）。</p>"

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
            f"<td>{_fmt(r.get('flux_area_sum_mol_d'), 0)}</td>"
            f"<td>{int(r.get('n', 0))}</td>"
            "</tr>"
        )
    table_m = paper_main_table_html()
    table4 = f"""
  <table>
    <caption>表 4 分组留一河段交叉验证 — 持出 C<sub>aq</sub> 与样点支撑 F<sub>CO₂</sub> 诊断（论文主指标）</caption>
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
    if appendix.empty:
        table_app = """
  <table>
    <caption>表 4b 样本内指标（乐观附录，非论文主结论）</caption>
    <thead><tr><th>模型</th><th>C RMSE</th><th>C Bias</th><th>C R²</th><th>n</th></tr></thead>
    <tbody>
<tr><td colspan="5" class="left">Not reported. After recalculation the paper metric is exclusively
leave-one-reach-out transport-coupled C<sub>aq</sub>; in-sample concentration skill is omitted.</td></tr>
    </tbody>
  </table>
"""
    else:
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
{''.join(arows)}
    </tbody>
  </table>
"""
    sub_html = ""
    if sub_p.exists():
        sub = pd.read_csv(sub_p)
        sub = sub[
            (sub["cv_protocol"] == "loo_reach")
            & (sub["model"].isin(["none", "mlp", "xgboost"]))
            & (sub["subgroup"].isin(["all_120", "R008_only", "multi_sample_tributaries",
                                     "one_sample_reaches_schematic"]))
        ]
        srows = []
        for _, r in sub.iterrows():
            srows.append(
                "<tr>"
                f"<td class=\"left\">{r.get('scheme','')}</td>"
                f"<td class=\"left\">{r.get('subgroup_label', r.get('subgroup',''))}</td>"
                f"<td>{r.get('evidence_weight','')}</td>"
                f"<td>{_fmt(r.get('rmse_c'))}</td>"
                f"<td>{'—' if (r.get('evidence_weight') == 'schematic' or (isinstance(r.get('r2_c'), float) and abs(float(r.get('r2_c'))) > 5)) else _fmt(r.get('r2_c'), 3)}</td>"
                f"<td>{int(r.get('n', 0))}</td>"
                "</tr>"
            )
        sub_html = f"""
  <table>
    <caption>表 5 子组分组留一河段交叉验证（留一河段 C<sub>aq</sub>）— 干流与支流不等权重</caption>
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
        src = str(fs["lattice_source"].iloc[0]) if "lattice_source" in fs.columns and len(fs) else ""
        # Drop study_reach / unresolved rows from formal table if present
        fs_show = fs[~fs["scale_id"].astype(str).str.contains("study_reach|unresolved", case=False, regex=True)].copy()
        rows = []
        for _, r in fs_show.iterrows():
            rows.append(
                "<tr>"
                f"<td class=\"left\">{r.get('dx_label', r.get('scale_id',''))}</td>"
                f"<td>{_fmt(r.get('dx_m'), 0)}</td>"
                f"<td>{int(r.get('n_cells_total', 0))}</td>"
                f"<td>{int(r.get('n_cells_with_samples', 0))}</td>"
                f"<td>{int(r.get('n_samples', 0))}</td>"
                f"<td>{_fmt(r.get('cell_mean_abs_S_sgs'), 3)}</td>"
                f"<td>{_fmt(r.get('cell_var_S_sgs'), 3)}</td>"
                "</tr>"
            )
        parts.append(
            f"""
  <table>
    <caption>表 6 滤波尺度实验（正式尺度；{src}）</caption>
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
  <p class="lead">仅报告已解析尺度（native / 2× / 4×）。<strong>study_reach 已排除</strong>：
  全边保留的河段级收缩出现环，不作“到研究河段尺度仍近似不变”的声称。
  曲线为采样条件敏感性，不是普适 SGS 定律，也不证明“真实未解析过程”。</p>
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
    <caption>表 7 可辨识性：同一分组 LOO-reach 持出协议下 k 与 S<sub>sgs</sub> 的权衡</caption>
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
    <caption>表 8b 无量纲稀疏式代入输运后的分组 CV（对照表 4 的 Baseline {_fmt(_m().get('baseline_rmse'))}）</caption>
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


def _figure_block(fname: str, caption: str, analysis: str) -> str:
    data = b64_img(fname)
    if not data:
        return ""
    large_cls = (
        " figure-large"
        if (
            "scatter" in fname
            or "nested_cv" in fname
            or "identifiability" in fname
            or "filter_scale" in fname
        )
        else ""
    )
    return f"""  <div class="figure-block{large_cls}">
    <img src="data:image/png;base64,{data}" alt="{fname}">
    <div class="fig-caption">{caption}</div>
    <div class="fig-analysis">{analysis}</div>
  </div>"""


_METRIC_TOKEN = __import__("re").compile(r"<<([A-Za-z0-9_]+)>>")


def resolve_metric_tokens(html: str) -> str:
    """Replace ``<<metric_key>>`` tokens with frozen values (Part C).

    Teaching notes name headline numbers, but a literal copy would drift the
    moment the frozen run is rebuilt.  Tokens are resolved from the same
    ``paper_values.json`` object the manuscript consumes.  A token that cannot
    be resolved is left intact so the gap is visible in the rendered report
    instead of being silently rendered as ``0`` or ``1.00``.
    """
    M = _m()

    def _sub(m):
        key = m.group(1)
        if key in M and M[key] is not None:
            return _fmt(M[key])
        return m.group(0)

    return _METRIC_TOKEN.sub(_sub, html)


def build_figure_sections() -> tuple[str, str, list[str]]:
    """Return (paper-figure HTML, appendix-figure HTML, embedded filenames).

    Part C requires the Chinese report to carry the *same* ten numbered figures
    in the *same* order as the manuscript, so that ``图 N`` here is the same
    object as ``Figure N`` in the paper.  Everything else is kept, but moved
    into a clearly separated appendix sequence (``附录图 A1`` …) so no two
    different pictures ever share a number.
    """
    embedded: list[str] = []

    # --- 1. the ten paper figures, in the paper's own order --------------
    paper_blocks: list[str] = []
    for fname, caption, source_note in PAPER_FIGURE_ORDER:
        analysis = resolve_metric_tokens(get_teach(fname, ""))
        block = _figure_block(fname, caption, f"{analysis}<p class=\"sidecar-note\">{source_note}</p>")
        if not block:
            continue
        embedded.append(fname)
        paper_blocks.append(block)

    # --- 2. the remaining teaching atlas, renumbered as an appendix -------
    sections: dict[str, list[str]] = {k: [] for k in SECTION_INTROS}
    a_index = 0
    for fname, caption, section, short_analysis in FIGURE_MANIFEST:
        if fname in PAPER_FIGURE_FILES:
            continue  # already shown as 图 1–10
        if not (FIG_DIR / fname).exists():
            continue
        a_index += 1
        body = _strip_fig_prefix(caption)
        analysis = resolve_metric_tokens(get_teach(fname, short_analysis))
        block = _figure_block(fname, f"<strong>附录图 A{a_index}</strong> {body}".strip(), analysis)
        if not block:
            continue
        embedded.append(fname)
        sections[section].append(block)

    appendix_parts = []
    for key in ["network", "hydro", "carbon", "comparison", "nestedcv", "innovation", "validation"]:
        if sections.get(key):
            appendix_parts.append(SECTION_INTROS[key])
            appendix_parts.extend(sections[key])

    return "\n".join(paper_blocks), "\n".join(appendix_parts), embedded


def main() -> None:
    M = load_frozen_report_metrics()
    paper_figures, appendix_figures, embedded = build_figure_sections()
    n_figs = len(embedded)
    missing = [f for f, _, _, _ in FIGURE_MANIFEST if f not in embedded]
    nested_tables = nested_cv_tables_html()
    innovation_tables = innovation_tables_html()
    reach_table1 = load_table1()
    reach_table_html = reach_network_table_html(reach_table1)

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
  <div class="subtitle">East River 流域案例：公开再分析 · 多尺度过滤 · 可辨识性 · 分组交叉验证</div>
  <div class="meta">
    研究框架来源：Gao et al., <em>The Innovation</em>（AI cross-fusion approach for river carbon transport）<br>
    案例基准：Saccardi &amp; Winnick (2021), <em>Global Biogeochemical Cycles</em>（公开观测再分析，非本项目自采）<br>
    冻结运行：<code>{M['run_id']}</code>（与 paper.md / nested_cv_summary.json 同源）<br>
    报告类型：正式研究报告（封面 · 目录 · 摘要 · 背景 · 方法 · 过程 · 结果 · 讨论 · 结论 · 展望）<br>
    研究区域：美国科罗拉多州 East River 流域（HUC 14020001）<br>
    内嵌图表：{n_figs} 幅（精选流水线产出，base64 内嵌，无外部 CDN / 无文件路径图片）
  </div>
  <div class="date">报告生成日期：{REPORT_DATE_ZH}</div>
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
    <p>本报告对 Saccardi &amp; Winnick (2021) HydroShare <strong>公开</strong> East River 战役观测
    （n=120，2019-08-02–11）与公共 NHDPlus HR / USGS 流量做<strong>再分析</strong>
    （非本项目自采野外），检验河网 CO₂ 基准输运 + 亚网格闭合路线，并写出 LES 式空间过滤、
    S<sub>sgs</sub>–k 实践等终性（practical equifinality）与无量纲稀疏闭合实验。
    冻结运行 <code>{M['run_id']}</code>；全程<strong>未使用合成观测</strong>。</p>
    <p>主指标是<strong>分组留一河段</strong>交叉验证（grouped LOO-reach，非带内环的 nested CV；
    训练集目标在折内重建，持出浓度不进入训练标签）。Baseline（S<sub>sgs</sub>=0）持出
    C<sub>aq</sub> RMSE = <strong>{_fmt(M['baseline_rmse'])}</strong>；Residual-AI MLP =
    <strong>{_fmt(M['mlp_rmse'])}</strong>，<strong>并未低于</strong> Baseline；RF = {_fmt(M['rf_rmse'])} 更高。
    折内目标下残差闭合整体上未降低持出浓度误差（干流 R008 子组更好、多样本支流更差），
    且样点支撑通量诊断出现数量级放大，故<strong>不构成预测成功主张</strong>；k 修正 =
    {_fmt(M['kcorr_rmse'])}（未优于 Baseline；k<sub>need</sub> 不可行比例 {M['k_infeasible_frac']:.0%}）。
    重叠样点面积通量诊断（<strong>非研究区总量</strong>）：Baseline ≈ {M['baseline_flux']:.0f}、
    MLP ≈ {M['mlp_flux']:.0f}、RF ≈ {M['rf_flux']:.0f} mol d<sup>−1</sup>。
    Profile SSE 盆地 RMSE 约 {_fmt(M['eq_rmse_lo'])}–{_fmt(M['eq_rmse_hi'])}；滤波正式尺度为
    {M['filter_scales']}（study_reach 因收缩成环已排除）。</p>
    <p>叙事重点不是“AI 已证明提高精度”，而是：滤波 Δx 定义、浓度单变量下 S–k 分配不可辨识、
    以及明确报告方法边界。干流 R008_S1–S6 为<strong>逻辑报告 / 汇流点 y 阈值简化树</strong>，
    不是已核验的“真实 NHD 有向压缩”。报告内嵌 {n_figs} 幅精选图。</p>
    <div class="kw"><strong>关键词：</strong>河网碳输运；CO₂ 逸散；亚网格闭合；可辨识性；LES 过滤；分组交叉验证；公开再分析；East River</div>
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
  “亚网格闭合项” S<sub>sgs</sub>。本报告在 East River 上对 <strong>Saccardi &amp; Winnick (2021) 公开观测</strong>
  做再分析（配公共 NHD/USGS），检验该路线在分组交叉验证下的边界——<strong>不是</strong>本项目自采野外。</p>
  <h3>1.2 研究区域与河网结构</h3>
  <p>East River 位于 Gunnison 县，属 Upper Colorado 流域（水文单元 HUC 14020001）。
  我们将河网划分为 <strong>8 条逻辑河段 R001–R008</strong>（见第四节表 2）；
  干流 R008_S1–S6 按汇流点北向坐标阈值串成<strong>逻辑报告树</strong>，不是已核验的 NHD 有向压缩。
  细尺度滤波使用 NHDPlus HR 端点匹配有向图。</p>
  <p>公开战役采样为 <strong>2019 年 8 月 2 日至 11 日</strong>，共 <strong>120 个水样</strong>
  （HydroShare；Saccardi &amp; Winnick, 2021）。本项目<strong>未使用合成观测</strong>，
  也<strong>未声称自采</strong>。</p>
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
  <h3>2.2b 水动力几何关系的闭合偏差</h3>
  <div class="note">
    宽度、水深与流速取自 Raymond et al. (2012) 三条<strong>分别拟合</strong>的经验关系
    <code>W = 12.88·Q<sup>0.42</sup></code>、<code>h = 0.4·Q<sup>0.29</sup></code>、
    <code>u = 0.19·Q<sup>0.29</sup></code>。三者并非严格相容：联立给出
    <code>u·W·h = 0.97888·Q</code>，即连续方程 <code>u = Q/(W·h)</code> 仅闭合到
    <strong>2.112%</strong>。我们保留已发表的 u 回归而不替换为连续方程导出的流速，
    因为替换会连带重算 k<sub>600</sub>、Re、Fr、Da 及全部下游残差；
    因此该 2.112% 偏差作为<strong>已声明的系统偏差</strong>随几何假设一并报告，而非静默吸收。
  </div>
  <h3>2.3 数据完整性政策</h3>
  <div class="note">
    <strong>真实数据唯一原则：</strong>data_policy.real_data_only: true；allow_synthetic_fallback: false。
    论文主指标是<strong>分组留一河段</strong>交叉验证（grouped LOO-reach；未实现带内环调参的 nested CV）；
    样本内 R² 仅作附录。NHD 河段映射：GNIS 优先，其余按最近战役 GPS 样点分配。
  </div>
</section>

<section id="process">
  <h2>三、研究过程</h2>
  <p>十五阶段流水线（run_pipeline.py）：数据获取 → 河网构建 → 基准输运 → 气体交换 → 残差 → 模型训练 → 耦合预测 → 验证 → 空间—时间图 → GIS 矢量河网 + quiver → 2D 断面与中心线捕捉 → <strong>分组留一河段输运消融</strong>（12）→ <strong>滤波尺度 S<sub>sgs</sub></strong>（13）→ <strong>k–S 可辨识性</strong>（14）→ <strong>无量纲稀疏闭合</strong>（15）。</p>
</section>

<section id="results">
  <h2>四、结果展示</h2>
  {READING_GUIDE_HTML}
  <h3>4.0 河网结构：先弄清“哪一段是哪条河”</h3>
  {reach_table_html}
  <h3>4.0b 样本与模型性能概览</h3>
  <table>
    <caption>表 3 验证数据集基本统计</caption>
    <thead><tr><th>指标</th><th>数值</th></tr></thead>
    <tbody>
      <tr><td class="left">有效样点数 n</td><td>120（真实战役样点，无合成）</td></tr>
      <tr><td class="left">河段数</td><td>8（R001–R008）；干流 R008 n=58；单样本河段 R001/R006/R007</td></tr>
      <tr><td class="left">论文主指标</td><td>分组 LOO-reach（grouped LOO-reach CV）持出样本的 C<sub>aq</sub> / F<sub>CO₂</sub>（表 4）</td></tr>
      <tr><td class="left">采样日期</td><td>2019-08-02 至 2019-08-11（10 天）</td></tr>
      <tr><td class="left">报告内嵌图数</td><td>{n_figs}（精选，含分组 LOO-reach CV 与论文创新实验图）</td></tr>
    </tbody>
  </table>
{nested_tables}
{innovation_tables}

  <h3>4.8 论文正文图 1–10（与手稿同序同号）</h3>
  <p>以下十幅图与英文手稿的 Figure 1–10 一一对应，编号按正文首次引用顺序排列；
  本报告中的“图 N”与手稿中的“Figure N”指同一对象。其余教学用图统一编入 4.9 附录序列（附录图 A1 起）。</p>
{paper_figures}

  <h3>4.9 附录教学图（附录图 A1 起，与方法正文图分离编号）</h3>
{appendix_figures}
</section>

<section id="discussion">
  <h2>五、分析与讨论</h2>
  <h3>5.1 河网图到底在说什么？</h3>
  <p>读者最容易困惑的是“R001–R008 和地图上弯弯曲曲的河线是什么关系”。简言之：
  <strong>表 2 的 8 行是逻辑报告河段</strong>；<strong>图 2 的彩色河线是 NHD 河道矢量</strong>。
  干流分段 R008_S1–S6 是汇流点 y 阈值简化树，<strong>不是</strong>“真实 NHD 有向拓扑压缩”的证明。
  碳通量与模型结论主要由样点最密的 R008 驱动；单样本支流只作示意。</p>
  <h3>5.2 水动力与 2D 断面示意</h3>
  <p>平面 quiver 图（附录图 A4–A5）用箭头示意水往哪里流、流量/流速有多大，数值来自 USGS 干流测站与文献回归，
  不是每个支流都有独立测站。断面 u(y,z) 图（附录图 A10）在缺少实测地形断面时，用梯形槽假设和经典流速分布公式画出示意图，
  目的是帮助理解“河水在断面内如何分布”，<strong>不能当作现场 ADCP 测量结果</strong>。</p>
  <h3>5.3 Baseline 与 AI：分组交叉验证怎么说？</h3>
  <p>Baseline 只用传统水动力 + 气体交换公式；Residual-AI 学习折内重建的 S<sub>sgs</sub>；
  k 修正试图用可变气体交换吸收残差。<strong>主文只看表 4 的持出 C<sub>aq</sub> 与样点支撑通量诊断</strong>
  （冻结 run <code>{M['run_id']}</code>）。
  MLP 持出 C RMSE = {_fmt(M['mlp_rmse'])}，<strong>高于</strong> Baseline {_fmt(M['baseline_rmse'])}，
  但干流子组 R008 上 MLP 为 {_fmt(M['subgroup_mlp_mainstem_rmse'])}、优于 Baseline 的
  {_fmt(M['subgroup_baseline_mainstem_rmse'])}，而多样本支流上反之，故整体差异并非一致改善：
  RF = {_fmt(M['rf_rmse'])} 更高、通量诊断出现数量级放大、河段组 n=8 极不平衡。
  因此<strong>不作预测成功主张</strong>，只报告子组结构与主导河段。
  k 修正 RMSE = {_fmt(M['kcorr_rmse'])}（未优于 Baseline；{M['k_infeasible_frac']:.0%} 样点无正 k<sub>need</sub>）。
  没有一种方案同时给出稳健浓度推广与物理可信的逸散通量。</p>
  <h3>5.3b 滤波、可辨识性与无量纲式说明了什么？</h3>
  <p>正式滤波尺度仅 {M['filter_scales']}：|S| 在采样条件下大致稳定，是敏感性诊断，不是普适律。
  <strong>study_reach 已排除</strong>（全边保留收缩成环），不得声称“到研究河段尺度仍近似不变”。</p>
  <p>可辨识性为 profile SSE（非似然）：盆地 RMSE 约 {_fmt(M['eq_rmse_lo'])}–{_fmt(M['eq_rmse_hi'])}；
  q<sub>A</sub> 中位数约 {_fmt(M['q_a_median'], 1)} m d<sup>−1</sup>（直接由 86400·Q<sub>routed</sub>/(L<sub>control</sub>·W) 键合并得到，
  不由残差反演）。浓度单变量下 S 与 k 实践等终。
  无量纲稀疏式形式可解释，持出输运耦合仍弱于或不稳于 Baseline 叙事所需的稳健推广。</p>
  <h3>5.4 数据与方法的诚实限制</h3>
  <ul>
    <li>公开再分析，非本项目自采；仅 10 天战役，不能代表全年。</li>
    <li>支流流量取公开同步 Q，没有支流日过程测站。</li>
    <li>干流分段为逻辑简化树；study_reach 滤波尺度因拓扑环排除。</li>
    <li>DIC/DOC 仅部分样点有值；碱度、营养盐未观测，未做任何插补。</li>
    <li>StreamPULSE 门户无 East River 站点；单样本河段不与 R008 均等权重。</li>
  </ul>
</section>

<section id="conclusions">
  <h2>六、主要结论</h2>
  <ol>
    <li>分组 LOO-reach（折内目标）下 Baseline C RMSE = {_fmt(M['baseline_rmse'])}；
    MLP = {_fmt(M['mlp_rmse'])}、RF = {_fmt(M['rf_rmse'])}，两者均<strong>未降低</strong>整体持出误差；
    子组结构（干流 R008 上残差闭合更好、多样本支流上更差）是主要发现，
    通量诊断为样点支撑量，非研究区总量。</li>
    <li>k 修正 RMSE = {_fmt(M['kcorr_rmse'])}；{M['k_infeasible_frac']:.0%} 样点无正 k<sub>need</sub>；
    浓度单变量下 S<sub>sgs</sub> 与 k 存在 practical equifinality（profile SSE）。</li>
    <li>滤波正式尺度 {M['filter_scales']}；study_reach 排除；无量纲稀疏式作形式诊断而非精度主张。</li>
    <li>干流 R008_S* 为逻辑报告树；R008（n=58）与支流分开报告；公开再分析立场贯穿全文。</li>
  </ol>
</section>

<section id="outlook">
  <h2>七、不足与展望</h2>
  <p>CH₄ / GRiMeDB、StreamPULSE <strong>其他</strong>流域、CONUS 产品对照、单河段 TELEMAC、PINN Saint-Venant 均属论文之后的拓展，不进入本篇主创新。
  已克隆 Fluvial-UMass/CONUS_carbon 仓库结构（查找表，无大陆输入栅格），仅作结构对照，<strong>不是</strong>第二场 East River 野外战役。
  StreamPULSE East River 仍为 0 站点，不重试为主路径。符号回归在 PySINDy 安装失败后改用 LASSO。
  论文图 2（4.8 节）使用 Esri World Imagery 卫星瓦片，瓦片本地缓存并记录来源与哈希；
  附录教学图仍使用本地地形渐变底图，不依赖 CDN。WQP 同日合并仍为 0/120。</p>
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
  · 冻结 run {M['run_id']} · MLP 浓度 RMSE 整体高于 Baseline（不作成功主张） · study_reach 已排除
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

    # Markdown mirror of Table 1, built from the same machine-derived object.
    _t1 = reach_table1
    _rows_md = [
        "| 编号 | 河流 | 角色 | 汇入干流段 | 域长 (km) | 已分配走廊线 | ·GNIS 匹配 | ·最近样点 | 逻辑路由段 | 采样控制体 | 战役样点 | 说明 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for _r in _t1.get("rows") or []:
        _rid = str(_r.get("reach_id", ""))
        _dom = _r.get("domain_length_km")
        _dom_s = "—" if _dom is None else f"{float(_dom):.3f}"
        if not _r.get("domain_consistent"):
            _dom_s += " †"
        _rows_md.append(
            f"| {_rid} | {_r.get('stream_name', '')} | {_r.get('role', '')} | "
            f"{_r.get('joins_mainstem', '')} | {_dom_s} | {_r.get('assigned_flowlines', '')} | "
            f"{_r.get('assigned_gnis_match', '')} | {_r.get('assigned_nearest_sample', '')} | "
            f"{_r.get('routing_segments', '')} | {_r.get('sampled_cells', '')} | "
            f"{_r.get('campaign_samples', '')} | {REACH_NOTES_ZH.get(_rid, '')} |"
        )
    reach_md_table = "\n".join(_rows_md)

    md = f"""# East River CO₂ 河网碳输运 — 公开再分析报告

**报告日期：** {REPORT_DATE_ZH}  
**冻结运行：** `{M['run_id']}`（与 paper / nested_cv_summary 同源）  
**内嵌图表：** {n_figs} 幅（精选，见 report.html；每图附五段教学讲解）  
**阅读建议：** 术语表 → 表 2（逻辑河段 / 简化干流树）→ 表 M / 表 4 → 滤波（无 study_reach）→ 可辨识性 / 无量纲式

## 摘要

对 Saccardi & Winnick (2021) 公开观测 + NHD/USGS 再分析（非自采）。分组 LOO-reach（折内目标）：
Baseline C RMSE **{_fmt(M['baseline_rmse'])}**；MLP **{_fmt(M['mlp_rmse'])}**（整体高于 Baseline，不作成功主张）；
RF {_fmt(M['rf_rmse'])}；k 修正 {_fmt(M['kcorr_rmse'])}（{M['k_infeasible_frac']:.0%} k_need 不可行）。
通量诊断为重叠样点面积量（非研究区总量）。滤波正式尺度 {M['filter_scales']}；study_reach 排除。
干流 R008_S* 为逻辑报告树，非已核验 NHD 压缩。

## 河网 8 段（四种估计量，数字由机器表动态生成）

{reach_md_table}
"""
    md += f"""
## 图表清单

### 论文正文图（与手稿 Figure 1–10 同序同号）

"""
    for fname, caption, source_note in PAPER_FIGURE_ORDER:
        if (FIG_DIR / fname).exists():
            plain = caption.replace("<strong>", "**").replace("</strong>", "**")
            plain = plain.replace("<sub>", "").replace("</sub>", "")
            md += f"- `{fname}` — {plain}\n"

    md += "\n### 附录教学图（附录图 A1 起）\n\n"
    _a = 0
    for fname, caption, section, _ in FIGURE_MANIFEST:
        if fname in PAPER_FIGURE_FILES:
            continue
        if (FIG_DIR / fname).exists():
            _a += 1
            body = _strip_fig_prefix(caption)
            plain = body.replace("<strong>", "**").replace("</strong>", "**")
            plain = plain.replace("<sub>", "").replace("</sub>", "")
            md += f"- [{section}] **附录图 A{_a}** `{fname}` — {plain}\n"

    md += """
## 已移除

- `network_map_*.png` — reach 质心散点图（由 GIS 线图 + quiver 替代）

## 数据限制

- 战役 10 天（无全年季节覆盖）
- GNIS 85/393 + 最近 GPS 样点分配（非质心回退）
- DIC/DOC 41/120 非空；Alk/N/P 缺失；WQP 同日合并 0/120
- 支流 Q 为公开同步值（无日过程；无 gage-ratio 虚构过程线）
- F_CO₂ 为模型通量诊断/代理，非腔室验证
- Residual-AI 分组 LOO-reach CV 未优于 Baseline；勿声称精度胜利

*完整自包含 HTML：report.html*  
*架构冻结：docs/ENGINEERING_NOTES.md；论文主表：results/tables/paper_main_results.csv*
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(f"MD: {OUT_MD} ({OUT_MD.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
