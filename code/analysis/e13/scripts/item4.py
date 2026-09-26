"""E13 Item 4: does the ProbeMax AUROC on a small paired fit sample predict the certification outcome?

Rule (as written in the paper): predict deploy iff sample AUROC >= .80; no disagreement in the sample -> deploy;
no agreement -> fallback. AUROC: sklearn.metrics.roc_auc_score (the function behind the paper's main-table development
AUROCs, P2_R1_CPU item3.py and E8 analyze_e8.py), via e11_common.auroc. Samples: for every (setting, n) a fresh
numpy default_rng(0); 200 draws of n fit questions without replacement (rng.choice(N, n, replace=False)).
Text+fact has no fit-split reference outputs -> development split, flagged.
"""
import numpy as np
from e13_settings import *
from e13_common import csvout, RES, LABEL, fmt  # noqa: F401

NS = [100, 200, 400]
ND = 200
PAPER_AUC = {('large', 'OBQA', 'Text'): .873, ('large', 'ARC', 'Text'): .952, ('medium', 'ARC', 'C2C'): .910,
             ('medium', 'ARC', 'Text'): .742, ('X2-OLMo', 'OBQA', 'Text'): .790, ('large', 'MMLU-Pro', 'Text'): .821}

rows, per, repro = [], [], []
for s in ALL26:
    L = C.load(s)
    dv = L['dev']; ddev = dis(dv)
    auc_dev = C.auroc(ddev, dv['u'])
    if s in PAPER_AUC:
        repro.append(dict(item=4, check=f'{C.sname(s)} dev AUROC', expected=PAPER_AUC[s], got=round(auc_dev, 3),
                          ok=round(auc_dev, 3) == PAPER_AUC[s]))
    F = load_fit(s)
    src = 'fit' if F is not None else 'dev (no fit-split reference outputs; flagged)'
    if F is None:
        F = dv
    u = np.asarray(F['u'], float); d = dis(F); N = len(u)
    outcome = 'deploy' if L['q0'] > 0 else 'fallback'
    row = dict(setting=C.sname(s), outcome=outcome, q0=L['q0'], dev_AUROC=auc_dev, sample_split=src, N_split=N,
               split_disagreement_rate=d.mean(), split_AUROC=C.auroc(d, u))
    for n in NS:
        rng = np.random.default_rng(0)
        aucs, preds, rates, nodis, noagr = [], [], [], 0, 0
        for _ in range(ND):
            ix = rng.choice(N, n, replace=False)
            dd = d[ix]; rates.append(dd.mean())
            if dd.sum() == 0:
                nodis += 1; preds.append('deploy'); aucs.append(np.nan)
            elif dd.sum() == n:
                noagr += 1; preds.append('fallback'); aucs.append(np.nan)
            else:
                a = C.auroc(dd, u[ix]); aucs.append(a); preds.append('deploy' if a >= .80 else 'fallback')
            per.append(dict(setting=C.sname(s), n=n, draw=len(preds) - 1, sample_AUROC=aucs[-1], prediction=preds[-1],
                            disagreement_rate=rates[-1]))
        A = np.array(aucs); ok = A[~np.isnan(A)]
        match = np.mean([p == outcome for p in preds])
        row.update({f'n{n}_AUROC_median': np.median(ok) if len(ok) else np.nan,
                    f'n{n}_AUROC_q25': np.percentile(ok, 25) if len(ok) else np.nan,
                    f'n{n}_AUROC_q75': np.percentile(ok, 75) if len(ok) else np.nan,
                    f'n{n}_share_pred_deploy': np.mean([p == 'deploy' for p in preds]),
                    f'n{n}_match_share': match, f'n{n}_no_disagreement_draws': nodis, f'n{n}_no_agreement_draws': noagr,
                    f'n{n}_dis_rate_median': np.median(rates), f'n{n}_dis_rate_q25': np.percentile(rates, 25),
                    f'n{n}_dis_rate_q75': np.percentile(rates, 75)})
    row['label'] = LABEL
    rows.append(row)
    print(f"{row['setting']:24s} {outcome:8s} devAUC={auc_dev:.3f} " + ' '.join(
        f"n{n}: med={row[f'n{n}_AUROC_median']:.3f} [{row[f'n{n}_AUROC_q25']:.3f},{row[f'n{n}_AUROC_q75']:.3f}] match={row[f'n{n}_match_share']:.3f}"
        for n in NS) + ('' if src == 'fit' else '  [DEV]'))

overall = []
for n in NS:
    for grp, sel in [('all', lambda r: True), ('deployed', lambda r: r['outcome'] == 'deploy'),
                     ('fallback', lambda r: r['outcome'] == 'fallback')]:
        rr = [r for r in rows if sel(r)]
        ms = [r[f'n{n}_match_share'] for r in rr]
        overall.append(dict(n=n, group=grp, n_settings=len(rr), mean_match_share=np.mean(ms), min_match_share=np.min(ms),
                            max_match_share=np.max(ms), n_settings_match_ge_0_8=sum(m >= .8 for m in ms),
                            n_no_disagreement_draws=sum(r[f'n{n}_no_disagreement_draws'] for r in rr),
                            n_no_agreement_draws=sum(r[f'n{n}_no_agreement_draws'] for r in rr),
                            worst_settings=';'.join(f"{r['setting']}={r[f'n{n}_match_share']:.3f}"
                                                    for r in sorted(rr, key=lambda r: r[f'n{n}_match_share'])[:4]),
                            label=LABEL))
        print(overall[-1])
    # same summary without the Text+fact dev-split row (sensitivity)
    rr = [r for r in rows if r['sample_split'] == 'fit']
    ms = [r[f'n{n}_match_share'] for r in rr]
    overall.append(dict(n=n, group='all, fit-split settings only (excl. Text+fact)', n_settings=len(rr), mean_match_share=np.mean(ms),
                        min_match_share=np.min(ms), max_match_share=np.max(ms), n_settings_match_ge_0_8=sum(m >= .8 for m in ms),
                        label=LABEL))
csvout(RES / 'item4_per_setting.csv', rows)
csvout(RES / 'item4_overall.csv', overall)
csvout(RES / 'item4_draws.csv', per)
csvout(RES / 'item4_repro_checks.csv', repro)
for r in repro: print(r)
