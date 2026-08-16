# -*- coding: utf-8 -*-
"""One-shot builder: writes scripts/figure_explanations.py with long teaching text."""
from pathlib import Path

OUT = Path(__file__).with_name("figure_explanations.py")


def _p(*parts):
    return "".join(f"<p>{x}</p>" for x in parts)


def _h(title):
    return f"<p><strong>{title}</strong></p>"


def teach(bg, how, panels, curves, conclusion):
    return (
        _h("1. 背景与目的")
        + _p(bg)
        + _h("2. 如何阅读")
        + _p(how)
        + _h("3. 子图逐一解释")
        + _p(panels)
        + _h("4. 曲线 / 分布表达的具体含义")
        + _p(curves)
        + _h("5. 能得出什么结论（通俗复述）")
        + _p(conclusion)
    )


FIGS: dict[str, str] = {}

FIGS["gis_reach_assignment_map.png"] = teach(
    "这张图是整份报告的“空间底图”。在谈论流量、浓度、亚网格闭合之前，必须先弄清：地图上弯弯曲曲的彩色细线是什么、它们如何对应到我们划分的 8 条研究河段 R001–R008。它回答的问题是“研究区河网长什么样、我们怎么把国家标准河线贴上研究标签”。",
    "背景是本地生成的地形渐变色（无外部地图瓦片、无 CDN）。彩色细线是 HydroShare 补充包 East_River_Lines.shp 提供的 NHD（国家水文数据集，National Hydrography Dataset）河道中心线，共 393 段真实线几何。不同颜色代表不同研究河段（图例给出 R001–R008）。线条越密集、越长的干流走廊通常对应 East River（R008）。",
    "本图为单幅地图（无 a/b 子图）。请对照正文表 2：颜色标签与河段编号一一对应。GNIS（地名信息系统，Geographic Names Information System）能自动对上名字的线段约 85 段；其余无名线段按“离哪个河段样点/中心最近”分配，因此 Bradley、Rock、Gothic 等支流的边界可能有一点模糊——这不是绘图错误，而是命名数据本身的局限。",
    "颜色不是连续色标，而是分类色：每一种颜色 = 一条逻辑河段。线的弯曲反映真实河道蜿蜒，不是示意折线。若某条颜色“串”进了相邻支流，说明最近邻分配在无名河线上的不确定性。",
    "请先记住：水从上游支流（R001 一侧）汇入，最终进入 R008 干流。后面所有图里的“按河段着色”都沿用这套颜色逻辑。干流样点最多（n=58），结论主要由 R008 驱动；单样本河段只作示意。",
)

FIGS["gis_samples_on_network.png"] = teach(
    "在弄清河段归属之后，下一步是看“我们真正采到了哪些点”。这张图把 2019 年 8 月战役的 120 个水样 GPS 位置叠在 NHD 河网上，让读者一眼看出采样密度如何沿干流与支流分布。",
    "灰色细线仍是 NHD 中心线；白边彩色圆点是野外 GPS 实测样点（按河段分色）。点 intentionally 较大，便于在报告里辨认。坐标未做任何插补或平滑。",
    "单幅地图。请注意 R008（干流）上点最密，R003–R005 支流也有一定密度，而 R001、R006、R007 往往只有零星一点——这与表 2 样点计数（1、3、15、24、17、1、1、58）完全一致。",
    "点密集 = 该河段证据权重大；点稀疏 = 统计不稳定。后面嵌套交叉验证会把“单样本河段”单独标为示意，正是因为这里看得见的稀疏。",
    "采样设计是“干流主导、支流补充”。任何声称“全河网均匀验证”的说法都不成立——我们只有这 120 个真实点。",
)

FIGS["sample_snap_centerline.png"] = teach(
    "GPS 点往往落在河岸边或河心附近，而模型需要把点放到河道中心线上才能计算链距（chainage，沿程里程）。这张图展示“捕捉”（snap）过程：野外坐标如何被投影到最近的 NHD 中心线。",
    "圆点 = 原始 GPS；叉号 = 投影到线上的位置；细线段连接二者，长度就是捕捉距离。标题通常给出中位捕捉距离（本战役中位约 8.5 m）。距离过大的点意味着坐标或河线匹配仍有不确定性。",
    "单幅图。请扫一眼是否有“长尾巴”连接线——那是捕捉距离偏大的样点，解读该点时要更谨慎。没有对任何点做人工挪动或插补。",
    "捕捉距离的分布反映 GPS 精度与河线几何精度的匹配程度。中位距离小，说明整体投影可信；个别离群点应在讨论里承认不确定性。",
    "模型沿程剖面、滤波实验的样点归属，都以这次捕捉为准。它是连接“野外点”与“河网线”的关键桥梁。",
)

