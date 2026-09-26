"""E12-a: per-query latency distribution from existing per-request records (login node, CPU only).

Definitions are the frozen E3/R2 ones, reused unchanged:
  version (a) = all paired panel questions;
  version (b) = drop every question on which EITHER compared arm made its first formal request
                within that replay (each arm's minimum `attempt`)  [e3_metrics.py saving_row / common_r2a.py].
Pairing is by question id (dict keyed by record['id']), never by position in the log.
"omitted" / "routed" use the RECORDED routing decision: omitted <=> selected == 'R'
  (asserted frozen in P2_R2_ANALYSIS.../scripts/e7_analysis.py: omitted == (selected == 'R')).
Quantiles are numpy.percentile defaults (linear interpolation).
Reads every P2_* folder read-only; writes only under P2_R4_E12_<ts>Z/.
"""
import sys
sys.dont_write_bytecode = True
import csv, json, pathlib
import numpy as np

ROOT = pathlib.Path('$DATA_DIR')
OUT = pathlib.Path(__file__).resolve().parents[1]
TS = '20260919T075315Z'
REP = {k: ROOT / f'P2_R1_E3POL_{k}_{TS}' for k in ['REPEAT1', 'REPEAT2', 'REPEAT3']}
FULLF = ROOT / f'P2_R1_E3POL_MMLU_C2C_FULL_{TS}'
FP = ROOT / 'P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z'
ME = ROOT / 'P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z'
MP = ROOT / 'P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z'
E7 = ROOT / 'P2_R2_E7_20260919T231531Z'

# ClusterA E3 version-(b) paired mean saving ranges supplied by the requester (reproduction gate).
GATE = {('large', 'OBQA', 'Text'): (419.6, 430.2), ('large', 'OBQA', 'C2C'): (27.4, 29.3),
        ('large', 'ARC', 'Text'): (573.2, 585.0), ('large', 'ARC', 'C2C'): (91.2, 92.4),
        ('medium', 'OBQA', 'C2C'): (45.6, 50.0), ('medium', 'ARC', 'C2C'): (76.6, 82.5),
        ('large', 'MMLU-Pro', 'Text'): (260.8, 262.7), ('large', 'MMLU-Pro', 'C2C'): (-0.0, 2.8)}


def jl(p):
    with open(p) as f:
        return [json.loads(s) for s in f if s.strip()]


def read(p): return json.loads(pathlib.Path(p).read_text())


