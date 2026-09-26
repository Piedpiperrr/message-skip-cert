# Prompts and answer parser

All prompts are shown exactly as the models received them: the user message(s) built by the frozen prompt code, then the string produced by the model's own chat template (`add_generation_prompt=True`, thinking disabled). Examples are one OBQA fit question and one MMLU-Pro fit question, for the large pair (helper Qwen2.5-7B-Instruct, receiver Qwen3-8B); the small and medium pairs use the same prompt code with their own tokenizers. Each rendering below was checked against saved run records (token counts, saved input ids and saved probe ids; see the end of this file).

Roles: the helper writes one sentence of background (Text path). The receiver answers either alone (receiver-only, R), after reading the helper's sentence (Text), or with the helper's cache fused into it (C2C; its user message is the receiver-only message). The probe is one forward pass of the receiver on the receiver-only prompt followed by the answer prefix.

## OBQA example (fit question)

### 1. Helper Text instruction

User message:

```text
In one clear sentence, describe the most essential background knowledge needed to answer the question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Do NOT directly solve or give answer to the question.
```

Rendered helper input:

```text
<|im_start|>system
You are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>
<|im_start|>user
In one clear sentence, describe the most essential background knowledge needed to answer the question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Do NOT directly solve or give answer to the question.<|im_end|>
<|im_start|>assistant

```

### 2. Receiver Text-reading prompt

Three turns: the helper's instruction as a user turn, the helper's sentence as an assistant turn (the saved helper output for this question is shown), and the receiver-only user message as the final user turn. Rendered receiver input:

```text
<|im_start|>user
In one clear sentence, describe the most essential background knowledge needed to answer the question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Do NOT directly solve or give answer to the question.<|im_end|>
<|im_start|>assistant
The essential background knowledge needed to answer the question is an understanding of the definitions of renewable and nonrenewable resources, as well as the properties of wind and metal.<|im_end|>
<|im_start|>user
Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is<|im_end|>
<|im_start|>assistant
<think>

</think>


```

### 3. Receiver-only prompt

User message:

```text
Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is
```

Rendered receiver input:

```text
<|im_start|>user
Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is<|im_end|>
<|im_start|>assistant
<think>

</think>


```

### 4. Probe input

The rendered receiver-only input followed by the answer prefix `The correct answer is` (4 tokens). The probe reads the next-token distribution at the last position, sums probability over each option label's token set, renormalises over the displayed labels, and returns ProbeMax = 1 - max label probability.

```text
<|im_start|>user
Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is<|im_end|>
<|im_start|>assistant
<think>

</think>

The correct answer is
```

### 5. Text+fact addition

Text+fact changes only the helper's input: the line `Useful fact: <fact>` (the question's first OpenBookQA fact) is placed immediately before the question text. The receiver's conversation is the Text conversation of section 2 with the fact-free instruction as the first turn; only the helper's sentence differs.

Helper user message:

```text
In one clear sentence, describe the most essential background knowledge needed to answer the question:

Useful fact: metal is a nonrenewable resource
Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Do NOT directly solve or give answer to the question.
```

Rendered helper input:

```text
<|im_start|>system
You are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>
<|im_start|>user
In one clear sentence, describe the most essential background knowledge needed to answer the question:

Useful fact: metal is a nonrenewable resource
Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Do NOT directly solve or give answer to the question.<|im_end|>
<|im_start|>assistant

```

Rendered receiver input (helper sentence from the saved Text+fact smoke run of this fit question):

```text
<|im_start|>user
In one clear sentence, describe the most essential background knowledge needed to answer the question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Do NOT directly solve or give answer to the question.<|im_end|>
<|im_start|>assistant
The most essential background knowledge needed to answer the question is the understanding that metal is a nonrenewable resource.<|im_end|>
<|im_start|>user
Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is<|im_end|>
<|im_start|>assistant
<think>

</think>


```


## MMLU-Pro example (fit question)

### 1. Helper Text instruction

User message:

