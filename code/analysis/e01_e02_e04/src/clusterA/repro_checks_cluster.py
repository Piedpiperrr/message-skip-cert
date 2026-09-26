"""R1 ClusterA reproduction checks (CPU, login node). Reads records read-only; writes results/repro_*.csv.

Runs after results/OUTPUT_HASHES.json exists (hash-before-gold); first re-verifies that every hashed output file is unchanged.
PASS criteria (fixed before any result was looked at):
 (a) per E4 population: V0 correct == paper Table 1 R  AND  V0-vs-saved-R parsed-answer agreement == N/N (INVALID as a symbol).
     Raw-output exact matches are reported, not part of the criterion.
 (b) per action (R, C2C), large ARC dev (299): ClusterA correct == Table 1 (R 268, C2C 266)  AND  parsed agreement == 299/299.
 (c) large/OBQA dev (742): max |dp| of the historical D model (P2_RISK_CALIBRATION_BINARY models/disagreement.joblib)
     <= 1e-3  AND  0 routing decisions change at its deployed threshold (q=.30, t=0.08307916184658852, route if p <= t).
     max |dz| over the 742 x 8192 feature entries is reported.
Parser: frozen P2_SCORING_V2 parse_answer (via common_r1.parser()).
"""
import sys
sys.dont_write_bytecode = True
import csv, json, pathlib, collections
import numpy as np
SRC = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC))
from common_r1 import *

RES = NEW / 'results'
BIN = ROOT / 'P2_RISK_CALIBRATION_BINARY_20260914T043954Z'
V2L = ROOT / 'P2_SCORING_V2_20260912T191445Z/labels/full_development_P2_SCORING_V2.jsonl'
MMLU_GOLD = ROOT / 'P2_MMLU_PRO_BREADTH_PROTOCOL_AND_COST_REVIEW_20260915T224801Z/dataset/test-00000-of-00001.parquet'
TABLE1_R = {('small', 'obqa'): 285, ('small', 'arc'): 110, ('medium', 'obqa'): 490, ('medium', 'arc'): 217,
            ('large', 'obqa'): 617, ('large', 'arc'): 268, ('large', 'mmlu_pro'): 1282}
TABLE1_ARC = {'R': 268, 'C': 266}
parse = parser()

# ---- 0. hashed outputs unchanged
H = json.loads((RES / 'OUTPUT_HASHES.json').read_text())['files']
changed = [k for k, v in H.items() if isinstance(v, str) and sha(NEW / k) != v]
assert not changed, changed
print('OUTPUT_HASHES re-verified:', sum(isinstance(v, str) for v in H.values()), 'files unchanged', flush=True)


def v2(raw, legal):
    p = parse(raw if isinstance(raw, str) else '', legal)
    return p['answer'] if p['valid'] else INV


