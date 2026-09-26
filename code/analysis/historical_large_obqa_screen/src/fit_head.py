from numerics import *
import sys,warnings,resource,joblib
from sklearn.linear_model import LogisticRegression
name=sys.argv[1];assert name in CFG['heads'];dest=P/f'models/{name}.joblib';assert not dest.exists()
ids=read(P/'splits/fit_ids.json');X,_=load_features(ids)
# Disagreement worker opens no gold/correctness file. Its complete target interface is id,d.
if name=='disagreement':
 rows=jl(P/'inputs/candidate_fit.jsonl');assert all(set(r)=={'id','d'} for r in rows);target='d'
else:rows=jl(P/'inputs/baseline_fit.jsonl');target={'correctness_R':'y_R','correctness_T':'y_T','harm':'harm'}[name]
assert [r['id'] for r in rows]==ids
y=np.array([r[target] for r in rows]);assert len(np.unique(y))==2,'SINGLE_CLASS: stop; no unreported fallback'
stop();append(P/'records/fit_attempts.jsonl',{'head':name,'utc':utc(),'n':len(ids),'event':'START'})
t=time.perf_counter();c=time.process_time()
with warnings.catch_warnings(record=True) as warns:
 warnings.simplefilter('always');model=LogisticRegression(**CFG['LR']).fit(X,y)
wall=time.perf_counter()-t;cpu=time.process_time()-c
joblib.dump(model,dest)
rec={'head':name,'n':len(ids),'target':target,'positive':int(y.sum()),'negative':int(len(y)-y.sum()),'n_iter':model.n_iter_.tolist(),'warnings':[str(w.message) for w in warns],'converged':bool(model.n_iter_.max()<1000),'fit_wall_seconds':wall,'fit_CPU_seconds':cpu,'path':str(dest),'sha256':sha(dest),'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'utc':utc()}
save(P/f'models/{name}_receipt.json',rec);print(json.dumps(rec),flush=True)
assert rec['converged'] and not warns,'FIT_WARNING: preserve model, stop before deployment'
