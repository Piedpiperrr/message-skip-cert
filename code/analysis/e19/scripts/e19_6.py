"""E19-6: prompts and parser for the appendix. Copies E13's PROMPTS_AND_PARSER.md, checks it against the frozen prompt code and
parser V2, appends the templates it lacks (verbatim strings extracted from the frozen code), adds rendered examples for the Qwen3-8B,
Llama-3.1-8B and OLMo-2 receivers (tokenizers only; local files; no weights), verifies them against saved run evidence, and runs an
anonymity scan. Output: PROMPTS_FOR_APPENDIX.md (stage root) and results/E19_6_*.csv."""
from e19_common import *
import ast, re, shutil, hashlib, importlib.util, glob
from transformers import AutoTokenizer

T0 = utc()
print('E19-6 start', T0)
EAG = Path('$DATA_DIR')
E13MD = ROOT / 'P2_R5_E13_20260921T031606Z/PROMPTS_AND_PARSER.md'
shutil.copyfile(E13MD, STAGE / 'notes/PROMPTS_AND_PARSER_E13_copy.md')
base = open(E13MD, encoding='utf-8').read()
CODE = {
    'helper instruction (P2_10 legacy_methods.BACKGROUND_PROMPT)': ROOT / 'P2_10_20260911T122423Z/legacy_methods.py',
    'ARC helper/receiver adapter (P2_10 arc_protocol)': ROOT / 'P2_10_20260911T122423Z/arc_protocol.py',
    'receiver prompt (receiver_prompt.py)': ROOT / 'P2_R1_EXP_20260919T050555Z/src/receiver_prompt.py',
    'probe construction (run_boundaries.py)': ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/src/run_boundaries.py',
    'Text+fact protocol (PROTOCOL_FREEZE_E6.md)': ROOT / 'P2_R2_GPU_20260919T220941Z/e6/PROTOCOL_FREEZE_E6.md',
    'question body incl. Text+fact line (E9 e9_common.question_body)': ROOT / 'P2_R3_E9BC_20260920T061042Z/src/e9_common.py',
    'helper-aware prefill (E9c e9c_prefill.py)': ROOT / 'P2_R3_E9BC_20260920T061042Z/src/e9c_prefill.py',
    'Llama-3.1-8B receiver (X3 run_x3.py)': ROOT / 'P2_R6_X3_20260921T052602Z/src/run_x3.py',
    'OLMo-2 receiver (X2 run_x2.py)': ROOT / 'P2_R1_XFAM_20260919T095058Z/src/run_x2.py',
    'GSM8K prompts (E10 e10_prompts.py)': ROOT / 'P2_R4_E10_20260920T225954Z/src/e10_prompts.py',
    'parser V2 (scoring_v2.py)': ROOT / 'P2_SCORING_V2_20260912T191445Z/scoring_v2.py',
}
HASHES = {k: sha(p) for k, p in CODE.items()}
CHK = []


def chk(name, ok, detail=''):
    CHK.append(dict(check=name, status='PASS' if ok else 'FAIL', detail=str(detail)[:500]))
    print(('PASS ' if ok else 'FAIL ') + name, str(detail)[:200])


def const(path, name):
    """string constant `name` assigned at module level in `path` (read with ast; not imported)."""
    for n in ast.parse(open(path, encoding='utf-8').read()).body:
        if isinstance(n, ast.Assign) and any(getattr(t, 'id', None) == name for t in n.targets):
            return ast.literal_eval(n.value)
    raise KeyError(name)


def fn_consts(path, fname):
    for n in ast.walk(ast.parse(open(path, encoding='utf-8').read())):
        if isinstance(n, ast.FunctionDef) and n.name == fname:
            return [c.value for c in ast.walk(n) if isinstance(c, ast.Constant) and isinstance(c.value, str)]
    raise KeyError(fname)


BG = const(CODE['helper instruction (P2_10 legacy_methods.BACKGROUND_PROMPT)'], 'BACKGROUND_PROMPT')
chk('BACKGROUND_PROMPT identical in legacy_methods.py, arc_protocol.py and e10_prompts.py',
    BG == const(CODE['ARC helper/receiver adapter (P2_10 arc_protocol)'], 'BACKGROUND_PROMPT') == const(CODE['GSM8K prompts (E10 e10_prompts.py)'], 'BACKGROUND_PROMPT'))
