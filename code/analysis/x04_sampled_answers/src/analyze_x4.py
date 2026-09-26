"""X4 Step 4 analysis (CPU, login node): certification with sampled receiver answers, large pair, Text reference, OBQA + ARC.

Order: (0) verify results/runs/MANIFEST.sha256; (1) everything gold-free -> results/analysis/*.csv + X4_PRE_GOLD.json, hashed in
CERT_HASHES.json (UTC); (2) only then gold (P2_SCORING_V2 labels, large pair, field 'gold') for accuracy.
Stored inputs (as the paper's re-analyses load them, P2_R1_CPU data_r1.load_pair_dataset): ProbeMax = ZG records/probe_records.jsonl
(OBQA) and BND records/large_arc_{fit,cal,dev}_probes.jsonl (ARC); frozen fit thresholds = BND thresholds/large_{obqa,arc}.json
(asserted equal to the fit order statistics of the stored scores); greedy labels = V2 labels o_R / o_T (pair large); units = BND
representatives (fit/cal/dev). Sampled labels = X4 outputs R.parsed / T.parsed (runtime error -> INVALID).
Rules as X3 (common_r1 thresholds/pval/cp999/deploy, data_r1 route_mask; INVALID an ordinary label). AUROC = Mann-Whitney, ties 1/2.
Added disagreement = dev mean(d_sampled) - mean(d_greedy), paired bootstrap default_rng(0).integers(0, n, (2000, n)), 2.5/97.5% quantiles.
u == 0 split as E14-2; 200 re-splits seeds 1..200 with the E5-b rule (thresholds re-fit on the re-drawn fit part from the stored scores).
Checks: greedy labels + stored scores reproduce the paper's large q (OBQA/Text .80, ARC/Text .95) and dev u == 0 counts (354/742, 217/299).
usage: analyze_x4.py 'results/runs/chain_*.jsonl'
"""
import sys
sys.dont_write_bytecode = True
import glob, csv, random
from xfam_common import *
sys.path.insert(0, str(ROOT / 'P2_R1_CPU_20260919T045556Z/src'))
from common_r1 import thresholds, pval, cp999, deploy, GRID, tv, EXPECTED_Q
from data_r1 import route_mask
import numpy as np
from scipy.stats import beta

A = X / 'results/analysis'; A.mkdir(parents=True, exist_ok=True)
INV = 'INVALID'; NFIT = {'obqa': 2100, 'arc': 670}; PAPER_Q = {'obqa': EXPECTED_Q[('large', 'OBQA', 'Text')], 'arc': EXPECTED_Q[('large', 'ARC', 'Text')]}
PAPER_U0 = {'obqa': (354, 742), 'arc': (217, 299)}

# ---------------- (0) manifest
man = X / 'results/runs/MANIFEST.sha256'; listed = {}
for line in man.read_text().splitlines():
    if line.strip() and not line.startswith('#'):
        h, p = line.split(None, 1); listed[p.strip().lstrip('*')] = h
mcheck = {p: dict(listed=h, now=sha(man.parent / p), ok=sha(man.parent / p) == h) for p, h in listed.items()}
assert all(v['ok'] for v in mcheck.values()), 'manifest mismatch'
files = sorted(glob.glob(str(X / sys.argv[1]))); assert files and {pathlib.Path(f).name for f in files} <= set(listed)
save(A / 'OUTPUT_HASHES.json', dict(utc=utc(), note='computed before any gold read', manifest_check=mcheck, files={str(pathlib.Path(f).relative_to(X)): sha(f) for f in files}))
out = {}
for f in files:
    for r in jl(f):
        k = (r['dataset'], r['id']); assert k not in out, k; assert r['sampling'] == 'on'; out[k] = r


def wcsv(name, rows):
    with open(A / name, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r))); w.writeheader(); w.writerows(rows)


def ledger_rows(u_cal, d_cal, cuts):
    rows = []
    for q, t in zip(GRID, cuts):
        m = route_mask(u_cal, q, t); n = int(m.sum()); k = int(d_cal[m].sum())
        rows.append(dict(q=q, threshold=t, N=len(u_cal), n=n, k=k, p=pval(k, n), CP999=cp999(k, n), accepted=pval(k, n) <= .001))
    return rows


