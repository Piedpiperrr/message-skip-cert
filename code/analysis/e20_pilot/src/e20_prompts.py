"""E20-pilot frozen prompts (G4). Written before any E20 model output and hashed in PREREG_E20P.md.

Derived from the frozen multiple-choice Text prompts by explicit string edits (each asserted to apply exactly once):
  frozen receiver prompt = P2_10 protocol_min.build_prompt(use_cot=False, use_template=True) (= arc_protocol.receiver_prompt for 4 options);
  frozen helper body     = question + "\\n\\nChoices:\\n" + choices (build_prompt use_template=False); helper prompt = BACKGROUND_PROMPT(body);
  frozen Text structure  = user: BACKGROUND_PROMPT(body) / assistant: helper message / user: receiver prompt (T2TReceiverBundle.consume).
Edits (receiver prompt; receiver-only and receiver-with-message use the identical string):
  R1 options block removed: "\\n\\nChoices:\\n{{choices}}" -> ""
  R2 "- Carefully read the question and all options." -> "- Carefully read the question."   (no options; as in E10)
  R3 "- Respond ONLY in the following format: \\"The correct answer is A/B/C/D\\"." -> "- " + answer instruction
  R4 trailing multiple-choice answer cue "\\n\\nThe correct answer is" removed (it primes the A/B/C/D format of R3)
  R5 passage datasets only: "{{question}}" -> "Passage:\\n{{passage}}\\n\\n{{question}}"
Helper: body = question (options block removed); passage datasets: body = "Passage:\\n{passage}\\n\\n" + question (same block, same position
as in R5). BACKGROUND_PROMPT unchanged.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
P10 = ROOT / 'P2_10_20260911T122423Z'

# verbatim copy of P2_10 legacy_methods.BACKGROUND_PROMPT (checked against the module in e20_render.py / e20_exec.py)
BACKGROUND_PROMPT = ("In one clear sentence, describe the most essential background knowledge "
                     "needed to answer the question:\n\n{question}\n\n"
                     "Do NOT directly solve or give answer to the question.")
INSTR_CLOSED = 'Answer with only the answer: a name, number, date or short phrase, not a sentence. Do not explain.'
INSTR_PASSAGE = 'Answer with the shortest span from the passage that answers the question. Do not explain.'
PASSAGE_DS = ('squad', 'nqp')


def frozen_template():
    sys.path.insert(0, str(P10))
    try:
        import protocol_min
        return protocol_min.build_prompt(dataset='mmlu-redux', locale='', question='{{question}}', choices='{{choices}}', use_cot=False,
                                         use_template=True)
    finally:
        sys.path.remove(str(P10))


def _sub(s, old, new):
    assert s.count(old) == 1, (old, s)
    return s.replace(old, new)


def receiver_template(passage):
    t = frozen_template()
    t = _sub(t, '\n\nChoices:\n{{choices}}', '')                                                        # R1
    t = _sub(t, '- Carefully read the question and all options.', '- Carefully read the question.')     # R2
    t = _sub(t, '- Respond ONLY in the following format: "The correct answer is A/B/C/D".',
             '- ' + (INSTR_PASSAGE if passage else INSTR_CLOSED))                                      # R3
    assert t.endswith('\n\nThe correct answer is')
    t = t[:-len('\n\nThe correct answer is')]                                                          # R4
    if passage:
        t = _sub(t, '{{question}}', 'Passage:\n{{passage}}\n\n{{question}}')                          # R5
    return t


_T = {}


def receiver_prompt(ds, item):
    p = ds in PASSAGE_DS
    if p not in _T: _T[p] = receiver_template(p)
    s = _T[p].replace('{{passage}}', item['passage']) if p else _T[p]
    return s.replace('{{question}}', item['question'])


def helper_body(ds, item):
    return ('Passage:\n' + item['passage'] + '\n\n' + item['question']) if ds in PASSAGE_DS else item['question']


def helper_prompt(ds, item):
    return BACKGROUND_PROMPT.format(question=helper_body(ds, item))


def receiver_only_messages(ds, item):
    return [{'role': 'user', 'content': receiver_prompt(ds, item)}]


def receiver_with_message_messages(ds, item, helper_message):
    return [{'role': 'user', 'content': helper_prompt(ds, item)},
            {'role': 'assistant', 'content': helper_message},
            {'role': 'user', 'content': receiver_prompt(ds, item)}]


def helper_messages(ds, item):
    return [{'role': 'user', 'content': helper_prompt(ds, item)}]
