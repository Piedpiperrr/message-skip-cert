# PREREG_E20P.md — E20-pilot (label-free), Paper A

Stage P2_R8_E20P_20260921T224653Z. Written 2026-09-21T23:30:43.360590+00:00, before any E20 model output and before the first job. The block between the markers is verbatim from the task; everything after it is resolved detail.

----- BEGIN PREREG BLOCK -----
E20-pilot (label-free). Candidates: SQuAD v1.1 (passage given), NQ-passage (MRQA NaturalQuestionsShort, passage given), TriviaQA
(closed-book), NQ-Open (closed-book); 400 pilot questions each, the first 400 of each dataset's fixed SHA order, disjoint from all later
full-run questions. Helper Qwen2.5-7B-Instruct writes the Text message (shared by both receivers). Receivers: Qwen3-8B (primary) and
Llama-3.1-8B-Instruct. Settings = dataset x receiver (up to 8).
Answer extraction (frozen): strip whitespace; strip leading markdown/quote characters (* _ " ' ` #); remove a leading "Answer:",
"Final answer:" or "The answer is" (case-insensitive); keep the first line that is non-empty after this; remove a trailing period; Unicode
NFKD with accents removed; then the official SQuAD normalization (lowercase, remove punctuation, remove articles a/an/the, collapse
whitespace). INVALID = empty after this. Change = 1[normalized o_R != normalized o_b]; two INVALIDs agree. The system's output is this
normalized answer; the certificate covers changes of it only.
Scores (larger = more uncertain; from raw logits in float64; 1 - max p computed as the total non-argmax probability):
  s1 = 1 - max_v p(v) at the first generated token whose text contains an alphanumeric character (the analogue of ProbeMax);
  s2 = 1 - P(answer) = -expm1(sum of log-probabilities of the answer tokens), where the answer tokens run from the first generated token
       containing a non-whitespace character up to, but excluding, the first later token whose text contains a newline, and exclude
       EOS/end-of-turn;
  s3 = -expm1(mean of the same log-probabilities) (length-normalized s2).
  With direct answering there is no derivation before the answer, so these scores read the model's confidence in the answer itself, as
  ProbeMax reads the chosen label.
Per setting report: disagreement rate d with two-sided 95% Clopper-Pearson interval; AUROC of s1, s2, s3 for disagreement (ties 1/2) with
bootstrap 95% intervals (seed 0, 2,000; N/A if d = 0); INVALID rates (R and reference); shares of s1 == 0 and s2 == 0; share of positions
where s1's token differs from the first generated token; median answer length in words; the empirical change rate among the 10%, 25% and
50% lowest-score questions (chosen score) with Clopper-Pearson upper bounds; the E17-5(a) check (max empirical TPR/FPR vs C(pi, alpha));
the share of changes where one normalized answer contains the other (descriptive).
Prediction: for each setting, its score is the one with the highest pilot AUROC (ties: s1, then s2). Feed (d, AUROC) into the frozen E17-5
binormal code (verify its hash; inputs only) with alpha = .05, delta = .001, N_fit = 500, the paper's 20 quantile levels, 1,000
simulations, seed 0. Report P(certify) at N_cal in {1,000, 2,000, 3,000}; a conservative P at the AUROC lower bound and d upper bound; the
AUROC needed for P = .5 at each N_cal; expected coverage only if the frozen code returns it (else N/A).
Eligibility and selection (label-free): a setting is eligible if its empirical change rate among the 25% lowest-score pilot questions is
<= 4% (point estimate; this guards against a floor of confident changes that the binormal model does not represent). Rank eligible settings by P@3000, then P@1000, then the AUROC lower bound, then Qwen3 before Llama. The full run
takes at most two settings with P@3000 >= .5: the top one, then the best one on a different dataset if its P@3000 >= .5, otherwise the next
one with P@3000 >= .5. If none qualifies, nothing is selected and the paper reports the pilot only.
Full-run design (frozen now): pool = the same deduplicated, length-filtered split minus the pilot, continuing the SHA order: fit 500
(receiver-only outputs only), calibration N_cal, dev 1,000, with N_cal the smallest of {1,000, 2,000, 3,000} whose P >= .8 (else 3,000).
Identical prompts, extractor, score code and decoding, verified by hash; nothing is edited after seeing the pilot. Certification exactly as
the paper (20 fit quantiles, alpha = .05, delta = .001, per-setting Bonferroni; each selected setting is its own family, as for every other
setting in the paper). Selected settings are run and reported whatever the outcome. If the full run is not complete by Sep 23 06:00 CDT,
the paper reports the pilot and states that the full run was not completed.
Writing rules (Paper A):
(1) A selected setting certifies with dev coverage >= 10% and a dev change-rate CP lower bound <= 5%: the abstract says certification
    extends to direct short-answer question answering on that dataset, predicted in advance by the label-free rule; the title drops
    "on Multiple Choice"; the main text reports d, AUROC, q, coverage, change rate [CI], the Text path's accuracy gain G with kappa*alpha vs
    G, and the split of certified changes into both-parse vs exactly-one-INVALID.
(2) Certifies with dev coverage < 10%, or with dev CP lower bound > 5%: reported as such in Sec. 4 and the appendix; abstract and title
    unchanged.
(3) Fallback: Sec. 7 reports it in one sentence with d and AUROC; title keeps "on Multiple Choice".
(4) Always: the full-run settings join the certification-outcome count and are reported as prospective tests of the binormal prediction;
    the pilot settings are not certification outcomes; an appendix reports every pilot setting, the selection rule and the order of
    events; the provenance table gets a row (later extension, run after the GSM8K fallback, label-free pilot on disjoint questions, rule
    hashed before selection); the main text notes that the selected setting's predicted P is inflated by choosing the best of eight.
----- END PREREG BLOCK -----

## Resolved dataset revisions and pool / pilot hashes

| dataset | repo @ revision | pool after filters + dedup | POOL_ORDER sha256 | PILOT sha256 |
|---|---|---|---|---|
| SQuAD | rajpurkar/squad @ `7b6d24c440a36b6815f21b70d25016731768db1f` | 86,830 | `9754449546d370e2ab7c690ee99f44a50c240230850574f195f596664ffab7f3` | `bcf2b0e2de5756a179893d7e4b711a667006007321842f325ac47b4d43937d9d` |
| NQ-passage | mrqa-workshop/mrqa @ `f3178d9888471dfb2b67c93de14f0ddf499a8d9f` | 98,071 | `ba6525fb9dd6693cfc88f3497dc300db10749e4e50d7b4e292121f04a5888036` | `eddf08f0701f08ca3fbcc08455a36273ab0fd251c4dd992ff03dc7884292088b` |
| TriviaQA | mandarjoshi/trivia_qa @ `0f7faf33a3908546c6fd5b73a660e0f8ff173c2f` | 76,341 | `3457e6978a7942344299c30859679c2103cf906b522790622a6e304386534b7e` | `fb0fe5a72f53f3bb38277380264c29387bb009abe7d3b6d0fe4a683af29f0a84` |
| NQ-Open | google-research-datasets/nq_open @ `5dd9790a83002ad084ddeb7c420dc716852c6f28` | 87,145 | `f7ec7dfca52f2443f704a822dec14fb2690c841782fee1fe9d7190840558e6bf` | `7cc1e18170835e8789a9583a7dd056a3e637af421882cfcbcceafb0f48394a91` |

PROMPTS_E20.md sha256 `6ed439e8c320c9c9bb62bb3fad969564219168976f134db7e3199db674c6814e`. GATE.md sha256 `46e64a6d88a09dc85bc5609d14d5dc5fec6614d09c92403e78f2b83373f51cd8`. notes/CODE_FREEZE.json sha256 `5dc333c88cc55741a9d6323fcab4b2147525c1f13a8b878a7905e64f42cdf895` (checked by every GPU rank at start-up; lists 27 files).

Frozen E17-5 binormal code: P2_R7_E17_20260921T183100Z/scripts/e17_5.py sha256 `ef1537c7289b30d7a0adfe5b9180fc9a53a35bf6cb6aba1021ebf6759dde2b6b` (= the value recorded in P2_R7_E16 E17_5_on_E16_5.json; asserted in src/e20_analyze.py).

Models: helper Qwen/Qwen2.5-7B-Instruct @ a09a35458c702b33eeacc393d103063234e8bc28; receivers Qwen/Qwen3-8B @ b968826d9c46dd6066d109eabc6255188de91218
and meta-llama/Llama-3.1-8B-Instruct @ 0e9e39f249a16976918f6564b8830bc894c89659 (X3 copy; chat template sha256 e10ca381...4d4b65).

## Code hashes

| file | sha256 |
|---|---|
| jobs/e20_jobA.pbs | `eca05000f4b4e2ced0cb29d062ae2d19ed30d74b5c8c0d1b59dd5c45ddcd48dd` |
| jobs/e20_jobB.pbs | `817cfc55e8ffe3272f37ce873f82ff62329440cd0ed36c4f616ff94a03740a5f` |
| jobs/e20_slot.sh | `ec14f16f60f45ddc76357cccc48e5974f92410c5736dd0b8b3e2607bd5cf38a6` |
| src/download_datasets.py | `73d58344d49e2ef255fad5acacae8aed541ee510bd90f5d0c7eedb1e643cf508` |
| src/e20_accuracy.py | `1806e0137eeda1dfef6d19074c47102b044db1d27ebaa3c6d1453ef6cd8ba6e1` |
| src/e20_analyze.py | `7185a3696d0ec3a805126f3872921acb29881ae996cbc7eb908dc985b793abac` |
| src/e20_exec.py | `841f849807d5be2f71d0fdb49ec77ab573585e21f16314108003741715769f3f` |
| src/e20_exec_common.py | `7e74678c1367a3e74a039e5fa1371cadb3bc2091ecbe60a12c1659e291f80c85` |
| src/e20_extract.py | `d9c30fa611218ff2decdf498349f3a1eefbdaada89dbed171b1d40fed9342be0` |
| src/e20_merge.py | `9085534ea8ce4a79e5b5101579c5404727168e32f890f401212d43b8f3758111` |
| src/e20_pool.py | `53413dc7ec8dab1a53b1cae9b043347d8f4086263ef437891f8f00ca3a60bee7` |
| src/e20_prompts.py | `c4b0be5dea890f56ed4a86f820045775743504556cb22b6f332b760f50c0c900` |
| src/e20_render.py | `e919aabc4741f94d80d7bba8923464716ffb9dd40c2349848c4f2fbb33312802` |

## Implementation choices where the block leaves a detail open (fixed in the hashed code before any output)

1. Prompts (PROMPTS_E20.md, src/e20_prompts.py): from the frozen MC receiver prompt, R1 options block removed; R2 "and all options" removed;
   R3 the answer-format bullet replaced by the task instruction; R4 the trailing MC cue "The correct answer is" removed; R5 passage datasets:
   "Passage:\n<passage>\n\n" before the question. Helper: BACKGROUND_PROMPT unchanged, body = question (+ the same passage block).
   Receiver-with-message = frozen 3-turn Text structure. Receiver ids = tokenizer(rendered, add_special_tokens=False) (identical to
   apply_chat_template(tokenize=True) on all 1,600 pilot prompts; Llama 1 BOS). Generations decoded with skip_special_tokens=True,
   clean_up_tokenization_spaces=False on both paths and both receivers; helper decoding as the frozen T2THelperBundle.
2. Pool: markup tokens = whitespace-separated tokens matching </?[A-Za-z][A-Za-z0-9]*> (MRQA only); normalized question for dedup =
   e20_extract.normalize_text (NFKD accents removed + SQuAD normalization); prompt question = raw question .strip();
   SHA string "<dataset>|<id>" with dataset in {SQuAD, NQ-passage, TriviaQA, NQ-Open}; ties by file row.
3. Extraction = e20_extract.extract (literal implementation; the official SQuAD normalization removes ASCII punctuation only, so e.g. curly
   quotes survive). Words = whitespace tokens of the normalized answer; INVALID = 0 words.
4. Scores: raw logits = generate(output_logits=True) (float32 copy of the bf16 model logits before any logits processor) -> float64;
   1 - max p = sum of softmax over all non-argmax ids. Token text = decode([id], skip_special_tokens=False). Special ids (tokenizer special
   ids, special added tokens, generation EOS ids) never start s1/s2 and end the s2 span. If no qualifying token exists the score is 1.0
   (flagged). argmax != chosen token is counted per row (expected 0).
5. Smoke (first 8 pilot questions per dataset, receiver-only): a dataset is dropped if, for either receiver, INVALID > 2/8 or the median
   answer words > 10. Projection = elapsed + measured load times + worst case (256 helper + 4 x 32 receiver tokens per question) at the
   measured decode rates, for the largest shard; > 45 min -> first 300 pilot questions per dataset in that job (deviation).
6. Statistics (src/e20_analyze.py docstring): AUROC with average ranks; paired bootstrap, percentile interval; lowest 10/25/50% = the
   paper's order-statistic threshold on the pilot scores with ties kept; Clopper-Pearson upper bound = two-sided 95%; E17-5(a) over the 20
   pilot-quantile candidates; missing / runtime-error rows excluded and counted; if d = 0 or 1 there is no AUROC, no prediction, and the
   setting cannot be ranked; expected coverage = N/A (the frozen code returns median coverage when certified, reported separately).
7. Step 6 aliases: SQuAD answers.text; MRQA answers; TriviaQA answer.value + aliases + normalized_aliases; NQ-Open answer.

## Job plan

ClusterA debug, 2 jobs x (select=2, 4 A100 40GB per node, walltime 00:55:00): job A = SQuAD + NQ-passage (rank 0: preflight 16 OBQA
large-pair rows + 16 X3 Llama rows bitwise, smoke, GATE), job B = TriviaQA + NQ-Open (preflight skipped if job A PASSED; smoke, GATE).
All ranks: helper -> Qwen3-8B (R, T) -> Llama-3.1-8B (R, T), 100 questions per GPU. Gold is not read before SELECTION_E20P.json is hashed.
