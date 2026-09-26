from common import *
import subprocess,socket,traceback,fcntl,resource
from guard_checks import allocation_identity,legacy_cgroup_pattern_match
raw=Path('/proc/self/cgroup').read_text()
(P/'evidence/cgroup_raw.txt').write_text(raw)
jid=os.environ.get('PBS_JOBID','');host=socket.gethostname()
save(P/'evidence/CGROUP_RECEIPT.json',dict(cgroup_raw=raw,utc=utc(),job_id=jid,host=host,
    legacy_cgroup_pattern_match=legacy_cgroup_pattern_match(raw,jid),legacy_match_is_fatal=False))
phase='SCHEDULER_GUARD';start=time.perf_counter()
try:
    lock=(P/'evidence/execution.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    response=json.loads(subprocess.check_output(['job-status','-f','-F','json',jid],text=True,timeout=30))
    assert list(response['Jobs'])==[jid]
    job=response['Jobs'][jid];job.pop('Variable_List',None)
    allocation=allocation_identity(job,host,Path(os.environ['PBS_NODEFILE']).read_text().split())
    save(P/'evidence/pbs/allocation.json',response)
    save(P/'evidence/ALLOCATION_GUARD.json',dict(**allocation,job_id=jid,host=host,utc=utc()))
    assert allocation['status']=='PASS',allocation
    stime=datetime.datetime.strptime(job['stime'],'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp()
    deadline=stime+allocation['walltime_seconds']-45
    os.environ['P2_MEDIUM_DEADLINE']=str(deadline)
    save(P/'evidence/DEADLINE.json',dict(PBS_stime=job['stime'],requested_walltime_seconds=allocation['walltime_seconds'],
        safety_seconds=45,deadline_epoch=deadline,max_GPU_allocation_hours=2*allocation['walltime_seconds']/3600))
    phase='FREEZE_AND_ASSET_RECHECK';verify_freeze(include_weights=True);stop_check()
    print('RESOLVED_PATHS',json.dumps(paths()),flush=True)
    phase='CUDA_GUARD'
    import torch
    available=torch.cuda.is_available();count=torch.cuda.device_count();devices=[]
    for i in range(count):
        prop=torch.cuda.get_device_properties(i)
        devices.append(dict(index=i,name=prop.name,uuid=str(getattr(prop,'uuid',None)),total_memory_bytes=prop.total_memory))
    save(P/'evidence/CUDA_RECEIPT.json',dict(utc=utc(),CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
        cuda_available=available,device_count=count,devices=devices))
    assert available and count==2,'PBS/process GPU visibility mismatch'
    phase='STRICT_LOADING_AND_FORMAL_REPLAY'
    from execute import main
    main()
    save(P/'JOB_WORK_COMPLETE.json',dict(status='COMPLETE_MEDIUM_STAGE2',utc=utc(),job_id=jid,
        entry_wall_seconds=time.perf_counter()-start,cpu_process_seconds=time.process_time(),
        success_counts=read(P/'REPLAY_COMPLETE.json')))
except BaseException as error:
    completed=rows(P/'records/e2e_requests.jsonl') if (P/'records/e2e_requests.jsonl').exists() else []
    save(P/'JOB_FAILURE.json',dict(utc=utc(),job_id=jid,phase=phase,error=repr(error),traceback=traceback.format_exc(),
        status='PARTIAL_MEDIUM_STAGE2' if completed else 'BLOCKED_MEDIUM_STAGE2',
        successful_count=len(completed),successful_keys=[r['key'] for r in completed],resubmit_allowed=False))
    raise
