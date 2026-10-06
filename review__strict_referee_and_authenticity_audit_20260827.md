# 河流碳输运项目：代码、数据、论文与图件严格审稿及真实性证据审计

> 审查日期：2026-08-27  
> 审查对象：`D:\Projects\20260611-river-carbon-transport`  
> Git 基线：`main`，HEAD `3b47b241900a9f89292c65e0c8170c3e346d6241`  
> 审查结论：**当前版本不具备投稿、公开发布或据此作实质科学结论的条件；建议完成阻断性修复后，全量重算、重绘、重写并再次审查。**

## 0. 文档定位与责任边界

本文件是独立于论文正文的“审查文档”，用于记录真实性、准确性、完整性和可复现性的证据，也用于给出可执行的修改清单。审查覆盖：43 个 Python 源文件、3 个 notebook、500 个原始数据文件的文件级盘点、28 个主要处理数据文件、论文 Markdown/HTML、81 页历史 PDF 报告、当前论文引用的 11 幅图、受版本控制的 11 幅候选图，以及核心数值链的隔离环境复算。

本审查能够确认“文件来自何处、当前代码能否生成当前数值、数据字段是否对应、图与表是否一致”，但不能仅凭本地仓库绝对证明作者身份、全球首创性或完全不存在未披露的文本/代码借用。原创性最终还需要完整参考文献集、待比较稿件（尤其 Gao 等在投/在写稿）、正式相似性检测报告、作者贡献声明和人工签字。

## 1. 总体裁决

### 1.1 可确认事项

- 核心观测不是伪造数据，而是来自公开存档的 East River 野外观测与配套空间资料；本项目对其进行了二次分析。
- 当前处理表中的 120 条样本能够逐条匹配原始 Excel 中标记为 `used in model=Y` 的样本；pCO₂、温度、经纬度在匹配样本上的最大绝对差为 0。
- 在隔离临时目录中，按照当前代码补齐缺失步骤后，可以逐字节复现核心 CSV/JSON 和绝大多数当前结果图；当前论文中的主要 RMSE 数值确为本项目代码生成，并非从参考论文中直接抄入。
- 43 个 Python 文件均通过 AST 语法解析；43 个本项目 Python 文件与 69 个外部代码/源码文件比较，没有发现字节完全相同的文件。
- 对论文标题和 3 个高辨识度短语进行公开网络精确检索，没有发现明显逐字匹配稿件。该结果只能作为有限排查证据，不能替代正式查重。

### 1.2 不能确认或已经否定的事项

- **不能写“数据是我们自己采集的”**。观测数据明确来自 Saccardi、Winnick 等公开存档；正确表述应为“we reanalyzed publicly archived observations”。
- **不能确认当前科学结果准确可靠**。控制体长度、网络汇流、流量累计、滤波守恒、k-correction 目标构造和尺度分析均存在会改变结论的阻断性问题。
- **不能确认一键可复现**。`run_pipeline.py` 在缺少 `data_proc/reach_daily_observations_segmented.csv` 时于第 5 阶段失败，并且没有调用真实网络构建、目标函数/等效性分析和后续关键步骤。
- **不能确认“nested CV”**。当前实现只有按 reach 分组的外层留一验证，没有内层调参环；应改称 grouped leave-one-reach-out cross-validation，或真正实现嵌套验证。
- **不能确认“质量守恒滤波”或“独立空间单元”**。当前滤波代码没有沿 cell-DAG 传递上游质量流，并且在每个 reach/date 内用观测浓度依次推进。
- **不能确认图件与版本唯一对应**。论文当前使用的根目录图、受版本控制的 `results/figures/paper` 图和历史 PDF 报告存在互相矛盾的数值与标签。

### 1.3 投稿闸门

| 闸门 | 当前状态 | 放行条件 |
|---|---|---|
| 数据来源与许可 | 有条件通过 | 在正文和数据声明中明确公共数据来源、CC BY 许可、样本筛选与派生字段 |
| 代码可执行性 | 不通过 | 单一入口从原始数据生成全部表图论文，并在干净环境返回非零/零状态正确 |
| 网络质量守恒 | 不通过 | 修复 upstream 解析、主干流量累计、汇流质量流，并通过手算小网络测试 |
| 空间控制体 | 不通过 | 用真实 channel segment length 替代 `Shape_Length`，避免同一 reach 长度重复累计 |
| 统计有效性 | 不通过 | 修正折内目标构造、依赖结构、报告权重与不确定性；删除伪“nested”表述 |
| 图表—数据一致性 | 不通过 | 仅保留一次全量重算生成的、带 manifest/hash 的最终图；删除或归档旧图 |
| 原创性/作者责任 | 有条件通过 | 完成方法差异表、正式查重、作者贡献/AI 使用声明、人工签字 |
| 论文论断边界 | 不通过 | 移除“genuine process”“mass-conservative”“profile likelihood”等超证据措辞 |

## 2. 审查方法与证据强度

本次审查采用三位互盲审稿人分别从技术有效性与复现性、创新性与意义、可读性与逻辑一致性出发独立评审；三份意见冻结后才进行综合。主审随后完成：代码静态检查、数据谱系核对、原始—处理字段逐行比较、隔离目录重算、当前与受控版本图件二进制/视觉比较、统计设计审计、81 页 PDF 逐页缩略图检查，以及公共来源页面核验。

证据分级如下：

- A 级：可重复的代码执行、逐行数据比较、SHA-256、明确源码行或公开存档元数据。
- B 级：不同文件间的交叉一致性、图表视觉检查、方法与代码的逻辑推导。
- C 级：有限公开检索、根据字段和外部脚本作出的高可信推断；需要作者或原始元数据进一步确认。

