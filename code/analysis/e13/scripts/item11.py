"""E13 Item 11: exact prompts (as rendered by the models' chat templates) and the final parser's rules.

Examples: OBQA fit question 14-1371 and MMLU-Pro fit representative test:3284, large pair (helper Qwen2.5-7B-Instruct,
receiver Qwen3-8B). Only the two tokenizers are loaded (CPU, local files, no weights) to apply the chat templates.
Every rendering is verified against saved evidence: MMLU-Pro against the saved native input ids of the Text and
receiver-only requests and the saved probe ids; OBQA against the saved E6 helper messages, the saved probe ids, and the
saved helper/receiver input-token counts. The Markdown file is then scanned for identifying strings.
"""
import sys, json, re, glob, importlib.util
from e13_common import *

sys.dont_write_bytecode = True
from transformers import AutoTokenizer  # noqa: E402

RCV = '$DATA_DIR/hf_cache/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218'
HLP = str(ROOT / 'P2_6_20260910T164138Z/assets/Qwen2.5-7B-Instruct')
rt = AutoTokenizer.from_pretrained(RCV, local_files_only=True)
ht = AutoTokenizer.from_pretrained(HLP, local_files_only=True)
spec = importlib.util.spec_from_file_location('rp13', ROOT / 'P2_R1_EXP_20260919T050555Z/src/receiver_prompt.py')
RP = importlib.util.module_from_spec(spec); spec.loader.exec_module(RP)
BACKGROUND_PROMPT = ("In one clear sentence, describe the most essential background knowledge "
                     "needed to answer the question:\n\n{question}\n\n"
                     "Do NOT directly solve or give answer to the question.")   # P2_10/legacy_methods.py, verbatim
PREFIX = 'The correct answer is'
PREFIX_IDS = [785, 4396, 4226, 374]
checks = []


def chk(name, ok, detail=''):
    checks.append(dict(check=name, ok=bool(ok), detail=detail, label=LABEL)); print(('PASS ' if ok else 'FAIL ') + name, detail)


def helper_body(q):
    return q['question_stem'] + '\n\nChoices:\n' + RP.choices_block(q['choice_text'])


def render_h(user):
    return ht.apply_chat_template([{'role': 'user', 'content': user}], tokenize=False, add_generation_prompt=True, enable_thinking=False)


def render_r(msgs):
    return rt.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)


def ntok(tok, s):
    return len(tok(s, add_special_tokens=False)['input_ids'])


def ids_of(tok, s):
    return tok(s, add_special_tokens=False)['input_ids']


