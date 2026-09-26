"""E4 null controls: receiver-only action under content-free input changes (no helper, no fuser loaded).

Flavors reproduce the runner that produced each population's paper R action:
  p210   small/large OBQA+ARC: P2_10 runtime + arc_runtime_adapter; receiver loaded exactly as runtime.Runner.__init__
  medium medium OBQA+ARC:      execution_retry1 native_runtime (P2_10 runtime + arc adapter); receiver as Runtime.__init__
  mmlu   large MMLU-Pro:       MMLU stage1 native_runtime (P2_10 runtime + format_mmlu patch); receiver as Runtime.__init__
Variants:
  V1 perm:  runner.request(v1_query, 'receiver_only'); parsed displayed label mapped back to the original label
  V2 irrelevant message: runner.tr.consume(query_i, helper_body(query_i), helper_message of position (i+floor(N/2)) mod N)
  V0 (supplementary, not requested): runner.request(query_i, 'receiver_only') unchanged, same job, run after V1/V2
Parser: frozen P2_SCORING_V2 parse_answer(raw, legal labels). Gold is never read.
"""
import sys
sys.dont_write_bytecode = True
import argparse, hashlib, json, pathlib, time, traceback
from common_r1 import *

ap = argparse.ArgumentParser()
ap.add_argument('--flavor', required=True, choices=['p210', 'medium', 'mmlu'])
ap.add_argument('--pair', required=True, choices=['small', 'medium', 'large'])
ap.add_argument('--datasets', required=True)
ap.add_argument('--variants', required=True)
a = ap.parse_args()
datasets = a.datasets.split(',')
variants = a.variants.split(',')
assert set(variants) <= {'V1', 'V2', 'V0'}
parse = parser()

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
torch.manual_seed(0); torch.cuda.manual_seed_all(0)
torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
assert torch.cuda.is_available() and torch.cuda.device_count() == 1
DEV = 'cuda:0'
t0 = time.perf_counter()
if a.flavor == 'p210':
    assert a.pair in ('small', 'large') and set(datasets) <= {'obqa', 'arc'}
    sys.path.insert(0, str(P210))
    import runtime
    import arc_runtime_adapter  # noqa: F401  (format_openbook -> P2-8 v2 format, as in run_p2_10.py)
    import protocol_min
    cfg = json.loads((P210 / 'frozen_config.json').read_text())
    receipt = json.loads((P210 / 'evidence/freeze_receipt.json').read_text())
    assert sha(P210 / 'frozen_config.json') == receipt['config_sha256']
    for name, h in cfg['execution_source_sha256'].items():
        assert sha(P210 / name) == h, name
    pc = cfg['pair_configs'][a.pair]
    torch.set_num_threads(4)
    spec = pc['models']['receiver']
    tok = AutoTokenizer.from_pretrained(spec['path'], local_files_only=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(spec['path'], local_files_only=True, torch_dtype=torch.bfloat16,
                                                 attn_implementation='sdpa').to(DEV).eval().requires_grad_(False)
    protocol_min.apply_generation_config(model, {'do_sample': False, 'max_new_tokens': 64})
    assert model.generation_config.to_dict() == pc['receiver_generation_config']
    native = runtime
    model_path = spec['path']
else:
    base = MEDX if a.flavor == 'medium' else MMLU
    assert (a.flavor, a.pair) in (('medium', 'medium'), ('mmlu', 'large'))
    assert set(datasets) <= ({'obqa', 'arc'} if a.flavor == 'medium' else {'mmlu_pro'})
    sys.path.insert(0, str(base / 'src'))
    import native_runtime as nr
    native = nr.native
    protocol_min = sys.modules['protocol_min']
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    index = json.loads((base / 'MODEL_SOURCE_INDEX.json').read_text())
    gpath = (MED if a.flavor == 'medium' else MMLU) / 'protocol/generation_configs.json'
    expected = json.loads(gpath.read_text())['model_generation_config_after_native_cleanup']
    loc = (base / 'assets/receiver') if a.flavor == 'medium' else pathlib.Path(index['models']['receiver']['path'])
    tok = AutoTokenizer.from_pretrained(loc, local_files_only=True)
    assert hashlib.sha256(tok.chat_template.encode()).hexdigest() == index['models']['receiver']['chat_template_sha256']
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model, info = AutoModelForCausalLM.from_pretrained(loc, local_files_only=True, torch_dtype=torch.bfloat16,
                                                       attn_implementation='sdpa', output_loading_info=True)
    assert all(not info.get(k) for k in ['missing_keys', 'unexpected_keys', 'mismatched_keys', 'error_msgs']), info
    model = model.to(DEV).eval().requires_grad_(False)
    nr.apply_generation_config(model, {'do_sample': False, 'max_new_tokens': 64})
    assert model.generation_config.to_dict() == expected['receiver']
    model_path = str(loc)
lm = native.lm
runner = native.Runner.__new__(native.Runner)
runner.receiver = model
runner.receiver_tok = tok
runner.tr = lm.T2TReceiverBundle(model, tok)
fmt = lm.format_openbook  # patched prompt builder of this flavor (use_template=False -> helper body)
tag = f'{a.pair}_{a.flavor}_{"-".join(variants)}'
save(NEW / f'results/e4/env_{tag}.json', {**env_record(), 'flavor': a.flavor, 'pair': a.pair, 'datasets': datasets,
     'variants': variants, 'model_path': model_path, 'load_seconds': time.perf_counter() - t0,
     'format_openbook': f'{fmt.__module__}.{fmt.__name__}', 'generation_config': model.generation_config.to_dict()})


def sync():
    torch.cuda.synchronize()


def one(r, variant):
    labels = r['legal_labels']
    rec = {'variant': variant, 'pair': r['pair'], 'dataset': r['dataset'], 'pos': r['pos'], 'id': r['id'], 'utc': utc()}
    sync(); t = time.perf_counter()
    if variant in ('V1', 'V0'):
        q = r['v1_query'] if variant == 'V1' else r['query']
        res = runner.request(q, 'receiver_only')
        raw, ids, n_in = res['raw_answer'], res['generated_token_ids'], res['receiver_input_tokens']
    else:
        q = r['query']
        res = runner.tr.consume(q, fmt(q, use_template=False), r['v2_helper_message'])
        raw, ids, n_in = res['generated_text'], res['generated_token_ids'], res['receiver_input_token_count']
        rec['receiver_prompt_token_ids_sha256'] = hashlib.sha256(json.dumps(res['receiver_prompt_token_ids']).encode()).hexdigest()
        rec['v2_message_pos'] = r['v2_message_pos']; rec['v2_message_id'] = r['v2_message_id']
    sync()
    rec['latency_ms'] = (time.perf_counter() - t) * 1000
    p = parse(raw, labels)
    disp = p['answer'] if p['valid'] else INV
    rec.update(raw_output=raw, generated_token_ids=ids, receiver_input_tokens=n_in, parse_reason=p['reason'],
               parsed_displayed=disp, runtime_error=None)
    rec['parsed_original'] = (r['v1_display_to_original'][disp] if disp != INV else INV) if variant == 'V1' else disp
    return rec


def rendered(r, variant):
    if variant in ('V1', 'V0'):
        q = r['v1_query'] if variant == 'V1' else r['query']
        prompt, text, tensors = protocol_min.receiver_prompt_tensors(tok, q, 'cpu')
        return {'variant': variant, 'pos': r['pos'], 'id': r['id'], 'rendered': text}
    q = r['query']
    msgs = [{'role': 'user', 'content': lm.BACKGROUND_PROMPT.format(question=fmt(q, use_template=False))},
            {'role': 'assistant', 'content': r['v2_helper_message']},
            {'role': 'user', 'content': fmt(q, use_template=True)}]
    return {'variant': variant, 'pos': r['pos'], 'id': r['id'],
            'rendered': tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)}


