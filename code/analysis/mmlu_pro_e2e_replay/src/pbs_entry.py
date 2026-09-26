from common import *
import subprocess,socket,fcntl,traceback
from guard_checks import allocation_identity
jid=os.environ.get('PBS_JOBID','');phase='SCHEDULER_GUARD';entry=time.perf_counter()
try:
    lock=(P/'evidence/execution.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    raw=Path('/proc/self/cgroup').read_text()
    save(P/'evidence/CGROUP_RECEIPT.json',dict(utc=utc(),job_id=jid,raw=raw,legacy_pattern_is_fatal=False))
    print('RESOLVED_PATHS',json.dumps(resolved_paths()),flush=True)
    rec=json.loads(subprocess.check_output(['job-status','-f','-F','json',jid],text=True,timeout=30));assert list(rec['Jobs'])==[jid]
    j=rec['Jobs'][jid];j.pop('Variable_List',None);save(P/'evidence/pbs/allocation.json',rec)
    check=allocation_identity(j,socket.gethostname(),Path(os.environ['PBS_NODEFILE']).read_text().split())
    save(P/'evidence/ALLOCATION_GUARD.json',dict(utc=utc(),job_id=jid,**check));assert check['status']=='PASS',check
    start=datetime.datetime.strptime(j['stime'],'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp()
    research_stop=datetime.datetime(2026,9,20,tzinfo=datetime.timezone.utc).timestamp()
    assert start+check['walltime_seconds']<=research_stop,'RESEARCH_HARD_STOP'
    deadline=start+check['walltime_seconds']-45;os.environ['MMLU_DEADLINE_EPOCH']=str(deadline)
    save(P/'evidence/DEADLINE.json',dict(utc=utc(),PBS_stime=j['stime'],walltime_seconds=check['walltime_seconds'],deadline_epoch=deadline,safety_margin_seconds=45))
    phase='CUDA_DEVICE_GUARD'
    import torch
    n=torch.cuda.device_count();available=torch.cuda.is_available()
    save(P/'evidence/CUDA_RECEIPT.json',dict(utc=utc(),available=available,device_count=n,CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
        devices=[dict(index=i,name=torch.cuda.get_device_properties(i).name,uuid=str(getattr(torch.cuda.get_device_properties(i),'uuid',None)),total_memory_bytes=torch.cuda.get_device_properties(i).total_memory) for i in range(n)]))
    assert available and n==2
    phase='ASSET_HASH_RECHECK';t=time.perf_counter();verify_freeze(include_weights=True)
    save(P/'evidence/ASSET_HASH_RECHECK.json',dict(utc=utc(),status='PASS',wall_seconds=time.perf_counter()-t))
    stop_check();phase='STRICT_LOAD_AND_FOUR_ARM_REPLAY'
    from execute import main
    main()
    save(P/'JOB_WORK_COMPLETE.json',dict(utc=utc(),job_id=jid,status='COLLECTION_COMPLETE',entry_wall_seconds=time.perf_counter()-entry,
        complete_requests=512,online_ProbeMax=256,scientific_analysis_performed=False))
except BaseException as exc:
    path=P/'records/four_arm_requests.jsonl';completed=[]
    if path.exists():
        for line in path.read_text().splitlines():
            try:completed.append(json.loads(line)['key'])
            except json.JSONDecodeError:pass
    save(P/'JOB_FAILURE.json',dict(utc=utc(),job_id=jid,phase=phase,error=repr(exc),traceback=traceback.format_exc(),
        status='PARTIAL_MMLU_PRO_STAGE2' if completed else 'BLOCKED_MMLU_PRO_STAGE2',successful_count=len(completed),successful_keys=completed,
        resubmit_allowed=False,second_PBS_forbidden=True))
    raise
