"""Task 3 - E6 development and calibration extras.

(a) Development, at the certified q = .75: policy vs fixed Text+fact correct answers, delta accuracy in
    percentage points with a 2,000-resample seed-0 paired bootstrap, and the lost/kept/gained/net/other/
    unused columns of the paper's reference-correction table (tab_omit_keep.tex), whose definitions are
    taken verbatim from P2_FOCUSED_REVISION_ROUND1B.../audit_v2/scripts/audit_v2.py (block C).
(b) Calibration: relabel the Text+fact calibration outputs with the pre-V2 D1 parser (the E5-a (c) check),
    then redo the 20 frozen tests; and redo them after removing X, the 208 reviewed OBQA calibration
    questions (the E5-a clean-test procedure).
"""
import sys
sys.dont_write_bytecode = True
from common_r2a import *      # noqa: F401,F403
import numpy as np

sys.path.insert(0, str(CPU / 'scripts'))
sys.path.insert(0, str(R1CPU / 'src'))
from common_r1 import tv, pval, cp999, GRID, V2, BND                    # noqa: E402
from r2_common import exposed_ids, ledger_rows                          # noqa: E402
import parsers_r2 as PR                                                 # noqa: E402
import rawio                                                            # noqa: E402

STOP = []


def stop(c, m):
    if not c:
        STOP.append(m)


# ---------------------------------------------------------------- sources (same as e6_analyze.py)
cal_ids = read(BND / 'splits/obqa_cal_representatives.json')
dev_ids = read(BND / 'splits/obqa_dev_representatives.json')
TH = read(BND / 'thresholds/large_obqa.json')
cuts = TH['thresholds']
stop(TH['q'] == GRID and TH['N_fit'] == 2100, 'frozen threshold grid changed')

lab = {}
for name in ['full_train', 'full_development']:
    for x in jl(V2 / f'labels/{name}_P2_SCORING_V2.jsonl'):
        if x['pair'] == 'large' and x['dataset'] == 'obqa':
            lab[x['id']] = x
probe = {r['id']: r for r in jl(ROOT / 'P2_ZERO_GOLD_CONTROLS_20260914T065145Z/records/probe_records.jsonl')}
e6 = {}
for f in sorted((GPU / 'e6/main').glob('e6_shard*.jsonl')):
    for r in jl(f):
        e6[r['id']] = r
stop(len(e6) == 2108, 'E6 main rows != 2108')
E6RES = read(GPU / 'e6/analysis/E6_RESULTS.json')
QSTAR, TSTAR = E6RES['certified_q'], E6RES['certified_threshold']
stop(QSTAR == 0.75 and not E6RES['fallback'], 'E6 certified q is not .75')


def o(i, s): return lab[i][f'o_{s}'] if lab[i][f'valid_{s}'] else INV


def mask(u, q, t):
    if q == 0: return np.zeros(len(u), bool)
    if q == 1: return np.ones(len(u), bool)
    return u <= tv(t)


# ================================================================ (a) development
ids = dev_ids
u = np.array([probe[i]['ProbeMax'] for i in ids], float)
oR = np.array([o(i, 'R') for i in ids], dtype=object)
oT = np.array([o(i, 'T') for i in ids], dtype=object)
oC = np.array([o(i, 'C') for i in ids], dtype=object)
oF = np.array([e6[i]['answer'] for i in ids], dtype=object)
g = np.array([lab[i]['gold'] for i in ids], dtype=object)
om = mask(u, QSTAR, TSTAR)
stop(int(om.sum()) == E6RES['dev']['at_deployed_q']['omitted'], 'dev omitted count differs from E6_RESULTS.json')

yR, yF, yT, yC = (oR == g), (oF == g), (oT == g), (oC == g)
y_pol = np.where(om, yR, yF)
pol_c, ref_c = int(y_pol.sum()), int(yF.sum())
stop(pol_c - ref_c == int((om & yR & ~yF).sum()) - int((om & ~yR & yF).sum()),
     'development identity policy-ref = gained - lost does not hold')

didx = bidx(len(ids))
dacc = (y_pol.astype(float) - yF.astype(float)) * 100.0
lo, hi = ci(dacc[didx].mean(axis=1))

