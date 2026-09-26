"""X3 Step 5 analysis (CPU, login node). Extends X2 analyze_x2.py (same rule functions from P2_R1_CPU common_r1/data_r1) with the X3 items.

Order: (0) verify the production output manifest (results/runs/MANIFEST.sha256); (1) certification and every gold-free diagnostic from
outputs only -> results/analysis/*.csv + X3_PRE_GOLD.json, hashed in CERT_HASHES.json (with UTC); (2) only then gold (P2_SCORING_V2 labels,
large pair, field 'gold', as X2) for accuracy -> accuracy_per_split.csv, dev_table.csv, X3_RESULTS.json.
Conventions: disagreement = o_R != o_Text with INVALID an ordinary label (two INVALID = agreement); representatives only; thresholds =
fit order statistics ceil(jN/20) (q=1 routes all); route iff u <= t; accept iff P[Bin(n,.05) <= k] <= .001; deploy the largest accepted q.
AUROC = explicit Mann-Whitney, tied pairs credit 1/2 (E13 item 8; equals sklearn roc_auc_score, also reported).
Diagnostics (NOT deployable / descriptive): both-parse certification (E11-a), 200 re-splits seeds 1..200 (E5-b rule: sorted fit+cal
representatives, random.Random(seed).shuffle, first N_fit = fit; dev unchanged), share of dev u == 0, argmax recertification (E13 item 5).
usage: analyze_x3.py '<outputs glob relative to this folder>'
  env (only for the code check on X2 outputs): X3A_ROOT=<folder with records/populations and outputs>, X3A_OUT=<out dir>, X3A_NO_MANIFEST=1
"""
import sys
sys.dont_write_bytecode = True
import glob, csv, math, random
from xfam_common import *
sys.path.insert(0, str(ROOT / 'P2_R1_CPU_20260919T045556Z/src'))
from common_r1 import thresholds, pval, cp999, deploy, GRID, tv
from data_r1 import route_mask
import numpy as np
from scipy.stats import beta
from sklearn.metrics import roc_auc_score

BASE = pathlib.Path(os.environ.get('X3A_ROOT', X)); POPD = BASE / 'records/populations'
A = pathlib.Path(os.environ.get('X3A_OUT', X / 'results/analysis')); A.mkdir(parents=True, exist_ok=True)
DIAG = 'DIAGNOSTIC (descriptive, not deployable)'
INV = 'INVALID'
NFIT = {'obqa': 2100, 'arc': 670}

# ---------------- (0) outputs and manifest
files = sorted(glob.glob(str(BASE / sys.argv[1]))); assert files
mcheck = None
if not os.environ.get('X3A_NO_MANIFEST'):
    man = BASE / 'results/runs/MANIFEST.sha256'; listed = {}
    for line in man.read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            h, p = line.split(None, 1); listed[p.strip().lstrip('*')] = h
    mcheck = {p: dict(listed=h, now=sha(man.parent / p), ok=sha(man.parent / p) == h) for p, h in listed.items()}
    assert all(v['ok'] for v in mcheck.values()), 'manifest mismatch'
    assert {pathlib.Path(f).name for f in files} <= set(listed), 'output file not in manifest'
save(A / 'OUTPUT_HASHES.json', dict(utc=utc(), note='computed before any gold read', manifest_check=mcheck,
                                    files={str(pathlib.Path(f).relative_to(BASE)): sha(f) for f in files}))
out = {}
for f in files:
    for r in jl(f):
        k = (r['dataset'], r['id']); assert k not in out, k; out[k] = r


def wcsv(name, rows):
    with open(A / name, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r))); w.writeheader(); w.writerows(rows)


ans = lambda r, a: (r[a]['parsed'] if r.get('runtime_error') is None else INV)


def ledger_rows(u_cal, d_cal, cuts, keep=None):   # = r2_common.ledger_rows (E5-b / E11-a / E13)
    if keep is not None: u_cal, d_cal = u_cal[keep], d_cal[keep]
    rows = []
    for q, t in zip(GRID, cuts):
        m = route_mask(u_cal, q, t); n = int(m.sum()); k = int(d_cal[m].sum())
        rows.append(dict(q=q, threshold=t, N=len(u_cal), n=n, k=k, p=pval(k, n), CP999=cp999(k, n), accepted=pval(k, n) <= .001))
    return rows


