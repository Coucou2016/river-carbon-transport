"""Round-level verification of paper.md / paper.html (read-only)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
md = (ROOT / "paper.md").read_text(encoding="utf-8")
html = (ROOT / "paper.html").read_text(encoding="utf-8")

nums = ["0.0284", "0.0573", "0.0745", "0.0244", "0.0506",
        "3.35", "3.24", "0.031", "1.92", "1.00", "838"]
print("frozen-number counts in paper.md:")
for n in nums:
    print(f"  {n}: {md.count(n)}")

print("base64 count md:", md.count("data:image/png;base64"))
print("base64 count html:", html.count("data:image/png;base64"))

http_md = re.findall(r"!\[[^\]]*\]\(http|<http", md)
http_assets = re.findall(r'<(img|link|script)[^>]*(?:href|src)="http', html)
print("external img/link in md:", len(http_md))
print("external img/link/script in html:", len(http_assets))
print("any href/src=http in html:", len(re.findall(r'(?:href|src)="http', html)))

print("local path D: in md:", md.count("D:"), "| html:", html.count("D:"))
print(".venv in md:", md.count(".venv"), "| html:", html.count(".venv"))
print("'scripts/' narrative in md:", md.count("scripts/"), "| html:", html.count("scripts/"))

print("em-dash count md:", md.count("\u2014"))
bold = re.findall(r"\*\*[^*\n]+\*\*", md)
print("bold spans md:", len(bold), "->", bold[:6])

body = md.split("\n", 1)[0:]
sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", md) if len(s.strip()) > 30]
avg = sum(len(s.split()) for s in sents) / max(1, len(sents))
print(f"mean sentence length (words): {avg:.1f} over {len(sents)} sentences")