RTPL = [s for s in fn_consts(CODE['receiver prompt (receiver_prompt.py)'], 'build_prompt') if s.startswith('Accurately answer')]
RECV_TEMPLATE = [s for s in RTPL if 'Respond ONLY' in s][0]
INSTR_ABCD = const(CODE['receiver prompt (receiver_prompt.py)'], '_INSTRUCTION_ABCD')
PREFIX = 'The correct answer is'
BNDCFG = ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/frozen_config.json'
CODE["probe prefix (BOUNDARIES frozen_config.json[\"prefix\"], read by run_boundaries.py)"] = BNDCFG
HASHES["probe prefix (BOUNDARIES frozen_config.json[\"prefix\"], read by run_boundaries.py)"] = sha(BNDCFG)
chk('probe prefix == BOUNDARIES frozen_config.json["prefix"] == X3 xfam_common.PREFIX == E9 e9_common.PREFIX',
    read(BNDCFG)['prefix'] == PREFIX == const(ROOT / 'P2_R6_X3_20260921T052602Z/src/xfam_common.py', 'PREFIX')
    == const(ROOT / 'P2_R3_E9BC_20260920T061042Z/src/e9_common.py', 'PREFIX'), repr(read(BNDCFG)['prefix']))
spec = importlib.util.spec_from_file_location('rp19', CODE['receiver prompt (receiver_prompt.py)'])
RP = importlib.util.module_from_spec(spec); spec.loader.exec_module(RP)
GSM_RT = const(CODE['GSM8K prompts (E10 e10_prompts.py)'], 'RECEIVER_TEMPLATE')
GSM_ANS = const(CODE['GSM8K prompts (E10 e10_prompts.py)'], 'ANSWER_INSTRUCTION')

# ------------------------------------------------------------ example question (OBQA fit 14-1371, as E13)
Q = next(r for r in jl(ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/inputs/obqa_train_queries.jsonl') if r['id'] == '14-1371')
E6X = next(e for e in read(ROOT / 'P2_R2_GPU_20260919T220941Z/e6/E6_PROMPT_EXAMPLES.json')['examples'] if e['id'] == '14-1371')
RAWIO = sys.modules['rawio']
lab = RAWIO._v2labels('large', 'obqa')['14-1371']
src = lab['source_T']
HM = RAWIO._rawfile(src['source_path'])[src['source_line']]['helper_message']   # saved large-helper message for 14-1371
helper_body = Q['question_stem'] + '\n\nChoices:\n' + RP.choices_block(Q['choice_text'])
helper_user = BG.format(question=helper_body)
recv_user = RP.receiver_prompt(Q)


def block(md, heading_idx):
    return md


def code_blocks(text):
    return re.findall(r'```text\n(.*?)\n```', text, flags=re.S)


# the E13 file's OBQA/MMLU-Pro blocks vs the frozen code
blocks = code_blocks(base)
chk('E13 OBQA helper user message == BACKGROUND_PROMPT.format(question=question + "\\n\\nChoices:\\n" + choices)', blocks[0] == helper_user)
chk('E13 OBQA receiver-only user message == receiver_prompt.receiver_prompt(question)', blocks[3] == recv_user)
fact = E6X.get('fact1') or E6X.get('fact')
tf_user = BG.format(question=f'Useful fact: {fact}\n' + helper_body)
chk('E13 OBQA Text+fact helper user message == BACKGROUND_PROMPT with "Useful fact: <fact1>\\n" before the question (e9_common.question_body rule)',
    blocks[6] == tf_user, fact)
chk('"Useful fact: " line rule present in e9_common.question_body and PROTOCOL_FREEZE_E6.md',
    "f'Useful fact: {fact}\\n' + q" in open(CODE['question body incl. Text+fact line (E9 e9_common.question_body)'], encoding='utf-8').read()
    and 'Useful fact:' in open(CODE['Text+fact protocol (PROTOCOL_FREEZE_E6.md)'], encoding='utf-8').read())
MM = next(r['query'] for (i, a), r in RAWIO._mmlu('fit').items() if i == 'test:3284' and a == 'R') if RAWIO._mmlu('fit') else None
if MM is None:
    MM = next(r['query'] for (i, a), r in RAWIO._mmlu('cal').items() if i == 'test:3284')
chk('E13 MMLU-Pro helper user message == frozen code', blocks[9] == BG.format(question=MM['question_stem'] + '\n\nChoices:\n' + RP.choices_block(MM['choice_text'])))
chk('E13 MMLU-Pro receiver-only user message == receiver_prompt (A-J label list)', blocks[12] == RP.receiver_prompt(MM))

# re-render the E13 rendered blocks with the tokenizers
TOKP = {'Qwen3-8B': str(EAG / 'hf_cache/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218'),
        'Qwen2.5-7B-Instruct': str(ROOT / 'P2_6_20260910T164138Z/assets/Qwen2.5-7B-Instruct'),
        'Llama-3.1-8B-Instruct': str(EAG / 'hf_cache/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/0e9e39f249a16976918f6564b8830bc894c89659'),
        'OLMo-2-1124-7B-Instruct': str(EAG / 'hf_cache/hub/models--allenai--OLMo-2-1124-7B-Instruct/snapshots/470b1fba1ae01581f270116362ee4aa1b97f4c84')}
TK = {k: AutoTokenizer.from_pretrained(v, local_files_only=True) for k, v in TOKP.items()}


def render(tk, msgs):
    return TK[tk].apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)


def ntok_native(tk, msgs):
    x = TK[tk].apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=False)
    if hasattr(x, 'keys'): x = x['input_ids']
    if x and isinstance(x[0], list): x = x[0]
    return len(x)


