"""E13 Item 5: recertification with the probe's argmax as the receiver's answer (separate post-hoc family).

o_A(x) = argmax over option labels of the saved probe probabilities p_labels (checked equal to the stored
argmax_probe_label). New change label d_A = 1[o_A != o_ref], reference answers with the frozen parser (INVALID stays
INVALID and counts as a change). Same ProbeMax scores, same 20 frozen fit thresholds (e11_common.load cuts), same test
(e11_common/r2_common.ledger_rows: P[Bin(n,.05) <= k] <= .001; deploy the largest accepted q).
Primary: the three OLMo (X2) settings; secondary: the four Llama-pair (X1) settings (receiver = small pair).
"""
import numpy as np
from e13_settings import *
from e13_common import csvout, RES, LABEL
from data_r1 import route_mask  # noqa: E402

INV = C.INV
BND = C.BND


def plabels_x2(ds):
    P = {}
    for f in sorted((C.XFAM / 'results/runs').glob('chain_*.jsonl')):
        for r in C.jl(f):
            if r['dataset'] == ds:
                P[r['id']] = r['P']
    return P


def plabels_small(ds):
    P = {}
    for sp in ['fit', 'cal', 'dev']:
        for r in C.jl(BND / f'records/small_{ds}_{sp}_probes.jsonl'):
            P[r['id']] = r
    return P


def argmax(p):
    return max(p['p_labels'], key=p['p_labels'].get)


rows, repro = [], []
PAPER_DIS = {'obqa': (172, 742), 'arc': (67, 299), 'mmlu_pro': (1112, 2641)}
for s in C.XSET:
    pair, task, ref = s
    ds = C.BENCH[task]
    L = C.load(s)
    P = plabels_x2(ds) if pair == 'X2-OLMo' else plabels_small(ds)
    cuts = L['cuts']
    out = {}
    for sp in ['cal', 'dev']:
        S = L[sp]
        oA = [argmax(P[i]) for i in S['ids']]
        assert all(a == P[i]['argmax_probe_label'] for a, i in zip(oA, S['ids']))
        assert np.allclose([P[i]['ProbeMax'] for i in S['ids']], S['u'])
        oR, ob = np.array(S['oR'], object), np.array(S['ob'], object)
        out[sp] = dict(u=S['u'], oA=np.array(oA, object), oR=oR, ob=ob, dA=np.array(oA, object) != ob, dR=oR != ob)
    # reproduction: original labels
    led0 = C.ledger_rows(out['cal']['u'], out['cal']['dR'], cuts)
    q0, _ = C.largest_accepted(led0)
    if pair == 'X2-OLMo':
        got = (int(out['dev']['dR'].sum()), len(out['dev']['dR']))
        repro.append(dict(item=5, check=f'{C.sname(s)} original dev disagreement', expected='%d/%d' % PAPER_DIS[ds],
                          got='%d/%d' % got, ok=got == PAPER_DIS[ds]))
        repro.append(dict(item=5, check=f'{C.sname(s)} original certification', expected='fallback',
                          got='fallback' if q0 == 0 else q0, ok=q0 == 0))
    # new family
    led = C.ledger_rows(out['cal']['u'], out['cal']['dA'], cuts)
    q, acc = C.largest_accepted(led)
    best = min(led, key=lambda r: r['p'])
    sel = next(r for r in led if r['q'] == q) if q else None
    dv = out['dev']
    om = route_mask(dv['u'], q, cuts[C.GRID.index(q)]) if q else np.zeros(len(dv['u']), bool)
    invdis = dv['dA'] & (dv['ob'] == INV)
    rows.append(dict(
        setting=C.sname(s), family='secondary (Llama pair)' if pair == 'X1-Llama' else 'primary (OLMo)',
        cal_N=len(out['cal']['u']), cal_agreement_oA_vs_native_R=float((out['cal']['oA'] == out['cal']['oR']).mean()),
        cal_native_R_invalid=int((out['cal']['oR'] == INV).sum()), cal_ref_invalid=int((out['cal']['ob'] == INV).sum()),
        cal_disagreement_rate_native=float(out['cal']['dR'].mean()), cal_disagreement_rate_argmax=float(out['cal']['dA'].mean()),
        deployed_q=q if q else 'fallback', accepted_q=';'.join(f'{x:g}' for x in acc),
        cal_n=sel['n'] if sel else '', cal_k=sel['k'] if sel else '', cal_p=sel['p'] if sel else '',
        smallest_p_q=best['q'], smallest_p_n=best['n'], smallest_p_k=best['k'], smallest_p=best['p'],
        q05_n=led[0]['n'], q05_k=led[0]['k'], q05_p=led[0]['p'],
        dev_N=len(dv['u']), dev_coverage=float(om.mean()), dev_changed=int(dv['dA'][om].sum()), dev_omitted=int(om.sum()),
        dev_disagreements_argmax=int(dv['dA'].sum()), dev_AUROC_u_argmax_label=C.auroc(dv['dA'], dv['u']),
        dev_AUROC_u_native_label=C.auroc(dv['dR'], dv['u']),
        dev_share_disagreements_with_INVALID_reference=float(invdis.sum() / dv['dA'].sum()) if dv['dA'].sum() else float('nan'),
        dev_disagreements_with_INVALID_reference=int(invdis.sum()), label=LABEL))
    print({k: v for k, v in rows[-1].items() if k != 'label'})
csvout(RES / 'item5_argmax_recert.csv', rows)
csvout(RES / 'item5_repro_checks.csv', repro)
for r in repro: print(r)
