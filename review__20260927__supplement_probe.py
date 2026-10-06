from pathlib import Path
import sys,json,hashlib
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent; P=ROOT/'tmp/review_20260927/packet'
sys.path.insert(0,str(P)); sys.dont_write_bytecode=True
from src.east_river_real_data import load_hydroshare_samples
from src.utils import load_config,co2_eq_concentration
cfg=load_config(P/'configs/east_river.yaml');cfg['paths']['data_raw']=str(ROOT/'data_raw')
raw=load_hydroshare_samples(cfg); obs=pd.read_csv(P/'data_proc/reach_daily_observations.csv',parse_dates=['date'])
raw=raw.rename(columns={'Sample':'sample_id'})
print('raw columns',list(raw.columns))
if 'sample_id' not in raw: raw['sample_id']=raw['SampleID']
keys=['date','reach_id','sample_id']; m=obs.merge(raw,on=keys,validate='one_to_one',suffixes=('','_raw'))
r={'raw_pco2_n':len(m),'raw_pco2_maxdiff':float((m.pCO2_uatm-m.CO2_ppm_corrected).abs().max())}
h=.035*np.exp(2400*(1/(m.T_C+273.15)-1/298.15))
c=h*(m.CO2_ppm_corrected*1e-6*1.01325)*1000
r['Henry_recompute_maxdiff']=float((c-m.C_aq_obs_mol_m3).abs().max())
f=pd.read_csv(P/'data_proc/nested_cv_holdout_predictions.csv')
f=f.loc[f.cv_protocol=='loo_reach']; f['se']=(f.C_model_mol_m3-f.C_obs_mol_m3)**2
b=f.loc[f.scheme=='baseline'].groupby('reach_id').agg(n=('se','size'),sse_base=('se','sum'))
a=f.loc[f.model=='mlp'].groupby('reach_id').agg(sse_mlp=('se','sum'))
t=b.join(a);t['sse_gain']=t.sse_base-t.sse_mlp
r['R002_fraction_of_SSE_gain']=float(t.loc['R002','sse_gain']/t.sse_gain.sum())
r['reach_equal_RMSE']={k:float(np.sqrt((t[v]/t.n).mean())) for k,v in [('baseline','sse_base'),('mlp','sse_mlp')]}
u=t.drop('R002');r['without_R002_pooled_RMSE']={k:float(np.sqrt(u[v].sum()/u.n.sum())) for k,v in [('baseline','sse_base'),('mlp','sse_mlp')]}
r['per_reach']=t.reset_index().to_dict('records')
mapping=pd.read_csv(P/'data_proc/gis_reach_line_mapping.csv');r['mapped_NHD_counts']=mapping.groupby('reach_id').size().to_dict()
manifest=json.loads((HERE/'source_manifest.json').read_text(encoding='utf-8'))
r['production_source_changes_during_review']=[e['path'] for e in manifest['files'] if hashlib.sha256((ROOT/e['path']).read_bytes()).hexdigest()!=e['sha256']]
(HERE/'evidence/supplement.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(r,indent=2))
