"""E9-a task 5 (descriptive): receiver confidence on changed answers, for the 14 main settings.
u = ProbeMax on the development split; the fit-split median of u is the frozen split point used for the share."""
import numpy as np
from e9a_common import *
from r2_common import load_main

MAIN14 = [(p, t, r) for p in ['small', 'medium'] for t in ['OBQA', 'ARC'] for r in ['Text', 'C2C']] + \
         [('large', t, r) for t in ['OBQA', 'ARC'] for r in ['Text', 'C2C']] + \
         [('large', 'MMLU-Pro', r) for r in ['Text', 'C2C']]
CODE = {'Text': 'T', 'C2C': 'C'}

main = load_main()
rows = []
for pair, task, ref in MAIN14:
    D = main[pair, task]
    u_fit = np.asarray(D['fit']['scores']['ProbeMax'], float)
    u = np.asarray(D['dev']['scores']['ProbeMax'], float)
    cut = float(np.median(u_fit))
    oR = list(D['dev']['ans']['R']); oX = list(D['dev']['ans'][CODE[ref]])
    ch = np.array([a != b for a, b in zip(oX, oR)], bool)
    n_ch = int(ch.sum())
    rows.append(dict(
        setting=f'{pair}/{task}/{ref}', N_dev=len(u), n_fit=len(u_fit),
        fit_split_median_u=f'{cut:.6g}', n_changed=n_ch,
        changed_pct=f'{100 * n_ch / len(u):.2f}',
        median_u_changed=f'{np.median(u[ch]):.6g}' if n_ch else 'nan',
        share_u_le_fit_median_changed=f'{(u[ch] <= cut).mean():.3f}' if n_ch else 'nan',
        median_u_all_dev=f'{np.median(u):.6g}',
        share_u_le_fit_median_all_dev=f'{(u <= cut).mean():.3f}',
        n_dev_u_exactly_at_or_below=int((u <= cut).sum()),
        n_dev_u_tied_at_cut=int((u == cut).sum()), label=LABEL))
    print(f'{rows[-1]["setting"]:22s} changed {n_ch:5d}  med_u_ch {rows[-1]["median_u_changed"]:>12s} '
          f'share {rows[-1]["share_u_le_fit_median_changed"]:>6s} | all med_u {rows[-1]["median_u_all_dev"]:>12s} '
          f'share {rows[-1]["share_u_le_fit_median_all_dev"]:>6s}  (ties at cut: {rows[-1]["n_dev_u_tied_at_cut"]})')

csvout(RES / 'e9a_receiver_confidence.csv', rows)
