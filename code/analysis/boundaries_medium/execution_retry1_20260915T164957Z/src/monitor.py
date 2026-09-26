"""只读监控唯一作业；永不提交、修改或重试。"""
from common import *
import subprocess
jid=read(P/'evidence/pbs/submission.json')['job_id']
rec=json.loads(subprocess.check_output(['job-status','-xf','-F','json',jid],text=True))
j=rec['Jobs'][jid];j.pop('Variable_List',None)
save(P/'evidence/pbs/latest_status.json',rec)
progress=read(P/'PROGRESS.json') if (P/'PROGRESS.json').exists() else {}
print(json.dumps({'utc':utc(),'PBS':j['job_state'],'Exit_status':j.get('Exit_status'),
    'comment':j.get('comment'),'started':j.get('stime'),'used':j.get('resources_used'),
    'phase':progress.get('phase'),'actions':progress.get('action_success_count',0),
    'probes':progress.get('probe_success_count',0),'progress_utc':progress.get('utc'),
    'GPU_mechanical_PASS':(P/'GPU_MECHANICAL_PASS.json').exists(),
    'inference_complete':(P/'INFERENCE_COMPLETE.json').exists(),
    'numerical_validation':read(P/'NUMERICAL_VALIDATION.json')['status'] if (P/'NUMERICAL_VALIDATION.json').exists() else None},ensure_ascii=False),flush=True)
for name in ['EXECUTION_FAILURE.json','JOB_FAILURE.json']:
    if (P/name).exists():print(name,json.dumps(read(P/name),ensure_ascii=False))
if j['job_state']=='F' and j.get('Exit_status')!=0:
    run=DATA_ROOT/'runs/iclr2027_p2'/f'{jid}_medium_stage1'
    for name in ['outer.log','entry.log','execute.log','analyze.log','validate_results.log']:
        if (run/name).exists():print(name,(run/name).read_text()[-2000:])
