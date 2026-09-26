"""Items 1-2 (POST-HOC): recompute deployed q from ledgers; calibration table."""
from common_r1 import *
L = ledgers()
t1, t2 = [], []
ok = True
for s in SETTINGS:
    rows = L[s]
    q, acc = deploy(rows)
    # recompute p and CP from (n,k) and compare to ledger values
    maxdp = max(abs(pval(r['k'], r['n']) - r['p']) for r in rows); maxdcp = max(abs(cp999(r['k'], r['n']) - r['CP']) for r in rows)
    ledger_acc = [r['q'] for r in rows if r['accepted']]
    match = abs(q - EXPECTED_Q[s]) < 1e-9 and acc == ledger_acc
    ok &= match
    t1.append(dict(pair=s[0], task=s[1], reference=s[2], recomputed_q=q, expected_q=EXPECTED_Q[s], ledger_accepted_flags_agree=acc == ledger_acc,
                   max_abs_p_diff=maxdp, max_abs_CP_diff=maxdcp, match=match, source=rows[0]['source'], label=LABEL))
    if q > 0: sel = next(r for r in rows if r['q'] == q); basis = 'selected'
    else: sel = min(rows, key=lambda r: r['p']); basis = 'fallback: min p over grid'
    row = dict(pair=s[0], task=s[1], reference=s[2], deployed_q=q, basis=basis, q=sel['q'], threshold=sel['threshold'], N_cal=sel['N'],
               n_q=sel['n'], k_q=sel['k'], p=pval(sel['k'], sel['n']), CP_upper_0999=cp999(sel['k'], sel['n']))
    if s[0] == 'small':
        for qq in (.05, .10):
            rr = next(r for r in rows if abs(r['q'] - qq) < 1e-9); row[f'n_q{qq:.2f}'] = rr['n']; row[f'k_q{qq:.2f}'] = rr['k']
    ties = [r['q'] for r in rows if r['p'] == sel['p']] if basis.startswith('fallback') else []
    row['min_p_tied_q'] = ';'.join(f'{x:g}' for x in ties); row['source'] = rows[0]['source']; row['label'] = LABEL
    t2.append(row)
csvout(P / 'results/item1_deployed_q_check.csv', t1)
csvout(P / 'results/item2_calibration_table.csv', t2)
for r in t1: print(r['pair'], r['task'], r['reference'], r['recomputed_q'], r['expected_q'], r['match'], f"{r['max_abs_p_diff']:.2e} {r['max_abs_CP_diff']:.2e}")
print('ALL_MATCH', ok)
for r in t2: print({k: v for k, v in r.items() if k not in ('source', 'label')})
