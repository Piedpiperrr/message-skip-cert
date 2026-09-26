from common import *
import subprocess,re,fcntl
v=P/'evidence/pbs';lock=(v/'submit.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert not (v/'submission_attempt.json').exists(),'Do not submit twice'
cmd=[str(Path.home()/'bin/submit-job'),str(P/'run_crossover.pbs')]
save(v/'submission_attempt.json',{'utc':utc(),'command':cmd,'wall_seconds':600,'GPUs_allocated':1,'GPU_compute':0,'max_submissions':1,'status':'ATTEMPTED; ambiguous receipt must not be retried'})
r=subprocess.run(cmd,capture_output=True,text=True,timeout=55);save(v/'submission_result.json',{'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'utc':utc()});print(r.stdout,r.stderr,flush=True)
ids=re.findall(r'^\d+\.ClusterB-pbs[^\s]*$',r.stdout,re.M);assert r.returncode==0 and len(ids)==1
jid=ids[0];j=json.loads(subprocess.check_output(['job-status','-xf','-F','json',jid],text=True));j['Jobs'][jid].pop('Variable_List',None);save(v/'submission_confirmed.json',j);save(v/'submission.json',{'job_id':jid,'wall_seconds':600,'GPU_count':1,'utc':utc()})
with (ROOT/'P2_1_20260910T041720Z/P2_STATE.md').open('a') as f:f.write(f'\n\n## {utc()} — {P.name} 已提交\n唯一P2_GOLD_BUDGET_CROSSOVER作业 {jid}，gpu-queue/select1/00:10:00，申请1/6 GPU allocation hour；GPU计算/模型backbone加载/prefill均0，CPU累计上限300秒（30秒准备报告预留）。15个嵌套子集已冻结，B32/128/512×r0..4，只新增correctness-R头，最多15次拟合、300新cal检验、11130dev策略题评价。原D/R2100及划分/特征只读复用，旧185721预算不恢复。配置SHA256 `{sha(P/"frozen_config.json")}`。准备阶段旧标签schema两行提前预览偏差见新目录evidence/PREPARATION_DEVIATION.json，用户预定抽样规则未变。禁止第二作业，未完成不解释为科学失败。\n')
print('CONFIRMED',jid,j['Jobs'][jid]['job_state'])
