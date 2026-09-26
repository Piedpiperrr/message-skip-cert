"""E16-3 probe prefill (and V4). One receiver per process, one dtype: bf16 (deployed) or fp32 (E16-3(b): weights/activations/attention fp32,
TF32 off). Probe input exactly as the X2/X3 probe (validated bitwise on the large pair): the paper's receiver prompt (P2_10 OBQA format,
P2-8 v2 ARC adapter, MMLU stage-1 format) in the receiver's chat template with add_generation_prompt=True, enable_thinking=False, tokenized with
add_special_tokens=False (asserted == apply_chat_template ids), then the prefix ids of "The correct answer is". One forward of model.model
(use_cache=False, attn_implementation='sdpa'), lm_head on the last position only, logits upcast to float32; option-label logits
l_k = logsumexp over label k's token set (float32, as deployed); u = 1 - max softmax(l) (float32, as deployed).
Saves per row: l (float32 values), u, p_labels, argmax, probe_ids_sha256, input_tokens. SDPA kernels from torch.profiler on the first row.
Gold is never read. modes: v4 (u and probe ids compared bitwise with the stored values in each row; exit 3 on any difference), run.
usage: e16_probe.py --receiver {qwen3_0_6b,qwen3_1_7b,qwen3_8b} --dtype {bf16,fp32} --mode {v4,run} --rows <jsonl> --out <jsonl>"""
import sys
sys.dont_write_bytecode = True
import argparse, time, traceback, hashlib, json, math
from xfam_common import *
ap = argparse.ArgumentParser()
ap.add_argument('--receiver', required=True, choices=['qwen3_0_6b', 'qwen3_1_7b', 'qwen3_8b']); ap.add_argument('--dtype', required=True, choices=['bf16', 'fp32'])
ap.add_argument('--mode', required=True, choices=['v4', 'run']); ap.add_argument('--rows', required=True); ap.add_argument('--out', required=True)
a = ap.parse_args()
OUT = pathlib.Path(a.out); assert not OUT.exists(), OUT
rows = jl(a.rows); DEADLINE = float(os.environ.get('XFAM_DEADLINE_EPOCH', 'inf'))
import numpy as np, torch
from transformers import AutoTokenizer, AutoModelForCausalLM
torch.manual_seed(0); torch.cuda.manual_seed_all(0)
torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
assert torch.cuda.is_available() and torch.cuda.device_count() == 1
sys.path.insert(0, str(P210))
import runtime, protocol_min, legacy_methods
FMT = {'obqa': protocol_min.format_openbook}
import arc_runtime_adapter  # noqa: F401
FMT['arc'] = protocol_min.format_openbook
sys.path.insert(0, str(MMLU / 'src'))
import native_runtime as mmlu_nr  # noqa: F401
FMT['mmlu_pro'] = protocol_min.format_openbook
assert FMT['obqa'] is not FMT['arc'] and FMT['arc'] is not FMT['mmlu_pro']
spec = RECEIVERS[a.receiver]; DEV = 'cuda:0'; t0 = time.perf_counter()
tok = AutoTokenizer.from_pretrained(spec['path'], local_files_only=True)
DT = torch.bfloat16 if a.dtype == 'bf16' else torch.float32
model = AutoModelForCausalLM.from_pretrained(spec['path'], local_files_only=True, torch_dtype=DT, attn_implementation='sdpa').to(DEV).eval().requires_grad_(False)
assert model.config._attn_implementation == 'sdpa' and next(model.parameters()).dtype == DT
prefix_ids = tok.encode(PREFIX, add_special_tokens=False)
sets = {l: [] for l in LABELS_ALL}; special = set(tok.all_special_ids)
for v in sorted(set(tok.get_vocab().values())):
    if v in special: continue
    d = tok.decode([v], skip_special_tokens=False, clean_up_tokenization_spaces=False)
    if d.strip() in sets: sets[d.strip()].append(v)
assert all(sets.values()) and len({v for s in sets.values() for v in s}) == sum(map(len, sets.values()))
ix = {l: torch.tensor(v, device=DEV) for l, v in sets.items()}


def probe(q, ds, labels):
    body = FMT[ds](q, use_template=True); msgs = [{'role': 'user', 'content': body}]
    rendered = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    plain = tok(rendered, add_special_tokens=False)['input_ids']
    assert plain == tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=False)
    ids = torch.tensor([plain + prefix_ids], dtype=torch.long); n = ids.shape[1]
    with torch.inference_mode():
        out = model.model(input_ids=ids.to(DEV), attention_mask=torch.ones_like(ids).to(DEV), use_cache=False, return_dict=True)
        logits = model.lm_head(out.last_hidden_state[:, n - 1:n, :])[0, 0, :].float()
        ll = torch.stack([torch.logsumexp(logits[ix[l]], dim=0) for l in labels])
        p = torch.log_softmax(ll, dim=0).exp(); ps = p.cpu().tolist(); u = float((1 - p.max()).item())
    lv = ll.cpu().tolist()
    assert all(map(math.isfinite, lv)) and all(map(math.isfinite, ps)) and 0 <= u <= 1
    return dict(label_logits=dict(zip(labels, lv)), ProbeMax=u, p_labels=dict(zip(labels, ps)), argmax_probe_label=labels[int(np.argmax(ps))],
                probe_ids_sha256=hashlib.sha256(ids.numpy().tobytes()).hexdigest(), input_tokens=n)


