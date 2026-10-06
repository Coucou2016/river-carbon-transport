# Reviewer 1 独立审稿报告

## 审查设置与材料边界

本报告仅依据冻结材料包 `tmp/review_20260919/packet` 中的 `paper.md`、`paper.html`、源码、脚本、测试、配置、结果表、README、依赖文件与流水线入口。仅以只读方式确认了根目录 `data_raw` 中部分输入文件的存在性。未读取根目录 `docs`、既有审查文档、`paper_versions`、其他审稿意见，也未联网检索。因而，对先前工作的优先权和文献覆盖度只能作材料内判断，不能作外部查新结论。

审查重点是物理离散、河网路由、水量与碳质量守恒、分组验证独立性和代码可执行性，同时覆盖原创性、重要性、跨学科读者、技术可靠性和非专业读者可读性。未修改科学代码或冻结材料包。

### 证据类别说明

- **静态判断** 指论文、源码、测试定义和冻结结果文件之间的逐行核对。R1-M2、R1-M3、R1-M5 和 R1-M6 主要属于这一类。它们指出代码按当前文本形成的依赖关系或 estimand，不声称已重跑全部科学流水线。
- **实际运行证据** 仅包括报告末尾列出的三个只读命令和一个内存小实验。R1-M1 中 `verify_paper.py` 的 10 个警告与退出码，以及 R1-M4 的串联聚合返回值属于这一类。
- **未运行事项** 完整 pipeline 会写出数据和结果，故按任务边界没有执行。120 个样本的全部指标没有独立复算。凡依赖全流程重算的结论均写成验收要求，而不是声称已经验证。

## 总体评估

稿件提出的科学问题重要，也有清楚的方法学动机。把机器学习闭合项重新插入河网输运方程，再以分组持出浓度评分，而不是只报告残差拟合，是值得发展的思路。单样本下 (k) 与 (S_{sgs}) 的代数补偿关系也直观且具有教学价值。

但是，当前稿件尚不能由同一冻结代码和结果包复现。最直接的问题是，论文称 MLP 在持出河段上劣于 Baseline，而包内最新主指标表称 MLP 优于 Baseline。除此之外，Residual-AI 的训练目标并未在每个持出折内重建，持出河段的观测浓度可以沿网络进入训练河段的残差目标。样本位置定义的控制体只覆盖几何河长的一小部分，未采样河段在前向模型中零面积通过，因而所谓“完整河网重新求解”并不是固定空间离散上的完整输运。滤波实验又把串联样本的 (QC) 相加为所谓守恒量，并在极低同步覆盖下把结果解释成“真实未解析过程”。这些问题直接影响主结论，而不仅是表述瑕疵。

在完成折内无泄漏目标构造、固定河网离散、真实守恒审计和全流程重算之前，我不建议把当前版本视为可送审的稳定稿。建议立场是实质性重大修订后重新评估。这不是编辑决定。

## 主要优势

- 科学问题明确。稿件没有把浓度拟合自动等同于过程真实性，并主动讨论 (k) 与未解析源项之间的补偿。
- 方程单位在局部一箱模型中基本写清。`paper.md:52-60` 明确区分水面面积、流量和日尺度换算。
- 代码中已有若干正确的防护意图。河网拓扑包含环检测，见 `src/network_topology.py:122-141`。汇流采用流量加权混合，见 `src/real_network.py:382-391`。当前通量评分函数也明确知道重叠样本面积不是研究区总量，见 `src/12_nested_cv_transport.py:101-106,164-170`。
- 稿件对缺少独立通量观测、样本不均衡和水力几何替代关系有所披露，见 `paper.md:33,45,68,228`。

## 预期读者

最可能感兴趣的读者包括河流碳循环与水文生物地球化学研究者、环境模型评估研究者、河网输运数值模型开发者，以及研究物理约束机器学习和闭合参数化的读者。若能建立严格的河网离散和无泄漏验证，本工作可作为“预测技能不等于过程可辨识性”的具体案例。当前实现问题尚使这一广泛意义停留在潜力层面。

## 重大意见

### R1-M1 论文主结论与冻结结果互相矛盾

**Blocking** Yes

