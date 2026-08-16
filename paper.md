# 河网 CO₂ 输运的多尺度过滤与亚网格闭合可辨识性

**English title:** Transport-coupled evaluation of river-network CO₂ closures: Evidence for practical equifinality under concentration-only observations

**Authors:** 待补充  
**Affiliation:** 待补充  
**Date:** 2026-08-16  
**Figures in paper.html:** 13

## Abstract

环境模型可能通过过程补偿得到相近浓度误差。本文构建河网 CO₂ 空间过滤与输运耦合评价框架（East River，n=120；reach-held-out）。
主结果：Residual-AI **没有**优于 Baseline（MLP 0.0573 / RF 0.0745 vs Baseline 0.0284）。
k 修正略降到 0.0244，并伴随 k_eff/k_emp≈3.4e-4 与 F_CO2 ~3.24→~0.03（共现诊断）。
滤波 mean |S_sgs|：1.92→1.00（研究河段有样点单元=6）。稀疏 Π 式可解释，嵌套 CV C RMSE≈0.051 仍差于 Baseline。
贡献是可操作过滤定义、输运耦合协议与 practical equifinality 诊断，不是精度提升。样本内 R²≈0.997 仅附录。

## Keywords

河网 CO₂ 输运；亚网格闭合；可辨识性；LES 过滤；reach-held-out 分组交叉验证；物理约束机器学习；East River

## IMRaD outline

1. Introduction — 科学问题与负结果框架
2. Methods — 数据、过滤、三种闭合、嵌套 CV、可辨识性、稀疏 Π
3. Results — 先负精度，再滤波 / 稀疏式 / k–S 权衡（见表与图）
4. Discussion — 浓度不足以评价闭合；需要独立通量
5. Conclusions — 三条硬结论
6. Data availability
7. References

## Paper figures

- `les_filter_conceptual.png` — Fig. 1 LES 类比过滤概念：细 NHD 线段 → 滤波窗 Δx → 粗控制体上的 Ssgs。
- `gis_reach_assignment_map.png` — Fig. 2a GIS 河网：研究河段 R001–R008 与 NHD 矢量线对应。
- `gis_samples_on_network.png` — Fig. 2b 120 个战役样点叠加于 NHD 河网（R008 n=58 主导）。
- `nested_cv_rmse_bar.png` — Fig. 3 reach-held-out 分组交叉验证：Baseline / Residual-AI / k 修正的持出 Caq RMSE（主图）。
- `nested_cv_scatter_holdout.png` — Fig. 4 留一河段持出：观测 vs 预测 Caq（Residual-AI MLP）。
- `identifiability_k_vs_sgs.png` — Fig. 5 可辨识性：keff 与隐含 Ssgs，及 Residual-AI 持出源项对照。
- `filter_scale_sgs.png` — Fig. 6 滤波尺度：平均 |Ssgs| 与方差随 Δx。
- `dimensionless_coefficients.png` — Fig. 7 无量纲 Π 群稀疏闭合系数（标准化 LASSO）。
- `subgroup_rmse_r008_vs_trib.png` — Fig. S1 子组误差：R008 vs 多样本支流 vs 单样本示意河段。
- `ablation_flux_comparison.png` — Fig. S2 三种闭合的持出 FCO₂ 合计与通量 RMSE（模型诊断）。
- `identifiability_tradeoff.png` — Fig. S3 浓度–通量权衡：keff/kemp 与持出 RMSE / 通量合计。
- `filter_scale_sgs_box.png` — Fig. S4 各滤波尺度上 120 样点 |Ssgs| 分布。
- `obs_vs_model_scatter_large.png` — Fig. A1 样本内散点（附录；R²≈0.997 为过拟合肖像，非主结论）。

## Tables (see paper.html for full HTML tables)

- Table M / Table 4: nested CV main metrics (`paper_main_results.csv`, `nested_cv_metrics.csv`)
- Table 5: subgroup metrics (`subgroup_metrics.csv`)
- Table 6: filter scale (`paper_filter_scale.csv`)
- Tables 7–8: identifiability + sparse Π

## DO NOT CLAIM

- Residual-AI beats Baseline on held-out C_aq
- in-sample R²=0.997 as skill
- F_CO2 independently validated
- universal SGS law / CONUS / CH4 / StreamPULSE / SINDy

*Full self-contained HTML: paper.html*
