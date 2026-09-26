"""完整推理与路由冻结后运行；仅此处读取原有 development gold。"""
from common import *
import numpy as np
from sklearn.metrics import roc_auc_score,average_precision_score

assert (P/'INFERENCE_COMPLETE.json').exists() and (P/'ALL_ROUTES_FREEZE.json').exists()
for f,h in read(P/'ALL_ROUTES_FREEZE.json')['hashes'].items():assert sha(P/f)==h
for f,h in read(P/'INFERENCE_COMPLETE.json')['files'].items():assert sha(P/f)==h
for f,h in read(P/'ALL_DEPLOYMENTS_FREEZE.json')['hashes'].items():assert sha(P/f)==h
validate_parent()
A={};Q={};expected_keys=set()
for ds in ['obqa','arc']:
    for split in ['fit','cal','dev']:
        ids0=ids(ds,split)
        ar=rows(P/f'actions/{ds}_{split}.jsonl');pr=rows(P/f'probes/{ds}_{split}.jsonl')
        assert len(ar)==3*len(ids0) and len(pr)==len(ids0)
        for r in ar:
            key=(ds,r['id'],r['action']);assert key not in A;A[key]=r
        for r in pr:
            key=(ds,r['id']);assert key not in Q;Q[key]=r
        expected_keys.update(f'{ds}|{split}|{i}|{a}' for i in ids0 for a in ['R','T','C','P'])
assert len(A)==16878 and len(Q)==5626
saved=read(P/'records/successful_keys.json');assert len(saved)==len(set(saved))==22504 and set(saved)==expected_keys
attempts=rows(P/'records/attempts.jsonl')
assert len(attempts)==45008 and {r['key'] for r in attempts if r['event']=='SUCCESS'}==expected_keys

# Existing gold is read only after all four deployments and all dev routes.
native_cfg=read(NATIVE/'frozen_config.json');gold={};gold_index=[]
for ds,split in [('obqa','dev'),('arc','validation')]:
    spec=native_cfg['data'][ds][split];source=Path(spec['path']);assert sha(source)==spec['sha256']
    records=rows(source);qm=query_map(ds);needed=set(ids(ds,'dev'))
    assert {r['id'] for r in records}==needed
    for r in records:
        assert all(r[k]==qm[r['id']][k] for k in ['id','question_stem','choice_labels','choice_text'])
        assert r['gold_answer'] in r['choice_labels'];gold[ds,r['id']]=r['gold_answer']
    gold_index.append({'task':ds,'path':str(source),'sha256':sha(source),'N':len(records)})
save(P/'GOLD_ASSOCIATION_RECEIPT.json',{'utc':utc(),'sources':gold_index,
    'ALL_ROUTES_FREEZE_sha256':sha(P/'ALL_ROUTES_FREEZE.json'),'ARC_test_read':False,
    'fit_cal_gold_read':False,'accuracy_used_for_selection':False})

def rank(ds,ii,ref):
    d=np.array([A[ds,i,'R']['answer']!=A[ds,i,ref]['answer'] for i in ii],dtype=int)
    u=np.array([Q[ds,i]['ProbeMax'] for i in ii])
    both=len(set(d.tolist()))==2
    return {'N':len(ii),'disagreement_count':int(d.sum()),'disagreement_prevalence':float(d.mean()) if len(ii) else None,
        'AUROC':float(roc_auc_score(d,u)) if both else None,'AP':float(average_precision_score(d,u)) if both else None}
def distribution(values):
    v=np.array(values,dtype=float)
    return {'N':len(v),'mean':float(v.mean()),'min':float(v.min()),'p05':float(np.quantile(v,.05)),
        'median':float(np.median(v)),'p95':float(np.quantile(v,.95)),'max':float(v.max()),'exact_zero_count':int((v==0).sum())}

