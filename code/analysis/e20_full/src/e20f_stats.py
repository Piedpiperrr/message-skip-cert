"""E20F Step 6 (login node; gold never read): dev and test statistics at the frozen CERT_E20F.json threshold, surface-form and length diagnostics,
200 re-splits, binormal P from dev, value estimate. Writes STATS_E20F.json + .sha256 and ROUTES_E20F.json + .sha256 (per question: split, id,
s2, route), both hashed before any gold is read.
Definitions (fixed before any E20-full output): change = normalized o_R != normalized o_b (two INVALIDs agree); omit iff s2 <= tau (route_mask;
fallback omits nothing); CP = two-sided 95% Clopper-Pearson; AUROC = explicit Mann-Whitney, ties 1/2 (analyze_x3 mw); bootstrap = dev rows
resampled with replacement, numpy default_rng(0), 2,000 resamples, single-class resamples skipped (counted), percentile 2.5/97.5; binormal =
frozen e17_5 draws/run/summarize (hash verified) with prevalence = dev d, AUROC = dev AUROC, N_fit 500, N_cal 2,000, 1,000 simulations,
default_rng(0) (the pilot's settings). Surface form (on omitted dev questions; also on all dev): raw-string change = pilot 'extracted' strings
(before NFKD + SQuAD normalization) differ; containment-as-agreement = change and not (both parse and one normalized answer contains the other);
token-F1 = SQuAD token F1 of the normalized answers (INVALID = no tokens); extraction-beyond-normalization = extract(raw).answer !=
normalize_text(raw) (empty -> INVALID), over the R and reference outputs. Lengths: words of the normalized answer (INVALID = 0), cap hit =
32 generated tokens, helper cap = 256 tokens. Test (only if deployed): single exact binomial test at the frozen threshold; pass iff CP upper
< .05, fail iff CP lower > .05, else inconclusive. Re-splits: E5-b / X3 rule (sorted fit + cal ids, random.Random(seed).shuffle, first 500 =
fit), seeds 1..200, dev fixed; agreement = same deploy/fallback outcome. Value (only if deployed; not a replay): per dev question
1[omit] * (helper + receiver-with-message wall ms) - receiver-only wall ms (pilot wall-clock definition), mean with bootstrap interval; also
always-omit (omit every question) and the component means.
usage: e20f_stats.py [--dry-run]"""
import sys, json, glob, argparse, pathlib, datetime, math, random, statistics, collections
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e20f_common as FC
from e20f_cert import thresholds, pval, deploy, GRID, ledger_rows, route_mask
from e20_extract import changed, INVALID, normalize_text, extract          # pilot module
import numpy as np
from scipy.stats import beta
E17S = FC.ROOT / 'P2_R7_E17_20260921T183100Z/scripts'
assert FC.sha(E17S / 'e17_5.py') == 'ef1537c7289b30d7a0adfe5b9180fc9a53a35bf6cb6aba1021ebf6759dde2b6b'
assert FC.sha(E17S / 'e17_common.py') == '84367e204e17b21702715bd1e2a67d594eca14a3b02c197d422a3c7ed5cc8a60'
sys.path.insert(0, str(E17S))
from e17_5 import draws, run, summarize                                     # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true'); a = ap.parse_args()
B = FC.base(a.dry_run); RES = B / 'results'
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
assert not (B / 'STATS_E20F.json').exists(), 'STATS_E20F.json already exists'
cert, cert_sha = FC.load_cert(a.dry_run)
q, tau = cert['deployed_q'], cert['threshold']
for ph in ['fitcal', 'devtest']:
    man = sorted(glob.glob(str(RES / f'OUTPUTS_HASH_{ph}_j*.txt'))); assert man, ph
    for hp in man:
        for ln in pathlib.Path(hp).read_text().splitlines():
            if ln.startswith('#'): continue
            h, p = ln.split('  ', 1)
            if p == f'results/E20F_{ph}_rows.jsonl' and hp != man[-1]: continue
            assert FC.sha(B / p) == h, (hp, p)
