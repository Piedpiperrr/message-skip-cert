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
        account=job.get('Account_Name')=='project',queue=job.get('queue')=='debug',nodect=int(r.get('nodect',0))==2,
        requested_GPUs=int(r.get('ngpus',0))==0,allocated_GPUs=sum(x['ngpus'] for x in assigned)==0,  # E3 ClusterA: GPUs are not a PBS resource (2 exclusive nodes of 4 A100); the CUDA guard still asserts 2 visible devices
        assigned_host=len(assigned)==2 and short in {x['node'].split('.')[0] for x in assigned},
        exec_host=len(job.get('exec_host','').split('+'))==2 and short in {x.split('/')[0].split('.')[0] for x in job.get('exec_host','').split('+')},
        nodefile=len({x.split('.')[0] for x in nodefile})==2 and short in {x.split('.')[0] for x in nodefile},fsreq=set(r.get('fsreq','').split(':'))>={'home','sharedfs'},
        budget=0<walltime_seconds(r['walltime'])<=3300)  # E3 ClusterA: debug walltime 00:55:00 (original cap 900 s; the replay's own 900 s budget is kept in pbs_entry.py)
    return dict(status='PASS' if all(checks.values()) else 'BLOCKED',checks=checks,assigned=assigned,walltime_seconds=walltime_seconds(r['walltime']))
