#!/usr/bin/env python3
"""Shared fold-local target construction for every model branch (P1-04).

Both the main transport branch (`12_nested_cv_transport`) and the sparse
Pi-group branch (`15_dimensionless_sparse`) must build their training targets
inside the fold, using training samples only. Duplicating that logic is how the
sparse branch silently kept full-data targets and full-data median imputation.

Everything here fails closed: geometry is fixed, but *labels* visible to a fold
are restricted to the training index.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.contracts import ContractError
from src.utils import setup_logging

LOG = setup_logging("fold_targets")

KEY_COLS = ("date", "reach_id", "sample_id")


def sample_keys(df: pd.DataFrame) -> list[str]:
    return [c for c in KEY_COLS if c in df.columns]


def key_frame(df: pd.DataFrame) -> pd.DataFrame:
    keys = sample_keys(df)
    out = df[keys].copy()
    out["date"] = pd.to_datetime(out["date"]).dt.normalize()
    out["reach_id"] = out["reach_id"].astype(str)
    if "sample_id" in out.columns:
        out["sample_id"] = out["sample_id"].astype(str)
    return out


def held_out_key_set(obs: pd.DataFrame, te_idx: np.ndarray) -> set[tuple]:
    te = key_frame(obs.iloc[te_idx])
    return set(map(tuple, te.to_numpy()))


def fold_diagnose(
    obs: pd.DataFrame,
    obs_seg: pd.DataFrame,
    seg_df: pd.DataFrame,
    tr_idx: np.ndarray,
    te_idx: np.ndarray,
    diagnose_fn,
) -> pd.DataFrame:
    """Diagnose S_sgs / C_in using training rows only.

    ``diagnose_fn`` is ``src.real_network.diagnose_sgs`` (passed in to avoid a
    circular import).
    """
    te_keys = held_out_key_set(obs, te_idx)
    seg_keys = key_frame(obs_seg)
    mask = np.array([tuple(r) not in te_keys for r in seg_keys.to_numpy()], dtype=bool)
    train_seg = obs_seg.loc[mask].copy()
    if train_seg.empty:
        return pd.DataFrame()
    return diagnose_fn(train_seg, seg_df)


def fold_sgs_targets(
    obs: pd.DataFrame,
    obs_seg: pd.DataFrame,
    seg_df: pd.DataFrame,
    tr_idx: np.ndarray,
    te_idx: np.ndarray,
    diagnose_fn,
) -> np.ndarray:
    """Fold-local S_sgs targets for the *training* index (NaN on held-out)."""
    diag = fold_diagnose(obs, obs_seg, seg_df, tr_idx, te_idx, diagnose_fn)
    y = np.full(len(obs), np.nan, dtype=float)
    if diag.empty:
        return y
    keys = sample_keys(obs)
    train = key_frame(obs.iloc[tr_idx]).assign(_row_id=np.asarray(tr_idx))
    merged = train.merge(
        key_frame(diag).assign(S_sgs_mol_m2d=diag["S_sgs_mol_m2d"].to_numpy(dtype=float)),
        on=keys,
        how="left",
        validate="one_to_one",
    ).sort_values("_row_id")
    if merged["S_sgs_mol_m2d"].isna().any():
        missing = int(merged["S_sgs_mol_m2d"].isna().sum())
        LOG.warning("%d training row(s) have no fold-local S_sgs target", missing)
    y[np.asarray(tr_idx)] = merged["S_sgs_mol_m2d"].to_numpy(dtype=float)
    return y


def fold_diagnostic_frame(
    obs: pd.DataFrame,
    obs_seg: pd.DataFrame,
    seg_df: pd.DataFrame,
    tr_idx: np.ndarray,
    te_idx: np.ndarray,
    diagnose_fn,
    extra_cols: tuple[str, ...] = ("C_in_obs_mol_m3", "L_control_m", "Q_routed_m3s"),
) -> pd.DataFrame:
    """Fold-local diagnosis merged onto the training rows (one row per key)."""
    diag = fold_diagnose(obs, obs_seg, seg_df, tr_idx, te_idx, diagnose_fn)
    keys = sample_keys(obs)
    train = key_frame(obs.iloc[tr_idx]).assign(_row_id=np.asarray(tr_idx))
    if diag.empty:
        for c in extra_cols:
            train[c] = np.nan
        return train
    cols = [c for c in extra_cols if c in diag.columns]
    merged = train.merge(
        key_frame(diag)[keys].assign(**{c: diag[c].to_numpy() for c in cols}),
        on=keys,
        how="left",
        validate="one_to_one",
    )
    if merged.duplicated(subset=["_row_id"]).any():
        raise ContractError("fold diagnostic merge duplicated training rows")
    return merged.sort_values("_row_id").reset_index(drop=True)


def fold_preprocessor(X: pd.DataFrame, tr_idx: np.ndarray) -> tuple[pd.DataFrame, pd.Series]:
    """Train-fold median imputation, computed on training rows only (P1-04).

    Returns ``(X_imputed_full, median_used)``. All-missing feature columns are
    dropped; if that empties the matrix the fold fails closed.
    """
    med = X.iloc[tr_idx].median(numeric_only=True)
    keep = med.notna()
    if not bool(keep.any()):
        raise ContractError("fold_preprocessor: every feature column is all-NA in train")
    dropped = [c for c in X.columns if c not in set(med.index[keep])]
    if dropped:
        LOG.info("fold_preprocessor: dropping all-NA-in-train columns %s", dropped)
    return X.loc[:, keep].fillna(med[keep]), med[keep]


def assert_fold_target_isolation(
    obs: pd.DataFrame,
    tr_idx: np.ndarray,
    te_idx: np.ndarray,
    y_fold: np.ndarray,
) -> None:
    """Exactly one finite-vs-NaN pattern: targets exist only on training rows."""
    overlap = set(np.asarray(tr_idx).tolist()) & set(np.asarray(te_idx).tolist())
    if overlap:
        raise ContractError(f"train/test index overlap: {sorted(overlap)[:5]}")
    if np.isfinite(y_fold[np.asarray(te_idx)]).any():
        raise ContractError("held-out rows carry training targets (fold leakage)")
