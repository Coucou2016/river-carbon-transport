# Reviewer 1

## 审查设置

- **输入范围** 仅审查 `tmp/review_20260927/packet` 中的 `paper.md`、`paper.html`、`report.pdf`、代码、配置、测试、`data_proc` 和 `results`。未读取其他 reviewer 报告、旧审稿文档或 `docs/ACTIVE_FIX_STATUS*`。
- **评估边界** 未运行会覆盖生产结果的流水线。允许读取项目根目录的现有虚拟环境与原始数据，但本轮没有修改生产文件。技术判断基于当前快照及其中可复核的代码和结果表。
- **稿件核心主张** 稿件以 120 个 East River 样本和八个逻辑河段为基础，比较零残差、机器学习残差和气体交换修正三类闭合，并据浓度持出误差及目标函数剖面主张浓度观测不能唯一约束 (S_{sgs}) 与 (k) 的过程分配。
- **可见证据** 准稳态质量平衡、逻辑河网路由、分组留一河段评估、滤波实验、稀疏闭合、目标函数剖面、处理后数据、结果表和单元测试。
- **影响信心的缺失材料** 当前包没有一个能够证明 `paper.md`、`paper.html`、`report.pdf`、论文图和结果表来自同一次不可变运行的发布清单。原始数据可公开获得本身不是科研诚信问题，但版本混杂使当前提交物不能被当作单一可审查结果集。

## 总体评估

研究问题具有方法学价值。稿件也做出了若干审慎处理，包括把通量明确限定为样本支持诊断量、承认三个单样本河段证据权重低、删除自观测上游边界、在主要 Residual-AI 和 (k)-correction 评估中重建折内目标，并将单样本等效谷表述为代数事实而非似然分析。

但当前快照尚不能建立技术上可审计的核心案例。最主要原因是交付物混入彼此冲突的结果代次，且经验输运计算所依赖的空间支持在关键河段 R002 上违反其自身 NHD 长度记录。前者使读者无法确定哪组数字是作者结论的真实依据，后者直接影响 (A_s=L W)、(q_A)、(S_{sgs})、(k_{need})、模型通量和 held-out 浓度。另有稀疏闭合的折间隔离不符合稿件方法描述，以及只有八个高度不平衡河段却没有组层面的不确定性评估。建议先完成一次范围很小但严格的结果冻结和空间支持修复，再判断论文的经验结论。

## 谁会对结果感兴趣，以及原因

河流碳循环、环境模型评价、水文水质模拟和物理约束机器学习研究者会关心这项工作，因为它直接讨论了浓度拟合与过程可识别性之间的差异。更广泛的地球系统建模读者也可能关注“预测技巧不能自动识别过程分配”这一信息。不过当前广泛意义主要来自一般性的欠定性，而不是已经被稳健验证的 East River 特异发现。稿件需要更清楚地区分这两层贡献。

## 主要优点

1. 质量平衡的日与秒单位转换在核心输运求解器中是显式的。`src/transport.py` 第 49 至 95 行将 (Q C) 保持为 mol s⁻¹，并用 86400 将面通量换算到秒基准。
2. 主要 Residual-AI 和 (k)-correction 代码确实尝试在每一折删除 held-out 浓度后重建训练目标。证据见 `src/12_nested_cv_transport.py` 第 209 至 311 行。
3. 稿件没有把重叠样本面积通量冒充流域总量，也没有把缺少独立通量观测解释为数据欺诈。`paper.md` 第 64 至 68 行和第 116 至 118 行给出了正确边界。
4. 滤波结果对未解决的 whole-reach 收缩环采取了排除而非强行补齐。`paper.md` 第 83 至 91 行及 `results/tables/filter_scale_summary.json` 中的 `excluded_scales` 支持这一点。
5. 结论已经明确限制在 East River，且承认未进行跨流域迁移。`paper.md` 第 231 至 240 行。

## Major Concerns

### R1-M1 [reproducibility]

