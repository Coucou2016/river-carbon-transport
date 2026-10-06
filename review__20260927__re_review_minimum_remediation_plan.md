# 2026-09-27 更新版复审意见与最小整改方案

## 结论与适用范围

能看到更新，而且不只是文件时间变化：与上一轮冻结材料相比，主模型代码、处理表、模型文件、图和论文均有变动。当前 paper.md / paper.html 为 9 月 20 日版本；根目录 report.pdf 仍为 8 月 16 日的 81 页旧报告，不是当前英文论文 PDF。

本轮建议：**完成范围有限的方法修复和一次统一重算后再投稿；不是仅改措辞即可直接投稿。** 不需要为解决这些问题另开一个研究课题，也不需要先扩展到新流域。最重要的计算问题是生产路由仍采用未验证的空间支持、MLP 负浓度截断没有完整传递守恒诊断、稀疏分支没有同步主模型的折内标签修复。

数据诚信判断必须区分两件事：原始观测确实来自第三方公开研究；本项目的主模型结果可以由当前代码重新训练得到。本轮没有发现足以指控伪造数据的证据，但也不能把“可复算”写成“方法正确、所有资料均为自己原创、没有任何复制”。作者应明确声明 public-data reanalysis，而不是自采数据。

新修订稿仅写入本目录的“修订稿”，没有覆盖根目录论文、代码、原始数据或生产结果。它已同步已核实的数字，重写主要方法、结果、讨论和结论，保留未完成事项。它不是把尚未修复的程序描述为已经修好。

## 一、这轮真正验证了什么

| 项目 | 本轮证据 | 判断 |
|---|---|---|
| 原始 pCO₂ 到处理表 | 120 个复合键一一匹配，数值最大差 0 | 支持忠实搬运公开观测 |
| 温度、DO、DOC、DIC | 温度和 DO 各 120 对；DOC/DIC 各 41 对，最大差均 0 | 缺失没有被冒充新增实测 |
| Henry 换算 | 重新计算 C_aq，最大差 9.71×10⁻¹⁷ mol m⁻³ | 当前转换可复算；不是独立实测浓度 |
| Baseline、SGS | 从冻结处理输入重新路由/诊断，最大差约 9.02×10⁻¹⁷、3.55×10⁻¹⁵ | 支持计算一致性 |
| 主模型重新训练 | MLP、RF、k-correction 各 120 个 OOF 预测，最大浓度差均约 9.71×10⁻¹⁷ | 当前主结果不是只读摘要而无法复算 |
| 测试 | 主审直接调用三文件 34 个 test 函数，34 通过 | 不等同于全新环境 pytest/完整流水线验收 |
| 主分支折内隔离 | 扰动 R005 持出浓度，训练 SGS 最大变化 0；持出目标为空 | 核心泄漏修复有实证支持 |
| 当前正文图片与 HTML | 10 张正文引用 PNG 与 HTML 嵌入哈希一致 | 只证明图片版本一致，不证明图注/数据解释正确 |
| 投稿门控 | development 返回 0；submission 返回 1 | 门控未能识别主要旧数字，覆盖不足 |

证据文件：evidence/audit_current.json、retrain_main.json、supplement.json。完整来源边界另见《真实性准确性完整性证据.md》。主模型复算从现有处理输入开始，未重新下载和重建全部 GIS、全部原始输入或所有分析阶段。

## 二、优先级与最小工作量

