# Reviewer 2

## 审查设置

- **审查范围** 仅审查冻结数据包中的 `paper.md`、`paper.html`、`report.pdf`、代码、配置、测试、`data_proc` 与 `results`。未读取任何其他审稿报告、汇总或历史审查文档。
- **侧重点** 主张与证据一致性、数据来源、可识别估计量、统计推断、原创性与科学意义，同时覆盖跨学科兴趣、技术可靠性和非专业读者可读性。
- **评估边界** 数据包没有独立气体交换观测、实测河道横断面或外流域验证。原始观测被明确标为公开再分析数据，不是作者自行采集的数据。此事实本身不构成数据诚信问题。
- **可见证据** 120 个公开战役样点，8 个逻辑河段，分组留一河段预测，模型输出表，过滤尺度结果，目标曲面代码与生成的 81 页报告 PDF。
- **缺失材料** 缺少能够把当前稿件、PDF、表格、图件和代码输出锁定为同一提交版本的有效清单。现有清单反而声明工作树为 dirty，且称核心主张仍被阻断。

## 总体评估

稿件提出了一个有价值的负结果与方法学警示。仅用浓度误差评价河网碳模型时，源汇项与气体交换项可能产生补偿，因而过程解释不能由较低 RMSE 自动推出。公开数据再分析、折内重建训练目标和对通量估计量边界的主动说明都是优点。

但当前数据包尚不能作为一致、可核验的科学记录。论文正文、正文表格、机器可读结果、代码生成逻辑和最终 PDF 同时给出相互冲突的主结果。更重要的是，标题和结论使用了“不能识别”的一般化语言，而核心证据是一个在固定观测上游浓度下、用统一 `alpha` 和统一 `S` 构造的等权 profile SSE。单样点零谷是一个方程含两个自由参数的代数结果，不能单独承担网络尺度或统计识别性的主张。以下两个问题在解决前阻断中心论证。

## 谁会对结果感兴趣，以及原因

河流碳循环、水文模型校准、环境模型评价、物理约束机器学习和地球系统参数化研究者会关注这一工作。最有潜力的贡献不是某个 AI 模型取得更高精度，而是展示浓度拟合、过程分配和通量诊断之间可能脱钩，并给出一个可审计的输运耦合评价框架。若主张被严格限定，这一信息也能服务于更广泛的环境模型可识别性研究。

## 主要优点

1. 数据来源边界总体透明。`data_proc/data_provenance.csv:2-8` 明确列出 HydroShare、USGS、NHD 和 WQP 来源，并标明没有合成回退。
2. 代码针对持出标签泄漏、汇流混合、控制体长度和通量估计量设置了专门测试。只读直接执行的 21 个可独立运行测试全部通过，覆盖 `test_network_p0_fixes.py` 和 `test_cell_dag_filter.py` 中的核心守恒与泄漏门控。
3. 稿件主动承认观测支持不均、几何来自经验关系、缺少独立逸散观测和跨流域验证，见 `paper.md:33,41,45,228,235`。
4. 通量被限定为重叠样点面积诊断量，而非流域总量，见 `paper.md:68,118` 和 `results/tables/paper_main_results.csv:2-6`。这一限定是必要且正确的。
5. 稿件没有把样内拟合当作主要预测证据，并明确说明当前分组交叉验证没有内层调参，见 `paper.md:111-113,142`。

## Major Concerns

### R2-M1 结果版本不一致，当前提交物不是单一可核验快照

**Severity** Major  
**Blocking** Yes  
**Axis** reproducibility, data-resource-quality, claim-moderation  
**Claim pointer** 稿件声称正文、表格、图件和公开代码共同支持同一组留一河段结果与过程解释，见 `paper.md:142-195,233-240`。  
**Evidence pointer** `paper.md:142,144,148,157-168,184-195,259-325`；`results/tables/paper_main_results.csv:2-6`；`results/tables/subgroup_metrics.csv:2-17`；`results/tables/k_correction_saturation.json:8-13`；`results/tables/dimensionless_sparse_summary.json:11-22`；`results/tables/equifinality_summary.json:9-23`；`results/tables/artifact_manifest.json:13-16,66-84`；`report.pdf` 第 2、14 至 18、55、62、79 至 80 页。  
**Concern** 多处矛盾直接改变科学叙述。

