"""E17-1 (omit iff u == 0) and E17-2 (certification on u > 0 questions only)."""
from e17_common import *

X = loadcache(); D = X['D']

# ------------------------------------------------------------------ E17-1
rows1, taus = [], []
for key, s, q in CERT:
    L = D[s]
    r = dict(policy=key, setting=sname(s), q=q)
    for sp in ['cal', 'dev']:
        u, d = L[sp]['u'], L[sp]['d']
        z = u == 0.0
        n0, k0, N = int(z.sum()), int(d[z].sum()), len(u)
        lo, hi = cp95(k0, n0)
        r.update({f'{sp}_N': N, f'{sp}_n0': n0, f'{sp}_k0': k0, f'{sp}_u0_coverage': n0 / N,
                  f'{sp}_k0_over_n0': rate(k0, n0), f'{sp}_CP_lo': lo, f'{sp}_CP_hi': hi})
        if sp == 'cal': r['cal_p_u0'] = pval(k0, n0) if n0 else float('nan')
    t = L['cuts'][GRID.index(q)]
    m = mask(L['dev']['u'], q, t); n, k = int(m.sum()), int(L['dev']['d'][m].sum())
    lo, hi = cp95(k, n)
    r.update(policy_dev_coverage=n / len(m), policy_dev_n=n, policy_dev_k=k, policy_dev_rate=k / n, policy_CP_lo=lo, policy_CP_hi=hi)
    # grid candidates with tau == 0 on fit, and whether accepted in the original certification
    led = ledger(L['cal']['u'], L['cal']['d'], L['cuts'])
    z0 = [(g, lr['accepted'], lr['n'], lr['k'], lr['p']) for g, t, lr in zip(GRID, L['cuts'], led) if C.tv(t) == 0.0]
    r['fit_grid_q_with_tau0'] = ';'.join(f'{g:.2f}' for g, *_ in z0) or 'none'
    r['tau0_candidates_accepted'] = ';'.join(f'{g:.2f}:{"acc" if a else "rej"}' for g, a, *_ in z0) or 'none'
    r['u0_rule_was_a_grid_candidate'] = bool(z0)
    r['label'] = LABEL
    rows1.append(r)
    for g, a, n_, k_, p_ in z0:
        taus.append(dict(setting=sname(s), policy=key, q=g, tau=0.0, cal_n=n_, cal_k=k_, cal_p=p_, accepted=a,
                         equals_u0_rule_on_cal=(n_ == r['cal_n0'] and k_ == r['cal_k0'])))
    print({k_: (round(v, 4) if isinstance(v, float) else v) for k_, v in r.items() if k_ != 'label'})
csvout('E17_1_u0_rule.csv', rows1)
csvout('E17_1_tau0_candidates.csv', taus or [dict(note='no fit grid candidate equals 0 in any certified setting')])
main9 = [r for r in rows1 if r['policy'] not in ('medium/OBQA/C2C q=.50',) and not r['policy'].startswith('Llama')]
print('u0 rule dev coverage range', min(r['dev_u0_coverage'] for r in main9), max(r['dev_u0_coverage'] for r in main9))
print('u0 rule dev change-rate range', min(r['dev_k0_over_n0'] for r in main9), max(r['dev_k0_over_n0'] for r in main9))
print('policy dev coverage range', min(r['policy_dev_coverage'] for r in main9), max(r['policy_dev_coverage'] for r in main9))
print('policy dev change-rate range', min(r['policy_dev_rate'] for r in main9), max(r['policy_dev_rate'] for r in main9))

# ------------------------------------------------------------------ E17-2
SET9 = [('large', 'OBQA', 'Text'), ('large', 'OBQA', 'C2C'), ('large', 'ARC', 'Text'), ('large', 'ARC', 'C2C'),
        ('large', 'MMLU-Pro', 'Text'), ('large', 'MMLU-Pro', 'C2C'), ('medium', 'OBQA', 'C2C'), ('medium', 'ARC', 'C2C'), C.FACT]
rows2, grid2 = [], []
for s in SET9:
    L = D[s]
    fu = L['fit']['u']; fp = fu > 0
    cuts = C.thresholds(list(fu[fp]))
    cu, cd = L['cal']['u'], L['cal']['d']; cp = cu > 0
    led = ledger(cu[cp], cd[cp], cuts)
    for lr in led: grid2.append(dict(setting=sname(s), **lr))
    qp, row = deployed(led)
    du, dd = L['dev']['u'], L['dev']['d']; dp = du > 0
    r = dict(setting=sname(s), N_fit=len(fu), N_fit_upos=int(fp.sum()), N_cal=len(cu), N_cal_upos=int(cp.sum()),
             N_dev=len(du), N_dev_upos=int(dp.sum()), cal_dis_upos=int(cd[cp].sum()),
             q_plus=qp if qp > 0 else 'fallback', accepted_q=';'.join(f"{x['q']:.2f}" for x in led if x['accepted']) or 'none')
    best = min(led, key=lambda x: (x['p'], x['q']))
    r.update(min_p=best['p'], min_p_q=best['q'], min_p_n=best['n'], min_p_k=best['k'])
    if qp > 0:
        t = cuts[GRID.index(qp)]
        m = mask(du[dp], qp, t); n, k = int(m.sum()), int(dd[dp][m].sum())
        lo, hi = cp95(k, n)
        r.update(threshold_plus=t, cal_n=row['n'], cal_k=row['k'], cal_p=row['p'], dev_n=n, dev_k=k,
                 dev_coverage_within_upos=n / dp.sum(), dev_coverage_of_all=n / len(du), dev_rate=k / n, dev_CP_lo=lo, dev_CP_hi=hi)
    r['label'] = LABEL
    rows2.append(r)
    print({k_: (round(v, 4) if isinstance(v, float) else v) for k_, v in r.items() if k_ != 'label'})
csvout('E17_2_upos_certification.csv', rows2)
csvout('E17_2_upos_ledgers.csv', grid2)
print('E17-2 certified:', sum(r['q_plus'] != 'fallback' for r in rows2), 'of', len(rows2))
