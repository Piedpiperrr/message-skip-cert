"""仅采集当前预固定shard；不导入risk、不计算threshold/calibration/accuracy。"""
from common import *
import signal,traceback,resource
from native_runtime import Runtime
assert SHARD in ['1','2'] and os.environ.get('PBS_JOBID')
assert not (S/'records/attempts.jsonl').exists(),'禁止重复执行同一shard或自动replacement'
freeze=validate_freeze();freeze_hash=sha(P/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json')
barrier=read(P/'BOTH_SUBMISSIONS_CONFIRMED.json')
assert len(barrier['jobs'])==2 and barrier['protocol_freeze_sha256']==freeze_hash
assert barrier['jobs'][SHARD]['job_id']==os.environ['PBS_JOBID']
def interrupted(signum,frame):raise RuntimeError(f'FACILITY_SIGNAL_{signum}_NO_REPLACEMENT')
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
started=time.perf_counter();counts={a:0 for a in ['R','T','C','P']};success=[];success_set=set();attempts=0;phase='MODEL_LOADING';failed_key=None
def progress(status='RUNNING'):
    done=sum(counts.values());elapsed=time.perf_counter()-started
    save(S/'PROGRESS.json',dict(status=status,phase=phase,utc=utc(),job_id=os.environ['PBS_JOBID'],shard=int(SHARD),
        action_success_count=sum(counts[a] for a in ['R','T','C']),probe_success_count=counts['P'],
        complete_rows=counts['P'],counts=counts,attempt_count=attempts,expected_rows=6016,expected_requests=24064,
        wall_seconds=elapsed,remaining_wall_seconds=max(0,float(os.environ['MMLU_DEADLINE_EPOCH'])-time.time()),
        ETA_remaining_seconds=elapsed*(24064-done)/done if done else None,runtime_failures=int(failed_key is not None),
        successful_IDs_path=str(S/'records/successful_keys.json'),scientific_analysis_performed=False))
    save(S/'records/successful_keys.json',success)
try:
    progress();rt=Runtime();phase='SYNTHETIC_MECHANICAL_SMOKE';progress()
    smoke=rt.mechanical_smoke();save(S/'GPU_MECHANICAL_PASS.json',smoke)
    assert smoke['status']=='PASS' and smoke['MMLU_PRO_OUTCOMES_OBSERVED'] is False
    save(S/'EXECUTION_CLEARANCE.json',dict(utc=utc(),job_id=os.environ['PBS_JOBID'],shard=SHARD,
        protocol_freeze_sha256=freeze_hash,mechanical_pass_sha256=sha(S/'GPU_MECHANICAL_PASS.json'),
        both_submissions_sha256=sha(P/'BOTH_SUBMISSIONS_CONFIRMED.json'),MMLU_PRO_OUTCOMES_OBSERVED=False))
    # 首次读取project query在所有机械检查通过之后；不打开parquet/gold。
    qmap=project_queries();shard=read(P/'splits/STAGE1_CANDIDATE_SHARDS.json')['jobs'][int(SHARD)-1]
    assert sum(len(shard[k]) for k in ['fit','cal','dev'])==6016
    for split in ['fit','cal','dev']:
        phase='COLLECT_'+split;progress()
        for ordinal,ident in enumerate(shard[split]):
            q=qmap[ident];qh=queryhash(q)
            for action in ['R','T','C','P']:
                stop_check();key=f'mmlu_pro|{split}|{ident}|{action}';assert key not in success_set
                attempts+=1;failed_key=key
                append(S/'records/attempts.jsonl',dict(event='START',utc=utc(),key=key,attempt=attempts,query_sha256=qh))
                result=rt.probe(q) if action=='P' else rt.action(q,action)
                record=dict(key=key,pair='large',task='mmlu_pro',split=split,id=ident,ordinal=ordinal,action=action,
                    query=q,query_sha256=qh,utc=utc(),attempt=attempts,shard=int(SHARD),job_id=os.environ['PBS_JOBID'],
                    protocol_freeze_sha256=freeze_hash,**result)
                append(S/f'{"probes" if action=="P" else "actions"}/{split}.jsonl',record)
                append(S/'records/attempts.jsonl',dict(event='SUCCESS',utc=utc(),key=key,attempt=attempts))
                counts[action]+=1;success.append(key);success_set.add(key);failed_key=None
                if sum(counts.values())==1:
                    save(S/'OUTCOMES_OBSERVED.json',dict(utc=utc(),MMLU_PRO_OUTCOMES_OBSERVED=True,first_success_key=key,
                        protocol_freeze_sha256=freeze_hash,both_submissions_confirmed_before_outcome=True))
            if (ordinal+1)%20==0 or ordinal+1==len(shard[split]):
                progress();print('PROGRESS',SHARD,split,ordinal+1,'actions',sum(counts[a] for a in ['R','T','C']),'probes',counts['P'],flush=True)
    assert all(counts[a]==6016 for a in counts) and len(success)==len(set(success))==24064
    phase='FORMAL_COLLECTION_COMPLETE';progress('INFERENCE_COMPLETE')
    save(S/'INFERENCE_COMPLETE.json',dict(utc=utc(),job_id=os.environ['PBS_JOBID'],shard=int(SHARD),actions=18048,probes=6016,
        expected_rows=6016,attempts=attempts,retries=0,gold_read=False,scientific_analysis_performed=False,
        CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
        files={str(p.relative_to(S)):sha(p) for d in ['actions','probes'] for p in sorted((S/d).glob('*.jsonl'))}))
except BaseException as exc:
    status='PARTIAL_MMLU_PRO_STAGE1' if sum(counts.values()) else 'BLOCKED_MMLU_PRO_STAGE1'
    progress(status)
    save(S/'EXECUTION_FAILURE.json',dict(status=status,utc=utc(),phase=phase,error=repr(exc),traceback=traceback.format_exc(),
        failed_request_key=failed_key,counts=counts,attempts=attempts,resubmit_allowed=False,third_job_forbidden=True))
    raise
