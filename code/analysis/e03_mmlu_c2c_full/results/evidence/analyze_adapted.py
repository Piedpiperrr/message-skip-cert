"""已完成实际四臂请求的 CPU 分析；不选择 policy，不拼接 Stage1 latency。"""
from common import *
import math,collections
import numpy as np
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
cfg=verify_freeze();resource=read(R/'RESOURCE_LEDGER_from_qstat.json');assert resource['job_state']=='F'
complete=read(P/'REPLAY_COMPLETE.json');assert complete['status']=='COMPLETE' and (P/'JOB_WORK_COMPLETE.json').exists()
assert sha(P/'records/four_arm_requests.jsonl')==complete['requests_sha256']
assert sha(P/'records/two_policy_probes.jsonl')==complete['probes_sha256']
assert sha(P/'records/attempts.jsonl')==complete['attempts_sha256']
save(R/'evidence/ANALYSIS_START.json',dict(utc=utc(),job_terminal_before_analysis=True,freeze_sha256=sha(FREEZE)))
rr=rows(P/'records/four_arm_requests.jsonl');pp=rows(P/'records/two_policy_probes.jsonl');attempts=rows(P/'records/attempts.jsonl')
ids=read(P/'inputs/panel_ids.json');panel=read(P/'protocol/PANEL_MANIFEST.json');meta={r['id']:r for r in panel['rows']}
N=len(ids);NREQ=N*len(ARMS);NPOL=N*sum(a.startswith('policy') for a in ARMS);REFS=[(x,{'T':'Text','C':'C2C'}[x]) for x in dict.fromkeys(a[-1] for a in ARMS)]  # E3 FULL: derived counts
assert len(rr)==NREQ and len(pp)==NPOL and len({r['key'] for r in rr})==NREQ and len({r['key'] for r in pp})==NPOL
assert len(ids)==len(set(ids))==cfg['expected_counts']['questions']
rm={(r['id'],r['arm']):r for r in rr};pm={r['key']:r for r in pp}
assert set(rm)=={(i,a) for i in ids for a in ARMS}
assert [r['key'] for r in rr]==[f'mmlu_pro|{i}|{a}' for n,i in enumerate(ids) for a in order_for(n)]
assert [r['key'] for r in attempts if r['event']=='START']==[r['key'] for r in rr]==[r['key'] for r in attempts if r['event']=='SUCCESS']
assert len(attempts)==2*NREQ and sum(r['first_formal_request_global'] for r in rr)==1 and rr[0]['first_formal_request_global']
parser=load_module(P/'protocol/scoring_v2.py','stage2_analysis_parser')
for r in rr:
    ispolicy=r['arm'].startswith('policy');ref=r['arm'][-1]
    assert r['query_sha256']==meta[r['id']]['query_sha256'] and r['stage2_freeze_sha256']==sha(FREEZE)
    assert r['job_id']==resource['job_id'] and r['panel_ordinal']==ids.index(r['id'])
    assert order_for(r['panel_ordinal'])[r['order_position']]==r['arm']
    assert all(math.isfinite(v) and v>=0 for v in r['parts_ms'].values()) and r['latency_ms']>0
    assert abs(sum(r['parts_ms'].values())-r['latency_ms'])<1e-7
    assert r['selected_action_really_executed'] and not r['runtime_failure'] and not r['probe_KV_reuse'] and not r['probe_prefill_reuse']
    legal=list('ABCDEFGHIJ')[:meta[r['id']]['K']];parsed=parser.parse_answer(r['output']['raw_answer'],legal)
    assert parsed==r['parsed'] and r['invalid']==(not parsed['valid']) and r['answer']==(parsed['answer'] if parsed['valid'] else 'INVALID')
    if ispolicy:
        pr=r['probe'];assert r['threshold']==THRESHOLD and r['policy_q']==.4
        assert set(pr['p_labels'])==set(legal) and abs(sum(pr['p_labels'].values())-1)<2e-6
        assert abs(pr['ProbeMax']-(1-max(pr['p_labels'].values())))<2e-7
        assert r['selected']==('R' if pr['ProbeMax']<=THRESHOLD else ref)
        assert not pr['cache_reused'] and not pr['invalid_probe'] and pr['last_valid_position']==pr['input_tokens']-1
        assert all(pm[r['key']][k]==v for k,v in pr.items()) and pm[r['key']]['route']==r['selected']
    else:assert r['probe'] is None and r['selected']==ref
save(R/'NUMERICAL_VALIDATION.json',dict(utc=utc(),status='FULL_COMPLETENESS_PASS_ANALYSIS_PENDING',requests=NREQ,online_probes=NPOL,
    N=N,duplicate_request_keys=0,missing_requests=0,input_hash_mismatches=0,reparsed_outputs=NREQ,runtime_failures=0,retries=0))