def mw(d, u):   # E13 item 8: explicit Mann-Whitney, ties 1/2
    d = np.asarray(d, bool); u = np.asarray(u, float); pos, neg = u[d], u[~d]
    if not len(pos) or not len(neg): return float('nan')
    return float(((pos[:, None] > neg[None, :]).sum() + .5 * (pos[:, None] == neg[None, :]).sum()) / (len(pos) * len(neg)))


def sk(d, u): return float(roc_auc_score(d, u)) if 0 < np.sum(d) < len(d) else float('nan')


def cp95(k, n):   # two-sided 95% Clopper-Pearson
    if n == 0: return (float('nan'), float('nan'))
    return (float(beta.ppf(.025, k, n - k + 1)) if k > 0 else 0.0, float(beta.ppf(.975, k + 1, n - k)) if k < n else 1.0)


def at_q(u_dev, d_dev, q, cuts):
    md = route_mask(u_dev, q, cuts[GRID.index(q)] if q > 0 else None) if q > 0 else np.zeros(len(u_dev), bool)
    n, k = int(md.sum()), int(d_dev[md].sum()); lo, hi = cp95(k, n)
    return md, dict(dev_coverage=n / len(u_dev), dev_omitted=n, dev_changed=k, dev_change_rate=(k / n if n else float('nan')), dev_change_CP95_lo=lo, dev_change_CP95_hi=hi)