**Severity** Major  
**Blocking** Yes  
**Claim pointer** 当前论文的主要数值结论是 Baseline RMSE 0.0486、MLP 0.0372、RF 0.1011、(k)-correction 0.0486，并据此解释闭合方案的 held-out 表现和过程分配。  
**Evidence pointer** `paper.md` 第 8 至 18、140 至 168、184 至 195、257 至 325 行；`paper.html` 第 111、197、198、210、244、251、262、269、293、308、317、339 行；`results/tables/nested_cv_summary.json`；`results/tables/identifiability_summary.json` 第 10 至 20 行；`results/tables/dimensionless_sparse_summary.json` 第 11 至 22 行；`results/tables/k_correction_saturation.json` 第 8 至 13 行；`results/figures/paper/nested_cv_rmse_bar.png`；`results/figures/paper/nested_cv_scatter_holdout.png`；`report.pdf` 第 1 至 3 页。  
**Concern** 当前审查包不是一个数值一致的论文快照。示例包括以下冲突。

- `report.pdf` 第 2 页报告 Baseline 0.0284、MLP 0.0573、RF 0.0745、(k)-correction 0.0244，而当前结果表为 0.0486、0.0372、0.1011、0.0486。
- `results/figures/paper/nested_cv_rmse_bar.png` 仍显示 0.0284、0.0244、0.0573、0.0745，根目录同名图则显示当前数值。
- `paper.md` 第 157 行称 (k_{eff}/k_{emp}=3.9\times10^{-5}) 且 18.8% 预测触及下界，但当前 `identifiability_summary.json` 给出 0.53999，`k_correction_saturation.json` 给出 0% 触及下界。
- `paper.md` 第 166 行称 (k)-correction 通量为 (5.99\times10^2) mol d⁻¹，表 2 和结果表为约 (1.26\times10^3) mol d⁻¹。
- `paper.md` 第 184 至 190 行给出两项稀疏式和 (R^2=-1.55)，表 8、HTML 和当前 JSON 给出含 `log10(Da)` 的三项式和 (R^2=-0.448)。同一节正文称 RMSE 0.0588，表 9 与 JSON 为 0.0529。
- `paper.md` 第 142 至 144 行的 MAE、bias 和分组 RMSE与表 3、表 5及 `subgroup_metrics.csv` 不一致。图 3 图注又写“没有闭合优于 Baseline”，与同页 MLP 0.0372 小于 0.0486 相冲突。
- `identifiability_summary.json` 第 20 行文字称 Residual-AI 不优于 Baseline，但同文件第 11 至 13 行显示 0.0372 小于 0.0486。

**Why it matters** 这些差异跨越摘要、正文、表格、图、HTML 和 PDF，并改变“哪一种闭合改善浓度”“(k)-修正是否饱和”“稀疏式包含哪些项”等科学解释。读者无法确定哪一代计算支撑标题和结论，因此当前核心案例不可审计。  
**Minimal repair** 指定 `results/tables` 中一组结果为唯一权威源，从该源一次性重建 `paper.md`、`paper.html`、全部论文图和 `report.pdf`。删除或隔离旧版 `results/figures/paper` 产物。无需增加新研究问题。  
**Resolution test** 增加一个只读一致性测试，逐项断言摘要、正文、表 2 至表 9、所有图内数值、HTML 和 PDF 文本中的 headline metrics 与 canonical JSON/CSV 完全一致。测试还应断言 MLP 的“beats baseline”文句与布尔结果一致、(k) 饱和比例等于 `frac_at_floor_oof`、稀疏方程和 (R^2) 仅来自 `dimensionless_sparse_summary.json`。发布包应附不可变 manifest，记录源表、图、HTML 和 PDF 的哈希及生成时间。

### R1-M2 [experimental-design]

