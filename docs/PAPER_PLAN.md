# 论文写作与实验实施计划

**工作目录：** `d:\Projects\20260611-river-carbon-transport`  
**数据政策：** 仅使用真实公开观测（HydroShare East River 战役水样 + USGS 日流量 + NHD/NHDPlus HR 矢量）。禁止合成观测，禁止把样本内 \(R^2=0.997\) 写成精度结论。  
**已由嵌套交叉验证否证的表述：** “AI 亚网格提高了持出样本 \(C_\mathrm{aq}\) 预测精度”。留一河段协议下 Residual-AI MLP RMSE = **0.057**，Baseline = **0.028**。

---

## 推荐论文定位

**不要写的故事：** “我们用机器学习把河网 \(p\mathrm{CO}_2\) / \(C_\mathrm{aq}\) 预测精度提高了。”  
该命题已被嵌套交叉验证证伪：在先预测闭合、再代入同一准稳态输运方程的协议下，Residual-AI **未能**优于 Baseline；样本内 \(R^2=0.997\) 仅能作为过拟合附录。

**要写的故事：** 把大涡模拟（LES）式空间过滤显式写成河网碳模型的亚网格源汇 \(S_\mathrm{sgs}\)，在公开 East River 河网矢量上做多滤波尺度 \(\Delta x\) 实验，并证明在当前观测尺度下 \(S_\mathrm{sgs}\) 与气体交换系数 \(k\) **不可联合辨识**。负结果本身是方法学贡献。

### 推荐中文题名方向

> **河网 \(\mathrm{CO}_2\) 输运的多尺度过滤与亚网格闭合可辨识性：East River 公开数据上的物理约束机器学习实验**

### 推荐英文题名方向（The Innovation / GBC / WRR methods 风格）

> **Multiscale filtering and identifiability of subgrid closures for river-network \(\mathrm{CO}_2\) transport: a physics-constrained machine-learning experiment on public East River data**

### 一句话框架

LES-analog filter + residual closure + identifiability of \(S_\mathrm{sgs}\) versus \(k\)，使用 Saccardi & Winnick (2021) 公开 East River 数据（HydroShare），辅以 Raymond et al. (2012) \(k_{600}\) 与 USGS 09112500。

---

## 1. 能取得什么样的创新点（诚实分层）

### 1.1 可发表的创新（推荐主线，必须做）

**（1）方法创新：河网碳模型的 LES 过滤书写与多 \(\Delta x\) 实验。**  
将 Gao 等 *The Innovation* 稿件中的“大涡类比”落到可操作定义：对 NHD / NHDPlus HR 线段做空间粗化（native → \(\times 2\) 合并 → \(\times 4\) 合并 → 研究河段），把样点捕捉到粗化后的控制体，按质量守恒重算残差 \(S_\mathrm{sgs}(\Delta x)\)。这是 Gao 思路的可复现版本。现有嵌套 CV 失败可解释为：**在当前观测尺度（8 条逻辑河段、\(n=120\)）上，闭合在持出样本上不可辨识 / 不可推广**，而不是“AI 算法没调好”。

**（2）可辨识性创新：同一观测下 \(S_\mathrm{sgs}\) 与 \(k\)-correction 的权衡。**  
本项目嵌套 CV 已给出新结果：\(k\) 修正把持出 \(C_\mathrm{aq}\) RMSE 从 0.028 略降到 0.024，但通过把 \(k_\mathrm{eff}\) 压到经验 \(k\) 的约千分之一，使 \(F_{\mathrm{CO}_2}\) 合计从 Baseline 的约 3.2 塌缩到约 0.03。物理含义是气体交换与源汇的 **equifinality**：准稳态平衡

\[
\frac{Q}{A}(C_\mathrm{in}-C) + S_\mathrm{sgs} - k(C-C_\mathrm{eq})=0
\]

