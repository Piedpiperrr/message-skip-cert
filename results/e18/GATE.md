# E18 Step 0 — gate checks (login node, read-only, no model weights, no gold)

Stage: `P2_R8_E18_20260922T003446Z` (created 2026-09-22T00:34:46Z). `job-status -u $USER` at 2026-09-22T00:30:38Z: empty.

**Result: STOPPED at G3 (a stop condition fires on a preflight row), and preflight (b) as written compares s2 against a
quantity E10 computed by a different code path.** No PREREG_E18.md was written, no new score was computed on any row,
no job was submitted. Decision needed: see the last section.

Scripts: `gate/g1_g3.py` → `gate/G1_G3.json`; `gate/g3_divergence.py` → `gate/G3_divergence.json`;
`gate/g6_repro.py` (uses `src/e18_cert.py`) → `gate/G6.json`. E10 `src/__pycache__` unchanged (`gate/e10_pycache_before.txt`).

## G1 — E10 inputs (all under `P2_R4_E10_20260920T225954Z/`)

| item | path | rows |
|---|---|---|
| frozen config (models, dtype, template hashes) | `P2_R3_E9BC_20260920T061042Z/large/frozen_config.json` ["native"] (as loaded by `src/e10_exec.py:25`) | |
| split IDs | `splits/gsm8k_{fit,cal,dev}_ids.json` (frozen in `SPLIT_FREEZE_E10.json`) | 400 / 1000 / 400 |
| question texts | `inputs/gsm8k_queries.jsonl` (id, row, split, question, qhash) | 1800 |
| stored R and Text outputs | `records/main_rank{0..7}.jsonl` | fit R 400; cal R 1000, cal T 1000; dev R 400, dev T 400 (3,200; 0 duplicates) |
| change indicator | not stored as a column; E10 computes it as `R.answer != T.answer` on the stored frozen-extractor outputs (`src/e10_seal.py` `disagree()`); sealed per-row copy in `analysis/SEALED_SCORES.jsonl` (answer_R, answer_T) and `analysis/SEALED_DEV_ROUTES.jsonl` | |
| per-row scores | `records/main_rank*.jsonl` fields `u`, `s2`, `s3`, `rescore.answer_token_logprobs`; sealed copy `analysis/SEALED_SCORES.jsonl` | 1800 R rows |
| per-row timing | `latency_ms` only (R rows: generation + extraction + re-scoring wall time; T rows: helper + receiver). No per-step decode timings. | |
| certification + AUROC code | `src/e10_seal.py` (a script writing into E10 `analysis/`; arithmetic copied line for line into `src/e18_cert.py`) | |
| re-scoring / generation code | `src/e10_exec.py` (`RT.__init__`, `gsm_receiver` l.126-147, `rescore` l.149-166, `scores_from` l.168-181) | |
| smoke rows | `records/smoke_rank{0..7}.jsonl` = the first 16 fit IDs, R and T; R rows carry `gen_logprobs` | 16 R + 16 T |

## G2 — receiver

Qwen/Qwen3-8B, revision `b968826d9c46dd6066d109eabc6255188de91218`, local snapshot path in the frozen config; bf16, `sdpa`,
tf32 off; chat template sha256 `a55ee1b1…74d8` (verified on the local tokenizer); `enable_thinking=False`; prompt =
`e10_prompts.receiver_only_messages(question)` (single user turn, frozen use_cot=True template with the two E10 edits),
rendered with `apply_chat_template(..., tokenize=False, add_generation_prompt=True, enable_thinking=False)`, prompt ids =
`tok(rendered)`. EOS ids {151645, 151643}. Greedy decoding, no logits processors (repetition_penalty None; temperature,
top_k, top_p removed). Rendered prompt length equals the stored `receiver_input_tokens` on 1800/1800 rows.

## G3 — token positions

Source: stored `generated_token_ids` (all 1800 R rows). 1604 end in EOS (excluded from positions), 196 hit the 320 cap.
Content length L: min 61, max 320; **0 rows with L < 32**; 1 row with L < 64.
Stored length field `n_gen_tokens` = len(ids) on 1800/1800; EOS only in last position; decode(ids) == `raw_answer` on 1800/1800.

Comparisons with E10's token-level fields:
- E10 re-scoring tokens (`rescore.prefix_token_ids + answer_token_ids`, a re-tokenization of the decoded text) are a
  prefix of the stored generated ids on **1794/1800**. The 6 exceptions: 1 diverges at generated index 26 (cal
  `gsm8k_train_04565`, `' Y'+'oque'` vs `' Yo'+'que'`); 5 diverge at index 311-315 of 320-capped outputs (whitespace runs
  merged differently). **One of the 5 is a preflight row: fit `gsm8k_train_05081` (u = .9909)**, diverging at index 315,
  before its answer tokens (generated `'    ',' ','5'` vs E10 re-scoring `'     ','5','6'`).
- Re-tokenizing `raw_answer` (the fallback method; not used, since ids are stored) differs from the stored ids on 18/1800
  (1.0%): the same cal row at index 26, all others at index 318-319 (E10 stripped a trailing newline before storing the
  text). Two of these are preflight rows (`gsm8k_train_03400`, `gsm8k_train_02899`, both at index 319).
- Within positions 1-64, the only divergence of any kind is the one cal row above; the E18 score uses stored ids, so its
  positions are exact on all 1800 rows.

