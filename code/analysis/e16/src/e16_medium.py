"""E16-2 driver: medium pair (Qwen2.5-1.5B-Instruct helper -> Qwen3-1.7B receiver, medium C2C fuser) through the MEDIUM stage-1 Runtime
(execution_retry1 src/native_runtime.py, imported read-only; two GPUs: helper cuda:0, receiver + fuser cuda:1). Per row: R = rt.action(q,'R'),
C = rt.action(q,'C'), P = rt.probe(q), exactly as the stage-1 execute.py calls them. Gold is never read.
One process, in order: V2 (16 stored medium ARC fit rows: R raw, C raw, ProbeMax, probe ids; exit 3 on any difference), V5 smoke (16 ARC test
rows: exit 4 if INVALID > 2/16 for R or for C), production (all ARC test rows).
usage: e16_medium.py --v2 <jsonl> --smoke <jsonl> --rows <jsonl> --outdir <dir>"""
import sys
sys.dont_write_bytecode = True
import argparse, json, os, pathlib, hashlib, traceback, datetime
X = pathlib.Path(__file__).resolve().parents[1]
ROOT = X.parent; MED = ROOT / 'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z'
sys.path.insert(0, str(MED / 'src'))
import native_runtime as mnr
ap = argparse.ArgumentParser(); ap.add_argument('--v2'); ap.add_argument('--smoke'); ap.add_argument('--rows'); ap.add_argument('--outdir'); a = ap.parse_args()
O = pathlib.Path(a.outdir); O.mkdir(parents=True, exist_ok=True)
jl = lambda p: [json.loads(l) for l in open(p) if l.strip()]
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()


def append(p, v):
    with open(p, 'a') as f: f.write(json.dumps(v, ensure_ascii=False) + '\n'); f.flush(); os.fsync(f.fileno())


def run(rows, out):
    assert not pathlib.Path(out).exists()
    res = []
    for r in rows:
        mnr.stop_check()
        rec = dict(id=r['id'], utc=utc(), runtime_error=None)
        try:
            for act in ['R', 'C']:
                x = rt.action(r['query'], act)
                rec[act] = dict(raw=x['output']['raw_answer'], generated_token_ids=x['output']['generated_token_ids'], answer=x['answer'], invalid=x['invalid'],
                                parse_reason=x['parsed'].get('reason'), latency_ms=x['latency_ms'])
            p = rt.probe(r['query']); p.pop('probe_ids', None); rec['P'] = p
        except Exception:
            rec['runtime_error'] = traceback.format_exc(); print('RUNTIME_ERROR', r['id'], flush=True)
        append(out, rec); res.append(rec)
    return res


rt = mnr.Runtime()
json.dump(dict(utc=utc(), load_seconds=rt.load_times, job=os.environ.get('PBS_JOBID'), host=os.uname().nodename), open(O / 'medium_env.json', 'w'), indent=1)
# ---- V2
stA = {(r['id'], r['action']): r for r in jl(MED / 'actions/arc_fit.jsonl')}; stP = {r['id']: r for r in jl(MED / 'probes/arc_fit.jsonl')}
v = run(jl(a.v2), O / 'v2_medium_arcfit.jsonl'); rows = []
for r in v:
    ok = r['runtime_error'] is None
    c = dict(id=r['id'], runtime_ok=ok, R_raw_equal=ok and r['R']['raw'] == stA[(r['id'], 'R')]['output']['raw_answer'],
             C_raw_equal=ok and r['C']['raw'] == stA[(r['id'], 'C')]['output']['raw_answer'],
             ProbeMax_equal=ok and r['P']['ProbeMax'] == stP[r['id']]['ProbeMax'], probe_ids_equal=ok and r['P']['probe_ids_sha256'] == stP[r['id']]['probe_ids_sha256'])
    c['all_equal'] = all(c[k] for k in ['runtime_ok', 'R_raw_equal', 'C_raw_equal', 'ProbeMax_equal', 'probe_ids_equal']); rows.append(c)
V2 = dict(utc=utc(), verdict='PASS' if len(rows) == 16 and all(c['all_equal'] for c in rows) else 'FAIL', rows=rows)
json.dump(V2, open(O / 'V2.json', 'w'), indent=1); print('V2', V2['verdict'], sum(c['all_equal'] for c in rows), '/', len(rows), flush=True)
if V2['verdict'] != 'PASS': sys.exit(3)
# ---- V5 smoke (ARC test, no gold)
s = run(jl(a.smoke), O / 'v5_medium_smoke.jsonl')
err = sum(r['runtime_error'] is not None for r in s); invR = sum(r['runtime_error'] is None and r['R']['invalid'] for r in s) + err; invC = sum(r['runtime_error'] is None and r['C']['invalid'] for r in s) + err
V5 = dict(utc=utc(), n=len(s), INVALID_R=invR, INVALID_C=invC, runtime_errors=err, verdict='PASS' if invR <= 2 and invC <= 2 and err == 0 else ('STOP_INVALID' if err == 0 else 'STOP_BUG'))
json.dump(V5, open(O / 'V5_medium.json', 'w'), indent=1); print('V5_MEDIUM', V5, flush=True)
if V5['verdict'] != 'PASS': sys.exit(4)
# ---- production
p = run(jl(a.rows), O / 'e16_2_medium_arc_test.jsonl')
print('DONE', len(p), 'runtime_errors', sum(r['runtime_error'] is not None for r in p), utc(), flush=True)
