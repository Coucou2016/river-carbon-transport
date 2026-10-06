# Reviewer 3 独立审稿报告

## 审稿设置与材料边界

- **评审重点**　论文逻辑，图表与数据一致性，方法叙述与实现一致性，图的视觉准确性，以及可发布的复现链。同时覆盖原创性、科学重要性、跨学科读者、技术可靠性和非专业读者可读性。
- **唯一材料包**　`tmp/review_20260919/packet` 内的 `paper.md`、`paper.html`、源码、脚本、测试、配置、处理后数据、结果、README、requirements 和 `run_pipeline.py`。仅在必要时只读查看 `data_raw`。未读取根目录 `docs`、`paper_versions`、既往审查文档或其他审稿意见，也未联网。
- **动态检查边界**　未运行会写出结果的全量流水线。执行了只读 `python scripts/verify_paper.py`。它返回退出码 0，但明确给出 10 个警告，其中包括 MLP 和随机森林的 RMSE 与冻结 guard 漂移，以及正文中仍存在 `independent cells`、`genuine unresolved process`、`summed over the study area` 和 `nested cross-validation` 等被脚本自身列为禁用或未关闭的表述。执行 `python -m pytest -q -p no:cacheprovider` 时，默认 Python 3.14 因缺少 `geopandas` 在收集阶段失败。按 README 指定的 Python 3.12 再试时环境缺少 `pytest`。因此本轮没有得到可执行的测试通过证据。为保持冻结包只读，未另写日志；上述命令、退出码和诊断冻结记录在本报告“复现与核验记录”中。
- **不可评估内容**　没有独立气体交换或河流 CO₂ 通量观测，没有其他流域外部验证，没有可直接提交的版本标签或干净提交状态。因而物理过程分配和跨流域推广均不可由本材料包验证。

## 总体评估

稿件提出把残差闭合重新耦合进河网输运并在河段留出条件下评价，同时用 (k\)-(S_{sgs}) 目标面展示浓度约束下的过程补偿。这个负结果导向的评价思路有方法学价值，也可能吸引河流碳循环、环境模型评价、数据驱动参数化和水文机器学习读者。

但当前版本尚不能支持标题、摘要和结论中的中心判断。最严重的问题不是模型表现差，而是冻结包内存在相互冲突的结果代际。正文和部分 PNG 使用 MLP RMSE 0.0602、随机森林 0.0750，而当前主结果表和当前 RMSE 图分别给出 0.0368 和 0.1050。前者意味着 MLP 不优于基线，后者意味着 MLP 明显优于基线。与此同时，正文把输运描述为在 NHDPlus HR 有向拓扑上求解，实际主评估代码却在 13 个逻辑节点上求解。残差学习的交叉验证目标由全数据诊断预先生成，未像 (k\)-correction 那样在每折移除留出样本后重建。滤波尺度的正文数字、表格和当前 PNG 也不一致，并且正文作出了结果生成器自身明确禁止的“genuine unresolved process”解释。通量则被正文写成研究区面积总量，而实现明确注明该量对日期和空间重叠样本重复计数。

这些矛盾共同切断了“代码到结果到正文到图”的发布链。现阶段建议立场是重大修改后重审。在中心数字、数据代际和折内目标构造没有统一之前，不应提交。

## 主要优势

1. 稿件主动报告机器学习闭合失败和外推失稳，没有把样本内拟合包装为泛化能力。
2. 质量平衡采用显式单位换算，并把 (S_{sgs}) 定义为带符号的源汇残差。正文也承认该残差可吸收观测误差、边界误差和结构误差，而非单一生物地球化学通量（`paper.md:52-68, 85-91`）。
3. 采用河段分组留出并报告主干、支流和单样本河段的异质性，方向上优于只给一个总体误差。
4. 对缺失横断面、协变量不完整、无独立逸散观测及样本极不均衡的限制已有较清楚披露（`paper.md:41-45, 228-235`）。

## 读者与潜在影响

