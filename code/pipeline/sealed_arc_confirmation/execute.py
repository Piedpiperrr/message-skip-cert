from common import *
import importlib.util,traceback
compute();verify_freeze('PRE_TEST_FREEZE.json');verify_freeze('TEST_POPULATION_FREEZE.json')
assert not (P/'records/attempts.jsonl').exists(),'No resume or repeated successful IDs'
spec=importlib.util.spec_from_file_location('frozen_parser',CFG['parser_path']);parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
assert sha(CFG['parser_path'])==CFG['parser_sha256']
from native_adapter import Runtime,sync
start=time.perf_counter();rt=Runtime();sync()
save(P/'evidence/startup_total.json',{'wall_seconds':time.perf_counter()-start,'job_id':os.environ['PBS_JOBID'],'per_question_amortization':False})
attempt=0;probes=0;success=[];first=True
thresholds={b:d['threshold'] for b,d in CFG['thresholds'].items()}
queries=jl(P/'inputs/test_queries_no_gold.jsonl')
for ordinal,row in enumerate(queries):
 assert ordinal==row['ordinal']
 paths=CFG['order']['paths'];k=ordinal%4;order=paths[k:]+paths[:k]
 for order_position,path in enumerate(order):
  stop_check();assert attempt<4688
  mode,b=path.split('_');i=row['id'];request_key=f'arc|{i}|{path}';threshold=CFG['thresholds'][b]['threshold']
  attempt+=1
  if mode=='policy':probes+=1;assert probes<=2344
  append(P/'records/attempts.jsonl',{'event':'START','utc':utc(),'key':request_key,'attempt':attempt,'probe_attempt':probes if mode=='policy' else None,'job_id':os.environ['PBS_JOBID']})
  try:
   rt.begin();sync();t0=time.perf_counter()
   q={k:row[k] for k in ['question_stem','choice_labels','choice_text']};t1=time.perf_counter();meta=None
   if mode=='policy':u,meta=rt.probe(q)
   t2=time.perf_counter()
   selected=('R' if u<=thresholds[b] else b) if mode=='policy' else b
   t3=time.perf_counter();result=rt.action(q,selected);sync();t4=time.perf_counter()
   parsed=parser.parse_answer(result['raw_answer'],q['choice_labels']);t5=time.perf_counter()
   rt.end();sync();t6=time.perf_counter()
   parts=dict(input_prepare_ms=(t1-t0)*1000,probe_ms=(t2-t1)*1000,selector_ms=(t3-t2)*1000,action_ms=(t4-t3)*1000,parse_ms=(t5-t4)*1000,cleanup_ms=(t6-t5)*1000)
   result['selected']=selected;rt.validate_and_release(result);traces,gpu=rt.trace_result()
   rec={'key':request_key,'attempt':attempt,'dataset':'arc','reference':b,'mode':mode,'id':i,'ordinal':ordinal,'group':row['group_representative'],'primary':row['primary'],'order_position':order_position,'selected':selected,'threshold':threshold if mode=='policy' else None,'latency_ms':(t6-t0)*1000,'parts_ms':parts,'probe':meta,'parsed':parsed,'output':result,'trace':traces,'GPU_forward_event_sum_ms':gpu,'cold_first_request':first,'runtime_failure':False,'utc':utc(),'job_id':os.environ['PBS_JOBID']}
   append(P/'records/e2e_requests.jsonl',rec);first=False
   if meta:
    append(P/'records/probe_timing_2344.jsonl',{'key':request_key,'id':i,'reference':b,'ordinal':ordinal,'probe_ordinal':probes,'probe_ms':parts['probe_ms'],'selector_ms':parts['selector_ms'],**meta})
    append(P/f'records/large_arc_{b}_scores_routes.jsonl',{'id':i,'ordinal':ordinal,'group':row['group_representative'],'primary':row['primary'],'reference':b,'q':CFG['thresholds'][b]['q'],'threshold':threshold,'ProbeMax':u,'route':selected,'probe_ids_sha256':meta['probe_ids_sha256'],'p_labels':meta['p_labels'],'record_key':request_key})
   success.append(request_key);append(P/'records/attempts.jsonl',{'event':'SUCCESS','key':request_key,'attempt':attempt,'utc':utc()})
   if attempt%16==0:
    save(P/'REPLAY_PROGRESS.json',{'utc':utc(),'job_id':os.environ['PBS_JOBID'],'successful_count':len(success),'successful_keys':success,'attempts':attempt,'probe_attempts':probes,'last_ordinal':ordinal,'remaining_action_attempts':4688-attempt,'remaining_online_probe_attempts':2344-probes});print('PROGRESS',attempt,ordinal,path,flush=True)
  except BaseException as e:
   append(P/'records/failures.jsonl',{'key':request_key,'attempt':attempt,'utc':utc(),'error':repr(e),'traceback':traceback.format_exc(),'no_retry':True})
   save(P/'REPLAY_PROGRESS.json',{'status':'PARTIAL','job_id':os.environ['PBS_JOBID'],'successful_count':len(success),'successful_keys':success,'attempts':attempt,'probe_attempts':probes});raise