FIGS["gis_flow_quiver_Q.png"] = teach(
    "读者常问：水到底往哪流、哪里流量大？平面 quiver（箭矢）图用箭头同时回答“方向”和“大小”。本图专门画流量 Q。",
    "每个箭头沿 NHD 线段指向下游（由链距拓扑 R001→R008 确定）。颜色与长度正比于该河段战役期平均流量 Q（m³/s）。色标在图旁：越暖/越长表示流量越大。这不是瞬时动画，而是战役期代表值的平面示意。",
    "单幅 quiver 图。干流 R008 箭头通常最长、颜色最深；上游支流箭头短而浅。若某支流箭头异常大，请回头核对流量来源（干流来自 USGS 09112500；支流为公开战役同步 Q，无独立日过程测站）。",
    "箭头场表达的是“汇流格局”：支流汇入干流、干流向 Almont 方向增大。它帮助建立水动力空间直觉，为后面解释碳通量沿干流累积做铺垫。",
    "流量空间格局由真实河网几何 + 实测/公开同步 Q 支撑，不是合成流场。但支流缺少连续测站，故支流箭头精度低于干流——这一点在不足与展望中会再次说明。",
)

FIGS["gis_flow_quiver_u.png"] = teach(
    "与流量 quiver 成对：本图展示流速 u。流量大不等于流速大——宽而深的河段可能 Q 大但 u 适中；陡窄河段可能 Q 小但 u 很大。",
    "读法与流量 quiver 相同：箭头指下游，颜色/长度 ∝ u（m/s）。u 由 Manning 公式（曼宁公式）结合 Q、坡度、断面几何估算，不是 ADCP（声学多普勒流速剖面仪）实测瞬时场。",
    "单幅图。请对比流量 quiver：某些陡坡支流（如 Rustlers Gulch 一带）可能流速偏高而流量不大；干流下游则流量大、流速中等。这种对比帮助理解气体交换速度 k 为何随坡度/流速变化。",
    "流速场直接影响 Raymond 经验式里的 k<sub>600</sub>（标准化气体交换速度），从而影响逸散通量诊断。高 u、高坡度 → 更大的潜在逸散能力。",
    "请把本图理解为“水力梯度的平面示意”。断面内部流速如何分布，要看后面的理想化 u(y,z) 面板——那里会明确标注非 ADCP。",
)

FIGS["gis_streamtube_QW_u.png"] = teach(
    "streamtube（流管）风格把流量与流速压缩进同一张线网图：线宽表达流量，颜色表达流速，避免两张 quiver 来回对照。",
    "线宽 ∝ Q，颜色 ∝ u，几何仍是真实 NHD LineString。色标给出 u 的数值范围。线越粗 = 流量越大；颜色越暖（视具体色图）= 流速越大。",
    "单幅图。East River 干流应呈现最粗的线带；上游细支流细而颜色可能偏冷或偏暖取决于局部坡度。请与表 2 河段衔接关系一起读。",
    "这种编码在可视化里很常见：用“粗细”承载一个标量、用“颜色”承载另一个标量，让汇流结构一目了然。",
    "若只记住一张水动力总览图，记住这一张即可：粗线走廊 = 干流主通道，颜色变化 = 局部流速起伏。",
)

FIGS["gis_network_map_Q.png"] = teach(
    "在 quiver 之外，用“线宽编码流量”的 GIS 线图更接近传统水系图读法，便于与文献中的河网图对照。",
    "每条 NHD 线按所属研究河段聚合后，用线宽表示河段平均 Q，颜色也可辅助区分量级。坐标为投影后的平面坐标。",
    "单幅线图。请从上游细线追到下游粗线，验证流量是否沿汇流方向增大——这是质量守恒的直观检查。",
    "线宽梯度 = 流量梯度。若某处突然变粗，通常对应较大支流汇入或进入干流段。",
    "干流 R008 流量最大（USGS 09112500）。支流 Q 取补充包公开的战役期同步值，未用虚构的日比值过程线。",
)