```text
In one clear sentence, describe the most essential background knowledge needed to answer the question:

The predominant cell type infected by HIV is CD4^+ cells. The mostimportant of these are the T-helper cells. (Review the immunogeneticschapter for a description of T_H-cells.) As the diseaseprogresses through latency into AIDS-related complexand finally full-blown AIDS, the absolute number of CD4^+ cells (i.e., T_H-cells) decreases.The rate of T_H-cell deletionincreases as the patient enters ARC. As the number ofT_H-cells decreases, the ratio of CD4^+ to CD8^+ cells inverts, goingfrom about 2:1 to less than 1:2. Why is the T_H-cell sucha devastating target ?

Choices:
A. T_H-cells are auxiliary cells that enhance the phagocytic function of macrophages without affecting lymphocytes.
B. T_H-cells are necessary for the proper functioning of the specific immune system, that is, for cytotoxic T-cells (T_c) and most B-cells.
C. T_H-cells are necessary for the functioning of only B-cells
D. T_H-cells are primarily involved in the production of mucus as a barrier against pathogens.
E. T_H-cells are the primary cell type that produces histamine in response to allergens.
F. T_H-cells are necessary for the maintenance of the skin's barrier function.
G. T_H-cells are only involved in the initial recognition of pathogens, without influencing the adaptive immune response.
H. T_H-cells are necessary for the functioning of non-specific immune system
I. T_H-cells are responsible for the production of antibodies against only non-pathogenic antigens.
J. T_H-cells are not necessary for the immune system


Do NOT directly solve or give answer to the question.
```

Rendered helper input:

```text
<|im_start|>system
You are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>
<|im_start|>user
In one clear sentence, describe the most essential background knowledge needed to answer the question:

The predominant cell type infected by HIV is CD4^+ cells. The mostimportant of these are the T-helper cells. (Review the immunogeneticschapter for a description of T_H-cells.) As the diseaseprogresses through latency into AIDS-related complexand finally full-blown AIDS, the absolute number of CD4^+ cells (i.e., T_H-cells) decreases.The rate of T_H-cell deletionincreases as the patient enters ARC. As the number ofT_H-cells decreases, the ratio of CD4^+ to CD8^+ cells inverts, goingfrom about 2:1 to less than 1:2. Why is the T_H-cell sucha devastating target ?

Choices:
A. T_H-cells are auxiliary cells that enhance the phagocytic function of macrophages without affecting lymphocytes.
B. T_H-cells are necessary for the proper functioning of the specific immune system, that is, for cytotoxic T-cells (T_c) and most B-cells.
C. T_H-cells are necessary for the functioning of only B-cells
D. T_H-cells are primarily involved in the production of mucus as a barrier against pathogens.
E. T_H-cells are the primary cell type that produces histamine in response to allergens.
F. T_H-cells are necessary for the maintenance of the skin's barrier function.
G. T_H-cells are only involved in the initial recognition of pathogens, without influencing the adaptive immune response.
H. T_H-cells are necessary for the functioning of non-specific immune system
I. T_H-cells are responsible for the production of antibodies against only non-pathogenic antigens.
J. T_H-cells are not necessary for the immune system


Do NOT directly solve or give answer to the question.<|im_end|>
<|im_start|>assistant

```

### 2. Receiver Text-reading prompt

Three turns: the helper's instruction as a user turn, the helper's sentence as an assistant turn (the saved helper output for this question is shown), and the receiver-only user message as the final user turn. Rendered receiver input:

