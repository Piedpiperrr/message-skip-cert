"""Actual online two-arm replay; exact Stage 1 runtime, no gold or expected-answer reads."""
from common import *
import traceback

def order_for(ordinal):
    return ['fixed_C','policy_C'] if ordinal%2==0 else ['policy_C','fixed_C']

def main():
    cfg=read(FREEZE);assert os.environ.get('PBS_JOBID')
    assert read(P/'evidence/ALLOCATION_GUARD.json')['status']=='PASS'
    assert not (P/'records/attempts.jsonl').exists(),'No second replay or retry'
    import_start=time.perf_counter()
    from native_runtime import Runtime,sync,native
    runtime_import_seconds=time.perf_counter()-import_start
    t=time.perf_counter();rt=Runtime();sync()
    load=dict(status='PASS',utc=utc(),job_id=os.environ['PBS_JOBID'],startup_wall_seconds=time.perf_counter()-t,
        load_seconds=rt.load_times,strict_model_loading_info=rt.load_info,fuser_loading_audit=native.lm.FUSER_LOAD_AUDIT,
        projector_count=len(rt.runner.cr.projectors),helper_device=str(rt.runner.helper.device),receiver_device=str(rt.runner.receiver.device),
        runtime_import_seconds=runtime_import_seconds,startup_total_including_runtime_import_seconds=time.perf_counter()-import_start,
        warmup_requests=0,synthetic_forward_requests=0,per_question_amortization=False)
    assert len(load['fuser_loading_audit'])==28 and all(x['strict'] and not x['missing_keys'] and not x['unexpected_keys'] for x in load['fuser_loading_audit'])
    save(P/'evidence/STARTUP.json',load);print('STRICT_LOAD_PASS',json.dumps(rt.load_times),flush=True)
    freeze_hash=sha(FREEZE);attempt=0;probe_attempt=0;success=[]
    for ds in cfg['execution_order']['tasks']:
        dep=cfg['deployments'][ds]; threshold=dep['threshold']
        panel=rows(P/f'inputs/{ds}_queries.jsonl')
        assert [r['id'] for r in panel]==read(P/f'inputs/{ds}_panel_ids.json')
        for ordinal,row in enumerate(panel):
            for position,arm in enumerate(order_for(ordinal)):
                stop_check();assert attempt<512
                attempt+=1;is_policy=arm=='policy_C'
                if is_policy:probe_attempt+=1;assert probe_attempt<=256
                key=f'{ds}|{row["id"]}|{arm}'
                append(P/'records/attempts.jsonl',dict(event='START',key=key,attempt=attempt,utc=utc(),
                    task=ds,panel_ordinal=ordinal,position=position,probe_attempt=probe_attempt if is_policy else None,job_id=os.environ['PBS_JOBID']))
                if attempt==1:save(P/'MEDIUM_STAGE2_OUTCOMES_STARTED.json',dict(utc=utc(),MEDIUM_STAGE2_RESULTS_OBSERVED=True,first_formal_attempt=key,successful_results_at_marker=0))
                try:
                    # The outer timer is authoritative. Inner Stage 1 timers are only diagnostics.
                    sync();t0=time.perf_counter()
                    q={'question_stem':row['question_stem'],'choice_labels':list(row['choice_labels']),'choice_text':list(row['choice_text'])}
                    rt.check_hooks();t1=time.perf_counter()
                    probe=rt.probe(q) if is_policy else None;t2=time.perf_counter()
                    selected=('R' if probe['ProbeMax']<=threshold else 'C') if is_policy else 'C';t3=time.perf_counter()
                    # action() calls complete native generation, decode, V2 parser and hook removal.
                    result=rt.action(q,selected);t4=time.perf_counter()
                    del q
                    rt.check_hooks();sync();t5=time.perf_counter()
                    parts=dict(input_preparation_and_entry_ms=(t1-t0)*1000,online_probe_ms=(t2-t1)*1000,
                        selector_ms=(t3-t2)*1000,complete_native_action_decode_parser_ms=(t4-t3)*1000,final_cleanup_sync_ms=(t5-t4)*1000)
                    record=dict(key=key,task=ds,id=row['id'],panel_ordinal=ordinal,order_position=position,arm=arm,
                        q=dep['q'],threshold=threshold,selected=selected,latency_ms=(t5-t0)*1000,parts_ms=parts,
                        probe=probe,**{k:result[k] for k in ['output','parsed','answer','invalid','native_first_input_ids','runtime_diagnostics']},
                        native_inner_diagnostic_ms=result['latency_ms'],runtime_failure=False,
                        probe_KV_reuse=False,probe_prefill_reuse=False,selected_action_really_executed=True,
                        first_formal_request_global=attempt==1,first_formal_request_task=ordinal==0 and position==0,
                        attempt=attempt,job_id=os.environ['PBS_JOBID'],utc=utc(),stage2_freeze_sha256=freeze_hash)
                    append(P/'records/e2e_requests.jsonl',record)
                    append(P/'records/attempts.jsonl',dict(event='SUCCESS',key=key,attempt=attempt,utc=utc()))
                    success.append(key)
                    if attempt%16==0:
                        save(P/'REPLAY_PROGRESS.json',dict(utc=utc(),job_id=os.environ['PBS_JOBID'],successful_count=len(success),
                            successful_keys=success,attempts=attempt,online_probe_attempts=probe_attempt,task=ds,panel_ordinal=ordinal,
                            remaining_requests=512-attempt,remaining_probes=256-probe_attempt))
                        print('PROGRESS',attempt,'/512',ds,ordinal,flush=True)
                    del result,record,probe
                except BaseException as error:
                    append(P/'records/attempts.jsonl',dict(event='FAILURE',key=key,attempt=attempt,error=repr(error),utc=utc()))
                    save(P/'REQUEST_FAILURE.json',dict(key=key,attempt=attempt,error=repr(error),traceback=traceback.format_exc(),
                        successful_count=len(success),successful_keys=success,probe_attempts=probe_attempt,resubmit_allowed=False))
                    raise
    assert attempt==512 and probe_attempt==256 and len(set(success))==512
    save(P/'REPLAY_COMPLETE.json',dict(status='COMPLETE',utc=utc(),job_id=os.environ['PBS_JOBID'],
        complete_requests=512,fixed_C2C_requests=256,policy_requests=256,online_ProbeMax_calls=256,
        requests_sha256=sha(P/'records/e2e_requests.jsonl'),attempts_sha256=sha(P/'records/attempts.jsonl'),
        gold_read_by_execution=False,expected_answer_read_by_execution=False,retries=0))
    print('REPLAY_COMPLETE',flush=True)

if __name__=='__main__':main()
