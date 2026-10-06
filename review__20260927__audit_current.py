"""Read-only probes of frozen current inputs. Only review evidence is written."""
from pathlib import Path
import sys, os, json, hashlib, importlib, importlib.util, subprocess, traceback, re, base64
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PACKET=ROOT/'tmp/review_20260927/packet'
OUT=HERE/'evidence'; OUT.mkdir(exist_ok=True)
sys.dont_write_bytecode=True
os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path.insert(0,str(PACKET))
import numpy as np
import pandas as pd
from src import real_network as rn
from src.utils import load_config
cfg=load_config(PACKET/'configs/east_river.yaml')
cfg['paths']['data_raw']=str(ROOT/'data_raw')
cfg['paths']['data_proc']=str(PACKET/'data_proc')
# Force audited calls to read the existing cached discharge only, never download.
qp=ROOT/'data_raw/usgs/09112500_discharge_daily_2019.csv'
q=pd.read_csv(qp,parse_dates=['date'])
q['date']=pd.to_datetime(q.date,utc=True).dt.tz_convert(None).dt.normalize()
qmap=dict(zip(q.date,q.Q_m3s))
def cached_q(_cfg,dates):
    return {pd.Timestamp(d).normalize():float(qmap[pd.Timestamp(d).normalize()]) for d in dates}
rn.build_outlet_q_table=cached_q

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(x):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [clean(v) for v in x]
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(float,np.floating)): return float(x) if np.isfinite(x) else None
    return x