**轴** technical soundness, reproducibility, claim moderation

**论文 claim pointer** `paper.md:18,142,146,203,233` 声称持出河段 MLP RMSE 为 0.0602，高于 Baseline 0.0485，因此 Residual-AI 不改进浓度预测，并产生 2.43×10^8 mol d⁻¹ 的通量诊断。

**源码和结果证据** 最新 `results/tables/nested_cv_metrics.csv:3,6-7` 给出 Baseline 0.048574、MLP 0.036825、RF 0.104991，MLP 实际优于 Baseline。相应重叠样本面积通量为 Baseline 1213.85、MLP 1,943,972 mol d⁻¹，并非论文的 4.29×10³ 和 2.43×10⁸。`results/tables/paper_main_results.csv:2-5` 和 `results/tables/paper_claim_guard.json:2-18` 保留另一套旧数字。`results/tables/artifact_manifest.json:3-6,14-38,73` 表明清单只是部分 smoke 运行，并明确写着标题级科学结论在完整重算前仍被阻断。只读执行 `python scripts/verify_paper.py` 也报告 MLP 与 RF 的 RMSE drift 以及多项禁用表述，但仍以退出码 0 标记 PASS。

**影响** 这不是舍入误差，而是改变 Residual-AI 是否优于 Baseline的方向，直接推翻摘要、结果、讨论、结论和图题中的中心负结果。当前读者无法判断哪套输出属于提交版本，也无法确认图表是否来自同一运行。

**具体修改建议** 建立一个不可手工覆写的结果源。完整流水线成功结束后，由同一 manifest、同一预测表自动生成主表、所有图、摘要数字和正文数字。删除“冻结开发数字”与“最新重算数字”双轨机制。把 `verify_paper.py` 的数值漂移、禁用表述和 manifest 非完整状态改成非零退出。提交时固定干净 commit、环境锁文件、输入哈希和全阶段产物哈希。

**验收测试** 在全新目录中以固定 Python 3.12 环境运行完整流水线两次。两次产物哈希和主指标一致。自动测试逐一解析摘要、正文、表 2 至表 9 和图数据，确认每个数字与唯一机器表一致。任一 RMSE 方向改变、旧结果文件存在或 manifest 标记 dirty、smoke、blocked 时，构建必须失败。

### R1-M2 Residual-AI 的持出折存在网络传播型目标泄漏

**Blocking** Yes

**轴** experimental design, reproducibility, causal versus correlative interpretation

**论文 claim pointer** `paper.md:111-113,142,233` 把评估描述为按河段持出、上游边界独立且目标盲的 transport-coupled evaluation。

**源码证据** `src/12_nested_cv_transport.py:294-320` 在进入 LeaveOneGroupOut 前直接读取整表 `y_sgs`，每折仅切片 `y_sgs[tr]` 拟合 Residual-AI，没有像 k-correction 那样调用折内重建函数。该整表残差来自 `src/real_network.py:503-550`。在诊断中，某样本的观测浓度在 `src/real_network.py:549-550` 被设置为下一个样本或下游汇流的状态。因此，若持出河段位于某训练河段上游，持出观测会参与下游训练样本的 (C_{in}) 和 (S_{sgs})。相反，k-correction 明确删除持出样本后重建目标，见 `src/12_nested_cv_transport.py:198-241,321-323`，这恰好显示 Residual-AI 缺少同等隔离。

**影响** 分组持出的统计独立性未成立。模型可能间接看到持出河段浓度，当前 MLP 优于 Baseline 的最新结果尤其不能解释为跨河段泛化。即使采用论文旧数字，“未能泛化”的比较也不是严格无泄漏检验。

**具体修改建议** 为每折重建训练网络诊断。先移除持出河段的所有观测浓度，再在固定物理网格上计算训练节点的上游状态和残差目标。若删除持出支流使下游训练节点边界未知，应把这些受影响节点从该折训练集中排除，或使用完全外生且不含持出观测的边界模型。Residual-AI、稀疏闭合和 k-correction 必须共用同一折隔离规则。