- `paper.md:142` 给出 MLP MAE 0.0336 和 bias 0.0187，而主结果表给出 0.0214 和 -0.0055，见 `paper_main_results.csv:4`。
- `paper.md:144` 称 MLP 在多样本支流的 RMSE 为 0.0835 且差于基线，但当前结果为 0.0470 且优于 0.0635，见 `subgroup_metrics.csv:4,12`。同段的 R008 与随机森林数值也不匹配。
- Figure 3 图注写“没有闭合优于 Baseline”，见 `paper.md:148`，但同页文字和主结果表均显示 MLP 点 RMSE 更低。
- `paper.md:157` 称 `k_eff/k_emp` 中位数为 `3.9×10^-5`、`k_eff` 为 0.0066 m d^-1、18.8% 预测触底。当前输出是中位比 0.539991、`k_eff` 123.3293 m d^-1、触底比例 0，见 `paper_main_results.csv:3` 和 `k_correction_saturation.json:11-13`。
- Figure 5 图注报告 0.0409 至 0.0465，正文与当前 JSON 报告 0.0360 至 0.0396，见 `paper.md:159,195` 和 `equifinality_summary.json:16-23`。正文给出的最佳 `alpha` 和 `S` 也与 JSON 不同。
- 稀疏闭合正文报告 RMSE 0.0588、R2 -1.55 和双项方程，机器结果报告 0.05285、R2 -0.448 和含 `log10(Da)` 的三项方程，见 `paper.md:184-190` 和 `dimensionless_sparse_summary.json:11-22`。
- `report.pdf` 是另一套更早结果。其第 2 页给出 Baseline 0.0284、MLP 0.0573、k 修正 0.0244，并在多页重复“k 修正改善、MLP 变差”。这与当前稿件的 0.0486、0.0372、0.0486 结论相反。
- 清单记录 dirty 工作树，且其三个已列产物的实际大小或 SHA256 与清单不一致。清单自身在 `artifact_manifest.json:84` 写明核心科学主张在完整重算前仍被阻断。

这些差异不能被视为局部排版问题。读者无法判断哪个数字、图件和结论属于拟提交分析。

**Why it matters** 所有后续原创性、显著性、模型比较和过程解释都依赖一个确定的结果版本。当前状态下，中心论证不可复核，且同一数据包可导出相反结论。

**Minimal repair** 选定一个权威、不可变的分析快照。仅从该快照生成 Markdown、HTML、PDF、表格、图件和清单。删除所有历史数值与叙述，不需要新增实验。

**Resolution test**

1. 生成并校验包含全部提交产物 SHA256、代码提交号、配置哈希和运行命令的清单，要求工作树状态与提交说明一致。
2. 增加一个跨产物一致性测试。它应从机器结果读取主指标，并逐项验证摘要、结果段、表格、图注、HTML 和 PDF 文本中的数值与方向性陈述。
3. 测试至少覆盖 MLP 与 Baseline 的 RMSE 比较、分组 RMSE、`k_eff/k_emp`、触底比例、profile RMSE 区间、稀疏方程和稀疏闭合 RMSE。
4. `scripts/verify_paper.py --mode submission` 必须在任何一项矛盾存在时失败。目前该命令只因 dirty 清单和 `independent cells` 短语失败，却没有识别上述数值矛盾。

### R2-M2 中心“不可识别”主张超出了所定义的估计量

**Severity** Major  
**Blocking** Yes  
**Axis** mechanism-evidence, statistical-rigor, claim-moderation  
**Claim pointer** 标题、摘要和结论称 concentration-only observations 不能识别 `S_sgs` 与 `k` 的过程分配，且 `paper.md:205` 进一步写成“cannot discriminate ... at all”，见 `paper.md:1,10,18,195,205,212,233`。  
**Evidence pointer** `src/16_equifinality_surface.py:41-76,85-110,113-168,292-316`；`results/tables/equifinality_summary.json:7-23`；`paper.md:123-129,193-195,212`。  
**Concern** 核心诊断混合了三个不同层次。

