"""完整 Stage1 后的 CPU 交付复核；不改冻结分析、选择规则或模型输出。"""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from common import *
import math,collections
import numpy as np
from scipy.special import logsumexp,gammaln,betainc
from scipy.optimize import brentq
from scipy.stats import rankdata
assert not os.environ.get('CUDA_VISIBLE_DEVICES','')
f=validate_freeze();v=read(P/'NUMERICAL_VALIDATION.json');assert v['status']=='PASS'
resource=read(P/'RESOURCE_LEDGER.json');assert resource['both_terminal']
assert all(j['terminal_exit_status']==0 for j in resource['jobs'].values())
def dt(t):return datetime.datetime.fromisoformat(t)
def pbsdt(t):return datetime.datetime.strptime(t,'%a %b %d %H:%M:%S %Y').replace(tzinfo=datetime.timezone.utc)
barrier=read(P/'BOTH_SUBMISSIONS_CONFIRMED.json')
for i in ['1','2']:
    first=read(P/f'shards/{i}/OUTCOMES_OBSERVED.json');clear=read(P/f'shards/{i}/EXECUTION_CLEARANCE.json')
    assert dt(f['utc'])<dt(barrier['utc'])<dt(clear['utc'])<=dt(first['utc'])
    for job in barrier['jobs'].values():assert dt(job['submission_utc'])<dt(first['utc'])
    assert clear['protocol_freeze_sha256']==sha(P/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json')
    assert clear['both_submissions_sha256']==sha(P/'BOTH_SUBMISSIONS_CONFIRMED.json')
start=read(P/'evidence/ANALYSIS_START.json')
assert dt(start['utc'])>max(pbsdt(j['end']) for j in resource['jobs'].values())
assert dt(start['utc'])<=dt(read(P/'thresholds/fit_thresholds.json')['utc'])<=dt(read(P/'deployments/deployment_configs.json')['utc'])
records={r['id']:r for r in rows(P/'summary/merged_numeric_rows.jsonl')};assert len(records)==12032
fit=ids('fit',True);cal=ids('cal',True);dev=ids('dev',True)
gg=[g for split in ['fit','cal','dev'] for g in read(P/f'splits/{split}_groups.json')]
assert len({g['group_hash'] for g in gg})==11641
assert len(set(fit+cal+dev))==11641
thresholds=read(P/'thresholds/fit_thresholds.json')['thresholds'];ordered=sorted(records[x]['u'] for x in fit)
for j,row in enumerate(thresholds,1):
    rank=(j*3000+19)//20;assert row['rank']==rank
    assert row['threshold']==('Infinity' if j==20 else ordered[rank-1])
led=read(P/'calibration/40_test_ledger.json');deploy=read(P/'deployments/deployment_configs.json')['deployments']
cal_checks=[]
for row in led:
    ref={'Text':'T','C2C':'C'}[row['reference']]
    ii=[x for x in cal if row['q']==1 or records[x]['u']<=row['threshold']]
    n=len(ii);k=sum(records[x]['R']!=records[x][ref] for x in ii)
    assert (n,k)==(row['routed'],row['changed'])
    z=np.arange(k+1,dtype=float)
    logp=float(logsumexp(gammaln(n+1)-gammaln(z+1)-gammaln(n-z+1)+z*math.log(.05)+(n-z)*math.log(.95)))
    explicit_p=math.exp(logp)
    assert abs(explicit_p-row['p_value'])<=2e-10
    assert (explicit_p<=.001)==row['accepted']
    upper=brentq(lambda p:betainc(k+1,n-k,p)-.999,0,1,xtol=1e-14) if k<n else 1.
    assert abs(upper-row['CP_upper_0_999'])<2e-11
    cal_checks.append(dict(reference=row['reference'],q=row['q'],routed=n,changed=k,explicit_binomial_sum=explicit_p,CP_betainc_root=upper,pass_=True))
for ref in ['T','C']:
    assert deploy[ref]['q']==max((r['q'] for r in led if r['reference']==deploy[ref]['reference'] and r['accepted']),default=0)
summaries=read(P/'development/split_summaries.json');keys=['N','routed','changed','reference_correct','policy_correct','benefit','harm','neutral_change','R_reference_disagreement_count','invalid_R','invalid_Text','invalid_C2C','invalid_policy']
aggregate_checks=[]
for name,dim,levels in [('category_summaries.csv','category',14),('K_summaries.csv','K',8)]:
    rr=list(csv.DictReader((P/'development'/name).open()));assert len(rr)==len(summaries)*levels
    for summary in summaries:
        subset=[r for r in rr if all(r[k]==summary[k] for k in ['split','unit','reference'])]
        assert len(subset)==levels and len({r[dim] for r in subset})==levels
        for key in keys:assert sum(int(r[key]) for r in subset)==summary[key],(name,key,summary)
    aggregate_checks.append(dict(file=name,rows=len(rr),partition_totals_match=True))
# Rank-sum AUROC and score-tie-group AP independently verify sklearn results.
rank_checks=[]
for summary in summaries:
    ii=ids(summary['split'],summary['unit']=='group_representatives');ref={'Text':'T','C2C':'C'}[summary['reference']]
    scores=np.array([records[x]['u'] for x in ii]);y=np.array([int(records[x]['R']!=records[x][ref]) for x in ii])
    n1=int(y.sum());n0=len(y)-n1;ranks=rankdata(scores,method='average')
    auc=(float(ranks[y==1].sum())-n1*(n1+1)/2)/(n1*n0)
    assert abs(auc-summary['AUROC'])<1e-12
    grouped=collections.defaultdict(list)
    for s,yy in zip(scores,y):grouped[float(s)].append(int(yy))
    seen=tp=0;ap=0.
    for s in sorted(grouped,reverse=True):
        ys=grouped[s];positive=sum(ys);seen+=len(ys);tp+=positive;ap+=positive/n1*tp/seen
    assert abs(ap-summary['AP'])<1e-12
    assert summary['changed']==summary['benefit']+summary['harm']+summary['neutral_change']
    assert summary['policy_correct']-summary['reference_correct']==summary['benefit']-summary['harm']
    if summary['unit']=='raw_rows_descriptive':assert summary['descriptive_CP_0_95_upper'] is None
    rank_checks.append(dict(split=summary['split'],unit=summary['unit'],reference=summary['reference'],AUROC_rank_sum=auc,AP_tie_groups=ap))
# Immutable source JSONL hashes have already been verified by frozen analyze.py;
# per-question gold decomposition is checked again from compact persisted outputs.
import pyarrow.parquet as pq
gold={'test:'+str(r['question_id']):r['answer'] for r in pq.read_table(REVIEW/'dataset/test-00000-of-00001.parquet',columns=['question_id','answer']).to_pylist()}
for summary in summaries:
    ii=ids(summary['split'],summary['unit']=='group_representatives');ref={'Text':'T','C2C':'C'}[summary['reference']];d=deploy[ref]
    c=collections.Counter()
    for x in ii:
        r=records[x];on=d['q']==1 or (d['q']>0 and r['u']<=d['threshold']);policy=r['R'] if on else r[ref]
        c['reference_correct']+=r[ref]==gold[x];c['policy_correct']+=policy==gold[x]
        if policy!=r[ref]:
            c['benefit']+=policy==gold[x] and r[ref]!=gold[x]
            c['harm']+=policy!=gold[x] and r[ref]==gold[x]
            c['neutral_change']+=(policy==gold[x])==(r[ref]==gold[x])
    for k in ['reference_correct','policy_correct','benefit','harm','neutral_change']:assert c[k]==summary[k]
mech=[]
for i in [1,2]:
    s=P/f'shards/{i}';a=read(s/'PBS_ALLOCATION_RECEIPT.json');g=read(s/'GPU_MECHANICAL_PASS.json');c=read(s/'CUDA_DEVICE_RECEIPT.json')
    assert a['allocation_identity']['status']=='PASS' and c['device_count']==2 and g['status']=='PASS' and g['projector_count']==36
    assert g['project_question_reads']==0 and not g['scientific_metrics_computed']
    assert all(ch['probability_sum_valid'] and not ch['cache_reused'] for ch in g['probe_structural_checks'])
    mech.append(dict(shard=i,status='PASS',PBS_GPUs=2,strict_projectors=36))
receipt=dict(utc=utc(),status='PASS',checks='CPU only; no new inference; no frozen code/config/output changes',
    freeze_and_two_submissions_before_first_outcomes=True,analysis_after_both_terminal=True,fit_then_cal_then_deployment_order=True,
    representative_counts=[len(fit),len(cal),len(dev)],group_overlap=0,independent_binomial_CP_checks=cal_checks,
    rank_sum_AUROC_and_tie_group_AP=rank_checks,category_K_partitions=aggregate_checks,accuracy_decomposition_recomputed=True,
    mechanical_receipts=mech,total_GPUh=resource['actual_GPUh'],below_56_GPUh=resource['actual_GPUh']<=56,
    CPU_extra_inference=0,E2E_jobs=0,new_PBS_jobs=0)
save(P/'evidence/FINAL_DELIVERY_AUDIT.json',receipt)
v['final_delivery_audit']=dict(path='evidence/FINAL_DELIVERY_AUDIT.json',sha256=sha(P/'evidence/FINAL_DELIVERY_AUDIT.json'),status='PASS')
save(P/'NUMERICAL_VALIDATION.json',v)
print('FINAL_DELIVERY_AUDIT_PASS',flush=True)