dev_rows = []
for other_name, yO in [('C2C', yC), ('Text', yT)]:
    dev_rows.append(dict(
        setting='large/OBQA/Text+fact', N=len(ids), q=QSTAR, other_communication_action=other_name,
        omitted=int(om.sum()), omitted_over_N=f'{int(om.sum())}/{len(ids)}', kept_questions=int((~om).sum()),
        policy_correct=pol_c, fixed_TextFact_correct=ref_c, R_correct=int(yR.sum()),
        Text_correct=int(yT.sum()), C2C_correct=int(yC.sum()),
        delta_accuracy_pp=float(dacc.mean()), delta_CI_low_pp=lo, delta_CI_high_pp=hi,
        bootstrap='2000 paired resamples, numpy default_rng(0), percentile 2.5/97.5',
        ref_corrections_total=int((~yR & yF).sum()),
        lost=int((om & ~yR & yF).sum()), kept=int((~om & ~yR & yF).sum()),
        gained=int((om & yR & ~yF).sum()), net=pol_c - ref_c,
        other=int((om & ~yR & ~yF & yO).sum()),
        unused_on_omit=int((om & ~yR & (yF | yO)).sum()),
        unused_on_keep=int((~om & ~yF & (yR | yO)).sum()),
        oracle3_correct=int((yR | yF | yO).sum()),
        unused_3action_opportunity=int((yR | yF | yO).sum()) - pol_c,
        changed_on_omitted=int((om & (oR != oF)).sum()),
        definitions='columns exactly as audit_v2.py block C / app_complementarity.tex', label=LABEL))
wcsv('E6_dev_reference_corrections.csv', dev_rows)

# ================================================================ (b) calibration
ids = cal_ids
uc = np.array([probe[i]['ProbeMax'] for i in ids], float)
raw, rawsrc = rawio.raw_cal(('large', 'OBQA', 'Text'), ids)
legal = [rawio.legal_labels('obqa', i) for i in ids]
oR_v2 = [o(i, 'R') for i in ids]
oF_v2 = [e6[i]['answer'] for i in ids]
rawF = [e6[i]['raw_answer'] for i in ids]
stop(all(PR.label_v2(t, L) == a for t, L, a in zip(raw['R'], legal, oR_v2)),
     'V2 re-parse of the saved R calibration outputs does not reproduce the frozen labels')
stop(all(PR.label_v2(t, L) == a for t, L, a in zip(rawF, legal, oF_v2)),
     'V2 re-parse of the E6 Text+fact outputs does not reproduce the recorded labels')

oR_d1 = [PR.label_d1(t, L) for t, L in zip(raw['R'], legal)]
oF_d1 = [PR.label_d1(t, L) for t, L in zip(rawF, legal)]
d_v2 = np.array([a != b for a, b in zip(oR_v2, oF_v2)], bool)
stop(int(d_v2.sum()) == E6RES['cal']['disagreement_R_vs_TextFact']['count'],
     'recomputed calibration disagreement differs from E6_RESULTS.json')

recs_x, allrev, X, CAL, FIT, DEV = exposed_ids()
ex = np.array([i in X['obqa'] for i in ids], bool)
stop(int(ex.sum()) == 208, f"|C n X| for OBQA is {int(ex.sum())}, expected 208")

d1_rows = []
for name, dvec in [('D1 both sides (E5-a (c) rule)', np.array([a != b for a, b in zip(oR_d1, oF_d1)], bool)),
                   ('D1 on Text+fact only, V2 on R', np.array([a != b for a, b in zip(oR_v2, oF_d1)], bool))]:
    led = ledger_rows(uc, dvec, cuts)
    r0 = next(r for r in led if abs(r['q'] - QSTAR) < 1e-9)
    acc = [r['q'] for r in led if r['accepted']]
    d1_rows.append(dict(variant=name, N_cal=len(ids), raw_source=rawsrc,
                        o_R_D1_vs_V2_differences=int(sum(a != b for a, b in zip(oR_d1, oR_v2))),
                        o_TextFact_D1_vs_V2_differences=int(sum(a != b for a, b in zip(oF_d1, oF_v2))),
                        d_label_differences_vs_V2=int((dvec != d_v2).sum()),
                        d_diff_in_X=int((dvec != d_v2)[ex].sum()), d_diff_in_clean=int((dvec != d_v2)[~ex].sum()),
                        disagreement_count=int(dvec.sum()),
                        n_at_q075=r0['n'], k_at_q075=r0['k'], p_at_q075=f"{r0['p']:.6g}",
                        CP999_at_q075=f"{r0['CP']:.6g}", q075_accepted=bool(r0['accepted']),
                        largest_accepted_q=acc[-1] if acc else 0.0,
                        parser_D1=PR.SOURCES['D1'], parser_D1_sha256=PR.HASHES['D1'], label=LABEL))