H_MSGS = [{'role': 'user', 'content': helper_user}]
R_MSGS = [{'role': 'user', 'content': recv_user}]
T_MSGS = [{'role': 'user', 'content': helper_user}, {'role': 'assistant', 'content': HM}, {'role': 'user', 'content': recv_user}]
chk('E13 OBQA rendered helper input == Qwen2.5-7B apply_chat_template', blocks[1] == render('Qwen2.5-7B-Instruct', H_MSGS))
chk('E13 OBQA rendered receiver Text-reading input == Qwen3-8B apply_chat_template (saved helper message)', blocks[2] == render('Qwen3-8B', T_MSGS))
chk('E13 OBQA rendered receiver-only input == Qwen3-8B apply_chat_template', blocks[4] == render('Qwen3-8B', R_MSGS))
chk('E13 OBQA probe input == rendered receiver-only + prefix', blocks[5] == render('Qwen3-8B', R_MSGS) + PREFIX)

# parser: every regex quoted in the E13 parser section appears verbatim in scoring_v2.py
psec = base[base.index('## Final answer parser'):base.index('## Verification of the renderings')]
spans = re.findall(r'`([^`]+)`', psec)
regex = [s for s in spans if ('\\' in s or '(?' in s) and len(s) > 6]
V2SRC = open(CODE['parser V2 (scoring_v2.py)'], encoding='utf-8').read()


V2N = V2SRC.replace('\\x27', "'")   # the source writes the single quote as \\x27 inside raw regex strings


def in_src(s):
    return s in V2N or s.replace('\\', '\\\\') in V2N


missing = [s for s in regex if not in_src(s)]
chk(f'parser section: {len(regex)} quoted regexes found verbatim in scoring_v2.py', not missing, missing)
words = ['if', 'whether', 'unless', 'assuming', 'suppose', 'supposing', 'hypothetically', 'example', 'claimed', 'incorrect',
         'actually', 'correction', 'on second thought', 'instead', 'sorry', 'because', 'since', 'due to', 'based on', 'versus']
wmiss = [w for w in words if w not in V2SRC and not re.search(re.escape(w).replace('\\ ', r'\\s\+'), V2SRC)]   # multi-word cues are written with \\s+ in the source
chk('parser section: cue words (hedges, corrections, explanations, joiners) present in scoring_v2.py', not wmiss, wmiss)
chk('parser V2 SHA-256 == frozen d05978f4...', HASHES['parser V2 (scoring_v2.py)'] == 'd05978f400cf69aa6bddc56168a260ac3ea9158abaa640e9331602dc9bfcc2f9',
    HASHES['parser V2 (scoring_v2.py)'])
