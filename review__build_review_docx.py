from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(r"D:\Projects\20260611-river-carbon-transport")
SOURCE = ROOT / "审查文档" / "审查文档_严格审稿与真实性证据审计_20260827.md"
OUTPUT = ROOT / "审查文档" / "审查文档_严格审稿与真实性证据审计_20260827.docx"

NAVY = "17365D"
TEAL = "1F6D73"
PALE_TEAL = "DDEBEC"
PALE_BLUE = "EAF0F6"
PALE_ORANGE = "FCE4D6"
PALE_GRAY = "F2F4F6"
DARK = "20252B"
MID = "5A6670"
WHITE = "FFFFFF"
ORANGE = "C65911"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=90, start=100, bottom=90, end=100) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_keep_with_next(paragraph, value=True) -> None:
    paragraph.paragraph_format.keep_with_next = value


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("第 ")
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor.from_string(MID)
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr_text)
    run._r.append(fld_char2)
    run.add_text(" 页")


def set_run_font(run, latin="Aptos", east_asia="Microsoft YaHei", size=None, color=None, bold=None):
    run.font.name = latin
    run._element.rPr.rFonts.set(qn("w:eastAsia"), east_asia)
    if size is not None:
        run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        run.bold = bold


def configure_styles(doc: Document) -> None:
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    normal.font.size = Pt(10.2)
    normal.font.color.rgb = RGBColor.from_string(DARK)
    normal.paragraph_format.space_after = Pt(5.5)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    normal.paragraph_format.line_spacing = 1.12

    for name, size, color, before, after in (
        ("Title", 23, NAVY, 0, 14),
        ("Heading 1", 17, NAVY, 14, 7),
        ("Heading 2", 13.2, NAVY, 12, 5),
        ("Heading 3", 11.2, TEAL, 9, 3),
    ):
        style = styles[name]
        style.font.name = "Aptos Display"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.keep_together = True

    if "Audit Caption" not in styles:
        caption = styles.add_style("Audit Caption", WD_STYLE_TYPE.PARAGRAPH)
    else:
        caption = styles["Audit Caption"]
    caption.font.name = "Aptos"
    caption._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    caption.font.size = Pt(8.4)
    caption.font.italic = True
    caption.font.color.rgb = RGBColor.from_string(MID)
    caption.paragraph_format.space_before = Pt(3)
    caption.paragraph_format.space_after = Pt(8)
    caption.paragraph_format.keep_with_next = False

    if "Audit Code" not in styles:
        code = styles.add_style("Audit Code", WD_STYLE_TYPE.PARAGRAPH)
    else:
        code = styles["Audit Code"]
    code.font.name = "Consolas"
    code._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    code.font.size = Pt(8.4)
    code.paragraph_format.left_indent = Cm(0.45)
    code.paragraph_format.right_indent = Cm(0.25)
    code.paragraph_format.space_after = Pt(2)


def configure_page(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.65)
    section.bottom_margin = Cm(1.55)
    section.left_margin = Cm(1.8)
    section.right_margin = Cm(1.8)
    section.header_distance = Cm(0.75)
    section.footer_distance = Cm(0.75)

    header = section.header
    p = header.paragraphs[0]
    p.text = "RIVER CARBON TRANSPORT  /  INTEGRITY & REPRODUCIBILITY AUDIT"
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_run_font(p.runs[0], size=7.5, color=MID, bold=True)
    p.paragraph_format.space_after = Pt(0)
    p_pr = p._p.get_or_add_pPr()
    border = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "3")
    bottom.set(qn("w:color"), TEAL)
    border.append(bottom)
    p_pr.append(border)

    footer = section.footer
    fp = footer.paragraphs[0]
    add_page_number(fp)


