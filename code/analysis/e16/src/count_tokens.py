"""E16-3 planning (login node, tokenizer only; no model, no gold): probe input tokens for every fit/cal/dev representative of OBQA, ARC and
MMLU-Pro, built exactly as e16_probe.py builds them (Qwen3 tokenizer; the three Qwen3 receivers share it: asserted). Also writes the E16-3 row
files records/work/e163_<bench>_<split>.jsonl. -> notes/TOKEN_COUNTS.json"""
import sys
sys.dont_write_bytecode = True
from xfam_common import *
from transformers import AutoTokenizer
sys.path.insert(0, str(P210)); import protocol_min, legacy_methods
FMT = {'obqa': protocol_min.format_openbook}
import arc_runtime_adapter; FMT['arc'] = protocol_min.format_openbook
sys.path.insert(0, str(MMLU / 'src')); import native_runtime as nr; FMT['mmlu_pro'] = protocol_min.format_openbook
toks = {r: AutoTokenizer.from_pretrained(RECEIVERS[r]['path'], local_files_only=True) for r in ['qwen3_0_6b', 'qwen3_1_7b', 'qwen3_8b']}
assert len({t.chat_template for t in toks.values()}) == 1 and len({json.dumps(t.get_vocab(), sort_keys=True) for t in toks.values()}) == 1
tok = toks['qwen3_8b']; pre = len(tok.encode(PREFIX, add_special_tokens=False))
src = {'obqa': lambda sp: jl(X3 / f'records/populations/obqa_{sp}.jsonl'), 'arc': lambda sp: [r for r in jl(X3 / f'records/populations/arc_{sp}.jsonl') if r['representative']],
       'mmlu_pro': lambda sp: jl(XFAM / f'records/populations/mmlu_pro_{sp}.jsonl')}
W = X / 'records/work'; out = dict(utc=utc(), note='tokenizer shared by Qwen3-0.6B/1.7B/8B (asserted)', counts={})
for ds in ['obqa', 'arc', 'mmlu_pro']:
    protocol_min.format_openbook = FMT[ds]; legacy_methods.format_openbook = FMT[ds]
    for sp in ['fit', 'cal', 'dev']:
        rows = src[ds](sp); n = []
        for r in rows:
            ids = tok.apply_chat_template([{'role': 'user', 'content': FMT[ds](r['query'], use_template=True)}], tokenize=True, add_generation_prompt=True, enable_thinking=False)
            n.append(len(ids) + pre)
        with open(W / f'e163_{ds}_{sp}.jsonl', 'w') as f:
            for r in rows: f.write(json.dumps(dict(dataset=ds, split=sp, id=r['id'], query=r['query'], legal_labels=r['legal_labels']), ensure_ascii=False) + '\n')
        out['counts'][f'{ds}/{sp}'] = dict(rows=len(rows), tokens=sum(n), mean=sum(n) / len(n), max=max(n))
out['total_rows'] = sum(v['rows'] for v in out['counts'].values()); out['total_tokens'] = sum(v['tokens'] for v in out['counts'].values())
save(X / 'notes/TOKEN_COUNTS.json', out); print(json.dumps(out, indent=1))
