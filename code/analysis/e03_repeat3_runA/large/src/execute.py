from common import *
compute();assert (P/'PANEL_VALIDATION_FREEZE.json').exists()
import importlib.util,traceback,resource
spec=importlib.util.spec_from_file_location('frozen_parser',CFG['parser_path']);parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
assert sha(CFG['parser_path'])==CFG['parser_sha256']
from native_adapter import Runtime,sync
assert not (P/'records/attempts.jsonl').exists(),'No automatic resume or duplicate successful request'
start=time.perf_counter();rt=Runtime();sync();save(P/'evidence/startup_total.json',{'wall_seconds':time.perf_counter()-start,'job_id':os.environ['PBS_JOBID'],'per_question_amortization':False})
expected={(ds,b):{r['id']:r for r in jl(P/f'inputs/large_{ds}_{b}_expected_routes.jsonl')} for ds in ['obqa','arc'] for b in ['T','C']}
thresholds={(ds,b):read(P/f'protocol/large_{ds}_{b}_deployment.json')['threshold'] for ds,b in expected}
attempt=0;probes=0;success=[];first=True
for ds in CFG['order']['tasks']:
 queries=jl(P/f'inputs/{ds}_queries.jsonl')
 for ordinal,row in enumerate(queries):
  paths=CFG['order']['paths'];k=ordinal%4;order=paths[k:]+paths[:k]
  for order_position,path in enumerate(order):
   stop_check();assert attempt<1024
   mode,b=path.split('_');i=row['id'];request_key=f'{ds}|{i}|{path}'
   attempt+=1
   if mode=='policy':probes+=1;assert probes<=512
   append(P/'records/attempts.jsonl',{'event':'START','utc':utc(),'key':request_key,'attempt':attempt,'probe_attempt':probes if mode=='policy' else None,'job_id':os.environ['PBS_JOBID']})
   try:
    rt.begin();sync();t0=time.perf_counter()
    q={k:row[k] for k in ['question_stem','choice_labels','choice_text']};t1=time.perf_counter();meta=None
    if mode=='policy':u,meta=rt.probe(q)
    t2=time.perf_counter()
    selected=('R' if u<=thresholds[ds,b] else b) if mode=='policy' else b
    t3=time.perf_counter();result=rt.action(q,selected);sync();t4=time.perf_counter()
    parsed=parser.parse_answer(result['raw_answer'],q['choice_labels']);t5=time.perf_counter()
    rt.end();sync();t6=time.perf_counter()
    parts=dict(input_prepare_ms=(t1-t0)*1000,probe_ms=(t2-t1)*1000,selector_ms=(t3-t2)*1000,action_ms=(t4-t3)*1000,parse_ms=(t5-t4)*1000,cleanup_ms=(t6-t5)*1000)
    result['selected']=selected;rt.validate_and_release(result)
    traces,gpu=rt.trace_result()
    exp=expected[ds,b][i]
    identity={'input_hash_match':meta['probe_ids_sha256']==exp['probe_ids_sha256'],'FP32_score_equal':meta['ProbeMax']==exp['ProbeMax'],'route_match':selected==exp['route']} if meta else None
    rec={'key':request_key,'attempt':attempt,'dataset':ds,'reference':b,'mode':mode,'id':i,'panel_ordinal':ordinal,'order_position':order_position,'selected':selected,'latency_ms':(t6-t0)*1000,'parts_ms':parts,'probe':meta,'frozen_identity':identity,'parsed':parsed,'output':result,'trace':traces,'GPU_forward_event_sum_ms':gpu,'cold_first_request':first,'runtime_failure':False,'utc':utc(),'job_id':os.environ['PBS_JOBID']}
    append(P/'records/e2e_requests.jsonl',rec);first=False
    if identity and not all(identity.values()):raise SemanticFailure('ONLINE_FROZEN_PROBE_IDENTITY_MISMATCH; record saved, no retuning or retry')
    success.append(request_key)
    append(P/'records/attempts.jsonl',{'event':'SUCCESS','key':request_key,'attempt':attempt,'utc':utc()})
    if attempt%16==0:
     save(P/'REPLAY_PROGRESS.json',{'utc':utc(),'job_id':os.environ['PBS_JOBID'],'successful_count':len(success),'successful_keys':success,'attempts':attempt,'probe_attempts':probes,'remaining_action_attempts':1024-attempt,'remaining_online_probe_attempts':512-probes,'records_sha256':sha(P/'records/e2e_requests.jsonl')});print('PROGRESS',attempt,ds,ordinal,path,flush=True)
   except BaseException as e:
    append(P/'records/failures.jsonl',{'key':request_key,'attempt':attempt,'utc':utc(),'error':repr(e),'traceback':traceback.format_exc(),'no_retry':True})
    save(P/'REPLAY_PROGRESS.json',{'status':'PARTIAL','job_id':os.environ['PBS_JOBID'],'successful_count':len(success),'successful_keys':success,'attempts':attempt,'probe_attempts':probes,'remaining_action_attempts':1024-attempt,'remaining_online_probe_attempts':512-probes,'records_sha256':sha(P/'records/e2e_requests.jsonl') if (P/'records/e2e_requests.jsonl').exists() else None});raise
assert attempt==1024 and probes==512 and len(set(success))==1024
freeze('REPLAY_COMPLETE.json',[P/'records/e2e_requests.jsonl',P/'records/attempts.jsonl'],job_id=os.environ['PBS_JOBID'],action_attempts=attempt,online_probe_attempts=probes,successful=1024,existing_gold_read_by_execution=False)
print('REPLAY_COMPLETE',flush=True)
