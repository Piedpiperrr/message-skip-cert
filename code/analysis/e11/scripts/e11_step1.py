"""E11 Step 1: reproduction check. Recompute cal n/k/p at the deployed candidate and the dev
disagreement rate + AUROC for all 26 settings, and match them against the stored ledgers and the
paper's Tables 2 and 6. Any mismatch -> FAIL."""
from e11_common import *

# Paper Table 6 (tab_dev_full.tex, P2_STRENGTHEN_20260918T205058Z/v2/paper) for the 14 main settings,
# plus E8 SUMMARY.md section 1, the X1/X2 cross-family tables, and E6_RESULTS.md.
PAPER = {
    ('small', 'OBQA', 'Text'): (339, 742, .641, 0.0), ('small', 'OBQA', 'C2C'): (350, 742, .700, 0.0),
    ('small', 'ARC', 'Text'): (145, 299, .634, 0.0), ('small', 'ARC', 'C2C'): (160, 299, .641, 0.0),
    ('medium', 'OBQA', 'Text'): (174, 742, .787, 0.0), ('medium', 'OBQA', 'C2C'): (131, 742, .840, .55),
    ('medium', 'ARC', 'Text'): (52, 299, .742, 0.0), ('medium', 'ARC', 'C2C'): (48, 299, .910, .60),
    ('large', 'OBQA', 'Text'): (72, 742, .873, .80), ('large', 'OBQA', 'C2C'): (60, 742, .883, .80),
    ('large', 'ARC', 'Text'): (15, 299, .952, .95), ('large', 'ARC', 'C2C'): (12, 299, .909, .90),
    ('large', 'MMLU-Pro', 'Text'): (561, 2641, .821, .40), ('large', 'MMLU-Pro', 'C2C'): (756, 2641, .846, .40),
    ('small', 'MMLU-Pro', 'Text'): (1235, 2641, .6438, 0.0), ('small', 'MMLU-Pro', 'C2C'): (1591, 2641, .6258, 0.0),
    ('medium', 'MMLU-Pro', 'Text'): (1128, 2641, .7166, 0.0), ('medium', 'MMLU-Pro', 'C2C'): (1410, 2641, .7652, 0.0),
    ('large', 'OBQA', 'Text+fact'): (76, 742, .88859, .75),
}
# cross-family reference values from the stored X1/X2 development tables (dis/N, AUROC, q)
for path, tag in [(XFAM / 'results/analysis/dev_table.csv', 'X2-OLMo'), (X1 / 'results/analysis/dev_table.csv', 'X1-Llama')]:
    for r in csvread(path):
        ds, ref = r['setting'].split(' ')[1].split('/')
        k, n = r['dis_over_N'].split('/')
        PAPER[(tag, {'obqa': 'OBQA', 'arc': 'ARC', 'mmlu_pro': 'MMLU-Pro'}[ds], ref)] = (
            int(k), int(n), round(float(r['AUROC']), 4), float(r['q']))
assert len(PAPER) == 26, len(PAPER)
# stored calibration ledgers, to match n/k/p row by row
from common_r1 import ledgers
STORED = ledgers()
STORED[('large', 'OBQA', 'Text+fact')] = [dict(q=float(r['q']), n=int(r['n']), k=int(r['k']), p=float(r['p']))
                                          for r in csvread(E6 / 'analysis/E6_LEDGER.csv')]
for r in csvread(E8 / 'analysis/calibration/80_test_ledger.csv'):
    s = (r['pair'], 'MMLU-Pro', r['reference'])
    STORED.setdefault(s, []).append(dict(q=float(r['q']), n=int(r['routed']), k=int(r['changed']), p=float(r['p_value'])))
for r in csvread(XFAM / 'results/analysis/certification_ledger_60.csv'):
    ds, ref = r['setting'].split('/')
    STORED.setdefault(('X2-OLMo', {'obqa': 'OBQA', 'arc': 'ARC', 'mmlu_pro': 'MMLU-Pro'}[ds], ref), []).append(
        dict(q=float(r['q']), n=int(r['n']), k=int(r['k']), p=float(r['p'])))