assert FC.sha(RES / 'E20F_fitcal_rows.jsonl') == cert['inputs']['rows_sha256'], 'fit/cal rows changed since CERT'
ROWS = FC.jl(RES / 'E20F_fitcal_rows.jsonl') + FC.jl(RES / 'E20F_devtest_rows.jsonl')
SPL = ['fit', 'cal', 'dev']
TEST_ROWS = [r for r in ROWS if r['split'] == 'test' and r['llama'] is not None and r['helper'] is not None]
if q > 0 and len(TEST_ROWS) == FC.N_SPLIT['test']: SPL.append('test')          # a late test is reported only if complete (rule 7)


def arr(sp):
    rr = [r for r in ROWS if r['split'] == sp]
    assert len(rr) == FC.N_SPLIT[sp] and all(r['llama'] is not None and r['helper'] is not None for r in rr), f'{sp} incomplete'
    L = [r['llama'] for r in rr]
    X = dict(ids=[r['id'] for r in rr], s2=np.array([x['R']['s2'] for x in L], float), oR=[x['R']['answer'] for x in L], oT=[x['T']['answer'] for x in L],
             exR=[x['R']['extracted'] for x in L], exT=[x['T']['extracted'] for x in L], rawR=[x['R']['raw'] for x in L], rawT=[x['T']['raw'] for x in L],
             wR=[x['R']['words'] for x in L], wT=[x['T']['words'] for x in L], nR=[x['R']['n_gen_tokens'] for x in L], nT=[x['T']['n_gen_tokens'] for x in L],
             hms=np.array([r['helper']['wall_ms'] for r in rr], float), Rms=np.array([x['R']['wall_ms'] for x in L], float),
             Tms=np.array([x['T']['wall_ms'] for x in L], float), htok=[len(r['helper']['helper_generated_token_ids']) for r in rr])
    X['d'] = np.array([changed(u, v) for u, v in zip(X['oR'], X['oT'])], bool)
    X['omit'] = route_mask(X['s2'], q, tau) if q > 0 else np.zeros(len(rr), bool)
    return X


D = {sp: arr(sp) for sp in SPL}


def cp95(k, n):
    if n == 0: return (None, None)
    return (float(beta.ppf(.025, k, n - k + 1)) if k > 0 else 0.0, float(beta.ppf(.975, k + 1, n - k)) if k < n else 1.0)


def mw(d, u):   # = analyze_x3 mw (E13 item 8): explicit Mann-Whitney, ties 1/2
    d = np.asarray(d, bool); u = np.asarray(u, float); pos, neg = u[d], u[~d]
    if not len(pos) or not len(neg): return float('nan')
    return float(((pos[:, None] > neg[None, :]).sum() + .5 * (pos[:, None] == neg[None, :]).sum()) / (len(pos) * len(neg)))


def boot(n, f, B_=2000):
    rng = np.random.default_rng(0); v = []; skip = 0
    for _ in range(B_):
        x = f(rng.integers(0, n, n))
        if x is None: skip += 1; continue
        v.append(x)
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) if v else (None, None), skip


def f1(a, b):
    ta, tb = ([] if a == INVALID else a.split()), ([] if b == INVALID else b.split())
    if not ta or not tb: return float(ta == tb)
    c = sum((collections.Counter(ta) & collections.Counter(tb)).values())
    if c == 0: return 0.0
    p, r = c / len(ta), c / len(tb); return 2 * p * r / (p + r)


def cont(a, b): return a != INVALID and b != INVALID and (a in b or b in a)


def split_changes(X, m):
    ch = [(u, v) for u, v, dd, mm in zip(X['oR'], X['oT'], X['d'], m) if dd and mm]
    return dict(both_parse=sum(u != INVALID and v != INVALID for u, v in ch), only_R_INVALID=sum(u == INVALID and v != INVALID for u, v in ch),
                only_ref_INVALID=sum(u != INVALID and v == INVALID for u, v in ch))


