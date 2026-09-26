"""E11-b: intersection of two extraction conventions (frozen parser V2 vs the official C2C evaluator's
extract_answer_from_content) over the 19 A-D settings. Frozen fit thresholds, 20 exact binomial tests."""
from e11_common import *

recs, allrev, X, CAL, FIT, DEV = exposed_ids()
assert sum(len(v) for v in X.values()) == 341, sum(len(v) for v in X.values())

APPLICABLE = [s for s in ALL26 if s[1] in ('OBQA', 'ARC')]
assert len(APPLICABLE) == 19, len(APPLICABLE)

# E5-a large-pair reference values that must reproduce exactly (results/e5a_independent_parser.csv)
E5A = {r['setting']: r for r in csvread(E5 / 'results/e5a_independent_parser.csv')}

rows, grid, mism = [], [], []
for s in APPLICABLE:
    D = load(s)
    ds, ref = D['benchmark'], s[2]
    out = dict(setting=sname(s), benchmark=ds, original_deployed_q=D['q0'], label=LABEL)
    per = {}
    for sp in ['cal', 'dev']:
        ids = D[sp]['ids']
        rawd, src = raw(s, sp, ids)
        legal = legal_for(s, ids)
        # the official extractor hard-codes A-D; one ARC development question has 5 options (A-E).
        app = np.array([PR.official_applicable(L) for L in legal], bool)
        if sp == 'cal': assert app.all(), (sname(s), sp)
        oR2, ob2 = list(D[sp]['oR']), list(D[sp]['ob'])
        oRo = [PR.label_official(t, L) if a else None for t, L, a in zip(rawd['R'], legal, app)]
        obo = [PR.label_official(t, L) if a else None for t, L, a in zip(rawd[ref], legal, app)]
        dV2 = np.array([a != b for a, b in zip(oR2, ob2)], bool)
        dOF = np.array([(a != b) if ap else False for a, b, ap in zip(oRo, obo, app)], bool)
        rowdiff = np.array([((a != b) or (c != d)) if ap else False
                            for a, b, c, d, ap in zip(oR2, oRo, ob2, obo, app)], bool)
        inX = np.array([i in X[ds] for i in ids], bool)
        per[sp] = dict(u=D[sp]['u'], dV2=dV2, dOF=dOF, oRo=oRo, obo=obo, src=src)
        out.update({f'{sp}_N': len(ids), f'{sp}_raw_source': src,
                    f'{sp}_rows_label_differs': int(rowdiff.sum()),
                    f'{sp}_rows_label_differs_inside_X': int(rowdiff[inX].sum()),
                    f'{sp}_rows_label_differs_outside_X': int(rowdiff[~inX].sum()),
                    f'{sp}_o_R_differs': int(sum(a != b for a, b in zip(oR2, oRo))),
                    f'{sp}_o_ref_differs': int(sum(a != b for a, b in zip(ob2, obo))),
                    f'{sp}_d_label_differs': int((dV2 != dOF).sum()),
                    f'{sp}_d_label_differs_inside_X': int((dV2 != dOF)[inX].sum()),
                    f'{sp}_d_label_differs_outside_X': int((dV2 != dOF)[~inX].sum()),
                    f'{sp}_in_X': int(inX.sum()),
                    f'{sp}_rows_official_not_applicable_excluded': int((~app).sum()),
                    f'{sp}_INVALID_R_official': int(sum(a == INV for a in oRo)),
                    f'{sp}_INVALID_ref_official': int(sum(a == INV for a in obo))})
    ledV2 = ledger_rows(per['cal']['u'], per['cal']['dV2'], D['cuts'])
    ledOF = ledger_rows(per['cal']['u'], per['cal']['dOF'], D['cuts'])
    qV2, aV2 = largest_accepted(ledV2)
    qOF, aOF = largest_accepted(ledOF)
    assert abs(qV2 - D['q0']) < 1e-9, (sname(s), qV2, D['q0'])
    st = 'both' if (qV2 > 0 and qOF > 0) else ('V2 only' if qV2 > 0 else ('official only' if qOF > 0 else 'neither'))
    r0 = next((r for r in ledOF if abs(r['q'] - D['q0']) < 1e-9), None)
    out.update(q_V2=qV2, q_official=qOF, deployed_under='V2 only' if st == 'V2 only' else st,
               official_n_at_orig_q=r0['n'] if r0 else '', official_k_at_orig_q=r0['k'] if r0 else '',
               official_p_at_orig_q=f"{r0['p']:.6g}" if r0 else '',
               official_accepts_orig_q=bool(r0['accepted']) if r0 else 'n/a (fallback)',
               all_accepted_q_official=';'.join(f'{x:g}' for x in aOF) or 'none')
    for nm, led in [('V2', ledV2), ('OFFICIAL', ledOF)]:
        for r in led:
            grid.append(dict(setting=sname(s), convention=nm, q=r['q'], threshold=r['threshold'], n=r['n'], k=r['k'],
                             p=f"{r['p']:.6g}", CP999=f"{r['CP']:.6g}", accepted=r['accepted'], label=LABEL))
    # reproduce E5-a exactly for the four large-pair settings (and, as a bonus, all 12 it also covered)
    e = E5A.get(sname(s))
    if e and e['official_applicable'] == 'True':
        chk = [('o_R', int(e['OFFICIAL_o_R_diff']), out['cal_o_R_differs']),
               ('o_ref', int(e['OFFICIAL_o_ref_diff']), out['cal_o_ref_differs']),
               ('d_total', int(e['OFFICIAL_d_diff_total']), out['cal_d_label_differs']),
               ('d_in_X', int(e['OFFICIAL_d_diff_in_X']), out['cal_d_label_differs_inside_X']),
               ('d_outside_X', int(e['OFFICIAL_d_diff_in_clean']), out['cal_d_label_differs_outside_X']),
               ('largest_q', float(e['OFFICIAL_largest_accepted_q']), qOF)]
        bad = [(k, a, b) for k, a, b in chk if a != b]
        out['E5a_reproduced'] = not bad
        if bad: mism.append((sname(s), bad))
    else:
        out['E5a_reproduced'] = 'n/a (not in E5-a)'
    rows.append(out)
    print(f"{sname(s):26s} q_V2={qV2:<5} q_OFF={qOF:<5} [{st}]  cal rowdiff {out['cal_rows_label_differs']} "
          f"(inX {out['cal_rows_label_differs_inside_X']}/outX {out['cal_rows_label_differs_outside_X']})  "
          f"dev rowdiff {out['dev_rows_label_differs']}  E5a={out['E5a_reproduced']}")

