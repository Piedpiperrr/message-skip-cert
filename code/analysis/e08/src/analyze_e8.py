"""E8 analysis (CPU, login node). Reuses the frozen MMLU-Pro Stage1 rule (src/risk.py) and the
frozen Stage1 analysis structure; extends it with the pre-registered descriptive extras.
Gold is opened only after the deployment configuration of every setting has been written."""
from common_e8 import *
import math,collections,glob
import numpy as np
from scipy.stats import beta,binom
from sklearn.metrics import roc_auc_score,average_precision_score
sys.path.insert(0,str(MMLU/'src'))
import importlib.util as _il
_s=_il.spec_from_file_location('e8_risk',MMLU/'src/risk.py');risk=_il.module_from_spec(_s);_s.loader.exec_module(risk)
sys.path.remove(str(MMLU/'src'))
assert not os.environ.get('CUDA_VISIBLE_DEVICES','')
PAIRS=['small','medium']
REFNAME={'T':'Text','C':'C2C'}
OUT=P/'analysis'
freeze=validate_freeze();FH=freeze['PROTOCOL_FREEZE_E8_sha256']
parser=load_module(P/'protocol/scoring_v2.py','e8_analysis_parser')
D1SRC=ROOT/'P2_SCORE_SENSITIVITY_20260912T055929Z/diagnostic_parser_v1.py'
d1=load_module(D1SRC,'e8_d1_parser')
meta=query_meta()

# ---------------------------------------------------------------- 1. completeness and re-parse
def load_pair(pair):
    records={};keys=set();counts=collections.Counter();files=[];attempts=0
    lanes=sorted((P/'shards'/pair).glob('lane_*'))
    for d in lanes:
        assert (d/'LANE_COMPLETE.json').exists(),f'lane not complete: {d}'
        comp=read(d/'LANE_COMPLETE.json')
        for rel,h in comp['files'].items():
            path=d/rel;assert sha(path)==h,path
            files.append(dict(path=str(path.resolve()),sha256=h))
            with path.open() as f:
                for line in f:
                    r=json.loads(line);ident=r['id'];a=r['action'];split=r['split'];key=r['key']
                    assert key==f'{pair}|mmlu_pro|{split}|{ident}|{a}' and key not in keys;keys.add(key)
                    assert r['pair']==pair and r['protocol_freeze_sha256']==FH
                    assert r['query_sha256']==queryhash(r['query'])
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
                        rr['u']=r['ProbeMax'];rr['p_labels']=r['p_labels'];rr['probe_latency_ms']=r['latency_ms']
                    else:
                        assert a in ['R','T','C']
                        raw=r['output']['raw_answer'];legal=meta[ident]['choice_labels']
                        pr=parser.parse_answer(raw,legal)
                        assert pr==r['parsed'] and r['answer']==(pr['answer'] if pr['valid'] else 'INVALID')
                        assert r['invalid']==(not pr['valid'])
                        rr[a]=r['answer'];rr[a+'_invalid']=r['invalid'];rr[a+'_latency_ms']=r['latency_ms']
                        dr=d1.parse_explicit(raw,legal)
                        rr[a+'_D1']=dr['answer'] if dr['valid'] else 'INVALID'
                        if a=='R':rr['native_R_input_hash']=queryhash(r['native_first_input_ids']['receiver'][0])
                    counts[a]+=1
        ev=rows(d/'records/attempts.jsonl')
        s=[x['key'] for x in ev if x['event']=='SUCCESS'];assert len(s)==len(set(s))
        attempts+=len([x for x in ev if x['event']=='START'])
    assert len(keys)==48128 and dict(counts)==dict(R=12032,T=12032,C=12032,P=12032),(pair,dict(counts),len(keys))
    assert set(records)==set(meta) and all(all(k in r for k in ['R','T','C','u']) for r in records.values())
    assert all(r['native_R_input_hash']==r['probe_base_hash'] for r in records.values())
    return records,files,attempts

# ---------------------------------------------------------------- 2. thresholds, calibration, deployment
fitreps=ids('fit',True);calreps=ids('cal',True);devreps=ids('dev',True)
assert (len(fitreps),len(calreps),len(devreps))==(3000,6000,2641)
DATA={};LEDGER=[];DEPLOY={};THRESH={}
for pair in PAIRS:
    rec,files,attempts=load_pair(pair);DATA[pair]=dict(records=rec,files=files,attempts=attempts)
    cuts=risk.thresholds([rec[x]['u'] for x in fitreps]);THRESH[pair]=cuts
    save(OUT/f'thresholds/{pair}_fit_thresholds.json',dict(utc=utc(),pair=pair,unit='frozen group representative',
        N_fit=3000,thresholds=[dict(q=q,threshold=t,fit_routed=sum(risk.mask([rec[x]['u'] for x in fitreps],q,t)),
            fixed_R=q==1) for q,t in zip(risk.GRID,cuts)],gold_used=False))
    for ref in ['T','C']:
        ll,dd=risk.calibrate([rec[x]['u'] for x in calreps],
                             [rec[x]['R']!=rec[x][ref] for x in calreps],cuts)
        for row in ll:row.update(pair=pair,reference=REFNAME[ref],setting=f'{pair}/MMLU-Pro/{REFNAME[ref]}')
        LEDGER+=ll;DEPLOY[pair,ref]=dict(pair=pair,reference=REFNAME[ref],**dd)
