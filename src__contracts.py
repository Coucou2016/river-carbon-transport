#!/usr/bin/env python3
"""
Explicit data contracts for observations, cells, cell state, and OOF predictions.

These tables may coexist with report groupings (reach_id) but must not be
conflated: reach_id is a reporting group, not a unique physical control volume.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

# Required columns (minimal schema). Extra columns are allowed.
OBSERVATION_KEYS = ("sample_id", "date")
OBSERVATION_REQUIRED = (
    "sample_id",
    "date",
    "reach_id",
    "lat",
    "lon",
    "C_aq_obs_mol_m3",
    "T_C",
    "Q_m3s",
)

CELL_KEYS = ("cell_id",)
CELL_REQUIRED = (
    "cell_id",
    "flowline_id",
    "path_s_start_m",
    "path_s_end_m",
    "length_m",
    "area_m2",
    "geometry_version",
)

CELL_STATE_KEYS = ("date", "cell_id", "scenario_id")
CELL_STATE_REQUIRED = (
    "date",
    "cell_id",
    "scenario_id",
    "Q_in_m3s",
    "Q_out_m3s",
    "QC_in_mol_s",
    "QC_out_mol_s",
    "coverage_complete",
)

OOF_KEYS = ("run_id", "scheme", "model", "protocol", "sample_id", "date")
OOF_REQUIRED = (
    "run_id",
    "scheme",
    "model",
    "protocol",
    "sample_id",
    "date",
    "fold_id",
    "C_model_mol_m3",
    "C_obs_mol_m3",
)


class ContractError(ValueError):
    """Schema or uniqueness violation."""


def _require_columns(df: pd.DataFrame, required: tuple[str, ...], name: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ContractError(f"{name} missing columns: {missing}")


def _require_unique(df: pd.DataFrame, keys: tuple[str, ...], name: str) -> None:
    if df.duplicated(subset=list(keys)).any():
        n = int(df.duplicated(subset=list(keys)).sum())
        raise ContractError(f"{name}: {n} duplicate key(s) on {keys}")


def validate_observations(df: pd.DataFrame) -> pd.DataFrame:
    _require_columns(df, OBSERVATION_REQUIRED, "observations")
    _require_unique(df, OBSERVATION_KEYS, "observations")
    if (df["C_aq_obs_mol_m3"].isna()).any():
        raise ContractError("observations: NaN C_aq_obs_mol_m3 not allowed")
    return df


def validate_cells(df: pd.DataFrame) -> pd.DataFrame:
    _require_columns(df, CELL_REQUIRED, "cells")
    _require_unique(df, CELL_KEYS, "cells")
    if (df["length_m"] <= 0).any() or (df["area_m2"] <= 0).any():
        raise ContractError("cells: length_m and area_m2 must be positive")
    return df


def validate_cell_state(df: pd.DataFrame) -> pd.DataFrame:
    _require_columns(df, CELL_STATE_REQUIRED, "cell_state")
    _require_unique(df, CELL_STATE_KEYS, "cell_state")
    return df


def validate_oof_predictions(df: pd.DataFrame, *, expected_n: int | None = None) -> pd.DataFrame:
    _require_columns(df, OOF_REQUIRED, "oof_predictions")
    _require_unique(df, OOF_KEYS, "oof_predictions")
    if expected_n is not None and len(df) != expected_n:
        raise ContractError(
            f"oof_predictions: expected {expected_n} rows, got {len(df)}"
        )
    return df


def assert_one_to_one_merge(left: pd.DataFrame, right: pd.DataFrame, on: list[str]) -> None:
    """Fail if merge keys are not unique on both sides (prevents silent fan-out)."""
    if left.duplicated(subset=on).any():
        raise ContractError(f"left side has duplicate keys on {on}")
    if right.duplicated(subset=on).any():
        raise ContractError(f"right side has duplicate keys on {on}")


@dataclass(frozen=True)
class FoldContext:
    """Immutable fold context: frozen geometry + visible training labels only."""

    geometry_version: str
    train_keys: frozenset
    test_keys: frozenset
    boundary_policy: str
    allowed_driver_columns: tuple[str, ...] = ()
    meta: dict[str, Any] = field(default_factory=dict)

    def assert_no_test_in_train(self) -> None:
        overlap = self.train_keys & self.test_keys
        if overlap:
            raise ContractError(f"train/test key overlap: {list(overlap)[:5]}")


def sample_key(row: pd.Series | dict) -> tuple:
    """Canonical (date, reach_id, sample_id) key."""
    date = pd.Timestamp(row["date"]).normalize()
    rid = str(row["reach_id"])
    sid = row.get("sample_id") if hasattr(row, "get") else row["sample_id"] if "sample_id" in row.index else None
    return (date, rid, sid)


def keys_from_frame(df: pd.DataFrame) -> frozenset:
    return frozenset(sample_key(r) for _, r in df.iterrows())
