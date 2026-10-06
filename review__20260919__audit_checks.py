"""Read-only scientific review probes; synthetic fixtures are TESTS, never research data.
Run with the project's .venv Python. Writes only review evidence beside this file.
The frozen packet and production scientific outputs are never modified.
"""
from pathlib import Path
import os, sys, json, hashlib, subprocess, importlib, platform, math
from datetime import datetime, timezone
import importlib.metadata as metadata

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "tmp/review_20260919/packet"
OUT = Path(__file__).resolve().parent / "evidence"
OUT.mkdir(parents=True, exist_ok=True)
sys.dont_write_bytecode = True
sys.path.insert(0, str(PACKET))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import numpy as np
import pandas as pd
from src.real_network import control_lengths_from_chainage, diagnose_sgs, route_steady_state
from src.cell_dag_filter import mass_conserving_aggregate, route_cell_dag_date

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def dump(name, value):
    def clean(x):
        if isinstance(x, dict): return {k:clean(v) for k,v in x.items()}
        if isinstance(x, (list,tuple)): return [clean(v) for v in x]
        if isinstance(x, float) and not math.isfinite(x): return None
        return x
    (OUT / name).write_text(json.dumps(clean(value), ensure_ascii=False, indent=2, default=str, allow_nan=False), encoding='utf-8')

manifest = []
for p in sorted(PACKET.rglob('*')):
    if not p.is_file() or '__pycache__' in p.parts: continue
    rel = p.relative_to(PACKET)
    live = ROOT / rel
    manifest.append(dict(path=rel.as_posix(), bytes=p.stat().st_size, sha256=sha(p),
                         live_matches=live.exists() and sha(live) == sha(p)))
dump('source_manifest.json', manifest)
result = {'timestamp_utc':datetime.now(timezone.utc).isoformat(), 'packet':str(PACKET),
          'python':sys.version, 'platform':platform.platform(), 'packages':{},
          'scope':'Read-only packet audit, not a complete scientific rerun.'}
for name in ['numpy','pandas','scipy','scikit-learn','xgboost','geopandas','shapely','pytest']:
    try: result['packages'][name] = metadata.version(name)
    except metadata.PackageNotFoundError: result['packages'][name] = 'NOT INSTALLED'