assert len(LEDGER)==80
csvout(OUT/'calibration/80_test_ledger.csv',LEDGER);save(OUT/'calibration/80_test_ledger.json',LEDGER)
save(OUT/'deployments/deployment_configs.json',dict(utc=utc(),family='E8 small+medium MMLU-Pro; 4 settings x 20 candidates = 80 tests',
    deployments={f'{p}/{REFNAME[r]}':DEPLOY[p,r] for p,r in DEPLOY},accuracy_used_for_selection=False,
    protocol_freeze_E8_sha256=FH,per_setting_ideal_Bonferroni_bound=.02,family_ideal_Bonferroni_bound=.08,
    earlier_families_combined=False,ledger_sha256=sha(OUT/'calibration/80_test_ledger.json')))
print('DEPLOYMENTS',{f'{p}/{REFNAME[r]}':DEPLOY[p,r]['q'] for p,r in DEPLOY},flush=True)

# ---------------------------------------------------------------- 3. gold opens only now
import pyarrow.parquet as pq
REVIEW=ROOT/'P2_MMLU_PRO_BREADTH_PROTOCOL_AND_COST_REVIEW_20260915T224801Z'
goldrows=pq.read_table(REVIEW/'dataset/test-00000-of-00001.parquet',columns=['question_id','answer']).to_pylist()
gold={'test:'+str(r['question_id']):r['answer'] for r in goldrows}
assert set(gold)>=set(meta)
save(OUT/'GOLD_OPENED.json',dict(utc=utc(),after_deployment_configs=True,
    deployment_configs_sha256=sha(OUT/'deployments/deployment_configs.json'),
    parquet=str(REVIEW/'dataset/test-00000-of-00001.parquet')))

def metrics(rec,ii,ref,d):
    n=len(ii);routed=risk.mask([rec[x]['u'] for x in ii],d['q'],d['threshold'])
    dis=[rec[x]['R']!=rec[x][ref] for x in ii];scores=[rec[x]['u'] for x in ii]
    nr=sum(routed);changed=sum(a and b for a,b in zip(routed,dis))
    refc=polc=benefit=harm=neutral=0;inv=collections.Counter()
    for x,on,diff in zip(ii,routed,dis):
        r=rec[x];a=r['R'] if on else r[ref];cr=r[ref]==gold[x];cp=a==gold[x]
        refc+=cr;polc+=cp
        if on and diff:
            benefit+=int(cp and not cr);harm+=int(cr and not cp);neutral+=int(cr==cp)
        for act in ['R','T','C']:inv[act]+=r[act+'_invalid']
        inv['policy']+=a=='INVALID'
    assert changed==benefit+harm+neutral and polc-refc==benefit-harm
    return dict(N=n,reference=d['reference'],q=d['q'],threshold=d['threshold'],mode=d['mode'],omitted=nr,
        coverage=nr/n if n else None,changed=changed,changed_over_omitted=f'{changed}/{nr}',
        conditional_disagreement=changed/nr if nr else None,marginal_disagreement=changed/n if n else None,
        descriptive_CP_0_95_upper=float(beta.ppf(.95,changed+1,nr-changed)) if nr and changed<nr else (1. if nr else None),
        R_reference_disagreement_count=sum(dis),R_reference_disagreement_prevalence=sum(dis)/n if n else None,
        AUROC=float(roc_auc_score(dis,scores)) if len(set(dis))==2 else None,
        AP=float(average_precision_score(dis,scores)) if any(dis) else None,
        score_direction='higher u predicts R/reference disagreement',
        correct_R=sum(rec[x]['R']==gold[x] for x in ii),correct_reference=refc,correct_policy=polc,
        accuracy_R=sum(rec[x]['R']==gold[x] for x in ii)/n if n else None,
        accuracy_reference=refc/n if n else None,accuracy_policy=polc/n if n else None,
        accuracy_difference=(polc-refc)/n if n else None,benefit=benefit,harm=harm,neutral_change=neutral,
        invalid_R=inv['R'],invalid_Text=inv['T'],invalid_C2C=inv['C'],invalid_policy=inv['policy'],
        invalid_rate_R=inv['R']/n if n else None,invalid_rate_reference=inv['T' if ref=='T' else 'C']/n if n else None)

