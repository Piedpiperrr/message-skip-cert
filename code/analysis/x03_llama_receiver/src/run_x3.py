"""X3 receiver-only driver = copy of X2 run_x2.py (approved changes A1 + A2) with the X3 changes marked "X3:" (receiver ids;
R-path tokenization of the rendered chat template with add_special_tokens=False, approved 2026-09-21 (no double BOS); explicit
add_special_tokens=False in the probe; per-row BOS counts; parsed-label comparison in validate mode). One GPU, one receiver; no helper, no fuser.

Per row, in order: R (runtime.Runner.request(q, 'receiver_only'), the paper's R path), Text-reading
(runtime T2TReceiverBundle.consume(q, format(q, use_template=False), saved helper message), the receiver half of the paper's
Text action), ProbeMax (A1: probe input = receiver tokenizer's own chat template of the paper's receiver prompt with
add_generation_prompt=True, then the unchanged prefix ids; label-token rule, K-label renormalization and u = 1 - max p as in
the paper's probe code). Receiver prompts per dataset = the paper's formatters: P2_10 OBQA format_openbook, P2_10
arc_runtime_adapter (P2-8 v2), MMLU stage-1 native_runtime format_mmlu (switched per row, as the adapters patch them).
Gold is never read. Each row's record is appended with fsync. Modes:
  validate : receiver Qwen3-8B; compares every output with the saved large-pair records; writes VALIDATION.json; exit 3 on any diff
  smoke/run: receiver as given; writes outputs only
usage: run_x3.py --mode {validate,smoke,run} --receiver {qwen3_8b,llama31_8b,mistral7b_v03} --rows <jsonl> --out <jsonl>
"""
import sys
sys.dont_write_bytecode = True
import argparse, time, traceback, hashlib, json
from xfam_common import *

ap = argparse.ArgumentParser()
ap.add_argument('--mode', required=True, choices=['validate', 'smoke', 'run'])
ap.add_argument('--receiver', required=True, choices=list(RECEIVERS))
ap.add_argument('--rows', required=True); ap.add_argument('--out', required=True)
a = ap.parse_args()
OUT = pathlib.Path(a.out); assert not OUT.exists(), f'refusing to overwrite {OUT}'
rows = jl(a.rows)
parse = parser()
DEADLINE = float(os.environ.get('XFAM_DEADLINE_EPOCH', 'inf'))

import numpy as np, torch
from transformers import AutoTokenizer, AutoModelForCausalLM
torch.manual_seed(0); torch.cuda.manual_seed_all(0)
torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
assert torch.cuda.is_available() and torch.cuda.device_count() == 1
# ---- paper runtime modules and per-dataset receiver-prompt formatters
sys.path.insert(0, str(P210))
import runtime, protocol_min, legacy_methods
FMT = {'obqa': protocol_min.format_openbook}
import arc_runtime_adapter  # noqa: F401  patches protocol_min / legacy_methods format_openbook -> P2-8 v2 ARC format
FMT['arc'] = protocol_min.format_openbook
sys.path.insert(0, str(MMLU / 'src'))
import native_runtime as mmlu_nr  # noqa: F401  patches format_openbook -> format_mmlu (MMLU stage 1)
FMT['mmlu_pro'] = protocol_min.format_openbook
assert FMT['obqa'] is not FMT['arc'] and FMT['arc'] is not FMT['mmlu_pro'] and mmlu_nr.native is runtime and runtime.lm is legacy_methods


def use_format(ds):
    protocol_min.format_openbook = FMT[ds]; legacy_methods.format_openbook = FMT[ds]


LAST = {}
def receiver_prompt_tensors_x3(tokenizer, example, device):
    # X3: protocol_min.receiver_prompt_tensors with add_special_tokens=False when tokenizing the rendered chat template (no second BOS)
    prompt = protocol_min.format_openbook(example, use_template=True)
    rendered = tokenizer.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    tokenized = tokenizer(rendered, return_tensors="pt", add_special_tokens=False)
    LAST['R_ids'] = tokenized['input_ids'][0].tolist()
    return prompt, rendered, {key: value.to(device) for key, value in tokenized.items()}


runtime.receiver_prompt_tensors = protocol_min.receiver_prompt_tensors = receiver_prompt_tensors_x3


# ---- receiver, loaded as runtime.Runner.__init__ loads it (bf16, sdpa, generation config do_sample False / 64 tokens)
spec = RECEIVERS[a.receiver]; DEV = 'cuda:0'; t0 = time.perf_counter()
tok = AutoTokenizer.from_pretrained(spec['path'], local_files_only=True)
if tok.pad_token is None: tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(spec['path'], local_files_only=True, torch_dtype=torch.bfloat16, attn_implementation='sdpa').to(DEV).eval().requires_grad_(False)
protocol_min.apply_generation_config(model, {'do_sample': False, 'max_new_tokens': 64})
gencfg = model.generation_config.to_dict()
if a.receiver == 'qwen3_8b':
    assert gencfg == read(P210 / 'frozen_config.json')['pair_configs']['large']['receiver_generation_config']
