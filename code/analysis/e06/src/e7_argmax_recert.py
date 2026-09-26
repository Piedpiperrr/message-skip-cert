"""E7 step 3 (CPU): probe-argmax re-certification over the 14 main settings.

o_A = saved probe argmax label. Agreement vs the native receiver-only answer o_R on calibration and
development (overall and on the questions omitted at the deployed q). Then the frozen 20-test family is
re-run with labels 1[o_A != o_b] on calibration, using the frozen fit-quantile thresholds, alpha=.05,
p<=.001, and the largest accepted q is reported as q_A. No gold label is read.
"""
import json,sys,math
from pathlib import Path
from scipy.stats import binom,beta
R=Path('$DATA_DIR')
BOUND=R/'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
ZERO=R/'P2_ZERO_GOLD_CONTROLS_20260914T065145Z'
V2=R/'P2_SCORING_V2_20260912T191445Z'
MED=R/'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z'
MM=R/'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z'
Q=[.05,.1,.15,.2,.25,.3,.35,.4,.45,.5,.55,.6,.65,.7,.75,.8,.85,.9,.95,1.0]
def rd(p):return json.loads(Path(p).read_text())
def jl(p):
    with Path(p).open() as f:return [json.loads(s) for s in f if s.strip()]
def tv(t):return float('inf') if t=='Infinity' else float(t)

