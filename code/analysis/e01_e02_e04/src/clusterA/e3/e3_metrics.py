"""E3 ClusterA metrics (login node, CPU). Rules fixed by the requester before any ClusterA E3 run (see E3_SUMMARY.md).

Latency logic = P2_R1_CPU_20260919T045556Z/src/item5_6.py (the code that produced the ClusterB version-(b) reference classes),
pointed at the E3 records:
 (a) all 128 (or 2,641) paired questions; paired saving = fixed - policy latency (ms); bootstrap = the ORIGINAL replay's saved
     seed-0 indices (asserted == default_rng(0).integers(0,n,(2000,n)) and same ids); percentile 2.5/97.5.
 (b) drop every question on which either arm made its first formal request (each arm's minimum attempt counter within the
     replay); bootstrap default_rng(0).integers(0,n_b,(2000,n_b)) over the remaining questions (as item5 (ii)).
 Class on (b): '+' low > 0, '-' high < 0, '?' otherwise.
(a) is cross-checked against each original analyze.py output (run by run_original_analyses.py).
Integrity counts come from the original analyses' identity outputs; large 'reference-routed vs same-run reference' is
computed from the records (the original large analysis compares the policy to the development records only).
Reads records read-only; writes <E3 folder>/results/e3_*.csv and P2_R1_EXP_20260919T050555Z/results/E3_*.csv.
"""
import sys
sys.dont_write_bytecode = True
import csv, json, math, pathlib, re, datetime, statistics
import numpy as np
ROOT = pathlib.Path('$DATA_DIR')
EXP = ROOT / 'P2_R1_EXP_20260919T050555Z'
TS = '20260919T075315Z'
REP = {k: ROOT / f'P2_R1_E3POL_{k}_{TS}' for k in ['REPEAT1', 'REPEAT2', 'REPEAT3']}
FULLF = ROOT / f'P2_R1_E3POL_MMLU_C2C_FULL_{TS}'
FP = ROOT / 'P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z'
ME = ROOT / 'P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z'
MP = ROOT / 'P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z'
CPU5 = ROOT / 'P2_R1_CPU_20260919T045556Z/results/item5_cold_request_sensitivity.csv'
ClusterB_CLASS = {('large', 'OBQA', 'Text'): '+', ('large', 'OBQA', 'C2C'): '+', ('large', 'ARC', 'Text'): '+', ('large', 'ARC', 'C2C'): '+',
                ('medium', 'OBQA', 'C2C'): '+', ('medium', 'ARC', 'C2C'): '+', ('large', 'MMLU-Pro', 'Text'): '+', ('large', 'MMLU-Pro', 'C2C'): '?'}
POLICIES = list(ClusterB_CLASS)


def jl(p):
    with open(p) as f:
        return [json.loads(s) for s in f if s.strip()]


def read(p): return json.loads(pathlib.Path(p).read_text())
def rcsv(p): return list(csv.DictReader(open(p)))
def ci(boot): return [float(x) for x in np.quantile(boot, [.025, .975])]
def cls(lo, hi): return '+' if lo > 0 else '-' if hi < 0 else '?'


def wcsv(p, rows):
    p = pathlib.Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(p, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def load_idx(path, ids):
    b = np.load(path, allow_pickle=False); assert b['ids'].tolist() == ids
    idx = b['indices']; n = len(ids); assert np.array_equal(idx, np.random.default_rng(0).integers(0, n, size=(2000, n)))
    return idx


def streams(F):
    """Yield (policy, ids, fixed{id:rec}, policy{id:rec}, original index file, records path) for one repeat (as item5 replays())."""
    reqs = jl(F / 'large/records/e2e_requests.jsonl')
    for ds, task in [('obqa', 'OBQA'), ('arc', 'ARC')]:
        ids = read(F / f'large/inputs/{ds}_panel_ids.json'); assert ids == read(FP / f'inputs/{ds}_panel_ids.json')
        for b, ref in [('T', 'Text'), ('C', 'C2C')]:
            fx = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'reference')}
            po = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'policy')}
            yield ('large', task, ref), ids, fx, po, FP / f'summary/{ds}_bootstrap_indices.npz', F / 'large/records/e2e_requests.jsonl'
    reqs = jl(F / 'medium/records/e2e_requests.jsonl')
    for ds, task in [('obqa', 'OBQA'), ('arc', 'ARC')]:
        ids = read(F / f'medium/inputs/{ds}_panel_ids.json'); assert ids == read(ME / f'inputs/{ds}_panel_ids.json')
        fx = {r['id']: r for r in reqs if (r['task'], r['arm']) == (ds, 'fixed_C')}
        po = {r['id']: r for r in reqs if (r['task'], r['arm']) == (ds, 'policy_C')}
        yield ('medium', task, 'C2C'), ids, fx, po, ME / f'summary/{ds}_bootstrap_indices.npz', F / 'medium/records/e2e_requests.jsonl'
    reqs = jl(F / 'mmlu/records/four_arm_requests.jsonl')
    ids = np.load(MP / 'protocol/bootstrap_indices.npz')['ids'].tolist(); assert ids == read(F / 'mmlu/inputs/candidate_e2e128_ids.json')
    for b, ref in [('T', 'Text'), ('C', 'C2C')]:
        fx = {r['id']: r for r in reqs if r['arm'] == f'fixed_{b}'}
        po = {r['id']: r for r in reqs if r['arm'] == f'policy_{b}'}
        yield ('large', 'MMLU-Pro', ref), ids, fx, po, MP / 'protocol/bootstrap_indices.npz', F / 'mmlu/records/four_arm_requests.jsonl'


