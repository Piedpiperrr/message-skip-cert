"""E15-1: predicting certification from the fit split alone (preregistered plug-in rule, no fitted parameter).

For every candidate j (frozen fit threshold tau_j; q = 1 -> all fit questions):
  m_j = #fit with u <= tau_j, d_j = # of those with o_R != o_b (frozen V2 labels; two INVALID agree),
  n_hat = round_half_up(N_cal * m_j / N_fit), k_hat = round_half_up(n_hat * d_j / m_j) (0 if m_j = 0),
  accepted iff Pr[Bin(n_hat, .05) <= k_hat] <= .001 (n_hat = 0 -> p = 1).  Exact rational arithmetic for rounding.
q_hat = largest accepted q, else predicted fallback; predicted coverage = m_j / N_fit at q_hat.
Saving model (8 replayed policies): kappa * (mean c_b - mean c_R) - mean c_s, with c_b, c_R, c_s from the component
accounting records behind Table 'Same-target baselines' (ii) (development populations); kappa = predicted fit coverage
(0 saving if predicted fallback) or the actual original-configuration panel coverage.
"""
from e15_common import *

TAB2ii = {('medium', 'OBQA', 'C2C'): (394.5, 216.4, 326.1), ('medium', 'ARC', 'C2C'): (445.5, 229.1, 340.1),
          ('large', 'OBQA', 'Text'): (978.5, 253.6, 462.9), ('large', 'OBQA', 'C2C'): (335.8, 253.6, 315.8),
          ('large', 'ARC', 'Text'): (1060.8, 267.6, 354.9), ('large', 'ARC', 'C2C'): (414.4, 267.6, 321.4),
          ('large', 'MMLU-Pro', 'Text'): (1292.0, 274.2, 946.6), ('large', 'MMLU-Pro', 'C2C'): (383.9, 274.2, 357.1)}
T2 = {(r['pair'], r['task'], r['reference']): r for r in csvread(AUDIT_T2) if r['option'] == 'frozen ProbeMax gate'}