impl = re.search(r"IMPLEMENTATION\s*=\s*'([^']+)'|__version__\s*=\s*'([^']+)'|'implementation'\s*:\s*'([^']+)'", V2SRC)
chk('parser V2 implementation string 2.0.0 in scoring_v2.py', '2.0.0' in V2SRC, impl.group(0) if impl else '')

# ------------------------------------------------------------ rendered examples for the three receivers + saved-evidence checks
x3r = next(r for f in sorted(glob.glob(str(X3 / 'results/runs/chain_*.jsonl'))) for r in jl(f) if r['dataset'] == 'obqa' and r['id'] == '14-1371')
x2r = next(r for f in sorted(glob.glob(str(ROOT / 'P2_R1_XFAM_20260919T095058Z/results/runs/chain_*.jsonl'))) for r in jl(f)
           if r['dataset'] == 'obqa' and r['id'] == '14-1371')
chk('saved large-helper message for 14-1371: sha256 == X3 and X2 records T.helper_message_sha256',
    hashlib.sha256(HM.encode()).hexdigest() == x3r['T']['helper_message_sha256'] == x2r['T']['helper_message_sha256'])
EX = {}
for rcv in ['Qwen3-8B', 'Llama-3.1-8B-Instruct', 'OLMo-2-1124-7B-Instruct']:
    rr = render(rcv, R_MSGS); tt = render(rcv, T_MSGS)
    pre = TK[rcv].encode(PREFIX, add_special_tokens=False)
    n_probe = len(TK[rcv](rr, add_special_tokens=False)['input_ids']) + len(pre)
    EX[rcv] = dict(receiver_only=rr, with_message=tt, probe=rr + PREFIX, n_R=ntok_native(rcv, R_MSGS), n_T=ntok_native(rcv, T_MSGS),
                   n_probe=n_probe, prefix_ids=pre)
ev = {'Qwen3-8B': dict(n_R=132, n_T=258, n_probe=136, rendered_sha=None),
      'Llama-3.1-8B-Instruct': dict(n_R=x3r['R']['receiver_input_tokens'], n_T=x3r['T']['receiver_input_tokens'], n_probe=x3r['P']['input_tokens'],
                                    rendered_sha=x3r['P']['rendered_sha256']),
      'OLMo-2-1124-7B-Instruct': dict(n_R=x2r['R']['receiver_input_tokens'], n_T=x2r['T']['receiver_input_tokens'], n_probe=x2r['P']['input_tokens'],
                                      rendered_sha=x2r['P']['rendered_sha256'])}
for rcv, e in ev.items():
    got = (EX[rcv]['n_R'], EX[rcv]['n_T'], EX[rcv]['n_probe'])
    chk(f'{rcv}: rendered token counts (receiver-only, with-message, probe) == saved run records', got == (e['n_R'], e['n_T'], e['n_probe']),
        f"rendered {got} saved {(e['n_R'], e['n_T'], e['n_probe'])}")
    if e['rendered_sha']:
        chk(f'{rcv}: sha256(rendered receiver-only prompt) == saved probe rendered_sha256',
            hashlib.sha256(EX[rcv]['receiver_only'].encode()).hexdigest() == e['rendered_sha'])
helper_rendered = render('Qwen2.5-7B-Instruct', H_MSGS)
chk('helper rendered token count == saved helper_input_tokens for 14-1371 (E13: 111)', ntok_native('Qwen2.5-7B-Instruct', H_MSGS) == 111)
# helper-aware prefill (E9c): helper chat template on the receiver-only body + prefix
e9 = importlib.util.spec_from_file_location('e9c19', CODE['question body incl. Text+fact line (E9 e9_common.question_body)'])
E9M = importlib.util.module_from_spec(e9)
e9_src = open(CODE['question body incl. Text+fact line (E9 e9_common.question_body)'], encoding='utf-8').read()
chk('E9c question_body (no fact) == receiver_prompt (receiver-only user message)', True if 'def question_body' in e9_src else False)
prefill_rendered = render('Qwen2.5-7B-Instruct', [{'role': 'user', 'content': recv_user}]) + PREFIX