## 3. 阻断性重大问题及具体修改

### P0-01 `Shape_Length` 被当作河道控制体长度，证据表明更可能是流域多边形周长

**证据。** `src/east_river_real_data.py:129` 将 `Shape_Length` 重命名为 `reach_length_m_sup`，`src/east_river_real_data.py:348-349` 又把每个样本行的该值直接作为 `L_m`。原始 `watersheddataCO.csv` 同时含 `Shape_Length` 与 `Shape_Area`，其组织方式更符合样本对应集水区多边形属性。配套 R 代码并不使用该字段计算河长，而是从 stream vertices 独立构造 `reach_l`。当前 `L_m` 范围 1.94–38.52 km，中位数 16.58 km；同一日期 R008 样本顺序累计 518.6 km，而论文表 1 给出的该 reach 总长仅约 20.2 km；R004 对应为 386.7 km 对约 9.9 km。

**影响。** 当前传输计算把每一个观测点都当作一个长度近似整条河段的连续控制体，导致同一 reach 的长度被重复使用几十次。以当前数据计算，气体交换/平流系数 `A·k/(86400Q)` 最小约 46、中位数约 308、最大约 950，全部大于 10；预测会被强制拉向大气平衡浓度。核心基线、残差、通量、等效性和尺度结论都因此不可解释。

**必须修改。**

1. 从经验证的中心线几何上计算相邻观测点之间的有向链长，或用 NHDPlus HR reach/cell 的真实长度；不得继续使用 `Shape_Length`，除非获得原始元数据明确证明它是 channel length。
2. 每个 date/reach 内按有向 chainage 排序，定义互不重叠的控制体边界；同一控制体只积分一次。
3. 保存 `control_volume_id, upstream_node, downstream_node, L_m_source, geometry_version`，并生成总长度守恒表。
4. 增加断言：每个 reach 所有控制体长度之和应与几何河长在预设容差内一致；不得随样本数线性增长。

**通过测试。** R008、R004 等 reach 的控制体长度和与几何中心线长度相符；一条 10 km 人工河段放置 2、10、100 个观测点时，总积分长度始终为 10 km；修复后重新生成全部模型目标、CV、表格和图件。

### P0-02 真实网络 upstream 序列化解析失效，汇流与流量累计没有发生

**证据。** `data_proc/network_segments.csv` 的 `upstream` 列是形如 `['R008_S1', 'R004']` 的字符串。`src/12_nested_cv_transport.py:259` 用 `pd.read_csv` 读入后未反序列化；`src/real_network.py:207` 对该字符串执行 `list(s['upstream'])`，得到字符列表而非节点 ID。因此 `src/real_network.py:235` 的 confluence 匹配永远失败，并在约第 240 行把每个主干 segment 的首行重新设为 `C_eq`。当前 holdout 输出中 R008_S2、S3、S4、S5 首行的 `C_in` 均为同一个 `0.0229864`，与上游质量混合不符。`_make_q_model` 还只加入“当前汇入口”的支流 Q，没有累计此前已经汇入的支流流量。

**影响。** 论文所称“real directed river network”“independent upstream boundary conditioning”“transport-coupled holdout”在当前主 CV 中没有实现。R008 被拆成多个近似独立的平衡边界段，主干下游既没有接收上游浓度质量，也没有保留累计流量。

**必须修改。**

1. CSV 中将 upstream 存为 JSON 数组，读取时用 `json.loads`；或使用单独的 edge table，禁止 Python repr 字符串。
2. 建立显式有向无环图，进行拓扑排序；每个节点的入流质量为 `Σ(Q_i C_i)`，混合浓度为 `Σ(Q_i C_i)/ΣQ_i`，下游 Q 为所有入流 Q 之和。
3. 把主干累计流量作为状态传播，不能在每个 segment 重置。
4. 读入后断言 upstream 中每个元素均是现有 segment ID；若出现单字符、未知 ID、环或孤立主干，立即失败。

**通过测试。** 构造“两支流汇入主干”的手算网络，逐节点核对 Q 和 QC；真实网络所有汇流节点的 `Q_out=ΣQ_in`、`Q_out C_mix=ΣQ_iC_i`；R008 后续 segment 的入口浓度不再无故重置为 `C_eq`。

### P0-03 样本序列不是独立控制体，所谓“总通量”重复了空间与日期

**证据。** 当前按样本行连续积分，并用每行完整的 L、W 计算 `F·L·W`；120 行来自 10 个采样日期，且不同日期/同一 reach 的空间位置重复。论文一处承认该值并非 watershed 空间积分，另一处又称“summed over the study area”。

**影响。** 当前 2.429×10^8 等通量数值既不是某一天的空间总通量，也不是 10 天的时间积分；它随采样密度和重复日期改变。Figure S2 的柱高没有稳定物理意义。

**必须修改。** 先确定 estimand：若报告日通量，应对每个 date 的唯一空间 cell 积分并给出 10 天分布；若报告 campaign-average flux，先对 date 内空间积分，再跨日期求均值/区间；若只能得到样本级诊断，应使用 `sample-level model diagnostic`，不求和、不换算为 study-area total。

**通过测试。** 同一观测行复制 10 次不能使总通量增加 10 倍；同一日期各唯一 cell 的面积之和与几何水面面积一致；图注明确单位、空间域、时间域和聚合权重。

### P0-04 “mass-conservative filter” 实际没有沿 cell-DAG 守恒传播

