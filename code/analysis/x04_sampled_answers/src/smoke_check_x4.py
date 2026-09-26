"""X4 smoke checks (outputs only; gold never used). (a) greedy X4 code path == stored large-pair greedy R and Text outputs, bit for bit
(results/validation/VALIDATION.json from run_x4.py --mode validate --sampling off); (b) sampled run 1 == sampled run 2 (same seeds) on
R and Text text and token ids; (c) descriptive: sampled R / Text answers (V2 label and raw text) that differ from the stored greedy ones.
Stops: INVALID > 2/16 on either sampled path (STOP_INVALID); mismatch in (a) or (b) (STOP_MISMATCH); runtime error or NaN (STOP_BUG).
-> results/smoke/SMOKE_CHECK_X4.json"""
import sys
sys.dont_write_bytecode = True
import math
from xfam_common import *
S = X / 'results/smoke'; V = read(X / 'results/validation/VALIDATION.json')
r1, r2, g = jl(S / 'sampled_run1.jsonl'), jl(S / 'sampled_run2.jsonl'), jl(X / 'results/validation/validate_greedy.jsonl')
lab = {}
for name in ['full_train', 'full_development']:
    for x in jl(V2L / f'{name}_P2_SCORING_V2.jsonl'):
        if x['pair'] == 'large' and x['dataset'] == 'obqa': lab[x['id']] = x
keys = ['runtime_ok', 'probe_ids_equal', 'ProbeMax_equal', 'p_labels_equal', 'R_raw_equal', 'T_raw_equal', 'R_parsed_equal', 'T_parsed_equal']
a_ok = V['verdict'] == 'PASS' and V['n'] == 16 and all(all(r[k] for k in keys) for r in V['rows'])
err = [(n, r['id']) for n, rr in [('greedy', g), ('run1', r1), ('run2', r2)] for r in rr if r.get('runtime_error')]
nan = [(n, r['id']) for n, rr in [('greedy', g), ('run1', r1), ('run2', r2)] for r in rr if not r.get('runtime_error') and not math.isfinite(r['P']['ProbeMax'])]
b = [dict(id=x['id'], R_equal=x['R']['raw'] == y['R']['raw'] and x['R']['generated_token_ids'] == y['R']['generated_token_ids'],
          T_equal=x['T']['raw'] == y['T']['raw'] and x['T']['generated_token_ids'] == y['T']['generated_token_ids'],
          seeds_equal=(x['R']['seed'], x['T']['seed']) == (y['R']['seed'], y['T']['seed'])) for x, y in zip(r1, r2)] if not err else []
b_ok = len(b) == 16 == len(r1) == len(r2) and all(v['R_equal'] and v['T_equal'] and v['seeds_equal'] for v in b) and [x['id'] for x in r1] == [x['id'] for x in r2]
c = dict(R_label_differs=0, R_raw_differs=0, T_label_differs=0, T_raw_differs=0)
for x in r1:
    if x.get('runtime_error'): continue
    L = lab[x['id']]
    rawR = rawline(L['source_R']['source_path'], L['source_R']['source_line'])['raw_answer']; rawT = rawline(L['source_T']['source_path'], L['source_T']['source_line'])['raw_answer']
    c['R_label_differs'] += x['R']['parsed'] != L['o_R']; c['R_raw_differs'] += x['R']['raw'] != rawR
    c['T_label_differs'] += x['T']['parsed'] != L['o_T']; c['T_raw_differs'] += x['T']['raw'] != rawT
invR = sum(x['R']['parsed'] == 'INVALID' for x in r1 if not x.get('runtime_error')); invT = sum(x['T']['parsed'] == 'INVALID' for x in r1 if not x.get('runtime_error'))
warm = [x for x in r1 if not x['cold_first_after_load'] and not x.get('runtime_error')]
lat = {k: sum(x[k]['latency_ms'] for x in warm) / max(len(warm), 1) for k in 'RTP'}
verdict = 'STOP_BUG' if err or nan else ('STOP_MISMATCH' if not (a_ok and b_ok) else ('STOP_INVALID' if invR > 2 or invT > 2 else 'PASS'))
out = dict(utc=utc(), a_greedy_equals_stored=a_ok, a_counts={k: sum(r[k] for r in V['rows']) for k in keys}, b_rerun_identical=b_ok, b_rows=b,
           c_sampled_vs_stored_greedy=c, INVALID_sampled_R=invR, INVALID_sampled_T=invT, runtime_errors=err, nan=nan,
           warm_mean_latency_ms=lat, warm_sec_per_row=sum(lat.values()) / 1000,
           files={n: sha(p) for n, p in [('sampled_run1', S / 'sampled_run1.jsonl'), ('sampled_run2', S / 'sampled_run2.jsonl'), ('validate_greedy', X / 'results/validation/validate_greedy.jsonl')]},
           verdict=verdict)
save(S / 'SMOKE_CHECK_X4.json', out)
print('SMOKE_X4', verdict, '(a)', a_ok, '(b)', b_ok, '(c)', c, 'INVALID R', invR, 'T', invT, 'errors', len(err), 'nan', len(nan), 'sec/row', round(out['warm_sec_per_row'], 3), flush=True)
