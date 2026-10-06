"""Figure sidecar metadata (2026-09-27 review, Part B item 11).

Every published figure gets a JSON sidecar next to it (``<figure>.json``) that
records how the PNG was produced so a reader can trace the figure back to the
frozen machine tables.  The required keys are:

``figure_id, run_id, generator, source_table_sha256, selected_rows,
aggregation, units, n_definition, output_sha256``

``source_table_sha256`` hashes each referenced source table at write time and
``output_sha256`` hashes the rendered PNG, so ``scripts/verify_paper.py`` can
fail closed when a figure is stale relative to its declared sources.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# The frozen run whose module constants the documents print. This is the single
# source of truth for the sidecar ``run_id``: generators may pass a richer value
# (e.g. a config-provided run id) but may not leave it empty, and the writer fills
# this default when they do. Keeping one constant stops the ``run_id`` from
# silently becoming ``None`` in a generator-written sidecar.
DEFAULT_RUN_ID = "20260919_remediation"

REQUIRED_KEYS = (
    "figure_id",
    "run_id",
    "generator",
    "source_table_sha256",
    "selected_rows",
    "aggregation",
    "units",
    "n_definition",
    "output_sha256",
)


def sha256_file(path: str | Path, *, chunk: int = 1 << 20) -> str | None:
    """Return the SHA-256 hex digest of ``path`` or ``None`` when absent."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _normalise_sources(source_table: Any) -> Any:
    """Hash every declared source table (path or list of paths)."""
    if source_table is None:
        return {}
    if isinstance(source_table, (str, Path)):
        items = [source_table]
    elif isinstance(source_table, dict):
        return {k: sha256_file(v) for k, v in source_table.items()}
    else:
        items = list(source_table)
    out: dict[str, Any] = {}
    for item in items:
        p = Path(item)
        if not p.is_absolute():
            cand = ROOT / p
            p = cand if cand.exists() else p
        out[str(item)] = sha256_file(p)
    return out


def _default_sidecar_path(image_path: Path) -> Path:
    """Sidecars live in a ``sidecars/`` sub-directory beside the figure."""
    return image_path.parent / "sidecars" / f"{image_path.stem}.json"


def write_figure_sidecar(
    image_path: str | Path,
    metadata: dict[str, Any],
    *,
    sidecar_dir: str | Path | None = None,
) -> Path:
    """Write the figure's JSON sidecar with the required keys plus any extras.

    This function is the **single authority** for the sidecar schema. A generator
    may pass a reduced ``metadata`` dict; the writer fills every required key,
    using ``DEFAULT_RUN_ID`` for a missing ``run_id`` and the figure stem for a
    missing ``figure_id``. That is deliberate: generator-written sidecars used to
    be left with ``run_id: None`` (schema-violating) and were only repaired if
    stage 19 happened to overwrite them, so whether a sidecar was complete
    depended on stage ordering. Missing values are still recorded (never raised)
    so ``verify_paper.py`` can report exactly which figure is incomplete.
    """
    image_path = Path(image_path)
    payload = dict(metadata)
    payload.setdefault("figure_id", image_path.stem)
    payload["sidecar_version"] = 1
    payload["image"] = image_path.name
    payload["image_path"] = str(image_path.relative_to(ROOT)) if image_path.is_relative_to(ROOT) else str(image_path)
    payload["source_table_sha256"] = _normalise_sources(
        metadata.get("source_table_sha256", metadata.get("source_table"))
    )
    payload.pop("source_table", None)
    payload["output_sha256"] = sha256_file(image_path)
    # Contract defaults, applied before the "record missing as None" sweep.
    if not payload.get("run_id"):
        payload["run_id"] = DEFAULT_RUN_ID
    for key in REQUIRED_KEYS:
        payload.setdefault(key, None)

    if sidecar_dir is not None:
        out = Path(sidecar_dir) / f"{image_path.stem}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        out = _default_sidecar_path(image_path)
        out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, default=str)
    return out


def load_figure_sidecar(image_path: str | Path) -> dict[str, Any] | None:
    """Read a sidecar for ``image_path`` (``sidecars/<stem>.json`` or legacy)."""
    p = Path(image_path)
    for cand in (
        _default_sidecar_path(p),
        p.with_suffix(p.suffix + ".json"),
        p.with_suffix(".json"),
    ):
        if cand.exists():
            return json.loads(cand.read_text(encoding="utf-8"))
    return None
