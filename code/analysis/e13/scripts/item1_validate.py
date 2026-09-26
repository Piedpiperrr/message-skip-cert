"""E13 Item 1 validation: (a) explicit per-draw reconstruction of the full null answer-correctness vectors from the same
random numbers, compared with the vectorised dN / gain; (b) closed-form E[dN] by linearity vs the 1,000-draw means."""
import copy
import numpy as np
from e13_common import *

pops = E.load_pops()
rows = []
for P in pops:
    v = xview(P)
    rng = np.random.default_rng(0)
    # skip to the joint stream position exactly as item1.py does
    v.per_reference_x(rng, 'T', E.NREP); v.per_reference_x(rng, 'C', E.NREP); v.independent_x(rng, E.NREP)
    r2 = copy.deepcopy(rng)
    g, d1, d2, forced, K, a, b, c, cs, under = v.joint_x(rng, E.NREP)
    # explicit replay with the same random numbers
    jj = v._pick(r2, K, E.NREP)
    cor1, i1, sz = v._one_draw(r2, jj)
    lo = a + b + cs
    cor2 = None
    if K > lo:
        s = sz[:, lo:]
        i2 = (i1[:, lo:] + 1 + (r2.random((jj.shape[0], K - lo)) * np.maximum(s - 1, 0)).astype(int)) % np.maximum(s, 1)
        cor2 = v.pcor[jj[:, lo:], i2]
    bad = 0
    for d in range(E.NREP):
        n1 = v.yR.copy(); n2 = v.yR.copy()
        for t in range(K):
            j = jj[d, t]
            if t < a: n1[j] = cor1[d, t]
            elif t < a + b: n2[j] = cor1[d, t]
            elif t < lo: n1[j] = cor1[d, t]; n2[j] = cor1[d, t]
            else: n1[j] = cor1[d, t]; n2[j] = cor2[d, t - lo]
        orc = int((v.yR | n1 | n2).sum())
        h = orc - max(v.cR, int(n1.sum()), int(n2.sum()))
        ok = (orc - v.cR == g[d]) and (n1.sum() - v.cR == d1[d]) and (n2.sum() - v.cR == d2[d]) and \
             (h == h_best_fixed_2(v.cR, g[d:d + 1], d1[d:d + 1], d2[d:d + 1])[0])
        bad += (not ok)
    # closed form
    p1 = np.zeros(P.N)
    for j in range(P.N):
        if v.psize[j]: p1[j] = v.pcor[j, :v.psize[j]].mean()
    w = np.zeros(P.N, bool); w[v.elig] = True
    base = (p1[w] - v.yR[w]).sum() / v.E
    rows.append(dict(population=P.name, design='joint-matched', explicit_replay_draws=E.NREP, explicit_replay_mismatches=bad,
                     exact_E_dN1=f'{(a + c) * base:.4f}', mc_mean_dN1=f'{d1.mean():.4f}',
                     exact_E_dN2=f'{(b + c) * base:.4f}', mc_mean_dN2=f'{d2.mean():.4f}',
                     rel_diff_dN1=f'{abs(d1.mean() - (a + c) * base) / abs((a + c) * base):.4f}',
                     rel_diff_dN2=f'{abs(d2.mean() - (b + c) * base) / abs((b + c) * base):.4f}', label=LABEL))
    print(rows[-1])
csvout(RES / 'item1_validation.csv', rows)
