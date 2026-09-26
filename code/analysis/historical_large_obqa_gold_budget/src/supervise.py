from common import *
import resource,subprocess,sys,math,fcntl
compute();lock=(P/'evidence/execution.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
job=read(P/'evidence/pbs/allocation.json')['scheduler']['Jobs'][os.environ['PBS_JOBID']];stime=datetime.datetime.strptime(job['stime'],'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc).timestamp();deadline=stime+600-30;os.environ['P2_DEADLINE_EPOCH']=str(deadline)
reserve=30;cap=300;rec={'job_id':os.environ['PBS_JOBID'],'start_utc':utc(),'phases':[],'status':'RUNNING','CPU_seconds':0,'preparation_reporting_reserve':reserve,'CPU_cap':cap}
def used():
 a=resource.getrusage(resource.RUSAGE_SELF);b=resource.getrusage(resource.RUSAGE_CHILDREN);return a.ru_utime+a.ru_stime+b.ru_utime+b.ru_stime
def record(status,child=0):
 rec.update(status=status,CPU_seconds=used()+child,utc=utc());save(P/'evidence/CPU_runs.json',rec)
 save(P/'PROGRESS.json',{'phase':status,'job_id':rec['job_id'],'CPU_charged':reserve+rec['CPU_seconds'],'CPU_remaining':max(0,cap-reserve-rec['CPU_seconds']),'wall_remaining':max(0,deadline-time.time()),'completed_models':[p.stem.replace('_receipt','') for p in (P/'models').glob('*_receipt.json')],'utc':utc()})
phases=[('prepare_labels.py','LABEL_INTERFACES_FREEZE.json'),('fit_models.py','MODELS_FREEZE.json'),('fit_thresholds.py','THRESHOLDS_FREEZE.json'),('calibrate.py','DEPLOYMENT_FREEZE.json'),('score_dev.py','DEV_ROUTES_FREEZE.json'),('analyze.py','ANALYSIS_COMPLETE.json'),('plot.py','FIGURES_COMPLETE.json')]
try:
 for name,done in phases:
  if (P/done).exists():continue
  attempt=0
  while True:
   stop();budget=math.floor(cap-reserve-used()-10);assert budget>15;attempt+=1
   def limits():resource.setrlimit(resource.RLIMIT_CPU,(budget,budget+1))
   env=os.environ.copy();env['CUDA_VISIBLE_DEVICES']='';log=Path(os.environ['P2_RUN'])/(name+f'.{attempt}.log');phase={'script':name,'attempt':attempt,'log':str(log),'started_utc':utc(),'CPU_limit':budget};rec['phases'].append(phase)
   before=used();t=time.time()
   with log.open('w') as out:
    proc=subprocess.Popen([sys.executable,'-u',str(P/'src'/name)],stdout=out,stderr=subprocess.STDOUT,cwd=P,env=env,preexec_fn=limits)
    while proc.poll() is None:
     try:
      s=Path(f'/proc/{proc.pid}/stat').read_text().rsplit(')',1)[1].split();cpu=(int(s[11])+int(s[12]))/os.sysconf('SC_CLK_TCK')
      if reserve+used()+cpu>cap-10 or time.time()>deadline:(P/'STOP_BUDGET').write_text('Preserve successful configurations; no second job.\n');proc.terminate()
      record(name,cpu)
     except FileNotFoundError:pass
     time.sleep(2)
   phase.update(exit_code=proc.returncode,CPU_seconds=used()-before,wall_seconds=time.time()-t,ended_utc=utc());record('FINISHED_'+name)
   if proc.returncode==0:break
   # Only a recorded necessary repair, inside this single allocation, may resume.
   request=P/'REPAIR_REQUEST.json';wait_until=min(deadline,time.time()+60);record('ERROR_WAITING_REPAIR_'+name)
   while time.time()<wait_until and not request.exists():time.sleep(2)
   if not request.exists():raise RuntimeError(f'{name} exit {proc.returncode}; no repair; preserve PARTIAL')
   repair=read(request);assert repair['job_id']==rec['job_id'] and repair['script']==name and repair['reason'];request.replace(P/f'evidence/repair_{len(rec["phases"])}.json')
 record('NUMERICAL_COMPLETE');save(P/'EXECUTION_COMPLETE.json',{'utc':utc(),'job_id':rec['job_id'],'models':15,'actual_LR_fits':read(P/'MODELS_FREEZE.json')['actual_LR_fits'],'constant_fallbacks':read(P/'MODELS_FREEZE.json')['constant_fallbacks'],'new_calibration_tests':300,'distinct_model_grid_items':340,'new_dev_evaluations':11130,'GPU_compute':0,'prefills':0,'CPU_with_reserve':reserve+used()})
except BaseException as e:rec['error']=repr(e);record('PARTIAL');raise
finally:record(rec['status'])