在缺少独立通量约束时，增大 \(S_\mathrm{sgs}\) 与减小 \(k\) 对浓度几乎等价，对逸散通量则完全相反。这是主文应强调的新结果，不是精度竞赛的脚注。

**（3）无量纲闭合形式：\(\Pi\) 群稀疏表达式。**  
用 \(\mathrm{Fr},\,\mathrm{Re},\,\mathrm{Da},\,h/W,\,\mathrm{Slope}\) 把闭合写成

\[
S_\mathrm{sgs}^* = \mathcal{F}(\mathrm{Fr},\,\mathrm{Re},\,\mathrm{Da},\,h/W,\,S_0)
\]

已有全特征 LASSO 显示 \(\mathrm{Fr}/\mathrm{Slope}/\mathrm{Da}\) 主导。即便持出预测弱，**可解释的稀疏式**仍可发表（符号回归 / 标准化 LASSO 系数），贡献在“形式”而不在“RMSE 金牌”。

**（4）验证协议创新：嵌套 CV + 按河段样本量分层。**  
先在训练折上预测闭合（\(S_\mathrm{sgs}\) 或 \(k_\mathrm{eff}\)），再代入与 Baseline 相同的输运方程，只对持出样本计 \(C_\mathrm{aq}\) 与 \(F_{\mathrm{CO}_2}\)。按河段样本量分层：R008（\(n=58\)）为干流主证据；R002–R005 为多样本支流；R001/R006/R007（各 \(n=1\)）仅作示意、不均等权重。该方法学适合写入 Methods，并作为对“随机划分 + 样本内 \(R^2\)”的纠正。

### 1.2 不要当主创新的

| 表述 | 原因 |
|------|------|
| “AI 亚网格提高了预测精度” | 嵌套 CV 否定（MLP 0.057 vs Baseline 0.028） |
| 完整 RHWQEC 系统 | 超出当前代码与数据；属后续工程 |
| \(\mathrm{CH}_4\) 耦合 | 本战役无甲烷通量；需 GRiMeDB 等外源 |
| CONUS 全境推演 | 无全国训练标签；最多做结构对照 |
| 样本内 \(R^2=0.997\) 作为主结论 | 过拟合；附录 only |

### 1.3 创新点与“负结果”如何共存

主贡献是 **问题的适定化**（filter 定义、\(\Delta x\) 依赖、\(S\)–\(k\) 不可辨识、分层验证协议），不是精度提升。Methods 论文完全可以建立在“当前数据下闭合不可推广”之上；Discussion 应明确：要辨识 \(S_\mathrm{sgs}\)，需要独立的气体交换或通量约束，而不是更多黑箱拟合。

---

## 2. 现有库 / 代码能实现什么

### 2.1 仓库映射（已存在）

| 组件 | 路径 | 论文中的角色 |
|------|------|----------------|
| 准稳态 1D 输运 | `src/03_baseline_transport.py` | Baseline：\(S_\mathrm{sgs}=0\)，Raymond \(k\) |
| 残差目标 | `src/05_compute_residual_sgs.py` | 战役样点配对残差 + \(\Pi\) 特征 |
| 稀疏 / 树 / MLP 训练 | `src/06_train_sgs_model.py` | LASSO 已选出 Fr/Slope/Da |
| 样本内耦合（附录） | `src/07_coupled_prediction.py` | 乐观拟合，非主表 |
| GIS 河网 | `src/10_gis_network_viz.py` | Fig. 2 类图；GNIS + 最近 GPS |
| 嵌套 CV | `src/12_nested_cv_transport.py` | **主精度表**；三方案消融 |
| 真实数据守卫 | `src/real_data_guard.py` | 禁止合成回退 |
| Raymond \(k_{600}\) | `src/04_estimate_k.py` | \(\ln k_{600}=5.139+0.594\ln u+0.403\ln S_0\) |
| 无量纲数 | `src/utils.py` | Fr, Re, Pe, Da |