FIGS["gis_network_map_u.png"] = teach(
    "与流量线图成对，展示流速沿网分布，帮助识别“急流河段”。",
    "线颜色（或线宽，视具体配色）编码河段平均 u。读图时关注暖色/高值是否落在陡坡、窄河段。",
    "单幅图。Rustlers Gulch（R007）与部分干流段 u 往往偏高，与坡度、河道宽度相关。",
    "流速高值区是气体交换潜在活跃区（Raymond 公式中 u 进入 ln k<sub>600</sub>）。",
    "流速是估算量（Manning），不是 ADCP。解释“哪里交换快”时请带着这份不确定性。",
)

FIGS["longitudinal_profile_hydraulics.png"] = teach(
    "把弯曲河网“拉直”成链距坐标后，可以像看河床纵剖面一样看水力变量如何沿程变化。",
    "横轴是链距（km），由 NHD 真实线长累加；纵轴自上而下（或分面板）给出水深 h、流速 u、流量 Q。散点 = 120 个样点；阶梯/折线 = 河段均值。",
    "通常为 3 个纵向子图（上：h；中：u；下：Q，具体以图面标题为准）。每个子图共享横轴链距，便于对齐同一位置。干流下游 h、Q 增大趋势应最明显。",
    "散点的竖直散布反映同一河段内不同日期/位置的差异；阶梯线是河段汇总，用来看“大趋势”。",
    "沿程水力剖面说明：越往下游，河道通常更宽更深、流量更大。这为理解干流碳累积与逸散提供水动力背景。",
)

FIGS["cross_section_u_field_panel.png"] = teach(
    "平面图看不清断面内部流速结构。本图用理想化梯形断面 + 抛物线垂向流速公式，画出每个河段的 u(y,z) 示意，帮助理解“河水在断面里怎么分布”。",
    "共 8 个小面板（2×4），每个对应一条河段。横轴 y 是横向（河宽方向），纵轴 z 是水深方向；颜色表示流速大小。色标统一或分面板给出。",
    "子图 a–h（或按 R001…R008 标题）：每个格子里，底部是河床、上方是自由水面；中间暖色通常是主流核。标题含河段名与平均流速 ū。无实测断面地形处，形状完全由假设生成。",
    "公式假设 u(z)=1.5ū(2ζ−ζ²)（ζ 为相对水深），横向近似均匀——这是开渠湍流的经典近似，不是现场 ADCP 测量。",
    "请务必记住：这是教学示意。若未来有 ADCP 或地形断面，应替换本图并重新评估断面平均 k。当前标注为待补充实测断面。",
)

FIGS["planview_velocity_network.png"] = teach(
    "把“线宽∝Q、颜色∝|u|”的 streamtube 思路再画一张平面总览，与 quiver 互补。",
    "读法同 streamtube：粗 = 大流量，颜色 = 流速大小。底图为本地地形渐变。",
    "单幅图。与 quiver 对照时，本图更强调连续线网，quiver 更强调方向矢量。",
    "数值均来自真实战役观测与 Manning 估算，无合成场。",
    "用于课堂式讲解“整张河网的水动力肖像”。",
)

FIGS["temporal_hydraulics.png"] = teach(
    "战役只有 10 天（2019-08-02 至 08-11）。本图看流域平均水动力是否随日期大起大落。",
    "横轴日期，纵轴为流域/样点平均的 Q 与 u（分曲线或分面板）。点或折线连接各采样日。",
    "若为双面板：上图 Q，下图 u；若为同图双曲线：请看图例区分。变化相对平缓，反映融雪后基流阶段较稳定。",
    "平缓的时间序列意味着：战役窗口内水文条件没有戏剧性洪水脉冲，模型结果主要反映空间异质性而非强时间强迫。",
    "不能外推到融雪洪峰或枯水期——那些季节<strong>待补充</strong>。",
)

FIGS["gis_network_map_pCO2.png"] = teach(
    "进入碳部分：先看 pCO₂（二氧化碳分压）的空间格局——哪里的河水更“想”向大气吐 CO₂。",
    "线颜色编码河段平均 pCO₂（µatm）。色标从低到高；高值区通常在干流样点密集段。",
    "单幅图。R008 变异最大（n=58），高 pCO₂ 与土壤 CO₂ 输入及有机质分解等过程一致（机制推断，非本图直接证明）。",
    "颜色深浅 = 分压高低。它是 C<sub>aq</sub> 的上游观测量（经亨利定律相关）。",
    "空间热点告诉你：闭合与验证的主战场在干流高 pCO₂ 段。",
)

