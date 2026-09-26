"""E7 pre-replay validation with the NEW driver, on 16 OBQA fit questions.  No gold is read.

All four arms are produced by `execute_e7.run_one`, the same function the formal replay calls:
  arm 1 FIXED    -> must equal the saved reference output of that fit row, exactly;
  arm 2 ORIGINAL -> must equal the saved R output when it omits, the saved reference when it keeps;
  arm 3 REUSE    -> frozen mismatch rule: at most 1 of 16 raw outputs may differ from the saved R;
  arm 4 ARGMAX   -> the probe argmax label must equal the saved probe argmax on all 16.
The cached probe of arm 3 must also return the frozen probe's ProbeMax bit-for-bit (freeze S2.2).
"""
import os, sys, json, time
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

KIND = os.environ['E7_KIND']
OUT = Path(sys.argv[1])
import common as C
import execute_e7 as D

ROOT = C.P.parent.parent
BND = ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
MED = ROOT / 'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z'


def jl(p):
    with Path(p).open() as f: return [json.loads(s) for s in f if s.strip()]


fit = C.read(BND / 'splits/obqa_fit_ids.json')[:16]
fitset = set(fit)
queries = {r['id']: r for r in jl(BND / 'inputs/obqa_train_queries.jsonl')}

if KIND == 'large':
    refs = ['T', 'C']
    name = {'R': 'receiver_only', 'T': 'text', 'C': 'c2c'}
    saved = {a: {} for a in ['R', 'T', 'C']}
    for r in jl(ROOT / 'P2_6_20260910T164138Z/results/train_cases.jsonl'):
        if r['id'] in fitset:
            for a, n in name.items():
                if r['action'] == n:
                    saved[a][r['id']] = r['raw_answer']
    saved_probe = {r['id']: r['argmax_probe_label']
                   for r in jl(ROOT / 'P2_ZERO_GOLD_CONTROLS_20260914T065145Z/records/probe_records.jsonl')
                   if r['id'] in fitset}
    receiver = 'Qwen3-8B'
else:
    refs = ['C']
    saved = {a: {} for a in ['R', 'T', 'C']}
    for r in jl(MED / 'actions/obqa_fit.jsonl'):
        if r['id'] in fitset:
            saved[r['action']][r['id']] = r['output']['raw_answer']
    saved_probe = {r['id']: r['argmax_probe_label'] for r in jl(MED / 'probes/obqa_fit.jsonl') if r['id'] in fitset}
    receiver = 'Qwen3-1.7B'

assert all(i in saved['R'] and i in saved_probe and all(i in saved[b] for b in refs) for i in fit)

t = time.perf_counter()
rt = D.Runtime(); D.sync()
load = time.perf_counter() - t
print('VALIDATION_LOAD', KIND, round(load, 1), 's', flush=True)

rows = []
counts = {}
with __import__('torch').inference_mode():
    for b in refs:
        s = D.SETTING % ('obqa', b)
        rec = D.recert[s]
        threshold = D.threshold_for('obqa', b)
        thr_A = rec['threshold_A']
        for i in fit:
            src = queries[i]
            per = {}
            for arm in D.ARMS:
                out = D.run_one(rt, src, 'obqa', b, arm, threshold, thr_A)
                per[arm] = out
            omit = per['original']['omitted']
            omit_A = per['argmax']['omitted']
            want_fixed = saved[b][i]
            want_orig = saved['R'][i] if omit else saved[b][i]
            want_reuse = saved['R'][i] if per['reuse']['omitted'] else saved[b][i]
            row = dict(id=i, reference=b, omitted=omit, omitted_argmax=omit_A,
                       fixed_raw=per['fixed']['raw_answer'], fixed_expected=want_fixed,
                       fixed_match=per['fixed']['raw_answer'] == want_fixed,
                       original_raw=per['original']['raw_answer'], original_expected=want_orig,
                       original_match=per['original']['raw_answer'] == want_orig,
                       reuse_raw=per['reuse']['raw_answer'], reuse_expected=want_reuse,
                       reuse_match=per['reuse']['raw_answer'] == want_reuse,
                       argmax_answer=per['argmax']['raw_answer'] if omit_A else None,
                       saved_probe_argmax=saved_probe[i],
                       argmax_match=((per['argmax']['raw_answer'] == saved_probe[i]) if omit_A else None),
                       ProbeMax_frozen=per['original']['ProbeMax'], ProbeMax_cached=per['reuse']['ProbeMax'],
                       probe_scores_identical=per['original']['ProbeMax'] == per['reuse']['ProbeMax'],
                       probe_ids_sha256_identical=per['original']['probe']['probe_ids_sha256'] ==
                       per['reuse']['probe']['probe_ids_sha256'],
                       route_identical=per['original']['omitted'] == per['reuse']['omitted'])
            rows.append(row)
        sub = [r for r in rows if r['reference'] == b]
        counts[b] = dict(n=len(sub),
                         fixed_mismatches=sum(not r['fixed_match'] for r in sub),
                         original_mismatches=sum(not r['original_match'] for r in sub),
                         reuse_mismatches=sum(not r['reuse_match'] for r in sub),
                         argmax_mismatches=sum(r['argmax_match'] is False for r in sub),
                         argmax_checked=sum(r['argmax_match'] is not None for r in sub),
                         probe_scores_identical_all=all(r['probe_scores_identical'] for r in sub),
                         probe_ids_identical_all=all(r['probe_ids_sha256_identical'] for r in sub),
                         route_identical_all=all(r['route_identical'] for r in sub),
                         omitted=sum(r['omitted'] for r in sub))
        print('VALIDATION', KIND, b, json.dumps(counts[b]), flush=True)

reuse_worst = max(c['reuse_mismatches'] for c in counts.values())
PASS = (all(c['fixed_mismatches'] == 0 and c['original_mismatches'] == 0 and c['argmax_mismatches'] == 0
            and c['probe_scores_identical_all'] and c['probe_ids_identical_all'] and c['route_identical_all']
            for c in counts.values()) and reuse_worst <= 1)
res = dict(kind=KIND, receiver=receiver, n_fit=len(fit), references=refs, per_reference=counts,
           reuse_mismatch_rule='at most 1 of 16 per receiver', reuse_worst_mismatches=reuse_worst,
           PASS=bool(PASS), gold_read=False, load_seconds=load, rows=rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False) + '\n')
print('E7_VALIDATION2', KIND, 'PASS', PASS, flush=True)
