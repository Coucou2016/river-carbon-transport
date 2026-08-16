# Real Data Audit — East River CO₂ Transport Pipeline

**Audit date:** 2026-08-15 (paper-innovation experiments: filter-scale, identifiability, dimensionless sparse)  
**Policy:** `data_policy.real_data_only: true` — pipeline **fails** if HydroShare Excel is missing; no synthetic fallback.

---

## Executive summary

| Item | Status |
|------|--------|
| HydroShare field samples | **REAL** — 120 campaign rows, 10 dates, 8 reaches |
| Forward-filled daily panel | **REMOVED** — campaign samples only |
| Synthetic data fallback | **DISABLED** |
| Discharge | **REAL** — USGS 09112500 on sample dates for R008; tributaries use published synoptic Q (no gage-ratio scaling) |
| Gas transfer k | **REAL** — Raymond et al. (2012) |
| Network geometry | **REAL** — East_River_Lines.shp + NHDPlus HR HU4 1402 HUC 14020001 extract (8212 flowlines) |
| WQP merge to samples | **0/120** — not re-attempted |
| StreamPULSE | **MISS** — no East River / Gothic / Coal Creek sites on portal |
| AI validation | **Nested CV on coupled C_aq / F_CO2** — in-sample R² is appendix-only |
| Filter-scale S_sgs | **REAL** — 120 samples snapped to coarsened NHDPlus HR corridor (536 lines) |
| CONUS_carbon | **STRUCTURE ONLY** — GitHub clone succeeded; continental inputs not bundled |

**Campaign sample size:** n = **120** (unique field samples), dates **2019-08-02 to 2019-08-11**, reaches **R001–R008**.
Actual n by reach: R001=1, R002=3, R003=15, R004=24, R005=17, R006=1, R007=1, R008=58.
R001/R006/R007 are **schematic only** (n=1), not equal evidence with R008.

---

## Data sources

### 1. HydroShare — Saccardi & Winnick (2021)

| Field | Value |
|-------|-------|
| Resource ID | `9f907b46baa848e180c49339d605bf31` |
| URL | https://www.hydroshare.org/resource/9f907b46baa848e180c49339d605bf31/ |
| File | `data_raw/east_river/east_river/Saccardi_and_Winnick_Data.xlsx` |
| Download | hsapi — **success** |
| Used columns | Stream, SampleID, Datestamp, Lat/Lon, T, pH, DO, CO₂ ppm corrected, DIC, DOC |
| Filter | `used in model == Y`, year ≥ 2015 (excludes 1 corrupted date: CC-1 → 1900-01-06) |

### 2. HydroShare — DIC supplement (Dataset 3)

| Field | Value |
|-------|-------|
| Resource ID | `2a2132999fb84214aad0596783812db2` |
| URL | https://www.hydroshare.org/resource/2a2132999fb84214aad0596783812db2/ |
| Files | `Dataset_3.zip` → `watersheddataCO.csv`, `stream_reach.csv`, `slopetable.csv`, `Q elivation regreshion.csv`, `East_River_Lines.shp` |
| Download | hsapi — **success** |

### 3. USGS discharge

| Gage | Name | Use | Download |
|------|------|-----|----------|
| **09112500** | East River at Almont, CO | Direct Q on sample dates for East River reach (R008) | **success** via `dataretrieval` → `data_raw/usgs/09112500_discharge_daily_2019.csv` (10 daily values, Aug 2–11 2019) |
| 09111250 | Coal Creek near Crested Butte | Cached 2019 daily (`data_raw/usgs/09111250_coal_creek_discharge_daily_2019.csv`); **not used** as universal proxy anymore | Pre-existing |

**Tributary Q (R001–R007):** Published `Q (CMS)` from `Q elivation regreshion.csv` used **as campaign synoptic Q** (no USGS daily-ratio scaling). watersheddataCO has **no per-sample Q**. Remaining uncertainty: no tributary hydrograph, one published value per stream.

### 4. NHDPlus / stream network

| File | Rows | Use |
|------|------|-----|
| `data_raw/nhdplus/stream_reach.csv` | 8001 (first **394** used per R code) | Length, GNIS names, NHDPlusID |
| `data_raw/nhdplus/slopetable.csv` (supplement) | 394 slopes | DEM-derived reach slope |
| `data_raw/nhdplus/East_River_Lines.shp` | 393 features | **GIS line maps (stage 10)** — positional merge with `stream_reach.csv` rows 1–393 |
| `data_proc/gis_reach_line_mapping.csv` | 393 rows | Per-segment reach assignment (GNIS + centroid fallback) |
| `data_proc/reach_chainage.csv` | 393 rows | Along-network chainage for stage 11 longitudinal profiles |
| `watersheddataCO.csv` | 152 samples | `Shape_Length` where GNIS match missing |