FIGS["carbon_heatmap_pCO2.png"] = teach(
    "热图把“河段 × 日期”摊成矩阵，适合看短战役里的时空脉冲。",
    "纵轴河段（R001–R008），横轴日期（8/2–8/11），格子颜色 = 该河段该日平均 pCO₂。色标在旁。白色/缺失格表示当日该河段无样。",
    "单幅热图。请找暖色块：干流 R008 在 8 月 5–8 日前后常出现峰值。支流行往往更稀疏。",
    "热图不是连续插值曲面，而是离散采样的矩阵显示；空格就是没采到，不要脑补。",
    "时间分辨率受战役限制，只能讨论这 10 天窗口内的起伏。",
)

FIGS["carbon_heatmap_C_aq.png"] = teach(
    "C<sub>aq</sub>（溶解态 CO₂ 浓度）是输运模型的直接目标变量。本热图展示其时空结构。",
    "读法同 pCO₂ 热图：河段×日期，颜色 = C<sub>aq</sub>（mol·m⁻³）。",
    "单幅热图。高值时空位置应与 pCO₂ 热图大致呼应。Baseline 常系统性低估高值格——这是引入残差闭合的动机，但动机 ≠ 持出成功。",
    "颜色对比帮助识别“难预报”的高浓度格点；嵌套 CV 会检验模型离开训练河段后是否还能抓住它们。",
    "记住：后面主文判据是持出 RMSE，不是这张热图好不好看。",
)

FIGS["longitudinal_profile_carbon.png"] = teach(
    "沿程看碳状态：pCO₂、C<sub>aq</sub>、DIC（溶解无机碳）、DOC（溶解有机碳）如何随链距变化。",
    "多面板共享链距横轴；散点为样点。DIC/DOC 仅显示有值样点（41/120），缺失不插补。",
    "子图通常包括 pCO₂、C<sub>aq</sub>，以及 DIC、DOC（若面板存在）。干流下游 pCO₂ 升高趋势与碳源输入一致。DIC/DOC 点更少，趋势解读要保守。",
    "沿程升高/降低反映源汇与稀释的综合结果，不是单一过程。",
    "碳剖面为机制讨论提供空间证据，但不能单独证明亚网格闭合可推广。",
)

FIGS["carbon_heatmap_F_CO2_ai.png"] = teach(
    "F<sub>CO₂</sub> 是模型导出的逸散通量诊断（proxy，代理量），由 k(C−C<sub>eq</sub>) 计算，不是通量箱实测。本图展示 AI 耦合后的时空通量。",
    "河段×日期热图，颜色 = F<sub>CO₂</sub>（mol·m⁻²·d⁻¹）。色标与 Baseline 对比图应对齐理解。",
    "单幅热图。干流格点往往更暖，表示更高的模型逸散诊断。请始终在心里加注：这是诊断，不是验证通量。",
    "热图强度反映浓度过饱和与 k 的乘积结构；k 用 Raymond 经验式。",
    "后面嵌套 CV 会证明：样本内/耦合诊断的高通量，不等于持出浓度更准，更不等于通量被独立证实。",
)

FIGS["gis_network_map_F_CO2_comparison.png"] = teach(
    "左右对照：同一色标下 Baseline 与 AI 的 F<sub>CO₂</sub> 空间分布，用于找“AI 抬升热点”。",
    "左/右两幅 GIS 线图，色标统一。颜色越暖通量诊断越大。",
    "子图 a（左）Baseline；子图 b（右）AI。请盯干流 R008：AI 侧通常明显更暖。统一色标是关键——否则视觉差异会被色标缩放误导。",
    "空间差分来自 S<sub>sgs</sub> 闭合改变了浓度，从而改变 k(C−C<sub>eq</sub>) 诊断。",
    "这张图属于“样本内耦合肖像”。主文仍以嵌套 CV 为准：Residual-AI 并未在持出浓度上击败 Baseline。",
)

FIGS["compare_F_CO2_baseline_vs_ai.png"] = teach(
    "把每个河段的平均 F<sub>CO₂</sub> 做成并列柱，量化 AI 相对 Baseline 的抬升。",
    "横轴河段，纵轴通量；每组两根柱（灰/蓝等）分别是 Baseline 与 AI。",
    "单幅分组柱图。R008 两组差异通常最大；单样本河段柱很不稳定，只作示意。",
    "柱高差 = 该河段平均诊断通量的方法差异，不是观测误差条。",
    "可见 AI 在样本内抬升干流通量；但请立刻联想到表 4：持出浓度并未因此变好。",
)

