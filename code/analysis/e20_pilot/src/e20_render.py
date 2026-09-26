"""E20P G4 (login node, tokenizers only, no weights): render one example per dataset (helper, receiver-only, receiver-with-message for each
receiver) into PROMPTS_E20.md; check BOS counts and that tokenizer(rendered, add_special_tokens=False) equals apply_chat_template(tokenize=True)
on every pilot prompt; record prompt token lengths -> notes/PROMPT_CHECKS.json."""
import sys, json, hashlib, pathlib, datetime, statistics
sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent; STAGE = HERE.parent; ROOT = STAGE.parent
sys.path.insert(0, str(HERE))
import e20_prompts as PR
from e20_exec_common import MODELS, DATASETS, PILOT, jl, load_tokenizer
sys.path.insert(0, str(PR.P10))
import legacy_methods
assert legacy_methods.BACKGROUND_PROMPT == PR.BACKGROUND_PROMPT
sys.path.remove(str(PR.P10))

PLACEHOLDER = '<<HELPER MESSAGE: the helper model\'s generated text is inserted here verbatim>>'
TOK = {r: load_tokenizer(r) for r in ['helper', 'qwen3', 'llama']}


def rend(role, msgs):
    t = TOK[role]
    r = t.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    ids = t(r, add_special_tokens=False)['input_ids']
    nat = t.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=False)
    bos = ids.count(t.bos_token_id) if t.bos_token_id is not None else 0
    return r, ids, ids == list(nat), bos


md = ['# PROMPTS_E20 — E20-pilot frozen prompts (rendered with the real chat templates)', '',
      f'Generated {datetime.datetime.now(datetime.timezone.utc).isoformat()} by src/e20_render.py (tokenizers only). Source: src/e20_prompts.py '
      f'(sha256 {hashlib.sha256((HERE / "e20_prompts.py").read_bytes()).hexdigest()}).', '',
      'Chat templates: helper Qwen2.5-7B-Instruct and receiver Qwen3-8B with enable_thinking=False; Llama-3.1-8B-Instruct default template, no',
      'system prompt added (the template inserts its own default header). Receiver ids = tokenizer(rendered, add_special_tokens=False);',
      'helper ids = apply_chat_template(tokenize=True) (frozen T2THelperBundle call). Receiver max new tokens 32, helper 256, greedy, bf16, batch 1.',
      '', '## Frozen multiple-choice receiver template (source) and the edits', '', '```text', PR.frozen_template(), '```', '',
      'Edits (each asserted to apply exactly once; see src/e20_prompts.py docstring): R1 options block removed; R2 "and all options" removed;',
      'R3 answer-format bullet replaced by the task instruction; R4 trailing multiple-choice cue "The correct answer is" removed;',
      'R5 (passage datasets) "Passage:\\n{passage}\\n\\n" placed before the question. Helper: options block removed from the body; passage',
      'datasets: the same passage block before the question. BACKGROUND_PROMPT verbatim.', '',
      '### Adapted receiver template, closed-book', '', '```text', PR.receiver_template(False), '```', '',
      '### Adapted receiver template, passage datasets', '', '```text', PR.receiver_template(True), '```', '']
checks = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), datasets={})
for ds in DATASETS:
    items = jl(PILOT(ds)); it = items[0]
    md += [f'## {ds}: first pilot item (id {it["id"]})', '']
    hr, hids, heq, hb = rend('helper', PR.helper_messages(ds, it))
    md += ['### Helper (Qwen2.5-7B-Instruct), rendered', '', '```text', hr, '```', '']
    for rc in ['qwen3', 'llama']:
        r1, i1, e1, b1 = rend(rc, PR.receiver_only_messages(ds, it))
        r2, i2, e2, b2 = rend(rc, PR.receiver_with_message_messages(ds, it, PLACEHOLDER))
        md += [f'### Receiver-only ({MODELS[rc]["repo"]}), rendered ({len(i1)} tokens, BOS count {b1})', '', '```text', r1, '```', '',
               f'### Receiver-with-message ({MODELS[rc]["repo"]}), rendered with a placeholder message', '', '```text', r2, '```', '']
    st = {}
    for role in ['helper', 'qwen3', 'llama']:
        L, eq, bo = [], [], []
        for x in items:
            if role == 'helper':
                r, ids, e, b = rend('helper', PR.helper_messages(ds, x))
            else:
                r, ids, e, b = rend(role, PR.receiver_only_messages(ds, x))
                r2, ids2, e2, b2 = rend(role, PR.receiver_with_message_messages(ds, x, 'x' * 50))
                eq.append(e2); bo.append(b2)
            L.append(len(ids)); eq.append(e); bo.append(b)
        st[role] = dict(n=len(items), prompt_tokens_max=max(L), prompt_tokens_median=statistics.median(L),
                        retokenized_equals_native_all=all(eq), bos_counts=sorted(set(bo)))
    checks['datasets'][ds] = st
    print(ds, json.dumps(st), flush=True)
(STAGE / 'PROMPTS_E20.md').write_text('\n'.join(md) + '\n')
(STAGE / 'notes/PROMPT_CHECKS.json').write_text(json.dumps(checks, indent=2) + '\n')
