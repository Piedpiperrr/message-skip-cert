from common import *
import subprocess,fcntl,re
cfg=verify_freeze();e=P/'evidence/pbs';lock=(e/'submit.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert not (e/'submission_attempt.json').exists(),'EXACTLY ONE SUBMISSION; NO RETRY'
cmd=[str(Path.home()/'bin/submit-job'),str(P/'run_mmlu_stage2.pbs')]
save(e/'submission_attempt.json',dict(utc=utc(),command=cmd,freeze_sha256=sha(FREEZE),max_submissions=1,GPUs=2,walltime_seconds=3600,
    note='Do not retry ambiguous or failed submission'))
proc=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
save(e/'submission_result.json',dict(utc=utc(),returncode=proc.returncode,stdout=proc.stdout,stderr=proc.stderr));print(proc.stdout,proc.stderr,flush=True)
jj=re.findall(r'^([0-9]+\.ClusterB-pbs[^\s]*)\s*$',proc.stdout,re.M);assert proc.returncode==0 and len(jj)==1
jid=jj[0];save(e/'submission.json',dict(utc=utc(),job_id=jid,GPUs=2,walltime_seconds=3600,freeze_sha256=sha(FREEZE)))
save(P/'RESOURCE_LEDGER.json',dict(utc=utc(),status='SUBMITTED',job_id=jid,formal_PBS_submissions=1,max_formal_PBS_jobs=1,GPUs=2,max_GPUh=2,
    walltime='01:00:00',second_submission_allowed=False))
proc=subprocess.run(['job-status','-xf','-F','json',jid],capture_output=True,text=True,timeout=30)
if proc.returncode==0:
    record=json.loads(proc.stdout)
    for j in record['Jobs'].values():j.pop('Variable_List',None)
    save(e/'submission_confirmed.json',record)
print('STAGE2_SINGLE_SUBMISSION',jid,flush=True)