def add_memo_masthead(doc: Document) -> None:
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Cm(11.8)
    table.columns[1].width = Cm(5.3)
    left, right = table.rows[0].cells
    left.width = Cm(11.8)
    right.width = Cm(5.3)
    set_cell_shading(left, NAVY)
    set_cell_shading(right, TEAL)
    set_cell_margins(left, 130, 180, 130, 180)
    set_cell_margins(right, 130, 160, 130, 160)
    lp = left.paragraphs[0]
    lp.text = "STRICT REVIEW MEMO"
    set_run_font(lp.runs[0], size=12, color=WHITE, bold=True)
    lp.paragraph_format.space_after = Pt(0)
    rp = right.paragraphs[0]
    rp.text = "2026-08-27\nSTATUS: BLOCKED"
    rp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in rp.runs:
        set_run_font(run, size=8.5, color=WHITE, bold=True)
    rp.paragraph_format.space_after = Pt(0)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


INLINE_TOKEN = re.compile(r"(\*\*.*?\*\*|`.*?`)")


def add_inline(paragraph, text: str) -> None:
    text = text.replace("  ", " ")
    pos = 0
    for m in INLINE_TOKEN.finditer(text):
        if m.start() > pos:
            paragraph.add_run(text[pos:m.start()])
        token = m.group(0)
        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            run.bold = True
            run.font.color.rgb = RGBColor.from_string(NAVY)
        else:
            run = paragraph.add_run(token[1:-1])
            run.font.name = "Consolas"
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
            run.font.size = Pt(9.1)
            run.font.color.rgb = RGBColor.from_string(TEAL)
        pos = m.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])


def add_callout(doc: Document, text: str, critical: bool = False) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    set_cell_shading(cell, PALE_ORANGE if critical else PALE_BLUE)
    set_cell_margins(cell, 130, 170, 130, 170)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    add_inline(p, text)
    for run in p.runs:
        run.font.size = Pt(9.4)
        if critical:
            run.font.color.rgb = RGBColor.from_string(ORANGE)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_markdown_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=ncols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = True
    for i, row in enumerate(rows):
        for j in range(ncols):
            cell = table.cell(i, j)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell, 80, 85, 80, 85)
            value = row[j] if j < len(row) else ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            add_inline(p, value)
            for run in p.runs:
                set_run_font(run, size=7.7 if ncols >= 4 else 8.2, color=DARK, bold=(i == 0))
            if i == 0:
                set_cell_shading(cell, NAVY)
                for run in p.runs:
                    run.font.color.rgb = RGBColor.from_string(WHITE)
            elif i % 2 == 0:
                set_cell_shading(cell, PALE_GRAY)
    set_repeat_table_header(table.rows[0])
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(1)


def parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    raw = []
    i = start
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        raw.append(cells)
        i += 1
    if len(raw) >= 2 and all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in raw[1]):
        raw.pop(1)
    return raw, i


IMAGE_RE = re.compile(r"^!\[(.*?)\]\((.*?)\)$")


def add_image(doc: Document, alt: str, path_text: str) -> None:
    path_text = path_text.replace("/", "\\")
    image_path = Path(path_text)
    if not image_path.is_absolute():
        image_path = (SOURCE.parent / image_path).resolve()
    if not image_path.exists():
        add_callout(doc, f"图像缺失：{image_path}", critical=True)
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_together = True
    try:
        run = p.add_run()
        run.add_picture(str(image_path), width=Inches(6.35))
    except Exception as exc:
        add_callout(doc, f"图像无法嵌入：{image_path}（{exc}）", critical=True)
        return
    caption = doc.add_paragraph(style="Audit Caption")
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.add_run(f"审查证据图｜{alt}")