def wcsv(name, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(RES / name, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


# gold (as in analyze_r1.py)
import pyarrow.parquet as pq
GOLD = {}
for ds, fn in [('obqa', 'obqa_dev.jsonl'), ('arc', 'arc_validation.jsonl')]:
    for r in jl(P210 / 'data' / fn):
        GOLD[(ds, r['id'])] = r['gold_answer']
for r in pq.read_table(MMLU_GOLD, columns=['question_id', 'answer']).to_pylist():
    GOLD[('mmlu_pro', 'test:' + str(r['question_id']))] = r['answer']

v2lab = {(r['pair'], r['dataset'], r['id']): r for r in jl(V2L)}
_lines, _idx = {}, {}


def rawline(path, line):
    if path not in _lines:
        with open(path) as f:
            _lines[path] = f.read().split('\n')
    return json.loads(_lines[path][line - 1])


def saved_raw(pair, ds, rid, act, rsrc):
    """Paper's saved ClusterB development raw output for act in {R, C} (same sources as analyze_r1.saved_action)."""
    if pair in ('small', 'large') and ds in ('obqa', 'arc'):
        s = v2lab[(pair, ds, rid)]['source_' + act]
        x = rawline(s['source_path'], s['source_line'])
        assert x['id'] == rid and x['action'] == {'R': 'receiver_only', 'C': 'c2c'}[act]
        return x['raw_answer'], s['source_path']
    path = pathlib.Path(rsrc['path'])
    if path not in _idx:
        _idx[path] = {(x['id'], x['action']): x for x in jl(path)}
    return _idx[path][(rid, act)]['output']['raw_answer'], str(path)


# ---- (a) E4 V0 vs saved R
rows_a, mism = [], []
for (pair, ds), t1 in TABLE1_R.items():
    pop = jl(POP / f'e4_{pair}_{ds}.jsonl'); N = len(pop)
    V0 = {}
    for f in sorted(RES.glob(f'e4/{pair}_{ds}__V*.jsonl')):
        for x in jl(f):
            if x['variant'] == 'V0':
                assert x['pos'] not in V0; V0[x['pos']] = (x, f.name)
    corr_v0 = corr_r = agree = exact = 0; src_r = set(); src_v = set()
    for r in pop:
        g = GOLD[(ds, r['id'])]; legal = r['legal_labels']
        x, fn = V0[r['pos']]; assert x['id'] == r['id']; src_v.add(fn)
        raw_r, sp = saved_raw(pair, ds, r['id'], 'R', r['R_source']); src_r.add(sp)
        a_v, a_r = v2(x['raw_output'], legal), v2(raw_r, legal)
        corr_v0 += a_v == g; corr_r += a_r == g; agree += a_v == a_r; exact += x['raw_output'] == raw_r
        if a_v != a_r or x['raw_output'] != raw_r:
            mism.append(dict(check='a', pair=pair, population=ds, pos=r['pos'], id=r['id'], gold=g, ClusterA_parsed=a_v, ClusterB_parsed=a_r,
                             parsed_differs=a_v != a_r, ClusterA_raw=x['raw_output'], ClusterB_raw=raw_r))
    ok = corr_v0 == t1 and agree == N
    rows_a.append(dict(check='a', pair=pair, population=ds, N=N, table1_R=t1, ClusterB_saved_R_correct=corr_r, ClusterA_V0_correct=corr_v0,
                       parsed_agreement=agree, raw_exact_match=exact, result='PASS' if ok else 'FAIL',
                       ClusterA_source='results/e4/' + '+'.join(sorted(src_v)), ClusterB_source=';'.join(sorted(src_r))))
    print(rows_a[-1], flush=True)

# ---- (b) E1FIX large ARC dev R and C2C vs saved ClusterB outputs
pop = jl(POP / 'e4_large_arc.jsonl'); byid = {r['id']: r for r in pop}
ours = collections.defaultdict(dict)
for x in jl(RES / 'e1/ours/large__e4_large_arc.jsonl'):
    assert x['id'] not in ours[x['action']]; ours[x['action']][x['id']] = x
rows_b = []
for act in ['R', 'C']:
    corr_p = corr_s = agree = exact = 0; src = set()
    for r in pop:
        g = GOLD[('arc', r['id'])]; legal = r['legal_labels']
        x = ours[act][r['id']]; assert not x.get('runtime_error')
        raw_s, sp = saved_raw('large', 'arc', r['id'], act, r['R_source']); src.add(sp)
        a_p, a_s = v2(x['raw_output'], legal), v2(raw_s, legal)
        corr_p += a_p == g; corr_s += a_s == g; agree += a_p == a_s; exact += x['raw_output'] == raw_s
        if a_p != a_s or x['raw_output'] != raw_s:
            mism.append(dict(check='b', pair='large', population='arc', action=act, id=r['id'], gold=g, ClusterA_parsed=a_p, ClusterB_parsed=a_s,
                             parsed_differs=a_p != a_s, ClusterA_raw=x['raw_output'], ClusterB_raw=raw_s))
    ok = corr_p == TABLE1_ARC[act] and agree == len(pop)
    rows_b.append(dict(check='b', pair='large', population='arc', action='R' if act == 'R' else 'C2C', N=len(pop), table1=TABLE1_ARC[act],
                       ClusterB_saved_correct=corr_s, ClusterA_correct=corr_p, parsed_agreement=agree, raw_exact_match=exact,
                       result='PASS' if ok else 'FAIL', ClusterA_source='results/e1/ours/large__e4_large_arc.jsonl (job 7635393)',
                       ClusterB_source=';'.join(sorted(src))))
    print(rows_b[-1], flush=True)

# ---- (c) E2b large/OBQA dev features vs saved ClusterB features + historical D probabilities
import joblib
dep = json.loads((BIN / 'models/deployment.json').read_text())['D']; q, t = dep['q'], dep['threshold']
hist = joblib.load(BIN / 'models/disagreement.joblib')


def load_dir(d):
    out = {}
    for f in sorted(pathlib.Path(d).glob('*.npz')):
        with np.load(f, allow_pickle=False) as z:
            m = json.loads(str(z['meta'])); assert m['id'] not in out; out[m['id']] = z['z'].copy()
    return out


pol = load_dir(RES / 'e2b/large/features/large_obqa_dev'); sop = load_dir(BIN / 'features/dev')
ids = [r['id'] for r in jl(POP / 'e2b_large_obqa_dev.jsonl')]
assert set(pol) == set(sop) == set(ids) and len(ids) == 742
Xp = np.stack([pol[i] for i in ids]); Xs = np.stack([sop[i] for i in ids])
dz = np.abs(Xp.astype(np.float64) - Xs.astype(np.float64))
pp, ps = hist.predict_proba(Xp)[:, 1], hist.predict_proba(Xs)[:, 1]
dp = np.abs(pp - ps); flips = int(((pp <= t) != (ps <= t)).sum())
ok = float(dp.max()) <= 1e-3 and flips == 0
rows_c = [dict(check='c', pair='large', population='obqa_dev', N=742, dim=Xp.shape[1], max_abs_dz=float(dz.max()), mean_abs_dz=float(dz.mean()),
               n_vectors_bit_identical=int((Xp == Xs).all(axis=1).sum()), max_abs_dp_historical_D=float(dp.max()),
               historical_D_q=q, historical_D_threshold=t, routed_ClusterA=int((pp <= t).sum()), routed_ClusterB=int((ps <= t).sum()),
               routing_decision_flips=flips, result='PASS' if ok else 'FAIL',
               ClusterA_source='results/e2b/large/features/large_obqa_dev (job 7634910)',
               ClusterB_source=str(BIN / 'features/dev') + ' ; model ' + str(BIN / 'models/disagreement.joblib'))]
print(rows_c[0], flush=True)
wcsv('repro_checks_a_e4_V0.csv', rows_a)
wcsv('repro_checks_b_large_arc.csv', rows_b)
wcsv('repro_checks_c_features.csv', rows_c)
wcsv('repro_mismatches.csv', mism if mism else [dict(note='no parsed or raw differences')])
print('DONE', len(mism), 'mismatch rows')