| ID | 等级 | 问题 | 最小动作 | 是否重算 |
|---|---|---|---|---|
| P0-01 | 阻断提交 | 正文、生成器、旧 PDF、旧图混代；k 比值格式化错误 | 单一数值对象和单一正文源，统一导出 | 方法修复后统一生成 |
| P0-02 | 阻断物理输运主张 | 局部 chainage、无界控制长度、逻辑树当 NHD 路径 | 验证路径与固定域，把现有 bounded helper 接入生产 | 是，影响几乎全部结果 |
| P0-03 | 阻断约束有效性 | 负浓度被截零，返回值丢失 clipping/守恒信息 | 严格求解或预定义约束；记录原始/受限源、原始浓度与残差 | 是 |
| P1-04 | 必修 | 稀疏模型全数据标签及插补泄漏 | 复用主分支折内目标和训练折插补 | 是，仅相关分支及派生图表 |
| P1-05 | 必修 | q_A 声称直接计算，实际因列后缀走残差反演 | 明确键连接，使用 routed Q 与 control length | 重算曲面；当前数值未发现差异 |
| P1-06 | 必修 | 把条件 SSE 写成一般不可识别结论 | 固定边界、共享参数、权重、10%阈值明确；收窄主张 | 最小文字路径无需新实验 |
| P1-07 | 必修 | MLP 改善被 3 个点主导 | 逐河段配对误差和剔除评分敏感性 | 现有 OOF 即可，本轮已计算 |
| P1-08 | 必修 | 图表估计量、网络对象、计数混用 | 每图定义行单位、权重、单位、模型；动态生成计数 | 文字/制图为主 |
| P2-09 | 可复现性 | pytest 环境缺失、清单局部且陈旧 | 独立开发依赖、全产物哈希、端到端日志 | 最终一次 clean-output 验证 |

这里 P0 是“未关掉前不能作对应强主张”，不是对诚信或人员的判定。dirty 工作树本身不是错误；可以保存 patch 与全部哈希，不必为了形式清洁丢弃用户未提交改动。

## 三、P0-01：数值与生成器同步

定位：paper.md 原始第 142–195 行；scripts/generate_paper.py 的段落常量、HTML 专用摘要、约第 1179–1183 和 1273–1274 行；scripts/report_content.py 中网络常量。

| 内容 | 当前正文旧值/说法 | 本轮核实的当前值 |
|---|---|---|
| MLP MAE / bias | 0.0336 / +0.0187 | 0.02138688 / −0.00554410 |
| RF MAE / bias | 0.0357 / +0.0119 | 0.05117607 / +0.03422980 |
| 多样本支流 MLP RMSE | 0.0835，变差 | 0.04697908，低于基线 0.06351384 |
| k_eff 中位数 | 0.0066 | 123.3293 m d⁻¹ |
| k 配对比值中位数 | 3.9×10⁻⁵；表又为 1.00 | 0.53999068 |
| k 下界饱和 | 18.8% | 0/120 |
| k 通量面积诊断 | 5.99×10² | 1256.1961 mol d⁻¹ |
| 平均 S_implied / S_MLP | 3.20 / 3.40 | 1.01335 / 4.03458 mol m⁻² d⁻¹ |
| 稀疏式 | 两项，Da 丢弃 | 三项，包含 +0.3457 log10(Da)_z |
| 稀疏 S* R² / transport RMSE | −1.55 / 0.0588 | −0.44838 / 0.05285224；仍属待修复分支 |
| profile 最优 α / S | 0.019 / 0.025 | 0.05843414 / 0.12767481 |
| Figure 3 结论 | 没有模型低于 Baseline | MLP 的点 RMSE 更低，但不是稳定成功 |

特别具体的真实 bug：生成器把 `kr >= 0.5` 的数统一显示为 `1.00`。这不是四舍五入，而是错误分类显示。应改为：

```python
def fmt_ratio(value):
    return '—' if not np.isfinite(value) else f'{float(value):.3f}'

assert fmt_ratio(0.5399906833903203) == '0.540'
assert fmt_ratio(1.0) == '1.000'
```

组织方式建议：`paper.md.j2` 或同等模板只保留作者正文；`paper_values.json` 汇集 machine tables 中已经核验的字段；MD、HTML、PDF使用同一渲染对象。不要在 `ABSTRACT`、`EN_ABSTRACT`、段落数组、图注常量四处再抄数字。禁止把缺失指标默认填成零或 1.00。`results/figures/paper/` 中存在旧图，应在确认后隔离为历史产物，不要用模糊同名搜索选图。本轮没有删除它们。

