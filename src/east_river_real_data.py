"""Load East River HydroShare observations and network from downloaded files.

REAL DATA ONLY: one row per field sample (campaign dates). No forward-fill.
"""

from __future__ import annotations

import re
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from src.real_data_guard import RealDataRequiredError, require_real_data
from src.usgs_download import load_or_download_gage, q_on_date
from src.wqp_merge import merge_external_wq
from src.utils import co2_eq_concentration, k_from_k600, load_config, resolve_path, setup_logging

LOG = setup_logging("east_river_real_data")

# Upstream -> downstream order for modeled tributaries (Saccardi & Winnick 2021, GBC).
STREAM_NETWORK_ORDER = [
    "Bradley Creek",
    "Bradley Meadow",
    "Rock Creek",
    "Copper Creek",
    "Gothic Creek",
    "Quigley Creek",
    "Rustlers Gulch",
    "East River",
]

STREAM_TO_REACH = {name: f"R{i:03d}" for i, name in enumerate(STREAM_NETWORK_ORDER, start=1)}

# Published Q–elevation regression (Dataset 3 supplement, m³/s at campaign conditions).
Q_REGRESSION_TRIBUTARY = {
    "Bradley Creek": ("Bradley", 0.115845432),
    "Bradley Meadow": ("Bradley", 0.115845432),
    "Rock Creek": ("Rock", 0.044967915),
    "Copper Creek": ("Copper", 0.904498081),
    "Gothic Creek": ("Gothic", 0.008420686),
    "Quigley Creek": ("Quigley", 0.048895926),
    "Rustlers Gulch": ("Rustlers", 0.557039987),
    "East River": ("Pumphouse", 2.734495415),
}

