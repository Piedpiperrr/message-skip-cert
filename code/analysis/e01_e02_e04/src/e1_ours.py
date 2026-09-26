"""E1 OURS path: the paper's runtime + C2C port on the official OBQA test split (500), actions R and C2C.

small/large: P2_10 runtime.Runner(frozen pair config) + arc_runtime_adapter, exactly as run_p2_10.py.
medium:      P2_MEDIUM ... execution_retry1 native_runtime.Runtime(), exactly as its execute.py.
Gold is never read. One request per (question, action); no retries; failures are recorded.
"""
import sys
sys.dont_write_bytecode = True
import argparse, json, time, traceback, hashlib
from common_r1 import *

ap = argparse.ArgumentParser()
ap.add_argument('--pair', required=True, choices=['small', 'medium', 'large'])
# R1 E1FIX (DEVIATIONS.md D5): optional ARC dev reproduction population; the default is unchanged
ap.add_argument('--population', default='e1_obqa_test500', choices=['e1_obqa_test500', 'e4_large_arc'])
args = ap.parse_args()
pair = args.pair
TAG = '' if args.population == 'e1_obqa_test500' else f'__{args.population}'
OUT = NEW / f'results/e1/ours/{pair}{TAG}.jsonl'
PROMPTS = NEW / f'results/e1/prompts/ours_{pair}{TAG}.json'
assert not OUT.exists(), f'refusing to overwrite {OUT}'
if TAG:  # E4 large ARC dev rows: the saved query plus its legal labels (large pair only)
    assert pair == 'large'
    rows = [{**r['query'], 'id': r['id'], 'official_index': None, 'legal_labels': r['legal_labels']}
            for r in jl(POP / f'{args.population}.jsonl')]
    assert len(rows) == 299
else:
    rows = jl(POP / 'e1_obqa_test500.jsonl')
    assert len(rows) == 500
parse = parser()
LABELS = ['A', 'B', 'C', 'D']

import torch
if pair in ('small', 'large'):
    sys.path.insert(0, str(P210))
    from threadpoolctl import threadpool_limits
    import runtime
    import arc_runtime_adapter  # noqa: F401  (same import order as run_p2_10.py)
    import protocol_min
    cfg = json.loads((P210 / 'frozen_config.json').read_text())
    receipt = json.loads((P210 / 'evidence/freeze_receipt.json').read_text())
    assert sha(P210 / 'frozen_config.json') == receipt['config_sha256']
    for name, h in cfg['execution_source_sha256'].items():
        assert sha(P210 / name) == h, name
    assert torch.cuda.is_available() and torch.cuda.device_count() == 2
    threadpool_limits(limits=1); torch.set_num_threads(4)
    torch.manual_seed(0); torch.cuda.manual_seed_all(0)
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    t = time.perf_counter()
    runner = runtime.Runner(cfg['pair_configs'][pair])
    load = {'load_times': runner.load_times, 'wall': time.perf_counter() - t, 'fusers': len(runner.cr.projectors),
            'mapping': {str(k): v for k, v in runner.cr.mapping.items()}}
    sync = runtime.sync

    def to_query(r):  # run_p2_10.query_only(row)
        return {k: r[k] for k in ['question_stem', 'choice_labels', 'choice_text', 'choices']}

    def call(q, a):
        res = runner.request(q, {'R': 'receiver_only', 'C': 'c2c'}[a])
        proj = res.pop('_projected', None)
        if proj is not None:
            assert proj.dtype == torch.float32 and torch.isfinite(proj).all().item()
        return res
else:
    sys.path.insert(0, str(MEDX / 'src'))
    import native_runtime as nr
    protocol_min = sys.modules['protocol_min']
    t = time.perf_counter()
    rt = nr.Runtime()
    runner = rt.runner
    load = {'load_times': rt.load_times, 'wall': time.perf_counter() - t, 'fusers': len(runner.cr.projectors)}
    sync = nr.sync

    def to_query(r):  # medium inputs carry exactly {id, question_stem, choice_labels, choice_text}
        return {k: r[k] for k in ['id', 'question_stem', 'choice_labels', 'choice_text']}

    def call(q, a):
        res = runner.request(q, {'R': 'receiver_only', 'C': 'c2c'}[a])
        proj = res.pop('_projected', None)
        if proj is not None:
            assert proj.dtype == torch.float32 and torch.isfinite(proj).all().item()
        return res

tok = runner.receiver_tok
save(NEW / f'results/e1/ours/{pair}{TAG}_environment.json', {**env_record(), 'pair': pair, 'load': load,
     'receiver_generation_config': runner.receiver.generation_config.to_dict()})

captured = {}


def capture(mod, args, kwargs):
    if 'receiver' in captured:
        return
    x = kwargs.get('input_ids', args[0] if args else None)
    if x is not None:
        captured['receiver'] = x.detach().cpu().tolist()


prompts = []
print('E1_OURS_START', pair, utc(), flush=True)
for n, r in enumerate(rows):
    q = to_query(r)
    for a in ['R', 'C']:
        if not deadline_ok(90):
            print('DEADLINE_STOP', pair, n, a, flush=True)
            break
        captured.clear()
        h = runner.receiver.register_forward_pre_hook(capture, with_kwargs=True)
        rec = {'path': 'OURS', 'pair': pair, 'action': a, 'official_index': r['official_index'], 'id': r['id'], 'utc': utc()}
        try:
            sync(); t0 = time.perf_counter()
            res = call(q, a)
            sync(); rec['latency_ms'] = (time.perf_counter() - t0) * 1000
            p = parse(res['raw_answer'], r.get('legal_labels', LABELS))
            rec.update(raw_output=res['raw_answer'], generated_token_ids=res['generated_token_ids'],
                       receiver_input_tokens=res['receiver_input_tokens'], parsed_answer=p['answer'] if p['valid'] else INV,
                       parse_reason=p['reason'], runtime_error=None,
                       receiver_first_input_ids_sha256=hashlib.sha256(json.dumps(captured.get('receiver')).encode()).hexdigest())
        except Exception:
            rec.update(runtime_error=traceback.format_exc(), raw_output=None, parsed_answer=INV)
            print('RUNTIME_ERROR', pair, a, r['official_index'], flush=True)
        finally:
            h.remove()
        if n < 3:
            prompt, rendered, tensors = protocol_min.receiver_prompt_tensors(tok, q, 'cpu')
            prompts.append({'pair': pair, 'action': a, 'official_index': r['official_index'], 'id': r['id'],
                            'user_message': prompt, 'rendered': rendered, 'rendered_input_ids': tensors['input_ids'][0].tolist(),
                            'receiver_first_forward_input_ids': captured.get('receiver')})
        append(OUT, rec)
    else:
        if (n + 1) % 50 == 0:
            print('E1_OURS_PROGRESS', pair, n + 1, utc(), flush=True)
        continue
    break
save(PROMPTS, prompts)
print('E1_OURS_DONE', pair, utc(), flush=True)