```text
<|im_start|>user
In one clear sentence, describe the most essential background knowledge needed to answer the question:

The predominant cell type infected by HIV is CD4^+ cells. The mostimportant of these are the T-helper cells. (Review the immunogeneticschapter for a description of T_H-cells.) As the diseaseprogresses through latency into AIDS-related complexand finally full-blown AIDS, the absolute number of CD4^+ cells (i.e., T_H-cells) decreases.The rate of T_H-cell deletionincreases as the patient enters ARC. As the number ofT_H-cells decreases, the ratio of CD4^+ to CD8^+ cells inverts, goingfrom about 2:1 to less than 1:2. Why is the T_H-cell sucha devastating target ?

Choices:
A. T_H-cells are auxiliary cells that enhance the phagocytic function of macrophages without affecting lymphocytes.
B. T_H-cells are necessary for the proper functioning of the specific immune system, that is, for cytotoxic T-cells (T_c) and most B-cells.
C. T_H-cells are necessary for the functioning of only B-cells
D. T_H-cells are primarily involved in the production of mucus as a barrier against pathogens.
E. T_H-cells are the primary cell type that produces histamine in response to allergens.
F. T_H-cells are necessary for the maintenance of the skin's barrier function.
G. T_H-cells are only involved in the initial recognition of pathogens, without influencing the adaptive immune response.
H. T_H-cells are necessary for the functioning of non-specific immune system
I. T_H-cells are responsible for the production of antibodies against only non-pathogenic antigens.
J. T_H-cells are not necessary for the immune system


Do NOT directly solve or give answer to the question.<|im_end|>
<|im_start|>assistant
The most essential background knowledge needed to answer the question is an understanding of the role of T-helper (T_H) cells in the immune system, particularly their importance in regulating and aiding other immune cells such as cytotoxic T-cells (T_c) and B-cells.<|im_end|>
<|im_start|>user
Accurately answer the following question:

The predominant cell type infected by HIV is CD4^+ cells. The mostimportant of these are the T-helper cells. (Review the immunogeneticschapter for a description of T_H-cells.) As the diseaseprogresses through latency into AIDS-related complexand finally full-blown AIDS, the absolute number of CD4^+ cells (i.e., T_H-cells) decreases.The rate of T_H-cell deletionincreases as the patient enters ARC. As the number ofT_H-cells decreases, the ratio of CD4^+ to CD8^+ cells inverts, goingfrom about 2:1 to less than 1:2. Why is the T_H-cell sucha devastating target ?

Choices:
A. T_H-cells are auxiliary cells that enhance the phagocytic function of macrophages without affecting lymphocytes.
B. T_H-cells are necessary for the proper functioning of the specific immune system, that is, for cytotoxic T-cells (T_c) and most B-cells.
C. T_H-cells are necessary for the functioning of only B-cells
D. T_H-cells are primarily involved in the production of mucus as a barrier against pathogens.
E. T_H-cells are the primary cell type that produces histamine in response to allergens.
F. T_H-cells are necessary for the maintenance of the skin's barrier function.
G. T_H-cells are only involved in the initial recognition of pathogens, without influencing the adaptive immune response.
H. T_H-cells are necessary for the functioning of non-specific immune system
I. T_H-cells are responsible for the production of antibodies against only non-pathogenic antigens.
J. T_H-cells are not necessary for the immune system


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D/E/F/G/H/I/J".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is<|im_end|>
<|im_start|>assistant
<think>

</think>


```

### 3. Receiver-only prompt

User message:

```text
Accurately answer the following question:

The predominant cell type infected by HIV is CD4^+ cells. The mostimportant of these are the T-helper cells. (Review the immunogeneticschapter for a description of T_H-cells.) As the diseaseprogresses through latency into AIDS-related complexand finally full-blown AIDS, the absolute number of CD4^+ cells (i.e., T_H-cells) decreases.The rate of T_H-cell deletionincreases as the patient enters ARC. As the number ofT_H-cells decreases, the ratio of CD4^+ to CD8^+ cells inverts, goingfrom about 2:1 to less than 1:2. Why is the T_H-cell sucha devastating target ?

Choices:
A. T_H-cells are auxiliary cells that enhance the phagocytic function of macrophages without affecting lymphocytes.
B. T_H-cells are necessary for the proper functioning of the specific immune system, that is, for cytotoxic T-cells (T_c) and most B-cells.
C. T_H-cells are necessary for the functioning of only B-cells
D. T_H-cells are primarily involved in the production of mucus as a barrier against pathogens.
E. T_H-cells are the primary cell type that produces histamine in response to allergens.
F. T_H-cells are necessary for the maintenance of the skin's barrier function.
G. T_H-cells are only involved in the initial recognition of pathogens, without influencing the adaptive immune response.
H. T_H-cells are necessary for the functioning of non-specific immune system
I. T_H-cells are responsible for the production of antibodies against only non-pathogenic antigens.
J. T_H-cells are not necessary for the immune system


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D/E/F/G/H/I/J".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is
```

Rendered receiver input:

