from numerics import *
import joblib,warnings
from sklearn.linear_model import LogisticRegression
receipts=[]
for c in CFG['configs']:
 stop();name=c['name'];dest=P/f'models/{name}.joblib';receipt=P/f'models/{name}_receipt.json'
 if receipt.exists():
  r=read(receipt);assert r['model_sha256']==sha(dest) and r['subset_sha256']==sha(P/c['subset_file']) and r['complete'];receipts.append(r);continue
 rows=jl(P/f'inputs/{name}_labels.jsonl');ids=read(P/c['subset_file']);assert [r['id'] for r in rows]==ids and all(set(r)=={'id','y_R'} for r in rows)
 X,_=load_features(ids);y=np.array([r['y_R'] for r in rows]);assert len(y)==c['B']
 append(P/'records/model_attempts.jsonl',{'name':name,'B':c['B'],'repeat':c['repeat'],'utc':utc(),'event':'START_MODEL','subset_sha256':sha(P/c['subset_file'])})
 t=time.perf_counter();cpu=time.process_time();classes=np.unique(y);warns=[]
 if len(classes)==1:model={'kind':'constant','probability_y_R_1':int(classes[0])};kind='constant_fallback';n_iter=[];did_fit=False
 else:
  attempts=jl(P/'records/fit_attempts.jsonl') if (P/'records/fit_attempts.jsonl').exists() else [];assert len(attempts)<15
  append(P/'records/fit_attempts.jsonl',{'name':name,'utc':utc(),'event':'START_LR','attempt':len(attempts)+1})
  with warnings.catch_warnings(record=True) as ws:
   warnings.simplefilter('always');model=LogisticRegression(**CFG['LR']).fit(X,y);warns=[str(w.message) for w in ws]
  kind='LogisticRegression';n_iter=model.n_iter_.tolist();did_fit=True
 wall=time.perf_counter()-t;cpu=time.process_time()-cpu
 joblib.dump(model,dest)
 r={**c,'kind':kind,'n':len(y),'fit_correct':int(y.sum()),'fit_incorrect':int(len(y)-y.sum()),'LR_fit_performed':did_fit,'n_iter':n_iter,'warnings':warns,'converged':not did_fit or max(n_iter)<1000,'fit_wall_seconds':wall,'fit_CPU_seconds':cpu,'subset_sha256':sha(P/c['subset_file']),'label_interface_sha256':sha(P/f'inputs/{name}_labels.jsonl'),'model_path':str(dest),'model_sha256':sha(dest),'LR_random_state':0,'subset_random_seed':c['repeat'],'no_old_model_initialization':True,'utc':utc()}
 r['complete']=r['converged'] and not warns;save(receipt,r);receipts.append(r);assert r['complete'],'fit warning/failure: preserve model and stop';print('MODEL_COMPLETE',name,kind,flush=True)
csvout(P/'models/MODEL_INDEX.csv',receipts)
freeze('MODELS_FREEZE.json',[P/'models/MODEL_INDEX.csv',*[P/f'models/{c["name"]}.joblib' for c in CFG['configs']]],model_outcomes=15,actual_LR_fits=sum(r['LR_fit_performed'] for r in receipts),constant_fallbacks=sum(r['kind']=='constant_fallback' for r in receipts),cal_labels_read=False)
