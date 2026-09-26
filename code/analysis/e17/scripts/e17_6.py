"""E17-6: MMLU-Pro per category (large Text and large C2C): category-specific fit quantiles, category calibration questions,
same alpha / delta = .001 per candidate / selection rule; also delta = .001/14."""
import collections
from e17_common import *

X = loadcache(); D = X['D']
MM = ROOT / 'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/splits'
CAT = {}
for sp in ['fit', 'cal', 'dev']:
    for g in read(MM / f'{sp}_groups.json'):
        CAT[g['representative_id']] = g['category']
rows = []
for ref in ['Text', 'C2C']:
    L = D['large', 'MMLU-Pro', ref]
    cat = {sp: np.array([CAT[i] for i in L[sp]['ids']]) for sp in ['fit', 'cal', 'dev']}
    cats = sorted(set(cat['fit']))
    assert len(cats) == 14 and set(cat['cal']) == set(cats) == set(cat['dev'])
    for c in cats:
        fu = L['fit']['u'][cat['fit'] == c]
        cuts = C.thresholds(list(fu))
        cu, cd = L['cal']['u'][cat['cal'] == c], L['cal']['d'][cat['cal'] == c]
        du, dd = L['dev']['u'][cat['dev'] == c], L['dev']['d'][cat['dev'] == c]
        r = dict(path=ref, category=c, N_fit=len(fu), N_cal=len(cu), cal_disagreements=int(cd.sum()), cal_dis_rate=float(cd.mean()), N_dev=len(du))
        for tag, delta in [('', .001), ('_delta_over_14', .001 / 14)]:
            led = ledger(cu, cd, cuts, delta=delta)
            q, row = deployed(led)
            r[f'q{tag}'] = q if q > 0 else 'fallback'
            if q > 0:
                m = mask(du, q, cuts[GRID.index(q)]); n, k = int(m.sum()), int(dd[m].sum()); lo, hi = cp95(k, n)
                r.update({f'cal_n{tag}': row['n'], f'cal_k{tag}': row['k'], f'cal_p{tag}': row['p'], f'dev_coverage{tag}': n / len(du),
                          f'dev_n{tag}': n, f'dev_k{tag}': k, f'dev_rate{tag}': rate(k, n), f'dev_CP_lo{tag}': lo, f'dev_CP_hi{tag}': hi})
        best = min(ledger(cu, cd, cuts), key=lambda x: (x['p'], x['q']))
        r.update(min_p=best['p'], min_p_q=best['q'], min_p_n=best['n'], min_p_k=best['k'], label=LABEL)
        rows.append(r)
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k != 'label'})
csvout('E17_6_mmlu_categories.csv', rows)
for ref in ['Text', 'C2C']:
    rr = [r for r in rows if r['path'] == ref]
    print(ref, 'certified', sum(r['q'] != 'fallback' for r in rr), '/14; with delta/14:', sum(r['q_delta_over_14'] != 'fallback' for r in rr), '/14')