**Severity** Major  
**Blocking** Yes  
**Claim pointer** 稿件声称在 NHDPlus HR 导向网络上进行 transport-coupled held-out 评价，并把 R002 的三个位点视为多样本支流证据的一部分。  
**Evidence pointer** `paper.md` 第 33、41 至 45、52 至 68、109 至 118、140 至 168 行及表 1；`src/real_network.py` 第 86 至 108、456 至 558、686 至 776 行；`results/tables/length_conservation.csv` 第 2 至 17 行，尤其第 7 行；`data_proc/reach_daily_observations_segmented.csv` 中 R002 的三行。  
**Concern** 经验输运的空间支持没有被固定到已验证的河道域。代码在每个日期和 segment 上使用未约束的样点中点间距，并在单样本情形固定为 100 m。`control_lengths_from_chainage` 的文档本身称其为 legacy unbounded sample-support diagnostic。R002 在 2019-08-05 的三个控制体长度总和为 837.76 m，而同一结果表记录的 NHD reach length 仅 170.22 m，比值为 4.92。稿件同时在表 1 中列出 R001、R002、R003、R005 和 R007 的 NHD segments 为 0，却在核心 transport-coupled 比较中把这些逻辑河段与主干一起路由。R002 又是当前数据中最极端的组之一，`per_reach_cv_metrics.csv` 显示 Baseline RMSE 0.2577、MLP 0.1725，因此几何支持问题不是无关紧要的制图细节。  
**Why it matters** (A_s=L W) 同时进入 (q_A)、残差诊断、(k_{need})、前向浓度和通量。一个超出记录河段域约五倍的支持长度会系统改变所有这些量。若若干支流没有已验证的 NHD 路径，稿件就不能把对应结果描述为在 NHDPlus HR 导向网络上的物理输运验证。该问题阻断当前经验 transport-coupled 证据，但不否定单方程两未知量的代数欠定性。  
**Minimal repair** 使用现有 NHD 和样点投影，给每个 reach-date 固定一个有界路径域，并用代码中已经存在的 `bounded_midpoint_lengths` 分配非重叠控制体。对于无法建立验证路径的逻辑河段，最小方案是从物理输运性能主张中移除，并将其保留为示意或敏感性分析。无需新增野外观测。  
**Resolution test** 每个参与物理输运主结果的 reach-date 必须满足控制体长度均为正、总长度等于预先声明的固定路径域，并且不超过验证的 NHD 路径长度。所有主结果河段必须至少映射到一条已验证且无环的有向 NHD 路径。修复后重新生成 held-out 预测，并报告 headline RMSE、R002 敏感性和 (S_{sgs})-(k) 剖面是否保持结论。测试应在 R002 当前 4.92 倍超界时失败。

### R1-M3 [experimental-design]

**Severity** Major  
**Blocking** No  
**Claim pointer** 稿件称稀疏无量纲闭合在每个留一河段折内进行训练折插补、标准化和 LASSO 拟合，并按同一 transport-coupled 协议评分。  
**Evidence pointer** `paper.md` 第 132 至 134、182 至 190 行；`src/15_dimensionless_sparse.py` 第 185 至 219、232 至 255、305 至 330 行；`src/12_nested_cv_transport.py` 第 209 至 311 行。  
**Concern** 稀疏闭合没有执行稿件所描述的完整折内隔离。`src/15_dimensionless_sparse.py` 第 232 至 251 行读取了由全数据诊断产生的 `S_sgs_residual_mol_m2d`，第 253 至 254 行在划分前用全数据中位数完成插补，第 328 行把这些全数据目标直接传入留一河段函数。第 198 至 203 行只在模型拟合层面划分训练和 held-out 行，没有像主要 Residual-AI 代码那样删除 held-out 浓度并重新路由生成训练目标。因而训练折中上游样本的残差可能经过 full-data `C_in` 依赖 held-out 河段浓度，且预处理也观察了 held-out 分布。  
**Why it matters** 稀疏闭合虽然不是主结论，但其 (R^2)、系数和 transport RMSE 被用于支持“紧凑但不预测”的结果。当前数值不能被描述为与主要闭合相同的严格折内协议。  
**Minimal repair** 复用 `src/12_nested_cv_transport.py` 的 `_fold_sgs_targets` 逻辑，在每一折删除 held-out 标签后重建稀疏目标。保留缺失值到折内，再以训练折中位数插补。  
**Resolution test** 在测试中扰动 held-out 河段的 `C_aq_obs_mol_m3`，断言该折的训练目标、插补中位数、标准化参数和拟合系数完全不变。再断言每个样本仅出现一次 OOF 预测，并将修复后的系数、(R^2) 和 RMSE同步到全部文稿产物。

