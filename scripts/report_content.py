"""Chinese report prose, river-network table, and figure manifest for generate_report.py."""

# Eight study reaches: upstream → downstream (R001 tributary head → R008 East River mainstem)
REACH_NETWORK_ROWS = [
    ("R001", "Bradley Creek", "—", "R002", "12.6", "0", "1", "支流源头，n=1 仅作示意"),
    ("R002", "Bradley Meadow", "R001", "R003", "12.5", "0", "3", "草甸河段，连接 Bradley 与 Rock"),
    ("R003", "Rock Creek", "R002", "R004", "6.1", "0", "15", "Rock 溪，多样本支流"),
    ("R004", "Copper Creek", "R003", "R005", "9.9", "23", "24", "NHD GNIS 匹配良好"),
    ("R005", "Gothic Creek", "R004", "R006", "4.8", "0", "17", "Gothic 支流，多样本"),
    ("R006", "Quigley Creek", "R005", "R007", "2.8", "6", "1", "单样本，仅作示意"),
    ("R007", "Rustlers Gulch", "R006", "R008", "23.5", "0", "1", "单样本，仅作示意"),
    ("R008", "East River 干流", "R007", "—", "20.2", "46", "58", "干流 Almont 上游，样点最密"),
]

REACH_NETWORK_TABLE_HTML = """
<table>
  <caption>表 2 East River 研究河网：8 条河段自上而下（上游→下游）的衔接关系</caption>
  <thead>
    <tr>
      <th>河段编号</th><th>河流名称</th><th>上游河段</th><th>下游河段</th>
      <th>河长 (km)</th><th>NHD 线段数</th><th>样点数</th><th>说明</th>
    </tr>
  </thead>
  <tbody>
""" + "\n".join(
    f'    <tr><td>{r[0]}</td><td class="left">{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td>'
    f'<td>{r[4]}</td><td>{r[5]}</td><td>{r[6]}</td><td class="left">{r[7]}</td></tr>'
    for r in REACH_NETWORK_ROWS
) + """
  </tbody>
</table>
<p class="lead">读图前请先理解这张表：<strong>水从 R001 一侧的支流出发，依次流经 R002–R007，最终在 R008 East River 干流汇集</strong>。
模型中的流量、浓度、CO₂ 通量都是按这条“链条”从上游向下游传递的。平面 GIS 图中的彩色河线，来自 HydroShare 补充包里的
<code>East_River_Lines.shp</code>（共 393 段国家水文数据库 NHD 线段），不是人工画的点。</p>
"""

READING_GUIDE_HTML = """
<div class="reading-guide">
  <h3>如何阅读本报告（建议顺序）</h3>
  <ol>
    <li><strong>先看表 2</strong>：弄清 8 条河段谁在上游、谁在下游、哪条是干流（R008）、各有多少个实测样点。</li>
    <li><strong>再看第四节 A 组图（图 1–5）</strong>：在真实河网线上看样点分布、流量与流速箭头——建立空间概念。</li>
    <li><strong>然后看 B 组（图 6–11）</strong>：水动力沿河道如何变化；图 9 是理想化断面内的流速分布示意。</li>
    <li><strong>接着看 C、D 组</strong>：pCO₂、CO₂ 通量在空间和时间上如何分布；Baseline 与 AI 方法差在哪里。</li>
    <li><strong>最后看嵌套交叉验证图与主表</strong>：论文主指标是<strong>留一河段/留一日期后的 C<sub>aq</sub> 与 F<sub>CO₂</sub></strong>，不是样本内 R²=0.997。单样本河段（R001、R006、R007）只作示意，不与干流 58 个点均等权重。</li>
    <li><strong>再看创新实验图（滤波、可辨识性、无量纲式）</strong>：用来解释<strong>为什么</strong> ML 不能推广，而不是用来声称精度提高。</li>
  </ol>
  <p>全文数据均来自 Saccardi &amp; Winnick (2021) 在 HydroShare 公开的 East River 战役观测（2019 年 8 月 2–11 日，共 120 个水样），未使用合成数据。</p>
</div>
"""

