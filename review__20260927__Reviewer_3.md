# Reviewer 3

## Review setup

- **Input scope** 仅审查冻结包 `tmp/review_20260927/packet` 中的 `paper.md`、`paper.html`、`report.pdf`、代码、配置、测试、`data_proc` 与 `results`。未读取任何其他 Reviewer 报告、旧审查文件、`docs/ACTIVE_FIX_STATUS*` 或综合意见。
- **Assessment boundary** 本报告是对当前快照的稿件前审，不是编辑决定。未运行会改写结果的流水线。公开数据本身不构成诚信问题。本轮也不把版本漂移误述为数据造假。
- **Shared manuscript claim summary** 稿件主张在 East River 的 120 个公开浓度观测上，通过折内目标构建、留一河段输运耦合评估和模型无关的 SSE 剖面，显示浓度误差不能唯一约束未解析源汇项 `S_sgs` 与气体交换速度 `k` 的过程分配。
- **Visible evidence base** 当前结果表、OOF 预测汇总、河网映射表、过滤尺度汇总、模型无关目标面代码、稿件生成器、现有 claim guard，以及 `report.pdf` 的 81 页只读渲染。
- **Missing materials affecting confidence** 冻结包未提供可据此重跑全部生产流水线的原始数据快照。当前 Python 环境未安装 `pytest`，因此三组现有测试未能实际执行。外部文献的优先权和期刊适配度没有在本轮独立检索核验。
- **Emphasis** 稿件逻辑与可读性、图表和格式一致性、方法完整性、结论边界。原创性、科学重要性、跨学科读者兴趣、技术可靠性和非专业读者可读性均纳入判断。

## Overall assessment

稿件提出的评价问题有价值。将闭合项重新放回输运方程后再评估、区分浓度技能与过程分配、明确通量只是重叠样点面积诊断，这些做法值得保留。当前快照却尚不能形成可审的单一科学叙事。正文、HTML、主图、表格、JSON 汇总和 PDF 报告代表了不同计算版本，多个关键数字、符号方向和结论方向互相冲突。河网逻辑树、NHD 映射网和过滤网之间的关系也没有以可复核的方式统一说明。即便先忽略这些同步问题，关于 MLP 改善和实际等效性的结论仍需更清楚地限定统计权重、固定上游边界和确定性 SSE 的适用范围。

## Who would be interested in the results, and why

河流碳循环、流域水文学、环境模型评价、物理约束机器学习和数据驱动闭合的研究者会关注这一工作。其潜在跨学科价值不在于某个 AI 模型取得最低 RMSE，而在于展示同一浓度拟合可以对应完全不同的源汇和气体交换分配，并据此要求过程级诊断。若要吸引更广泛读者，稿件必须先提供一个稳定、可追溯且不依赖项目内部术语的证据链。

## Major strengths

1. 稿件主动说明数据来自公开再分析，明确列出 10 天采样、河段样本不平衡、几何参数化、协变量缺失和缺少独立逸散观测等边界。相关证据见 `paper.md` 第 41 至 45 行和第 228 行。
2. 折内重新构建目标以及持出后再求解输运的设计，方向上优于先构建全数据标签再切分。实现见 `src/12_nested_cv_transport.py` 第 372 至 447 行，尤其是第 389 至 405 行的折内 `S_sgs` 目标。
3. 稿件没有把重叠样点面积通量误称为流域总通量，也没有把模型通量诊断冒充独立观测。见 `paper.md` 第 68 行、第 118 行和第 166 行。
4. 模型无关的单样本零谷是清楚的代数诊断，源代码也明确标注其为固定 `C_in` 下的 SSE 而非统计似然。见 `src/16_equifinality_surface.py` 第 6 至 14 行、第 79 至 110 行和第 308 至 316 行。
5. 正文多处主动压低不支持的推广表述，例如不把 MLP 的点 RMSE 改善视为已定论成功，也不声称结构可辨识性定理或普适 SGS 标度律。见 `paper.md` 第 203 至 212 行和第 219 至 228 行。

## Major Concerns

### R3-M1 [figures-and-tables]