**GIS vector provenance (2026-08-14):** USGS NHDPlus HR HU4 1402 GeoPackage downloaded (ScienceBase `NHDPLUS_H_1402_HU4_20220414_GPKG.zip`, 284,145,677 bytes). HUC 14020001 subset: **8212** flowlines, **2016** named GNIS, saved as `data_raw/nhdplus_hr/nhdplus_hr_huc14020001_flowlines.gpkg`. Study maps still use HydroShare `East_River_Lines.shp` (393 segments) joined to HR by ReachCode/Permanent_Identifier.

**Reach-to-line mapping (stage 10, after HR enrich):**

| Method | Segments | Streams |
|--------|----------|---------|
| GNIS substring match | 85 | East River (46), Copper Creek (23), Rock Creek (10), Quigley Creek (6) |
| Nearest campaign GPS sample | 308 | Bradley, Gothic, Rustlers, unnamed tributaries |

GNIS count rose 75→85 (Rock Creek named via HR join). Centroid fallback replaced by nearest of 120 GPS samples. Sample snap median distance **8.5 m** (`data_proc/sample_snap_centerline.csv`).

**Cross-section assumptions (stage 11):** Trapezoid (bottom width = campaign mean `W_m`, depth = mean `h_m`, side slope 1:1); velocity u(y,z) = parabolic vertical × uniform lateral; chainage from `network_edges.length_m` cumulative.

**GNIS match status:**

| Stream | Length source | Slope source |
|--------|---------------|--------------|
| Copper Creek | NHD (23 segments) | NHD slopetable |
| Quigley Creek | NHD (6 segments) | NHD slopetable |
| East River | NHD (46 segments) | NHD slopetable |
| Bradley Creek, Bradley Meadow, Rock Creek, Gothic Creek, Rustlers Gulch | Supplement `Shape_Length` | Basin median slopetable (no GNIS name match in NHD extract) |

### 5. WQP

| File | Status |
|------|--------|
| `wqp_huc14020001_results.csv` | Legacy HUC-wide pull (~10.8 MB); **no lat/lon** — not used for merge |
| `wqp_stations_huc14020001.csv` | **579** monitoring locations (East River HUC bbox) |
| `wqp_site_results_20190801_20190815.csv` | **Downloaded 2026-06-11** — per-site WQP Result/search, 2019-08-01–15; **441** rows from **11** sites |
| `wqp_site_download_errors.json` | **[]** (579/579 site queries completed after TLS retries) |
| `data_raw/usgs/09112500_water_quality_samples_201908.csv` | **47** rows via `dataretrieval.waterdata.get_samples` |
| `data_raw/usgs/09111250_water_quality_samples_201908.csv` | **58** rows via `dataretrieval.waterdata.get_samples` |
| Bbox result query | **FAILED** (historical HTTP 400) — superseded by per-site pull |
| Merged to campaign samples | **0/120 enriched** — 9 samples within 200 m of a listed station, but **no exact calendar-date + monitoring-location** overlap with target analytes (Alk, N, P, DOC gaps remain NaN) |

---

## What is real vs interpolated

| Variable | Status | Notes |
|----------|--------|-------|
| pCO₂, pH, T, DO | **Measured** | HydroShare Excel |
| DIC, DOC | **Measured** (partial) | 41/120 non-null; 79 samples lack lab DIC/DOC |
| Alkalinity, PAR, N, P | **Missing** | Not in HydroShare; WQP/USGS pull succeeded but **0** exact site-day merges |
| Land cover fractions | **Missing** | Not extracted from supplement rasters |
| Q (East River) | **Gaged** | USGS 09112500 daily |
| Q (tributaries) | **Published synoptic** | `Q elivation regreshion.csv` campaign-condition CMS; **no** USGS daily-ratio scaling |
| k600 | **Empirical** | Raymond (2012) from u, slope — not direct gas flux measurement |
| Daily forward-fill | **REMOVED** | Prior pipeline expanded 10 campaign days × 8 reaches = 80 rows with stale chemistry |

---

## Algorithm choices

| Step | Method | Citation |
|------|--------|----------|
| Baseline transport | Quasi-steady 1D advection–evasion balance | Saccardi & Winnick (2021) framework |
| k600 | ln(k600) = 5.139 + 0.594 ln(u) + 0.403 ln(slope) | Raymond et al. (2012) Nature Geoscience |
| S_sgs residual | Paired sample-level model–obs closure | Same date + reach + sample_id |
| AI training | Leave-one-reach-out & leave-one-date-out CV | No random split (avoids leakage across sparse campaign) |
| k correction | log-space XGBoost; k > 0 via exp | Physics constraint |

