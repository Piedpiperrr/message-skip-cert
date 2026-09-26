"""CPU analysis of actual paired Stage 2 requests, after replay completion. No policy fitting."""
from common import *
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
import numpy as np
start=time.process_time();cfg=read(FREEZE)
complete=read(P/'REPLAY_COMPLETE.json');assert complete['status']=='COMPLETE'
assert sha(P/'records/e2e_requests.jsonl')==complete['requests_sha256']
rr=rows(P/'records/e2e_requests.jsonl');assert len(rr)==512
rm={(r['task'],r['id'],r['arm']):r for r in rr};assert len(rm)==512
gold={(r['task'],r['id']):r for r in rows(P/'inputs/existing_gold_ANALYSIS_ONLY.jsonl')}
old={(r['task'],r['id']):r for r in rows(P/'inputs/expected_Stage1_identity_ANALYSIS_ONLY.jsonl')}
summary=[];paired=[];boots=[];ident=[];runtime=[];proxyrows=[];fixedrows=[];policyrows=[];probetiming=[]
startup=read(P/'evidence/STARTUP.json')
for ds in ['obqa','arc']:
    ids=read(P/f'inputs/{ds}_panel_ids.json');assert len(ids)==len(set(ids))==128
    idx=np.random.default_rng(0).integers(0,128,size=(2000,128))
    np.savez_compressed(P/f'summary/{ds}_bootstrap_indices.npz',ids=np.array(ids),indices=idx,seed=0)
    pairs=[]
    for ordinal,i in enumerate(ids):
        c=rm[ds,i,'fixed_C'];p=rm[ds,i,'policy_C'];e=old[ds,i];g=gold[ds,i]['gold']
        assert c['panel_ordinal']==p['panel_ordinal']==ordinal
        assert not c['runtime_failure'] and not p['runtime_failure']
        assert c['selected']=='C' and p['selected']==('R' if p['probe']['ProbeMax']<=cfg['deployments'][ds]['threshold'] else 'C')
        for r in [c,p]:
            assert abs(sum(r['parts_ms'].values())-r['latency_ms'])<1e-7
            assert r['stage2_freeze_sha256']==sha(FREEZE) and r['selected_action_really_executed']
            assert not r['probe_KV_reuse'] and not r['probe_prefill_reuse']
            assert r['invalid']==(not r['parsed']['valid']) and r['answer']==(r['parsed']['answer'] if r['parsed']['valid'] else 'INVALID')
        pc=int(p['parsed']['valid'] and p['answer']==g);cc=int(c['parsed']['valid'] and c['answer']==g)
        identity=dict(task=ds,id=i,route=p['selected'],policy_C_vs_same_round_fixed_C_raw_match=None,
            policy_C_vs_same_round_fixed_C_parsed_match=None,policy_C_vs_same_round_fixed_C_token_ids_match=None,
            policy_R_vs_Stage1_R_raw_match=None,policy_R_vs_Stage1_R_parsed_match=None,policy_R_vs_Stage1_R_token_ids_match=None)
        if p['selected']=='C':
            identity.update(policy_C_vs_same_round_fixed_C_raw_match=p['output']['raw_answer']==c['output']['raw_answer'],
                policy_C_vs_same_round_fixed_C_parsed_match=(p['answer'],p['invalid'])==(c['answer'],c['invalid']),
                policy_C_vs_same_round_fixed_C_token_ids_match=p['output']['generated_token_ids']==c['output']['generated_token_ids'])
        else:
            identity.update(policy_R_vs_Stage1_R_raw_match=p['output']['raw_answer']==e['R']['raw_answer'],
                policy_R_vs_Stage1_R_parsed_match=(p['answer'],p['invalid'])==(e['R']['answer'],e['R']['invalid']),
                policy_R_vs_Stage1_R_token_ids_match=p['output']['generated_token_ids']==e['R']['generated_token_ids'])
        identity.update(fixed_C_vs_Stage1_C_raw_match=c['output']['raw_answer']==e['C']['raw_answer'],
            fixed_C_vs_Stage1_C_parsed_match=(c['answer'],c['invalid'])==(e['C']['answer'],e['C']['invalid']),
            online_ProbeMax_exactly_matches_Stage1=p['probe']['ProbeMax']==e['ProbeMax'],
            online_probe_input_hash_matches_Stage1=p['probe']['probe_ids_sha256']==e['probe_ids_sha256'],
            online_route_matches_Stage1=p['selected']==e['frozen_stage1_route'],differences_retained_no_retry=True)
        ident.append(identity)
        z=dict(task=ds,id=i,panel_ordinal=ordinal,route=p['selected'],q=p['q'],threshold=p['threshold'],
            fixed_C2C_ms=c['latency_ms'],policy_ms=p['latency_ms'],saving_ms=c['latency_ms']-p['latency_ms'],
            gold=g,fixed_C2C_answer=c['answer'],policy_answer=p['answer'],fixed_C2C_correct=cc,policy_correct=pc,
            accuracy_difference=pc-cc,fixed_C2C_invalid=c['invalid'],policy_invalid=p['invalid'],
            online_probe_ms=p['parts_ms']['online_probe_ms'],selector_ms=p['parts_ms']['selector_ms'],
            probe_selector_ms=p['parts_ms']['online_probe_ms']+p['parts_ms']['selector_ms'],
            first_formal_request_pair=c['first_formal_request_global'] or p['first_formal_request_global'],
            fixed_record_key=c['key'],policy_record_key=p['key'])
        pairs.append(z);paired.append(z)
        fixedrows.append(dict(**c,gold=g,correct=cc));policyrows.append(dict(**p,gold=g,correct=pc))
        probetiming.append(dict(task=ds,id=i,route=p['selected'],ProbeMax=p['probe']['ProbeMax'],threshold=p['threshold'],
            outer_online_probe_ms=p['parts_ms']['online_probe_ms'],selector_ms=p['parts_ms']['selector_ms'],
            saved_native_probe_inner_ms=p['probe']['latency_ms'],probe_ids_sha256=p['probe']['probe_ids_sha256'],
            argmax_probe_label=p['probe']['argmax_probe_label'],probe_argmax_used_as_R_answer=False,cache_reused=False))
    def arr(k):return np.array([r[k] for r in pairs],float)
    savings=arr('saving_ms');lo,hi=map(float,np.quantile(savings[idx].mean(axis=1),[.025,.975]))
    nR=sum(z['route']=='R' for z in pairs);cmean=float(arr('fixed_C2C_ms').mean());pmean=float(arr('policy_ms').mean())
    gate='E2E_POSITIVE' if savings.mean()>0 and lo>0 else 'E2E_UNCERTAIN_OR_NEGATIVE'
    summary.append(dict(task=ds,reference='C2C',N=128,q=cfg['deployments'][ds]['q'],threshold=cfg['deployments'][ds]['threshold'],
        route_to_R_count=nR,coverage=nR/128,fixed_C2C_correct=int(arr('fixed_C2C_correct').sum()),policy_correct=int(arr('policy_correct').sum()),
        fixed_C2C_accuracy=float(arr('fixed_C2C_correct').mean()),policy_accuracy=float(arr('policy_correct').mean()),
        accuracy_difference=float(arr('accuracy_difference').mean()),accuracy_difference_pp=100*float(arr('accuracy_difference').mean()),
        policy_mean_latency_ms=pmean,policy_median_latency_ms=float(np.median(arr('policy_ms'))),
        fixed_C2C_mean_latency_ms=cmean,fixed_C2C_median_latency_ms=float(np.median(arr('fixed_C2C_ms'))),
        paired_mean_saving_ms=float(savings.mean()),paired_median_saving_ms=float(np.median(savings)),
        paired_mean_saving_fraction=float(savings.mean()/cmean),descriptive_CI95_low_ms=lo,descriptive_CI95_high_ms=hi,
        ProbeMax_outer_mean_latency_ms=float(arr('online_probe_ms').mean()),selector_mean_latency_ms=float(arr('selector_ms').mean()),
        ProbeMax_selector_mean_latency_ms=float(arr('probe_selector_ms').mean()),
        fixed_C2C_invalid=int(arr('fixed_C2C_invalid').sum()),policy_invalid=int(arr('policy_invalid').sum()),
        runtime_failures=0,classification=gate,identity='actual complete online requests; exposed development panel descriptive evidence'))
    for metric in ['saving_ms','accuracy_difference']:
        vals=arr(metric);low,high=map(float,np.quantile(vals[idx].mean(axis=1),[.025,.975]))
        boots.append(dict(task=ds,metric=metric,N=128,mean=float(vals.mean()),median=float(np.median(vals)),
            CI95_low=low,CI95_high=high,seed=0,resamples=2000,unit='paired question',
            indices_sha256=sha(P/f'summary/{ds}_bootstrap_indices.npz'),interpretation='descriptive exposed panel; no population guarantee'))
    oldproxy=cfg['prior_proxy'][ds];delta=float(savings.mean()-oldproxy['proxy_ms'])
    proxyrows.append(dict(task=ds,actual_E2E_panel_N=128,proxy_full_dev_N=oldproxy['full_dev_N'],
        prior_proxy_ms=oldproxy['proxy_ms'],prior_displayed_proxy_ms=oldproxy['displayed_proxy_ms'],
        actual_E2E_mean_saving_ms=float(savings.mean()),actual_minus_proxy_ms=delta,
        actual_minus_displayed_proxy_ms=float(savings.mean()-oldproxy['displayed_proxy_ms']),
        directional_description='proxy偏保守（实际节省较大）' if delta>0 else 'proxy偏乐观（实际节省较小）' if delta<0 else '相同',
        scope='full-dev arithmetic versus actual panel; difference mixes population and execution/batch boundaries; no hardware causal attribution'))
    di=[r for r in ident if r['task']==ds]
    for arm in ['fixed_C','policy_C']:
        selected=[r for r in rr if r['task']==ds and r['arm']==arm]
        diag=dict(task=ds,arm=arm,N=len(selected),runtime_failure_count=sum(r['runtime_failure'] for r in selected),
            invalid_count=sum(r['invalid'] for r in selected),first_request_retained=True,
            first_request_ms=selected[0]['latency_ms'],first_request_id=selected[0]['id'],
            order_position_0=sum(r['order_position']==0 for r in selected),order_position_1=sum(r['order_position']==1 for r in selected),
            startup_total_seconds=startup['startup_total_including_runtime_import_seconds'],startup_amortized=False,
            same_residency_same_allocation=True,job_id=selected[0]['job_id'],
            output_identity_mismatch_count=sum(any(v is False for k,v in d.items() if k.endswith('_match') or k.endswith('_Stage1')) for d in di),
            online_probe_invalid_count=sum(r['probe']['invalid_probe'] for r in selected if r['probe']))
        for part in selected[0]['parts_ms']:diag[part+'_mean']=float(np.mean([r['parts_ms'][part] for r in selected]))
        runtime.append(diag)
write_rows(P/'records/fixed_C2C_requests_with_correctness.jsonl',fixedrows)
write_rows(P/'records/policy_requests_with_correctness.jsonl',policyrows)
write_rows(P/'records/paired_per_question.jsonl',paired)
for name,data in [('medium_e2e_summary',summary),('paired_latency_bootstrap',boots),('proxy_vs_e2e',proxyrows),
        ('runtime_diagnostics',runtime),('output_identity_checks',ident),('probe_timing',probetiming),('paired_per_question',paired)]:
    csvout(P/f'summary/{name}.csv',data)
save(P/'ANALYSIS_COMPLETE.json',dict(status='PASS',utc=utc(),actual_requests=512,online_probes=256,pairs=256,
    gold_associated_after_replay=True,CPU_process_seconds=time.process_time()-start,
    classifications={r['task']:r['classification'] for r in summary}))
print(json.dumps(summary,ensure_ascii=False,indent=2))