cand, per, checks = [], [], []
for s in SET25:
    L = C.load(s)
    F = load_fit(s)
    u, d = np.asarray(F['u'], float), dis(F)
    Nf, Nc = len(u), len(L['cal']['u'])
    led = C.ledger_rows(L['cal']['u'], dis(L['cal']), L['cuts'])
    q, _ = C.largest_accepted(led)
    assert q == L['q0']
    pred = []
    for (qq, t), lr in zip(zip(GRID, L['cuts']), led):
        mk = cover(u, qq, t)
        m, dd = int(mk.sum()), int(d[mk].sum())
        n_hat = rhu(Fraction(Nc * m, Nf))
        k_hat = rhu(Fraction(n_hat * dd, m)) if m > 0 else 0
        p_hat = C.pval(k_hat, n_hat)
        pred.append(dict(q=qq, m=m, d=dd, acc=p_hat <= .001))
        cand.append(dict(setting=sname(s), q=qq, threshold=t, N_fit=Nf, N_cal=Nc, m_fit=m, d_fit=dd, n_hat=n_hat, k_hat=k_hat,
                         p_hat=p_hat, predicted_accept=p_hat <= .001, cal_n=lr['n'], cal_k=lr['k'], cal_p=lr['p'],
                         actual_accept=lr['accepted'], label=LABEL))
    accq = [r for r in pred if r['acc']]
    q_hat = accq[-1]['q'] if accq else 0.0
    pcov = accq[-1]['m'] / Nf if accq else None
    row = dict(setting=sname(s), N_fit=Nf, N_cal=Nc, actual_outcome='deploy' if q > 0 else 'fallback', actual_q=q,
               predicted_outcome='deploy' if q_hat > 0 else 'fallback', q_hat=q_hat,
               outcome_match=(q > 0) == (q_hat > 0), predicted_fit_coverage=pcov)
    if q > 0:
        cut = L['cuts'][GRID.index(q)]
        row['actual_dev_coverage'] = float(cover(L['dev']['u'], q, cut).mean())
        row['N_dev'] = len(L['dev']['u'])
    if q > 0 and q_hat > 0:
        row['grid_steps_qhat_minus_q'] = int(round((q_hat - q) * 20))
        row['abs_grid_steps'] = abs(row['grid_steps_qhat_minus_q'])
        row['abs_coverage_error'] = abs(row['actual_dev_coverage'] - pcov)
    if s in DEPLOY8:
        comp = component_dev(s)
        assert set(comp) == set(L['dev']['ids']), sname(s)
        idx = [comp[i] for i in L['dev']['ids']]
        lR, lb, pr = (np.array([x[k] for x in idx], float) for k in range(3))
        om = cover(L['dev']['u'], q, L['cuts'][GRID.index(q)])
        cb, cR, cs = float(lb.mean()), float(lR.mean()), float(pr.mean())
        pol = float(np.mean(pr + np.where(om, lR, lb)))
        exp = TAB2ii[s]
        t2 = T2[(s[0], TASKDS[s[1]], s[2])]
        ok = (round(cb, 1), round(cR, 1), round(pol, 1)) == exp and abs(float(t2['coverage_dev']) - float(om.mean())) < 5e-5
        checks.append(dict(check='Table baselines (ii) Ref/R/Policy and T2 dev coverage reproduced from component records',
                           setting=sname(s), expected=exp, got=(round(cb, 1), round(cR, 1), round(pol, 1)),
                           T2_coverage_dev=t2['coverage_dev'], got_coverage=round(float(om.mean()), 4), ok=ok))
        ids, fx, po, f = original_replay(s)
        kp = float(np.mean([po[i]['selected'] == 'R' for i in ids]))
        meas = float(np.mean([fx[i]['latency_ms'] - po[i]['latency_ms'] for i in ids]))
        gap = cb - cR
        pf = (pcov * gap - cs) if q_hat > 0 else 0.0
        pp = kp * gap - cs
        row.update(c_b_mean_ms=cb, c_R_mean_ms=cR, c_s_mean_ms=cs, gap_ms=gap, panel_coverage=kp,
                   measured_saving_ms=meas, table2_saving_ms=TABLE2[s],
                   pred_saving_fitcov_ms=pf, pred_saving_panelcov_ms=pp,
                   abs_err_fitcov_ms=abs(pf - meas), rel_err_fitcov=abs(pf - meas) / abs(meas),
                   abs_err_panelcov_ms=abs(pp - meas), rel_err_panelcov=abs(pp - meas) / abs(meas),
                   component_recomposed_saving_ms=cb - pol, replay_source=str(f))
    row['label'] = LABEL
    per.append(row)
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items() if k not in ('label', 'replay_source')})

dep = [r for r in per if r['actual_outcome'] == 'deploy']
fb = [r for r in per if r['actual_outcome'] == 'fallback']
both = [r for r in per if 'abs_grid_steps' in r]
x = sum(r['predicted_outcome'] == 'deploy' for r in dep)
y = sum(r['predicted_outcome'] == 'fallback' for r in fb)
med = lambda v: float(np.median(v)) if len(v) else None
summ = dict(n_settings=len(per), n_deployed=len(dep), n_fallback=len(fb), x_deployed_predicted_deploy=x,
            y_fallback_predicted_fallback=y, n_both_deploy=len(both),
            median_abs_grid_steps=med([r['abs_grid_steps'] for r in both]), max_abs_grid_steps=max([r['abs_grid_steps'] for r in both]) if both else None,
            median_abs_coverage_error=med([r['abs_coverage_error'] for r in both]),
            median_abs_saving_err_fitcov_ms=med([r['abs_err_fitcov_ms'] for r in dep]),
            median_rel_saving_err_fitcov=med([r['rel_err_fitcov'] for r in dep]),
            median_abs_saving_err_panelcov_ms=med([r['abs_err_panelcov_ms'] for r in dep]),
            median_rel_saving_err_panelcov=med([r['rel_err_panelcov'] for r in dep]))
rule = x >= 7 and y >= 15 and both and summ['median_abs_grid_steps'] <= 1
summ['paper_rule'] = 'predicts' if rule else 'does not reliably predict'
summ['label'] = LABEL
print(summ)
for c in checks: print(c)
csvout('e15_1_per_setting.csv', per)
csvout('e15_1_candidates.csv', cand)
csvout('e15_1_summary.csv', [summ])
csvout('e15_1_checks.csv', checks)
csvout('e15_1_files_read.csv', [dict(path=p) for p in dict.fromkeys(READ)])
assert all(c['ok'] for c in checks)
