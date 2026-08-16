# East River CO₂ 河网碳输运 — 真实数据验证报告

**报告日期：** 2026 年 8 月 16 日  
**内嵌图表：** 37 幅（精选，见 report.html；每图附五段教学讲解）  
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

## 图表清单（精选 37 幅）

- [network] `gis_reach_assignment_map.png` — **图 1** 研究河段 R001–R008 与 NHD 河网矢量线的对应关系（393 段真实线几何）。
- [network] `gis_samples_on_network.png` — **图 2** 战役样点（n=120）叠加于 NHD 河网线。
- [network] `sample_snap_centerline.png` — **图 2b** 120 个 GPS 样点捕捉到最近 NHD 中心线（圆点=野外坐标，叉号=线上投影）。
- [network] `gis_flow_quiver_Q.png` — **图 3** 平面流量场 quiver 图：箭头指向下游，颜色/长度 ∝ Q。
- [network] `gis_flow_quiver_u.png` — **图 4** 平面流速场 quiver 图：箭头指向下游，颜色/长度 ∝ u。
- [network] `gis_streamtube_QW_u.png` — **图 5** streamtube 示意：线宽 ∝ Q，颜色 ∝ u（NHD 真实线几何）。
- [hydro] `gis_network_map_Q.png` — **图 6** GIS 河网线图：河段平均流量 Q（m³/s），线宽 ∝ Q。
- [hydro] `gis_network_map_u.png` — **图 7** GIS 河网线图：流速 u（m/s）。
- [hydro] `longitudinal_profile_hydraulics.png` — **图 8** 沿程水动力剖面（链距 km）：h、u、Q。
- [hydro] `cross_section_u_field_panel.png` — **图 9** 各河段理想化 u(y,z) 场（梯形断面，抛物线垂向分布）。
- [hydro] `planview_velocity_network.png` — **图 10** 平面流速分布：线宽 ∝ Q，颜色 ∝ |u|。
- [hydro] `temporal_hydraulics.png` — **图 11** 战役期流域平均水动力时间序列（Q、u）。
- [carbon] `gis_network_map_pCO2.png` — **图 12** GIS 河网线图：pCO₂（µatm）空间格局。
- [carbon] `carbon_heatmap_pCO2.png` — **图 13** pCO₂ 河段 × 日期热图（战役期 10 天）。
- [carbon] `carbon_heatmap_C_aq.png` — **图 14** 观测 Caq 河段 × 日期热图。
- [carbon] `longitudinal_profile_carbon.png` — **图 15** 沿程碳状态剖面：pCO₂、Caq、DIC、DOC。
- [carbon] `carbon_heatmap_F_CO2_ai.png` — **图 16** AI 耦合 FCO₂ 河段 × 日期热图。
- [comparison] `gis_network_map_F_CO2_comparison.png` — **图 17** Baseline vs AI FCO₂ 并列 GIS 对比（统一色标）。
- [comparison] `compare_F_CO2_baseline_vs_ai.png` — **图 18** 各河段 FCO₂：Baseline vs AI 并列柱图。
- [comparison] `difference_F_CO2_ai_minus_baseline.png` — **图 19** AI − Baseline CO₂ 通量差值（按河段）。
- [comparison] `temporal_baseline_vs_ai_flux.png` — **图 20** 战役期日均 CO₂ 通量演化：Baseline vs AI。
- [nestedcv] `nested_cv_rmse_bar.png` — **图 N1** 嵌套交叉验证：Baseline / Residual-AI / k 修正的持出样本 Caq RMSE（论文主图）。
- [nestedcv] `nested_cv_scatter_holdout.png` — **图 N2** 留一河段持出：观测 vs 预测 Caq（Residual-AI，大圆点按河段着色）。
- [nestedcv] `subgroup_rmse_r008_vs_trib.png` — **图 N3** 子组误差：R008 干流 vs 多样本支流 vs 单样本河段（示意）。
- [nestedcv] `ablation_flux_comparison.png` — **图 N4** 三种闭合的持出样本 FCO₂ 合计与通量 RMSE（模型通量诊断）。
- [innovation] `les_filter_conceptual.png` — **图 I1** LES 类比过滤概念：细 NHD 线段 → 滤波窗 Δx → 粗控制体上的 Ssgs。
- [innovation] `filter_scale_sgs.png` — **图 I2** 滤波尺度实验：平均 |Ssgs| 与方差随 Δx（真实样点捕捉到粗化 NHDPlus HR 线）。
- [innovation] `filter_scale_sgs_box.png` — **图 I2b** 各滤波尺度上 120 个真实样点的 |Ssgs| 分布。
- [innovation] `identifiability_k_vs_sgs.png` — **图 I3** 可辨识性：keff 与隐含 Ssgs，以及 Residual-AI 持出源项对照。
- [innovation] `identifiability_tradeoff.png` — **图 I3b** 浓度–通量权衡：keff/kemp 与三种闭合的持出 RMSE / 通量合计。
- [innovation] `dimensionless_coefficients.png` — **图 I4** 无量纲 Π 群稀疏闭合系数（标准化 LASSO；PySINDy 未安装）。
- [validation] `obs_vs_model_scatter_large.png` — **图 21** 验证散点总览（大图）：圆点 = Baseline，三角 = AI；颜色区分河段（n=120）。
- [validation] `obs_vs_model_scatter.png` — **图 22** 分模型验证散点：左 Baseline，右 AI（分河段着色，附 RMSE 与 R²）。
- [validation] `obs_vs_model_by_reach.png` — **图 23** 八个河段各自的验证小图：每格对应表 2 中的一条河。
- [validation] `flux_by_reach.png` — **图 24** 各河段平均 CO₂ 向大气释放通量 FCO₂（Baseline vs AI 柱图）。
- [validation] `seasonal_rmse.png` — **图 25** 战役期逐日预测误差 RMSE（Caq）：Baseline vs AI。
- [validation] `sgs_residual_by_reach.png` — **图 26** 亚网格残差 Ssgs 各河段分布（AI 需要学习的“缺口”）。

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
