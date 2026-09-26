from numerics import *
import joblib
assert (P/'THRESHOLDS_FREEZE.json').exists();thresholds=read(P/'thresholds/all.json')
ids=read(P/'inputs/cal_ids.json');X,meta=load_features(ids)
# Use the exact inherited binomial/CP functions. Only id,d enters calibration.
rows=jl(OLD/'inputs/candidate_cal.jsonl');assert [r['id'] for r in rows]==ids and all(set(r)=={'id','d'} for r in rows)
d=np.array([r['d'] for r in rows],bool)
oldtests=list(csv.DictReader((OLD/'summary/calibration_100.csv').open()));shared=[]
for r in oldtests:
 if r['family'] in ['D','R']:
  shared.append({**r,'family':'R2100' if r['family']=='R' else 'D','source_identity':'reused_parent_test','source_path':str(OLD/'summary/calibration_100.csv')})
assert len(shared)==40;csvout(P/'comparisons/shared_reference_40.csv',shared)
newtests=[];deployment={}
for c in CFG['configs']:
 stop();name=c['name'];m=joblib.load(P/f'models/{name}.joblib');u=1-predict(m,X)
 writejl(P/f'records/{name}_cal_scores.jsonl',({'id':i,'u':float(u[j])} for j,i in enumerate(ids)))
 accepted=[];tests=[]
 for q,t in zip(CFG['q_grid'],thresholds[name]):
  mask=u<=threshold_value(t);r={**c,'family':name,'q':q,'threshold':t,'N':len(d),**test(int(mask.sum()),int(d[mask].sum())),'coverage':float(mask.mean()),'marginal_change':float((d&mask).mean()),'M':100,'source_identity':'new_test'};tests.append(r)
  if r['accepted']:accepted.append(r)
 selected=accepted[-1] if accepted else None
 deployment[name]={'B':c['B'],'repeat':c['repeat'],'q':selected['q'] if selected else 0.,'threshold':selected['threshold'] if selected else None,'mode':('fixed_R' if selected['q']==1 else 'selective') if selected else 'fixed_T','accepted_q':[r['q'] for r in accepted],'calibration':selected,'minimum_grid_p':min(r['p_value'] for r in tests),'maximum_zero_change_n':max([r['n_R'] for r in tests if r['changed']==0] or [0]),'maximum_n_empirical_risk_le_alpha':max([r['n_R'] for r in tests if r['conditional_risk'] is not None and r['conditional_risk']<=.05] or [0])}
 newtests.extend(tests)
csvout(P/'summary/calibration_new_300.csv',newtests);save(P/'models/deployment.json',deployment)
for r in range(5):
 view=[{**x,'comparison_repeat':r} for x in shared]+[{**x,'comparison_repeat':r} for x in newtests if x['repeat']==r];assert len(view)==100;csvout(P/f'comparisons/r{r}_100.csv',view)
refs=read(OLD/'models/deployment.json');save(P/'models/reference_deployment.json',{'D':refs['D'],'R2100':refs['R'],'source':str(OLD/'models/deployment.json'),'sha256':sha(OLD/'models/deployment.json')})
save(P/'summary/cal_pool_feature_cost.json',{'n':len(meta),'feature_wall_seconds_reused':sum(r['feature_ms'] for r in meta)/1000})
checks=[{'case':s,**test(n,k)} for s,n,k in [('empty',0,0),('all_changed',135,135),('zero134',134,0),('zero135',135,0)]];assert not checks[2]['accepted'] and checks[3]['accepted'];save(P/'evidence/boundary_checks.json',checks)
freeze('DEPLOYMENT_FREEZE.json',[P/'models/deployment.json',P/'models/reference_deployment.json',P/'summary/calibration_new_300.csv',*list((P/'comparisons').glob('*.csv'))],new_tests=300,shared_tests=40,distinct_tests=340,comparison_views=5,per_repeat_FWER_nominal=.10,global_repeats_FWER_point10_claim=False,dev_answers_or_gold_associated=False)
print('CALIBRATION_COMPLETE',json.dumps({n:(p['q'],p['mode']) for n,p in deployment.items()}),flush=True)
