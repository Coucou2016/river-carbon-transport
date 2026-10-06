"""Re-fit main held-out models from frozen processed inputs; no production writes."""
from pathlib import Path
import sys, os, json, importlib, warnings
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
P=ROOT/'tmp/review_20260927/packet'
sys.dont_write_bytecode=True; sys.path.insert(0,str(P))
from src import real_network as rn
from src.utils import load_config
cfg=load_config(P/'configs/east_river.yaml')
cfg['paths']['data_raw']=str(ROOT/'data_raw'); cfg['paths']['data_proc']=str(P/'data_proc')
q=pd.read_csv(ROOT/'data_raw/usgs/09112500_discharge_daily_2019.csv',parse_dates=['date'])
qmap=dict(zip(pd.to_datetime(q.date,utc=True).dt.tz_convert(None).dt.normalize(),q.Q_m3s))
rn.build_outlet_q_table=lambda _cfg,dates:{pd.Timestamp(d).normalize():float(qmap[pd.Timestamp(d).normalize()]) for d in dates}
cv=importlib.import_module('src.12_nested_cv_transport')
proc=P/'data_proc'; keys=['date','reach_id','sample_id']
obs=pd.read_csv(proc/'reach_daily_observations.csv',parse_dates=['date'])
seg=pd.read_csv(proc/'reach_daily_observations_segmented.csv',parse_dates=['date'])
net=pd.read_csv(proc/'network_segments.csv')
train=pd.read_csv(proc/'sgs_training_data.csv',parse_dates=['date'])
obs=obs.merge(train,on=keys,how='left',suffixes=('','_tr')).reset_index(drop=True)
diag=rn.diagnose_sgs(seg,net)
obs=obs.drop(columns=['C_in_obs_mol_m3','L_control_m'],errors='ignore').merge(diag[keys+['C_in_obs_mol_m3','L_control_m']],on=keys,how='left',validate='one_to_one')
if 'control_volume_id' in seg and 'control_volume_id' not in obs:
    obs=obs.merge(seg[keys+['control_volume_id']],on=keys,how='left',validate='one_to_one')
old=pd.read_csv(proc/'nested_cv_holdout_predictions.csv',parse_dates=['date'])
results=[]
for scheme,model in [('residual_ai','mlp'),('residual_ai','random_forest'),('k_correction','xgboost')]:
    print('START',scheme,model,flush=True)
    new,sat,meta=cv.grouped_holdout(scheme=scheme,model_name=model,obs=obs,obs_seg=seg,seg_df=net,feat_cols=cv.feature_columns(obs,cfg),groups=obs.reach_id.astype(str).values,protocol='loo_reach',cfg=cfg,k_emp=obs.k_CO2_m_d.values.astype(float))
    reference=old.loc[(old.scheme==scheme)&(old.model==model)&(old.cv_protocol=='loo_reach')]
    matched=new.merge(reference,on=keys,validate='one_to_one',suffixes=('_new','_saved'))
    result={'scheme':scheme,'model':model,'n':len(matched),'max_C_absdiff':float((matched.C_model_mol_m3_new-matched.C_model_mol_m3_saved).abs().max()),'rmse':float(np.sqrt(np.mean((new.C_model_mol_m3-new.C_obs_mol_m3)**2))),'zero_C_keys':new.loc[new.C_model_mol_m3==0,keys].astype(str).to_dict('records')}
    results.append(result)
    (HERE/'evidence/retrain_main.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(result,flush=True)
