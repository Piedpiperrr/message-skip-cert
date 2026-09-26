"""当前授权内的只读监控及结束后 CPU 分析；无提交、无 E2E、无论文编辑。"""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from common import *
import subprocess,fcntl
lock=(P/'evidence/supervisor.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
os.environ['CUDA_VISIBLE_DEVICES']=''
print('CPU_SUPERVISOR_PATHS',json.dumps(resolved_paths()),flush=True)
failures=0
while True:
    proc=subprocess.run([sys.executable,str(P/'monitor_resources.py')],capture_output=True,text=True)
    if proc.returncode:
        failures+=1;append(P/'evidence/monitor_errors.jsonl',dict(utc=utc(),stderr=proc.stderr,returncode=proc.returncode))
        print('MONITOR_TRANSPORT_ERROR',utc(),failures,flush=True)
        if failures>=10:raise RuntimeError('Repeated scheduler read failure; inspect without resubmission')
    else:
        failures=0
        with (P/'evidence/monitor_history.jsonl').open('a') as f:f.write(proc.stdout)
        rec=json.loads(proc.stdout);summary=[dict(shard=j['shard'],state=j['state'],
            phase=(j['progress'] or {}).get('phase'),complete_rows=(j['progress'] or {}).get('complete_rows',0),
            actions=(j['progress'] or {}).get('action_success_count',0),probes=(j['progress'] or {}).get('probe_success_count',0),
            failure=bool(j['failure'])) for j in rec['jobs']]
        print('RESOURCE_PROGRESS',rec['utc'],json.dumps(summary),flush=True)
        if rec['both_terminal']:break
    # Conservative latest launch time for an entire 14h allocation before the research stop.
    cutoff=datetime.datetime(2026,9,19,10,tzinfo=datetime.timezone.utc).timestamp()
    if time.time()>=cutoff:
        ledger=read(P/'RESOURCE_LEDGER.json')
        for shard,j in ledger['jobs'].items():
            if j['job_state'] in ['Q','H','W']:
                receipt=P/f'evidence/pbs/research_stop_cancel_{shard}.json'
                if not receipt.exists():
                    stopped=subprocess.run(['job-delete',j['job_id']],capture_output=True,text=True)
                    save(receipt,dict(utc=utc(),reason='14h requested allocation would cross 2026-09-20 00:00Z research hard stop',
                        job_id=j['job_id'],returncode=stopped.returncode,stdout=stopped.stdout,stderr=stopped.stderr))
    time.sleep(50)
if all((P/f'shards/{i}/INFERENCE_COMPLETE.json').exists() and (P/f'shards/{i}/JOB_WORK_COMPLETE.json').exists() for i in [1,2]):
    print('BOTH_TERMINAL_FULL_COLLECTION_START_CPU_ANALYSIS',utc(),flush=True)
    with (P/'evidence/analysis_cpu.log').open('w') as out:
        proc=subprocess.run([str(PYTHON),str(P/'src/analyze.py')],stdout=out,stderr=subprocess.STDOUT,env=os.environ.copy())
    if proc.returncode:
        save(P/'evidence/ANALYSIS_FAILURE.json',dict(utc=utc(),returncode=proc.returncode,log='evidence/analysis_cpu.log'))
        raise RuntimeError('CPU analysis validation failed; inspect, no new model request permitted')
subprocess.run([sys.executable,str(P/'verify_frozen_sources.py')],check=True)
subprocess.run([sys.executable,str(P/'finalize_reports.py')],check=True)
print('STAGE1_RETURN_TO_WORK_NO_E2E',utc(),flush=True)
