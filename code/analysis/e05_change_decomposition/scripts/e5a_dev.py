"""E5-a follow-up: development coverage/change at the largest clean-accepted q, for settings whose deployed q
is not accepted on C \ X (pre-registered: recompute dev at the largest clean-accepted q or fallback)."""
from r2_common import *
import numpy as np, data_r1

main = load_main()
rows = []
for s, qnew in [(('medium', 'OBQA', 'C2C'), 0.50)]:
    pair, task, ref = s
    D = main[pair, task]
    cuts = D['stored_thresholds']
    for q in [EXPECTED_Q[s], qnew]:
        t = cuts[GRID.index(q)]
        m = data_r1.route_mask(D['dev']['scores']['ProbeMax'], q, t)
        d = data_r1.disagreement(D['dev'], ref)
        rows.append(dict(setting=sname(s), q=q, threshold=t, N_dev=len(m), omitted=int(m.sum()),
                         coverage_pct=f'{100 * m.mean():.1f}', changed=int(d[m].sum()),
                         change_rate_among_omitted=f'{d[m].mean():.4f}' if m.sum() else '',
                         note='ORIGINAL frozen deployment' if q == EXPECTED_Q[s] else 'largest clean-accepted q (C \\ X)',
                         label=LABEL))
csvout(RES / 'e5a_dev_at_clean_q.csv', rows)
for r in rows: print(r['setting'], 'q=', r['q'], 'cov', r['coverage_pct'], 'changed/omitted', f"{r['changed']}/{r['omitted']}", '|', r['note'])