**验收测试** 新增干预式泄漏测试。将某持出河段的所有 (C_{obs}) 乘以 10 或随机置换，折内训练目标、训练模型参数以及不依赖该河段外生边界的训练节点预测必须逐位不变。另输出每折的依赖图和被排除节点数，证明任何训练 target 的祖先中不存在 held-out observation。

### R1-M3 前向输运使用由采样位置决定的可变控制体，并忽略大部分未采样河长

**Blocking** Yes

**轴** mechanism evidence, hydrological validity, technical soundness

**论文 claim pointer** `paper.md:52-62,83-91,111-118,235` 称每个样本对应控制体，闭合项被重新插入相同河网输运，并对完整准稳态网络重新求解。

**源码证据** `src/real_network.py:86-110` 仅以同日同 segment 的样本 chainage 中点生成长度，单样本一律赋 100 m。`src/real_network.py:128-138` 使空间离散随日期和采样密度改变。`src/real_network.py:395-398` 对没有样本的 segment 直接传递浓度，不赋面积，也不施加气体交换。包内 `results/tables/length_conservation.csv:2-17` 显示控制体总长度通常只占 NHD 河长约 0.5% 至 12%，但 R002 又达到 492%。所谓“conservation”函数只在大于 50 或 100 km 时警告或报错，见 `src/real_network.py:171-184`，没有要求控制体铺满且不重叠覆盖物理河长。

**影响** 模型求解的是“样本周围若干短箱体”，不是固定网格上的全河网平衡。未采样河段的气体交换和输运衰减被设为零，面积和停留时间随采样设计变化。不同日期、河段和交叉验证折的物理算子不相同，浓度 RMSE、(k_{need})、(S_{sgs}) 及通量分配均受到采样几何驱动。因而，当前“transport-coupled”对比不能隔离闭合项差异。

**具体修改建议** 先建立与观测无关的固定河网有限体积网格。每个 NHD 流线或预定义子段都具有固定长度、宽度、面积、流量和下游连接。观测仅用于与网格状态比较，不创建或改变控制体。所有未采样单元也必须推进水量和溶质质量，并施加气体交换及已规定的源项。支流汇入时分别审计 ΣQ 和 ΣQC，网络出口审计全域碳收支残差。

**验收测试** 对每日期要求固定网格长度和面积完全相同。每条河段控制体长度之和与几何长度相对误差小于预设容差。对无源、无气体交换的合成 DAG，出口 ΣQC 等于入口 ΣQC 至机器精度。对已知解析解的单河段衰减问题做网格收敛测试。随机删除观测点后，前向物理解不得改变，只能改变评分样本数。

### R1-M4 滤波算子没有证明串联质量守恒，且现有覆盖不支持“真实未解析过程”解释

**Blocking** Yes

**轴** mechanism evidence, data-resource quality, claim moderation

**论文 claim pointer** `paper.md:18,83-91,175-177,219` 报告 Δx 从约 591 m 到 73,109 m 时 |(S_{sgs})| 约为 3.72 至 3.93，并据此称残差由“真实未解析过程”而非分辨率截断主导。

**源码和结果证据** 对同一串联河道单元内的多个样本，`src/cell_dag_filter.py:248-266` 计算 `sigma_qc = sum(Q_i C_i)`，将多个沿程状态作为并联通量相加，再把浓度设为该和除以 ΣQ，同时又把 Q 设成最后一个样本的出口流量。对串联状态，这三个量不能同时代表同一控制体出口。`src/cell_dag_filter.py:68-92,307-324` 在上游状态缺失时使用可用父节点或 (C_{eq})，并继续诊断。现有结果自己标记为 sampling-conditional sensitivity。`results/tables/filter_scale_metrics.csv:2-5` 显示每日期被诊断单元比例仅约 0.8%、1.3%、2.2% 和 18.6%，平均不同步节点数仍为 3.8、3.3、2.9 和 0.7。其最新数值 3.988 至 4.195、587 至 40,153 m、方差 21.834 至 21.524 也与论文数值不一致。

**直接小实验** 在不写文件的独立调用中输入两个串联样本 (Q=1)，(C=1,3)。`aggregate_samples_in_cell` 返回 `Q=1, C=2, Sigma_QC=4`。物理出口 (QC) 应为 3。现有单元测试把 `Sigma_QC` 的代数相加当成守恒目标，见 `tests/test_cell_dag_filter.py:206-247`，因此测试通过并不能证明串联控制体的质量守恒。

