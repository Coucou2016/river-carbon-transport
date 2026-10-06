#!/usr/bin/env python3
"""
Grouped leave-one-reach/date-out CV of coupled CO2 transport closures.

  1. Routes through the REAL directed tree (real_network.route_steady_state)
     with flow-weighted confluence mixing and a C_eq headwater boundary.
  2. k_needed is built INSIDE each fold from training reaches/dates only (P0-06).
  3. Infeasible rows (k_needed<=0) are EXCLUDED from k-correction training —
     not clipped to a log-floor while claiming exclusion.
  4. Held-out predictions: one row per sample per protocol (n=120); saturation
     JSON uses held-out g_hat only (not fold×sample duplicates).
  5. Flux metrics are sample-level / overlapping-area diagnostics, NOT study-area
     totals (P0-03). Prefer L_control when present.

Schemes: baseline (S_sgs=0), residual_ai (signed S_sgs), k_correction (k_eff).
Protocols: leave-one-reach-out (LOO-reach) and leave-one-date-out (LOO-date).
NOTE: There is no inner hyperparameter loop; do not call this nested CV.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import LeaveOneGroupOut
from xgboost import XGBRegressor

from src.fold_targets import (
    assert_fold_target_isolation,
    fold_diagnose,
    fold_diagnostic_frame,
    fold_preprocessor,
    fold_sgs_targets,
)
from src.ml_models import SignedMLP
from src.plot_style import FIG_DPI, apply_plot_style
from src.real_data_guard import require_real_data, validate_processed_observations
from src.real_network import diagnose_sgs, route_steady_state
from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("nested_cv")
sns.set_theme(style="whitegrid", context="notebook", font_scale=1.25)
apply_plot_style(font_scale=1.4)

REACH_ORDER = [f"R{i:03d}" for i in range(1, 9)]

# k-correction bounds (sensitivity); exp(K_FLOOR) is the reported saturation floor.
K_FLOOR = -12.0
K_CEIL = 3.0

_DRIVER_ALIASES = {
    "Q": "Q_m3s",
    "u": "u_ms",
    "h": "h_m",
    "W": "W_m",
    "T": "T_C",
    "DOC": "DOC_mgL",
    "DO": "DO_mgL",
    "Alk": "Alk_ueqL",
    "PAR": "PAR_umolm2s",
    "N": "N_uM",
    "P": "P_uM",
}


def feature_columns(df: pd.DataFrame, cfg: dict) -> list[str]:
    cols = (
        cfg["features"]["drivers"]
        + cfg["features"]["landcover"]
        + cfg["features"]["dimensionless"]
    )
    available: list[str] = []
    for c in cols:
        use = c if c in df.columns else _DRIVER_ALIASES.get(c)
        if use and use in df.columns and df[use].notna().any():
            if use not in available:
                available.append(use)
    return available


def make_mlp(cfg: dict) -> SignedMLP:
    mlp_cfg = cfg["ai_models"]["mlp"]
    return SignedMLP(
        mlp_cfg["hidden_layers"],
        mlp_cfg["max_iter"],
        mlp_cfg["learning_rate_init"],
        mlp_cfg["random_state"],
    )


def make_rf(cfg: dict) -> RandomForestRegressor:
    return RandomForestRegressor(**cfg["ai_models"]["random_forest"])


def make_xgb(cfg: dict) -> XGBRegressor:
    return XGBRegressor(**cfg["ai_models"]["xgboost"], objective="reg:squarederror")


def score_transport(pred: pd.DataFrame, obs: pd.DataFrame) -> dict:
    """C_aq metrics + flux diagnostics with explicit estimands (P0-03).

    Flux columns are sample-level / overlapping-area diagnostics. They are NOT
    study-area spatial totals: samples overlap in space across dates and
    within-reach control volumes.
    """
    keys = ["date", "reach_id"]
    if "sample_id" in pred.columns and "sample_id" in obs.columns:
        keys.append("sample_id")
    obs_extra = ["C_aq_obs_mol_m3", "L_m", "W_m", "k_CO2_m_d", "C_eq_mol_m3"]
    if "control_volume_id" in obs.columns and "control_volume_id" not in pred.columns:
        obs_extra.append("control_volume_id")
    obs_side = obs[keys + obs_extra].rename(
        columns={"k_CO2_m_d": "k_emp_m_d", "C_eq_mol_m3": "C_eq_obs_mol_m3"}
    )
    # Drop obs-side columns already present on pred (except keys) to avoid _x/_y
    overlap = [c for c in obs_side.columns if c not in keys and c in pred.columns]
    pred_use = pred.drop(columns=overlap, errors="ignore")
    m = pred_use.merge(obs_side, on=keys, how="inner")
    if m.empty:
        raise RuntimeError("Grouped CV merge of transport output with observations is empty.")
    # Prefer routed control length when available
    if "L_control_m" in m.columns and m["L_control_m"].notna().any():
        L = m["L_control_m"].fillna(m["L_m"]).values.astype(float)
    else:
        L = m["L_m"].values.astype(float)
    W = m["W_m"].values.astype(float)
    area = L * W
    c_err = m["C_model_mol_m3"] - m["C_aq_obs_mol_m3"]
    f_mod = m["F_CO2_mol_m2d"].values
    f_obs = (m["k_emp_m_d"] * (m["C_aq_obs_mol_m3"] - m["C_eq_obs_mol_m3"])).values
    f_err = f_mod - f_obs
    ss_tot = float(((m["C_aq_obs_mol_m3"] - m["C_aq_obs_mol_m3"].mean()) ** 2).sum())

    # Date × unique spatial cell then mean over dates
    cell_key = "control_volume_id" if "control_volume_id" in m.columns else (
        "sample_id" if "sample_id" in m.columns else None
    )
    date_fluxes = []
    for _, day in m.groupby("date"):
        if cell_key and cell_key in day.columns and day[cell_key].notna().any():
            uniq = day.drop_duplicates(subset=[cell_key], keep="first")
        elif "sample_id" in day.columns:
            uniq = day.drop_duplicates(subset=["sample_id"], keep="first")
        else:
            uniq = day.drop_duplicates(subset=["reach_id"], keep="first")
        if "L_control_m" in uniq.columns:
            L_u = uniq["L_control_m"].fillna(uniq["L_m"]).values
        else:
            L_u = uniq["L_m"].values
        A_u = np.asarray(L_u, dtype=float) * uniq["W_m"].values.astype(float)
        date_fluxes.append(float(np.sum(uniq["F_CO2_mol_m2d"].values * A_u)))

    return {
        "n": int(len(m)),
        "n_reaches": int(m["reach_id"].nunique()),
        "rmse_c": float((c_err**2).mean() ** 0.5),
        "mae_c": float(c_err.abs().mean()),
        "bias_c": float(c_err.mean()),
        "r2_c": float(1.0 - float((c_err**2).sum()) / max(ss_tot, 1e-12)),
        "rmse_f": float((f_err**2).mean() ** 0.5),
        "bias_f": float(f_err.mean()),
        "flux_sample_sum_mol_m2d": float(f_mod.sum()),
        "flux_overlapping_sample_area_mol_d": float(np.sum(f_mod * area)),
        "flux_area_sum_mol_d": float(np.sum(f_mod * area)),
        "flux_date_mean_unique_cell_mol_d": float(np.mean(date_fluxes)) if date_fluxes else float("nan"),
        "flux_estimand": (
            "sample_level_diagnostic; flux_overlapping_sample_area_mol_d double-counts "
            "space/dates; flux_date_mean_unique_cell_mol_d averages per-date unique-cell integrals"
        ),
    }


def invert_k_needed(obs: pd.DataFrame) -> np.ndarray:
    """Invert quasi-steady budget for k that matches C_obs at S_sgs=0.

    Uses routed Q (Q_routed_m3s) when present so diagnosis and inversion share
    the same discharge (T05). Falls back to Q_m3s only if routed Q absent.
    """
    from src.transport import invert_k_needed as _inv

    if "Q_routed_m3s" in obs.columns and obs["Q_routed_m3s"].notna().any():
        q = obs["Q_routed_m3s"].fillna(
            obs["Q_m3s"] if "Q_m3s" in obs.columns else obs["Q_routed_m3s"]
        ).values.astype(float)
    else:
        q = obs["Q_m3s"].values.astype(float)
    # The fixed control volume is authoritative (P0-02); L_m is only a legacy alias.
    if "L_control_m" in obs.columns and obs["L_control_m"].notna().any():
        l_fallback = (
            obs["L_m"] if "L_m" in obs.columns else obs["L_control_m"]
        )
        L = obs["L_control_m"].fillna(l_fallback).values.astype(float)
    elif "L_m" in obs.columns:
        L = obs["L_m"].values.astype(float)
    else:
        raise RuntimeError(
            "invert_k_needed: neither L_control_m nor L_m present; refusing to invert k "
            "without a control volume (P0-02)"
        )
    area = L * obs["W_m"].values.astype(float)
    c_in = obs["C_in_obs_mol_m3"].values.astype(float)
    c_obs = obs["C_aq_obs_mol_m3"].values.astype(float)
    c_eq = obs["C_eq_mol_m3"].values.astype(float)
    k_need = np.full(len(obs), np.nan)
    for i in range(len(obs)):
        if not np.isfinite(c_in[i]):
            continue
        k_need[i] = _inv(
            q_out=float(q[i]),
            area=float(area[i]),
            c_in=float(c_in[i]),
            c_obs=float(c_obs[i]),
            c_eq=float(c_eq[i]),
        )
    return k_need


def _fold_diagnose(
    obs: pd.DataFrame,
    obs_seg: pd.DataFrame,
    seg_df: pd.DataFrame,
    tr_idx: np.ndarray,
    te_idx: np.ndarray,
) -> pd.DataFrame:
    """Fold-local diagnosis: hide held-out concentration labels (T05/P1-04).

    Geometry is frozen; only observation labels on test keys are removed from
    the routing diagnosis so they cannot enter training C_in / S_sgs / k targets.
    """
    return fold_diagnose(obs, obs_seg, seg_df, tr_idx, te_idx, diagnose_sgs)


def _fold_k_targets(
    obs: pd.DataFrame,
    obs_seg: pd.DataFrame,
    seg_df: pd.DataFrame,
    tr_idx: np.ndarray,
    te_idx: np.ndarray,
) -> tuple[np.ndarray, dict]:
    """Build k_needed inside the fold using training samples only (T05/P0-06).

    Uses the shared fold-local diagnostic frame so the sparse branch and this
    branch cannot drift apart (P1-04).
    """
    physical = ["C_in_obs_mol_m3", "L_control_m", "Q_routed_m3s"]
    training = fold_diagnostic_frame(
        obs, obs_seg, seg_df, tr_idx, te_idx, diagnose_sgs, extra_cols=tuple(physical)
    )
    if training.empty or training["C_in_obs_mol_m3"].isna().all():
        return np.full(len(obs), np.nan), {"n_train_feasible": 0, "n_train_infeasible": 0}
    assert not any(
        c.endswith(("_x", "_y")) for c in training.columns if c.startswith("L_control")
    ), "L_control merge produced _x/_y — fold target bug"

    training = training.set_index("_row_id").reindex(np.asarray(tr_idx))

    # Geometry, forcing and the training rows' own observations come from the
    # frozen observation/geometry tables.  These are NOT held-out labels: they
    # are the training rows' own measured values, which the inverse k target is
    # defined to reproduce.  Held-out keys never enter `tr_idx`.
    #
    # `C_in_obs_mol_m3` and `L_control_m` are deliberately NOT taken from `obs`:
    # the fold-local C_in must survive, and L_control_m is fixed geometry that
    # the fold frame already carries.
    src = obs.iloc[np.asarray(tr_idx)].reset_index(drop=True)
    src.index = np.asarray(tr_idx)
    need_from_obs = [
        c
        for c in ("W_m", "C_aq_obs_mol_m3", "C_eq_mol_m3", "k_CO2_m_d", "Q_m3s")
        if c in obs.columns
    ]
    training = training.drop(columns=[c for c in need_from_obs if c in training.columns], errors="ignore")
    training = training.join(src[need_from_obs], how="left")

    if training["C_in_obs_mol_m3"].isna().any():
        missing = int(training["C_in_obs_mol_m3"].isna().sum())
        raise RuntimeError(
            f"_fold_k_targets: {missing}/{len(training)} training rows lack a fold-local "
            "C_in diagnosis; refusing to fall back to full-data labels (P1-04)"
        )
    for required in ("W_m", "C_aq_obs_mol_m3", "C_eq_mol_m3"):
        if required not in training.columns:
            raise RuntimeError(
                f"_fold_k_targets: required column {required!r} missing; the k inverse cannot "
                "be evaluated without it (P0-02/P1-04)"
            )
    if "Q_routed_m3s" in training.columns:
        # The fold diagnostic frame carries only the routed discharge (P0-02).
        # Fall back to a raw Q column only if it actually exists; never assume it.
        fallback = next((c for c in ("Q_m3s", "Q_m3s_x", "Q_m3s_y") if c in training.columns), None)
        if fallback is None:
            training = training.assign(Q_m3s=training["Q_routed_m3s"])
        else:
            training = training.assign(Q_m3s=training["Q_routed_m3s"].fillna(training[fallback]))

    # invert_k_needed expects the fixed control length under L_control_m; the
    # fold diagnostic frame supplies it directly, and L_m is a back-compat alias.
    if "L_control_m" not in training.columns and "L_m" in training.columns:
        training = training.assign(L_control_m=training["L_m"])

    k_tr = invert_k_needed(training)
    k_all = np.full(len(obs), np.nan)
    k_all[tr_idx] = k_tr
    feasible = np.isfinite(k_tr) & (k_tr > 0)
    meta = {
        "n_train": int(len(tr_idx)),
        "n_train_with_cin": int(training["C_in_obs_mol_m3"].notna().sum()),
        "n_train_feasible": int(feasible.sum()),
        "n_train_infeasible": int((np.isfinite(k_tr) & (k_tr <= 0)).sum()),
    }
    return k_all, meta


def _fold_sgs_targets(
    obs: pd.DataFrame,
    obs_seg: pd.DataFrame,
    seg_df: pd.DataFrame,
    tr_idx: np.ndarray,
    te_idx: np.ndarray,
) -> np.ndarray:
    """Fold-local S_sgs targets — NO test-label leakage (T05/P1-04)."""
    y = fold_sgs_targets(obs, obs_seg, seg_df, tr_idx, te_idx, diagnose_sgs)
    assert_fold_target_isolation(obs, tr_idx, te_idx, y)
    return y


def run_transport(obs_seg: pd.DataFrame, seg_df: pd.DataFrame, sgs_series=None, k_eff=None, obs_for_k=None) -> pd.DataFrame:
    """Route transport through the real tree.

    If k_eff is provided, it must align with ``obs_for_k`` (same length/order as
    the feature table). Values are mapped onto ``obs_seg`` by sample keys.
    """
    if k_eff is not None:
        obs_seg = obs_seg.copy()
        if obs_for_k is None or len(k_eff) != len(obs_for_k):
            if len(k_eff) == len(obs_seg):
                obs_seg["k_CO2_m_d"] = k_eff
            else:
                raise ValueError("k_eff length does not match obs_seg or obs_for_k")
        else:
            keys = ["date", "reach_id"]
            if "sample_id" in obs_for_k.columns and "sample_id" in obs_seg.columns:
                keys.append("sample_id")
            kmap = obs_for_k[keys].copy()
            kmap["k_eff_m_d"] = np.asarray(k_eff, dtype=float)
            obs_seg = obs_seg.drop(columns=["k_eff_m_d"], errors="ignore").merge(kmap, on=keys, how="left")
            obs_seg["k_CO2_m_d"] = obs_seg["k_eff_m_d"].fillna(obs_seg["k_CO2_m_d"])
            obs_seg = obs_seg.drop(columns=["k_eff_m_d"])
    return route_steady_state(obs_seg, seg_df, s_sgs_series=sgs_series)


def sgs_frame(obs: pd.DataFrame, preds: np.ndarray) -> pd.DataFrame:
    out = {"date": obs["date"].values, "reach_id": obs["reach_id"].values, "S_sgs_mol_m2d": preds}
    if "sample_id" in obs.columns:
        out["sample_id"] = obs["sample_id"].values
    return pd.DataFrame(out)


def grouped_holdout(
    scheme: str,
    model_name: str,
    obs: pd.DataFrame,
    obs_seg: pd.DataFrame,
    seg_df: pd.DataFrame,
    feat_cols: list[str],
    groups: np.ndarray,
    protocol: str,
    cfg: dict,
    k_emp: np.ndarray,
) -> tuple[pd.DataFrame, list[float], dict]:
    """Leave-one-group-out predictions, one row per held-out sample.

    For k_correction: targets built per fold from training reaches only;
    infeasible (k_needed<=0) rows are excluded from training (not floor-clipped).
    Saturation list contains held-out g_hat only (one value per held-out sample).
    """
    logo = LeaveOneGroupOut()
    rows = []
    X_all = obs[feat_cols].replace([np.inf, -np.inf], np.nan)
    saturation_oof: list[float] = []
    fold_meta = {"folds": [], "infeasible_policy": "exclude_from_training", "cv_type": "grouped_loo"}
    failed_folds: list[dict] = []

    for fold_i, (tr, te) in enumerate(logo.split(X_all, np.zeros(len(obs)), groups)):
        # Fold-local median imputation from TRAIN only, all-NA columns dropped (P1-04)
        X_imputed, med = fold_preprocessor(X_all, tr)
        X_tr = X_imputed.iloc[tr]
        X_full = X_imputed
        held_groups = ",".join(sorted({str(g) for g in groups[te]}))

        sgs_series = None
        k_eff = None
        g_hat_full = None

        if scheme == "baseline":
            pass
        elif scheme == "residual_ai":
            # T05: rebuild SGS targets from train-only diagnosis (no test leakage)
            y_sgs_fold = _fold_sgs_targets(obs, obs_seg, seg_df, tr, te)
            tr_ok = np.isfinite(y_sgs_fold[tr])
            if int(tr_ok.sum()) < 5:
                failed_folds.append({"fold_id": fold_i, "held_group": held_groups, "reason": "too_few_sgs_targets"})
                raise RuntimeError(
                    f"residual_ai fold {held_groups}: too few train SGS targets ({int(tr_ok.sum())})"
                )
            model = make_mlp(cfg) if model_name == "mlp" else make_rf(cfg)
            try:
                X_fit = X_tr[tr_ok]
                model.fit(X_fit, y_sgs_fold[tr][tr_ok])
            except Exception as exc:
                failed_folds.append({"fold_id": fold_i, "held_group": held_groups, "reason": str(exc)})
                raise RuntimeError(f"{model_name} {held_groups} fit failed: {exc}") from exc
            sgs_hat = np.asarray(model.predict(X_full), dtype=float)
            sgs_series = sgs_frame(obs, sgs_hat)
        elif scheme == "k_correction":
            k_needed_fold, km = _fold_k_targets(obs, obs_seg, seg_df, tr, te)
            fold_meta["folds"].append({"fold_id": fold_i, "held_group": held_groups, **km})
            g_target = np.full(len(obs), np.nan)
            feas = np.isfinite(k_needed_fold) & (k_needed_fold > 0)
            g_target[feas] = np.clip(
                np.log(k_needed_fold[feas] / np.maximum(k_emp[feas], 1e-6)),
                K_FLOOR,
                K_CEIL,
            )
            tr_ok = feas[tr]
            if int(tr_ok.sum()) < 5:
                failed_folds.append({"fold_id": fold_i, "held_group": held_groups, "reason": "too_few_k_targets"})
                raise RuntimeError(
                    f"k-correction fold {held_groups}: too few feasible train targets ({int(tr_ok.sum())})"
                )
            model = make_xgb(cfg)
            model.fit(X_tr[tr_ok], g_target[tr][tr_ok])
            g_hat_full = np.clip(np.asarray(model.predict(X_full), dtype=float), K_FLOOR, K_CEIL)
            saturation_oof.extend(float(g) for g in g_hat_full[te])
            k_eff = np.maximum(k_emp * np.exp(g_hat_full), 1e-6)
        else:
            raise ValueError(scheme)

        pred_all = run_transport(obs_seg, seg_df, sgs_series, k_eff, obs_for_k=obs)
        pred_all["date"] = pd.to_datetime(pred_all["date"]).dt.normalize()
        te_keys = obs.iloc[te][["date", "reach_id"]].copy()
        if "sample_id" in obs.columns:
            te_keys["sample_id"] = obs.iloc[te]["sample_id"].values
        merge_on = [c for c in ["date", "reach_id", "sample_id"] if c in te_keys.columns and c in pred_all.columns]
        held = pred_all.merge(te_keys, on=merge_on, how="inner")
        held["scheme"] = scheme
        held["model"] = model_name
        held["cv_protocol"] = protocol
        held["fold_id"] = fold_i
        held["held_group"] = held_groups
        held["split"] = "holdout"
        if g_hat_full is not None:
            g_map = obs.iloc[te][merge_on].copy()
            g_map["g_hat_oof"] = g_hat_full[te]
            held = held.merge(g_map, on=merge_on, how="left")
        rows.append(held)

    if failed_folds:
        fold_meta["failed_folds"] = failed_folds
    if not rows:
        raise RuntimeError(f"No OOF rows for {scheme}/{model_name}/{protocol} — fail closed")
    out = pd.concat(rows, ignore_index=True)
    id_cols = [c for c in ["date", "reach_id", "sample_id"] if c in out.columns]
    if out.duplicated(subset=id_cols).any():
        raise RuntimeError(
            f"{scheme}/{model_name}/{protocol}: duplicate OOF keys — refuse keep='first' (T06)"
        )
    # Coverage: every observation must appear exactly once
    if len(out) != len(obs):
        raise RuntimeError(
            f"{scheme}/{model_name}/{protocol}: OOF n={len(out)} != obs n={len(obs)} (T06)"
        )
    return out, saturation_oof, fold_meta


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    require_real_data(cfg, "12_nested_cv_transport")
    proc = resolve_path(cfg, "data_proc")
    fig_dir = resolve_path(cfg, "figures")
    tbl_dir = resolve_path(cfg, "tables")
    fig_dir.mkdir(parents=True, exist_ok=True)
    tbl_dir.mkdir(parents=True, exist_ok=True)
    validate_processed_observations(proc / "reach_daily_observations.csv")

    obs = pd.read_csv(proc / "reach_daily_observations.csv", parse_dates=["date"])
    obs["date"] = pd.to_datetime(obs["date"]).dt.normalize()
    obs_seg = pd.read_csv(proc / "reach_daily_observations_segmented.csv", parse_dates=["date"])
    obs_seg["date"] = pd.to_datetime(obs_seg["date"]).dt.normalize()
    seg_df = pd.read_csv(proc / "network_segments.csv")
    train_df = pd.read_csv(proc / "sgs_training_data.csv", parse_dates=["date"])
    train_df["date"] = pd.to_datetime(train_df["date"]).dt.normalize()

    # Merge features + diagnosed S_sgs into obs (C_in rebuilt per fold for k-correction)
    merge_on = ["date", "reach_id"]
    if "sample_id" in train_df.columns and "sample_id" in obs.columns:
        merge_on.append("sample_id")
    feat_df = obs.merge(train_df, on=merge_on, how="left", suffixes=("", "_tr"))
    obs = feat_df.reset_index(drop=True).copy()
    # Full-data diagnose only for reporting / histogram (not used as CV train targets)
    diag = diagnose_sgs(obs_seg, seg_df)
    dmerge = ["date", "reach_id"] + (["sample_id"] if "sample_id" in diag.columns else [])
    obs = obs.drop(columns=[c for c in ["C_in_obs_mol_m3", "L_control_m"] if c in obs.columns], errors="ignore")
    obs = obs.merge(
        diag[dmerge + ["C_in_obs_mol_m3", "L_control_m"]],
        on=dmerge,
        how="left",
    )
    if "control_volume_id" in obs_seg.columns and "control_volume_id" not in obs.columns:
        obs = obs.merge(obs_seg[dmerge + ["control_volume_id"]], on=dmerge, how="left")

    feat_cols = feature_columns(obs, cfg)
    k_emp = obs["k_CO2_m_d"].values.astype(float)
    k_needed_report = invert_k_needed(obs)
    feasible_mask = np.isfinite(k_needed_report) & (k_needed_report > 0)
    infeasible_frac = float(1.0 - feasible_mask.mean())
    LOG.info(
        "k_needed (full-data diagnostic): infeasible (<=0) = %.1f%% (%d/%d); "
        "CV training excludes these (does not floor-clip)",
        100 * infeasible_frac,
        int((~feasible_mask).sum()),
        len(obs),
    )

    reach_groups = obs["reach_id"].astype(str).values
    date_groups = obs["date"].astype(str).values

    jobs = [
        ("baseline", "none", "loo_reach", reach_groups),
        ("baseline", "none", "loo_date", date_groups),
        ("residual_ai", "mlp", "loo_reach", reach_groups),
        ("residual_ai", "random_forest", "loo_reach", reach_groups),
        ("k_correction", "xgboost", "loo_reach", reach_groups),
        ("k_correction", "xgboost", "loo_date", date_groups),
    ]

    holdout_parts = []
    saturation_oof_reach: list[float] = []
    kcorr_meta = {}
    for scheme, model_name, protocol, groups in jobs:
        LOG.info("Grouped CV %s / %s / %s", scheme, model_name, protocol)
        part, sat, meta = grouped_holdout(
            scheme=scheme,
            model_name=model_name,
            obs=obs,
            obs_seg=obs_seg,
            seg_df=seg_df,
            feat_cols=feat_cols,
            groups=groups,
            protocol=protocol,
            cfg=cfg,
            k_emp=k_emp,
        )
        if part.empty:
            LOG.warning("No holdout rows for %s %s %s", scheme, model_name, protocol)
            continue
        if scheme == "k_correction" and protocol == "loo_reach":
            saturation_oof_reach = sat
            kcorr_meta = meta
            n_oof = part["sample_id"].nunique() if "sample_id" in part.columns else len(part)
            LOG.info("k-correction loo_reach OOF n_rows=%d n_samples=%d sat_n=%d", len(part), n_oof, len(sat))
        holdout_parts.append(part)

    holdout = pd.concat(holdout_parts, ignore_index=True)
    holdout.to_csv(proc / "nested_cv_holdout_predictions.csv", index=False)

    # Metrics
    nested_rows = []
    for (scheme, model, protocol), g in holdout.groupby(["scheme", "model", "cv_protocol"]):
        extra = {
            "scheme": scheme,
            "model": model,
            "cv_protocol": protocol,
            "subgroup": "all_120",
            "subgroup_label": "All 120 samples",
            "evidence_weight": "all",
        }
        sc = score_transport(g, obs)
        sc.update(extra)
        nested_rows.append(sc)
    nested_df = pd.DataFrame(nested_rows)
    nested_df.to_csv(tbl_dir / "nested_cv_metrics.csv", index=False)

    # per-reach RMSE for baseline / residual_ai / k_correction (LOO-reach)
    reach_rows = []
    for (scheme, model), g in holdout[holdout["cv_protocol"] == "loo_reach"].groupby(["scheme", "model"]):
        for rid, sub in g.groupby("reach_id"):
            err = sub["C_model_mol_m3"] - sub["C_obs_mol_m3"]
            reach_rows.append(
                {
                    "scheme": scheme,
                    "model": model,
                    "reach_id": rid,
                    "n": len(sub),
                    "rmse_c": float((err**2).mean() ** 0.5),
                    "mae_c": float(err.abs().mean()),
                    "bias_c": float(err.mean()),
                }
            )
    pd.DataFrame(reach_rows).to_csv(tbl_dir / "per_reach_cv_metrics.csv", index=False)

    # --- P1-07: paired per-reach errors and leave-out sensitivity -------------
    _write_paired_reach_analysis(holdout, obs, tbl_dir)

    # Saturation summary: OOF held-out g_hat only (n≈120 for loo_reach), not fold×sample
    if saturation_oof_reach:
        sat = np.array(saturation_oof_reach)
        floor_frac = float(np.mean(sat <= K_FLOOR + 1e-6))
        LOG.info(
            "k-correction OOF saturation at floor (g<=%.1f): %.1f%% (n=%d held-out preds)",
            K_FLOOR,
            100 * floor_frac,
            len(sat),
        )
        with (tbl_dir / "k_correction_saturation.json").open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "K_FLOOR": K_FLOOR,
                    "floor_ratio_exp": float(np.exp(K_FLOOR)),
                    "infeasible_policy": "exclude_from_training",
                    "n_predictions": int(len(sat)),
                    "n_predictions_note": (
                        "One leave-one-reach-out held-out g_hat per sample "
                        "(not fold×sample duplicates)."
                    ),
                    "n_campaign": int(len(obs)),
                    "n_feasible_full_data": int(feasible_mask.sum()),
                    "n_infeasible_full_data": int((~feasible_mask).sum()),
                    "infeasible_frac_full_data": infeasible_frac,
                    "frac_at_floor_oof": floor_frac,
                    "g_hat_min": float(sat.min()),
                    "g_hat_median": float(np.median(sat)),
                    "fold_training_meta": kcorr_meta,
                },
                f,
                indent=2,
            )

    # Summary JSON
    def _pick(scheme, model, protocol="loo_reach"):
        hit = nested_df[
            (nested_df["scheme"] == scheme) & (nested_df["model"] == model) & (nested_df["cv_protocol"] == protocol)
        ]
        return hit.iloc[0] if len(hit) else None

    b = _pick("baseline", "none")
    m = _pick("residual_ai", "mlp")
    rf = _pick("residual_ai", "random_forest")
    k = _pick("k_correction", "xgboost")
    summary = {
        "n_campaign": int(len(obs)),
        "cv_design": "grouped_leave_one_reach_out_no_inner_loop",
        "k_needed_infeasible_frac": infeasible_frac,
        "k_infeasible_policy": "exclude_from_training",
        "flux_estimand": "sample_level_diagnostic_not_study_area_total",
        "loo_reach_rmse_c": {
            "baseline": None if b is None else float(b["rmse_c"]),
            "residual_ai_mlp": None if m is None else float(m["rmse_c"]),
            "residual_ai_rf": None if rf is None else float(rf["rmse_c"]),
            "k_correction": None if k is None else float(k["rmse_c"]),
        },
        "post_fix_development_numbers": True,
    }
    if b is not None and m is not None:
        summary["mlp_beats_baseline_loo_reach"] = bool(m["rmse_c"] < b["rmse_c"])
    if b is not None and k is not None:
        summary["kcorr_beats_baseline_loo_reach"] = bool(k["rmse_c"] < b["rmse_c"])
        summary["kcorr_overlapping_sample_area_flux_mol_d"] = float(k["flux_overlapping_sample_area_mol_d"])
        summary["baseline_overlapping_sample_area_flux_mol_d"] = float(b["flux_overlapping_sample_area_mol_d"])
        summary["kcorr_date_mean_unique_cell_flux_mol_d"] = float(k["flux_date_mean_unique_cell_mol_d"])
        summary["baseline_date_mean_unique_cell_flux_mol_d"] = float(b["flux_date_mean_unique_cell_mol_d"])
    with (tbl_dir / "nested_cv_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    LOG.info("Grouped CV summary:\n%s", json.dumps(summary, indent=2))

    _plot_rmse_bar(nested_df, fig_dir, holdout=holdout)
    _plot_k_saturation(obs, k_emp, k_needed_report, fig_dir)
    LOG.info("Tables written to %s", tbl_dir)


def _write_paired_reach_analysis(holdout: pd.DataFrame, obs: pd.DataFrame, tbl_dir: Path) -> None:
    """Per-reach paired errors and drop-one-reach sensitivity (P1-07).

    Eight groups cannot support strong generalization inference, so this reports
    descriptive per-reach paired differences and the effect of removing R002 —
    no p-values, confidence intervals or bootstrap are manufactured.

    Row unit: one held-out sample (leave-one-reach-out OOF). Weights: equal per
    sample. Units: mol/m3 (C), mol/d (SSE).
    """
    loo = holdout[holdout["cv_protocol"] == "loo_reach"].copy()
    loo["date"] = pd.to_datetime(loo["date"]).dt.normalize()
    loo["reach_id"] = loo["reach_id"].astype(str)
    if "sample_id" in loo.columns:
        loo["sample_id"] = loo["sample_id"].astype(str)

    keys = [c for c in ["date", "reach_id", "sample_id"] if c in loo.columns]
    wide = loo.pivot_table(
        index=keys,
        columns=["scheme", "model"],
        values="C_model_mol_m3",
        aggfunc="first",
    )
    wide.columns = [f"C_{s}_{m}" for s, m in wide.columns]
    obs_side = (
        loo.sort_values(keys)
        .drop_duplicates(subset=keys, keep="first")[keys + ["C_obs_mol_m3"]]
        .set_index(keys)
    )
    paired = wide.join(obs_side, how="left", validate="one_to_one").reset_index()
    paired = paired.rename(columns={"C_obs_mol_m3": "C_aq_obs_mol_m3"})

    schemes = {
        "baseline": "C_baseline_none",
        "mlp": "C_residual_ai_mlp",
        "rf": "C_residual_ai_random_forest",
        "kcorr": "C_k_correction_xgboost",
    }
    rows: list[dict] = []
    for rid, g in paired.groupby("reach_id"):
        rec = {"reach_id": rid, "n": int(len(g))}
        for label, col in schemes.items():
            if col not in g.columns:
                continue
            err = (g[col] - g["C_aq_obs_mol_m3"]).astype(float)
            rec[f"{label}_rmse"] = float((err**2).mean() ** 0.5)
            rec[f"{label}_mae"] = float(err.abs().mean())
            rec[f"{label}_bias"] = float(err.mean())
            rec[f"{label}_sse"] = float((err**2).sum())
        rows.append(rec)
    per_reach = pd.DataFrame(rows).sort_values("reach_id").reset_index(drop=True)

    # paired difference (MLP - baseline) per reach
    if {"mlp_sse", "baseline_sse"}.issubset(per_reach.columns):
        per_reach["mlp_minus_baseline_sse"] = per_reach["mlp_sse"] - per_reach["baseline_sse"]
        per_reach["mlp_sse_gain"] = -per_reach["mlp_minus_baseline_sse"]
        total_gain = float(per_reach["mlp_sse_gain"].sum())
        positive = per_reach["mlp_sse_gain"].clip(lower=0.0)
        positive_sum = float(positive.sum())
        if positive_sum > 0:
            # Share of the *gross* per-reach gains. Reported even when the net
            # total is negative, so a single dominant reach cannot be hidden.
            per_reach["mlp_gain_contribution_frac"] = positive / positive_sum
        per_reach.attrs["net_mlp_sse_gain"] = total_gain
        per_reach.attrs["gross_positive_mlp_sse_gain"] = positive_sum
    per_reach.to_csv(tbl_dir / "per_reach_paired_metrics.csv", index=False)

    def _pooled_rmse(frame: pd.DataFrame, col: str) -> float:
        err = (frame[col] - frame["C_aq_obs_mol_m3"]).astype(float)
        return float((err**2).mean() ** 0.5)

    sensitivity: dict = {
        "note": (
            "Descriptive sensitivity only: eight groups do not support strong "
            "generalization inference. No p-values, confidence intervals or bootstrap."
        ),
        "row_unit": "one held-out sample (leave-one-reach-out OOF predictions)",
        "weights": "equal weight per sample",
        "n_groups": int(paired["reach_id"].nunique()),
        "per_reach_n": {str(r["reach_id"]): int(r["n"]) for _, r in per_reach.iterrows()},
        "equal_weight_reach_mse_then_sqrt": {},
        "drop_reach_without_retraining": {},
        "rmse_estimand_note": (
            "equal_weight_reach_mse_then_sqrt is the unweighted mean of per-reach MSE "
            "followed by a square root. It is NOT the mean of per-reach RMSE, and it is "
            "NOT the pooled sample-level RMSE."
        ),
    }
    for label, col in schemes.items():
        if col not in paired.columns:
            continue
        per_reach_mse = []
        for _rid, g in paired.groupby("reach_id"):
            e = (g[col] - g["C_aq_obs_mol_m3"]).astype(float)
            per_reach_mse.append(float((e**2).mean()))
        sensitivity["equal_weight_reach_mse_then_sqrt"][label] = float(np.sqrt(np.mean(per_reach_mse)))
        sensitivity["drop_reach_without_retraining"][label] = {}
        for rid in sorted(paired["reach_id"].unique()):
            sub = paired[paired["reach_id"] != rid]
            if len(sub):
                sensitivity["drop_reach_without_retraining"][label][f"drop_{rid}"] = _pooled_rmse(sub, col)
        sensitivity["drop_reach_without_retraining"][label]["all"] = _pooled_rmse(paired, col)

    if "mlp_gain_contribution_frac" in per_reach.columns:
        top = per_reach.dropna(subset=["mlp_gain_contribution_frac"]).nlargest(3, "mlp_gain_contribution_frac")
        sensitivity["top_gain_contributors"] = {
            str(r["reach_id"]): float(r["mlp_gain_contribution_frac"]) for _, r in top.iterrows()
        }
        r002 = per_reach.loc[per_reach["reach_id"] == "R002", "mlp_gain_contribution_frac"]
        if len(r002):
            sensitivity["r002_gain_contribution_frac"] = float(r002.iloc[0])
    net_gain = float(per_reach["mlp_sse_gain"].sum())
    sensitivity["net_mlp_sse_gain"] = net_gain
    sensitivity["gross_positive_mlp_sse_gain"] = float(
        per_reach["mlp_sse_gain"].clip(lower=0.0).sum()
    )
    sensitivity["net_mlp_improves_all_reaches"] = bool(net_gain > 0)
    worse = per_reach.loc[per_reach["mlp_minus_baseline_sse"] > 0, "reach_id"].tolist()
    sensitivity["reaches_where_mlp_is_worse"] = [str(x) for x in worse]

    # Per-reach paired metrics travel with the sensitivity file so consumers do
    # not have to re-read a second CSV to explain the same number (P1-07).
    sensitivity["per_reach_paired"] = [
        {
            str(k): (
                str(v)
                if k == "reach_id"
                else (None if pd.isna(v) else (int(v) if k == "n" else float(v)))
            )
            for k, v in rec.items()
        }
        for rec in per_reach.to_dict(orient="records")
    ]
    sensitivity["per_reach_paired_columns"] = list(per_reach.columns)

    with (tbl_dir / "reach_sensitivity.json").open("w", encoding="utf-8") as f:
        json.dump(sensitivity, f, indent=2)
    LOG.info("Per-reach paired metrics + sensitivity written")


def _plot_rmse_bar(metrics: pd.DataFrame, fig_dir: Path, holdout: pd.DataFrame | None = None,
                   per_reach: pd.DataFrame | None = None) -> None:
    """Figure 3: pooled held-out RMSE with the per-reach spread behind it.

    Design notes for the 2026-09-27 revision (review P1-07, author request):
      * thin bars instead of the previous chunky 0.72-width bars;
      * the pooled (sample-weighted) value is the filled bar;
      * the per-reach values are drawn as open markers on a thin whisker, so the
        reader can see that the pooled contrast is driven by a few reaches;
      * the infeasible-row annotation records n=120 / 8 groups / seed.
    No error bars are drawn: the per-reach points are the observations, not an
    inferred uncertainty interval.
    """
    want = metrics[metrics["cv_protocol"] == "loo_reach"].copy()
    if want.empty:
        return
    keys = [
        ("baseline", "none"),
        ("residual_ai", "mlp"),
        ("residual_ai", "random_forest"),
        ("k_correction", "xgboost"),
    ]
    labels = ["Baseline\n$S_{sgs}=0$", "Residual-AI\nMLP", "Residual-AI\nRF",
              "k-correction\n$k_{eff}$"]
    colors = ["#5b6b7b", "#2f6fb0", "#2a9d8f", "#e0813a"]
    vals = []
    for scheme, model in keys:
        sub = want[(want["scheme"] == scheme) & (want["model"] == model)]
        vals.append(float(sub["rmse_c"].iloc[0]) if len(sub) else np.nan)

    # Per-reach RMSE from the same OOF predictions (never re-simulated).
    per_reach_vals: list[list[float]] = [[] for _ in keys]
    if holdout is not None and not holdout.empty:
        h = holdout[holdout["cv_protocol"] == "loo_reach"]
        for j, (scheme, model) in enumerate(keys):
            sub = h[(h["scheme"] == scheme) & (h["model"] == model)]
            for _rid, g in sub.groupby("reach_id"):
                e = (g["C_model_mol_m3"] - g["C_obs_mol_m3"]).to_numpy(dtype=float)
                e = e[np.isfinite(e)]
                if len(e):
                    per_reach_vals[j].append(float(np.sqrt((e ** 2).mean())))

    fig, ax = plt.subplots(figsize=(8.4, 5.6))
    x = np.arange(len(keys))
    width = 0.46
    bars = ax.bar(x, vals, color=colors, edgecolor="white", linewidth=0.9,
                  width=width, zorder=2)
    base_v = next((v for v, (s, m) in zip(vals, keys) if s == "baseline"), np.nan)
    if np.isfinite(base_v):
        ax.axhline(base_v, color="#44505c", ls="--", lw=1.2, zorder=1,
                   label=f"Baseline pooled RMSE = {base_v:.4f}")

    # Per-reach spread: thin whisker + open markers, offset to the bar's right.
    for xi, pv in zip(x, per_reach_vals):
        if len(pv) < 2:
            continue
        arr = np.asarray(pv, dtype=float)
        xr = xi + width / 2.0 + 0.055
        ax.vlines(xr, arr.min(), arr.max(), color="#8a97a5", lw=1.0, zorder=3)
        ax.scatter(np.full(arr.size, xr), arr, s=13, facecolors="white",
                   edgecolors="#44505c", linewidths=0.75, zorder=4)
        ax.text(xr + 0.028, arr.mean(), "per-reach", rotation=90, fontsize=6.2,
                color="#5b6b7b", va="center", ha="left")

    ymax = max([v for v in vals if np.isfinite(v)] + [1e-3]) * 1.20
    ax.set_ylim(0, ymax)
    for b2, v in zip(bars, vals):
        if np.isfinite(v):
            ax.text(b2.get_x() + b2.get_width() / 2, v + ymax * 0.015,
                    f"{v:.4f}", ha="center", va="bottom", fontsize=9.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10.5)
    ax.set_ylabel(r"Held-out $C_{\mathrm{aq}}$ RMSE (mol m$^{-3}$)", fontsize=12)
    ax.set_title("Leave-one-reach-out held-out concentration error by closure",
                 fontsize=12.5, fontweight="bold", pad=10)
    ax.grid(True, axis="y", alpha=0.30, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.text(
        0.985, 0.03,
        "n = 120 samples | 8 reach groups | seed 42 | filled bar = pooled (sample-weighted)\n"
        "open markers = per-reach RMSE (3 of 8 groups have n = 1)",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=6.6, color="#44505c",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9,
                  edgecolor="#cbd3db"),
    )
    ax.legend(loc="upper left", fontsize=8.2, framealpha=0.92)
    fig.tight_layout()
    fig.savefig(fig_dir / "nested_cv_rmse_bar.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)


def _plot_k_saturation(obs: pd.DataFrame, k_emp: np.ndarray, k_needed: np.ndarray, fig_dir: Path) -> None:
    """Histogram of k_needed/k_emp on log axis with the exp(K_FLOOR) line."""
    ratio = k_needed / np.maximum(k_emp, 1e-6)
    pos = ratio[ratio > 0]
    fig, ax = plt.subplots(figsize=(10, 6))
    if len(pos):
        ax.hist(np.log10(pos), bins=40, color="#e67e22", alpha=0.8, edgecolor="white")
    ax.axvline(K_FLOOR / np.log(10), color="#c0392b", ls="--", lw=2, label=f"floor $e^{{{K_FLOOR:.0f}}}$")
    ax.set_xlabel("$\\log_{10}(k_{needed}/k_{emp})$", fontsize=15)
    ax.set_ylabel("Count", fontsize=15)
    ax.set_title(
        f"Inverted k$_{{needed}}/k_{{emp}}$ distribution (infeasible frac = {np.mean(k_needed <= 0):.0%})",
        fontsize=15,
        fontweight="bold",
    )
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.35)
    fig.tight_layout()
    fig.savefig(fig_dir / "k_correction_saturation_hist.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nested CV coupled transport (corrected)")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
