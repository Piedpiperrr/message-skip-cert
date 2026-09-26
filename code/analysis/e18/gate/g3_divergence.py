"""E18 G3 detail: first divergence index between stored generated ids and (a) E10 rescore ids, (b) re-tokenized raw_answer.
Tokenizer only; no weights; no gold; no scores computed."""
import sys, json, glob
sys.dont_write_bytecode = True
from pathlib import Path
ROOT = Path('$DATA_DIR')
E10 = ROOT / 'P2_R4_E10_20260920T225954Z'
from transformers import AutoTokenizer
CFG = json.loads((ROOT / 'P2_R3_E9BC_20260920T061042Z/large/frozen_config.json').read_text())['native']
tok = AutoTokenizer.from_pretrained(CFG['models']['receiver']['path'], local_files_only=True)
EOS = set(CFG['receiver_generation_config']['eos_token_id'])
G = json.load(open(Path(__file__).parent / 'G1_G3.json'))
pre = set(G['preflight_rows']['ids'])
rows = {(r['split'], r['id']): r for f in sorted(glob.glob(str(E10 / 'records/main_rank*.jsonl'))) for l in open(f) if l.strip()
        for r in [json.loads(l)] if r['action'] == 'R'}
def first_div(a, b):
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]: k += 1
    return k
out = []
for kind in ['rescore_ids_ne_generated_prefix', 'retokenized_raw_answer_ne_content_ids']:
    for i in G['G3']['mismatch_ids'][kind]:
        (s, _), r = [(k, v) for k, v in rows.items() if k[1] == i][0]
        g = r['generated_token_ids']; c = g[:-1] if g and g[-1] in EOS else g
        other = (r['rescore']['prefix_token_ids'] + r['rescore']['answer_token_ids']) if kind.startswith('rescore') \
            else tok(r['raw_answer'], add_special_tokens=False)['input_ids']
        k = first_div(c, other)
        n_pre = len(r['rescore']['prefix_token_ids'])
        d = {'kind': kind, 'id': i, 'split': s, 'preflight': i in pre, 'L': len(c), 'first_divergence_index0': k,
             'len_other': len(other), 'rescore_prefix_len': n_pre, 'rescore_answer_len': len(r['rescore']['answer_token_ids']),
             'u': r['u'], 'extract_route': r['extract_route'],
             'gen_tokens_at_div': [tok.decode([t]) for t in c[k:k + 3]], 'other_tokens_at_div': [tok.decode([t]) for t in other[k:k + 3]]}
        out.append(d); print(d)
json.dump(out, open(Path(__file__).parent / 'G3_divergence.json', 'w'), indent=1)