FIGS["difference_F_CO2_ai_minus_baseline.png"] = teach(
    "直接画 AI−Baseline 的通量差，避免在两组柱之间心算。",
    "横轴河段，纵轴差值；正值（常红）= AI 更高。",
    "单幅柱图。若所有河段为正，说明样本内 AI 全面抬升诊断通量，干流贡献主导总量变化。",
    "差值图把“方向”说清楚：正差不是精度胜利，只是诊断值变大。",
    "与嵌套 CV 的通量崩溃（k 修正）对照阅读：不同闭合可以朝完全相反的通量方向走。",
)

FIGS["temporal_baseline_vs_ai_flux.png"] = teach(
    "看战役期内日均通量诊断如何随时间演化，比较两种方法。",
    "横轴日期，纵轴日均 F<sub>CO₂</sub>；两条曲线分别是 Baseline 与 AI。",
    "单幅时间序列。AI 曲线通常整体高于 Baseline 一个数量级量级（以实际图面为准），各采样日形态可能平行。",
    "平行抬升意味着差异主要来自系统性闭合，而不是某一天的偶然尖峰。",
    "时间维同样属于样本内肖像；推广性仍看嵌套 CV。",
)

# ---- Nested CV (paper metrics) ----
FIGS["nested_cv_rmse_bar.png"] = teach(
    "这是论文主图之一。目的：在完全相同的“先预测闭合、再代入输运方程”协议下，比较 Baseline、Residual-AI、k 修正的持出样本 C<sub>aq</sub> RMSE。它直接回答“AI 有没有提高推广精度”。",
    "横轴是三种（或四种，含 RF）闭合方案，纵轴是留一河段（LOO-reach）交叉验证的 C<sub>aq</sub> RMSE（mol·m⁻³）。柱顶标注数值。颜色区分方案：灰 Baseline、蓝 MLP、青绿 RF、橙 k 修正。",
    "单幅柱图（无多子图）。请按柱高排序：Baseline ≈ 0.0284；Residual-AI MLP ≈ 0.0573（更高=更差）；RF ≈ 0.0745（更差）；k 修正 ≈ 0.0244（略低）。",
    "柱高就是持出均方根误差。Residual-AI 柱高于 Baseline，就是负结果的图形化。k 修正柱略短，必须与通量崩溃图一起读，不能单独宣布“更好的物理模型”。",
    "通俗结论：在当前数据与协议下，学习亚网格残差的 AI 没有把“没见过的河段”上的浓度预测做得更好；它比简单 Baseline 更差。这不是调参失败的托词，而是可辨识性与样本量的方法学边界。",
)

FIGS["nested_cv_scatter_holdout.png"] = teach(
    "柱图给总误差，散点图给“错在哪些点”。本图展示留一河段持出时，Residual-AI（MLP）的观测 vs 预测 C<sub>aq</sub>。",
    "横轴观测浓度，纵轴模型预测；黑色虚线是 1:1 线（完美预测）。大圆点按河段着色，图例给出各河段 n。左上角文本框含 n、RMSE、R²。",
    "单幅散点。点离 1:1 线越远误差越大。R008 点最多，对总 RMSE 贡献最大；R001/R006/R007 可能只有孤立点，不能当独立证据。若多数点系统性偏上或偏下，说明有偏差（bias）。",
    "持出 R² 常为负：模型还不如用观测均值。这与附录里几乎贴线的样本内三角图形成尖锐对比——那是过拟合肖像。",
    "请用一句话记住：换一条河来考，AI 闭合答不好。",
)

FIGS["subgroup_rmse_r008_vs_trib.png"] = teach(
    "总体 RMSE 会被样本结构扭曲。本图按证据权重拆开：干流 R008、多样本支流、单样本示意河段。",
    "横轴三个子组，每组三根柱（Baseline / Residual-AI MLP / k 修正）。纵轴仍是 LOO-reach C<sub>aq</sub> RMSE。",
    "子组 1：R008（n≈58，主证据）；子组 2：多样本支流 R002–R005；子组 3：单样本河段（示意，不均等权重）。请分别比较组内三柱，不要把组 3 与组 1 的柱高当成同等结论强度。",
    "分组柱显示误差来源结构：有时支流上 AI 更差，拉高总体 RMSE；干流上也可能出现不同排序。以实际数值为准。",
    "分层报告是方法学要求：58 个点的干流与 1 个点的支流，证据权重要差两个数量级。",
)

