"""E20P Steps 4-5 (login node; gold is never read): per-setting statistics, frozen E17-5 binormal predictions -> PILOT_STATS.csv /
results/PILOT_STATS.json; eligibility + selection -> SELECTION_E20P.json, hashed immediately in SELECTION_E20P.sha256 (SHA-256 + UTC).

Operationalization (fixed before any output): setting = dataset x receiver; unit = pilot question; change d_i = normalized o_R != normalized
o_b (receiver-only vs receiver-with-message; two INVALIDs agree); scores = receiver-only s1/s2/s3; rows that are missing or have a runtime error
are excluded and counted. AUROC = Mann-Whitney with ties 1/2 (average ranks); bootstrap: rows resampled with replacement, numpy default_rng(0) fresh per
setting, 2,000 resamples, the same resample indices for s1/s2/s3, resamples with a single class skipped (counted), percentile 2.5/97.5.
Chosen score = highest pilot AUROC (ties: s1, then s2); N/A AUROC if d = 0 or d = 1 (then no prediction; the setting cannot be ranked).
"Lowest q share": the paper's rule with the pilot as its own fit split: threshold = order statistic ceil(j N / 20) of the chosen score with
j = 20 q (common_r1.thresholds), questions with score <= threshold (ties kept); change rate k/n with the two-sided 95% Clopper-Pearson upper
bound. E17-5(a): pi = 1 - d, C = (1 - pi)(1 - alpha)/(pi alpha); max over the 20 pilot-quantile candidates (q = 1 = all) of TPR/FPR with
TPR = omitted agreeing / all agreeing, FPR = omitted changes / all changes. Binormal: e17_5.draws/run/summarize/bisect (hash verified), inputs
only: prevalence = d, AUROC = chosen-score AUROC, N_fit = 500, N_cal in {1000, 2000, 3000}, 1,000 simulations, default_rng(0); conservative
P = same with (CP upper of d, bootstrap lower bound of AUROC); AUROC needed for P = .5 = e17_5.bisect(d, 500, N_cal) (B = 1,000, seed 0).
The frozen code returns median coverage when certified, not expected coverage: expected coverage = N/A (median coverage reported separately).
usage: e20_analyze.py [--dry-run]"""
import sys, json, csv, math, argparse, pathlib, statistics
sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from e20_exec_common import *
from e20_extract import INVALID, changed
import numpy as np
from scipy.stats import beta, rankdata

ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true'); a = ap.parse_args()
RES = (STAGE / 'notes/dryrun/results') if a.dry_run else (STAGE / 'results')
TOP = RES if a.dry_run else STAGE
E17S = ROOT / 'P2_R7_E17_20260921T183100Z/scripts'
E17_5_SHA = 'ef1537c7289b30d7a0adfe5b9180fc9a53a35bf6cb6aba1021ebf6759dde2b6b'           # = E16 E17_5_on_E16_5.json
E17_COMMON_SHA = '84367e204e17b21702715bd1e2a67d594eca14a3b02c197d422a3c7ed5cc8a60'
assert sha(E17S / 'e17_5.py') == E17_5_SHA and sha(E17S / 'e17_common.py') == E17_COMMON_SHA
sys.path.insert(0, str(E17S))
from e17_5 import draws, run, summarize, bisect, A_, DELTA   # noqa: E402
assert A_ == .05 and DELTA == .001
R1SRC = ROOT / 'P2_R1_CPU_20260919T045556Z/src'
sys.path.insert(0, str(R1SRC))
from common_r1 import thresholds, GRID   # noqa: E402
assert len(GRID) == 20
NFIT, NCALS, BSIM, BBOOT, ELIG = 500, (1000, 2000, 3000), 1000, 2000, .04
SC = ['s1', 's2', 's3']


def cp95(k, n):
    if n == 0: return (None, None)
    return (0.0 if k == 0 else float(beta.ppf(.025, k, n - k + 1)), 1.0 if k == n else float(beta.ppf(.975, k + 1, n - k)))


