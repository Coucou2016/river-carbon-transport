# East River CO₂ 河网碳输运 — 公开再分析报告

**报告日期：** 2026 年 9 月 28 日  
**冻结运行：** `20260919_remediation`（与 paper / nested_cv_summary 同源）  
**内嵌图表：** 40 幅（精选，见 report.html；每图附五段教学讲解）  
**阅读建议：** 术语表 → 表 2（逻辑河段 / 简化干流树）→ 表 M / 表 4 → 滤波（无 study_reach）→ 可辨识性 / 无量纲式

## 摘要

对 Saccardi & Winnick (2021) 公开观测 + NHD/USGS 再分析（非自采）。分组 LOO-reach（折内目标）：
Baseline C RMSE **0.0485**；MLP **0.0507**（整体高于 Baseline，不作成功主张）；
RF 0.0557；k 修正 0.0485（55% k_need 不可行）。
通量诊断为重叠样点面积量（非研究区总量）。滤波正式尺度 native / merge_2x / merge_3x / merge_4x / merge_6x / merge_8x / merge_12x / merge_16x；study_reach 排除。
干流 R008_S* 为逻辑报告树，非已核验 NHD 压缩。

## 河网 8 段（四种估计量，数字由机器表动态生成）

| 编号 | 河流 | 角色 | 汇入干流段 | 域长 (km) | 已分配走廊线 | ·GNIS 匹配 | ·最近样点 | 逻辑路由段 | 采样控制体 | 战役样点 | 说明 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R001 | Bradley Creek | Tributary | R008_S4 | 0.100 † | 0 | 0 | 0 | 1 | 1 | 1 | 支流源头，n=1 仅作示意 |
| R002 | Bradley Meadow | Tributary | R008_S4 | 0.092 † | 15 | 0 | 15 | 1 | 3 | 3 | 草甸河段，连接 Bradley 与 Rock |
| R003 | Rock Creek | Tributary | R008_S5 | 4.145 | 29 | 10 | 19 | 1 | 15 | 15 | Rock 溪，多样本支流 |
| R004 | Copper Creek | Tributary | R008_S6 | 3.568 | 140 | 23 | 117 | 1 | 24 | 24 | Copper 溪，走廊线最多 |
| R005 | Gothic Creek | Tributary | R008_S5 | 2.504 † | 6 | 0 | 6 | 1 | 17 | 17 | Gothic 支流，多样本 |
| R006 | Quigley Creek | Tributary | R008_S2 | 0.069 † | 8 | 6 | 2 | 1 | 1 | 1 | 单样本，仅作示意 |
| R007 | Rustlers Gulch | Tributary | R008_S3 | 0.050 † | 2 | 0 | 2 | 1 | 1 | 1 | 单样本，仅作示意 |
| R008 | East River | Mainstem | outlet | 11.313 | 193 | 46 | 147 | 6 | 58 | 58 | 干流 Almont 上游，样点最密 |

## 图表清单

### 论文正文图（与手稿 Figure 1–10 同序同号）