# Existing gold and Stage1 outputs are first linked after full replay completeness.
import pyarrow.parquet as pq
gold={f'test:{r["question_id"]}':r['answer'] for r in pq.read_table(REVIEW/'dataset/test-00000-of-00001.parquet',columns=['question_id','answer']).to_pylist()}
old={i:{} for i in ids}
with (STAGE1/'shards/2/actions/dev.jsonl').open() as f:
    for line in f:
        r=json.loads(line)
        if r['id'] in old:old[r['id']][r['action']]=r
with (STAGE1/'shards/2/probes/dev.jsonl').open() as f:
    for line in f:
        r=json.loads(line)
        if r['id'] in old:old[r['id']]['P']=r
assert all(set(v)==set('RTCP') for v in old.values())
startup=read(P/'evidence/STARTUP.json');b=np.load(P/'protocol/bootstrap_indices.npz');idx=b['indices'];assert b['ids'].tolist()==ids and idx.shape==(2000,N)
assert np.array_equal(idx,np.random.default_rng(0).integers(0,N,size=(2000,N)))
paired=[];ident=[];summary=[];boot=[];runtime=[];correct_rows=[];probe_rows=[]
for ref,label in REFS:
    pairs=[]
    for ordinal,i in enumerate(ids):
        fixed=rm[i,'fixed_'+ref];policy=rm[i,'policy_'+ref];route=policy['selected'];expected=fixed if route==ref else old[i]['R']
        match=dict(reference=label,id=i,panel_ordinal=ordinal,route=route,expected_source='same-round fixed reference' if route==ref else 'Stage1 native R',
            expected_answer=expected['answer'],policy_answer=policy['answer'],raw_answer_match=policy['output']['raw_answer']==expected['output']['raw_answer'],
            canonical_parsed_match=(policy['answer'],policy['invalid'])==(expected['answer'],expected['invalid']),
            full_parsed_record_match=policy['parsed']==expected['parsed'],generated_token_ids_match=policy['output']['generated_token_ids']==expected['output']['generated_token_ids'],
            helper_message_match=(policy['output'].get('helper_message')==expected['output'].get('helper_message')) if route=='T' else None,
            fixed_vs_Stage1_raw_match=fixed['output']['raw_answer']==old[i][ref]['output']['raw_answer'],
            fixed_vs_Stage1_parsed_match=(fixed['answer'],fixed['invalid'])==(old[i][ref]['answer'],old[i][ref]['invalid']),
            online_probe_equals_Stage1=policy['probe']['ProbeMax']==old[i]['P']['ProbeMax'],
            online_probe_input_hash_matches_Stage1=policy['probe']['probe_ids_sha256']==old[i]['P']['probe_ids_sha256'],
            online_route_matches_Stage1=(route=='R')==(old[i]['P']['ProbeMax']<=THRESHOLD),differences_retained_without_retry=True)
        match['required_output_identity_pass']=all(match[k] for k in ['raw_answer_match','canonical_parsed_match','full_parsed_record_match','generated_token_ids_match']) and match['helper_message_match'] is not False
        ident.append(match)
        fc=int(not fixed['invalid'] and fixed['answer']==gold[i]);pc=int(not policy['invalid'] and policy['answer']==gold[i])
        z=dict(reference=label,id=i,panel_ordinal=ordinal,group_hash=meta[i]['group_hash'],category=meta[i]['category'],K=meta[i]['K'],
            route=route,q=.4,threshold=THRESHOLD,fixed_ms=fixed['latency_ms'],policy_ms=policy['latency_ms'],saving_ms=fixed['latency_ms']-policy['latency_ms'],
            fixed_correct=fc,policy_correct=pc,accuracy_difference=pc-fc,fixed_answer=fixed['answer'],policy_answer=policy['answer'],gold=gold[i],
            fixed_invalid=fixed['invalid'],policy_invalid=policy['invalid'],online_probe_ms=policy['parts_ms']['online_probe_ms'],selector_ms=policy['parts_ms']['selector_ms'],
            first_formal_request_in_pair=fixed['first_formal_request_global'] or policy['first_formal_request_global'],fixed_key=fixed['key'],policy_key=policy['key'])
        pairs.append(z);paired.append(z)
        for r,c in [(fixed,fc),(policy,pc)]:correct_rows.append(dict(**r,gold=gold[i],correct=c))
        probe_rows.append(dict(reference=label,id=i,key=policy['key'],online_probe_ms=z['online_probe_ms'],selector_ms=z['selector_ms'],
            saved_inner_probe_ms=policy['probe']['latency_ms'],ProbeMax=policy['probe']['ProbeMax'],route=route,probe_shared=False))
    def arr(key):return np.asarray([r[key] for r in pairs],dtype=float)
    savings=arr('saving_ms');bootmeans=savings[idx].mean(axis=1);lo,hi=map(float,np.quantile(bootmeans,[.025,.975],method='linear'))
    for n,x in enumerate(bootmeans):boot.append(dict(reference=label,resample=n,mean_saving_ms=float(x),seed=0,N=N))
    nR=sum(z['route']=='R' for z in pairs);fmean=float(arr('fixed_ms').mean());pmean=float(arr('policy_ms').mean());mean=float(savings.mean())
    summary.append(dict(reference=label,N=N,q=.4,threshold=THRESHOLD,route_to_R_count=nR,coverage=nR/N,
        fixed_reference_correct=int(arr('fixed_correct').sum()),policy_correct=int(arr('policy_correct').sum()),
        fixed_reference_accuracy=float(arr('fixed_correct').mean()),policy_accuracy=float(arr('policy_correct').mean()),accuracy_difference_pp=100*float(arr('accuracy_difference').mean()),
        policy_mean_ms=pmean,policy_median_ms=float(np.median(arr('policy_ms'))),fixed_mean_ms=fmean,fixed_median_ms=float(np.median(arr('fixed_ms'))),
        paired_mean_saving_ms=mean,paired_median_saving_ms=float(np.median(savings)),mean_saving_fraction=mean/fmean,
        descriptive_bootstrap95_low_ms=lo,descriptive_bootstrap95_high_ms=hi,bootstrap_seed=0,bootstrap_resamples=2000,
        probe_mean_ms=float(arr('online_probe_ms').mean()),selector_mean_ms=float(arr('selector_ms').mean()),
        fixed_invalid=int(arr('fixed_invalid').sum()),policy_invalid=int(arr('policy_invalid').sum()),runtime_failures=0,
        identity_mismatches=sum(not x['required_output_identity_pass'] for x in ident if x['reference']==label),
        classification='E2E_POSITIVE' if mean>0 and lo>0 else 'E2E_UNCERTAIN_OR_NEGATIVE'))
