"""正式 shard 入口；仅资源检查、身份检查与采集，没有科学分析。"""
from common import *
import subprocess,socket,fcntl,traceback
from guard_checks import allocation_identity
assert SHARD in ['1','2']
S.mkdir(parents=True,exist_ok=True)
jid=os.environ.get('PBS_JOBID','');phase='SCHEDULER_ALLOCATION_GUARD'
try:
    lock=(S/'execution.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    raw=Path('/proc/self/cgroup').read_text()
    save(S/'CGROUP_RECEIPT.json',dict(utc=utc(),job_id=jid,raw=raw,pattern_match_is_fatal=False))
    paths=resolved_paths();print('RESOLVED_PATHS',json.dumps(paths),flush=True)
    rec=json.loads(subprocess.check_output(['job-status','-f','-F','json',jid],text=True,timeout=30))
    assert list(rec['Jobs'])==[jid]
    j=rec['Jobs'][jid];j.pop('Variable_List',None)
    identity=allocation_identity(j,socket.gethostname(),Path(os.environ['PBS_NODEFILE']).read_text().split())
    save(S/'PBS_ALLOCATION_RECEIPT.json',dict(utc=utc(),job_id=jid,scheduler=rec,allocation_identity=identity,paths=paths))
    assert identity['status']=='PASS',identity
    started=datetime.datetime.strptime(j['stime'],'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp()
    hard_stop=datetime.datetime(2026,9,20,0,0,tzinfo=datetime.timezone.utc).timestamp()
    deadline=min(started+identity['walltime_seconds']-90,hard_stop)
    assert started+identity['walltime_seconds']<=hard_stop,'QUEUE_CROSSES_RESEARCH_HARD_STOP'
    os.environ['MMLU_DEADLINE_EPOCH']=str(deadline)
    save(S/'DEADLINE_RECEIPT.json',dict(utc=utc(),PBS_stime=j['stime'],deadline_epoch=deadline,safety_margin_seconds=90,max_GPUh_this_job=28))
    phase='CUDA_DEVICE_GUARD'
    import torch
    n=torch.cuda.device_count();available=torch.cuda.is_available()
    receipt=dict(utc=utc(),available=available,device_count=n,CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
        devices=[dict(index=i,name=torch.cuda.get_device_properties(i).name,total_memory=torch.cuda.get_device_properties(i).total_memory) for i in range(n)])
    save(S/'CUDA_DEVICE_RECEIPT.json',receipt);assert available and n==2,receipt
    phase='FROZEN_IDENTITIES_RECHECK';validate_freeze()
    barrier=read(P/'BOTH_SUBMISSIONS_CONFIRMED.json')
    assert barrier['jobs'][SHARD]['job_id']==jid and len(barrier['jobs'])==2
    assert barrier['protocol_freeze_sha256']==sha(P/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json')
    for spec in read(P/'MODEL_SOURCE_INDEX.json')['models'].values():
        for f in spec['files']:assert sha(f['path'])==f['sha256'],f['path']
    save(S/'MODEL_HASH_RECHECK.json',dict(utc=utc(),status='PASS',model_source_index_sha256=sha(P/'MODEL_SOURCE_INDEX.json')))
    stop_check();phase='execute.py'
    log=Path(os.environ['P2_RUN'])/'execute.log'
    with log.open('w') as out:
        proc=subprocess.run([sys.executable,'-u',str(P/'src/execute.py')],stdout=out,stderr=subprocess.STDOUT,env=os.environ.copy(),cwd=P)
    if proc.returncode:raise RuntimeError(f'execute.py exit={proc.returncode}; replacement forbidden')
    save(S/'JOB_WORK_COMPLETE.json',dict(utc=utc(),job_id=jid,status='COLLECTION_COMPLETE',scientific_analysis_performed=False,log=str(log)))
except BaseException as exc:
    save(S/'JOB_FAILURE.json',dict(utc=utc(),job_id=jid,phase=phase,error=repr(exc),traceback=traceback.format_exc(),
        replacement_allowed=False,MMLU_PRO_OUTCOMES_OBSERVED=(S/'OUTCOMES_OBSERVED.json').exists()))
    raise