**Severity** Major  
**Blocking** Yes  
**Claim pointer** 当前稿件声称所有主要结论来自同一冻结运行，并用一组一致的留一河段指标、通量诊断、等效性剖面和稀疏闭合结果支撑主结论。  
**Evidence pointer** `paper.md` 第 142、144、148、157、159、166、168、184 至 190、195、257 至 325 行；`paper.html` 第 111、197、198、210、224、244、251、262、265、293、338 至 342 行；`results/tables/paper_main_results.csv` 第 2 至 6 行；`results/tables/identifiability_summary.json` 第 4 至 20 行；`results/tables/equifinality_summary.json` 第 9 至 23 行；`results/tables/dimensionless_sparse_summary.json` 第 11 至 22 行；`scripts/generate_paper.py` 第 131 至 188、583 至 684、1008 至 1029、1361 至 1392 行。  
**Concern** 当前不存在唯一的数值事实源。正文第 142 行给出的 MLP 和 RF 的 MAE 与 Bias 分别是 0.0336、0.0357、0.0187 和 0.0119，而表 3 与主结果 CSV 是 0.0214、0.0512、-0.0055 和 0.0342。正文第 157 行称 `k_eff` 中位数为 0.0066、比值为 3.9×10^-5，表 7 与 JSON 则是 123.329 和 0.53999。正文第 166 行称 k 修正通量为 5.99×10^2，表 2 与 JSON 是 1.26×10^3。图 5 图注使用 0.0409 至 0.0465，正文和 `equifinality_summary.json` 使用 0.0360 至 0.0396。稀疏闭合正文和图注只保留 Fr 与 slope，并给出 R²=-1.55 和 C RMSE=0.0588，实际图与 JSON 保留 `log10(Da)`，给出 R²=-0.448 和 C RMSE=0.0529。方法第 134 行还说 Da 项被删除，与当前结果相反。Figure 3 图注称没有闭合优于 Baseline，但图和表明确显示 MLP 的点 RMSE 0.0372 低于 0.0486。HTML 专用摘要又使用 2.43×10^8、1.79×10^8、4.29×10^3 和 3.9×10^-5，与 Markdown 摘要及当前结果表不同。这些冲突直接改变模型优劣、过程分配和稀疏式的科学解释。  
**Why it matters** 读者无法知道哪些数字属于当前分析，也无法判断主结论是否由所示图表支持。该问题影响核心证据而非局部排版，因此在统一前稿件的中心案例不能成立。  
**Minimal repair** 以当前冻结结果表和 JSON 为唯一事实源，删除 `generate_paper.py` 中所有手写结果数字、方程、图注和 HTML 专用摘要。正文、HTML、图注、表格和报告必须由同一结构化对象渲染。只保留一套经过作者确认的结果，不需要新增研究。  
**Resolution test** 扩展 `scripts/verify_paper.py`。测试应逐字段读取 `paper_main_results.csv`、`subgroup_metrics.csv`、`identifiability_summary.json`、`equifinality_summary.json` 和 `dimensionless_sparse_summary.json`，再断言 Markdown、HTML、图中可见标注和 PDF 提取文本完全一致。任何关键数值、符号、模型排序或“优于 Baseline”方向不一致时必须非零退出。还应对生成器做静态检查，禁止在叙述区重复硬编码这些数值。

### R3-M2 [reproducibility]

**Severity** Major  
**Blocking** Yes  
**Claim pointer** 稿件把 120 个样点映射到 NHDPlus HR 有向网络，并在八个逻辑河段上执行输运耦合留一河段评估，同时用细 NHD 网进行过滤实验。  
**Evidence pointer** `paper.md` 第 41 至 47 行和表 1 的第 244 至 255 行；`data_proc/network_segments.csv` 第 1 至 14 行；`data_proc/gis_reach_line_mapping.csv` 第 1 行及按 `reach_id` 汇总后的 R002=15、R003=29、R004=140、R005=6、R006=8、R007=2、R008=193；`scripts/report_content.py` 第 5 至 15 行；`scripts/generate_paper.py` 第 1142 至 1169 行。  
**Concern** 三个网络对象被混在同一叙述和同一张表中。`network_segments.csv` 是包含七个支流节点和六个 R008 主干段的逻辑输运树。`gis_reach_line_mapping.csv` 是 393 条细 NHD 线段的可视化或过滤映射。表 1 的“NHD segments”却来自 `report_content.py` 的手写常量，给 R002、R003、R005 和 R007 记为 0，而映射文件分别有 15、29、6 和 2 条。Figure 2 图注只说 R001 没有分配线段，也与表 1 不一致。当前方法没有清楚说明哪一张网络承担前向输运、哪一张承担空间过滤、长度和汇流点如何从两者传递，以及留一河段时未持出河段的网络状态如何生成。  
**Why it matters** “transport-coupled”是本稿相对于普通点预测的核心贡献。若控制体、连接关系和长度来源不能从数据文件追溯到稿件，读者无法复现输运计算，也无法判断空间持出的独立性。  
**Minimal repair** 在方法中明确命名并分开描述“逻辑输运树”和“细 NHD 过滤/制图网”。表 1 分列逻辑节点数与实际映射的 NHD 线段数，全部从当前 CSV 生成，不再使用手写计数。增加一段简短的数据流说明，交代样点、逻辑河段、主干分段、NHD 单元和过滤单元之间的映射。无需新采样或新模型。  
**Resolution test** 新增一致性测试，从 `network_segments.csv` 验证逻辑树为 DAG、每个 R001 至 R007 仅在声明的 R008 主干段汇入一次，并从 `gis_reach_line_mapping.csv` 动态计算每个河段的 NHD 计数。生成后的表 1 和 Figure 2 图注必须与这些计数一致。测试还应失败于任何把逻辑节点计数写成 NHD 线段计数的情况。