验收：除字符串数字检查外，计算 `mlp_rmse < baseline_rmse` 并约束句子方向；同时验证 fraction_at_floor、三项稀疏式、paired ratio。PDF 文本抽取和图内标注也属于发布检查。不能因为 development guard 返回 0 就宣告通过。

## 四、P0-02：路径、chainage 和长度域必须真实对应

定位：src/real_network.py 第 86–108 行 legacy helper；111–176 行新 bounded/path helpers；318–335 行局部投影；生产 route_steady_state 约 520 行和 diagnose_sgs 约 749 行仍调用 legacy helper。

已经有正确方向的辅助函数，但“辅助函数测试通过”不等于生产调用正确。当前 R002 的 `sum_L_control_m=837.76194`，`nhd_reach_length_m=170.21613`，比值 4.92175。注意：这首先证明两个自称物理支持的对象不一致，不足以证明 170.216 m 就是真实河段长度，不能简单把所有 L 按 4.92 除掉。

最小实现顺序：

1. 固定每个逻辑河段所用的有向路径，保存 `flowline_id, from_node, to_node, path_offset_m, path_length_m, direction_status`。沿拓扑累加 path_offset；不能每换一条 flowline 就把 chainage 清零。
2. 投影使用已有 `project_sample_to_directed_path`，输出 local_s 与 path_s；多线几何必须先验证段间连续，不能把不相连 parts 任意拼接。
3. 保存 `domain_start_m, domain_end_m, domain_source, geometry_version`；同一空间域不能随某天采样数变化。重复坐标归同一物理 cell，重复观测不重复面积。
4. 一次预计算控制体表，在诊断和前向路由中按稳定键读取同一份。删除生产函数里再次从样本排序临时算 L 的路径。
5. 单样本 100 m 只能作为声明过的支持假设，不可称实测或已验证 NHD domain。无法验证的支流留作敏感性/示意；若要排除出主物理结论，必须重新算并报告样本数，不能删掉不利样本后沿用原指标。

接口建议（示意补丁，尚未应用）：

```python
# Build once before any CV split; geometry uses no concentration labels.
for segment_id, g in geometry.groupby('segment_id', sort=False):
    lo, hi = domain_bounds[segment_id]   # verified external path domain
    lengths = bounded_midpoint_lengths(g['path_s_m'].to_numpy(), lo, hi)
    geometry.loc[g.index, 'L_control_m'] = lengths
    assert np.isclose(lengths.sum(), hi - lo)

# Both diagnose_sgs and route_steady_state consume these same fixed lengths.
rows = rows.merge(geometry[keys + ['L_control_m', 'domain_id']],
                  on=keys, validate='one_to_one')
assert rows['L_control_m'].gt(0).all()
```

验收：路径有向且连续；样点投影落在域内；每域控制体不重叠且总长等于域长；持出标签扰动不改变几何；R002 现状必须被门控拒绝。不要仅检查代码里出现了 `bounded_midpoint_lengths` 字样。修复后重建 SGS、k targets、全部 OOF、通量和 profile；原数值只保留为历史比较。

## 五、P0-03：不能把截零当作守恒解

定位：src/real_network.py 约 561–598 行。注释称不静默截断，但 except 捕获物理不可行后仍 `allow_clip_negative=True`，返回 `res.c` 丢掉其他诊断。route 中 `n_clips=0` 没有完成有效逐行统计。

重训确认 3 个持出零值：R005/GC-1/2019-08-03、R005/GC-14/2019-08-06、R005/GC-2/2019-08-06。当前记录可重算的最大质量平衡绝对残差约 9.34×10⁻⁴ mol s⁻¹。日志中还有非持出网络节点警告，因此不能以总日志条数替代 OOF clipping 数。

