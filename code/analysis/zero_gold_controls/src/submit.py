from common import *
import subprocess,re,fcntl
EVID=P/'evidence/pbs';lock=(EVID/'submit.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert not (EVID/'submission_attempt.json').exists(),'One submission attempt already recorded; no retry'
cmd=[str(Path.home()/'bin/submit-job'),str(P/'run_controls.pbs')]
save(EVID/'submission_attempt.json',{'utc':utc(),'command':cmd,'wall_seconds':1800,'GPUs':1,'max_submissions':1,'status':'ATTEMPTED; ambiguous receipt never retried'})
proc=subprocess.run(cmd,capture_output=True,text=True,timeout=55)
save(EVID/'submission_result.json',{'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'utc':utc()});print(proc.stdout,proc.stderr,flush=True)
ids=re.findall(r'^\d+\.ClusterB-pbs[^\s]*$',proc.stdout,re.M);assert proc.returncode==0 and len(ids)==1
jid=ids[0];rec=json.loads(subprocess.check_output(['job-status','-xf','-F','json',jid],text=True));rec['Jobs'][jid].pop('Variable_List',None)
save(EVID/'submission_confirmed.json',rec);save(EVID/'submission.json',{'job_id':jid,'wall_seconds':1800,'GPU_count':1,'utc':utc()})
print('CONFIRMED',jid,rec['Jobs'][jid]['job_state'])
with (ROOT/'P2_1_20260910T041720Z/P2_STATE.md').open('a') as f:f.write(f'\n\n## {utc()} — {P.name} 已提交\n唯一新授权 P2_ZERO_GOLD_CONTROLS 作业 {jid}，gpu-queue/select1/00:30:00，申请0.5 GPU allocation hour；CPU累计上限900秒（含120秒准备报告预留）。最多4208次probe prefill、1次WordD拟合、60项新cal、2226条新冻结dev策略题评价。主对照ProbeMax，辅助ProbeEntropy/WordD；D/R2100及原划分/风险规则/历史输出完全复用。旧预算关闭；禁止第二作业。配置SHA256 `{sha(P/"frozen_config.json")}`。尚无成功结论。\n')
