"""X1 preparation (CPU, tokenizers only; no model outputs, no gold): populations, fixed 16-row sample, checks B, C (3 examples), D1,
and freeze inputs. Writes x1/records/..., x1/notes/prepare_checks.json."""
import sys
sys.dont_write_bytecode = True
import ast, hashlib, json
import numpy as np
from x1_common import *
from transformers import AutoTokenizer, GenerationConfig
sys.path.insert(0, str(P210)); import protocol_min, legacy_methods
FMT = {'obqa': protocol_min.format_openbook}
import arc_runtime_adapter; FMT['arc'] = protocol_min.format_openbook
sys.path.insert(0, str(BND / 'src')); import receiver_prompt as brp
out = {}
# ---- populations (same splits / ids / representatives as X2 = the paper's; helper fields dropped)
X1POP.mkdir(parents=True, exist_ok=True); man = {}
for ds in DS1:
    for sp in ['fit', 'cal', 'dev']:
        rows = [{k: r[k] for k in ['dataset', 'split', 'id', 'representative', 'query', 'legal_labels']} for r in jl(X / f'records/populations/{ds}_{sp}.jsonl')]
        p = X1POP / f'{ds}_{sp}.jsonl'
        with open(p, 'w') as f:
            for r in rows: f.write(json.dumps(r, ensure_ascii=False) + '\n')
        man[p.name] = dict(n=len(rows), representatives=sum(r['representative'] for r in rows), sha256=sha(p))
save(X1POP / 'POPULATION_MANIFEST.json', dict(utc=utc(), files=man, source='P2_R1_XFAM records/populations (X2), helper fields removed'))
W = X1 / 'records/work'; W.mkdir(parents=True, exist_ok=True)
fit = {ds: jl(X1POP / f'{ds}_fit.jsonl') for ds in DS1}
for name, rs in [('sample16_obqa.jsonl', fit['obqa'][:8]), ('sample16_arc.jsonl', fit['arc'][:8]), ('sample16_all.jsonl', fit['obqa'][:8] + fit['arc'][:8])]:
    with open(W / name, 'w') as f:
        for r in rs: f.write(json.dumps(r, ensure_ascii=False) + '\n')
