"""CPU 监控现有唯一作业，终止后执行已冻结分析；没有 submit-job 调用。"""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from common import *
import subprocess,fcntl
lock=(P/'evidence/supervisor.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
os.environ['CUDA_VISIBLE_DEVICES']='';print('CPU_SUPERVISOR_PATHS',json.dumps(resolved_paths()),flush=True)
failures=0
while True:
    proc=subprocess.run([sys.executable,str(P/'monitor_resources.py')],capture_output=True,text=True)
    if proc.returncode:
        failures+=1;append(P/'evidence/monitor_errors.jsonl',dict(utc=utc(),stderr=proc.stderr,returncode=proc.returncode))
        print('MONITOR_TRANSPORT_ERROR',utc(),failures,flush=True)
        if failures>=10:raise RuntimeError('Repeated scheduler read failure; no resubmission')
    else:
        failures=0
        with (P/'evidence/monitor_history.jsonl').open('a') as f:f.write(proc.stdout)
        rec=json.loads(proc.stdout);print('RESOURCE_PROGRESS',json.dumps(rec),flush=True)
        if rec['state']=='F':break
    time.sleep(50)
if (P/'REPLAY_COMPLETE.json').exists() and (P/'JOB_WORK_COMPLETE.json').exists():
    for name in ['src/analyze.py','validate_results_cpu.py']:
        print('START_CPU_POSTRUN',name,utc(),flush=True)
        log=P/'evidence'/('analysis_cpu.log' if name.startswith('src/') else 'validation_cpu.log')
        with log.open('w') as out:proc=subprocess.run([str(PYTHON),str(P/name)],stdout=out,stderr=subprocess.STDOUT,env=os.environ.copy())
        if proc.returncode:
            save(P/'evidence/POSTRUN_FAILURE.json',dict(utc=utc(),phase=name,returncode=proc.returncode,log=str(log)))
            raise RuntimeError('CPU postrun validation failed; inspect without new model requests')
subprocess.run([sys.executable,str(P/'finalize_reports.py')],check=True)
print('STAGE2_RETURN_TO_WORK_NO_NEXT_TASK',utc(),flush=True)
