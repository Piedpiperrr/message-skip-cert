"""E5-a: parser exposure. Rebuild X, redo the 20 tests on C \\ X with the FROZEN fit thresholds for all 21 settings."""
from r2_common import *
import numpy as np
import data_r1

recs, allrev, X, CAL, FIT, DEV = exposed_ids()

# ---------------- (a) X as a table
rows = []
for (ds, i), e in sorted(recs.items()):
    rows.append(dict(benchmark={'obqa': 'OBQA', 'arc': 'ARC'}[ds], question_id=i, split='calibration',
                     reviewed_pairs=';'.join(sorted(e['pairs'])), reviewed_actions=';'.join(sorted(e['actions'])),
                     n_review_records=e['reviews'], diagnostic_reasons=';'.join(sorted(e['reasons'])),
                     selection_rule='saved-vs-diagnostic parser disagreement or ambiguous diagnostic parse (content-selected, NOT random)',
                     source='P2_SCORE_SENSITIVITY_20260912T055929Z/case_review.jsonl', label=LABEL))
csvout(RES / 'e5a_exposed_ids.csv', rows)
print('X distinct calibration questions:', len(rows), {k: len(v) for k, v in X.items()})

# where else reviewed questions landed
extra = []
for ds in ['obqa', 'arc']:
    tot = sum(1 for (d, i) in allrev if d == ds)
    extra.append(dict(benchmark=ds, reviewed_questions_total=tot,
                      in_calibration=sum(1 for (d, i) in allrev if d == ds and i in CAL[ds]),
                      in_fit=sum(1 for (d, i) in allrev if d == ds and i in FIT[ds]),
                      in_development=sum(1 for (d, i) in allrev if d == ds and i in DEV[ds]), label=LABEL))
csvout(RES / 'e5a_review_split_membership.csv', extra)
print(extra)

# ---------------- data for the 21 settings
main = load_main()
x2 = load_x2()
x1 = load_x1()


def xcuts(csvpath, setting):
    rr = [r for r in csvread(csvpath) if r['setting'] == setting]
    assert len(rr) == 20, (csvpath, setting, len(rr))
    return [r['threshold'] for r in rr]


def get(s):
    """-> ds, cal ids, u (np), d (np), frozen cuts, original deployed q"""
    pair, task, ref = s
    if pair in ('small', 'medium', 'large'):
        D = main[pair, task]
        return (BENCH[task], D['cal']['ids'], D['cal']['scores']['ProbeMax'],
                data_r1.disagreement(D['cal'], ref), D['stored_thresholds'], EXPECTED_Q[s])
    if pair == 'X2-OLMo':
        ds = BENCH[task]; D = x2[ds]
        d = np.array([a != b for a, b in zip(D['cal']['oR'], D['cal']['oT'])], bool)
        cuts = xcuts(XFAM / 'results/analysis/certification_ledger_60.csv', f'{ds}/Text')
        return ds, D['cal']['ids'], np.array(D['cal']['u']), d, cuts, 0.0
    ds = BENCH[task]; D = x1[ds]
    o = D['cal']['oT'] if ref == 'Text' else D['cal']['oC']
    d = np.array([a != b for a, b in zip(D['cal']['oR'], o)], bool)
    cuts = xcuts(X1 / 'results/analysis/certification_ledger_80.csv', f'{ds}/{ref}')
    return ds, D['cal']['ids'], np.array(D['cal']['u']), d, cuts, 0.0


summary, fullgrid, disag = [], [], []
for s in ALL21:
    ds, ids, u, d, cuts, q0 = get(s)
    ex = np.array([i in X[ds] for i in ids], bool)
    keep = ~ex
    clean = ledger_rows(u, d, cuts, keep)
    orig = ledger_rows(u, d, cuts)                      # frozen thresholds, full C (reproduction)
    acc = [r['q'] for r in clean if r['accepted']]
    largest = acc[-1] if acc else 0.0
    row0 = next((r for r in clean if abs(r['q'] - q0) < 1e-9), None)
    summary.append(dict(setting=sname(s), benchmark=ds, N_cal=len(ids), exposed_in_cal=int(ex.sum()), N_clean=int(keep.sum()),
                        orig_q=q0,
                        clean_n=row0['n'] if row0 else '', clean_k=row0['k'] if row0 else '',
                        clean_p=f"{row0['p']:.6g}" if row0 else '', clean_CP999=f"{row0['CP']:.6g}" if row0 else '',
                        orig_q_accepted_on_clean=bool(row0['accepted']) if row0 else 'n/a (fallback: no deployed q)',
                        largest_clean_accepted_q=largest,
                        full_C_n_at_orig_q=next((r['n'] for r in orig if abs(r['q'] - q0) < 1e-9), ''),
                        full_C_k_at_orig_q=next((r['k'] for r in orig if abs(r['q'] - q0) < 1e-9), ''),
                        full_C_p_at_orig_q=f"{next((r['p'] for r in orig if abs(r['q'] - q0) < 1e-9), float('nan')):.6g}",
                        label=LABEL))
    for r, ro in zip(clean, orig):
        fullgrid.append(dict(setting=sname(s), q=r['q'], threshold=r['threshold'], N_clean=r['N'], n=r['n'], k=r['k'],
                             p=f"{r['p']:.6g}", CP999=f"{r['CP']:.6g}", accepted=r['accepted'],
                             orig_n=ro['n'], orig_k=ro['k'], orig_p=f"{ro['p']:.6g}", orig_accepted=ro['accepted'], label=LABEL))
    nx, nc = int(ex.sum()), int(keep.sum())
    disag.append(dict(setting=sname(s), benchmark=ds, n_X=nx, dis_X=int(d[ex].sum()),
                      rate_X=f"{d[ex].mean():.4f}" if nx else '', n_clean=nc, dis_clean=int(d[keep].sum()),
                      rate_clean=f"{d[keep].mean():.4f}" if nc else '',
                      rate_full=f"{d.mean():.4f}", label=LABEL))

csvout(RES / 'e5a_clean_tests.csv', summary)
csvout(RES / 'e5a_clean_ledger_all_q.csv', fullgrid)
csvout(RES / 'e5a_disagreement_X_vs_clean.csv', disag)
for r in summary:
    print(f"{r['setting']:26s} N={r['N_cal']:5d} |C&X|={r['exposed_in_cal']:4d} q0={r['orig_q']:<5} "
          f"n/k/p={r['clean_n']}/{r['clean_k']}/{r['clean_p']} acc={r['orig_q_accepted_on_clean']} largest={r['largest_clean_accepted_q']}")
print()
for r in disag:
    print(f"{r['setting']:26s} X {r['dis_X']}/{r['n_X']}={r['rate_X']}   clean {r['dis_clean']}/{r['n_clean']}={r['rate_clean']}  full={r['rate_full']}")