assert attempt==4688 and probes==2344 and len(set(success))==4688
writejl(P/'records/successful_request_keys.jsonl',[{'key':k} for k in success])
# Gold-free identity audit and complete 1172-row combined score/route artifact.
rows=jl(P/'records/e2e_requests.jsonl');rr={(r['id'],r['mode'],r['reference']):r for r in rows};combined=[];identity=[]
for q in queries:
 i=q['id'];a=rr[i,'policy','T'];b=rr[i,'policy','C']
 combined.append({'id':i,'ordinal':q['ordinal'],'group':q['group_representative'],'primary':q['primary'],'Text_ProbeMax':a['probe']['ProbeMax'],'C2C_ProbeMax':b['probe']['ProbeMax'],'Text_route':a['selected'],'C2C_route':b['selected'],'independent_probe_scores_equal':a['probe']['ProbeMax']==b['probe']['ProbeMax'],'independent_probe_input_hashes_equal':a['probe']['probe_ids_sha256']==b['probe']['probe_ids_sha256']})
 for ref in ['T','C']:
  p=rr[i,'policy',ref];r=rr[i,'reference',ref]
  if p['selected']==ref:
   fields=['raw_answer','generated_token_ids']+(['helper_message','helper_generated_token_ids'] if ref=='T' else [])
   identity.append({'id':i,'reference':ref,'raw_answer_equal':p['output']['raw_answer']==r['output']['raw_answer'],'generated_token_ids_equal':p['output']['generated_token_ids']==r['output']['generated_token_ids'],'parsed_equal':p['parsed']==r['parsed'],'native_output_identity':all(p['output'].get(f)==r['output'].get(f) for f in fields)})
writejl(P/'records/frozen_scores_routes_1172.jsonl',combined);writejl(P/'records/reference_route_identity.jsonl',identity)
save(P/'evidence/PREDICTION_DIAGNOSTICS.json',{'utc':utc(),'actions':4688,'probes':2344,'gold_read':False,'score_identity_failures':sum(not r['independent_probe_scores_equal'] for r in combined),'input_identity_failures':sum(not r['independent_probe_input_hashes_equal'] for r in combined),'reference_route_identity_checks':len(identity),'reference_route_identity_failures':[r for r in identity if not all(r[k] for k in ['raw_answer_equal','generated_token_ids_equal','parsed_equal','native_output_identity'])],'cold_request_count':sum(r['cold_first_request'] for r in rows)})
freeze('PREDICTION_TIMING_FREEZE.json',list((P/'records').glob('*.jsonl'))+[P/'evidence/PREDICTION_DIAGNOSTICS.json',P/'TEST_POPULATION_FREEZE.json',P/'evidence/startup_total.json'],job_id=os.environ['PBS_JOBID'],complete_actions=4688,independent_online_probes=2344,gold_read=False)
print('PREDICTION_TIMING_FREEZE_COMPLETE',sha(P/'PREDICTION_TIMING_FREEZE.json'),flush=True)