def mw(d, u):
    d = np.asarray(d, bool); u = np.asarray(u, float); pos, neg = u[d], u[~d]
    if not len(pos) or not len(neg): return float('nan')
    return float(((pos[:, None] > neg[None, :]).sum() + .5 * (pos[:, None] == neg[None, :]).sum()) / (len(pos) * len(neg)))


def cp95(k, n):
    if n == 0: return (float('nan'), float('nan'))
    return (float(beta.ppf(.025, k, n - k + 1)) if k > 0 else 0.0, float(beta.ppf(.975, k + 1, n - k)) if k < n else 1.0)


def mask_at(u, q, cuts): return route_mask(u, q, cuts[GRID.index(q)]) if q > 0 else np.zeros(len(u), bool)


# ---------------- stored inputs
lab = {}
for nm, sp in [('full_train', 'train'), ('full_development', 'dev')]:
    for r in jl(V2L / f'{nm}_P2_SCORING_V2.jsonl'):
        if r['pair'] == 'large' and r['dataset'] in NFIT: lab[(r['dataset'], sp, r['id'])] = dict(o_R=r['o_R'], o_T=r['o_T'])   # gold not kept
probes = {'obqa': {r['id']: r['ProbeMax'] for r in jl(ZG / 'records/probe_records.jsonl')}, 'arc': {}}
for sp in ['fit', 'cal', 'dev']:
    for r in jl(BND / f'records/large_arc_{sp}_probes.jsonl'): probes['arc'][r['id']] = r['ProbeMax']

