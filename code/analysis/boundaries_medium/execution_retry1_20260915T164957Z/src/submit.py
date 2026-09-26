"""Work授权的一次replacement；提交收据不确定也绝不重提。"""
from common import *
import subprocess,re,fcntl
pre=read(P/'MEDIUM_PAIR_EXECUTION_PRECHECK_RETRY1.json');assert pre['status']=='PASS'
validate_parent()
for f,h in pre['frozen_files'].items():assert sha(f)==h,f
e=P/'evidence/pbs';lock=(e/'submit.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert not (e/'submission_attempt.json').exists(),'Only one replacement submission attempt; never retry ambiguous receipt'
selected=subprocess.run(['qselect','-u','user'],capture_output=True,text=True,timeout=30)
assert selected.returncode==0,selected.stderr
live={}
for selected_id in selected.stdout.split():
    query=subprocess.run(['job-status','-xf','-F','json',selected_id],capture_output=True,text=True,timeout=30)
    if query.returncode!=0 and 'Unknown Job Id' in query.stderr:continue
    assert query.returncode==0,query.stderr
    queue=json.loads(query.stdout)
    for k,v in queue.get('Jobs',{}).items():
        live[k]={a:v.get(a) for a in ['Job_Name','Job_Owner','job_state','queue','Submit_arguments']}
save(e/'pre_submission_queue.json',{'utc':utc(),'live_user_jobs':live})
assert not any(v['job_state']!='F' and (str(v['Job_Name']).startswith('p2_medium') or str(PARENT) in str(v['Submit_arguments'])) for v in live.values()),'A same-task job is already live'
command=[str(Path.home()/'bin/submit-job'),str(P/'run_medium_stage1.pbs')]
save(e/'submission_attempt.json',{'utc':utc(),'command':command,'precheck_sha256':sha(P/'MEDIUM_PAIR_EXECUTION_PRECHECK_RETRY1.json'),
    'retry_authorization_sha256':sha(P/'MEDIUM_PAIR_RETRY_AUTHORIZATION.json'),'status':'ATTEMPTED; ambiguous receipt must not be retried',
    'walltime':'03:29:50','GPU_count':2,'attempt_number':2,'no_third_submission':True})
proc=subprocess.run(command,capture_output=True,text=True,timeout=55)
save(e/'submission_result.json',{'utc':utc(),'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr})
print(proc.stdout,proc.stderr,flush=True)
jobs=re.findall(r'^\d+\.ClusterB-pbs[^\s]*$',proc.stdout,re.M)
assert proc.returncode==0 and len(jobs)==1
jid=jobs[0];save(e/'submission.json',{'job_id':jid,'utc':utc(),'walltime':'03:29:50','GPU_count':2,'attempt_number':2})
rec=json.loads(subprocess.check_output(['job-status','-xf','-F','json',jid],text=True,timeout=30));rec['Jobs'][jid].pop('Variable_List',None)
save(e/'submission_confirmed.json',rec)
ledger=read(P/'RESOURCE_LEDGER.json');ledger.update(status='SUBMITTED',utc=utc())
ledger['replacement_attempt'].update(formal_submissions=1,job_id=jid,actual_GPU_allocation_hours=None)
save(P/'RESOURCE_LEDGER.json',ledger)
session=read(P/'SESSION_RESUME_ZH.json');session.update(phase='SUBMITTED',job_id=jid,formal_submissions_this_attempt=1,total_submissions=2,utc=utc())
save(P/'SESSION_RESUME_ZH.json',session)
print('REPLACEMENT_SUBMISSION_CONFIRMED',jid,rec['Jobs'][jid]['job_state'],flush=True)