# GNIS substring for NHD segment matching
GNIS_MATCH = {
    "Bradley Creek": "Bradley",
    "Bradley Meadow": "Bradley",
    "Rock Creek": "Rock",
    "Copper Creek": "Copper",
    "Gothic Creek": "Gothic",
    "Quigley Creek": "Quigley",
    "Rustlers Gulch": "Rustler",
    "East River": "East River",
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _supplement_dir(cfg: dict) -> Path:
    base = resolve_path(cfg, "data_raw") / "east_river" / "dic_supplement"
    candidates = list(base.rglob("watersheddataCO.csv"))
    if candidates:
        return candidates[0].parent
    return base


def hydroshare_excel_path(cfg: dict) -> Path:
    raw = resolve_path(cfg, "data_raw") / "east_river"
    candidates = list(raw.rglob("Saccardi_and_Winnick_Data.xlsx"))
    if not candidates:
        raise FileNotFoundError("Saccardi_and_Winnick_Data.xlsx not found under data_raw/east_river/")
    return candidates[0]


def real_data_available(cfg: dict) -> bool:
    try:
        hydroshare_excel_path(cfg)
        return True
    except FileNotFoundError:
        return False


def load_hydroshare_samples(cfg: dict) -> pd.DataFrame:
    """Parse HydroShare Excel — field campaign samples only."""
    path = hydroshare_excel_path(cfg)
    df = pd.read_excel(path)
    df = df.rename(
        columns={
            "Latitude ": "Latitude",
            "Datestamp": "date",
            "Temperature C": "T_C",
            "DO mg/l": "DO_mgL",
            "DIC mmol_L": "DIC_mmolL",
            "DOC mg_L": "DOC_mgL",
            "CO2 ppm corrected": "CO2_ppm_corrected",
        }
    )
    df = df[df["used in model"] == "Y"].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    # Exclude Excel serial-date corruption (e.g. CC-1 -> 1900-01-06)
    df = df[df["date"].notna() & (df["date"].dt.year >= 2015)]
    df["reach_id"] = df["Stream"].map(STREAM_TO_REACH)
    df = df[df["reach_id"].notna()]
    if df.empty:
        raise RealDataRequiredError("No valid HydroShare campaign samples after date filtering.")
    return df


def load_watershed_supplement(cfg: dict) -> pd.DataFrame:
    """Merge Dataset 3 watershed geometry / land cover by SampleID."""
    sup = _supplement_dir(cfg) / "watersheddataCO.csv"
    if not sup.exists():
        LOG.warning("watersheddataCO.csv not found; geometry from NHD only.")
        return pd.DataFrame()
    w = pd.read_csv(sup)
    w = w.rename(
        columns={
            "Elev.m": "Elevation_m",
            "T.c": "T_C_sup",
            "DO.mg/l": "DO_mgL_sup",
            "ppm.in.water": "pCO2_sup_uatm",
            "Shape_Length": "reach_length_m_sup",
            "Shape_Area": "catchment_area_m2_sup",
            "MEAN El": "mean_elevation_m",
            "MEAN GPP": "mean_gpp",
            "MAJORITY land": "landcover_code",
        }
    )
    return w


def load_stream_reach_table(cfg: dict) -> pd.DataFrame:
    """NHD stream_reach.csv (first 394 segments per published R code)."""
    nhd_dir = resolve_path(cfg, "data_raw") / "nhdplus"
    path = nhd_dir / "stream_reach.csv"
    if not path.exists():
        sup = _supplement_dir(cfg) / "stream_reach.csv"
        path = sup if sup.exists() else path
    if not path.exists():
        raise RealDataRequiredError(f"stream_reach.csv not found in {nhd_dir}")
    sr = pd.read_csv(path)
    n_seg = cfg.get("network", {}).get("nhd_segments", 394)
    sr = sr.iloc[:n_seg].copy()
    slope_path = _supplement_dir(cfg) / "slopetable.csv"
    if slope_path.exists():
        slopes = pd.read_csv(slope_path)["slope"].iloc[: len(sr)].values
        slopes = np.where(slopes <= 0, 4.07111e-15, slopes)  # per Dataset 3 R code
        sr["slope"] = slopes
    gnis_col = "GNIS_Name"
    len_col = "LengthKM"
    sr["length_m"] = pd.to_numeric(sr[len_col], errors="coerce") * 1000.0
    return sr


def stream_geometry_from_nhd(cfg: dict) -> dict[str, dict]:
    """Aggregate NHD length and median slope per modeled stream."""
    sr = load_stream_reach_table(cfg)
    gnis_col = "GNIS_Name"
    basin_slope_median = float(sr["slope"].median()) if "slope" in sr.columns else np.nan
    geom: dict[str, dict] = {}
    for stream, pattern in GNIS_MATCH.items():
        mask = sr[gnis_col].astype(str).str.contains(pattern, case=False, na=False)
        sub = sr[mask]
        if sub.empty:
            LOG.warning("No NHD GNIS match for %s; will use supplement length", stream)
            continue
        geom[stream] = {
            "length_m": float(sub["length_m"].sum()),
            "slope": float(sub["slope"].median()) if "slope" in sub.columns else basin_slope_median,
            "n_segments": len(sub),
            "length_source": "nhd_gnis",
            "slope_source": "nhd_slopetable",
        }
    return geom


def supplement_geometry_by_stream(cfg: dict) -> dict[str, dict]:
    """Reach length from Dataset 3 watersheddataCO Shape_Length (published supplement)."""
    samples = load_hydroshare_samples(cfg)
    sup = load_watershed_supplement(cfg)
    if sup.empty:
        return {}
    merged = samples.merge(sup, on="SampleID", how="left")
    out: dict[str, dict] = {}
    for stream in STREAM_NETWORK_ORDER:
        sub = merged[merged["Stream"] == stream]
        if sub.empty or "reach_length_m_sup" not in sub.columns:
            continue
        length = float(sub["reach_length_m_sup"].median())
        if length > 0:
            out[stream] = {"length_m": length, "length_source": "watersheddataCO"}
    return out


def raymond_k600_m_d(u_ms: float, slope: float) -> float:
    """
    Raymond et al. (2012) Nature Geoscience empirical k600 for streams.

    ln(k600) = 5.139 + 0.594*ln(u) + 0.403*ln(slope); k600 in m/d, u in m/s, slope m/m.
    """
    u = max(float(u_ms), 1e-4)
    s = max(float(slope), 1e-6)
    return float(np.exp(5.139 + 0.594 * np.log(u) + 0.403 * np.log(s)))


def manning_depth(Q_m3s: float, width_m: float, slope: float, n: float = 0.035) -> float:
    """Estimate depth (m) from discharge and geometry."""
    if Q_m3s <= 0 or width_m <= 0 or slope <= 0:
        return np.nan
    # Q = (1/n) * W * h^(5/3) * S^(1/2)  =>  h = (Q*n / (W*S^0.5))^(3/5)
    h = (Q_m3s * n / (width_m * (slope**0.5))) ** 0.6
    return float(np.clip(h, 0.02, 3.0))


def build_network_from_streams(cfg: dict) -> pd.DataFrame:
    """One reach per modeled stream; geometry from NHD + supplement."""
    samples = load_hydroshare_samples(cfg)
    nhd_geom = stream_geometry_from_nhd(cfg)
    sup_geom = supplement_geometry_by_stream(cfg)
    sr = load_stream_reach_table(cfg)
    basin_slope = float(sr["slope"].median())
    rows = []
    for i, stream in enumerate(STREAM_NETWORK_ORDER):
        rid = STREAM_TO_REACH[stream]
        sub = samples[samples["Stream"] == stream]
        lon = float(sub["Longitude"].median()) if len(sub) else np.nan
        lat = float(sub["Latitude"].median()) if len(sub) else np.nan
        if np.isnan(lon) or np.isnan(lat):
            raise RealDataRequiredError(f"No coordinates for stream {stream}")

        g = nhd_geom.get(stream, {})
        sg = sup_geom.get(stream, {})
        length_m = g.get("length_m") or sg.get("length_m")
        length_source = g.get("length_source") or sg.get("length_source", "unknown")
        slope = g.get("slope", basin_slope)
        slope_source = g.get("slope_source", "nhd_slopetable_basin_median")
        if not length_m or length_m <= 0:
            raise RealDataRequiredError(
                f"Missing reach length for {stream}. Need NHD GNIS or watersheddataCO Shape_Length."
            )
        if slope is None or np.isnan(slope) or slope <= 0:
            raise RealDataRequiredError(f"Missing slope for {stream} from slopetable.csv.")

        # Width from sample spread (m) or conservative default from NHD segment count
        if len(sub) >= 2:
            lon_span = (sub["Longitude"].max() - sub["Longitude"].min()) * 111_000 * np.cos(np.radians(lat))
            width_m = float(np.clip(max(lon_span / max(len(sub), 1), 2.0), 2.0, 15.0))
        else:
            width_m = 5.0

        upstream = STREAM_TO_REACH[STREAM_NETWORK_ORDER[i - 1]] if i > 0 else None
        downstream = (
            STREAM_TO_REACH[STREAM_NETWORK_ORDER[i + 1]] if i < len(STREAM_NETWORK_ORDER) - 1 else None
        )
        rows.append(
            {
                "reach_id": rid,
                "stream_name": stream,
                "upstream_id": upstream,
                "downstream_id": downstream,
                "length_m": length_m,
                "slope": slope,
                "width_m": width_m,
                "area_m2": length_m * width_m,
                "forest_frac": np.nan,
                "wetland_frac": np.nan,
                "meadow_frac": np.nan,
                "lon": lon,
                "lat": lat,
                "nhd_segments": g.get("n_segments", 0),
                "length_source": length_source,
                "slope_source": slope_source,
            }
        )
    return pd.DataFrame(rows)


def _load_east_river_usgs(cfg: dict, samples: pd.DataFrame) -> pd.DataFrame:
    """USGS 09112500 daily Q for campaign window."""
    dmin = samples["date"].min().strftime("%Y-%m-%d")
    dmax = samples["date"].max().strftime("%Y-%m-%d")
    return load_or_download_gage(cfg, "09112500", dmin, dmax)


def assign_reach_discharge(
    stream: str,
    date: pd.Timestamp,
    q_east_daily: pd.DataFrame,
) -> tuple[float, str]:
    """
    Reach discharge (m³/s) and provenance label.

    East River: USGS 09112500 on sample date.
    Tributaries: published synoptic Q from `Q elivation regreshion.csv` (campaign-condition
    CMS). watersheddataCO has no per-sample Q, so gage-ratio scaling is NOT applied —
    that would invent a daily tributary hydrograph that was never measured.
    """
    q_east_date = q_on_date(q_east_daily, date)
    if q_east_date is None:
        raise RealDataRequiredError(f"No USGS 09112500 discharge on {date.date()}")

    if stream == "East River":
        return q_east_date, "usgs:09112500"

    _, q_ref = Q_REGRESSION_TRIBUTARY[stream]
    return float(q_ref), "supplement:Q_elevation_regression_synoptic"


def build_campaign_observations(cfg: dict) -> pd.DataFrame:
    """One row per HydroShare sample — actual campaign dates only."""
    require_real_data(cfg, "build_campaign_observations")
    network = build_network_from_streams(cfg)
    samples = load_hydroshare_samples(cfg)
    supplement = load_watershed_supplement(cfg)
    net_lookup = network.set_index("reach_id")
    q_east = _load_east_river_usgs(cfg, samples)

    if not supplement.empty:
        samples = samples.merge(supplement, on="SampleID", how="left", suffixes=("", "_sup"))

    c_eq_atm = cfg["baseline"].get("c_eq_pco2_uatm", 410.0)
    records = []
    for _, row in samples.iterrows():
        rid = row["reach_id"]
        stream = row["Stream"]
        reach = net_lookup.loc[rid]
        date = pd.Timestamp(row["date"]).normalize()

        if pd.isna(row["CO2_ppm_corrected"]):
            LOG.warning("Skipping %s: missing pCO2", row.get("SampleID"))
            continue

        temp = float(row["T_C"])
        pco2 = float(row["CO2_ppm_corrected"])
        qt, q_src = assign_reach_discharge(stream, date, q_east)
        width = float(reach["width_m"])
        slope = float(reach["slope"])
        h = manning_depth(qt, width, slope)
        if np.isnan(h):
            raise RealDataRequiredError(f"Cannot compute depth for {row.get('SampleID')}")
        u = qt / (width * h)

        k600 = raymond_k600_m_d(u, slope)
        k_co2 = k_from_k600(k600, temp)
        c_eq = co2_eq_concentration(c_eq_atm, temp)
        c_aq_obs = co2_eq_concentration(pco2, temp)

        length_m = float(reach["length_m"])
        if "reach_length_m_sup" in row and pd.notna(row["reach_length_m_sup"]):
            length_m = float(row["reach_length_m_sup"])

        records.append(
            {
                "date": date,
                "reach_id": rid,
                "stream_name": stream,
                "sample_id": row.get("SampleID"),
                "Q_m3s": qt,
                "Q_source": q_src,
                "u_ms": float(u),
                "h_m": h,
                "W_m": width,
                "L_m": length_m,
                "T_C": temp,
                "DOC_mgL": float(row["DOC_mgL"]) if pd.notna(row.get("DOC_mgL")) else np.nan,
                "DIC_mmolL": float(row["DIC_mmolL"]) if pd.notna(row.get("DIC_mmolL")) else np.nan,
                "DO_mgL": float(row["DO_mgL"]) if pd.notna(row.get("DO_mgL")) else np.nan,
                "pH": float(row["pH"]) if pd.notna(row.get("pH")) else np.nan,
                "Alk_ueqL": np.nan,
                "Slope": slope,
                "PAR_umolm2s": np.nan,
                "N_uM": np.nan,
                "P_uM": np.nan,
                "forest_frac": np.nan,
                "wetland_frac": np.nan,
                "meadow_frac": np.nan,
                "pCO2_uatm": pco2,
                "k600_m_d": k600,
                "k_CO2_m_d": k_co2,
                "k600_method": "raymond_2012",
                "C_aq_obs_mol_m3": c_aq_obs,
                "C_eq_mol_m3": c_eq,
                "S_sgs_true_mol_m2d": np.nan,
                "is_campaign_sample": True,
                "data_source": "hydroshare_saccardi_winnick",
                "lon": float(row["Longitude"]),
                "lat": float(row["Latitude"]),
            }
        )

    obs = pd.DataFrame(records)
    if obs.empty:
        raise RealDataRequiredError("No campaign observations built from HydroShare samples.")
    LOG.info(
        "Campaign observations: n=%d, dates=%s–%s, reaches=%s",
        len(obs),
        obs["date"].min().date(),
        obs["date"].max().date(),
        sorted(obs["reach_id"].unique()),
    )
    return obs


def export_nhdplus_network_csv(cfg: dict) -> Path | None:
    """Build reach table from East_River_Lines.shp (reference topology)."""
    nhd_dir = resolve_path(cfg, "data_raw") / "nhdplus"
    shp = nhd_dir / "East_River_Lines.shp"
    if not shp.exists():
        return None
    gdf = gpd.read_file(shp)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)
    gdf = gdf.sort_values("OBJECTID").reset_index(drop=True)
    sr = load_stream_reach_table(cfg)
    slope_by_oid = {}
    obj_col = [c for c in sr.columns if "OBJECT" in c.upper()][0]
    for _, r in sr.iterrows():
        oid_val = r[obj_col]
        if pd.notna(oid_val):
            slope_by_oid[int(oid_val)] = r.get("slope", np.nan)

    rows = []
    prev_id = None
    for _, row in gdf.iterrows():
        oid = int(row["OBJECTID"])
        rid = f"NHD_{oid:04d}"
        length_m = float(row.get("Shape_Leng", row.get("LengthKM", 0.5) * 1000))
        if length_m <= 0:
            length_m = float(row.geometry.length) * 111_000
        rows.append(
            {
                "reach_id": rid,
                "upstream_id": prev_id,
                "length_m": max(length_m, 50.0),
                "width_m": np.nan,
                "slope": slope_by_oid.get(oid, np.nan),
                "NHDPlusID": row.get("NHDPlusID"),
                "GNIS_Name": row.get("GNIS_Name"),
            }
        )
        prev_id = rid
    out = pd.DataFrame(rows)
    out_path = nhd_dir / "east_river_flowlines_simplified.csv"
    out.to_csv(out_path, index=False)
    return out_path


