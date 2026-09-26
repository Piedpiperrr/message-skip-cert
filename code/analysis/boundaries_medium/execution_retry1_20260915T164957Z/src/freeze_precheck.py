"""提交前锁定工程变更和原科学身份；最终execution freeze须等GPU smoke PASS。"""
from common import *
import ast,difflib
old=PARENT/'execution_20260915T152640Z';oldex=read(old/'MEDIUM_PAIR_EXECUTION_FREEZE.json')
assert not (P/'MEDIUM_PAIR_EXECUTION_PRECHECK_RETRY1.json').exists()
scientific=validate_parent()
assert read(P/'ENGINEERING_GUARD_CHECKS.json')['status']=='PASS'
assert read(P/'MEDIUM_PAIR_RETRY_AUTHORIZATION.json')['Work_authorizes_exactly_one_replacement_submission']
assert read(old/'FINAL_RECEIPT.json')['action_success_count']==read(old/'FINAL_RECEIPT.json')['ProbeMax_success_count']==0
assert read(old/'evidence/pbs/terminal_status.json')['Jobs']['run001']['job_state']=='F'
identity=read(P/'ATTEMPT1_IMMUTABILITY_INDEX.json')
assert {str(f.relative_to(old)) for f in old.rglob('*') if f.is_file()}==set(identity['file_sha256'])
for rel,h in identity['file_sha256'].items():assert sha(old/rel)==h,rel
unchanged={}
for name in ['common.py','native_runtime.py','risk.py','analyze.py','validate_results.py','validate_input_records.py','test_risk.py']:
    assert sha(P/'src'/name)==sha(old/'src'/name),name
    unchanged[str(P/'src'/name)]=sha(P/'src'/name)
# Mechanically prove the driver differs only at the audit imports/freeze points.
prior=(old/'src/execute.py').read_text()
expected=prior.replace('from risk import thresholds,calibrate,mask\n','from risk import thresholds,calibrate,mask\nfrom retry_audit import freeze_after_gpu_smoke\n')
expected=expected.replace("freeze=read(P/'MEDIUM_PAIR_EXECUTION_FREEZE.json');assert freeze['status']=='PASS'\nEXEC_HASH=sha(P/'MEDIUM_PAIR_EXECUTION_FREEZE.json')", "freeze=read(P/'MEDIUM_PAIR_EXECUTION_PRECHECK_RETRY1.json');assert freeze['status']=='PASS'\nEXEC_HASH=None  # Set after synthetic smoke; before any project inference.")
expected=expected.replace("    assert smoke['status']=='PASS' and not smoke['MEDIUM_PAIR_OUTCOMES_OBSERVED']\n", "    assert smoke['status']=='PASS' and not smoke['MEDIUM_PAIR_OUTCOMES_OBSERVED']\n    freeze_after_gpu_smoke(smoke)\n    EXEC_HASH=sha(P/'MEDIUM_PAIR_EXECUTION_FREEZE_RETRY1.json')\n")
assert (P/'src/execute.py').read_text()==expected,'UNEXPECTED_SCIENTIFIC_DRIVER_CHANGE'
(P/'evidence/execute_audit_only.diff').write_text(''.join(difflib.unified_diff(prior.splitlines(True),expected.splitlines(True),fromfile='attempt1/execute.py',tofile='retry1/execute.py')))
(P/'evidence/engineering_entry.diff').write_text(''.join(difflib.unified_diff((old/'src/pbs_entry.py').read_text().splitlines(True),(P/'src/pbs_entry.py').read_text().splitlines(True),fromfile='attempt1/pbs_entry.py',tofile='retry1/pbs_entry.py')))
for f in (P/'src').glob('*.py'):ast.parse(f.read_text(),filename=str(f))
sources=read(P/'RUNTIME_SOURCE_INDEX.json')
for f,h in sources.items():assert sha(f)==h,f
for name in ['protocol/formal_input_identities.jsonl','PROTOCOL_RENDER_CHECKS.json','STRICT_LOADING_CPU.json','RISK_UNIT_CHECKS.json']:
    assert sha(P/name)==sha(old/name),name
paths_resolved=paths();print('RESOLVED_PATHS',json.dumps(paths_resolved),flush=True)
index=read(P/'MODEL_SOURCE_INDEX.json')
for role,m in index['local_verification']['models'].items():
    for f in m['weight_files']:assert sha(f['path'])==f['sha256']==f['official_LFS_sha256'],f['path']
