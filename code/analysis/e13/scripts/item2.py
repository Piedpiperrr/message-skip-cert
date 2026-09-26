"""E13 Item 2: joint-matched null stratified by whether R is correct.

Within each stratum (R incorrect, R correct) the unchanged E9-a joint sampler (XInst.joint_x = E9-a Inst.joint plus
correctness deltas) is run with that stratum's own a, b, c, c_same and eligible set; the union of the two strata is one
draw. Stream: one fresh default_rng(0) per population, stratum "R incorrect" drawn first, then "R correct", 1,000 draws
each. Bootstrap: one default_rng(0) stream, 2,000 question resamples (populations in fixed order), in each resample the
strata are re-formed from the resampled questions and 100 null draws are taken per stratum in the same order.
Ratios: best-fixed (Item 1 definition) and gain over R (E9-a definition); median of 7 inside each bootstrap iteration.
Usage: item2.py point | boot
"""
import sys, time
import numpy as np
from e13_common import *


def strat_draw(P, idx, rng, D):
    """Returns gain, dN1, dN2 (union of strata) plus per-stratum meta."""
    yR = P.yR[idx]
    g = np.zeros(D, int); d1 = np.zeros(D, int); d2 = np.zeros(D, int); meta = {}
    for name, sel in [('R_incorrect', ~yR), ('R_correct', yR)]:
        sub = idx[sel]
        v = xview(P, sub)
        gs, a1, a2, forced, K, a, b, c, cs, under = v.joint_x(rng, D)
        g += gs; d1 += a1; d2 += a2
        meta[name] = dict(n=len(sub), E=v.E, a=v.a, b=v.b, c=v.c, c_same=v.c_same, K=K, a_used=a, b_used=b,
                          c_used=c, cs_used=cs, under=under, forced_mean=forced.mean() if len(forced) else 0.)
    return g, d1, d2, meta


def point():
    pops = E.load_pops()
    rows, stratrows = [], []
    for P in pops:
        rng = np.random.default_rng(0)
        idx = np.arange(P.N)
        g, d1, d2, meta = strat_draw(P, idx, rng, E.NREP)
        v = xview(P); H = real_h(v)
        h = h_best_fixed_2(v.cR, g, d1, d2)
        flags = [k for k in meta if meta[k]['under']]
        rows.append(dict(population=P.name, N=P.N, H_real_best_fixed=H['TC'], gain_real_over_R=v.real_TC,
                         H_null_mean=f'{h.mean():.3f}', H_null_p2_5=f'{np.percentile(h, 2.5):.1f}',
                         H_null_p97_5=f'{np.percentile(h, 97.5):.1f}', ratio_best_fixed=fmt(h.mean() / H['TC']),
                         gain_null_mean=f'{g.mean():.3f}', gain_null_p2_5=f'{np.percentile(g, 2.5):.1f}',
                         gain_null_p97_5=f'{np.percentile(g, 97.5):.1f}', ratio_gain_over_R=fmt(g.mean() / v.real_TC),
                         mean_correct_N1=f'{v.cR + d1.mean():.3f}', mean_correct_N2=f'{v.cR + d2.mean():.3f}',
                         mean_best_fixed_null_minus_R=f'{np.maximum(0, np.maximum(d1, d2)).mean():.3f}',
                         under_matched_strata=';'.join(flags) if flags else 'none',
                         lower_bound_flag='yes' if flags else 'no', draws=E.NREP, label=LABEL))
        for k, m in meta.items():
            stratrows.append(dict(population=P.name, stratum=k, n_questions=m['n'], n_eligible_P_nonempty=m['E'],
                                  a_Text_only=m['a'], b_C2C_only=m['b'], c_both=m['c'], c_same=m['c_same'],
                                  a_plus_b_plus_c=m['a'] + m['b'] + m['c'], K_drawn=m['K'], a_used=m['a_used'],
                                  b_used=m['b_used'], c_used=m['c_used'], c_same_used=m['cs_used'],
                                  under_matched='yes' if m['under'] else 'no', forced_same_mean_per_draw=f"{m['forced_mean']:.2f}",
                                  label=LABEL))
        print(rows[-1]['population'], rows[-1]['ratio_best_fixed'], rows[-1]['ratio_gain_over_R'], rows[-1]['under_matched_strata'])
    for key in ['ratio_best_fixed', 'ratio_gain_over_R']:
        print('median', key, fmt(np.median([float(r[key]) for r in rows])))
    rows.append(dict(population='MEDIAN of 7', ratio_best_fixed=fmt(np.median([float(r['ratio_best_fixed']) for r in rows])),
                     ratio_gain_over_R=fmt(np.median([float(r['ratio_gain_over_R']) for r in rows])), label=LABEL))
    csvout(RES / 'item2_stratified_ratios.csv', rows)
    csvout(RES / 'item2_strata.csv', stratrows)


def boot():
    pops = E.load_pops()
    rng = np.random.default_rng(0)
    RB = np.full((E.NBOOT, len(pops)), np.nan); RG = np.full((E.NBOOT, len(pops)), np.nan)
    nunder = np.zeros(len(pops), int)
    t0 = time.time()
    for t in range(E.NBOOT):
        for pi, P in enumerate(pops):
            idx = rng.integers(0, P.N, P.N)
            g, d1, d2, meta = strat_draw(P, idx, rng, E.NBOOT_NULL)
            v = xview(P, idx); H = real_h(v)
            nunder[pi] += any(m['under'] for m in meta.values())
            if v.real_TC:
                RG[t, pi] = g.mean() / v.real_TC
            if H['TC']:
                RB[t, pi] = h_best_fixed_2(v.cR, g, d1, d2).mean() / H['TC']
        if (t + 1) % 200 == 0:
            print(f'  {t + 1}/{E.NBOOT} resamples, {time.time() - t0:.0f}s', flush=True)
    rows = []
    for key, A in [('best_fixed', RB), ('gain_over_R', RG)]:
        for pi, P in enumerate(pops):
            x = A[:, pi]; ok = x[~np.isnan(x)]
            rows.append(dict(ratio=key, population=P.name, n_resamples=E.NBOOT, n_defined=len(ok),
                             n_resamples_with_an_under_matched_stratum=int(nunder[pi]), boot_mean=fmt(ok.mean()),
                             ci_lo_2_5=fmt(np.percentile(ok, 2.5)), ci_hi_97_5=fmt(np.percentile(ok, 97.5)), label=LABEL))
        med = np.nanmedian(A, axis=1); okm = med[~np.isnan(med)]
        rows.append(dict(ratio=key, population='MEDIAN of 7', n_resamples=E.NBOOT, n_defined=len(okm), boot_mean=fmt(okm.mean()),
                         ci_lo_2_5=fmt(np.percentile(okm, 2.5)), ci_hi_97_5=fmt(np.percentile(okm, 97.5)), label=LABEL))
        print(key, 'median of 7:', fmt(np.percentile(okm, 2.5)), fmt(np.percentile(okm, 97.5)))
    csvout(RES / 'item2_bootstrap_intervals.csv', rows)
    np.save(RES / 'item2_bootstrap_ratios.npy', np.stack([RB, RG], axis=-1))
    print(f'total {time.time() - t0:.0f}s')


if __name__ == '__main__':
    {'point': point, 'boot': boot}[sys.argv[1]]()
