"""只读单个正式作业的调度、完成计数与运行失败；不读科学结果。"""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from common import *
import subprocess
submission=read(P/'evidence/pbs/submission.json');jid=submission['job_id'];cache=P/'evidence/pbs/latest.json'
old=read(cache) if cache.exists() else {}
if old.get('job_state')=='F':j=old
else:
    proc=subprocess.run(['job-status','-xf','-F','json',jid],capture_output=True,text=True,timeout=30)
    if proc.returncode:raise RuntimeError(proc.stderr)
    j=json.loads(proc.stdout)['Jobs'][jid];j.pop('Variable_List',None);save(cache,j)
progress=read(P/'REPLAY_PROGRESS.json') if (P/'REPLAY_PROGRESS.json').exists() else None
failure=read(P/'JOB_FAILURE.json') if (P/'JOB_FAILURE.json').exists() else None
ledger=dict(utc=utc(),job_id=jid,job_state=j['job_state'],submission_utc=submission['utc'],qtime=j.get('qtime'),start=j.get('stime'),end=j.get('obittime'),
    exit_status=j.get('Exit_status'),allocated_GPUs=int(j['Resource_List'].get('ngpus',2)),walltime_requested=j['Resource_List']['walltime'],
    actual_GPUh=None,max_GPUh=2,formal_PBS_submissions=1,max_formal_PBS_jobs=1,second_submission_allowed=False,resources_used=j.get('resources_used'),
    progress=progress,failure=failure,scientific_results_read_by_monitor=False)
if j.get('stime') and j.get('obittime'):
    def epoch(s):return datetime.datetime.strptime(s,'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp()
    ledger['actual_allocation_seconds']=epoch(j['obittime'])-epoch(j['stime']);ledger['actual_GPUh']=ledger['actual_allocation_seconds']*ledger['allocated_GPUs']/3600
elif j['job_state']=='F':ledger['actual_allocation_seconds']=0;ledger['actual_GPUh']=0.
save(P/'RESOURCE_LEDGER.json',ledger)
if j['job_state']=='F':save(P/'evidence/pbs/TERMINAL_RECEIPT.json',dict(utc=utc(),job_id=jid,scheduler=j))
print(json.dumps(dict(utc=utc(),job_id=jid,state=j['job_state'],start=ledger['start'],end=ledger['end'],exit_status=ledger['exit_status'],
    complete_requests=(progress or {}).get('complete_requests',0),complete_questions=(progress or {}).get('complete_questions',0),
    online_probes=(progress or {}).get('online_probe_attempts',0),ETA_remaining_seconds=(progress or {}).get('ETA_remaining_seconds'),failure=failure),ensure_ascii=False),flush=True)
