# E10 deviations from PREREG_E10.md

Every item below was decided and frozen **before** any GSM8K model output existed
(see CODE_FREEZE_E10.sha256, 2026-09-20T23:10:36Z).  The preregistration file itself is
unmodified: sha256 a07185d35c84533e8a4d5c9054a60ab868a11a709c3f9ffb15276de532e0d785.

## 1. Receiver token cap 64 -> 320 (intended, preregistered)

PREREG_E10 "Setting" raises the receiver cap from the 64 of the multiple-choice protocol to 320,
because a worked short-answer solution does not fit in 64 tokens.  Implemented in
`src/e10_exec.py` (`RECEIVER_MAX_NEW = 320`).  The helper cap stays at the frozen 256.  This is
the one deliberate protocol change the task statement asked to be recorded as intended.

## 2. "exactly as the OBQA pool was built" is not literally reproducible

PREREG_E10 "Splits" says to sort by content hash of the question string "exactly as the OBQA pool
was built".  The OBQA pool was in fact **not** built that way: it was built by taking the
lexicographically smallest id of each duplicate group, sorting those representatives, and then
applying `random.Random(0).shuffle`
(`P2_RISK_CALIBRATION_BINARY_20260914T043954Z/src/prepare.py:17-20`, inherited verbatim by
`P2_CONFIDENCE_REFERENCE_BOUNDARIES_.../src/prepare.py`).  GSM8K also has no stable ids, so the
id-based rule is not available at all.

Resolution: the operative instruction ("sort by content hash of the question string") was followed
literally.  Order = ascending sha256 of the utf-8 question string, ties broken by the synthetic id
`gsm8k_train_%05d` (the train-split row index).  The descriptive clause is recorded here as
inaccurate.  See SPLIT_FREEZE_E10.json.  The pool has 7,473 train questions and **0** exact
duplicate question strings, so no grouping step was needed.

## 3. Receiver prompt: which frozen template, and the two forced edits

PREREG_E10 fixes the helper prompt exactly, and fixes the receiver prompt only through two
requirements: no option list, and "instruct the model to end with the exact string
'The answer is <number>.'".  It does not name a base template.  The frozen builder
(`P2_10/protocol_min.build_prompt`) has exactly two, `use_cot=False` and `use_cot=True`.
`use_cot=False` also says "Do not include any explanations, additional text, or punctuation
besides the answer" and ends with the priming string "The correct answer is"; it cannot produce a
worked solution.  Since PREREG_E10 justifies the 320-token cap by "a short-answer solution does not
fit in 64", the intended generation is a solution, so the `use_cot=True` template was used.

Edits to that frozen template, both forced by PREREG_E10 (`src/e10_prompts.py`):
- the `\n\nChoices:\n{{choices}}` block is removed with the option list;
- `- Carefully read the question and all options.` -> `- Carefully read the question.`
  (the option clause is vacuous with no options);
- `- Then give the final answer starting with The correct answer is`
  -> `- End your response with the exact string "The answer is <number>."`.
Everything else, including the trailing whitespace on line 2 of the frozen template, is byte for
byte identical.  The helper prompt is the frozen `BACKGROUND_PROMPT` with the bare GSM8K question
as the body, verified identical to `legacy_methods.BACKGROUND_PROMPT`.  The receiver-with-message
prompt is the frozen three-turn structure of `legacy_methods.T2TReceiverBundle.consume`
(user = background prompt, assistant = helper message, user = receiver prompt), unchanged apart
from the receiver prompt above and the 320-token cap.

**This is the one choice a reader could reasonably have made differently**, and it materially
affects the accuracies (GSM8K with and without a worked solution differ by tens of points).  It
does not affect what is being certified, which is agreement between two deployed paths.

## 4. Extracted answer string `a`: exact definition

PREREG_E10 defines the score over "the tokens of a" and "the character position where a begins"
but does not say whether a currency symbol or percent sign belongs to `a`.  The frozen extractor
defines `a` as the matched numeric token itself (optional sign, digits, embedded commas, optional
fractional part); `$` and `%` sit outside the match and are removed by normalization.  Frozen in
`src/e10_extract.py` before any model output existed.

## 5. Smoke-test INVALID gate applies to the two receiver paths

The task's pre-flight gate is "INVALID > 2/16 on any path".  The helper produces a background
sentence, not an answer, so "INVALID" is undefined for it.  The gate is evaluated on the
receiver-only and Text paths; the count of empty helper messages is recorded separately
(`records/GATE.json`).

## 6. Both models share one GPU

The frozen runtime places the helper on cuda:0 and the receiver on cuda:1.  E10 places both on a
single A100 40GB (31.6 GB of bf16 weights) so that 2 nodes give 8 independent shards instead of 4,
which is what brings the job inside both the 50-minute walltime and the 8 GPU-hour budget.  This
is a placement change only.  It is validated, not assumed: every rank reproduces 16 stored OBQA
fit rows bit for bit on the receiver-only and Text paths, through the unchanged frozen 64-token
code paths, before any GSM8K generation runs, and the job refuses to generate if any row differs.

## 7. No batching

Batching was permitted by the task but is not used: every generation is batch size one, so the
teacher-forced re-scoring corresponds exactly to the greedy generation that produced the answer.

## 8. Development Text rows finished in a second job

Job 7640159 reached its internal deadline with 397 of the 400 development Text rows done (rank 7
was 3 short).  Job 7640195 (1 node, resume only, pre-flight and smoke already passed and recorded)
generated exactly those 3 rows: gsm8k_train_06547, gsm8k_train_01743, gsm8k_train_00819.  The
split is therefore the full preregistered 400.  The seal was written once, after all 3,200 rows
existed; no analysis was sealed against the partial data.