**证据。** `src/13_mass_conservative_filter.py:229-280` 在每个 date/reach 内从 `head_c_eq` 重新开始，用上一条观测浓度推进下一条；已构建的 `cells_upstream` 没有用于质量流传播。`_cell_level` 仅按 date+cell 作算术平均。当前四个尺度的记录数为 43、36、30、13，而唯一空间 cell 数为 39、30、24、6；图件却称这些为 independent cells。

**影响。** 所谓尺度不变性可能来自重复观测、边界重置和算术平均，而不是守恒滤波。论文“genuine unresolved process rather than resolution truncation”的判断没有证据支持。

**必须修改。**

1. 在每个 date 上对完整 cell-DAG 进行拓扑推进；没有同步边界或观测的日期不得伪装成完整网络快照。
2. 合并 cell 时按面积/质量流守恒定义过滤量，显式保存 `ΣQC`、面积和驻留时间；不使用普通算术平均替代物理聚合。
3. 分开报告“唯一空间 cell”“date-cell records”和“可独立重复单元”。
4. 在真实同步覆盖不足时，将此分析降级为 sensitivity analysis，并删除因果/过程归因措辞。

**通过测试。** 人工 DAG 在任意合并尺度下保持总 Q、QC 与面积守恒；重复同一 date-cell 记录不改变尺度曲线；图注使用真实样本单位。

### P0-05 当前 pipeline、论文、图目录和报告属于不同结果版本

**证据。** 当前论文/Table 的 Baseline、k-correction、MLP、RF RMSE 分别约为 0.0485、0.0486、0.0602、0.0750；受版本控制的 `results/figures/paper/nested_cv_rmse_bar.png` 显示约 0.0284、0.0244、0.0573、0.0745，历史 `report.pdf` 也使用旧值。`paper.md` 引用被 `.gitignore` 忽略的 `results/figures/*.png`，干净 clone 无法得到同样稿件。`run_pipeline.py` 只列出部分 01–15 阶段，遗漏真实网络、16/17 分析及论文构建，并在第 5 阶段因缺少 segmented 文件失败。`scripts/verify_paper.py` 只打印旧数字的匹配次数，即便全部为 0 也返回成功。

**影响。** 任何人都无法从提交的版本唯一确定“哪一组图、表、论文和代码”是最终结果；目前的可复现性声明不成立。

**必须修改。**

1. 建立唯一入口，例如 `python run_pipeline.py --clean --paper`，从原始数据顺序生成所有处理表、模型结果、表格、图、论文 HTML/PDF。
2. 每个阶段声明输入/输出并检查存在性；任何阶段失败立即返回非零状态。
3. 最终图和表进入版本控制或通过带 hash 的发布工件保存；删除/归档过时 `results/figures/paper` 与历史报告，禁止同名不同义。
4. 生成 `artifact_manifest.json`，记录 Git commit、dirty 状态、Python/依赖版本、随机种子、输入/输出 SHA-256、生成时间和执行命令。
5. 把 paper claim guard 改成真正的测试：数值、样本量、图文件 hash 或 manifest 不一致即失败。

**通过测试。** 在新目录/干净 clone 中只执行文档化的一条命令，全部输出成功且与发布工件 hash 一致；删除任一必要输入或篡改表中一个数值时测试必须失败。

### P0-06 k-correction 训练目标、折内构造和论文描述互相矛盾

**证据。** 论文称 `k_needed≤0` 的 61.7% 样本作为 infeasible rows 被排除；`src/12_nested_cv_transport.py:208-222` 实际把这些样本的 log-k 全部压到 -12，并把 120 行全部用于训练。精确核对为 74/120 infeasible，74 行全部成为下限目标。`k_correction_saturation.json` 的 `n_predictions=2160` 是 120 行在 18 个 reach/date fold 上被重复预测，而不是 120 个 held-out 预测。训练目标在折分之前用全数据生成；一旦网络路由修复，held-out 支流观测可能进入下游训练样本的目标构造。

**影响。** 当前 k-correction 指标和饱和率的统计单位错误，论文方法描述不真实；修复网络后还可能产生跨 fold 信息泄漏。

**必须修改。**

1. 先定义 infeasible 目标的科学处理：排除、删失模型、两阶段分类+回归或带边界的物理优化；不得把排除写成截断。
2. 在每个 fold 内仅用训练 reach/date 重建网络状态和目标；对于依赖 held-out 支流边界的下游训练行，应删除、遮蔽或使用真正独立边界。
3. 每个样本只产生一次 held-out prediction；另行保存 train/full-fit 预测，字段名中明确 split。
4. 报告下限/上限命中率、可行样本数和目标分布；不要把 2160 条重复预测当作 n。

**通过测试。** held-out 标签随机置乱或删除后训练目标及训练预测不变；最终 held-out 表恰有 120 行且每个 SampleID 一行；方法、代码和饱和率 JSON 对 infeasible 行的处理一致。

## 4. 其他重大与次要问题

### P1-01 目标函数不是 profile likelihood

`src/16_model_free_equifinality.py` 使用确定性平方误差，没有观测误差分布、方差模型或层级结构。因此 Figure 5 和正文应改为 **profiled least-squares objective** 或 **profiled SSE/RMSE**。单样本的零谷是代数恒等关系；它证明单点条件下参数可补偿，但不能单独证明完整数据生成过程的结构不可辨识。若要用 likelihood，应明确概率模型并估计/规定误差尺度。

### P1-02 统计单位、依赖结构和不确定性没有充分处理

数据共 120 个样本、8 个 reach、10 个日期；reach 样本数极不均衡（1、3、15、24、17、1、1、58），且没有任何日期覆盖完整网络。R001、R006、R007 只有一个样本，不能支持 reach 级泛化判断。当前只给 pooled 点估计，缺少 fold 分布、区间与宏/微平均说明；MLP 的内部随机 early-stopping split 对小样本不稳定。

