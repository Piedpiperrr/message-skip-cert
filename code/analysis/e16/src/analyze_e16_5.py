"""E16-5 analysis (CPU, login node), as PREREG.md. Strong-helper Text setting: receiver Qwen3-1.7B reading the stored Qwen2.5-7B Text messages
(E16 Job A outputs, T.parsed); R answers and ProbeMax reused from the medium pair (MEDIUM stage-1 actions/probes, hash-checked against its
INFERENCE_COMPLETE.json), so the 20 candidate thresholds are the medium pair's (thresholds/{ds}.json, asserted = fit order statistics).
Units: the medium pair's representatives (splits/{ds}_{split}_representatives.json). Rules: common_r1 thresholds/pval/cp999/deploy, data_r1 route_mask;
INVALID an ordinary label. AUROC = Mann-Whitney, ties 1/2. Re-splits: E5-b rule, seeds 1-200. Needed N_cal: E5-b needed_m rule.
Order: certification + everything gold-free written and hashed (SEAL_RECEIPT.json), then gold (V2 labels 'gold') and the E9c large-helper argmax."""
import sys
sys.dont_write_bytecode = True
import csv, glob, random, math
from xfam_common import *
sys.path.insert(0, str(ROOT / 'P2_R1_CPU_20260919T045556Z/src'))
from common_r1 import thresholds, pval, cp999, deploy, GRID, tv
from data_r1 import route_mask
import numpy as np
from scipy.stats import beta, binom
A = X / 'results/analysis_e16_5'; A.mkdir(parents=True, exist_ok=True); INV = 'INVALID'; NFIT = {'obqa': 2100, 'arc': 670}
man = X / 'results/MANIFEST_jobA.sha256'
for line in man.read_text().splitlines():
    if line.strip() and not line.startswith('#'):
        h, p = line.split(None, 1); assert sha(X / 'results' / p.strip()) == h, p
inv = read(MED / 'INFERENCE_COMPLETE.json')['files']
for f in ['actions', 'probes']:
    for ds in NFIT:
        for sp in ['fit', 'cal', 'dev']: assert sha(MED / f'{f}/{ds}_{sp}.jsonl') == inv[f'{f}/{ds}_{sp}.jsonl'], (f, ds, sp)
T = {(r['dataset'], r['id']): r for f in sorted((X / 'results/e16_5').glob('shard*.jsonl')) for r in jl(f)}


def cp95(k, n): return (float(beta.ppf(.025, k, n - k + 1)) if k > 0 else 0.0, float(beta.ppf(.975, k + 1, n - k)) if k < n else 1.0) if n else (float('nan'),) * 2


def mw(d, u):
    d = np.asarray(d, bool); u = np.asarray(u, float); pos, neg = u[d], u[~d]
    return float(((pos[:, None] > neg[None, :]).sum() + .5 * (pos[:, None] == neg[None, :]).sum()) / (len(pos) * len(neg))) if len(pos) and len(neg) else float('nan')


def ledger(u, d, cuts):
    out = []
    for q, t in zip(GRID, cuts):
        m = route_mask(u, q, t); n = int(m.sum()); k = int(d[m].sum()); out.append(dict(q=q, threshold=t, N=len(u), n=n, k=k, p=pval(k, n), CP999=cp999(k, n), accepted=pval(k, n) <= .001))
    return out


def needed_m(rows, N_cal):   # E5-b rule (P2_R2_CPU scripts/e5b.py needed_m)
    best = min(rows, key=lambda r: (r['p'], r['q'])); n, k = best['n'], best['k']
    if n == 0: return dict(min_p_q=best['q'], needed='unreachable (n=0 at the smallest-p candidate)')
    r = k / n
    if r >= .05: return dict(min_p_q=best['q'], r=r, needed='unreachable (r >= .05)')
    m = 1
    while m < 2_000_000 and binom.cdf(int(np.floor(r * m)), m, .05) > .001: m += 1
    return dict(min_p_q=best['q'], r=r, m=m, needed_N_cal=round(m * N_cal / n)) if m < 2_000_000 else dict(min_p_q=best['q'], r=r, needed='unreachable (m > 2e6)')