最直接的读者是河流碳循环和河网反应输运研究者，因为论文讨论如何区分气体交换与未解析源汇。环境模型评价和科学机器学习读者也会关心“先诊断残差、再闭合、再回插物理模型”的评价协议。若结果链得到统一，负结果对于提醒读者不要用单一浓度误差解释过程正确性具有实用价值。当前单流域、单次十日调查且无独立通量约束，使其更像有价值的方法学案例，而不是已经建立的普适河流碳规律。

## 重大意见

### R3-M1　冻结包混用互相冲突的结果代际，中心结论可被直接反转

- **Blocking**　Yes
- **轴**　技术可靠性，图表一致性，可复现性，主张节制
- **论文 claim pointer**　摘要和结果称 MLP 与随机森林 RMSE 分别为 0.0602 和 0.0750，均不优于 0.0485 的 Baseline（`paper.md:18, 140-150, 231-235`）。表 2、表 3 和表 5重复同一判断（`paper.md:257-294`）。
- **代码或图表精确证据**　当前 `results/tables/nested_cv_metrics.csv:3,6-7` 的 loo-reach 数字是 Baseline 0.048574、MLP 0.036825、随机森林 0.104991。`results/tables/nested_cv_summary.json:7-14` 同样记录 MLP 优于 Baseline，并把 `mlp_beats_baseline_loo_reach` 设为 true。当前 `results/figures/nested_cv_rmse_bar.png` 视觉上标注 0.0486、0.0368、0.1050、0.0486。相反，`results/figures/nested_cv_scatter_holdout.png` 的图内统计仍是 RMSE 0.0602、MAE 0.0336、R² -1.009，与当前结果表和当前 RMSE 图矛盾。`results/tables/paper_main_results.csv:2-5` 又保留旧值 0.0485、0.0602、0.0750、0.0486。`scripts/verify_paper.py:57-97` 在 `post_fix_development_numbers` 为真时仅把这种漂移降为 warning，因此退出码 0 不能证明论文数字一致。`results/tables/artifact_manifest.json` 还明确写明当前是 smoke 运行、工作树 dirty，且 headline claims remain blocked。
- **影响**　中心结论“Residual-AI 不优于 Baseline”取决于选择哪一代文件。正文、主表、散点图和柱状图不能同时为真。读者也无法知道哪个产物具有提交权威性。
- **具体修改方案**　删除硬编码科学数字和“development pin”分支。让 `scripts/generate_paper.py` 只读取一次全量、干净运行生成的权威表，并由同一 manifest 中的哈希绑定所有正文数字和 PNG。`scripts/build_paper_tables.py` 不应继续生成名为 `frozen_*` 的旧值。`scripts/verify_paper.py` 对任意论文数字、图内数字和权威表漂移均必须非零退出，不能因 `post_fix_development_numbers` 而降级。重新生成 Figure 3、Figure 4、Figure S1、所有主表、摘要和结论。
- **验收标准**　一次从干净环境和固定 commit 完成的全流程产生唯一 manifest。论文、HTML、CSV 和每张引用 PNG 中的 Baseline、MLP、RF、k-correction、Sparse-Π 数字逐项一致。自动测试从 PNG 生成输入或图旁 sidecar 元数据核验图内统计。对 `paper.md` 运行 claim guard 时零 warning、零 error。最重要的是，MLP 是否优于 Baseline 的布尔判断在所有产物中唯一且一致。

### R3-M2　论文称在 NHDPlus HR 有向拓扑上执行主输运，但实现是在 13 个逻辑节点上路由

