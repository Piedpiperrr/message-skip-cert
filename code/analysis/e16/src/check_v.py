"""E16 verification checks on driver outputs (no gold). Exit 0 = PASS, 1 = FAIL/STOP. -> results/verification/<name>.json
  v1   <out> : Llama outputs vs the stored X3 records (results/runs/chain_*.jsonl): R raw, T raw, ProbeMax, p_labels, probe ids (byte-identical)
  v3a  <out> : Qwen3-1.7B outputs with the medium helper's own messages vs the stored medium records (MEDIUM actions/probes obqa_fit): R raw, T raw, ProbeMax, probe ids
  smoke <out> <name> : INVALID per population and action (R, T); STOP if > 2/16 for any, or any runtime error"""
import sys
sys.dont_write_bytecode = True
import glob, collections
from xfam_common import *
mode, out = sys.argv[1], jl(sys.argv[2]); name = sys.argv[3] if len(sys.argv) > 3 else mode
V = X / 'results/verification'; V.mkdir(parents=True, exist_ok=True)
if mode in ('v1', 'v3a'):
    if mode == 'v1':
        st = {(r['dataset'], r['id']): r for f in sorted(glob.glob(str(X3 / 'results/runs/chain_*.jsonl'))) for r in jl(f)}
        ref = lambda o: st[(o['dataset'], o['id'])]
        get = lambda s: dict(R=s['R']['raw'], T=s['T']['raw'], u=s['P']['ProbeMax'], p=s['P']['p_labels'], ids=s['P']['probe_ids_sha256'])
    else:
        A = {(r['id'], r['action']): r for r in jl(MED / 'actions/obqa_fit.jsonl')}; P = {r['id']: r for r in jl(MED / 'probes/obqa_fit.jsonl')}
        ref = lambda o: o['id']
        get = lambda i: dict(R=A[(i, 'R')]['output']['raw_answer'], T=A[(i, 'T')]['output']['raw_answer'], u=P[i]['ProbeMax'], p=P[i]['p_labels'], ids=P[i]['probe_ids_sha256'])
    rows = []
    for o in out:
        ok = o['runtime_error'] is None; s = get(ref(o))
        c = dict(dataset=o['dataset'], id=o['id'], runtime_ok=ok, R_raw_equal=ok and o['R']['raw'] == s['R'], T_raw_equal=ok and o['T']['raw'] == s['T'],
                 u_equal=ok and o['P']['ProbeMax'] == s['u'], p_labels_equal=ok and o['P']['p_labels'] == s['p'], probe_ids_equal=ok and o['P']['probe_ids_sha256'] == s['ids'])
        c['all_equal'] = all(v for k, v in c.items() if k not in ('dataset', 'id')); rows.append(c)
    verdict = 'PASS' if len(rows) == 16 and all(c['all_equal'] for c in rows) else 'FAIL'
    save(V / f'{name}.json', dict(utc=utc(), verdict=verdict, n=len(rows), counts={k: sum(c[k] for c in rows) for k in rows[0] if k not in ('dataset', 'id')}, rows=rows))
else:
    by = collections.defaultdict(lambda: dict(n=0, R_INVALID=0, T_INVALID=0, runtime_errors=0))
    for o in out:
        b = by[o['split']]; b['n'] += 1
        if o['runtime_error']: b['runtime_errors'] += 1; b['R_INVALID'] += 1; b['T_INVALID'] += 1; continue
        b['R_INVALID'] += o['R']['parsed'] == 'INVALID'; b['T_INVALID'] += o['T']['parsed'] == 'INVALID'
    bad = [k for k, b in by.items() if b['runtime_errors']]; inv = [k for k, b in by.items() if b['R_INVALID'] > 2 or b['T_INVALID'] > 2]
    verdict = 'STOP_BUG' if bad else ('STOP_INVALID' if inv else 'PASS')
    save(V / f'{name}.json', dict(utc=utc(), verdict=verdict, per_population=dict(by)))
print(name, verdict, flush=True)
sys.exit(0 if verdict == 'PASS' else 1)
