"""四动作 LR/Ridge；三动作屏蔽 A，复用同一 R/T/C 头。"""
import json,os,time,warnings,itertools
import joblib
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression,Ridge
from threadpoolctl import threadpool_limits
from query_features import serialize_question,semantic_encode
from common_p2_10 import ROOT,ACTIONS,LAMBDAS,save,freeze,readrows,append,sha,utc,query_only

class ConstantProbability:
    def __init__(self,value):self.value=float(value);self.n_iter_=np.array([0])
    def predict_proba(self,x):return np.tile([1-self.value,self.value],(x.shape[0],1))

def query(row):return serialize_question(row['question_stem'],tuple(row['choice_labels']),tuple(row['choice_text']))

def predict(bundle,x,n_actions):
    p=np.column_stack([m.predict_proba(x)[:,1] for m in bundle['correctness'][:n_actions]])
    c=np.exp(np.column_stack([m.predict(x) for m in bundle['log_latency'][:n_actions]]))
    choices=(p[:,None,:]-np.asarray(LAMBDAS)[None,:,None]*c[:,None,:]/bundle['c_ref_ms']).argmax(2)
    return p,c,choices

def best_mixture(acc,cost,budget):
    """Exact one-cost-constraint simplex vertices: fixed points and pair edges."""
    acc=np.asarray(acc,dtype=float);cost=np.asarray(cost,dtype=float);cand=[]
    for i in range(4):
        if cost[i]<=budget:
            p=np.eye(4)[i];cand.append((float(p@acc),float(p@cost),p))
    for i,j in itertools.combinations(range(4),2):
        if cost[i]==cost[j]:continue
        w=(budget-cost[j])/(cost[i]-cost[j])
        if 0<=w<=1:
            p=np.zeros(4);p[i]=w;p[j]=1-w;cand.append((float(p@acc),float(p@cost),p))
    if not cand:return {'status':'infeasible','probabilities':None,'budget_ms':float(budget)}
    # R,T,C,A lexicographic probability preference is the final exact tie break.
    best=max(cand,key=lambda x:(x[0],-x[1],*x[2].tolist()))
    return {'status':'feasible','probabilities':best[2].tolist(),'expected_accuracy':best[0],'expected_ms':best[1],'budget_ms':float(budget)}

def get_train(out,cfg,dataset):
    rr=readrows(cfg['data'][dataset]['train']['path']);ids=[r['id'] for r in rr]
    old={(r['id'],r['action']):r for r in readrows(out/'train_historical_rtc.jsonl')}
    new=[r for r in readrows(out/'train_cases.jsonl') if r['runtime_error'] is None]
    nm={(r['id'],r['action']):r for r in new};assert len(new)==len(nm)
    y=np.array([[ (nm if a=='acw' else old)[r['id'],a]['scoring']['correct'] for a in ACTIONS] for r in rr],dtype=np.int8)
    pi=cfg['cost_panel'][dataset]['train']['ids'];indices=[ids.index(i) for i in pi]
    costs=np.array([[nm[i,a]['latency_ms'] for a in ACTIONS] for i in pi]);py=np.array([[nm[i,a]['scoring']['correct'] for a in ACTIONS] for i in pi],dtype=np.int8)
    assert np.isfinite(costs).all() and (costs>0).all()
    for i in pi:assert len({nm[i,a]['block_id'] for a in ACTIONS})==len({nm[i,a]['job_id'] for a in ACTIONS})==1,'train panel crosses execution block/job'
    return rr,y,pi,indices,costs,py