def write_real_dataset(cfg: dict) -> dict[str, Path]:
    """Write HydroShare-based network and campaign observations to data_proc."""
    require_real_data(cfg, "write_real_dataset")
    proc = resolve_path(cfg, "data_proc")
    proc.mkdir(parents=True, exist_ok=True)
    network = build_network_from_streams(cfg)
    obs = build_campaign_observations(cfg)
    obs, wqp_stats = merge_external_wq(obs, cfg)

    net_path = proc / "network_edges.csv"
    obs_path = proc / "reach_daily_observations.csv"
    network.to_csv(net_path, index=False)
    obs.to_csv(obs_path, index=False)

    nhd_path = export_nhdplus_network_csv(cfg)
    samples = load_hydroshare_samples(cfg)
    prov_rows = [
        {
            "component": "observations",
            "source": "hydroshare:9f907b46baa848e180c49339d605bf31",
            "label": f"Saccardi_and_Winnick_Data.xlsx ({len(obs)} campaign samples, no forward-fill)",
            "synthetic_fallback": False,
            "n_rows": len(obs),
            "date_min": str(obs["date"].min().date()),
            "date_max": str(obs["date"].max().date()),
        },
        {
            "component": "network",
            "source": "hydroshare_supplement:2a213299 + NHD stream_reach.csv",
            "label": "8-reach tributary chain; length/slope from NHD+slopetable",
            "synthetic_fallback": False,
            "n_rows": len(network),
        },
        {
            "component": "discharge_east_river",
            "source": "usgs:09112500",
            "label": "East River at Almont daily Q on sample dates (dataretrieval)",
            "synthetic_fallback": False,
        },
        {
            "component": "discharge_tributaries",
            "source": "supplement:Q_elevation_regression_synoptic",
            "label": "Published synoptic tributary Q (Q elivation regreshion.csv); no daily gage",
            "synthetic_fallback": False,
        },
        {
            "component": "gas_transfer_k",
            "source": "raymond_2012",
            "label": "k600 from Raymond et al. (2012) ln(k600)=5.139+0.594ln(u)+0.403ln(slope)",
            "synthetic_fallback": False,
        },
        {
            "component": "nhdplus_lines",
            "source": str(nhd_path) if nhd_path else "missing",
            "label": "East_River_Lines.shp from Dataset_3.zip (393 segments in R code)",
            "synthetic_fallback": nhd_path is None,
        },
        {
            "component": "wqp",
            "source": "wqp_site_results_20190801_20190815.csv + USGS Samples API",
            "label": (
                f"Per-site WQP Aug 2019 + USGS 09112500/09111250; exact site-day merge: "
                f"{wqp_stats.get('samples_enriched', 0)}/{len(obs)} samples enriched"
            ),
            "synthetic_fallback": False,
            "n_rows": wqp_stats.get("wqp_rows_loaded", 0),
        },
    ]
    prov = pd.DataFrame(prov_rows)
    prov_path = proc / "data_provenance.csv"
    prov.to_csv(prov_path, index=False)
    return {"network": net_path, "observations": obs_path, "provenance": prov_path}
