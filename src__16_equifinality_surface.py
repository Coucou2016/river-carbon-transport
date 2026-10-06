#!/usr/bin/env python3
"""
Equifinality of gas-exchange k versus subgrid source S_sgs from the objective
surface and profile SSE/objective (NOT a statistical profile likelihood).

Steady-state balance per sample i:
    q_A,i (C_in,i - C) + S - k (C - C_eq,i) = 0

Model prediction given (k, S):
    C_model(k, S) = (q_A,i C_in,i + S + k C_eq,i) / (q_A,i + k)

Without an error distribution this is a profile SSE / objective analysis (T09),
not a profile likelihood. q_A is read from routed Q and area, not inverted from
the diagnostic residual when Cobs≈Cin.

REAL DATA ONLY. Uses sgs_training_data.csv and grouped-CV holdout operating points.
"""

from __future__ import annotations

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.plot_style import FIG_DPI, apply_plot_style
from src.real_data_guard import require_real_data, validate_processed_observations
from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("equifinality_surface")
apply_plot_style(font_scale=1.4)

S_REF = 1.0  # mol m-2 d-1; source is parametrized directly in physical units


def load_per_sample(cfg: dict) -> pd.DataFrame:
    proc = resolve_path(cfg, "data_proc")
    tr = pd.read_csv(proc / "sgs_training_data.csv", parse_dates=["date"])
    obs = pd.read_csv(proc / "reach_daily_observations.csv", parse_dates=["date"])
    diag = pd.read_csv(proc / "sgs_training_data.csv", parse_dates=["date"])

    keys = ["date", "reach_id", "sample_id"]
    missing = [k for k in keys if k not in tr.columns or k not in obs.columns]
    if missing:
        raise RuntimeError(f"sgs_training_data / observations missing merge keys {missing}")

    # P1-05: q_A = 86400 * Q_routed / (L_control * W) via an EXPLICIT keyed merge.
    # Never fall back to the residual inverse, and never use whole-reach L_m:
    # that silently substituted a different estimand while claiming to be direct.
    # C_in_obs_mol_m3 is a DIAGNOSED routed boundary state, so it travels with the
    # physical table, not with the raw observation table (P0-02/P1-05).
    need_phys = ["Q_routed_m3s", "L_control_m", "C_in_obs_mol_m3"]
    missing_phys = [c for c in need_phys if c not in diag.columns]
    if missing_phys:
        raise RuntimeError(
            "direct q_A and the routed boundary need "
            f"{need_phys}; missing from sgs_training_data = {missing_phys}. "
            f"available physical columns = {list(diag.columns)}. "
            "Refusing the residual-inverse / whole-reach-L fallback (P1-05)."
        )
    physical = diag[keys + need_phys].copy()
    if physical.duplicated(subset=keys).any():
        raise RuntimeError("sgs_training_data has duplicate (date, reach_id, sample_id) keys")

    obs_cols = [c for c in ("W_m", "C_aq_obs_mol_m3", "C_eq_mol_m3", "k_CO2_m_d") if c in obs.columns]
    m = obs[keys + obs_cols].merge(physical, on=keys, how="inner", validate="one_to_one")
    if m.empty:
        raise RuntimeError("no rows after the explicit q_A merge")

    m["q_A_m_d"] = 86400.0 * m["Q_routed_m3s"].astype(float) / (
        m["L_control_m"].astype(float) * m["W_m"].astype(float)
    )
    if not np.isfinite(m["q_A_m_d"]).all() or not (m["q_A_m_d"] > 0).all():
        bad = int((~np.isfinite(m["q_A_m_d"]) | ~(m["q_A_m_d"] > 0)).sum())
        raise RuntimeError(f"{bad} row(s) have non-positive/non-finite directly computed q_A")
    m["q_A_source"] = "direct_Q_routed_over_control_length_times_width"
    m["boundary_source"] = "upstream routed state (C_in_obs_mol_m3 from diagnosed routing)"

    # The residual-inverse q_A is retained ONLY as a cross-check diagnostic and
    # is never used in the objective.
    c_in = m["C_in_obs_mol_m3"].to_numpy(dtype=float) if "C_in_obs_mol_m3" in m.columns else np.full(len(m), np.nan)
    c_obs = m["C_aq_obs_mol_m3"].to_numpy(dtype=float)
    c_eq = m["C_eq_mol_m3"].to_numpy(dtype=float)
    k_emp = m["k_CO2_m_d"].to_numpy(dtype=float)
    s_diag = np.full(len(m), np.nan)
    if "S_sgs_residual_mol_m2d" in tr.columns:
        s_diag = tr.set_index(keys)["S_sgs_residual_mol_m2d"].reindex(
            pd.MultiIndex.from_frame(m[keys])
        ).to_numpy(dtype=float)

    denom = c_obs - c_in
    q_a_inv = np.where(
        np.abs(denom) > 1e-12,
        (s_diag - k_emp * (c_obs - c_eq)) / np.where(np.abs(denom) > 1e-12, denom, 1.0),
        np.nan,
    )
    finite = np.isfinite(q_a_inv) & np.isfinite(m["q_A_m_d"].to_numpy(dtype=float))
    m["q_A_from_residual_m_d"] = q_a_inv
    m["q_A_direct_minus_inverse_m_d"] = m["q_A_m_d"].to_numpy(dtype=float) - q_a_inv

    m = m.copy()
    m["dC_mol_m3"] = c_obs - c_eq
    m["k_emp_m_d"] = k_emp
    m["S_diag_mol_m2d"] = s_diag
    if finite.any():
        LOG.info(
            "q_A direct vs residual-inverse: max |diff| = %.3e m/d over %d rows "
            "(metadata/robustness check, not an observed numeric error)",
            float(np.nanmax(np.abs(m.loc[finite, "q_A_direct_minus_inverse_m_d"]))),
            int(finite.sum()),
        )
    return m