### 2.2 本计划新增（必须实现）

| 实验 | 脚本 | 产物 |
|------|------|------|
| 多滤波尺度 | `src/13_filter_scale_sgs.py` | `filter_scale_metrics.csv`, `filter_scale_sgs.png`, 概念图 |
| \(S\)–\(k\) 可辨识性 | `src/14_identifiability_ksgs.py` | `identifiability_k_vs_sgs.png` + 表 |
| 无量纲稀疏闭合 | `src/15_dimensionless_sparse.py` | `dimensionless_coefficients.png` + 表达式；嵌套 CV |

### 2.3 库能力（现在就能跑）

- **geopandas / shapely：** 粗化 NHD 线段、样点捕捉、长度 \(\Delta x\)。优先 `data_raw/nhdplus_hr/nhdplus_hr_huc14020001_flowlines.gpkg`（HUC 14020001，8212 条；研究廊道缓冲后约 500+ 条）；若缺失则 `East_River_Lines.shp`（393 段）。
- **sklearn：** `StandardScaler` + `Lasso` / `ElasticNet`；嵌套 CV 用 `LeaveOneGroupOut`（已在 stage 12）。
- **xgboost：** \(k\)-correction 已完成，本计划只做后处理，不重训。
- **pysindy：** 尝试安装；失败则 **不阻塞**，改用 LASSO/ElasticNet。表达式仍可写成 \(S_\mathrm{sgs}^*\sim a\,\mathrm{Fr}+b\,S_0+c\,\mathrm{Da}\)。
- **matplotlib / seaborn：** 中文字体经 `plot_style.apply_plot_style` 在 seaborn 之后调用；大标记；`dpi=200`。

### 2.4 现在就能做、且不需要新野外数据的分析

1. 将 393（或廊道内 HR）线段粗化为至少 3 个尺度，重算 \(S_\mathrm{sgs}(\Delta x)\)，画 \(\overline{|S_\mathrm{sgs}|}\) 与方差对 \(\Delta x\)。
2. 用已有 nested-CV 持出预测：Baseline \(C\)、Residual-AI \(C\) 与 \(S_\mathrm{sgs}\)、\(k\)-correction \(C\) 与 \(k_\mathrm{eff}\)，画 \(k_\mathrm{eff}\) 对隐含 \(S_\mathrm{sgs}\) 的权衡。
3. 仅用无量纲特征做稀疏回归，报告可解释式，并做嵌套 CV（**预期弱，如实报告**）。
4. 嵌套 CV 主表保持不动：不重写、不美化 Residual-AI 的持出误差。

### 2.5 现在做不到、不要写进 Methods 当已完成

- 符号回归若 pysindy 无法安装：改 LASSO，不虚构 SINDy 方程。
- TELEMAC 二维、PINN Saint-Venant、CONUS 全境反演：无网格/无标签。
- StreamPULSE East River 代谢时间序列：门户检索已失败（0 站点），**不再作为主路径重试**。

---

## 3. 公开资料验证

### 3.1 已经在手（主验证，不可替换）

| 资料 | 标识 | 用途 |
|------|------|------|
| East River 水化学 / \(p\mathrm{CO}_2\) | HydroShare `9f907b46baa848e180c49339d605bf31` | 120 个战役样点（2019-08-02–11） |
| DIC 补充包（shp、坡度、同步 Q） | HydroShare `2a2132999fb84214aad0596783812db2` | `East_River_Lines.shp`、`slopetable.csv`、`Q elivation regreshion.csv` |
| 干流流量 | USGS **09112500** East River at Almont | 样点日 Q（R008） |
| NHDPlus HR | HU4 1402 / HUC **14020001** | 8212 flowlines；滤波粗化优先用此 gpkg |
| \(k_{600}\) | Raymond et al. (2012) | 经验气体交换，非实测通量 |

