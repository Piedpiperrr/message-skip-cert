"""E18 certification = the E10 certification arithmetic with only the score column replaced.

Copied line for line from P2_R4_E10_20260920T225954Z/src/e10_seal.py (thresholds, 20 exact binomial
tests, largest-accepted-q deployment, mid-rank AUROC).  e10_seal.py is a script that writes into the
E10 analysis/ folder, which is read-only for E18, so its arithmetic is reproduced here as functions
instead of being executed.  G6 checks that cert(u) reproduces E10's sealed tests exactly.
NO GOLD IS READ HERE."""
import json, glob
from pathlib import Path
import numpy as np
from scipy.stats import binom, beta

E10 = Path('$DATA_DIR/P2_R4_E10_20260920T225954Z')
Q = [j / 20 for j in range(1, 21)]
ALPHA, DELTA = .05, .001

def load_e10():
    rows = []
    for f in sorted(glob.glob(str(E10 / 'records/main_rank*.jsonl'))):
        for line in open(f):
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    by = {}
    for r in rows:
        by[(r['split'], r['action'], r['id'])] = r
    splits = {s: json.loads((E10 / f'splits/gsm8k_{s}_ids.json').read_text()) for s in ['fit', 'cal', 'dev']}
    return by, splits

def tv(t):
    return float('inf') if t == 'Infinity' else float(t)

def auroc(score, label):
    s, y = np.asarray(score, float), np.asarray(label, int)
    if y.sum() == 0 or y.sum() == len(y):
        return None
    r = np.empty(len(s), float)
    order = np.argsort(s, kind='mergesort')
    ss = s[order]; i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    n1 = int(y.sum()); n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))

def certify(score, by, splits):
    """score: dict id -> float (the only thing that differs from E10, where score = record['u'])."""
    def usable(split):
        need = ['R'] if split == 'fit' else ['R', 'T']
        return [i for i in splits[split] if all((split, a, i) in by for a in need)]

    def disagree(i, split):
        return by[(split, 'R', i)]['answer'] != by[(split, 'T', i)]['answer']

    fit_ids = usable('fit')
    fit_u = sorted(score[i] for i in fit_ids)
    n_fit = len(fit_u)
    thresholds = [fit_u[(j * n_fit + 19) // 20 - 1] if j < 20 else 'Infinity' for j in range(1, 21)]

    cal_ids = usable('cal')
    cu = np.array([score[i] for i in cal_ids], float)
    cd = np.array([disagree(i, 'cal') for i in cal_ids], int)
    tests = []
    for q, t in zip(Q, thresholds):
        mask = cu <= tv(t)
        n, k = int(mask.sum()), int(cd[mask].sum())
        pv = float(binom.cdf(k, n, ALPHA)) if n else 1.
        cp = float(beta.ppf(.999, k + 1, n - k)) if n and k < n else 1.
        tests.append({'q': q, 'threshold': t, 'N_cal': len(cu), 'n': n, 'changed': k,
                      'conditional_change_rate': (k / n) if n else None, 'p_value': pv,
                      'CP_upper_0_999': cp, 'accepted': pv <= DELTA, 'coverage': n / len(cu)})
    acc = [t for t in tests if t['accepted']]
    chosen = acc[-1] if acc else None
    best = min(tests, key=lambda t: t['p_value'])
    deployment = {'q': chosen['q'] if chosen else 0.0,
                  'threshold': chosen['threshold'] if chosen else None,
                  'mode': ('fixed_R' if chosen['q'] == 1 else 'selective') if chosen else 'fixed_reference',
                  'accepted_q': [t['q'] for t in acc], 'calibration': chosen,
                  'smallest_p_value': best['p_value'], 'smallest_p_candidate': best['q'],
                  'smallest_p_n': best['n'], 'smallest_p_k': best['changed'],
                  'alpha': ALPHA, 'delta_per_test': DELTA, 'tests': 20,
                  'family_wise_bound': 20 * DELTA,
                  'rule': 'largest accepted q; no acceptance -> always communicate (Text)'}

    dev_ids = usable('dev')
    du = np.array([score[i] for i in dev_ids], float)
    dd = np.array([disagree(i, 'dev') for i in dev_ids], int)
    tau = tv(deployment['threshold']) if deployment['threshold'] is not None else -float('inf')
    omit = du <= tau
    n_om = int(omit.sum()); k_om = int(dd[omit].sum())
    dev_summary = {'N': len(dev_ids), 'coverage': n_om / len(dev_ids) if dev_ids else None,
                   'omitted': n_om, 'changed_among_omitted': k_om,
                   'conditional_change_rate': (k_om / n_om) if n_om else None,
                   'CP95': ([float(beta.ppf(.025, k_om, n_om - k_om + 1)) if k_om else 0.0,
                             float(beta.ppf(.975, k_om + 1, n_om - k_om)) if k_om < n_om else 1.0]
                            if n_om else None),
                   'always_omit_change_rate': float(dd.mean()) if len(dd) else None}
    return {'N_fit': n_fit, 'thresholds': thresholds, 'q_grid': Q, 'tests': tests, 'deployment': deployment,
            'dev': dev_summary, 'dev_ids': dev_ids, 'dev_omitted': [bool(x) for x in omit],
            'dev_disagree': [int(x) for x in dd],
            'cal_disagreement': [int(cd.sum()), len(cd)], 'dev_disagreement': [int(dd.sum()), len(dd)]}
