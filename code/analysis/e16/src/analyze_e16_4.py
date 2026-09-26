"""E16-4 analysis (CPU, login node): Llama-3.1-8B latency replay, E3 protocol (replay_llama/records/e2e_requests.jsonl, Job C).
Paired saving = fixed(reference_T) - policy latency (ms) per panel question, as P2_R1_E3POL.../e3_build/e3_metrics.py saving_row:
 (a) all 128 paired questions; bootstrap default_rng(0).integers(0, n, (2000, n)); percentile 2.5/97.5;
 (b) drop every question on which either arm made its first formal request (each arm's minimum attempt counter); bootstrap
     default_rng(0).integers(0, n_b, (2000, n_b)) over the rest. Class from (b): positive if low > 0, negative if high < 0, else inconclusive.
Also: median saving, share of queries slower (saving < 0), cold requests (the job's first request after model load and each arm's first request),
frozen identity of every policy probe (input hash, FP32 score, route vs X3). -> results/e16_4/E16_4_RESULTS.json, e16_4_savings.csv"""
import sys
sys.dont_write_bytecode = True
import csv
from xfam_common import *
import numpy as np
S = X / 'replay_llama'; O = X / 'results/e16_4'
man = X / 'results/MANIFEST_jobC.sha256'
for line in man.read_text().splitlines():
    if line.strip() and not line.startswith('#'):
        h, p = line.split(None, 1); assert sha(X / p.strip()) == h, p
assert (S / 'REPLAY_COMPLETE.json').exists(), 'replay not complete'
reqs = jl(S / 'records/e2e_requests.jsonl')
ci = lambda b: [float(x) for x in np.quantile(b, [.025, .975])]
cls = lambda lo, hi: 'positive' if lo > 0 else ('negative' if hi < 0 else 'inconclusive')
cold = min(reqs, key=lambda r: r['attempt'])
rows = []
for ds in ['obqa', 'arc']:
    ids = read(S / f'inputs/{ds}_panel_ids.json')
    fx = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, 'T', 'reference')}
    po = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, 'T', 'policy')}
    assert set(ids) == set(fx) == set(po)
    d = np.array([fx[i]['latency_ms'] - po[i]['latency_ms'] for i in ids]); n = len(ids)
    idx = np.random.default_rng(0).integers(0, n, (2000, n)); c1 = ci(d[idx].mean(axis=1))
    ff, pf = min(fx.values(), key=lambda r: r['attempt']), min(po.values(), key=lambda r: r['attempt'])
    excl = {ff['id'], pf['id']}; keep = [i for i in ids if i not in excl]
    d2 = np.array([fx[i]['latency_ms'] - po[i]['latency_ms'] for i in keep]); n2 = len(keep)
    idx2 = np.random.default_rng(0).integers(0, n2, (2000, n2)); c2 = ci(d2[idx2].mean(axis=1))
    ident = [all(po[i]['frozen_identity'].values()) for i in ids]
    rows.append(dict(policy=f'Llama-3.1-8B {ds.upper() if ds == "obqa" else "ARC"}/Text', N=n, a_mean_ms=float(d.mean()), a_CI_low=c1[0], a_CI_high=c1[1], a_median_ms=float(np.median(d)),
                     a_share_slower=float((d < 0).mean()), b_N=n2, b_excluded_ids=';'.join(sorted(excl)), b_mean_ms=float(d2.mean()), b_CI_low=c2[0], b_CI_high=c2[1],
                     b_median_ms=float(np.median(d2)), b_share_slower=float((d2 < 0).mean()), b_class=cls(*c2),
                     policy_omitted=sum(po[i]['selected'] == 'R' for i in ids), frozen_identity_all_true=f'{sum(ident)}/{n}',
                     fixed_first_id=ff['id'], fixed_first_attempt=ff['attempt'], fixed_first_ms=ff['latency_ms'], policy_first_id=pf['id'], policy_first_attempt=pf['attempt'], policy_first_ms=pf['latency_ms'],
                     mean_fixed_ms=float(np.mean([fx[i]['latency_ms'] for i in ids])), mean_policy_ms=float(np.mean([po[i]['latency_ms'] for i in ids]))))
out = dict(utc=utc(), job=read(S / 'REPLAY_COMPLETE.json').get('job_id'), requests=len(reqs),
           cold_first_request=dict(key=cold['key'], attempt=cold['attempt'], latency_ms=cold['latency_ms'], cold_flag=cold.get('cold_first_request')), results=rows)
save(O / 'E16_4_RESULTS.json', out)
with open(O / 'e16_4_savings.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(json.dumps(out, indent=1))