prevalence=[];ranking=[];probes=[];invalid=[];dev=[];per_question=[];timings=[]
for ds in ['obqa','arc']:
    for split in ['fit','cal','dev']:
        allids=ids(ds,split);reps=ids(ds,split,True)
        ps=[Q[ds,i] for i in allids]
        probes.append({'task':ds,'split':split,'N_rows':len(allids),'N_groups':len(reps),
            'score_distribution':distribution([p['ProbeMax'] for p in ps]),
            'label_union_mass_distribution':distribution([p['label_union_mass'] for p in ps]),
            'label_argmax_agreement_with_native_R':sum(Q[ds,i]['argmax_probe_label']==A[ds,i,'R']['answer'] for i in allids),
            'invalid_probe_count':sum(p['invalid_probe'] for p in ps),
            'argmax_is_only_diagnostic':True})
        for action in ['R','T','C']:
            rs=[A[ds,i,action] for i in allids]
            invalid.append({'task':ds,'split':split,'action':action,'N':len(rs),'invalid_count':sum(r['invalid'] for r in rs),'runtime_failure_count':sum(r['runtime_failure'] for r in rs)})
            timings.append({'task':ds,'split':split,'request':action,**distribution([r['latency_ms'] for r in rs]),'identity':'formal action runtime diagnostic; no E2E replay or component cost measurement'})
        timings.append({'task':ds,'split':split,'request':'ProbeMax',**distribution([p['latency_ms'] for p in ps]),'identity':'formal probe runtime diagnostic; no policy-cost recomposition'})
        for ref in ['T','C']:
            prevalence.append({'task':ds,'split':split,'reference':ref,'scope':'independent_representatives',**rank(ds,reps,ref)})
            prevalence.append({'task':ds,'split':split,'reference':ref,'scope':'all_original_rows',**rank(ds,allids,ref)})
            ranking.append({'task':ds,'split':split,'reference':ref,'scope':'all_representatives',**rank(ds,reps,ref)})
            valid=[i for i in reps if not A[ds,i,'R']['invalid'] and not A[ds,i,ref]['invalid']]
            ranking.append({'task':ds,'split':split,'reference':ref,'scope':'both_valid_diagnostic',**rank(ds,valid,ref)})
    for ref in ['T','C']:
        dep=read(P/f'deployments/{ds}_{ref}.json');rr=rows(P/f'development/{ds}_{ref}_routes.jsonl')
        assert [r['id'] for r in rr]==ids(ds,'dev')
        n=len(rr);nR=changed=benefit=harm=neutral=policy_correct=ref_correct=invalid_R=invalid_ref=invalid_policy=0
        for route in rr:
            i=route['id'];m=route['selected']=='R';r=A[ds,i,'R'];b=A[ds,i,ref];answer=r if m else b
            d=r['answer']!=b['answer'];changed_here=bool(m and d)
            yr=int(not r['invalid'] and r['answer']==gold[ds,i]);yb=int(not b['invalid'] and b['answer']==gold[ds,i]);yp=yr if m else yb
            ben=int(changed_here and yr>yb);ha=int(changed_here and yr<yb);ne=int(changed_here and yr==yb)
            nR+=int(m);changed+=int(changed_here);benefit+=ben;harm+=ha;neutral+=ne;policy_correct+=yp;ref_correct+=yb
            invalid_R+=r['invalid'];invalid_ref+=b['invalid'];invalid_policy+=answer['invalid']
            per_question.append({'task':ds,'reference':ref,'id':i,'q':dep['q'],'threshold':dep['threshold'],
                'score':route['score'],'selected':route['selected'],'R_answer':r['answer'],'reference_answer':b['answer'],
                'policy_answer':answer['answer'],'gold_answer':gold[ds,i],'R_correct':yr,'reference_correct':yb,'policy_correct':yp,
                'routed':int(m),'R_reference_disagreement':int(d),'changed':int(changed_here),'benefit':ben,'harm':ha,'neutral_change':ne,
                'R_invalid':r['invalid'],'reference_invalid':b['invalid'],'policy_invalid':answer['invalid']})
        assert benefit+harm+neutral==changed and policy_correct-ref_correct==benefit-harm
        rankrow=rank(ds,ids(ds,'dev'),ref)
        dev.append({'task':ds,'reference':'Text' if ref=='T' else 'C2C','reference_code':ref,
            'q':dep['q'],'threshold':dep['threshold'],'N':n,'route_to_R_count':nR,'coverage':nR/n,
            'changed':changed,'changed/routed':f'{changed}/{nR}',
            'conditional_disagreement':changed/nR if nR else None,'marginal_disagreement':changed/n,
            'AUROC':rankrow['AUROC'],'AP':rankrow['AP'],'disagreement_prevalence':rankrow['disagreement_prevalence'],
            'reference_correct':ref_correct,'policy_correct':policy_correct,'reference_accuracy':ref_correct/n,
            'policy_accuracy':policy_correct/n,'accuracy_difference':(policy_correct-ref_correct)/n,
            'benefit':benefit,'harm':harm,'neutral_change':neutral,
            'invalid_R':invalid_R,'invalid_reference':invalid_ref,'invalid_policy':invalid_policy,'invalid_probe':0,
            'fallback/deploy':'fallback' if dep['q']==0 else 'deploy','mode':dep['mode']})
csvout(P/'summary/compact_summary.csv',dev)
csvout(P/'summary/disagreement_prevalence.csv',prevalence)
csvout(P/'summary/ranking_AUROC_AP.csv',ranking)
csvout(P/'summary/invalid_counts.csv',invalid)
csvout(P/'summary/runtime_diagnostics.csv',timings)
save(P/'summary/probe_diagnostics.json',probes)
write_rows(P/'development/accuracy_decomposition.jsonl',per_question)
save(P/'summary/development_summaries.json',dev)
save(P/'ANALYSIS_COMPLETE.json',{'utc':utc(),'MEDIUM_DEPLOY_COUNT':sum(r['q']>0 for r in dev),
    'nontrivial_deployment_count':sum(0<r['q']<1 for r in dev),'strata_completed':4,
    'action_success_count':len(A),'probe_success_count':len(Q),'accuracy_rows':len(per_question),
    'all_four_results_retained':True,'Stage2_started':False,'new_E2E_or_component_cost_measurements':0})
print('ANALYSIS_COMPLETE',json.dumps(dev),flush=True)