### R1-M4 [statistical-rigor]

**Severity** Major  
**Blocking** No  
**Claim pointer** Key Points、摘要和结果将 MLP 0.0372 对 Baseline 0.0486 描述为 held-out 浓度误差改善。  
**Evidence pointer** `paper.md` 第 8 至 18、41、111 至 118、140 至 152、201 至 205、231 至 235 行；`results/tables/per_reach_cv_metrics.csv`；`results/tables/subgroup_metrics.csv`。  
**Concern** 比较只有八个非均衡河段，其中三个河段各一个样本，R008 有 58 个样本。稿件报告样本加权 pooled point RMSE，却没有河段层面的配对效应、不确定区间或对单个组影响的量化。现有 per-reach 表显示 MLP 并非一致改善，R001、R004 和 R007 变差，改善幅度在河段间高度不均。固定超参数避免了内层调参泄漏，但不能替代对组层面采样变异的描述。  
**Why it matters** 当前数字支持“在这 120 行 OOF 预测上的点估计更低”，但不足以支持稳定的跨河段性能改善。稿件虽已拒绝“settled success”，Key Points 和摘要仍容易被读成一般化改进。  
**Minimal repair** 使用现有 OOF 预测增加每河段的配对误差差异，并给出等权河段汇总及以河段为重采样单元的区间或完整八河段差异表。若八组不足以给出稳定区间，则把表述收窄为描述性点差异。  
**Resolution test** 发布表应同时显示样本加权 pooled RMSE、等权河段结果、八个配对河段差异和明确的组级不确定性说明。摘要和 Key Points 只可使用与该组级证据相匹配的措辞。

### R1-M5 [claim-moderation]

**Severity** Major  
**Blocking** No  
**Claim pointer** 标题和核心结论将单样本零谷及 pooled shallow profile 作为 practical equifinality 的主要证据，并提出对环境模型评价具有一般意义。  
**Evidence pointer** `paper.md` 第 1、10、18、25 至 33、121 至 129、193 至 235 行；`results/tables/equifinality_summary.json`。  
**Concern** 单样本零谷是固定 (C_{in}) 下一个质量平衡方程包含 (k) 和 (S) 两个未知量的代数结果。它证明单点联合识别不可能，但本身不是 East River 数据提供的经验发现。pooled profile 才是数据相关证据，但它又强制所有样本共享单一 (k)-scale 和单一 source，并依赖 R1-M2 中尚未固定的 (q_A) 和面积支持。稿件尚未充分区分“结构上必然的单方程欠定”与“在该数据和该共享参数化下观测信息不足”的两层结论，也没有从提供的材料中清楚证明该诊断相对既有等效性或可识别性分析的原创增量。  
**Why it matters** 这影响原创性、科学重要性和跨学科读者对贡献层级的判断。代数事实可以很好地作为解释框架，但不应单独承担广泛经验结论。  
**Minimal repair** 明确把单样本零谷标为解析基准，把 pooled profile 标为依赖共享参数化和空间支持的 East River 敏感性。用现有参考文献和方法比较说明本工作新增的是何种 transport-coupled、group-held-out 或样本支持诊断，而不是泛称首次发现 equifinality。  
**Resolution test** 摘要、讨论和结论必须分别陈述解析结论与数据条件结论，并列出 pooled profile 对控制体修复、样本权重和共享参数假设的敏感性。若这些敏感性改变“shallow”的判断，应进一步收窄标题和结论。

### R1-M6 [reproducibility]

