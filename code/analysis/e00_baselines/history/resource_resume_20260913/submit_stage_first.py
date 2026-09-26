"""One deliberate submit-job call, preceded and followed by own-job deduplication."""
import os,subprocess,json,re,time,datetime
from pathlib import Path
O=Path(__file__).resolve().parent
E=O/'evidence/pbs'
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def own():
 q=subprocess.run(['qselect','-u',os.environ['USER']],capture_output=True,text=True)
 assert q.returncode in [0,153],q.stderr
 ids=q.stdout.split()
 if not ids:return {}
 raw=json.loads(subprocess.check_output(['job-status','-f','-F','json',*ids],text=True))['Jobs']
 keys=['Job_Name','Job_Owner','job_state','queue','Account_Name','Resource_List','qtime','stime','comment','Submit_arguments','exec_host','exec_vnode','session_id','resources_used','Output_Path','Error_Path']
 return {k:{f:v[f] for f in keys if f in v} for k,v in raw.items()}
jobs=own();save(E/'own_jobs_before_submit.json',{'observed_epoch':time.time(),'Jobs':jobs})
matching={i:j for i,j in jobs.items() if O.name in j.get('Submit_arguments','') or j['Job_Name']=='p2_v2_ffr_e0'}
assert not matching,('Stage already in flight',list(matching))
assert not (E/'submissions.json').exists(),'Existing submission ledger: inspect; never resubmit automatically'
queued=sum(j['Account_Name']=='project' for j in jobs.values())
assert queued<20,('Explicit own-account queued/running limit conflict',queued)
start=time.time();cmd=[str(Path.home()/'bin/submit-job'),str(O/'run_p2_v2_ffr_e0.pbs')]
save(E/'submission_attempt.json',{'started_epoch':start,'command':cmd,'requested_walltime_seconds':5400,'result':'PENDING; query scheduler if interrupted'})
try:
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
 result={'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'ended_epoch':time.time()}
except subprocess.TimeoutExpired as e:
 result={'returncode':None,'stdout':str(e.stdout),'stderr':str(e.stderr),'ended_epoch':time.time(),'ambiguous':True}
save(E/'submission_result.json',result)
found=re.findall(r'^\d+\.ClusterB-pbs[^\s]*$',result['stdout'],re.M)
after=own();save(E/'own_jobs_after_submit.json',{'observed_epoch':time.time(),'Jobs':after})
if not found:found=[i for i,j in after.items() if O.name in j.get('Submit_arguments','') or j['Job_Name']=='p2_v2_ffr_e0']
assert len(found)==1,('Submission unconfirmed; do not repeat',result)
jid=found[0];j=after[jid]
save(E/'submissions.json',[{'job_id':jid,'ordinal':1,'submitted_epoch':start,'requested_walltime_seconds':5400,'script':str(O/'run_p2_v2_ffr_e0.pbs'),'state_on_confirmation':j['job_state']}])
save(O/'PROGRESS.json',{'status':'PBS_'+j['job_state'],'task_complete':False,'job_id':jid,'baseline_C_heads_completed':0,'OOF_heads_completed':0,'LR_attempts':0,'CPU_budget_charged_seconds':91.608204,'remaining_work':'PBS start, formal fitting, metrics and validation, report and manuscript results','scheduler_comment':j.get('comment')})
print(json.dumps({'job_id':jid,'state':j['job_state'],'comment':j.get('comment'),'Resource_List':j['Resource_List'],'submission_stdout':result['stdout']},ensure_ascii=False,indent=2))