def build() -> None:
    doc = Document()
    configure_page(doc)
    configure_styles(doc)
    doc.core_properties.title = "河流碳输运项目：严格审稿与真实性证据审计"
    doc.core_properties.subject = "代码、数据、论文、图件、统计与可复现性审查"
    doc.core_properties.author = "Codex-assisted audit; human author verification required"
    doc.core_properties.keywords = "research integrity, reproducibility, code review, data provenance, figure audit"

    add_memo_masthead(doc)

    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    i = 0
    in_code = False
    code_buffer: list[str] = []
    # Headings are kept with their following text.  Avoid manual page breaks:
    # several sections are intentionally short, and forced breaks produce
    # mostly blank pages in Word/PDF rendering.
    section_break_heads: set[str] = set()

    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("```"):
            if in_code:
                p = doc.add_paragraph(style="Audit Code")
                p.add_run("\n".join(code_buffer))
                p_pr = p._p.get_or_add_pPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:fill"), PALE_GRAY)
                p_pr.append(shd)
                code_buffer = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buffer.append(line)
            i += 1
            continue
        if not line.strip():
            i += 1
            continue

        image_match = IMAGE_RE.match(line.strip())
        if image_match:
            add_image(doc, image_match.group(1), image_match.group(2))
            i += 1
            continue

        if line.lstrip().startswith("|"):
            rows, i = parse_table(lines, i)
            add_markdown_table(doc, rows)
            continue

        if line.startswith("# "):
            p = doc.add_paragraph(style="Title")
            add_inline(p, line[2:].strip())
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.keep_with_next = True
            i += 1
            continue

        if line.startswith("## "):
            heading = line[3:].strip()
            if heading in section_break_heads:
                doc.add_page_break()
            p = doc.add_paragraph(style="Heading 1")
            add_inline(p, heading)
            i += 1
            continue

        if line.startswith("### "):
            p = doc.add_paragraph(style="Heading 2")
            add_inline(p, line[4:].strip())
            i += 1
            continue

        if line.startswith("#### "):
            p = doc.add_paragraph(style="Heading 3")
            add_inline(p, line[5:].strip())
            i += 1
            continue

        if line.startswith("> "):
            block_lines = []
            while i < len(lines) and lines[i].startswith("> "):
                block_lines.append(lines[i][2:].strip())
                i += 1
            block = "  ·  ".join(block_lines)
            add_callout(doc, block, critical=("不具备投稿" in block or "BLOCK" in block))
            continue

        if re.match(r"^\s*[-*] \[[ xX]\] ", line):
            checked = line.lstrip()[3].lower() == "x"
            text = re.sub(r"^\s*[-*] \[[ xX]\] ", "", line)
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.left_indent = Cm(0.7)
            p.paragraph_format.first_line_indent = Cm(-0.35)
            add_inline(p, ("☑ " if checked else "☐ ") + text)
            i += 1
            continue

        if re.match(r"^\s*[-*] ", line):
            text = re.sub(r"^\s*[-*] ", "", line)
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.left_indent = Cm(0.7)
            p.paragraph_format.first_line_indent = Cm(-0.35)
            add_inline(p, text)
            i += 1
            continue

        numbered = re.match(r"^\s*(\d+)\.\s+(.*)$", line)
        if numbered:
            number, text = numbered.groups()
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.75)
            p.paragraph_format.first_line_indent = Cm(-0.35)
            lead = p.add_run(f"{number}. ")
            lead.bold = True
            lead.font.color.rgb = RGBColor.from_string(NAVY)
            add_inline(p, text)
            i += 1
            continue

        p = doc.add_paragraph()
        add_inline(p, line)
        if line.startswith("**证据。**") or line.startswith("**影响。**") or line.startswith("**必须修改。**") or line.startswith("**通过测试。**"):
            p.paragraph_format.left_indent = Cm(0.2)
        i += 1

    # Ensure East-Asian font metadata is present even for runs created by list/table styles.
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            r_pr = run._element.get_or_add_rPr()
            r_fonts = r_pr.rFonts
            if r_fonts is None:
                r_fonts = OxmlElement("w:rFonts")
                r_pr.insert(0, r_fonts)
            r_fonts.set(qn("w:eastAsia"), "Microsoft YaHei")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