---

## Validation metrics (honest) — nested CV on coupled transport

Main paper metrics are **held-out C_aq and F_CO2** after training S_sgs / k-correction on other reaches or dates, then plugging predictions into the same physics as stages 03/07. In-sample R² is appendix-only.

From `results/tables/nested_cv_metrics.csv` (leave-one-reach-out, n=120):

### Concentration (C_aq)

| Scheme | Model | RMSE | MAE | Bias | R² |
|--------|-------|------|-----|------|-----|
| Baseline (S_sgs=0) | — | 0.0284 | 0.0132 | −0.0132 | −0.26 |
| Residual-AI | MLP | **0.0573** | 0.0326 | +0.0177 | −4.16 |
| Residual-AI | Random Forest | 0.0745 | 0.0301 | +0.0180 | −7.72 |
| k-correction | XGBoost | 0.0244 | 0.0046 | −0.0046 | +0.06 |
| Residual-AI in-sample (appendix) | XGBoost | 0.0013 | 0.0006 | +0.0005 | 0.997 |

### Flux (F_CO2 vs k_emp × C_obs proxy)

| Scheme | F RMSE | F total (mol/m²/d) | vs proxy (~120) |
|--------|--------|--------------------|-----------------|
| Baseline | 1.73 | 3.24 | strongly under |
| Residual-AI MLP | 1.56 | 69.5 | closer in magnitude, worse C |
| k-correction | 1.78 | **0.03** | flux collapsed (k driven toward 0) |

**Conclusion:** Residual-AI does **not** beat Baseline on held-out C_aq. k-correction slightly lowers C RMSE by shrinking k, which collapses F_CO2 — not a successful flux closure. No scheme simultaneously improves held-out concentration and physically consistent evasion.

Subgroups (`results/tables/subgroup_metrics.csv`): R008 n=58 is the only well-sampled reach; R004+R006 n=25 (mostly Copper); 1-sample reaches R001/R006/R007 are schematic.

---

## Code changes enforcing real-data-only

1. `configs/east_river.yaml` — `data_policy.real_data_only: true`; removed `synthetic.enabled`
2. `src/real_data_guard.py` — fail-loud guards
3. `src/01_fetch_water_quality.py` — no synthetic fallback
4. `src/02_build_network.py` — requires stage-01 network; no synthetic
5. `src/east_river_real_data.py` — campaign samples only; Raymond k; USGS Q
6. `src/05_compute_residual_sgs.py` — paired merge on `sample_id`
7. `src/06_train_sgs_model.py` — LOO-reach / LOO-date CV

---

## Download failures & manual steps

### WQP per-site retry (2026-06-11)

Previous failure: `Client network socket disconnected before secure TLS connection was established` (transient SSL/TLS).

**Automated retry (3 attempts, 180 s timeout, urllib3 backoff):** `scripts/retry_wqp_download.py` → `src/wqp_download.py`

```
579 MonitoringLocationIdentifier queries × Result/search
  startDateLo=08-01-2019, startDateHi=08-15-2019
  → 11 sites with data, 441 result rows, 0 hard failures
USGS Samples API: USGS-09112500 (47 rows), USGS-09111250 (58 rows)
```

**Merge rule:** `src/wqp_merge.py` — nearest station ≤ 200 m, same `ActivityStartDate` / `Activity_StartDate`, fill **only NaN** fields (no forward-fill).

**Manual fallback (if TLS fails again):**

1. Open https://www.waterqualitydata.us/ → Result search.
2. For each `MonitoringLocationIdentifier` in `data_raw/wqp/wqp_stations_huc14020001.csv`, download CSV for 2019-08-01–2019-08-15.
3. Concatenate to `data_raw/wqp/wqp_site_results_20190801_20190815.csv` (include `MonitoringLocationIdentifier`, `ActivityStartDate`, `CharacteristicName`, `ResultMeasureValue`, units).
4. USGS: https://waterdata.usgs.gov/download-samples/ — sites 09112500, 09111250, same date window → save under `data_raw/usgs/`.

### WQP bbox results (HTTP 400)

```
GET https://www.waterqualitydata.us/data/Result/search?latmin=38.85&latmax=38.95&longmin=-107.05&longmax=-106.95&...
→ HTTP 400 (empty body)
```

**Manual workaround:** Use https://www.waterqualitydata.us/ → draw bbox → export Results with MonitoringLocation coordinates, or query by `siteid` from `data_raw/wqp/wqp_stations_huc14020001.csv` (211 sites in bbox).