runner = runtime.Runner.__new__(runtime.Runner)
runner.receiver, runner.receiver_tok = model, tok
runner.tr = legacy_methods.T2TReceiverBundle(model, tok)
# ---- A1 probe setup: label-token rule on the receiver's own tokenizer
prefix_ids = tok.encode(PREFIX, add_special_tokens=False)
assert tok.decode(prefix_ids, skip_special_tokens=False, clean_up_tokenization_spaces=False) == PREFIX
sets = {l: [] for l in LABELS_ALL}; special = set(tok.all_special_ids)
for v in sorted(set(tok.get_vocab().values())):
    if v in special: continue
    d = tok.decode([v], skip_special_tokens=False, clean_up_tokenization_spaces=False)
    if d.strip() in sets: sets[d.strip()].append(v)
assert all(sets.values()) and len({v for s in sets.values() for v in s}) == sum(map(len, sets.values()))
ix = {l: torch.tensor(v, device=DEV) for l, v in sets.items()}
env = dict(utc=utc(), receiver=a.receiver, spec=spec, mode=a.mode, rows_file=a.rows, rows_sha256=sha(a.rows), n_rows=len(rows),
           load_seconds=time.perf_counter() - t0, generation_config=gencfg, chat_template_sha256=hashlib.sha256(tok.chat_template.encode()).hexdigest(),
           prefix_ids=prefix_ids, label_token_sets=sets, torch=torch.__version__, gpu=str(torch.cuda.get_device_properties(0)),
           job_id=os.environ.get('PBS_JOBID'), host=os.uname().nodename, CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
           bos_token_id=tok.bos_token_id, tokenizer_adds_bos_on_call=(tok('x')['input_ids'][:1] == [tok.bos_token_id]) if tok.bos_token_id is not None else False,
           tokenizer_class=type(tok).__name__, transformers=__import__('transformers').__version__, PYTHONPATH=os.environ.get('PYTHONPATH'),
           sentencepiece=(__import__('sentencepiece').__file__ if __import__('importlib').util.find_spec('sentencepiece') else None))
save(OUT.with_suffix('.env.json'), env)


def sync(): torch.cuda.synchronize()


def probe(q, ds, labels):
    body = FMT[ds](q, use_template=True)
    msgs = [{'role': 'user', 'content': body}]
    rendered = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    native = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=False)
    plain = tok(rendered, add_special_tokens=False)['input_ids']   # X3: explicit; equals apply_chat_template(tokenize=True)
    assert plain == native
    ids = torch.tensor([plain + prefix_ids], dtype=torch.long)
    inp = {'input_ids': ids.to(DEV), 'attention_mask': torch.ones_like(ids).to(DEV)}
    n = ids.shape[1]; pos = n - 1
    with torch.inference_mode():
        out = model.model(**inp, use_cache=False, return_dict=True, output_hidden_states=False, output_attentions=False)
        last = out.last_hidden_state[:, pos:pos + 1, :]
        logits = model.lm_head(last)[0, 0, :].float()
        label_logits = torch.stack([torch.logsumexp(logits[ix[l]], dim=0) for l in labels])
        logp = torch.log_softmax(label_logits, dim=0); p = logp.exp(); ps = p.cpu().tolist()
        u = float((1 - p.max()).item())
        union = torch.cat([ix[l] for l in labels]); mass = float(torch.exp(torch.logsumexp(logits[union], 0) - torch.logsumexp(logits, 0)).item())
    assert all(np.isfinite(ps)) and abs(sum(ps) - 1) < 2e-6 and 0 <= u <= 1
    return dict(ProbeMax=u, p_labels=dict(zip(labels, ps)), label_union_mass=mass, argmax_probe_label=labels[int(np.argmax(ps))],
                probe_ids_sha256=hashlib.sha256(ids.numpy().tobytes()).hexdigest(), rendered_sha256=hashlib.sha256(rendered.encode()).hexdigest(),
                input_tokens=n, native_ids_equal_retokenized_rendered=tok(rendered)['input_ids'] == native, bos_count=bos_count(ids[0].tolist()))


def bos_count(ids): return ids.count(tok.bos_token_id) if tok.bos_token_id is not None else 0


def v2(raw, legal):
    p = parse(raw if isinstance(raw, str) else '', legal)
    return (p['answer'] if p['valid'] else 'INVALID'), p['reason']


