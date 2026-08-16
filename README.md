# 河流碳输运 + AI 亚网格闭合（East River MVP）

基于 East River 案例的一维河网 CO₂ / DIC 输运基线模型，并用机器学习学习亚网格闭合项 \(S_{sgs}\) 或 \(k\) 修正。灵感来自 *The Innovation* 稿件中 AI 跨融合河网碳输运框架与 Saccardi & Winnick (2021, GBC) 的河网 CO₂ 模型。

**论文定位（诚实）：** 方法学贡献是 LES 式过滤 + 嵌套 CV 协议 + \(S_{sgs}\)–\(k\) 的 **practical equifinality**。嵌套 CV 下 Residual-AI **未能**优于 Baseline（C RMSE 0.057 vs 0.028）。详见 `docs/PAPER_PLAN.md` 与 `docs/ENGINEERING_NOTES.md`。

## 项目目标

1. **基线（Phase 1 — CO₂）：** reach 尺度质量平衡  
   \(\frac{d(V_i C_i)}{dt} = \sum Q_{in} C_{in} - Q_{out} C_i + S_{gw} + S_{bio} + S_{sgs} - A_i k_i (C_i - C_{eq})\)
2. **AI 亚网格：** 从基线–观测残差学习 \(S_{sgs}=f_\theta(X)\) 或 \(k_{eff}=k_{emp}\exp(g_\theta(X))\)
3. **验证：** 跨河段、跨日期比较 baseline / residual-AI / dimensionless-AI（**持出嵌套 CV 为主指标**）

## 目录结构

```
configs/east_river.yaml    # 路径、物理参数、AI 超参
data_raw/                  # 原始数据（HydroShare、NHDPlus、WQP）
data_proc/                 # 处理后网络、观测、模型输出
src/01–15_*.py             # 流水线各阶段
docs/PAPER_PLAN.md         # 论文计划
docs/ENGINEERING_NOTES.md  # 冻结数字与架构决策
notebooks/                 # 复现与分析笔记本
results/figures|tables/    # 图表与指标
run_pipeline.py            # 一键运行
```

## 环境配置