def fit_freeze(out,cfg,dataset,pair):
    threadpool_limits(limits=1)
    receipt=out/'router_fit_receipt.json'
    if receipt.exists():
        rec=json.loads(receipt.read_text())
        for name,h in rec['hashes'].items():assert sha(out/name)==h
        return {f:joblib.load(out/'models'/f'{f}.joblib') for f in ['word','semantic']}
    rr,y,pi,ix,costs,py=get_train(out,cfg,dataset)
    devsplit=next(s for s in cfg['data'][dataset] if s!='train');dev=readrows(cfg['data'][dataset][devsplit]['path'])
    md=out/'models';fd=out/'features';md.mkdir(exist_ok=True);fd.mkdir(exist_ok=True)
    vectorizer=TfidfVectorizer(ngram_range=(1,2),max_features=20000,min_df=2)
    xt=vectorizer.fit_transform([query(r) for r in rr]);xd=vectorizer.transform([query(r) for r in dev])
    sparse.save_npz(fd/'word_train.npz',xt);sparse.save_npz(fd/f'word_{devsplit}.npz',xd)
    st=np.load(ROOT/'data'/f'{dataset}_train_semantic.npy');sd=np.load(ROOT/'data'/f'{dataset}_{devsplit}_semantic.npy')
    save(fd/'row_ids.json',{'train':[r['id'] for r in rr],devsplit:[r['id'] for r in dev]})
    np.savez(out/'train_targets.npz',ids=[r['id'] for r in rr],correctness=y,cost_panel_ids=pi,cost_panel_indices=ix,cost_panel_ms=costs,cost_panel_correctness=py)
    fitted={};info={};hashes={}
    for family,x,d in [('word',xt,xd),('semantic',st,sd)]:
        path=md/f'{family}.joblib'
        if path.exists():
            b=joblib.load(path);assert b['training_ids']==[r['id'] for r in rr]
        else:
            began=time.perf_counter();b={'family':family,'correctness':[],'log_latency':[],'vectorizer':vectorizer if family=='word' else None,'training_ids':[r['id'] for r in rr],'cost_training_ids':pi,'c_ref_ms':float(costs[:,0].mean()),'actions':ACTIONS,'lambdas':LAMBDAS}
            constants={}
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter('always')
                for a in range(4):
                    classes=np.unique(y[:,a])
                    if len(classes)==1:m=ConstantProbability(classes[0]);constants[ACTIONS[a]]=int(classes[0])
                    else:m=LogisticRegression(penalty='l2',C=1,class_weight=None,max_iter=1000,random_state=0).fit(x,y[:,a])
                    b['correctness'].append(m)
                    b['log_latency'].append(Ridge(alpha=1).fit(x[ix],np.log(costs[:,a])))
            b['fit_info']={'seconds':time.perf_counter()-began,'features':x.shape[1],'n_iter':[m.n_iter_.tolist() for m in b['correctness']],'warnings':[str(w.message) for w in captured],'constant_probabilities':constants,'correctness_n':len(rr),'cost_n':256,'lr_solver':LogisticRegression().solver,'ridge_solver':'auto'}
            joblib.dump(b,path)
        info[family]=b['fit_info'];fitted[family]=b
        p,c,ch4=predict(b,d,4);_,_,ch3=predict(b,d,3)
        assert np.isfinite(p).all() and np.isfinite(c).all() and (c>0).all()
        dp=out/f'dev_predictions_{family}.npz'
        if dp.exists():
            old=np.load(dp);assert np.array_equal(old['choices4'],ch4) and np.array_equal(old['choices3'],ch3)
        else:np.savez(dp,ids=[r['id'] for r in dev],probabilities=p,predicted_ms=c,choices4=ch4,choices3=ch3,lambdas=LAMBDAS)
        tp,tc,t4=predict(b,x,4);_,_,t3=predict(b,x,3)
        if not (out/f'train_predictions_{family}.npz').exists():np.savez(out/f'train_predictions_{family}.npz',ids=[r['id'] for r in rr],probabilities=tp,predicted_ms=tc,choices4=t4,choices3=t3)
        hashes[str(path.relative_to(out))]=sha(path);hashes[dp.name]=sha(dp)
    save(out/'fit_info.json',info)
    freeze(receipt,{'utc':utc(),'job_id':os.environ['PBS_JOBID'],'pair':pair,'dataset':dataset,'hashes':hashes,'config_sha256':sha(ROOT/'frozen_config.json'),'c_ref_ms':float(costs[:,0].mean()),'fit_only_train':True})
    return fitted

def measure_overhead(out,row,split,runner,bundles,job,block_id,sync):
    path=out/'router_overhead.jsonl'
    # Caller supplies per-residency cache of completed measurement keys.
    done=bundles['_overhead_done']
    for family,n_actions in [('word',3),('word',4),('semantic',3),('semantic',4)]:
        key=(row['id'],split,family,n_actions)
        if key in done:continue
        b=bundles[family];sync();began=time.perf_counter_ns()
        text=query(row)
        if family=='word':x=b['vectorizer'].transform([text])
        else:x,_=semantic_encode(runner.semantic,runner.semantic_tok,[text],batch_size=1)
        p,c,choice=predict(b,x,n_actions)
        sync();elapsed=(time.perf_counter_ns()-began)/1e6
        assert np.isfinite(p).all() and np.isfinite(c).all() and (c>0).all()
        entry={'id':row['id'],'split':split,'family':family,'n_actions':n_actions,'job_id':job,'block_id':block_id,'utc':utc(),'overhead_ms':elapsed,'probabilities':p[0].tolist(),'predicted_ms':c[0].tolist(),'choices':choice[0].tolist(),'includes_all_seven_lambdas':True,'feature_cache_used':False}
        append(path,entry);done.add(key)

def freeze_train_mixture(out,cfg,dataset,job):
    path=out/'train_mixture_receipt.json'
    if path.exists():return json.loads(path.read_text())
    rr,y,pi,ix,costs,py=get_train(out,cfg,dataset)
    oh={(r['id'],r['family'],r['n_actions']):r for r in readrows(out/'router_overhead.jsonl') if r['split']=='train'}
    select=np.array([oh[i,'word',4]['choices'][1] for i in pi])
    b=float(np.mean([oh[i,'word',4]['overhead_ms'] for i in pi])+costs[np.arange(256),select].mean())
    mix=best_mixture(py.mean(0),costs.mean(0),b)
    rec={'utc':utc(),'job_id':job,'cost_panel_ids':pi,'primary_family':'word','primary_lambda':.01,'action_accuracy_means':py.mean(0).tolist(),'action_cost_means_ms':costs.mean(0).tolist(),'B_train':b,'mixture':mix,'router_fit_receipt_sha256':sha(out/'router_fit_receipt.json'),'train_overhead_source':str(out/'router_overhead.jsonl'),'overhead_measurement_job_ids':sorted({oh[i,'word',4]['job_id'] for i in pi}),'correctness_source':'new same-job train panel for all four actions'}
    freeze(path,rec);return rec