### R3-M3 [statistical-rigor]

**Severity** Major  
**Blocking** No  
**Claim pointer** MLP 的留一河段点 RMSE 从 Baseline 的 0.0486 降至 0.0372，但这一改善不被解释为稳定成功。  
**Evidence pointer** `paper.md` 第 9、18、111 至 113、142 至 146、203、233 行；`results/tables/per_reach_cv_metrics.csv` 第 2 至 33 行；`results/tables/subgroup_metrics.csv` 第 2 至 17 行。  
**Concern** 稿件只给样点加权的汇总 RMSE，没有给八个持出河段的分布、河段等权汇总或差值不确定性。由现有 `per_reach_cv_metrics.csv` 可直接计算，MLP 相对 Baseline 的总 SSE 降幅约 95% 来自 R002 的三个样点。当前正文第 144 行反而使用了旧子组数字，并称 MLP 在多样本支流上变差，而当前子组表显示 MLP 为 0.0470、Baseline 为 0.0635。现有点估计因而同时受到版本错误和强烈河段权重影响。  
**Why it matters** 样本级 RMSE 可以回答当前 120 个观测点的平均误差，却不能单独支撑跨河段推广的稳定性。对非专业读者而言，“held-out generalization”容易被理解为各河段一致改善。  
**Minimal repair** 用现有 OOF 预测补充每河段误差和一个河段等权汇总，并明确 R002 对样点加权改善的贡献。若作者不希望加入不确定性分析，则把所有“改善推广”表述改为“在当前样点加权汇总中点 RMSE 较低”，保持现有谨慎结论。无需新数据。  
**Resolution test** 用 `nested_cv_holdout_predictions.csv` 重算逐河段 SSE、样点加权 RMSE和河段等权指标，并与 `per_reach_cv_metrics.csv`、表 3、表 5 和叙述自动比对。测试需断言正文不再出现与当前子组表方向相反的句子。

### R3-M4 [claim-moderation]

**Severity** Major  
**Blocking** No  
**Claim pointer** 标题、Plain Language Summary 和结论称浓度数据单独不能识别 `S_sgs` 与 `k` 的过程分配，并以单样本零谷和汇总剖面为主要证据。  
**Evidence pointer** `paper.md` 第 1、10、14、18、127 至 129、195、205、210 至 212、226 至 235 行；`src/16_equifinality_surface.py` 第 41 至 76、85 至 110、113 至 168、277 至 316 行；`results/tables/equifinality_summary.json` 第 7 至 23 行。  
**Concern** 单样本零谷是在观测上游浓度 `C_in_obs_mol_m3` 固定时由同一个稳态方程代数构造出来的。汇总剖面进一步假定所有样点共享一个 `k` 比例因子和一个统一源项，并按 120 个样点等权求 SSE。它不是网络级结构可辨识性分析，也不是带观测误差的统计似然。正文第 212 行承认这一边界，但标题、Plain Language Summary 和若干结论句仍容易被读成对“浓度数据”一般性质的证明。  
**Why it matters** 实际等效性是全文最重要的概念贡献。若不把固定边界、统一参数化和样本权重写进结论，证据范围会被夸大，且广泛读者难以区分代数欠定、统计可辨识性和闭合模型泛化失败。  
**Minimal repair** 在标题或副标题、摘要、通俗摘要和结论中统一限定为“在该固定上游条件和统一 `k` 比例/源项的确定性 SSE 诊断下”。如作者保留更广的“浓度单独不能识别”措辞，则用现有数据至少给出河段等权剖面作为敏感性检查。两条路径任选其一，不要求扩展研究区域。  
**Resolution test** 结果生成器应把 `objective_name`、`C_in` 来源和权重方案写入汇总 JSON，并由稿件自动渲染。claim guard 应禁止未伴随限定语的“cannot identify from concentration alone”和“model-free proof”等句式。

