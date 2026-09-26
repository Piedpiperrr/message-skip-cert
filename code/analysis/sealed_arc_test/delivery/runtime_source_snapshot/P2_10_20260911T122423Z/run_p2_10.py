"""单一阶段恢复入口：大 W -> 大两数据集 -> 小两数据集；各组合先 train。"""
import argparse,gc,json,os,socket,sys,time,traceback
from pathlib import Path
import torch,transformers
from threadpoolctl import threadpool_limits,threadpool_info
import runtime
import arc_runtime_adapter
from arc_runtime_adapter import arc_protocol as arc
from common_p2_10 import ROOT,ACTIONS,save,readrows,append,sha,utc,query_only
from ac_p2_10 import large_w,ac_request,validate_result
from router_p2_10 import fit_freeze,measure_overhead,freeze_train_mixture
from scoring import score as obqa_score

def hook_counts(runner):
    return {'helper':[len(m._forward_hooks) for m in runner.helper.model.layers],'receiver':[len(m._forward_hooks) for m in runner.receiver.model.layers]}

def main(max_seconds):
    assert os.environ.get('PBS_JOBID') and socket.gethostname().startswith('ClusterB-gpu')
    assert torch.cuda.is_available() and torch.cuda.device_count()==2
    threadpool_limits(limits=1);torch.set_num_threads(4)
    torch.manual_seed(0);torch.cuda.manual_seed_all(0)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    cfg=json.loads((ROOT/'frozen_config.json').read_text());receipt=json.loads((ROOT/'evidence/freeze_receipt.json').read_text())
    assert sha(ROOT/'frozen_config.json')==receipt['config_sha256']
    for name,h in cfg['execution_source_sha256'].items():assert sha(ROOT/name)==h,name
    assert sha(cfg['small_W']['path'])==cfg['small_W']['sha256']
    job=os.environ['PBS_JOBID'];run=Path(os.environ['P2_RUN']);started=time.monotonic();deadline=started+max_seconds
    save(run/'environment.json',{'job_id':job,'utc':utc(),'hostname':socket.gethostname(),'python':sys.version,'torch':torch.__version__,'transformers':transformers.__version__,'cuda_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES'),'gpus':[str(torch.cuda.get_device_properties(i)) for i in [0,1]],'torch_threads':torch.get_num_threads(),'threadpool':threadpool_info(),'config_sha256':sha(ROOT/'frozen_config.json'),'source_sha256':cfg['execution_source_sha256']})
    requests=readrows(ROOT/'data/request_manifest.jsonl')
    def stop(phase,pair=None,dataset=None,split=None):
        save(run/'segment_complete.json',{'complete':False,'resume_required':True,'phase':phase,'pair':pair,'dataset':dataset,'split':split,'utc':utc(),'seconds':time.monotonic()-started});return False
    for pair in cfg['pair_order']:
        if all((ROOT/'results'/pair/d/'completion.json').exists() for d in cfg['dataset_order']):continue
        if time.monotonic()>deadline-600:return stop('before_load',pair)
        runtime.lm.FUSER_LOAD_AUDIT.clear();runner=runtime.Runner(cfg['pair_configs'][pair]);baseline_hooks=hook_counts(runner)
        layers={r:cfg['ac_layers'][r][pair] for r in ['helper','receiver']}
        for r in layers:
            model=getattr(runner,r);assert model.config.num_hidden_layers==layers[r]['num_hidden_layers'] and model.config.hidden_size==layers[r]['hidden_size']
        save(run/f'{pair}_load.json',{'utc':utc(),'job_id':job,'load_times':runner.load_times,'layers':layers,'fusers':runtime.lm.FUSER_LOAD_AUDIT,'c2c_mapping':runner.cr.mapping,'torch_threads':torch.get_num_threads(),'cuda_peer_0_to_1':torch.cuda.can_device_access_peer(0,1),'W_device':'cuda:1'})
        if pair=='large':
            W=large_w(runner,cfg,deadline)
            if W is None:return stop('large_W',pair)
        else:
            W=torch.nn.Linear(layers['helper']['hidden_size'],layers['receiver']['hidden_size'],bias=False,device='cuda:1',dtype=torch.float32)
            w=torch.load(cfg['small_W']['path'],map_location='cpu',weights_only=True);assert w['steps']==960
            W.load_state_dict(w['state_dict'],strict=True);W.eval().requires_grad_(False)
            save(run/'small_W_receipt.json',{'utc':utc(),'sha256':sha(cfg['small_W']['path']),'source':cfg['small_W']['path'],'not_trained':True})
        def call(row,action):
            q=query_only(row)
            result=ac_request(runner,q,W,layers) if action=='acw' else runner.request(q,action)
            if action=='receiver_only':result['transfer']={'path':'CPU prompt IDs -> cuda:1; no inter-model payload','logical_payload_bytes':0,'receiver_input_id_bytes':result['receiver_input_tokens']*8,'generated_id_D2H_bytes':len(result['generated_token_ids'])*8}
            elif action=='text':result['transfer']={'path':'cuda:0 generated IDs -> CPU decode/template/tokenize -> cuda:1 receiver IDs','helper_generated_id_D2H_bytes':len(result['helper_generated_token_ids'])*8,'helper_text_utf8_bytes':len(result['helper_message'].encode()),'receiver_input_id_H2D_bytes':result['receiver_input_tokens']*8}
            elif action=='c2c':result['transfer']={'path':'cuda:0 contiguous KV -> cuda:1 per-layer tensors','actual_kv_bytes':result['transferred_kv_bytes']}
            return result
        # No extra generation beyond these three fixed structural smoke questions.
        smoke=ROOT/'evidence/smoke_attempts.jsonl';smoke_results=[]
        for idx,n in enumerate([3,4,5]):
            row={'id':f'synthetic_{n}','question_stem':'Which animal can fly?','choice_labels':list('ABCDE')[:n],'choice_text':['cat','dog','sharedfs','cow','horse'][:n]}
            row['choices']={'label':row['choice_labels'],'text':row['choice_text']}
            for action in cfg['orders'][idx]:
                assert len(readrows(smoke))<72
                append(smoke,{'job_id':job,'pair':pair,'id':row['id'],'action':action,'utc':utc()})
                result=call(row,action);runtime.sync();validate_result(result,action);assert hook_counts(runner)==baseline_hooks
                smoke_results.append({'id':row['id'],'action':action,**result})
        save(run/f'{pair}_smoke.json',{'passed':True,'correctness_not_a_gate':True,'requests':smoke_results,'hook_cleanup_passed':True})
        del smoke_results,result
        print(json.dumps({'phase':'GPU_READY','pair':pair,'utc':utc()}),flush=True)
        for dataset in cfg['dataset_order']:
            out=ROOT/'results'/pair/dataset
            if (out/'completion.json').exists():continue
            bundles=None
            for split,spec in cfg['data'][dataset].items():
                assert sha(spec['path'])==spec['sha256'];rr=readrows(spec['path']);byid={r['id']:r for r in rr}
                panel=set(cfg['cost_panel'][dataset][split]['ids'])
                if split!='train':
                    if time.monotonic()>deadline-240:return stop('before_fit',pair,dataset,split)
                    bundles=fit_freeze(out,cfg,dataset,pair)
                    # Keep all action and router measurement CPU settings identical.
                    torch.set_num_threads(4)
                    bundles['_overhead_done']={(r['id'],r['split'],r['family'],r['n_actions']) for r in readrows(out/'router_overhead.jsonl')}
                    tr={r['id']:r for r in readrows(cfg['data'][dataset]['train']['path'])}
                    for i in cfg['cost_panel'][dataset]['train']['ids']:
                        if time.monotonic()>deadline-120:return stop('train_overhead',pair,dataset)
                        measure_overhead(out,query_only(tr[i])|{'id':i},'train',runner,bundles,job,f'{job}|{pair}|{dataset}|train_router|{i}',runtime.sync)
                    freeze_train_mixture(out,cfg,dataset,job)
                    assert (out/'router_fit_receipt.json').exists() and (out/'train_mixture_receipt.json').exists()
                    print(json.dumps({'phase':'ROUTER_AND_DEV_CHOICES_FROZEN','pair':pair,'dataset':dataset,'utc':utc()}),flush=True)
                dest=out/f'{split}_cases.jsonl';old=readrows(dest);success={r['key']:r for r in old if r['runtime_error'] is None};assert len(success)==sum(r['runtime_error'] is None for r in old)
                grouped={}
                for r in requests:
                    if (r['pair'],r['dataset'],r['split'])==(pair,dataset,split):grouped.setdefault(r['id'],[]).append(r)
                for qi,(qid,block) in enumerate(grouped.items()):
                    row=byid[qid];block_id=f'{job}|{pair}|{dataset}|{split}|{qid}'
                    missing=[r for r in block if r['key'] not in success]
                    overhead_missing=split!='train' and qid in panel and any((qid,split,f,n) not in bundles['_overhead_done'] for f in ['word','semantic'] for n in [3,4])
                    if not missing and not overhead_missing:continue
                    if time.monotonic()>deadline-120:return stop('requests',pair,dataset,split)
                    for req in missing:
                        while True:
                            failures=[r for r in readrows(ROOT/'evidence/failures.jsonl') if r['key']==req['key']]
                            retries=readrows(ROOT/'evidence/retry_attempts.jsonl')
                            if failures:
                                assert len(failures)==1 and not any(r['key']==req['key'] for r in retries),'failed key exhausted one retry'
                                assert len(retries)<32,'stage retry limit exhausted'
                                append(ROOT/'evidence/retry_attempts.jsonl',{'key':req['key'],'job_id':job,'utc':utc()})
                            try:
                                assert hook_counts(runner)==baseline_hooks
                                runtime.sync();began=time.perf_counter_ns();result=call(row,req['action']);runtime.sync();ms=(time.perf_counter_ns()-began)/1e6
                                diag_ms=validate_result(result,req['action']);assert hook_counts(runner)==baseline_hooks
                                scored=obqa_score(result['raw_answer'],row['gold_answer']) if dataset=='obqa' else arc.score(result['raw_answer'],row['gold_answer'],row['choice_labels'])
                                entry={**req,'job_id':job,'block_id':block_id,'utc':utc(),'runtime_error':None,'latency_ms':ms,'diagnostics_ms':diag_ms,'gold_answer':row['gold_answer'],'legal_labels':row['choice_labels'],'receiver_generated_tokens':len(result['generated_token_ids']),'helper_generated_tokens':len(result.get('helper_generated_token_ids',[])),'config_sha256':receipt['config_sha256'],**result,'scoring':scored}
                                append(dest,entry);success[req['key']]=entry;break
                            except Exception:
                                err={**req,'job_id':job,'block_id':block_id,'utc':utc(),'runtime_error':traceback.format_exc(),'config_sha256':receipt['config_sha256']}
                                append(dest,err);append(ROOT/'evidence/failures.jsonl',err)
                                if failures:raise
                    if overhead_missing:measure_overhead(out,query_only(row)|{'id':qid},split,runner,bundles,job,block_id,runtime.sync)
                    if (qi+1)%64==0 or qi+1==len(grouped):print(json.dumps({'phase':'ACTIONS','pair':pair,'dataset':dataset,'split':split,'questions':qi+1,'successes':len(success),'utc':utc()}),flush=True)
                assert len(success)==sum(len(b) for b in grouped.values())
            save(out/'completion.json',{'utc':utc(),'job_id':job,'complete':True,'router_fit_receipt_sha256':sha(out/'router_fit_receipt.json'),'train_mixture_sha256':sha(out/'train_mixture_receipt.json')})
        del W,runner,bundles;gc.collect();torch.cuda.empty_cache();runtime.sync()
    complete=all((ROOT/'results'/p/d/'completion.json').exists() for p in cfg['pair_order'] for d in cfg['dataset_order'])
    save(run/'segment_complete.json',{'complete':complete,'resume_required':not complete,'seconds':time.monotonic()-started,'utc':utc()})
    print('P2_10_GPU_COMPLETE' if complete else 'P2_10_RESUME_REQUIRED',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--max-seconds',type=int,required=True)
    try:main(ap.parse_args().max_seconds)
    except Exception:
        save(Path(os.environ['P2_RUN'])/'fatal_error.json',{'utc':utc(),'traceback':traceback.format_exc()});raise
