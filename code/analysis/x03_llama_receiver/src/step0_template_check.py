"""X3 Step 0 supplement (tokenizers only, no model output, no gold): render the X2 R / Text / probe message lists of OBQA fit row 1
with each candidate receiver's default chat template; BOS counts of the paper's R-path tokenization (tokenizer(rendered)) vs
apply_chat_template(tokenize=True); default system text. Mistral is loaded with sentencepiece from a scratch overlay (sys.path) only.
Writes notes/STEP0_TEMPLATE_CHECK.json."""
import sys
sys.dont_write_bytecode = True
import json, pathlib, hashlib
X = pathlib.Path(__file__).resolve().parents[1]; ROOT = X.parent
if len(sys.argv) > 1: sys.path.append(sys.argv[1])   # sentencepiece overlay (scratch), for Mistral only
sys.path.insert(0, str(ROOT / 'P2_10_20260911T122423Z')); import protocol_min, legacy_methods
from transformers import AutoTokenizer
POP = ROOT / 'P2_R1_XFAM_20260919T095058Z/records/populations'
r = json.loads(open(POP / 'obqa_fit.jsonl').readline()); q = r['query']
msgR = [{'role': 'user', 'content': protocol_min.format_openbook(q, use_template=True)}]
msgT = [{'role': 'user', 'content': legacy_methods.BACKGROUND_PROMPT.format(question=protocol_min.format_openbook(q, use_template=False))},
        {'role': 'assistant', 'content': r['helper_message']}, msgR[0]]
S = json.load(open(X / 'notes/STEP0_RECEIVER_CHECK.json'))['models']
out = {}
for repo, m in S.items():
    src = m['tokenizer_source']; o = out[repo] = dict(tokenizer_source=src)
    try:
        tok = AutoTokenizer.from_pretrained(src, local_files_only=True)
    except Exception as e:
        o['load_error'] = str(e)[:200]; continue
    rR = tok.apply_chat_template(msgR, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    rT = tok.apply_chat_template(msgT, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    nat = tok.apply_chat_template(msgR, tokenize=True, add_generation_prompt=True, enable_thinking=False)
    paper = tok(rR)['input_ids']; bos = tok.bos_token_id
    o.update(bos_token=tok.bos_token, bos_id=bos, add_bos_on_call=tok('x')['input_ids'][:1] == [bos] if bos is not None else False,
             R_rendered=rR, T_rendered_head=rT[:400], R_rendered_sha256=hashlib.sha256(rR.encode()).hexdigest(),
             bos_count_paper_R_path=paper.count(bos) if bos is not None else 0, bos_count_native=nat.count(bos) if bos is not None else 0,
             paper_R_ids_equal_native=paper == nat, paper_R_ids_equal_native_without_added_special=tok(rR, add_special_tokens=False)['input_ids'] == nat,
             tokenizer_class=type(tok).__name__, chat_template_sha256=hashlib.sha256(tok.chat_template.encode()).hexdigest())
    if 'mistral' in repo:
        from transformers import GenerationConfig
        sets = {l: [] for l in 'ABCDE'}; special = set(tok.all_special_ids)
        for v in sorted(set(tok.get_vocab().values())):
            if v in special: continue
            d = tok.decode([v], skip_special_tokens=False, clean_up_tokenization_spaces=False)
            if d.strip() in sets: sets[d.strip()].append(v)
        allv = [v for s in sets.values() for v in s]; pid = tok.encode('The correct answer is', add_special_tokens=False)
        o['label_rule_with_sentencepiece_overlay'] = dict(sets=sets, nonempty=all(sets.values()), disjoint=len(set(allv)) == len(allv),
                                                          encode_label_alone={l: tok.encode(l, add_special_tokens=False) for l in 'ABCDE'},
                                                          prefix_ids=pid, prefix_roundtrip=tok.decode(pid, skip_special_tokens=False, clean_up_tokenization_spaces=False) == 'The correct answer is')
json.dump(out, open(X / 'notes/STEP0_TEMPLATE_CHECK.json', 'w'), indent=1)
for k, o in out.items():
    print('==', k); print({a: b for a, b in o.items() if a not in ('R_rendered', 'T_rendered_head')}); print(repr(o.get('R_rendered', ''))[:900])