- **Blocking**　Yes
- **轴**　方法与实现一致性，水文合理性，图表准确性
- **论文 claim pointer**　正文称八个逻辑河段只是交叉验证组与报告单元，而“underlying transport is routed on the directed NHDPlus HR topology”，主干分为六段、七条支流在映射汇流点混合（`paper.md:41-43`）。图 2 又被用来支持逻辑河段与 NHD 网络映射（`paper.md:45-47`）。
- **代码或图表精确证据**　`src/real_network.py:314-331` 明确新建七个 tributary 节点和六个 mainstem 节点，之后 `src/real_network.py:359-378` 以这些逻辑节点构造 `topo` 并路由。冻结产物 `data_proc/network_segments.csv:2-14` 只有 13 个节点。真正的 536-cell NHDPlus DAG 只在滤波脚本中出现，而不是主交叉验证输运求解。Table 1 的 NHD segments 列为 R002、R003、R005、R007 各 0，R004 为 23，R008 为 46（`paper.md:244-255`），但当前 Figure 2 图例分别显示 R002 15、R003 29、R004 140、R005 6、R007 2、R008 193，图表口径明显不同。`src/real_network.py:246-265` 只是用 NHD 路径定位首次主干汇流点，`src/real_network.py:286-331` 随后把网络压缩为逻辑树。
- **影响**　空间支持、汇流拓扑、控制体尺度和“真实 NHD 拓扑输运”的原创性表述均被高估。读者无法判断主结果属于高分辨率河网模型，还是由 NHD 辅助定位的简化 13 节点模型。
- **具体修改方案**　作者需二选一。若贡献是高分辨率 NHD 路由，应改造 `route_steady_state`，直接读取 `network_topology.py` 的 flowline DAG，在每个 NHD 控制体推进质量并把样本投影回评价点。若保留当前 13 节点模型，应在题目、摘要、方法、图 2 和讨论中明确它是 NHD 辅助构建的逻辑河段树，并删去“underlying transport is routed on directed NHDPlus HR topology”。Table 1 的 NHD segment 数必须由 Figure 2 的同一 assignment manifest 自动生成。
- **验收标准**　主输运网络节点数、边数、汇流关系和样本映射由一个机器可读 manifest 唯一确定。方法文字、Table 1、Figure 2 图例、`network_segments.csv` 和求解器实际迭代节点逐项一致。测试需验证每条边的质量守恒以及样本从 NHD flowline 到求解控制体的唯一映射。

### R3-M3　Residual-AI 的训练目标不是折内重建，河段留出不能保证目标侧独立

- **Blocking**　Yes
- **轴**　实验设计，统计严谨性，可复现性
- **论文 claim pointer**　稿件称每折在训练河段拟合闭合，并以与被预测样本完全独立的上游边界重新求解完整网络（`paper.md:109-113`），摘要也称无 observed-concentration fallback（`paper.md:18`）。
- **代码或图表精确证据**　`src/12_nested_cv_transport.py:296-320` 直接从合并后的全数据 `obs["S_sgs_residual_mol_m2d"]` 取 `y_sgs`，每折仅按行索引选择训练目标，并未移除留出河段后重新诊断。该列来自 `src/05_compute_residual_sgs.py:46-51` 的一次全数据 `diagnose_sgs`。而 `src/real_network.py:477-550` 的诊断沿河使用观测浓度，上一样本的观测值成为下一样本的 `C_in`，支流观测出口也可通过汇流进入同日主干训练样本的目标。代码作者已经对 k-correction 认识到这一风险，并在 `src/12_nested_cv_transport.py:198-241,321-345` 中专门移除 held-out samples 后按折重建 `k_needed`，但 Residual-AI 没有对应处理。
- **影响**　留出河段的观测浓度可能通过同日下游训练样本的 (C_{in}) 进入训练目标。即使最终前向求解不用观测浓度，模型拟合阶段也不是完全独立。当前 MLP 结果恰好在不同产物代际间从劣于基线变成优于基线，因此这一泄漏必须在解释任何泛化结论前关闭。
- **具体修改方案**　在 `grouped_holdout` 中为 Residual-AI 添加与 `_fold_k_targets` 同构的 `_fold_sgs_targets`。每折从 `obs_seg` 删除 held-out 样本，重新执行诊断，只使用仍具有合法上游状态的训练样本。更严格的方案是把目标定义和所有由观测派生的特征都放进 sklearn 风格的 fold pipeline。记录每折可用目标数、缺失原因和受 held-out 支流影响的下游节点。
- **验收标准**　新增反事实泄漏测试。任意改变 held-out 河段的 `C_aq_obs`，训练折的目标、拟合参数和其他河段预测必须完全不变。每折训练目标哈希只依赖训练索引。重新计算后报告逐折 RMSE、按河段宏平均 RMSE及样本加权总体 RMSE，并保留完整 out-of-fold 行键唯一性检查。

