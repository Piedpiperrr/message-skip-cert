from numerics import *
import joblib
fit=read(P/'splits/fit_ids.json');cal=read(P/'splits/cal_ids.json')
models={h:joblib.load(P/f'models/{h}.joblib') for h in CFG['heads']}
X,_=load_features(fit)
def scores(X):
 p={h:m.predict_proba(X)[:,1] for h,m in models.items()}
 return {'D':p['disagreement'],'R':1-p['correctness_R'],'Diff':p['correctness_T']-p['correctness_R'],'H':p['harm']}
s=scores(X);thresholds={}
for family,vals in s.items():
 order=np.sort(vals);thresholds[family]=[float(order[int(np.ceil(q*len(fit)))-1]) if q<1 else 'Infinity' for q in CFG['q_grid']]
thresholds['Random']=CFG['q_grid']
save(P/'models/thresholds.json',thresholds)
writejl(P/'records/fit_scores.jsonl',({'id':i,**{f:float(v[j]) for f,v in s.items()}} for j,i in enumerate(fit)))
csvout(P/'models/MODEL_INDEX.csv',[read(P/f'models/{h}_receipt.json') for h in CFG['heads']])
freeze('THRESHOLDS_FREEZE.json',[P/'models/thresholds.json',P/'records/fit_scores.jsonl',P/'RANDOM_FREEZE.json',*[P/f'models/{h}.joblib' for h in CFG['heads']]],M=100,cal_d_read_by_calibrator=False,rule=CFG['selection'])
# Only now may calibration outcomes be read; no cal gold enters this process.
X,_=load_features(cal);s=scores(X);s['Random']=np.array([r['u'] for r in jl(P/'splits/random_cal.jsonl')])
rows=jl(P/'inputs/candidate_cal.jsonl');assert all(set(r)=={'id','d'} for r in rows) and [r['id'] for r in rows]==cal
d=np.array([r['d'] for r in rows],dtype=bool)
checks=[{'case':name,**test(n,k)} for name,n,k in [('empty',0,0),('all_changed',135,135),('zero_134',134,0),('zero_135',135,0)]]
assert checks[0]['p_value']==checks[1]['p_value']==1 and checks[0]['CP_upper_0_999']==checks[1]['CP_upper_0_999']==1
assert not checks[2]['accepted'] and checks[3]['accepted'];save(P/'evidence/numerical_boundaries.json',checks)
tests=[];deployment={};route_rows=[]
for f,vals in s.items():
 accepted=[]
 for q,threshold in zip(CFG['q_grid'],thresholds[f]):
  mask=vals<=threshold_value(threshold);r={'family':f,'q':q,'threshold':threshold,'N':len(cal),**test(int(mask.sum()),int(d[mask].sum())),'coverage':float(mask.mean()),'marginal_change':float((d&mask).mean())};tests.append(r)
  if r['accepted']:accepted.append(r)
 selected=accepted[-1] if accepted else None
 deployment[f]={'q':selected['q'] if selected else 0.,'threshold':selected['threshold'] if selected else None,'mode':('fixed_R' if selected['q']==1 else 'selective') if selected else 'fixed_T','accepted_q':[r['q'] for r in accepted],'calibration':selected,'fallback_reason':None if selected else 'No strategy passed p<=0.001; not evidence of absent ranking signal'}
for j,i in enumerate(cal):route_rows.append({'id':i,**{f:float(v[j]) for f,v in s.items()}})
writejl(P/'records/cal_scores.jsonl',route_rows);csvout(P/'summary/calibration_100.csv',tests);save(P/'models/deployment.json',deployment)
freeze('DEPLOYMENT_FREEZE.json',[P/'THRESHOLDS_FREEZE.json',P/'summary/calibration_100.csv',P/'models/deployment.json',P/'records/cal_scores.jsonl'],heads=4,calibration_tests=100,families=5,dev_gold_or_answers_read=False,calibration_gold_used=False)
print('A_COMPLETE',json.dumps({f:{'q':r['q'],'mode':r['mode'],'accepted':r['accepted_q']} for f,r in deployment.items()}),flush=True)