**影响** 观测密度、同步覆盖和串并联混用足以制造或掩盖尺度不变性。当前实验最多是稀疏采样条件下的算子敏感性，不能区分分辨率截断、边界替代、观测布局和真实过程。该结论进入摘要并被列为框架贡献，故为阻断项。

**具体修改建议** 对串联粗化采用边界通量而不是沿程 (QC) 求和。粗单元的入流取最上游边界，出流取最下游边界，面积和源汇在内部求和。并联支流才使用 ΣQ 与 ΣQC。不要在上游父节点缺测时继续把结果标为完整诊断，应显式设为不可识别或进行经验证的边界同化。正文应在修复前删除“真实未解析过程”因果解释。

**验收测试** 建立具有已知源汇、串联段和汇流节点的同步合成网络。分别在 1、2、4 段粗化后，水量、入口与出口碳通量及积分源汇闭合到机器精度，且恢复相同的已知 (S)。对真实数据报告仅含完整上游状态的结果，并做采样稀疏化和日期同步敏感性分析。若只能保留当前数据，结论应降格为 sampling-conditional sensitivity。

### R1-M5 通量 estimand 被论文误写成研究区总量，并与当前代码数值不一致

**Blocking** No

**轴** technical soundness, figures and tables, readability

**论文 claim pointer** `paper.md:68,118,146,166` 把 (F_{CO2}A_s) 的和称为“summed over the study area”或研究区释放总量，并用它论证各闭合分配到不物理极端。

**源码和结果证据** `src/12_nested_cv_transport.py:101-106` 明确说样本在空间和日期上重叠，相关列不是研究区空间总量。`src/12_nested_cv_transport.py:136-170` 同时计算重叠样本面积和按日期唯一 cell 的平均值，并在元数据中写明 double-counts space/dates。`scripts/build_paper_tables.py:65-80` 却把重叠面积列重新命名为 `flux_area_sum_mol_d`，尽管 notes 又说不是研究区总量。当前 `nested_cv_metrics.csv:3,5-7` 的数值也与论文表不一致。

**影响** 单位虽为 mol d⁻¹，但统计总体不明确，不能解释为同一天、同一固定空间域的总释放。跨模型数量级比较还混入日期重复、控制体定义和样本覆盖差异。由于论文承认没有独立通量观测，此问题不单独推翻代数等效关系，但会使“物理极端”证据失真。

**具体修改建议** 选择并预注册一个明确 estimand。若目标是网络日总量，应在固定、非重叠网格上逐日积分，再按日期汇总不确定性。若只能保留样本诊断，应改名为 `overlapping-sample-area diagnostic`，不得称 study-area total，也不得据其绝对量级判断网络碳排放。

**验收测试** 构造重复同一日期或复制同一样本的测试。研究区日总量在复制观测后必须不变。固定网格各单元只计一次，且总量等于逐单元 (F A) 的独立手算结果。

### R1-M6 河网映射和汇流结构尚缺少足够的可验证性

**Blocking** No

**轴** hydrological validity, reproducibility, data-resource quality

**论文 claim pointer** `paper.md:41-47,83` 称 120 个样本映射到高分辨率有向 NHDPlus HR 网络，七条支流在映射汇流点进入六个主干段，并以真实流向过滤。

**源码和论文证据** 表 1 显示 R001、R002、R003、R005、R007 的 `NHD segments` 均为 0，见 `paper.md:244-255`。实际构网以每个 reach 最近流线的众数作为代表，见 `src/real_network.py:214-223,246-260`。遇到分叉时 `_first_mainstem_downstream` 只取 `ds[0]`，见 `src/real_network.py:226-240`。找不到主干汇流时设为 `np.inf` 并视为 independent，随后仍会进入按 y 阈值构造的逻辑树，见 `src/real_network.py:258-265,268-329`。滤波粗化还会删除不满足平均 rank 前进的 contracted edges，见 `src/13_filter_scale_sgs.py:217-238`。

