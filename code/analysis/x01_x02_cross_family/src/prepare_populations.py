"""Build the X2 populations (gold-free) with the reused large-pair helper messages, and run the A3 checks (CPU, tokenizers only).

OBQA/ARC: paper splits P2_CONFIDENCE_REFERENCE_BOUNDARIES splits/{ds}_{fit,cal,dev}_ids.json (all rows) + *_representatives.json
          (certification units); queries BND inputs; helper messages = large-pair saved Text records (V2 labels source_T).
MMLU-Pro: group representatives of MMLU stage-1 splits/{fit,cal,dev}_groups.json; query and helper message from the saved
          large-pair Text action records (shards/*/actions/*.jsonl).
Writes records/populations/*.jsonl, POPULATION_MANIFEST.json, notes/A3_checks.json.
"""
import sys
sys.dont_write_bytecode = True
import importlib.util, ast, glob
from xfam_common import *
from transformers import AutoTokenizer
sys.path.insert(0, str(P210)); import protocol_min, arc_protocol
sys.path.insert(0, str(BND / 'src')); import receiver_prompt as brp


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


mprompt = load_module(MMLU / 'protocol/receiver_prompt.py', 'mmlu_receiver_prompt_x')
BACKGROUND_PROMPT = next(ast.literal_eval(n.value) for n in ast.parse((P210 / 'legacy_methods.py').read_text()).body
                         if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'BACKGROUND_PROMPT')
BODY = {'obqa': lambda q: protocol_min.format_openbook(q, use_template=False), 'arc': lambda q: arc_protocol.helper_body(q),
        'mmlu_pro': lambda q: mprompt.build_prompt(dataset='mmlu-redux', locale='', question=q['question_stem'],
                                                   choices=mprompt.choices_block(q['choice_text']), use_cot=False, use_template=False)}
t7 = AutoTokenizer.from_pretrained(ROOT / 'P2_6_20260910T164138Z/assets/Qwen2.5-7B-Instruct', local_files_only=True)
sources, pops, checks = {}, {}, {'helper_input_rebuilt_equals_saved': {}, 'saved_message_decodes_from_saved_ids': {}, 'examples': []}


def helper_check(ds, q, rec, helper_ids, msg, n_saved, tag):
    ids = t7.apply_chat_template([{'role': 'user', 'content': BACKGROUND_PROMPT.format(question=BODY[ds](q))}], tokenize=True, add_generation_prompt=True, enable_thinking=False)
    ok_n = len(ids) == n_saved
    ok_d = t7.decode(helper_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False) == msg
    checks['helper_input_rebuilt_equals_saved'][ds] = checks['helper_input_rebuilt_equals_saved'].get(ds, 0) + ok_n
    checks['saved_message_decodes_from_saved_ids'][ds] = checks['saved_message_decodes_from_saved_ids'].get(ds, 0) + ok_d
    return ids, ok_n, ok_d


# ---- OBQA / ARC
lab = {}
for name in ['full_train', 'full_development']:
    f = V2L / f'{name}_P2_SCORING_V2.jsonl'; sources[str(f)] = sha(f)
    for r in jl(f):
        if r['pair'] == 'large':
            lab[(r['dataset'], r['id'])] = r
for ds in ['obqa', 'arc']:
    Q = {}
    for s in ['train', 'dev']:
        f = BND / f'inputs/{ds}_{s}_queries.jsonl'; sources[str(f)] = sha(f)
        for r in jl(f): Q[r['id']] = r
    for sp in ['fit', 'cal', 'dev']:
        fi, fr = BND / f'splits/{ds}_{sp}_ids.json', BND / f'splits/{ds}_{sp}_representatives.json'
        sources[str(fi)] = sha(fi); sources[str(fr)] = sha(fr)
        ids, reps = read(fi), set(read(fr))
        assert reps <= set(ids)
        rows = []
        for i in ids:
            s = lab[(ds, i)]['source_T']; x = rawline(s['source_path'], s['source_line']); sources.setdefault(s['source_path'], sha(s['source_path']))
            assert x['id'] == i and x['action'] == 'text' and not x.get('runtime_error')
            q = runtime_query(Q[i]); legal = brp.display_labels(len(q['choice_text'])); assert legal == q['choice_labels']
            _, ok_n, ok_d = helper_check(ds, q, x, x['helper_generated_token_ids'], x['helper_message'], x['helper_input_tokens'], i)
            rows.append(dict(dataset=ds, split=sp, id=i, representative=i in reps, query=q, legal_labels=legal, helper_message=x['helper_message'],
                             helper_message_sha256=hashlib.sha256(x['helper_message'].encode()).hexdigest(), helper_source=f"{s['source_path']}:{s['source_line']}",
                             helper_input_tokens_saved=x['helper_input_tokens']))
        pops[(ds, sp)] = rows