ledger, table, inv_rows, u0_rows, rs_rows, rs_seed, checks, D = [], [], [], [], [], [], [], {}
for ds in DATASETS:
    S = {}
    for sp in ['fit', 'cal', 'dev']:
        ids = read(BND / f'splits/{ds}_{sp}_representatives.json')
        assert ids == [r['id'] for r in jl(POP / f'{ds}_{sp}.jsonl') if r['representative']]
        miss = [i for i in ids if (ds, i) not in out]; assert not miss, ('missing outputs', ds, sp, len(miss))
        rr = [out[(ds, i)] for i in ids]; g = [lab[(ds, 'dev' if sp == 'dev' else 'train', i)] for i in ids]
        S[sp] = dict(ids=ids, u=np.array([probes[ds][i] for i in ids], float),
                     sR=np.array([r['R']['parsed'] if r.get('runtime_error') is None else INV for r in rr], object),
                     sT=np.array([r['T']['parsed'] if r.get('runtime_error') is None else INV for r in rr], object),
                     gR=np.array([x['o_R'] for x in g], object), gT=np.array([x['o_T'] for x in g], object),
                     err=sum(r.get('runtime_error') is not None for r in rr),
                     seeds_ok=all(r['R']['seed'] == int(hashlib.sha256(('X4|' + r['id'] + '|R').encode()).hexdigest()[:8], 16) and
                                  r['T']['seed'] == int(hashlib.sha256(('X4|' + r['id'] + '|Text').encode()).hexdigest()[:8], 16) for r in rr if r.get('runtime_error') is None))
        S[sp]['ds'] = S[sp]['sR'] != S[sp]['sT']; S[sp]['dg'] = S[sp]['gR'] != S[sp]['gT']
    D[ds] = S; name = f'large/{ds}/Text sampled'
    frozen = read(BND / f'thresholds/large_{ds}.json')['thresholds']; cuts = thresholds(list(S['fit']['u']))
    assert [tv(x) for x in cuts] == [tv(x) for x in frozen], 'frozen thresholds differ from the stored fit scores'
    qg, _ = deploy(ledger_rows(S['cal']['u'], S['cal']['dg'], cuts)); u0 = int((S['dev']['u'] == 0).sum())
    checks.append(dict(setting=name, greedy_q_reproduced=qg, paper_greedy_q=PAPER_Q[ds], ok_q=qg == PAPER_Q[ds], dev_u0=f"{u0}/{len(S['dev']['u'])}",
                       paper_dev_u0='%d/%d' % PAPER_U0[ds], ok_u0=(u0, len(S['dev']['u'])) == PAPER_U0[ds], seeds_ok=all(S[s]['seeds_ok'] for s in S),
                       runtime_errors=sum(S[s]['err'] for s in S)))
    led = ledger_rows(S['cal']['u'], S['cal']['ds'], cuts); q, acc = deploy(led)
    for r in led: ledger.append(dict(setting=name, **r))
    best = min(led, key=lambda r: (r['p'], r['q'])); dv = S['dev']; md = mask_at(dv['u'], q, cuts)
    n, k = int(md.sum()), int(dv['ds'][md].sum()); lo, hi = cp95(k, n)
    N = len(dv['ids']); idx = np.random.default_rng(0).integers(0, N, (2000, N))
    diff = dv['ds'].astype(float) - dv['dg'].astype(float); boot = diff[idx].mean(axis=1); blo, bhi = [float(x) for x in np.quantile(boot, [.025, .975])]
    table.append(dict(setting=name, N_fit=len(S['fit']['ids']), N_cal=len(S['cal']['ids']), N_dev=N,
                      cal_disagreements_sampled=int(S['cal']['ds'].sum()), cal_disagreement_rate_sampled=float(S['cal']['ds'].mean()),
                      dev_disagreements_sampled=int(dv['ds'].sum()), dev_disagreement_rate_sampled=float(dv['ds'].mean()),
                      dev_disagreements_greedy=int(dv['dg'].sum()), dev_disagreement_rate_greedy=float(dv['dg'].mean()),
                      added_disagreement=float(diff.mean()), added_disagreement_boot95_lo=blo, added_disagreement_boot95_hi=bhi,
                      dev_AUROC_stored_u_sampled_disagreement=mw(dv['ds'], dv['u']),
                      deployed_q=q if q > 0 else 'fallback', threshold=cuts[GRID.index(q)] if q > 0 else '', accepted_q=';'.join(f'{x:g}' for x in acc) or 'none',
                      min_p=best['p'], min_p_q=best['q'], min_p_k=best['k'], min_p_n=best['n'], min_UCB999=min(r['CP999'] for r in led),
                      dev_coverage=n / N, dev_omitted=n, dev_changed=k, dev_change_rate=(k / n if n else float('nan')), dev_change_CP95_lo=lo, dev_change_CP95_hi=hi,
                      dev_sampled_vs_greedy_R=float((dv['sR'] != dv['gR']).mean()), dev_sampled_vs_greedy_R_n=int((dv['sR'] != dv['gR']).sum()),
                      dev_sampled_vs_greedy_T=float((dv['sT'] != dv['gT']).mean()), dev_sampled_vs_greedy_T_n=int((dv['sT'] != dv['gT']).sum()),
                      status_note='nominal (OBQA calibration used when ProbeMax was chosen)' if ds == 'obqa' else ''))
    for sp in ['fit', 'cal', 'dev']:
        x = S[sp]; iR, iT = x['sR'] == INV, x['sT'] == INV
        inv_rows.append(dict(setting=name, split=sp, N=len(iR), sampled_R_INVALID=int(iR.sum()), sampled_R_INVALID_rate=float(iR.mean()),
                             sampled_T_INVALID=int(iT.sum()), sampled_T_INVALID_rate=float(iT.mean()), both_INVALID_counted_as_agreement=int((iR & iT).sum())))
    for sp in ['cal', 'dev']:   # E14-2 split at the deployed q
        x = S[sp]; m = mask_at(x['u'], q, cuts); z = x['u'] == 0
        n0, k0 = int((m & z).sum()), int(x['ds'][m & z].sum()); npl, kpl = int((m & ~z).sum()), int(x['ds'][m & ~z].sum())
        r0, rp = cp95(k0, n0), cp95(kpl, npl)
        u0_rows.append(dict(setting=name, split=sp, q=q if q > 0 else 'fallback', N=len(z), share_u0_all=float(z.mean()), omitted_n=int(m.sum()),
                            n0=n0, k0=k0, k0_over_n0=(k0 / n0 if n0 else float('nan')), k0_CP95_lo=r0[0], k0_CP95_hi=r0[1],
                            n_pos=npl, k_pos=kpl, kpos_over_npos=(kpl / npl if npl else float('nan')), kpos_CP95_lo=rp[0], kpos_CP95_hi=rp[1],
                            share_u0_among_omitted=(n0 / int(m.sum()) if m.sum() else float('nan'))))
    pool = S['fit']['ids'] + S['cal']['ids']; up = np.concatenate([S['fit']['u'], S['cal']['u']]); dp = np.concatenate([S['fit']['ds'], S['cal']['ds']])
    orig_fit = set(S['fit']['ids'])

    def rmask(seed):
        reps = sorted(pool); random.Random(seed).shuffle(reps); f = set(reps[:NFIT[ds]]); return np.array([i in f for i in pool], bool)

    seed0 = bool((rmask(0) == np.array([i in orig_fit for i in pool], bool)).all()); cert = 0; qs = []
    for seed in range(1, 201):
        m = rmask(seed); c_s = thresholds(list(up[m])); q_s, _ = deploy(ledger_rows(up[~m], dp[~m], c_s))
        rs_seed.append(dict(setting=name, seed=seed, q=q_s)); cert += q_s > 0; qs += [q_s] if q_s > 0 else []
    rs_rows.append(dict(setting=name, seed0_reproduces_frozen_split=seed0, x4_outcome='deploy' if q > 0 else 'fallback', n_resplits=200,
                        certification_rate=cert / 200, agreement_with_x4_outcome=(cert if q > 0 else 200 - cert) / 200, median_q=float(np.median(qs)) if qs else '',
                        label='descriptive'))