```text
<|im_start|>user
Accurately answer the following question:

The predominant cell type infected by HIV is CD4^+ cells. The mostimportant of these are the T-helper cells. (Review the immunogeneticschapter for a description of T_H-cells.) As the diseaseprogresses through latency into AIDS-related complexand finally full-blown AIDS, the absolute number of CD4^+ cells (i.e., T_H-cells) decreases.The rate of T_H-cell deletionincreases as the patient enters ARC. As the number ofT_H-cells decreases, the ratio of CD4^+ to CD8^+ cells inverts, goingfrom about 2:1 to less than 1:2. Why is the T_H-cell sucha devastating target ?

Choices:
A. T_H-cells are auxiliary cells that enhance the phagocytic function of macrophages without affecting lymphocytes.
B. T_H-cells are necessary for the proper functioning of the specific immune system, that is, for cytotoxic T-cells (T_c) and most B-cells.
C. T_H-cells are necessary for the functioning of only B-cells
D. T_H-cells are primarily involved in the production of mucus as a barrier against pathogens.
E. T_H-cells are the primary cell type that produces histamine in response to allergens.
F. T_H-cells are necessary for the maintenance of the skin's barrier function.
G. T_H-cells are only involved in the initial recognition of pathogens, without influencing the adaptive immune response.
H. T_H-cells are necessary for the functioning of non-specific immune system
I. T_H-cells are responsible for the production of antibodies against only non-pathogenic antigens.
J. T_H-cells are not necessary for the immune system


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D/E/F/G/H/I/J".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is<|im_end|>
<|im_start|>assistant
<think>

</think>


```

### 4. Probe input

The rendered receiver-only input followed by the answer prefix `The correct answer is` (4 tokens). The probe reads the next-token distribution at the last position, sums probability over each option label's token set, renormalises over the displayed labels, and returns ProbeMax = 1 - max label probability.

```text
<|im_start|>user
Accurately answer the following question:

The predominant cell type infected by HIV is CD4^+ cells. The mostimportant of these are the T-helper cells. (Review the immunogeneticschapter for a description of T_H-cells.) As the diseaseprogresses through latency into AIDS-related complexand finally full-blown AIDS, the absolute number of CD4^+ cells (i.e., T_H-cells) decreases.The rate of T_H-cell deletionincreases as the patient enters ARC. As the number ofT_H-cells decreases, the ratio of CD4^+ to CD8^+ cells inverts, goingfrom about 2:1 to less than 1:2. Why is the T_H-cell sucha devastating target ?

Choices:
A. T_H-cells are auxiliary cells that enhance the phagocytic function of macrophages without affecting lymphocytes.
B. T_H-cells are necessary for the proper functioning of the specific immune system, that is, for cytotoxic T-cells (T_c) and most B-cells.
C. T_H-cells are necessary for the functioning of only B-cells
D. T_H-cells are primarily involved in the production of mucus as a barrier against pathogens.
E. T_H-cells are the primary cell type that produces histamine in response to allergens.
F. T_H-cells are necessary for the maintenance of the skin's barrier function.
G. T_H-cells are only involved in the initial recognition of pathogens, without influencing the adaptive immune response.
H. T_H-cells are necessary for the functioning of non-specific immune system
I. T_H-cells are responsible for the production of antibodies against only non-pathogenic antigens.
J. T_H-cells are not necessary for the immune system


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D/E/F/G/H/I/J".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is<|im_end|>
<|im_start|>assistant
<think>

</think>

The correct answer is
```

### 5. Text+fact addition

Not applicable: Text+fact was run on OBQA only (the fact comes from the OpenBookQA fact field).

## Final answer parser (version 2, implementation 2.0.0)
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

## Verification of the renderings

- PASS: OBQA helper Text instruction equals saved E6 example
- PASS: OBQA helper Text+fact instruction equals saved E6 example
- PASS: OBQA helper rendered input tokens == saved helper_input_tokens (111 vs 111)
- PASS: OBQA receiver Text-reading rendered tokens == saved receiver_input_tokens (258 vs 258)
- PASS: OBQA receiver-only rendered tokens == saved receiver_input_tokens (132 vs 132)
- PASS: OBQA probe input ids == saved probe_ids (136 ids)
- PASS: probe prefix tokenizes to [785, 4396, 4226, 374]
- PASS: OBQA Text+fact helper rendered tokens == saved (E6 smoke) helper_input_tokens (124 vs 124)
- PASS: OBQA Text+fact receiver rendered tokens == saved (E6 smoke) receiver_input_tokens (247 vs 247)
- PASS: MMLU-Pro helper rendered == decoded saved helper input ids
- PASS: MMLU-Pro receiver Text-reading rendered == decoded saved receiver input ids
- PASS: MMLU-Pro receiver-only rendered == decoded saved receiver input ids
- PASS: MMLU-Pro probe input ids == saved probe_ids