first = True
for r in rows:
    if time.time() > DEADLINE - 60:
        print('DEADLINE_STOP', r['dataset'], r['id'], flush=True); break
    ds, q, legal = r['dataset'], r['query'], r['legal_labels']
    use_format(ds)
    rec = dict(dataset=ds, split=r['split'], id=r['id'], representative=r['representative'], receiver=a.receiver, utc=utc(), cold_first_after_load=first, runtime_error=None)
    try:
        sync(); t = time.perf_counter(); res = runner.request(q, 'receiver_only'); sync()
        o, why = v2(res['raw_answer'], legal)
        rec['R'] = dict(raw=res['raw_answer'], generated_token_ids=res['generated_token_ids'], receiver_input_tokens=res['receiver_input_tokens'],
                        parsed=o, parse_reason=why, latency_ms=(time.perf_counter() - t) * 1000,
                        bos_count=bos_count(LAST['R_ids']), input_ids_sha256=hashlib.sha256(json.dumps(LAST['R_ids']).encode()).hexdigest())
        assert res['receiver_input_tokens'] == len(LAST['R_ids'])
        sync(); t = time.perf_counter()
        with torch.inference_mode():
            tr = runner.tr.consume(q, FMT[ds](q, use_template=False), r['helper_message'])
        sync(); o, why = v2(tr['generated_text'], legal)
        rec['T'] = dict(raw=tr['generated_text'], generated_token_ids=tr['generated_token_ids'], receiver_input_tokens=tr['receiver_input_token_count'],
                        prompt_ids_sha256=hashlib.sha256(json.dumps(tr['receiver_prompt_token_ids']).encode()).hexdigest(),
                        helper_message_sha256=r['helper_message_sha256'], parsed=o, parse_reason=why, latency_ms=(time.perf_counter() - t) * 1000,
                        bos_count=bos_count(tr['receiver_prompt_token_ids']))
        sync(); t = time.perf_counter(); pr = probe(q, ds, legal); sync()
        rec['P'] = dict(**pr, latency_ms=(time.perf_counter() - t) * 1000)
    except Exception:
        rec['runtime_error'] = traceback.format_exc(); print('RUNTIME_ERROR', ds, r['id'], flush=True)
    append(OUT, rec); first = False
print('DONE', a.mode, a.receiver, len(rows), utc(), flush=True)

if a.mode == 'validate':   # compare with the saved large-pair (ClusterB) records
    lab = {}
    for name in ['full_train', 'full_development']:
        for x in jl(V2L / f'{name}_P2_SCORING_V2.jsonl'):
            if x['pair'] == 'large': lab[(x['dataset'], x['id'])] = x
    zg = {x['id']: x for x in jl(ZG / 'records/probe_records.jsonl')}
    arcp = {x['id']: x for x in jl(BND / 'records/large_arc_fit_probes.jsonl')}
    mm, mp = {}, {}
    for f in sorted((MMLU / 'shards').glob('*/actions/fit.jsonl')):
        for x in jl(f): mm[(x['id'], x['action'])] = x
    for f in sorted((MMLU / 'shards').glob('*/probes/fit.jsonl')):
        for x in jl(f): mp[x['id']] = x
    res = []
    for o in jl(OUT):
        ds, i = o['dataset'], o['id']
        if ds in ('obqa', 'arc'):
            sR, sT = lab[(ds, i)]['source_R'], lab[(ds, i)]['source_T']
            rawR, rawT = rawline(sR['source_path'], sR['source_line'])['raw_answer'], rawline(sT['source_path'], sT['source_line'])['raw_answer']
            sp = zg[i] if ds == 'obqa' else arcp[i]
        else:
            rawR, rawT, sp = mm[(i, 'R')]['output']['raw_answer'], mm[(i, 'T')]['output']['raw_answer'], mp[i]
        ok = o['runtime_error'] is None
        c = dict(dataset=ds, id=i, runtime_ok=ok,
                 probe_ids_equal=ok and o['P']['probe_ids_sha256'] == sp['probe_ids_sha256'],
                 ProbeMax_equal=ok and o['P']['ProbeMax'] == sp['ProbeMax'], p_labels_equal=ok and o['P']['p_labels'] == sp['p_labels'],
                 R_raw_equal=ok and o['R']['raw'] == rawR, T_raw_equal=ok and o['T']['raw'] == rawT,
                 R_parsed_equal=ok and ds in ('obqa', 'arc') and o['R']['parsed'] == lab[(ds, i)]['o_R'], T_parsed_equal=ok and ds in ('obqa', 'arc') and o['T']['parsed'] == lab[(ds, i)]['o_T'],
                 ProbeMax_ClusterA=o['P']['ProbeMax'] if ok else None, ProbeMax_saved=sp['ProbeMax'])
        c['all_equal'] = all(c[k] for k in ['runtime_ok', 'probe_ids_equal', 'ProbeMax_equal', 'p_labels_equal', 'R_raw_equal', 'T_raw_equal', 'R_parsed_equal', 'T_parsed_equal'])
        res.append(c)
    verdict = 'PASS' if res and all(c['all_equal'] for c in res) and len(res) == len(rows) else 'FAIL'
    save(OUT.parent / 'VALIDATION.json', dict(utc=utc(), verdict=verdict, n=len(res), rows=res, outputs_sha256=sha(OUT),
                                              saved_sources=dict(obqa_probe=str(ZG / 'records/probe_records.jsonl'), arc_probe=str(BND / 'records/large_arc_fit_probes.jsonl'),
                                                                 obqa_arc_R_T='P2_SCORING_V2 labels source_R/source_T (P2_6 / P2_9 large train cases)',
                                                                 mmlu='MMLU stage-1 shards/*/actions/fit.jsonl and probes/fit.jsonl')))
    print('VALIDATION', verdict, sum(c['all_equal'] for c in res), '/', len(res), flush=True)
    sys.exit(0 if verdict == 'PASS' else 3)
