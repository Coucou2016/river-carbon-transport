# 本轮术语与修订约束

本文件在正文编辑前建立。修订对象为冻结的 paper.md；不覆盖根目录原稿，不改变原始数据或生产代码。

| 概念 | 统一写法 | 禁止混淆 |
|---|---|---|
| 数据归属 | reanalysis of publicly archived observations | 不写成作者自行采样 |
| 作者计算 | recomputed model outputs / diagnosed residuals | 不等于独立观测或方法原创性证明 |
| 前向网络 | logical simplified routing tree | 不等于已验证的 NHD path compression |
| 地理对象 | NHDPlus HR mapping / filtering network | 图上匹配不等于物理路径验证 |
| 验证协议 | grouped leave-one-reach-out evaluation | 无内层调参，不称 nested CV |
| 浓度表现 | sample-weighted point RMSE | 不宣称显著、稳定或跨流域优势 |
| 通量 | overlapping sample-area flux diagnostic | 不称 watershed total 或实测通量 |
| 目标曲面 | conditional deterministic profile SSE | 不是 likelihood、置信区间或全网络识别定理 |
| SGS | diagnosed source–sink residual | 不是实测生物地球化学源项 |
| 无量纲稀疏式 | descriptive full-data S* fit | 与 dimensional transport LASSO 分开 |

写作顺序：先证据、后句子；逐段保留原有研究问题、方法、结果和局限；更正旧数字，补足实现细节；未修复的代码不得改写成已完成。用具体主语、动词和量替代夸张评价，不制造“人类作者”身份、经历或检测器通过保证。

本轮参考 humanizer、human-writing、no-ai-slop 的去模板化原则，优先服从学术精确性，不采用其博客式口语或禁用某种标点的机械规则。Manchester Phrasebank 仅用于方法顺序、结果限定和讨论衔接，不拼接原句。