# ---------------- (1) certification and gold-free diagnostics
ledger, table, splitrows, bp_rows, bp_grid, rs_rows, rs_seed, am_rows, am_grid, routes_rows, U = [], [], [], [], [], [], [], [], [], [], {}
for ds in DATASETS:
    S = {}
    for sp in ['fit', 'cal', 'dev']:
        reps = [r['id'] for r in jl(POPD / f'{ds}_{sp}.jsonl') if r['representative']]
        miss = [i for i in reps if (ds, i) not in out]
        assert not miss, ('missing outputs', ds, sp, len(miss))
        rr = [out[(ds, i)] for i in reps]
        S[sp] = dict(ids=reps, recs=rr, u=np.array([r['P']['ProbeMax'] if r.get('runtime_error') is None else np.nan for r in rr], float),
                     oR=np.array([ans(r, 'R') for r in rr], object), oT=np.array([ans(r, 'T') for r in rr], object),
                     err=sum(r.get('runtime_error') is not None for r in rr))
        S[sp]['d'] = S[sp]['oR'] != S[sp]['oT']
        assert np.isfinite(S[sp]['u']).all(), ('non-finite or missing ProbeMax', ds, sp)
    U[ds] = S
    name = f'{ds}/Text'; cuts = thresholds(list(S['fit']['u']))
    led = ledger_rows(S['cal']['u'], S['cal']['d'], cuts); q, acc = deploy(led)
    for r in led: ledger.append(dict(setting=name, **r))
    best = min(led, key=lambda r: (r['p'], r['q']))
    md, dq = at_q(S['dev']['u'], S['dev']['d'], q, cuts)
    dv = S['dev']
    table.append(dict(setting=f'X3 {name}', N_fit=len(S['fit']['ids']), N_cal=len(S['cal']['ids']), N_dev=len(dv['ids']),
                      runtime_errors=sum(S[s]['err'] for s in S),
                      cal_disagreements=int(S['cal']['d'].sum()), cal_disagreement_rate=float(S['cal']['d'].mean()),
                      dev_disagreements=int(dv['d'].sum()), dev_disagreement_rate=float(dv['d'].mean()),
                      dev_AUROC_MW_ties_half=mw(dv['d'], dv['u']), dev_AUROC_sklearn=sk(dv['d'], dv['u']),
                      deployed_q=q if q > 0 else 'fallback', threshold=cuts[GRID.index(q)] if q > 0 else '', accepted_q=';'.join(f'{x:g}' for x in acc) or 'none',
                      min_p=best['p'], min_p_q=best['q'], min_p_k=best['k'], min_p_n=best['n'], min_UCB999=min(r['CP999'] for r in led), **dq,
                      dev_share_u_eq_0=float((dv['u'] == 0).mean()), dev_n_u_eq_0=int((dv['u'] == 0).sum())))
    for r, m in zip(dv['recs'], md):
        routes_rows.append(dict(dataset=ds, id=r['id'], ProbeMax=r['P']['ProbeMax'], route='R' if m else 'Text', o_R=ans(r, 'R'), o_T=ans(r, 'T')))
    # INVALID rates and disagreement split (E5-e / E11-a cells)
    for sp in ['fit', 'cal', 'dev']:
        oR, oT = S[sp]['oR'], S[sp]['oT']; iR, iT = oR == INV, oT == INV; d = S[sp]['d']
        splitrows.append(dict(setting=name, split=sp, N=len(oR), R_INVALID=int(iR.sum()), R_INVALID_rate=float(iR.mean()), T_INVALID=int(iT.sum()), T_INVALID_rate=float(iT.mean()),
                              disagreements=int(d.sum()), both_parseable_differ=int((~iR & ~iT & d).sum()), only_R_INVALID=int((iR & ~iT).sum()),
                              only_T_INVALID=int((~iR & iT).sum()), both_INVALID_counted_as_agreement=int((iR & iT).sum())))
    # both-parse diagnostic (E11-a)
    kc = (S['cal']['oR'] != INV) & (S['cal']['oT'] != INV); kd = (dv['oR'] != INV) & (dv['oT'] != INV)
    lb = ledger_rows(S['cal']['u'], S['cal']['d'], cuts, kc); qb, accb = deploy(lb)
    for r in lb: bp_grid.append(dict(setting=name, **r, label=DIAG))
    ub, db = dv['u'][kd], dv['d'][kd]; mb, dqb = at_q(ub, db, qb, cuts)
    bestb = min(lb, key=lambda r: (r['p'], r['q']))
    bp_rows.append(dict(setting=name, N_cal_bothparse=int(kc.sum()), N_cal=len(kc), N_dev_bothparse=int(kd.sum()), N_dev=len(kd),
                        bothparse_q=qb if qb > 0 else 'no candidate accepted', bothparse_accepted_q=';'.join(f'{x:g}' for x in accb) or 'none',
                        min_p=bestb['p'], min_p_q=bestb['q'], min_p_k=bestb['k'], min_p_n=bestb['n'],
                        dev_disagreement_bothparse=float(db.mean()), dev_AUROC_bothparse_MW=mw(db, ub),
                        **{k.replace('dev_', 'dev_bothparse_'): v for k, v in dqb.items()},
                        dev_coverage_of_all_dev=int(mb.sum()) / len(kd), label=DIAG))
    # 200 re-splits (E5-b)
    pool = S['fit']['ids'] + S['cal']['ids']; up = np.concatenate([S['fit']['u'], S['cal']['u']]); dp = np.concatenate([S['fit']['d'], S['cal']['d']])
    orig_fit = set(S['fit']['ids']); assert len(orig_fit) == NFIT[ds]

    def mask(seed):
        reps = sorted(pool); random.Random(seed).shuffle(reps); f = set(reps[:NFIT[ds]]); return np.array([i in f for i in pool], bool)

    seed0 = bool((mask(0) == np.array([i in orig_fit for i in pool], bool)).all())
    cert, qs, covs = 0, [], []
    for seed in range(1, 201):
        m = mask(seed); c_s = thresholds(list(up[m])); l_s = ledger_rows(up[~m], dp[~m], c_s); q_s, _ = deploy(l_s)
        row = dict(setting=name, seed=seed, q=q_s, N_cal=int((~m).sum()), n=l_s[GRID.index(q_s)]['n'] if q_s else 0, k=l_s[GRID.index(q_s)]['k'] if q_s else 0)
        if q_s > 0:
            cert += 1; qs.append(q_s); _, dq_s = at_q(dv['u'], dv['d'], q_s, c_s); covs.append(dq_s['dev_coverage']); row.update(dev_coverage=dq_s['dev_coverage'], dev_changed=dq_s['dev_changed'], dev_omitted=dq_s['dev_omitted'])
        rs_seed.append(dict(**row, label=DIAG))
    orig = 'deploy' if q > 0 else 'fallback'
    rs_rows.append(dict(setting=name, seed0_reproduces_frozen_split=seed0, original_outcome=orig, n_resplits=200, certification_rate=cert / 200,
                        agreement_with_original=(cert if q > 0 else 200 - cert) / 200, median_q=float(np.median(qs)) if qs else '',
                        median_dev_coverage=float(np.median(covs)) if covs else '', label=DIAG))
    # argmax recertification (E13 item 5)
    out_a = {}
    for sp in ['cal', 'dev']:
        P = [r['P'] for r in S[sp]['recs']]
        oA = np.array([max(p['p_labels'], key=p['p_labels'].get) for p in P], object)
        assert all(a == p['argmax_probe_label'] for a, p in zip(oA, P))
        out_a[sp] = dict(oA=oA, dA=oA != S[sp]['oT'])
    la = ledger_rows(S['cal']['u'], out_a['cal']['dA'], cuts); qa, acca = deploy(la)
    for r in la: am_grid.append(dict(setting=name, **r, label='E13-5 style post hoc family'))
    ma, dqa = at_q(dv['u'], out_a['dev']['dA'], qa, cuts); besta = min(la, key=lambda r: (r['p'], r['q']))
    invd = out_a['dev']['dA'] & (dv['oT'] == INV)
    am_rows.append(dict(setting=name, cal_agreement_oA_vs_native_R=float((out_a['cal']['oA'] == S['cal']['oR']).mean()),
                        cal_disagreement_rate_argmax=float(out_a['cal']['dA'].mean()), q_A=qa if qa > 0 else 'fallback', accepted_q=';'.join(f'{x:g}' for x in acca) or 'none',
                        min_p=besta['p'], min_p_q=besta['q'], min_p_k=besta['k'], min_p_n=besta['n'],
                        dev_disagreements_argmax=int(out_a['dev']['dA'].sum()), dev_AUROC_u_argmax_label_MW=mw(out_a['dev']['dA'], dv['u']),
                        **{k.replace('dev_', 'dev_argmax_'): v for k, v in dqa.items()},
                        dev_share_argmax_disagreements_with_INVALID_Text=float(invd.sum() / out_a['dev']['dA'].sum()) if out_a['dev']['dA'].sum() else float('nan'),
                        label='E13-5 style post hoc family (descriptive)'))