out['populations'] = man; out['sample16'] = {n: sha(W / n) for n in ['sample16_obqa.jsonl', 'sample16_arc.jsonl', 'sample16_all.jsonl']}
# ---- B: reuse of the small pair's saved R outputs and ProbeMax records (receiver Qwen3-0.6B c1899de)
tq = AutoTokenizer.from_pretrained(QWEN06['path'], local_files_only=True)
pre = tq.encode(PREFIX, add_special_tokens=False)
ids_sha = lambda ids: hashlib.sha256(np.asarray(ids, dtype=np.int64).tobytes()).hexdigest()
Q = {ds: {r['id']: r for s in ['train', 'dev'] for r in jl(BND / f'inputs/{ds}_{s}_queries.jsonl')} for ds in DS1}
b = dict(probe_rows=0, probe_rendered_sha=0, probe_ids_sha=0, R_rows=0, R_input_tokens=0)
for ds in DS1:
    for sp in ['fit', 'cal', 'dev']:
        for r in jl(BND / f'records/small_{ds}_{sp}_probes.jsonl'):
            rendered = tq.apply_chat_template([{'role': 'user', 'content': brp.receiver_prompt(Q[ds][r['id']])}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
            b['probe_rows'] += 1; b['probe_rendered_sha'] += hashlib.sha256(rendered.encode()).hexdigest() == r['rendered_sha256']
            b['probe_ids_sha'] += ids_sha(tq(rendered)['input_ids'] + pre) == r['probe_ids_sha256']
for name in ['full_train', 'full_development']:
    for lab in jl(V2L / f'{name}_P2_SCORING_V2.jsonl'):
        if lab['pair'] != 'small': continue
        s = lab['source_R']; x = rawline(s['source_path'], s['source_line']); q = runtime_query(Q[lab['dataset']][lab['id']])
        n = len(tq(tq.apply_chat_template([{'role': 'user', 'content': FMT[lab['dataset']](q, use_template=True)}], tokenize=False, add_generation_prompt=True, enable_thinking=False))['input_ids'])
        b['R_rows'] += 1; b['R_input_tokens'] += n == x['receiver_input_tokens']
out['B_reuse'] = b
print('B', b, flush=True)
# ---- C: Llama helper prompt (fixed date, one BOS) and receiver prompt = small-pair Text prompt except the message text
tl = AutoTokenizer.from_pretrained(LLAMA['path'], local_files_only=True)
BG = legacy_methods.BACKGROUND_PROMPT
lab = {}
for name in ['full_train', 'full_development']:
    for x in jl(V2L / f'{name}_P2_SCORING_V2.jsonl'):
        if x['pair'] == 'small': lab[(x['dataset'], x['id'])] = x
ex = []
for r in [fit['obqa'][0], fit['obqa'][1], fit['arc'][0]]:
    ds, q = r['dataset'], r['query']
    protocol_min.format_openbook = FMT[ds]; legacy_methods.format_openbook = FMT[ds]
    hm = [{'role': 'user', 'content': BG.format(question=FMT[ds](q, use_template=False))}]
    txt = tl.apply_chat_template(hm, tokenize=False, add_generation_prompt=True, enable_thinking=False, date_string=LLAMA_DATE)
    ids = tl.apply_chat_template(hm, tokenize=True, add_generation_prompt=True, enable_thinking=False, date_string=LLAMA_DATE)
    txt_default = tl.apply_chat_template(hm, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    s = lab[(ds, r['id'])]['source_T']; saved = rawline(s['source_path'], s['source_line']); msg = saved['helper_message']
    PH = '<<<XFAM_MESSAGE_PLACEHOLDER>>>'
    mk = lambda m: tq.apply_chat_template([{'role': 'user', 'content': BG.format(question=FMT[ds](q, use_template=False))}, {'role': 'assistant', 'content': m},
                                           {'role': 'user', 'content': FMT[ds](q, use_template=True)}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    small_prompt, ph_prompt = mk(msg), mk(PH)
    n_small = len(tq.apply_chat_template([{'role': 'user', 'content': BG.format(question=FMT[ds](q, use_template=False))}, {'role': 'assistant', 'content': msg},
                                          {'role': 'user', 'content': FMT[ds](q, use_template=True)}], tokenize=True, add_generation_prompt=True, enable_thinking=False))
    ex.append(dict(dataset=ds, id=r['id'], llama_helper_prompt_rendered=txt, llama_bos_count=ids.count(tl.bos_token_id), llama_bos_id=tl.bos_token_id,
                   fixed_date_present=f'Today Date: {LLAMA_DATE}' in txt, default_render_differs_by_date_only=txt_default.replace(txt_default.split('Today Date: ')[1].split('\n')[0], LLAMA_DATE) == txt if 'Today Date: ' in txt_default else None,
                   receiver_prompt_differs_only_in_message=ph_prompt.replace(PH, msg) == small_prompt and ph_prompt.count(PH) == 1,
                   small_pair_saved_T_input_tokens=saved['receiver_input_tokens'], rebuilt_small_T_input_tokens=n_small, saved_record=f"{s['source_path']}:{s['source_line']}"))
out['C_examples'] = ex
for e in ex: print('C', {k: v for k, v in e.items() if k != 'llama_helper_prompt_rendered'}, flush=True)
# ---- D1: prompt identity (task E) still applies to the unchanged overlay
pi = read(X / 'x1_optionB/PROMPT_IDENTITY.json')
out['D1'] = dict(overlay_sha256_now=sha(EVALUATOR), overlay_sha256_at_check=pi['evaluator_sha256'], unchanged=sha(EVALUATOR) == pi['evaluator_sha256'],
                 results={k: {kk: v[kk] for kk in ['n', 'user_message_equal', 'rendered_equal', 'ids_equal', 'K_not_4', 'K_not_4_all_equal']} for k, v in pi['results'].items()})
print('D1', out['D1'], flush=True)
# ---- freeze inputs: chat templates and generation configs (after the paper's apply_generation_config)
class M: pass
def gen(path):
    m = M(); m.generation_config = GenerationConfig.from_pretrained(path); protocol_min.apply_generation_config(m, {'do_sample': False, 'max_new_tokens': 64}); return m.generation_config.to_dict()
gl, gq = gen(LLAMA['path']), gen(QWEN06['path'])
out['freeze_inputs'] = dict(llama_chat_template_sha256=hashlib.sha256(tl.chat_template.encode()).hexdigest(), llama_date_string=LLAMA_DATE,
                            llama_generation_config={k: gl.get(k) for k in ['do_sample', 'max_new_tokens', 'eos_token_id', 'pad_token_id', 'bos_token_id', 'temperature', 'top_p']},
                            qwen06_chat_template_sha256=hashlib.sha256(tq.chat_template.encode()).hexdigest(),
                            qwen06_generation_config_equals_frozen_small=gq == read(P210 / 'frozen_config.json')['pair_configs']['small']['receiver_generation_config'])
print('FREEZE_INPUTS', out['freeze_inputs'], flush=True)
save(X1 / 'notes/prepare_checks.json', out)