---

# Additions (E19-6)

The sections above are E13's `PROMPTS_AND_PARSER.md`, copied unchanged. The additions below were extracted as strings from the frozen prompt code (not re-typed) and rendered with each model's own tokenizer (`apply_chat_template(..., add_generation_prompt=True)`; `enable_thinking=False` is passed on every call, as the frozen code does, and only the Qwen3 template uses it). Example question: the same OBQA fit question as above.

## A. Check of the sections above against the frozen code

| check | result |
|---|---|
| BACKGROUND_PROMPT identical in legacy_methods.py, arc_protocol.py and e10_prompts.py | PASS |
| probe prefix == BOUNDARIES frozen_config.json["prefix"] == X3 xfam_common.PREFIX == E9 e9_common.PREFIX | PASS |
| E13 OBQA helper user message == BACKGROUND_PROMPT.format(question=question + "\n\nChoices:\n" + choices) | PASS |
| E13 OBQA receiver-only user message == receiver_prompt.receiver_prompt(question) | PASS |
| E13 OBQA Text+fact helper user message == BACKGROUND_PROMPT with "Useful fact: <fact1>\n" before the question (e9_common.question_body rule) | PASS |
| "Useful fact: " line rule present in e9_common.question_body and PROTOCOL_FREEZE_E6.md | PASS |
| E13 MMLU-Pro helper user message == frozen code | PASS |
| E13 MMLU-Pro receiver-only user message == receiver_prompt (A-J label list) | PASS |
| E13 OBQA rendered helper input == Qwen2.5-7B apply_chat_template | PASS |
| E13 OBQA rendered receiver Text-reading input == Qwen3-8B apply_chat_template (saved helper message) | PASS |
| E13 OBQA rendered receiver-only input == Qwen3-8B apply_chat_template | PASS |
| E13 OBQA probe input == rendered receiver-only + prefix | PASS |
| parser section: 8 quoted regexes found verbatim in scoring_v2.py | PASS |
| parser section: cue words (hedges, corrections, explanations, joiners) present in scoring_v2.py | PASS |
| parser V2 SHA-256 == frozen d05978f4... | PASS |
| parser V2 implementation string 2.0.0 in scoring_v2.py | PASS |
| saved large-helper message for 14-1371: sha256 == X3 and X2 records T.helper_message_sha256 | PASS |
| Qwen3-8B: rendered token counts (receiver-only, with-message, probe) == saved run records | PASS |
| Llama-3.1-8B-Instruct: rendered token counts (receiver-only, with-message, probe) == saved run records | PASS |
| Llama-3.1-8B-Instruct: sha256(rendered receiver-only prompt) == saved probe rendered_sha256 | PASS |
| OLMo-2-1124-7B-Instruct: rendered token counts (receiver-only, with-message, probe) == saved run records | PASS |
| OLMo-2-1124-7B-Instruct: sha256(rendered receiver-only prompt) == saved probe rendered_sha256 | PASS |
| helper rendered token count == saved helper_input_tokens for 14-1371 (E13: 111) | PASS |
| E9c question_body (no fact) == receiver_prompt (receiver-only user message) | PASS |

Code files checked (SHA-256):