保守的最小方案是默认严格求解并显式失败，不再 catch 后自动截零。若业务上需要约束闭合，使用事先定义的物理下界，而非根据测试误差挑 bound。在当前 routed state 中：

```python
# qc_in and lateral_qc: mol/s; A: m2; k: m/day
s_min = -(86400.0 * (qc_in + lateral_qc) / A + k * c_eq)
s_used = max(s_pred, s_min)  # explicitly changes the closure
sol = steady_concentration(qc_in=qc_in, q_out=q_out,
    lateral_qc=lateral_qc, area=A, k=k, c_eq=c_eq,
    sgs=s_used, allow_clip_negative=False)
```

这只是可选约束设计，不是替你默默采用的科学决定。报告必须保存 `S_pred_raw, S_used, constraint_active, C_raw, C_model, mass_balance_residual, fold_id, is_held_out`，并展示无约束失效数与约束后的全新指标。验收阈值需兼顾量纲和流量尺度，例如 `abs(balance) <= atol + rtol*max(abs(qc_in), abs(q_out*C), ...)`；不能用固定宽阈值掩盖小流量误差。

## 六、P1-04：稀疏分支修到与主分支同一标准

定位：src/15_dimensionless_sparse.py 约 185–219、232–255、305–330 行。transport 函数第 202 行使用 `y_sgs[tr]`，来源是全数据诊断；main 第 254 和 324 行全数据 median fill。不得只改方法文字称“fold-local”。

建议先把 `src/12_nested_cv_transport.py` 的 `_fold_diagnose`、`_fold_sgs_targets` 移入公共模块 `src/fold_targets.py`，两分支引用同一实现；数字开头文件可 importlib 导入，但公共模块便于测试和维护。

```python
for tr, te in LeaveOneGroupOut().split(X, groups=groups):
    y_fold = fold_sgs_targets(obs, obs_seg, seg_df, tr, te)
    med = X.iloc[tr].median()
    keep = med.notna()  # explicit all-missing policy, derived on train only
    xtr = X.iloc[tr].loc[:, keep].fillna(med[keep])
    xall = X.loc[:, keep].fillna(med[keep])
    pipe = make_pipeline(StandardScaler(), Lasso(alpha=0.05))
    pipe.fit(xtr, y_fold[tr])
    s_all = pipe.predict(xall)
    # Re-route full network, then select te keys exactly once.
```

若保持目前方法，transport 继续用 dimensional S target；full-data S* 公式仅描述性展示。若改成预测 S* 再乘 k_emp*C_eq，则是另一项方法改动，需明确记录，不能把两者混写为同一个模型。原变量方程不要保留 `_z`；`format_equation(..., standardized=False)` 应用不同显示名。

测试不应只测拆分索引：扰动整个 held-out group 的浓度，训练 y、med、scaler、拟合系数应不变；扰动 held-out 特征不影响训练预处理；测试用至少一个存在跨河段上游依赖的真实折。每个观测键严格一个 OOF，全部有限，键集合等于预期集合。

## 七、P1-05/06：q_A 与等效性估计量

定位：src/16_equifinality_surface.py 第 41–76 行。training 和 obs 同有 Q/W，默认 merge 产生后缀；因此 `if 'Q_m3s' in m ...` 未进入，实际走 residual inverse。当前审计发现反演 q_A 与直接 routed Q/(L_control*W) 最大差约 6.14×10⁻¹² m d⁻¹，所以不能声称本次曲面数值因此已算错；错误在元数据、脆弱回退和未来一致性风险。

最小改法：

