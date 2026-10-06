"""Verify reviewed originals and deliverables; write only final review evidence."""
from pathlib import Path
import ast
import hashlib
import json
import re
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / 'tmp/review_20260919/packet'
OUT = HERE / 'evidence'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

manifest = json.loads((OUT / 'source_manifest.json').read_text(encoding='utf-8'))
checks = []
for entry in manifest:
    rel = entry['path']
    checks.append({'path': rel,
                   'live_matches': (ROOT / rel).is_file() and sha(ROOT / rel) == entry['sha256'],
                   'packet_matches': (PACKET / rel).is_file() and sha(PACKET / rel) == entry['sha256']})
raw = json.loads((OUT / 'supplement_results.json').read_text(encoding='utf-8'))['raw_data_trace']
raw_matches = sha(Path(raw['path'])) == raw['sha256']
stamp = datetime.now(timezone.utc).isoformat()
reviews = [{'path': p.name, 'sha256': sha(p), 'bytes': p.stat().st_size}
           for p in sorted(HERE.glob('Reviewer_*.md'))]
(OUT / 'frozen_reviews.json').write_text(json.dumps({'recorded_at_utc': stamp, 'reports': reviews}, ensure_ascii=False, indent=2), encoding='utf-8')

# Resolve local Markdown links; the final integrity file is about to be created.
missing_links = []
for p in HERE.glob('*.md'):
    for link in re.findall(r'\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
        target = link.strip('<>').split('#')[0]
        if not target or target.startswith(('https://', 'http://')):
            continue
        target = re.sub(r':\d+$', '', target)
        if re.match(r'^/[A-Za-z]:/', target):
            target = target[1:]
        resolved = Path(target) if Path(target).is_absolute() else p.parent / target
        if resolved == OUT / 'final_integrity_check.json':
            continue
        if not resolved.exists():
            missing_links.append({'document': p.name, 'target': link})
for p in HERE.glob('audit_*.py'):
    ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
report = {'timestamp_utc': stamp, 'source_files_checked': len(checks),
          'live_mismatches': [x['path'] for x in checks if not x['live_matches']],
          'packet_mismatches': [x['path'] for x in checks if not x['packet_matches']],
          'raw_excel_matches_initial_hash': raw_matches,
          'reviewer_reports': len(reviews), 'missing_local_markdown_links': missing_links,
          'audit_script_syntax': 'PASS',
          'scope': 'Only the 187 manifest files and the traced raw Excel are covered by original-file integrity checks.'}
(OUT / 'final_integrity_check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
if report['live_mismatches'] or report['packet_mismatches'] or not raw_matches or missing_links:
    raise SystemExit(1)
