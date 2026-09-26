"""Descriptive (no rerun, tokenizer only + stored records): did X2's OLMo-2 inputs contain a duplicated BOS?
(1) stored X2 run records: probe flag native_ids_equal_retokenized_rendered (= tokenizer(rendered) used by the paper R path equals
    apply_chat_template ids) and R receiver_input_tokens == probe input_tokens - len(prefix);
(2) OLMo tokenizer on all 17,267 X2 rows: leading-BOS count of the R-path ids (tokenizer(rendered), as run), probe ids, Text-path ids.
-> notes/X2_OLMO_BOS_CHECK.json"""
import sys
sys.dont_write_bytecode = True
import glob, collections
from xfam_common import *
X2 = ROOT / 'P2_R1_XFAM_20260919T095058Z'
from transformers import AutoTokenizer
sys.path.insert(0, str(P210)); import protocol_min, legacy_methods
FMT = {'obqa': protocol_min.format_openbook}
import arc_runtime_adapter; FMT['arc'] = protocol_min.format_openbook
sys.path.insert(0, str(MMLU / 'src')); import native_runtime as nr; FMT['mmlu_pro'] = protocol_min.format_openbook
tok = AutoTokenizer.from_pretrained(RECEIVERS['olmo2_7b']['path'], local_files_only=True); B = tok.bos_token_id
lead = lambda ids: next((i for i, v in enumerate(ids) if v != B), len(ids))
out = dict(utc=utc(), olmo_bos_token=tok.bos_token, bos_id=B, eos_id=tok.eos_token_id, tokenizer_adds_bos_on_call=tok('x')['input_ids'][:1] == [B])
st = collections.Counter(); npre = len(tok.encode(PREFIX, add_special_tokens=False))
for f in sorted(glob.glob(str(X2 / 'results/runs/chain_*.jsonl'))):
    for r in jl(f):
        st['rows'] += 1
        if r.get('runtime_error'): st['runtime_error'] += 1; continue
        st['probe_native_equals_retokenized'] += r['P']['native_ids_equal_retokenized_rendered']
        st['R_len_equals_probe_len_minus_prefix'] += r['R']['receiver_input_tokens'] == r['P']['input_tokens'] - npre
out['stored_x2_records'] = dict(st)
c = collections.Counter()
for ds in ['obqa', 'arc', 'mmlu_pro']:
    for sp in ['fit', 'cal', 'dev']:
        for r in jl(X2 / f'records/populations/{ds}_{sp}.jsonl'):
            q = r['query']
            protocol_min.format_openbook = FMT[ds]; legacy_methods.format_openbook = FMT[ds]
            mR = [{'role': 'user', 'content': FMT[ds](q, use_template=True)}]
            mT = [{'role': 'user', 'content': legacy_methods.BACKGROUND_PROMPT.format(question=FMT[ds](q, use_template=False))},
                  {'role': 'assistant', 'content': r['helper_message']}, mR[0]]
            rR = tok.apply_chat_template(mR, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            idsR = tok(rR)['input_ids']; idsP = tok.apply_chat_template(mR, tokenize=True, add_generation_prompt=True, enable_thinking=False)
            idsT = tok.apply_chat_template(mT, tokenize=True, add_generation_prompt=True, enable_thinking=False)
            c['rows'] += 1
            for k, ids in [('R_path', idsR), ('probe', idsP), ('T_path', idsT)]:
                c[f'{k}_leading_bos={lead(ids)}'] += 1
out['tokenizer_render_all_x2_rows'] = dict(sorted(c.items()))
out['duplicated_bos_rows'] = sum(v for k, v in c.items() if '_leading_bos=' in k and int(k.split('=')[1]) >= 2)
save(X / 'notes/X2_OLMO_BOS_CHECK.json', out); print(json.dumps(out, indent=1))