### HydroShare full bagit

Full resource bag requires browser login. hsapi downloads individual public files — **sufficient** for this pipeline.

### Per-tributary USGS gages

No dedicated daily gages for Bradley, Rock, Gothic, etc. in downloaded data. Tributary Q uses published elevation–area regression (supplement) — **documented limitation**.

---

## Blockers requiring user action

1. **WQP chemistry merge** — Per-site download done; need co-located monitoring on **same dates** as campaign (Aug 2–11) or alternate lab sources for Alk/N/P.
2. **DIC/DOC gaps** — 79/120 samples missing lab DIC/DOC in Excel; no fabrication applied.
3. **Tributary discharge** — Install temporary gages or use published synoptic Q only (no daily tributary gage in dataset).
4. **Out-of-sample AI transport** — Nested CV implemented (`src/12_nested_cv_transport.py`). Residual-AI does not beat baseline on held-out C_aq; k-correction collapses flux. Filter-scale / identifiability / dimensionless sparse experiments added (`src/13_*.py`–`15_*.py`) as the paper methods contribution.

---

### NHDPlus HR HU4 1402 (2026-08-14)

| Attempt | URL | Result |
|---------|-----|--------|
| USGS S3 GPKG | https://prd-tnm.s3.amazonaws.com/StagedProducts/Hydrography/NHDPlusHR/VPU/Current/GPKG/NHDPLUS_H_1402_HU4_20220414_GPKG.zip | **SUCCESS** after resume — 284,145,677 bytes; HUC 14020001 extract 8212 flowlines |
| Intermediate stall | same URL | curl stalled ~0 B/s after ~200 MB; incomplete `GPKG.zip` (239,679,856) was **not** a valid zip; complete bytes were in `.part` |
| USGS S3 GDB | https://prd-tnm.s3.amazonaws.com/StagedProducts/Hydrography/NHDPlusHR/VPU/Current/GDB/NHDPLUS_H_1402_HU4_20220414_GDB.zip | **SUCCESS** — 123,681,476 bytes (full HEAD size) |
| ArcGIS REST | https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/3/query `ReachCode LIKE '14020001%'` | **FAILED** — `ReadTimeout` (25 s) on hydro.nationalmap.gov:443 |

Fallback if extract had failed: `East_River_Lines.shp` (already NHDPlus HR Resolution=High). Extract succeeded; mapping still uses the 393-segment study shapefile + HR GNIS join.

### StreamPULSE (2026-08-14)

| Attempt | Result |
|---------|--------|
| `GET https://data.streampulse.org/query_available_data?type=site_data` | **HTTP 500** Internal Server Error |
| `GET https://data.streampulse.org/download` site list | **SUCCESS** — 306 sites parsed, 30 Colorado sites |
| Keywords East River / Gothic / Coal Creek / Crested Butte / Gunnison / Almont | **0 matches** |

No StreamPULSE time series downloaded. Evidence: `data_raw/streampulse/streampulse_site_search.json`. **Not retried as a main path on 2026-08-15.**

### Fluvial-UMass/CONUS_carbon (2026-08-15)

| Attempt | Result |
|---------|--------|
| `git clone --depth 1 https://github.com/Fluvial-UMass/CONUS_carbon.git` | **SUCCESS** → `data_raw/conus_carbon/` (R `targets` pipeline, HUC4 lookup tables) |
| Continental input rasters / Rocher-Ros 2019 chemistry | **NOT in this repo** (README: stored in a separate public data path) |
| Use in this project | Structure / HUC4 topology check only. **Not** a second East River field campaign. East River sits in HUC4 1402 in their lookup; no CONUS fluxes were substituted for the 120 HydroShare samples. |

Reproduction baseline remains Saccardi & Winnick (2021) 1D/network interpretation of the same HydroShare observations.

### PySINDy (2026-08-15)

`pip install pysindy` failed (`IncompleteRead` / broken connection). Dimensionless closure uses sklearn `StandardScaler` + `Lasso` on Π features. No fabricated SINDy equation.

### Filter-scale lattice (2026-08-15)

NHDPlus HR HUC 14020001 gpkg clipped to a 1.5 km buffer of `East_River_Lines.shp`: **536** flowlines (median length 326 m). Samples snapped to coarsened cells at native / 2× / 4× / study-reach scales. Residual recomputed from the same 120 real samples. Study-reach scale had **6** cells with samples (HR reach assignment did not populate all 8 logical reaches) — reported as-is.

---

## File manifest

See `data_raw/DOWNLOAD_MANIFEST.md` and `data_proc/data_provenance.csv` for machine-readable provenance.
