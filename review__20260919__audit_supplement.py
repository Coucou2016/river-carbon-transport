"""Additional read-only provenance, topology, figure and objective probes."""
from pathlib import Path
import sys, os, json, hashlib, importlib, re, base64, math
ROOT=Path(__file__).resolve().parents[2]
PACKET=ROOT/'tmp/review_20260919/packet'
OUT=Path(__file__).resolve().parent/'evidence'
sys.dont_write_bytecode=True
os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path.insert(0,str(PACKET))
import numpy as np
import pandas as pd
from src.utils import load_config
cfg=load_config(PACKET/'configs/east_river.yaml')
cfg['paths']['data_raw']=str(ROOT/'data_raw')
cfg['paths']['data_proc']=str(PACKET/'data_proc')
report={}
from src.east_river_real_data import load_hydroshare_samples, hydroshare_excel_path
rawpath=hydroshare_excel_path(cfg)
raw=load_hydroshare_samples(cfg)
flat=pd.read_csv(PACKET/'data_proc/reach_daily_observations.csv',parse_dates=['date'])
raw['sample_id']=raw['Sample ID'] if 'Sample ID' in raw else raw['SampleID']
keys=['date','reach_id','sample_id']
matched=flat.merge(raw,on=keys,suffixes=('_proc','_raw'),validate='one_to_one')
report['raw_data_trace']={'path':str(rawpath),'sha256':hashlib.sha256(rawpath.read_bytes()).hexdigest(),
 'n_loaded':len(raw),'n_proc':len(flat),'n_matched':len(matched),'columns':list(raw)}
for col in ['T_C','DOC_mgL','DIC_mmolL','DO_mgL']:
    if col+'_proc' in matched and col+'_raw' in matched:
        a,b=matched[col+'_proc'],matched[col+'_raw']
        report['raw_data_trace'][col]={'n_both':int((a.notna()&b.notna()).sum()),'max_abs_diff':float((a-b).abs().max())}
eq=importlib.import_module('src.16_equifinality_surface')
m=eq.load_per_sample(cfg)
surface=eq.build_surface(m)
qa=m.q_A_m_d.to_numpy(); cin=m.C_in_obs_mol_m3.to_numpy(); ce=m.C_eq_mol_m3.to_numpy()
co=m.C_aq_obs_mol_m3.to_numpy(); ke=m.k_CO2_m_d.to_numpy()
exact=[]
for alpha, grid_j in zip(surface['alphas'],surface['prof']):
    den=qa+alpha*ke; a=(qa*cin+alpha*ke*ce)/den; b=1/den
    s=float(np.sum(b*(co-a))/np.sum(b*b))
    j=float(np.sum((co-a-b*s)**2))
    exact.append({'alpha':float(alpha),'s_exact':s,'J_exact':j,'J_grid':float(grid_j)})
best=min(exact,key=lambda x:x['J_exact'])
report['objective_probe']={'q_A_median_current':float(np.median(qa)),
 'grid_min_rmse_current':surface['rmse_min'],'grid_basin_current':[surface['rmse_basin_min'],surface['rmse_basin_max']],
 'exact_best':best,'max_J_grid_minus_exact':max(x['J_grid']-x['J_exact'] for x in exact),'profile':exact}

md=(PACKET/'paper.md').read_text(encoding='utf-8')
html=(PACKET/'paper.html').read_text(encoding='utf-8')
embeds=[hashlib.sha256(base64.b64decode(s)).hexdigest() for s in re.findall(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)',html)]
figs=[]
for rel in re.findall(r'!\[.*?\]\(([^)]+)\)',md):
    p=PACKET/rel
    figs.append({'path':rel,'exists':p.exists(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None,
                 'current_png_found_in_html':p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() in embeds})
report['figure_links']=figs;report['html_embedded_image_count']=len(embeds)

fil=importlib.import_module('src.13_filter_scale_sgs')
g=fil._load_study_lines(cfg)
g,attrs=fil._add_flow_direction(g)
report['flowdir_counts']=g.flowdir.value_counts(dropna=False).to_dict()
report['contractions']=[]
for nm,label in [(1,'native'),(2,'merge_2x'),(4,'merge_4x'),(0,'study_reach')]:
    cells,membership,up=fil.coarsen_lines(g,attrs,nm,label)
    expected=set()
    for i,at in attrs.items():
        for j in at['downstream']:
            if membership[i]!=membership[j]:expected.add((membership[i],membership[j]))
    actual={(u,c) for c,ups in up.items() for u in ups}
    discrepancy=cells.length_m-cells.geometry.length
    report['contractions'].append({'scale':label,'n_cells':len(cells),'n_expected_cross_cell_edges':len(expected),
        'n_edges_dropped':len(expected-actual),'examples_dropped':sorted(expected-actual)[:8],
        'n_geometries_shorter_than_reported_length':int(discrepancy.gt(1.).sum()),'max_missing_geometry_m':float(discrepancy.max())})
report['note']='No pipeline rerun. Objective rebuilt without saving figures. Raw input and production outputs untouched.'
def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if isinstance(x,float) and not math.isfinite(x):return None
    return x
(OUT/'supplement_results.json').write_text(json.dumps(clean(report),ensure_ascii=False,indent=2,default=str,allow_nan=False),encoding='utf-8')
report['objective_probe'].pop('profile')
print(json.dumps(clean(report),ensure_ascii=False,indent=2,default=str))