def fmt_for(r): return protocol_min.__setattr__('format_openbook', FMT[r['dataset']]) or legacy_methods.__setattr__('format_openbook', FMT[r['dataset']])


# SDPA kernels actually launched (first row, profiled; that forward is repeated unprofiled for the record)
kern = []
try:
    from torch.profiler import profile, ProfilerActivity
    r0 = rows[0]; fmt_for(r0)
    with profile(activities=[ProfilerActivity.CUDA]) as prof: probe(r0['query'], r0['dataset'], r0['legal_labels'])
    kern = sorted({e.key for e in prof.key_averages() if any(s in e.key.lower() for s in ['flash', 'fmha', 'efficient', 'attention', 'sdpa', 'softmax', 'bmm', 'cutlass'])})[:40]
except Exception as e:
    kern = [f'profiler failed: {type(e).__name__}: {e}']
env = dict(utc=utc(), receiver=a.receiver, spec=spec, dtype=a.dtype, mode=a.mode, rows_file=a.rows, rows_sha256=sha(a.rows), n_rows=len(rows), load_seconds=time.perf_counter() - t0,
           attn_implementation=model.config._attn_implementation, sdp_flags=dict(flash=torch.backends.cuda.flash_sdp_enabled(), mem_efficient=torch.backends.cuda.mem_efficient_sdp_enabled(),
           math=torch.backends.cuda.math_sdp_enabled()), sdpa_kernels_first_row=kern, tf32=dict(matmul=torch.backends.cuda.matmul.allow_tf32, cudnn=torch.backends.cudnn.allow_tf32),
           torch=torch.__version__, gpu=str(torch.cuda.get_device_properties(0)), prefix_ids=prefix_ids, label_token_sets=sets,
           chat_template_sha256=hashlib.sha256(tok.chat_template.encode()).hexdigest(), job_id=os.environ.get('PBS_JOBID'), host=os.uname().nodename)
save(OUT.with_suffix('.env.json'), env)
for r in rows:
    if time.time() > DEADLINE - 60: print('DEADLINE_STOP', r['dataset'], r['id'], flush=True); break
    fmt_for(r); rec = dict(dataset=r['dataset'], split=r['split'], id=r['id'], receiver=a.receiver, dtype=a.dtype, runtime_error=None)
    try:
        t = time.perf_counter(); rec.update(probe(r['query'], r['dataset'], r['legal_labels'])); rec['latency_ms'] = (time.perf_counter() - t) * 1000
    except Exception:
        rec['runtime_error'] = traceback.format_exc(); print('RUNTIME_ERROR', r['id'], flush=True)
    append(OUT, rec)
print('DONE', a.receiver, a.dtype, a.mode, len(rows), utc(), flush=True)
if a.mode == 'v4':
    res = []
    for r, o in zip(rows, jl(OUT)):
        ok = o['runtime_error'] is None
        res.append(dict(dataset=r['dataset'], id=r['id'], stored_u=r['stored_u'], new_u=o.get('ProbeMax'), u_equal=ok and o['ProbeMax'] == r['stored_u'],
                        probe_ids_equal=(ok and o['probe_ids_sha256'] == r['stored_probe_ids_sha256']) if r.get('stored_probe_ids_sha256') else None))
    by = {}
    for x in res:
        k = x['dataset']; b = by.setdefault(k, dict(n=0, u_equal=0, u_pos=0, ids_checked=0, ids_equal=0))
        b['n'] += 1; b['u_equal'] += x['u_equal']; b['u_pos'] += x['stored_u'] > 0
        if x['probe_ids_equal'] is not None: b['ids_checked'] += 1; b['ids_equal'] += x['probe_ids_equal']
    for k, b in by.items(): b['pass'] = b['n'] == 16 and b['u_equal'] == 16 and b['ids_equal'] == b['ids_checked'] and b['u_pos'] >= 8
    save(OUT.parent / f'V4_{a.receiver}.json', dict(utc=utc(), receiver=a.receiver, per_benchmark=by, rows=res, sdpa_kernels_first_row=kern))
    print('V4', a.receiver, {k: ('PASS' if b['pass'] else 'FAIL', b['u_equal'], b['ids_equal'], b['ids_checked']) for k, b in by.items()}, flush=True)
    sys.exit(0 if all(b['pass'] for b in by.values()) else 3)