def cold_flag(r): return bool(r.get('cold_first_request') or r.get('first_formal_request_global'))


def saving_row(policy, ids, fx, po, idx, rpath, repeat):
    assert set(ids) <= set(fx) and set(ids) <= set(po)
    d = np.array([fx[i]['latency_ms'] - po[i]['latency_ms'] for i in ids])
    m1, c1 = float(d.mean()), ci(d[idx].mean(axis=1))
    ff, pf = min(fx.values(), key=lambda r: r['attempt']), min(po.values(), key=lambda r: r['attempt'])
    excl = {ff['id'], pf['id']}; keep = [i for i in ids if i not in excl]
    d2 = np.array([fx[i]['latency_ms'] - po[i]['latency_ms'] for i in keep]); n2 = len(keep)
    idx2 = np.random.default_rng(0).integers(0, n2, size=(2000, n2))
    m2, c2 = float(d2.mean()), ci(d2[idx2].mean(axis=1))
    return dict(repeat=repeat, pair=policy[0], task=policy[1], reference=policy[2], N=len(ids),
                a_mean_ms=m1, a_CI_low=c1[0], a_CI_high=c1[1], a_median_ms=float(np.median(d)),
                b_N=n2, b_excluded_ids=';'.join(sorted(excl)), b_mean_ms=m2, b_CI_low=c2[0], b_CI_high=c2[1], b_median_ms=float(np.median(d2)),
                b_class=cls(*c2), ClusterB_class_b=ClusterB_CLASS[policy],
                fixed_first_id=ff['id'], fixed_first_attempt=ff['attempt'], fixed_first_ms=ff['latency_ms'], fixed_first_global_cold=cold_flag(ff),
                policy_first_id=pf['id'], policy_first_attempt=pf['attempt'], policy_first_ms=pf['latency_ms'], policy_first_global_cold=cold_flag(pf),
                source=str(rpath))


def original_a(F, policy):
    """(mean, low, high) of version (a) as written by the ORIGINAL analyze.py (run through the adapter)."""
    pair, task, ref = policy
    if pair == 'large' and task != 'MMLU-Pro':
        rows = rcsv(F / 'large/results/summary/paired_bootstrap.csv')
        r = next(r for r in rows if r['dataset'] == task.lower() and r['reference'] == ref[0] and r['metric'] == 'net_saving_ms')
        return float(r['mean']), float(r['CI95_low']), float(r['CI95_high'])
    if pair == 'medium':
        r = next(r for r in rcsv(F / 'medium/results/summary/paired_latency_bootstrap.csv') if r['task'] == task.lower() and r['metric'] == 'saving_ms')
        return float(r['mean']), float(r['CI95_low']), float(r['CI95_high'])
    r = next(r for r in rcsv(F / 'mmlu/results/summary/paired_latency_bootstrap.csv') if r['reference'] == ref)
    return float(r['paired_mean_saving_ms']), float(r['CI95_low_ms']), float(r['CI95_high_ms'])


tb = lambda v: str(v) == 'True'
integrity, savings = [], []


