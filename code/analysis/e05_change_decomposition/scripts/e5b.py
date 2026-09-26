"""E5-b: re-split stability. Re-draw fit/calibration from fit U calibration with seeds 1..200 (original = seed 0),
same grouping, sizes and shuffle rule; development unchanged; all settings of a benchmark share the re-splits."""
from r2_common import *
import random, hashlib, collections
import numpy as np
from scipy.stats import binom
import data_r1

SEEDS = list(range(0, 201))
MMLU_SEED = 'P2_MMLU_PRO_BREADTH_20260915_v1'          # build_candidates.py
MMLU_STAGE = ROOT / 'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z'

main = load_main()
x2 = load_x2()
x1 = load_x1()


def xcuts_csv(csvpath, setting):
    return [r['threshold'] for r in csvread(csvpath) if r['setting'] == setting]


# ---------------- per-setting unit tables (pool = fit + cal, plus dev)
def units(s):
    pair, task, ref = s
    if pair in ('small', 'medium', 'large'):
        D = main[pair, task]
        f, c, d = D['fit'], D['cal'], D['dev']
        b = 'T' if ref == 'Text' else 'C'
        return (BENCH[task],
                list(f['ids']) + list(c['ids']),
                np.concatenate([f['scores']['ProbeMax'], c['scores']['ProbeMax']]),
                np.array([x != y for x, y in zip(list(f['ans']['R']) + list(c['ans']['R']),
                                                 list(f['ans'][b]) + list(c['ans'][b]))], bool),
                d['scores']['ProbeMax'], data_r1.disagreement(d, ref))
    if pair == 'X2-OLMo':
        ds = BENCH[task]; D = x2[ds]
        pool_ids = D['fit']['ids'] + D['cal']['ids']
        u = np.array(D['fit']['u'] + D['cal']['u'])
        d = np.array([a != b for a, b in zip(D['fit']['oR'] + D['cal']['oR'], D['fit']['oT'] + D['cal']['oT'])], bool)
        dv = np.array([a != b for a, b in zip(D['dev']['oR'], D['dev']['oT'])], bool)
        return ds, pool_ids, u, d, np.array(D['dev']['u']), dv
    ds = BENCH[task]; D = x1[ds]
    key = 'oT' if ref == 'Text' else 'oC'
    pool_ids = D['fit']['ids'] + D['cal']['ids']
    u = np.array(D['fit']['u'] + D['cal']['u'])
    d = np.array([a != b for a, b in zip(D['fit']['oR'] + D['cal']['oR'], D['fit'][key] + D['cal'][key])], bool)
    dv = np.array([a != b for a, b in zip(D['dev']['oR'], D['dev'][key])], bool)
    return ds, pool_ids, u, d, np.array(D['dev']['u']), dv


U = {s: units(s) for s in ALL21}

# ---------------- re-splits per benchmark (shared by all settings of that benchmark)
POOL = {}            # bench -> ordered pool ids (as the settings list them)
for s in ALL21:
    ds, ids, *_ = U[s]
    if ds in POOL:
        assert POOL[ds] == ids, ('pool mismatch', s)   # all settings of a benchmark share units and order
    else:
        POOL[ds] = ids
NFIT = {'obqa': 2100, 'arc': 670, 'mmlu_pro': 3000}
ORIG_FIT = {'obqa': set(main['large', 'OBQA']['fit']['ids']), 'arc': set(main['large', 'ARC']['fit']['ids']),
            'mmlu_pro': set(main['large', 'MMLU-Pro']['fit']['ids'])}


def h(x): return hashlib.sha256(x.encode()).hexdigest()