def wcsv(name, rows):
    p = OUT / 'results' / name
    p.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(p, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    return p


def om_of(r):
    """Recorded routing decision for one policy/arm record."""
    if 'omitted' in r:
        assert bool(r['omitted']) == (r['selected'] == 'R'), r['key']
        return bool(r['omitted'])
    return r['selected'] == 'R'


# ------------------------------------------------------------------ streams
def streams():
    """(replay, machine, pair, task, reference, arm, ids, fixed{id:rec}, arm{id:rec}, source)."""
    # ---- original ClusterB replays (Appendix B)
    reqs = jl(FP / 'records/e2e_requests.jsonl')
    for ds, task in [('obqa', 'OBQA'), ('arc', 'ARC')]:
        ids = read(FP / f'inputs/{ds}_panel_ids.json')
        for b, ref in [('T', 'Text'), ('C', 'C2C')]:
            fx = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'reference')}
            po = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'policy')}
            yield ('ClusterB', 'ClusterB', 'large', task, ref, 'POLICY', ids, fx, po, FP / 'records/e2e_requests.jsonl')
    reqs = jl(ME / 'records/e2e_requests.jsonl')
    for ds, task in [('obqa', 'OBQA'), ('arc', 'ARC')]:
        ids = read(ME / f'inputs/{ds}_panel_ids.json')
        fx = {r['id']: r for r in reqs if (r['task'], r['arm']) == (ds, 'fixed_C')}
        po = {r['id']: r for r in reqs if (r['task'], r['arm']) == (ds, 'policy_C')}
        yield ('ClusterB', 'ClusterB', 'medium', task, 'C2C', 'POLICY', ids, fx, po, ME / 'records/e2e_requests.jsonl')
    reqs = jl(MP / 'records/four_arm_requests.jsonl')
    ids = np.load(MP / 'protocol/bootstrap_indices.npz')['ids'].tolist()
    for b, ref in [('T', 'Text'), ('C', 'C2C')]:
        fx = {r['id']: r for r in reqs if r['arm'] == f'fixed_{b}'}
        po = {r['id']: r for r in reqs if r['arm'] == f'policy_{b}'}
        yield ('ClusterB', 'ClusterB', 'large', 'MMLU-Pro', ref, 'POLICY', ids, fx, po, MP / 'records/four_arm_requests.jsonl')

    # ---- ClusterA E3 repeats (same 8 policies), streams() of e3_metrics.py
    for rep, F in REP.items():
        reqs = jl(F / 'large/records/e2e_requests.jsonl')
        for ds, task in [('obqa', 'OBQA'), ('arc', 'ARC')]:
            ids = read(F / f'large/inputs/{ds}_panel_ids.json')
            assert ids == read(FP / f'inputs/{ds}_panel_ids.json')
            for b, ref in [('T', 'Text'), ('C', 'C2C')]:
                fx = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'reference')}
                po = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'policy')}
                yield (f'E3_{rep}', 'ClusterA', 'large', task, ref, 'POLICY', ids, fx, po, F / 'large/records/e2e_requests.jsonl')
        reqs = jl(F / 'medium/records/e2e_requests.jsonl')
        for ds, task in [('obqa', 'OBQA'), ('arc', 'ARC')]:
            ids = read(F / f'medium/inputs/{ds}_panel_ids.json')
            fx = {r['id']: r for r in reqs if (r['task'], r['arm']) == (ds, 'fixed_C')}
            po = {r['id']: r for r in reqs if (r['task'], r['arm']) == (ds, 'policy_C')}
            yield (f'E3_{rep}', 'ClusterA', 'medium', task, 'C2C', 'POLICY', ids, fx, po, F / 'medium/records/e2e_requests.jsonl')
        reqs = jl(F / 'mmlu/records/four_arm_requests.jsonl')
        ids = read(F / 'mmlu/inputs/candidate_e2e128_ids.json')
        for b, ref in [('T', 'Text'), ('C', 'C2C')]:
            fx = {r['id']: r for r in reqs if r['arm'] == f'fixed_{b}'}
            po = {r['id']: r for r in reqs if r['arm'] == f'policy_{b}'}
            yield (f'E3_{rep}', 'ClusterA', 'large', 'MMLU-Pro', ref, 'POLICY', ids, fx, po, F / 'mmlu/records/four_arm_requests.jsonl')

    # ---- full development MMLU-Pro C2C replay (2,641 questions)
    reqs = jl(FULLF / 'records/four_arm_requests.jsonl')
    ids = read(FULLF / 'inputs/panel_ids.json')
    fx = {r['id']: r for r in reqs if r['arm'] == 'fixed_C'}
    po = {r['id']: r for r in reqs if r['arm'] == 'policy_C'}
    yield ('E3_MMLU_C2C_FULL', 'ClusterA', 'large', 'MMLU-Pro-FULL', 'C2C', 'POLICY', ids, fx, po,
           FULLF / 'records/four_arm_requests.jsonl')

    # ---- E7 (second hardware configuration): FIXED reference vs ORIGINAL / REUSE / ARGMAX
    recs, PANEL = {}, {}
    for sub, ds_list in [('large', ['obqa', 'arc']), ('medium', ['obqa', 'arc']), ('mmlu', ['mmlu_pro'])]:
        for r in jl(E7 / f'{sub}/records_e7/e7_requests.jsonl'):
            recs[r['setting'], r['id'], r['arm']] = r
        for ds in ds_list:
            key = ('large' if sub != 'medium' else 'medium', ds)
            f = E7 / (f"{sub}/inputs/candidate_e2e128_ids.json" if ds == "mmlu_pro" else f"{sub}/inputs/{ds}_panel_ids.json")
            PANEL[key] = read(f)
    E7POL = [('large', 'OBQA', 'Text', 'large/obqa/T', 'obqa'), ('large', 'OBQA', 'C2C', 'large/obqa/C', 'obqa'),
             ('large', 'ARC', 'Text', 'large/arc/T', 'arc'), ('large', 'ARC', 'C2C', 'large/arc/C', 'arc'),
             ('medium', 'OBQA', 'C2C', 'medium/obqa/C', 'obqa'), ('medium', 'ARC', 'C2C', 'medium/arc/C', 'arc'),
             ('large', 'MMLU-Pro', 'Text', 'large/mmlu_pro/T', 'mmlu_pro'), ('large', 'MMLU-Pro', 'C2C', 'large/mmlu_pro/C', 'mmlu_pro')]
    for pair, task, ref, setting, ds in E7POL:
        ids = PANEL[('large' if pair == 'large' else 'medium'), ds]
        fx = {i: recs[setting, i, 'fixed'] for i in ids}
        for arm in ['original', 'reuse', 'argmax']:
            ar = {i: recs[setting, i, arm] for i in ids}
            yield ('E7', 'ClusterA-E7', pair, task, ref, arm.upper(), ids, fx, ar, E7 / 'various/records_e7/e7_requests.jsonl')

    # ---- E6 Text+fact replay
    rows = jl(E7 / 'e6replay/records_e6/e6_replay_requests.jsonl')
    ids = read(E7 / 'e6replay/inputs/obqa_panel_ids.json')
    rec = {(r['id'], r['arm']): r for r in rows}
    yield ('E6_REPLAY', 'ClusterA-E7', 'large', 'OBQA', 'Text+fact', 'POLICY', ids,
           {i: rec[i, 'fixed_TF'] for i in ids}, {i: rec[i, 'policy_TF'] for i in ids},
           E7 / 'e6replay/records_e6/e6_replay_requests.jsonl')