assert sha(PARENT/'MEDIUM_PAIR_PROTOCOL_FREEZE.json')==PARENT_HASH
frozen={str(f):sha(f) for f in (P/'src').glob('*.py')}
frozen.update(sources)
for f in ['run_medium_stage1.pbs','MODEL_SOURCE_INDEX.json','MEDIUM_PAIR_RETRY_AUTHORIZATION.json','ATTEMPT1_IMMUTABILITY_INDEX.json','ENGINEERING_GUARD_CHECKS.json','RUNTIME_SOURCE_INDEX.json','protocol/formal_input_identities.jsonl','STRICT_LOADING_CPU.json','RISK_UNIT_CHECKS.json','PROTOCOL_RENDER_CHECKS.json']:
    frozen[str(P/f)]=sha(P/f)
for role,m in index['models'].items():
    for f in m['verified_local_config_tokenizer_files']:
        path=P/'assets'/role/f['official_file'];assert sha(path)==f['sha256'];frozen[str(path)]=f['sha256']
auth=read(P/'MEDIUM_PAIR_RETRY_AUTHORIZATION.json')
pre={'status':'PASS','utc':utc(),'scope':'pre-submission engineering and identity precheck, not GPU smoke or final execution freeze',
    'parent_protocol_path':str(PARENT/'MEDIUM_PAIR_PROTOCOL_FREEZE.json'),'parent_protocol_sha256':PARENT_HASH,
    'parent_protocol_timestamp':scientific['utc'],'retry_authorization_sha256':sha(P/'MEDIUM_PAIR_RETRY_AUTHORIZATION.json'),
    'modified_engineering_entry_source_hashes':{str(P/'src'/n):sha(P/'src'/n) for n in ['pbs_entry.py','guard_checks.py','retry_audit.py','execute.py']},
    'unchanged_scientific_runtime_source_hashes':{**unchanged,**sources},
    'scientific_driver_diff_scope':'only audit import, precheck input and post-smoke execution freeze; exact patch verified',
    'local_models':index['local_verification'],'strict_CPU_loading':read(P/'STRICT_LOADING_CPU.json'),
    'PBS_script_sha256':sha(P/'run_medium_stage1.pbs'),'Work_retry_authorization':auth,
    'formal_populations':oldex['formal_populations'],'formal_question_rows':5626,'expected_action_count':16878,'expected_ProbeMax_count':5626,
    'action_order':oldex['action_order'],'fit_cal_task_order':oldex['fit_cal_task_order'],'dev_order':oldex['dev_order'],
    'all_deployments_before_dev':True,'all_routes_before_gold':True,'no_retries':True,
    'MEDIUM_PAIR_OUTCOMES_OBSERVED':False,'frozen_files':frozen,'parent_history_hashes':oldex['parent_history_hashes'],
    'attempt1_immutable_index_sha256':sha(P/'ATTEMPT1_IMMUTABILITY_INDEX.json'),
    'positioning':scientific['positioning'],'report_all_four_strata':True,'Stage2_automatic':False,
    'engineering_guard_repair_only':True,'scientific_protocol_unchanged':True,'scientific_protocol_changes':[]}
save(P/'MEDIUM_PAIR_EXECUTION_PRECHECK_RETRY1.json',pre)
save(P/'RESOURCE_LEDGER.json',{'status':'PRE_SUBMISSION','utc':utc(),'cumulative_Stage1_GPU_cap_hours':7,
    'prior_attempt':{'job_id':'run001','terminal_state':'F','Exit_status':1,'GPU_allocation_hours':10*2/3600,
        'scientific_outputs':0,'failure':'engineering cgroup-guard failure','immutable_ledger_path':str(old/'RESOURCE_LEDGER.json')},
    'replacement_attempt':{'formal_submissions':0,'GPU_count':2,'walltime_cap':'03:29:50','max_GPU_allocation_hours':12590*2/3600},
    'maximum_cumulative_requested_with_prior_actual_GPU_hours':7,'no_third_submission':True,'Stage2_started':False})
print('EXECUTION_PRECHECK_RETRY1_PASS',sha(P/'MEDIUM_PAIR_EXECUTION_PRECHECK_RETRY1.json'),flush=True)