### R3-M4　滤波尺度结论同时违背当前结果文件、图像和生成器自身的解释边界

- **Blocking**　Yes
- **轴**　机制证据，图表一致性，主张节制，气候生态与水文证据门控
- **论文 claim pointer**　摘要和讨论称 |S_sgs| 从约 591 m 到 73,109 m 保持 3.72 到 3.93，因而“indicates that the residual is dominated by a genuine unresolved process rather than by resolution truncation”（`paper.md:18, 173-179, 217-221`）。Table 6 重复 591、1100、1924、73109 m 和 3.720、3.667、3.864、3.932（`paper.md:296-303`）。
- **代码或图表精确证据**　当前 `results/tables/filter_scale_metrics.csv:2-5` 给出 587、1033、1831、40153 m，unique-cell mean |S_sgs| 为 3.988、3.960、4.204、4.195，方差为 21.834、19.057、20.886、21.524。当前 `results/figures/filter_scale_sgs.png` 视觉上也是约 4.0 到 4.2 和最粗约 40 km，不是正文数值。更关键的是，同一结果的同步诊断覆盖率只有 0.0080、0.0133、0.0219、0.1857（`results/tables/filter_scale_metrics.csv:2-5`）。`src/13_filter_scale_sgs.py:651-655,680-720` 把分析明确标为 `sampling_conditional_sensitivity`，并写明“not evidence of a genuine unresolved process or watershed scaling law”，且把 `genuine unresolved process` 放入 `do_not_claim`。
- **影响**　不同尺度比较的空间支持和同步覆盖并不等价，接近的均值不能区分真实未解析过程、观测稀疏性、边界条件和算子选择。当前文字把条件敏感性提升为机制判断，并使用了过时数字。
- **具体修改方案**　先统一结果代际。随后把滤波结论降为“在当前稀疏、采样条件化算子下，均值对所测试尺度不敏感”。若要保留“genuine unresolved process”，需要在同一组同步覆盖的嵌套控制体上比较尺度，并通过 bootstrap 或层级模型传播日期和空间支持不平衡，另做观测误差与边界条件敏感性。`metrics_from_cell_records` 应输出固定-support 子集指标及其不确定区间，生成器应拒绝在覆盖率阈值以下生成机制性文字。
- **验收标准**　Table 6、Figure 6、Figure S3、摘要与讨论使用同一 CSV。每个尺度报告 unique cells、date-cell records、同步覆盖率和不确定区间。固定-support 分析或明确降调后的文字通过 claim guard，且不再出现结果 summary 的 `do_not_claim` 词组。

### R3-M5　通量列并非研究区总量，却被正文作为 area-weighted study-area flux 解释