def c_model(q_a: np.ndarray, c_in: np.ndarray, c_eq: np.ndarray, k: np.ndarray, s: np.ndarray) -> np.ndarray:
    denom = q_a + k
    denom = np.where(denom < 1e-12, 1e-12, denom)
    return (q_a * c_in + s + k * c_eq) / denom


def analytical_s_best(alpha: float, m: pd.DataFrame, weights: np.ndarray | None = None) -> tuple[float, float]:
    """For fixed alpha, S is linear — analytical least-squares (T09)."""
    q_a = m["q_A_m_d"].to_numpy()
    c_in = m["C_in_obs_mol_m3"].to_numpy()
    c_eq = m["C_eq_mol_m3"].to_numpy()
    c_obs = m["C_aq_obs_mol_m3"].to_numpy()
    k_emp = m["k_CO2_m_d"].to_numpy()
    k = alpha * k_emp
    den = q_a + k
    den = np.where(np.abs(den) < 1e-12, np.nan, den)
    a = (q_a * c_in + k * c_eq) / den
    b = 1.0 / den
    w = np.ones(len(m)) if weights is None else np.asarray(weights, dtype=float)
    mask = np.isfinite(a) & np.isfinite(b)
    num = np.sum(w[mask] * b[mask] * (c_obs[mask] - a[mask]))
    den_s = np.sum(w[mask] * b[mask] * b[mask])
    s_best = float(num / den_s) if den_s > 1e-15 else 0.0
    j_best = float(np.sum(w[mask] * (c_obs[mask] - a[mask] - b[mask] * s_best) ** 2))
    return s_best, j_best


def objective_pooled(alpha: float, s: float, m: pd.DataFrame) -> float:
    k = alpha * m["k_CO2_m_d"].to_numpy()
    c = c_model(m["q_A_m_d"].to_numpy(), m["C_in_obs_mol_m3"].to_numpy(), m["C_eq_mol_m3"].to_numpy(), k, np.full(len(m), s))
    r = m["C_aq_obs_mol_m3"].to_numpy() - c
    return float(np.sum(r * r))