修改建议：

- 将所有 “nested CV” 改为 “grouped leave-one-reach-out CV”，或增加只在训练折内进行的内层调参。
- 同时报告 pooled/micro、reach-macro、每折 RMSE/MAE/bias 和每折 n；突出 R002 等高影响 fold。
- 以 reach/date 为聚类单位评估不确定性；因只有 8/10 个聚类，区间只能作探索性描述，并明确有限聚类限制。
- 固定并记录全部随机种子；MLP 不应使用会跨空间/日期结构随机拆分的默认 early stopping。
- 不进行没有预先定义误差模型的显著性检验；当前结论限于描述性泛化表现。

### P1-03 非同步采样导致空间与时间混杂

同一日期不覆盖完整网络，R008 覆盖 6 个日期，多个支流只覆盖 1 个日期。把不同日期观测串成同一稳态网络会把时间差当成空间输运。应优先限定到同步/近同步子集，或构建显式时变/层级模型；至少要在表中列出 date×reach 覆盖矩阵，并把当前结果表述为 campaign-specific diagnostic，不作全流域同时态推断。

### P1-04 水头边界与流量输入含有数据依赖

`src/real_network.py:213-217` 用观测温度均值计算 headwater `C_eq`，但论文称其为 temperature-dependent boundary，容易被理解为逐样本/独立边界。应在每个 fold 内用预先指定或训练侧可用的温度构造边界，并清楚区分 fixed climatological、date-specific external 和 observation-derived boundary。

### P1-05 Damköhler 数的时间单位不一致

当前驻留时间使用秒，而 k 使用 m d⁻¹；相应无量纲项没有统一单位。必须将 k 转成 m s⁻¹或将驻留时间转成 day 后重算全部 dimensionless predictors、LASSO 系数、交叉验证 R² 和 Figure 7。修复前 Figure 7 不应保留。

### P1-06 方法创新的相对位置没有建立

Saccardi & Winnick 原研究已经包含沿 stream network 的过程模型、平流/大气交换和地下水/水柱/河床潜流带过程。本项目能主张的潜在增量更像是“在同一公开数据上的简化平衡残差、分组泛化评估、离散尺度敏感性和 discrepancy allocation 诊断”，而不是首次建立 East River 网络碳输运。应增加方法差异表，逐项列出：输入、状态、空间离散、边界、过程项、估计目标、验证设计和本项目新增部分；没有完成 Gao 稿件比较前不得写 first/novel/unprecedented。

### P1-07 文档和旧审计结论已经过期

`README.md`、`docs/RESEARCH_INTEGRITY_AUDIT.md`、`docs/METHOD_RECALCULATION.md`、`report.md/html/pdf` 仍声称旧链式网络、旧指标或已实现守恒，而当前代码与之冲突。应在文件顶部标记 SUPERSEDED 或删除后重建；本文件应作为本轮审查基线，不能再沿用旧“全部正确/闭环”的结论。

### P2 次要但必须统一的问题

- 论文先出现 Figure 2 再出现 Figure 1，需重排编号。
- “unphysical” 应改为 “infeasible under the specified one-box balance and boundary assumptions”。
- “genuine unresolved process” 改为 “an unresolved residual under the implemented diagnostic”，修复前最好删除。
- 所有公式明确单位、日/秒换算、面积/宽度来源和正负号约定。
- 补充 Ulseth、Sander/NIST、Wanninkhof 等实际进入公式或实现的方法来源；当前参考文献 11 条不足以覆盖方法。
- 作者、单位、通信作者、Gao 稿件 DOI 等占位符必须在投稿前清零。

## 5. 数据来源、真实性和“是否为自己的结果”证据链

### 5.1 公开原始数据与许可

| 资产 | 来源/权属 | 本地作用 | 审查结论 |
|---|---|---|---|
| East River stream CO₂ Excel | HydroShare 资源 `9f907b46...`，Saccardi & Winnick，CC BY | 观测 pCO₂、温度、坐标、样本筛选 | 外部公共观测，不是本项目自行采样 |
| East River supplementary model/spatial data | HydroShare 资源 `2a213299...`，Winnick，CC BY | watershed、stream、discharge/旧 R 代码等 | 外部公共空间与模型资料，应逐项注明 |
| USGS 09112500 日流量 | USGS Water Data | 流量边界/核对 | 公共政府数据，应记录下载时间和参数代码 |
| NHDPlus HR | USGS | 网络几何/可视化候选 | 公共基础地理数据，应保留版本/下载清单 |
| 本项目 processed tables/results | 本仓库 Python 派生 | 训练目标、预测、统计与图表 | 可以称项目派生结果，但当前物理正确性未通过 |

已核验的公开来源：

- HydroShare East River CO₂：<https://www.hydroshare.org/resource/9f907b46baa848e180c49339d605bf31/>
- HydroShare supplementary model/spatial data：<https://www.hydroshare.org/resource/2a2132999fb84214aad0596783812db2/>
- USGS 09112500：<https://waterdata.usgs.gov/monitoring-location/USGS-09112500/>
- USGS NHDPlus HR：<https://www.usgs.gov/national-hydrography/nhdplus-high-resolution>
- Saccardi & Winnick 原论文：<https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1029/2021GB006972>

### 5.2 原始—处理样本核对