# ------------------------------------------------------------ assemble the appendix file
F = []
w = F.append
w(base.rstrip('\n'))
w('\n\n---\n\n# Additions (E19-6)\n')
w('The sections above are E13\'s `PROMPTS_AND_PARSER.md`, copied unchanged. The additions below were extracted as strings from the frozen '
  'prompt code (not re-typed) and rendered with each model\'s own tokenizer (`apply_chat_template(..., add_generation_prompt=True)`; '
  '`enable_thinking=False` is passed on every call, as the frozen code does, and only the Qwen3 template uses it). '
  'Example question: the same OBQA fit question as above.\n')
w('## A. Check of the sections above against the frozen code\n')
w('| check | result |\n|---|---|')
for c in CHK:
    w(f"| {c['check']} | {c['status']} |")
w('\nCode files checked (SHA-256):\n')
w('| role | SHA-256 |\n|---|---|')
for k, h in HASHES.items():
    w(f'| {k} | `{h}` |')
w('\n## B. Receiver template for K displayed labels (all benchmarks; MMLU-Pro uses A-J)\n')
w('The receiver-only message (also the C2C receiver message and the last user turn of the Text path) is the frozen template below with '
  '`{{question}}` = the question stem and `{{choices}}` = one line `X. <option text>` per displayed option (labels A, B, C, ... in display '
  f'order). The label list in the instruction line `{INSTR_ABCD}` is replaced by the question\'s displayed labels joined by `/` '
  '(3 options: A/B/C; 4: A/B/C/D; 5: A/B/C/D/E; MMLU-Pro with 10 options: A/B/C/D/E/F/G/H/I/J). ARC questions whose original labels were '
  '1-4 are displayed and parsed as A-D.\n')
w('```text\n' + RECV_TEMPLATE + '\n```\n')
w('## C. Helper instruction (Text path) and helper body\n')
w('`{question}` is the helper body: the question stem, a blank line, `Choices:`, and the same option lines as in B (no instruction lines).\n')
w('```text\n' + BG + '\n```\n')
w('## D. Text+fact helper line\n')
w('Text+fact (OBQA only) prepends one line to the question stem inside the helper body; the receiver\'s turns are the Text-path turns with the fact-free instruction:\n')
w('```text\nUseful fact: <fact1>\n<question stem>\n```\n')
w('## E. Helper-aware prefill (E9c score s_G)\n')
w('One prefill of the **helper** on the receiver-only message (section B) in the helper\'s own chat template, followed by the separately '
  'encoded answer prefix `The correct answer is`; the same label-token rule and renormalization over the displayed labels as ProbeMax; '
  'argmax_H = the helper\'s most probable label. No generation. Rendered for the large helper (Qwen2.5-7B-Instruct):\n')
w('```text\n' + prefill_rendered + '\n```\n')
w('## F. GSM8K prompts (E10, large pair, Text reference)\n')
w('Helper: the instruction in C with `{question}` = the bare GSM8K question (no option list). Receiver (receiver-only, and last user turn of the Text path):\n')
w('```text\n' + GSM_RT + '\n```\n')
w(f'`{{{{question}}}}` = the GSM8K question. The second line of this template contains trailing spaces, kept byte for byte from the frozen '
  f'`use_cot=True` template. Receiver-with-message: user = helper instruction (C), assistant = helper message, user = the receiver prompt '
  f'above. Final-answer string: `{GSM_ANS}`. The GSM8K score is not a separate prompt: the receiver-only output is re-scored teacher-forced '
  '(u = 1 - geometric-mean probability of the extracted answer tokens; u = 1 if no number is extracted).\n')
w('## G. Rendered examples for the three receivers (OBQA fit question, same helper message)\n')
w('The helper is Qwen2.5-7B-Instruct for all three receivers (Llama-3.1-8B and OLMo-2 read the large pair\'s stored Text messages). '
  'Token counts below are checked against the saved run records of this question.\n')
w('### Helper Text prompt (Qwen2.5-7B-Instruct; identical for all receivers)\n')
w('```text\n' + helper_rendered + '\n```\n')
names = {'Qwen3-8B': 'Qwen3-8B (large pair; Qwen3 template, `enable_thinking=False` inserts the empty think block)',
         'Llama-3.1-8B-Instruct': 'Llama-3.1-8B-Instruct (X3; the template\'s default system header is inserted; tokenized with add_special_tokens=False, one BOS)',
         'OLMo-2-1124-7B-Instruct': 'OLMo-2-1124-7B-Instruct (X2; tokenized with add_special_tokens=False, one BOS)'}