1. 单样点零谷是固定 `C_in`、`q_A` 和 `C_eq` 后，一个浓度方程同时允许 `k` 与 `S` 自由变化的代数非唯一性。它证明的是该局部条件方程欠定，不是河网模型、closure function 或统计模型的一般结构不可识别性。
2. 汇总 profile 使用全体观测中的 `C_obs` 与观测路由得到的 `C_in_obs`，对所有样点施加一个统一 `alpha=k/k_emp` 和一个统一 `S`，并以等权 SSE 拟合，见 `src/16_equifinality_surface.py:85-110`。这不是持出预测估计量，也不是两类机器学习闭合的联合参数化。
3. “浅”由 RMSE 不超过最小值 10% 的代码阈值定义，见 `src/16_equifinality_surface.py:137-146`。稿件没有给出该阈值的科学依据、观测误差尺度、河段聚类权重或阈值敏感性。

稿件在 `paper.md:212` 承认这不是正式结构可识别性分析，但标题、摘要和结论没有始终保持这一边界。尤其“at all”与汇总 profile 仍有非零曲率相冲突。

**Why it matters** “practical equifinality under concentration-only observations”是标题和摘要的中心贡献。如果估计量只支持条件性的代数非唯一和特定 profile SSE 下的弱区分，就不能据此推广为浓度数据在该河网问题上普遍不能识别过程分配。

**Minimal repair** 不需要增加新观测。将中心结论改为“在本文固定边界、统一 `alpha` 与统一 `S` 的条件性 profile SSE 中，过程分配弱区分”。在方法中明确估计量、样点权重、固定量、profile 参数化和 10% 阈值。删除“at all”“confirm non-identifiability”等超出证据的表达，并把单样点零谷作为代数动机，而非网络尺度证明。

**Resolution test**

1. 代码测试应从公开输入重算 profile，并验证 `alpha`、`S`、RMSE 区间和样点权重。
2. 增加阈值与权重敏感性输出，至少报告等权样点与等权河段两个版本。若不做此最小敏感性，则只保留描述性结果，不使用识别性结论。
3. 文本测试应拒绝把单样点零谷表述为正式结构识别性证明，并拒绝“不能区分任何过程分配”的绝对措辞。

### R2-M3 MLP 的点 RMSE 改善没有与河段层级不确定性和影响度相匹配

**Severity** Major  
**Blocking** No  
**Axis** statistical-rigor, experimental-design  
**Claim pointer** 稿件强调 MLP 的留一河段 RMSE 为 0.0372，低于 Baseline 0.0486，见 `paper.md:9,18,142,233`。  
**Evidence pointer** `paper.md:41,111-118`；`results/tables/per_reach_cv_metrics.csv:2-9,18-25`；`results/tables/subgroup_metrics.csv:2-13`；`src/12_nested_cv_transport.py:347-464,575-591`。  
**Concern** 120 个样点不是 120 个独立泛化单位。实际只有 8 个持出河段，其中 3 个河段各只有 1 个样点，R008 有 58 个样点。由当前 per-reach 表可直接计算，MLP 相对 Baseline 的总平方误差下降约 94% 来自 R002 的 3 个极端样点。MLP 在 R004、R001 和 R007 上反而更差。当前主结果仅给样点加权汇总点估计，没有河段加权指标、折级配对差异或聚类不确定性。

**Why it matters** 当前数字可以支持“在这 120 个样点的样点加权 RMSE 上更低”，但不能支持稳定的跨河段改善，也不能用作模型优越性的统计证据。它同时影响科学意义，因为一个由 3 个极端样点主导的改善与可推广的 closure advance 不是同一结论。

**Minimal repair** 用现有预测即可完成。报告每个河段的配对损失差、等权河段汇总、删除 R002 和删除单样点河段的敏感性。给出按河段聚类的区间，或将所有改善表述严格限定为描述性点估计。