ex = {}
# ---------------- OBQA fit 14-1371
q = next(r for r in jl(ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/inputs/obqa_train_queries.jsonl') if r['id'] == '14-1371')
E6X = next(e for e in read(ROOT / 'P2_R2_GPU_20260919T220941Z/e6/E6_PROMPT_EXAMPLES.json')['examples'] if e['id'] == '14-1371')
lab = next(r for r in jl(ROOT / 'P2_SCORING_V2_20260912T191445Z/labels/full_train_P2_SCORING_V2.jsonl') if r['pair'] == 'large' and r['dataset'] == 'obqa' and r['id'] == '14-1371')


def caserec(src):
    for i, l in enumerate(open(src['source_path']), 1):
        if i == src['source_line']:
            return json.loads(l)


tcase, rcase = caserec(lab['source_T']), caserec(lab['source_R'])
smoke = {r['id']: r for r in jl(ROOT / 'P2_R2_GPU_20260919T220941Z/e6/smoke/e6_smoke.jsonl')}
h_user = BACKGROUND_PROMPT.format(question=helper_body(q))
chk('OBQA helper Text instruction equals saved E6 example', h_user == E6X['helper_user_message_Text'])
h_user_tf = BACKGROUND_PROMPT.format(question='Useful fact: ' + E6X['fact1'] + '\n' + helper_body(q))
chk('OBQA helper Text+fact instruction equals saved E6 example', h_user_tf == E6X['helper_user_message_Text_plus_fact'])
r_user = RP.receiver_prompt(q)
h_rend = render_h(h_user)
chk('OBQA helper rendered input tokens == saved helper_input_tokens', ntok(ht, h_rend) == tcase['helper_input_tokens'], f"{ntok(ht, h_rend)} vs {tcase['helper_input_tokens']}")
t_rend = render_r([{'role': 'user', 'content': h_user}, {'role': 'assistant', 'content': tcase['helper_message']}, {'role': 'user', 'content': r_user}])
chk('OBQA receiver Text-reading rendered tokens == saved receiver_input_tokens', ntok(rt, t_rend) == tcase['receiver_input_tokens'], f"{ntok(rt, t_rend)} vs {tcase['receiver_input_tokens']}")
r_rend = render_r([{'role': 'user', 'content': r_user}])
chk('OBQA receiver-only rendered tokens == saved receiver_input_tokens', ntok(rt, r_rend) == rcase['receiver_input_tokens'], f"{ntok(rt, r_rend)} vs {rcase['receiver_input_tokens']}")
zg = next(r for r in jl(ROOT / 'P2_ZERO_GOLD_CONTROLS_20260914T065145Z/records/probe_records.jsonl') if r['id'] == '14-1371')
chk('OBQA probe input ids == saved probe_ids', ids_of(rt, r_rend) + PREFIX_IDS == zg['probe_ids'], f"{len(zg['probe_ids'])} ids")
chk('probe prefix tokenizes to [785, 4396, 4226, 374]', ids_of(rt, PREFIX) == PREFIX_IDS)
tf = smoke.get('14-1371')
tf_h_rend = render_h(h_user_tf)
if tf:
    chk('OBQA Text+fact helper rendered tokens == saved (E6 smoke) helper_input_tokens', ntok(ht, tf_h_rend) == tf['helper_input_tokens'], f"{ntok(ht, tf_h_rend)} vs {tf['helper_input_tokens']}")
    tf_r_rend = render_r([{'role': 'user', 'content': h_user}, {'role': 'assistant', 'content': tf['helper_message']}, {'role': 'user', 'content': r_user}])
    chk('OBQA Text+fact receiver rendered tokens == saved (E6 smoke) receiver_input_tokens', ntok(rt, tf_r_rend) == tf['receiver_input_tokens'], f"{ntok(rt, tf_r_rend)} vs {tf['receiver_input_tokens']}")
ex['obqa'] = dict(q=q, h_user=h_user, h_rend=h_rend, msg=tcase['helper_message'], t_rend=t_rend, r_user=r_user, r_rend=r_rend,
                  p_rend=r_rend + PREFIX, h_user_tf=h_user_tf, tf_h_rend=tf_h_rend, tf_msg=tf['helper_message'] if tf else None,
                  tf_r_rend=tf_r_rend if tf else None, fact=E6X['fact1'])

# ---------------- MMLU-Pro fit test:3284
MM = ROOT / 'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z'
recs = {}
for f in sorted(glob.glob(str(MM / 'shards/*/actions/fit.jsonl'))) + sorted(glob.glob(str(MM / 'shards/*/probes/fit.jsonl'))):
    for l in open(f):
        r = json.loads(l)
        if r['id'] == 'test:3284':
            recs[r['action']] = r
qm = recs['T']['query']
mh_user = BACKGROUND_PROMPT.format(question=helper_body(qm))
mr_user = RP.receiver_prompt(qm)
mh_rend = render_h(mh_user)
dec = lambda tok, ids: tok.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)
hid = recs['T']['native_first_input_ids']['helper'][0]; rid = recs['T']['native_first_input_ids']['receiver'][0]
chk('MMLU-Pro helper rendered == decoded saved helper input ids', ids_of(ht, mh_rend) == hid and dec(ht, hid) == mh_rend)
mt_rend = render_r([{'role': 'user', 'content': mh_user}, {'role': 'assistant', 'content': recs['T']['output']['helper_message']}, {'role': 'user', 'content': mr_user}])
chk('MMLU-Pro receiver Text-reading rendered == decoded saved receiver input ids', ids_of(rt, mt_rend) == rid and dec(rt, rid) == mt_rend)
mr_rend = render_r([{'role': 'user', 'content': mr_user}])
rrid = recs['R']['native_first_input_ids']['receiver'][0]
chk('MMLU-Pro receiver-only rendered == decoded saved receiver input ids', ids_of(rt, mr_rend) == rrid and dec(rt, rrid) == mr_rend)
chk('MMLU-Pro probe input ids == saved probe_ids', ids_of(rt, mr_rend) + PREFIX_IDS == recs['P']['probe_ids'])
ex['mmlu'] = dict(q=qm, h_user=mh_user, h_rend=mh_rend, msg=recs['T']['output']['helper_message'], t_rend=mt_rend, r_user=mr_user,
                  r_rend=mr_rend, p_rend=mr_rend + PREFIX)

# ---------------- Markdown
F = lambda s: '```text\n' + s + '\n```'
L = []
w = L.append
w('# Prompts and answer parser')
w('')
w('All prompts are shown exactly as the models received them: the user message(s) built by the frozen prompt code, then the '
  'string produced by the model\'s own chat template (`add_generation_prompt=True`, thinking disabled). Examples are one OBQA '
  'fit question and one MMLU-Pro fit question, for the large pair (helper Qwen2.5-7B-Instruct, receiver Qwen3-8B); the small and '
  'medium pairs use the same prompt code with their own tokenizers. Each rendering below was checked against saved run records '
  '(token counts, saved input ids and saved probe ids; see the end of this file).')
w('')
w('Roles: the helper writes one sentence of background (Text path). The receiver answers either alone (receiver-only, R), after '
  'reading the helper\'s sentence (Text), or with the helper\'s cache fused into it (C2C; its user message is the receiver-only '
  'message). The probe is one forward pass of the receiver on the receiver-only prompt followed by the answer prefix.')
for key, title in [('obqa', 'OBQA example (fit question)'), ('mmlu', 'MMLU-Pro example (fit question)')]:
    e = ex[key]
    w(''); w(f'## {title}'); w('')
    w('### 1. Helper Text instruction'); w(''); w('User message:'); w(''); w(F(e['h_user'])); w('')
    w('Rendered helper input:'); w(''); w(F(e['h_rend'])); w('')
    w('### 2. Receiver Text-reading prompt'); w('')
    w('Three turns: the helper\'s instruction as a user turn, the helper\'s sentence as an assistant turn (the saved helper output '
      'for this question is shown), and the receiver-only user message as the final user turn. Rendered receiver input:'); w('')
    w(F(e['t_rend'])); w('')
    w('### 3. Receiver-only prompt'); w(''); w('User message:'); w(''); w(F(e['r_user'])); w('')
    w('Rendered receiver input:'); w(''); w(F(e['r_rend'])); w('')
    w('### 4. Probe input'); w('')
    w('The rendered receiver-only input followed by the answer prefix `The correct answer is` (4 tokens). The probe reads the '
      'next-token distribution at the last position, sums probability over each option label\'s token set, renormalises over the '
      'displayed labels, and returns ProbeMax = 1 - max label probability.'); w('')
    w(F(e['p_rend'])); w('')
    if key == 'obqa':
        w('### 5. Text+fact addition'); w('')
        w('Text+fact changes only the helper\'s input: the line `Useful fact: <fact>` (the question\'s first OpenBookQA fact) is '
          'placed immediately before the question text. The receiver\'s conversation is the Text conversation of section 2 with '
          'the fact-free instruction as the first turn; only the helper\'s sentence differs.'); w('')
        w('Helper user message:'); w(''); w(F(e['h_user_tf'])); w('')
        w('Rendered helper input:'); w(''); w(F(e['tf_h_rend'])); w('')
        if e['tf_r_rend']:
            w('Rendered receiver input (helper sentence from the saved Text+fact smoke run of this fit question):'); w('')
            w(F(e['tf_r_rend'])); w('')
    else:
        w('### 5. Text+fact addition'); w('')
        w('Not applicable: Text+fact was run on OBQA only (the fact comes from the OpenBookQA fact field).'); w('')

w('## Final answer parser (version 2, implementation 2.0.0)')
PARSER = r'''
Input: the receiver's raw output and the question's displayed option labels (distinct uppercase letters). Output: one label or
INVALID. The parser uses syntax only; it never sees the gold answer, the question id, the method, or the option texts.

**Normalisation.** Unicode NFKC; strip; remove one surrounding Markdown code fence; delete `**`, `__` and backticks; map curly
quotes to straight quotes; if the whole output is wrapped in one pair of quotes, remove them. Empty output -> INVALID (`empty`).

**Where a selection can come from.**

1. A leading label at the very start: `(X)`, `[X]`, or a capital `X` followed by `.`, `)`, `:`, `,`, `;`, `!`, `?` or the end
   of the text. Regex: `^(?:\(([A-Z])\)|\[([A-Z])\]|([A-Z])(?=\s*(?:[.):,;!?]|$)))`. A leading `X` joined to further labels
   (`A/B`, `A or B`) is recorded as a multiple selection.
2. A declaration: `answer`, `choice`, `option` or `response`, optionally preceded by `the/my/your` and `final/correct`,
   followed by `is`, `is:` or `:`. Regex:
   `\b(?:(?:the|my|your)\s+)?(?:(?:final|correct)\s+)?(?:answer|choice|option|response)\s*(?:is\s*:?\s*|:\s*)` (case-insensitive).
3. An embedded selection: `the/my correct/right/best/final ... is` with up to 180 characters in between, optionally followed by
   `option`/`choice`. Regex: `\b(?:the|my)\s+(?:correct|right|best|final)\s+[^.!?;:\n]{1,180}?\s+is\s*(?:(?:option|choice)\s+)?`.
4. A choice verb: `I (finally|therefore)? choose/select/pick (option|choice)?`. Regex:
   `\bI\s+(?:(?:finally|therefore)\s+)?(?:choose|select|pick)\s+(?:(?:option|choice)\s+)?`.
5. A reverse selection: `option/choice X is (also)? correct/right/the (correct)? answer`. Regex:
   `\b(?:option|choice)\s+([A-Z])\s+is\s+(?:also\s+)?(?:correct|right|the\s+(?:correct\s+)?answer)\b`.

After patterns 2-4 the label is read with `^[\s"']*(?:\(([A-Za-z])\)|\[([A-Za-z])\]|([A-Za-z])\b)` and upper-cased.

**What is not a selection.** A pattern inside double or single quotes, or on a line starting with `>`, is ignored. A pattern
is ignored when the sentence before it (back to the last `.`, `!`, `?` or line break) or the pattern itself contains one of
`if, whether, unless, assuming, suppose, supposing, hypothetically, example, quote(d), say(s), said, claim(s), claimed,
incorrect, not`. A label followed by `=`, `+`, `*`, `/`, `^` or `°` is a formula or unit, and a lower-case letter followed by a
word is an article or a variable; both are ignored. A label followed by `if`, `unless`, `would`, `might`, `may` or `could` is a
conditional and is ignored. A declaration followed by `because`, `since`, `due to`, `that` or `based on` is an explanation and
is ignored; a declaration followed by `not`/`neither` is a negated declaration; any other declaration without a label counts
as a declaration with no option.

**Joined labels.** Labels joined by `/`, `|`, `,`, `or`, `and` or `versus`
(`^\s*(?:/|\||,\s*(?:(?:or|and)\s+)?|\b(?:or|and|versus)\b)\s*([A-Z])\b`) form a multiple selection.

**Resolution.** The last declaration, embedded selection, choice verb or reverse selection that says `final` or is preceded in
its sentence by a correction word (`actually, correction, on second thought, I revise, I change, instead, sorry`) and has no
issue starts a new scope; only selections from there on count. If the remaining single selections agree on one legal label, an
earlier enumeration of exactly all displayed labels (for example `A/B/C/D`) is disregarded. Then, in order:
any selected letter outside the displayed labels -> INVALID (`illegal_label`); any remaining multiple selection, negated
declaration or declaration without an option -> INVALID (that issue); more than one distinct label -> INVALID
(`unresolved_conflict`); two or more option headings at line starts (`^\s*(?:\([A-Z]\)|\[[A-Z]\]|[A-Z][.)])(?=\s|$)`, multiline)
with no selection after the last heading -> INVALID (`multiple_options`); the chosen label explicitly denied later
(`(option|choice)? X is|would be incorrect|wrong|not correct|not the answer`, not quoted or hedged) -> INVALID
(`unresolved_conflict`); a refusal (`I cannot/can't/am unable to/won't provide/answer/determine/select`, or `please
rephrase/clarify the question`) without a resolved final selection -> INVALID (`refusal`). No selection at all -> INVALID
(`refusal` if a refusal phrase occurs, otherwise `no_explicit_option`). Otherwise the single label is the answer.

INVALID is its own answer value: it is never equal to the gold label, and INVALID versus a letter counts as an answer change.
'''
w(PARSER.strip())
w('')
w('## Verification of the renderings')
w('')
for c in checks:
    w(f"- {'PASS' if c['ok'] else 'FAIL'}: {c['check']}" + (f" ({c['detail']})" if c['detail'] else ''))
md = '\n'.join(L) + '\n'

# ---------------- anonymity scan
DENY = ['user', '<redacted-handle>', '<redacted-mail-host>', '/lus', '/home', 'sharedfs', '<redacted-project-1>', '<redacted-project-2>', 'ClusterA', 'ClusterB', 'the-cluster', 'cluster.invalid',
        '<redacted-site>', '<redacted-host>', 'pbs', 'iclr2027', 'p2_', '<redacted-net>', 'scratch', '/tmp', 'snapshot', 'hf_cache', 'claude', 'c2c_reproduction']
low = md.lower()
hits = {d: low.count(d) for d in DENY if d in low}
paths = re.findall(r'(?<![A-Za-z0-9])/(?:[a-z0-9_.-]{3,}/)+[a-z0-9_.-]*', md)
chk('anonymity: no denylisted string in PROMPTS_AND_PARSER.md', not hits, str(hits))
chk('anonymity: no file-system path pattern in PROMPTS_AND_PARSER.md', not paths, str(paths[:5]))
(STAGE / 'PROMPTS_AND_PARSER.md').write_text(md)
csvout(RES / 'item11_checks.csv', checks)
print('written', STAGE / 'PROMPTS_AND_PARSER.md', len(md), 'chars')
