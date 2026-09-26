"""Prepared resumable fitting entry. Not executed on the current login node.

Baseline dev predictions and train-only OOF predictions remain separate.
No model generation, semantic encoding, scheduler, hyperparameter search, or scoring parser.
"""
import os
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='1'
import json,csv,hashlib,time,warnings,copy,resource,datetime
from pathlib import Path
import numpy as np
import joblib
from scipy import sparse
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer

O=Path(__file__).resolve().parent
P=Path('$DATA_DIR')
P10=P/'P2_10_20260911T122423Z';V2=P/'P2_SCORING_V2_20260912T191445Z'
A=['R','T','C','A'];lam=np.array([0,.01,.03,.1,.3,1,3])
cfg=json.loads((O/'frozen_config.json').read_text());freeze=json.loads((O/'PROTOCOL_FREEZE.json').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(path,x):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
def append(x):
    with (O/'fit_receipts.jsonl').open('a') as f:f.write(json.dumps(x,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def jl(p):
    with Path(p).open() as f:
        for line in f:
            if line.strip():yield json.loads(line)
def cpu():r=resource.getrusage(resource.RUSAGE_SELF);return r.ru_utime+r.ru_stime
def predict(m,x):
    return np.full(x.shape[0],m['value'],float) if isinstance(m,dict) else m.predict_proba(x)[:,1]
def fit(path,x,y,key):
    path=Path(path);receipt=path.with_suffix('.receipt.json')
    if path.exists() and receipt.exists():
        rec=json.loads(receipt.read_text());assert rec['protocol_sha256']==freeze['config_sha256'] and rec['model_sha256']==sha(path)
        return joblib.load(path)
    assert not path.exists(),'Unreceipted model: inspect and recover; do not silently refit'
    history=list(jl(O/'fit_receipts.jsonl')) if (O/'fit_receipts.jsonl').exists() else []
    attempts=sum(r['event']=='START_LR' for r in history)
    if len(np.unique(y))>1 and attempts>=320:raise RuntimeError('FIT_BUDGET_EXHAUSTED; preserve completed heads')
    path.parent.mkdir(parents=True,exist_ok=True);t=cpu()
    if len(np.unique(y))==1:
        model={'value':float(y[0]),'type':'constant_probability'};warn=[];iterations=0;kind='CONSTANT'
    else:
        append({'event':'START_LR','key':key,'path':str(path),'attempt_number':attempts+1,'cpu_at_start':t})
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always');model=LogisticRegression(**cfg['LR']).fit(x,y)
        warn=[str(w.message) for w in captured];iterations=int(model.n_iter_.max());kind='LR'
    temp=path.with_suffix('.tmp');joblib.dump(model,temp);temp.replace(path)
    rec={'event':'HEAD_COMPLETE','key':key,'kind':kind,'n':len(y),'positive':int(y.sum()),'iterations':iterations,
         'warnings':warn,'CPU_seconds':cpu()-t,'protocol_sha256':freeze['config_sha256'],'model_sha256':sha(path)}
    save(receipt,rec);append(rec);return model
def ymat(labels,pair,ds,ids,prefix):return np.array([[labels[pair,ds,i][prefix+'_'+a] for a in A] for i in ids])
def readlabels(name):return {(r['pair'],r['dataset'],r['id']):r for r in jl(V2/'labels'/name)}
def query(r):return '\n'.join(['Question: '+r['question_stem'],'Choices:']+[a+': '+b for a,b in zip(r['choice_labels'],r['choice_text'])])

def main():
    assert os.environ.get('P2_BOUNDED_SUPERVISED')==O.name,'Use run_bounded.py after explicit node eligibility is recorded'
    assert sha(O/'frozen_config.json')==freeze['config_sha256'] and sha(O/'folds/group_folds.csv')==freeze['folds_sha256']
    train=readlabels('full_train_P2_SCORING_V2.jsonl');oldcfg=json.loads((P10/'frozen_config.json').read_text())
    # Full-train update. Existing R/T/A heads are used only here, never in OOF.
    for asset in cfg['baseline_assets']:
        pair,ds,family=asset['pair'],asset['dataset'],asset['family'];out=O/'baseline'/pair/ds;out.mkdir(parents=True,exist_ok=True)
        complete=out/(family+'_COMPLETE.json')
        if complete.exists():continue
        src=Path(asset['source_bundle']['path']);assert sha(src)==asset['source_bundle']['sha256'];b=joblib.load(src)
        d=P10/'results'/pair/ds;ids=json.loads((d/'features/row_ids.json').read_text());dv='dev' if ds=='obqa' else 'validation'
        assert b['training_ids']==ids['train']
        x=sparse.load_npz(d/'features/word_train.npz') if family=='word' else np.load(P10/'data'/(ds+'_train_semantic.npy'),mmap_mode='r')
        y=ymat(train,pair,ds,ids['train'],'y')
        model=fit(out/(family+'_C_V2.joblib'),x,y[:,2],f'baseline/{pair}/{ds}/{family}/C')
        preserved=joblib.hash(([b['correctness'][i] for i in [0,1,3]],b['log_latency'],b['c_ref_ms'],b['vectorizer']))
        new=copy.deepcopy(b);new['correctness'][2]=model
        assert joblib.hash(([new['correctness'][i] for i in [0,1,3]],new['log_latency'],new['c_ref_ms'],new['vectorizer']))==preserved
        dest=out/(family+'_V2.joblib');joblib.dump(new,dest)
        xd=sparse.load_npz(d/'features'/('word_'+dv+'.npz')) if family=='word' else np.load(P10/'data'/(ds+'_'+dv+'_semantic.npy'),mmap_mode='r')
        probabilities=np.column_stack([predict(m,xd) for m in new['correctness']])
        costs=np.exp(np.column_stack([m.predict(xd) for m in new['log_latency']]))
        choice={str(na):(probabilities[:,None,:na]-lam[None,:,None]*costs[:,None,:na]/new['c_ref_ms']).argmax(2) for na in [3,4]}
        np.savez(out/(family+'_dev_predictions.npz'),ids=ids[dv],probabilities=probabilities,predicted_ms=costs,choices3=choice['3'],choices4=choice['4'],lambdas=lam)
        save(complete,{'status':'BASELINE_PREDICTIONS_COMPLETE','protocol_sha256':freeze['config_sha256'],'source_bundle_sha256':sha(src),
            'new_bundle_sha256':sha(dest),'preserved_component_hash':preserved,'RTA_and_cost_components_unchanged':True,
            'development':'fixed protocol baseline only; no FFR dev access'})
        print('BASELINE_COMPLETE',pair,ds,family,flush=True)
    # Train-only OOF; fold vocabulary shared across pairs and methods.
    foldrows=list(csv.DictReader((O/'folds/group_folds.csv').open()))
    for ds in ['obqa','arc']:
        rows=list(jl(cfg['dataset_inputs'][ds]['query_train']));ids=[r['id'] for r in rows];texts=[query(r) for r in rows]
        foldmap={r['id']:int(r['fold']) for r in foldrows if r['dataset']==ds};fold=np.array([foldmap[i] for i in ids])
        semantic=np.load(cfg['dataset_inputs'][ds]['semantic_train'],mmap_mode='r');assert semantic.shape[0]==len(ids)
        for family in ['word','semantic']:
            for k in range(5):
                dest=O/'oof'/ds/family/('fold'+str(k));dest.mkdir(parents=True,exist_ok=True)
                tr=np.flatnonzero(fold!=k);te=np.flatnonzero(fold==k)
                if all((dest/pair/'COMPLETE.json').exists() for pair in ['large','small']):continue
                if family=='word':
                    vf=dest/'tfidf.joblib'
                    if vf.exists():vec=joblib.load(vf)
                    else:
                        vec=TfidfVectorizer(**{**cfg['tfidf'],'ngram_range':tuple(cfg['tfidf']['ngram_range'])});vec.fit([texts[i] for i in tr]);joblib.dump(vec,vf)
                    xtr=vec.transform([texts[i] for i in tr]);xte=vec.transform([texts[i] for i in te])
                else:xtr=semantic[tr];xte=semantic[te]
                for pair in ['large','small']:
                    d=dest/pair;d.mkdir(exist_ok=True)
                    if (d/'COMPLETE.json').exists():continue
                    y=ymat(train,pair,ds,ids,'y');f=ymat(train,pair,ds,ids,'f')[:,1:]
                    valid=ymat(train,pair,ds,ids,'valid');train_y=y[tr];train_f=f[tr]
                    m=[];pr=[]
                    for j,a in enumerate(A[1:]):
                        head=fit(d/('FFR_'+a+'.joblib'),xtr,train_f[:,j],f'OOF/{ds}/{family}/{k}/{pair}/f_{a}')
                        m.append(predict(head,xte))
                    for j,a in enumerate(A):
                        head=fit(d/('IndepLR_'+a+'.joblib'),xtr,train_y[:,j],f'OOF/{ds}/{family}/{k}/{pair}/y_{a}')
                        pr.append(predict(head,xte))
                    m=np.column_stack(m);pr=np.column_stack(pr)
                    gain=(train_y[:,1:]>train_y[:,[0]]).sum(0);harm=(train_y[:,1:]<train_y[:,[0]]).sum(0)
                    delta=(gain-harm)/(train_f.sum(0)+2);base_rate=train_f.mean(0)
                    costpath=P10/'results'/pair/ds/'train_cost_panel_matrix.npz'
                    with np.load(costpath,allow_pickle=False) as pc:
                        panel_ids=pc['ids'].tolist();keep=np.array([foldmap[i]!=k for i in panel_ids]);cost=pc['latency_ms'][keep].mean(0)
                    assert keep.any();c_ref=float(cost[0]);assert np.isfinite(cost).all() and c_ref>0
                    g={'FFR_E0':np.column_stack([np.zeros(len(te)),m*delta]),
                       'IndepLR':pr-pr[:,[0]],
                       'FFR_constant_flip_rate':np.broadcast_to(np.r_[0,base_rate*delta],(len(te),4)),
                       'FFR_true_flip_DIAGNOSTIC':np.column_stack([np.zeros(len(te)),f[te]*delta])}
                    arrays={'ids':np.array(ids)[te],'fold':np.full(len(te),k),'y':y[te],'f':f[te],'valid':valid[te],
                        'm':m,'p':pr,'constant_flip_rate':base_rate,'delta':delta,'fit_gain':gain,'fit_harm':harm,
                        'fit_flip_n':train_f.sum(0),'cost_proxy_ms':cost,'c_ref_ms':c_ref,'lambdas':lam,'fit_panel_ids':np.array(panel_ids)[keep]}
                    for name,scores in g.items():
                        for na in [3,4]:arrays[name+'_choices'+str(na)]=(scores[:,None,:na]-lam[None,:,None]*cost[None,None,:na]/c_ref).argmax(2)
                    for na in [3,4]:arrays['query_independent_choices'+str(na)]=(train_y.mean(0)[None,:na]-lam[:,None]*cost[None,:na]/c_ref).argmax(1)
                    np.savez(d/'predictions.npz',**arrays)
                    save(d/'COMPLETE.json',{'status':'OOF_FOLD_COMPLETE','pair':pair,'dataset':ds,'family':family,'fold':k,'n_fit':len(tr),'n_heldout':len(te),
                        'fit_panel_n':int(keep.sum()),'protocol_sha256':freeze['config_sha256'],'prediction_sha256':sha(d/'predictions.npz'),
                        'dev_used':False,'full_train_pretrained_heads_used':False})
                    print('OOF_FOLD_COMPLETE',ds,family,k,pair,flush=True)
    save(O/'FITTING_COMPLETE.json',{'status':'FITTING_AND_PREDICTIONS_COMPLETE_ANALYSIS_PENDING','baseline_C_heads':8,'OOF_heads':280,
        'note':'Model/prediction generation only. Scientific metric tables and report still required; do not declare task complete.'})
if __name__=='__main__':main()