- `les_filter_conceptual.png` — **图 1** 单元 DAG 算子两条聚合规则的并排示意：（a）同一河道上的串行收缩，Q 沿链恒定、ΣQC 沿链累加而非重新平均；（b）汇流口的并行汇合，Qout=Q1+Q2、Cout 按流量加权（非算术平均），面积相加、同一单元内重复观测不增加面积。两幅均为**示意、非按比例**，仅陈述算子规则，**不作为**某次运行已实现守恒的证据。
- `figure2_reach_assignment_and_samples.png` — **图 2** （a）逻辑河段指派：NHDPlus HR 河线按 GNIS 名称匹配与样点邻近度归入 R001–R008（R001 在本渲染中无指派线段）；（b）120 个战役样点在同一位底图上的位置，颜色表示逻辑河段，R008 有 58 点。细箭头仅表示数字化流向，故本图是**位置参照**、**不是**流向有效性检验。两幅均为 Web Mercator（EPSG:3857），含比例尺与指北针；底图为 Esri World Imagery 卫星瓦片，瓦片本地缓存并记录来源与哈希（见图旁 JSON 清单）。
- `nested_cv_rmse_bar.png` — **图 3** 分组留一河段 + 输运耦合交叉验证（120 样点、8 个河段组、固定随机种子）：Baseline、Residual-AI（MLP / random forest）与 k 修正的持出 Caq RMSE。实心柱为按样点加权的合并指标，空心标记为背后的各河段值，可对照河段离散度阅读；虚线为 Baseline 水平。没有任何闭合把合并 RMSE 降到零残差 Baseline 之下。
- `nested_cv_scatter_holdout.png` — **图 4** 留一河段分组评估下 Residual-AI（MLP）的观测 vs 输运预测持出 Caq（n=120）；颜色表示逻辑河段，虚线为 1:1。统计量由这些点直接计算，键可追溯至 `data_proc/nested_cv_holdout_predictions.csv`。内嵌小图放大低浓度区间（多数干流样点所在）；极端点保留、不作剔除。本冻结运行中 480 行持出预测**全部**未激活 Ssgs 物理下界，故残差闭合不含裁剪后处理；若该计数非零将显式报告。
- `subgroup_rmse_r008_vs_trib.png` — **图 5** 子组 Caq RMSE：Baseline、Residual-AI（MLP 与 random forest）与 k 修正。R008 含 58 个样点；多样本支流组 R002–R005 含 59 个样点；R001、R006、R007 为单样本逻辑河段，单独展示而不并入比较。
- `supp_flux_diagnostics.png` — **图 6** 分组留一河段评估下 Baseline、Residual-AI（MLP）与 k 修正的模型 FCO₂ 诊断。（a）面积加权模型通量诊断 ΣF·A（mol d<sup>−1</sup>），与表 2 同一估计量，故二者一致；（b）该诊断的各河段构成，显示残差闭合总量集中在少数河段；（c）样点级 keff/kemp 与 k 修正模型通量诊断的关系。这些量是 k(C−Ceq) 形式的**模型诊断**，既非研究区总量、也非独立验证的逸散观测；面板（a）背后的未面积加权密度和在补充表中保留。
- `filter_scale_sgs.png` — **图 7** 仅限已解析尺度（native 至 16× 合并；study_reach 因整河段收缩形成 DAG 环而排除）的滤波尺度依赖。上panel：唯一单元平均与中位 |Ssgs| 对滤波尺度 Δx（对数轴），并标出实际平均与中位控制长度；下panel：Ssgs 的单元级方差，次轴为中位控制长度。八个已解析尺度上（Δx ≈ 587–1615 m）唯一单元平均 |S| 稳定在 3.54–3.84 mol m<sup>−2</sup> d<sup>−1</sup> 的窄带内；这是稀疏同步覆盖下守恒算子的**采样条件敏感性**，不是经 study_reach 聚合的尺度不变性主张。
- `filter_scale_sgs_box.png` — **图 8** 日期×单元记录层级上、各已解析滤波尺度（native 至 16× 合并）的 |Ssgs| 分布，每组上方标注记录数。散点已展示全部点，故不再显示 flier；多样本日期-单元记录不是独立抽样，同一单元内重复观测不增加面积。study_reach 聚合因与图 7 相同的收缩环原因排除。日期×单元记录数（native 的 43 至最粗尺度的 27）与唯一空间单元数（39 至 22）不同，因为同一单元可在多日内被采样。
- `dimensionless_coefficients.png` — **图 9** 稀疏无量纲闭合的标准化 LASSO 系数，目标在折内重建（五个候选 Π 项保留四个；仅 log₁₀(Re) 收缩至零）。系数数值为零的项画成**显式零柱**而非省略，便于读者看到哪些候选被丢弃及其原因。所示关系为 S* ≈ 1.386 − 4.777·Fr_z − 0.6142·Slope_z − 2.295·(h/W)_z − 2.75·log10(Da)_z。S* 的留一河段 R² 为 −2.58334（n=120）；稀疏分支仍为**临时性**结论。
- `equifinality_objective_surface.png` — **图 10** 准稳态平衡的模型无关实践等终性诊断（n=120）。这是条件模型诊断：目标函数在所有样点间共享单一 k 尺度与单一源项，并固定观测上游状态。（a）单个代表性样点的单样本目标函数 log₁₀ J(k, S)；深红线为精确零谷 S = S_diag + (C_obs − C_eq)(k − k_emp)，故单一浓度观测使 (k, S) 代数上欠定。（b）在均匀 k 尺度 α = k/k_emp 与均匀源项 S 上的合并目标函数 J(α, S)；Baseline、k 修正与 Residual-AI 点为描述性中位标记，仅用于定位，非拟合的河网运行点。（c）轮廓 SSE J_prof(α) = min_S J(α, S)；轮廓平坦，最小值在 α ≈ 0.1795 附近（轮廓 RMSE 0.0343 mol m<sup>−3</sup>）。

### 附录教学图（附录图 A1 起）

