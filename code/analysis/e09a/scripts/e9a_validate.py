"""E9-a validation: exact expectations of every null design, by linearity of expectation, vs the 1,000-draw
Monte-Carlo means, plus a check that the independent design reproduces the saved E5-c ratios."""
import csv
import numpy as np
from e9a_common import *

pops = load_pops()
rows = []
for P in pops:
    v = P.view()
    p1 = np.zeros(P.N); q2 = np.zeros(P.N)
    for j in range(P.N):
        s = v.psize[j]
        if s:
            c = v.pcor[j, :s]
            p1[j] = c.mean()
            q2[j] = float(c.any()) if s >= 2 else p1[j]   # two distinct draws exhaust a 2-element pool
    w = np.zeros(P.N, bool); w[v.elig] = True; w &= v.need
    E = v.E
    ex_T = (v.mT / E) * p1[w].sum()
    ex_C = (v.mC / E) * p1[w].sum()
    sT, sC = v.mT / E, v.mC / E
    ex_I = (1 - (1 - sT * p1[w]) * (1 - sC * p1[w])).sum()
    a, b, c, cs = v.a, v.b, v.c, v.c_same
    if a + b + c > E:  # same largest-remainder reduction as e9a_common.Inst.joint
        K2 = E; raw = [a * K2 / (a + b + c), b * K2 / (a + b + c), c * K2 / (a + b + c)]
        fl = [int(np.floor(x)) for x in raw]
        for i in np.argsort([-(raw[i] - fl[i]) for i in range(3)])[:K2 - sum(fl)]:
            fl[i] += 1
        a, b, c = fl; cs = min(cs, c) if c else 0
    ex_J = ((a + b + cs) * p1[w].sum() + (c - cs) * q2[w].sum()) / E

    rng = np.random.default_rng(0)
    mc = dict(T=v.per_reference(rng, 'T', NREP).mean(), C=v.per_reference(rng, 'C', NREP).mean(),
              I=v.independent(rng, NREP).mean(), J=v.joint(rng, NREP)[0].mean())
    for k, ex in [('per-reference Text', ex_T), ('per-reference C2C', ex_C),
                  ('independent (E5-c)', ex_I), ('joint-matched', ex_J)]:
        m = mc[k[0] if k[0] != 'i' else 'I'] if False else mc[{'per-reference Text': 'T', 'per-reference C2C': 'C',
                                                               'independent (E5-c)': 'I', 'joint-matched': 'J'}[k]]
        rows.append(dict(population=P.name, design=k, exact_expected_null_gain=f'{ex:.4f}',
                         monte_carlo_mean_1000=f'{m:.4f}', abs_diff=f'{abs(ex - m):.4f}',
                         rel_diff=f'{abs(ex - m) / ex:.5f}' if ex else 'nan', label=LABEL))

# saved E5-c ratios (independent design) for comparison
e5c = {r['population']: float(r['rho']) for r in csv.DictReader(
    (ROOT / 'P2_R2_CPU_20260919T220412Z/results/e5c_null_control.csv').open())}
mine = {r['population']: float(r['independent_ratio']) for r in csv.DictReader((RES / 'e9a_ratios.csv').open())}
cmp_rows = [dict(population=k, e5c_rho_saved=f'{e5c[k]:.3f}', e9a_independent_ratio=f'{mine[k]:.3f}',
                 abs_diff=f'{abs(e5c[k] - mine[k]):.3f}', label=LABEL) for k in mine]
cmp_rows.append(dict(population='MEDIAN', e5c_rho_saved=f'{np.median(list(e5c.values())):.3f}',
                     e9a_independent_ratio=f'{np.median(list(mine.values())):.3f}',
                     abs_diff=f'{abs(np.median(list(e5c.values())) - np.median(list(mine.values()))):.3f}', label=LABEL))

worst = max(float(r['rel_diff']) for r in rows if r['rel_diff'] != 'nan')
print(f'max |MC - exact| / exact over 28 (population x design) cells: {worst:.5f}')
print(f'max |E5-c rho - E9-a independent ratio|: {max(float(r["abs_diff"]) for r in cmp_rows):.3f}')
for r in cmp_rows: print(' ', r['population'], r['e5c_rho_saved'], r['e9a_independent_ratio'], r['abs_diff'])
csvout(RES / 'e9a_validation_exact_vs_mc.csv', rows)
csvout(RES / 'e9a_validation_vs_e5c.csv', cmp_rows)
