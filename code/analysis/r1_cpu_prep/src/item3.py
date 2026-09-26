"""Item 3 (POST-HOC sensitivity): alpha .02/.10, fixed-sequence, entropy and margin scores; dev at the fit threshold."""
import time
from sklearn.metrics import roc_auc_score
from data_r1 import *

t0 = time.time()
L = ledgers()
DATA = load_all()
# Paper Table tab_dev_full (P2_STRENGTHEN_20260918T205058Z/paper/tab_dev_full.tex): Dis, AUROC, cov%, changed/omitted
PAPER = {('small', 'OBQA', 'Text'): (339, .641, 0.0, None), ('small', 'OBQA', 'C2C'): (350, .700, 0.0, None),
         ('small', 'ARC', 'Text'): (145, .634, 0.0, None), ('small', 'ARC', 'C2C'): (160, .641, 0.0, None),
         ('medium', 'OBQA', 'Text'): (174, .787, 0.0, None), ('medium', 'OBQA', 'C2C'): (131, .840, 52.6, (11, 390)),
         ('medium', 'ARC', 'Text'): (52, .742, 0.0, None), ('medium', 'ARC', 'C2C'): (48, .910, 63.2, (4, 189)),
         ('large', 'OBQA', 'Text'): (72, .873, 77.1, (19, 572)), ('large', 'OBQA', 'C2C'): (60, .883, 77.1, (13, 572)),
         ('large', 'ARC', 'Text'): (15, .952, 95.0, (9, 284)), ('large', 'ARC', 'C2C'): (12, .909, 90.3, (3, 270)),
         ('large', 'MMLU-Pro', 'Text'): (561, .821, 40.5, (40, 1069)), ('large', 'MMLU-Pro', 'C2C'): (756, .846, 40.5, (37, 1069))}


def dev_eval(u, d, q, t):
    m = route_mask(u, q, t); n = int(m.sum()); k = int(d[m].sum())
    return dict(dev_N=len(u), dev_omitted=n, dev_changed=k, dev_coverage_pct=100 * n / len(u))


def summarize(variant, s, q, rows, cuts, u_dev, d_dev, accepted, note=''):
    sel = next((r for r in rows if r['q'] == q), None) if q > 0 else None
    t = cuts[GRID.index(q)] if q > 0 else None
    ev = dev_eval(u_dev, d_dev, q, t) if q > 0 else dict(dev_N=len(u_dev), dev_omitted=0, dev_changed=0, dev_coverage_pct=0.0)
    return dict(pair=s[0], task=s[1], reference=s[2], variant=variant, deployed_q=q, fit_threshold=t,
                cal_n=sel['n'] if sel else None, cal_k=sel['k'] if sel else None,
                accepted_q=';'.join(f'{x:g}' for x in accepted), **ev,
                dev_changed_over_omitted=f"{ev['dev_changed']}/{ev['dev_omitted']}" if q > 0 else 'N/A',
                historically_tested=note, label=LABEL)