**Resolution test** 从 `nested_cv_holdout_predictions.csv` 按 `sample_id` 对齐 Baseline 与 MLP。测试应复现每个河段的平方误差差值、验证汇总改善的 R002 贡献比例，并确保摘要不把样点加权 RMSE 转述为跨河段稳定改善。若报告区间，重采样单位必须是河段而不是样点。

### R2-M4 原创性与广泛科学意义尚未由稿内比较建立

**Severity** Major  
**Blocking** No  
**Axis** novelty-significance, interdisciplinary-readership  
**Claim pointer** 稿件把“显式空间滤波、输运耦合分组评价和模型无关目标曲面”的组合框架作为贡献，并推及 concentration-primary model evaluation，见 `paper.md:29-33,224-235`。  
**Evidence pointer** `paper.md:25-33,212,235,327-339`。  
**Concern** 现有引言说明了问题重要，但没有清楚区分三类可能的创新。它们分别是已知质量平衡中的代数补偿、将留组预测重新代入输运方程、以及 East River 数据上的具体实证发现。最接近的河流模型工作只作背景介绍，等效性或可识别性文献没有形成直接对比，唯一“相关工作”还是 manuscript in preparation，见 `paper.md:31,331`。因此，从所给材料只能判断该组合在本案例中可能有方法学价值，不能判断其相对既有环境模型校准或河流碳模型工作的原创增量。广泛意义同样受到单流域、10 天战役、经验水力几何和缺少独立通量观测的限制。

**Why it matters** 技术上成立的案例研究不自动构成广泛、即时且深远的科学推进。若原创性主要来自协议组合，稿件应准确说明组合解决了既有工作中哪个可验证缺口。

**Minimal repair** 不需要扩展研究。重写引言最后两段与讨论，分别列出已有方法、本文新增步骤和本数据真正支持的新结论。把“识别性证明”降为条件性诊断，把科学意义定位为过程感知模型评价的可复核案例。用已发表文献替代对 in-preparation 工作的关键依赖。

**Resolution test** 摘要、引言和结论中的每一条原创性陈述都应能映射到一个明确的 prior-work 对比和一个当前结果。无法映射的 superlative 或广泛推广语句应删除或限定。

## Minor Comments

### R2-m1 作者与归属仍是占位符

**Severity** Minor  
**Axis** writing-clarity  
**Affected element** 稿件元数据。  
**Evidence pointer** `paper.md:3-4`。  
**Issue** 作者和单位仍写为待补充，无法形成完整提交物。  
**Required correction** 在冻结提交版本前补齐作者、单位、通讯信息和贡献声明。

### R2-m2 Figure 1 在 Figure 2 之后首次出现

**Severity** Minor  
**Axis** figures-and-tables  
**Affected element** 图件叙事顺序。  
**Evidence pointer** `paper.md:45-47,83,93`。  
**Issue** Figure 2 在数据部分先出现，Figure 1 到过滤方法部分才出现，增加非专业读者的导航负担。  
**Required correction** 调整图号或首次引用顺序。

### R2-m3 “unphysical”缺少判据

**Severity** Minor  
**Axis** claim-moderation  
**Affected element** 对残差闭合外推的物理解读。  
**Evidence pointer** `paper.md:146,166,203`。  
**Issue** 结果清楚显示源项和重叠样点面积通量诊断非常大，但稿件未定义何种经验或守恒边界使其成为“unphysical”。在没有独立通量观测时，证据直接支持的是“极端且不稳定”。  
**Required correction** 给出预先定义的物理范围，或改为“extreme and unstable relative to the Baseline diagnostic”。

### R2-m4 k-only 不可行目标与持出预测应分开表述

**Severity** Minor  
**Axis** writing-clarity  
**Affected element** k 修正解释。  
**Evidence pointer** `paper.md:157,210`；`results/tables/k_correction_saturation.json:4-13`。  
**Issue** 60% 指的是在 `S_sgs=0` 下反演 `k_needed` 非正，因而这些样点被排除出训练目标。当前持出模型仍为所有样点生成正的 `k_eff`，且没有触底。把模型称为“partly undefined”会混淆训练目标可行性与前向预测定义域。  
**Required correction** 明确区分 target infeasibility、training exclusion 和 OOF prediction behaviour。