summ=[];compact=[]
for pair in PAIRS:
    rec=DATA[pair]['records']
    for split,ii in [('fit',fitreps),('cal',calreps),('dev',devreps)]:
        for unit,jj in [('group_representatives',ii),('raw_rows_descriptive',ids(split))]:
            for ref in ['T','C']:
                m=dict(pair=pair,setting=f'{pair}/MMLU-Pro/{REFNAME[ref]}',split=split,unit=unit,
                       **metrics(rec,jj,ref,DEPLOY[pair,ref]))
                if unit=='raw_rows_descriptive':m['descriptive_CP_0_95_upper']=None
                summ.append(m)
                if split=='dev' and unit=='group_representatives':compact.append(m)
csvout(OUT/'development/split_summaries.csv',summ);save(OUT/'development/split_summaries.json',summ)
csvout(OUT/'development/compact_4_settings.csv',compact);save(OUT/'development/compact_4_settings.json',compact)

# ---------------------------------------------------------------- 4. oracle headroom (development representatives)
orc=[]
for pair in PAIRS:
    rec=DATA[pair]['records'];n=len(devreps)
    cor={a:sum(rec[x][a]==gold[x] for x in devreps) for a in ['R','T','C']}
    oracle=sum(any(rec[x][a]==gold[x] for a in ['R','T','C']) for x in devreps)
    best=max(cor,key=lambda a:cor[a])
    orc.append(dict(pair=pair,N=n,correct_R=cor['R'],correct_Text=cor['T'],correct_C2C=cor['C'],
        accuracy_R=cor['R']/n,accuracy_Text=cor['T']/n,accuracy_C2C=cor['C']/n,
        best_fixed_action=best,best_fixed_correct=cor[best],best_fixed_accuracy=cor[best]/n,
        oracle_correct=oracle,oracle_accuracy=oracle/n,
        oracle_gain_over_best_fixed=(oracle-cor[best])/n,oracle_gain_over_R=(oracle-cor['R'])/n,
        unit='development group representatives'))
csvout(OUT/'development/oracle_headroom.csv',orc);save(OUT/'development/oracle_headroom.json',orc)

# ---------------------------------------------------------------- 5. D1 label differences
d1rows=[]
for pair in PAIRS:
    rec=DATA[pair]['records']
    for a in ['R','T','C']:
        diff=[x for x in meta if rec[x][a]!=rec[x][a+'_D1']]
        v2inv=sum(rec[x][a]=='INVALID' for x in meta);d1inv=sum(rec[x][a+'_D1']=='INVALID' for x in meta)
        d1rows.append(dict(pair=pair,action=a,N=len(meta),differences=len(diff),
            difference_rate=len(diff)/len(meta),V2_INVALID=v2inv,D1_INVALID=d1inv,
            V2_valid_D1_invalid=sum(rec[x][a]!='INVALID' and rec[x][a+'_D1']=='INVALID' for x in meta),
            D1_valid_V2_invalid=sum(rec[x][a]=='INVALID' and rec[x][a+'_D1']!='INVALID' for x in meta),
            both_valid_different_label=sum(rec[x][a]!='INVALID' and rec[x][a+'_D1']!='INVALID' and rec[x][a]!=rec[x][a+'_D1'] for x in meta),
            D1_source=str(D1SRC),D1_sha256=sha(D1SRC)))
csvout(OUT/'development/D1_label_differences.csv',d1rows);save(OUT/'development/D1_label_differences.json',d1rows)