for ds in datasets:
    rows = jl(POP / f'e4_{a.pair}_{ds}.jsonl')
    out = NEW / f'results/e4/{a.pair}_{ds}__{"-".join(variants)}.jsonl'
    assert not out.exists(), f'refusing to overwrite {out}'
    prompts = []
    print('E4_START', a.pair, ds, variants, len(rows), utc(), flush=True)
    stopped = False
    for r in rows:
        for v in variants:
            if not deadline_ok(60):
                stopped = True
                break
            try:
                rec = one(r, v)
            except Exception:
                rec = {'variant': v, 'pair': r['pair'], 'dataset': r['dataset'], 'pos': r['pos'], 'id': r['id'],
                       'runtime_error': traceback.format_exc(), 'parsed_original': INV, 'raw_output': None}
                print('RUNTIME_ERROR', a.pair, ds, v, r['pos'], flush=True)
            append(out, rec)
            if r['pos'] < 3:
                prompts.append(rendered(r, v))
        if stopped:
            print('DEADLINE_STOP', a.pair, ds, r['pos'], flush=True)
            break
        if (r['pos'] + 1) % 100 == 0:
            print('E4_PROGRESS', a.pair, ds, r['pos'] + 1, utc(), flush=True)
    save(NEW / f'results/e4/prompts_{a.pair}_{ds}__{"-".join(variants)}.json', prompts)
    print('E4_DONE', a.pair, ds, variants, utc(), flush=True)
    if stopped:
        break