- [network] **附录图 A1** `gis_reach_assignment_map.png` — 研究河段 R001–R008 与 NHD 河网矢量线的对应关系（393 段真实线几何）。
- [network] **附录图 A2** `gis_samples_on_network.png` — 战役样点（n=120）叠加于 NHD 河网线。
- [network] **附录图 A3** `sample_snap_centerline.png` — 120 个 GPS 样点捕捉到最近 NHD 中心线（圆点=野外坐标，叉号=线上投影）。
- [network] **附录图 A4** `gis_flow_quiver_Q.png` — 平面流量场 quiver 图：箭头指向下游，颜色/长度 ∝ Q。
- [network] **附录图 A5** `gis_flow_quiver_u.png` — 平面流速场 quiver 图：箭头指向下游，颜色/长度 ∝ u。
- [network] **附录图 A6** `gis_streamtube_QW_u.png` — streamtube 示意：线宽 ∝ Q，颜色 ∝ u（NHD 真实线几何）。
- [hydro] **附录图 A7** `gis_network_map_Q.png` — GIS 河网线图：河段平均流量 Q（m³/s），线宽 ∝ Q。
- [hydro] **附录图 A8** `gis_network_map_u.png` — GIS 河网线图：流速 u（m/s）。
- [hydro] **附录图 A9** `longitudinal_profile_hydraulics.png` — 沿程水动力剖面（链距 km）：h、u、Q。
- [hydro] **附录图 A10** `cross_section_u_field_panel.png` — 各河段理想化 u(y,z) 场（梯形断面，抛物线垂向分布）。
- [hydro] **附录图 A11** `planview_velocity_network.png` — 平面流速分布：线宽 ∝ Q，颜色 ∝ |u|。
- [hydro] **附录图 A12** `temporal_hydraulics.png` — 战役期流域平均水动力时间序列（Q、u）。
- [carbon] **附录图 A13** `gis_network_map_pCO2.png` — GIS 河网线图：pCO₂（µatm）空间格局。
- [carbon] **附录图 A14** `carbon_heatmap_pCO2.png` — pCO₂ 河段 × 日期热图（战役期 10 天）。
- [carbon] **附录图 A15** `carbon_heatmap_C_aq.png` — 观测 Caq 河段 × 日期热图。
- [carbon] **附录图 A16** `longitudinal_profile_carbon.png` — 沿程碳状态剖面：pCO₂、Caq、DIC、DOC。
- [carbon] **附录图 A17** `carbon_heatmap_F_CO2_ai.png` — AI 耦合 FCO₂ 河段 × 日期热图。
- [comparison] **附录图 A18** `gis_network_map_F_CO2_comparison.png` — Baseline vs AI FCO₂ 并列 GIS 对比（统一色标）。
- [comparison] **附录图 A19** `compare_F_CO2_baseline_vs_ai.png` — 各河段 FCO₂：Baseline vs AI 并列柱图。
- [comparison] **附录图 A20** `difference_F_CO2_ai_minus_baseline.png` — AI − Baseline CO₂ 通量差值（按河段）。
- [comparison] **附录图 A21** `temporal_baseline_vs_ai_flux.png` — 战役期日均 CO₂ 通量演化：Baseline vs AI。
- [nestedcv] **附录图 A22** `ablation_flux_comparison.png` — 三种闭合的持出样本 FCO₂ 合计与通量 RMSE（模型通量诊断）。
- [innovation] **附录图 A23** `identifiability_k_vs_sgs.png` — 可辨识性：keff 与隐含 Ssgs，以及 Residual-AI 持出源项对照。
- [innovation] **附录图 A24** `identifiability_tradeoff.png` — 浓度–通量权衡：keff/kemp 与三种闭合的持出 RMSE / 通量合计。
- [validation] **附录图 A25** `obs_vs_model_scatter_large.png` — 验证散点总览（大图）：圆点 = Baseline，三角 = AI；颜色区分河段（n=120）。
- [validation] **附录图 A26** `obs_vs_model_scatter.png` — 分模型验证散点：左 Baseline，右 AI（分河段着色，附 RMSE 与 R²）。
- [validation] **附录图 A27** `obs_vs_model_by_reach.png` — 八个河段各自的验证小图：每格对应表 2 中的一条河。
- [validation] **附录图 A28** `flux_by_reach.png` — 各河段平均 CO₂ 向大气释放通量 FCO₂（Baseline vs AI 柱图）。
- [validation] **附录图 A29** `seasonal_rmse.png` — 战役期逐日预测误差 RMSE（Caq）：Baseline vs AI。
- [validation] **附录图 A30** `sgs_residual_by_reach.png` — 亚网格残差 Ssgs 各河段分布（AI 需要学习的“缺口”）。

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
