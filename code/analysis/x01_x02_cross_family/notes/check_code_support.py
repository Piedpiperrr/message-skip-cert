"""XFAM feasibility, step 3 (login node, tokenizers only; no model weights). Writes notes/code_support_checks.json."""
import sys
sys.dont_write_bytecode = True
import ast, json, hashlib, pathlib, glob
import numpy as np
ROOT = pathlib.Path('$DATA_DIR')
DATA_ROOT = ROOT.parent.parent
X = pathlib.Path(__file__).resolve().parents[1]
P210 = ROOT / 'P2_10_20260911T122423Z'; BND = ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
V2L = ROOT / 'P2_SCORING_V2_20260912T191445Z/labels'
sys.path.insert(0, str(P210)); import protocol_min, arc_protocol
sys.path.insert(0, str(BND / 'src')); import receiver_prompt as brp
from transformers import AutoTokenizer
QWEN06 = DATA_ROOT / 'c2c_reproduction_assets/models/Qwen--Qwen3-0.6B'
QWEN7 = ROOT / 'P2_6_20260910T164138Z/assets/Qwen2.5-7B-Instruct'
OLMO = DATA_ROOT / 'hf_cache/hub/models--allenai--OLMo-2-1124-7B-Instruct/snapshots/470b1fba1ae01581f270116362ee4aa1b97f4c84'
FUSER_CFG = DATA_ROOT / 'hf_cache/hub/models--nics-efc--C2C_Fuser/snapshots/f01fc3258b305e280e04c7238f4f2cf31b7dc70d/qwen3_0.6b+llam3.2_1b_Fuser/config.json'
BACKGROUND_PROMPT = next(ast.literal_eval(n.value) for n in ast.parse((P210 / 'legacy_methods.py').read_text()).body
                         if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'BACKGROUND_PROMPT')
PREFIX = 'The correct answer is'
jl = lambda p: [json.loads(s) for s in open(p) if s.strip()]
Q = {ds: {r['id']: r for s in ['train', 'dev'] for r in jl(BND / f'inputs/{ds}_{s}_queries.jsonl')} for ds in ['obqa', 'arc']}
rq = lambda row: {**row, 'choices': {'label': row['choice_labels'], 'text': row['choice_text']}}  # runtime query_only(row) carries 'choices'
rt_prompt = lambda ds, row: protocol_min.format_openbook(rq(row), use_template=True) if ds == 'obqa' else arc_protocol.receiver_prompt(rq(row))
rt_body = lambda ds, row: protocol_min.format_openbook(rq(row), use_template=False) if ds == 'obqa' else arc_protocol.helper_body(rq(row))
ids_sha = lambda ids: hashlib.sha256(np.asarray(ids, dtype=np.int64).tobytes()).hexdigest()
out = {}

# ---------------- 3d: X1 reuse of the small pair's receiver-only records
tq = AutoTokenizer.from_pretrained(QWEN06, local_files_only=True)
meta = sorted(glob.glob(str(QWEN06 / '.cache/huggingface/download/*.metadata')))
revs = sorted({open(m).read().split('\n')[0] for m in meta})
cfg210 = json.loads((P210 / 'frozen_config.json').read_text())['pair_configs']['small']['models']['receiver']
bnd = json.loads((BND / 'frozen_config.json').read_text())['models']['small']
pre = tq.encode(PREFIX, add_special_tokens=False)
probe = dict(rows=0, rendered_sha_match=0, probe_ids_sha_match=0, generation_prefix_sha_match=0, bnd_prompt_equals_runtime_prompt=0)
for ds in ['obqa', 'arc']:
    for sp in ['fit', 'cal', 'dev']:
        for r in jl(BND / f'records/small_{ds}_{sp}_probes.jsonl'):
            row = Q[ds][r['id']]; body = brp.receiver_prompt(row)
            rendered = tq.apply_chat_template([{'role': 'user', 'content': body}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
            base = tq(rendered)['input_ids']
            probe['rows'] += 1; probe['rendered_sha_match'] += hashlib.sha256(rendered.encode()).hexdigest() == r['rendered_sha256']
            probe['probe_ids_sha_match'] += ids_sha(base + pre) == r['probe_ids_sha256']
            probe['generation_prefix_sha_match'] += ids_sha(base) == r['original_generation_prefix_ids_sha256']
            probe['bnd_prompt_equals_runtime_prompt'] += body == rt_prompt(ds, row)
rr = dict(rows=0, receiver_input_tokens_match=0, sources=set())
for name in ['full_train', 'full_development']:
    for lab in jl(V2L / f'{name}_P2_SCORING_V2.jsonl'):
        if lab['pair'] != 'small': continue
        s = lab['source_R']; x = json.loads(open(s['source_path']).read().split('\n')[s['source_line'] - 1])
        ds = lab['dataset']; row = Q[ds][lab['id']]
        n = len(tq(tq.apply_chat_template([{'role': 'user', 'content': rt_prompt(ds, row)}], tokenize=False, add_generation_prompt=True, enable_thinking=False))['input_ids'])
        rr['rows'] += 1; rr['receiver_input_tokens_match'] += n == x['receiver_input_tokens']; rr['sources'].add(s['source_path'].split('iclr2027_p2/')[1])
rr['sources'] = sorted(rr['sources'])
out['3d_X1_reuse_small_receiver_records'] = dict(
    receiver_local_path=str(QWEN06), receiver_revision_from_download_metadata=revs, p210_small_receiver=dict(path=cfg210.get('path'), revision=cfg210.get('revision')),
    boundaries_small_model=dict(path=bnd.get('path'), revision=bnd.get('revision'), chat_template_sha256_match=hashlib.sha256(tq.chat_template.encode()).hexdigest() == bnd['chat_template_sha256']),
    probemax_records_recomputed=probe, R_outputs_input_token_counts=rr)
print('3d', json.dumps(out['3d_X1_reuse_small_receiver_records'], indent=1)[:1500], flush=True)

# ---------------- 3b: helper Text input is receiver-independent; saved large-pair messages
t7 = AutoTokenizer.from_pretrained(QWEN7, local_files_only=True)
ex = []
for name, ds, k in [('full_train', 'obqa', 2), ('full_train', 'arc', 1)]:
    labs = [l for l in jl(V2L / f'{name}_P2_SCORING_V2.jsonl') if l['pair'] == 'large' and l['dataset'] == ds][:k]
    for lab in labs:
        s = lab['source_T']; x = json.loads(open(s['source_path']).read().split('\n')[s['source_line'] - 1]); row = Q[ds][lab['id']]
        msgs = [{'role': 'user', 'content': BACKGROUND_PROMPT.format(question=rt_body(ds, row))}]
        ids_a = t7.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=False)   # large pair (receiver Qwen3-8B)
        ids_b = t7.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=False)   # X2 (receiver OLMo/Llama): same inputs
        ex.append(dict(dataset=ds, id=lab['id'], saved_record=f"{s['source_path'].split('iclr2027_p2/')[1]}:{s['source_line']}",
                       helper_input_ids_sha256=ids_sha(ids_a), X2_equals_large_bytes=ids_sha(ids_a) == ids_sha(ids_b),
                       helper_input_tokens_rebuilt=len(ids_a), helper_input_tokens_saved=x['helper_input_tokens'],
                       saved_message_decodes_from_saved_ids=t7.decode(x['helper_generated_token_ids'], skip_special_tokens=True, clean_up_tokenization_spaces=False) == x['helper_message']))
