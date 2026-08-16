# -*- coding: utf-8 -*-
"""Export report.pdf from report.html.

Try order:
1. Playwright Chromium print-to-PDF (preferred on Windows)
2. weasyprint (often fails without GTK on Windows)
3. reportlab text+figure fallback (always available if reportlab installed)

Reports exactly which method worked. Does not claim PDF exists on failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_HTML = ROOT / "report.html"
OUT_PDF = ROOT / "report.pdf"
FIG_DIR = ROOT / "results" / "figures"


def try_playwright() -> tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return False, f"playwright import failed: {exc}"

    if not REPORT_HTML.exists():
        return False, f"missing {REPORT_HTML}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(REPORT_HTML.resolve().as_uri(), wait_until="networkidle", timeout=180000)
            page.pdf(
                path=str(OUT_PDF),
                format="A4",
                print_background=True,
                margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"},
            )
            browser.close()
        if OUT_PDF.exists() and OUT_PDF.stat().st_size > 1000:
            return True, f"playwright chromium print-to-pdf → {OUT_PDF} ({OUT_PDF.stat().st_size/1024/1024:.2f} MB)"
        return False, "playwright ran but PDF missing/too small"
    except Exception as exc:
        return False, f"playwright PDF failed: {exc}"


def try_weasyprint() -> tuple[bool, str]:
    try:
        from weasyprint import HTML
    except Exception as exc:
        return False, f"weasyprint import failed: {exc}"
    try:
        HTML(filename=str(REPORT_HTML)).write_pdf(str(OUT_PDF))
        if OUT_PDF.exists() and OUT_PDF.stat().st_size > 1000:
            return True, f"weasyprint → {OUT_PDF} ({OUT_PDF.stat().st_size/1024/1024:.2f} MB)"
        return False, "weasyprint ran but PDF missing/too small"
    except Exception as exc:
        return False, f"weasyprint PDF failed: {exc}"


def try_reportlab_fallback() -> tuple[bool, str]:
    """Text + embedded key figures PDF when browser engines unavailable."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Image,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except Exception as exc:
        return False, f"reportlab import failed: {exc}"

    # Register a Chinese-capable font if present on Windows
    font_name = "Helvetica"
    for fp in [
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ]:
        if fp.exists():
            try:
                pdfmetrics.registerFont(TTFont("CNFont", str(fp), subfontIndex=0))
                font_name = "CNFont"
                break
            except Exception:
                try:
                    pdfmetrics.registerFont(TTFont("CNFont", str(fp)))
                    font_name = "CNFont"
                    break
                except Exception:
                    continue

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "CNTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=16,
        leading=22,
    )
    body = ParagraphStyle(
        "CNBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=10,
        leading=15,
    )
    h = ParagraphStyle(
        "CNH",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=12,
        leading=16,
        spaceBefore=10,
        spaceAfter=6,
    )

    story = []
    story.append(Paragraph("East River 河网 CO₂ 输运研究报告（PDF 回退版）", title))
    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            "完整排版见 report.html。本 PDF 由 reportlab 回退生成：含封面要点、主结论与关键图件。"
            "Residual-AI 未优于 Baseline（嵌套 CV C RMSE：MLP 0.0573 vs Baseline 0.0284）。",
            body,
        )
    )
    story.append(Paragraph("主要结论", h))
    bullets = [
        "Baseline C_aq RMSE = 0.0284；Residual-AI MLP = 0.0573（更差）；RF = 0.0745。",
        "k 修正 C RMSE = 0.0244，但 F_CO2 从约 3.24 塌到约 0.03（k_eff/k_emp ≈ 3.4e-4）。",
        "滤波 mean |S_sgs|：1.92（Δx≈838 m）→ 1.00（研究河段≈26 km；有样点单元=6）。",
        "稀疏 Π 式可解释，嵌套 CV C RMSE≈0.051 仍差于 Baseline。样本内 R²≈0.997 仅附录。",
        "F_CO2 为模型通量诊断/代理；断面非 ADCP；StreamPULSE / WQP / Alk-N-P 待补充。",
    ]
    for b in bullets:
        story.append(Paragraph(f"• {b}", body))

    key_figs = [
        "nested_cv_rmse_bar.png",
        "nested_cv_scatter_holdout.png",
        "ablation_flux_comparison.png",
        "filter_scale_sgs.png",
        "identifiability_k_vs_sgs.png",
        "identifiability_tradeoff.png",
        "dimensionless_coefficients.png",
        "gis_samples_on_network.png",
        "les_filter_conceptual.png",
    ]
    story.append(PageBreak())
    story.append(Paragraph("关键图件", h))
    for name in key_figs:
        p = FIG_DIR / name
        if not p.exists():
            story.append(Paragraph(f"[缺失] {name}", body))
            continue
        story.append(Paragraph(name, body))
        try:
            img = Image(str(p), width=170 * mm, height=110 * mm, kind="proportional")
            # constrain
            iw, ih = img.imageWidth, img.imageHeight
            max_w, max_h = 170 * mm, 200 * mm
            scale = min(max_w / iw, max_h / ih)
            img.drawWidth = iw * scale
            img.drawHeight = ih * scale
            story.append(img)
        except Exception as exc:
            story.append(Paragraph(f"[无法嵌入 {name}: {exc}]", body))
        story.append(Spacer(1, 4 * mm))

    try:
        doc = SimpleDocTemplate(
            str(OUT_PDF),
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
        )
        doc.build(story)
        if OUT_PDF.exists() and OUT_PDF.stat().st_size > 1000:
            return True, f"reportlab fallback → {OUT_PDF} ({OUT_PDF.stat().st_size/1024/1024:.2f} MB)"
        return False, "reportlab ran but PDF missing/too small"
    except Exception as exc:
        return False, f"reportlab PDF failed: {exc}"


def main() -> int:
    log: list[str] = []
    if not REPORT_HTML.exists():
        print(f"ERROR: {REPORT_HTML} not found. Run generate_report.py first.")
        return 1

    for name, fn in [
        ("playwright", try_playwright),
        ("weasyprint", try_weasyprint),
        ("reportlab", try_reportlab_fallback),
    ]:
        ok, msg = fn()
        log.append(f"[{name}] {'OK' if ok else 'FAIL'}: {msg}")
        print(log[-1])
        if ok:
            print("PDF_METHOD=" + name)
            (ROOT / "results" / "tables" / "pdf_export_log.txt").write_text(
                "\n".join(log) + "\n", encoding="utf-8"
            )
            return 0

    print("PDF_METHOD=none")
    print("report.pdf 待补充 — all exporters failed; see messages above.")
    (ROOT / "results" / "tables" / "pdf_export_log.txt").write_text(
        "\n".join(log) + "\nPDF not produced.\n", encoding="utf-8"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