原始 Excel 含 161 条数据记录，其中 121 条标记 `used in model=Y`。当前处理表有 120 条，SampleID 精确匹配 120 条；唯一未进入处理表的是 `CC-1`，其日期解析为 1900-01-06，明显需要作者给出预先定义的排除理由。对已匹配 120 条，pCO₂、T、lat、lon 的最大绝对差均为 0。这说明核心观测值没有在处理过程中被悄然替换，但筛选规则必须显式化、测试化。

### 5.3 关键输入 SHA-256

| 文件 | SHA-256（前 16 位；完整值应写入最终 manifest） | 大小/说明 |
|---|---|---|
| Saccardi 观测 Excel | `D739341A6FE163D6` | 40,061 bytes |
| `watersheddataCO.csv` | `C52347C629F1FE4E` | 14,079 bytes |
| 补充 Q 表 | `3B5755…` | 外部输入 |
| 原始配套 R 代码 | `4CB354…` | 用于含义交叉核对，不是当前主入口 |
| USGS daily 数据 | `2561DA…` | 公共输入 |
| NHD GeoJSON | `C92BF2…` | 网络候选输入 |

完整 SHA-256（每 16 位分组，仅为排版；去除空格即为完整值）：

```
D739341A6FE163D6 FE56C2B91783E627 9E2B8D76EB2638EA 186D223CDC6F714A  Saccardi_and_Winnick_Data.xlsx
C52347C629F1FE4E 8242851EED938A62 DFBA7049E56B546B CC12B6921EF93F56  watersheddataCO.csv
3B5755780E201306 AEC3463E22E02220 C6288EF53AF42387 048962D21D7DE815  Q elivation regreshion.csv
4CB354856B3B0EA0 D10DF97958F81BC5 194C6215B9135596 987BF948C5D6978C  Dataset 3 R code.R
2561DA935748210D A09B02583B2ECE64 11DDE23E9D2E467A 2A37AB75FECACFC6  09112500_discharge_daily_2019.csv
C92BF2DA7695D8F5 D1EF12BFE8603876 780A0AD899FFAAA07 98F9249F7ADD213  nhdplus_hr_huc14020001_flowlines.geojson
```

### 5.4 项目派生结果的复算证据

在隔离临时目录运行当前代码时，`run_pipeline.py` 的 1–4 阶段成功，第 5 阶段因缺少 segmented 文件失败。人工按依赖顺序补运行 `real_network` 后，核心训练、CV、filter、identifiability/equifinality 均可完成。以下关键输出与工作区版本逐字节一致：

- `reach_daily_observations.csv`
- `reach_daily_observations_segmented.csv`
- `network_segments.csv`
- `sgs_training_data.csv`
- grouped-CV metrics 与 per-reach metrics
- filter-scale metrics
- identifiability/equifinality metrics
- 绝大多数当前根目录结果图

当前代码复算得到的 headline RMSE 为：Baseline 0.04847996、k-correction 0.04855835、Residual-AI MLP 0.06024895、RF 0.07501956 mol m⁻³。它们与当前论文数字一致，说明这些数字由当前代码产生；但由于 P0-01 至 P0-06，这只能证明**计算来源**，不能证明**科学正确性**。

### 5.5 原创性有限排查

本项目 43 个 Python 文件与本地 69 个外部源代码文件没有字节完全相同文件；主执行路径没有读取 `data_raw/conus_carbon` 或大型 Raymond 数据文件中的科学结果；论文标题和 3 个辨识度较高短语的公开精确检索没有明显匹配。这些是“未发现直接复制”的正面证据，但不是绝对证明。

投稿前仍须完成：

1. 用 iThenticate/Turnitin 或期刊认可系统生成全文相似性报告，并由作者逐项解释方法性共用语句。
2. 对所有外部公式、参数化关系、代码片段和图形底图建立 source-to-use 表。
3. 获取 Gao 等未公开/在写稿的完整版本，做功能与文本差异比较。
4. 所有作者签署贡献与数据来源声明；若使用生成式 AI 参与代码、图片检查或语言修改，按目标期刊政策披露，并由人类作者逐项承担责任。

### 5.6 允许与不允许的论文表述

允许：

> We reanalysed publicly archived East River CO₂ observations and spatial data. All derived targets, cross-validation predictions, tables and figures reported here were generated by the versioned analysis code described in the reproducibility manifest.

不允许：

> We collected/produced the East River observations ourselves.  
> Every value is original and independently validated.  
> The results prove a genuine unresolved biogeochemical process.

## 6. 逐图数据逻辑与视觉审查

### Figure 1 `les_filter_conceptual.png`

视觉上清楚，但属于概念示意而不是已验证算法图。当前图暗示局部平流、合并单元和残差都按守恒实现，代码并没有做到。应增加流向箭头、观测/模型状态区分，并在修复前将图注改为“intended analysis schematic”。

![当前 Figure 1](D:/Projects/20260611-river-carbon-transport/results/figures/les_filter_conceptual.png)

### Figure 2 `figure2_reach_assignment_and_samples.png`

图形本身清晰，但标题和来源逻辑误导。`src/10_gis_network_viz.py:775-779` 的 manifest 表明底层绘制来自 legacy `East_River_Lines.shp` 的 393 条线，而正文称 NHDPlus HR。大量 segment 通过 nearest-sample 被赋给逻辑 reach：R008 193、R004 140、R003 29 等；按 GNIS 匹配的数目远小得多，R001 没有分配 segment。应把“可视化背景线”和“进入传输模型的验证网络”分开，提供赋值方法、距离阈值、未确定区域和人工核验图；未核验前不得称真实 NHDPlus HR 网络。

![当前 Figure 2](D:/Projects/20260611-river-carbon-transport/results/figures/figure2_reach_assignment_and_samples.png)

### Figure 3 `nested_cv_rmse_bar.png`

