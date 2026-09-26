from common import *
import subprocess,re,fcntl
EVID=P/'evidence/pbs';lock=(EVID/'submit.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert not (EVID/'submission_attempt.json').exists(),'One submission attempt already recorded; no retry'
cmd=[str(Path.home()/'bin/submit-job'),str(P/'run_pilot.pbs')]
save(EVID/'submission_attempt.json',{'utc':utc(),'command':cmd,'wall_seconds':1800,'GPUs':1,'max_submissions':1,'status':'ATTEMPTED; ambiguous receipt never retried'})
proc=subprocess.run(cmd,capture_output=True,text=True,timeout=55)
save(EVID/'submission_result.json',{'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'utc':utc()});print(proc.stdout,proc.stderr,flush=True)
ids=re.findall(r'^\d+\.ClusterB-pbs[^\s]*$',proc.stdout,re.M);assert proc.returncode==0 and len(ids)==1
jid=ids[0];rec=json.loads(subprocess.check_output(['job-status','-xf','-F','json',jid],text=True));rec['Jobs'][jid].pop('Variable_List',None)
save(EVID/'submission_confirmed.json',rec);save(EVID/'submission.json',{'job_id':jid,'wall_seconds':1800,'GPU_count':1,'utc':utc()})
print('CONFIRMED',jid,rec['Jobs'][jid]['job_state'])
with (ROOT/'P2_1_20260910T041720Z/P2_STATE.md').open('a') as f:f.write(f'\n\n## {utc()} — {P.name}\n本轮独立二元风险校准任务已提交，唯一作业 {jid}，gpu-queue/select=1/00:30:00，申请0.5 GPU allocation hour，CPU累计上限1200秒，prefill尝试上限742。fit/cal无标签随机划分2100/1366已冻结；4新头、100项Bonferroni规则，alpha=.05/delta=.10/M=100。配置SHA256 `{sha(P/"frozen_config.json")}`。原历史只读；尚未完成不解释为科学失败。禁止第二次提交/扩预算。\n')
