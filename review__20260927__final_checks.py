from pathlib import Path
import re,json,hashlib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((HERE/'source_manifest.json').read_text(encoding='utf-8'))
old=(ROOT/'tmp/review_20260927/packet/paper.md').read_text(encoding='utf-8')
new=(HERE/'修订稿/paper_revised.md').read_text(encoding='utf-8')
sections=lambda s:re.findall(r'^#{2,3}\s+(\d+(?:\.\d+)?)[. ]',s,re.M)
audit=json.loads((HERE/'evidence/audit_current.json').read_text(encoding='utf-8'))
retrain=json.loads((HERE/'evidence/retrain_main.json').read_text(encoding='utf-8'))
r={
 'source_file_count':len(manifest['files']),
 'changed_originals':[e['path'] for e in manifest['files'] if sha(ROOT/e['path'])!=e['sha256']],
 'all_numbered_sections_retained':sections(old)==sections(new),
 'numbered_sections':sections(new),
 'tests_passed':sum(t['status']=='PASS' for t in audit['tests']),
 'tests_total':len(audit['tests']),
 'main_retrain_matches':all(t['n']==120 and t['max_C_absdiff']<1e-12 for t in retrain),
 'stale_numeric_tokens_in_revision':[s for s in ['18.8%','0.0066','3.9×10','0.0588','-1.55','0.0409','No closure improves'] if s in new],
 'all_10_revision_images_exist':all((HERE/'修订稿'/p).exists() for p in re.findall(r'!\[.*?\]\((.*?)\)',new)),
 'raw_excel_sha256':sha(ROOT/'data_raw/east_river/east_river/Saccardi_and_Winnick_Data.xlsx'),
 'word_counts':{'original':len(old.split()),'revised':len(new.split())},
 'PDF_visual_review':'All 22 pages rendered and contact-sheet checked; tables and references inspected at page scale. Wide original panels remain best read with zoom in HTML/PDF. Not a scientific submission clearance.',
}
(HERE/'evidence/final_checks.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
assert not r['changed_originals'] and r['all_numbered_sections_retained'] and not r['stale_numeric_tokens_in_revision']
assert r['tests_passed']==r['tests_total']==34 and r['main_retrain_matches'] and r['all_10_revision_images_exist']
files=[{'path':str(p.relative_to(HERE)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='review_delivery_manifest.json']
(HERE/'review_delivery_manifest.json').write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),'scope':'Review delivery, not a production scientific run manifest','files':files},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=False,indent=2))