**影响** 对多数逻辑支流，没有逐段 NHD 支持。最近线、单一代表流线、任取第一个下游分支和删除歧义边都会改变汇流位置和祖先关系。由于残差和交叉验证泄漏都依赖祖先结构，拓扑误差可能改变主要结论。

**具体修改建议** 输出可审计的 sample-to-flowline、flowline-to-reach 和 confluence 表，包括 NHDPlusID、snap distance、所有候选下游边、选边规则和人工核验标记。对 0-segment reach 不应同时声称有真实 NHD 离散。应补齐河道几何，或清楚定义为逻辑 lumped tributary 并降低“高分辨率河网”表述。

**验收测试** 每个样本必须唯一映射到连通流线且 snap distance 在阈值内。每个逻辑支流应有可追溯路径到正确主干汇流点。不得存在未解释的 `np.inf`、任意 `ds[0]` 或被静默删除的拓扑边。生成水量闭合表，逐汇流验证 (Q_{out}=\sum Q_{in}+Q_{lateral})。

## 小问题

### R1-m1

**轴** writing clarity, statistical rigor

**受影响元素** `paper.md:129,159,195,212`

**证据** 文中称 `profile likelihood`，但定义的是平方误差目标的逐 α 最小化，没有观测误差分布、似然函数或置信阈值。

**必要修正** 改称 profiled objective 或 profiled RMSE。若坚持 likelihood，应给出概率观测模型、方差处理和置信区间构造。

### R1-m2

**轴** reproducibility, writing clarity

**受影响元素** `paper.md:74,113`

**证据** 论文说 (C_{eq}) 随每个样本温度变化，但网络头水边界使用所有样本平均温度，见 `src/real_network.py:364-368,497-499`。

**必要修正** 区分单元内 (C_{eq}) 与头水边界 (C_{eq})。说明平均温度边界，并报告按日期或头水温度的敏感性。

### R1-m3

**轴** reproducibility, claim consistency

**受影响元素** `paper.md:104,157,210`

**证据** 论文称 k-only 不可行比例 61.7%，并称 18.8% 持出预测达到 (g=-12)。最新 `results/tables/k_correction_saturation.json:5-13` 给出不可行 72/120，即 60.0%，且持出预测达到 floor 的比例为 0，最小 (g=-4.276)。

**必要修正** 随完整重算统一数字，并区分 full-data target 不可行比例、各折训练比例和 held-out prediction saturation。

### R1-m4

**轴** technical soundness, readability

**受影响元素** `paper.md:134`

**证据** 稿件承认 Damköhler 特征将秒和 m d⁻¹ 混用，因此并非无量纲，却仍把它列入候选特征。

**必要修正** 在建模前修正时间单位并全流程重算。不能以“最终系数为零”证明错误特征没有影响，因为其存在可能改变标准化、正则化路径和选择结果。

### R1-m5

**轴** readability for nonspecialists

**受影响元素** `paper.md:54-60,87-91,123-129`

**证据** 方程本身清楚，但没有用一个简单示意解释 (S_{sgs}>0) 与减小 (k) 为什么都能提高过饱和浓度。

**必要修正** 增加一句符号约定和一个不带机器学习的单箱例子，避免非专业读者把“equifinality”误解为两个模型在所有状态下相同。

### R1-m6

**轴** reproducibility

**受影响元素** README 与测试入口

**证据** `README.md:5,12,60,105` 仍使用“嵌套 CV”及另一套旧 RMSE。以系统 Python 而非项目 `.venv` 执行全测试时，`tests/test_network_p0_fixes.py` 因缺少 geopandas 在收集阶段失败，另一 Python 3.12 解释器未安装 pytest。该输出只说明入口环境不明确，不证明项目 `.venv` 不可执行。`requirements.txt` 未列 pytest，也没有独立开发依赖文件。

**必要修正** 提供明确的开发依赖或 `requirements-dev.txt`，CI 固定 Python 3.12，并使 README、命令、方法名称和产物版本同步。当前设计无 inner loop，应始终称 grouped leave-one-reach-out CV。

### R1-m7

**轴** reproducibility, testing