- **Blocking**　Yes
- **轴**　数据定义，图表准确性，科学重要性
- **论文 claim pointer**　方法称通量总量是把 (F_{CO2}) 乘 (A_s) 后“summed over the study area”（`paper.md:64-68,116-118`），结果据此比较 4.29×10³、5.99×10²、2.43×10⁸ 和 1.79×10⁸ mol d⁻¹（`paper.md:146,164-170,257-275`）。
- **代码或图表精确证据**　`src/12_nested_cv_transport.py:101-107` 明确写这些列是 sample-level 或 overlapping-area diagnostics，绝非 study-area spatial totals。实现 `src/12_nested_cv_transport.py:123-170` 对所有样本的控制面积求和，会跨日期并在同一河段重复空间；另算的 `flux_date_mean_unique_cell_mol_d` 才试图按日期去重。当前 loo-reach 表 `results/tables/nested_cv_metrics.csv:3,5-7` 的重叠面积值为 Baseline 1213.85、k-correction 1254.56、MLP 1.94×10⁶、RF 6.59×10⁵，而论文仍展示旧代际 4290.7、598.8、2.43×10⁸、1.79×10⁸。`scripts/build_paper_tables.py:65-80` 虽保留了警告说明，却仍把重叠诊断写进名为 `flux_area_sum_mol_d` 的列，容易再次误用。
- **影响**　单位虽是 mol d⁻¹，但估计量并不代表一个不重叠空间域在一天内的排放。把它称为研究区总量会造成数量级和物理意义误读。旧值与当前值又相差 2 到 3 个数量级。
- **具体修改方案**　重命名所有列和图注为 `overlapping_sample_support_diagnostic`，从主结果表删除 “F total”。若确需研究区每日通量，必须构建互斥河段面积、每日期唯一状态和清楚的时间聚合，再报告日期分布而非跨日期相加。主文可保留样本级 (F_{CO2}) 误差和无量纲/面积归一化诊断，但不得称 watershed 或 study-area total。
- **验收标准**　全仓搜索不再出现把该量称为 total、budget 或 summed over study area 的表述。一个合成两日期同控制体测试应证明日期复制不会使“每日空间总量”翻倍。正文通量数字与权威结果表一致，并在表头直接写明估计量和重叠规则。

### R3-M6　“model-free profile likelihood”并非统计似然，且使用观测条件化上游状态，不能独立验证 grouped transport 结论

- **Blocking**　Yes
- **轴**　原创性，统计严谨性，因果与相关区分，主张节制
- **论文 claim pointer**　标题、摘要和结论把模型自由目标面与 profile likelihood 作为 practical equifinality 的确认性证据，并称 concentration data alone cannot identify discrepancy allocation（`paper.md:1,18,121-129,193-195,208-212,231-235`）。
- **代码或图表精确证据**　`src/16_equifinality_surface.py:55-76` 从全数据 `sgs_training_data.csv` 读取由观测路由得到的 `C_in_obs` 和 `S_diag`，再由同一诊断平衡反推 (q_A)。单样本零谷因此是一个方程、两个自由参数的代数恒等式，不是独立数据检验。池化分析在 `src/16_equifinality_surface.py:93-113` 强制所有 120 行共享单一 (\alpha) 和单一 (S)，并在固定网格上最小化未加权平方误差，没有观测误差模型、似然、置信区间或自由度处理，却在图和正文中称“profile likelihood”。它也没有使用 grouped forward routing，而使用观测条件化的 `C_in_obs`，所以其 RMSE 0.0409 到 0.0465 不可与 0.0485 的 grouped transport RMSE直接对应。Figure 5(c) 还以阶梯状 `arg min S` 展示粗网格最小值，视觉上可能把离散化结构误认为参数信息。
- **影响**　中心结论包含两个不同层次。单样本不可辨识是模型结构的代数性质，池化浅谷则高度依赖共同 (S)、共同比例、误差权重和观测条件化边界。把后者称为 profile likelihood 并称“confirm”会高估统计证据与原创性。
- **具体修改方案**　把单样本部分表述为解析等价线。池化部分改称 profiled sum-of-squares sensitivity，或显式规定误差分布后构造真正的 likelihood。用连续优化而非粗 (S) 网格，报告曲率、置信区间或 bootstrap，并对 (C_{in})、(k_{emp})、几何误差和河段层级相关性做敏感性。最关键的是，增加与 grouped forward transport 同边界条件的折外 profile，或明确该分析仅为观测条件化的局部结构诊断。
- **验收标准**　术语与实际目标函数一致。解析零谷和池化实证证据在文中分开。结论明确适用的参数共享假设。连续优化复现网格结果，并给出不确定区间。任何与 grouped CV 的比较均在相同上游边界、相同样本权重和相同误差定义下完成。

## 小问题

### R3-m1　Table 8 的“Original-variable form”仍使用 `_z`

