"""E8 replay analysis (CPU). Paired fixed-minus-policy saving on the frozen panel, versions (a) and (b),
class + / - / ?, exactly the rule of P2_R1_E3POL.../e3_build/e3_metrics.py::saving_row. Only the class is
reported; it is not compared with the original hardware."""
from common_e8 import *
import numpy as np
R=P/'REPLAY_E8';cfg=read(R/'REPLAY_FREEZE_E8.json')
def ci(v):return (float(np.quantile(v,.025)),float(np.quantile(v,.975)))
def cls(lo,hi):return '+' if lo>0 else ('-' if hi<0 else '?')
out=[];settings=[]
for pair,ARMS in cfg['arms'].items():
    rec=rows(R/pair/'records/requests.jsonl')
    assert len(rec)==128*len(ARMS) and len({r['key'] for r in rec})==len(rec)
    comp=read(R/pair/'REPLAY_COMPLETE.json');assert comp['status']=='COMPLETE'
    for ref in ['T','C']:
        if f'fixed_{ref}' not in ARMS:continue
        fx={r['id']:r for r in rec if r['arm']==f'fixed_{ref}'}
        po={r['id']:r for r in rec if r['arm']==f'policy_{ref}'}
        ids=[r['id'] for r in rows(R/'inputs/panel_queries.jsonl')]
        assert set(ids)==set(fx)==set(po)
        d=np.array([fx[i]['latency_ms']-po[i]['latency_ms'] for i in ids])
        idx=np.random.default_rng(0).integers(0,len(ids),size=(2000,len(ids)))
        m1,c1=float(d.mean()),ci(d[idx].mean(axis=1))
        ff=min(fx.values(),key=lambda r:r['attempt']);pf=min(po.values(),key=lambda r:r['attempt'])
        excl={ff['id'],pf['id']};keep=[i for i in ids if i not in excl]
        d2=np.array([fx[i]['latency_ms']-po[i]['latency_ms'] for i in keep]);n2=len(keep)
        idx2=np.random.default_rng(0).integers(0,n2,size=(2000,n2))
        m2,c2=float(d2.mean()),ci(d2[idx2].mean(axis=1))
        omitted=sum(1 for i in ids if po[i]['selected']=='R')
        changed=sum(1 for i in ids if po[i]['selected']=='R' and po[i]['answer']!=fx[i]['answer'])
        name=f"{pair}/MMLU-Pro/{'Text' if ref=='T' else 'C2C'}"
        settings.append(name)
        out.append(dict(setting=name,pair=pair,reference='Text' if ref=='T' else 'C2C',
            q=cfg['policies'][f"{pair}/{'Text' if ref=='T' else 'C2C'}"]['q'],
            N_a=len(ids),a_mean_saving_ms=m1,a_CI_low=c1[0],a_CI_high=c1[1],a_median_ms=float(np.median(d)),
            a_class=cls(*c1),N_b=n2,b_excluded_ids=';'.join(sorted(excl)),b_mean_saving_ms=m2,
            b_CI_low=c2[0],b_CI_high=c2[1],b_median_ms=float(np.median(d2)),b_class=cls(*c2),
            panel_omitted=omitted,panel_changed=changed,
            fixed_first_id=ff['id'],fixed_first_attempt=ff['attempt'],fixed_first_ms=ff['latency_ms'],
            policy_first_id=pf['id'],policy_first_attempt=pf['attempt'],policy_first_ms=pf['latency_ms'],
            saving='paired fixed-reference latency minus policy latency, ms',
            hardware='ClusterA A100 40GB; class only, not compared with the original hardware'))
csvout(R/'results/replay_savings.csv',out);save(R/'results/replay_savings.json',out)
save(R/'REPLAY_CLASS.json',dict(utc=utc(),settings=settings,
    **{'class':{r['setting']:dict(version_a=r['a_class'],version_b=r['b_class']) for r in out}},
    note='class + = saving above zero, - = below zero, ? = interval contains zero'))
for r in out:print(f"{r['setting']}: (a) {r['a_mean_saving_ms']:.1f} ms [{r['a_CI_low']:.1f},{r['a_CI_high']:.1f}] class {r['a_class']} | "
                   f"(b) N={r['N_b']} {r['b_mean_saving_ms']:.1f} ms [{r['b_CI_low']:.1f},{r['b_CI_high']:.1f}] class {r['b_class']}",flush=True)