SECTION_INTROS = {
    "network": (
        "<h3>4.1 研究区河网：哪一段是哪条河？</h3>"
        "<p>本节回答三个问题：<strong>（1）河网在地图上长什么样？（2）8 条研究河段与 NHD 矢量线如何对应？（3）水流方向与流量大小如何直观展示？</strong>"
        "所有图均基于真实 Shapefile 线几何绘制，样点为野外 GPS 实测位置。</p>"
    ),
    "hydro": (
        "<h3>4.2 水动力：流量、流速沿河道如何分布？</h3>"
        "<p>本节展示战役期各河段的流量 Q、流速 u、水深 h 等水力变量。"
        "干流 R008 流量最大；平面箭头图表示<strong>沿河道指向下游</strong>的流动方向。"
        "断面图（图 9）在缺乏实测地形断面时，用<strong>梯形断面 + 抛物线流速分布</strong>做示意，并非现场 ADCP 测量结果。</p>"
    ),
    "carbon": (
        "<h3>4.3 碳状态与 CO₂ 通量：河水里有多少碳、向大气释放多少？</h3>"
        "<p>pCO₂ 与溶解 CO₂ 浓度 C<sub>aq</sub> 来自野外水样化验；CO₂ 逸散通量 F<sub>CO₂</sub> 由 Raymond (2012) 经验公式结合流速、坡度计算。"
        "热图横轴为日期、纵轴为河段，颜色越深表示数值越高。</p>"
    ),
    "comparison": (
        "<h3>4.4 两种方法对比：不加 AI 闭合（Baseline）vs 加入亚网格闭合（AI）</h3>"
        "<p>Baseline 只用水动力输运和气体交换公式，不额外修正源汇项；AI 方法在 Baseline 基础上学习残差闭合项 S<sub>sgs</sub>，"
        "用来弥补小尺度过程（如地下水 CO₂ 输入、局地呼吸）在大尺度模型中被“平均掉”的部分。</p>"
    ),
    "nestedcv": (
        "<h3>4.5 嵌套交叉验证（论文主指标）</h3>"
        "<p>把某一条河或某一天全部留出，在其余样本上训练 S<sub>sgs</sub> 或 k 修正，再代入与基准模型相同的输运方程，只对留出样本计分。"
        "三种闭合方案公平对比：① Baseline（S<sub>sgs</sub>=0）；② Residual-AI（学习残差源项）；③ k 修正（k<sub>eff</sub>=k<sub>emp</sub>exp(g(X))）。"
        "<strong>主文只报告这套持出样本的 C<sub>aq</sub> / F<sub>CO₂</sub> 指标。</strong>"
        "样本内 R²≈0.997 放在附录，属于同一批点既训练又预测，不能代表推广能力。</p>"
    ),
    "innovation": (
        "<h3>4.6 论文创新实验：滤波尺度、可辨识性、无量纲稀疏式</h3>"
        "<p>本节<strong>不是</strong>精度竞赛。嵌套交叉验证已经表明 Residual-AI 不能降低持出 C<sub>aq</sub> RMSE。"
        "这里回答三个方法学问题：（1）把 LES 过滤写成河网控制体粗化后，S<sub>sgs</sub> 如何随 Δx 变化？"
        "（2）同一观测下，增大源汇与减小气体交换系数 k 是否不可辨识？"
        "（3）仅用 Fr、Slope、Da、h/W 等 Π 群，能否得到可解释的稀疏式——即使持出预测仍然弱？</p>"
    ),
    "validation": (
        "<h3>4.7 样本内散点（乐观附录，非主指标）</h3>"
        "<p>散点图横轴为观测值、纵轴为模型预测值；点越靠近对角线表示预测越准。"
        "圆点按河段着色。这些图展示的是<strong>样本内拟合</strong>，R² 会偏高，请与嵌套交叉验证对照阅读，不要把附录 R² 写成论文结论。</p>"
    ),
}
