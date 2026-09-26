"""E16-4 gate (inside Job C, before the replay): the modified E3 driver (replay_llama/src/native_adapter.py Runtime: Qwen2.5-7B helper on cuda:0,
Llama-3.1-8B receiver on cuda:1) reproduces 16 stored X3 rows byte-identically: R output, u (and probe ids) and Text output, on the first 8 OBQA
and first 8 ARC panel ids (X3 dev records). The Text request runs as in the replay (live helper generation); whether the live helper message
equals the stored Qwen2.5-7B message is recorded. Exit 0 = PASS (replay may run), 3 = FAIL (replay not run). Gold is not read."""
import sys
sys.dont_write_bytecode = True
import os, json, glob, pathlib, datetime, traceback
E = pathlib.Path(__file__).resolve().parents[1]; ROOT = E.parent; X3 = ROOT / 'P2_R6_X3_20260921T052602Z'; STAGE = E / 'replay_llama'
jl = lambda p: [json.loads(l) for l in open(p) if l.strip()]
st = {(r['dataset'], r['id']): r for f in sorted(glob.glob(str(X3 / 'results/runs/chain_*.jsonl'))) for r in jl(f)}
msg = {(r['dataset'], r['id']): r['helper_message'] for f in glob.glob(str(X3 / 'records/populations/*_dev.jsonl')) for r in jl(f)}
os.environ['PBS_JOBID'] = os.environ.get('PBS_JOBID', 'none') + '_E164_CHECK'   # separate model-load evidence file
sys.path.insert(0, str(STAGE / 'src'))
from native_adapter import Runtime
rt = Runtime(); rows = []
for ds in ['obqa', 'arc']:
    for q in jl(STAGE / f'inputs/{ds}_queries.jsonl')[:8]:
        i = q['id']; s = st[(ds, i)]; qq = {k: q[k] for k in ['question_stem', 'choice_labels', 'choice_text']}; c = dict(dataset=ds, id=i)
        try:
            u, meta = rt.probe(qq); r = rt.action(qq, 'R'); t = rt.action(qq, 'T')
            c.update(u_equal=u == s['P']['ProbeMax'], probe_ids_equal=meta['probe_ids_sha256'] == s['P']['probe_ids_sha256'], R_equal=r['raw_answer'] == s['R']['raw'],
                     T_equal=t['raw_answer'] == s['T']['raw'], live_helper_message_equals_stored=t['helper_message'] == msg[(ds, i)], runtime_ok=True)
        except Exception:
            c.update(runtime_ok=False, error=traceback.format_exc())
        c['all_equal'] = c['runtime_ok'] and all(c[k] for k in ['u_equal', 'probe_ids_equal', 'R_equal', 'T_equal']); rows.append(c)
verdict = 'PASS' if len(rows) == 16 and all(c['all_equal'] for c in rows) else 'FAIL'
out = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), verdict=verdict, n=len(rows),
           counts={k: sum(bool(c.get(k)) for c in rows) for k in ['runtime_ok', 'u_equal', 'probe_ids_equal', 'R_equal', 'T_equal', 'live_helper_message_equals_stored', 'all_equal']}, rows=rows)
(E / 'results/e16_4').mkdir(parents=True, exist_ok=True)
json.dump(out, open(E / 'results/e16_4/CHECK_16ROWS.json', 'w'), indent=1)
print('E164_CHECK', verdict, out['counts'], flush=True)
sys.exit(0 if verdict == 'PASS' else 3)