names = ['certification_ledger_40.csv', 'dev_table_pre_gold.csv', 'invalid_and_disagreement_split.csv', 'dev_routes.csv',
         'diag_bothparse.csv', 'diag_bothparse_grid.csv', 'diag_resplit.csv', 'diag_resplit_per_seed.csv', 'diag_argmax_recert.csv', 'diag_argmax_grid.csv']
for n_, rows in zip(names, [ledger, table, splitrows, routes_rows, bp_rows, bp_grid, rs_rows, rs_seed, am_rows, am_grid]): wcsv(n_, rows)
save(A / 'X3_PRE_GOLD.json', dict(utc=utc(), table=table, invalid_split=splitrows, bothparse=bp_rows, resplit=rs_rows, argmax=am_rows))
save(A / 'CERT_HASHES.json', dict(utc=utc(), note='certification and all gold-free diagnostics written before any gold read',
                                  files={n_: sha(A / n_) for n_ in names + ['X3_PRE_GOLD.json']}))
print('PRE-GOLD', json.dumps(dict(table=table, bothparse=bp_rows, resplit=rs_rows, argmax=am_rows), indent=1, default=str), flush=True)

# ---------------- (2) gold (only after CERT_HASHES.json)
gold = {}
for nm in ['full_train', 'full_development']:
    for r in jl(V2L / f'{nm}_P2_SCORING_V2.jsonl'):
        if r['pair'] == 'large': gold[(r['dataset'], r['id'])] = r['gold']
acc_rows = []
for row, ds in zip(table, DATASETS):
    S = U[ds]; g = [gold[(ds, i)] for i in S['dev']['ids']]
    routed = {x['id']: x['route'] == 'R' for x in routes_rows if x['dataset'] == ds}
    pol = sum((o_r if routed[i] else o_t) == y for i, o_r, o_t, y in zip(S['dev']['ids'], S['dev']['oR'], S['dev']['oT'], g))
    row.update(dev_correct_policy=int(pol), dev_correct_reference_Text=int(sum(o == y for o, y in zip(S['dev']['oT'], g))))
    for sp in ['fit', 'cal', 'dev']:
        y = [gold[(ds, i)] for i in S[sp]['ids']]; n = len(y)
        rc = int(sum(o == t for o, t in zip(S[sp]['oR'], y))); tc = int(sum(o == t for o, t in zip(S[sp]['oT'], y)))
        acc_rows.append(dict(dataset=ds, split=sp, N=n, R_correct=rc, T_correct=tc, R_acc=rc / n, T_acc=tc / n))
wcsv('dev_table.csv', table); wcsv('accuracy_per_split.csv', acc_rows)
save(A / 'X3_RESULTS.json', dict(utc=utc(), gold_source='P2_SCORING_V2 labels full_train/full_development, pair large, field gold', table=table, accuracy=acc_rows))
print('GOLD', json.dumps(acc_rows, indent=1), flush=True)
