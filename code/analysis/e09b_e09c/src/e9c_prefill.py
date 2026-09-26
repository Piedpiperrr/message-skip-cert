"""E9c helper prefill (GPU). One fixed-format helper probe per question.

Protocol E9C, "Score": argmax_H comes from one helper prefill of the question and options in the
helper's own chat template followed by the separately encoded literal "The correct answer is", with
the same label-token rule and renormalization over the displayed labels as ProbeMax.

The construction is the frozen ProbeMax construction with the receiver replaced by the helper of the
same pair. No generation, no fuser, no gold, no receiver forward. batch=1, bf16, sdpa, FP32 scoring.
"""
import os, sys, json, time, hashlib, argparse
import numpy as np, torch, transformers
from transformers import AutoTokenizer, AutoModelForCausalLM
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e9_common import *

ap = argparse.ArgumentParser()
ap.add_argument('--rank', type=int, required=True)
ap.add_argument('--plan', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--deadline-epoch', type=float, default=float('inf'))
ap.add_argument('--validate-rows', type=int, default=16)
A = ap.parse_args()

OUT = Path(A.out); OUT.mkdir(parents=True, exist_ok=True)
plan = rd(A.plan)
lane = plan['lanes'][A.rank]
pair = lane['helper_pair']
spec = HELPERS[pair]
log = lambda *a: print(f'[rank{A.rank}]', *a, flush=True)

def expired():
    return time.time() > A.deadline_epoch

# ---------------- tokenizer, label-token rule, protocol freeze ----------------
t_start = time.perf_counter()
tok = AutoTokenizer.from_pretrained(spec['path'], local_files_only=True)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
assert hashlib.sha256(tok.chat_template.encode()).hexdigest() == HELPER_CHAT_TEMPLATE_SHA256, 'helper chat template changed'
prefix_ids = tok.encode(PREFIX, add_special_tokens=False)
assert tok.decode(prefix_ids, skip_special_tokens=False, clean_up_tokenization_spaces=False) == PREFIX

# labels needed by every task on this lane (dynamic K per question at scoring time)
maxK = 0
QCACHE, RCACHE = {}, {}
for t in lane['tasks']:
    key = (t['pair'], t['dataset'])
    if key not in QCACHE:
        QCACHE[key] = queries(*key); RCACHE[key] = reps(*key)
    maxK = max(maxK, max(len(QCACHE[key][i]['choice_text']) for i in RCACHE[key][t['split']]))
labels = display_labels(maxK)
sets, mapping = label_token_sets(tok, labels)
save(OUT / f'protocol_rank{A.rank}.json', {
    'helper_pair': pair, 'helper': spec, 'chat_template_sha256': HELPER_CHAT_TEMPLATE_SHA256,
    'prefix_literal': PREFIX, 'prefix_ids': prefix_ids, 'prefix_encoding': 'add_special_tokens=False',
    'label_token_sets': sets, 'label_token_count': {l: len(v) for l, v in sets.items()},
    'max_K_on_lane': maxK, 'rule': 'own tokenizer non-special single tokens decoding.strip()==displayed label; dynamic K',
    'renormalization': 'FP32 label logsumexp then softmax over the K displayed labels',
    'score': 'HelperMax = 1 - max p; argmax_helper_label = argmax p',
    'generation': False, 'fuser_loaded': False, 'receiver_loaded': False, 'gold_read': False})
writejl(OUT / f'token_decode_mapping_rank{A.rank}.jsonl', mapping)
log('tokenizer ready', time.perf_counter() - t_start, 's; labels', labels)

def construct(row, fact=None):
    body = question_body(row, fact)
    rendered = tok.apply_chat_template([{'role': 'user', 'content': body}],
                                       tokenize=False, add_generation_prompt=True, enable_thinking=False)
    base = tok(rendered, return_tensors='pt')
    suffix = tok.encode(PREFIX, add_special_tokens=False)
    assert suffix == prefix_ids
    ids = torch.cat([base['input_ids'], torch.tensor([suffix], dtype=base['input_ids'].dtype)], dim=1)
    mask = torch.cat([base['attention_mask'], torch.ones((1, len(suffix)), dtype=base['attention_mask'].dtype)], dim=1)
    return rendered, base, {'input_ids': ids, 'attention_mask': mask}

# ---------------- model ----------------
t0 = time.perf_counter()
lm = AutoModelForCausalLM.from_pretrained(spec['path'], local_files_only=True, torch_dtype=torch.bfloat16,
                                          attn_implementation='sdpa', low_cpu_mem_usage=True).to('cuda:0').eval().requires_grad_(False)
torch.cuda.synchronize()
load_s = time.perf_counter() - t0
assert lm.config._attn_implementation == 'sdpa'
assert all(0 <= v < lm.config.vocab_size for s in sets.values() for v in s)
ix = {l: torch.tensor(v, device='cuda:0') for l, v in sets.items()}
save(OUT / f'startup_rank{A.rank}.json', {
    'helper_pair': pair, 'model_load_wall_seconds': load_s, 'torch': torch.__version__,
    'transformers': transformers.__version__, 'GPU': str(torch.cuda.get_device_properties(0)),
    'CUDA_VISIBLE_DEVICES': os.environ.get('CUDA_VISIBLE_DEVICES'), 'dtype': 'bfloat16',
    'attention': 'sdpa', 'hidden_size': lm.config.hidden_size, 'num_hidden_layers': lm.config.num_hidden_layers})
log('model loaded', load_s, 's')

cold_done = False
def probe(row, fact=None):
    """One helper prefill. Returns the record; component timings mirror the frozen probe fields."""
    global cold_done
    torch.cuda.synchronize(); t0 = time.perf_counter()
    rendered, base, inputs = construct(row, fact); t1 = time.perf_counter()
    pos = int(torch.nonzero(inputs['attention_mask'][0], as_tuple=False)[-1, 0])
    n = inputs['input_ids'].shape[1]
    tensors = {k: v.to('cuda:0') for k, v in inputs.items()}
    torch.cuda.synchronize(); t2 = time.perf_counter()
    item_labels = display_labels(len(row['choice_text']))
    ev0 = torch.cuda.Event(enable_timing=True); ev1 = torch.cuda.Event(enable_timing=True)
    with torch.inference_mode():
        ev0.record()
        out = lm.model(**tensors, use_cache=False, return_dict=True, output_hidden_states=False, output_attentions=False)
        assert out.past_key_values is None and pos == n - 1 and int(inputs['attention_mask'].sum()) == n
        last = out.last_hidden_state[:, pos:pos + 1, :]
        logits = lm.lm_head(last)[0, 0, :].float()
        ev1.record(); torch.cuda.synchronize(); t3 = time.perf_counter()
        label_logits = torch.stack([torch.logsumexp(logits[ix[l]], dim=0) for l in item_labels])
        p = torch.log_softmax(label_logits, dim=0).exp()
        ps = p.cpu().tolist()
        torch.cuda.synchronize(); t4 = time.perf_counter()
        umax = float((1 - p.max()).item())
        item_union = torch.cat([ix[l] for l in item_labels])
        mass = float(torch.exp(torch.logsumexp(logits[item_union], 0) - torch.logsumexp(logits, 0)).item())
    assert np.isfinite(ps).all() and abs(sum(ps) - 1) < 2e-6 and 0 <= mass <= 1.00001 and 0 <= umax <= 1
    cold = not cold_done; cold_done = True
    r = {'helper_pair': pair, 'id': row['id'], 'input_tokens': int(n), 'last_valid_position': pos,
         'helper_p_labels': dict(zip(item_labels, ps)), 'HelperMax': umax, 'helper_label_union_mass': mass,
         'argmax_helper_label': item_labels[int(np.argmax(ps))],
         'helper_probe_ids_sha256': hashlib.sha256(inputs['input_ids'].numpy().tobytes()).hexdigest(),
         'helper_rendered_sha256': hashlib.sha256(rendered.encode()).hexdigest(),
         'cold_first_after_load': cold,
         'tokenization_prefix_ms': (t1 - t0) * 1000, 'prepare_transfer_ms': (t2 - t1) * 1000,
         'prefill_projection_ms': (t3 - t2) * 1000, 'label_distribution_ms': (t4 - t3) * 1000,
         'helper_probe_core_ms': (t4 - t0) * 1000, 'GPU_prefill_projection_event_ms': ev0.elapsed_time(ev1)}
    del out, last, logits, tensors, p, label_logits
    return r

# ---------------- phase 1: validation (no gold; label distribution only) ----------------
vrows = []
for t in lane['tasks']:
    if t.get('optional') or t['split'] != 'fit':
        continue
    key = (t['pair'], t['dataset'])
    ids = RCACHE[key]['fit'][:A.validate_rows]
    for i in ids:
        r = probe(QCACHE[key][i]); r.update(pair_tag=t['pair'], dataset=t['dataset'], split='fit', phase='validation')
        vrows.append(r)
    break
writejl(OUT / f'validation_rank{A.rank}.jsonl', vrows)
dist = {}
for r in vrows:
    dist[r['argmax_helper_label']] = dist.get(r['argmax_helper_label'], 0) + 1
save(OUT / f'validation_rank{A.rank}.json', {
    'helper_pair': pair, 'n': len(vrows), 'argmax_label_distribution': dist,
    'label_union_mass_min': min([r['helper_label_union_mass'] for r in vrows], default=None),
    'label_union_mass_mean': float(np.mean([r['helper_label_union_mass'] for r in vrows])) if vrows else None,
    'HelperMax_min': min([r['HelperMax'] for r in vrows], default=None),
    'HelperMax_max': max([r['HelperMax'] for r in vrows], default=None),
    'failures': 0, 'gold_read': False})
log('validation done', len(vrows), dist)

# ---------------- phase 2: main ----------------
done, skipped = [], []
for t in lane['tasks']:
    key = (t['pair'], t['dataset'])
    ids = RCACHE[key][t['split']][t['slice'][0]:t['slice'][1]]
    dest = OUT / f"{t['pair']}_{t['dataset']}_{t['split']}_{t.get('variant','plain')}_rank{A.rank}.jsonl"
    if dest.exists():
        log('already present, skipping', dest.name); continue
    if expired():
        skipped.append({**{k: t[k] for k in ('pair', 'dataset', 'split')}, 'variant': t.get('variant', 'plain'),
                        'n': len(ids), 'reason': 'walltime deadline reached before this task started'})
        log('DEADLINE, skipping', dest.name); continue
    facts = rd(t['facts']) if t.get('facts') else None
    rows = []
    t_task = time.perf_counter()
    for j, i in enumerate(ids):
        if expired():
            skipped.append({**{k: t[k] for k in ('pair', 'dataset', 'split')}, 'variant': t.get('variant', 'plain'),
                            'n': len(ids) - j, 'reason': 'walltime deadline reached mid-task'})
            log('DEADLINE mid-task', dest.name, j, '/', len(ids)); break
        r = probe(QCACHE[key][i], facts.get(i) if facts else None)
        r.update(pair_tag=t['pair'], dataset=t['dataset'], split=t['split'], variant=t.get('variant', 'plain'), phase='main')
        rows.append(r)
        if (j + 1) % 500 == 0:
            log('PROGRESS', dest.name, j + 1, '/', len(ids), '%.3fs/row' % ((time.perf_counter() - t_task) / (j + 1)))
    writejl(dest, rows)
    done.append({'file': dest.name, 'n': len(rows), 'requested': len(ids),
                 'seconds': time.perf_counter() - t_task})
    log('TASK_DONE', dest.name, len(rows), '/', len(ids), '%.1fs' % (time.perf_counter() - t_task))

save(OUT / f'LANE_COMPLETE_rank{A.rank}.json', {
    'rank': A.rank, 'helper_pair': pair, 'utc': utc(), 'tasks_done': done, 'tasks_skipped': skipped,
    'job_id': os.environ.get('PBS_JOBID'), 'gold_read': False, 'generation': False,
    'complete': not skipped})
log('LANE COMPLETE; skipped', len(skipped))
