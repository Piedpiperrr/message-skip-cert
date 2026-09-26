"""Fixed work lists (first rows of each fit split, in paper split order) and CPU-only freeze inputs for OLMo."""
import sys
sys.dont_write_bytecode = True
from xfam_common import *
W = X / 'records/work'; W.mkdir(parents=True, exist_ok=True)
fit = {ds: jl(POP / f'{ds}_fit.jsonl') for ds in DATASETS}
def dump(name, rows):
    with open(W / name, 'w') as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    return sha(W / name)
out = dict(validate_rows=dump('validate_rows.jsonl', fit['obqa'][:8] + fit['arc'][:8] + fit['mmlu_pro'][:4]),
           smoke_rows=dump('smoke_rows.jsonl', fit['obqa'][:6] + fit['arc'][:6] + fit['mmlu_pro'][:4]))
# OLMo chat template / generation config (after the paper's apply_generation_config) / rendered examples, tokenizer only
from transformers import AutoTokenizer, GenerationConfig
sys.path.insert(0, str(P210)); import protocol_min, legacy_methods
FMT = {'obqa': protocol_min.format_openbook}
import arc_runtime_adapter; FMT['arc'] = protocol_min.format_openbook
sys.path.insert(0, str(MMLU / 'src')); import native_runtime as nr; FMT['mmlu_pro'] = protocol_min.format_openbook
p = RECEIVERS['olmo2_7b']['path']; tok = AutoTokenizer.from_pretrained(p, local_files_only=True)
class M: pass
m = M(); m.generation_config = GenerationConfig.from_pretrained(p)
protocol_min.apply_generation_config(m, {'do_sample': False, 'max_new_tokens': 64})
g = m.generation_config.to_dict()
ex = {}
for ds in DATASETS:
    r = fit[ds][0]; q = r['query']
    msgR = [{'role': 'user', 'content': FMT[ds](q, use_template=True)}]
    msgT = [{'role': 'user', 'content': legacy_methods.BACKGROUND_PROMPT.format(question=FMT[ds](q, use_template=False))},
            {'role': 'assistant', 'content': r['helper_message']}, {'role': 'user', 'content': FMT[ds](q, use_template=True)}]
    ex[ds] = dict(id=r['id'], R_rendered=tok.apply_chat_template(msgR, tokenize=False, add_generation_prompt=True, enable_thinking=False),
                  T_rendered=tok.apply_chat_template(msgT, tokenize=False, add_generation_prompt=True, enable_thinking=False),
                  probe_decoded=tok.decode(tok.apply_chat_template(msgR, tokenize=True, add_generation_prompt=True, enable_thinking=False) + tok.encode(PREFIX, add_special_tokens=False), skip_special_tokens=False))
out.update(olmo_chat_template_sha256=hashlib.sha256(tok.chat_template.encode()).hexdigest(), olmo_generation_config=g,
           olmo_eos=g.get('eos_token_id'), olmo_pad=g.get('pad_token_id'), rendered_examples=ex,
           system_prompt_in_R_render=any('<|system|>' in e['R_rendered'] for e in ex.values()))
save(X / 'notes/freeze_inputs.json', out)
print(json.dumps({k: v for k, v in out.items() if k != 'rendered_examples'}, indent=1)); print(repr(ex['mmlu_pro']['T_rendered'][:700]))
