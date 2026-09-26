"""E8 task 5: end-to-end replay of every deployed E8 policy on the frozen 128-question MMLU-Pro panel.

Built from the frozen MMLU-Pro replay driver
P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z/src/execute.py: `timed_arm` is reproduced verbatim and the
frozen Runtime.probe / Runtime.action are called unchanged. Differences, all forced by which policies
deployed: the pair is small or medium instead of large, and the arm list holds only the deployed
references of that pair (2 arms if one reference deployed, 4 if both), rotated left by question
ordinal as in the frozen driver. No warm-up, cold requests kept, batch 1, no gold."""
from common_e8 import *
import traceback,signal
R=P/'REPLAY_E8'
PAIRREF=os.environ['E8_REPLAY_REFS']          # e.g. "C" or "T,C"
REFS=[x for x in PAIRREF.split(',') if x]
ARMS=[a for ref in ['T','C'] if ref in REFS for a in (f'fixed_{ref}',f'policy_{ref}')]
JOB=os.environ.get('PBS_JOBID','')

def order_for(i):
    offset=i%len(ARMS);return ARMS[offset:]+ARMS[:offset]

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
    assert JOB and PAIR in ('small','medium') and REFS
    out=R/PAIR
    assert not (out/'records/attempts.jsonl').exists(),'ONE FORMAL REPLAY PER PAIR ONLY'
    validate_freeze()
    cfg=read(R/'REPLAY_FREEZE_E8.json')
    dep={ref:cfg['policies'][f'{PAIR}/{ref}'] for ref in REFS}
    assert cfg['arms'][PAIR]==ARMS,(cfg['arms'][PAIR],ARMS)
    def interrupted(signum,frame):raise RuntimeError(f'FACILITY_SIGNAL_{signum}_NO_RESUBMISSION')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    begin=time.perf_counter()
    from native_runtime_e8 import Runtime,sync,native
    imported=time.perf_counter();rt=Runtime(PAIR);sync();loaded=time.perf_counter()
    audit=native.lm.FUSER_LOAD_AUDIT
    assert len(audit)==pair_config(PAIR)['projector_count'] and all(x['strict'] and not x['missing_keys'] and not x['unexpected_keys'] for x in audit)
    save(out/'evidence/STARTUP.json',dict(status='PASS',utc=utc(),pair=PAIR,runtime_import_seconds=imported-begin,
        startup_total_including_runtime_import_seconds=loaded-begin,model_and_fuser_load_seconds=rt.load_times,
        strict_model_loading_info=rt.load_info,fuser_loading_audit=audit,projector_count=len(audit),
        helper_device=str(rt.runner.helper.device),receiver_device=str(rt.runner.receiver.device),
        warmup_requests=0,synthetic_forward_requests=0,amortized_into_question_latency=False,
        first_formal_request_retained=True,one_residency=True))
    print('STRICT_LOAD_PASS',PAIR,json.dumps(rt.load_times),flush=True)
    panel=rows(R/'inputs/panel_queries.jsonl');pids=read(R/'inputs/candidate_e2e128_ids.json')
    assert [r['id'] for r in panel]==pids and len(pids)==128
    schedule=read(R/f'protocol/SCHEDULE_{PAIR}.json')
    expected=128*len(ARMS);attempt=probes=0;success=[];started=time.perf_counter()
    def progress(state='RUNNING'):
        e=time.perf_counter()-started
        save(out/'REPLAY_PROGRESS.json',dict(utc=utc(),status=state,pair=PAIR,job_id=JOB,complete_requests=len(success),
            complete_questions=len(success)//len(ARMS),online_probe_attempts=probes,attempts=attempt,
            expected_requests=expected,expected_probes=128*len(REFS),elapsed_seconds=e,
            ETA_remaining_seconds=e*(expected-len(success))/len(success) if success else None,
            remaining_wall_seconds=max(0,float(os.environ['E8_DEADLINE_EPOCH'])-time.time()),
            scientific_analysis_performed=False))
    progress()
    for ordinal,row in enumerate(panel):
        assert schedule[ordinal]['id']==row['id'] and schedule[ordinal]['arms']==order_for(ordinal)
        for position,arm in enumerate(schedule[ordinal]['arms']):
            stop_check();attempt+=1;assert attempt<=expected
            is_policy=arm.startswith('policy');reference=arm[-1]
            if is_policy:probes+=1
            key=f'{PAIR}|mmlu_pro|{row["id"]}|{arm}';threshold=dep[reference]['threshold']
            append(out/'records/attempts.jsonl',dict(event='START',utc=utc(),key=key,attempt=attempt,
                probe_attempt=probes if is_policy else None,panel_ordinal=ordinal,order_position=position,
                query_sha256=queryhash(row),job_id=JOB))
            try:
                selected,probe,result,parts,elapsed=timed_arm(rt,row,arm,threshold,sync)
                record=dict(key=key,pair=PAIR,task='mmlu_pro',id=row['id'],query_sha256=queryhash(row),
                    panel_ordinal=ordinal,order_position=position,arm=arm,reference=reference,
                    policy_q=dep[reference]['q'] if is_policy else None,threshold=threshold if is_policy else None,
                    selected=selected,latency_ms=elapsed,parts_ms=parts,probe=probe,
                    **{k:result[k] for k in ['output','parsed','answer','invalid','native_first_input_ids','runtime_diagnostics']},
                    native_inner_diagnostic_ms=result['latency_ms'],runtime_failure=False,
                    probe_KV_reuse=False,probe_prefill_reuse=False,selected_action_really_executed=True,
                    first_formal_request_global=attempt==1,attempt=attempt,job_id=JOB,utc=utc(),
                    protocol_freeze_E8_sha256=freeze_hash())
                append(out/'records/requests.jsonl',record)
                if probe:append(out/'records/policy_probes.jsonl',dict(key=key,id=row['id'],arm=arm,panel_ordinal=ordinal,
                    query_sha256=record['query_sha256'],outer_probe_ms=parts['online_probe_ms'],selector_ms=parts['selector_ms'],
                    route=selected,threshold=threshold,independent_online_probe=True,**probe))
                append(out/'records/attempts.jsonl',dict(event='SUCCESS',utc=utc(),key=key,attempt=attempt));success.append(key)
                if attempt%16==0:
                    progress();print('REPLAY',PAIR,len(success),'/',expected,'probes',probes,flush=True)
                del result,record,probe
            except BaseException as error:
                append(out/'records/attempts.jsonl',dict(event='FAILURE',utc=utc(),key=key,attempt=attempt,error=repr(error)))
                progress('PARTIAL' if success else 'BLOCKED')
                save(out/'REQUEST_FAILURE.json',dict(utc=utc(),key=key,attempt=attempt,error=repr(error),
                    traceback=traceback.format_exc(),complete_requests=len(success),resubmit_allowed=False))
                raise
    assert attempt==len(success)==len(set(success))==expected and probes==128*len(REFS)
    progress('REPLAY_COMPLETE')
    save(out/'REPLAY_COMPLETE.json',dict(utc=utc(),status='COMPLETE',pair=PAIR,job_id=JOB,arms=ARMS,
        complete_requests=expected,online_ProbeMax=probes,retries=0,
        requests_sha256=sha(out/'records/requests.jsonl'),probes_sha256=sha(out/'records/policy_probes.jsonl'),
        attempts_sha256=sha(out/'records/attempts.jsonl'),gold_read=False,scientific_analysis_performed=False))
    print('REPLAY_COMPLETE',PAIR,flush=True)

if __name__=='__main__':main()