def integ(repeat, policy, n_probe_route, n_probe_ok, n_R, n_R_ok, n_ref, n_ref_ok, src):
    integrity.append(dict(repeat=repeat, pair=policy[0], task=policy[1], reference=policy[2],
                          probe_score_and_route_match=f'{n_probe_ok}/{n_probe_route}', R_routed_match_dev_R_raw=f'{n_R_ok}/{n_R}',
                          reference_routed_match_same_run_fixed_raw=f'{n_ref_ok}/{n_ref}', all_match=(n_probe_ok == n_probe_route and n_R_ok == n_R and n_ref_ok == n_ref),
                          source=src))


for rep, F in REP.items():
    rows_f = []
    for policy, ids, fx, po, ipath, rpath in streams(F):
        row = saving_row(policy, ids, fx, po, load_idx(ipath, ids), rpath, rep)
        o = original_a(F, policy)
        row['a_equals_original_analyze'] = all(abs(x - y) < 1e-6 for x, y in zip(o, (row['a_mean_ms'], row['a_CI_low'], row['a_CI_high'])))
        rows_f.append(row); savings.append(row)
        # integrity
        pair, task, ref = policy
        if pair == 'large' and task != 'MMLU-Pro':
            ds, b = task.lower(), ref[0]
            pz = [z for z in jl(F / 'large/results/records/paired_e2e_512.jsonl') if z['dataset'] == ds and z['reference'] == b]
            fid = [all(po[i]['frozen_identity'].values()) for i in ids]
            rr = [z for z in pz if z['route'] == 'R']
            rb = [i for i in ids if po[i]['selected'] == b]
            integ(rep, policy, len(fid), sum(fid), len(rr), sum(z['policy_historical_raw_match'] for z in rr),
                  len(rb), sum(po[i]['output']['raw_answer'] == fx[i]['output']['raw_answer'] for i in rb),
                  'large/records/e2e_requests.jsonl frozen_identity; large/results/records/paired_e2e_512.jsonl; same-run raw from records')
        elif pair == 'medium':
            ic = [r for r in rcsv(F / 'medium/results/summary/output_identity_checks.csv') if r['task'] == task.lower()]
            pr = [tb(r['online_ProbeMax_exactly_matches_Stage1']) and tb(r['online_probe_input_hash_matches_Stage1']) and tb(r['online_route_matches_Stage1']) for r in ic]
            rr = [r for r in ic if r['route'] == 'R']; rc = [r for r in ic if r['route'] == 'C']
            integ(rep, policy, len(pr), sum(pr), len(rr), sum(tb(r['policy_R_vs_Stage1_R_raw_match']) for r in rr),
                  len(rc), sum(tb(r['policy_C_vs_same_round_fixed_C_raw_match']) for r in rc), 'medium/results/summary/output_identity_checks.csv')
        else:
            ic = [r for r in rcsv(F / 'mmlu/results/summary/output_identity_checks.csv') if r['reference'] == ref]
            pr = [tb(r['online_probe_equals_Stage1']) and tb(r['online_probe_input_hash_matches_Stage1']) and tb(r['online_route_matches_Stage1']) for r in ic]
            rr = [r for r in ic if r['route'] == 'R']; rb = [r for r in ic if r['route'] != 'R']
            integ(rep, policy, len(pr), sum(pr), len(rr), sum(tb(r['raw_answer_match']) for r in rr),
                  len(rb), sum(tb(r['raw_answer_match']) for r in rb), 'mmlu/results/summary/output_identity_checks.csv')
    wcsv(F / 'results/e3_policy_savings.csv', rows_f)
    wcsv(F / 'results/e3_integrity.csv', [r for r in integrity if r['repeat'] == rep])

# ---- ClusterB version-(b) reference classes recomputed from P2_R1_CPU item5 (check against the stated classes)
soph = {}
for r in rcsv(CPU5):
    s = (r['pair'], r['task'], r['reference'])
    if s in ClusterB_CLASS:
        soph[s] = dict(mean=float(r['ii_mean_ms']), lo=float(r['ii_CI_low']), hi=float(r['ii_CI_high']), cls=cls(float(r['ii_CI_low']), float(r['ii_CI_high'])))
        assert soph[s]['cls'] == ClusterB_CLASS[s], (s, soph[s])

