"""E9c feasibility and GPU-hour estimate, derived from recorded probe timings (login node, no GPU).

The estimate uses the measured batch-1 receiver-probe component times of each population as the
per-row proxy for the helper prefill of the same pair; helper and receiver of a pair are of
comparable size (0.5B/0.6B, 1.5B/1.7B, 7B/8B) and the prefill is the identical operation.
This is an estimate from frozen records, not a measurement of the helper.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e9_common import *
import numpy as np

src = open(Path(__file__).with_name('e9c_analyze.py')).read().split('# ---------------- per-setting analysis')[0]
ns = {'__name__': 'loaders', '__file__': str(Path(__file__).with_name('e9c_analyze.py'))}
exec(compile(src.replace('A = ap.parse_args()', 'A = ap.parse_args([])'), 'loaders', 'exec'), ns)

plan = rd(STAGE / 'jobs/LANE_PLAN.json')
rows = []
for pair, ds in POPULATIONS:
    pr = ns['load_probes'](pair, ds); rp = reps(pair, ds)
    t = [pr[s][i]['probe_core_ms'] for s in ['fit', 'cal', 'dev'] for i in rp[s] if 'probe_core_ms' in pr[s].get(i, {})]
    if not t:
        t = [pr[s][i]['latency_ms'] for s in ['fit', 'cal', 'dev'] for i in rp[s] if 'latency_ms' in pr[s].get(i, {})]
    n = sum(len(rp[s]) for s in ['fit', 'cal', 'dev'])
    rows.append({'population': f'{pair}/{ds}', 'rows': n,
                 'recorded_receiver_probe_core_ms_mean': float(np.mean(t)) if t else None,
                 'recorded_receiver_probe_core_ms_median': float(np.median(t)) if t else None,
                 'estimated_lane_seconds': (float(np.mean(t)) * n / 1000.0) if t else None})
lane_s = {}
for l in plan['lanes']:
    s = 0.0
    for tk in l['tasks']:
        k = f"{tk['pair']}/{tk['dataset']}"
        r = next((x for x in rows if x['population'] == k), None)
        if r and r['recorded_receiver_probe_core_ms_mean']:
            s += r['recorded_receiver_probe_core_ms_mean'] * (tk['slice'][1] - tk['slice'][0]) / 1000.0
    lane_s[l['rank']] = s
load = {'small': 30, 'medium': 60, 'large': 120}     # model load + cold import allowance, seconds
wall = {r: v + load[next(l for l in plan['lanes'] if l['rank'] == r)['helper_pair']] + 90 for r, v in lane_s.items()}
crit = max(wall.values())
out = {'utc': utc(), 'populations': rows, 'lane_estimated_seconds': lane_s,
       'lane_estimated_wall_seconds_incl_load_and_import': wall,
       'critical_path_seconds': crit, 'critical_path_minutes': crit / 60.0,
       'walltime_requested_seconds': 3000, 'headroom_factor': 3000.0 / crit if crit else None,
       'node_hours_estimate': crit / 3600.0, 'A100_gpu_hours_estimate': 4 * crit / 3600.0,
       'nodes': 1, 'gpus': 4, 'queue': 'debug',
       'basis': 'recorded batch-1 receiver-probe component times of the same population, used as the '
                'per-row proxy for the helper prefill of the same pair; an estimate, not a helper measurement',
       'feasible_E9C': crit < 3000 * 0.6,
       'E9B': 'not executed; the E9b gate failed (see PROTOCOL_FREEZE_E9B.md section 4). Zero GPU hours.'}
save(STAGE / 'FEASIBILITY.json', out)
for r in rows:
    print('%-18s rows=%6d recorded probe_core mean=%9.2f ms  est lane %8.1f s' % (
        r['population'], r['rows'], r['recorded_receiver_probe_core_ms_mean'] or -1, r['estimated_lane_seconds'] or -1))
print('\nlane wall estimates (s):', {k: round(v) for k, v in wall.items()})
print('critical path %.1f min; requested 50 min; headroom x%.1f' % (crit / 60, 3000 / crit))
print('estimate: %.2f node-hours = %.2f A100 GPU-hours' % (crit / 3600, 4 * crit / 3600))