**Stop condition fires**: "STOP and report if … any of the preflight rows disagree." For `gsm8k_train_05081`, E10's u
and s3 were computed on a token sequence that is not the stored generated sequence, so the single teacher-forced pass over
the stored tokens cannot, by construction, reproduce its stored u/s3 (preflight (b)).

## G4 — prior first-token / derivation-prefix scores

None on cal or dev. Found: (i) `gen_logprobs` (per-token generation log-probs of the whole output) only on the 16 smoke
rows = the first 16 **fit** IDs; (ii) `rescore.answer_token_logprobs` on all rows = answer tokens only (the E10 score u);
the earliest answer token starts at generated index 59 (2 rows start before index 64, none before 32); (iii) E13 item 12
(`P2_R5_E13_20260921T031606Z/SUMMARY.md` "Item 12") stopped as "not stored"; (iv) E13 items 7/8/10, E19 (`scripts/e19_4.py`)
touch E10 only for file times, AUROC method inventory and N/A rows. Nothing else in the project references GSM8K outputs.

## G5 — gold

E10 R/T records contain no gold field (only a `gold_read: false` flag); `inputs/gsm8k_queries.jsonl` has no answer column.
E18 code (`src/e18_score.py`, `src/e18_merge.py`, `src/e18_cert.py`) reads only E10 records, split ID lists, question
texts and the frozen config; it never opens the GSM8K parquet or `analysis/E10_RESULTS.json`. (E10 `SUMMARY.md` was read
during G1; it contains aggregate accuracies only, no per-row gold.)

## G6 — reproduction of E10 (stored u, `src/e18_cert.py`)  PASS

20 tests identical to `analysis/SEALED_CAL_TESTS.jsonl` (all fields); thresholds, deployment and dev summary identical to
`analysis/E10_SEALED.json`; all 20 p = 1.000; 18/20 thresholds exactly 0.0 (19th 1.19e-07, 20th +inf); dev disagreement
77/400; calibration 174/1000 = 17.4%; dev AUROC u .579470, s2 .644445, s3 .568031 (mid-rank ties); fit u == 0 on 378/400.
Note: the s2 range .0163-.1952 in the task text is the fit split; over all 1800 R rows s2 spans .0099-.2285.

## Dry run (login node, tokenizer only)  PASS

4 ranks run in parallel with `--dry-run` (`dryrun/`): 1800 rows loaded, sharded 450 per rank, prompts rendered and
length-checked (assertion on every row), 37 preflight rows sharded 10/9/9/9, cross-rank gather, per-shard writes, merge to
parquet (1800 × 70 columns; 400/1000/400), SHA-256 written. Placeholder values only (constant -1); the placeholder parquet
was deleted.

## Why preflight (b) is expected to fail for reasons unrelated to the E18 code

1. **s2 comes from a different code path.** E10's stored s2 is not from the re-scoring forward pass. It is read from
   `generate(..., output_scores=True)` scores during KV-cached incremental decoding (`src/e10_exec.py` l.133-143, 172).
   Only u and s3 come from the teacher-forced re-scoring pass (l.149-166). A no-cache teacher-forced pass computes the same
   quantity with different bf16 kernels (M=1 decode GEMMs and attention vs full-sequence). The logits are bf16
   (spacing 0.0625-0.125 at typical magnitudes), and s2 averages ~210 tokens including EOS. So max |diff| <= 1e-4 over 37
   rows is not assured. No stored measurement bounds it: E10's own re-score-vs-generation check covered answer tokens only,
   whose log-probs were exactly 0.0 on both sides (`records/GATE.json` rescore_check).
2. **Row `gsm8k_train_05081`**: see G3; its stored u/s3 cannot come out of the specified pass.

## Decision needed (nothing frozen yet)

- **D1 (row 05081)**: (A, recommended) compare its u/s3 via a second pass over E10's exact re-scoring input
  (`[prompt ; tok(text[:start]) ; tok(a)]`, i.e. `RT.rescore` verbatim), gated at 1e-4 like the other rows; or (B) exclude
  it from the u/s3 comparison (36 rows, 21 with u > 0) and report it; or (C) keep verbatim, so (b) fails and branch (4)
  applies.
- **D2 (s2)**: (A, recommended) report s2's max |diff| without gating; gate = (a) plus u/s3 <= 1e-4; or (B) gate s2 at a
  looser tolerance you fix now; or (C) keep 1e-4 and accept the risk of branch (4).
- Residual risk under any option: u/s3 are teacher-forced on both sides but over sequences of slightly different length
  (E10 stopped at the answer end; E18 runs to EOS). They are expected to match at the answer positions, but that is not
  verified.

Proposed replacement for the (b) sentence of the PREREG block (D1-A + D2-A):
> (b) the same forward pass, with E10's own definitions, must reproduce E10's stored u and s3 on these rows with max
> absolute difference <= 1e-4 (report the max difference); for the one preflight row whose E10 re-scoring tokens are not
> a prefix of the stored generated tokens (gsm8k_train_05081, re-tokenized differently at generated index 315 of 320,
> before its answer tokens), u and s3 are instead compared from one extra pass over E10's own re-scoring input. E10's
> stored s2 was read from the KV-cached generation scores, not from a teacher-forced pass; its max absolute difference is
> reported and does not gate.

Implementation status: `src/e18_score.py` computes every quantity these options need (s2 on all rows; u/s3 on aligned
rows from the same pass; the E10 re-scoring-input pass for 05081). The chosen rule is one constant (`PREFLIGHT_RULE`,
currently VERBATIM). `job.sh` is ready but not submitted.