def dump(name,x): (OUT/name).write_text(json.dumps(clean(x),ensure_ascii=False,indent=2,default=str,allow_nan=False),encoding='utf-8')
r={'date_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'scope':'Frozen code probes and partial independent recomputation, not full raw-to-paper rerun.'}
old=json.loads((ROOT/'审查文档/20260919/evidence/source_manifest.json').read_text(encoding='utf-8'))
r['changed_since_previous_review']=[e['path'] for e in old if (PACKET/e['path']).exists() and sha(PACKET/e['path'])!=e['sha256']]
r['tests']=[]
for p in sorted((PACKET/'tests').glob('test_*.py')):
    spec=importlib.util.spec_from_file_location(p.stem,p); mod=importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        for name in sorted(dir(mod)):
            if not name.startswith('test_') or not callable(getattr(mod,name)): continue
            try:
                getattr(mod,name)(); r['tests'].append({'file':p.name,'test':name,'status':'PASS'})
            except Exception:
                r['tests'].append({'file':p.name,'test':name,'status':'FAIL','error':traceback.format_exc()})
    except Exception:
        r['tests'].append({'file':p.name,'status':'IMPORT_FAIL','error':traceback.format_exc()})
proc=PACKET/'data_proc'; keys=['date','reach_id','sample_id']
obs=pd.read_csv(proc/'reach_daily_observations.csv',parse_dates=['date'])
segobs=pd.read_csv(proc/'reach_daily_observations_segmented.csv',parse_dates=['date'])
segs=pd.read_csv(proc/'network_segments.csv')
train=pd.read_csv(proc/'sgs_training_data.csv',parse_dates=['date'])
diag=rn.diagnose_sgs(segobs,segs)
base=rn.route_steady_state(segobs,segs)
saved=pd.read_csv(proc/'baseline_model_output.csv',parse_dates=['date'])
bm=base.merge(saved,on=keys,suffixes=('_new','_saved'),validate='one_to_one')
tm=train.merge(diag,on=keys,validate='one_to_one')
r['partial_reproduction']={'baseline_n':len(bm),'baseline_maxdiff':(bm.C_model_mol_m3_new-bm.C_model_mol_m3_saved).abs().max(),'sgs_maxdiff':(tm.S_sgs_residual_mol_m2d-tm.S_sgs_mol_m2d).abs().max()}
cv=importlib.import_module('src.12_nested_cv_transport')
feat=obs.merge(train,on=keys,suffixes=('','_tr'),validate='one_to_one')
tr=np.flatnonzero(feat.reach_id.ne('R005')); te=np.flatnonzero(feat.reach_id.eq('R005'))
y=cv._fold_sgs_targets(feat,segobs,segs,tr,te)
pert=segobs.copy(); pert.loc[pert.reach_id.eq('R005'),'C_aq_obs_mol_m3']+=.1
yp=cv._fold_sgs_targets(feat,pert,segs,tr,te)
fullpert=rn.diagnose_sgs(pert,segs)
dd=diag.merge(fullpert,on=keys,suffixes=('_before','_after'))
r['fold_label_test']={'train_maxdiff':np.nanmax(abs(y[tr]-yp[tr])),'test_labels_all_missing':bool(np.isnan(y[te]).all()),'full_data_train_targets_changed':int(((dd.S_sgs_mol_m2d_before-dd.S_sgs_mol_m2d_after).abs().gt(1e-10)&dd.reach_id.ne('R005')).sum())}
k,meta=cv._fold_k_targets(feat,segobs,segs,tr,te)
r['fold_k']={'finite_train':int(np.isfinite(k[tr]).sum()),'finite_test':int(np.isfinite(k[te]).sum()),'meta':meta}
oof=pd.read_csv(proc/'nested_cv_holdout_predictions.csv',parse_dates=['date'])
r['metrics']=[]
for group,g in oof.groupby(['scheme','model','cv_protocol']):
    e=g.C_model_mol_m3-g.C_obs_mol_m3
    record=dict(zip(['scheme','model','protocol'],group)); record.update(n=len(g),duplicates=int(g.duplicated(keys).sum()),rmse=float(np.sqrt(np.mean(e**2))),mae=float(e.abs().mean()),bias=float(e.mean()),n_zero_c=int(g.C_model_mol_m3.eq(0).sum()))
    m=g.merge(obs[keys+['k_CO2_m_d','C_eq_mol_m3']],on=keys,suffixes=('','_emp'),validate='one_to_one')
    record['k_ratio_median']=float((m.k_CO2_m_d/m.k_CO2_m_d_emp).median())
    record['k_median']=float(g.k_CO2_m_d.median())
    record['flux_area_sum']=float((g.F_CO2_mol_m2d*g.L_control_m*g.W_m).sum())
    res=g.Q_m3s*(g.C_in_mol_m3-g.C_model_mol_m3)+g.L_control_m*g.W_m*(g.S_sgs_used_mol_m2d-g.k_CO2_m_d*(g.C_model_mol_m3-g.C_eq_mol_m3))/86400
    record['n_mass_balance_residual_gt_1e_8']=int(res.abs().gt(1e-8).sum()); record['max_mass_balance_residual']=float(res.abs().max())
    r['metrics'].append(record)
r['subgroups']=[]
for group,g in oof[oof.cv_protocol.eq('loo_reach')].groupby(['scheme','model']):
    for label,mask in [('mainstem',g.reach_id.eq('R008')),('tributary',g.reach_id.isin(['R002','R003','R004','R005']))]:
        v=g.loc[mask]; r['subgroups'].append({'scheme':group[0],'model':group[1],'group':label,'n':len(v),'rmse':np.sqrt(np.mean((v.C_model_mol_m3-v.C_obs_mol_m3)**2))})
eq=importlib.import_module('src.16_equifinality_surface')
em=eq.load_per_sample(cfg); sf=eq.build_surface(em)
ed=em.merge(diag[keys+['Q_routed_m3s','L_control_m']],on=keys,validate='one_to_one').merge(obs[keys+['W_m']].rename(columns={'W_m':'width_diag'}),on=keys,validate='one_to_one')
correct_qa=86400*ed.Q_routed_m3s/(ed.L_control_m*ed.width_diag)
pred=eq.c_model(em.q_A_m_d.values,em.C_in_obs_mol_m3.values,em.C_eq_mol_m3.values,em.k_CO2_m_d.values,em.S_diag_mol_m2d.values)
rep=eq.representative_sample(em)
r['objective']={k:v for k,v in sf.items() if np.ndim(v)==0}
r['objective'].update(merged_columns=list(em.columns),n_qa_disagree=int((em.q_A_m_d-correct_qa).abs().gt(1e-8).sum()),qa_maxdiff=(em.q_A_m_d-correct_qa).abs().max(),reconstruct_c_maxdiff=float(np.max(abs(pred-em.C_aq_obs_mol_m3))),representative_key={k:rep[k] for k in keys},representative_sdiag=float(rep.S_diag_mol_m2d),representative_consistent_s=float(rep.q_A_m_d*(rep.C_aq_obs_mol_m3-rep.C_in_obs_mol_m3)+rep.k_CO2_m_d*(rep.C_aq_obs_mol_m3-rep.C_eq_mol_m3)))
from src.east_river_real_data import load_hydroshare_samples,hydroshare_excel_path
raw=load_hydroshare_samples(cfg); raw['sample_id']=raw['Sample ID'] if 'Sample ID' in raw else raw['SampleID']
mm=obs.merge(raw,on=keys,suffixes=('_proc','_raw'),validate='one_to_one')
r['raw_trace']={'path':str(hydroshare_excel_path(cfg)),'sha256':sha(hydroshare_excel_path(cfg)),'n_raw_loaded':len(raw),'n_matched':len(mm),'checks':{}}
for col in ['T_C','DOC_mgL','DIC_mmolL','DO_mgL','pCO2_uatm','C_aq_obs_mol_m3']:
    if col+'_proc' in mm and col+'_raw' in mm:
        a,b=mm[col+'_proc'],mm[col+'_raw']; r['raw_trace']['checks'][col]={'nonmissing_pairs':int((a.notna()&b.notna()).sum()),'maxdiff':(a-b).abs().max()}
html=(PACKET/'paper.html').read_text(encoding='utf-8'); md=(PACKET/'paper.md').read_text(encoding='utf-8')
embeds=[hashlib.sha256(base64.b64decode(s)).hexdigest() for s in re.findall(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)',html)]
r['figures']=[{'path':rel,'exists':(PACKET/rel).is_file(),'matches_html':sha(PACKET/rel) in embeds} for rel in re.findall(r'!\[.*?\]\(([^)]+)\)',md)]
r['commands']=[]
for mode in ['development','submission']:
    cmd=[sys.executable,str(PACKET/'scripts/verify_paper.py'),'--mode',mode]
    done=subprocess.run(cmd,cwd=PACKET,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (OUT/('verify_'+mode+'.log')).write_text(done.stdout+'\n'+done.stderr,encoding='utf-8')
    r['commands'].append({'cmd':cmd,'exit_code':done.returncode})
dump('audit_current.json',r)
print(json.dumps(clean(r),ensure_ascii=False,indent=2,default=str))
