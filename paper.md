# Transport-coupled evaluation of river-network CO₂ closures

**English title:** Transport-coupled evaluation of river-network CO₂ closures: Evidence for practical equifinality under concentration-only observations

**Chinese title:** 河网 CO₂ 闭合的输运耦合评价：浓度单变量观测下的 practical equifinality 证据

**Authors:** 待补充  
**Affiliation:** 待补充  
**Date:** 2026-08-17  
**Figures in paper.html:** 13

## Abstract (English)

Environmental-model evaluation can favor a closure that reproduces concentration while distorting the underlying process partition.
We develop a transport-coupled diagnostic framework for river-network CO₂ using public East River campaign data (HydroShare; n=120; 8 logical reaches).
Leave-one-reach-out held-out C_aq RMSE: Baseline **0.0284**; Residual-AI MLP **0.0573**; RF **0.0745** — residual learners do **not** beat Baseline.
k-correction reaches **0.0244** but coincides with k_eff/k_emp≈3.4e-4 and model flux diagnostic F_CO2 ~3.24→~0.03.
Filter mean |S_sgs|: 1.92→1.00 (sampled cells=6). Sparse Π C RMSE≈0.051 still worse than Baseline.
In-sample R²≈0.997 is appendix-only. Contribution = filter + protocol + practical equifinality evidence, not AI accuracy gains.

## Highlights

1. Reach-held-out Residual-AI does not outperform Baseline (0.0573/0.0745 vs 0.0284).
2. Lower C RMSE from k-correction coincides with model-flux collapse (~3.24→~0.03).
3. Spatial filtering exposes scale dependence and practical S_sgs–k equifinality.

## Keywords

River carbon cycling; environmental model evaluation; transport-coupled validation; spatial coarse-graining; subgrid residual; gas-transfer velocity; practical equifinality; grouped cross-validation

## Paper vs report

This manuscript uses academic EMS language only. Absolute local paths, virtual-environment setup notes, and pipeline script filenames as process narrative belong in the research report, not here.

## IMRaD outline

1. Introduction — evaluation gap; concentration vs process allocation; East River setting
2. Methods — data; quasi-steady transport; filter-induced S_sgs; three closures; leave-one-reach-out CV; equifinality diagnostic; sparse Π
3. Results — negative Residual-AI; concentration–flux disagreement; filter scale; sparse Π
4. Discussion — failed generalization; practical equifinality; limitations
5. Conclusions — three hard points
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

## Tables (see paper.html)

- Table M / Table 4: leave-one-reach-out main metrics
- Table 5: subgroup metrics
- Table 6: filter scale
- Tables 7–8: identifiability + sparse Π

## DO NOT CLAIM

- Residual-AI beats Baseline on held-out C_aq
- in-sample R²=0.997 as skill
- F_CO2 independently validated
- universal SGS law / CONUS / CH4 / StreamPULSE / SINDy

*Full self-contained HTML: paper.html*
