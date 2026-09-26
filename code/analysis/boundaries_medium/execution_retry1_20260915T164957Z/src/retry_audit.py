"""同一allocation内，synthetic smoke通过后、第一道项目题推理前冻结执行身份。"""
from common import *

def freeze_after_gpu_smoke(smoke):
    destination=P/'MEDIUM_PAIR_EXECUTION_FREEZE_RETRY1.json'
    assert not destination.exists(),'Never overwrite execution freeze'
    assert not (P/'records/attempts.jsonl').exists() and not (P/'OUTCOMES_OBSERVED.json').exists()
    assert smoke['status']=='PASS' and smoke['MEDIUM_PAIR_OUTCOMES_OBSERVED'] is False
    assert smoke['project_question_reads']==0 and smoke['probe_calls']==0 and smoke['parser_calls']==0
    assert smoke['helper_device']=='cuda:0' and smoke['receiver_device']=='cuda:1' and smoke['projector_count']==28
    pre=read(P/'MEDIUM_PAIR_EXECUTION_PRECHECK_RETRY1.json')
    for f,h in pre['frozen_files'].items():assert sha(f)==h,f
    allocation=read(P/'evidence/pbs/allocation.json');cuda=read(P/'evidence/CUDA_DEVICE_RECEIPT.json')
    assert allocation['allocation_identity']['status']=='PASS' and cuda['status']=='PASS'
    assert allocation['job_id']==os.environ['PBS_JOBID']
    record={**pre,'status':'PASS','utc':utc(),'freeze_stage':'after synthetic GPU smoke, before first formal project inference',
        'precheck_sha256':sha(P/'MEDIUM_PAIR_EXECUTION_PRECHECK_RETRY1.json'),
        'retry_authorization_sha256':sha(P/'MEDIUM_PAIR_RETRY_AUTHORIZATION.json'),
        'scheduler_allocation_identity':allocation,'cgroup_receipt':read(P/'evidence/CGROUP_RECEIPT.json'),
        'cgroup_raw_sha256':sha(P/'evidence/cgroup_raw.txt'),'CUDA_device_receipt':cuda,
        'synthetic_smoke_PASS':smoke,'synthetic_smoke_receipt_sha256':sha(P/'GPU_MECHANICAL_PASS.json'),
        'deadline_receipt':read(P/'evidence/DEADLINE_RECEIPT.json'),
        'engineering_guard_repair_only':True,'scientific_protocol_unchanged':True,
        'MEDIUM_PAIR_OUTCOMES_OBSERVED':False,'project_questions_inferred':0,'no_third_submission':True}
    save(destination,record)
    print('EXECUTION_FREEZE_RETRY1_PASS',sha(destination),flush=True)
    return record