- **轴**　图表与写作清晰度
- **受影响元素**　`paper.md:313-320`
- **证据**　表中写 `S_sgs* ≈ 3.141 − 8.686·Fr_z − 6.505·Slope_z`，但 `_z` 在 `paper.md:184-188` 被定义为标准化预测量。`src/15_dimensionless_sparse.py:276-282` 实际同时生成 standardized 与 original 两套系数。
- **要求修正**　原变量式必须使用未标准化变量名和清楚单位，或把该行改名为另一种标准化响应表达。自动核对表中变量名与系数来源列。

### R3-m2　已知不是无量纲的 Da 仍进入候选库

- **轴**　方法可靠性
- **受影响元素**　`paper.md:132-134`，`src/05_compute_residual_sgs.py:27-40`
- **证据**　稿件承认 (\tau) 用秒而 (k) 用 m d⁻¹，所以候选 Da 不是无量纲，却仅因最终被 LASSO 删除而认为不影响结果。
- **要求修正**　在特征生成前统一时间单位并重跑全部稀疏模型。不能用“系数被压到零”替代输入正确性，因为标准化、正则化路径和特征相关性仍可能受影响。

### R3-m3　Table 4 只有一句说明而没有表

- **轴**　可读性
- **受影响元素**　`paper.md:276-277`
- **证据**　“Table 4”没有列或数据，只是一句不报告样本内指标的声明。
- **要求修正**　删除该编号并顺延表号，或把必要的协议对照整理为真实表格。

### R3-m4　“nested”命名与方法声明冲突

- **轴**　术语一致性
- **受影响元素**　`README.md` 多处，`src/12_nested_cv_transport.py` 文件名，`nested_cv_*` 产物名，Figure 3/4 文件名，以及 `paper.md:111`
- **证据**　代码注释 `src/12_nested_cv_transport.py:15-17` 和正文均明确没有 inner loop，因此不是 nested CV。README 仍称“嵌套 CV”。
- **要求修正**　统一改为 grouped leave-one-reach-out CV。若保留旧文件名以兼容，应在 manifest 中标注 legacy filename，正文和 README 不再使用 nested。

### R3-m5　超参数固定但缺乏选择依据和不确定性报告

- **轴**　统计严谨性
- **受影响元素**　`paper.md:102-104,111-113`
- **证据**　MLP、RF、XGBoost 和 LASSO 的超参数直接固定，且没有内层选择或预注册理由。八个组中三个仅 n=1，单个总体 RMSE不足以表征稳定性。
- **要求修正**　说明超参数来源。至少报告八折逐折误差、宏平均和 bootstrap 区间。若调参，则必须在训练折内完成。

### R3-m6　Figure 2 和 Table 1 的“segment”含义未定义一致

- **轴**　视觉准确性
- **受影响元素**　`paper.md:41-47,244-255` 和 `results/figures/figure2_reach_assignment_and_samples.png`
- **证据**　图例中的 segs 数与 Table 1 的 NHD segments 数不同，且 Figure 2(a) 未显示 R001，但表中 R001 长度 12.6 km、0 segments。
- **要求修正**　分别定义 raw NHD flowline、assigned corridor flowline、logical transport segment 和 sampled control volume。不同对象不得共用 “segment”。

### R3-m7　发布信息尚未冻结

- **轴**　可复现性
- **受影响元素**　`paper.md:238-240`
- **证据**　Data availability 仍写 “a version-specific release or immutable commit should be cited”。manifest 记录 dirty working tree 和 smoke 命令，而非一次完整运行。
- **要求修正**　提交前建立带 DOI 或 tag 的只读 release，记录原始数据校验和、完整命令、Python 与依赖锁、随机种子、所有产物哈希及许可证。

### R3-m8　Figure 5 的视觉编码需要降低误导风险

- **轴**　图的视觉准确性
- **受影响元素**　`results/figures/equifinality_objective_surface.png`，`paper.md:159,195`
- **证据**　panel (a) 的 “exact-match line” 与截断后的 log objective 颜色极值重合，panel (c) 的橙色阶梯来自离散 (S) 网格，且纵轴画的是 objective 而正文主要讨论 RMSE。
- **要求修正**　用解析线与连续 profile，panel (c) 直接画 RMSE 及其变化幅度，并在图注写出网格或优化精度。不要把色标截断导致的视觉平台解释成证据强度。

