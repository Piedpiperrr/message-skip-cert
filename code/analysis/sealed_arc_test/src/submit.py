from common import *
import subprocess,re,fcntl
EVID=P/'evidence/pbs';lock=(EVID/'submit.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
verify_freeze('PRE_TEST_FREEZE.json');assert (P/'evidence/SEALED_DOWNLOAD_RECEIPT.json').exists()
assert not (EVID/'submission_attempt.json').exists(),'One submission attempt already recorded; no retry'
cmd=[str(Path.home()/'bin/submit-job'),str(P/'run_sealed.pbs')]
save(EVID/'submission_attempt.json',{'utc':utc(),'command':cmd,'wall_seconds':7200,'GPUs':2,'max_submissions':1,'status':'ATTEMPTED; ambiguous receipt never retried'})
proc=subprocess.run(cmd,capture_output=True,text=True,timeout=55)
save(EVID/'submission_result.json',{'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'utc':utc()});print(proc.stdout,proc.stderr,flush=True)
ids=re.findall(r'^\d+\.ClusterB-pbs[^\s]*$',proc.stdout,re.M);assert proc.returncode==0 and len(ids)==1
jid=ids[0]
save(EVID/'submission.json',{'job_id':jid,'wall_seconds':7200,'GPU_count':2,'utc':utc()})
rec=json.loads(subprocess.check_output(['job-status','-xf','-F','json',jid],text=True));rec['Jobs'][jid].pop('Variable_List',None);save(EVID/'submission_confirmed.json',rec)
print('CONFIRMED',jid,rec['Jobs'][jid]['job_state'])
with (ROOT/'P2_1_20260910T041720Z/P2_STATE.md').open('a') as f:f.write(f'\n\n## {utc()} — {P.name} 已提交\n唯一正式作业 {jid}，双GPU/gpu-queue/02:00:00，4 GPU申请小时，上限5；CPU独立上限9000秒含1200秒准备统计报告预留。4688完整动作、2344独立在线probe；small/OBQA不运行。PRE_TEST_FREEZE SHA256 `{sha(P/"PRE_TEST_FREEZE.json")}`。只有固定版本ARC test全部1172题；gold等待预测计时freeze后关联；方法搜索关闭。禁止第二提交、重试或重跑成功ID。\n')