# ---- classification + verdict
clsrows, mism = [], []
for p in POLICIES:
    row = dict(pair=p[0], task=p[1], reference=p[2], ClusterB_b=f"{ClusterB_CLASS[p]} ({soph[p]['mean']:.1f} [{soph[p]['lo']:.1f}, {soph[p]['hi']:.1f}])")
    for rep in REP:
        s = next(r for r in savings if r['repeat'] == rep and (r['pair'], r['task'], r['reference']) == p)
        row[rep] = s['b_class']
        if s['b_class'] != ClusterB_CLASS[p]:
            mism.append(f"{'/'.join(p)} {rep}: {s['b_class']} (ClusterB {ClusterB_CLASS[p]})")
    clsrows.append(row)
verdict = 'CONSISTENT' if not mism else 'NOT CONSISTENT'

# ---- FULL
rr = jl(FULLF / 'records/four_arm_requests.jsonl')
ids = np.load(FULLF / 'protocol/bootstrap_indices.npz')['ids'].tolist(); assert ids == read(FULLF / 'inputs/panel_ids.json') and len(ids) == 2641
fx = {r['id']: r for r in rr if r['arm'] == 'fixed_C'}; po = {r['id']: r for r in rr if r['arm'] == 'policy_C'}
full = saving_row(('large', 'MMLU-Pro', 'C2C'), ids, fx, po, load_idx(FULLF / 'protocol/bootstrap_indices.npz', ids), FULLF / 'records/four_arm_requests.jsonl', 'MMLU_C2C_FULL')
fo = next(r for r in rcsv(FULLF / 'results/summary/paired_latency_bootstrap.csv') if r['reference'] == 'C2C')
full['a_equals_original_analyze'] = all(abs(float(x) - y) < 1e-6 for x, y in zip((fo['paired_mean_saving_ms'], fo['CI95_low_ms'], fo['CI95_high_ms']), (full['a_mean_ms'], full['a_CI_low'], full['a_CI_high'])))
full['a_class'] = cls(full['a_CI_low'], full['a_CI_high'])
ic = rcsv(FULLF / 'results/summary/output_identity_checks.csv')
pr = [tb(r['online_probe_equals_Stage1']) and tb(r['online_probe_input_hash_matches_Stage1']) and tb(r['online_route_matches_Stage1']) for r in ic]
r_R = [r for r in ic if r['route'] == 'R']; r_C = [r for r in ic if r['route'] != 'R']
integ('MMLU_C2C_FULL', ('large', 'MMLU-Pro', 'C2C'), len(pr), sum(pr), len(r_R), sum(tb(r['raw_answer_match']) for r in r_R),
      len(r_C), sum(tb(r['raw_answer_match']) for r in r_C), 'MMLU_C2C_FULL/results/summary/output_identity_checks.csv')
wcsv(FULLF / 'results/e3_full_saving.csv', [full])
wcsv(FULLF / 'results/e3_integrity.csv', [r for r in integrity if r['repeat'] == 'MMLU_C2C_FULL'])


# ---- REPEAT1 vs REPEAT2 MMLU-Pro replay diagnosis (report only)
def ts(u): return datetime.datetime.fromisoformat(u).timestamp()


def pct(v, q): return float(np.percentile(v, q))


diag, armrows = [], []
for rep in ['REPEAT1', 'REPEAT2', 'REPEAT3']:
    F = REP[rep]; recs = jl(F / 'mmlu/records/four_arm_requests.jsonl')
    log = (F / 'logs/replays.log').read_text()
    st = re.search(r'REPLAY_START mmlu utc=(\S+) .* host=(\S+)', log); en = re.search(r'REPLAY_END mmlu exit=(\d+) utc=(\S+)', log)
    startup = read(F / 'mmlu/evidence/STARTUP.json'); asset = read(F / 'mmlu/evidence/ASSET_HASH_RECHECK.json')
    t = sorted(ts(r['utc']) for r in recs); order = sorted(recs, key=lambda r: r['attempt'])
    gaps = [ts(b['utc']) - ts(a['utc']) - b['latency_ms'] / 1000 for a, b in zip(order, order[1:])]
    lat = [r['latency_ms'] for r in recs]
    diag.append(dict(repeat=rep, host=st.group(2), replay_start=st.group(1), replay_end=en.group(2), replay_exit=en.group(1),
                     replay_wall_min=round((ts(en.group(2).replace('Z', '+00:00')) - ts(st.group(1).replace('Z', '+00:00'))) / 60, 2),
                     startup_total_s=round(startup.get('startup_total_including_runtime_import_seconds', float('nan')), 1),
                     asset_hash_recheck_s=round(asset['wall_seconds'], 1), request_span_min=round((t[-1] - t[0]) / 60, 2),
                     sum_request_latency_min=round(sum(lat) / 60000, 2), n_requests=len(recs),
                     max_gap_between_requests_s=round(max(gaps), 3), gaps_over_1s=sum(g > 1 for g in gaps),
                     source=f'{F.name}/mmlu/records/four_arm_requests.jsonl; logs/replays.log; mmlu/evidence/STARTUP.json, ASSET_HASH_RECHECK.json'))
    for arm in ['fixed_T', 'policy_T', 'fixed_C', 'policy_C']:
        v = [r['latency_ms'] for r in recs if r['arm'] == arm]
        parts = {}
        for k in recs[0]['parts_ms']:
            parts[f'median_{k}'] = round(float(np.median([r['parts_ms'][k] for r in recs if r['arm'] == arm])), 1)
        armrows.append(dict(repeat=rep, arm=arm, N=len(v), median_ms=round(pct(v, 50), 1), p90_ms=round(pct(v, 90), 1), max_ms=round(max(v), 1),
                            mean_ms=round(float(np.mean(v)), 1), **parts))