| role | SHA-256 |
|---|---|
| helper instruction (P2_10 legacy_methods.BACKGROUND_PROMPT) | `91b03c146f56fe151dc399c4202411974afb61c4a195080cf8c54abd584bffdf` |
| ARC helper/receiver adapter (P2_10 arc_protocol) | `b88840e37086c82dc6d485fe6ed3777bd99feb9718a47c901b4d4a5ad74ddbbe` |
| receiver prompt (receiver_prompt.py) | `868a4760d92b123127b347a9e5e69dec2f00855d17e2eee0eec4876d7cb21c66` |
| probe construction (run_boundaries.py) | `1b034b11dc2eef167d78cceb6fe76d18936f64585865092b673a5d03b4adb4d7` |
| Text+fact protocol (PROTOCOL_FREEZE_E6.md) | `d9fd5b9539fb6de1461bdb2f39958f3399295fd84563b0ec016e2b62c00e3793` |
| question body incl. Text+fact line (E9 e9_common.question_body) | `538247a5b8556fd123a355672ef53de3be0d3b98832c4d1e3d8c2c6862c29da9` |
| helper-aware prefill (E9c e9c_prefill.py) | `64989beba5af58654a3b623afc97ded9d722a4bb905ae9d9fc3e749edccb1076` |
| Llama-3.1-8B receiver (X3 run_x3.py) | `6e4a34d2c6baf4e46b526e630287962edb1837145cc92d94d053313d1dba1855` |
| OLMo-2 receiver (X2 run_x2.py) | `91f145e2f2849061fc1d2a6d9a41e040e47f98c89c48ab7ebd4a3618dec5a078` |
| GSM8K prompts (E10 e10_prompts.py) | `8d5809beb9451e1670a468a3213ccc8435fdc24694c0ddf8d7742c2a86c2afc7` |
| parser V2 (scoring_v2.py) | `d05978f400cf69aa6bddc56168a260ac3ea9158abaa640e9331602dc9bfcc2f9` |
| probe prefix (BOUNDARIES frozen_config.json["prefix"], read by run_boundaries.py) | `e84c015eb04ef92dfc252917e2f1ae3cfb0e86d2e830bf283afbaba0e9073f22` |

## B. Receiver template for K displayed labels (all benchmarks; MMLU-Pro uses A-J)

The receiver-only message (also the C2C receiver message and the last user turn of the Text path) is the frozen template below with `{{question}}` = the question stem and `{{choices}}` = one line `X. <option text>` per displayed option (labels A, B, C, ... in display order). The label list in the instruction line `"The correct answer is A/B/C/D"` is replaced by the question's displayed labels joined by `/` (3 options: A/B/C; 4: A/B/C/D; 5: A/B/C/D/E; MMLU-Pro with 10 options: A/B/C/D/E/F/G/H/I/J). ARC questions whose original labels were 1-4 are displayed and parsed as A-D.

```text
Accurately answer the following question:

{{question}}

Choices:
{{choices}}

Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is
```

## C. Helper instruction (Text path) and helper body

`{question}` is the helper body: the question stem, a blank line, `Choices:`, and the same option lines as in B (no instruction lines).

```text
In one clear sentence, describe the most essential background knowledge needed to answer the question:

{question}

Do NOT directly solve or give answer to the question.
```

## D. Text+fact helper line

Text+fact (OBQA only) prepends one line to the question stem inside the helper body; the receiver's turns are the Text-path turns with the fact-free instruction:

```text
Useful fact: <fact1>
<question stem>
```

## E. Helper-aware prefill (E9c score s_G)

One prefill of the **helper** on the receiver-only message (section B) in the helper's own chat template, followed by the separately encoded answer prefix `The correct answer is`; the same label-token rule and renormalization over the displayed labels as ProbeMax; argmax_H = the helper's most probable label. No generation. Rendered for the large helper (Qwen2.5-7B-Instruct):

```text
<|im_start|>system
You are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>
<|im_start|>user
Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is<|im_end|>
<|im_start|>assistant
The correct answer is
```

## F. GSM8K prompts (E10, large pair, Text reference)

Helper: the instruction in C with `{question}` = the bare GSM8K question (no option list). Receiver (receiver-only, and last user turn of the Text path):

```text
Accurately answer the following question:
                   
{{question}}

Instructions:
- Carefully read the question.
- Let's think step by step and explain your reasoning briefly.
- End your response with the exact string "The answer is <number>."
```

`{{question}}` = the GSM8K question. The second line of this template contains trailing spaces, kept byte for byte from the frozen `use_cot=True` template. Receiver-with-message: user = helper instruction (C), assistant = helper message, user = the receiver prompt above. Final-answer string: `The answer is <number>.`. The GSM8K score is not a separate prompt: the receiver-only output is re-scored teacher-forced (u = 1 - geometric-mean probability of the extracted answer tokens; u = 1 if no number is extracted).

## G. Rendered examples for the three receivers (OBQA fit question, same helper message)