result['commands'] = []
for rel in ['tests/test_network_p0_fixes.py','tests/test_cell_dag_filter.py','scripts/verify_paper.py']:
    p = subprocess.run([sys.executable, str(PACKET / rel)], cwd=PACKET,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
    name = Path(rel).stem + '.log'
    (OUT / name).write_text(p.stdout+'\n'+p.stderr, encoding='utf-8')
    result['commands'].append({'command':rel,'exit_code':p.returncode,'log':name})

result['length_fixed_10km_span'] = {str(n):float(control_lengths_from_chainage(np.linspace(0,10000,n)).sum()) for n in [2,10,100]}
result['duplicate_chainage_lengths'] = control_lengths_from_chainage(np.array([100.,100.,100.])).tolist()
parts = [dict(Q_m3s=1,C_mol_m3=c,area_m2=100,h_m=.3,k_CO2_m_d=0,C_eq_mol_m3=0,q_mode='outlet') for c in [2.,4.]]
a = mass_conserving_aggregate(parts)
result['serial_test_fixture'] = dict(input=parts, output=a, returned_outlet_QC=a['Q_m3s']*a['C_mol_m3'], actual_outlet_QC=4.)
obs = {'U':dict(Q_m3s=1,C_mol_m3=2,area_m2=100,k_CO2_m_d=0,C_eq_mol_m3=0),
       'W':dict(Q_m3s=3,C_mol_m3=4,area_m2=100,k_CO2_m_d=0,C_eq_mol_m3=0)}
recs, state, cov = route_cell_dag_date({'U':[], 'MISSING':[], 'V':['U','MISSING'], 'W':['V']}, obs, 0)
result['missing_ancestor_and_lateral_fixture'] = dict(records=recs, coverage=cov,
    explanation='V lacks one parent; W is nevertheless marked sync_complete. With lateral carbon influx set to zero, W residual should be 8640, not 5184; actual lateral carbon is unspecified.')

proc = PACKET / 'data_proc'
seg = pd.read_csv(proc/'network_segments.csv')
obsseg = pd.read_csv(proc/'reach_daily_observations_segmented.csv',parse_dates=['date'])
diag = diagnose_sgs(obsseg, seg)
keys = ['date','reach_id','sample_id']
target = 'S_sgs_residual_mol_m2d'
result['diagnostic_columns'] = list(diag.columns)
changed = obsseg.copy()
hold = changed.reach_id.eq('R005')
changed.loc[hold,'C_aq_obs_mol_m3'] += 0.1
d2 = diagnose_sgs(changed, seg)
scol = next(c for c in diag if c.startswith('S_sgs'))
m = diag.merge(d2,on=keys,suffixes=('_original','_perturbed'),validate='one_to_one')
m['delta'] = m[scol+'_perturbed']-m[scol+'_original']
affected = m.loc[m.reach_id.ne('R005') & m.delta.abs().gt(1e-10),keys+['delta']]
result['heldout_concentration_perturbation'] = dict(held_reach='R005',increment_mol_m3=.1,
    n_training_targets_changed=len(affected),affected=affected.to_dict('records'))

cv = importlib.import_module('src.12_nested_cv_transport')
flat = pd.read_csv(proc/'reach_daily_observations.csv',parse_dates=['date'])
train = pd.read_csv(proc/'sgs_training_data.csv',parse_dates=['date'])
merged = flat.merge(train,on=keys,how='left',suffixes=('','_tr')).reset_index(drop=True)
merged = merged.drop(columns=['C_in_obs_mol_m3','L_control_m'],errors='ignore').merge(diag[keys+['C_in_obs_mol_m3','L_control_m']],on=keys,how='left')
te = np.flatnonzero(merged.reach_id.eq('R005'))
tr = np.flatnonzero(merged.reach_id.ne('R005'))
captured = {}
orig = cv.invert_k_needed
def capture(frame):
    captured['length_columns'] = [c for c in frame if c.startswith('L_control')]
    captured['has_exact_L_control_m'] = 'L_control_m' in frame
    captured['fallback_L_m_equals_full_length'] = bool(np.allclose(frame.L_m,frame.L_control_m_x)) if 'L_control_m_x' in frame else None
    return orig(frame)
cv.invert_k_needed = capture
_, km = cv._fold_k_targets(merged, obsseg, seg, tr, te)
cv.invert_k_needed = orig
result['fold_k_merge_probe'] = dict(**captured,meta=km)
qmerge = flat[keys+['Q_m3s']].merge(diag[keys+['Q_m3s']],on=keys,suffixes=('_input','_routed'))
result['q_input_vs_routed'] = dict(n_different=int((qmerge.Q_m3s_input-qmerge.Q_m3s_routed).abs().gt(1e-9).sum()),
    max_abs_difference=float((qmerge.Q_m3s_input-qmerge.Q_m3s_routed).abs().max()))

oof = pd.read_csv(proc/'nested_cv_holdout_predictions.csv')
metrics=[]
for group,g in oof.groupby(['scheme','model','cv_protocol']):
    metrics.append(dict(zip(['scheme','model','cv_protocol'],group)) | dict(n=len(g),duplicate_keys=int(g.duplicated(keys).sum()),
                   rmse_c=float(np.sqrt(np.mean((g.C_model_mol_m3-g.C_obs_mol_m3)**2)))))
result['oof_recomputed'] = metrics
fresh_baseline = route_steady_state(obsseg, seg)
old_baseline = pd.read_csv(proc/'baseline_model_output.csv',parse_dates=['date'])
bm = fresh_baseline.merge(old_baseline,on=keys,suffixes=('_fresh','_saved'),validate='one_to_one')
sm = train.merge(diag,on=keys,validate='one_to_one')
result['fresh_partial_reproduction'] = dict(n_baseline=len(bm),
    max_baseline_C_difference=float((bm.C_model_mol_m3_fresh-bm.C_model_mol_m3_saved).abs().max()),
    max_SGS_target_difference=float((sm.S_sgs_residual_mol_m2d-sm.S_sgs_mol_m2d).abs().max()),
    statement='Reproduction from processed inputs only; does not validate physics or full pipeline.')
cells = pd.read_csv(proc/'filter_scale_cell_residuals.csv')
result['filter_columns'] = list(cells)
if {'Sigma_QC','Q_m3s','C_obs_mol_m3'} <= set(cells):
    discrepancy = (cells.Sigma_QC-cells.Q_m3s*cells.C_obs_mol_m3).abs()
    result['filter_flux_state_discrepancy'] = dict(n=len(cells),n_discrepant=int(discrepancy.gt(1e-10).sum()),max_abs=float(discrepancy.max()))
old = json.loads((PACKET/'results/tables/artifact_manifest.json').read_text(encoding='utf-8'))
result['old_artifact_manifest_check'] = [dict(path=rel,exists=(PACKET/rel).exists(),
    sha_matches=(PACKET/rel).exists() and sha(PACKET/rel)==v['sha256']) for rel,v in old['artifacts'].items()]
dump('audit_results.json',result)
print(json.dumps(result,ensure_ascii=False,indent=2,default=str))