def auroc(d, s):
    d = np.asarray(d, bool); n1 = int(d.sum()); n0 = len(d) - n1
    if n1 == 0 or n0 == 0: return None
    r = rankdata(np.asarray(s, float))
    return float((r[d].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def pc(p, auc, nc):
    return summarize(*run(draws(np.random.default_rng(0), BSIM, NFIT, nc, p), p, auc, NFIT, nc))


# ------------------------------------------------------------------ outputs: verify per-job hashes, write OUTPUTS_HASH.txt
if not a.dry_run:
    lines = []
    for j in ['A', 'B']:
        hp = RES / f'OUTPUTS_HASH_job{j}.txt'
        for ln in hp.read_text().splitlines():
            if ln.startswith('#'): continue
            h, p = ln.split('  ', 1); assert sha(STAGE / p) == h, p
        lines.append(f'{sha(hp)}  {hp.relative_to(STAGE)}')
    oh = STAGE / 'OUTPUTS_HASH.txt'
    if not oh.exists():
        oh.write_text('\n'.join(lines) + f'\n# utc={utc()} (per-job manifests verified file by file before this line was written)\n')

rows = {}
for j in ['A', 'B']:
    p = RES / f'E20P_job{j}_rows.jsonl'
    if p.exists():
        for r in jl(p): rows.setdefault(r['dataset'], []).append(r)

stats, ex = [], {}
for ds in DATASETS:
    if ds not in rows: continue
    for rc in RECEIVERS:
        R = [x for x in rows[ds] if x[rc] is not None and x[rc].get('runtime_error') is None and x['helper'] is not None
             and x['helper'].get('runtime_error') is None]
        nerr = len(rows[ds]) - len(R)
        if not R: print('no usable rows', ds, rc, flush=True); continue
        oR = [x[rc]['R']['answer'] for x in R]; ob = [x[rc]['T']['answer'] for x in R]
        d = np.array([changed(u, v) for u, v in zip(oR, ob)], bool); n = len(d); k = int(d.sum())
        S = {s: np.array([x[rc]['R'][s] for x in R], float) for s in SC}
        st = dict(dataset=NAME[ds], ds=ds, receiver=rc, n=n, n_excluded_missing_or_runtime_error=nerr, k=k, d=k / n if n else None)
        st['d_lo'], st['d_hi'] = cp95(k, n)
        au = {s: auroc(d, S[s]) for s in SC}
        rng = np.random.default_rng(0); bo = {s: [] for s in SC}; skip = 0
        if au['s1'] is not None:
            for b in range(BBOOT):
                ix = rng.integers(0, n, n); db = d[ix]
                if db.all() or not db.any(): skip += 1; continue
                for s in SC: bo[s].append(auroc(db, S[s][ix]))
        for s in SC:
            st[f'auroc_{s}'] = au[s]
            st[f'auroc_{s}_lo'] = float(np.percentile(bo[s], 2.5)) if bo[s] else None
            st[f'auroc_{s}_hi'] = float(np.percentile(bo[s], 97.5)) if bo[s] else None
        st['boot_skipped'] = skip
        ch = 's1'
        if au['s1'] is not None:
            for s in ['s2', 's3']:
                if au[s] > au[ch]: ch = s
        st['chosen'] = ch; st['auroc_chosen'] = au[ch]; st['auroc_chosen_lo'] = st[f'auroc_{ch}_lo']; st['auroc_chosen_hi'] = st[f'auroc_{ch}_hi']
        st['invalid_R'] = float(np.mean([v == INVALID for v in oR])); st['invalid_T'] = float(np.mean([v == INVALID for v in ob]))
        st['share_s1_eq0'] = float((S['s1'] == 0).mean()); st['share_s2_eq0'] = float((S['s2'] == 0).mean())
        st['share_s1_pos_ne_first'] = float(np.mean([x[rc]['R']['s1_pos'] != 0 for x in R]))
        st['n_s1_missing'] = sum(x[rc]['R']['s1_missing'] for x in R); st['n_span_missing'] = sum(x[rc]['R']['span_missing'] for x in R)
        st['median_words_R'] = statistics.median(x[rc]['R']['words'] for x in R)
        st['median_words_T'] = statistics.median(x[rc]['T']['words'] for x in R)
        st['R_hit_32_tokens'] = sum(x[rc]['R']['n_gen_tokens'] >= RECEIVER_MAX_NEW for x in R)
        st['T_hit_32_tokens'] = sum(x[rc]['T']['n_gen_tokens'] >= RECEIVER_MAX_NEW for x in R)
        st['argmax_ne_chosen_positions'] = sum(x[rc]['R']['argmax_ne_chosen'] + x[rc]['T']['argmax_ne_chosen'] for x in R)
        st['helper_tokens_median'] = statistics.median(len(x['helper']['helper_generated_token_ids']) for x in R)
        st['helper_hit_256_tokens'] = sum(len(x['helper']['helper_generated_token_ids']) >= HELPER_MAX_NEW for x in R)
        s = S[ch]; cuts = thresholds(list(s))
        for q in [.10, .25, .50]:
            m = s <= cuts[round(q * 20) - 1]; nq, kq = int(m.sum()), int(d[m].sum())
            tag = f'low{round(q * 100)}'
            st[f'{tag}_n'], st[f'{tag}_k'] = nq, kq
            st[f'{tag}_rate'] = kq / nq if nq else None; st[f'{tag}_cp_up'] = cp95(kq, nq)[1]
        st['eligible'] = st['low25_rate'] is not None and st['low25_rate'] <= ELIG
        A, Dn = n - k, k
        if A and Dn:
            pi = 1 - st['d']; C = (1 - pi) * (1 - A_) / (pi * A_); best = -1.0
            for q, t in zip(GRID, cuts):
                m = np.ones(n, bool) if q == 1 else s <= t; nm, km = int(m.sum()), int(d[m].sum())
                if nm == 0: continue
                best = max(best, float('inf') if km == 0 else ((nm - km) / A) / (km / Dn))
            st.update(e17_5a_pi=pi, e17_5a_C=C, e17_5a_max_TPR_over_FPR='inf' if math.isinf(best) else best, e17_5a_max_ge_C=bool(best >= C))
        else:
            st.update(e17_5a_pi=None, e17_5a_C=None, e17_5a_max_TPR_over_FPR=None, e17_5a_max_ge_C=None)
        chg = [(u, v) for u, v, dd in zip(oR, ob, d) if dd]
        bv = [(u, v) for u, v in chg if u != INVALID and v != INVALID]
        st['changes_both_parse'] = len(bv); st['changes_one_invalid'] = len(chg) - len(bv)
        st['containment_count'] = sum((u in v) or (v in u) for u, v in bv)
        st['containment_share_of_changes'] = st['containment_count'] / len(chg) if chg else None
        if st['auroc_chosen'] is not None:
            for nc in NCALS:
                P, mode, mc = pc(st['d'], st['auroc_chosen'], nc)
                st[f'P_{nc}'], st[f'modal_q_{nc}'], st[f'median_cov_when_cert_{nc}'] = P, mode, mc
                st[f'expected_coverage_{nc}'] = 'N/A'
                st[f'Pcons_{nc}'] = pc(st['d_hi'], st['auroc_chosen_lo'], nc)[0]
                txt, val, _ = bisect(st['d'], NFIT, nc)
                st[f'auroc_needed_{nc}'] = txt; st[f'auroc_needed_{nc}_value'] = val
        else:
            for nc in NCALS:
                for key in ['P', 'modal_q', 'median_cov_when_cert', 'Pcons', 'auroc_needed']: st[f'{key}_{nc}'] = None
                st[f'auroc_needed_{nc}_value'] = None; st[f'expected_coverage_{nc}'] = 'N/A'
        stats.append(st)
        ex[(ds, rc)] = dict(changes=[(x['id'], x[rc]['R']['extracted'], x[rc]['T']['extracted']) for x, dd in zip(R, d) if dd][:3],
                            agreements=[(x['id'], x[rc]['R']['extracted'], x[rc]['T']['extracted']) for x, dd in zip(R, d) if not dd][:3])
        print(json.dumps({k2: (round(v, 4) if isinstance(v, float) else v) for k2, v in st.items()}), flush=True)

RES.mkdir(parents=True, exist_ok=True)
with open(TOP / 'PILOT_STATS.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k2 for r in stats for k2 in r))); w.writeheader(); w.writerows(stats)
save(RES / 'PILOT_STATS.json', dict(utc=utc(), gold_read=False, analysis_sha256=sha(pathlib.Path(__file__)), e17_5_sha256=E17_5_SHA,
                                    settings=stats, examples={f'{k[0]}|{k[1]}': v for k, v in ex.items()}))

# ------------------------------------------------------------------ Step 5: eligibility and selection (label-free)
RO = {'qwen3': 0, 'llama': 1}
rankable = [s for s in stats if s['eligible'] and s.get('P_3000') is not None]
ranked = sorted(rankable, key=lambda s: (-s['P_3000'], -s['P_1000'], -(s['auroc_chosen_lo'] if s['auroc_chosen_lo'] is not None else -1),
                                         RO[s['receiver']]))
qual = [s for s in ranked if s['P_3000'] >= .5]
sel = []
if qual:
    sel = [qual[0]]
    diff = [s for s in qual[1:] if s['ds'] != qual[0]['ds']]
    if diff: sel.append(diff[0])
    elif len(qual) > 1: sel.append(qual[1])


def ncal(s):
    for nc in NCALS:
        if s[f'P_{nc}'] >= .8: return nc
    return 3000


def brief(s):
    return dict(setting=f'{s["dataset"]}|{s["receiver"]}', dataset=s['dataset'], receiver=s['receiver'], score=s['chosen'], d=s['d'],
                d_CI=[s['d_lo'], s['d_hi']], AUROC=s['auroc_chosen'], AUROC_CI=[s['auroc_chosen_lo'], s['auroc_chosen_hi']],
                low25_rate=s['low25_rate'], P={nc: s[f'P_{nc}'] for nc in NCALS}, conservative_P={nc: s[f'Pcons_{nc}'] for nc in NCALS})


selection = dict(
    utc=utc(), gold_read=False, dry_run=a.dry_run,
    rule='eligible iff change rate among the 25% lowest-score pilot questions <= 4% (point estimate); rank eligible settings by P@3000, then '
         'P@1000, then the AUROC lower bound, then Qwen3 before Llama; take at most two settings with P@3000 >= .5: the top one, then the best '
         'one on a different dataset if its P@3000 >= .5, otherwise the next one with P@3000 >= .5; N_cal = smallest of {1000, 2000, 3000} '
         'with P >= .8 (else 3000).',
    selected=[dict(**brief(s), N_cal=ncal(s), P_at_N_cal=s[f'P_{ncal(s)}'], conservative_P_at_N_cal=s[f'Pcons_{ncal(s)}']) for s in sel],
    none_selected=not sel,
    ranking=[brief(s) for s in ranked],
    eligibility_failures=[dict(setting=f'{s["dataset"]}|{s["receiver"]}', low25_rate=s['low25_rate'], low25_n=s['low25_n'], low25_k=s['low25_k'])
                          for s in stats if not s['eligible']],
    not_rankable_no_prediction=[f'{s["dataset"]}|{s["receiver"]}' for s in stats if s['eligible'] and s.get('P_3000') is None],
    inputs={p.name: sha(p) for p in sorted(RES.glob('E20P_job*_rows.jsonl'))}, pilot_stats_sha256=sha(RES / 'PILOT_STATS.json'),
    analysis_sha256=sha(pathlib.Path(__file__)))
sp = TOP / 'SELECTION_E20P.json'
sp.write_text(json.dumps(selection, indent=2, allow_nan=False) + '\n')
(TOP / 'SELECTION_E20P.sha256').write_text(f'{sha(sp)}  SELECTION_E20P.json\nhashed_utc: {utc()}\n')
print('SELECTION', json.dumps(selection['selected']), flush=True)
print((TOP / 'SELECTION_E20P.sha256').read_text(), flush=True)
