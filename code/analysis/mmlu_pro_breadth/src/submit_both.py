"""仅两次 held 提交；两份收据确认后统一放行，绝不自动重试提交。"""
from common import *
import subprocess,re,fcntl
validate_freeze()
lock=(P/'evidence/pbs/submission.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
attempt=P/'evidence/pbs/SUBMISSION_ATTEMPT.json'
assert not attempt.exists(),'No automatic retry/replacement submission'
save(attempt,dict(utc=utc(),maximum_submissions=2,hold=True))
jobs={}
for i in [1,2]:
    script=P/f'run_shard{i}.pbs'
    append(P/'evidence/pbs/submission_events.jsonl',dict(utc=utc(),event='SUBMIT_BEGIN',shard=i,script_sha256=sha(script)))
    proc=subprocess.run([str(Path.home()/'bin/submit-job'),str(script),'-h'],capture_output=True,text=True,timeout=90)
    save(P/f'evidence/pbs/submission_{i}.json',dict(utc=utc(),shard=i,returncode=proc.returncode,stdout=proc.stdout,stderr=proc.stderr,script_sha256=sha(script)))
    assert proc.returncode==0,'Submission failed; no automatic retry'
    matches=re.findall(r'^([0-9]+\.[A-Za-z0-9_.-]+)\s*$',proc.stdout,re.M)
    assert len(matches)==1,'Ambiguous submission receipt; do not retry'
    jid=matches[0]
    rec=json.loads(subprocess.check_output(['job-status','-f','-F','json',jid],text=True,timeout=30))
    j=rec['Jobs'][jid];j.pop('Variable_List',None)
    save(P/f'evidence/pbs/held_{i}.json',rec)
    assert j['job_state']=='H' and j['Resource_List']['walltime']=='14:00:00'
    jobs[str(i)]=dict(job_id=jid,submission_utc=utc(),held_receipt_sha256=sha(P/f'evidence/pbs/held_{i}.json'),PBS_script_sha256=sha(script))
    save(P/'evidence/pbs/submitted_jobs.json',jobs)
assert len(jobs)==2 and not any((P/'shards').glob('*/OUTCOMES_OBSERVED.json'))
save(P/'BOTH_SUBMISSIONS_CONFIRMED.json',dict(utc=utc(),jobs=jobs,protocol_freeze_sha256=sha(P/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json'),MMLU_PRO_OUTCOMES_OBSERVED=False))
proc=subprocess.run(['qrls',*[j['job_id'] for j in jobs.values()]],capture_output=True,text=True,timeout=30)
save(P/'evidence/pbs/release.json',dict(utc=utc(),returncode=proc.returncode,stdout=proc.stdout,stderr=proc.stderr,jobs=jobs))
assert proc.returncode==0,'Release failed: investigate held jobs; do not resubmit'
print(json.dumps(dict(status='BOTH_JOBS_SUBMITTED_AND_RELEASED',jobs=jobs),ensure_ascii=False),flush=True)
