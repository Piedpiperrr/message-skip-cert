"""One-thread/nice CPU ledger; no subprocess may escape the total stage limit."""
import os,sys,json,time,resource,subprocess,datetime
from pathlib import Path
O=Path(__file__).resolve().parent
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:
    os.environ[k]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['TMPDIR']=str(O/'tmp'); (O/'tmp').mkdir(exist_ok=True)
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
if os.getpriority(os.PRIO_PROCESS,0)<10:os.nice(10-os.getpriority(os.PRIO_PROCESS,0))
ledger=O/'evidence/resource_ledger.json'
d=json.loads(ledger.read_text()) if ledger.exists() else {'preparation_and_unmetered_cpu_reserved_seconds':30,'limit_cpu_seconds':600,'runs':[]}
used=d['preparation_and_unmetered_cpu_reserved_seconds']+sum(r['cpu_seconds'] for r in d['runs'])
if used>=590:raise SystemExit('CPU budget reserved for finalization; no new analysis allowed')
limit=min(240,int(595-used))
def cap():
    resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(limit,limit+1))
print(json.dumps({'model':'NOT_LOADED','tokenizer':'NOT_LOADED','dataset':'registered P2-10 train/dev/validation only',
    'cache':{k:os.environ.get(k) for k in ['HF_HOME','XDG_CACHE_HOME']},'output':str(O),'checkpoints':'NONE','log':str(ledger),
    'temporary':os.environ['TMPDIR'],'nice':os.getpriority(os.PRIO_PROCESS,0),'affinity':list(os.sched_getaffinity(0)),'cpu_budget_remaining':600-used}),flush=True)
for p in [str(O),os.environ['TMPDIR'],*filter(None,[os.environ.get('HF_HOME'),os.environ.get('XDG_CACHE_HOME')])]:
    if p.startswith('$HOME_DIR'):raise SystemExit('growing path under Home')
t=time.monotonic(); b=resource.getrusage(resource.RUSAGE_CHILDREN)
p=subprocess.run([sys.executable,*sys.argv[1:]],cwd=O,preexec_fn=cap)
a=resource.getrusage(resource.RUSAGE_CHILDREN)
d['runs'].append({'command':sys.argv[1:],'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'cpu_seconds':a.ru_utime+a.ru_stime-b.ru_utime-b.ru_stime,'wall_seconds':time.monotonic()-t,'max_rss_kib':a.ru_maxrss,
    'exit_code':p.returncode,'nice':10,'threads':1,'cpu_hard_limit_seconds':limit+1,'address_space_limit_mib':768})
ledger.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(d['runs'][-1]),flush=True)
sys.exit(p.returncode)