# ---------------------------------------------------------------- 6. re-split stability (E5-b rule)
import random,hashlib as _h
MMLU_SEED='P2_MMLU_PRO_BREADTH_20260915_v1'
CAT={g['representative_id']:(g['category'],g['group_hash']) for sp in ['fit','cal'] for g in read(P/f'splits/{sp}_groups.json')}
POOL=fitreps+calreps;ORIG=set(fitreps)
def _h256(x):return _h.sha256(x.encode()).hexdigest()
def allocate(N,counts):
    total=sum(counts.values());quotas={c:N*n//total for c,n in counts.items()}
    order=sorted(counts,key=lambda c:(-(N*counts[c]%total),c))
    for c in order[:N-sum(quotas.values())]:quotas[c]+=1
    assert sum(quotas.values())==N
    return quotas
def resplit(seed):
    seedstr=MMLU_SEED if seed==0 else f'{MMLU_SEED}|resplit{seed}'
    counts=collections.Counter(CAT[i][0] for i in POOL);quotas=allocate(3000,counts);fit=set()
    for c in sorted(counts):
        rr=sorted([i for i in POOL if CAT[i][0]==c],key=lambda i:_h256(seedstr+'|split_fit|'+CAT[i][1]))
        fit.update(rr[:quotas[c]])
    return np.array([i in fit for i in POOL],bool)
MASK={s:resplit(s) for s in range(0,201)}
seed0_ok=bool((MASK[0]==np.array([i in ORIG for i in POOL],bool)).all())
stab=[];perseed=[]
for pair in PAIRS:
    rec=DATA[pair]['records']
    u=np.array([rec[x]['u'] for x in POOL])
    udev=np.array([rec[x]['u'] for x in devreps])
    for ref in ['T','C']:
        d=np.array([rec[x]['R']!=rec[x][ref] for x in POOL],bool)
        ddev=np.array([rec[x]['R']!=rec[x][ref] for x in devreps],bool)
        q0=DEPLOY[pair,ref]['q'];orig='deploy' if q0>0 else 'fallback'
        qs=[];cov=[];chg=[];omi=[];cert=0
        for s in range(1,201):
            m=MASK[s];cuts=risk.thresholds(list(u[m]))
            ucal=u[~m];dcal=d[~m];acc=[]
            for q,t in zip(risk.GRID,cuts):
                mm=np.array(risk.mask(list(ucal),q,t),bool);n=int(mm.sum());k=int(dcal[mm].sum())
                if (float(binom.cdf(k,n,.05)) if n else 1.)<=.001:acc.append((q,t))
            q,t=acc[-1] if acc else (0.,None)
            perseed.append(dict(setting=f'{pair}/MMLU-Pro/{REFNAME[ref]}',seed=s,q=q,N_cal=int((~m).sum())))
            if q>0:
                cert+=1;qs.append(q)
                md=np.array(risk.mask(list(udev),q,t),bool)
                cov.append(100*md.mean());chg.append(int(ddev[md].sum()));omi.append(int(md.sum()))
        match=cert if orig=='deploy' else 200-cert
        f=lambda v:round(float(np.median(v)),4) if v else None
        stab.append(dict(setting=f'{pair}/MMLU-Pro/{REFNAME[ref]}',original_outcome=f'{orig} q={q0:g}',
            seeds=200,certification_rate=cert/200,match_rate=match/200,
            stable='stable' if match/200>=.80 else 'split-sensitive',
            median_q=f(qs),IQR_q=[f([np.percentile(qs,25)]),f([np.percentile(qs,75)])] if qs else None,
            median_dev_coverage_pct=f(cov),median_dev_changed=f(chg),median_dev_omitted=f(omi),
            n_deploying=cert,seed0_reproduces_frozen_split=seed0_ok))
csvout(OUT/'development/resplit_stability.csv',stab);save(OUT/'development/resplit_stability.json',stab)
csvout(OUT/'development/resplit_per_seed.csv',perseed)

# ---------------------------------------------------------------- 7. receipts
for pair in PAIRS:
    write_rows(OUT/f'merged/{pair}_rows.jsonl',[{k:v for k,v in DATA[pair]['records'][x].items() if k!='p_labels'}
        for x in ids('fit')+ids('cal')+ids('dev')])
save(P/'NUMERICAL_VALIDATION_E8.json',dict(status='PASS',utc=utc(),protocol_freeze_E8_sha256=FH,
    pairs=PAIRS,rows_per_pair=12032,actions_per_pair=36096,probes_per_pair=12032,
    duplicate_request_keys=0,missing_IDs=0,input_hash_mismatches=0,reparsed_actions=72192,
    fit_reps=3000,cal_reps=6000,dev_reps=2641,calibration_tests=80,group_leakage=0,
    resplit_seed0_reproduces_frozen_split=seed0_ok,
    deploy_count=sum(DEPLOY[k]['q']>0 for k in DEPLOY),
    output_files={p:DATA[p]['files'] for p in PAIRS},scientific_analysis_complete=True))
save(P/'ANALYSIS_COMPLETE_E8.json',dict(utc=utc(),status='COMPLETE_E8',
    deployments={f'{p}/{REFNAME[r]}':DEPLOY[p,r]['q'] for p,r in DEPLOY},
    compact=compact,oracle=orc,resplit=stab,D1=d1rows))
print(json.dumps(dict(deployments={f'{p}/{REFNAME[r]}':DEPLOY[p,r]['q'] for p,r in DEPLOY}),indent=1),flush=True)
print('ANALYSIS_COMPLETE_E8 written',flush=True)
