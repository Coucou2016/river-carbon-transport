# 代码级整改方案：接口、算法、测试与重算顺序

审查日期：2026-09-19。对应冻结材料：`tmp/review_20260919/packet`。

**本文件是待实施方案，不是已完成修复声明。** 本轮没有修改 `src/`、原始数据、正式结果或论文。以下函数和测试名中标为“新增”的均尚未实现。代码片段是接口/核心算法建议，不是可直接替换整个项目的完整补丁。先解决物理和数据契约，再调模型参数；不能根据旧结论倒推应该得到的数字。

## 1. 先统一数据契约

目前至少存在三种相互混用的空间单元：论文的 8 个逻辑河段、主求解器的 13 个节点、滤波实验的 536 个原生 flowline。它们可以共存，但必须显式映射，不能统称“在真实 NHD DAG 上路由”。

建议新增 `src/contracts.py`、`src/validation.py`，先落实以下四张表。

| 表 | 唯一键 | 必需字段 | 禁止行为 |
|---|---|---|---|
| `observations` | `sample_id + date`，必要时增加采样批次 | 原始行号、源文件哈希、坐标、原始 pCO₂、温度、浓度转换方法、QC 标记 | 重复键取第一条；缺测补零；将经验参数叫观测 |
| `cells` | 稳定的 `cell_id` | `flowline_id`、有向起止节点、路径里程、边界里程、长度、面积、几何版本 | 以日期或当日采样序号定义永久空间单元 |
| `cell_state` | `date + cell_id + scenario_id` | `Q_in/Q_out`、`QC_in/QC_out`、侧向水/碳输入、边界来源、同步覆盖、质量平衡误差 | 未采样等同于无源无损；未知支流连接到最后节点 |
| `oof_predictions` | `run_id + scheme + model + protocol + sample_id + date` | `fold_id`、预测浓度、原始观测、目标来源、训练键哈希、几何版本、模型种子 | 跳过失败折仍写成功；重复记录静默去重 |

`reach_id` 是报告分组，不等于唯一物理控制体。`sample_id` 是观测身份，不等于独立统计重复。`Q_source`、`k_source`、`C_in_source` 必须分别记录。

## 2. T01：修正水流方向与河网压缩（P0）

位置：`src/network_topology.py:47`、`src/real_network.py:246`、`:286`、`:344`；滤波侧 `src/13_filter_scale_sgs.py:148`、`:173`。

### 2.1 FlowDir 不能把 0 当作反向

