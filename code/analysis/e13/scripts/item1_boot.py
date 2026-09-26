"""E13 Item 1: question-level bootstrap intervals for the best-fixed ratio, with exactly the E9-a protocol
(e9a_boot.py): one default_rng(0) stream, 2,000 iterations, populations visited in the fixed order, in each
resample independent / per-ref T / per-ref C / joint with 100 null draws. Because XInst makes the same random calls,
the gain-over-R ratios reproduce e9a_bootstrap_ratios.npy (checked) and the best-fixed ratios use the same draws."""
import time
import numpy as np
from e13_common import *

DESIGNS = ['independent (E5-c)', 'per-reference Text', 'per-reference C2C', 'joint-matched']
pops = E.load_pops()
rng = np.random.default_rng(0)
RG = np.full((E.NBOOT, len(pops), 4), np.nan)   # gain-over-R ratios (must equal E9-a)
RB = np.full((E.NBOOT, len(pops), 4), np.nan)   # best-fixed ratios
t0 = time.time()
for t in range(E.NBOOT):
    for pi, P in enumerate(pops):
        idx = rng.integers(0, P.N, P.N)
        v = xview(P, idx)
        H = real_h(v)
        gI, i1, i2 = v.independent_x(rng, E.NBOOT_NULL)
        gT, dT = v.per_reference_x(rng, 'T', E.NBOOT_NULL)
        gC, dC = v.per_reference_x(rng, 'C', E.NBOOT_NULL)
        gJ, j1, j2 = v.joint_x(rng, E.NBOOT_NULL)[:3]
        hs = [h_best_fixed_2(v.cR, gI, i1, i2), h_best_fixed_1(v.cR, gT, dT), h_best_fixed_1(v.cR, gC, dC),
              h_best_fixed_2(v.cR, gJ, j1, j2)]
        for di, (g, greal, h, hreal) in enumerate([(gI, v.real_TC, hs[0], H['TC']), (gT, v.real_T, hs[1], H['T']),
                                                   (gC, v.real_C, hs[2], H['C']), (gJ, v.real_TC, hs[3], H['TC'])]):
            if greal:
                RG[t, pi, di] = g.mean() / greal
            if hreal:
                RB[t, pi, di] = h.mean() / hreal
    if (t + 1) % 200 == 0:
        print(f'  {t + 1}/{E.NBOOT} resamples, {time.time() - t0:.0f}s', flush=True)

saved = np.load(E9A / 'results/e9a_bootstrap_ratios.npy')
same = np.array_equal(np.isnan(saved), np.isnan(RG)) and np.allclose(saved[~np.isnan(saved)], RG[~np.isnan(RG)], rtol=0, atol=1e-12)
print('gain-over-R bootstrap array identical to saved E9-a array:', same)

rows = []
for di, dn in enumerate(DESIGNS):
    for key, A in [('best_fixed', RB), ('gain_over_R', RG)]:
        for pi, P in enumerate(pops):
            x = A[:, pi, di]; ok = x[~np.isnan(x)]
            rows.append(dict(design=dn, ratio=key, population=P.name, n_resamples=E.NBOOT, n_defined=len(ok),
                             n_undefined_real_zero=E.NBOOT - len(ok), boot_mean=fmt(ok.mean()),
                             ci_lo_2_5=fmt(np.percentile(ok, 2.5)), ci_hi_97_5=fmt(np.percentile(ok, 97.5)), label=LABEL))
        med = np.nanmedian(A[:, :, di], axis=1); okm = med[~np.isnan(med)]
        rows.append(dict(design=dn, ratio=key, population='MEDIAN of 7', n_resamples=E.NBOOT, n_defined=len(okm),
                         n_undefined_real_zero=E.NBOOT - len(okm), boot_mean=fmt(okm.mean()),
                         ci_lo_2_5=fmt(np.percentile(okm, 2.5)), ci_hi_97_5=fmt(np.percentile(okm, 97.5)), label=LABEL))
        print(f'{dn:20s} {key:12s} median of 7: [{np.percentile(okm, 2.5):.3f}, {np.percentile(okm, 97.5):.3f}]')
rows.append(dict(design='CHECK', ratio='gain_over_R', population='identical to e9a_bootstrap_ratios.npy', boot_mean=str(same), label=LABEL))
csvout(RES / 'item1_bootstrap_intervals.csv', rows)
np.save(RES / 'item1_bootstrap_ratios_best_fixed.npy', RB)
print(f'total {time.time() - t0:.0f}s')
