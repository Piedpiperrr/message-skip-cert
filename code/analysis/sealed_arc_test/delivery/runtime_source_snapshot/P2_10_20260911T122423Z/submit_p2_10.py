"""仅P2-10；至多3个job ID、21600申请节点秒；不取消或修改任何作业。"""
import argparse,fcntl,json,os,re,subprocess
from pathlib import Path
from common_p2_10 import ROOT,sha,utc,save,append
ap=argparse.ArgumentParser();ap.add_argument('--check-only',action='store_true');args=ap.parse_args()
lock=(ROOT/'evidence/submission.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
ledger=ROOT/'evidence/submissions.json';records=json.loads(ledger.read_text())
assert not (ROOT/'evidence/uncertain_submission.json').exists(),'resolve uncertain submission before retry'
assert len(records)<3
assert sha(ROOT/'frozen_config.json')==json.loads((ROOT/'evidence/freeze_receipt.json').read_text())['config_sha256']
assert json.loads((ROOT/'evidence/implementation_checks.json').read_text())['passed']
if records:assert not all((ROOT/'results'/p/d/'completion.json').exists() for p in ['large','small'] for d in ['obqa','arc']),'already complete'
p=subprocess.run(['job-status','-f','-F','json'],capture_output=True,text=True,check=True,timeout=20)
jobs=json.loads(p.stdout).get('Jobs',{})
matches={j:v for j,v in jobs.items() if re.search(r'p2[_-]?10',v.get('Job_Name',''),re.I) or 'P2_10_' in v.get('Submit_arguments','')}
save(ROOT/'evidence/pre_submit_jobs.json',{j:{k:v.get(k) for k in ['Job_Name','job_state','Resource_List','comment']} for j,v in matches.items()})
assert all(v.get('job_state') in ['F','X'] for v in matches.values()),'P2-10 job already active'
for r in records:
    p=subprocess.run(['job-status','-xf','-F','json',r['job_id']],capture_output=True,text=True,check=True,timeout=20)
    v=json.loads(p.stdout)['Jobs'][r['job_id']];assert v['job_state']=='F','previous job must be terminated'
idx=len(records)+1;seconds=[10800,7200,3600][idx-1];script=ROOT/f'run_p2_10_{idx}.pbs'
assert sum(r['requested_node_seconds'] for r in records)+seconds<=21600
if args.check_only:print('PRE_SUBMIT_CHECK_PASS',idx,seconds);raise SystemExit(0)
env=os.environ.copy()
for k in ['CUDA_VISIBLE_DEVICES','NVIDIA_VISIBLE_DEVICES']:env.pop(k,None)
attempt={'utc':utc(),'submission_number':idx,'requested_node_seconds':seconds,'script':str(script),'script_sha256':sha(script),'resources':{'nodes':1,'gpus':2,'cpus':64,'mem':'240gb','queue':'gpu-queue'}}
save(ROOT/'evidence/uncertain_submission.json',attempt)
p=subprocess.run([str(Path.home()/'bin/submit-job'),str(script)],capture_output=True,text=True,env=env)
attempt.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
append(ROOT/'evidence/submission_attempts.jsonl',attempt);print(p.stdout,flush=True);print(p.stderr,flush=True)
ids=re.findall(r'(?m)^(\d+\.ClusterB[^\s]*)$',p.stdout)
if not ids:
    # Retain evidence; no ID means no resource debit. Uncertainty requires review.
    raise RuntimeError('submission yielded no job ID; inspect attempt before any retry')
assert len(ids)==1
records.append({**attempt,'job_id':ids[0],'cluster':'ClusterB','script_text':script.read_text()});save(ledger,records)
(ROOT/'evidence/uncertain_submission.json').rename(ROOT/f'evidence/submission_receipt_{idx}.json')
print(json.dumps({'job_id':ids[0],'requested_node_seconds':sum(r['requested_node_seconds'] for r in records),'remaining_node_seconds':21600-sum(r['requested_node_seconds'] for r in records)}))
