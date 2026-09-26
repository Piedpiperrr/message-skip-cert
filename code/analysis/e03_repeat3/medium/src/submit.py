"""Exactly one submit-job call; no retries even if the submission receipt is ambiguous."""
from common import *
import subprocess,fcntl,re
cfg=verify_freeze(include_weights=False)
e=P/'evidence/pbs';lock=(e/'submit.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert not (e/'submission_attempt.json').exists(),'ONE SUBMISSION ONLY'
q=subprocess.run(['qselect','-u','user'],capture_output=True,text=True,timeout=30)
assert q.returncode==0,q.stderr
live={}
for jid in q.stdout.split():
    r=subprocess.run(['job-status','-xf','-F','json',jid],capture_output=True,text=True,timeout=30)
    if r.returncode and 'Unknown Job Id' in r.stderr:continue
    assert r.returncode==0,r.stderr
    for k,v in json.loads(r.stdout)['Jobs'].items():
        live[k]={a:v.get(a) for a in ['job_state','Job_Name','Submit_arguments']}
save(e/'pre_submission_queue.json',dict(utc=utc(),live_user_jobs=live))
assert not any(v['job_state']!='F' and ('medium' in str(v['Job_Name']).lower() or str(P) in str(v['Submit_arguments'])) for v in live.values())
command=[str(Path.home()/'bin/submit-job'),str(P/'run_medium_stage2.pbs')]
save(e/'submission_attempt.json',dict(utc=utc(),command=command,freeze_sha256=sha(FREEZE),max_submissions=1,
    status='ATTEMPTED; do not retry ambiguous receipt',walltime_seconds=900,GPUs=2))
r=subprocess.run(command,capture_output=True,text=True,timeout=55)
save(e/'submission_result.json',dict(utc=utc(),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
print(r.stdout,r.stderr,flush=True)
jobs=re.findall(r'^\d+\.ClusterB-pbs[^\s]*$',r.stdout,re.M)
assert r.returncode==0 and len(jobs)==1
jid=jobs[0];save(e/'submission.json',dict(utc=utc(),job_id=jid,GPUs=2,walltime_seconds=900))
ledger=read(P/'RESOURCE_LEDGER.json');ledger.update(status='SUBMITTED',submissions=1,job_id=jid,submitted_utc=utc())
save(P/'RESOURCE_LEDGER.json',ledger)
r=subprocess.run(['job-status','-xf','-F','json',jid],capture_output=True,text=True,timeout=30)
if r.returncode==0:
    rec=json.loads(r.stdout)
    for j in rec['Jobs'].values():j.pop('Variable_List',None)
    save(e/'submission_confirmed.json',rec)
print('SUBMITTED',jid,flush=True)
