"""E9-a task 3: question-level bootstrap intervals for the four designs.
2,000 bootstrap resamples of questions (numpy default_rng(0), one stream, populations visited in a fixed order so
each population is resampled independently inside every iteration). In each resample the real gain, the change
counts (m_Text, m_C2C, a, b, c, c_same) and the eligible set are recomputed, the expected null gain is estimated
from 100 null draws within that resample, and ratio = mean null gain / real gain. The median across the 7
populations is taken inside each iteration from that iteration's 7 ratios."""
import time
import numpy as np
from e9a_common import *

DESIGNS = ['independent (E5-c)', 'per-reference Text', 'per-reference C2C', 'joint-matched']
pops = load_pops()
rng = np.random.default_rng(0)
R = np.full((NBOOT, len(pops), len(DESIGNS)), np.nan)
t0 = time.time()
for t in range(NBOOT):
    for pi, P in enumerate(pops):
        idx = rng.integers(0, P.N, P.N)
        v = P.view(idx)
        gI = v.independent(rng, NBOOT_NULL)
        gT = v.per_reference(rng, 'T', NBOOT_NULL)
        gC = v.per_reference(rng, 'C', NBOOT_NULL)
        gJ = v.joint(rng, NBOOT_NULL)[0]
        for di, (g, real) in enumerate([(gI, v.real_TC), (gT, v.real_T), (gC, v.real_C), (gJ, v.real_TC)]):
            if real:
                R[t, pi, di] = g.mean() / real
    if (t + 1) % 200 == 0:
        print(f'  {t + 1}/{NBOOT} resamples, {time.time() - t0:.0f}s', flush=True)

rows = []
for di, dn in enumerate(DESIGNS):
    for pi, P in enumerate(pops):
        x = R[:, pi, di]; ok = x[~np.isnan(x)]
        rows.append(dict(design=dn, population=P.name, n_resamples=NBOOT, n_defined=len(ok),
                         n_undefined_real_gain_zero=NBOOT - len(ok),
                         boot_mean=fmt(ok.mean()) if len(ok) else 'nan',
                         ci_lo_2_5=fmt(np.percentile(ok, 2.5)) if len(ok) else 'nan',
                         ci_hi_97_5=fmt(np.percentile(ok, 97.5)) if len(ok) else 'nan', label=LABEL))
    med = np.nanmedian(R[:, :, di], axis=1)
    okm = med[~np.isnan(med)]
    rows.append(dict(design=dn, population='MEDIAN of 7', n_resamples=NBOOT, n_defined=len(okm),
                     n_undefined_real_gain_zero=NBOOT - len(okm), boot_mean=fmt(okm.mean()),
                     ci_lo_2_5=fmt(np.percentile(okm, 2.5)), ci_hi_97_5=fmt(np.percentile(okm, 97.5)), label=LABEL))
    print(f'{dn:20s} median of 7: [{np.percentile(okm, 2.5):.3f}, {np.percentile(okm, 97.5):.3f}] '
          f'(undefined resamples: {NBOOT - len(okm)})')

csvout(RES / 'e9a_bootstrap_intervals.csv', rows)
np.save(RES / 'e9a_bootstrap_ratios.npy', R)
print(f'total {time.time() - t0:.0f}s')
