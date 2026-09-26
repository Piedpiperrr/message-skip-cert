"""Bounded CPU checks for one-shot entry and frozen rotation; no model import."""
from common import *
import ast,copy
from guard_checks import allocation_identity,walltime_seconds,legacy_cgroup_pattern_match
from execute import order_for
cfg=read(STAGE1/'evidence/pbs/allocation.json')
job=copy.deepcopy(next(iter(cfg['scheduler']['Jobs'].values())))
job['Resource_List']['walltime']='00:15:00'
host=cfg['host'];nodes=cfg['nodefile_nodes']
assert allocation_identity(job,host,nodes)['status']=='PASS'
for field,value in [('ngpus',1),('nodect',2),('walltime','00:15:01')]:
    bad=copy.deepcopy(job);bad['Resource_List'][field]=value
    assert allocation_identity(bad,host,nodes)['status']=='BLOCKED'
bad=copy.deepcopy(job);bad['exec_vnode']=bad['exec_vnode'].replace('ngpus=2','ngpus=1')
assert allocation_identity(bad,host,nodes)['status']=='BLOCKED'
assert allocation_identity(job,'unassigned-host',nodes)['status']=='BLOCKED'
assert walltime_seconds('00:15:00')==900
assert legacy_cgroup_pattern_match('0::/unified/pbs.slice/workload','123.server') is False
for ds in ['obqa','arc']:
    orders=[order_for(i) for i in range(128)]
    assert all(sorted(o)==['fixed_C','policy_C'] for o in orders)
    assert sum(o[0]=='fixed_C' for o in orders)==64
assert sha(P/'src/native_runtime.py')==sha(STAGE1/'src/native_runtime.py')
for file in (P/'src').glob('*.py'):ast.parse(file.read_text())
code=(P/'src/execute.py').read_text()
assert 'mechanical_smoke(' not in code and 'existing_gold_ANALYSIS_ONLY' not in code and 'expected_Stage1_identity' not in code
assert "rt.action(q,selected)" in code and "rt.probe(q)" in code
pbs=(P/'run_medium_stage2.pbs').read_text()
assert '#SCHED -l walltime=00:15:00' in pbs and '#SCHED -l fsreq=<fs>' in pbs
save(P/'evidence/ENGINEERING_PREFLIGHT.json',dict(status='PASS',utc=utc(),real_scheduler_fixture=True,
    wrong_allocation_rejected=True,cgroup_legacy_nonfatal=True,rotation_64_64=True,
    unchanged_native_runtime=True,model_imports=0,model_forwards=0))
print('ENGINEERING_PREFLIGHT_PASS')