def build_surface(m: pd.DataFrame) -> dict:
    """Pooled objective J(alpha, S) with analytical S profile (T09)."""
    alphas = np.logspace(-6, 0.5, 121)
    s_grid = np.linspace(-3.0, 30.0, 121)

    c_obs = m["C_aq_obs_mol_m3"].to_numpy()
    c_eq = m["C_eq_mol_m3"].to_numpy()
    c_in = m["C_in_obs_mol_m3"].to_numpy()
    q_a = m["q_A_m_d"].to_numpy()
    k_emp = m["k_CO2_m_d"].to_numpy()

    J = np.full((len(s_grid), len(alphas)), np.nan)
    prof = np.full(len(alphas), np.nan)
    prof_s = np.full(len(alphas), np.nan)
    for j, a in enumerate(alphas):
        s_star, j_star = analytical_s_best(float(a), m)
        prof[j] = j_star
        prof_s[j] = s_star
        k = a * k_emp
        for i, s in enumerate(s_grid):
            c = c_model(q_a, c_in, c_eq, k, np.full(len(m), s))
            r = c_obs - c
            J[i, j] = np.sum(r * r)

    n = len(m)
    rmse = np.sqrt(prof / n)
    rmin = float(np.nanmin(rmse))
    ok = rmse <= rmin * 1.10
    loga = np.log10(alphas)
    if ok.any():
        lo, hi = float(loga[ok].min()), float(loga[ok].max())
        span = hi - lo
        basin = (alphas >= 1e-2) & (alphas <= 1.0)
        rmse_basin = (float(rmse[basin].min()), float(rmse[basin].max()))
    else:
        lo = hi = float(np.log10(alphas[np.nanargmin(prof)]))
        span = 0.0
        rmse_basin = (rmin, rmin)

    return {
        "alphas": alphas,
        "s_grid": s_grid,
        "J": J,
        "prof": prof,
        "prof_s": prof_s,
        "flatness_span_decades": float(span),
        "flatness_lo": float(lo),
        "flatness_hi": float(hi),
        "argmin_alpha": float(alphas[np.nanargmin(prof)]),
        "argmin_s": float(prof_s[np.nanargmin(prof)]),
        "rmse_min": float(rmin),
        "rmse_basin_min": rmse_basin[0],
        "rmse_basin_max": rmse_basin[1],
        "objective_name": "profile_SSE",
        "q_A_median_m_d": float(np.nanmedian(q_a)),
    }


def representative_sample(m: pd.DataFrame) -> pd.Series:
    """Sample whose supersaturation dC is closest to the dataset median."""
    med = float(m["dC_mol_m3"].median())
    idx = int((m["dC_mol_m3"] - med).abs().idxmin())
    return m.loc[idx]