names = ['certification_ledger_40.csv', 'dev_table_pre_gold.csv', 'invalid_sampled.csv', 'u0_split_E14_2.csv', 'resplit.csv', 'resplit_per_seed.csv', 'input_checks.csv']
for n_, rows in zip(names, [ledger, table, inv_rows, u0_rows, rs_rows, rs_seed, checks]): wcsv(n_, rows)
save(A / 'X4_PRE_GOLD.json', dict(utc=utc(), table=table, invalid=inv_rows, u0=u0_rows, resplit=rs_rows, checks=checks))
save(A / 'CERT_HASHES.json', dict(utc=utc(), note='certification and all gold-free results written before any gold read', files={n_: sha(A / n_) for n_ in names + ['X4_PRE_GOLD.json']}))
print('PRE-GOLD', json.dumps(dict(checks=checks, table=table, u0=u0_rows, resplit=rs_rows), indent=1, default=str), flush=True)

# ---------------- (2) gold (only after CERT_HASHES.json)
gold = {}
for nm in ['full_train', 'full_development']:
    for r in jl(V2L / f'{nm}_P2_SCORING_V2.jsonl'):
        if r['pair'] == 'large': gold[(r['dataset'], r['id'])] = r['gold']
acc_rows = []
for ds in DATASETS:
    for sp in ['fit', 'cal', 'dev']:
        x = D[ds][sp]; y = np.array([gold[(ds, i)] for i in x['ids']], object); n = len(y)
        acc_rows.append(dict(dataset=ds, split=sp, N=n, sampled_R_correct=int((x['sR'] == y).sum()), sampled_T_correct=int((x['sT'] == y).sum()),
                             sampled_R_acc=float((x['sR'] == y).mean()), sampled_T_acc=float((x['sT'] == y).mean()),
                             greedy_R_acc=float((x['gR'] == y).mean()), greedy_T_acc=float((x['gT'] == y).mean())))
wcsv('accuracy_per_split.csv', acc_rows)
save(A / 'X4_RESULTS.json', dict(utc=utc(), gold_source='P2_SCORING_V2 labels, pair large, field gold', accuracy=acc_rows))
print('GOLD', json.dumps(acc_rows, indent=1), flush=True)