res, ledg, rs_seed, S = {}, [], [], {}
for ds in NFIT:
    D = {}
    for sp in ['fit', 'cal', 'dev']:
        reps = read(MED.parent / f'splits/{ds}_{sp}_representatives.json')
        Ra = {r['id']: r for r in jl(MED / f'actions/{ds}_{sp}.jsonl') if r['action'] == 'R'}; Pm = {r['id']: r for r in jl(MED / f'probes/{ds}_{sp}.jsonl')}
        miss = [i for i in reps if (ds, i) not in T or T[(ds, i)].get('runtime_error')]; assert not miss, (ds, sp, len(miss))
        D[sp] = dict(ids=reps, u=np.array([Pm[i]['ProbeMax'] for i in reps], float), oR=np.array([Ra[i]['answer'] for i in reps], object),
                     oT=np.array([T[(ds, i)]['T']['parsed'] for i in reps], object))
        D[sp]['d'] = D[sp]['oR'] != D[sp]['oT']
    S[ds] = D
    cuts = thresholds(list(D['fit']['u'])); stored = read(MED / f'thresholds/{ds}.json')['thresholds']
    assert [tv(x) for x in cuts] == [tv(x) for x in stored], 'medium thresholds differ'
    L = ledger(D['cal']['u'], D['cal']['d'], cuts); q, acc = deploy(L)
    for r in L: ledg.append(dict(setting=f'strong-helper {ds}/Text', **r))
    dv = D['dev']; md = route_mask(dv['u'], q, cuts[GRID.index(q)]) if q > 0 else np.zeros(len(dv['u']), bool)
    n, k = int(md.sum()), int(dv['d'][md].sum()); lo, hi = cp95(k, n); best = min(L, key=lambda r: (r['p'], r['q']))
    pool = D['fit']['ids'] + D['cal']['ids']; up = np.concatenate([D['fit']['u'], D['cal']['u']]); dp = np.concatenate([D['fit']['d'], D['cal']['d']])
    def rmask(seed):
        reps = sorted(pool); random.Random(seed).shuffle(reps); f = set(reps[:NFIT[ds]]); return np.array([i in f for i in pool], bool)
    seed0 = bool((rmask(0) == np.array([i in set(D['fit']['ids']) for i in pool], bool)).all()); cert = 0
    for seed in range(1, 201):
        m = rmask(seed); qq, _ = deploy(ledger(up[~m], dp[~m], thresholds(list(up[m])))); cert += qq > 0; rs_seed.append(dict(setting=ds, seed=seed, q=qq))
    auc = mw(dv['d'], dv['u'])
    res[ds] = dict(setting=f'strong-helper {ds}/Text (Qwen2.5-7B messages -> Qwen3-1.7B)', N_fit=len(D['fit']['ids']), N_cal=len(D['cal']['ids']), N_dev=len(dv['ids']),
                   cal_disagreements=int(D['cal']['d'].sum()), cal_disagreement=float(D['cal']['d'].mean()), dev_disagreements=int(dv['d'].sum()), dev_disagreement=float(dv['d'].mean()),
                   dev_AUROC_MW=auc, deployed_q=q if q > 0 else 'fallback', accepted_q=';'.join(f'{x:g}' for x in acc) or 'none', min_p=best['p'], min_p_q=best['q'], min_p_k=best['k'], min_p_n=best['n'],
                   kappa=n / len(dv['ids']), dev_omitted=n, dev_changed=k, dev_change_rate=k / n if n else float('nan'), dev_CP95_lo=lo, dev_CP95_hi=hi,
                   INVALID_R_cal=int((D['cal']['oR'] == INV).sum()), INVALID_T_cal=int((D['cal']['oT'] == INV).sum()), INVALID_R_dev=int((dv['oR'] == INV).sum()), INVALID_T_dev=int((dv['oT'] == INV).sum()),
                   resplit_seed0_ok=seed0, resplit_cert_rate=cert / 200, needed=(needed_m(L, len(D['cal']['ids'])) if q == 0 else None),
                   pattern=('consistent' if (q > 0 and auc >= .80) or (q == 0 and auc < .80) else 'exception'))
for n_, rows in [('ledger_40.csv', ledg), ('resplit_per_seed.csv', rs_seed)]:
    with open(A / n_, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
save(A / 'E16_5_PRE_GOLD.json', dict(utc=utc(), results=res))
save(A / 'SEAL_RECEIPT.json', dict(utc=utc(), note='certification and all gold-free results hashed before gold', gold_read=False,
                                   files={n_: sha(A / n_) for n_ in ['ledger_40.csv', 'resplit_per_seed.csv', 'E16_5_PRE_GOLD.json']}))
print('SEALED', json.dumps(res, indent=1, default=str), flush=True)
# ---- gold (only after SEAL_RECEIPT.json)
gold = {}
for nm in ['full_train', 'full_development']:
    for r in jl(V2L / f'{nm}_P2_SCORING_V2.jsonl'):
        if r['pair'] == 'large': gold[(r['dataset'], r['id'])] = r['gold']
for ds, D in S.items():
    dv = D['dev']; y = np.array([gold[(ds, i)] for i in dv['ids']], object); q = res[ds]['deployed_q']
    cuts = thresholds(list(D['fit']['u'])); md = route_mask(dv['u'], q, cuts[GRID.index(q)]) if q != 'fallback' else np.zeros(len(y), bool)
    pol = np.where(md, dv['oR'], dv['oT'])
    H = {r['id']: r['argmax_helper_label'] for r in jl(E9 / f'records/large_{ds}_dev_plain_rank2.jsonl')}
    hacc = float(np.mean([H[i] == g for i, g in zip(dv['ids'], y)])) if all(i in H for i in dv['ids']) else None
    aR, aT, aP = float((dv['oR'] == y).mean()), float((dv['oT'] == y).mean()), float((pol == y).mean())
    G = 100 * (aT - aR)
    res[ds].update(acc_helper_alone_E9c_argmax=hacc, acc_R=aR, acc_Text_strong=aT, acc_policy=aP, G_points=G, kappa_alpha_points=(100 * res[ds]['kappa'] * .05 if q != 'fallback' else None),
                   retained_gain=((aP - aR) / (aT - aR) if aT - aR > 0 else 'n/a'))
save(A / 'E16_5_RESULTS.json', dict(utc=utc(), results=res))
print('GOLD', json.dumps({k: {a: v[a] for a in ['acc_helper_alone_E9c_argmax', 'acc_R', 'acc_Text_strong', 'acc_policy', 'G_points', 'kappa_alpha_points', 'retained_gain']} for k, v in res.items()}, indent=1))