results, ledgers_out, aurocs, checks = [], [], [], []
for s in SETTINGS:
    D = DATA[s[0], s[1]]
    fit, cal, dev = D['fit'], D['cal'], D['dev']
    cd, dd = disagreement(cal, s[2]), disagreement(dev, s[2])
    # --- checks: stored thresholds, ledger n/k, dev prevalence/AUROC/primary dev vs paper
    cutsPM, rowsPM = ledger_from_scores(fit['scores']['ProbeMax'], cal['scores']['ProbeMax'], cd)
    thr_ok = [str(a) for a in cutsPM] == [str(b) for b in D['stored_thresholds']]
    led_ok = all((a['n'], a['k']) == (b['n'], b['k']) for a, b in zip(rowsPM, L[s]))
    qP, accP = deploy(L[s])
    prim = summarize('primary_ProbeMax', s, qP, L[s], cutsPM, dev['scores']['ProbeMax'], dd, accP,
                     'historically tested (reused certification)' if s == ('large', 'OBQA', 'Text') else '')
    pp = PAPER[s]
    auc_pm = roc_auc_score(dd, dev['scores']['ProbeMax'])
    paper_ok = (int(dd.sum()) == pp[0] and round(auc_pm, 3) == pp[1] and round(prim['dev_coverage_pct'], 1) == pp[2] and
                (pp[3] is None or (prim['dev_changed'], prim['dev_omitted']) == pp[3]))
    checks.append(dict(pair=s[0], task=s[1], reference=s[2], N_fit=len(fit['ids']), N_cal=len(cal['ids']), N_dev=len(dev['ids']),
                       thresholds_match_stored=thr_ok, ledger_n_k_reproduced_from_scores=led_ok, dev_disagreements=int(dd.sum()),
                       dev_AUROC_ProbeMax=auc_pm, primary_dev_matches_paper_table=paper_ok, **{f'src_{k}': v for k, v in D['sources'].items()}))
    results.append(prim)
    # --- (a) alpha .02 / .10 on ledger n,k ; (b) fixed sequence
    for a in (.02, .10):
        q, acc = deploy(L[s], alpha=a)
        results.append(summarize(f'alpha_{a:.2f}', s, q, L[s], cutsPM, dev['scores']['ProbeMax'], dd, acc))
    qf = deploy_fixed_sequence(L[s])
    accf = [r['q'] for r in L[s] if r['q'] <= qf] if qf > 0 else []
    results.append(summarize('fixed_sequence_0.02', s, qf, L[s], cutsPM, dev['scores']['ProbeMax'], dd, accf))
    # --- (c) Entropy, Margin: thresholds from fit order statistics; certification on cal
    aurocs.append(dict(pair=s[0], task=s[1], reference=s[2], score='ProbeMax', dev_N=len(dd), dev_disagreements=int(dd.sum()), dev_AUROC=auc_pm, label=LABEL))
    for fam in ['Entropy', 'Margin']:
        cuts, rows = ledger_from_scores(fit['scores'][fam], cal['scores'][fam], cd)
        q, acc = deploy(rows)
        note = 'historically tested (ProbeEntropy = H/ln4 in P2_ZERO_GOLD_CONTROLS; rank-equivalent, K=4)' if (fam == 'Entropy' and s == ('large', 'OBQA', 'Text')) else ''
        results.append(summarize(fam, s, q, rows, cuts, dev['scores'][fam], dd, acc, note))
        for r in rows: ledgers_out.append(dict(pair=s[0], task=s[1], reference=s[2], score=fam, **r, label=LABEL))
        aurocs.append(dict(pair=s[0], task=s[1], reference=s[2], score=fam, dev_N=len(dd), dev_disagreements=int(dd.sum()),
                           dev_AUROC=roc_auc_score(dd, dev['scores'][fam]), label=LABEL))
    print(s, 'checks', thr_ok, led_ok, paper_ok, f'{time.time()-t0:.0f}s', flush=True)

# historical entropy ledger comparison (large/OBQA/Text)
hist = [r for r in csvread(ZG / 'summary/calibration_new_60.csv') if r['family'] == 'ProbeEntropy']
mine = [r for r in ledgers_out if (r['pair'], r['task'], r['reference'], r['score']) == ('large', 'OBQA', 'Text', 'Entropy')]
hist_ok = all((int(h['n_R']), int(h['changed']), h['accepted'] == 'True') == (m['n'], m['k'], m['accepted']) for h, m in zip(hist, mine))
print('historical ProbeEntropy ledger reproduced:', hist_ok)
for c in checks: c['historical_entropy_ledger_reproduced'] = hist_ok if (c['pair'], c['task'], c['reference']) == ('large', 'OBQA', 'Text') else ''
csvout(P / 'results/item3_sensitivity.csv', results)
csvout(P / 'results/item3_entropy_margin_ledgers.csv', ledgers_out)
csvout(P / 'results/item3_dev_auroc.csv', aurocs)
csvout(P / 'results/item3_input_checks.csv', checks)
print('done', f'{time.time()-t0:.0f}s')