### R3-M5 [novelty-significance]

**Severity** Major  
**Blocking** No  
**Claim pointer** 稿件将显式空间过滤、输运耦合分组评估和模型无关目标面组合描述为贡献框架，并暗示其可服务更广泛的环境模型评价。  
**Evidence pointer** `paper.md` 第 25 至 33、87、203 至 228、235、327 至 339 行。  
**Concern** 原创性边界尚未充分建立。引言主要依赖原 East River 模型、一般环境模型评价文献、气候领域的 SGS 类比和一篇“manuscript in preparation”。读者难以判断真正的新意是河流 CO2 过程发现、一个防泄漏评估协议、确定性等效性可视化，还是这些元素的工程整合。当前单流域、10 天、无独立通量验证的证据足以支持方法学警示，但尚不足以展示广泛的水文或碳循环规律。  
**Why it matters** 这决定了工作对跨学科读者的意义，也影响摘要和讨论是否把一个有用的局部诊断包装成普适科学结论。  
**Minimal repair** 不新增实验。只需在引言末尾列出两到三个可检验贡献，并在讨论中分别说明相对 Saccardi and Winnick、常规残差学习和一般等效性分析的增量。把科学重要性定位为“评价设计和结论边界”的方法学贡献，而不是跨流域过程规律。未发表稿件不能承担关键优先权依据。  
**Resolution test** 结构检查应确认摘要、引言贡献句和结论一一对应，并且每个贡献都有当前结果或方法锚点。删除任何仅由“manuscript in preparation”支撑的原创性断言。

## Minor Comments

### R3-m1 [writing-clarity]

**Severity** Minor  
**Affected element** 章节与图号顺序。  
**Evidence pointer** `paper.md` 第 47 行先出现 Figure 2，第 93 行才出现 Figure 1。  
**Issue** 逆序出现会干扰首次阅读，也放大“逻辑网”和“过滤网”之间的混淆。  
**Required correction** 按首次引用顺序编号，或先介绍过滤概念图再展示河网图。

### R3-m2 [figures-and-tables]

**Severity** Minor  
**Affected element** 表 4 与指标命名。  
**Evidence pointer** `paper.md` 第 267 至 276 行。  
**Issue** 表 4 只有一句“in-sample metrics are not reported”，却占据正式表号。表 3 标题又把 F 叫作 primary metrics，而方法只把浓度 RMSE 定义为 primary metric，F 是 secondary diagnostic。  
**Required correction** 删除空表并重编号。把表 3 标题改为主要浓度指标和次要通量诊断，保持与方法一致。

### R3-m3 [reproducibility]

**Severity** Minor  
**Affected element** 作者信息与版本引用。  
**Evidence pointer** `paper.md` 第 3 至 4 行和第 240 行。  
**Issue** 作者和单位仍是占位符，数据可用性只给可变 GitHub 地址并提示未来补不可变版本。  
**Required correction** 投稿前补齐作者、单位、贡献声明以及不可变 commit 或 release DOI。

### R3-m4 [writing-clarity]

**Severity** Minor  
**Affected element** “nested CV”术语。  
**Evidence pointer** `paper.md` 第 111 行明确没有内层调参；`results/tables/identifiability_summary.json` 第 3 行仍写 `loo_reach nested CV`；`report.md` 第 52 行和 `report.pdf` 多页继续使用“嵌套交叉验证”。  
**Issue** 同一包内同时使用 grouped CV 和 nested CV，容易让读者误以为存在内层模型选择。  
**Required correction** 所有读者可见产物统一为 grouped leave-one-reach-out CV。历史文件名可保留，但显示标签不得再称 nested。

### R3-m5 [figures-and-tables]

**Severity** Minor  
**Affected element** `report.pdf` 的版式与版本状态。  
**Evidence pointer** `report.pdf` 第 2、13 至 18、55、70、80 页；PDF 元数据创建时间为 2026-08-16，而 `paper.md` 和 `report.md` 为 2026-09-20 快照。  
**Issue** PDF 使用旧的 Baseline 0.0284、MLP 0.0573、k 修正 0.0244 等结果，与当前论文方向相反。版式虽无明显裁切或乱码，但 81 页中存在大量半页或整页留白，表格字号偏小，图文说明频繁被拆为两页。  
**Required correction** 在 R3-M1 完成后从同一事实源重建 PDF，并重新分页。若 PDF 不是交付物，应从当前审查包移除并清楚标记为历史产物，不能与当前稿并列。

