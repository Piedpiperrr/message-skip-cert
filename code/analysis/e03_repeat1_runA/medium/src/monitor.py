"""Read-only scheduler/status query; writes only new Stage 2 audit receipts."""
from common import *
import subprocess
jid=read(P/'evidence/pbs/submission.json')['job_id']
r=subprocess.run(['job-status','-xf','-F','json',jid],capture_output=True,text=True,timeout=30)
result=dict(utc=utc(),job_id=jid,qstat_returncode=r.returncode)
if r.returncode:
    result['stderr']=r.stderr;save(P/'evidence/pbs/query_failure.json',result)
else:
    response=json.loads(r.stdout)
    for j in response['Jobs'].values():j.pop('Variable_List',None)
    job=response['Jobs'][jid];save(P/'evidence/pbs/latest_status.json',response)
    result.update({k:job.get(k) for k in ['job_state','substate','Exit_status','stime','mtime','obittime','exec_vnode','resources_used','comment']})
    if job['job_state']=='F':save(P/'evidence/pbs/terminal_status.json',response)
if (P/'REPLAY_PROGRESS.json').exists():
    p=read(P/'REPLAY_PROGRESS.json');result['progress']={k:p[k] for k in ['utc','successful_count','attempts','online_probe_attempts','task','panel_ordinal']}
for name in ['STARTUP.json']:
    path=P/'evidence'/name
    if path.exists():result['startup']={k:read(path).get(k) for k in ['status','startup_wall_seconds','startup_total_including_runtime_import_seconds']}
for name in ['JOB_FAILURE.json','REQUEST_FAILURE.json','REPLAY_COMPLETE.json','JOB_WORK_COMPLETE.json']:
    path=P/name
    if path.exists():result[name]=read(path)
save(P/'LATEST_STATUS.json',result)
print(json.dumps(result,ensure_ascii=False,indent=2))