FIGS["ablation_flux_comparison.png"] = teach(
    "浓度只是故事一半。本图比较三种闭合在持出样本上的 F<sub>CO₂</sub> 合计与通量 RMSE（相对经验 k×观测浓度的代理通量）。",
    "左右两子图：左纵轴是持出 F 合计（mol·m⁻²·d⁻¹）；右纵轴是 F 的 RMSE。横轴均为三种方案。",
    "子图 a（左）：Baseline 合计约 3.24；Residual-AI MLP 合计可到约 69.5（诊断飙升）；k 修正合计约 0.03（几乎塌缩到 0）。子图 b（右）：给出相对代理通量的误差大小，帮助看“诊断偏离代理”的程度。",
    "左图的极端对比是 equifinality（等效性）的直观证据：为了贴近浓度，可以“加源”让通量变大，也可以“砍 k”让通量消失——浓度观测无法裁决。",
    "没有任何方案在持出上同时改进浓度与物理一致的逸散诊断。F 不是腔室验证通量。",
)

# ---- Innovation ----
FIGS["les_filter_conceptual.png"] = teach(
    "概念图：把 LES（大涡模拟）式过滤翻译成河网语言——细 NHD 线段如何被滤波窗 Δx 合并成粗控制体，未分辨过程如何进入 S<sub>sgs</sub>。",
    "左右两幅示意图。左：细网格，短控制体，样点落在较短河段上；右：粗网格，橙色大控制体，多样点落入同一单元，箭头指向 S<sub>sgs</sub>(Δx)。",
    "子图 a（左）“细网格（NHD 原生线段）”：虚线竖线示意小 Δx，红点为样点，局地平流梯度仍可能可分辨。子图 b（右）“粗网格（合并河段）”：粗线+大框表示滤波后控制体，未分辨过程只能进闭合项。",
    "概念图不承载实测数字；它定义后面滤波实验的语言。Δx 越大，被“平均掉”的过程越多，残差的统计性质会变。",
    "记住类比：不是宣布 AI 更准，而是宣布我们如何可计算地定义亚网格项。",
)

FIGS["filter_scale_sgs.png"] = teach(
    "把概念落到真实数据：样点捕捉到粗化后的 NHDPlus HR 线，按质量守恒重算 S<sub>sgs</sub>，看平均幅度与方差如何随 Δx 变化。",
    "左右两子图共享横轴 Δx（有样点单元的平均长度，m）。左纵轴平均 |S<sub>sgs</sub>|；右纵轴 Var(S<sub>sgs</sub>)。折线+大标记，旁注尺度名称与有样点单元数。",
    "子图 a：四点约对应原生（Δx≈838 m，mean|S|≈1.92）、约 2×（≈1183 m，≈1.12）、约 4×（≈1949 m，≈1.05）、研究河段（≈26 km，≈1.00）。有样点单元从 39→30→24→6（不是 8，因 HR 廊道未覆盖全部逻辑河段）。子图 b：方差从约 22.4 降到约 2.2，同样随粗化下降。",
    "下降趋势 = 细网格上尖锐的局地收支不匹配被粗化平滑。这是 East River 廊道经验依赖，不是普适 SGS 定律。",
    "通俗说：放大格子，残差看起来更“温和”——也更容易与 k 的调整搅在一起。这解释了为何在观测尺度上闭合难推广。",
)

FIGS["filter_scale_sgs_box.png"] = teach(
    "平均值可能被少数极端点拉动。箱线图展示 120 个真实样点在每个尺度上 |S<sub>sgs</sub>| 的整分布。",
    "横轴四个滤波尺度，纵轴 |S<sub>sgs</sub>|。箱线给出中位与四分位，须线外点为离群；叠加的散点是每个样点。",
    "单幅箱线+散点。请比较各箱的中位线与箱体高度（离散程度）。干流高残差点会拉高均值，使均值曲线比中位更“戏剧性”。",
    "分布宽度随尺度变化，补充说明“平滑”不只发生在均值上。",
    "读图时与嵌套 CV 主表一起看：细尺度残差更大 ≠ 更需要 AI，更 ≠ AI 能泛化。",
)