**受影响元素** `tests/test_cell_dag_filter.py:206-247` 与 `tests/test_network_p0_fixes.py:59-147`

**证据** 当前测试主要验证内部代数定义和“不要过大”，没有验证固定物理网格覆盖完整河长、串联边界质量守恒、折内观测祖先隔离、论文数字与当前结果单一来源。

**必要修正** 将 R1-M1 至 R1-M5 的验收测试加入 CI，并要求失败时非零退出。

## 技术缺陷中必须先解决的项目

必须先解决 R1-M1、R1-M2、R1-M3 和 R1-M4。四者分别对应结果版本、验证独立性、前向物理离散和滤波守恒。任何一项未解决，当前“transport-coupled grouped evaluation”与“scale-invariant unresolved process”均不能作为已建立的中心证据。R1-M5 和 R1-M6 也应在提交前实质修正。

## 五轴评价

| 评价轴 | 当前判断 |
|---|---|
| 原创性 | 将闭合项重插入河网输运后再做分组评估，以及用目标面展示 (k) 与 (S_{sgs}) 补偿，组合上有方法学潜力。由于本次不联网且材料只含有限参考文献，无法核实相对既有研究的完整优先权。当前实现缺陷使原创贡献尚未被可靠示范。 |
| 科学重要性 | 浓度技能与过程可辨识性之间的差别对河流碳预算很重要。若严格验证，负结果也有价值。但现有主指标冲突、泄漏和离散问题阻断科学解释。 |
| 跨学科读者 | 水文、碳循环、环境建模和物理约束机器学习读者都可能关注。当前大量实现细节与声明冲突，会显著降低广泛读者的信任和可读性。 |
| 技术可靠性 | 目前不足。关键问题是结果版本不一致、Residual-AI 折间泄漏、采样驱动控制体、串并联质量量混用、通量 estimand 错置和拓扑审计不足。 |
| 非专业读者可读性 | Plain Language Summary 和问题动机较清楚。术语 `profile likelihood`、`mass-conservative`、`study-area total` 和“真实未解析过程”目前过强，会误导非专业读者。 |

## 建议立场

当前版本需要重大修订并完整重算后再评估。最稳妥的保留核心是局部质量平衡中的 (k) 与 (S_{sgs}) 代数补偿，以及“浓度误差不足以验证过程分配”的受限论点。机器学习优劣、网络通量数量级和尺度不变性结论必须等待修复后的统一结果。

## 直接验证记录

- `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q tests/test_cell_dag_filter.py ...` 得到 `11 passed in 0.71s`。
- 同条件以系统 Python 运行全部测试时，在收集 `tests/test_network_p0_fixes.py` 阶段因 Python 3.14 环境缺少 `geopandas` 失败，退出码 1。另一 Python 3.12 解释器缺少 pytest。任务后续环境信息表明项目 `.venv` 具备 geopandas 等依赖，但为保持冻结范围，本报告没有再启动新的动态检查。因此这条只作为运行入口与开发依赖未自说明的证据，不作为科学代码失败证据。
- `PYTHONDONTWRITEBYTECODE=1 python scripts/verify_paper.py` 输出 10 个警告，包括 MLP 与 RF RMSE drift、`genuine unresolved process`、`summed over the study area` 等禁用表述，但脚本仍输出 `Claim guard PASS` 并以退出码 0 结束。
- 独立串联聚合小实验返回 `{'Q_m3s': 1.0, 'C_mol_m3': 2.0, 'Sigma_QC': 4.0, 'area_m2': 1000.0}`，而同一串联路径的物理出口 (QC=1\times3=3)。

## 风险与不可评估事项

- 未联网，不能对文献遗漏、全球首创性或目标期刊适配作确定判断。
- 冻结包未包含可直接从零运行所需的完整 `data_raw` 和生成中的 `data_proc`。原始数据仅按授权做只读存在性检查，没有运行会写输出的流水线。因此未独立复算 120 个样本的科学指标。
- 没有独立气体交换、河宽河深或同步全网观测，物理过程正确性不能由现有浓度资料单独验证。
- 本报告没有读取历史结论或其他审稿报告，意见为该冻结材料包上的独立判断。