# ------------------------------------------------------------------ metrics
def q(v, p): return float(np.percentile(np.asarray(v, float), p))


def group_block(pol, fix, prefix):
    d = np.asarray(fix, float) - np.asarray(pol, float)
    if len(d) == 0:
        return {f'{prefix}n': 0}
    return {f'{prefix}n': len(d),
            f'{prefix}pol_p50': q(pol, 50), f'{prefix}pol_p90': q(pol, 90), f'{prefix}pol_p99': q(pol, 99),
            f'{prefix}fix_p50': q(fix, 50), f'{prefix}fix_p90': q(fix, 90), f'{prefix}fix_p99': q(fix, 99),
            f'{prefix}d_p10': q(d, 10), f'{prefix}d_p50': q(d, 50), f'{prefix}d_p90': q(d, 90),
            f'{prefix}frac_slower': float(np.mean(d < 0)), f'{prefix}mean_saving': float(d.mean())}


rows, repro = [], []
for replay, machine, pair, task, ref, arm, ids, fx, ar, src in streams():
    assert set(ids) <= set(fx) and set(ids) <= set(ar), (replay, pair, task, ref, arm)
    assert len(ids) == len(set(ids))
    ff = min((fx[i] for i in ids), key=lambda r: r['attempt'])
    af = min((ar[i] for i in ids), key=lambda r: r['attempt'])
    excl = {ff['id'], af['id']}
    for ver, keep in [('a', list(ids)), ('b', [i for i in ids if i not in excl])]:
        om = [i for i in keep if om_of(ar[i])]
        ro = [i for i in keep if not om_of(ar[i])]
        row = dict(replay=replay, machine=machine, pair=pair, task=task, reference=ref, arm=arm, version=ver,
                   N=len(keep), n_omitted=len(om), n_routed=len(ro),
                   b_excluded_ids=('' if ver == 'a' else ';'.join(sorted(excl))))
        for tag, sub in [('all_', keep), ('om_', om), ('rt_', ro)]:
            row.update(group_block([ar[i]['latency_ms'] for i in sub], [fx[i]['latency_ms'] for i in sub], tag))
        row['pol_p90_worse'] = bool(row.get('all_pol_p90', 0) > row.get('all_fix_p90', 0))
        row['pol_p99_worse'] = bool(row.get('all_pol_p99', 0) > row.get('all_fix_p99', 0))
        row['source'] = str(src)
        rows.append(row)
        if arm == 'POLICY':
            repro.append(dict(replay=replay, machine=machine, pair=pair, task=task, reference=ref, version=ver,
                              N=len(keep), mean_saving_ms=row['all_mean_saving'], median_saving_ms=row['all_d_p50']))

wcsv('E12A_per_arm_quantiles.csv', rows)
wcsv('E12A_reproduction.csv', repro)

# ---- reproduction gate: ClusterA E3 version-(b) means must land inside the supplied ranges
gate_rows, fails = [], []
for p, (lo, hi) in GATE.items():
    vals = [r for r in repro if r['replay'].startswith('E3_REPEAT') and r['version'] == 'b'
            and (r['pair'], r['task'], r['reference']) == p]
    assert len(vals) == 3, (p, len(vals))
    mn, mx = min(v['mean_saving_ms'] for v in vals), max(v['mean_saving_ms'] for v in vals)
    ok = all(lo - 0.05 <= v['mean_saving_ms'] <= hi + 0.05 for v in vals)
    gate_rows.append(dict(pair=p[0], task=p[1], reference=p[2], expected_low=lo, expected_high=hi,
                          repeat1=round(vals[0]['mean_saving_ms'], 2), repeat2=round(vals[1]['mean_saving_ms'], 2),
                          repeat3=round(vals[2]['mean_saving_ms'], 2),
                          observed_min=round(mn, 2), observed_max=round(mx, 2), in_range=ok))
    if not ok:
        fails.append(f'{"/".join(p)}: observed [{mn:.2f}, {mx:.2f}] vs expected [{lo}, {hi}]')
wcsv('E12A_reproduction_gate.csv', gate_rows)
json.dump(dict(reproduction_pass=not fails, failures=fails,
               n_rows=len(rows), n_streams=len(rows) // 2),
          open(OUT / 'results' / 'E12A_CHECKS.json', 'w'), indent=2)
print('REPRODUCTION', 'PASS' if not fails else 'FAIL', fails)
print('streams', len(rows) // 2, 'rows', len(rows))
