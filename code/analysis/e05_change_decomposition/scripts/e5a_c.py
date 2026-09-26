"""E5-a (c): independent-parser check. Re-parse the saved raw calibration outputs with the official C2C evaluator's
extraction and with the pre-V2 D1 parser; compare d_b labels to frozen V2 and redo the deployed-q test."""
from r2_common import *
import numpy as np
import data_r1
import parsers_r2 as PR
import rawio

recs, allrev, X, CAL, FIT, DEV = exposed_ids()
main = load_main()
x2 = load_x2()
x1 = load_x1()


def xcuts(csvpath, setting):
    rr = [r for r in csvread(csvpath) if r['setting'] == setting]
    return [r['threshold'] for r in rr]


def get(s):
    pair, task, ref = s
    if pair in ('small', 'medium', 'large'):
        D = main[pair, task]
        oR = list(D['cal']['ans']['R']); ob = list(D['cal']['ans']['T' if ref == 'Text' else 'C'])
        return BENCH[task], D['cal']['ids'], D['cal']['scores']['ProbeMax'], oR, ob, D['stored_thresholds'], EXPECTED_Q[s]
    if pair == 'X2-OLMo':
        ds = BENCH[task]; D = x2[ds]
        return ds, D['cal']['ids'], np.array(D['cal']['u']), D['cal']['oR'], D['cal']['oT'], xcuts(XFAM / 'results/analysis/certification_ledger_60.csv', f'{ds}/Text'), 0.0
    ds = BENCH[task]; D = x1[ds]
    ob = D['cal']['oT'] if ref == 'Text' else D['cal']['oC']
    return ds, D['cal']['ids'], np.array(D['cal']['u']), D['cal']['oR'], ob, xcuts(X1 / 'results/analysis/certification_ledger_80.csv', f'{ds}/{ref}'), 0.0


rows, detail = [], []
for s in ALL21:
    ds, ids, u, oR, ob, cuts, q0 = get(s)
    raw, src = rawio.raw_cal(s, ids)
    ref = s[2]
    legal = [rawio.legal_labels(ds, i) for i in ids]
    applicable = all(PR.official_applicable(L) for L in legal)
    ex = np.array([i in X[ds] for i in ids], bool)
    dV2 = np.array([a != b for a, b in zip(oR, ob)], bool)
    out = dict(setting=sname(s), benchmark=ds, N_cal=len(ids), raw_source=src,
               official_applicable=applicable, label=LABEL)
    for name, fn in [('OFFICIAL', PR.label_official), ('D1', PR.label_d1)]:
        if name == 'OFFICIAL' and not applicable:
            out.update({f'{name}_o_R_diff': 'n/a (A-D only)', f'{name}_o_ref_diff': 'n/a (A-D only)',
                        f'{name}_d_diff_total': 'n/a (A-D only)', f'{name}_d_diff_in_X': 'n/a', f'{name}_d_diff_in_clean': 'n/a',
                        f'{name}_n_at_orig_q': '', f'{name}_k_at_orig_q': '', f'{name}_p_at_orig_q': '',
                        f'{name}_orig_q_accepted': 'n/a', f'{name}_largest_accepted_q': ''})
            continue
        nR = [fn(t, L) for t, L in zip(raw['R'], legal)]
        nb = [fn(t, L) for t, L in zip(raw[ref], legal)]
        d2 = np.array([a != b for a, b in zip(nR, nb)], bool)
        diff = d2 != dV2
        led = ledger_rows(u, d2, cuts)
        r0 = next((r for r in led if abs(r['q'] - q0) < 1e-9), None)
        acc = [r['q'] for r in led if r['accepted']]
        out.update({f'{name}_o_R_diff': int(sum(a != b for a, b in zip(nR, oR))),
                    f'{name}_o_ref_diff': int(sum(a != b for a, b in zip(nb, ob))),
                    f'{name}_d_diff_total': int(diff.sum()), f'{name}_d_diff_in_X': int(diff[ex].sum()),
                    f'{name}_d_diff_in_clean': int(diff[~ex].sum()),
                    f'{name}_n_at_orig_q': r0['n'] if r0 else '', f'{name}_k_at_orig_q': r0['k'] if r0 else '',
                    f'{name}_p_at_orig_q': f"{r0['p']:.6g}" if r0 else '',
                    f'{name}_orig_q_accepted': bool(r0['accepted']) if r0 else 'n/a (fallback)',
                    f'{name}_largest_accepted_q': acc[-1] if acc else 0.0})
        for q, r in zip(GRID, led):
            detail.append(dict(setting=sname(s), parser=name, q=q, n=r['n'], k=r['k'], p=f"{r['p']:.6g}",
                               accepted=r['accepted'], label=LABEL))
    rows.append(out)
    print(out['setting'], 'OFFICIAL d-diff', out['OFFICIAL_d_diff_total'], 'D1 d-diff', out['D1_d_diff_total'],
          'OFFICIAL acc@q0', out['OFFICIAL_orig_q_accepted'], 'D1 acc@q0', out['D1_orig_q_accepted'])

csvout(RES / 'e5a_independent_parser.csv', rows)
csvout(RES / 'e5a_independent_parser_grid.csv', detail)

# X1 C2C rows carry the official evaluator's own prediction: direct check against our re-run of its extractor
chk = []
for ds in ['obqa', 'arc']:
    ids = x1[ds]['cal']['ids']
    raw, _ = rawio.raw_cal(('X1-Llama', {'obqa': 'OBQA', 'arc': 'ARC'}[ds], 'C2C'), ids)
    legal = [rawio.legal_labels(ds, i) for i in ids]
    stored = rawio.official_pred_x1(ds, ids)
    mine = [PR.label_official(t, L) for t, L in zip(raw['C2C'], legal)]
    agree = sum((a if a is not None else PR.INV) == b for a, b in zip(stored, mine))
    chk.append(dict(benchmark=ds, N=len(ids), agree_with_stored_official_pred=agree, label=LABEL))
    print('X1 official_pred agreement', ds, agree, '/', len(ids))
csvout(RES / 'e5a_official_pred_crosscheck.csv', chk)
csvout(RES / 'e5a_parser_sources.csv', [dict(parser=k, path=v, sha256=PR.HASHES[k], label=LABEL) for k, v in PR.SOURCES.items()])
print(PR.HASHES)