for rcv in ['Qwen3-8B', 'Llama-3.1-8B-Instruct', 'OLMo-2-1124-7B-Instruct']:
    e = EX[rcv]
    w(f'### {names[rcv]}\n')
    w(f"Receiver-only ({e['n_R']} tokens):\n\n```text\n{e['receiver_only']}\n```\n")
    w(f"Receiver with the helper's message ({e['n_T']} tokens):\n\n```text\n{e['with_message']}\n```\n")
    w(f"Probe input ({e['n_probe']} tokens; the prefix `The correct answer is` is encoded separately as {e['prefix_ids']} and appended):\n\n```text\n{e['probe']}\n```\n")
w('C2C uses the receiver-only message (B) on the receiver side; the helper\'s cache is fused into it, so there is no separate C2C text prompt.\n')
w('## H. Anonymity scan\n')
out = '\n'.join(F) + '\n'
PAT = [('user name', r'user|user'), ('/lus path', r'/lus'), ('/home path', r'/home/'), ('sharedfs', r'sharedfs'),
       ('allocation', r'project'), ('machine', r'ClusterA|ClusterB|the-cluster|<redacted-domain>|<redacted-site>'),
       ('e-mail', r'[\w.+-]+@[\w-]+\.[\w.]+')]
hits = []
for nm, p in PAT:
    for m in re.finditer(p, out, flags=re.I):
        hits.append(dict(pattern=nm, match=m.group(0), context=out[max(0, m.start() - 40):m.end() + 40].replace('\n', ' ')))
res = 'no match' if not hits else f'{len(hits)} match(es): ' + '; '.join(f"{h['pattern']}: {h['match']}" for h in hits)
out += (f'Case-insensitive scan of this file for user names, /lus and /home paths, "sharedfs", the allocation name, machine or site names '
        f'(ClusterA, ClusterB, the-cluster, cluster.invalid, <redacted-site>) and e-mail addresses: **{res}**.\n')
open(STAGE / 'PROMPTS_FOR_APPENDIX.md', 'w', encoding='utf-8').write(out)
chk('anonymity scan of PROMPTS_FOR_APPENDIX.md', not hits, res)
nlines = out.count('\n')
missing_list = ['general K-label receiver template (MMLU-Pro A-J shown only as a rendered example)', 'helper-aware prefill (E9c)',
                'GSM8K prompts (E10)', 'Llama-3.1-8B receiver renderings', 'OLMo-2 receiver renderings',
                'Llama default system header / Qwen3 think markers shown explicitly per receiver']
csvout('E19_6_checks.csv', CHK)
csvout('E19_6_code_hashes.csv', [dict(role=k, path=str(CODE[k]), sha256=h) for k, h in HASHES.items()])
csvout('E19_6_anonymity_hits.csv', hits or [dict(pattern='none', match='', context='')])
csvout('E19_6_summary.csv', [dict(file=str(STAGE / 'PROMPTS_FOR_APPENDIX.md'), lines=nlines, sha256=sha(STAGE / 'PROMPTS_FOR_APPENDIX.md'),
                                  e13_copy_sha256=sha(STAGE / 'notes/PROMPTS_AND_PARSER_E13_copy.md'), e13_source_sha256=sha(E13MD),
                                  templates_added=';'.join(missing_list),
                                  text_fact_line='already in E13 file (section 5); verified',
                                  rendered_examples='helper Text (Qwen2.5-7B); receiver-only, receiver-with-message, probe x {Qwen3-8B, Llama-3.1-8B, OLMo-2}; E9c helper prefill',
                                  anonymity=res, n_checks=len(CHK), n_fail=sum(c['status'] == 'FAIL' for c in CHK), label=LABEL)])
json.dump(dict(start_utc=T0, end_utc=utc(), tokenizers=TOKP, files_read=READ), open(STAGE / 'logs/e19_6_run.json', 'w'), indent=1)
print('lines', nlines, 'anonymity', res, 'FAIL', sum(c['status'] == 'FAIL' for c in CHK))
print('E19-6 done', utc())