The helper is Qwen2.5-7B-Instruct for all three receivers (Llama-3.1-8B and OLMo-2 read the large pair's stored Text messages). Token counts below are checked against the saved run records of this question.

### Helper Text prompt (Qwen2.5-7B-Instruct; identical for all receivers)

```text
<|im_start|>system
You are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>
<|im_start|>user
In one clear sentence, describe the most essential background knowledge needed to answer the question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Do NOT directly solve or give answer to the question.<|im_end|>
<|im_start|>assistant

```

### Qwen3-8B (large pair; Qwen3 template, `enable_thinking=False` inserts the empty think block)

Receiver-only (132 tokens):

```text
<|im_start|>user
Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is<|im_end|>
<|im_start|>assistant
<think>

</think>


```

Receiver with the helper's message (258 tokens):

```text
<|im_start|>user
In one clear sentence, describe the most essential background knowledge needed to answer the question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Do NOT directly solve or give answer to the question.<|im_end|>
<|im_start|>assistant
The essential background knowledge needed to answer the question is an understanding of the definitions of renewable and nonrenewable resources, as well as the properties of wind and metal.<|im_end|>
<|im_start|>user
Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is<|im_end|>
<|im_start|>assistant
<think>

</think>


```

Probe input (136 tokens; the prefix `The correct answer is` is encoded separately as [785, 4396, 4226, 374] and appended):

```text
<|im_start|>user
Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is<|im_end|>
<|im_start|>assistant
<think>

</think>

The correct answer is
```

### Llama-3.1-8B-Instruct (X3; the template's default system header is inserted; tokenized with add_special_tokens=False, one BOS)

Receiver-only (155 tokens):

```text
<|begin_of_text|><|start_header_id|>system<|end_header_id|>

Cutting Knowledge Date: December 2023
Today Date: 26 Jul 2024

<|eot_id|><|start_header_id|>user<|end_header_id|>

Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is<|eot_id|><|start_header_id|>assistant<|end_header_id|>


```

Receiver with the helper's message (281 tokens):

```text
<|begin_of_text|><|start_header_id|>system<|end_header_id|>

Cutting Knowledge Date: December 2023
Today Date: 26 Jul 2024

<|eot_id|><|start_header_id|>user<|end_header_id|>

In one clear sentence, describe the most essential background knowledge needed to answer the question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Do NOT directly solve or give answer to the question.<|eot_id|><|start_header_id|>assistant<|end_header_id|>

The essential background knowledge needed to answer the question is an understanding of the definitions of renewable and nonrenewable resources, as well as the properties of wind and metal.<|eot_id|><|start_header_id|>user<|end_header_id|>

Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is<|eot_id|><|start_header_id|>assistant<|end_header_id|>


```

Probe input (159 tokens; the prefix `The correct answer is` is encoded separately as [791, 4495, 4320, 374] and appended):

```text
<|begin_of_text|><|start_header_id|>system<|end_header_id|>

Cutting Knowledge Date: December 2023
Today Date: 26 Jul 2024

<|eot_id|><|start_header_id|>user<|end_header_id|>

Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is<|eot_id|><|start_header_id|>assistant<|end_header_id|>

The correct answer is
```

### OLMo-2-1124-7B-Instruct (X2; tokenized with add_special_tokens=False, one BOS)

Receiver-only (132 tokens):

```text
<|endoftext|><|user|>
Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is
<|assistant|>

```

Receiver with the helper's message (260 tokens):

```text
<|endoftext|><|user|>
In one clear sentence, describe the most essential background knowledge needed to answer the question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Do NOT directly solve or give answer to the question.
<|assistant|>
The essential background knowledge needed to answer the question is an understanding of the definitions of renewable and nonrenewable resources, as well as the properties of wind and metal.<|endoftext|>
<|user|>
Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is
<|assistant|>

```

Probe input (136 tokens; the prefix `The correct answer is` is encoded separately as [791, 4495, 4320, 374] and appended):

```text
<|endoftext|><|user|>
Accurately answer the following question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Instructions:
- Carefully read the question and all options.
- Select the single most correct answer.
- Respond ONLY in the following format: "The correct answer is A/B/C/D".
- Do not include any explanations, additional text, or punctuation besides the answer.

The correct answer is
<|assistant|>
The correct answer is
```

C2C uses the receiver-only message (B) on the receiver side; the helper's cache is fused into it, so there is no separate C2C text prompt.

## H. Anonymity scan

Case-insensitive scan of this file for user names, /lus and /home paths, "sharedfs", the allocation name, machine or site names (ClusterA, ClusterB, the-cluster, cluster.invalid, <redacted-site>) and e-mail addresses: **no match**.