if mism:
    print('\nE5-a REPRODUCTION FAILED:'); [print(' ', m) for m in mism]; sys.exit(1)

csvout(RES / 'E11b_two_conventions.csv', rows)
csvout(RES / 'E11b_grid.csv', grid)

dep_v2 = [r['setting'] for r in rows if r['q_V2'] > 0]
dep_of = [r['setting'] for r in rows if r['q_official'] > 0]
inter = [r['setting'] for r in rows if r['q_V2'] > 0 and r['q_official'] > 0]
summ = [dict(quantity=k, n=len(v), settings=';'.join(v) or 'none', label=LABEL) for k, v in
        [('deployed under V2 (frozen)', dep_v2), ('deployed under official extractor', dep_of),
         ('INTERSECTION (deployed under both)', inter),
         ('V2 only (flips to fallback under official)', [x for x in dep_v2 if x not in dep_of]),
         ('official only (would certify only under official)', [x for x in dep_of if x not in dep_v2]),
         ('neither', [r['setting'] for r in rows if r['q_V2'] == 0 and r['q_official'] == 0])]]
csvout(RES / 'E11b_intersection.csv', summ)
print()
for r in summ: print(f"{r['quantity']:48s} n={r['n']:2d}  {r['settings']}")

# q changes among the settings deployed under V2
print('\nq under V2 -> q under official, for V2-deployed settings:')
for r in rows:
    if r['q_V2'] > 0: print(f"  {r['setting']:26s} {r['q_V2']} -> {r['q_official']}")