USGS 官方编码为 `0=Uninitialized`、`1=WithDigitized`。当前 `_flow_endpoints()` 在 0 时反转坐标，属于确定的字段解释错误。本次 536 条滤波走廊内有 14 条值为 0，因此不是纯假设分支。源：[USGS 数据字典](https://www.usgs.gov/ngp-standards-and-specifications/national-hydrography-dataset-nhd-data-dictionary-feature-domains)。

建议逻辑：

```python
def directed_endpoints(geometry, flowdir):
    if flowdir != 1:
        raise UnresolvedFlowDirection(flowdir)
    coords = list(geometry.coords)
    return coords[0][:2], coords[-1][:2]
```

这里的异常不是“把 14 条全部丢掉就完成”。需输出待核验清单，通过官方连接表/上游下游标识及可核查的水系资料解决方向。裁剪导致的边界节点与真正源头分开编码。坐标系缺失也不能未经依据指定 EPSG。

### 2.2 移除按北向坐标构造流向

当前 `build_segment_network()` 用汇流点的 `centroid.y` 分组、按样点 y 分配 S1…S6，再指定 S1→S2→…；这不能由“已存在 NHD 拓扑构造函数”自动证明正确。

新增 `build_path_graph(flowlines, official_links)`：

1. 优先使用可靠的节点或 PlusFlow 关系，端点匹配只作为有明确容差和歧义检查的补充。
2. 选定真实出口，以有向可达性识别流域内节点。
3. 汇流节点用实际图节点标识，不用线段中心点近似。
4. 逻辑河段若需要压缩，保存 `fine_cell_id → routing_cell_id` 成员表及每条原始跨组边。
5. 每个串联合并组必须是连通有向路径。不能因为节点拓扑序连续就认定空间连通。
6. 发现环时回报具体节点/边；禁止 Y/X fallback，也禁止删除“平均 rank 后退”的真实边来得到 DAG。
7. 不能找到汇流关系的支流写 `unresolved` 并阻止正式结果发布，不能先记 `inf` 再接到末段。

验收：`test_flowdir_zero_is_unknown`、`test_confluence_preserves_all_parent_edges`、`test_disconnected_nodes_cannot_form_serial_cell`、`test_cycle_reports_ids`、`test_unknown_confluence_blocks_release`。增加一个弯曲且南北往返的测试河道，坐标变换/旋转后流向与预测不得改变。

## 3. T02：连续里程与固定控制体（P0）

位置：`src/real_network.py:86`、`:113`、`:206`、`:214`、`:397`附近。

当前 `geometry.project(point)` 得到的是某一条 flowline 的局部里程；不同 flowline 的里程都从零开始。把这些数混在一个逻辑河段里排序会跨线错序。之后又按每个日期已有样点重新计算长度，使“观测覆盖变化”改变了“物理模型面积”。

### 3.1 分离固定网格与观测

优选固定 NHD 控制体或预先确定的有限体积网格，样本只负责映射到单元，不负责每天重新生成单元。若采用样点中点边界，必须事先明确该方法仅定义采样支持范围，并以独立确定的域端点闭合；不能将其当全河长。

```python
def bounded_midpoint_lengths(chainage_m, domain_start_m, domain_end_m):
    """仅适用于同一条已核验有向路径上的不同位置。"""
    x = np.asarray(chainage_m, dtype=float)
    if x.ndim != 1 or len(x) == 0 or not np.isfinite(x).all():
        raise ValueError("invalid chainage")
    if not domain_start_m < domain_end_m:
        raise ValueError("invalid fixed domain")
    order = np.argsort(x, kind="stable")
    xs = x[order]
    if np.any(np.diff(xs) <= 0):
        raise ValueError("replicates must be mapped to the same cell first")
    if xs[0] < domain_start_m or xs[-1] > domain_end_m:
        raise ValueError("sample outside fixed domain")
    edges = np.r_[domain_start_m, (xs[:-1] + xs[1:]) / 2, domain_end_m]
    lengths = np.diff(edges)
    if np.any(lengths <= 0):
        raise ValueError("nonpositive cell length")
    result = np.empty_like(lengths)
    result[order] = lengths
    assert np.isclose(result.sum(), domain_end_m - domain_start_m)
    return result
```

注意：这段函数只修正边界闭合，不修复错误里程，也不解决“用样点形成网格”对采样设计的依赖。不能只替换它就宣布 P0 完成。

### 3.2 里程接口

新增 `project_sample_to_directed_path()` 返回 `flowline_id, local_s_m, path_s_m, snap_distance_m, snap_status`。其中 `path_s_m = verified_upstream_path_offset + local_s_m`；分叉路径不可强行共享一个无歧义的全局一维里程。永久保存 flowline 身份，不能在落盘时丢掉。

验收：

- 两条串联 1 km flowline，样点分别位于首条 800 m、次条 200 m，路径里程应为 800、1200 m，而非 800、200 m。
- 固定 [0,10000] m 域内 2/10/100 个采样位置，面积与长度总量均保持固定；当前函数分别返回 20000、11111.11、10101.01 m。
- 同位置技术重复不新增面积；调换 CSV 行序不改变预测。
- 留出标签时不能重划几何；模型诊断、训练、前向预测读取同一 `geometry_version`。
- `length_conservation_table()` 改成相对指定支持域的守恒检查，不再以“没有超过 100 km”代替守恒。

## 4. T03：一套带侧向输入的质量平衡求解器（P0）

位置：`src/real_network.py:439`、`:449`、`:477`；`src/cell_dag_filter.py:95`、`:285`；旧路径 `src/03_baseline_transport.py:56`、`src/07_coupled_prediction.py:99`。

单位统一：Q 为 m³/s，QC 为 mol/s，k 为 m/day，S 为 mol/m²/day，A 为 m²。

建议把所有前向路径迁移到单一 `src/transport.py`。明确侧向碳源是否已包含在 S 中，防止重复计入。

```python
def steady_concentration(*, qc_in, q_out, lateral_qc, area, k, c_eq, sgs):
    # 前置校验：有限数；q_out, area > 0；k >= 0。
    denom = q_out + area * k / 86400.0
    c = (qc_in + lateral_qc + area * (sgs + k*c_eq)/86400.0) / denom
    if c < 0:
        raise PhysicallyInfeasibleState("negative concentration")
    residual = qc_in + lateral_qc - q_out*c + area*(sgs-k*(c-c_eq))/86400.0
    return c, residual

def diagnose_source(*, qc_in, q_out, c_obs, lateral_qc, area, k, c_eq):
    return 86400.0*(q_out*c_obs-qc_in-lateral_qc)/area + k*(c_obs-c_eq)
```

不能继续简单使用 `q_out*(C-C_in)` 同时又允许 `q_out != q_in`，除非明确假设侧向来水的浓度就是 C_in。当前代码没有声明并检验这个隐含假设。

`_make_q_model()` 必须按日期从已核验流量表读取出口流量，不依赖当天是否采到 R008。删除 `sum(tributaries)*5` 的无观测替代。若出口流量小于支流合计，报告不一致并确定测站范围/时间尺度，不能用 `max(...,0.01)`掩盖。

`u,W,h,Q` 应有明确水力几何关系及误差说明。当前经验式相乘 `W*h*u = 0.97888 Q`，不是严格恒等；文中又声称 `u=Q/A_c`。选定一致实现，或将其作为经验关系不闭合误差记录，不要两种说法混用。

禁止 `max(C,0)`后仍宣称原方程精确守恒。若确需非负约束，输出截断次数、修正碳量和受影响样本；不能只隐藏负值。

验收：无源无交换恒浓度、两支流汇合、侧向稀释、侧向碳输入、不同 Q 的出入边、空采样节点、有源单元串联、全网络质量平衡，均需解析解或独立计算对照。逐节点保存绝对/相对平衡误差，容差随数值尺度定义，不能把大误差归入 S 而不报告。

## 5. T04：重写串并联合并，传播缺测状态（P0）

位置：`src/cell_dag_filter.py:111`、`:248`、`:285`；`src/13_filter_scale_sgs.py:173`。

当前 `q_mode='outlet'` 只使 Q 取末条，C 仍为全部样本的 Q 加权平均，`Sigma_QC` 又累计全部内部横截面的 QC。这三个量不是同一出口状态。单纯把“内部 QC 求和”存下来不构成守恒证明。

拆成两个接口：

- `mix_parallel_inflows(states)`：仅处理不同入边在同一汇流节点的混合，返回 `Q=sumQ, QC=sumQC, C=QC/Q`。
- `contract_serial_cells(cells, ordered_edges)`：内部边通量相互抵消，只保留组边界 `QC_in/QC_out`，并累计体积、面积、总源量与总气体交换量。

必须分别存 `C_out` 与用于体积/面积平均的 `C_bar`。二者不是默认可互换。气体交换积分应保留 `sum(A_i*k_i*(C_i-Ceq_i))`，而不是先分别平均 k、C、Ceq 再相乘。

粗单元诊断可采用：

```text
A_G = Σ A_i
S_G = [86400 (QC_out,G - QC_in,G - lateral_QC,G)
       + Σ A_i k_i (C_i - Ceq_i)] / A_G
```

成立前提是边界与内部状态均有定义；没有同步全网观测时应给出条件化假设/缺测范围，不得把无观测通量当已知。

缺测传播建议新增 `state['coverage_complete']` 和 `state['missing_ancestors']`：

```python
complete = all(u in state and state[u]['coverage_complete'] for u in upstream_ids)
missing = set(u for u in upstream_ids if u not in state)
for u in upstream_ids:
    if u in state:
        missing |= state[u]['missing_ancestors']
```

透传不能重置 complete。源头“使用边界假设”与“实际已观测”应是不同状态。未观测节点若进行无损透传，要在方法中承认关闭了该处气体交换和源项，不要称为完整物理传播。

验收：

1. 串联两单元 Q=1，C=2、4，出口 QC 应为 4，不是当前 3，也不是内部 QC 和 6。
2. 并联两入边的 QC 才需要相加；串联不允许按并联算法处理。
3. 重复一个采样记录不改变单元体积、面积、出口 QC 或单元权重。
4. U 与缺测支流汇入 V，V 透传给 W，W 必须保留 incomplete。
5. 粗图所有跨组边与细图映射一致；不是“过滤掉若干边后仍然能拓扑排序”。
6. 保留多段几何，不得 `_as_linestring()` 只取最长分支，同时长度却取全部分支之和。

## 6. T05：真正隔离留出标签，统一 SGS 与 k 的目标构造（P0）

位置：`src/05_compute_residual_sgs.py:44`；`src/12_nested_cv_transport.py:198`、`:276`；`src/15_dimensionless_sparse.py:185`。

本轮反例：将 R005 的观测浓度全部增加 0.1 mol/m³ 后，R008 的训练样本 ER-5（2019-08-03）诊断残差改变约 -0.171747 mol/m²/day。说明先诊断全数据残差、再按 reach 切训练集，不构成独立留出。

### 6.1 先明确预测问题

区分两类评估，不能混写：

- **严格新河段预测**：测试组的浓度标签在训练目标、上游边界和选择中均不可见；可使用哪些地形/水文驱动需事先定义。
- **有上游实测条件的条件预测**：允许指定的边界浓度，但不再宣称完全独立的空间外推；边界点不能同时作为被评分标签。

建议新增 `build_fold_context()` 返回不可变网格、允许读取的驱动、训练标签、可用边界、完整来源键；不要通过删除几何行实现“隐藏标签”。测试标签只能进入最终 scoring。

```python
for fold in fixed_group_splits:
    context = build_fold_context(
        geometry=frozen_cells,
        drivers=allowed_drivers,
        observations=observations,
        visible_label_keys=fold.train_keys,
        boundary_policy=declared_policy,
    )
    targets = build_fold_targets(context)   # SGS 和 k 都从此接口产生
    assert not (targets.dependency_keys & fold.test_keys)
    model = fit_train_only_preprocessing_and_model(targets, fold)
    pred = route_with_predicted_closure(context, model)
    score_only(pred, observations.loc[fold.test_keys])
```

如果隐藏某上游标签导致下游训练目标无可靠 C_in，可选择排除该目标、采用独立边界或额外训练内预测，但必须记录影响。不能偷读测试标签维持 n，也不能凭空补一个“合理浓度”。

### 6.2 k 目标合并的具体修补

当前 `_fold_k_targets()` 只删除旧 `C_in_obs_mol_m3`，没有删除已有 `L_control_m`，合并后变成 `_x/_y`；反演函数找不到原名，回退到 `L_m`。实际探针已重现。还需使用同一路由 Q：当前 120 条中 39 条输入 Q 与诊断路由 Q 不同，最大差约 0.8910 m³/s。

短期补丁不能只 drop 一列，应加入稳定行号、强制唯一键和同源物理状态：

```python
training = obs.iloc[tr_idx].assign(_row_id=tr_idx)
physical = ['C_in_obs_mol_m3', 'L_control_m', 'Q_routed_m3s']
training = training.drop(columns=physical, errors='ignore')
training = training.merge(
    fold_diag[keys + physical], on=keys, how='left', validate='one_to_one'
).sort_values('_row_id')
assert not any(c.endswith(('_x', '_y')) for c in training if c.startswith('L_control'))
```

`fold_diag` 新接口应直接给 `QC_in/Q_out/area`；反演 k 使用统一平衡式，而非各处拼凑 Q、L、C_in。`C≈Ceq`、无解、负 k、缺边界要分类记录。仅 `k_needed>0` 的条件训练改变了目标人群，评估仍需覆盖全部测试样本，报告可行率及分组差异。

验收：测试组 C/pCO₂ 随意置换、极端扰动或设为不可访问，训练标签、特征处理器参数、模型参数和测试预测必须不变。最后评分数值可以变化。分别测试 leave-one-reach、leave-one-date 和跨上游依赖情形。

## 7. T06：OOF 完整性与统计报告（P1，涉及结论时为 P0）

位置：`src/12_nested_cv_transport.py:101`、`:276`、`:372`；`src/06_train_sgs_model.py:52`；`src/cell_dag_filter.py:378`。

- 折失败：保存异常及 fold ID，正式运行以非零码退出，不得 `continue` 后继续发布全样本标签。
- OOF 合并使用 `validate='one_to_one'` 和外连接覆盖检查；重复键报错，不 `keep='first'`。
- n 从实际符合条件的唯一键计算，不硬编码 `all_120`；六个 scheme/protocol 各自应覆盖其预定 120 个测试键，而不是整表总计 120。
- 缺测列若训练集全空：按预定策略移除或报错，不能借测试集统计量补齐。
- `06` 的全数据中位数填补需迁入每折 Pipeline；其历史指标与 `12` 的 transport 指标分开存放。
- 当前没有内层超参数循环，统一称 grouped CV；若以后选超参数，才新增内层分组验证。
- 至少报告 pooled RMSE、各河段 RMSE、宏平均河段损失、与基线的配对误差差值、各河段 n。三个单样本河段不能与充分采样河段当同等精度的证据。
- 多随机种子报告模型训练随机性；河段/日期分块敏感性报告采样结构不确定性。二者不能混成一条“95% CI”。河网依赖和仅 8 组限制使简单独立 bootstrap 并非自动有效，需论证块定义并明确探索性。
- `n_independently_repeatable_units=n_unique_cells` 删除；改为 `n_unique_spatial_cells`，独立性由设计与依赖模型判断。

验收：注入缺一条预测、重复一条预测、缺一折、训练列全 NA、错误分组键，发布检查全部失败；完整 OOF 的分母和模型间样本集合完全一致。

## 8. T07：纠正量纲与稀疏模型的训练目标（P1）

位置：`src/05_compute_residual_sgs.py:27`、`src/utils.py:108`、`src/15_dimensionless_sparse.py:185`及主函数。

```python
tau_s = L_m / u_ms
Da = (k_CO2_m_d / 86400.0) * tau_s / h_m
# 若 DOC_mgL 的单位为 mg C/L，DIC_mmolL 为 mmol C/L：
DOC_over_DIC = DOC_mgL / (12.011 * DIC_mmolL)
```

以上 DOC 换算以源数据确实按碳质量报告为前提，先核对列定义。`k_tau_h` 与 Da 同义时保留一个，避免重复特征。重新生成训练表、稀疏系数与全部相关指标，不能以“最后没选中”豁免错误特征。

当前全数据展示拟合 `S*`，transport CV 却拟合有量纲 `S`。建议统一为 `S*=S/(k_emp*Ceq)`，在每折反变换成 S 后路由；或者明确报告两个不同模型，不把前者的简洁公式归功于后者的预测结果。报告标准化均值/标准差和原尺度系数；原尺度公式不应仍写 `_z`。

验收：等价的秒/天输入给出同一 Da；正确的无量纲比值在单位换算后不变；每折 `S*→S` 反变换 round-trip；标准化式和原尺度式逐点预测一致。

## 9. T08：重新定义通量估计对象（P0）

位置：`src/12_nested_cv_transport.py:101`；论文 2.6、Tables 2/3/7、Fig. S2。

不能把 120 个不同日期样点的 `ΣF_i A_i`叫研究区总排放。当前新增的“逐日去重再日期平均”也不自动得到全研究区通量，因为各天覆盖范围不一致且 cell ID 本身随日期变化。

优先方案：冻结空间域 Ω，对每个日期在相同 Ω 上求解所有单元，计算 `F_domain(date)=Σ_{cell∈Ω} A_cell F_cell(date)`，再按明确时间权重汇总。没有足够边界条件支撑这种完整解时，只报告 `sample-support flux diagnostic`，同时给出日期、覆盖面积、支持域和缺测比例。

源数据表分开列 `flux_density_mol_m2d`、`cell_flux_mol_d`、`domain_flux_mol_d`、`time_integral_mol`。`sum(flux_density)`没有空间积分含义，不能用一个单位标签把它变成预算。

验收：复制记录不增加域通量；日期拆分/合并不造成重复空间积分；只在明确时间积分时累加天数；所有比较用相同支持域；经验 k×观测 C 是模型代理量，不叫实测 F。

## 10. T09：把 equifinality 检验改成可解释的目标函数分析（P1）

位置：`src/16_equifinality_surface.py:55`、`:93`、`:157`。

1. 不从 S 的诊断恒等式反推 q_A，直接从已核验 Q、面积读取；`Cobs≈Cin`时反推式病态，当前置零不合理。
2. 区分“固定观测条件下单个方程存在一条解析零谷”与“完整网络在独立预测下不可识别”。前者是代数事实，不足以自动推出后者。
3. 没有误差分布/方差模型就称 `profile SSE/objective`，不称统计意义的 profile likelihood，也不从任意 10% RMSE 阈值生成置信区间。
4. 固定 α 时 S 是线性系数，可解析求最优值，避免 121 个粗网格近似：

```python
den = q_A + alpha*k_emp
a = (q_A*C_in + alpha*k_emp*Ceq) / den
b = 1.0 / den
S_best = np.sum(weights*b*(Cobs-a)) / np.sum(weights*b*b)
J_best = np.sum(weights*(Cobs-a-b*S_best)**2)
```

该式只适用于当前“固定 C_in、统一 S”的条件模型；若使用完整路由、浓度截断或参数边界，需采用对应求解和优化，不能直接套用。

5. 在二维“统一 α、统一 S”平面上放异质模型逐样本参数的中位数，只能叫 descriptive median parameter marker，不是真实模型 operating point；中位数点的 J 与模型实际误差一般不相等。
6. 新增完整网络参数敏感性、多起点优化及独立边界/气体交换观测约束的比较；结果无论支持或不支持浅谷，都如实报告。

验收：解析最优与高精度优化一致；网格加密不改变论断；图区标记的 J 可由同一参数定义重算；明确包含/不包含下游传播。

## 11. T10：恢复一条可复现的正式流水线（P0）

位置：`run_pipeline.py:27`、`:144`、`:150`、`:183`；`src/07_coupled_prediction.py:99`；`scripts/verify_paper.py:44`。

建议：

1. 将 `03/07/08` 的历史演示路径迁到 `legacy/` 或由显式 `--legacy`调用；默认管线不能同时生成新树模型与旧串联/观测 fallback 模型，再混放在一个结果目录。
2. 所有 stage 使用配置解析的路径；当前 `_check_paths` 与 manifest 用 ROOT 硬编码，不能真实验证用户自定义输出目录。
3. 每次运行写到 `runs/<run_id>/`，raw 只读；完成后通过原子发布选定正式 run。不要先清空已有成果再尝试。
4. 完整 manifest 至少包含：raw 文件哈希、代码和配置哈希、依赖锁文件、种子、命令、dirty patch、所有 stage 输入/输出哈希、样本数、时间、失败状态、图/表/稿件构建哈希。
5. partial/smoke 运行必须有 `run_type=partial` 与缺失阶段列表，不能用其 manifest 证明 full reproducibility。
6. `verify_paper --mode development` 可以 warning，但退出信息应是“开发检查，不可投稿”；`--mode submission` 对数字漂移、缺表、缺图、旧图哈希、失败 fold、无源码版本全部 fail closed。
7. 原始采集与下载拆开；离线重算不应再次联网更新输入。
8. 更新依赖锁：当前运行 numpy 2.4.6、pandas 3.0.3、sklearn 1.9.0、XGBoost 3.2.0，requirements 却锁到旧版本。先验证所选环境，不能直接把版本号改得和机器一致就算完成。测试依赖纳入 dev lock。

验收：在空衍生目录、固定本地 raw、固定环境，从唯一命令完成所有正式分析与稿件构建；第二次运行数值在明确容差内一致。删掉任一必需输出或改动一个图源数字，投稿校验必须非零退出。

## 12. T11：图表与稿件单一数据源（P0）

新增 `results/paper_metrics.json` 和 `scripts/build_paper.py`。不要把预期 RMSE 再硬编码进 guard；应从同一 run 的 OOF 计算，再生成正文数字、表格和图注。科学解释仍需人工审核，不能自动按分数生成夸大结论。

每图建立 sidecar：`figure_id, run_id, generator, source_table_sha256, selected_rows, aggregation, units, n_definition, output_sha256`。HTML 内嵌图片与引用 PNG 按哈希核对；PDF 另行渲染目视核对。只更新 PNG 不代表 HTML/PDF已更新。

图 3 用相同 OOF 画总体指标与逐河段差值；图 4 用同样的 sample keys；图 5 使用同一重算的 objective 数据；图 6/S3 先解决 T01/T04；图 7 先解决 T07。禁止用绘图代码中写死数字维持原论文结论。

## 13. 验收矩阵及执行顺序

| 顺序 | 完成任务 | 必需验收证据 | 可重算的结果 |
|---|---|---|---|
| 1 | 数据来源、字段字典、排除记录 | 120 行源映射，原始文件哈希，公开数据引用 | 观测表 |
| 2 | T01/T02/T03 | 方向、边界、面积与水碳平衡测试 | 基线与诊断标签 |
| 3 | T04 | 串并联、粗图边、缺测传播测试 | 尺度实验 |
| 4 | T05/T06/T07 | 留出扰动不变性、OOF 完整性、单位测试 | 所有机器学习与稀疏实验 |
| 5 | T08/T09 | 支持域与目标函数验收 | 通量与可识别性诊断 |
| 6 | T10 | 隔离全链重算、完整 manifest | 正式结果集 |
| 7 | T11 | 逐图 source data、MD/HTML/PDF 同步 | 完整投稿稿件 |

性能优化在科学正确性之后：端点 O(n²) 匹配可改空间索引/KDTree；每样本反复布尔扫描改唯一键索引；纯函数化便于测试；缓存必须使用输入/代码/配置哈希，不能仅靠文件存在。不能为加速而改变样本集、精度或缺测策略。

最终完成标准不是“测试全绿”“脚本能跑”或“图很漂亮”中的某一项，而是：数据来源声明正确、物理守恒成立、评估不存在测试标签依赖、每个正式结果能从冻结输入重算、正文和所有格式图表完全对应。
