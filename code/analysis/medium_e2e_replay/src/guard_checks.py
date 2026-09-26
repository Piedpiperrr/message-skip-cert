"""Scheduler/device engineering checks; cgroup spelling is nonfatal."""
import re
def walltime_seconds(value):
    h,m,s=map(int,value.split(':'))
    if h<0 or not 0<=m<60 or not 0<=s<60:raise ValueError('Invalid walltime')
    return 3600*h+60*m+s
def legacy_cgroup_pattern_match(raw,jid):
    return any('jobs' in x.split(':',2)[-1].split('/') and jid.split('.')[0] in x.split(':',2)[-1].split('/') for x in raw.splitlines())
def allocation_identity(job,host,nodefile):
    assigned=[]
    for node,res in re.findall(r'\(([^:()]+):([^()]*)\)',job.get('exec_vnode','')):
        fields=dict(x.split('=',1) for x in res.split(':') if '=' in x)
        assigned.append(dict(node=node,ngpus=int(fields.get('ngpus',0))))
    r=job['Resource_List'];short=host.split('.')[0]
    checks=dict(state_R=job.get('job_state')=='R',user=job.get('Job_Owner','').split('@')[0]=='user',
        account=job.get('Account_Name')=='project',queue=job.get('queue')=='gpu-queue',nodect=int(r.get('nodect',0))==1,
        requested_GPUs=int(r.get('ngpus',0))==2,allocated_GPUs=sum(x['ngpus'] for x in assigned)==2,
        assigned_host=bool(assigned) and {x['node'].split('.')[0] for x in assigned}=={short},
        exec_host={x.split('/')[0].split('.')[0] for x in job.get('exec_host','').split('+')}=={short},
        nodefile={x.split('.')[0] for x in nodefile}=={short},fsreq=set(r.get('fsreq','').split(':'))>={'home','sharedfs'},
        budget=0<walltime_seconds(r['walltime'])<=900)
    return dict(status='PASS' if all(checks.values()) else 'BLOCKED',checks=checks,assigned=assigned,walltime_seconds=walltime_seconds(r['walltime']))