# ---- MMLU-Pro
T = {}
for f in sorted(glob.glob(str(MMLU / 'shards/*/actions/*.jsonl'))):
    sources[f] = sha(f)
    with open(f) as fh:
        for n, line in enumerate(fh, start=1):
            r = json.loads(line)
            if r['action'] == 'T':
                assert r['id'] not in T; T[r['id']] = (f, n, r)
fq = MMLU / 'inputs/queries_only.jsonl'; sources[str(fq)] = sha(fq); QM = {r['id']: r for r in jl(fq)}
missing = {}
for sp in ['fit', 'cal', 'dev']:
    fg = MMLU / f'splits/{sp}_groups.json'; sources[str(fg)] = sha(fg)
    ids = [g['representative_id'] for g in read(fg)]
    missing[sp] = [i for i in ids if i not in T]
    rows = []
    for i in ids:
        if i not in T: continue
        f, n, x = T[i]
        assert not x['runtime_failure'] and x['query']['id'] == i
        qr = {k: x['query'][k] for k in ['question_stem', 'choice_labels', 'choice_text']}
        assert qr == {k: QM[i][k] for k in qr}, i
        q = runtime_query(qr); legal = mprompt.display_labels(len(q['choice_text'])); assert legal == q['choice_labels']
        o = x['output']
        helper_check('mmlu_pro', q, x, o['helper_generated_token_ids'], o['helper_message'], o['helper_input_tokens'], i)
        rows.append(dict(dataset='mmlu_pro', split=sp, id=i, representative=True, query=q, legal_labels=legal, helper_message=o['helper_message'],
                         helper_message_sha256=hashlib.sha256(o['helper_message'].encode()).hexdigest(), helper_source=f'{f}:{n}',
                         helper_input_tokens_saved=o['helper_input_tokens']))
    pops[('mmlu_pro', sp)] = rows

# ---- 3 detailed MMLU-Pro examples (same per-row check as the OBQA/ARC examples)
for i in [pops[('mmlu_pro', 'fit')][0]['id'], pops[('mmlu_pro', 'cal')][0]['id'], pops[('mmlu_pro', 'dev')][0]['id']]:
    f, n, x = T[i]; q = runtime_query({k: x['query'][k] for k in ['question_stem', 'choice_labels', 'choice_text']})
    ids = t7.apply_chat_template([{'role': 'user', 'content': BACKGROUND_PROMPT.format(question=BODY['mmlu_pro'](q))}], tokenize=True, add_generation_prompt=True, enable_thinking=False)
    checks['examples'].append(dict(id=i, split=x['split'], saved_record=f"{f.split('iclr2027_p2/')[1]}:{n}", helper_input_ids_sha256=hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
                                   helper_input_tokens_rebuilt=len(ids), helper_input_tokens_saved=x['output']['helper_input_tokens'],
                                   X2_equals_large_bytes=True, reason='helper input is built from the question and the helper tokenizer only (T2THelperBundle.prepare)',
                                   saved_message_decodes_from_saved_ids=t7.decode(x['output']['helper_generated_token_ids'], skip_special_tokens=True, clean_up_tokenization_spaces=False) == x['output']['helper_message']))

# ---- OLMo label sets A..J
to = AutoTokenizer.from_pretrained(RECEIVERS['olmo2_7b']['path'], local_files_only=True)
sets = {l: [] for l in LABELS_ALL}; special = set(to.all_special_ids)
for v in sorted(set(to.get_vocab().values())):
    if v in special: continue
    d = to.decode([v], skip_special_tokens=False, clean_up_tokenization_spaces=False)
    if d.strip() in sets: sets[d.strip()].append(v)
allv = [v for s in sets.values() for v in s]
checks['olmo_label_sets_A_J'] = dict(nonempty=all(sets.values()), disjoint=len(set(allv)) == len(allv), counts={l: len(v) for l, v in sets.items()}, sets=sets)
checks['mmlu_missing_saved_T'] = {k: len(v) for k, v in missing.items()}
checks['counts'] = {f'{d}_{s}': len(r) for (d, s), r in pops.items()}
checks['representatives'] = {f'{d}_{s}': sum(x['representative'] for x in r) for (d, s), r in pops.items()}
for (d, s), rows in pops.items():
    p = POP / f'{d}_{s}.jsonl'; p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w') as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + '\n')
save(POP / 'POPULATION_MANIFEST.json', dict(utc=utc(), files={f'{d}_{s}.jsonl': dict(n=len(r), sha256=sha(POP / f'{d}_{s}.jsonl')) for (d, s), r in pops.items()},
                                            sources=sources, gold_read=False))
save(X / 'notes/A3_checks.json', checks)
print(json.dumps({k: v for k, v in checks.items() if k != 'olmo_label_sets_A_J'}, indent=1))
print('olmo', {k: v for k, v in checks['olmo_label_sets_A_J'].items() if k != 'sets'})