FIGS["identifiability_k_vs_sgs.png"] = teach(
    "核心诊断图：在同一套嵌套 CV 持出预测上，展示“压低 k”如何等价于“增大源项”，以及它与 Residual-AI 的 S<sub>sgs</sub> 是否同一回事。",
    "左右散点。点按河段着色，白色描边。左：横轴 k<sub>eff</sub>，纵轴隐含 S=(k<sub>emp</sub>−k<sub>eff</sub>)(C−C<sub>eq</sub>)。右：横轴 Residual-AI 持出 S<sub>sgs</sub>，纵轴同一隐含 S，虚线为 1:1；文本框给 Spearman ρ。",
    "子图 a：k<sub>eff</sub> 远小于 k<sub>emp</sub> 时，点跑到很大的隐含源项——浓度可拟合，逸散通量会崩。子图 b：若点贴近 1:1，说明两种闭合吸收同一缺口；若离散，说明它们并不是同一条等价路径上的同一解。以图上 ρ 为准。",
    "这是 practical equifinality（实践等效）的几何图像：参数朝不同方向走，浓度观测仍可能被“糊弄”过去。",
    "结论：仅有浓度时，不能诚实地说“我们辨识出了真正的亚网格源汇”。需要独立通量或独立 k。",
)

FIGS["identifiability_tradeoff.png"] = teach(
    "把可辨识性翻译成决策者能懂的权衡：k 比值 vs 通量，以及三种方案的持出 RMSE 与通量合计。",
    "左：横轴 k<sub>eff</sub>/k<sub>emp</sub>（对数轴），纵轴 k 修正持出 F；竖虚线标比值=1。右：柱 = C RMSE，菱形（右轴）= F 合计。",
    "子图 a：当比值中位数约 3.4×10⁻⁴ 时，F 点靠近 0——“砍气体交换”的代价。子图 b：k 修正 RMSE 略低于 Baseline，但 F 合计几乎消失；Residual-AI RMSE 高于 Baseline，F 合计却飙升。",
    "双轴图强调：优化浓度与保持通量诊断可以背道而驰。",
    "一句话：没有免费午餐——略好的浓度可能买自崩溃的通量；更大的源项诊断也不等于更准的持出浓度。",
)

FIGS["dimensionless_coefficients.png"] = teach(
    "展示仅用无量纲 Π 群（Fr、Slope、h/W、log₁₀Re、log₁₀Da）做标准化 LASSO 得到的稀疏系数。贡献在“形式可解释”，不在“RMSE 金牌”。",
    "水平条形：纵轴特征名，横轴标准化系数；蓝=正、红=负。图下文本给出方程与对 S 的留一河段 R²（常为负）。",
    "单幅系数图。主导项通常为 Fr（正）、Slope（负）、h/W（负）；logRe/logDa 接近 0。对应稀疏式约 S*_z ≈ 1.059 + 1.536 Fr − 1.669 Slope − 2.179 h/W。",
    "系数大小是“标准化后的相对贡献”，不是原始单位下的因果效应强度；解释方向（正/负）比绝对数值更稳健。",
    "嵌套 CV 代入输运后 C RMSE≈0.051，仍差于 Baseline 0.028。发表点是可解释形式 + 诚实的弱预测。",
)

# ---- Validation appendix ----
FIGS["obs_vs_model_scatter_large.png"] = teach(
    "附录肖像：同一批 120 点上 Baseline（圆）与 AI（三角）的观测-预测总散点。用于展示过拟合有多“好看”，不是主结论。",
    "横轴观测，纵轴预测，1:1 虚线。颜色分河段。圆=Baseline，三角=AI。",
    "单幅大散点。三角几乎贴线（样本内 R²≈0.997），圆点系统性偏低。请立刻对照嵌套 CV 散点：持出并不贴线。",
    "样本内高 R² 只说明模型记住了这 120 个点，不说明换河还能用。",
    "教学用途：演示“看起来完美”的图为什么不能进主文当精度声明。",
)

FIGS["obs_vs_model_scatter.png"] = teach(
    "把总散点拆成左右，便于对比 Baseline 与 AI 的样本内拟合。",
    "左面板 Baseline，右面板 AI；各自有 RMSE/R² 标注，点按河段着色。",
    "子图 a（左）：点多在 1:1 下方 → 系统性低估。子图 b（右）：点贴线 → 样本内闭合成功（乐观）。",
    "左右对比是残差学习的直观教材：AI 把 Baseline 的缺口补上了——在训练分布内。",
    "请用红笔在心里标注：附录 only。",
)