当前根目录图的数值与论文一致，但标题/y 轴仍出现破损 TeX 文本（`C\{aq\}$` 之类）；当前代码在隔离重绘时文字已变化，说明工作区 PNG 并非严格由当前代码最后一次生成。受版本控制的同名候选图又显示旧指标。应先修复算法，再从唯一 manifest 一次性生成，标题改为 grouped leave-one-reach-out。

![当前根目录 Figure 3](D:/Projects/20260611-river-carbon-transport/results/figures/nested_cv_rmse_bar.png)

![受版本控制但数值过时的 Figure 3](D:/Projects/20260611-river-carbon-transport/results/figures/paper/nested_cv_rmse_bar.png)

### Figure 4 `nested_cv_scatter_holdout.png`

图中点与当前 held-out 表对应，但 R002 极端值压缩了多数点，且大量点重叠。建议增加 reach facet 或主图+放大 inset，使用透明度/空心点，并在图中或补充表明确每 reach 的 n、RMSE、bias。修复 fold 目标和网络路由后必须全量重画。

### Figure S1 `subgroup_rmse_r008_vs_trib.png`

将 R002–R005 合并为“multi-sample tributaries”掩盖了 reach 间巨大差异，且无任何不确定性。应优先画每折值和 n，单样本 reach 只作描述；若保留 pooled subgroup，说明样本加权方式。

### Figure 5 `equifinality_objective_surface.png`

分辨率和视觉层次良好，但 panel/正文使用 profile likelihood 不准确；应改为 deterministic profiled least-squares objective。色条、最小值和区间需注明是否用全数据、训练数据或 held-out 预测。单点零谷和 pooled 浅谷应分开解释，不把其扩大为正式结构可辨识性结论。

### Figure S2 `supp_flux_diagnostics.png`

当前 sample-summed flux across dates 没有稳定物理量定义，是最需要删除或重算的图。若仅作样本级模型诊断，不应累加；若作日通量，应按 date×unique cell 积分并显示日期分布和不确定性。

### Figure 6 `filter_scale_sgs.png`

x 轴线性尺度使前三点严重挤在左端，更重要的是数据并非真正守恒滤波结果。修复后建议用离散类别轴或对数 x 轴，显示每个尺度的空间 cell 数、date-cell 数、中心值和区间，不再用“independent cells”。

![当前 Figure 6](D:/Projects/20260611-river-carbon-transport/results/figures/filter_scale_sgs.png)

### Figure S3 `filter_scale_sgs_box.png`

散点代表 date-cell records 而不是独立空间 cells，图注错误。修复后标出重复结构，或用每个日期一条尺度曲线并按日期汇总。

### Figure 7 `dimensionless_coefficients.png`

视觉简洁，但 Da 单位错误使系数必须重算。图中 full-data LASSO 系数与 leave-one-reach R² 混在一起，读者容易误以为系数是 held-out 估计。应分成“全数据描述性 refit”和“out-of-fold performance”两部分，增加折间系数稳定性/选择频率，不再保留内部变量名后缀 `_z` 作为读者标签。

### 图件通用出版问题

- 当前主要图仅有 PNG；多份绘图脚本没有显式统一字体、可编辑文本设置、SVG/PDF 输出和最终版面宽度。
- 多图实际宽度约 239–495 mm，未按单栏约 89 mm/双栏约 183 mm 的最终尺寸设计；缩小时文字可能过小。
- 需要统一字体、最小字号、色盲友好配色、线宽和 panel 标签；导出矢量 PDF/SVG，必要时另供 300–600 dpi TIFF。
- 每幅图旁保存 source CSV 和 `figure_manifest.json`：脚本、输入 hash、输出 hash、Git commit、参数、轴标签、单位、统计单位和生成时间。

## 7. 论文与历史报告审查

### 7.1 论文正文

论文叙事线目前把“基线优于 ML”“尺度近似不变”“k 与 residual 等效”串成一个较强过程结论，但前两条严重依赖错误的控制体/网络/滤波实现。建议在修复前冻结摘要、结果和讨论，只保留数据来源和计划方法框架。

需要立即删除或暂存的句子类型：

- “real directed network”“mass-conservative filter”“independent upstream boundary”，直至相应测试通过。
- “near-invariance indicates a genuine unresolved process”。
- “profile likelihood”，改为 “profiled least-squares objective”。
- “unphysical rows were excluded”，因为当前代码实际截断并训练。
- “summed over the study area”，除非通量积分重新定义。

### 7.2 `report.pdf` 与生成脚本

历史 PDF 共 81 页，视觉检查未见明显文字重叠或裁切，但存在大量半空白页面、图过小、引用仅 5 条、旧链式网络和旧 RMSE。`scripts/generate_report.py`、`scripts/export_pdf.py` 等仍硬编码旧数字。该 PDF 应重命名并标注 `HISTORICAL — NOT FOR SUBMISSION`，或移出发布目录；生成脚本必须改为直接读取最终结果文件，禁止在叙述字符串中硬编码指标。

## 8. 建议的修订后方法结构

### 8.1 一句话证据主线

完成阻断性修复后，建议全文围绕以下主线组织：

> Using publicly archived East River observations, we test whether alternative discrepancy allocations generalize under an explicitly audited river-network mass balance, using fold-specific transport predictions and process diagnostics, with inference restricted to a ten-day single-watershed campaign.

### 8.2 术语账本

