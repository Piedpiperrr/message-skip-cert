"""E22-1: the per-reference matched null run inside the two strata S+ / S- (primary).

Strata: S+ = o_R = gold, S- = o_R != gold (INVALID counts as wrong).  Inside each stratum E9-a's own
Inst.per_reference sampler draws min(n_s(b), elig_s) of that stratum's eligible questions uniformly without
replacement and gives each a uniform draw from P(x); the two strata are pooled into one null action.
Stream (declared): one fresh numpy.random.default_rng(0) per population; references in the order Text, C2C;
inside each reference the strata in the order S-, S+.
Bootstrap: one default_rng(0) stream, 2,000 question resamples, populations in the E9-a order, 100 null draws
inside each resample, everything (strata, n_s(b), elig_s, real gain) recomputed in the resample.

Usage: e22_1.py point | boot
"""
import sys, time
import numpy as np
from e22_common import *
import e22_common as C

REFS = [('T', 'Text'), ('C', 'C2C')]
STORED_R = {r['population']: r for r in csvread(E9A / 'results' / 'e9a_ratios.csv')}
STORED_CI = {(r['design'], r['population']): r for r in csvread(E9A / 'results' / 'e9a_bootstrap_intervals.csv')}


def unstrat(pop, ref):
    """The stored E9-a unstratified per-reference ratio and interval printed in tab:null_matched."""
    r = STORED_R[pop][f'perref_{ref}_ratio']
    c = STORED_CI[f'per-reference {ref}', pop]
    return r, f"[{c['ci_lo_2_5']}, {c['ci_hi_97_5']}]"


def point():
    pops = E.load_pops()
    rows, checks = [], []
    stop = False
    for P in pops:
        rng = np.random.default_rng(SEED)
        v = P.view()
        for code, ref in REFS:
            g, meta = strat_perref(P, np.arange(P.N), rng, code, NREP)
            mm, mp = meta['S_minus'], meta['S_plus']
            real = v.real_T if code == 'T' else v.real_C
            gm = g_minus(mm['inst'])
            exp = mm['drawn'] * gm
            obs = float(g.mean())
            se = float(g.std(ddof=1)) / np.sqrt(NREP)
            ok = abs(obs - exp) <= 3 * se if se > 0 else abs(obs - exp) < 1e-9
            sp_zero = bool(mp['gain'].max() == 0)
            checks.append(dict(population=P.name, reference=ref, check='mean null gain == min(n-, elig-) * g_-',
                               expected=f'{exp:.4f}', obtained=f'{obs:.4f}', mc_se=f'{se:.4f}',
                               abs_diff_in_mc_se=f'{abs(obs - exp) / se:.3f}' if se > 0 else '0',
                               pass_=str(ok), s_plus_gain_always_zero=str(sp_zero), label=LABEL))
            stop |= (not ok) or (not sp_zero)
            und = bool(mm['under'])
            ratio = obs / real if real else float('nan')
            sr, sci = unstrat(P.name, ref)
            rows.append(dict(
                population=P.name, reference=ref, N=P.N,
                n_plus=mp['n_changed'], n_minus=mm['n_changed'], elig_plus=mp['elig'], elig_minus=mm['elig'],
                n_questions_S_plus=mp['n'], n_questions_S_minus=mm['n'],
                drawn_S_minus=mm['drawn'], drawn_S_plus=mp['drawn'],
                undetermined='yes' if und else 'no',
                under_matched_S_plus='yes' if mp['under'] else 'no',
                real_gain_over_R=real, null_gain_mean=f'{obs:.3f}',
                null_gain_p2_5=f'{np.percentile(g, 2.5):.1f}', null_gain_p97_5=f'{np.percentile(g, 97.5):.1f}',
                g_minus=fmt(gm), stratified_ratio=fmt(ratio),
                appendix_scaled_ratio_if_undetermined=(fmt(ratio * mm['n_changed'] / mm['elig'])
                                                       if und and mm['elig'] else ''),
                unstratified_ratio_stored_E9a=sr, unstratified_CI95_stored_E9a=sci,
                draws=NREP, seed=SEED, label=LABEL))
            print(f"{P.name:16s} {ref:4s} n+/n- {mp['n_changed']:4d}/{mm['n_changed']:4d} "
                  f"elig+/elig- {mp['elig']:4d}/{mm['elig']:4d} {'UNDET' if und else '     '} "
                  f"real {real:5d} null {obs:8.3f} g- {fmt(gm)} ratio {fmt(ratio)} (unstrat {sr})", flush=True)
    csvout(RES / 'E22_1_point.csv', rows)
    csvout(RES / 'E22_1_mc_checks.csv', checks)
    for code, ref in REFS:
        rr = [float(r['stratified_ratio']) for r in rows if r['reference'] == ref]
        print(f'median {ref} over 7: {fmt(np.median(rr))}')
    rc = [float(rows[2 * i + 1]['stratified_ratio']) for i in MEDLARGE]
    print(f'median C2C over the 5 medium/large: {fmt(np.median(rc))}')
    if stop:
        print('STOP: the E22-1 identity check failed; see E22_1_mc_checks.csv')
        sys.exit(2)


