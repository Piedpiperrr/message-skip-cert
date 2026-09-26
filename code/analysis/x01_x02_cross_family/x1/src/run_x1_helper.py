"""X1 stage C1: helper Text messages with the paper's helper code (legacy_methods.T2THelperBundle.run, unchanged).
The helper prompt is [user: BACKGROUND_PROMPT(format_openbook(q, use_template=False))] (ARC: P2-8 v2 helper body), rendered
with the helper's own chat template, add_generation_prompt=True, enable_thinking=False; greedy, bf16, sdpa, max_new_tokens 256,
EOS/pad from the checkpoint generation config (after the paper's apply_generation_config, as runtime.Runner loads the helper).
Only X1 change: for the Llama helper, apply_chat_template gets date_string=LLAMA_DATE (fixed) via functools.partial.
Modes: validate (helper Qwen2.5-0.5B = small pair; compare messages with the saved small-pair Text records; exit 3 on any diff),
       smoke/run (helper Llama-3.2-1B). Gold is never read.
usage: run_x1_helper.py --mode {validate,smoke,run} --rows <population rows jsonl> --out <jsonl>"""
import sys
sys.dont_write_bytecode = True
import argparse, functools, time, traceback, hashlib, os
from x1_common import *

ap = argparse.ArgumentParser()
ap.add_argument('--mode', required=True, choices=['validate', 'smoke', 'run'])
ap.add_argument('--rows', required=True); ap.add_argument('--out', required=True)
a = ap.parse_args()
OUT = pathlib.Path(a.out); assert not OUT.exists(), f'refusing to overwrite {OUT}'
rows = jl(a.rows); DEADLINE = float(os.environ.get('XFAM_DEADLINE_EPOCH', 'inf'))
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
torch.manual_seed(0); torch.cuda.manual_seed_all(0)
torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
assert torch.cuda.is_available() and torch.cuda.device_count() == 1
sys.path.insert(0, str(P210))
import runtime, protocol_min, legacy_methods
FMT = {'obqa': protocol_min.format_openbook}
import arc_runtime_adapter  # noqa: F401
FMT['arc'] = protocol_min.format_openbook
spec = SMALL_HELPER if a.mode == 'validate' else LLAMA
t0 = time.perf_counter()
tok = AutoTokenizer.from_pretrained(spec['path'], local_files_only=True)
if tok.pad_token is None: tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(spec['path'], local_files_only=True, torch_dtype=torch.bfloat16, attn_implementation='sdpa').to('cuda:0').eval().requires_grad_(False)
protocol_min.apply_generation_config(model, {'do_sample': False, 'max_new_tokens': 64})   # as runtime.Runner; generate() then passes max_new_tokens=256
if spec is LLAMA:
    tok.apply_chat_template = functools.partial(tok.apply_chat_template, date_string=LLAMA_DATE)
helper = legacy_methods.T2THelperBundle(model, tok)
bos = tok.bos_token_id
save(OUT.with_suffix('.env.json'), dict(utc=utc(), mode=a.mode, helper=spec, load_seconds=time.perf_counter() - t0, generation_config=model.generation_config.to_dict(),
                                        chat_template_sha256=hashlib.sha256(tok.chat_template.encode()).hexdigest(), date_string=LLAMA_DATE if spec is LLAMA else None,
                                        bos_token_id=bos, rows_file=a.rows, rows_sha256=sha(a.rows), job_id=os.environ.get('PBS_JOBID'), host=os.uname().nodename,
                                        gpu=str(torch.cuda.get_device_properties(0))))
first = True
for r in rows:
    if time.time() > DEADLINE - 60:
        print('DEADLINE_STOP', r['dataset'], r['id'], flush=True); break
    ds, q = r['dataset'], r['query']
    protocol_min.format_openbook = FMT[ds]; legacy_methods.format_openbook = FMT[ds]
    rec = dict(dataset=ds, split=r['split'], id=r['id'], representative=r['representative'], helper=spec['repo'], utc=utc(), cold_first_after_load=first, runtime_error=None)
    try:
        torch.cuda.synchronize(); t = time.perf_counter()
        with torch.inference_mode():
            m = helper.run(q)
        torch.cuda.synchronize()
        ids = tok.apply_chat_template([{'role': 'user', 'content': legacy_methods.BACKGROUND_PROMPT.format(question=m['helper_body'])}], tokenize=True, add_generation_prompt=True, enable_thinking=False)
        rec.update(helper_message=m['helper_message'], helper_generated_token_ids=m['helper_generated_token_ids'], helper_input_tokens=m['helper_input_token_count'],
                   helper_output_tokens=m['helper_output_token_count'], helper_input_ids_sha256=hashlib.sha256(str(ids).encode()).hexdigest(),
                   bos_count=ids.count(bos) if bos is not None else None, helper_body_sha256=hashlib.sha256(m['helper_body'].encode()).hexdigest(),
                   latency_ms=(time.perf_counter() - t) * 1000)
    except Exception:
        rec['runtime_error'] = traceback.format_exc(); print('RUNTIME_ERROR', ds, r['id'], flush=True)
    append(OUT, rec); first = False
print('DONE', a.mode, spec['repo'], len(rows), utc(), flush=True)
if a.mode == 'validate':
    lab = {}
    for name in ['full_train', 'full_development']:
        for x in jl(V2L / f'{name}_P2_SCORING_V2.jsonl'):
            if x['pair'] == 'small': lab[(x['dataset'], x['id'])] = x
    res = []
    for o in jl(OUT):
        s = lab[(o['dataset'], o['id'])]['source_T']; saved = rawline(s['source_path'], s['source_line'])
        res.append(dict(dataset=o['dataset'], id=o['id'], runtime_ok=o['runtime_error'] is None,
                        message_equal=o.get('helper_message') == saved['helper_message'], token_ids_equal=o.get('helper_generated_token_ids') == saved.get('helper_generated_token_ids'),
                        input_tokens_equal=o.get('helper_input_tokens') == saved.get('helper_input_tokens'), saved_record=f"{s['source_path']}:{s['source_line']}"))
    ok = all(c['runtime_ok'] and c['message_equal'] and c['token_ids_equal'] and c['input_tokens_equal'] for c in res) and len(res) == len(rows)
    save(OUT.parent / 'HELPER_VALIDATION.json', dict(utc=utc(), verdict='PASS' if ok else 'FAIL', rows=res))
    print('HELPER_VALIDATION', 'PASS' if ok else 'FAIL', flush=True); sys.exit(0 if ok else 3)
