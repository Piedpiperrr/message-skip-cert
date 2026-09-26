"""E15 (Round 6) CPU re-analysis. Read-only on every existing P2_* folder; writes only under this stage.

Settings, fit/cal/dev arrays and frozen thresholds: the E13 loader (P2_R5_E13_.../scripts/e13_settings.py), which
reuses the E11 loader (e11_common.load) and, through it, the E5/R1 modules. Nothing in those modules is changed.
"""
import sys, json, csv, ast
from fractions import Fraction
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
ROOT = STAGE.parent
RES = STAGE / 'results'
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'P2_R5_E13_20260921T031606Z' / 'scripts'))
import numpy as np  # noqa: E402
from e13_settings import C, load_fit, dis  # noqa: E402

LABEL = 'POST-HOC re-analysis (E15); does not change any primary decision'
SET25 = [s for s in C.ALL26 if s != C.FACT]            # 18 main + 7 cross-family (Text+fact excluded: no fit outputs)
DEPLOY8 = [s for s in SET25 if C.Q0[s] > 0]
GRID = C.GRID
TASKDS = {'OBQA': 'obqa', 'ARC': 'arc', 'MMLU-Pro': 'mmlu_pro'}
CODE = {'Text': 'T', 'C2C': 'C'}

# paper Table 2 savings (ms, original configuration)
TABLE2 = {('large', 'MMLU-Pro', 'Text'): 346.3, ('large', 'MMLU-Pro', 'C2C'): 8.2,
          ('large', 'OBQA', 'Text'): 517.1, ('large', 'OBQA', 'C2C'): 36.6,
          ('large', 'ARC', 'Text'): 717.6, ('large', 'ARC', 'C2C'): 110.9,
          ('medium', 'OBQA', 'C2C'): 79.7, ('medium', 'ARC', 'C2C'): 100.7}

BND = ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
V2 = ROOT / 'P2_SCORING_V2_20260912T191445Z'
MEDX = ROOT / 'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z'
MMLU1 = ROOT / 'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z'
FP = ROOT / 'P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z'
ME = ROOT / 'P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z'
MP = ROOT / 'P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z'
REP = {k: ROOT / f'P2_R1_E3POL_{k}_20260919T075315Z' for k in ['REPEAT1', 'REPEAT2', 'REPEAT3']}
E7 = ROOT / 'P2_R2_E7_20260919T231531Z'
AUDIT_T2 = ROOT / 'P2_FOCUSED_REVISION_ROUND1B_AUDIT_FIX_AND_MANUSCRIPT_20260918T072631Z/audit_v2/outputs/T2_risk_baselines.csv'

READ = []  # every input file read by E15 code (in addition to those read inside the reused loaders)


def jl(p):
    READ.append(str(p))
    with open(p) as f:
        return [json.loads(s) for s in f if s.strip()]


def read(p):
    READ.append(str(p))
    return json.loads(Path(p).read_text())


def csvread(p):
    READ.append(str(p))
    return list(csv.DictReader(open(p)))


def csvout(name, rows):
    RES.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    with open(RES / name, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader(); w.writerows(rows)


def rhu(x):
    """Round half up of a non-negative Fraction -> int."""
    x = Fraction(x)
    return int((x + Fraction(1, 2)).__floor__())


def sname(s): return C.sname(s)


def cover(u, q, t):
    return C.data_r1.route_mask(np.asarray(u, float), q, t)


# ------------------------------------------------------------ component accounting records (Table "Same-target baselines" (ii))
_raw = {}


def _rawline(path, line):
    if path not in _raw:
        READ.append(str(path))
        _raw[path] = open(path).read().split('\n')
    return json.loads(_raw[path][line - 1])


def component_dev(s):
    """Per development question: lat_R, lat_b (historical complete request latency) and probe_ms (component probe cost),
    exactly the per-question inputs of audit_v2.py (P2_FOCUSED_REVISION_ROUND1B.../audit_v2/scripts/audit_v2.py) that
    produce Table 'Same-target baselines' (ii). Returns dict id -> (lat_R, lat_b, probe_ms)."""
    pair, task, ref = s
    ds, b = TASKDS[task], CODE[ref]
    out = {}
    if pair in ('small', 'large') and task != 'MMLU-Pro':
        act = {'R': 'receiver_only', 'T': 'text', 'C': 'c2c'}
        lat = {}
        for r in jl(V2 / 'labels/full_development_P2_SCORING_V2.jsonl'):
            if (r['pair'], r['dataset']) != (pair, ds):
                continue
            for a in ('R', b):
                src = r['source_' + a]
                src = ast.literal_eval(src) if isinstance(src, str) else src
                x = _rawline(src['source_path'], src['source_line'])
                assert x['id'] == r['id'] and x['action'] == act[a]
                lat[r['id'], a] = x['latency_ms']
        probe = {r['id']: r['measured_selective_overhead_ms'] for r in jl(BND / f'records/{pair}_{ds}_{b}_routes.jsonl')}
        ids = {i for i, _ in lat}
        for i in ids:
            out[i] = (lat[i, 'R'], lat[i, b], probe[i])
    elif pair == 'medium':
        A = {(r['id'], r['action']): r['latency_ms'] for r in jl(MEDX / f'actions/{ds}_dev.jsonl')}
        P = {r['id']: r['latency_ms'] for r in jl(MEDX / f'probes/{ds}_dev.jsonl')}
        for i in P:
            out[i] = (A[i, 'R'], A[i, b], P[i])
    else:
        reps = [g['representative_id'] for g in read(MMLU1 / 'splits/dev_groups.json')]
        M = {r['id']: r for r in jl(MMLU1 / 'summary/merged_numeric_rows.jsonl')}
        for i in reps:
            out[i] = (M[i]['R_latency_ms'], M[i][b + '_latency_ms'], M[i]['probe_latency_ms'])
    return out


# ------------------------------------------------------------ original-configuration replays (paper Table 2), paired by id
def original_replay(s):
    """-> (ids in panel order, fixed{id: rec}, policy{id: rec}, source path). Same selection as E12 streams() (ClusterB)."""
    pair, task, ref = s
    ds, b = TASKDS[task], CODE[ref]
    if pair == 'large' and task != 'MMLU-Pro':
        f = FP / 'records/e2e_requests.jsonl'
        reqs = jl(f)
        ids = read(FP / f'inputs/{ds}_panel_ids.json')
        fx = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'reference')}
        po = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'policy')}
    elif pair == 'medium':
        f = ME / 'records/e2e_requests.jsonl'
        reqs = jl(f)
        ids = read(ME / f'inputs/{ds}_panel_ids.json')
        fx = {r['id']: r for r in reqs if (r['task'], r['arm']) == (ds, 'fixed_C')}
        po = {r['id']: r for r in reqs if (r['task'], r['arm']) == (ds, 'policy_C')}
    else:
        f = MP / 'records/four_arm_requests.jsonl'
        reqs = jl(f)
        READ.append(str(MP / 'protocol/bootstrap_indices.npz'))
        ids = np.load(MP / 'protocol/bootstrap_indices.npz')['ids'].tolist()
        fx = {r['id']: r for r in reqs if r['arm'] == f'fixed_{b}'}
        po = {r['id']: r for r in reqs if r['arm'] == f'policy_{b}'}
    assert len(ids) == 128 and set(ids) == set(fx) == set(po)
    return ids, fx, po, f