wcsv('E6_cal_D1_relabel.csv', d1_rows)

# ---- remove X, as in E5-a
keepm = ~ex
clean = ledger_rows(uc, d_v2, cuts, keepm)
orig = ledger_rows(uc, d_v2, cuts)
r0 = next(r for r in clean if abs(r['q'] - QSTAR) < 1e-9)
o0 = next(r for r in orig if abs(r['q'] - QSTAR) < 1e-9)
accq = [r['q'] for r in clean if r['accepted']]
wcsv('E6_cal_without_X.csv', [dict(
    setting='large/OBQA/Text+fact', N_cal=len(ids), exposed_in_cal=int(ex.sum()), N_clean=int(keepm.sum()),
    orig_q=QSTAR, clean_n=r0['n'], clean_k=r0['k'], clean_p=f"{r0['p']:.6g}", clean_CP999=f"{r0['CP']:.6g}",
    q075_accepted_on_clean=bool(r0['accepted']), largest_clean_accepted_q=accq[-1] if accq else 0.0,
    full_C_n_at_q075=o0['n'], full_C_k_at_q075=o0['k'], full_C_p_at_q075=f"{o0['p']:.6g}",
    full_C_q075_accepted=bool(o0['accepted']),
    dis_X=int(d_v2[ex].sum()), rate_X=f"{d_v2[ex].mean():.4f}",
    dis_clean=int(d_v2[keepm].sum()), rate_clean=f"{d_v2[keepm].mean():.4f}", rate_full=f"{d_v2.mean():.4f}",
    X_source=str(ROOT / 'P2_SCORE_SENSITIVITY_20260912T055929Z/case_review.jsonl'),
    procedure='E5-a clean test: frozen fit thresholds, 20 tests, p = binom.cdf(k, n, .05) <= .001', label=LABEL)])
wcsv('E6_cal_without_X_ledger.csv', [dict(
    q=r['q'], threshold=r['threshold'], N_clean=r['N'], n=r['n'], k=r['k'], p=f"{r['p']:.6g}",
    CP999=f"{r['CP']:.6g}", accepted=r['accepted'], full_C_n=ro['n'], full_C_k=ro['k'],
    full_C_p=f"{ro['p']:.6g}", full_C_accepted=ro['accepted'], label=LABEL) for r, ro in zip(clean, orig)])

json.dump(dict(stop_conditions=STOP), open(RES / 'E6_EXTRAS_CHECKS.json', 'w'), indent=2)
print('STOP CONDITIONS:', STOP if STOP else 'none')
r = dev_rows[0]
print(f"dev: policy {r['policy_correct']} / fixed TF {r['fixed_TextFact_correct']}  "
      f"delta {r['delta_accuracy_pp']:+.3f} pp [{r['delta_CI_low_pp']:.3f}, {r['delta_CI_high_pp']:.3f}]  "
      f"lost {r['lost']}/{r['ref_corrections_total']} kept {r['kept']}/{r['ref_corrections_total']} "
      f"gained {r['gained']} net {r['net']:+d} other {r['other']} unused {r['unused_on_omit']}/{r['unused_on_keep']}")
print(f"dev (other = Text): other {dev_rows[1]['other']} unused {dev_rows[1]['unused_on_omit']}/{dev_rows[1]['unused_on_keep']}")
for x in d1_rows:
    print(f"D1 [{x['variant']}]: d-label diffs {x['d_label_differences_vs_V2']}  "
          f"n/k/p at .75 = {x['n_at_q075']}/{x['k_at_q075']}/{x['p_at_q075']}  "
          f"accepted={x['q075_accepted']}  largest={x['largest_accepted_q']}")
print(f"without X: N_clean {int(keepm.sum())}  n/k/p at .75 = {r0['n']}/{r0['k']}/{r0['p']:.6g}  "
      f"accepted={r0['accepted']}  largest accepted q={accq[-1] if accq else 0.0}")
