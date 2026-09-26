"""Resumable PBS supervisor: numerical phases share the original CPU ledger."""
import os,sys,json,socket,resource,subprocess,datetime,time,math,fcntl
from pathlib import Path
O=Path(__file__).resolve().parent
def save(p,x):
 p=Path(p);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
c=json.loads((O/'execution_clearance.json').read_text())
assert c.get('allowed') is True and c.get('host')==socket.gethostname() and c.get('stage')==O.name and c.get('evidence')
assert c['job_id']==os.environ['PBS_JOBID'] and socket.gethostname().startswith('ClusterB-gpu')
assert all(Path(p).exists() for p in c['evidence'])
lock=(O/'evidence/execution.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS','BLIS_NUM_THREADS']:os.environ[k]='1'
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['NVIDIA_VISIBLE_DEVICES']='none'
os.environ['PYTHONDONTWRITEBYTECODE']='1';os.environ['P2_BOUNDED_SUPERVISED']=O.name
assert os.environ['TMPDIR'].startswith(os.environ['DATA_ROOT']+'/tmp/')
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
if os.getpriority(os.PRIO_PROCESS,0)<10:os.nice(10-os.getpriority(os.PRIO_PROCESS,0))
ledger=O/'evidence/CPU_runs.json';runs=json.loads(ledger.read_text()) if ledger.exists() else []
historical=json.loads((O/'history/resource_resume_20260913/FINAL_RECEIPT.json').read_text())['CPU_budget_charged_seconds']
allowance=json.loads((O/'evidence/resume_preparation_allowance.json').read_text())['CPU_seconds_charged']
prior=historical+allowance+sum(r['cpu_seconds'] for r in runs)
record={'started_utc':utc(),'job_id':os.environ['PBS_JOBID'],'host':socket.gethostname(),'threads':1,'nice':10,'phases':[],'cpu_seconds':0,'peak_RSS_KiB':0,'status':'RUNNING'}
runs.append(record);start=time.monotonic()
def used():
 a=resource.getrusage(resource.RUSAGE_SELF);b=resource.getrusage(resource.RUSAGE_CHILDREN)
 return a.ru_utime+a.ru_stime+b.ru_utime+b.ru_stime
def checkpoint(status,child_cpu=0,child_rss=0):
 record.update(status=status,cpu_seconds=used()+child_cpu,peak_RSS_KiB=max(record['peak_RSS_KiB'],child_rss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss),updated_utc=utc(),wall_seconds=time.monotonic()-start)
 save(ledger,runs)
 receipts=[json.loads(s) for s in (O/'fit_receipts.jsonl').read_text().splitlines()] if (O/'fit_receipts.jsonl').exists() else []
 heads={r['key'] for r in receipts if r['event']=='HEAD_COMPLETE'}
 save(O/'PROGRESS.json',{'status':status,'task_complete':False,'job_id':record['job_id'],'host':record['host'],'baseline_C_heads_completed':sum(k.startswith('baseline/') for k in heads),'OOF_heads_completed':sum(k.startswith('OOF/') for k in heads),'LR_attempts':sum(r['event']=='START_LR' for r in receipts),'CPU_budget_charged_seconds':prior+record['cpu_seconds'],'CPU_remaining_seconds':max(0,3600-prior-record['cpu_seconds']),'updated_utc':utc()})
def phase(script,reserve):
 budget=math.floor(3600-prior-used()-reserve-5)
 if budget<5:raise RuntimeError('CPU_BUDGET_EXHAUSTED before '+script)
 def limits():
  resource.setrlimit(resource.RLIMIT_AS,(3584*1024**2,3584*1024**2))
  resource.setrlimit(resource.RLIMIT_CPU,(budget,budget+1))
 before=used();entry={'script':script,'started_utc':utc(),'CPU_limit_seconds':budget};record['phases'].append(entry)
 logfile=Path(os.environ['P2_RUN'])/(script+'.attempt'+str(len(record['phases']))+'.log');entry['log']=str(logfile)
 with logfile.open('w') as log:
  p=subprocess.Popen([sys.executable,'-u',str(O/script)],cwd=O,preexec_fn=limits,stdout=log,stderr=subprocess.STDOUT)
  entry['pid']=p.pid;last=0
  while p.poll() is None:
   try:
    fields=Path('/proc/'+str(p.pid)+'/stat').read_text().rsplit(')',1)[1].split()
    cpu=(int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK')
    rss=int(fields[21])*os.sysconf('SC_PAGE_SIZE')//1024
    if rss>4*1024**2:p.terminate();entry['stop_reason']='RSS_LIMIT'
    if time.monotonic()-last>10:checkpoint('RUNNING_'+script,cpu,rss);last=time.monotonic()
   except FileNotFoundError:pass
   time.sleep(1)
 entry.update(exit_code=p.returncode,ended_utc=utc(),CPU_seconds_including_supervision=used()-before)
 checkpoint(('PHASE_COMPLETE_' if p.returncode==0 else 'PHASE_FAILED_')+script)
 return p.returncode
try:
 checkpoint('PBS_ALLOCATION_VERIFIED')
 for script,reserve in [('fit_stage.py',180),('analyze_stage.py',60),('validate_stage.py',10)]:
  while phase(script,reserve)!=0:
   checkpoint('FAILED_AWAITING_TARGETED_FIX_'+script)
   request=O/'TARGETED_RETRY.json';deadline=time.monotonic()+900
   while time.monotonic()<deadline and not request.exists():time.sleep(5)
   if not request.exists():raise RuntimeError('TARGETED_FIX_NOT_RECEIVED: '+script)
   fix=json.loads(request.read_text());assert fix['job_id']==record['job_id'] and fix['script']==script and fix['reason']
   request.replace(O/'evidence'/('targeted_retry_'+str(len(record['phases']))+'.json'))
 checkpoint('NUMERICAL_WORK_COMPLETE_REPORT_PENDING');record['exit_code']=0
except BaseException as e:
 record['error']=repr(e);record['exit_code']=1;checkpoint('PARTIAL_EXECUTION_STOPPED');raise
finally:
 record['ended_utc']=utc();record['cpu_seconds']=used();save(ledger,runs)