def surface(X, m):
    idx = np.where(m)[0]
    if not len(idx): return None
    d = X['d'][idx]; ch = [i for i in idx if X['d'][i]]
    beyond = [extract(raw)['answer'] != (normalize_text(raw) or INVALID) for i in idx for raw in (X['rawR'][i], X['rawT'][i])]
    return dict(n=len(idx), change_rate_normalized=float(d.mean()), raw_string_change_rate=float(np.mean([X['exR'][i] != X['exT'][i] for i in idx])),
                containment_as_agreement_change_rate=float(np.mean([X['d'][i] and not cont(X['oR'][i], X['oT'][i]) for i in idx])),
                n_changes=len(ch), containment_share_of_changes=(float(np.mean([cont(X['oR'][i], X['oT'][i]) for i in ch])) if ch else None),
                median_token_F1_among_changes=(float(statistics.median([f1(X['oR'][i], X['oT'][i]) for i in ch])) if ch else None),
                extraction_beyond_normalization_share=float(np.mean(beyond)), n_outputs=len(beyond))


def lengths(X):
    return dict(median_words_R=statistics.median(X['wR']), median_words_ref=statistics.median(X['wT']),
                cap32_hits_R=sum(n >= 32 for n in X['nR']), cap32_hits_ref=sum(n >= 32 for n in X['nT']),
                helper_tokens_median=statistics.median(X['htok']), helper_cap256_share=float(np.mean([t >= 256 for t in X['htok']])),
                helper_cap256_n=sum(t >= 256 for t in X['htok']), n=len(X['htok']))


out = dict(utc=utc(), gold_read=False, dry_run=a.dry_run, cert_sha256=cert_sha, deployed_q=q, threshold=tau, deployed=q > 0)
V = D['dev']; n = len(V['d']); k = int(V['d'].sum())
auc = mw(V['d'], V['s2'])
ci, skip = boot(n, lambda ix: (None if V['d'][ix].all() or not V['d'][ix].any() else mw(V['d'][ix], V['s2'][ix])))
no, ko = int(V['omit'].sum()), int(V['d'][V['omit']].sum())
P, mode, mc = summarize(*run(draws(np.random.default_rng(0), 1000, 500, 2000, k / n), k / n, auc, 500, 2000))
out['dev'] = dict(n=n, disagreements=k, d=k / n, d_CP95=cp95(k, n), AUROC_s2=auc, AUROC_s2_CI95=ci, bootstrap_skipped=skip,
                  omitted=no, coverage=no / n, omitted_changes=ko, omitted_change_rate=(ko / no if no else None), omitted_change_CP95=cp95(ko, no),
                  omitted_changes_split=split_changes(V, V['omit']), invalid_R=sum(v == INVALID for v in V['oR']), invalid_ref=sum(v == INVALID for v in V['oT']),
                  binormal_P_certify_at_Ncal2000=P, binormal_modal_q=mode, binormal_median_coverage_when_certified=mc,
                  AUROC_ge_080=bool(auc >= .80))
out['surface'] = dict(omitted_dev=surface(V, V['omit']), all_dev=surface(V, np.ones(n, bool)))
out['lengths'] = dict(dev=lengths(V), cal=lengths(D['cal']))
if q > 0 and 'test' not in D:
    out['test'] = dict(status='incomplete', complete_rows=len(TEST_ROWS), needed=FC.N_SPLIT['test'])
elif q > 0:
    T = D['test']; nt, kt = int(T['omit'].sum()), int(T['d'][T['omit']].sum()); lo, hi = cp95(kt, nt); pt = pval(kt, nt)
    out['test'] = dict(n_questions=len(T['d']), omitted=nt, changed=kt, change_rate=(kt / nt if nt else None), CP95=[lo, hi], p=pt, p_le_001=pt <= .001,
                       coverage=nt / len(T['d']), verdict=('pass' if hi is not None and hi < .05 else 'fail' if lo is not None and lo > .05 else 'inconclusive'),
                       disagreements_all=int(T['d'].sum()), invalid_R=sum(v == INVALID for v in T['oR']), invalid_ref=sum(v == INVALID for v in T['oT']),
                       omitted_changes_split=split_changes(T, T['omit']), surface_omitted=surface(T, T['omit']), lengths=lengths(T))
