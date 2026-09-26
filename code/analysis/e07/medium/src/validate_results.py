"""Independent CPU arithmetic and saved-source integrity checks; no GPU/runtime import."""
from common import *
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
import math,random,statistics,numpy as np
cfg=verify_freeze(include_weights=False)
rr=rows(P/'records/e2e_requests.jsonl');assert len(rr)==len({r['key'] for r in rr})==512
g={(r['task'],r['id']):r['gold'] for r in rows(P/'inputs/existing_gold_ANALYSIS_ONLY.jsonl')}
exp={(r['task'],r['id']):r for r in rows(P/'inputs/expected_Stage1_identity_ANALYSIS_ONLY.jsonl')}
sm=list(csv.DictReader((P/'summary/medium_e2e_summary.csv').open()));assert len(sm)==2
identity=list(csv.DictReader((P/'summary/output_identity_checks.csv').open()));assert len(identity)==256
lookup={(r['task'],r['id'],r['arm']):r for r in rr};tests=[]
def eq(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-11,abs_tol=1e-7),(a,b)
for ds in ['obqa','arc']:
    ids=read(P/f'inputs/{ds}_panel_ids.json');s=next(r for r in sm if r['task']==ds)
    c=[lookup[ds,i,'fixed_C'] for i in ids];p=[lookup[ds,i,'policy_C'] for i in ids]
    cv=[r['latency_ms'] for r in c];pv=[r['latency_ms'] for r in p];dif=[a-b for a,b in zip(cv,pv)]
    eq(s['fixed_C2C_mean_latency_ms'],statistics.mean(cv));eq(s['policy_mean_latency_ms'],statistics.mean(pv))
    eq(s['fixed_C2C_median_latency_ms'],statistics.median(cv));eq(s['policy_median_latency_ms'],statistics.median(pv))
    eq(s['paired_mean_saving_ms'],statistics.mean(dif));eq(s['paired_median_saving_ms'],statistics.median(dif))
    assert int(s['route_to_R_count'])==sum(r['selected']=='R' for r in p)
    assert int(s['fixed_C2C_correct'])==sum(r['parsed']['valid'] and r['answer']==g[ds,r['id']] for r in c)
    assert int(s['policy_correct'])==sum(r['parsed']['valid'] and r['answer']==g[ds,r['id']] for r in p)
    indices=np.random.default_rng(0).integers(0,128,size=(2000,128))
    saved=np.load(P/f'summary/{ds}_bootstrap_indices.npz',allow_pickle=False)
    assert np.array_equal(indices,saved['indices']) and saved['ids'].tolist()==ids
    # Independent scalar aggregation/percentile interpolation, without analysis helper or vectorized mean.
    means=sorted(math.fsum(dif[int(k)] for k in sample)/128 for sample in indices)
    def quantile(pct):
        rank=pct*(len(means)-1);lo=math.floor(rank);hi=math.ceil(rank)
        return means[lo]+(rank-lo)*(means[hi]-means[lo])
    lo=quantile(.025);hi=quantile(.975)
    eq(s['descriptive_CI95_low_ms'],lo);eq(s['descriptive_CI95_high_ms'],hi)
    gate='E2E_POSITIVE' if statistics.mean(dif)>0 and lo>0 else 'E2E_UNCERTAIN_OR_NEGATIVE'
    assert s['classification']==gate
    for ordinal,(a,b) in enumerate(zip(c,p)):
        assert a['order_position']==ordinal%2 and b['order_position']==1-ordinal%2
        assert b['selected']==('R' if b['probe']['ProbeMax']<=cfg['deployments'][ds]['threshold'] else 'C')
        assert b['q']==cfg['deployments'][ds]['q'] and b['threshold']==cfg['deployments'][ds]['threshold']
        for r in [a,b]:
            eq(sum(r['parts_ms'].values()),r['latency_ms']);assert r['latency_ms']>0 and not r['runtime_failure']
            assert not r['probe_KV_reuse'] and not r['probe_prefill_reuse'] and r['selected_action_really_executed']
        row=next(r for r in identity if r['task']==ds and r['id']==a['id'])
        target=a if b['selected']=='C' else exp[ds,a['id']]['R']
        raw=target['output']['raw_answer'] if b['selected']=='C' else target['raw_answer']
        col='policy_C_vs_same_round_fixed_C_' if b['selected']=='C' else 'policy_R_vs_Stage1_R_'
        assert (row[col+'raw_match']=='True')==(b['output']['raw_answer']==raw)
        assert (row[col+'parsed_match']=='True')==((b['answer'],b['invalid'])==(target['answer'],target['invalid']))
    tests.append(dict(task=ds,N=128,arithmetic='PASS',independent_scalar_bootstrap='PASS',rotation_64_64='PASS',
        fixed_threshold_application='PASS',output_identity_accounting='PASS',gate=gate))
attempts=rows(P/'records/attempts.jsonl')
assert sum(r['event']=='START' for r in attempts)==sum(r['event']=='SUCCESS' for r in attempts)==512
assert not any(r['event']=='FAILURE' for r in attempts)
assert sum(r['probe'] is not None for r in rr)==256 and sum(r['first_formal_request_global'] for r in rr)==1
assert len({r['job_id'] for r in rr})==1
for source in read(P/'SOURCE_INDEX.json'):
    assert sha(source['path'])==source['sha256'],source['path']
    assert Path(source['path']).stat().st_mtime_ns==source['mtime_ns'],source['path']
save(P/'NUMERICAL_VALIDATION.json',dict(status='PASS',utc=utc(),groups=tests,complete_requests=512,
    online_probes=256,fixed_requests=256,policy_requests=256,paired_questions=256,retries=0,
    first_formal_request_retained=True,paired_bootstrap_seed=0,paired_bootstrap_resamples=2000,
    same_allocation_and_residency=True,source_hashes_and_mtimes_unchanged=True,
    independent_arithmetic=True,gold_after_replay=True,new_calibration=0,new_thresholds=0,new_gold_generation=0,
    ARC_test_reads=0,Text_replays=0,small_large_replays=0,utility_computed=False,
    identity_mismatch_rows=sum(any(r[k]=='False' for k in r if 'match' in k) for r in identity),
    identity_mismatches_retained=True))
print('NUMERICAL_VALIDATION_PASS',flush=True)