ratio = []
for arm in ['fixed_T', 'policy_T', 'fixed_C', 'policy_C']:
    a = next(r for r in armrows if r['repeat'] == 'REPEAT1' and r['arm'] == arm); b = next(r for r in armrows if r['repeat'] == 'REPEAT2' and r['arm'] == arm)
    ratio.append(dict(arm=arm, median_ratio_R1_over_R2=round(a['median_ms'] / b['median_ms'], 2), p90_ratio=round(a['p90_ms'] / b['p90_ms'], 2),
                      mean_ratio=round(a['mean_ms'] / b['mean_ms'], 2)))

# ---- hardware (rule 6)
hw = []
for name, F in list(REP.items()) + [('MMLU_C2C_FULL', FULLF)]:
    txt = (F / 'logs/node_hardware.txt').read_text()
    g = lambda pat: (re.search(pat, txt, re.M).group(1).strip() if re.search(pat, txt, re.M) else '')
    topo = re.search(r'^GPU0\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', txt, re.M)
    hw.append(dict(folder=name, host=g(r'host=(\S+)'), job=g(r'PBS_JOBID=(\S+)'), gpu_count=len(re.findall(r'^GPU \d: ', txt, re.M)),
                   gpu_model=g(r'^GPU 0: (.+?) \(UUID'), driver=g(r'Driver Version: (\S+)'), cuda_driver_api=g(r'CUDA Version: (\S+)'),
                   torch=g(r"^__version__ = '([^']+)'"), torch_cuda=g(r"^cuda: Optional\[str\] = '([^']+)'") or g(r"^cuda = '([^']+)'"),
                   topo_GPU0_to_GPU1=topo.group(2) if topo else '', topo_GPU0_row=' '.join(topo.groups()) if topo else '',
                   cpu_model=g(r'^Model name:\s+(.+)$'), cpus=g(r'^CPU\(s\):\s+(\d+)'), sockets=g(r'^Socket\(s\):\s+(\d+)'),
                   cores_per_socket=g(r'^Core\(s\) per socket:\s+(\d+)'), threads_per_core=g(r'^Thread\(s\) per core:\s+(\d+)'),
                   source=f'{F.name}/logs/node_hardware.txt'))

OUT = EXP / 'results'
wcsv(OUT / 'E3_policy_savings.csv', savings)
wcsv(OUT / 'E3_classification.csv', clsrows)
wcsv(OUT / 'E3_full_mmlu_c2c.csv', [full])
wcsv(OUT / 'E3_integrity.csv', integrity)
wcsv(OUT / 'E3_repeat_mmlu_diagnosis.csv', diag)
wcsv(OUT / 'E3_repeat_mmlu_arm_latency.csv', armrows)
wcsv(OUT / 'E3_repeat1_vs_repeat2_ratios.csv', ratio)
wcsv(OUT / 'E3_hardware.csv', hw)
json.dump(dict(verdict=verdict, mismatches=mism, a_equals_original_all=all(r['a_equals_original_analyze'] for r in savings) and full['a_equals_original_analyze']),
          open(OUT / 'E3_verdict.json', 'w'), indent=2)
print('VERDICT', verdict, mism)
print('a==original', all(r['a_equals_original_analyze'] for r in savings), full['a_equals_original_analyze'])
