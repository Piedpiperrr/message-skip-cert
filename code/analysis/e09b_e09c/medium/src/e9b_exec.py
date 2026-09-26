"""E9B medium pair: probe + R + C2C on the 744 held-out OBQA questions.

The frozen medium runtime (native_runtime.Runtime, a thin wrapper over P2_10 runtime.Runner with the
medium checkpoints) is imported unchanged. No threshold is refitted and no gold is read.
"""
import os, sys, json, time, argparse, traceback
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
P = C.P
sys.path.insert(0, str(P.parent / 'src'))
import e9b_common as E9

ap = argparse.ArgumentParser()
ap.add_argument('--mode', choices=['validate', 'main'], required=True)
ap.add_argument('--actions', required=True)
ap.add_argument('--shard', type=int, default=0)
ap.add_argument('--nshards', type=int, default=1)
ap.add_argument('--out', required=True)
ap.add_argument('--deadline-epoch', type=float, default=float('inf'))
a = ap.parse_args()
ACT = a.actions.split(',')

from native_runtime import Runtime, sync

def run_action(rt, row, act):
    q = {k: row[k] for k in ['question_stem', 'choice_labels', 'choice_text']}
    if act == 'probe':
        return {'action': 'probe', **rt.probe(q)}
    return {'action': act, **rt.action(q, act)}

OUT = Path(a.out); OUT.parent.mkdir(parents=True, exist_ok=True)
start = time.perf_counter(); rt = Runtime(); sync()
print('E9B medium runtime up in %.1f s' % (time.perf_counter() - start), flush=True)

def jdump(p, v):
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

if a.mode == 'validate':
    report = {'pair': 'medium', 'utc': C.utc(), 'job_id': os.environ.get('PBS_JOBID'), 'per_action': {}, 'rows': []}
    qs = {r['id']: r for r in E9.jl(E9.BOUND / 'inputs/obqa_train_queries.jsonl')}
    for act in ACT:
        refs = E9.reference_rows('medium', act, 8)
        mism = 0
        for i, ref in refs:
            row = {'id': i, **{k: list(qs[i][k]) if isinstance(qs[i][k], list) else qs[i][k]
                               for k in ['question_stem', 'choice_labels', 'choice_text']}}
            got = run_action(rt, row, act)
            if act == 'probe':
                ok = (got['ProbeMax'] == ref['ProbeMax'] and got['argmax_probe_label'] == ref['argmax_probe_label']
                      and got['probe_ids_sha256'] == ref['probe_ids_sha256'])
                d = {'id': i, 'action': act, 'ProbeMax': got['ProbeMax'], 'expected_ProbeMax': ref['ProbeMax'],
                     'argmax': got['argmax_probe_label'], 'expected_argmax': ref['argmax_probe_label'],
                     'probe_ids_sha256_match': got['probe_ids_sha256'] == ref['probe_ids_sha256'], 'match': ok}
            else:
                etext, eids = E9.expected_text_and_ids('medium', act, ref)
                graw = got['output']['raw_answer']; gids = got['output']['generated_token_ids']
                ok = (graw == etext and list(gids) == list(eids))
                d = {'id': i, 'action': act, 'raw': graw, 'expected': etext,
                     'token_ids_match': list(gids) == list(eids), 'match': ok}
            mism += (not ok); report['rows'].append(d)
        report['per_action'][act] = {'n': len(refs), 'mismatches': mism}
        print('VALIDATE medium %-5s n=%d mismatches=%d' % (act, len(refs), mism), flush=True)
    report['PASS'] = all(v['mismatches'] == 0 for v in report['per_action'].values())
    report['criterion'] = 'bit-for-bit: raw_answer and generated_token_ids identical; probe ProbeMax, argmax and probe_ids_sha256 identical'
    report['gold_read'] = False
    jdump(OUT, report)
    print('E9B medium VALIDATION PASS =', report['PASS'], flush=True)
    sys.exit(0 if report['PASS'] else 4)

rows = E9.population()
work = [r for j, r in enumerate(rows) if j % a.nshards == a.shard]
# Resume: a row counts as done only when every requested action of it is already on disk.
have = {}
if OUT.exists():
    for line in OUT.open():
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except Exception: continue
        have.setdefault(r['id'], set()).add(r['action'])
skipped_resume = [r['id'] for r in work if have.get(r['id'], set()) >= set(ACT)]
work = [r for r in work if not (have.get(r['id'], set()) >= set(ACT))]
if skipped_resume:
    print('RESUME: %d rows already complete, %d remaining' % (len(skipped_resume), len(work)), flush=True)
done = 0; errors = []
with OUT.open('a') as f:
    for row in work:
        if time.time() > a.deadline_epoch:
            print('DEADLINE reached, stopping cleanly', flush=True); break
        for act in ACT:
            if act in have.get(row['id'], set()):
                continue
            try:
                rec = run_action(rt, row, act)
                rec.pop('probe_ids', None)                      # keep the hash, drop the 100+ ids
                f.write(json.dumps({'id': row['id'], 'pair': 'medium', 'dataset': 'obqa',
                                    'population': 'held_out_744', **rec,
                                    'job_id': os.environ.get('PBS_JOBID'), 'gold_read': False},
                                   ensure_ascii=False) + '\n')
                f.flush()
            except BaseException as e:
                errors.append({'id': row['id'], 'action': act, 'error': repr(e), 'traceback': traceback.format_exc()})
        done += 1
        if done % 50 == 0:
            print('PROGRESS medium shard %d: %d/%d rows' % (a.shard, done, len(work)), flush=True)
jdump(Path(str(OUT) + '.status.json'),
      {'pair': 'medium', 'mode': 'main', 'shard': a.shard, 'nshards': a.nshards, 'actions': ACT,
       'rows_done': done, 'rows_requested': len(work), 'rows_resumed': len(skipped_resume), 'errors': errors,
       'complete': done == len(work) and not errors,
       'job_id': os.environ.get('PBS_JOBID'), 'utc': C.utc(), 'gold_read': False})
print('E9B medium shard %d done %d/%d errors %d' % (a.shard, done, len(work), len(errors)), flush=True)