for r in csvread(X1 / 'results/analysis/certification_ledger_80.csv'):
    ds, ref = r['setting'].split('/')
    STORED.setdefault(('X1-Llama', {'obqa': 'OBQA', 'arc': 'ARC'}[ds], ref), []).append(
        dict(q=float(r['q']), n=int(r['n']), k=int(r['k']), p=float(r['p'])))

rows, fails = [], []
for s in ALL26:
    D = load(s)
    dcal = np.array([a != b for a, b in zip(D['cal']['oR'], D['cal']['ob'])], bool)
    ddev = np.array([a != b for a, b in zip(D['dev']['oR'], D['dev']['ob'])], bool)
    led = ledger_rows(D['cal']['u'], dcal, D['cuts'])
    q, acc = largest_accepted(led)
    q0 = D['q0']
    r0 = next(r for r in led if abs(r['q'] - q0) < 1e-9) if q0 > 0 else None
    st = {round(r['q'], 4): r for r in STORED[s]}
    # every one of the 20 rows must match the stored ledger
    lmis = [f"q={r['q']}: n {r['n']}!={st[round(r['q'],4)]['n']} k {r['k']}!={st[round(r['q'],4)]['k']}"
            for r in led if (r['n'], r['k']) != (st[round(r['q'], 4)]['n'], st[round(r['q'], 4)]['k'])]
    pmis = [f"q={r['q']}: p {r['p']:.6g} vs {st[round(r['q'],4)]['p']:.6g}"
            for r in led if abs(r['p'] - st[round(r['q'], 4)]['p']) > 1e-9 * max(1, abs(st[round(r['q'], 4)]['p']))]
    pk, pn, pauc, pq = PAPER[s] if s in PAPER else (None, None, None, None)
    a = auroc(ddev, D['dev']['u'])
    ok_q = (abs(q - q0) < 1e-9)
    tol = 5 * 10 ** -(len(str(pauc).split('.')[1]) + 1) if pauc is not None else 0
    ok_dev = pk is None or (int(ddev.sum()) == pk and len(ddev) == pn and abs(a - pauc) <= tol)
    ok = not lmis and not pmis and ok_q and ok_dev and (pq is None or abs(pq - q0) < 1e-9)
    if not ok:
        fails.append((sname(s), lmis[:2], pmis[:2], f'q_recomputed={q} q_expected={q0}' if not ok_q else '',
                      f'dev {int(ddev.sum())}/{len(ddev)} auroc {a:.4f} vs paper {pk}/{pn} {pauc}' if not ok_dev else ''))
    rows.append(dict(setting=sname(s), deployed_q=q0, q_recomputed_from_records=q,
                     cal_N=len(dcal), cal_n_at_q0=r0['n'] if r0 else '', cal_k_at_q0=r0['k'] if r0 else '',
                     cal_p_at_q0=f"{r0['p']:.6g}" if r0 else '', cal_CP999_at_q0=f"{r0['CP']:.6g}" if r0 else '',
                     ledger_20_rows_match_stored=not lmis, ledger_20_pvalues_match_stored=not pmis,
                     dev_N=len(ddev), dev_disagreements=int(ddev.sum()), dev_disagreement_rate=f'{ddev.mean():.5f}',
                     dev_AUROC=f'{a:.5f}',
                     paper_dev_disagreements=pk if pk is not None else '', paper_dev_N=pn if pn is not None else '',
                     paper_dev_AUROC=pauc if pauc is not None else '', paper_q=pq if pq is not None else '',
                     status='PASS' if ok else 'FAIL', label=LABEL))
    print(f"{sname(s):26s} q0={q0:<5} n/k/p={rows[-1]['cal_n_at_q0']}/{rows[-1]['cal_k_at_q0']}/{rows[-1]['cal_p_at_q0']:<10} "
          f"dev {int(ddev.sum())}/{len(ddev)} AUROC {a:.4f}  {rows[-1]['status']}")

csvout(RES / 'E11_step1_reproduction.csv', rows)
print()
if fails:
    print('REPRODUCTION CHECK: FAIL')
    for f in fails: print(' ', f)
    sys.exit(1)
print('REPRODUCTION CHECK: PASS  (26/26 settings; 520 ledger rows matched; dev dis/AUROC matched against the published value for all 26)')