def boot():
    pops = E.load_pops()
    rng = np.random.default_rng(SEED)
    R = np.full((NBOOT, len(pops), 2), np.nan)
    nunder = np.zeros((len(pops), 2), int)
    t0 = time.time()
    for t in range(NBOOT):
        for pi, P in enumerate(pops):
            idx = rng.integers(0, P.N, P.N)
            v = P.view(idx)
            for di, (code, _) in enumerate(REFS):
                g, meta = strat_perref(P, idx, rng, code, NBOOT_NULL)
                nunder[pi, di] += int(meta['S_minus']['under'])
                real = v.real_T if code == 'T' else v.real_C
                if real:
                    R[t, pi, di] = g.mean() / real
        if (t + 1) % 200 == 0:
            print(f'  {t + 1}/{NBOOT} resamples, {time.time() - t0:.0f}s', flush=True)
    rows = []
    for di, (code, ref) in enumerate(REFS):
        for pi, P in enumerate(pops):
            x = R[:, pi, di]; ok = x[~np.isnan(x)]
            rows.append(dict(design=f'stratified per-reference {ref}', population=P.name, n_resamples=NBOOT,
                             n_defined=len(ok), n_undefined_real_gain_zero=NBOOT - len(ok),
                             n_resamples_undetermined_S_minus=int(nunder[pi, di]),
                             boot_mean=fmt(ok.mean()) if len(ok) else 'nan',
                             ci_lo_2_5=fmt(np.percentile(ok, 2.5)) if len(ok) else 'nan',
                             ci_hi_97_5=fmt(np.percentile(ok, 97.5)) if len(ok) else 'nan', label=LABEL))
        for nm, cols in [('MEDIAN of 7', list(range(len(pops))))] + \
                        ([('MEDIAN of the 5 medium/large', MEDLARGE)] if ref == 'C2C' else []):
            med = np.nanmedian(R[:, cols, di], axis=1); okm = med[~np.isnan(med)]
            rows.append(dict(design=f'stratified per-reference {ref}', population=nm, n_resamples=NBOOT,
                             n_defined=len(okm), n_undefined_real_gain_zero=NBOOT - len(okm),
                             n_resamples_undetermined_S_minus='', boot_mean=fmt(okm.mean()),
                             ci_lo_2_5=fmt(np.percentile(okm, 2.5)), ci_hi_97_5=fmt(np.percentile(okm, 97.5)),
                             label=LABEL))
            print(f'{ref} {nm}: {fmt(okm.mean())} [{fmt(np.percentile(okm, 2.5))}, {fmt(np.percentile(okm, 97.5))}]'
                  f' (undefined {NBOOT - len(okm)})')
    csvout(RES / 'E22_1_bootstrap_intervals.csv', rows)
    np.save(RES / 'E22_1_bootstrap_ratios.npy', R)
    print(f'total {time.time() - t0:.0f}s')


if __name__ == '__main__':
    {'point': point, 'boot': boot}[sys.argv[1]]()
