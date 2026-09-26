from numerics import *
import joblib
assert (P/'MODELS_FREEZE.json').exists()
ids=read(P/'inputs/fit_ids.json');X,meta=load_features(ids);assert len(X)==2100
thresholds={};scores=[]
for c in CFG['configs']:
 stop();name=c['name'];m=joblib.load(P/f'models/{name}.joblib');u=1-predict(m,X);order=np.sort(u)
 th=[float(order[int(np.ceil(q*2100))-1]) if q<1 else 'Infinity' for q in CFG['q_grid']];thresholds[name]=th
 writejl(P/f'records/{name}_fit_scores.jsonl',({'id':i,'u':float(u[j])} for j,i in enumerate(ids)))
 scores.append({'name':name,'thresholds':th,'reference_n':2100,'labels_opened_by_process':False})
save(P/'thresholds/all.json',thresholds);save(P/'summary/fit_pool_feature_cost.json',{'n':len(meta),'feature_wall_seconds_reused':sum(r['feature_ms'] for r in meta)/1000})
freeze('THRESHOLDS_FREEZE.json',[P/'thresholds/all.json',*[P/f'records/{c["name"]}_fit_scores.jsonl' for c in CFG['configs']]],new_models=15,fit_reference_pool=2100,cal_d_read=False,unlabeled_reference_pool=True)
