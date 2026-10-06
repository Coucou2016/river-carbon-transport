#!/usr/bin/env python3
"""Offline-cached web-map tiles for the network figures (Figure 2 provenance).

The manuscript's network map is drawn over satellite imagery.  Web tiles are
not reproducible by default, so this module:

  * downloads tiles once into ``data_raw/basemap_cache/<layer>/`` (raw bytes
    are never re-fetched if already present);
  * records a provenance manifest (layer, attribution, license note, zoom,
    tile bounds, per-tile SHA-256 and the composite raster SHA-256);
  * returns a single stitched RGB array in **Web Mercator (EPSG:3857)** plus
    its extent, so callers can ``imshow`` it and plot in the same CRS.

If the network is unavailable and the cache is empty, :func:`fetch_basemap`
returns ``None`` and the caller must fall back to a *documented* terrain
shading — never to a silent blank background.

REAL DATA ONLY. Tiles come from an acknowledged public provider; nothing here
is synthetic cartography.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.utils import setup_logging

LOG = setup_logging("basemap_tiles")

WEBMERC_R = 6378137.0
WEBMERC_MAX = math.pi * WEBMERC_R

# Public, acknowledged tile services.  ``attribution`` is printed on the figure.
LAYERS: dict[str, dict] = {
    "esri_world_imagery": {
        "url": (
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}"
        ),
        "attribution": "Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        "license_note": (
            "Esri World Imagery basemap tiles, accessed for scientific figure "
            "production with attribution; not redistributed as a dataset."
        ),
        "max_zoom": 19,
    },
}

_TILE = 256


class BasemapUnavailable(RuntimeError):
    """No cached tiles and the provider could not be reached."""


@dataclass
class BasemapRaster:
    image: np.ndarray            # (H, W, 3) uint8
    extent: tuple[float, float, float, float]  # (xmin, xmax, ymin, ymax) EPSG:3857
    zoom: int
    layer: str
    attribution: str
    manifest: dict


def _lonlat_to_merc(lon: float, lat: float) -> tuple[float, float]:
    x = WEBMERC_R * math.radians(lon)
    y = WEBMERC_R * math.log(math.tan(math.pi / 4.0 + math.radians(lat) / 2.0))
    return x, y


def _merc_to_tile(x: float, y: float, z: int) -> tuple[float, float]:
    n = 2.0**z
    tx = (x + WEBMERC_MAX) / (2.0 * WEBMERC_MAX) * n
    ty = (WEBMERC_MAX - y) / (2.0 * WEBMERC_MAX) * n
    return tx, ty


def _tile_to_merc(tx: float, ty: float, z: int) -> tuple[float, float]:
    n = 2.0**z
    x = tx / n * (2.0 * WEBMERC_MAX) - WEBMERC_MAX
    y = WEBMERC_MAX - ty / n * (2.0 * WEBMERC_MAX)
    return x, y


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _cache_dir(cache_root: Path, layer: str, z: int) -> Path:
    return cache_root / layer / f"z{z}"


def _tile_path(cache_root: Path, layer: str, z: int, tx: int, ty: int) -> Path:
    return _cache_dir(cache_root, layer, z) / f"{tx}_{ty}.jpg"


def _download_tile(url: str, timeout: float = 30.0) -> bytes:
    import requests

    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "east-river-carbon/1.0"})
    resp.raise_for_status()
    if not resp.content:
        raise BasemapUnavailable(f"empty tile from {url}")
    return resp.content


def fetch_basemap(
    lon_min: float,
    lon_max: float,
    lat_min: float,
    lat_max: float,
    *,
    cache_root: Path,
    layer: str = "esri_world_imagery",
    max_tiles: int = 400,
    allow_download: bool = True,
) -> BasemapRaster | None:
    """Stitch cached (or freshly downloaded) tiles covering a lon/lat box.

    Returns ``None`` when nothing is cached and downloading is disabled or
    fails, so the caller can fall back explicitly.
    """
    if layer not in LAYERS:
        raise KeyError(f"unknown basemap layer {layer!r}")
    spec = LAYERS[layer]

    x0, y0 = _lonlat_to_merc(lon_min, lat_max)   # top-left
    x1, y1 = _lonlat_to_merc(lon_max, lat_min)   # bottom-right

    # Pick the largest zoom whose tile count still fits the budget.
    chosen_z = None
    for z in range(spec["max_zoom"], 0, -1):
        tx0, ty0 = _merc_to_tile(x0, y0, z)
        tx1, ty1 = _merc_to_tile(x1, y1, z)
        nx = int(math.floor(tx1)) - int(math.floor(tx0)) + 1
        ny = int(math.floor(ty1)) - int(math.floor(ty0)) + 1
        if nx * ny <= max_tiles and nx > 0 and ny > 0:
            chosen_z = (z, int(math.floor(tx0)), int(math.floor(ty0)), nx, ny)
            break
    if chosen_z is None:
        LOG.warning("Basemap: no zoom level fits the %d-tile budget", max_tiles)
        chosen_z = (spec["max_zoom"] - 4, 0, 0, 1, 1)

    z, tx_start, ty_start, nx, ny = chosen_z
    manifest_tiles: list[dict] = []
    canvas = np.zeros((ny * _TILE, nx * _TILE, 3), dtype=np.uint8)
    from PIL import Image

    n_ok = 0
    for j in range(ny):
        for i in range(nx):
            tx, ty = tx_start + i, ty_start + j
            path = _tile_path(cache_root, layer, z, tx, ty)
            data: bytes | None = None
            source = "cache"
            if path.exists():
                data = path.read_bytes()
            elif allow_download:
                url = spec["url"].format(z=z, x=tx, y=ty)
                try:
                    data = _download_tile(url)
                except Exception as exc:  # noqa: BLE001
                    LOG.warning("Basemap tile %s/%s/%s failed: %s", z, tx, ty, exc)
                    data = None
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                    source = "download"
            if data is None:
                continue
            try:
                img = Image.open(io.BytesIO(data)).convert("RGB")
            except Exception as exc:  # noqa: BLE001
                LOG.warning("Basemap tile %s/%s/%s unreadable: %s", z, tx, ty, exc)
                continue
            if img.size != (_TILE, _TILE):
                img = img.resize((_TILE, _TILE))
            canvas[j * _TILE : (j + 1) * _TILE, i * _TILE : (i + 1) * _TILE] = np.asarray(img)
            n_ok += 1
            manifest_tiles.append(
                {
                    "z": z,
                    "x": tx,
                    "y": ty,
                    "sha256": _sha256_bytes(data),
                    "source": source,
                }
            )

    if n_ok == 0:
        LOG.warning(
            "Basemap layer %s unavailable: no cached tiles under %s and download disabled/failed",
            layer,
            _cache_dir(cache_root, layer, z),
        )
        return None

    # Extent of the stitched block, trimmed to the requested box.
    bx0, by0 = _tile_to_merc(tx_start, ty_start, z)
    bx1, by1 = _tile_to_merc(tx_start + nx, ty_start + ny, z)
    px_per_m_x = canvas.shape[1] / (bx1 - bx0)
    px_per_m_y = canvas.shape[0] / (by0 - by1)
    left = max(0, int(round((x0 - bx0) * px_per_m_x)))
    right = min(canvas.shape[1], int(round((x1 - bx0) * px_per_m_x)))
    top = max(0, int(round((by0 - y0) * px_per_m_y)))
    bottom = min(canvas.shape[0], int(round((by0 - y1) * px_per_m_y)))
    if right <= left or bottom <= top:
        left, right, top, bottom = 0, canvas.shape[1], 0, canvas.shape[0]
        crop_extent = (bx0, bx1, by1, by0)
    else:
        crop_extent = (
            bx0 + left / px_per_m_x,
            bx0 + right / px_per_m_x,
            by0 - bottom / px_per_m_y,
            by0 - top / px_per_m_y,
        )
    cropped = canvas[top:bottom, left:right].copy()

    manifest = {
        "layer": layer,
        "zoom": z,
        "attribution": spec["attribution"],
        "license_note": spec["license_note"],
        "url_template": spec["url"],
        "tile_grid": {"x0": tx_start, "y0": ty_start, "nx": nx, "ny": ny},
        "n_tiles_used": n_ok,
        "tiles": manifest_tiles,
        "composite_sha256": hashlib.sha256(cropped.tobytes()).hexdigest(),
        "crs": "EPSG:3857",
        "extent_epsg3857": list(crop_extent),
        "requested_bbox_lonlat": [lon_min, lat_min, lon_max, lat_max],
    }
    LOG.info(
        "Basemap %s z=%d: %d/%d tiles, composite %s",
        layer,
        z,
        n_ok,
        nx * ny,
        manifest["composite_sha256"][:12],
    )
    return BasemapRaster(
        image=cropped,
        extent=tuple(crop_extent),
        zoom=z,
        layer=layer,
        attribution=spec["attribution"],
        manifest=manifest,
    )


def write_basemap_manifest(path: Path, rasters: list[BasemapRaster]) -> Path:
    """Persist tile provenance next to the figures that used it."""
    payload = {
        "purpose": "reproducible satellite/hillshade basemap provenance for figure redraw",
        "layers": [r.manifest for r in rasters],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
