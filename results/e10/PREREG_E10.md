# E10 preregistration (Round 4, 2026-09-20)

## Question

Does the reference-preserving omission procedure work when the answer is a free-form short answer
rather than one of a fixed set of option labels? Concretely: with the change indicator defined by
normalized exact match on a numeric answer, and with a label-free confidence score, does any
threshold certify at alpha = .05, delta = .001?

## Setting

- Pair: large (helper Qwen2.5-7B-Instruct, receiver Qwen3-8B), the same frozen revisions as the
  rest of the paper.
- Reference path b: Text only. C2C is not evaluated here.
- Benchmark: GSM8K, config "main", train split. Record and freeze the dataset revision hash.
- Decoding: greedy, bf16, thinking disabled, same chat templates as the main protocol. Helper
  message capped at 256 new tokens, as in the main protocol. Receiver generations capped at 320 new
  tokens (raised from 64 because a short-answer solution does not fit in 64).
- Both the receiver-only prompt and the receiver-with-message prompt instruct the model to end with
  the exact string "The answer is <number>." The helper prompt is the frozen Text-path helper prompt
  with the GSM8K question substituted for the multiple-choice question and with the option list
  removed. No other prompt change.

## Splits

Pool = GSM8K train. Sort by content hash of the question string, exactly as the OBQA pool was built,
and take the first 400 as fit, the next 1,000 as calibration, the next 400 as development. Gold
answers are not read while the splits are formed. The remaining train questions and the whole test
split are untouched.

## Change indicator and answer extraction

The extracted answer is the number following the last occurrence of "answer is" in the generation;
if that string does not occur, the last number in the generation; if there is no number, INVALID.
Normalization: strip surrounding whitespace, commas, currency symbols, percent signs and a trailing
period; parse as a Decimal; strip trailing zeros. Two answers are equal iff both parse and their
normalized Decimals are equal, or both are INVALID. As in the main protocol, all unparseable
outputs share one INVALID label.

The extractor is written and frozen before any model output exists, and is tested only on these
synthetic strings, which are written by hand and contain no model output:
  "The answer is 42." -> 42
  "the answer is $1,250" -> 1250
  "The answer is 3.50" -> 3.5
  "The answer is -7" -> -7
  "so the answer is 18 apples" -> 18
  "The answer is 12. The answer is 15." -> 15
  "Step 1: 3+4=7. Step 2: 7*2=14." -> 14
  "The answer is 100%" -> 100
  "The answer is one hundred" -> INVALID
  "No numbers here." -> INVALID
  "The answer is 0.0" -> 0
  "The answer is 007" -> 7
The extractor source file is hashed together with the preregistration. It is not modified after any
model output exists. If it turns out to be wrong on real outputs, that is reported as a limitation,
not fixed.

## Score (label-free)

Let the receiver, run alone, generate its solution greedily, and let a be the extracted answer
string. The score is
    u(x) = 1 - exp( (1/m) * sum_i log p(a_i | prompt, generated prefix) )
where a_1..a_m are the tokens of a, obtained by teacher-forced re-scoring: tokenize the prompt, the
generated text up to and including the character position where a begins, and a itself, concatenate,
run one forward pass, and read the log-probabilities at the positions of a's tokens. If a is INVALID
(no extractable number), set u(x) = 1, so such questions are never omitted at any threshold below 1.
This mirrors the deployable INVALID-routing rule and reads only the receiver's own output.

This score reduces to ProbeMax when the answer is a single label token, which is the sense in which
it is the same score as the rest of the paper.

Two further scores are computed and reported as descriptive only, not used for certification:
(s2) 1 - exp(mean token log-probability over the entire generated continuation);
(s3) 1 - p(first token of a).

## Cost model

The policy always pays one receiver-only generation plus one re-scoring forward pass. If the score
is at or below the threshold, the policy returns the receiver's own answer and stops. Otherwise it
pays the helper generation and the receiver-with-message generation. This is the open-ended analogue
of the argmax-answering implementation already reported for the multiple-choice settings, and the
paper states plainly that the decision cost here is a generation rather than a single prefill, so
the break-even is harder than in the multiple-choice settings.

## Certification

Identical to the main protocol: 20 candidate quantiles of u on the fit split, alpha = .05,
delta = .001, exact binomial test of H0: rho(tau) >= alpha on the calibration split, Bonferroni over
the 20 candidates, fallback if no candidate is accepted. This is a separate family of 20 tests.
Thresholds are computed from the fit split before any calibration disagreement is computed.

## Order of operations (sealing)

1. Freeze the preregistration and the extractor; hash both.
2. Form the splits from question text only.
3. Generate: fit receiver-only; calibration and development receiver-only, helper, and
   receiver-with-message.
4. Compute scores, thresholds from the fit split, disagreements, and the routing decision.
5. Hash all outputs, scores, thresholds and routing decisions.
6. Only then read the GSM8K gold answers and compute accuracies.
   Record the hash and the timestamp of step 5 and the timestamp of step 6.

## What is reported, whatever the outcome

- Receiver-only, Text, and oracle{receiver, Text} accuracy; the disagreement rate on calibration and
  on development; the INVALID rate on each path.
- Development AUROC of u, and of s2 and s3 for comparison.
- The largest accepted quantile q, or "no candidate accepted" with the smallest p-value and its
  candidate; the calibration n and k at that candidate.
- Development coverage, conditional change rate, and the accuracy of the policy against the Text
  reference with a paired bootstrap interval (seed 0, 2,000 resamples).
- The number of questions where u = 1 because the answer was INVALID.

## Reporting rules (fixed in advance)

- If a threshold certifies: the main text gains two to three sentences reporting that the same
  procedure, with normalized exact match as the change indicator and a label-free score, certifies
  omission on a free-form short-answer task, with the coverage and the conditional change rate. The
  title and abstract are not narrowed to multiple choice; Section 3 and Section 7 state that the
  certified settings are 26 multiple-choice settings plus one short-answer setting.
- If no threshold certifies: the main text says so plainly in one or two sentences, reports the
  disagreement rate and the AUROC, and the title, abstract and contribution list are explicitly
  narrowed to two-agent multiple-choice communication. A negative result here is reported, not
  dropped.
- If the Text path does not improve accuracy over the receiver alone, the paper says so and states
  that this setting demonstrates the machinery in a non-label answer space and is not evidence about
  informative messages. The oracle accuracy is reported for context.
- GSM8K is likely present in the pretraining data of both models. The paper states this, and states
  that the certified quantity is defined relative to the deployed path rather than to gold answers,
  so contamination affects the reported accuracies but not the target being controlled.
- If the frozen extractor is observed to mis-handle real outputs, the rate and the failure mode are
  reported and the extractor is not changed.

## Optional latency replay (only if time permits)

If and only if a threshold certifies and a job slot is available before the deadline below: replay a
frozen 128-question panel drawn from the development split at batch size one, with the fixed Text
reference and the policy interleaved in one allocation, no warm-up, cold requests retained, paired
mean saving with a paired bootstrap interval (seed 0, 2,000 resamples). Report the classification
only. If it does not happen, the paper reports the certification without a latency claim for this
setting and says so.

## Budget and deadline

Stop and report if the total exceeds 8 GPU-hours or 4 debug jobs. If there is no complete result by
2026-09-22 20:00 CDT, report what exists; E10 then does not enter the main text and the scope is
narrowed as in the negative-result rule above.