FIGS["obs_vs_model_by_reach.png"] = teach(
    "8 个河段各自一张小散点，避免干流点淹没支流。",
    "2×4 面板，共享坐标；每格标题含 rid 与 n。",
    "子图对应 R001…R008。R008 点最多、Baseline 偏离最明显；n=1 的格子只有单点，无法谈趋势。",
    "分河段查看能发现误差是否集中在某类支流。",
    "结合表 2 样点数阅读，防止对稀缺河段过度解读。",
)

FIGS["flux_by_reach.png"] = teach(
    "各河段平均 F<sub>CO₂</sub> 的 Baseline vs AI 柱图（样本内耦合）。",
    "横轴河段，分组柱比较两种方法。",
    "单幅图。干流抬升通常最大，与高 pCO₂、大残差一致。",
    "通量对 k 公式敏感；绝对值解释需谨慎。",
    "再次提醒：这是诊断对比，主文看嵌套 CV。",
)

FIGS["seasonal_rmse.png"] = teach(
    "战役窗口内逐日 C<sub>aq</sub> RMSE，看样本内误差是否某天崩盘。",
    "横轴日期，纵轴 RMSE；两条线/柱对比 Baseline 与 AI。",
    "单幅图。AI 在各日通常低于 Baseline（样本内）。仅 10 天，不能代表季节。",
    "逐日稳定 ≠ 跨河段可推广。",
    "融雪期/枯水期表现待补充。",
)

FIGS["sgs_residual_by_reach.png"] = teach(
    "展示 AI 的学习目标：各河段质量守恒残差 S<sub>sgs</sub> 的分布。",
    "横轴河段，纵轴 S<sub>sgs</sub>（箱线或柱）。",
    "单幅图。R008 残差通常最大，说明干流未解释源汇最多。",
    "残差大 = Baseline 缺口大，也 = 过拟合风险高（特征在河段内近乎常值时尤甚）。",
    "LOO-reach 下 MLP 持出变差，说明这些残差模式没能迁移到未见河段。",
)


header = '''"""Long teaching-style figure explanations for report.html / paper.html.

Every figure gets: 背景与目的 / 如何阅读 / 子图逐一解释 / 曲线含义 / 通俗结论.
Numbers cited are frozen from results/tables/*.csv (see docs/ENGINEERING_NOTES.md).
"""
from __future__ import annotations

'''

body = "FIGURE_TEACH: dict[str, str] = {\n"
for k, v in FIGS.items():
    body += f"    {k!r}: (\n        {v!r}\n    ),\n"
body += "}\n\n\ndef get_teach(filename: str, fallback: str = '') -> str:\n"
body += '    """Return long teaching HTML for a figure filename."""\n'
body += "    return FIGURE_TEACH.get(filename, fallback)\n"

OUT.write_text(header + body, encoding="utf-8")
print(f"Wrote {OUT} with {len(FIGS)} figures, {OUT.stat().st_size/1024:.1f} KB")
missing_expected = [
    "gis_reach_assignment_map.png", "gis_samples_on_network.png", "sample_snap_centerline.png",
    "gis_flow_quiver_Q.png", "gis_flow_quiver_u.png", "gis_streamtube_QW_u.png",
    "gis_network_map_Q.png", "gis_network_map_u.png", "longitudinal_profile_hydraulics.png",
    "cross_section_u_field_panel.png", "planview_velocity_network.png", "temporal_hydraulics.png",
    "gis_network_map_pCO2.png", "carbon_heatmap_pCO2.png", "carbon_heatmap_C_aq.png",
    "longitudinal_profile_carbon.png", "carbon_heatmap_F_CO2_ai.png",
    "gis_network_map_F_CO2_comparison.png", "compare_F_CO2_baseline_vs_ai.png",
    "difference_F_CO2_ai_minus_baseline.png", "temporal_baseline_vs_ai_flux.png",
    "nested_cv_rmse_bar.png", "nested_cv_scatter_holdout.png", "subgroup_rmse_r008_vs_trib.png",
    "ablation_flux_comparison.png", "les_filter_conceptual.png", "filter_scale_sgs.png",
    "filter_scale_sgs_box.png", "identifiability_k_vs_sgs.png", "identifiability_tradeoff.png",
    "dimensionless_coefficients.png", "obs_vs_model_scatter_large.png", "obs_vs_model_scatter.png",
    "obs_vs_model_by_reach.png", "flux_by_reach.png", "seasonal_rmse.png", "sgs_residual_by_reach.png",
]
assert list(FIGS.keys()) == missing_expected, set(missing_expected) - set(FIGS)
print("All 37 manifest keys present.")
