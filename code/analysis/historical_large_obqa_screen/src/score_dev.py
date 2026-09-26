from numerics import *
import joblib
assert (P/'DEPLOYMENT_FREEZE.json').exists() and (P/'DEV_FEATURES_COMPLETE.json').exists()
models={h:joblib.load(P/f'models/{h}.joblib') for h in CFG['heads']};policies=read(P/'models/deployment.json');thresholds=read(P/'models/thresholds.json')
ids=read(P/'splits/dev_ids.json');coins=jl(P/'splits/random_dev.jsonl');assert [r['id'] for r in coins]==ids
idx=list(csv.DictReader((P/'features/DEV_FEATURE_INDEX.csv').open()));assert [r['id'] for r in idx]==ids
rows=[];allgrid=[]
for j,r in enumerate(idx):
 stop();assert sha(r['path'])==r['sha256']
 with np.load(r['path'],allow_pickle=False) as a:z=a['z'].reshape(1,-1)
 scores={};cost={};selected={};components={}
 for f in CFG['families']:
  p=policies[f];t=time.perf_counter_ns()
  if f=='D':u=float(models['disagreement'].predict_proba(z)[0,1])
  elif f=='R':u=1-float(models['correctness_R'].predict_proba(z)[0,1])
  elif f=='Diff':u=float(models['correctness_T'].predict_proba(z)[0,1]-models['correctness_R'].predict_proba(z)[0,1])
  elif f=='H':u=float(models['harm'].predict_proba(z)[0,1])
  else:u=coins[j]['u']
  routed=(u<=threshold_value(p['threshold'])) if p['mode']=='selective' else p['mode']=='fixed_R'
  elapsed=(time.perf_counter_ns()-t)/1e6
  if f=='Random':elapsed+=coins[j]['rng_generation_ms']
  scores[f]=u;selected[f]='R' if routed else 'T';cost[f]=elapsed
  components[f]=elapsed if p['mode']=='selective' else 0.
 rows.append({'id':ids[j],'feature_ms':float(r['feature_ms']),'scores':scores,'route':selected,'head_selector_ms_measured':cost,'head_selector_ms_charged':components,'feature_ms_charged':{f:float(r['feature_ms']) if f!='Random' and policies[f]['mode']=='selective' else 0. for f in CFG['families']}})
 allgrid.append({'id':ids[j],'routes':{f:[int(scores[f]<=threshold_value(t)) for t in thresholds[f]] for f in CFG['families']}})
writejl(P/'records/dev_scored_routes.jsonl',rows);writejl(P/'records/dev_grid_routes.jsonl',allgrid)
freeze('DEV_ROUTES_FREEZE.json',[P/'records/dev_scored_routes.jsonl',P/'records/dev_grid_routes.jsonl',P/'DEPLOYMENT_FREEZE.json',P/'DEV_FEATURES_COMPLETE.json'],N=742,dev_answers_or_gold_read_by_scoring_process=False,selection_changed=False)
print('DEV_ROUTES_FROZEN',sha(P/'records/dev_scored_routes.jsonl'),flush=True)
