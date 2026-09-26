"""四臂实际完整在线请求。没有 gold、Stage1 分数/输出或 calibration 入口。"""
from common import *
import traceback,signal

def timed_arm(rt,row,arm,threshold,sync,clock=time.perf_counter):
    is_policy=arm.startswith('policy');reference=arm[-1]
    # Synchronize prior work before entering this request's authoritative timer.
    sync();t0=clock()
    q={k:(list(row[k]) if k in ['choice_labels','choice_text'] else row[k]) for k in ['id','question_stem','choice_labels','choice_text']}
    rt.check_hooks();t1=clock()
    probe=rt.probe(q) if is_policy else None;t2=clock()
    selected=('R' if probe['ProbeMax']<=threshold else reference) if is_policy else reference;t3=clock()
    result=rt.action(q,selected);t4=clock()
    del q
    rt.check_hooks();sync();t5=clock()
    parts=dict(input_preparation_and_entry_ms=(t1-t0)*1000,online_probe_ms=(t2-t1)*1000,
        selector_ms=(t3-t2)*1000,complete_native_action_decode_parser_ms=(t4-t3)*1000,final_cleanup_sync_ms=(t5-t4)*1000)
    return selected,probe,result,parts,(t5-t0)*1000

def main():
    assert os.environ.get('PBS_JOBID') and read(P/'evidence/ALLOCATION_GUARD.json')['status']=='PASS'
    assert not (P/'records/attempts.jsonl').exists(),'ONE FORMAL REPLAY ONLY'
    cfg=verify_freeze();fhash=sha(FREEZE)
    def interrupted(signum,frame):raise RuntimeError(f'FACILITY_SIGNAL_{signum}_NO_RESUBMISSION')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    begin=time.perf_counter()
    from native_runtime import Runtime,sync,native
    imported=time.perf_counter();rt=Runtime();sync();loaded=time.perf_counter()
    assert len(native.lm.FUSER_LOAD_AUDIT)==36 and all(x['strict'] and not x['missing_keys'] and not x['unexpected_keys'] for x in native.lm.FUSER_LOAD_AUDIT)
    save(P/'evidence/STARTUP.json',dict(status='PASS',utc=utc(),runtime_import_seconds=imported-begin,
        startup_total_including_runtime_import_seconds=loaded-begin,model_and_fuser_load_seconds=rt.load_times,
        strict_model_loading_info=rt.load_info,fuser_loading_audit=native.lm.FUSER_LOAD_AUDIT,projector_count=36,
        helper_device=str(rt.runner.helper.device),receiver_device=str(rt.runner.receiver.device),
        warmup_requests=0,synthetic_forward_requests=0,amortized_into_question_latency=False,
        first_formal_request_retained=True,one_residency=True))
    print('STRICT_LOAD_PASS',json.dumps(rt.load_times),flush=True)
    panel=rows(P/'inputs/panel_queries.jsonl');ids=read(P/'inputs/panel_ids.json')
    N=len(ids);NREQ=N*len(ARMS);NPOL=N*sum(a.startswith('policy') for a in ARMS)  # E3 FULL: counts derived from the list length
    assert [r['id'] for r in panel]==ids and N==len(set(ids))==cfg['expected_counts']['questions'] and NREQ==cfg['expected_counts']['complete_action_requests']
    schedule=read(P/'protocol/ARM_SCHEDULE.json');attempt=probes=0;success=[];started=time.perf_counter()
    def progress(state='RUNNING'):
        elapsed=time.perf_counter()-started
        save(P/'REPLAY_PROGRESS.json',dict(utc=utc(),status=state,job_id=os.environ['PBS_JOBID'],complete_requests=len(success),
            complete_questions=len(success)//len(ARMS),online_probe_attempts=probes,attempts=attempt,expected_requests=NREQ,expected_probes=NPOL,
            successful_keys=success,elapsed_seconds=elapsed,ETA_remaining_seconds=elapsed*(NREQ-len(success))/len(success) if success else None,
            remaining_wall_seconds=max(0,float(os.environ['MMLU_DEADLINE_EPOCH'])-time.time()),scientific_analysis_performed=False))
    progress()
    for ordinal,row in enumerate(panel):
        assert schedule[ordinal]['id']==row['id'] and schedule[ordinal]['arms']==order_for(ordinal)
        for position,arm in enumerate(schedule[ordinal]['arms']):
            stop_check();attempt+=1;assert attempt<=NREQ
            is_policy=arm.startswith('policy');reference=arm[-1]
            if is_policy:probes+=1;assert probes<=NPOL
            key=f'mmlu_pro|{row["id"]}|{arm}';threshold=cfg['deployments'][reference]['threshold'];assert threshold==THRESHOLD
            append(P/'records/attempts.jsonl',dict(event='START',utc=utc(),key=key,attempt=attempt,probe_attempt=probes if is_policy else None,
                panel_ordinal=ordinal,order_position=position,query_sha256=queryhash(row),job_id=os.environ['PBS_JOBID']))
            if attempt==1:save(P/'MMLU_PRO_STAGE2_OUTCOMES_STARTED.json',dict(utc=utc(),MMLU_PRO_STAGE2_RESULTS_OBSERVED=True,
                first_formal_attempt=key,successful_results_at_marker=0,freeze_sha256=fhash))
            try:
                selected,probe,result,parts,elapsed=timed_arm(rt,row,arm,threshold,sync)
                record=dict(key=key,task='mmlu_pro',id=row['id'],query_sha256=queryhash(row),panel_ordinal=ordinal,order_position=position,
                    arm=arm,reference=reference,policy_q=.4 if is_policy else None,threshold=threshold if is_policy else None,
                    selected=selected,latency_ms=elapsed,parts_ms=parts,probe=probe,
                    **{k:result[k] for k in ['output','parsed','answer','invalid','native_first_input_ids','runtime_diagnostics']},
                    native_inner_diagnostic_ms=result['latency_ms'],runtime_failure=False,
                    probe_KV_reuse=False,probe_prefill_reuse=False,selected_action_really_executed=True,
                    first_formal_request_global=attempt==1,attempt=attempt,job_id=os.environ['PBS_JOBID'],utc=utc(),stage2_freeze_sha256=fhash)
                append(P/'records/four_arm_requests.jsonl',record)
                if probe:append(P/'records/two_policy_probes.jsonl',dict(key=key,id=row['id'],arm=arm,panel_ordinal=ordinal,
                    query_sha256=record['query_sha256'],outer_probe_ms=parts['online_probe_ms'],selector_ms=parts['selector_ms'],
                    route=selected,threshold=threshold,independent_online_probe=True,**probe))
                append(P/'records/attempts.jsonl',dict(event='SUCCESS',utc=utc(),key=key,attempt=attempt));success.append(key)
                if attempt%16==0:
                    progress();print('PROGRESS',len(success),f'/{NREQ}','ONLINE_PROBES',probes,f'/{NPOL}',flush=True)
                del result,record,probe
            except BaseException as error:
                append(P/'records/attempts.jsonl',dict(event='FAILURE',utc=utc(),key=key,attempt=attempt,error=repr(error)))
                progress('PARTIAL' if success else 'BLOCKED')
                save(P/'REQUEST_FAILURE.json',dict(utc=utc(),key=key,attempt=attempt,error=repr(error),traceback=traceback.format_exc(),
                    complete_requests=len(success),successful_keys=success,resubmit_allowed=False))
                raise
    assert attempt==len(success)==len(set(success))==NREQ and probes==NPOL
    progress('REPLAY_COMPLETE')
    save(P/'REPLAY_COMPLETE.json',dict(utc=utc(),status='COMPLETE',job_id=os.environ['PBS_JOBID'],complete_requests=NREQ,
        per_arm_requests={a:N for a in ARMS},online_ProbeMax=NPOL,retries=0,
        requests_sha256=sha(P/'records/four_arm_requests.jsonl'),probes_sha256=sha(P/'records/two_policy_probes.jsonl'),
        attempts_sha256=sha(P/'records/attempts.jsonl'),gold_read=False,Stage1_outputs_read=False,scientific_analysis_performed=False))
    print('REPLAY_COMPLETE',flush=True)

if __name__=='__main__':main()