样点结构（必须在文中写明）：R001=1，R002=3，R003=15，R004=24，R005=17，R006=1，R007=1，R008=**58**。单样本河段为示意图，不与干流均等权重。

### 3.2 拟增加的一项外部公开对照（成功则写入，失败则记录）

**优先 A：** [Fluvial-UMass/CONUS_carbon](https://github.com/Fluvial-UMass/CONUS_carbon) — 若仓库可克隆，仅对照其河网碳通量产品的**结构 / 变量字典 / 某一流域子集的公开栅格或表**，**不**把 CONUS 产品当作本战役的第二套野外观测，也**不**声称跨流域精度验证。

**优先 B（若 A 失败）：** 以 Saccardi & Winnick (2021, *GBC*) 原文网络模型为 **reproduction baseline**：本仓库 1D 准稳态模型是其公开数据上的简化实现，对照文献中的过程解释（干流高 \(p\mathrm{CO}_2\)、支流源汇），而不是第二场采样。

**禁止：** 编造第二次野外战役；把 StreamPULSE 无站点写成“已验证”；用合成序列补齐 Alk/N/P。

### 3.3 明确不再作为主路径的数据

- StreamPULSE：East River / Gothic / Coal Creek / Crested Butte 关键词 **0 匹配**；查询接口曾 HTTP 500。不重试为主路径。
- WQP 同日合并：**0/120**。不再为论文主文重复拉取。

---

## 4. 论文结构（IMRaD）

### 4.1 Introduction

1. 河网是陆地–大气碳交换的活跃界面（Battin et al., 2023 及后续综述）。
2. 现有流域模型在河段尺度平均掉湍流混合、地下水 \(\mathrm{CO}_2\)、局地代谢 → 需要亚网格源汇。
3. Gao 等 *The Innovation* 稿件提出 LES 类比 + AI 闭合；本文把它写成可计算的过滤算子，而不是精度宣言。
4. East River 是理想的公开试验床：Saccardi & Winnick (2021) 提供战役 \(p\mathrm{CO}_2\) 与河网几何；Raymond et al. (2012) 提供 \(k_{600}\)；Yuval & O’Gorman (2020) 代表“物理约束 ML 闭合”的气象学先例（残差学习，而非替代控制方程）。
5. 科学问题：（i）\(S_\mathrm{sgs}\) 是否随 \(\Delta x\) 系统变化？（ii）\(S_\mathrm{sgs}\) 与 \(k\) 在浓度观测下能否辨识？（iii）无量纲稀疏式能否在嵌套 CV 下推广？

### 4.2 Methods

1. **研究区与数据：** HUC 14020001，120 样点，8 逻辑河段，NHD 393 / HR 8212，USGS 09112500。真实数据唯一。
2. **过滤算子：** 将 NHD 线段按沿程链距在同一 `reach_id` 内每 \(N\) 段合并；\(\Delta x=\) 有样点的粗化单元平均长度。样点捕捉到粗化线后，按准稳态质量守恒重算 \(S_\mathrm{sgs}\)。
3. **基准输运：** `03_baseline_transport.py` 的准稳态平流–逸散平衡。
4. **三种闭合：** (A) Baseline \(S=0\)；(B) Residual-AI（MLP / RF 学习 \(S_\mathrm{sgs}\)）；(C) \(k_\mathrm{eff}=k_\mathrm{emp}\exp(g_\theta(X))\)。
5. **嵌套 CV：** 留一河段、留一日期；先预测闭合再代入物理；分层报告。
6. **可辨识性诊断：** \(S_\mathrm{implied}=(k_\mathrm{emp}-k_\mathrm{eff})(C-C_\mathrm{eq})\)，与 Residual-AI 的 \(S_\mathrm{sgs}\) 对照。
7. **无量纲稀疏：** 仅 \(\Pi\) 特征；标准化 LASSO/ElasticNet（pysindy 若可用则并列）；同样走嵌套 CV。

### 4.3 Results（顺序已冻结：先负精度）

1. East River GIS 河网与样点（R008 主导）。
2. **§3.1 先报负结果：** 嵌套 CV 主表 — Residual-AI **不优于** Baseline（MLP 0.057 vs 0.028）；样本内 \(R^2\) 仅附录。
3. **§3.2** 滤波尺度：\(\overline{|S_\mathrm{sgs}|}\) 与方差随 \(\Delta x\)（East River 廊道经验依赖，非普适律）。
4. **§3.3** 无量纲稀疏式与系数图；嵌套 CV 如实（弱）。
5. **§3.4** \(k\) 修正略降 \(C\) RMSE 但模型通量诊断崩溃。
6. **§3.5** 可辨识性综合：\(k_\mathrm{eff}\) 与隐含 \(S_\mathrm{sgs}\) 的权衡（**practical equifinality**，非形式化结构不可辨识证明）。

主表文件：`results/tables/paper_main_results.csv`（由 `scripts/build_paper_tables.py` 从嵌套 CV 等汇总）。架构冻结见 `docs/ENGINEERING_NOTES.md`。

### 4.4 Discussion

- 为何浓度精度不足以评价河网 CO₂ 闭合：持出 C 与模型通量诊断可背离。
- 为何 ML 不能推广：\(n=120\)、R008 占 48%、单样本河段、无独立通量、\(\Pi\) 特征在河段内几乎常值。
- LES 类比仍贡献什么：\(\Delta x\) 定义、残差随尺度诊断、浓度等价参数化下的 equifinality。
- 与 Saccardi & Winnick (2021) 的关系：公开数据上的闭合可辨识性实验，不是重复其全部过程模块。
- \(F_{\mathrm{CO}_2}\) 为模型导出诊断/代理，非腔室验证通量。
- 要区分浓度等价参数化，下一步是独立 \(k\) 或通量观测，而不是加深网络。

### 4.5 Conclusions

三条硬结论（与嵌套 CV 一致）：（1）当前观测尺度上 Residual-AI 不能作为精度改进；（2）在**仅有浓度观测**时 \(S_\mathrm{sgs}\) 与 \(k\) 存在 **practical equifinality**；（3）多尺度过滤 + 分层嵌套 CV 是可迁移的方法学。不写 CONUS/\(\mathrm{CH}_4\) 已完成。

### 4.6 建议图件与仓库文件对应

| 论文图 | 内容 | 文件（`results/figures/`） |
|--------|------|---------------------------|
| Fig. 1 | LES 过滤概念：细河网 → 滤波窗 \(\Delta x\) → \(S_\mathrm{sgs}\) | `les_filter_conceptual.png` |
| Fig. 2 | GIS 河网 + 120 样点 | `gis_reach_assignment_map.png`, `gis_samples_on_network.png` |
| Fig. 3 | 嵌套 CV RMSE 柱（三方案） | `nested_cv_rmse_bar.png` |
| Fig. 4 | 持出散点 | `nested_cv_scatter_holdout.png` |
| Fig. 5 | 可辨识性 \(k_\mathrm{eff}\) vs \(S_\mathrm{sgs}\) | `identifiability_k_vs_sgs.png` |
| Fig. 6 | 残差随 \(\Delta x\) | `filter_scale_sgs.png` |
| Fig. 7 | 无量纲稀疏系数 / 公式 | `dimensionless_coefficients.png` |
| 补充 | 子组 RMSE、通量消融 | `subgroup_rmse_r008_vs_trib.png`, `ablation_flux_comparison.png` |

主表：`results/tables/paper_main_results.csv`（汇总）← `nested_cv_metrics.csv`；`paper_filter_scale.csv`；稀疏方程表。样本内散点进入附录。

---

## 5. 拓展路线（论文之后）

| 方向 | 依赖 | 与本文关系 |
|------|------|------------|
| \(\mathrm{CH}_4\) / GRiMeDB | 公开甲烷数据库 + 新闭合 | 物种扩展，需独立通量 |
| StreamPULSE **其他**流域 | 门户上确有站点的流域 | 代谢时间序列；East River 已排除 |
| CONUS 产品对照 | CONUS_carbon 或类似公开层 | 尺度外推，不是本战役精度 |
| 单河段 2D TELEMAC | 地形断面 + 网格 | 检验断面内 \(u(y,z)\) 对 \(k\) 的影响 |
| PINN Saint-Venant | 连续水位/流量 | 另一套物理约束，不替代嵌套 CV |

以上均不进入本篇主创新。

---

## 6. 投稿策略

### 6.1 不推荐作为第一选择

**The Innovation（commentary / 高影响力快报）：** Gao 稿件的叙事容易被理解成“AI 提高了碳输运预测”。在嵌套 CV 负结果下，该刊的“突破性精度”预期与本文诚实结论冲突，除非改写成对 Gao 框架的 **方法学评论**（过滤定义 + 可辨识性），且编辑部接受负结果。可作为邀请评论或通讯，不宜当作“精度论文”首投。

### 6.2 推荐首投

**Water Resources Research 或 Global Biogeochemical Cycles 的 methods / 数据–模型实验，或 Environmental Modelling & Software。**

理由：

- 负的精度结果 + 强的协议（嵌套 CV、分层 \(n\)、真实数据、多 \(\Delta x\)）符合 WRR/EM&S 对可复现方法的胃口。
- GBC 与 Saccardi & Winnick (2021) 同领域，便于把 East River 公开数据上的闭合可辨识性写成对该工作的延伸，而不是唱反调。
- EM&S 适合“过滤算子 + 验证协议 + 开源流水线”的软件–方法文。

### 6.3 文稿语气清单（投稿前自检）

- [ ] 摘要第一句不是“AI 提高了精度”。
- [ ] 主表是 nested CV \(C_\mathrm{aq}/F_{\mathrm{CO}_2}\)，不是 in-sample \(R^2\)。
- [ ] 明确 \(n=120\)、R008=58、三河段 \(n=1\) 为示意。
- [ ] \(k\) 修正的 \(C\) RMSE 下降必须与通量崩溃同时出现。
- [ ] 无合成观测；缺失 Alk/N/P/DIC 保持缺失。
- [ ] 无量纲式即使 CV 很弱也如实写“形式可解释、预测不推广”。

---

## 7. 本仓库实施清单（与 Part B 对应）

1. 本文件：`docs/PAPER_PLAN.md`。
2. `src/13_filter_scale_sgs.py` → `results/tables/filter_scale_metrics.csv`, `results/figures/filter_scale_sgs.png`, `les_filter_conceptual.png`。
3. `src/14_identifiability_ksgs.py` → `identifiability_k_vs_sgs.png`。
4. `src/15_dimensionless_sparse.py` → 稀疏方程 + `dimensionless_coefficients.png` + 嵌套 CV（如实）。
5. 更新 `scripts/generate_report.py` / `report.md` / `report.html`：新增“论文创新实验”节；嵌套 CV 仍为主精度表；不声称 Residual-AI 获胜。
6. 更新 `REAL_DATA_AUDIT.md`：HR 用于滤波；CONUS_carbon 或文献对照的下载成败。
7. `docs/ENGINEERING_NOTES.md` + `scripts/build_paper_tables.py`：冻结主数字与 DO-NOT-CLAIM；产出 `paper_main_results.csv`。

**一句话贡献（可进摘要末句）：**  
本文在公开 East River 数据上把河网 \(\mathrm{CO}_2\) 输运的亚网格项写成 LES 式过滤残差，在仅有浓度观测时展示 \(S_\mathrm{sgs}\) 与 \(k\) 的 practical equifinality，并给出分层嵌套交叉验证协议；机器学习闭合未能改善持出浓度，这一负结果界定了当前数据所能支持的方法边界。
