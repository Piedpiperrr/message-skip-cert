"""从逐题记录独立复算：不调用执行器的风险/排名函数。"""
from common import *
import math,struct
import numpy as np

assert (P/'ANALYSIS_COMPLETE.json').exists()
validate_parent();parser=load_module(PARENT/'protocol/scoring_v2.py','validation_parser')
def cdf(k,n,p):
    if n==0 or k==n:return 1.
    if p<=0:return 1.
    if p>=1:return 0.
    terms=[math.lgamma(n+1)-math.lgamma(j+1)-math.lgamma(n-j+1)+j*math.log(p)+(n-j)*math.log1p(-p) for j in range(k+1)]
    m=max(terms);return min(1.,math.exp(m)*sum(math.exp(t-m) for t in terms))
def cp_upper(k,n):
    if not n or k==n:return 1.
    lo,hi=0.,1.
    for _ in range(70):
        mid=(lo+hi)/2
        if cdf(k,n,mid)>.001:lo=mid
        else:hi=mid
    return (lo+hi)/2
def rank_metrics(values,labels):
    n=len(labels);pos=sum(labels);neg=n-pos
    if not pos or not neg:return None,None
    order=sorted(range(n),key=values.__getitem__)
    rank_sum=0.;at=0
    while at<n:
        end=at+1
        while end<n and values[order[end]]==values[order[at]]:end+=1
        rank_sum+=((at+1+end)/2)*sum(labels[i] for i in order[at:end]);at=end
    auc=(rank_sum-pos*(pos+1)/2)/(pos*neg)
    order=sorted(range(n),key=values.__getitem__,reverse=True)
    ap=0.;tp=0;at=0
    while at<n:
        end=at+1
        while end<n and values[order[end]]==values[order[at]]:end+=1
        gain=sum(labels[i] for i in order[at:end]);tp+=gain
        ap+=(gain/pos)*(tp/end);at=end
    return auc,ap
def close(a,b,tol=1e-10):
    assert (a is None and b is None) or (a is not None and b is not None and abs(a-b)<tol),(a,b)

A={};Q={};checks={};cal_count=0;max_p_error=0.;max_cp_error=0.
for ds in ['obqa','arc']:
    qm=query_map(ds)
    for split in ['fit','cal','dev']:
        aa=rows(P/f'actions/{ds}_{split}.jsonl');pp=rows(P/f'probes/{ds}_{split}.jsonl')
        assert len(aa)==3*len(ids(ds,split)) and len(pp)==len(ids(ds,split))
        for r in aa:
            key=(ds,r['id'],r['action']);assert key not in A;A[key]=r
            assert r['query']==qm[r['id']]
            parsed=parser.parse_answer(r['output']['raw_answer'],r['query']['choice_labels'])
            assert parsed==r['parsed'] and r['answer']==(parsed['answer'] if parsed['valid'] else 'INVALID')
            assert r['invalid']==(not parsed['valid']) and not r['runtime_failure']
        for r in pp:
            key=(ds,r['id']);assert key not in Q;Q[key]=r
            assert r['query']==qm[r['id']]
            packed=struct.pack('<'+'q'*len(r['probe_ids']),*r['probe_ids'])
            assert hashlib.sha256(packed).hexdigest()==r['probe_ids_sha256']
            probs=r['p_labels'];assert list(probs)==r['query']['choice_labels']
            assert abs(sum(probs.values())-1)<2e-6
            assert float(np.float32(1)-np.float32(max(probs.values())))==r['ProbeMax']
            assert max(probs,key=probs.get)==r['argmax_probe_label'] and not r['invalid_probe']
    f=read(P/f'thresholds/{ds}.json');v=sorted(Q[ds,i]['ProbeMax'] for i in ids(ds,'fit',True))
    expected=[v[math.ceil(j*len(v)/20)-1] for j in range(1,20)]+['Infinity']
    assert f['thresholds']==expected
    for ref in ['T','C']:
        with (P/f'calibration/{ds}_{ref}.csv').open() as handle:led=list(csv.DictReader(handle))
        assert len(led)==20
        acceptable=[]
        for j,row in enumerate(led,1):
            q=j/20;t=expected[j-1];ii=ids(ds,'cal',True)
            rr=ii if j==20 else [i for i in ii if Q[ds,i]['ProbeMax']<=t]
            n=len(rr);k=sum(A[ds,i,'R']['answer']!=A[ds,i,ref]['answer'] for i in rr)
            p=cdf(k,n,.05);cp=cp_upper(k,n)
            assert n==int(row['routed']) and k==int(row['changed']) and float(row['q'])==q
            close(p,float(row['p_value']));close(cp,float(row['CP_upper_0_999']),1e-9)
            max_p_error=max(max_p_error,abs(p-float(row['p_value'])));max_cp_error=max(max_cp_error,abs(cp-float(row['CP_upper_0_999'])))
            assert (p<=.001)==(row['accepted']=='True')
            if p<=.001:acceptable.append(q)
            cal_count+=1
        dep=read(P/f'deployments/{ds}_{ref}.json')
        assert dep['q']==max(acceptable,default=0.)
        assert dep['threshold']==(expected[int(dep['q']*20)-1] if dep['q'] else None)
        routes=rows(P/f'development/{ds}_{ref}_routes.jsonl')
        for r in routes:
            routed=dep['q']==1 or (0<dep['q']<1 and Q[ds,r['id']]['ProbeMax']<=dep['threshold'])
            assert r['selected']==('R' if routed else ref)