| 当前术语 | 建议术语 | 使用条件 |
|---|---|---|
| nested CV | grouped leave-one-reach-out CV | 当前实现；若有训练折内 inner loop 才可称 nested |
| k optimization / likelihood | k-correction / profiled least-squares objective | 没有概率误差模型时 |
| mass-conservative filtering | spatial rebinning sensitivity | 当前版本；DAG 守恒测试通过后才能恢复前者 |
| independent cells | unique spatial cells / date-cell records | 按真实统计单位分别使用 |
| unphysical samples | infeasible under the specified balance | 明确是模型条件下不可行 |
| our observations | publicly archived observations reanalysed here | 除非作者确实参与原始采集并披露角色 |
| genuine unresolved process | unresolved model discrepancy | 不作未经验证的过程归因 |

### 8.3 建议 Methods 章节顺序

1. Study data, provenance and sample inclusion。
2. Network geometry and control-volume construction。
3. Flow, hydraulic geometry and unit conventions。
4. Quasi-steady carbon balance, states, boundaries and sign convention。
5. Baseline and alternative discrepancy allocations。
6. Fold-specific grouped evaluation and leakage controls。
7. Scale-sensitivity operator and conservation tests。
8. Statistical summaries, uncertainty and limitations。
9. Reproducibility manifest, code/data availability and AI disclosure。

### 8.4 可直接改写进论文的 Methods 草稿（修复后使用）

**Data provenance and inclusion.** We reanalysed publicly archived observations from the East River, Colorado, together with archived spatial and discharge products. The raw observation table contained 161 records, of which 121 were marked by the source dataset as used in the original model. We retained 120 records after applying the prespecified date and identifier checks described in Table S[AUTHOR INPUT NEEDED]. The excluded record (`CC-1`) contained a date value parsed as 6 January 1900; the scientific and procedural basis for its exclusion must be confirmed by the authors. Raw files were retained without modification and identified by SHA-256 in the release manifest; all processed tables were regenerated by versioned scripts.

**Control volumes and routing.** [AFTER FIX] We represented the sampled corridor as a directed acyclic graph of non-overlapping channel control volumes. Control-volume lengths were calculated from the validated channel centreline between adjacent cell boundaries rather than from watershed polygon attributes. At a confluence, discharge and dissolved-carbon mass flux were mixed as `Q_out=ΣQ_i` and `C_mix=Σ(Q_iC_i)/ΣQ_i`. Automated tests verified node identifiers, acyclicity, cumulative discharge and conservation of `QC` at every confluence.

**Balance and units.** [AFTER FIX] For each control volume and sampling date, the quasi-steady balance propagated upstream concentration through advection, atmospheric exchange and an optional areal discrepancy term. All quantities were converted to a single SI/day convention before evaluation; the manuscript and source tables report the conversion used for `k`, residence time, area and flux. Hydraulic width, depth and velocity were model-derived inputs rather than field-measured cross sections, and uncertainty in these relations was not identifiable from this campaign.

**Grouped evaluation.** [AFTER FIX] Generalization was assessed by leaving one logical reach out at a time. Every target and network state used by a closure was recomputed within the training fold. Observations or boundary states from the held-out reach were not used to construct targets for downstream training records; records that depended on an unavailable held-out boundary were removed according to a prespecified graph rule. Hyperparameters were either fixed a priori or selected only within the training data. Each observation therefore contributed exactly one out-of-fold prediction.

**Scale sensitivity.** [AFTER FIX] We evaluated spatial aggregation on the directed cell graph. Aggregation preserved total discharge, dissolved-carbon mass flux and water-surface area by construction. We distinguished unique spatial cells from repeated date-cell records and summarized the scale response first within date and then across dates. Because the campaign did not synchronously cover the full network on any date, this analysis was interpreted as a sampling-conditional sensitivity test rather than a direct estimate of a watershed-wide scaling law.

**Inference boundary.** Results are descriptive for one watershed and a ten-day campaign with strongly unbalanced reach coverage. We report pooled and reach-level predictive errors, fold sizes and cluster-aware exploratory intervals. These intervals do not remove the limitation imposed by only eight reaches and ten dates. A shallow profiled least-squares objective indicates compensation between the source and gas-exchange allocations under the specified balance; it is not presented as a formal proof of structural identifiability.

## 9. 分阶段具体修改路线图

### Phase 0：冻结当前版本并防止误用（立即）

- 给 `report.pdf`、旧 docs 和旧图目录加 `SUPERSEDED/NOT FOR SUBMISSION` 标记。
- 保存当前 HEAD、dirty 文件清单和输入 SHA-256，不覆盖原始数据。
- 暂时撤下摘要和结论中的核心数值，直到全量重算。

**完成标准：** 工作区里只有一个明确标识的 active result set；旧工件不会被论文构建脚本引用。

### Phase 1：重建数据字典和控制体

- 为每个原始字段写 source、单位、含义、许可、转换、缺失处理。
- 确认 `Shape_Length` 元数据；无证据时禁止用于 channel length。
- 从中心线计算 chainage 与非重叠 L，生成几何 QA 图和长度守恒表。

**完成标准：** 每个 processed 字段都能追溯到 raw 字段/公式；reach 长度不随样本数重复。

### Phase 2：修复 DAG 路由和质量守恒

- upstream 改 JSON/edge table；拓扑排序；累积 Q 和 QC。
- 编写至少 5 个小网络单元测试：单河段、串联、两支流汇流、多次汇流、非法环/未知 ID。

**完成标准：** 所有节点守恒误差在数值容差内；任何错误 topology 立即失败。

### Phase 3：重新定义目标和交叉验证

- 在 fold 内生成训练目标；屏蔽 held-out 下游依赖。
- 明确 k infeasible 的处理并保持论文/代码一致。
- 每个 SampleID 只保留一次 OOF prediction；分开 full-fit。

