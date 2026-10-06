#!/usr/bin/env python3
"""Regression tests for the 2026-09-28 determinism + staleness follow-up.

Three defects are pinned here, each with a reverse example that the earlier code
failed:

1. ``sns.stripplot(jitter=...)`` draws its x-offsets from numpy's *global* RNG
   and has no seed argument, so ``filter_scale_sgs_box.png`` changed bytes on
   every run.  The figure now seeds immediately before the jitter.
2. ``topological_order_cells`` seeded Kahn's frontier from a ``set`` of strings,
   so the cell order -- and therefore ``filter_scale_cell_residuals.csv`` and the
   figures drawn from it -- depended on salted hashing (``PYTHONHASHSEED``).
3. ``run_pipeline._is_current`` compared mtimes and *skipped* ``.png`` inputs, so
   a regenerated live figure left stage 19 reporting "up-to-date" and the
   ``results/figures/paper/`` mirror stale.  Staleness is now decided by content
   hash, which also makes the archive mirror refresh on a live-PNG change.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_stage13():
    """Import ``src/13_filter_scale_sgs.py`` (the name is not a valid identifier)."""
    path = ROOT / "src" / "13_filter_scale_sgs.py"
    spec = importlib.util.spec_from_file_location("_s13_determinism", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _tiny_box_inputs():
    """Minimal synthetic inputs for the box figure (no real data needed)."""
    rng = np.random.default_rng(0)
    scales = [("native", 600.0), ("s2", 1200.0)]
    rows = []
    for lab, dx in scales:
        for _ in range(30):
            rows.append(
                {"dx_label": lab, "abs_S_sgs": float(abs(rng.normal(0.2, 0.05)) + 0.01)}
            )
    cell_detail = pd.DataFrame(rows)
    metrics = pd.DataFrame(
        {
            "dx_label": [lab for lab, _ in scales],
            "dx_m": [dx for _, dx in scales],
            "dx_median_m": [dx for _, dx in scales],
            "n_unique_spatial_cells": [3, 2],
            "n_date_cell_records": [30, 30],
            "cell_mean_abs_S_sgs": [0.2, 0.22],
            "median_abs_S_sgs": [0.19, 0.21],
            "cell_var_S_sgs": [0.003, 0.004],
        }
    )
    return metrics, cell_detail


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# 1. Figure determinism (stripplot jitter)
# ---------------------------------------------------------------------------

def test_box_figure_bytes_are_identical_across_renders(tmp_path):
    """Rendering the box figure twice must give byte-identical PNGs.

    Reverse example: before the seed was added, seaborn's jitter came from the
    global numpy RNG, so two renders differed whenever the global state differed
    between them.
    """
    import matplotlib.pyplot as plt

    s13 = _load_stage13()
    metrics, cell_detail = _tiny_box_inputs()
    hashes = []
    for i in range(2):
        fig = s13.render_filter_scale_box(metrics, cell_detail)
        out = tmp_path / f"box_{i}.png"
        fig.savefig(out, dpi=100, bbox_inches="tight")
        plt.close(fig)
        hashes.append(_sha256(out))
    assert hashes[0] == hashes[1], "box figure is not byte-deterministic across renders"


def test_box_figure_ignores_pre_existing_global_rng_state(tmp_path):
    """The seed inside the renderer must make the output independent of caller state.

    This is the strong form of the fix: the caller leaves numpy's global RNG in a
    different state before each call, yet the drawn jitter -- and so the bytes --
    must be identical.  It fails on the old code, where the jitter inherited
    whatever global state the caller happened to be in.
    """
    import matplotlib.pyplot as plt

    s13 = _load_stage13()
    metrics, cell_detail = _tiny_box_inputs()
    hashes = []
    for seed in (1, 987654321):
        np.random.seed(seed)
        np.random.uniform(size=17)  # advance the global state
        fig = s13.render_filter_scale_box(metrics, cell_detail)
        out = tmp_path / f"state_{seed}.png"
        fig.savefig(out, dpi=100, bbox_inches="tight")
        plt.close(fig)
        hashes.append(_sha256(out))
    assert hashes[0] == hashes[1], (
        "box figure bytes depend on the caller's global RNG state; the jitter is not seeded"
    )


def test_every_script_stage_accepts_the_runner_flags():
    """Each script stage must accept the flags run_pipeline forwards.

    run_script_stage passes ``--config`` to every ``scripts/*.py`` stage. Stage 19
    now actually re-runs (the staleness fix), so a script that rejects the flag no
    longer stays hidden behind a permanent "up-to-date".
    """
    import run_pipeline as rp

    for name, _desc, _inputs, _outputs in rp.STAGES:
        if not name.endswith(".py"):
            continue
        src = (rp.ROOT / name).read_text(encoding="utf-8")
        assert 'add_argument("--config"' in src or "add_argument('--config'" in src, (
            f"{name} does not accept --config, which run_script_stage always passes"
        )


def test_box_figure_seeds_the_global_rng_explicitly():
    """The renderer must seed the global RNG it relies on (documented intent)."""
    src = (ROOT / "src" / "13_filter_scale_sgs.py").read_text(encoding="utf-8")
    body = src[src.index("def render_filter_scale_box"):]
    body = body[: body.index("\ndef ")] if "\ndef " in body else body
    assert "np.random.seed(" in body, "box renderer does not seed the RNG"
    seed_pos = body.index("np.random.seed(")
    jitter_pos = body.index("sns.stripplot(")
    assert seed_pos < jitter_pos, "the RNG seed must be set before the jittered plot call"


# ---------------------------------------------------------------------------
# 2. Hash-order independence in the cell DAG
# ---------------------------------------------------------------------------

def _topo_order_under_hash_seed(seed: str) -> str:
    probe = (
        "import sys; sys.path.insert(0, r'%s');"
        "from src.cell_dag_filter import topological_order_cells;"
        "cells = {f'R003_cell_{i:04d}': ([f'R003_cell_{i-1:04d}'] if i else []) for i in range(20)};"
        "cells.update({f'R009_cell_{j:04d}': [] for j in range(5)});"
        "print(','.join(topological_order_cells(cells)))" % str(ROOT).replace("\\", "\\\\")
    )
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = seed
    r = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def test_cell_dag_order_is_independent_of_hash_seed():
    """The topological order must not depend on salted string hashing.

    Reverse example: the old ``known = set(cells_upstream)`` frontier made the
    order differ between processes with different ``PYTHONHASHSEED`` values, which
    reordered ``filter_scale_cell_residuals.csv`` rows across runs.
    """
    orders = {_topo_order_under_hash_seed(s) for s in ("0", "1", "12345", "999983")}
    assert len(orders) == 1, f"cell-DAG order varies with PYTHONHASHSEED: {orders}"


def test_cell_dag_order_preserves_topology():
    """Determinism must not break the topological guarantee."""
    from src.cell_dag_filter import topological_order_cells

    cells = {"T1": [], "T2": [], "M": ["T1", "T2"], "OUT": ["M"]}
    order = topological_order_cells(cells)
    assert order.index("T1") < order.index("M") < order.index("OUT")
    assert order.index("T2") < order.index("M")
    # Declared (insertion) order is the deterministic tie-break.
    assert order == ["T1", "T2", "M", "OUT"]


# ---------------------------------------------------------------------------
# 3. Content-hash staleness (stage 19 must re-run when a live PNG changes)
# ---------------------------------------------------------------------------

def _scratch_tree(tmp_path: Path) -> Path:
    fig = tmp_path / "results" / "figures"
    (fig / "sidecars").mkdir(parents=True, exist_ok=True)
    return fig


def test_stage_current_uses_content_hash_not_mtime(tmp_path, monkeypatch):
    """Touching an input must NOT make a stage stale; changing its bytes must."""
    import run_pipeline as rp

    fig = _scratch_tree(tmp_path)
    live = fig / "a.png"
    live.write_bytes(b"PNG-AAAA")
    side = fig / "sidecars" / "a.json"
    side.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(rp, "ROOT", tmp_path)
    inputs = ["results/figures/a.png"]
    outputs = ["results/figures/sidecars/a.json"]

    assert rp._stage_is_current("k", inputs, outputs, {}) is False, "unrecorded stage skipped"
    state = {"k": {"inputs": rp._fingerprint(inputs), "outputs": rp._fingerprint(outputs)}}
    assert rp._stage_is_current("k", inputs, outputs, state) is True

    # mtime-only change (content identical): still current.
    os.utime(live, (2_000_000_000, 2_000_000_000))
    assert rp._stage_is_current("k", inputs, outputs, state) is True, "mtime change wrongly assumed stale"

    # Content change with the SAME byte length: the old mtime/`.png`-skip logic
    # missed this; the content hash must catch it.
    live.write_bytes(b"PNG-BBBB")
    assert rp._stage_is_current("k", inputs, outputs, state) is False, (
        "a changed PNG did not invalidate the stage (the old code skipped .png inputs)"
    )


def test_stage_with_no_declared_inputs_is_never_skipped(tmp_path, monkeypatch):
    """A stage with no inputs cannot be proven current by hash, so it always runs."""
    import run_pipeline as rp

    fig = _scratch_tree(tmp_path)
    (fig / "b.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(rp, "ROOT", tmp_path)
    outputs = ["results/figures/b.json"]
    state = {"k": {"inputs": {}, "outputs": rp._fingerprint(outputs)}}
    assert rp._stage_is_current("k", [], outputs, state) is False


def test_stage19_declares_png_inputs_and_sidecar_outputs():
    """Stage 19 must declare live PNGs as inputs (glob) so it can never skip them."""
    import run_pipeline as rp

    stage = next(s for s in rp.STAGES if s[0] == "scripts/build_figure_sidecars.py")
    inputs, outputs = stage[2], stage[3]
    assert any(pat.endswith("*.png") for pat in inputs), (
        "stage 19 does not declare the live PNGs as inputs"
    )
    assert "results/figures/sidecars/*.json" in outputs, (
        "stage 19 does not declare the sidecars it owns as outputs"
    )
    # A glob input must actually expand to the live PNGs on this tree.
    expanded = rp._expand_paths(inputs)
    assert any(p.endswith("filter_scale_sgs_box.png") for p in expanded), expanded[:5]


def test_every_stage_declares_expandable_io():
    """Every stage's declared I/O must expand without error.

    Reverse example: the content-hash rewrite shipped an undefined name
    (``declared_outputs``) that only surfaced mid-run, after earlier stages had
    already written artifacts. Expanding the whole graph up front catches that
    class of error without running anything.
    """
    import run_pipeline as rp

    for i, (name, _desc, declared_inputs, declared_outputs) in enumerate(rp.STAGES, start=1):
        inputs, outputs = rp.stage_io(declared_inputs, declared_outputs)
        assert isinstance(inputs, list) and isinstance(outputs, list), name
        # Stage 19's globs must resolve to real, existing files on this tree.
        for rel in inputs + outputs:
            if any(ch in str(rel) for ch in "*?["):
                raise AssertionError(f"stage {i} ({name}) left an unexpanded glob: {rel!r}")
            assert (rp.ROOT / rel).exists(), f"stage {i} ({name}) declares missing path {rel}"


def test_stage19_refreshes_mirror_and_sidecar_when_live_png_changes(tmp_path, monkeypatch):
    """Mutating a live PNG must refresh the paper/ mirror and the sidecar.

    This is the end-to-end behaviour the mtime skip defeated: stage 19 reports
    "up-to-date" and the archive keeps the old render, so the repo shows a
    different image than the documents embed.
    """
    import scripts.build_figure_sidecars as bfs
    from src.figure_sidecar import sha256_file, write_figure_sidecar

    fig = _scratch_tree(tmp_path)
    paper = fig / "paper"
    paper.mkdir(parents=True, exist_ok=True)
    tables = tmp_path / "results" / "tables"
    tables.mkdir(parents=True, exist_ok=True)

    live = fig / "toy.png"
    live.write_bytes(b"PNG-VERSION-ONE")
    write_figure_sidecar(live, {"figure_id": "toy", "generator": "test", "units": "u",
                                "aggregation": "a", "n_definition": "n", "selected_rows": {}})

    monkeypatch.setattr(bfs, "ROOT", tmp_path)
    monkeypatch.setattr(bfs, "FIG_DIR", fig)
    monkeypatch.setattr(bfs, "PAPER_ARCHIVE_DIR", paper)
    monkeypatch.setattr(bfs, "TABLES", tables)

    refreshed, current, _ = bfs.sync_paper_archive()
    assert refreshed == ["toy.png"], (refreshed, current)
    assert (paper / "toy.png").read_bytes() == live.read_bytes()

    # Re-run with no change: nothing refreshed (the mirror is genuinely current).
    refreshed2, current2, _ = bfs.sync_paper_archive()
    assert refreshed2 == [] and current2 == ["toy.png"], (refreshed2, current2)

    # Now change the live PNG; stage 19 must refresh the mirror and the sidecar.
    live.write_bytes(b"PNG-VERSION-TWO-LONGER")
    side_before = json.loads((fig / "sidecars" / "toy.json").read_text(encoding="utf-8"))
    write_figure_sidecar(live, {"figure_id": "toy", "generator": "test", "units": "u",
                                "aggregation": "a", "n_definition": "n", "selected_rows": {}})
    side_after = json.loads((fig / "sidecars" / "toy.json").read_text(encoding="utf-8"))
    assert side_before["output_sha256"] != side_after["output_sha256"], "sidecar hash not refreshed"
    assert side_after["output_sha256"] == sha256_file(live)
    assert side_after["run_id"], "sidecar lost its run_id"

    refreshed3, _, _ = bfs.sync_paper_archive()
    assert refreshed3 == ["toy.png"], refreshed3
    assert (paper / "toy.png").read_bytes() == live.read_bytes()

    # The archive manifest the gate consumes must report a clean mirror.
    bfs.write_derived_archive_manifest()
    manifest = json.loads((paper / "derived_archive_manifest.json").read_text(encoding="utf-8"))
    counts = manifest["counts"]
    assert counts["drifted"] == 0, counts
    assert counts["matching"] == counts["published_figures"], counts
    assert manifest["figures"]["toy.png"]["archived_png_sha256"] == sha256_file(paper / "toy.png")
    assert manifest["figures"]["toy.png"]["canonical_png_sha256"] == sha256_file(live)
    assert manifest["figures"]["toy.png"]["matches_canonical"] is True


def test_sidecar_writer_fills_run_id_and_required_keys(tmp_path):
    """The sidecar writer is the single authority: it must never leave run_id None."""
    from src.figure_sidecar import DEFAULT_RUN_ID, REQUIRED_KEYS, write_figure_sidecar

    img = tmp_path / "fig.png"
    img.write_bytes(b"PNG")
    # A reduced generator-style payload (no run_id, no figure_id, no hashes).
    out = write_figure_sidecar(img, {"generator": "test::gen"})
    meta = json.loads(out.read_text(encoding="utf-8"))
    assert meta["run_id"] == DEFAULT_RUN_ID, "writer left run_id empty"
    assert meta["figure_id"] == "fig"
    for key in REQUIRED_KEYS:
        assert key in meta, f"writer omitted required key {key}"
    assert meta["output_sha256"] == hashlib.sha256(b"PNG").hexdigest()


def test_sidecar_writer_respects_an_explicit_run_id(tmp_path):
    """A generator that knows its run id must keep it (the default is a fallback)."""
    from src.figure_sidecar import write_figure_sidecar

    img = tmp_path / "fig.png"
    img.write_bytes(b"PNG")
    out = write_figure_sidecar(img, {"run_id": "custom-run", "generator": "g"})
    assert json.loads(out.read_text(encoding="utf-8"))["run_id"] == "custom-run"


# ---------------------------------------------------------------------------
# 4. Cross-stage global-state isolation (each src/ stage in its own process)
# ---------------------------------------------------------------------------

def test_run_src_stage_spawns_an_isolated_interpreter(monkeypatch):
    """A src/ stage must run as a subprocess, not via an in-process import.

    Reverse example: ``main()`` imported every ``src/`` stage into one
    interpreter and called ``mod.main(config)``. Each figure stage sets a *global*
    matplotlib style at import time (``sns.set_theme`` + ``apply_plot_style``), so
    the style left behind by stage 8/9 leaked into stage 10 and its PNG bytes
    depended on the invocation path rather than on the stage's own code.
    """
    import sys

    import run_pipeline as rp

    calls = []

    class _Done:
        returncode = 0

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return _Done()

    monkeypatch.setattr(rp.subprocess, "run", fake_run)
    mode = rp.run_src_stage("10_gis_network_viz", "configs/east_river.yaml")

    assert mode == "ran"
    cmd, kwargs = calls[0]
    assert cmd[0] == sys.executable
    assert cmd[1] == str(rp.ROOT / "run_pipeline.py")
    assert "--exec-stage-module" in cmd
    assert cmd[cmd.index("--exec-stage-module") + 1] == "10_gis_network_viz"
    assert cmd[cmd.index("--config") + 1] == "configs/east_river.yaml"
    # Same subprocess contract run_script_stage already uses.
    assert kwargs.get("cwd") == rp.ROOT
    assert kwargs.get("check") is True


def test_cli_wires_the_exec_stage_module_child_entry():
    """The child entry point run_src_stage spawns must exist in __main__."""
    src = (ROOT / "run_pipeline.py").read_text(encoding="utf-8")
    assert '"--exec-stage-module"' in src, "the child CLI flag is missing"
    # The flag must actually execute one module and exit, not fall through to a
    # full pipeline run.
    handler = src[src.index("if args.exec_stage_module:"):]
    assert "mod.main(args.config)" in handler[:800]
    assert "SystemExit(0)" in handler[:800]


def test_every_src_stage_declares_a_main_and_is_reachable_by_the_child_entry():
    """Every non-script stage must expose main() so --exec-stage-module can run it."""
    import run_pipeline as rp

    for name, _desc, _inputs, _outputs in rp.STAGES:
        if name.endswith(".py"):
            continue
        mod = rp.load_stage(name)
        assert hasattr(mod, "main"), f"{name} has no main(); run_src_stage would fail"


def test_style_setting_stages_actually_mutate_global_rcparams():
    """Documents *why* isolation is required: importing a style stage is global.

    If this ever stops being true the isolation is merely belt-and-braces rather
    than load-bearing; the assertion pins the coupling so the reason stays honest.
    """
    probe = (
        "import importlib.util, sys;"
        "sys.path.insert(0, r'%s');"
        "import matplotlib; matplotlib.use('Agg');"
        "import matplotlib.pyplot as plt;"
        "before = plt.rcParams['font.size'];"
        "spec = importlib.util.spec_from_file_location('s08', r'%s');"
        "m = importlib.util.module_from_spec(spec); sys.modules['s08'] = m;"
        "spec.loader.exec_module(m);"
        "print(f'{before}|{plt.rcParams[\"font.size\"]}')"
        % (str(ROOT).replace("\\", "\\\\"),
           str(ROOT / "src" / "08_validate_flux_budget.py").replace("\\", "\\\\"))
    )
    r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=ROOT)
    assert r.returncode == 0, r.stderr
    before, after = r.stdout.strip().splitlines()[-1].split("|")
    assert before != after, (
        "importing 08_validate_flux_budget no longer mutates global rcParams; "
        "re-check whether per-stage process isolation is still needed"
    )



def test_superseded_constants_are_frozen_not_head_derived():
    """Stage 19 must not re-derive historical hashes from a moving HEAD."""
    import scripts.build_figure_sidecars as bfs

    assert bfs._SUPERSEDED_ARCHIVE_COMMIT, "recovery commit is not pinned"
    for name, full in bfs._SUPERSEDED_ARCHIVE_RENDERS.items():
        assert len(full) == 64, f"{name}: expected a full SHA-256, got {full!r}"
        assert bfs._SUPERSEDED_ARCHIVE_SIZES[name] > 0, name
    # The recovery command must name the frozen commit, not resolve against HEAD.
    src = (ROOT / "scripts" / "build_figure_sidecars.py").read_text(encoding="utf-8")
    code = [ln for ln in src.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    assert not any("git cat-file" in ln or "HEAD:results/figures" in ln for ln in code), (
        "recovery command still resolves historical bytes against a moving HEAD"
    )
    assert bfs._SUPERSEDED_ARCHIVE_COMMIT[:7] in src


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    if failed:
        raise SystemExit(1)
    print(f"All {len(tests)} tests passed.")
