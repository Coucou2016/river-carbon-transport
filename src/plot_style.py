"""Shared matplotlib style: SciencePlots + Times New Roman, CJK fallback."""

from __future__ import annotations

import matplotlib.pyplot as plt

# SciencePlots registers styles under matplotlib; import is required once.
import scienceplots  # noqa: F401

# Latin/numbers: Times New Roman.
# Decision (2026-08-16): SciencePlots + TNR do NOT mix with Chinese (matplotlib
# warns "Glyph ... missing from font(s) Times New Roman" and does not reliably
# per-glyph-fallback within font.serif). Prefer ENGLISH axis/titles on all
# scientific figures; keep Chinese only in report/paper captions & body HTML.
SERIF_FAMILIES = [
    "Times New Roman",
    "DejaVu Serif",
    "Microsoft YaHei",
    "SimHei",
    "PingFang SC",
    "Noto Sans SC",
]
SANS_FALLBACK = [
    "Microsoft YaHei",
    "SimHei",
    "PingFang SC",
    "Noto Sans SC",
    "DejaVu Sans",
]
FIG_DPI = 300


def apply_plot_style(font_scale: float = 1.0) -> None:
    """Apply SciencePlots (no-latex) then publication fonts.

    Call AFTER any ``sns.set_theme`` so seaborn does not override the style.
    Base size ~10 pt (readable in HTML reports at 300 DPI).
    """
    plt.style.use(["science", "no-latex"])
    base = 10.0 * font_scale
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": SERIF_FAMILIES,
            "font.sans-serif": SANS_FALLBACK,
            "axes.unicode_minus": False,
            "font.size": base,
            "axes.titlesize": base * 1.15,
            "axes.labelsize": base * 1.05,
            "xtick.labelsize": base * 0.95,
            "ytick.labelsize": base * 0.95,
            "legend.fontsize": base * 0.9,
            "figure.titlesize": base * 1.2,
            "savefig.dpi": FIG_DPI,
            "figure.dpi": 120,
        }
    )
