"""只读调度器/完成计数/机械失败，不读模型输出或科学统计。"""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from common import *
import subprocess
barrier=read(P/'BOTH_SUBMISSIONS_CONFIRMED.json');jobs={};display=[]
for shard,spec in barrier['jobs'].items():
    jid=spec['job_id']
    cached=P/f'evidence/pbs/latest_{shard}.json'
    old=read(cached) if cached.exists() else {}
    if old.get('job_state')=='F':j=old
    else:
        proc=subprocess.run(['job-status','-xf','-F','json',jid],capture_output=True,text=True,timeout=30)
        if proc.returncode:raise RuntimeError(proc.stderr)
        j=json.loads(proc.stdout)['Jobs'][jid];j.pop('Variable_List',None)
    save(P/f'evidence/pbs/latest_{shard}.json',j)
    progress=read(P/f'shards/{shard}/PROGRESS.json') if (P/f'shards/{shard}/PROGRESS.json').exists() else None
    failure=read(P/f'shards/{shard}/JOB_FAILURE.json') if (P/f'shards/{shard}/JOB_FAILURE.json').exists() else None
    # Only scheduler timing / allocation / completion fields enter this output.
    rec=dict(shard=shard,job_id=jid,job_state=j['job_state'],submission_utc=spec['submission_utc'],
        qtime=j.get('qtime'),start=j.get('stime'),end=j.get('obittime'),terminal_exit_status=j.get('Exit_status'),
        allocation_GPUs=int(j['Resource_List'].get('ngpus',2)),walltime_requested=j['Resource_List']['walltime'],
        resources_used=j.get('resources_used'),progress=progress,failure=failure)
    if j.get('stime') and j.get('obittime'):
        def epoch(s):return datetime.datetime.strptime(s,'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp()
        rec['actual_allocation_seconds']=epoch(j['obittime'])-epoch(j['stime'])
        rec['actual_GPUh']=rec['actual_allocation_seconds']*rec['allocation_GPUs']/3600
    jobs[shard]=rec
    display.append(dict(shard=shard,job_id=jid,state=j['job_state'],start=rec['start'],end=rec['end'],
        exit_status=rec['terminal_exit_status'],progress=progress,failure=failure))
all_terminal=all(j['job_state']=='F' for j in jobs.values())
ledger=dict(utc=utc(),task='P2_MMLU_PRO_BREADTH_STAGE1',authorized_max_GPUh=56,formal_submissions=2,
    third_submission_allowed=False,E2E_submissions=0,jobs=jobs,both_terminal=all_terminal,
    actual_GPUh=sum(j.get('actual_GPUh',0) for j in jobs.values()) if all_terminal else None,
    scientific_outputs_read_by_monitor=False)
save(P/'RESOURCE_LEDGER.json',ledger)
if all_terminal:save(P/'evidence/pbs/TERMINAL_RECEIPTS.json',dict(utc=utc(),jobs=jobs))
print(json.dumps(dict(utc=utc(),both_terminal=all_terminal,jobs=display),ensure_ascii=False),flush=True)
