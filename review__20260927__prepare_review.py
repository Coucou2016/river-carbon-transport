"""Freeze the current review inputs without changing production files."""
from pathlib import Path
import shutil, hashlib, json
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / 'tmp/review_20260927/packet'
PACKET.mkdir(parents=True, exist_ok=True)
paths = []
for folder in ['src', 'scripts', 'configs', 'tests', 'data_proc', 'results', 'runs', 'docs']:
    for p in (ROOT / folder).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
            paths.append(p)
paths += [ROOT / n for n in ['paper.md','paper.html','report.md','report.html','report.pdf','README.md','requirements.txt','run_pipeline.py','.gitignore'] if (ROOT/n).is_file()]
manifest = []
for p in sorted(set(paths)):
    rel = p.relative_to(ROOT)
    dest = PACKET / rel
    if dest.exists():
        raise RuntimeError('Snapshot already exists; do not overwrite: '+str(dest))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dest)
    manifest.append({'path':rel.as_posix(),'bytes':p.stat().st_size,'mtime':p.stat().st_mtime,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(OUT/'source_manifest.json').write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),'files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'packet':str(PACKET),'files':len(manifest)},ensure_ascii=False))