### R3-m9　参考文献中存在未完成条目

- **轴**　可读性与原创性定位
- **受影响元素**　`paper.md:31,332`
- **证据**　Gao et al. 标为 manuscript in preparation，DOI to be added，无法供读者核验，也承担了“related work”定位功能。
- **要求修正**　若尚不可公开，避免依赖其建立新颖性。补充可核验的公开先行工作比较，并把未公开稿件仅作非关键背景或删除。

## 五轴评价

- **原创性**　将残差闭合、河段留出和前向输运耦合为一个评价框架，方向有一定新意。但单样本 (k\)-(S) 零谷是一个方程两个未知量的代数结果，当前高分辨率 NHD 路由表述又与实现不符。原创性尚需在准确的方法边界内重新定位。
- **科学重要性**　“浓度拟合不能替代过程约束”对河流碳预算和环境模型评价重要。当前只有 East River 十日样本、无独立通量观测、结果代际冲突，尚不足以支撑广泛结论。
- **跨学科读者**　河流碳、水文建模、生态模型和科学机器学习读者会感兴趣。要达到更广读者层面，需要更清楚地区分结构恒等式、局部案例结果和可推广规律。
- **技术可靠性**　目前不合格。中心数值矛盾、主网络叙述与求解器不一致、Residual-AI 折内目标构造不独立、滤波机制性解释越界、通量估计量误标。
- **非专业读者可读性**　Plain Language Summary 较清楚，负结果叙事也易懂。但多个“不能识别”“genuine process”“study-area total”表述比证据更强，图表代际冲突会使任何读者无法形成稳定理解。

## 技术问题清单与建议立场

在作者的中心论证成立前必须解决 R3-M1 至 R3-M6。其中 R3-M1、R3-M3 和 R3-M4 会直接反转或削弱中心结论，R3-M2 决定方法到底是什么，R3-M5 决定通量数字是否具有物理含义，R3-M6 决定标题中的 equifinality 证据属于解析结构还是统计支持。

**建议立场**　重大修改后重审。该立场不是期刊最终决定，而是基于当前冻结材料包的技术判断。若作者只能完成文字降调而不能统一全量运行、关闭折内泄漏并建立单一权威产物链，则中心结论仍不可接受。

## 复现与核验记录

1. `python scripts/verify_paper.py`，只读执行，退出码 0，10 warnings。关键警告包括 MLP `table=0.0368` 与 guard `0.0602`，RF `table=0.105` 与 guard `0.075`，以及正文和 HTML 中四类禁用表述仍存在。
2. `python -m pytest -q -p no:cacheprovider`，只读收集，退出码 1。默认 Python 3.14 缺少 `geopandas`，测试未开始。
3. `py -3.12 -m pytest -q -p no:cacheprovider`，退出码 1。Python 3.12 环境缺少 `pytest`，测试未开始。
4. 逐图只读查看当前论文引用 PNG。确认 Figure 3 显示 0.0368 和 0.1050，Figure 4 显示旧 MLP 0.0602，Figure 6 约为 4.0 到 4.2 且最粗尺度约 40 km，Figure 2 图例 segment 数与 Table 1 不同。
5. 未运行任何写输出的 pipeline、训练或绘图命令，也未修改冻结材料包。

## 风险与未支持主张

- “Residual-AI learners do not beat Baseline” 在当前权威性不明的产物集合中既被支持也被反驳。
- “underlying transport is routed on directed NHDPlus HR topology” 与主求解器的 13 节点逻辑树不一致。
- “genuine unresolved process rather than resolution truncation” 被结果生成器自身明确列为不可主张。
- “study-area total flux” 不由当前重叠样本面积估计量支持。
- “profile likelihood confirms” 不由未指定误差模型的网格平方误差支持。
- 跨流域普适性、真实逸散通量正确性以及 (S_{sgs}) 的生物地球化学归因，均不能从提供材料评估。
