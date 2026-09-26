from common import *
import resource,subprocess,sys,math,fcntl
compute();lock=(P/'evidence/execution.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
job=read(P/'evidence/pbs/allocation.json')['scheduler']['Jobs'][os.environ['PBS_JOBID']]
stime=float(os.environ['R1E3_REPLAY_START_EPOCH']);deadline=stime+1800-60;os.environ['P2_DEADLINE_EPOCH']=str(deadline)  # E3: this replay's own start (original: PBS stime)
reserve=180;rec={'job_id':os.environ['PBS_JOBID'],'start_utc':utc(),'phases':[],'status':'RUNNING','CPU_seconds':0,'preparation_reporting_reserve':reserve,'CPU_cap':1500}
def used():
 a=resource.getrusage(resource.RUSAGE_SELF);b=resource.getrusage(resource.RUSAGE_CHILDREN);return a.ru_utime+a.ru_stime+b.ru_utime+b.ru_stime
def record(status,child=0):
 rec.update(status=status,CPU_seconds=used()+child,utc=utc());save(P/'evidence/CPU_runs.json',rec)
 save(P/'PROGRESS.json',{'phase':status,'job_id':rec['job_id'],'CPU_charged':reserve+rec['CPU_seconds'],'CPU_remaining':max(0,1500-reserve-rec['CPU_seconds']),'wall_remaining':max(0,deadline-time.time()),'replay_progress':read(P/'REPLAY_PROGRESS.json') if (P/'REPLAY_PROGRESS.json').exists() else None,'utc':utc()})
phases=[['validate_sources.py'],['execute.py']]  # E3: records only; original analyze.py/render.py run later on the login node
try:
 for args in phases:
  stop();budget=math.floor(1500-reserve-used()-15);assert budget>20
  def limits():resource.setrlimit(resource.RLIMIT_CPU,(budget,budget+1))
  env=os.environ.copy()
  if args[0]!='execute.py':env['CUDA_VISIBLE_DEVICES']=''
  name='_'.join(args);log=Path(os.environ['P2_RUN'])/(name+'.log');phase={'args':args,'log':str(log),'started_utc':utc(),'CPU_limit':budget};rec['phases'].append(phase)
  before=used();t=time.time()
  with log.open('w') as out:
   proc=subprocess.Popen([sys.executable,'-u',str(P/'src'/args[0]),*args[1:]],stdout=out,stderr=subprocess.STDOUT,cwd=P,env=env,preexec_fn=limits)
   while proc.poll() is None:
    try:
     s=Path(f'/proc/{proc.pid}/stat').read_text().rsplit(')',1)[1].split();cpu=(int(s[11])+int(s[12]))/os.sysconf('SC_CLK_TCK')
     if reserve+used()+cpu>1485 or time.time()>deadline:
      (P/'STOP_BUDGET').write_text('Preserve successful IDs; no second job.\n');proc.terminate()
     record(name,cpu)
    except FileNotFoundError:pass
    time.sleep(2)
  phase.update(exit_code=proc.returncode,CPU_seconds=used()-before,wall_seconds=time.time()-t,ended_utc=utc());record('FINISHED_'+name)
  if proc.returncode:raise RuntimeError(f'Phase failed {name} exit={proc.returncode}; no automatic retry')
 record('NUMERICAL_COMPLETE');save(P/'EXECUTION_COMPLETE.json',{'utc':utc(),'job_id':rec['job_id'],'complete_action_requests':1024,'online_policy_probes':512,'paired_evaluations':512,'CPU_with_reserve':reserve+used()})
except BaseException as e:
 rec['error']=repr(e);record('PARTIAL');raise
finally:record(rec['status'])
