"""仅处理PBS/device审计；不接触模型、题目或科学计算。"""
import re

def walltime_seconds(value):
    pieces=value.split(':')
    if len(pieces)!=3:raise ValueError('PBS walltime must be H+:MM:SS')
    h,m,s=map(int,pieces)
    if h<0 or not 0<=m<60 or not 0<=s<60:raise ValueError('Invalid PBS walltime')
    return h*3600+m*60+s

def legacy_cgroup_pattern_match(raw,job_id):
    paths=[line.split(':',2)[-1].split('/') for line in raw.splitlines()]
    return any('jobs' in parts and job_id.split('.')[0] in parts for parts in paths)

def allocation_identity(job,host,nodefile_nodes):
    assigned=[]
    for node,resources in re.findall(r'\(([^:()]+):([^()]*)\)',job.get('exec_vnode','')):
        fields=dict(field.split('=',1) for field in resources.split(':') if '=' in field)
        assigned.append({'node':node,'ngpus':int(fields.get('ngpus','0'))})
    r=job['Resource_List'];short=host.split('.')[0]
    checks={'current_job_state_R':job.get('job_state')=='R',
        'current_user':job.get('Job_Owner','').split('@')[0]=='user',
        'account_project':job.get('Account_Name')=='project',
        'queue_gpu_queue':job.get('queue')=='gpu-queue','nodect_1':int(r.get('nodect',0))==1,
        'requested_ngpus_2':int(r.get('ngpus',0))==2,
        'allocated_ngpus_2':sum(item['ngpus'] for item in assigned)==2,
        'assigned_host_matches_process':bool(assigned) and {item['node'].split('.')[0] for item in assigned}=={short},
        'exec_host_matches_process':{part.split('/')[0].split('.')[0] for part in job.get('exec_host','').split('+')}=={short},
        'PBS_nodefile_matches_process':{node.split('.')[0] for node in nodefile_nodes}=={short},
        'fsreq_home_sharedfs':set(r.get('fsreq','').split(':'))>={'home','sharedfs'},
        'stage2_walltime_cap':0<walltime_seconds(r.get('walltime','0:00:00'))<=walltime_seconds('01:00:00')}
    return {'checks':checks,'assigned_vnodes':assigned,'status':'PASS' if all(checks.values()) else 'BLOCKED',
        'walltime_seconds':walltime_seconds(r.get('walltime','0:00:00'))}
