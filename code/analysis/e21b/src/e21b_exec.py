"""E9B large pair: probe + R + Text + C2C + Text+fact on the 744 held-out OBQA questions.

The frozen runtime is imported unchanged (native_adapter.Runtime, itself a thin wrapper over
P2_10 runtime.Runner). Text+fact is the frozen Text action with the one E6 helper-prompt flag,
copied verbatim from e6replay/src/execute_e6replay.py. No threshold is refitted here and no gold
is read: this step only produces and hashes outputs.
"""
import os, sys, json, time, hashlib, argparse, traceback
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, os.environ['E21B_STAGE'] + '/src')  # E21B: per-slot byte-identical copy of the E9B large stage
import common as C
import torch
P, CFG = C.P, C.CFG
sys.path.insert(0, str(P.parent.parent / 'P2_R3_E9BC_20260920T061042Z/src'))  # E21B: E9B helpers, read-only
import e9b_common as E9
import ast  # E21B: E4 V1 rotation, exec'd from the frozen E4 file (its module body writes files, so no plain import)
_E4 = P.parent.parent / 'P2_R1_EXP_20260919T050555Z/src/prepare_populations.py'
assert C.sha(_E4) == 'f4941cf4f4efd5d7face281c63586b587037d5102b953538269c890c68b1213f'
_V1 = {}; exec(compile(ast.Module([n for n in ast.parse(_E4.read_text()).body if isinstance(n, ast.FunctionDef) and n.name in ('labels', 'rotate')], []), str(_E4), 'exec'), _V1)

ap = argparse.ArgumentParser()
ap.add_argument('--mode', choices=['validate', 'main'], required=True)
ap.add_argument('--actions', required=True)          # comma list of probe,R,T,C,TF
ap.add_argument('--shard', type=int, default=0)
ap.add_argument('--nshards', type=int, default=1)
ap.add_argument('--out', required=True)
ap.add_argument('--deadline-epoch', type=float, default=float('inf'))
ap.add_argument('--population', choices=['arc', 'obqa'], required=True)   # E21B
ap.add_argument('--transform', choices=['v1', 'identity'], required=True)  # E21B: identity = preflight P1
ap.add_argument('--ids', default=None)                                     # E21B: JSON id list (preflight rows)
a = ap.parse_args()
ACT = a.actions.split(',')
TRANSFORM = {'v1': _V1['rotate'], 'identity': lambda q: (dict(q), {l: l for l in q['choice_labels']})}[a.transform]  # E21B

import importlib.util as _iu
_s = _iu.spec_from_file_location('frozen_parser', CFG['parser_path'])
parser = _iu.module_from_spec(_s); _s.loader.exec_module(parser)
assert C.sha(CFG['parser_path']) == CFG['parser_sha256']
from native_adapter import Runtime, sync
import runtime as native            # already in sys.modules via native_adapter
lm = native.lm
import protocol_min

# ---- the one E6 change: a flag on the helper prompt builder, default off (verbatim from e6replay)
_frozen_format_openbook = lm.format_openbook
E6 = {'enabled': False, 'fact': None}
def format_openbook_e6(example, use_template=True):
    out = _frozen_format_openbook(example, use_template=use_template)
    if use_template or not E6['enabled']:
        return out
    assert E6['fact'], 'fact line requested but no fact set'
    return 'Useful fact: ' + E6['fact'] + '\n' + out
lm.format_openbook = format_openbook_e6
protocol_min.format_openbook = format_openbook_e6
# ---------------------------------------------------------------------------------------------

@torch.inference_mode()
def action_text_plus_fact(rt, q, fact):
    E6['enabled'] = False
    frozen_body = _frozen_format_openbook(q, use_template=False)
    E6['enabled'] = True; E6['fact'] = fact
    try:
        message = rt.runner.th.run(q)
    finally:
        E6['enabled'] = False; E6['fact'] = None
    result = rt.runner.tr.consume(q, frozen_body, message['helper_message'])
    return {'raw_answer': result['generated_text'], 'generated_token_ids': result['generated_token_ids'],
            'receiver_input_tokens': result['receiver_input_token_count'],
            'helper_message': message['helper_message'], 'helper_body_with_fact': message['helper_body'],
            'helper_generated_token_ids': message['helper_generated_token_ids'],
            'helper_input_tokens': message['helper_input_token_count'],
            'frozen_receiver_body_sha256': hashlib.sha256(frozen_body.encode()).hexdigest()}

