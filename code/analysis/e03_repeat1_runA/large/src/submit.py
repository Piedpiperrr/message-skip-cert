from common import *
import subprocess,re,fcntl
EVID=P/'evidence/pbs';lock=(EVID/'submit.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert not (EVID/'submission_attempt.json').exists(),'One submission attempt already recorded; no retry'
cmd=[str(Path.home()/'bin/submit-job'),str(P/'run_e2e.pbs')]
save(EVID/'submission_attempt.json',{'utc':utc(),'command':cmd,'wall_seconds':1800,'GPUs':2,'max_submissions':1,'status':'ATTEMPTED; ambiguous receipt never retried'})
proc=subprocess.run(cmd,capture_output=True,text=True,timeout=55)
save(EVID/'submission_result.json',{'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'utc':utc()});print(proc.stdout,proc.stderr,flush=True)
ids=re.findall(r'^\d+\.ClusterB-pbs[^\s]*$',proc.stdout,re.M);assert proc.returncode==0 and len(ids)==1
jid=ids[0];rec=json.loads(subprocess.check_output(['job-status','-xf','-F','json',jid],text=True));rec['Jobs'][jid].pop('Variable_List',None)
save(EVID/'submission_confirmed.json',rec);save(EVID/'submission.json',{'job_id':jid,'wall_seconds':1800,'GPU_count':2,'utc':utc()})
print('CONFIRMED',jid,rec['Jobs'][jid]['job_state'])
with (ROOT/'P2_1_20260910T041720Z/P2_STATE.md').open('a') as f:f.write(f'\n\n## {utc()} — {P.name} 已提交\n唯一 P2_FROZEN_POLICY_E2E_VALIDATION 作业 {jid}，gpu-queue/select2/00:30:00，申请上限1 GPU allocation hour；累计CPU上限1500秒含180秒准备报告预留。仅原两large模型任务128题panel的四个冻结ProbeMax policy及fixed Text/C2C真实完整重放：1024完整动作、512独立在线probe，0新拟合/校准/gold/warmup/retry。small四层fallback不执行；上一轮冻结资产只读、不重采。D仍learned control，ProbeMax普通基线，ARC test继续封存。配置SHA256 `{sha(P/"frozen_config.json")}`。尚无E2E结论；禁止第二提交。\n')
