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
