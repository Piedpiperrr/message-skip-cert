"""E15 step 2: reproduction checks (stop if any fails).
(i)  25 settings: certification outcome and deployed q recomputed from the stored frozen fit thresholds and the calibration
     records (e11_common.load / ledger_rows / largest_accepted, unchanged); expected = e11_common.Q0.
     Also: stored thresholds == fit order statistics of the stored fit scores (needed by E15-1), split sizes.
(ii) Table 2 savings: paired mean (fixed - policy) latency over the 128 original-configuration panel questions.
"""
import sys
from e15_common import *

rows, ok_all = [], True
for s in SET25:
    L = C.load(s)
    F = load_fit(s)
    led = C.ledger_rows(L['cal']['u'], dis(L['cal']), L['cuts'])
    q, acc = C.largest_accepted(led)
    thr_fit = C.thresholds(list(F['u']))
    thr_ok = [str(a) for a in thr_fit] == [str(a) for a in L['cuts']] or all(
        (a == b) or (C.tv(a) == C.tv(b)) for a, b in zip(thr_fit, L['cuts']))
    ok = (q == L['q0']) and thr_ok
    ok_all &= ok
    rows.append(dict(check='(i) certification', setting=sname(s), N_fit=len(F['u']), N_cal=len(L['cal']['u']), N_dev=len(L['dev']['u']),
                     expected_q=L['q0'], recomputed_q=q, outcome='deploy' if q > 0 else 'fallback',
                     accepted_q=';'.join(f'{a:.2f}' for a in acc),
                     p_at_q=next((r['p'] for r in led if r['q'] == q), ''), n_at_q=next((r['n'] for r in led if r['q'] == q), ''),
                     k_at_q=next((r['k'] for r in led if r['q'] == q), ''),
                     stored_thresholds_equal_fit_order_statistics=thr_ok, ok=ok))
    print(rows[-1])
print('deploy count', sum(r['recomputed_q'] > 0 for r in rows), 'fallback count', sum(r['recomputed_q'] == 0 for r in rows))

sav = []
for s in DEPLOY8:
    ids, fx, po, f = original_replay(s)
    d = np.array([fx[i]['latency_ms'] - po[i]['latency_ms'] for i in ids])
    got = float(d.mean())
    ok = round(got, 1) == TABLE2[s]
    ok_all &= ok
    sav.append(dict(check='(ii) Table 2 saving', setting=sname(s), N=len(ids), expected_ms=TABLE2[s], recomputed_ms=got,
                    n_omitted=sum(po[i]['selected'] == 'R' for i in ids), source=str(f), ok=ok))
    print(sav[-1])
csvout('step2_repro_certification.csv', rows)
csvout('step2_repro_table2.csv', sav)
print('ALL_OK', ok_all)
sys.exit(0 if ok_all else 1)