```python
keys = ['date', 'reach_id', 'sample_id']
physical = diag[keys + ['Q_routed_m3s', 'L_control_m']]
m = observations[keys + ['W_m', 'C_aq_obs_mol_m3', 'C_eq_mol_m3',
                         'k_CO2_m_d']].merge(physical, on=keys,
                         validate='one_to_one')
m['q_A_m_d'] = 86400*m.Q_routed_m3s/(m.L_control_m*m.W_m)
assert np.isfinite(m.q_A_m_d).all() and m.q_A_m_d.gt(0).all()
```

不要退回 obs 的整段 `L_m` 来代替当前 control length。若物理字段缺失，抛错，不从自己待检验的 S 反算并宣称独立直接来源。summary 写入实际 `q_A_source`、边界来源、objective_name、权重、共享参数、profile区间。

最小文字修复已在新稿完成：单样本是固定 C_in 下一式两未知量的代数欠定；pooling 是 120 样点等权、共同 α 与 S、固定观测上游状态的 SSE，不是 network rerouting / profile likelihood / 置信区间。图内模型中位参数只作参考标记，不能称真实网络 operating points。若保留更广“实用不可识别”主张，最小加一个等权河段 profile 和 5%/10%/20%描述阈值敏感性；不做则只报告描述区间，当前修订稿采用后者。

## 八、P1-07/08：统计与每张图的对应

MLP 的总 SSE 下降中 R002 贡献 **0.938237**。删除 R002 行后（不重训）Baseline/MLP pooled RMSE 是 **0.0267845/0.0256044**。八河段等权 MSE 再开根为 **0.0932466/0.0640389**，不能误称平均每河段 RMSE。R001、R004、R007 变差。完整逐河段 SSE 已在 supplement.json；这比只说“有 120 个样本”更准确。八组不足以支持强泛化推断；本轮不制造 p 值、置信度或样本级 bootstrap。

| 图 | 当前视觉与数据关系 | 最小调整 |
|---|---|---|
| Figure 1 概念图 | 概念示意，不是实测几何 | 保留 conceptual，避免作为守恒实现已正确的证据 |
| Figure 2 地图 | 映射数为 R002=15、R003=29、R004=140、R005=6、R006=8、R007=2、R008=193 | 表1原手写0/23/46计数必须替换；R001仍为0；地图不是流向验证 |
| Figure 3 RMSE | 图上新值正确，旧图注结论反了 | 本轮已改图注；最终增加可行性标记或表注 |
| Figure 4 scatter | 与当前 OOF 相符，含3个零预测 | 标识 clipped 点；主图保留全范围，可增加低浓度 inset，不能删极端点 |
| Figure 5 surface | 新profile曲线，图例“model point”容易误读；宽图缩到单栏很小 | 共享参数/固定边界写清；最终拆分或横向双栏提高标签可读性 |
| Figure 6 scale | unique-cell mean，39/32/27 | 不当作完整同步预算；说明非独立和已排除study_reach |
| Figure 7 sparse | 图内正确为三项与−0.448，正文旧值错 | 本轮同步并标 provisional；重算后整图替换 |
| S1 subgroup | MLP支流0.0470优于0.0635 | 本轮已修正文相反结论 |
| S2 flux | a 是未加面积的密度求和，表2是ΣF*A；两者单位不同 | 本轮明确图注；最终建议改 a 为与表一致的ΣF*A，并保留原密度数据为附表 |
| S3 box | 43/36/32个cell-date，而非39/32/27 spatial cells | 本轮修正图注，不称 independent cells |

图号1/2首次出现顺序为原稿历史顺序。本轮为便于逐项对照保留图号，投稿前可统一交换编号；无需改动科学数据。宽图 S2、Figure 5 适合独立横向页或更大版芯，不应把缩小后文字难辨当作科学清晰。

## 九、修复顺序与验收命令

补充小问题：`hydraulic_geometry_raymond` 同时使用 W=12.88Q^0.42、h=0.4Q^0.29、u=0.19Q^0.29，因此 uWh=0.97888Q，不严格等于Q。原方法又写“所用速度为Q/A_c”，前后不完全一致。本轮新稿已准确写为三条经验关系。最小修改是解释该2.112%的连续性偏差；若改用u=Q/(Wh)，必须重算k、Re、Fr、Da等，不可只改一句话。