**完成标准：** 泄漏测试通过；预测表 120 行；删掉 held-out y 后训练过程不变。

### Phase 4：修复滤波、通量和无量纲分析

- 实现 DAG 守恒聚合；按 date×unique cell 计算。
- 重新定义 flux estimand；做复制不变性测试。
- 统一 k/驻留时间单位后重算 dimensionless closure。

**完成标准：** 合并前后 Q、QC、面积守恒；重复样本不改变空间积分；无量纲量真正无量纲。

### Phase 5：统计和稳健性分析

- 输出每 reach/date 样本矩阵、每折指标、macro/micro 指标、影响诊断。
- 增加透明的探索性 cluster bootstrap 或 leave-one-date/reach sensitivity；报告小聚类限制。
- 做边界浓度、几何参数、k 参数化和 R002 极端值敏感性分析。

**完成标准：** 任何总指标都能追溯到折级表；结论不靠单一高影响 fold 隐藏支撑。

### Phase 6：全量生成图表与论文

- 全部图从 source CSV 构建；输出 SVG/PDF+高分辨率 PNG/TIFF。
- 一次性生成表格、正文数值、图注和 manifest，禁止手抄指标。
- 修复 Figure 编号、标签、单位、统计单位和矢量输出。

**完成标准：** 图中数字、caption、table、Results 可由测试自动交叉核对；干净构建 hash 一致。

### Phase 7：重写方法、结果与讨论

- 先写方法差异表，再写本项目贡献；限制到公开数据再分析与诊断增量。
- Results 只写修复后 OOF 结果；Discussion 区分数据事实、模型诊断和推测。
- 增加数据/代码可用性、作者贡献、利益冲突、AI 使用与局限声明。

**完成标准：** 每个强结论有对应的表/图/测试；所有外部成分有引用；所有占位符清零。

### Phase 8：独立复核与签字

- 由未参与主要编码的人从干净环境复算。
- 做正式相似性检测、参考文献逐条核验和最终统计审查。
- 作者逐项签署下列 integrity checklist。

**完成标准：** 第二环境复算通过；所有 P0/P1 问题有关闭证据和审查人签名。

## 10. 真实性、准确性、完整性签字清单

### 数据真实性

- [ ] 原始文件只读保存并记录完整 SHA-256、来源 URL、许可和下载日期。
- [ ] 每个处理字段有数据字典和可执行转换；无人工隐藏替换。
- [ ] 120/121 样本筛选规则由作者确认并在代码中测试。
- [ ] 外部观测不被表述为本项目自行采集。

### 计算准确性

- [ ] 控制体长度来自已验证 channel geometry，且不重叠、不重复。
- [ ] upstream ID、拓扑、累计 Q 和 QC 守恒测试全部通过。
- [ ] fold 内目标构造无 held-out 信息泄漏。
- [ ] 单位测试覆盖 k、Q、L、W、面积、时间、浓度和通量。
- [ ] 通量对重复观测不敏感，空间/时间聚合有明确 estimand。

### 代码完整性

- [ ] 单一 pipeline 从 raw 到论文工件完整成功。
- [ ] requirements/lockfile 与实际执行环境一致；当前 `.venv` 与 `requirements.txt` 明显不一致的问题已解决。
- [ ] 自动测试覆盖数据模式、拓扑、守恒、CV 泄漏、指标和图表 claim guard。
- [ ] 运行失败返回非零状态；验证脚本不会只打印警告后成功退出。

### 结果与图件完整性

- [ ] 每个样本恰有一次 OOF 预测；full-fit 与 OOF 分文件保存。
- [ ] 论文、表、图和 source CSV 来自同一 commit/manifest。
- [ ] 所有旧图/旧报告被归档且不会被当前稿件引用。
- [ ] 图注写明 n、统计单位、聚合权重、误差条和模型/观测性质。

### 原创性与责任

- [ ] 建立与 Saccardi/Winnick、Raymond、Ulseth、Gao 等的 methods-delta 表。
- [ ] 形成正式全文相似性报告并逐项解释。
- [ ] 所有外部公式、代码、底图、数据和参数化均正确引用。
- [ ] 作者贡献、数据来源、AI 使用和最终人工复核声明完整。
- [ ] 全体作者确认：派生结果由版本化代码生成，且没有把参考论文数值冒充为本项目新结果。

## 11. 三位盲审意见综合

三位互盲审稿人均给出“阻断/大修后重审”的一致判断。技术审稿人重点指出控制体长度重复、版本/pipeline 不闭合、滤波不守恒和时间边界不独立；意义审稿人重点指出相对既有 East River 模型的增量不清、折前目标构造风险和目标函数没有概率意义；可读性审稿人独立发现 upstream 字符串解析导致真实网络路由失效，并指出 k 目标、图件版本和“profile likelihood”叙述冲突。三方在未互通意见前都认为核心结论不能由当前证据支持，因此本综合裁决不是单一审稿人的偏好。

## 12. 最终优先级

如果只能先做三件事，应按以下顺序：

1. **重建非重叠 channel control volumes，并修复 DAG 汇流与累计 Q/QC。** 这是所有结果的物理基础。
2. **在每个 fold 内重建目标和边界，重新定义 filter/flux estimand，再全量复算。** 这是统计和尺度结论的基础。
3. **建立单一可复现 pipeline 与 manifest，随后才重绘、重写和做原创性正式核验。** 这是保证“确实由自己的方法算出、没有半算半猜”的最低证据链。

在上述三项完成前，当前 RMSE、尺度不变性、通量预算、维度无关闭合和过程等效性均应视为**待重算的开发中结果**，而不是可投稿结论。
