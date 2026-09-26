"""E9B step 2 (login node, CPU): decode the answer key and compute every prespecified statistic.
Runs only after e9b_seal.py has written and hashed the scores, routes and outputs."""
import sys, os, json, hashlib, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e9b_common import *
from pathlib import Path
import numpy as np
from scipy.stats import binom, beta
import pyarrow.parquet as pq

OUT = STAGE / 'analysis'
rec = rd(OUT / 'SEAL_RECEIPT.json')
def sha(p):
    h = hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
for f, h in rec['files'].items():
    assert sha(OUT / f) == h, f'seal broken: {f}'
print('seal verified:', rec['utc'])

DS = Path('$DATA_DIR/c2c_reproduction_assets/datasets/allenai--openbookqa/main/train-00000-of-00001.parquet')
tb = pq.read_table(DS, columns=['id', 'answerKey'])          # <- the answer key, opened only now
GOLD = dict(zip(tb.column('id').to_pylist(), tb.column('answerKey').to_pylist()))
pop = [r['id'] for r in population()]
gold = {i: GOLD[i] for i in pop}

routes = jl(OUT / 'SEALED_ROUTES.jsonl')
by = {}
for r in routes: by.setdefault(r['policy'], []).append(r)

def cp95(k, n):
    lo = float(beta.ppf(.025, k, n - k + 1)) if k > 0 else 0.0
    hi = float(beta.ppf(.975, k + 1, n - k)) if k < n else 1.0
    return lo, hi

rng = np.random.default_rng(0)
rows = []
for pol in POLICIES:
    rr = by[pol['key']]
    assert len(rr) == len(pop)
    om = np.array([r['omitted'] for r in rr], bool)
    ch = np.array([r['changed'] for r in rr], int)
    n, k = int(om.sum()), int(ch[om].sum())
    rate = k / n if n else None
    lo, hi = cp95(k, n) if n else (None, None)
    p = float(binom.cdf(k, n, .05)) if n else 1.0
    pol_ok = np.array([r['policy_answer'] == gold[r['id']] for r in rr], int)
    ref_ok = np.array([r['reference_answer'] == gold[r['id']] for r in rr], int)
    idx = rng.integers(0, len(rr), size=(2000, len(rr)))
    diffs = pol_ok[idx].mean(1) - ref_ok[idx].mean(1)
    rows.append({'policy': pol['key'], 'pair': pol['pair'], 'reference': pol['action'], 'q': pol['q'],
                 'threshold': pol['threshold'], 'N': len(rr),
                 'omitted': n, 'changed': k, 'conditional_change_rate': rate,
                 'CP95_lo': lo, 'CP95_hi': hi,
                 'p_value_H0_rho_ge_0.05': p, 'H0_rejected_at_0.05': bool(p <= .05),
                 'always_omit_change_rate': float(ch.mean()),
                 'accuracy_policy': float(pol_ok.mean()), 'accuracy_reference': float(ref_ok.mean()),
                 'accuracy_diff': float(pol_ok.mean() - ref_ok.mean()),
                 'diff_boot95_lo': float(np.quantile(diffs, .025)),
                 'diff_boot95_hi': float(np.quantile(diffs, .975)),
                 'correct_policy': int(pol_ok.sum()), 'correct_reference': int(ref_ok.sum())})

res = {'utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
       'population': 'held-out OBQA questions never used by this study; an earlier project stage scored '
                     'small-pair outputs on them (see PROTOCOL_AMENDMENT_E9B.md)',
       'N': len(pop), 'seal_receipt_utc': rec['utc'], 'seal_verified': True,
       'bootstrap': {'seed': 0, 'resamples': 2000, 'unit': 'question', 'paired': True},
       'test': 'exact binomial, H0: rho >= .05 at the frozen threshold; p = P[Bin(n,.05) <= k]',
       'interval': 'two-sided Clopper-Pearson 95% on k/n',
       'latency_measured': False, 'policies': rows}
Path(OUT / 'E9B_RESULTS.json').write_text(json.dumps(res, indent=2) + '\n')
hdr = '%-22s %7s %7s %9s %-20s %10s %10s %9s %9s %-20s'
print(hdr % ('policy', 'omitted', 'changed', 'rate', 'CP95', 'p', 'always', 'acc_pol', 'acc_ref', 'diff [95%]'))
for r in rows:
    print(hdr % (r['policy'], r['omitted'], r['changed'],
                 '%.4f' % r['conditional_change_rate'] if r['conditional_change_rate'] is not None else 'NA',
                 '[%.4f,%.4f]' % (r['CP95_lo'], r['CP95_hi']),
                 '%.3e' % r['p_value_H0_rho_ge_0.05'], '%.4f' % r['always_omit_change_rate'],
                 '%.4f' % r['accuracy_policy'], '%.4f' % r['accuracy_reference'],
                 '%+.4f [%+.4f,%+.4f]' % (r['accuracy_diff'], r['diff_boot95_lo'], r['diff_boot95_hi'])))