FACTS = E9.facts()
def run_action(rt, row, act):
    q = {k: row[k] for k in ['question_stem', 'choice_labels', 'choice_text']}
    q, back = TRANSFORM(q)  # E21B: rotate option contents before every frozen prompt builder
    rt.begin(); sync(); t0 = time.perf_counter()
    if act == 'probe':
        u, meta = rt.probe(q); sync(); dt = (time.perf_counter() - t0) * 1000
        rt.end()
        return {'action': 'probe', 'latency_ms': dt, **meta, 'back': back, 'choice_text_used': q['choice_text']}  # E21B
    if act == 'TF':
        res = action_text_plus_fact(rt, q, FACTS[row['id']])
    else:
        res = rt.action(q, act)
    sync(); dt = (time.perf_counter() - t0) * 1000
    rt.end()
    p = parser.parse_answer(res['raw_answer'], q['choice_labels'])
    return {'action': act, 'latency_ms': dt, 'raw_answer': res['raw_answer'],
            'generated_token_ids': res['generated_token_ids'],
            'receiver_input_tokens': res.get('receiver_input_tokens'),
            'helper_message': res.get('helper_message'),
            'helper_input_tokens': res.get('helper_input_tokens'),
            'parsed': p, 'answer': p['answer'] if p['valid'] else 'INVALID', 'invalid': not p['valid'],
            'runtime_failure': False,
            'answer_original': back[p['answer']] if p['valid'] else 'INVALID',  # E21B: label of the original option index
            'back': back, 'choice_text_used': q['choice_text'],  # E21B
            'helper_generated_token_ids': res.get('helper_generated_token_ids')}  # E21B: for first-differing-token reports

OUT = Path(a.out); OUT.parent.mkdir(parents=True, exist_ok=True)
start = time.perf_counter(); rt = Runtime(); sync()
print('E9B large runtime up in %.1f s' % (time.perf_counter() - start), flush=True)

if a.mode == 'validate':
    report = {'pair': 'large', 'utc': C.utc(), 'job_id': os.environ.get('PBS_JOBID'), 'per_action': {}, 'rows': []}
    for act in ACT:
        refs = E9.reference_rows('large', act, 8)
        qs = {r['id']: r for r in E9.jl(E9.BOUND / 'inputs/obqa_train_queries.jsonl')}
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
                etext, eids = E9.expected_text_and_ids('large', act, ref)
                ok = (got['raw_answer'] == etext and list(got['generated_token_ids']) == list(eids))
                d = {'id': i, 'action': act, 'raw': got['raw_answer'], 'expected': etext,
                     'token_ids_match': list(got['generated_token_ids']) == list(eids), 'match': ok}
            mism += (not ok); report['rows'].append(d)
        report['per_action'][act] = {'n': len(refs), 'mismatches': mism}
        print('VALIDATE large %-5s n=%d mismatches=%d' % (act, len(refs), mism), flush=True)
    report['PASS'] = all(v['mismatches'] == 0 for v in report['per_action'].values())
    report['criterion'] = 'bit-for-bit: raw_answer and generated_token_ids identical; probe ProbeMax, argmax and probe_ids_sha256 identical'
    report['gold_read'] = False
    C.save(OUT, report)
    print('E9B large VALIDATION PASS =', report['PASS'], flush=True)
    sys.exit(0 if report['PASS'] else 4)

rows = E9.population() if a.population == 'obqa' else E9.jl(P.parent.parent / 'P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/inputs/test_queries_no_gold.jsonl')  # E21B
if a.ids:  # E21B
    keep = set(json.loads(Path(a.ids).read_text())); rows = [r for r in rows if r['id'] in keep]; assert len(rows) == len(keep)
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
                f.write(json.dumps({'id': row['id'], 'pair': 'large', 'dataset': a.population,  # E21B
                                    'population': {'obqa': 'held_out_744', 'arc': 'sealed_arc_1172'}[a.population],
                                    'transform': a.transform, 'utc': C.utc(), **rec,  # E21B
                                    'job_id': os.environ.get('PBS_JOBID'), 'gold_read': False},
                                   ensure_ascii=False) + '\n')
                f.flush()
            except BaseException as e:
                errors.append({'id': row['id'], 'action': act, 'error': repr(e), 'traceback': traceback.format_exc()})
                E6['enabled'] = False; E6['fact'] = None
        done += 1
        if done % 50 == 0:
            print('PROGRESS large shard %d: %d/%d rows' % (a.shard, done, len(work)), flush=True)
C.save(Path(str(OUT) + '.status.json'),
       {'pair': 'large', 'mode': 'main', 'shard': a.shard, 'nshards': a.nshards, 'actions': ACT,
        'rows_done': done, 'rows_requested': len(work), 'rows_resumed': len(skipped_resume), 'errors': errors,
        'complete': done == len(work) and not errors,
        'job_id': os.environ.get('PBS_JOBID'), 'utc': C.utc(), 'gold_read': False})
print('E9B large shard %d done %d/%d errors %d' % (a.shard, done, len(work), len(errors)), flush=True)
