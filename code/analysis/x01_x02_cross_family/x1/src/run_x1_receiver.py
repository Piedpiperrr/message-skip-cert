"""X1 stage C2: receiver Qwen3-0.6B reads helper messages (receiver half of the paper's Text action), receiver-only.
Same calls as the X2 driver (src/run_x2.py, validated): receiver loaded as runtime.Runner.__init__ (bf16, sdpa,
apply_generation_config do_sample False / 64 tokens; generation config asserted equal to the paper's small-pair frozen config),
then legacy_methods.T2TReceiverBundle.consume(q, format(q, use_template=False), message) with the paper's formatters
(P2_10 OBQA / arc_runtime_adapter ARC), thinking disabled, max_new_tokens 64. Parser: frozen V2. Gold is never read.
Modes: validate (messages = saved small-pair helper messages; outputs must equal the saved small-pair Text raw outputs; exit 3 on diff)
       smoke/run (messages = X1 Llama helper outputs, --messages).
usage: run_x1_receiver.py --mode {validate,smoke,run} --rows <population rows> [--messages <helper outputs jsonl>] --out <jsonl>"""
import sys
sys.dont_write_bytecode = True
import argparse, time, traceback, hashlib, json, os
from x1_common import *

ap = argparse.ArgumentParser()
ap.add_argument('--mode', required=True, choices=['validate', 'smoke', 'run'])
ap.add_argument('--rows', required=True); ap.add_argument('--messages'); ap.add_argument('--out', required=True)
a = ap.parse_args()
OUT = pathlib.Path(a.out); assert not OUT.exists(), f'refusing to overwrite {OUT}'
rows = jl(a.rows); parse = parser(); DEADLINE = float(os.environ.get('XFAM_DEADLINE_EPOCH', 'inf'))
lab = {}
for name in ['full_train', 'full_development']:
    for x in jl(V2L / f'{name}_P2_SCORING_V2.jsonl'):
        if x['pair'] == 'small': lab[(x['dataset'], x['id'])] = x
if a.mode == 'validate':
    MSG = {}
    for r in rows:
        s = lab[(r['dataset'], r['id'])]['source_T']; MSG[(r['dataset'], r['id'])] = rawline(s['source_path'], s['source_line'])['helper_message']
else:
    MSG = {(m['dataset'], m['id']): m['helper_message'] for m in jl(a.messages) if m['runtime_error'] is None}
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
t0 = time.perf_counter()
tok = AutoTokenizer.from_pretrained(QWEN06['path'], local_files_only=True)
if tok.pad_token is None: tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(QWEN06['path'], local_files_only=True, torch_dtype=torch.bfloat16, attn_implementation='sdpa').to('cuda:0').eval().requires_grad_(False)
protocol_min.apply_generation_config(model, {'do_sample': False, 'max_new_tokens': 64})
assert model.generation_config.to_dict() == read(P210 / 'frozen_config.json')['pair_configs']['small']['receiver_generation_config']
tr = legacy_methods.T2TReceiverBundle(model, tok)
save(OUT.with_suffix('.env.json'), dict(utc=utc(), mode=a.mode, receiver=QWEN06, load_seconds=time.perf_counter() - t0, rows_file=a.rows, rows_sha256=sha(a.rows),
                                        messages_file=a.messages, messages_sha256=sha(a.messages) if a.messages else None, job_id=os.environ.get('PBS_JOBID'),
                                        host=os.uname().nodename, gpu=str(torch.cuda.get_device_properties(0))))
first = True
for r in rows:
    if time.time() > DEADLINE - 60:
        print('DEADLINE_STOP', r['dataset'], r['id'], flush=True); break
    ds, q = r['dataset'], r['query']
    protocol_min.format_openbook = FMT[ds]; legacy_methods.format_openbook = FMT[ds]
    rec = dict(dataset=ds, split=r['split'], id=r['id'], representative=r['representative'], receiver=QWEN06['repo'], utc=utc(), cold_first_after_load=first, runtime_error=None)
    try:
        msg = MSG[(ds, r['id'])]
        torch.cuda.synchronize(); t = time.perf_counter()
        with torch.inference_mode():
            res = tr.consume(q, FMT[ds](q, use_template=False), msg)
        torch.cuda.synchronize()
        p = parse(res['generated_text'], r['legal_labels'])
        rec['T'] = dict(raw=res['generated_text'], generated_token_ids=res['generated_token_ids'], receiver_input_tokens=res['receiver_input_token_count'],
                        prompt_ids_sha256=hashlib.sha256(json.dumps(res['receiver_prompt_token_ids']).encode()).hexdigest(),
                        helper_message_sha256=hashlib.sha256(msg.encode()).hexdigest(), parsed=p['answer'] if p['valid'] else 'INVALID', parse_reason=p['reason'],
                        latency_ms=(time.perf_counter() - t) * 1000)
    except Exception:
        rec['runtime_error'] = traceback.format_exc(); print('RUNTIME_ERROR', ds, r['id'], flush=True)
    append(OUT, rec); first = False
print('DONE', a.mode, len(rows), utc(), flush=True)
if a.mode == 'validate':
    res = []
    for o in jl(OUT):
        s = lab[(o['dataset'], o['id'])]['source_T']; saved = rawline(s['source_path'], s['source_line'])
        ok = o['runtime_error'] is None
        res.append(dict(dataset=o['dataset'], id=o['id'], runtime_ok=ok, T_raw_equal=ok and o['T']['raw'] == saved['raw_answer'],
                        T_input_tokens_equal=ok and o['T']['receiver_input_tokens'] == saved['receiver_input_tokens']))
    v = all(c['runtime_ok'] and c['T_raw_equal'] and c['T_input_tokens_equal'] for c in res) and len(res) == len(rows)
    save(OUT.parent / 'RECEIVER_VALIDATION.json', dict(utc=utc(), verdict='PASS' if v else 'FAIL', rows=res))
    print('RECEIVER_VALIDATION', 'PASS' if v else 'FAIL', flush=True); sys.exit(0 if v else 3)