### R2-m5 通量表头需要直接写出估计量和单位

**Severity** Minor  
**Axis** figures-and-tables  
**Affected element** Tables 2、3、7、9。  
**Evidence pointer** `paper.md:257-274,304-325`。  
**Issue** `F total` 容易被读成空间总通量，尽管正文已作限定。  
**Required correction** 把表头改为 `overlapping sample-area diagnostic, mol d^-1`，并在每个相关图注重复该限定。

### R2-m6 历史纠错叙述不应替代当前方法证据

**Severity** Minor  
**Axis** writing-clarity  
**Affected element** 对“earlier impression”的解释。  
**Evidence pointer** `paper.md:157,210`。  
**Issue** 正文提到早期结果由边界泄漏和 clipping 造成，但当前稿件没有定义该早期分析，也不需要依赖历史版本来建立现行结果。  
**Required correction** 删除历史版本叙述，或把它改成当前实现的正面方法说明，并由测试和代码位置支撑。

## 在中心论证成立前必须解决的技术问题

必须解决 `R2-M1` 与 `R2-M2`。前者要求形成单一、可验证、同源的提交快照。后者要求使中心识别性主张与实际 profile SSE 估计量严格一致。`R2-M3` 决定 MLP 点改善能否被解释为跨河段证据。`R2-M4` 决定案例价值能否上升为清楚的原创与广泛意义主张。

## 对五项标准的评估

- **原创性** 当前可见的是方法组合与案例应用的潜在原创性。相对于既有等效性、校准和河流碳模型工作的增量尚未被稿内比较建立。
- **科学重要性** 浓度拟合与过程归因脱钩是重要问题，但当前证据只支持 East River 条件性诊断。广泛重要性仍依赖主张校准和稳定的结果快照。
- **跨学科读者兴趣** 水文、碳循环、环境建模和物理约束机器学习读者均可能感兴趣。对更广泛读者最有价值的是估计量与过程归因的区别，而不是特定模型排行榜。
- **技术可靠性** 折内标签处理和若干守恒门控有实质改进，测试也提供正面证据。但跨产物矛盾和中心估计量外推当前阻断可靠性判断。
- **非专业读者可读性** Plain Language Summary 清楚，方法边界多处说明得当。数值互相冲突、图号顺序和“不可识别”层次混用会使非专业读者得到错误结论。

## 建议姿态

当前中心论证尚未由所给数据包建立。若作者先完成版本冻结并把识别性结论收窄到实际估计量，再用现有预测补充河段层级稳健性，稿件可形成一篇有价值的、边界明确的环境模型评价案例。此评价不构成期刊接收判断，也不承诺其符合 Nature 的最终编辑门槛。

## 不支持或不可评估的边界

- 不支持正式结构可识别性或统计 profile likelihood 的主张。
- 不支持流域总 CO2 逸散量或独立验证通量的主张。
- 不支持跨流域、跨季节或一般河网的泛化主张。
- 不支持 MLP 在跨河段意义上稳定优于 Baseline 的统计主张。当前仅有样点加权点 RMSE。
- 不支持将极端源项直接称为物理不可能，除非给出外部范围或约束。
- 无法从当前稿内比较判断该框架相对全部既有 equifinality 与 environmental-model calibration 文献的原创程度。
- 数据是公开数据再分析。来源不一致与版本不一致要求修复，但不应被描述为数据伪造或欺诈。

## 审查验证记录

- 直接执行 `test_network_p0_fixes.py`，10 项通过。
- 直接执行 `test_cell_dag_filter.py`，11 项通过，伴随两个空数组均值的 RuntimeWarning，不影响这 11 项断言结果。
- `.venv` 未安装 pytest，因此未能以 pytest runner 执行 `test_remediation_20260919.py` 中需要 pytest fixture 的测试。
- 执行 `scripts/verify_paper.py --mode submission`。它因 dirty 清单和 `paper.html` 中的 `independent cells` 短语失败，但未识别稿件与结果表的多项数值矛盾。
- 只读渲染并检查 `report.pdf` 全部 81 页。版式整体可读，但科学内容属于与当前论文相反的早期结果版本。

