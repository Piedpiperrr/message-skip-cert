"""只在两个正式 PBS 已终止且所有请求完整时运行；CPU 分组主分析。"""
from common import *
import math,collections
import numpy as np
from scipy.stats import beta,binom
from sklearn.metrics import roc_auc_score,average_precision_score
from risk import thresholds,calibrate,mask,GRID
assert not os.environ.get('CUDA_VISIBLE_DEVICES','')
freeze=validate_freeze();fh=sha(P/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json')
jobs=read(P/'evidence/pbs/TERMINAL_RECEIPTS.json')['jobs']
assert len(jobs)==2 and all(j['job_state']=='F' for j in jobs.values()),'Both shards must terminate before analysis'
for i in ['1','2']:
    assert (P/f'shards/{i}/INFERENCE_COMPLETE.json').exists()
    assert (P/f'shards/{i}/JOB_WORK_COMPLETE.json').exists()
save(P/'evidence/ANALYSIS_START.json',dict(utc=utc(),both_PBS_terminal_before_analysis=True,protocol_freeze_sha256=fh))
expected=read(P/'protocol/QUERY_IDENTITIES.json');population=read(P/'protocol/POPULATION_IDENTITY.json')
meta={r['id']:r for r in rows(P/'inputs/queries_only.jsonl') if r['source_split']=='test'}
records={};keys=set();counts=collections.Counter();outputfiles=[];requestfiles=[]
parser=load_module(P/'protocol/scoring_v2.py','analysis_parser')
for i in ['1','2']:
    shard=P/f'shards/{i}';comp=read(shard/'INFERENCE_COMPLETE.json')
    manifest=read(P/'splits/STAGE1_CANDIDATE_SHARDS.json')['jobs'][int(i)-1]
    allowed={split:set(manifest[split]) for split in ['fit','cal','dev']}
    for rel,h in comp['files'].items():
        path=shard/rel;assert sha(path)==h;outputfiles.append(dict(shard=i,path=str(path.resolve()),sha256=h))
        with path.open() as f:
            for line in f:
                r=json.loads(line);ident=r['id'];a=r['action'];split=r['split'];key=r['key']
                assert ident in allowed[split] and r['shard']==int(i) and r['job_id']==jobs[i]['job_id']
                assert key==f'mmlu_pro|{split}|{ident}|{a}' and key not in keys;keys.add(key)
                assert r['protocol_freeze_sha256']==fh and r['query_sha256']==queryhash(r['query'])==expected[ident]
                assert not r['runtime_failure'] and math.isfinite(r['latency_ms']) and r['latency_ms']>0
                rr=records.setdefault(ident,dict(id=ident,split=split,query_sha256=r['query_sha256']))
                if a=='P':
                    labels=meta[ident]['choice_labels'];assert set(r['p_labels'])==set(labels)
                    assert all(math.isfinite(v) and 0<=v<=1 for v in r['p_labels'].values())
                    assert abs(sum(r['p_labels'].values())-1)<2e-6
                    assert abs(r['ProbeMax']-(1-max(r['p_labels'].values())))<2e-7
                    assert not r['cache_reused'] and not r['invalid_probe'] and r['last_valid_position']==r['input_tokens']-1
                    assert r['probe_ids'][-4:]==[785,4396,4226,374]
                    rr['probe_base_hash']=queryhash(r['probe_ids'][:-4])
                    rr['u']=r['ProbeMax'];rr['probe_latency_ms']=r['latency_ms']
                else:
                    assert a in ['R','T','C'];pr=parser.parse_answer(r['output']['raw_answer'],meta[ident]['choice_labels'])
                    assert pr==r['parsed'] and r['answer']==(pr['answer'] if pr['valid'] else 'INVALID')
                    assert r['invalid']==(not pr['valid'])
                    rr[a]=r['answer'];rr[a+'_invalid']=r['invalid'];rr[a+'_latency_ms']=r['latency_ms']
                    if a=='R':rr['native_R_input_hash']=queryhash(r['native_first_input_ids']['receiver'][0])
                counts[a]+=1
    events=rows(shard/'records/attempts.jsonl');starts=[r['key'] for r in events if r['event']=='START'];success=[r['key'] for r in events if r['event']=='SUCCESS']
    assert len(starts)==len(set(starts))==len(success)==len(set(success))==24064 and set(starts)==set(success)
    requestfiles.append(dict(shard=i,starts=len(starts),success=len(success),sha256=sha(shard/'records/attempts.jsonl')))
assert len(keys)==48128 and dict(counts)==dict(R=12032,T=12032,C=12032,P=12032)
assert set(records)==set(expected) and all(all(k in r for k in ['R','T','C','u']) for r in records.values())
assert all(r['native_R_input_hash']==r['probe_base_hash'] for r in records.values())
save(P/'NUMERICAL_VALIDATION.json',dict(status='COMPLETENESS_PASS_ANALYSIS_PENDING',utc=utc(),rows=12032,actions=36096,probes=12032,
    duplicate_request_keys=0,missing_IDs=0,input_hash_mismatches=0,reparsed_actions=36096,requests=requestfiles,
    primary_groups=11641,raw_rows_not_independent=True,output_files=outputfiles))
save(P/'summary/OUTPUT_SOURCE_INDEX.json',outputfiles)
write_rows(P/'summary/merged_numeric_rows.jsonl',[records[x] for x in ids('fit')+ids('cal')+ids('dev')])
# Threshold construction reads only frozen fit representatives and their u values.
fit=ids('fit',True);cal=ids('cal',True);dev=ids('dev',True)
assert (len(fit),len(cal),len(dev))==(3000,6000,2641)
cutoffs=thresholds([records[x]['u'] for x in fit])
threshold_ledger=[dict(q=q,rank=math.ceil(j*len(fit)/20),N_fit=3000,threshold=t,
    fit_routed=sum(mask([records[x]['u'] for x in fit],q,t)),ties='all retained',fixed_R=q==1) for j,(q,t) in enumerate(zip(GRID,cutoffs),1)]
save(P/'thresholds/fit_thresholds.json',dict(utc=utc(),unit='frozen group representative',thresholds=threshold_ledger,gold_used=False))
deploy={};ledger=[]
for ref,label in [('T','Text'),('C','C2C')]:
    ll,dd=calibrate([records[x]['u'] for x in cal],[records[x]['R']!=records[x][ref] for x in cal],cutoffs)
    for row in ll:row.update(reference=label,stratum='large/MMLU-Pro/'+label)
    ledger+=ll;deploy[ref]=dict(reference=label,**dd)
assert len(ledger)==40
csvout(P/'calibration/40_test_ledger.csv',ledger);save(P/'calibration/40_test_ledger.json',ledger)
save(P/'deployments/deployment_configs.json',dict(utc=utc(),deployments=deploy,accuracy_used_for_selection=False,
    fit_threshold_file_sha256=sha(P/'thresholds/fit_thresholds.json'),calibration_file_sha256=sha(P/'calibration/40_test_ledger.json'),
    per_stratum_ideal_Bonferroni_bound=.02,extension_ideal_Bonferroni_bound=.04,historical_families_combined=False))
# Gold is first opened only after deployments are fixed and written.
import pyarrow.parquet as pq
goldrows=pq.read_table(REVIEW/'dataset/test-00000-of-00001.parquet',columns=['question_id','answer']).to_pylist()
gold={'test:'+str(r['question_id']):r['answer'] for r in goldrows};assert set(gold)==set(records)
def metrics(ii,ref):
    n=len(ii);d=deploy[ref];routed=mask([records[x]['u'] for x in ii],d['q'],d['threshold'])
    disagreements=[records[x]['R']!=records[x][ref] for x in ii]
    scores=[records[x]['u'] for x in ii];nr=sum(routed);changed=sum(a and b for a,b in zip(routed,disagreements))
    reference_correct=policy_correct=benefit=harm=neutral=0
    invalid=collections.Counter()
    for x,on,diff in zip(ii,routed,disagreements):
        r=records[x];a=r['R'] if on else r[ref];cr=r[ref]==gold[x];cp=a==gold[x]
        reference_correct+=cr;policy_correct+=cp
        if on and diff:
            benefit+=int(cp and not cr);harm+=int(cr and not cp);neutral+=int(cr==cp)
        for act in ['R','T','C']:invalid[act]+=r[act+'_invalid']
        invalid['policy']+=a=='INVALID'
    assert changed==benefit+harm+neutral and policy_correct-reference_correct==benefit-harm
    return dict(N=n,reference=d['reference'],q=d['q'],threshold=d['threshold'],mode=d['mode'],routed=nr,
        coverage=nr/n if n else None,changed=changed,changed_over_routed=f'{changed}/{nr}',
        conditional_disagreement=changed/nr if nr else None,marginal_disagreement=changed/n if n else None,
        descriptive_CP_0_95_upper=float(beta.ppf(.95,changed+1,nr-changed)) if nr and changed<nr else (1. if nr else None),
        R_reference_disagreement_count=sum(disagreements),R_reference_disagreement_prevalence=sum(disagreements)/n if n else None,
        AUROC=float(roc_auc_score(disagreements,scores)) if len(set(disagreements))==2 else None,
        AP=float(average_precision_score(disagreements,scores)) if any(disagreements) else None,
        score_direction='higher u predicts R/reference disagreement',reference_correct=reference_correct,policy_correct=policy_correct,
        reference_accuracy=reference_correct/n if n else None,policy_accuracy=policy_correct/n if n else None,
        accuracy_difference=(policy_correct-reference_correct)/n if n else None,benefit=benefit,harm=harm,neutral_change=neutral,
        invalid_R=invalid['R'],invalid_Text=invalid['T'],invalid_C2C=invalid['C'],invalid_policy=invalid['policy'])
allsummary=[];cats=[];ks=[];compact=[]
for split in ['fit','cal','dev']:
    for unit,ii in [('group_representatives',ids(split,True)),('raw_rows_descriptive',ids(split))]:
        for ref in ['T','C']:
            mm=dict(split=split,unit=unit,**metrics(ii,ref))
            if unit=='raw_rows_descriptive':mm['descriptive_CP_0_95_upper']=None
            allsummary.append(mm)
            if split=='dev' and unit=='group_representatives':compact.append(mm)
            for category in sorted(population['category_counts']):
                subset=[x for x in ii if meta[x]['category']==category]
                cm=dict(split=split,unit=unit,category=category,**metrics(subset,ref))
                if unit=='raw_rows_descriptive':cm['descriptive_CP_0_95_upper']=None
                cats.append(cm)
            for K in range(3,11):
                subset=[x for x in ii if meta[x]['K']==K]
                km=dict(split=split,unit=unit,K=K,**metrics(subset,ref))
                if unit=='raw_rows_descriptive':km['descriptive_CP_0_95_upper']=None
                ks.append(km)
csvout(P/'development/split_summaries.csv',allsummary);save(P/'development/split_summaries.json',allsummary)
csvout(P/'development/category_summaries.csv',cats);csvout(P/'development/K_summaries.csv',ks)
csvout(P/'summary/compact_table.csv',compact);save(P/'summary/compact_table.json',compact)
# Independent numerical recomputation of ranks, p values and maximum accepted q.
for r in ledger:
    ref='T' if r['reference']=='Text' else 'C';on=[x for x in cal if r['q']==1 or records[x]['u']<=r['threshold']]
    k=sum(records[x]['R']!=records[x][ref] for x in on)
    assert len(on)==r['routed'] and k==r['changed']
    assert abs(float(binom.cdf(k,len(on),.05)) - r['p_value'])<1e-14 if on else r['p_value']==1
for ref in ['T','C']:
    accepted=[r['q'] for r in ledger if r['reference']==deploy[ref]['reference'] and r['accepted']]
    assert deploy[ref]['q']==max(accepted,default=0)
validation=read(P/'NUMERICAL_VALIDATION.json');validation.update(status='PASS',utc=utc(),fit_reps=3000,cal_reps=6000,dev_reps=2641,
    calibration_tests=40,group_leakage=0,calibration_rank_pvalue_selection_recomputed=True,accuracy_decomposition_reconciled=True,
    MMLU_PRO_DEPLOY_COUNT=sum(d['q']>0 for d in deploy.values()),E2E_jobs=0,scientific_analysis_complete=True)
save(P/'NUMERICAL_VALIDATION.json',validation)
save(P/'ANALYSIS_COMPLETE.json',dict(utc=utc(),status='COMPLETE_MMLU_PRO_STAGE1',MMLU_PRO_DEPLOY_COUNT=validation['MMLU_PRO_DEPLOY_COUNT'],
    metrics=compact,E2E_authorized=False,manuscript_modified=False))
print(json.dumps(dict(status='COMPLETE_MMLU_PRO_STAGE1',compact=compact),ensure_ascii=False),flush=True)