def allocate(N, counts):                                  # verbatim from build_candidates.py
    total = sum(counts.values()); quotas = {c: N * n // total for c, n in counts.items()}
    order = sorted(counts, key=lambda c: (-(N * counts[c] % total), c))
    for c in order[:N - sum(quotas.values())]: quotas[c] += 1
    assert sum(quotas.values()) == N
    return quotas


MMLU_CAT = {}
for sp in ['fit', 'cal']:
    for g in read(MMLU_STAGE / f'splits/{sp}_groups.json'):
        MMLU_CAT[g['representative_id']] = (g['category'], g['group_hash'])


def resplit(bench, seed):
    """-> boolean mask over POOL[bench]: True = fit. Same grouping, sizes and shuffle rule as the frozen split."""
    ids = POOL[bench]
    if bench in ('obqa', 'arc'):
        reps = sorted(ids)                                # lexicographically sorted representatives
        random.Random(seed).shuffle(reps)
        fit = set(reps[:NFIT[bench]])
    else:                                                 # MMLU-Pro: category quotas, hash order (build_candidates.pick)
        seedstr = MMLU_SEED if seed == 0 else f'{MMLU_SEED}|resplit{seed}'
        counts = collections.Counter(MMLU_CAT[i][0] for i in ids)
        quotas = allocate(NFIT[bench], counts)
        fit = set()
        for c in sorted(counts):
            rows = sorted([i for i in ids if MMLU_CAT[i][0] == c], key=lambda i: h(seedstr + '|split_fit|' + MMLU_CAT[i][1]))
            fit.update(rows[:quotas[c]])
    return np.array([i in fit for i in ids], bool)


MASKS = {b: {s: resplit(b, s) for s in SEEDS} for b in POOL}
seed0_ok = {b: bool((MASKS[b][0] == np.array([i in ORIG_FIT[b] for i in POOL[b]], bool)).all()) for b in POOL}
print('seed 0 reproduces the frozen split:', seed0_ok)

# ---------------- original ledgers (for the original outcome and the needed-m computation)
from common_r1 import ledgers                                       # noqa: E402
LED = ledgers()


def orig_ledger(s):
    pair, task, ref = s
    if pair in ('small', 'medium', 'large'):
        return [dict(q=r['q'], n=r['n'], k=r['k'], p=r['p']) for r in LED[s]]
    path = (XFAM / 'results/analysis/certification_ledger_60.csv') if pair == 'X2-OLMo' else (X1 / 'results/analysis/certification_ledger_80.csv')
    name = f"{BENCH[task]}/{'Text' if pair == 'X2-OLMo' else ref}"
    return [dict(q=float(r['q']), n=int(r['n']), k=int(r['k']), p=float(r['p'])) for r in csvread(path) if r['setting'] == name]


def needed_m(rows, N_cal):
    best = min(rows, key=lambda r: (r['p'], r['q']))
    n, k = best['n'], best['k']
    if n == 0:
        return dict(min_p_q=best['q'], r='', m='not attainable (n=0 at the smallest-p grid point)', m_scaled='')
    r = k / n
    if r >= .05:
        return dict(min_p_q=best['q'], r=f'{r:.4f}', m='not attainable (r >= .05)', m_scaled='')
    m = 1
    while m < 2_000_000:
        if binom.cdf(int(np.floor(r * m)), m, .05) <= .001:
            break
        m += 1
    else:
        return dict(min_p_q=best['q'], r=f'{r:.4f}', m='not attainable (m > 2e6)', m_scaled='')
    return dict(min_p_q=best['q'], r=f'{r:.4f}', m=m, m_scaled=f'{m * N_cal / n:.0f}')


# ---------------- the 200 re-splits
rows, per_seed = [], []
for s in ALL21:
    ds, ids, u, d, udev, ddev = U[s]
    q0 = EXPECTED_Q[s] if s in EXPECTED_Q else 0.0
    orig_outcome = 'deploy' if q0 > 0 else 'fallback'
    qs, cov, chg, omit, cert = [], [], [], [], 0
    for seed in SEEDS[1:]:
        m = MASKS[ds][seed]
        cuts = thresholds(list(u[m]))
        led = ledger_rows(u[~m], d[~m], cuts)
        acc = [r['q'] for r in led if r['accepted']]
        q = acc[-1] if acc else 0.
        per_seed.append(dict(setting=sname(s), seed=seed, q=q, N_cal=int((~m).sum()),
                             n=led[GRID.index(q)]['n'] if q > 0 else 0, k=led[GRID.index(q)]['k'] if q > 0 else 0, label=LABEL))
        if q > 0:
            cert += 1; qs.append(q)
            t = cuts[GRID.index(q)]
            md = data_r1.route_mask(udev, q, t)
            cov.append(100 * md.mean()); chg.append(int(ddev[md].sum())); omit.append(int(md.sum()))
    n_seeds = len(SEEDS) - 1
    match = cert if orig_outcome == 'deploy' else n_seeds - cert
    fmt = lambda v: f'{np.median(v):.4g}' if v else ''
    iqr = lambda v: f'[{np.percentile(v, 25):.4g}, {np.percentile(v, 75):.4g}]' if v else ''
    N_cal_orig = orig_ledger(s)[0]['n'] if False else None
    led0 = orig_ledger(s)
    N_cal = {'obqa': 1366, 'arc': 448, 'mmlu_pro': 6000}[ds]
    nm = needed_m(led0, N_cal)
    rows.append(dict(setting=sname(s), benchmark=ds, orig_outcome=f'{orig_outcome} q={q0:g}',
                     cert_rate=f'{cert / n_seeds:.3f}', match_rate=f'{match / n_seeds:.3f}',
                     stable='stable' if match / n_seeds >= .80 else 'split-sensitive',
                     median_q=fmt(qs), IQR_q=iqr(qs), median_dev_coverage_pct=fmt(cov),
                     median_dev_changed=fmt(chg), median_dev_omitted=fmt(omit),
                     n_deploying=cert, min_p_q=nm['min_p_q'], r_at_min_p=nm['r'], needed_m=nm['m'],
                     needed_m_scaled_to_N_cal=nm['m_scaled'], label=LABEL))
    print(f"{sname(s):24s} {orig_outcome:8s} cert={cert / n_seeds:.3f} match={match / n_seeds:.3f} "
          f"medq={fmt(qs)} {iqr(qs)} cov={fmt(cov)} chg={fmt(chg)}/{fmt(omit)} m={nm['m']} ({nm['m_scaled']})")

csvout(RES / 'e5b_resplit_stability.csv', rows)
csvout(RES / 'e5b_resplit_per_seed.csv', per_seed)
csvout(RES / 'e5b_seed0_check.csv', [dict(benchmark=b, seed0_reproduces_frozen_split=v, label=LABEL) for b, v in seed0_ok.items()])