**Severity** Major  
**Blocking** No  
**Claim pointer** 数据可用性和代码包暗示读者可以按固定环境复现全部测试和主要结果。  
**Evidence pointer** `paper.md` 第 238 至 240 行；`requirements.txt` 第 1 至 23 行；`tests/test_cell_dag_filter.py`、`tests/test_network_p0_fixes.py`、`tests/test_remediation_20260919.py`；本轮只读测试记录。  
**Concern** `requirements.txt` 没有列出 pytest。项目现有 `.venv` 无法执行 `python -m pytest`，因为缺少 pytest。系统 Python 可运行 pytest，但完整收集因缺少 geopandas 而失败。仅 `tests/test_cell_dag_filter.py` 在系统环境下独立通过，结果为 11 passed 和 2 个 `nanmean` warning。因而当前声明环境不能直接执行随包测试，也没有一条经过验证的命令证明主结果可以从指定版本依赖重建。数据可用性段还明确说提交时仍需补充不可变 commit 或 release。  
**Why it matters** 结果版本已经发生严重分叉，缺失可执行测试环境和不可变版本会放大无法复核的问题。  
**Minimal repair** 增加测试依赖文件或将 pytest 固定进开发依赖，提供 CPython 3.10 至 3.12 中一个实际验证过的环境锁，并在提交时引用不可变 release。  
**Resolution test** 在全新环境中按文档安装后，`python -m pytest -p no:cacheprovider -q` 必须完整收集并通过。随后以只读或临时输出目录运行结果一致性检查，确认生成表、图、HTML 和 PDF 的哈希或 canonical 数值一致。

## Minor Comments

### R1-m1 [writing-clarity]

**Severity** Minor  
**Affected element** “nested CV” 和 grouped CV 的术语。  
**Evidence pointer** `paper.md` 第 109 至 113 行明确说明没有内层超参数循环；代码文件名 `src/12_nested_cv_transport.py`、结果文件 `nested_cv_*`、`identifiability_summary.json` 第 3 行仍写 nested CV。  
**Issue** 同一协议被两种术语命名，容易让读者误以为进行了内层模型选择。  
**Required correction** 在文稿和面向读者的产物中统一称 grouped leave-one-reach-out CV。历史文件名可以保留，但 JSON 的 protocol 字段和图题应使用准确术语。

### R1-m2 [mechanism-evidence]

**Severity** Minor  
**Affected element** 头水边界的 (C_{eq}) 定义。  
**Evidence pointer** `paper.md` 第 74、85、113 行；`src/real_network.py` 第 479 至 489、512 至 525、704 至 720 行。  
**Issue** 稿件强调 (C_{eq}) 随样本温度变化，但路由的头水边界使用全数据平均温度计算的单一 (C_{eq})，局部气体交换项才使用逐样本 (C_{eq})。  
**Required correction** 在方法中明确这一区别，并用现有数据报告按日期或局部温度设定头水 (C_{eq}) 的敏感性，或说明其影响可忽略。

### R1-m3 [data-resource-quality]

**Severity** Minor  
**Affected element** 网络来源和逻辑河段证据等级。  
**Evidence pointer** `paper.md` 第 41 至 47 行及表 1。  
**Issue** “mapped to an NHDPlus HR directed network”容易掩盖多个逻辑支流没有 NHD segment，以及主干分段是 y-threshold 简化树。稿件后文虽有限定，但摘要和 Plain Language Summary 没有同等清楚。  
**Required correction** 在摘要层面将其写为 NHDPlus HR corridor 加逻辑简化路由，并清楚区分实测、公开数据、经验几何和逻辑映射。公开数据不应被暗示为问题，问题仅在于空间支持和推断范围。

### R1-m4 [figures-and-tables]

**Severity** Minor  
**Affected element** 表 7 的 (k_{eff}/k_{emp}) 与表 8 的方程标签。  
**Evidence pointer** `paper.md` 第 304 至 319 行。  
**Issue** 表 7 当前把 (k)-correction 的比例写成 1.00，与 current result 0.53999 不符。表 8 的“Original-variable form”仍在变量名后保留 `_z`，不能被称为原变量形式。  
**Required correction** 从 canonical JSON 自动填表，并把标准化系数、反标准化系数和维度量响应方程分别命名。

### R1-m5 [writing-clarity]