out['3b_helper_input_examples'] = ex
print('3b', json.dumps(ex, indent=1), flush=True)

# ---------------- 3a: OLMo-2 as receiver (Llama tokenizers are gated and could not be loaded)
to = AutoTokenizer.from_pretrained(OLMO, local_files_only=True)
row = Q['obqa'][jl(BND / 'records/small_obqa_dev_probes.jsonl')[0]['id']]; body = rt_prompt('obqa', row)
m = [{'role': 'user', 'content': body}]
r1 = to.apply_chat_template(m, tokenize=False, add_generation_prompt=True, enable_thinking=False)
r0 = to.apply_chat_template(m, tokenize=False, add_generation_prompt=True)
native = to.apply_chat_template(m, tokenize=True, add_generation_prompt=True, enable_thinking=False)
via_text = to(r1)['input_ids']
text3 = to.apply_chat_template([{'role': 'user', 'content': 'B'}, {'role': 'assistant', 'content': 'H'}, {'role': 'user', 'content': body}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
labels = sorted({l for ds in ['obqa', 'arc'] for r in Q[ds].values() for l in brp.display_labels(len(r['choice_text']))})
sets = {l: [] for l in labels}; special = set(to.all_special_ids)
for v in sorted(set(to.get_vocab().values())):
    if v in special: continue
    d = to.decode([v], skip_special_tokens=False, clean_up_tokenization_spaces=False)
    if d.strip() in sets: sets[d.strip()].append(v)
pid = to.encode(PREFIX, add_special_tokens=False)
gen = json.loads((OLMO / 'generation_config.json').read_text()); tcfg = json.loads((OLMO / 'tokenizer_config.json').read_text())
out['3a_OLMo_receiver'] = dict(
    chat_template_present=bool(to.chat_template), enable_thinking_kwarg_ignored=r1 == r0, rendered_example=r1,
    bos_token=to.bos_token, add_bos_token=tcfg.get('add_bos_token'), tokenizer_of_rendered_equals_native_ids=via_text == native,
    extra_leading_tokens_when_retokenized=len(via_text) - len(native), three_message_text_path_renders=('H' in text3),
    qwen_role_markers_present=('<|im_start|>assistant' in r1), label_sets_nonempty_disjoint=all(sets.values()) and len({v for s in sets.values() for v in s}) == sum(map(len, sets.values())),
    label_token_counts={l: len(v) for l, v in sets.items()}, prefix_roundtrip=to.decode(pid, skip_special_tokens=False, clean_up_tokenization_spaces=False) == PREFIX,
    generation_config={k: gen.get(k) for k in ['eos_token_id', 'pad_token_id', 'bos_token_id', 'do_sample', 'temperature']}, tokenizer_pad_token=to.pad_token)
print('3a', json.dumps({k: v for k, v in out['3a_OLMo_receiver'].items() if k != 'rendered_example'}, indent=1), flush=True)
print('3a rendered:', repr(r1[:400]))

# ---------------- 3c: X1 fuser config
fc = json.loads(FUSER_CFG.read_text())
flat = {}
def walk(d, p=''):
    for k, v in d.items():
        if isinstance(v, dict): walk(v, p + k + '.')
        else: flat[p + k] = v
walk(fc)
out['3c_X1_fuser_config'] = {k: v for k, v in flat.items() if any(s in k.lower() for s in ['align', 'model', 'teacher', 'base', 'strategy'])}
print('3c', json.dumps(out['3c_X1_fuser_config'], indent=1))
json.dump(out, open(X / 'notes/code_support_checks.json', 'w'), indent=1, default=str)
