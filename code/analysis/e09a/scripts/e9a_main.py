"""E9-a tasks 1, 2, 4: per-reference matched ratios, the joint-matched null, and the overlap table.
1,000 draws per design per population, numpy default_rng(0) (one fresh stream per population)."""
import numpy as np
from e9a_common import *

pops = load_pops()
ratio_rows, overlap_rows, draw_rows = [], [], []
for P in pops:
    v = P.view()
    rng = np.random.default_rng(0)
    gT = v.per_reference(rng, 'T', NREP)
    gC = v.per_reference(rng, 'C', NREP)
    gI = v.independent(rng, NREP)
    gJ, forced, K, aU, bU, cU, csU = v.joint(rng, NREP)

    under_ref = 'Text' if v.mT > v.E else ('C2C' if v.mC > v.E else 'no')
    under_joint = (v.a + v.b + v.c) > v.E
    r = lambda gains, real: float(gains.mean() / real) if real else float('nan')

    ratio_rows.append(dict(
        population=P.name, N=P.N, n_eligible_P_nonempty=v.E,
        real_gain_R_Text=v.real_T, real_gain_R_C2C=v.real_C, real_gain_R_Text_C2C=v.real_TC,
        m_Text=v.mT, m_C2C=v.mC,
        perref_Text_null_gain_mean=f'{gT.mean():.2f}', perref_Text_ratio=fmt(r(gT, v.real_T)),
        perref_C2C_null_gain_mean=f'{gC.mean():.2f}', perref_C2C_ratio=fmt(r(gC, v.real_C)),
        independent_null_gain_mean=f'{gI.mean():.2f}', independent_ratio=fmt(r(gI, v.real_TC)),
        joint_null_gain_mean=f'{gJ.mean():.2f}', joint_ratio=fmt(r(gJ, v.real_TC)),
        joint_K_drawn=K, joint_a_used=aU, joint_b_used=bU, joint_c_used=cU, joint_c_same_used=csU,
        joint_forced_same_mean_per_draw=f'{forced.mean():.2f}',
        joint_forced_same_min=int(forced.min()), joint_forced_same_max=int(forced.max()),
        under_matched_per_reference=under_ref, under_matched_joint='yes' if under_joint else 'no',
        repetitions=NREP, label=LABEL))

    for nm, g in [('per-reference Text', gT), ('per-reference C2C', gC), ('independent (E5-c)', gI), ('joint-matched', gJ)]:
        draw_rows.append(dict(population=P.name, design=nm, draws=NREP, null_gain_mean=f'{g.mean():.3f}',
                              null_gain_sd=f'{g.std(ddof=1):.3f}', null_gain_p2_5=f'{np.percentile(g, 2.5):.1f}',
                              null_gain_p50=f'{np.percentile(g, 50):.1f}', null_gain_p97_5=f'{np.percentile(g, 97.5):.1f}',
                              label=LABEL))

    exp_indep = (v.a + v.c) * (v.b + v.c) / P.N
    overlap_rows.append(dict(population=P.name, N=P.N, a_Text_only=v.a, b_C2C_only=v.b, c_both=v.c,
                             c_same_answer=v.c_same, c_different_answer=v.c - v.c_same,
                             expected_both_if_independent=f'{exp_indep:.2f}',
                             ratio_c_over_expected=fmt(v.c / exp_indep) if exp_indep else 'nan',
                             a_plus_b_plus_c=v.a + v.b + v.c, n_eligible_P_nonempty=v.E,
                             under_matched_joint='yes' if under_joint else 'no', label=LABEL))
    print(f'{P.name:16s} perrefT {ratio_rows[-1]["perref_Text_ratio"]} perrefC {ratio_rows[-1]["perref_C2C_ratio"]} '
          f'indep {ratio_rows[-1]["independent_ratio"]} joint {ratio_rows[-1]["joint_ratio"]} '
          f'forced {forced.mean():.2f}' + ('  UNDER-MATCHED(joint)' if under_joint else ''))

for key, nm in [('perref_Text_ratio', 'per-reference Text'), ('perref_C2C_ratio', 'per-reference C2C'),
                ('independent_ratio', 'independent (E5-c)'), ('joint_ratio', 'joint-matched')]:
    print(f'median {nm:22s} {np.median([float(x[key]) for x in ratio_rows]):.3f}')

csvout(RES / 'e9a_ratios.csv', ratio_rows)
csvout(RES / 'e9a_null_draw_distribution.csv', draw_rows)
csvout(RES / 'e9a_overlap.csv', overlap_rows)
