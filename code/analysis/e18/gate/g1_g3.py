"""E18 Step 0, G1/G2/G3/G5 (login node, tokenizer only, no model weights, no gold).
Reads the E10 records read-only; writes only into this E18 stage."""
import sys, json, glob, hashlib
sys.dont_write_bytecode = True
from pathlib import Path
from collections import Counter

ROOT = Path('$DATA_DIR')
E10 = ROOT / 'P2_R4_E10_20260920T225954Z'
OUT = Path(__file__).resolve().parents[1] / 'gate'
sys.path.insert(0, str(E10 / 'src'))
import e10_prompts as PR
CFG = json.loads((ROOT / 'P2_R3_E9BC_20260920T061042Z/large/frozen_config.json').read_text())['native']
spec = CFG['models']['receiver']

rows = [json.loads(l) for f in sorted(glob.glob(str(E10 / 'records/main_rank*.jsonl'))) for l in open(f) if l.strip()]
SPL = {s: json.loads((E10 / f'splits/gsm8k_{s}_ids.json').read_text()) for s in ['fit', 'cal', 'dev']}
QUERIES = {json.loads(l)['id']: json.loads(l) for l in open(E10 / 'inputs/gsm8k_queries.jsonl')}
rep = {}
rep['record_counts'] = {'%s %s' % k: v for k, v in sorted(Counter((r['split'], r['action']) for r in rows).items())}
rep['split_sizes'] = {s: len(v) for s, v in SPL.items()}
rep['record_keys'] = sorted({k for r in rows for k in r})
rep['query_keys'] = sorted({k for q in QUERIES.values() for k in q})
rep['gold_like_keys'] = [k for k in rep['record_keys'] + rep['query_keys']
                         if any(s in k.lower() for s in ['gold', 'label', 'correct', 'target'])]
dup = Counter((r['split'], r['action'], r['id']) for r in rows)
rep['duplicate_records'] = sum(v > 1 for v in dup.values())

# ---- G2: receiver tokenizer / template
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained(spec['path'], local_files_only=True)
rep['receiver'] = {'repo_id': spec['repo_id'], 'revision': spec['revision'], 'path': spec['path'],
                   'chat_template_sha256_expected': spec['chat_template_sha256'],
                   'chat_template_sha256_actual': hashlib.sha256(tok.chat_template.encode()).hexdigest(),
                   'dtype': CFG.get('dtype'), 'attention': CFG.get('attention'), 'tf32': CFG.get('tf32'),
                   'thinking': CFG.get('thinking'), 'eos_token_id': CFG['receiver_generation_config']['eos_token_id']}
EOS = set(CFG['receiver_generation_config']['eos_token_id'])

# ---- G3: token positions
by = {(r['split'], r['action'], r['id']): r for r in rows}
R = [by[(s, 'R', i)] for s in ['fit', 'cal', 'dev'] for i in SPL[s]]
bad = {'n_gen_tokens_ne_len_ids': [], 'eos_not_last': [], 'decode_ne_raw_answer': [],
       'prompt_len_ne_receiver_input_tokens': [], 'rescore_ids_ne_generated_prefix': [],
       'retokenized_raw_answer_ne_content_ids': []}
lens, ends_eos = [], 0
for r in R:
    g = r['generated_token_ids']
    if r['n_gen_tokens'] != len(g): bad['n_gen_tokens_ne_len_ids'].append(r['id'])
    if any(t in EOS for t in g[:-1]): bad['eos_not_last'].append(r['id'])
    e = bool(g) and g[-1] in EOS
    ends_eos += e
    content = g[:-1] if e else g
    lens.append(len(content))
    if tok.decode(g, skip_special_tokens=True).strip('\n') != r['raw_answer']:
        bad['decode_ne_raw_answer'].append(r['id'])
    rendered = tok.apply_chat_template(PR.receiver_only_messages(QUERIES[r['id']]['question']),
                                       tokenize=False, add_generation_prompt=True, enable_thinking=False)
    if len(tok(rendered)['input_ids']) != r['receiver_input_tokens']:
        bad['prompt_len_ne_receiver_input_tokens'].append(r['id'])
    rs = r['rescore']
    if rs is not None:
        cat = rs['prefix_token_ids'] + rs['answer_token_ids']
        if cat != g[:len(cat)]: bad['rescore_ids_ne_generated_prefix'].append(r['id'])
    if tok(r['raw_answer'], add_special_tokens=False)['input_ids'] != content:
        bad['retokenized_raw_answer_ne_content_ids'].append(r['id'])

fit_R = [by[('fit', 'R', i)] for i in SPL['fit']]
pre_ids = SPL['fit'][:16] + [r['id'] for r in fit_R if r['u'] > 0 and r['id'] not in SPL['fit'][:16]]
rep['preflight_rows'] = {'n': len(pre_ids), 'first16': SPL['fit'][:16],
                         'u_gt_0_fit_rows': sum(r['u'] > 0 for r in fit_R),
                         'u_gt_0_in_first16': sum(by[('fit', 'R', i)]['u'] > 0 for i in SPL['fit'][:16]),
                         'ids': pre_ids}
rep['G3'] = {'token_id_source': 'stored generated_token_ids (E10 main records)', 'n_R_rows': len(R),
             'rows_ending_in_eos': ends_eos, 'rows_without_eos': len(R) - ends_eos,
             'content_len_min': min(lens), 'content_len_max': max(lens),
             'content_len_lt_32': sum(l < 32 for l in lens),
             'mismatch_counts': {k: len(v) for k, v in bad.items()},
             'mismatch_ids': {k: v[:20] for k, v in bad.items()},
             'preflight_rows_with_any_mismatch': sorted({i for v in bad.values() for i in v} & set(pre_ids))}
rep['G3']['rescore_rows'] = sum(r['rescore'] is not None for r in R)

# smoke vs main for the 16 smoke fit rows (stored values only)
sm = {json.loads(l)['id']: json.loads(l) for f in sorted(glob.glob(str(E10 / 'records/smoke_rank*.jsonl')))
      for l in open(f) if json.loads(l)['action'] == 'R'}
rep['smoke_vs_main'] = {'n': len(sm),
                        'generated_ids_equal': sum(sm[i]['generated_token_ids'] == by[('fit', 'R', i)]['generated_token_ids'] for i in sm),
                        's2_equal': sum(sm[i]['s2'] == by[('fit', 'R', i)]['s2'] for i in sm),
                        'u_equal': sum(sm[i]['u'] == by[('fit', 'R', i)]['u'] for i in sm)}
rep['timing_fields'] = sorted({k for r in rows for k in r if any(s in k for s in ['latency', 'time', 'ms', 'seconds'])})
(OUT / 'G1_G3.json').write_text(json.dumps(rep, indent=1) + '\n')
print(json.dumps({k: v for k, v in rep.items() if k not in ('record_keys',)}, indent=1)[:6000])
