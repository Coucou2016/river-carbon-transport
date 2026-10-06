#!/usr/bin/env python3
"""Claim-guard verification for paper.md / paper.html and the frozen results.

Two modes:

``development``
    Warnings are allowed; exits non-zero only on hard structural errors.
``submission``
    Fail-closed.  Besides the historical checks (RMSE drift vs the claim guard,
    forbidden claim phrases, saturation policy, stale figure archive) it now
    verifies the 2026-09-27 acceptance list:

      * the generator's number formatter reports ratios instead of classifying
        them (``fmt_ratio(0.5399906833903203) == "0.540"``);
      * ``paper_values.json`` is consistent with the machine tables it claims to
        summarise (direction assertions, not just string equality);
      * the geometry/domain gate flags the R002 measure inconsistency
        (ΣL_control ≠ recorded support) and every other unverified reach;
      * no held-out prediction is a silent zero / clip, and every row carries a
        finite mass-balance residual;
      * the sparse branch was trained on fold-local targets with training-only
        imputation (no full-data labels), and the displayed equation has the
        documented three non-zero terms and no ``_z`` in the original-variable
        equation;
      * the k floor is not saturated and the paired k ratio is the measured
        value, not a class label;
      * every figure's PNG hash matches its sidecar ``output_sha256`` and its
        declared source tables still hash the same as when the sidecar was
        written.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TABLES = ROOT / "results" / "tables"
FIG_DIR = ROOT / "results" / "figures"
SIDECAR_DIR = FIG_DIR / "sidecars"
DATA_PROC = ROOT / "data_proc"
MD = ROOT / "paper.md"
HTML = ROOT / "paper.html"

# Phrases that must not appear as affirmative scientific claims.
FORBIDDEN_PHRASES = [
    "mass-conservative filter",
    "mass-conservative aggregation",
    "independent cells",
    "genuine unresolved process",
    "summed over the study area",
    "nested cross-validation",  # no inner hyperparameter loop implemented
]

# The ten manuscript figures, in first-mention order.
FIGURE_ORDER = [
    "les_filter_conceptual.png",
    "figure2_reach_assignment_and_samples.png",
    "nested_cv_rmse_bar.png",
    "nested_cv_scatter_holdout.png",
    "subgroup_rmse_r008_vs_trib.png",
    "supp_flux_diagnostics.png",
    "filter_scale_sgs.png",
    "filter_scale_sgs_box.png",
    "dimensionless_coefficients.png",
    "equifinality_objective_surface.png",
]

# Figures explicitly archived as historical (never fuzzy-matched into the paper).
STALE_FIGURE_MARKERS = ["results/figures/paper"]


class Report:
    def __init__(self, submission: bool) -> None:
        self.submission = submission
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def fail(self, msg: str) -> None:
        self.errors.append(msg)
        print(f"FAIL: {msg}")

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        print(f"WARN: {msg}")

    def check(self, condition: bool, msg: str) -> bool:
        """Hard check in submission mode; warning otherwise (returns success)."""
        if condition:
            return True
        if self.submission:
            self.fail(msg)
        else:
            self.warn(msg + " (development mode)")
        return False


def _sha256(path: Path) -> str | None:
    from src.figure_sidecar import sha256_file

    return sha256_file(path)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_fmt_ratio(rep: Report) -> None:
    """P0-01 regression: the formatter must report values, not classify them."""
    try:
        from scripts.paper_values import fmt_ratio
    except Exception:  # pragma: no cover - path bootstrap differences
        from paper_values import fmt_ratio  # type: ignore

    cases = [
        (0.5399906833903203, "0.540"),
        (1.0, "1.000"),
        (0.0944555603113767, "0.094"),
        (float("nan"), "\u2014"),
        (None, "\u2014"),
    ]
    for value, expected in cases:
        got = fmt_ratio(value)
        rep.check(
            got == expected,
            f"fmt_ratio({value!r}) returned {got!r}, expected {expected!r}",
        )


def _check_paper_values(rep: Report) -> dict:
    """P0-01: the single numeric object must agree with the machine tables."""
    pv_path = TABLES / "paper_values.json"
    if not pv_path.exists():
        rep.check(False, "results/tables/paper_values.json missing")
        return {}
    pv = _load_json(pv_path)

    # --- direction assertions: compare against the raw machine tables ---------
    try:
        import pandas as pd

        nested = pd.read_csv(TABLES / "nested_cv_metrics.csv")
        loo = nested[(nested["cv_protocol"] == "loo_reach") & (nested["subgroup"] == "all_120")]

        def rmse(scheme: str, model: str):
            hit = loo[(loo["scheme"] == scheme) & (loo["model"] == model)]
            return float(hit["rmse_c"].iloc[0]) if len(hit) else None

        mlp = rmse("residual_ai", "mlp")
        base = rmse("baseline", "none")
        rf = rmse("residual_ai", "random_forest")
        kcorr = rmse("k_correction", "xgboost")

        rep.check(
            pv["main_results"]["mlp"]["rmse_c"] == round(mlp, 6),
            f"paper_values mlp.rmse_c={pv['main_results']['mlp']['rmse_c']} != table {mlp}",
        )
        rep.check(
            pv["main_results"]["baseline"]["rmse_c"] == round(base, 6),
            f"paper_values baseline.rmse_c != table {base}",
        )
        # The boolean must match the actual comparison, so the sentence direction
        # ("MLP is not lower than Baseline") cannot drift.
        expected_bool = bool(mlp < base - 1e-12)
        rep.check(
            bool(pv["main_results"].get("mlp_rmse_lt_baseline")) == expected_bool,
            "paper_values.mlp_rmse_lt_baseline disagrees with the machine tables",
        )
        rep.check(
            pv["main_results"]["random_forest"]["rmse_c"] == round(rf, 6),
            "paper_values rf.rmse_c disagrees with the machine tables",
        )
        rep.check(
            pv["main_results"]["k_correction"]["rmse_c"] == round(kcorr, 6),
            "paper_values k_correction.rmse_c disagrees with the machine tables",
        )

        # --- counting estimands must be dynamically generated ---------------
        counting = pv.get("counting", {})
        obs = pd.read_csv(DATA_PROC / "reach_daily_observations.csv")
        if "is_campaign_sample" in obs.columns:
            obs = obs[obs["is_campaign_sample"].astype(bool)]
        rep.check(
            int(counting.get("n_campaign_samples") or -1) == int(len(obs)),
            f"paper_values n_campaign_samples={counting.get('n_campaign_samples')} != {len(obs)}",
        )
        gc = {str(k): int(v) for k, v in (counting.get("group_counts") or {}).items()}
        real = {str(k): int(v) for k, v in obs.groupby(obs["reach_id"].astype(str)).size().items()}
        rep.check(gc == real, f"paper_values group_counts {gc} != observed {real}")
        mr = pd.read_csv(DATA_PROC / "gis_reach_line_mapping.csv")
        real_map = {str(k): int(v) for k, v in mr.groupby(mr["reach_id"].astype(str)).size().items()}
        mc = {str(k): int(v) for k, v in (counting.get("group_mapping_counts") or {}).items()}
        rep.check(mc == real_map, f"paper_values group_mapping_counts {mc} != mapping table {real_map}")
        # The two estimands must not be silently conflated.
        rep.check(
            gc != mc,
            "group_counts and group_mapping_counts are identical; estimands were conflated",
        )
    except Exception as exc:  # noqa: BLE001
        rep.check(False, f"paper_values consistency check raised: {exc}")

    # --- sparse equation: documented terms, no `_z` in original form --------
    sparse = pv.get("sparse", {})
    eq_std = str(sparse.get("equation_standardized_Sstar") or "")
    # The 2026-09-27 bug was that log10(Da) was dropped from the displayed
    # relation; the frozen run must retain it as a non-zero predictor.
    rep.check("log10(Da)" in eq_std, "sparse standardized equation lost the log10(Da) term")
    for term in ("Fr", "h/W", "log10(Da)"):
        rep.check(term in eq_std, f"sparse standardized equation missing {term}")
    # The three *dominant* terms (the sentence quotes three) must include Da.
    dom = str(sparse.get("dominant_standardized") or "")
    rep.check(
        int(sparse.get("n_terms_standardized") or 0) >= 3,
        f"sparse equation reports {sparse.get('n_terms_standardized')} standardized terms, expected >=3",
    )
    rep.check("log10(Da)_z" in dom, f"sparse dominant terms lost log10(Da): {dom!r}")
    eq_orig = str(sparse.get("equation_original_Sstar") or "")
    rep.check(
        "_z" not in eq_orig,
        f"sparse original-variable equation still contains `_z`: {eq_orig}",
    )
    rep.check(bool(eq_orig), "sparse original-variable equation missing")

    # --- paired k ratio and floor saturation must be measured ---------------
    kest = pv.get("k_estimate", {})
    sat_frac = kest.get("floor_saturation_fraction")
    rep.check(sat_frac is not None, "k floor saturation fraction missing (never default it)")
    if sat_frac is not None:
        rep.check(
            -1e-9 <= float(sat_frac) <= 1e-6,
            f"k floor is saturated: frac_at_floor_oof={sat_frac} (expected ~0 in the frozen run)",
        )
    kratio = kest.get("k_ratio_median")
    disp = kest.get("k_ratio_median_display")
    rep.check(
        disp == f"{float(kratio):.3f}" if kratio is not None else False,
        f"k ratio display {disp!r} does not report the measured value {kratio!r}",
    )

    # --- constraint diagnostics (P0-03) ------------------------------------
    cd = pv.get("constraint_diagnostics", {})
    rep.check((cd or {}).get("n_oof_rows"), "constraint_diagnostics.n_oof_rows missing")
    if cd.get("n_C_model_at_zero") is not None:
        rep.check(
            int(cd["n_C_model_at_zero"]) == 0,
            f"{cd['n_C_model_at_zero']} held-out predictions are exactly zero (silent clip)",
        )
    if cd.get("unconstrained_failure_count") is not None:
        rep.check(
            int(cd["unconstrained_failure_count"]) == 0,
            f"{cd['unconstrained_failure_count']} held-out rows are physically infeasible "
            "before the bound (unconstrained failure)",
        )
    resid = cd.get("max_abs_mass_balance_residual_mol_s")
    rep.check(resid is not None, "constraint_diagnostics mass-balance residual missing")
    if resid is not None:
        rep.check(
            abs(float(resid)) < 1e-6,
            f"max |mass balance residual| = {resid} mol/s exceeds the 1e-6 tolerance",
        )
    # The reported RMSE must be the post-constraint number, not a pre-constraint one.
    try:
        import pandas as pd

        holdout = pd.read_csv(DATA_PROC / "nested_cv_holdout_predictions.csv")
        loo = holdout[holdout["cv_protocol"] == "loo_reach"]
        import numpy as np

        err = (loo["C_model_mol_m3"] - loo["C_obs_mol_m3"]).to_numpy()
        # Pooled across schemes is meaningless; check per scheme/model instead.
        for (scheme, model), g in loo.groupby(["scheme", "model"]):
            e = (g["C_model_mol_m3"].astype(float) - g["C_obs_mol_m3"].astype(float)).to_numpy()
            e = e[np.isfinite(e)]
            if not len(e):
                continue
            got = float(np.sqrt(np.mean(e**2)))
            want = (cd.get("post_constraint_rmse") or {}).get(f"{scheme}/{model}")
            if want is None:
                rep.check(False, f"post_constraint_rmse missing for {scheme}/{model}")
                continue
            rep.check(
                abs(got - float(want)) < 1e-6,
                f"post-constraint RMSE for {scheme}/{model}: values={got} json={want}",
            )
        del err
    except Exception as exc:  # noqa: BLE001
        rep.check(False, f"post-constraint RMSE check raised: {exc}")

    # --- geometry / domain consistency gate (P0-02) -------------------------
    gate_path = TABLES / "domain_consistency_gate.csv"
    if not gate_path.exists():
        rep.check(False, "results/tables/domain_consistency_gate.csv missing")
    else:
        import pandas as pd

        g = pd.read_csv(gate_path)
        geo = pv.get("geometry", {})
        # R002 must be flagged: ΣL_control is not the recorded support length.
        r002 = g[g["reach_id"].astype(str) == "R002"]
        if len(r002):
            ratio = geo.get("r002_ratio")
            rep.check(
                ratio is None or abs(float(ratio) - 1.0) > 1e-6,
                "R002 ΣL_control / recorded support == 1.0; the measure inconsistency is not flagged",
            )
            rep.check(
                not bool(r002["domain_consistent"].any()),
                "R002 is marked domain-consistent even though its control lengths do not "
                "match the recorded support (P0-02 gate must fail closed)",
            )
        flagged = sorted(g.loc[~g["domain_consistent"], "reach_id"].astype(str).unique())
        rep.check(bool(flagged), "domain gate flagged no reach; it must reject the current R002 state")
        rep.check(
            sorted(geo.get("gate_flagged_reaches") or []) == flagged,
            f"paper_values gate_flagged_reaches {geo.get('gate_flagged_reaches')} != gate table {flagged}",
        )
        # Unverified support must never be reported as a verified NHD domain.
        # `recorded_support_basis` values are e.g. "verified_path_domain" or
        # "provisional_sample_gps_span"; an inconsistent reach whose basis is
        # *exactly* the verified label is a contradiction.  Substring matching on
        # "verified" would also flag "unverified_...", which is honest.
        bad_basis = g[
            (~g["domain_consistent"])
            & (g["recorded_support_basis"].astype(str).str.strip() == "verified_path_domain")
        ]
        rep.check(
            len(bad_basis) == 0,
            "an inconsistent reach claims the verified_path_domain support basis",
        )

    # --- reach sensitivity: no manufactured statistics ---------------------
    sens = pv.get("reach_sensitivity", {})
    rep.check(bool(sens.get("row_unit")), "reach_sensitivity.row_unit missing")
    rep.check(bool(sens.get("weights")), "reach_sensitivity.weights missing")

    def _stat_keys(d, prefix="") -> list[str]:
        out: list[str] = []
        if isinstance(d, dict):
            for k, v in d.items():
                out += _stat_keys(v, f"{prefix}{k}")
        elif isinstance(d, list):
            for v in d:
                out += _stat_keys(v, prefix)
        return out

    # Only key names count: the note legitimately *denies* fabricating these.
    key_names = " ".join(_stat_keys(sens)).lower()
    for banned in ("p_value", "pvalue", "ci_low", "ci_high", "confidence_interval", "bootstrap"):
        rep.check(banned not in key_names, f"reach_sensitivity contains fabricated statistic key {banned!r}")

    return pv


def _machine_table1_ground_truth() -> dict:
    """Re-derive every Table 1 count from the machine tables (P1-08 / R3-m6).

    Deliberately independent of ``paper_values.json``: the verifier reads the
    raw DataFrames itself so the gate catches both a stale ``paper_values.json``
    and a stale rendered table.
    """
    import json as _json

    import pandas as pd

    reaches = ("R001", "R002", "R003", "R004", "R005", "R006", "R007", "R008")
    obs = pd.read_csv(DATA_PROC / "reach_daily_observations.csv")
    if "is_campaign_sample" in obs.columns:
        obs = obs[obs["is_campaign_sample"].astype(bool)]
    obs = obs.copy()
    obs["reach_id"] = obs["reach_id"].astype(str)
    mapping = pd.read_csv(DATA_PROC / "gis_reach_line_mapping.csv")
    mapping["reach_id"] = mapping["reach_id"].astype(str)
    segments = pd.read_csv(DATA_PROC / "network_segments.csv")

    joins: dict[str, str] = {}
    for _, r in segments.iterrows():
        if not bool(r.get("is_mainstem", False)):
            continue
        upstream = r.get("upstream")
        if isinstance(upstream, str):
            try:
                upstream = _json.loads(upstream)
            except Exception:
                upstream = []
        for u in upstream or []:
            u = str(u)
            if u in reaches and u != "R008":
                joins[u] = str(r["segment_id"])

    truth: dict[str, dict] = {}
    for rid in reaches:
        sub_map = mapping[mapping["reach_id"] == rid]
        sub_obs = obs[obs["reach_id"] == rid]
        truth[rid] = {
            "joins_mainstem": joins.get(rid, "outlet"),
            "assigned_flowlines": int(len(sub_map)),
            "assigned_gnis_match": int((sub_map["assign_method"] == "gnis_match").sum()),
            "assigned_nearest_sample": int(
                (sub_map["assign_method"] == "nearest_campaign_sample").sum()
            ),
            "routing_segments": int((segments["reach_id"].astype(str) == rid).sum()),
            "sampled_cells": int(sub_obs["physical_cell_id"].nunique()),
            "campaign_samples": int(len(sub_obs)),
        }
    truth["_raw_pool"] = int(len(mapping))
    return truth


def _parse_rendered_table1(text: str) -> dict:
    """Extract ``{reach_id: [cells...]}`` from a rendered markdown or HTML table."""
    import re

    reaches = {"R001", "R002", "R003", "R004", "R005", "R006", "R007", "R008"}
    out: dict[str, list[str]] = {}
    if "<td" in text:
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", text, flags=re.S | re.I):
            cells = [
                re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ").strip()
                for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S | re.I)
            ]
            if cells and cells[0] in reaches and cells[0] not in out:
                out[cells[0]] = cells
    else:
        for line in text.splitlines():
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and cells[0] in reaches and cells[0] not in out:
                out[cells[0]] = cells
    return out


def _check_table1_counts(rep: Report) -> None:
    """P1-08 / R3-m6: rendered Table 1 must equal the machine-table values.

    Four objects shared the word "segment": raw corridor flowline, assigned
    corridor line, logical routing segment, sampled control volume.  Every
    number in the rendered table must match the machine tables, so a
    hand-written count cannot survive.      In submission mode a mismatch is a
    hard failure, mirroring the ``group_mapping_counts`` gate.
    """
    import re

    try:
        truth = _machine_table1_ground_truth()
    except Exception as exc:  # noqa: BLE001
        rep.check(False, f"Table 1 ground truth could not be derived: {exc}")
        return

    pv = _load_json(TABLES / "paper_values.json") if (TABLES / "paper_values.json").exists() else {}
    t1 = (pv or {}).get("table1") or {}
    pv_rows = {str(r.get("reach_id")): r for r in (t1.get("rows") or [])}

    # --- paper_values.json itself must agree with the raw tables ------------
    for rid, want in truth.items():
        if rid.startswith("_"):
            continue
        got = pv_rows.get(rid)
        if got is None:
            rep.check(False, f"paper_values.table1 missing reach {rid}")
            continue
        for key in (
            "joins_mainstem",
            "assigned_flowlines",
            "assigned_gnis_match",
            "assigned_nearest_sample",
            "routing_segments",
            "sampled_cells",
            "campaign_samples",
        ):
            rep.check(
                got.get(key) == want[key],
                f"paper_values.table1[{rid}].{key}={got.get(key)!r} != machine {want[key]!r}",
            )
    rep.check(
        int(t1.get("raw_corridor_pool_n") or -1) == truth["_raw_pool"],
        f"paper_values.table1.raw_corridor_pool_n={t1.get('raw_corridor_pool_n')} != {truth['_raw_pool']}",
    )
    # The four estimands must not be silently identical objects.
    rep.check(
        bool(t1.get("estimands")),
        "paper_values.table1.estimands definitions missing (estimands would be conflated)",
    )

    # --- the rendered tables must agree with the machine tables -------------
    column_index = {
        "joins_mainstem": 3,
        "assigned_flowlines": 5,
        "assigned_gnis_match": 6,
        "assigned_nearest_sample": 7,
        "routing_segments": 8,
        "sampled_cells": 9,
        "campaign_samples": 10,
    }
    for path in (MD, HTML, ROOT / "report.md", ROOT / "report.html"):
        if not path.exists():
            continue
        parsed = _parse_rendered_table1(path.read_text(encoding="utf-8", errors="ignore"))
        if not parsed:
            rep.check(False, f"{path.name} has no parseable Table 1 rows")
            continue
        for rid, want in truth.items():
            if rid.startswith("_"):
                continue
            cells = parsed.get(rid)
            if cells is None:
                rep.check(False, f"{path.name} Table 1 missing row {rid}")
                continue
            for key, idx in column_index.items():
                if idx >= len(cells):
                    rep.check(False, f"{path.name} Table 1 {rid} missing column {key}")
                    continue
                cell = cells[idx]
                if key == "joins_mainstem":
                    ok = cell == str(want[key])
                else:
                    digits = re.sub(r"[^\d]", "", cell)
                    ok = bool(digits) and int(digits) == int(want[key])
                rep.check(
                    ok,
                    f"{path.name} Table 1 {rid}.{key}={cell!r} != machine {want[key]!r}",
                )


def _check_figures(rep: Report) -> None:
    """Part B item 11: sidecar presence, PNG hash, and source-table hashes."""
    from src.figure_sidecar import REQUIRED_KEYS, sha256_file

    for name in FIGURE_ORDER:
        img = FIG_DIR / name
        if not img.exists():
            rep.check(False, f"manuscript figure missing: {name}")
            continue
        side = SIDECAR_DIR / f"{Path(name).stem}.json"
        if not side.exists():
            rep.check(False, f"figure sidecar missing for {name}")
            continue
        meta = _load_json(side)
        missing = [k for k in REQUIRED_KEYS if meta.get(k) in (None, "", {})]
        # `source_table_sha256` may legitimately be empty for a pure schematic.
        missing = [k for k in missing if not (k == "source_table_sha256" and meta.get(k) == {})]
        rep.check(not missing, f"sidecar {side.name} missing keys: {missing}")

        want = meta.get("output_sha256")
        got = sha256_file(img)
        rep.check(
            bool(want) and want == got,
            f"figure {name} hash changed since its sidecar was written "
            f"(stale figure; re-run the generator)",
        )
        for src, expected in (meta.get("source_table_sha256") or {}).items():
            if not expected:
                rep.warn(f"sidecar {side.name}: source {src} had no hash at write time")
                continue
            path = Path(src) if Path(src).is_absolute() else ROOT / src
            current = sha256_file(path)
            rep.check(
                current == expected,
                f"figure {name}: source table {src} changed since the figure was rendered",
            )

    # Archived stale figures must be explicitly labelled, never silently reused.
    for marker in STALE_FIGURE_MARKERS:
        d = ROOT / marker
        if d.exists() and not (d / "HISTORICAL_README.md").exists():
            rep.check(
                False,
                f"{marker} exists without HISTORICAL_README.md (archive old figures explicitly)",
            )

    # Figures referenced in the paper must be in FIGURE_ORDER (no fuzzy matching).
    for path, label in ((MD, "paper.md"), (HTML, "paper.html")):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name in FIGURE_ORDER:
            stem = Path(name).stem
            if stem in text and name not in text:
                # Reference by stem only (e.g. an HTML alias) is a drift risk.
                rep.warn(f"{label} references {stem} without the exact file {name}")

    _check_embedded_images(rep)
    _check_figure_numbering(rep)
    _check_regeneration_wiring(rep)


def _check_regeneration_wiring(rep: Report) -> None:
    """P2-09: every committed provenance/artifact view must declare how it is rebuilt.

    ``run_pipeline.py`` owns the stage graph.  This gate keeps the contract
    honest in the opposite direction from the artifact manifest: for each
    provenance artifact we commit on purpose (figure sidecars, the Figure 2
    basemap manifest, the derived archive manifest, ``paper_values.json``,
    ``figure_sidecar_index.json``, the script-stage table outputs) it asserts
    that *some* stage declares that path as an output.  A path that exists but
    no stage produces is an orphan with no documented regeneration command.
    """
    sys.path.insert(0, str(ROOT))
    try:
        import run_pipeline  # noqa: PLC0415
    except Exception as exc:  # pragma: no cover - import bootstrap differences
        rep.warn(f"could not import run_pipeline to check regeneration wiring: {exc}")
        return

    declared: set[str] = set()
    if hasattr(run_pipeline, "STAGES"):
        for stage in run_pipeline.STAGES:
            outputs = stage[3] if len(stage) >= 4 else []
            declared.update(str(o) for o in outputs)

    if not declared:
        rep.warn("run_pipeline.STAGES declared no outputs; regeneration wiring unverified")
        return

    expected = {
        "results/tables/paper_values.json": "single numeric source of truth",
        "results/tables/figure_sidecar_index.json": "figure sidecar index",
        "results/tables/per_reach_paired_metrics.csv": "P1-07 per-reach statistics",
        "results/tables/reach_sensitivity.json": "P1-07 leave-out sensitivity",
    }
    for rel, why in expected.items():
        rep.check(
            rel in declared,
            f"{rel} ({why}) is not declared as an output of any run_pipeline stage",
        )

    # Every committed sidecar for a manuscript figure must sit next to a figure
    # that some stage declares it renders.
    for name in FIGURE_ORDER:
        side = SIDECAR_DIR / f"{Path(name).stem}.json"
        if not side.exists():
            continue
        rep.check(
            f"results/figures/{name}" in declared,
            f"committed sidecar {side.name} has no stage declaring results/figures/{name}",
        )

    for rel in (
        "results/figures/figure2_basemap_manifest.json",
        "results/figures/paper/derived_archive_manifest.json",
    ):
        rep.check(rel in declared, f"provenance artifact {rel} is not regenerable by any stage")

    # Verify the committed archive mirror: results/figures/paper/ is
    # version-controlled, so a reader browsing the repo must see the same bytes
    # the documents embed. Checks are re-derived from disk (not trusted from the
    # manifest), so tampering is caught; the manifest is then required to agree
    # with what we measured.
    from src.figure_sidecar import sha256_file

    archive = FIG_DIR / "paper" / "derived_archive_manifest.json"
    if not archive.exists():
        rep.check(
            False,
            "results/figures/paper/derived_archive_manifest.json missing; run stage 19",
        )
        return
    try:
        data = _load_json(archive)
    except Exception as exc:  # noqa: BLE001
        rep.check(False, f"could not read {archive.name}: {exc}")
        return

    figs = data.get("figures") or {}
    rep.check(bool(figs), "archive manifest lists no published figures")

    mismatches: list[str] = []
    for name, meta in figs.items():
        archived = FIG_DIR / "paper" / name
        canonical = FIG_DIR / name
        if not archived.exists():
            mismatches.append(f"{name}(archived missing)")
            continue
        got_arch = sha256_file(archived)
        got_live = sha256_file(canonical)
        recorded_arch = meta.get("archived_png_sha256")
        recorded_live = meta.get("canonical_png_sha256")
        # Recomputed truth: archived bytes must equal the live bytes.
        if got_live is None or got_arch != got_live:
            mismatches.append(f"{name}(drift)")
        # Manifest must describe the bytes actually on disk, so deleting a PNG
        # or editing the manifest cannot hide a mismatch.
        if recorded_arch != got_arch or recorded_live != got_live:
            mismatches.append(f"{name}(manifest stale or edited)")

    rep.check(
        not mismatches,
        "results/figures/paper is not a byte-exact mirror of the live figures: "
        f"{len(mismatches)} problem(s) "
        f"({', '.join(sorted(mismatches)[:4])}{', ...' if len(mismatches) > 4 else ''}); "
        "re-run stage 19 (scripts/build_figure_sidecars.py)",
    )

    for hist in data.get("historical_figures") or []:
        rep.check(
            bool(hist.get("reason")) and bool(hist.get("action")),
            f"historical archive entry {hist.get('name')!r} lacks a documented reason/action",
        )

    # Any published figure the documents embed must be mirrored in the archive.
    for name in FIGURE_ORDER:
        if name in figs:
            continue
        # A manuscript figure with a committed sidecar is published; it must be
        # mirrored, otherwise the repo shows fewer figures than the paper.
        if (SIDECAR_DIR / f"{Path(name).stem}.json").exists():
            rep.check(False, f"manuscript figure {name} is not mirrored in results/figures/paper/")


def _check_embedded_images(rep: Report) -> None:
    """Part B item 11: base64 images inlined in the HTML must match the PNGs.

    Both ``paper.html`` and ``report.html`` embed their figures as base64 data
    URIs, so the HTML can silently keep an *older* render than the PNG on disk.
    Every embedded ``data:image/png;base64,...`` payload is decoded and its
    SHA-256 compared with the ``output_sha256`` of the corresponding figure
    sidecar; a mismatch means the HTML and the figure files disagree.
    """
    import base64
    import hashlib
    import re

    by_hash: dict[str, str] = {}
    for name in FIGURE_ORDER:
        side = SIDECAR_DIR / f"{Path(name).stem}.json"
        if not side.exists():
            continue
        meta = _load_json(side)
        want = meta.get("output_sha256")
        if want:
            by_hash[str(want)] = name

    for path, label in ((HTML, "paper.html"), (REPORT_HTML, "report.html"), (REPORT_MD, "report.md")):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        payloads = re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]+)", text)
        if not payloads:
            continue
        matched = 0
        for payload in payloads:
            try:
                digest = hashlib.sha256(base64.b64decode(payload)).hexdigest()
            except Exception:  # noqa: BLE001
                continue
            if digest in by_hash:
                matched += 1
        # Only require a match for images that are one of our sidecar figures;
        # a report may legitimately embed extra appendix PNGs.
        if matched == 0:
            rep.check(
                False,
                f"{label} embeds {len(payloads)} base64 PNG(s) but none match any "
                "manuscript figure sidecar hash (stale or unverified embed)",
            )
        elif matched < len(FIGURE_ORDER):
            rep.warn(
                f"{label} embeds {matched}/{len(FIGURE_ORDER)} manuscript figures by "
                "sidecar hash (remaining embeds are appendix/other images)"
            )


def _check_figure_numbering(rep: Report) -> None:
    """Part B item 5/2: figures must be numbered by *first mention* in the text.

    The earlier draft embedded Figure 2 before Figure 1 and cited the
    equifinality surface as Figure 5, so a reader following ``Figure N``
    references arrived at the wrong picture.  This gate walks the rendered
    Markdown and asserts that the first appearance of each ``Figure N`` token is
    monotonically increasing, that every ``Figure N`` has an embedded image in
    the same order as FIGURE_ORDER, and that no leftover supplementary
    (``Figure S*``) numbering survives anywhere in the manuscript.
    """
    import re

    if not MD.exists():
        return
    md = MD.read_text(encoding="utf-8", errors="ignore")

    # 1. embedded images, in document order, must equal FIGURE_ORDER
    embedded = [
        Path(p).name for p in re.findall(r"\]\((results/figures/[^)]+)\)", md)
    ]
    rep.check(
        embedded == FIGURE_ORDER,
        "paper.md embeds figures in a different order than FIGURE_ORDER "
        f"(got {embedded})",
    )

    # 2. first mention of each number must be strictly increasing & complete
    first_seen: list[int] = []
    for m in re.finditer(r"Figure\s+(\d+)", md):
        n = int(m.group(1))
        if n not in first_seen:
            first_seen.append(n)
    expected = list(range(1, len(FIGURE_ORDER) + 1))
    rep.check(
        first_seen == expected,
        f"figures are not numbered by first mention: order {first_seen}, expected {expected}",
    )

    # 3. no residual supplementary numbering and no stale figure files
    supp = re.findall(r"Figure\s+S\d+", md)
    rep.check(not supp, f"paper.md still uses supplementary numbering: {sorted(set(supp))}")

    # 4. caption number must match the position of the embedded image
    block_matches = re.findall(
        r"!\[(?:<strong>)?Figure\s+(\d+)\..*?\]\(results/figures/([^)]+)\)", md, re.S
    )
    for idx, (num, fname) in enumerate(block_matches, start=1):
        rep.check(
            int(num) == idx and Path(fname).name == FIGURE_ORDER[idx - 1],
            f"Figure {idx} caption/file mismatch: caption says Figure {num} on {Path(fname).name}",
        )


REPORT_MD = ROOT / "report.md"
REPORT_HTML = ROOT / "report.html"


def _check_report_sync(rep: Report) -> None:
    """Part C: the Chinese report must carry the paper's numbers and figure order.

    The report is a *second renderer* of the same frozen run, so the two can
    silently drift if either generator grows its own literal copies of a
    headline number.  This gate re-reads both rendered artifacts and asserts:

      * every headline metric in ``paper_values.json`` appears in the report;
      * the report's ten numbered figures (``图 1``…``图 10``) are the paper's
        ten figures, in the paper's order;
      * no leftover ``report.pdf`` is presented as the current paper.
    """
    import re

    if not REPORT_MD.exists():
        rep.check(False, "report.md missing")
        return
    rmd = REPORT_MD.read_text(encoding="utf-8", errors="ignore")

    # --- figure identity and order: 图 N == Figure N ------------------------
    paper_caps = re.findall(r"!\[(?:<strong>)?Figure\s+(\d+)\.", MD.read_text(encoding="utf-8"))
    report_caps = re.findall(r"\*\*图\s+(\d+)\*\*", rmd)
    rep.check(
        report_caps == paper_caps == [str(i) for i in range(1, len(FIGURE_ORDER) + 1)],
        f"report figure numbering {report_caps} != paper figure numbering {paper_caps}",
    )

    pv = _load_json(TABLES / "paper_values.json") if (TABLES / "paper_values.json").exists() else {}
    mr = pv.get("main_results", {})
    headline = [
        ("baseline rmse", mr.get("baseline", {}).get("rmse_c")),
        ("mlp rmse", mr.get("mlp", {}).get("rmse_c")),
        ("random forest rmse", mr.get("random_forest", {}).get("rmse_c")),
        ("k-correction rmse", mr.get("k_correction", {}).get("rmse_c")),
    ]
    for label, value in headline:
        if value is None:
            continue
        rep.check(
            f"{float(value):.4f}" in rmd,
            f"report.md does not carry the frozen {label} ({value}); generators have drifted",
        )

    # --- stale root report.pdf must not stand in for the current paper ------
    stale_pdf = ROOT / "report.pdf"
    if stale_pdf.exists():
        import datetime as _dt

        age_days = (_dt.date.today() - _dt.date.fromtimestamp(stale_pdf.stat().st_mtime)).days
        rep.check(
            age_days < 30,
            f"root report.pdf is {age_days} days old and still looks like the current paper; "
            "regenerate it or move it under docs/ with a HISTORICAL label",
        )


def _check_sparse_leakage(rep: Report) -> None:
    """P1-04: the sparse branch must not use full-data labels or medians."""
    path = TABLES / "dimensionless_sparse_summary.json"
    if not path.exists():
        rep.check(False, "dimensionless_sparse_summary.json missing")
        return
    s = _load_json(path)
    rep.check(
        s.get("target_source") == "fold_local_diagnosis_no_full_data_labels",
        f"sparse target_source={s.get('target_source')!r} is not fold-local",
    )
    rep.check(
        s.get("imputation_source") == "train_fold_median_only",
        f"sparse imputation_source={s.get('imputation_source')!r} is not training-fold only",
    )
    folds = s.get("folds") or []
    rep.check(bool(folds), "sparse fold metadata missing")
    for f in folds:
        rep.check(
            f.get("target_source") == "fold_local_diagnosis",
            f"sparse fold {f.get('fold_id')} target_source={f.get('target_source')!r}",
        )
        rep.check(
            int(f.get("n_train_targets") or 0) >= 5,
            f"sparse fold {f.get('fold_id')} has {f.get('n_train_targets')} training targets",
        )
    # Exactly one OOF row per key, all finite, key set == expected set.
    pred = DATA_PROC / "sparse_pi_holdout_predictions.csv"
    if not pred.exists():
        rep.check(False, "sparse_pi_holdout_predictions.csv missing")
        return
    import numpy as np
    import pandas as pd

    df = pd.read_csv(pred)
    keys = [c for c in ("date", "reach_id", "sample_id") if c in df.columns]
    rep.check(bool(keys), "sparse holdout predictions lack identifying keys")
    if keys:
        dupes = int(df.duplicated(subset=keys).sum())
        rep.check(dupes == 0, f"sparse OOF predictions have {dupes} duplicate key rows")
    val = pd.to_numeric(df.get("C_model_mol_m3"), errors="coerce")
    rep.check(bool(np.isfinite(val.to_numpy(dtype=float)).all()), "sparse OOF predictions contain non-finite values")

    # The original-variable equation must not carry standardized `_z` labels.
    coefs = TABLES / "dimensionless_sparse_coefficients.csv"
    if coefs.exists():
        cdf = pd.read_csv(coefs)
        rep.check(
            cdf["feature"].astype(str).str.contains("_z").sum() == 0,
            "sparse coefficient feature names carry standardized `_z` suffixes",
        )
        zeroed = cdf.loc[cdf["coef_standardized_Sstar"].abs() <= 1e-12, "feature"].astype(str).tolist()
        rep.check(
            bool(zeroed),
            "no LASSO-zeroed term recorded; Figure 10's explicit zero bars would be vacuous",
        )


def _check_claim_guard_narrative(rep: Report) -> None:
    """P0-01: the guard's *narrative* literals must track the machine tables.

    The 2026-09-27 review caught ``paper_claim_guard.json`` still advertising
    ``Residual-AI MLP RMSE 0.0372 vs Baseline 0.0486`` and ``RF 0.1011`` (an
    older snapshot) and a paired k ratio of ``3.89e-5`` while the frozen tables
    say otherwise.  Hard-coded summary prose is exactly how a single source of
    truth rots, so the narrative numbers are parsed back out and compared with
    the tables that produced them.
    """
    guard_path = TABLES / "paper_claim_guard.json"
    if not guard_path.exists():
        return
    import re

    guard = _load_json(guard_path)
    rmse = guard.get("frozen_loo_reach_rmse_c", {})

    claim = str(guard.get("preferred_claim") or "")
    if claim:
        nums = {round(float(n), 4) for n in re.findall(r"\d+\.\d+", claim)}
        for key in ("baseline", "residual_ai_mlp", "residual_ai_rf"):
            want = rmse.get(key)
            if want is None:
                continue
            # <=4-decimal rounded forms of the frozen value must be the ones quoted
            if round(float(want), 4) not in nums and round(float(want), 3) not in nums:
                rep.check(
                    False,
                    f"preferred_claim quotes no value matching {key}={want} "
                    f"(stale narrative numbers: {sorted(nums)})",
                )

    # paired k ratio literal must equal the measured identifiability value
    ident_path = TABLES / "identifiability_summary.json"
    if ident_path.exists():
        ident = _load_json(ident_path)
        measured = ident.get("k_ratio_median")
        quoted = guard.get("k_ratio_median_k_correction")
        if measured is not None and quoted is not None:
            rep.check(
                abs(float(quoted) - float(measured)) < 1e-9,
                f"paper_claim_guard k_ratio_median_k_correction={quoted} != "
                f"measured identifiability k_ratio_median={measured}",
            )


# The 2026-09-27 review caught headless prose that still quoted the pre-fix
# generation (Baseline 0.0284 / MLP 0.0573 / RF 0.0745 / k 0.0244 / sparse
# 0.051, and a 3.4e-4 k ratio).  Those literals must never reappear in the
# rendered manuscript; the frozen run quotes different values.  The
# 2026-09-20 generation also reported MLP 0.0372 ("better than baseline"),
# RF 0.1011, k_eff median 123.3293, and paired ratio 0.54 -- the exact
# false-success literals the remediation removed, so they are blacklisted too.
STALE_NUMBER_LITERALS = (
    "0.0284", "0.0573", "0.0745", "0.0244",
    "3.4e-4", "3.4e-04",
    "0.0372", "0.1011", "123.3293",
)
# Boundary-anchored stale literals: a plain substring test would false-positive
# on legitimate neighbours (e.g. Baseline 0.0485, r002 ratio 0.5422).
STALE_BOUNDARY_LITERALS = ("0.0486", "0.54")


def _check_stale_prose(rep: Report) -> None:
    """Fail closed if a pre-fix headline literal survives in the prose.

    Catches the exact class of defect a reviewer found in ``paper.md`` (a
    stale "60% / 18.8%" sentence): a number in narrative prose that is not
    traceable to the frozen run.  Some literals (e.g. ``0.0486`` vs the
    correct Baseline 0.0485, and ``0.54`` vs the r002 ratio 0.5422) must be
    checked with a digit boundary so a longer legitimate value is not matched.
    """
    import re

    for path in (MD, HTML):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        # strip base64 payloads so compressed image bytes cannot create hits
        text = re.sub(r"data:image/[a-z+]+;base64,[A-Za-z0-9+/=]+", "<IMG>", text)
        for lit in STALE_NUMBER_LITERALS:
            if lit.lower() in text.lower():
                rep.fail(f"{path.name} quotes stale pre-fix literal {lit!r}")
        for lit in STALE_BOUNDARY_LITERALS:
            if re.search(rf"(?<![\d.]){re.escape(lit)}(?![\d])", text):
                rep.fail(f"{path.name} quotes stale pre-fix literal {lit!r}")


def _check_manuscript(rep: Report, post_fix: bool) -> None:
    for path in (MD, HTML):
        if not path.exists():
            rep.check(False, f"{path.name} missing")
            continue
        text = path.read_text(encoding="utf-8").lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() not in text:
                continue
            idx = text.find(phrase.lower())
            window = text[max(0, idx - 80) : idx + len(phrase) + 80]
            if any(
                t in window
                for t in ("not ", "demot", "audit", "superseded", "do not", "blocked",
                          "sample-support", "grouped")
            ):
                continue
            if rep.submission:
                rep.fail(f"{path.name} still contains claim phrase: {phrase!r}")
            elif post_fix:
                rep.warn(f"{path.name} contains claim phrase {phrase!r} (paper rewrite still open)")
            else:
                rep.fail(f"{path.name} still contains claim phrase: {phrase!r}")


def main(mode: str = "development") -> int:
    rep = Report(submission=mode == "submission")
    post_fix = False

    summary_path = TABLES / "nested_cv_summary.json"
    if summary_path.exists():
        summary = _load_json(summary_path)
        post_fix = bool(summary.get("post_fix_development_numbers"))
        if summary.get("failed_folds"):
            rep.fail(f"nested_cv_summary reports failed_folds={summary['failed_folds']}")

    guard_path = TABLES / "paper_claim_guard.json"
    if not guard_path.exists():
        rep.fail(f"missing {guard_path.relative_to(ROOT)}")
        print("Claim guard cannot run without paper_claim_guard.json")
        return 1
    guard = _load_json(guard_path)
    frozen = guard.get("frozen_loo_reach_rmse_c", {})

    manifest_path = TABLES / "artifact_manifest.json"
    if rep.submission and not manifest_path.exists():
        rep.fail("submission mode requires artifact_manifest.json")
    if manifest_path.exists():
        man = _load_json(manifest_path)
        if rep.submission and man.get("git", {}).get("dirty"):
            rep.fail("submission mode: working tree is dirty (git dirty=true)")
        if rep.submission and not man.get("git", {}).get("commit"):
            rep.fail("submission mode: missing git commit in manifest")

    # ---- RMSE drift vs the recorded claim guard -----------------------------
    metrics_path = TABLES / "nested_cv_metrics.csv"
    if metrics_path.exists():
        import pandas as pd

        nested = pd.read_csv(metrics_path)
        loo = (
            nested[(nested["cv_protocol"] == "loo_reach") & (nested["subgroup"] == "all_120")]
            if "subgroup" in nested.columns
            else nested[nested["cv_protocol"] == "loo_reach"]
        )
        mapping = {
            "baseline": ("baseline", "none"),
            "residual_ai_mlp": ("residual_ai", "mlp"),
            "residual_ai_rf": ("residual_ai", "random_forest"),
            "k_correction_xgboost": ("k_correction", "xgboost"),
        }
        for gkey, (scheme, model) in mapping.items():
            if gkey not in frozen:
                continue
            sub = loo[(loo["scheme"] == scheme) & (loo["model"] == model)]
            if sub.empty:
                rep.fail(f"metrics missing row for {scheme}/{model}")
                continue
            got = round(float(sub["rmse_c"].iloc[0]), 4)
            want = round(float(frozen[gkey]), 4)
            if abs(got - want) > 5e-4:
                msg = f"RMSE mismatch {scheme}/{model}: table={got} guard={want}"
                if rep.submission or not post_fix:
                    rep.fail(msg)
                else:
                    rep.warn(f"post-fix RMSE drift {msg}")
    else:
        rep.check(False, "nested_cv_metrics.csv missing")

    # ---- k-correction saturation bookkeeping -------------------------------
    sat_path = TABLES / "k_correction_saturation.json"
    if sat_path.exists():
        sat = _load_json(sat_path)
        n_pred = int(sat.get("n_predictions", -1))
        n_camp = int(sat.get("n_campaign", 120))
        if n_pred > n_camp * 2:
            rep.fail(
                f"k_correction_saturation n_predictions={n_pred} looks like fold×sample duplicates",
            )
        policy = sat.get("infeasible_policy")
        if policy not in (None, "exclude_from_training", "censored_floor"):
            rep.fail(f"unknown infeasible_policy={policy!r}")
        if policy is None:
            rep.warn("saturation JSON missing infeasible_policy field")
        if policy != "exclude_from_training" and (rep.submission or not post_fix):
            rep.fail("infeasible_policy must be exclude_from_training (or document censored_floor)")
    else:
        rep.check(False, "k_correction_saturation.json missing")

    # ---- 2026-09-27 acceptance checks -------------------------------------
    _check_fmt_ratio(rep)
    _check_paper_values(rep)
    _check_table1_counts(rep)
    _check_sparse_leakage(rep)
    _check_figures(rep)
    _check_report_sync(rep)
    _check_claim_guard_narrative(rep)
    _check_stale_prose(rep)
    _check_manuscript(rep, post_fix)

    if rep.errors:
        print(
            f"\nClaim guard FAILED with {len(rep.errors)} error(s), "
            f"{len(rep.warnings)} warning(s) [mode={mode}]."
        )
        return 1
    if rep.submission:
        print(f"\nClaim guard PASS (submission) ({len(rep.warnings)} warning(s)).")
    else:
        print(
            f"\nClaim guard PASS (development check — not for submission) "
            f"({len(rep.warnings)} warning(s))."
        )
    return 0


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Verify paper claims and frozen artifacts")
    p.add_argument(
        "--mode",
        choices=("development", "submission"),
        default="development",
        help="development=warnings OK; submission=fail-closed",
    )
    args = p.parse_args()
    raise SystemExit(main(args.mode))