gold={};nc=read(NATIVE/'frozen_config.json')
for ds,s in [('obqa','dev'),('arc','validation')]:
    source=Path(nc['data'][ds][s]['path']);assert sha(source)==nc['data'][ds][s]['sha256']
    gold.update({(ds,r['id']):r['gold_answer'] for r in rows(source)})
for row in read(P/'summary/development_summaries.json'):
    ds=row['task'];ref=row['reference_code'];rr=[r for r in rows(P/'development/accuracy_decomposition.jsonl') if r['task']==ds and r['reference']==ref]
    for r in rr:
        i=r['id'];a=A[ds,i,'R'];b=A[ds,i,ref]
        yr=int(not a['invalid'] and a['answer']==gold[ds,i]);yb=int(not b['invalid'] and b['answer']==gold[ds,i])
        assert r['gold_answer']==gold[ds,i] and r['R_correct']==yr and r['reference_correct']==yb
        assert r['policy_correct']==(yr if r['routed'] else yb)
        assert r['changed']==int(bool(r['routed']) and a['answer']!=b['answer'])
        assert r['benefit']==int(bool(r['changed']) and yr>yb)
        assert r['harm']==int(bool(r['changed']) and yr<yb)
        assert r['neutral_change']==int(bool(r['changed']) and yr==yb)
    for field,target in [('routed','route_to_R_count'),('changed','changed'),('benefit','benefit'),('harm','harm'),('neutral_change','neutral_change'),('policy_correct','policy_correct'),('reference_correct','reference_correct')]:
        assert sum(r[field] for r in rr)==row[target]
    assert row['policy_correct']-row['reference_correct']==row['benefit']-row['harm']
    assert row['changed']==row['benefit']+row['harm']+row['neutral_change']
    close(row['coverage'],row['route_to_R_count']/len(rr))
    close(row['conditional_disagreement'],row['changed']/row['route_to_R_count'] if row['route_to_R_count'] else None)
    auc,ap=rank_metrics([Q[ds,r['id']]['ProbeMax'] for r in rr],[int(A[ds,r['id'],'R']['answer']!=A[ds,r['id'],ref]['answer']) for r in rr])
    close(auc,row['AUROC']);close(ap,row['AP'])
with (P/'summary/disagreement_prevalence.csv').open() as f:
    for r in csv.DictReader(f):
        ds=r['task'];ref=r['reference'];ii=ids(ds,r['split'],r['scope']=='independent_representatives')
        d=[int(A[ds,i,'R']['answer']!=A[ds,i,ref]['answer']) for i in ii]
        assert len(ii)==int(r['N']) and sum(d)==int(r['disagreement_count'])
        auc,ap=rank_metrics([Q[ds,i]['ProbeMax'] for i in ii],d)
        close(auc,float(r['AUROC']) if r['AUROC'] else None);close(ap,float(r['AP']) if r['AP'] else None)
assert len(A)==16878 and len(Q)==5626 and cal_count==80
checks={k:True for k in ['parent_freeze_identity','16878_unique_actions','5626_unique_probes','parser_replay',
    'query_ID_identity','probe_token_ID_hashes','FP32_ProbeMax_reconstruction','integer_fit_thresholds','whole_tie_inclusion',
    '80_calibration_tests_independent_CDF','CP999_independent_bisection','maximum_accepted_q','dev_route_reconstruction',
    'AUROC_tie_rank_and_AP_independent','accuracy_benefit_harm_neutral','prevalence_counts','all_four_strata_retained']}
save(P/'NUMERICAL_VALIDATION.json',{'status':'PASS','utc':utc(),'checks':checks,'new_inference_for_validation':0,
    'max_CDF_absolute_error':max_p_error,'max_CP_upper_absolute_error':max_cp_error,
    'action_success_count':16878,'ProbeMax_success_count':5626,'calibration_tests':80})
print('NUMERICAL_VALIDATION_PASS',flush=True)
