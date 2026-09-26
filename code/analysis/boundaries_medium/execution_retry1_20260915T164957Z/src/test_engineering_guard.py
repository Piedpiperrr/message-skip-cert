"""用第一次PBS真实回执及不同cgroup格式检查修复；无GPU或项目推理。"""
from common import *
from guard_checks import walltime_seconds,legacy_cgroup_pattern_match,allocation_identity
import copy
old=PARENT/'execution_20260915T152640Z'
j=next(iter(read(old/'evidence/pbs/terminal_status.json')['Jobs'].values()))
j=copy.deepcopy(j);j['job_state']='R';j['Resource_List']['walltime']='03:29:50'
cases=[]
assert walltime_seconds('03:29:50')==12590
assert (10+walltime_seconds('03:29:50'))*2/3600==7
for raw in ['0::/\n','0::/system.slice/pbs.service/task_185994\n','7:cpu:/pbs_jobs/run004\n','7:cpu:/jobs/185994\n']:
    identity=allocation_identity(j,'ClusterB-gpu-03',['ClusterB-gpu-03'])
    assert identity['status']=='PASS'
    cases.append({'cgroup_raw':raw,'legacy_match':legacy_cgroup_pattern_match(raw,'run004'),'scheduler_guard':'PASS'})
for mutation in ['wrong_host','allocated_one_gpu','requested_one_gpu','not_running','wrong_account','wrong_queue','too_long']:
    x=copy.deepcopy(j);host='ClusterB-gpu-03'
    if mutation=='wrong_host':host='ClusterB-gpu-04'
    if mutation=='allocated_one_gpu':x['exec_vnode']=x['exec_vnode'].replace('ngpus=2','ngpus=1')
    if mutation=='requested_one_gpu':x['Resource_List']['ngpus']=1
    if mutation=='not_running':x['job_state']='Q'
    if mutation=='wrong_account':x['Account_Name']='wrong'
    if mutation=='wrong_queue':x['queue']='infer-svc'
    if mutation=='too_long':x['Resource_List']['walltime']='03:30:00'
    assert allocation_identity(x,host,['ClusterB-gpu-03'])['status']=='BLOCKED',mutation
    cases.append({'mutation':mutation,'expected':'BLOCKED'})
save(P/'ENGINEERING_GUARD_CHECKS.json',{'status':'PASS','utc':utc(),'cases':cases,
    'dynamic_deadline_wall_seconds':12590,'safety_margin_seconds':45,'cumulative_cap_GPU_hours':7,
    'project_question_reads':0,'model_loading_calls':0,'model_forwards':0})
print('ENGINEERING_GUARD_CHECKS_PASS')