```bash
cd d:\Projects\20260611-river-carbon-transport
# 需要 CPython 3.10–3.12（PyPy 无 pandas 轮子）
py -3.12 -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## 运行方式

### 一键全流程（推荐）

```bash
python run_pipeline.py
```

从第 N 阶段续跑：

```bash
python run_pipeline.py --from-stage 3
```

### 分阶段运行

| 阶段 | 命令 | 说明 |
|------|------|------|
| 1 | `python src/01_fetch_water_quality.py` | 拉取 HydroShare；真实数据缺失则失败（无合成回退） |
| 2 | `python src/02_build_network.py` | 构建河网拓扑（NHDPlus） |
| 3 | `python src/03_baseline_transport.py` | 基线 CO₂ 输运（\(S_{sgs}=0\)） |
| 4 | `python src/04_estimate_k.py` | 气体交换系数 \(k\) 估算 |
| 5 | `python src/05_compute_residual_sgs.py` | 计算亚网格残差 + 无量纲特征 |
| 6 | `python src/06_train_sgs_model.py` | LASSO / ElasticNet / RF / XGBoost / MLP |
| 7 | `python src/07_coupled_prediction.py` | 耦合 AI 闭合的预测（样本内，附录） |
| 8 | `python src/08_validate_flux_budget.py` | RMSE、bias、通量预算、作图 |
| 9–11 | GIS / 断面可视化 | 河网线图、quiver、2D 断面 |
| 12 | `python src/12_nested_cv_transport.py` | **论文主精度表**（嵌套 CV） |
| 13–15 | 滤波尺度 / 可辨识性 / 无量纲稀疏 | 方法学创新实验 |

论文表汇总：`python scripts/build_paper_tables.py`  
报告：`python scripts/generate_report.py`

## 数据要求

| 数据源 | 资源 | 用途 |
|--------|------|------|
| East River HydroShare | [9f907b46…](https://www.hydroshare.org/resource/9f907b46baa848e180c49339d605bf31/) | 溶质化学 / pCO₂ |
| Winnick & Saccardi DIC 补充 | [2a213299…](https://www.hydroshare.org/resource/2a2132999fb84214aad0596783812db2/) | DIC、shp、坡度、同步 Q |
| NHDPlus HR | USGS | 河网矢量 → `data_raw/nhdplus/` / `nhdplus_hr/` |
| WQP / USGS | waterqualitydata.us | DOC、pH、温度、DO、营养盐（同日合并现为 0/120） |

NHDPlus 需包含列：`reach_id`, `upstream_id`, `length_m`, `width_m`, `slope`。

完整出处见 **REAL_DATA_AUDIT.md**。

## 无量纲特征

- Fr = u/√(gh)；Re = uh/ν；Pe = uL/D；Da ≈ kτ/h  
- h/W；DOC/DIC；kτ/h

## 输出

- `data_proc/baseline_model_output.csv` — 基线浓度与 F_CO₂  
- `data_proc/ai_coupled_output.csv` — AI 耦合结果  
- `data_proc/models/` — 训练好的模型  
- `results/tables/nested_cv_metrics.csv` — **主指标** RMSE、bias、通量  
- `results/tables/paper_main_results.csv` — 论文友好汇总表  
- `results/figures/` — 散点图、河段通量、嵌套 CV 图  
- `report.html` / `report.md` — 自包含验证报告

## 参考文献

- Saccardi & Winnick (2021), *Global Biogeochemical Cycles* — East River 河网 CO₂  
- Raymond et al. (2012) — 河流 \(k_{600}\) 经验式  
- The Innovation — AI cross-fusion for river carbon transport（方法灵感）

## 局限

- Phase 1 仅 CO₂；DIC/完整碳预算与 CH₄ 为后续  
- n=120 战役样点；R001/R006/R007 各 n=1 仅示意  
- Residual-AI 嵌套 CV **不优于** Baseline；勿把样本内 \(R^2\) 当主结论  
- NHDPlus 自动下载未实现（需本地 Shapefile/GPKG）  
- SINDy 符号回归未安装成功时改用 LASSO（见 stage 15）

## 许可证

研究用途；引用上述文献与 HydroShare 数据 DOI。

---

### One-command setup (Windows)

```powershell
.\setup_env.ps1
.\.venv\Scripts\Activate.ps1
python run_pipeline.py
```

If `pip install -r requirements.txt` fails with IncompleteRead on a mirror, `setup_env.ps1` uses https://pypi.org/simple.

### Data download status (2026-06-11)

| Item | Status |
|------|--------|
| HydroShare 9f907b46 (Saccardi and Winnick Excel) | Downloaded via hsapi |
| HydroShare 2a213299 (R scripts + Dataset_3.zip) | Downloaded under `data_raw/east_river/dic_supplement/` |
| WQP HUC 14020001 | `wqp/wqp_huc14020001_results.csv` (~10 MB) |
| USGS 09111250 discharge (2019 daily) | `data_raw/usgs/` |
| NHDPlus East River lines | `East_River_Lines.shp` in `data_raw/nhdplus/` |

Manifest: `data_raw/DOWNLOAD_MANIFEST.md`. See **REAL_DATA_AUDIT.md** for full provenance.

### Data integrity policy (real-data-only)

- **`data_policy.real_data_only: true`** (default) — pipeline **exits with error** if `Saccardi_and_Winnick_Data.xlsx` is missing.
- **No synthetic fallback** — `synthetic_data.py` is not invoked by the pipeline.
- **Campaign samples only** — one row per field sample (`is_campaign_sample: true`); daily forward-fill is disabled.
- **Discharge:** USGS 09112500 (East River at Almont) on sample dates; tributaries use published synoptic Q from `Q elivation regreshion.csv` (**no gage-ratio scaling** of a fake daily hydrograph).
- **Gas transfer k:** Raymond et al. (2012) empirical formula from measured u and NHD slope — not arbitrary constants.
- **Provenance:** every run writes `data_proc/data_provenance.csv`; synthetic fallback flags cause stage 02 to fail.
- **Honest limitations:** n = 120 samples, 10 dates, partial DIC/DOC; nested CV is the paper metric (in-sample AI \(R^2\) is optimistic appendix-only).
