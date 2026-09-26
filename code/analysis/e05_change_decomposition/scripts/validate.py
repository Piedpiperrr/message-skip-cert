"""Validation: recompute each setting's 20 frozen-threshold tests on the FULL calibration set and compare to the
stored ledgers (14 main: calibration_all_160 / medium / MMLU-Pro; 7 cross-family: X1/X2 certification ledgers)."""
from r2_common import *
import numpy as np, data_r1
from common_r1 import ledgers

L = ledgers()
main = load_main(); x2 = load_x2(); x1 = load_x1()
rows = []
for s in ALL21:
    pair, task, ref = s
    ds = BENCH[task]
    if pair in ('small', 'medium', 'large'):
        D = main[pair, task]
        u = D['cal']['scores']['ProbeMax']; d = data_r1.disagreement(D['cal'], ref); cuts = D['stored_thresholds']
        stored = [(r['n'], r['k']) for r in L[s]]
        src = 'stored ledger (calibration_all_160 / medium / MMLU-Pro 40_test_ledger)'
    elif pair == 'X2-OLMo':
        D = x2[ds]; u = np.array(D['cal']['u'])
        d = np.array([a != b for a, b in zip(D['cal']['oR'], D['cal']['oT'])], bool)
        rr = [r for r in csvread(XFAM / 'results/analysis/certification_ledger_60.csv') if r['setting'] == f'{ds}/Text']
        cuts = [r['threshold'] for r in rr]; stored = [(int(r['n']), int(r['k'])) for r in rr]
        src = 'X2 certification_ledger_60.csv'
    else:
        D = x1[ds]; u = np.array(D['cal']['u'])
        o = D['cal']['oT'] if ref == 'Text' else D['cal']['oC']
        d = np.array([a != b for a, b in zip(D['cal']['oR'], o)], bool)
        rr = [r for r in csvread(X1 / 'results/analysis/certification_ledger_80.csv') if r['setting'] == f'{ds}/{ref}']
        cuts = [r['threshold'] for r in rr]; stored = [(int(r['n']), int(r['k'])) for r in rr]
        src = 'X1 certification_ledger_80.csv'
    mine = [(r['n'], r['k']) for r in ledger_rows(u, d, cuts)]
    rows.append(dict(setting=sname(s), n_k_reproduced=str(mine == stored), grid_points=len(mine), source=src, label=LABEL))
csvout(RES / 'validation_checks.csv', rows)
bad = [r for r in rows if r['n_k_reproduced'] != 'True']
print('reproduced', sum(r['n_k_reproduced'] == 'True' for r in rows), '/', len(rows))
for r in bad: print('MISMATCH', r['setting'])
