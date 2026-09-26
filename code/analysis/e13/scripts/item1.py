"""E13 Item 1: best-fixed oracle headroom of the rate-matched null (point estimates over the same 1,000 E9-a draws).

Draw stream identical to e9a_main.py: one fresh default_rng(0) per population; per_reference T, per_reference C,
independent, joint, in that order, 1,000 draws each. Reproduction: the per-draw null gains must reproduce the saved
E9-a means exactly and the paper's joint ratios / real gains / real best-fixed headroom.
"""
import csv
import numpy as np
from e13_common import *

PAPER_JOINT = [.664, .737, .903, .845, .761, .641, .970]
PAPER_GAIN = [213, 94, 103, 31, 53, 12, 276]
PAPER_HBF = [132, 49, 70, 27, 25, 6, 239]
saved = {(r['population'], r['design']): float(r['null_gain_mean'])
         for r in csv.DictReader((E9A / 'results/e9a_null_draw_distribution.csv').open())}

pops = E.load_pops()
rows, repro, draws = [], [], {}
for pi, P in enumerate(pops):
    v = xview(P)
    rng = np.random.default_rng(0)
    gT, dT = v.per_reference_x(rng, 'T', E.NREP)
    gC, dC = v.per_reference_x(rng, 'C', E.NREP)
    gI, dI1, dI2 = v.independent_x(rng, E.NREP)
    gJ, dJ1, dJ2, forced, K, aU, bU, cU, csU, under = v.joint_x(rng, E.NREP)
    H = real_h(v)
    # reproduction checks
    for nm, g in [('per-reference Text', gT), ('per-reference C2C', gC), ('independent (E5-c)', gI), ('joint-matched', gJ)]:
        repro.append(dict(check=f'{P.name} {nm} null gain mean (1000 draws) vs saved E9-a', expected=f'{saved[P.name, nm]:.3f}',
                          got=f'{g.mean():.3f}', ok=f'{g.mean():.3f}' == f'{saved[P.name, nm]:.3f}'))
    repro.append(dict(check=f'{P.name} joint gain-over-R ratio vs paper', expected=f'{PAPER_JOINT[pi]:.3f}',
                      got=f'{gJ.mean() / v.real_TC:.3f}', ok=f'{gJ.mean() / v.real_TC:.3f}' == f'{PAPER_JOINT[pi]:.3f}'))
    repro.append(dict(check=f'{P.name} real gain over R (questions) vs paper', expected=PAPER_GAIN[pi], got=v.real_TC,
                      ok=v.real_TC == PAPER_GAIN[pi]))
    repro.append(dict(check=f'{P.name} real best-fixed headroom (questions) vs paper', expected=PAPER_HBF[pi], got=H['TC'],
                      ok=H['TC'] == PAPER_HBF[pi]))

    designs = [('independent (E5-c)', gI, dI1, dI2, H['TC'], v.real_TC),
               ('per-reference Text', gT, dT, None, H['T'], v.real_T),
               ('per-reference C2C', gC, dC, None, H['C'], v.real_C),
               ('joint-matched', gJ, dJ1, dJ2, H['TC'], v.real_TC)]
    for nm, g, d1, d2, hreal, greal in designs:
        hn = h_best_fixed_2(v.cR, g, d1, d2) if d2 is not None else h_best_fixed_1(v.cR, g, d1)
        best = np.maximum(0, np.maximum(d1, d2) if d2 is not None else d1)  # best-fixed null acc - correct(R)
        draws[P.name, nm] = hn
        if d2 is not None:
            real_T_minus_R, real_C_minus_R = v.cT - v.cR, v.cC - v.cR
            real_best = max(v.cR, v.cT, v.cC) - v.cR
        else:
            b = v.cT if nm.endswith('Text') else v.cC
            real_T_minus_R = (b - v.cR) if nm.endswith('Text') else ''
            real_C_minus_R = (b - v.cR) if nm.endswith('C2C') else ''
            real_best = max(v.cR, b) - v.cR
        rows.append(dict(
            population=P.name, design=nm, N=P.N, correct_R=v.cR, correct_Text=v.cT, correct_C2C=v.cC,
            H_real_best_fixed=hreal, gain_real_over_R=greal,
            H_null_mean=f'{hn.mean():.3f}', H_null_sd=f'{hn.std(ddof=1):.3f}',
            H_null_p2_5=f'{np.percentile(hn, 2.5):.1f}', H_null_p97_5=f'{np.percentile(hn, 97.5):.1f}',
            ratio_best_fixed=fmt(hn.mean() / hreal) if hreal else 'nan',
            gain_null_mean=f'{g.mean():.3f}', ratio_gain_over_R=fmt(g.mean() / greal) if greal else 'nan',
            mean_correct_N1=f'{v.cR + d1.mean():.3f}',
            mean_correct_N2=f'{v.cR + d2.mean():.3f}' if d2 is not None else '',
            mean_best_fixed_null_minus_R=f'{best.mean():.3f}',
            share_draws_best_fixed_null_is_R=f'{(best == 0).mean():.3f}',
            real_Text_minus_R=real_T_minus_R, real_C2C_minus_R=real_C_minus_R, real_best_fixed_minus_R=real_best,
            under_matched=('yes' if under else 'no') if nm == 'joint-matched' else
            ('Text' if v.mT > v.E else ('C2C' if v.mC > v.E else 'no')),
            draws=E.NREP, label=LABEL))

for nm in ['independent (E5-c)', 'per-reference Text', 'per-reference C2C', 'joint-matched']:
    rr = [r for r in rows if r['design'] == nm]
    rows.append(dict(population='MEDIAN of 7', design=nm,
                     ratio_best_fixed=fmt(np.median([float(r['ratio_best_fixed']) for r in rr])),
                     ratio_gain_over_R=fmt(np.median([float(r['ratio_gain_over_R']) for r in rr])), label=LABEL))
med_j = np.median([float(r['ratio_gain_over_R']) for r in rows if r['design'] == 'joint-matched' and r['population'] != 'MEDIAN of 7'])
repro.append(dict(check='joint gain-over-R median vs paper', expected='0.761', got=f'{med_j:.3f}', ok=f'{med_j:.3f}' == '0.761'))

csvout(RES / 'item1_best_fixed_headroom.csv', rows)
csvout(RES / 'item1_repro_checks.csv', repro)
np.savez_compressed(RES / 'item1_null_draws_H.npz', **{f'{k[0]}|{k[1]}': v for k, v in draws.items()})
for r in rows:
    print(f"{r['population']:15s} {r['design']:20s} Hreal={r.get('H_real_best_fixed','')!s:>4} Hnull={r.get('H_null_mean','')!s:>8} "
          f"[{r.get('H_null_p2_5','')}, {r.get('H_null_p97_5','')}] bf={r['ratio_best_fixed']} gain={r['ratio_gain_over_R']}")
print('repro failures:', [r for r in repro if not r['ok']])