**Severity** Minor  
**Affected element** 标题页和提交完整性。  
**Evidence pointer** `paper.md` 第 3 至 4、238 至 240 行。  
**Issue** 作者和单位仍为占位符，数据可用性也尚未给出版本特异 release。  
**Required correction** 提交前补全作者、单位、不可变代码版本和所需的数据引用。

### R1-m6 [figures-and-tables]

**Severity** Minor  
**Affected element** 滤波单元警告。  
**Evidence pointer** `tests/test_cell_dag_filter.py` 的只读执行结果；`src/cell_dag_filter.py` 第 200 至 201 行。  
**Issue** 一个守恒测试通过时仍产生两个 `Mean of empty slice` warning。警告不改变该测试结论，但会掩盖真正的数值异常。  
**Required correction** 在缺失 (k) 或 (C_{eq}) 的测试路径中显式处理空值，并将意外 runtime warning 设为测试失败。

## 在核心案例建立前必须解决的技术问题

必须先解决 R1-M1 和 R1-M2。R1-M1 要求冻结单一一致的结果版本。R1-M2 要求经验输运所用控制体和逻辑河网具有可验证的空间支持。R1-M3、R1-M4、R1-M5 和 R1-M6 会实质影响次级结果、推广力度和可复现性，也应在提交前处理。

## 对五项标准的评估

- **原创性** transport-coupled grouped evaluation 与显式过程分配诊断的组合具有潜在原创性，但单样本零谷本身是方程欠定的直接结果。当前稿件还没有充分界定其相对已有 equifinality 和 identifiability 工作的新增部分。
- **科学重要性** “浓度技巧不等于过程识别”具有重要意义。当前数据仅覆盖一个流域、十天和八个高度不平衡逻辑河段，且空间支持尚未闭合，因此尚不能从现有材料证明广泛的重要性。
- **跨学科读者兴趣** 碳循环、水文模型、机器学习闭合和环境模型评价读者均可能关注。若能把解析欠定与经验信息不足清楚分层，跨学科可读性会明显增强。
- **技术可靠性** 单位换算和主要折内目标重建有可取之处，但结果代次冲突与控制体域超界是阻断性问题。稀疏闭合还存在折间隔离缺口。
- **非专业读者可读性** Plain Language Summary 对核心问题解释较清楚，但同一包内互相矛盾的数字、图和术语使任何读者都难以判断最终结论。简化网络与样本支持通量的含义仍需要在摘要层面解释。

## Recommendation posture

当前证据尚不能建立完整案例。判断不涉及期刊最终决定，也不承诺任何 Nature 系列接收结果。若 R1-M1 和 R1-M2 以最小、可复核的方式解决，并据此校准 R1-M3 至 R1-M5 的结论范围，我会把该工作视为一个有价值但严格限于 East River 的方法学诊断研究。

## 不支持或不可评估的边界

- 不能从当前材料判断 closure 的通量分配哪一个更接近真实 evasion，因为没有独立气体交换或通量观测。
- 不能把重叠样本面积通量解释为流域总量。稿件对此限制是正确的。
- 不能从单一流域推断跨流域泛化或政策尺度效用。
- 不能把全数据稀疏系数解释为 held-out 物理定律。
- 不能在结果版本未冻结前判断当前 PDF、HTML 或 Markdown 哪一个代表最终论文。
- 不能把公开数据、空间映射误差或版本分叉本身解释为数据造假。这里提出的是可复现性和推断支持问题。

## 验证记录

- `tests/test_cell_dag_filter.py` 在系统 Python 下只读执行，11 项通过，出现 2 个 `nanmean` warning。
- 项目 `.venv` 缺少 pytest，无法启动测试套件。
- 系统 Python 的完整测试收集因缺少 geopandas 失败，未得到全套通过结果。
- 未运行任何会写入 `data_proc`、`results`、`paper.*` 或 `report.pdf` 的流水线。
- `report.pdf` 共 81 页。抽查封面和摘要页确认其生成日期为 2026-08-16，且摘要 headline metrics 与当前结果表不一致。