### R3-m6 [writing-clarity]

**Severity** Minor  
**Affected element** 术语对非专业读者的解释。  
**Evidence pointer** `paper.md` 第 6 至 20 行、第 81 至 91 行和第 121 至 129 行。  
**Issue** 通俗摘要较清楚，但 “closure”“filter-induced residual”“profile SSE”“uniform source” 在首次出现时仍需要读者自行推断。  
**Required correction** 各用一句非公式语言说明它们分别代表“未解析过程的模型规则”“质量平衡剩余”“对每个 k 选择最佳 S 后的误差曲线”和“对所有样点施加同一个源项”。

## Technical failings that need to be addressed before the case is established

必须先解决 R3-M1 和 R3-M2。前者要求所有读者可见产物使用唯一数值事实源，后者要求逻辑输运树与 NHD 过滤/制图网可追溯且表述一致。R3-M3 至 R3-M5 不必扩展研究范围，但需要用现有结果补足权重说明、收窄实际等效性结论并明确方法学原创性。

## Assessment against Nature-style criteria

| Criterion | Assessment |
|---|---|
| Originality | 将折内闭合目标、前向输运评估和确定性等效性剖面放在同一框架中具有潜在方法学新意，但与最接近已发表工作的区别尚未清晰，且不应依赖未发表稿件证明优先权。 |
| Scientific importance | 对环境模型“低浓度误差不等于正确过程分配”的警示有实质意义。当前证据支持 East River 个案和评价方法边界，不支持跨流域过程规律。 |
| Interdisciplinary readership | 水文学、碳循环、环境建模和科学机器学习读者均可能感兴趣。网络对象混用和内部结果冲突目前阻断了这种广泛可读性。 |
| Technical soundness | 折内目标和持出后物理求解是优点。当前快照因核心数值不一致、网络映射不可追溯及统计权重说明不足而尚未建立可靠技术案例。 |
| Readability for nonspecialists | Plain Language Summary 的方向较好，局限也相对坦诚。大量项目内部术语、版本残留、相反的模型排序和旧 PDF 使非专业读者无法形成稳定理解。 |

## Recommendation posture

当前证据链尚未建立，不宜按现状对外发布或作为投稿包评估。建议先做一次严格的版本收敛和方法映射修订。若 R3-M1 与 R3-M2 被完整关闭，并按 R3-M3 至 R3-M5 收窄结论与定位，这项工作可成为一篇有价值的环境模型评价个案和方法学警示。这里不对任何期刊的接收结果作承诺。

## Risk and unsupported boundaries

- 不能从当前包判断稿件中哪一套硬编码数字是作者最终认可版本，需以结构化结果表为准并由作者确认。
- 当前材料不支持独立验证的 CO2 逸散通量、研究区总通量、结构可辨识性定理、普适 SGS 标度律或跨流域泛化。
- MLP 的点 RMSE 较低不等于稳定跨河段优势。现有差值主要由 R002 的三个样点贡献。
- 单样本零谷是固定 `C_in` 下的代数性质。汇总 SSE 的结论依赖统一 `alpha`、统一 `S` 和样点权重。
- 对原创性的评价受限于未做外部文献检索，不能据此断言最早或唯一。
- `report.pdf` 是明显早于当前结果快照的产物，不能作为当前论文证据使用。

## Validation performed

- `scripts/verify_paper.py --mode development` 返回 0，仅报告 `paper.html` 中 `independent cells` 的一个警告。它没有发现本报告列出的跨产物数字冲突，说明现有 claim guard 覆盖不足。
- 尝试执行 `python -m pytest -q tests` 失败，原因是当前 `.venv` 未安装 `pytest`。没有据此推断测试失败或算法错误。
- 使用 Poppler 将 `report.pdf` 的全部 81 页只读渲染并检查页面缩略图，同时抽取第 2、13 至 18、55、70、80 和 81 页文本核对关键结果。未发现明显裁切或乱码，但确认版本过时和分页空白问题。
- 直接核对四张关键图。当前 RMSE 图显示 MLP 0.0372 低于 Baseline 0.0486，等效性图显示确定性 SSE，稀疏系数图保留 `log10(Da)` 且 R²=-0.448，子组图显示 MLP 在多样本支流上为 0.0470。它们均与正文若干句子不一致。

**Report status** Frozen. 本报告不会在其他 Reviewer 意见或后续综合阶段被回写。
