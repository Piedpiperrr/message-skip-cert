"""独立 CPU 重算配对统计、bootstrap 和 identity 诊断；不重跑模型。"""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from common import *
import numpy as np,statistics,math
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
cfg=verify_freeze();v=read(P/'NUMERICAL_VALIDATION.json');assert v['status']=='PASS'
rr=rows(P/'records/four_arm_requests.jsonl');pairs=list(csv.DictReader((P/'summary/paired_per_question.csv').open()))
ids=read(P/'inputs/candidate_e2e128_ids.json');rm={(r['id'],r['arm']):r for r in rr};summary=read(P/'summary/mmlu_pro_e2e_summary.json')
idx=np.load(P/'protocol/bootstrap_indices.npz')['indices'];assert np.array_equal(idx,np.random.default_rng(0).integers(0,128,size=(2000,128)))
def quantile(vals,q):
    z=sorted(vals);a=(len(z)-1)*q;i=math.floor(a);j=math.ceil(a);return z[i]+(a-i)*(z[j]-z[i])
checks=[]
for s,ref in zip(summary,['T','C']):
    fixed=[rm[i,'fixed_'+ref]['latency_ms'] for i in ids];policy=[rm[i,'policy_'+ref]['latency_ms'] for i in ids];saving=[a-b for a,b in zip(fixed,policy)]
    means=[math.fsum(saving[int(k)] for k in draws)/128 for draws in idx]
    lo=quantile(means,.025);hi=quantile(means,.975)
    for actual,expected in [(math.fsum(saving)/128,s['paired_mean_saving_ms']),(statistics.median(saving),s['paired_median_saving_ms']),
        (math.fsum(fixed)/128,s['fixed_mean_ms']),(math.fsum(policy)/128,s['policy_mean_ms']),
        (statistics.median(fixed),s['fixed_median_ms']),(statistics.median(policy),s['policy_median_ms']),
        (lo,s['descriptive_bootstrap95_low_ms']),(hi,s['descriptive_bootstrap95_high_ms'])]:assert abs(actual-expected)<1e-8
    assert s['classification']==('E2E_POSITIVE' if math.fsum(saving)>0 and lo>0 else 'E2E_UNCERTAIN_OR_NEGATIVE')
    assert s['route_to_R_count']==sum(rm[i,'policy_'+ref]['selected']=='R' for i in ids)
    for part,field in [('online_probe_ms','probe_mean_ms'),('selector_ms','selector_mean_ms')]:assert abs(math.fsum(rm[i,'policy_'+ref]['parts_ms'][part] for i in ids)/128-s[field])<1e-8
    checks.append(dict(reference=s['reference'],N=128,mean_saving_ms=math.fsum(saving)/128,bootstrap_low_ms=lo,bootstrap_high_ms=hi,classification=s['classification'],status='PASS'))
correct=rows(P/'records/four_arm_requests_with_correctness.jsonl');assert len(correct)==512
for s,ref in zip(summary,['T','C']):
    for prefix,key in [('fixed_','fixed_reference_correct'),('policy_','policy_correct')]:
        selected=[r for r in correct if r['arm']==prefix+ref];assert sum(not r['invalid'] and r['answer']==r['gold'] for r in selected)==s[key]
identity=list(csv.DictReader((P/'summary/output_identity_checks.csv').open()));assert len(identity)==256
assert sum(r['required_output_identity_pass']=='False' for r in identity)==v['output_identity_mismatches']
runtime=list(csv.DictReader((P/'summary/runtime_diagnostics.csv').open()))
for r in runtime:assert all(int(r['order_position_'+str(i)])==32 for i in range(4))
assert sum(r['probe'] is not None for r in rr)==256 and sum(r['first_formal_request_global'] for r in rr)==1
assert len({r['job_id'] for r in rr})==1 and all(not r['runtime_failure'] for r in rr)
def dt(t):return datetime.datetime.fromisoformat(t)
assert dt(cfg['utc'])<dt(read(P/'MMLU_PRO_STAGE2_OUTCOMES_STARTED.json')['utc'])
resource=read(P/'RESOURCE_LEDGER.json');end=datetime.datetime.strptime(resource['end'],'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc)
assert end<dt(read(P/'evidence/ANALYSIS_START.json')['utc'])
assert resource['actual_GPUh']<=2 and resource['formal_PBS_submissions']==1
source_checks=[]
for r in read(STAGE1/'evidence/FROZEN_SOURCE_VERIFICATION.json')['checks']:
    actual=sha(r['path']);assert actual==r['expected'],r['path'];source_checks.append(dict(path=r['path'],sha256=actual,match=True))
save(P/'evidence/FROZEN_SOURCE_VERIFICATION.json',dict(utc=utc(),status='PASS',checks=source_checks))
receipt=dict(utc=utc(),status='PASS',independent_math_fsum_and_linear_percentiles=checks,bootstrap_seed=0,resamples=2000,
    accuracy_recomputed=True,all_first_requests_retained=True,all_128_items_retained=True,identity_differences_retained=True,
    one_allocation_one_residency=True,models_and_runtime_parent_hashes_unchanged=True,V4_and_existing_sources_unchanged=len(source_checks),
    extra_model_requests=0,extra_PBS=0,no_next_task=True)
save(P/'evidence/FINAL_NUMERICAL_AUDIT.json',receipt)
v['independent_final_numerical_audit']=dict(status='PASS',path='evidence/FINAL_NUMERICAL_AUDIT.json',sha256=sha(P/'evidence/FINAL_NUMERICAL_AUDIT.json'))
save(P/'NUMERICAL_VALIDATION.json',v)
print('INDEPENDENT_FINAL_NUMERICAL_VALIDATION_PASS',flush=True)