1. 保存当前快照和原始输入哈希，禁止覆写原始 Excel。先关 P0-02 几何与 P0-03 可行性，再改 sparse / q_A。
2. 单元测试从“helper存在”升级到“生产代码实际调用正确”；记录每个测试名称与通过数。增加 `requirements-dev.txt` 固定 pytest 及一个真实验证的 Python/依赖组合。
3. 在独立输出目录从原始输入或锁定处理阶段重建，记录明确起点。不要用 `--from-stage 14` 的后段运行清单宣称 full raw-to-paper。
4. 生成全部 OOF、逐河段、feasibility、length、filter、profile 表，再绘图。只有这个新 run 的表可进入新稿。
5. 新稿数值由模板读取；输出 MD/HTML/PDF 和全部图的 SHA256、配置、依赖、git commit + dirty patch。读取已生成 PDF 验数并渲染看图表。

```powershell
# 本轮已经完成的只写审查目录的复核，可重复；不是最终科学修复验收。
.\.venv\Scripts\python.exe '审查文档\20260927\audit_current.py'
.\.venv\Scripts\python.exe '审查文档\20260927\retrain_probe.py'
.\.venv\Scripts\python.exe '审查文档\20260927\supplement_probe.py'
# 完成环境及上述生产修复后的预期验收（本轮未宣称已完成）：
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
.\.venv\Scripts\python.exe scripts\verify_paper.py --mode submission
```

## 十、三份独立审稿的整合与纠偏

Reviewer_1/2/3 在相互不可见结论的情况下审查同一冻结包，先冻结后整合，原报告不回写。三者一致指出版本漂移、网络对象不清和结论范围问题。主审另行重训并做来源/守恒探针后补充以下限定：

- R1据原表把多个reach解释为无NHD匹配；R3指出当前mapping实际上有匹配。最终采用映射CSV计数，不把“表中0”当真实没有线段。R001仍为0，路径有效性另需验证。
- R1/R3约94–95%的改善贡献，主审精确复算为93.8237%；以此为准。
- 各审稿因环境不同只执行部分测试或pytest失败；主审直接执行三文件全部34函数通过。pytest缺失属环境完整性问题，不能说34算法测试失败。
- 工作树dirty不是科研问题；当前旧manifest与文件不一致才是可追溯性问题。
- q_A来源声明不实但当前反演数值一致，不能将该实现风险夸大成已观察到的数值失真。
- 数百万mol/d面积诊断没有独立通量真值，不能仅据大数宣判“物理不可能”；负浓度截断及守恒残差则是具体可验证的可行性问题。

## 十一、文字优化的边界与来源

新稿保留全部章节、10张原始图和9个表号，补足数据归属、不同网络对象、公式逆解、折内数据流、统计权重、剪裁失效、稀疏分支状态。以自然、具体、可核实的科学英语替换“honest negative result”“not merely weak”“cannot discriminate at all”等口号式或绝对化表述。不增加虚构经历，不承诺通过AI检测。

参考：[humanizer](https://github.com/blader/humanizer)、[human-writing](https://github.com/KKKKhazix/human-writing)、[no-ai-slop](https://github.com/petergyang/no-ai-slop)、[Manchester Academic Phrasebank 方法写作](https://www.phrasebank.manchester.ac.uk/describing-methods/)。这些是表达指导，不是证明数据真实的来源。human-writing偏中文散文，未机械套用其标点禁令或删减篇幅规则；用户“内容不要减少”和学术准确性优先。补全已有正文所引 Ulseth 的文献信息依据[出版社记录](https://www.nature.com/articles/s41561-019-0324-8)，其余参考文献未宣称完成逐条外部全文核验。