def thresholds_from_fit(vals):
    vals=sorted(vals);n=len(vals)
    return [vals[(j*n+19)//20-1] if j<20 else 'Infinity' for j in range(1,21)]

def tests(u,d,ths):
    """The frozen calibration test family, unchanged except for the label vector d."""
    rr=[]
    for q,t in zip(Q,ths):
        m=[i for i in range(len(u)) if u[i]<=tv(t)]
        n=len(m);k=sum(d[i] for i in m)
        pv=float(binom.cdf(k,n,.05)) if n else 1.
        cp=float(beta.ppf(.999,k+1,n-k)) if n and k<n else 1.
        rr.append({'q':q,'threshold':t,'N':len(u),'n_R':n,'changed':k,'p_value':pv,
                   'CP_upper_0_999':cp,'accepted':pv<=.001,'coverage':n/len(u) if u else 0.})
    acc=[r for r in rr if r['accepted']]
    return rr,(acc[-1] if acc else None)

# ---------------- per-setting data assembly ----------------
def small_large(pair,ds):
    """probes (ProbeMax + argmax) and o_R/o_T/o_C for the small and large pairs on OBQA/ARC."""
    if (pair,ds)==('large','obqa'):
        pr={s:{r['id']:r for r in jl(ZERO/'records/probe_records.jsonl') if r['split']==s} for s in ['fit','cal','dev']}
    else:
        pr={s:{r['id']:r for r in jl(BOUND/f'records/{pair}_{ds}_{s}_probes.jsonl')} for s in ['fit','cal','dev']}
    lab={}
    for f in ['full_train','full_development']:
        for r in jl(V2/f'labels/{f}_P2_SCORING_V2.jsonl'):
            if r['pair']==pair and r['dataset']==ds:lab[r['id']]=r
    reps={s:rd(BOUND/f'splits/{ds}_{s}_representatives.json') for s in ['fit','cal','dev']}
    return pr,lab,reps

def medium(ds):
    pr={s:{r['id']:r for r in jl(MED/f'probes/{ds}_{s}.jsonl')} for s in ['fit','cal','dev']}
    lab={}
    for s in ['fit','cal','dev']:
        for r in jl(MED/f'actions/{ds}_{s}.jsonl'):
            lab.setdefault(r['id'],{})['o_'+r['action']]=(r['answer'] if not r['invalid'] else 'INVALID')
    reps={s:rd(R/f'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/splits/{ds}_{s}_representatives.json') for s in ['fit','cal','dev']}
    return pr,lab,reps

def mmlu():
    pr={s:{} for s in ['fit','cal','dev']};lab={}
    for sh in ['1','2']:
        d=MM/'shards'/sh
        for s in ['fit','cal','dev']:
            if (d/'probes'/f'{s}.jsonl').exists():
                for r in jl(d/'probes'/f'{s}.jsonl'):pr[s][r['id']]=r
            if (d/'actions'/f'{s}.jsonl').exists():
                for r in jl(d/'actions'/f'{s}.jsonl'):
                    lab.setdefault(r['id'],{})['o_'+r['action']]=(r['answer'] if not r['invalid'] else 'INVALID')
    reps={s:[g['representative_id'] for g in rd(MM/f'splits/{s}_groups.json')] for s in ['fit','cal','dev']}
    return pr,lab,reps

DEPLOY={}
for pair in ['small','large']:
    for ds in ['obqa','arc']:
        for b in ['T','C']:
            DEPLOY[pair,ds,b]=rd(BOUND/f'deployments/{pair}_{ds}_{b}.json')
for ds in ['obqa','arc']:
    for b in ['T','C']:
        DEPLOY['medium',ds,b]=rd(MED/f'deployments/{ds}_{b}.json')
for b in ['T','C']:
    DEPLOY['large','mmlu_pro',b]=rd(MM/'deployments/deployment_configs.json')['deployments'][b]

CACHE={}
def data(pair,ds):
    if (pair,ds) not in CACHE:
        CACHE[pair,ds]=medium(ds) if pair=='medium' else (mmlu() if ds=='mmlu_pro' else small_large(pair,ds))
    return CACHE[pair,ds]

rows=[];detail={}
SETTINGS=[(p,d,b) for p in ['small','medium','large'] for d in ['obqa','arc'] for b in ['T','C']]+[('large','mmlu_pro',b) for b in ['T','C']]
for pair,ds,b in SETTINGS:
    tag=f'{pair}/{ds}/{b}'
    pr,lab,reps=data(pair,ds)
    missing=[s for s in ['fit','cal','dev'] if not pr[s]]
    if missing or any('p_labels' not in next(iter(pr[s].values())) for s in ['fit','cal','dev']):
        rows.append({'setting':tag,'probe_distributions_saved':False});print('NO PROBE DIST',tag);continue
    ths=thresholds_from_fit([pr['fit'][i]['ProbeMax'] for i in reps['fit']])
    dep=DEPLOY[pair,ds,b];dq=dep['q'];dth=dep['threshold']
    out={'setting':tag,'probe_distributions_saved':True,'orig_q':dq,'N_cal':len(reps['cal']),'N_dev':len(reps['dev'])}
    per={}
    for s in ['cal','dev']:
        ids=reps[s]
        u=[pr[s][i]['ProbeMax'] for i in ids]
        oA=[pr[s][i]['argmax_probe_label'] for i in ids]
        oR=[lab[i]['o_R'] for i in ids]
        ob=[lab[i]['o_'+b] for i in ids]
        per[s]=(ids,u,oA,oR,ob)
        out[f'agree_A_vs_R_{s}']=round(sum(a==r for a,r in zip(oA,oR))/len(ids),4)
        if dq>0:
            m=[j for j in range(len(ids)) if u[j]<=tv(dth)]
            out[f'agree_A_vs_R_{s}_omitted_at_orig_q']=round(sum(oA[j]==oR[j] for j in m)/len(m),4) if m else None
            out[f'n_omitted_{s}_at_orig_q']=len(m)
        else:
            out[f'agree_A_vs_R_{s}_omitted_at_orig_q']=None;out[f'n_omitted_{s}_at_orig_q']=0
    # re-certification with d_A = 1[o_A != o_b] on calibration
    ids,u,oA,oR,ob=per['cal']
    dA=[int(a!=o) for a,o in zip(oA,ob)]
    rr,chosen=tests(u,dA,ths)
    qA=chosen['q'] if chosen else 0.
    thA=chosen['threshold'] if chosen else None
    out['q_A']=qA;out['threshold_A']=thA
    out['cal_changed_at_qA']=chosen['changed'] if chosen else None
    out['cal_n_omitted_at_qA']=chosen['n_R'] if chosen else None
    out['cal_p_at_qA']=chosen['p_value'] if chosen else None
    ids,u,oA,oR,ob=per['dev']
    if qA>0:
        m=[j for j in range(len(ids)) if u[j]<=tv(thA)]
        out['dev_coverage_at_qA']=round(len(m)/len(ids),4)
        out['dev_omitted_at_qA']=len(m)
        out['dev_changed_at_qA']=sum(oA[j]!=ob[j] for j in m)
    else:
        out['dev_coverage_at_qA']=0.0;out['dev_omitted_at_qA']=0;out['dev_changed_at_qA']=None
    rows.append(out);detail[tag]=rr
    print('%-22s agree cal %.3f dev %.3f | orig q %.2f | q_A %.2f | dev cov %.3f changed %s/%s'%(
        tag,out['agree_A_vs_R_cal'],out['agree_A_vs_R_dev'],dq,qA,out['dev_coverage_at_qA'],
        out['dev_changed_at_qA'],out['dev_omitted_at_qA']),flush=True)
Path(sys.argv[1]).write_text(json.dumps({'settings':rows,'tests':detail,'q_grid':Q,'alpha':0.05,'p_cutoff':0.001,'gold_read':False},indent=2)+'\n')
