"""仅读取已保存的进度/退出receipt；不查询模型结果或修改作业。"""
from common import *
state=read(P/'PROGRESS.json') if (P/'PROGRESS.json').exists() else {}
jid=read(P/'evidence/pbs/submission.json')['job_id']
end=DATA_ROOT/'runs/iclr2027_p2'/f'{jid}_medium_stage1/job_exit.txt'
age=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(state['utc'])).total_seconds() if state.get('utc') else None
print(json.dumps({'utc':utc(),'progress_utc':state.get('utc'),'progress_age_seconds':age,'phase':state.get('phase'),
    'actions':state.get('action_success_count',0),'probes':state.get('probe_success_count',0),
    'job_exit':end.read_text() if end.exists() else None,
    'inference_complete':(P/'INFERENCE_COMPLETE.json').exists(),
    'validation':read(P/'NUMERICAL_VALIDATION.json')['status'] if (P/'NUMERICAL_VALIDATION.json').exists() else None,
    'failure_files':[name for name in ['JOB_FAILURE.json','EXECUTION_FAILURE.json'] if (P/name).exists()]},ensure_ascii=False))