for arm in ARMS:
    selected=[r for r in rr if r['arm']==arm]
    diagnostic=dict(arm=arm,N=len(selected),job_id=resource['job_id'],runtime_failures=sum(r['runtime_failure'] for r in selected),
        invalid=sum(r['invalid'] for r in selected),first_arm_request_id=selected[0]['id'],first_arm_request_ms=selected[0]['latency_ms'],
        first_formal_request_kept=True,independent_online_probe_count=sum(r['probe'] is not None for r in selected),
        startup_total_seconds=startup['startup_total_including_runtime_import_seconds'],startup_amortized=False,same_allocation_same_residency=True)
    for pos in range(len(ARMS)):diagnostic['order_position_'+str(pos)]=sum(r['order_position']==pos for r in selected)
    for key in selected[0]['parts_ms']:diagnostic[key+'_mean']=float(np.mean([r['parts_ms'][key] for r in selected]))
    runtime.append(diagnostic)
write_rows(R/'records/four_arm_requests_with_correctness.jsonl',correct_rows)
write_rows(R/'records/paired_per_question.jsonl',paired)
for name,data in [('mmlu_pro_e2e_summary',summary),('paired_per_question',paired),('runtime_diagnostics',runtime),('output_identity_checks',ident),('probe_timing',probe_rows),('bootstrap_resample_means',boot)]:csvout(R/f'summary/{name}.csv',data)
csvout(R/'summary/paired_latency_bootstrap.csv',[dict(reference=r['reference'],N=N,paired_mean_saving_ms=r['paired_mean_saving_ms'],paired_median_saving_ms=r['paired_median_saving_ms'],
    CI95_low_ms=r['descriptive_bootstrap95_low_ms'],CI95_high_ms=r['descriptive_bootstrap95_high_ms'],seed=0,resamples=2000,unit='paired question',
    indices_sha256=sha(P/'protocol/bootstrap_indices.npz'),interval='percentile mean; exposed panel descriptive') for r in summary])
save(R/'summary/mmlu_pro_e2e_summary.json',summary)
csvout(R/'summary/panel_category_distribution.csv',[dict(category=k,N=v) for k,v in panel['category_counts'].items()])
csvout(R/'summary/panel_K_distribution.csv',[dict(K=k,N=v) for k,v in panel['K_distribution'].items()])
v=read(R/'NUMERICAL_VALIDATION.json');v.update(status='PASS',utc=utc(),same_allocation=True,one_residency=True,each_arm_each_position_balanced=True,
    independent_online_probes_per_policy=N,no_probe_KV_or_prefill_reuse=True,first_formal_request_kept=True,gold_linked_after_complete_replay=True,
    scientific_analysis_complete=True,output_identity_mismatches=sum(not r['required_output_identity_pass'] for r in ident),
    **{'MMLU_'+r['reference'].upper()+'_E2E':r['classification'] for r in summary})
save(R/'NUMERICAL_VALIDATION.json',v)
save(R/'ANALYSIS_COMPLETE.json',dict(utc=utc(),status='COMPLETE_MMLU_PRO_STAGE2',classifications={r['reference']:r['classification'] for r in summary},
    no_policy_selection=True,no_new_calibration=True,no_next_task=True))
print(json.dumps(summary,ensure_ascii=False),flush=True)
