"""Prepared supervisor. Requires documented permission for the actual execution host."""
import os,sys,json,socket,resource,subprocess,datetime
from pathlib import Path
O=Path(__file__).resolve().parent
clear=O/'execution_clearance.json'
if not clear.exists():raise SystemExit('NOT STARTED: actual-node execution eligibility has not been established; see evidence/node_policy.json')
c=json.loads(clear.read_text())
assert c.get('allowed') is True and c.get('host')==socket.gethostname() and c.get('stage')==O.name and c.get('evidence'), 'Clearance must identify this host, stage, and governing evidence'
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1';os.environ['P2_BOUNDED_SUPERVISED']=O.name
os.environ['TMPDIR']=str(O/'tmp');(O/'tmp').mkdir(exist_ok=True)
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
if os.getpriority(os.PRIO_PROCESS,0)<10:os.nice(10-os.getpriority(os.PRIO_PROCESS,0))
ledger=O/'evidence/CPU_runs.json';runs=json.loads(ledger.read_text()) if ledger.exists() else []
prep=json.loads((O/'evidence/preparation_resources.json').read_text())['cpu_seconds']
remaining=int(3600-30-prep-sum(r['cpu_seconds'] for r in runs))
if remaining<=5:raise SystemExit('PARTIAL: CPU budget exhausted; preserve existing heads/folds')
def limits():
    resource.setrlimit(resource.RLIMIT_AS,(3584*1024*1024,3584*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(remaining-1,remaining))
print(json.dumps({'model':'only saved LR/Ridge bundles; no LLM/tokenizer','data':'frozen source manifest','cache':os.environ.get('XDG_CACHE_HOME'),
    'output':str(O),'checkpoint':str(O/'oof'),'log':str(ledger),'temp':os.environ['TMPDIR'],'CPU_remaining':remaining,'threads':1,'nice':10}),flush=True)
p=subprocess.run([sys.executable,str(O/'fit_stage.py')],cwd=O,preexec_fn=limits)
ru=resource.getrusage(resource.RUSAGE_CHILDREN)
runs.append({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cpu_seconds':ru.ru_utime+ru.ru_stime,'peak_RSS_KiB':ru.ru_maxrss,
    'exit_code':p.returncode,'host':socket.gethostname(),'threads':1,'nice':10,'reserved_unmetered_seconds':30})
ledger.write_text(json.dumps(runs,indent=2)+'\n');sys.exit(p.returncode)
