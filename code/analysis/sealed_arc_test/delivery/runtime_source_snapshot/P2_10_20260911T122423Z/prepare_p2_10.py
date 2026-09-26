"""有界 CPU 准备；最终 freeze 由单独入口独占创建。"""
import ast, hashlib, itertools, json, shutil
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pyarrow as pa
from transformers import AutoTokenizer

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
P={i:next(PROJECT.glob(f'P2_{i}_20*')) for i in [3,4,5,6,8,9]}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p): return [json.loads(x) for x in Path(p).read_text().splitlines()]
def save(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def jsonl(p,x): Path(p).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in x))
def main():
    assert not (ROOT/'frozen_config.json').exists()
    cfg9=json.loads((P[9]/'frozen_config.json').read_text())
    cfg3=json.loads((P[3]/'frozen_config.json').read_text())
    cfg4=json.loads((P[4]/'frozen_config.json').read_text())
    pairs=cfg9['pair_configs']
    # Resolve actual hooks from AST, never infer the index from prose k/j=20.
    tree=ast.parse((P[4]/'ac_runtime.py').read_text()); old_indices={}
    for fn in [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['helper_vector','receiver_run']]:
        indices=[]
        for n in ast.walk(fn):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='register_forward_hook':
                v=n.func.value
                if isinstance(v,ast.Subscript) and isinstance(v.value,ast.Attribute) and v.value.attr=='layers': indices.append(ast.literal_eval(v.slice))
        assert indices==[19],indices
        old_indices['helper' if fn.name=='helper_vector' else 'receiver']=indices[0]
    layers={}
    for role in ['helper','receiver']:
        s=json.loads((Path(pairs['small']['models'][role]['path'])/'config.json').read_text())
        l=json.loads((Path(pairs['large']['models'][role]['path'])/'config.json').read_text())
        k=old_indices[role];ls=s['num_hidden_layers'];ll=l['num_hidden_layers']
        j=(2*(k+1)*ll+ls)//(2*ls);kl=min(ll-1,max(0,j-1))
        layers[role]={'small':{'block_index':k,'position_1based':k+1,'num_hidden_layers':ls,'hidden_size':s['hidden_size']},'large':{'block_index':kl,'position_1based':kl+1,'num_hidden_layers':ll,'hidden_size':l['hidden_size']},'mapped_j':j,'formula':'floor(((k+1)*L_large/L_small)+0.5), then clamp(j-1)'}
    assert [layers[r][p]['num_hidden_layers'] for p in ['small','large'] for r in ['helper','receiver']]==[24,28,28,36]
    assert sha(cfg4['W_path'])==cfg4['W_sha256']=='6cbafe3cb009a395608937649b5a666ba4c8b38b92c8b3932626d34b0ce6fcb0'
    data={}; provenance={}; panel={}; req=[]
    actions=['receiver_only','text','c2c','acw'];orders=list(itertools.permutations(actions))
    for dataset,splits in [('obqa',[('train',3466),('dev',742)]),('arc',[('train',1119),('validation',299)])]:
        data[dataset]={};panel[dataset]={}
        for split,n in splits:
            src=P[5]/f'{split}_questions.jsonl' if dataset=='obqa' else P[8]/f'arc_challenge_{split}.jsonl'
            rr=rows(src);assert len(rr)==n and len({r['id'] for r in rr})==n
            if dataset=='obqa':
                arrow=Path('$DATA_DIR/gate2c_train_dev_question_staging_v1_20260727')/f'router_{split}_questions.arrow'
                with pa.memory_map(str(arrow),'r') as f: aa=pa.ipc.open_file(f).read_all().to_pylist()
                am={r['id']:r for r in aa};assert set(am)=={r['id'] for r in rr}
                p6={r['id']:r for r in rows(P[6]/f'{split}_questions.jsonl')}
                for r in rr:
                    assert all(am[r['id']][k]==r[k] for k in ['question_stem','choice_labels','choice_text'])
                    assert all(p6[r['id']][k]==r[k] for k in ['question_stem','choice_labels','choice_text','gold_answer'])
                provenance[f'{dataset}/{split}/arrow']={'path':str(arrow),'sha256':sha(arrow),'aligned_n':n,'join':'id + question_stem + ordered labels/text; gold from frozen P2-5 exact original-train match'}
            else: assert sha(src)==cfg9['data'][split]['sha256']
            dest=ROOT/'data'/f'{dataset}_{split}.jsonl';shutil.copy2(src,dest)
            data[dataset][split]={'path':str(dest),'source':str(src),'sha256':sha(dest),'n':n}
            hashed=sorted((hashlib.sha256(f'P2_10_COST_PANEL_V1|{dataset}|{split}|{r["id"]}'.encode()).hexdigest(),r['id']) for r in rr)
            ids=[i for h,i in hashed[:256 if split=='train' else 128]]
            pf=ROOT/'data'/f'{dataset}_{split}_cost_ids.json';save(pf,ids)
            panel[dataset][split]={'ids':ids,'path':str(pf),'sha256':sha(pf),'sampling_dataset_literal':dataset,'sampling_split_literal':split,'ranked_sha256':[h for h,i in hashed[:len(ids)]]}
            # Panels first, in frozen hash order; non-panels follow original frozen data order.
            seq=ids+[r['id'] for r in rr if r['id'] not in set(ids)]
            jsonl(ROOT/'data'/f'{dataset}_{split}_execution_order.jsonl',[{'id':i,'panel':i in set(ids),'order_cycle':k%24 if i in set(ids) else None,'actions':orders[k%24] if i in set(ids) else ['acw']} for k,i in enumerate(seq)])
            for pair in ['large','small']:
                out=ROOT/'results'/pair/dataset;out.mkdir(parents=True,exist_ok=True)
                hist=(P[5] if pair=='small' else P[6])/'results'/f'{split}_cases.jsonl' if dataset=='obqa' else P[9]/'results'/pair/f'{split}_cases.jsonl'
                hr=rows(hist);hs=[x for x in hr if x['runtime_error'] is None];hm={(x['id'],x['action']):x for x in hs}
                assert len(hs)==len(hm)==n*3
                assert set(hm)=={(r['id'],a) for r in rr for a in actions[:3]}
                for r in rr:
                    for a in actions[:3]:
                        h=hm[r['id'],a];assert h['split']==split and h['gold_answer']==r['gold_answer']
                        if dataset=='arc': assert h['pair']==pair and h['legal_labels']==r['choice_labels']
                provenance[f'{pair}/{dataset}/{split}']={'path':str(hist),'sha256':sha(hist),'successes':len(hs),'job_ids':sorted({h['job_id'] for h in hs}),'protocol_source':str(P[9] if dataset=='arc' else P[5] if pair=='small' else P[6]),'models':pairs[pair]['models'],'data_source':str(src),'join':'dataset,split,id,action; verified gold, ordered input, model/revision and frozen protocol'}
                # Success originals retain all fields and provenance; no new costs in these columns.
                jsonl(out/f'{split}_historical_rtc.jsonl',hs)
                for k,i in enumerate(seq):
                    for pos,a in enumerate(orders[k%24] if i in set(ids) else ['acw']):
                        req.append({'key':f'P2_10|{pair}|{dataset}|{split}|{i}|{a}','pair':pair,'dataset':dataset,'split':split,'id':i,'action':a,'panel':i in set(ids),'question_order':k,'action_position':pos,'order_cycle':k%24 if i in set(ids) else None})
        # Reuse same validated semantic source for both pairs; no outputs used for feature selection.
        fd=P[5]/'results/features' if dataset=='obqa' else P[9]/'results/large/features'
        fi=json.loads((fd/'row_ids.json').read_text())
        for split,n in splits:
            rr=rows(data[dataset][split]['path']);assert fi[split]==[r['id'] for r in rr]
            a=np.load(fd/f'semantic_{split}.npy');assert a.shape==(n,1024) and np.isfinite(a).all() and np.allclose(np.linalg.norm(a,axis=1),1,atol=1e-5)
            dst=ROOT/'data'/f'{dataset}_{split}_semantic.npy';shutil.copy2(fd/f'semantic_{split}.npy',dst)
            provenance[f'{dataset}/{split}/semantic']={'path':str(fd/f'semantic_{split}.npy'),'sha256':sha(dst),'row_ids':str(fd/'row_ids.json'),'row_ids_sha256':sha(fd/'row_ids.json'),'identity':pairs['small']['models']['semantic_encoder'],'query_implementation_sha256':sha(ROOT/'query_features.py')}
    c4={}
    toks={r:AutoTokenizer.from_pretrained(pairs['large']['models'][r]['path'],local_files_only=True) for r in ['helper','receiver']}
    for split,n in [('train',3072),('heldout',256)]:
        src=P[3]/f'c4_{split}_sentences.jsonl';rr=rows(src);assert len(rr)==n
        checks={}
        for role,tok in toks.items():
            ids=[tok(r['text'],add_special_tokens=True,truncation=False)['input_ids'] for r in rr]
            assert all(1<=len(x)<=256 for x in ids)
            checks[role]={'n':n,'max_tokens':max(map(len,ids)),'same_as_small_token_ids':all(x==r['token_ids'][role] for x,r in zip(ids,rr)),'token_ids_sha256':hashlib.sha256(json.dumps(ids).encode()).hexdigest()}
            save(ROOT/'data'/f'c4_{split}_{role}_token_ids.json',ids)
        shutil.copy2(src,ROOT/'data'/src.name)
        c4[split]={'path':str(ROOT/'data'/src.name),'source':str(src),'sha256':sha(src),'n':n,'large_tokenizer_checks':checks}
    assert len(req)==15860 and sum(r['action']=='acw' for r in req)==11252
    jsonl(ROOT/'data/request_manifest.jsonl',req)
    cfg={'experiment':'P2-10','pair_order':['large','small'],'dataset_order':['obqa','arc'],'actions':actions,'lambdas':[0,.01,.03,.1,.3,1,3],'pair_configs':pairs,'ac_layers':layers,'small_W':{'path':cfg4['W_path'],'sha256':cfg4['W_sha256']},'large_W':{'shape':[layers['receiver']['large']['hidden_size'],layers['helper']['large']['hidden_size']],'bias':False,'device':'cuda:1','steps':960,'selection':'final step 960 only','recipe':cfg3['W'],'c4_recipe':cfg3['c4'],'c4_data':c4,'backbones':'frozen eval BF16 SDPA','activation':'own tokenizer plain text add_special_tokens=True truncation=False; last valid position, chosen block output; no chat template; BF16 -> FP32'},'data':data,'cost_panel':panel,'orders':orders,'request_manifest':{'path':str(ROOT/'data/request_manifest.jsonl'),'sha256':sha(ROOT/'data/request_manifest.jsonl'),'n':15860},'history_and_features':provenance,'budget':{'node_seconds':21600,'submissions_max':3,'walltime_caps_seconds':[10800,7200,3600],'gpus':2,'nodes':1,'ncpus':64,'mem':'240gb','smoke_actions_max':72,'retry_actions_max':32,'retries_per_key':1},'router':{'tfidf':{'ngram_range':[1,2],'max_features':20000,'min_df':2},'logistic':{'penalty':'l2','C':1,'class_weight':None,'max_iter':1000,'random_state':0,'solver':'lbfgs'},'ridge':{'alpha':1,'solver':'auto','target':'log(ms), exp prediction'},'training':'full train correctness; same 256 new panel costs for every cost head','constant_probability':'single training class -> exact 0 or 1','c_ref':'new train panel R mean ms','ablation':'same heads and features, exclude A; do not compute A heads online','freeze_gate':'models + all dev predictions/choices + measured train mixture receipt before any new dev action','overhead':'independent raw query serialization, actual feature extraction and 3/4 heads; all seven lambdas timed; same job/residency for dev panel'},'mixtures':{'grid':[[a/10,b/10,c/10,(10-a-b-c)/10] for a in range(11) for b in range(11-a) for c in range(11-a-b)],'continuous':'four vertices + six pair edges; infeasible -> null','primary':'word lambda=0.01, train-only cost-constrained mixture; max accuracy, min cost, lexicographic R/T/C/A probability preference'},'bootstrap':{'seed':0,'replicates':20000,'unit':'question, same draws for all references within population','interval':'percentile 2.5,97.5','conditional':True},'boundaries':['ARC test sealed, not read','OBQA dev and ARC validation exposed development','full accuracy historical RTC + new AC','current accuracy-latency only 128 new same-job panel rows','no CV, search, cross-dataset routing or additional seeds','no P2-9 modification or submission','AC independent paper-based Qwen port, not official reproduction'],'ac_inference':{'W_device':'cuda:1','operation':'W(a.to(device=W.weight.device,dtype=torch.float32)); mapped FP32 -> receiver BF16 before single initial prompt prefill full-vector replacement','transfer':'helper cuda:0 -> W/receiver cuda:1; preserve torch.to conversion order; source/destination bytes and realized CUDA copy operation audited in smoke','helper_generation':False}}
    assert len(cfg['mixtures']['grid'])==286
    save(ROOT/'prepared_config.json',cfg)
    save(ROOT/'evidence/cpu_preparation.json',{'utc':datetime.now(timezone.utc).isoformat(),'passed':True,'layers':layers,'requests':len(req),'c4':c4,'small_W_unchanged':True,'semantic_cache_alignment':True,'history_alignment':True})
    if not (ROOT/'evidence/submissions.json').exists():save(ROOT/'evidence/submissions.json',[])
    print(json.dumps({'CPU_PREPARED':True,'layers':layers,'requests':len(req),'C4':c4},ensure_ascii=False))
if __name__=='__main__':main()
