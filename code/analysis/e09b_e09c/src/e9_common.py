"""E9b/E9c shared paths, population assembly and the frozen label-token rule.

Additive only: nothing in this file writes to, or imports from, a frozen stage folder.
The helper probe reuses the frozen ProbeMax construction verbatim, with the receiver
replaced by the helper of the same pair (protocol E9C section "Score").
"""
import json, hashlib, datetime
from pathlib import Path

R = Path('$DATA_DIR')
STAGE = Path(__file__).resolve().parents[1]

BOUND = R / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
ZERO  = R / 'P2_ZERO_GOLD_CONTROLS_20260914T065145Z'
V2    = R / 'P2_SCORING_V2_20260912T191445Z'
MEDS  = R / 'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z'
MED   = MEDS / 'execution_retry1_20260915T164957Z'
MM    = R / 'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z'
E6    = R / 'P2_R2_GPU_20260919T220941Z/e6'
E8    = R / 'P2_R2_E8_20260920T012544Z'

# Helper models, one per pair (MODEL_SOURCE_INDEX of the owning stage).
HELPERS = {
 'small':  dict(repo_id='Qwen/Qwen2.5-0.5B-Instruct', revision='7ae557604adf67be50417f59c2c2f167def9a775',
                path='$DATA_DIR/c2c_reproduction_assets/models/Qwen--Qwen2.5-0.5B-Instruct'),
 'medium': dict(repo_id='Qwen/Qwen2.5-1.5B-Instruct', revision='989aa7980e4cf806f80c7fef2b1adb7bc71aa306',
                path=str(MEDS / 'execution_20260915T152640Z/assets/helper')),
 'large':  dict(repo_id='Qwen/Qwen2.5-7B-Instruct', revision='a09a35458c702b33eeacc393d103063234e8bc28',
                path=str(R / 'P2_6_20260910T164138Z/assets/Qwen2.5-7B-Instruct')),
}
HELPER_CHAT_TEMPLATE_SHA256 = 'cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f'
PREFIX = 'The correct answer is'          # frozen_config.json["prefix"], separately encoded, no trailing space
Q = [j / 20 for j in range(1, 21)]        # 19 fit quantiles plus q=1
ALPHA, P_CUTOFF, CP_LEVEL = .05, .001, .999

def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def rd(p):
    return json.loads(Path(p).read_text())

def jl(p):
    with Path(p).open() as f:
        return [json.loads(s) for s in f if s.strip()]

def save(p, v):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + '.tmp')
    t.write_text(json.dumps(v, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    t.replace(p)

def writejl(p, rows):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with Path(p).open('w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n')

# ---------------- frozen prompt construction (extracted verbatim) ----------------
_INSTRUCTION_ABCD = '"The correct answer is A/B/C/D"'
_TEMPLATE = """Accurately answer the following question:

{{question}}

Choices:
{{choices}}

Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is"""

def display_labels(n):
    assert 1 <= n <= 26
    return [chr(65 + i) for i in range(n)]

def choices_block(texts):
    return ''.join(f'{chr(65 + i)}. {t}\n' for i, t in enumerate(texts))

def question_body(rec, fact=None):
    """The frozen receiver_prompt() body. `fact` is used only by the descriptive
    Text+fact variant and prepends one 'Useful fact:' line, as in PROTOCOL_FREEZE_E6.md."""
    q = str(rec['question_stem'])
    if fact is not None:
        q = f'Useful fact: {fact}\n' + q
    prompt = _TEMPLATE.replace('{{question}}', q).replace('{{choices}}', choices_block(rec['choice_text']))
    assert prompt.count(_INSTRUCTION_ABCD) == 1
    labels = '/'.join(display_labels(len(rec['choice_text'])))
    return prompt.replace(_INSTRUCTION_ABCD, f'"The correct answer is {labels}"')

def label_token_sets(tokenizer, labels):
    """Frozen label-token rule: own tokenizer, non-special single tokens whose
    decoding.strip() equals the actual displayed label; dynamic K per question."""
    sets = {l: [] for l in labels}
    mapping = []
    special = set(tokenizer.all_special_ids)
    for v in sorted(set(tokenizer.get_vocab().values())):
        if v in special:
            continue
        decoded = tokenizer.decode([v], skip_special_tokens=False, clean_up_tokenization_spaces=False)
        if decoded.strip() in sets:
            l = decoded.strip()
            sets[l].append(v)
            mapping.append({'label': l, 'token_id': v,
                            'token_string': tokenizer.convert_ids_to_tokens(v), 'decoded': decoded})
    assert all(sets.values())
    assert len({v for s in sets.values() for v in s}) == sum(map(len, sets.values()))
    return sets, mapping

# ---------------- populations ----------------
def queries(pair, ds):
    if ds == 'mmlu_pro':
        src = MM / 'inputs/queries_only.jsonl' if pair == 'large' else E8 / 'inputs/queries_only.jsonl'
        return {r['id']: r for r in jl(src)}
    return {r['id']: r for s in ['train', 'dev'] for r in jl(BOUND / f'inputs/{ds}_{s}_queries.jsonl')}

def reps(pair, ds):
    if ds == 'mmlu_pro':
        base = MM if pair == 'large' else E8
        return {s: [g['representative_id'] for g in rd(base / f'splits/{s}_groups.json')] for s in ['fit', 'cal', 'dev']}
    base = MEDS if pair == 'medium' else BOUND
    return {s: rd(base / f'splits/{ds}_{s}_representatives.json') for s in ['fit', 'cal', 'dev']}

POPULATIONS = [('small', 'obqa'), ('small', 'arc'), ('medium', 'obqa'), ('medium', 'arc'),
               ('large', 'obqa'), ('large', 'arc'), ('large', 'mmlu_pro')]
OPTIONAL_POPULATIONS = [('small', 'mmlu_pro'), ('medium', 'mmlu_pro')]

def e8_ready():
    """small/medium MMLU-Pro are included only once every E8 lane has finished."""
    lanes = sorted(E8.glob('shards/*/lane_*'))
    return bool(lanes) and all((d / 'LANE_COMPLETE.json').exists() for d in lanes)