else:
    out['test'] = None
# re-splits (E5-b / X3 rule)
pool = D['fit']['ids'] + D['cal']['ids']; up = np.concatenate([D['fit']['s2'], D['cal']['s2']]); dp = np.concatenate([D['fit']['d'], D['cal']['d']])
rs = []
for seed in range(1, 201):
    reps = sorted(pool); random.Random(seed).shuffle(reps); f = set(reps[:500]); m = np.array([i in f for i in pool], bool)
    c_s = thresholds(list(up[m])); l_s = ledger_rows(up[~m], dp[~m], c_s); q_s, _ = deploy(l_s)
    row = dict(seed=seed, q=q_s)
    if q_s > 0:
        md = route_mask(V['s2'], q_s, c_s[GRID.index(q_s)]); row.update(dev_coverage=float(md.mean()), dev_omitted=int(md.sum()), dev_changed=int(V['d'][md].sum()))
    rs.append(row)
cq = [r['q'] for r in rs if r['q'] > 0]
out['resplits'] = dict(n=200, certification_rate=len(cq) / 200, agreement_with_original=sum((r['q'] > 0) == (q > 0) for r in rs) / 200,
                       same_q_share=sum(r['q'] == q for r in rs) / 200, median_q=(float(np.median(cq)) if cq else None),
                       median_dev_coverage=(float(np.median([r['dev_coverage'] for r in rs if r['q'] > 0])) if cq else None), per_seed=rs)
sel = json.loads((FC.PILOT_DIR / 'SELECTION_E20P.json').read_text())['selected'][0]
out['prediction'] = dict(pilot_P_at_2000=sel['P']['2000'], pilot_conservative_P_at_2000=sel['conservative_P']['2000'], outcome=('deployed' if q > 0 else 'fallback'))
if q > 0:
    om = V['omit'].astype(float); v = om * (V['hms'] + V['Tms']) - V['Rms']; w = V['hms'] + V['Tms'] - V['Rms']
    out['value_estimate_ms'] = dict(note='estimate from recorded per-row wall-clock on ClusterA A100 (pilot definition), sequential execution assumed; not a replay',
                                    policy_mean=float(v.mean()), policy_CI95=boot(n, lambda ix: float(v[ix].mean()))[0],
                                    always_omit_mean=float(w.mean()), always_omit_CI95=boot(n, lambda ix: float(w[ix].mean()))[0],
                                    helper_mean=float(V['hms'].mean()), receiver_only_mean=float(V['Rms'].mean()), receiver_with_message_mean=float(V['Tms'].mean()))
else:
    out['value_estimate_ms'] = None
sp_ = B / 'STATS_E20F.json'; sp_.write_text(json.dumps(out, indent=1, allow_nan=False) + '\n')
(B / 'STATS_E20F.sha256').write_text(f'{FC.sha(sp_)}  STATS_E20F.json\nhashed_utc: {utc()}\n')
routes = [dict(split=sp, id=i, s2=float(s), route='omit' if o else 'message') for sp in SPL for i, s, o in zip(D[sp]['ids'], D[sp]['s2'], D[sp]['omit'])]
rp = B / 'ROUTES_E20F.json'; rp.write_text(json.dumps(dict(utc=utc(), deployed_q=q, threshold=tau, routes=routes), indent=0) + '\n')
(B / 'ROUTES_E20F.sha256').write_text(f'{FC.sha(rp)}  ROUTES_E20F.json\nhashed_utc: {utc()}\n')
print(json.dumps({k: v for k, v in out.items() if k != 'resplits'}, indent=1, default=str)[:6000])
print('resplits', {k: v for k, v in out['resplits'].items() if k != 'per_seed'})
print((B / 'STATS_E20F.sha256').read_text(), (B / 'ROUTES_E20F.sha256').read_text())