def plot_surface(m: pd.DataFrame, surf: dict, fig_dir, holdout: pd.DataFrame | None) -> dict:
    rep = representative_sample(m)

    fig, axes = plt.subplots(1, 3, figsize=(19.5, 6.2))

    # ---- (a) single-sample objective surface (structural valley) ----
    ax = axes[0]
    q_a = float(rep["q_A_m_d"])
    c_in = float(rep["C_in_obs_mol_m3"])
    c_eq = float(rep["C_eq_mol_m3"])
    c_obs = float(rep["C_aq_obs_mol_m3"])
    k_emp = float(rep["k_CO2_m_d"])
    s_diag = float(rep["S_diag_mol_m2d"])
    dC = float(rep["dC_mol_m3"])

    k_grid = np.logspace(-3, np.log10(max(k_emp * 1.5, 300.0)), 160)
    s_grid = np.linspace(min(-3.0, s_diag - 6.0), max(s_diag + 6.0, 30.0), 160)
    KK, SS = np.meshgrid(k_grid, s_grid)
    C = (q_a * c_in + SS + KK * c_eq) / np.maximum(q_a + KK, 1e-12)
    R = c_obs - C
    J = np.log10(np.maximum(R * R, 1e-14))
    im = ax.pcolormesh(k_grid, s_grid, J, shading="auto", cmap="viridis_r")
    ax.plot(k_grid, s_diag + dC * (k_grid - k_emp), color="crimson", lw=2.2, label="exact-match line (J=0)")
    ax.scatter([k_emp], [0.0], marker="o", s=180, color="#7f8c8d", edgecolors="white", linewidths=1.4, zorder=5, label="Baseline (k_emp, S=0)")
    ax.scatter([k_emp], [s_diag], marker="s", s=180, color="#2980b9", edgecolors="white", linewidths=1.4, zorder=5, label="Residual-AI target (k_emp, S_diag)")
    ax.set_xscale("log")
    ax.set_xlabel(r"$k$ (m d$^{-1}$)")
    ax.set_ylabel(r"$S$ (mol m$^{-2}$ d$^{-1}$)")
    ax.set_title("(a) Single-sample objective $\\log_{10}J(k,S)$", fontweight="bold")
    ax.legend(loc="lower right", fontsize=9, framealpha=0.95)
    ax.grid(True, alpha=0.3, which="both")
    fig.colorbar(im, ax=ax, pad=0.02, label=r"$\log_{10}\,[C_{obs}-C(k,S)]^2$")

    # ---- (b) pooled objective surface J(alpha, S) ----
    ax = axes[1]
    alphas = surf["alphas"]
    s_grid_p = surf["s_grid"]
    JP = np.log10(np.maximum(surf["J"], 1e-14))
    im2 = ax.pcolormesh(alphas, s_grid_p, JP, shading="auto", cmap="viridis_r")
    ax.set_xscale("log")
    ax.set_xlabel(r"$k$-scale $\alpha = k/k_{emp}$")
    ax.set_ylabel(r"Uniform source $S$ (mol m$^{-2}$ d$^{-1}$)")
    ax.set_title("(b) Pooled objective $\\log_{10}J(\\alpha,S)$", fontweight="bold")
    ax.grid(True, alpha=0.3, which="both")
    # operating points
    k_ratio_med = float((holdout["k_eff"] / holdout["k_emp"]).median()) if holdout is not None else np.nan
    s_ai_med = float(holdout["S_ai"].median()) if holdout is not None else np.nan
    ax.scatter([1.0], [0.0], marker="o", s=170, color="#7f8c8d", edgecolors="white", linewidths=1.3, zorder=5, label="Baseline")
    if np.isfinite(k_ratio_med) and k_ratio_med > 0:
        ax.scatter([k_ratio_med], [0.0], marker="D", s=170, color="#e67e22", edgecolors="white", linewidths=1.3, zorder=5, label="k-correction")
    if np.isfinite(s_ai_med):
        ax.scatter([1.0], [s_ai_med], marker="s", s=170, color="#2980b9", edgecolors="white", linewidths=1.3, zorder=5, label="Residual-AI")
    ax.legend(loc="upper right", fontsize=9, framealpha=0.95)
    fig.colorbar(im2, ax=ax, pad=0.02, label=r"$\log_{10}\,\Sigma\,(C_{obs}-C)^2$")

    # ---- (c) profile SSE over k-scale ----
    ax = axes[2]
    prof = surf["prof"]
    prof_s = surf["prof_s"]
    ax.plot(alphas, prof, color="#2980b9", lw=2.4, label=r"$J_{prof}(\alpha)=\min_S J(\alpha,S)$")
    ax.axvline(surf["argmin_alpha"], color="#7f8c8d", ls="--", lw=1.4)
    ax.set_xscale("log")
    ax.set_xlabel(r"$k$-scale $\alpha = k/k_{emp}$")
    ax.set_ylabel(r"Profile SSE $J_{prof}$ (mol$^2$ m$^{-6}$)", color="#2980b9")
    ax.tick_params(axis="y", labelcolor="#2980b9")
    ax.set_title("(c) Profile SSE over $k$-scale (not likelihood)", fontweight="bold")
    ax.grid(True, alpha=0.3, which="both")
    ax2 = ax.twinx()
    ax2.plot(alphas, prof_s, color="#e67e22", lw=2.0, ls=":", label=r"$\mathrm{arg\,min}_S\,J$ (analytical)")
    ax2.set_ylabel(r"Best uniform $S$ (mol m$^{-2}$ d$^{-1}$)", color="#e67e22")
    ax2.tick_params(axis="y", labelcolor="#e67e22")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper center", fontsize=10, framealpha=0.95)

    fig.suptitle(
        "Equifinality of gas-exchange $k$ and subgrid source $S_{sgs}$: objective surface and profile SSE",
        fontsize=15.5, fontweight="bold", y=1.02,
    )
    fig.tight_layout()
    fig.savefig(fig_dir / "equifinality_objective_surface.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)

    return {"rep_sample": rep.to_dict(), "flatness_span_decades": surf["flatness_span_decades"]}


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    require_real_data(cfg, "16_equifinality_surface")
    proc = resolve_path(cfg, "data_proc")
    fig_dir = resolve_path(cfg, "figures")
    tbl_dir = resolve_path(cfg, "tables")
    fig_dir.mkdir(parents=True, exist_ok=True)
    tbl_dir.mkdir(parents=True, exist_ok=True)
    validate_processed_observations(proc / "reach_daily_observations.csv")

    m = load_per_sample(cfg)
    surf = build_surface(m)

    # Load nested-CV operating points (k_eff for k-correction, S_ai for residual-AI)
    holdout = None
    hp = proc / "nested_cv_holdout_predictions.csv"
    if hp.exists():
        h = pd.read_csv(hp, parse_dates=["date"])
        h = h[h["cv_protocol"] == "loo_reach"].copy()
        kc = h[h["scheme"] == "k_correction"][["date", "reach_id", "sample_id", "k_CO2_m_d"]].rename(columns={"k_CO2_m_d": "k_eff"})
        ra = h[(h["scheme"] == "residual_ai") & (h["model"] == "mlp")][["date", "reach_id", "sample_id", "S_sgs_used_mol_m2d"]].rename(columns={"S_sgs_used_mol_m2d": "S_ai"})
        ho = m[["date", "reach_id", "sample_id", "k_CO2_m_d"]].rename(columns={"k_CO2_m_d": "k_emp"})
        ho = ho.merge(kc, on=["date", "reach_id", "sample_id"], how="inner")
        ho = ho.merge(ra, on=["date", "reach_id", "sample_id"], how="inner")
        holdout = ho

    meta = plot_surface(m, surf, fig_dir, holdout)

    summary = {
        "n": int(len(m)),
        "k_emp_median_m_d": float(m["k_CO2_m_d"].median()),
        "q_A_median_m_d": float(m["q_A_m_d"].median()),
        "q_A_source": "direct_86400_Q_routed_over_L_control_times_W (explicit keyed merge)",
        "q_A_direct_vs_inverse_max_abs_diff_m_d": float(
            np.nanmax(np.abs(m["q_A_direct_minus_inverse_m_d"].to_numpy(dtype=float)))
        )
        if m["q_A_direct_minus_inverse_m_d"].notna().any()
        else None,
        "boundary_source": "fixed observed upstream routed state per sample",
        "objective_name": "profile_SSE_not_likelihood",
        "weights": "equal_weight_per_sample",
        "shared_parameters": ["alpha (uniform k-scale)", "S (uniform source)"],
        "profile_interval": "rmse <= 1.10 * rmse_min over the alpha grid",
        "S_diag_median_mol_m2d": float(m["S_diag_mol_m2d"].median()),
        "dC_median_mol_m3": float(m["dC_mol_m3"].median()),
        "single_sample_zero_valley": True,
        "single_sample_profile_flat": True,
        "pooled_argmin_alpha": surf["argmin_alpha"],
        "pooled_argmin_s": surf["argmin_s"],
        "profile_flatness_span_decades": surf["flatness_span_decades"],
        "profile_flatness_log10_range": [surf["flatness_lo"], surf["flatness_hi"]],
        "profile_rmse_min": surf["rmse_min"],
        "profile_rmse_basin_range": [surf["rmse_basin_min"], surf["rmse_basin_max"]],
        "claims_scope": {
            "single_sample": (
                "algebraic under-determination of ONE equation with fixed C_in and two "
                "unknowns (k, S)"
            ),
            "pooled": (
                "equal-weight 120-sample SSE with a shared alpha and shared S and a fixed "
                "observed upstream state"
            ),
            "explicitly_NOT": [
                "network rerouting",
                "profile likelihood",
                "a confidence interval",
                "a statistical identifiability test",
            ],
            "planar_markers": (
                "model median parameters drawn for orientation only; they are descriptive "
                "markers, not fitted network operating points"
            ),
            "sensitivity_thresholds": "10% RMSE inflation used for the reported interval; "
            "no 5%/20% sensitivity is claimed",
        },
        "finding": (
            "A single concentration observation cannot identify (k, S) jointly: "
            "the per-sample objective has an exact zero valley S = S_diag + dC (k - k_emp), "
            "so the per-sample profile SSE is identically flat. This is an algebraic fact "
            "under fixed C_in, not a statistical likelihood. Pooling the samples with a "
            "uniform k-scale and source leaves the profile shallow: RMSE changes only "
            f"from {surf['rmse_basin_min']:.4f} to {surf['rmse_basin_max']:.4f} mol/m3 across "
            "the k-scale interval [0.01, 1]. Markers on the pooled plane are descriptive "
            "medians, not network operating points."
        ),
    }
    with (tbl_dir / "equifinality_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    LOG.info("Equifinality summary: %s", json.dumps(summary, indent=2))
    plt.close("all")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="k-S objective surface / profile SSE")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
