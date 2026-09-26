# E21B inputs (P2_R9_E21B_20260922T065040Z)

All paths are relative to the project root `$DATA_DIR`.
Every input was read without modification. No gold label was read. Files that hold answer keys were never opened, for
example `P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/inputs/evaluation_gold_after_prediction_freeze.jsonl`.
Two stored summary files were read only for their k/n fields; they also contain accuracy values computed earlier:
`summary/primary_sealed.csv` and `analysis/E9B_RESULTS.json`.

## 1. Populations

| population | file | SHA-256 | N |
|---|---|---|---|
| sealed ARC test (large pair, ARC-Challenge test) | `P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/inputs/test_queries_no_gold.jsonl` | `6eadf788cad4a8c65762b34febc73b07f8630d53f8ec35bdf261c173caa80f3c` | 1,172 |
| held-out OBQA (E9b; not sealed, see `PROTOCOL_AMENDMENT_E9B.md`) | `P2_R3_E9BC_20260920T061042Z/inputs/holdout_744_queries.jsonl` | `b0c6dd2c1696a89b5d7f88213b38a4b70a64e1025916841ebcf650a9919e2b25` | 744 |
| OBQA fact1 (Text+fact helper line) | `P2_R3_E9BC_20260920T061042Z/inputs/obqa_fact1.json` | `4aa386201dabab9372ba258e33f484831804a04fcdcb50abc4ce4491786b2be3` | 744 keys |

Counts confirmed:
- Sealed ARC: 1,172 rows and 1,172 distinct ids. The file hash matches `TEST_POPULATION_FREEZE.json` (`N: 1172`, `gold_read: false`).
  - Option counts: 1,165 with K=4, 4 with K=3, 3 with K=5.
  - 22 questions have numeric original labels. The sealed input already shows letters A.. in original option order (`display_label_map`), so `choice_labels` is `A..` for all 1,172.
- Held-out OBQA: 744 rows and 744 distinct ids, all K=4 with labels A-D.

## 2. Stored original-format outputs (what the rotated runs are compared with)

| population | file | SHA-256 | verification |
|---|---|---|---|
| sealed ARC | `P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/records/e2e_requests.jsonl` | `389b5a27e1f19640bd2a331d2eb67bb045dcbcac963973e61b54566cdbd7f9d8` | matches `PREDICTION_TIMING_FREEZE.json` |
| held-out OBQA | `P2_R3_E9BC_20260920T061042Z/large/records/e9b_large_shard0.jsonl` | `a4ac6302913d49ca70bfc7643be104ee618074b4de2ee87cc5b8f6c3f7aaa8ca` | see below |
| | `.../e9b_large_shard1.jsonl` | `f348f90deea67f9a91105a63b9a5cc86ee74820b4d5d61002f94f4cd98602cd3` | |
| | `.../e9b_large_shard2.jsonl` | `c02dc17a5334403b2577fcc0d34dbc9f9a5708bab59655b94cfc270ff9afb3cd` | |

Sealed ARC (ClusterB job 185883):
- Each question has 4 records: policy_T, reference_T, policy_C, reference_C.
- The stored u (ProbeMax) is identical in the two policy probes on 1,172/1,172 questions.
- **R_orig exists on 1,100 questions**, those omitted by the Text policy (the C-omitted 1,047 are a subset). Where both policies omitted a question, R is byte-identical in the two records (1,047/1,047).
- Text_orig = reference_T and C2C_orig = reference_C, both for all 1,172 questions.

Held-out OBQA (ClusterA jobs 7638751 and 7638821):
- 3,720 records = 744 x (probe, R, T, C, TF), with no duplicate (id, action).
- The R/T/C/TF records agree with E9B's hashed `analysis/SEALED_OUTPUTS.jsonl` on 2,976/2,976 (id, action) pairs (answer and raw_answer). Hashes were verified against `analysis/SEAL_RECEIPT.json`.

## 3. Frozen policies and thresholds, checked against the certification records

| policy | PREREG q | stored q | stored tau | certification record (SHA-256) | match |
|---|---|---|---|---|---|
| large/ARC/Text | .95 | 0.95 | 0.01800704002380371 | `P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/deployments/large_arc_T.json` (`30028f08…865c`); cal N 448, n_R 422, changed 4, p 4.80e-06, accepted | yes |
| large/ARC/C2C | [frozen q] -> **.90** | 0.9 | 0.0007095932960510254 | `…/deployments/large_arc_C.json` (`a3391054…18b5`); cal N 448, n_R 404, changed 7, p 5.40e-04, accepted | yes (placeholder filled with the stored value) |
| large/OBQA/Text | .80 | 0.8 | 0.001170039176940918 | `…/deployments/large_obqa_T.json` (`6f4f7baa…814b`); cal N 1366, n_R 1064, changed 18, accepted | yes |
| large/OBQA/C2C | .80 | 0.8 | 0.001170039176940918 | `…/deployments/large_obqa_C.json` (`507a9c09…641e`); cal N 1366, n_R 1064, changed 22, accepted | yes |
| large/OBQA/Text+fact | .75 | 0.75 | 0.0002611875534057617 | `P2_R2_GPU_20260919T220941Z/e6/analysis/E6_RESULTS.json` (`d4e2d6bd…67cf9`): `certified_q` 0.75, `certified_threshold` 0.0002611875534057617; the q=.80 row is not accepted | yes |

Cross-checks:
- The sealed run's `frozen_config.json` `thresholds` block carries the same two ARC values, with `source_sha256` equal to the two deployment files above.
- E9B's `src/e9b_common.py` `POLICIES` and `large/protocol/e6_deployment.json` carry the same three OBQA values.

No bracketed q differs from its record, so there is no STOP. `[frozen q]` was replaced in PREREG.md by
`q=.90, tau=0.0007095932960510254` before hashing.

Stored original-format k/n quoted in the PREREG:

| policy | k/n | from stored summary | recomputed from stored outputs (`e21b_stats.py`) |
|---|---|---|---|
| sealed Text | 20/1100 | `summary/primary_sealed.csv`, SHA `bd602c13…` | 20/1100 |
| sealed C2C | 11/1047 | `summary/primary_sealed.csv` | 11/1047 |
| held-out Text | 12/595 | `analysis/E9B_RESULTS.json`, SHA `f4ec419b…` | 12/595 |
| held-out C2C | 13/595 | `analysis/E9B_RESULTS.json` | 13/595 |
| held-out Text+fact | 16/558 | `analysis/E9B_RESULTS.json` | 16/558 |

- The recomputation uses omitted = stored u <= tau and changed = stored R answer != stored reference answer under parser V2.
- It was run with the hashed stats code on the stored outputs during the login-node test.

## 4. E4 V1 rotation (the only rotation used)

- Source: `P2_R1_EXP_20260919T050555Z/src/prepare_populations.py`, SHA-256
  `f4941cf4f4efd5d7face281c63586b587037d5102b953538269c890c68b1213f`. This equals the hash in that stage's
  `PROTOCOL_FREEZE.md` §8. Functions used: `labels(k)` and `rotate(q)`.
- The file's module body writes population files, so it cannot be imported plainly. The driver and the stats script
  parse it with `ast` and exec only the two function definitions, after asserting the file hash. The code is used
  unchanged.
- **Reading of the code:**
  - `rotate` asserts `choice_labels == [A, B, …]`.
  - It sets `choice_text' = [t[K-1]] + t[:K-1]`, so original option i sits at position (i+1) mod K.
  - It keeps `choice_labels` unchanged; labels stay in their displayed positions.
  - It rotates a `choices` field identically if present. The driver's question dict has no `choices` field.
  - It returns `back = {label at p: label at (p-1) mod K}`.
  - It is a pure permutation of option contents with labels in place, as the PREREG requires.
- The mapping back is the same one E4 used in `e4_null.py` (`v1_display_to_original[displayed]`, INVALID stays INVALID).
  The mapped-back label is the letter of the original option index.
- **Random draw: none.** V1 is a deterministic shift by one position, so the PREREG's "derived from the question id"
  rule does not apply.
- Questions with K != 4 (7 sealed ARC) are rotated by the same rule over their own K options.
- For the 22 sealed ARC questions with numeric original labels, the sealed inputs already show letters in original order. V1 applies to the displayed letters, and mapping back gives the original option index.
- The Text+fact fact line is not rotated. It is prepended to the helper body of the rotated question by E9B's
  unchanged `format_openbook_e6`.

## 5. Runtime, prompt builders, parser (all unchanged)

| item | path | SHA-256 |
|---|---|---|
| E9B large driver (base of `src/e21b_exec.py`) | `P2_R3_E9BC_20260920T061042Z/large/src/e9b_exec.py` | `df21bf0f8ebcf9650278bf682c95a615b8db544441206d1c8cf821ce0bc8c28e` |
| E9B helpers (population, facts; imported read-only) | `P2_R3_E9BC_20260920T061042Z/src/e9b_common.py` | `0ee1f997df1c2a6c5ed42c42c3223f743c2a6a40a81788e6a5f70850881e355b` |
| native_adapter (Runtime; equals the sealed run's) | `P2_R3_E9BC_20260920T061042Z/large/src/native_adapter.py` | `4709d439ec57f5e64dc79ba85f1295f73d1b08b29da2588c830b1e2daa22aab7` |
| common (ClusterA adaptation of the sealed common.py) | `P2_R3_E9BC_20260920T061042Z/large/src/common.py` | `0ff6b7ed00b0d231f7d68960fd835c3a58120b53d4945ee53893091cf05b3d8c` |
| probe prompt builder | `P2_R3_E9BC_20260920T061042Z/large/src/receiver_prompt.py` | `868a4760d92b123127b347a9e5e69dec2f00855d17e2eee0eec4876d7cb21c66` |
| stage config | `P2_R3_E9BC_20260920T061042Z/large/frozen_config.json` | `4fce806e4b928b8ac1c6fa74bfa59eef67a9ea42c88af2675eb16300bb7d2719` |
| P2_10 runtime (R/Text/C2C actions) | `P2_10_20260911T122423Z/runtime.py` | `a6888586a8bd5f13c62ccc17079f4bd86e34bfa1ada2d804a4d502dfec726514` |
| legacy_methods (helper/receiver/C2C bundles) | `P2_10_20260911T122423Z/legacy_methods.py` | `91b03c146f56fe151dc399c4202411974afb61c4a195080cf8c54abd584bffdf` |
| prompt builders | `P2_10_20260911T122423Z/arc_protocol.py` | `b88840e37086c82dc6d485fe6ed3777bd99feb9718a47c901b4d4a5ad74ddbbe` |
| | `P2_10_20260911T122423Z/arc_runtime_adapter.py` | `c6f6127037ec6e3a75aad6c5ccc78e005c95916fd57b89261684e15206d79f76` |
| | `P2_10_20260911T122423Z/protocol_min.py` (= `P2_5_20260910T072811Z/protocol_min.py`) | `23c702e16ff5b2bb164ab25ef4e35f4105ac81becb83747c138d222faab2cd35` |
| parser V2 | `P2_SCORING_V2_20260912T191445Z/scoring_v2.py` | `d05978f400cf69aa6bddc56168a260ac3ea9158abaa640e9331602dc9bfcc2f9` |
| prompt/parser documentation | `P2_R5_E13_20260921T031606Z/PROMPTS_AND_PARSER.md` | `e7ae0047fe2c12d48ae30d87a817d8f6ef20e1d8c8289a00339ddaad7f02847e` |

- The sealed run's `native_adapter.py` and `receiver_prompt.py` are byte-identical to E9B's copies.
- The sealed and E9B `frozen_config.json` files differ only in bookkeeping keys. `native`, `native_root`, `parser_path`, `parser_sha256`, `prefix`, `topology` and `timing` are identical, and so are `protocol/label_token_sets.json`, `prefix_ids.json`, `chat_template.jinja` and `PROBE_PROTOCOL_FREEZE.json`.
- All 25 files listed in `P2_10_20260911T122423Z/frozen_config.json` `execution_source_sha256` match.
- Models (from `frozen_config.json` `native.models`):
  - helper `Qwen/Qwen2.5-7B-Instruct@a09a35458c702b33eeacc393d103063234e8bc28`
  - receiver `Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218`
  - fuser `nics-efc/C2C_Fuser@f01fc3258b305e280e04c7238f4f2cf31b7dc70d` (`qwen3_8b+qwen2.5_7b_Fuser/final`)
- Settings: bf16, sdpa, greedy decoding; receiver `max_new_tokens` 64, helper 256 (legacy_methods).
- Hardware: the sealed run used ClusterB A100-SXM4-40GB; E9B and E21B use ClusterA A100-SXM4-40GB. Both use the same Python env, `c2c_official` (torch 2.6.0, transformers 4.52.4).

## 6. Preflight rows (`preflight/ROWS.json`, written by `e21b_stats.py select` from query files and stored outputs only)

- P1 and P3, sealed ARC: the first 16 questions in ordinal order that have a stored R. These are ordinals 0.. up to `Mercury_7166425`.
- P1 and P3, held-out OBQA: the first 16 questions in population order, `9-732` … `9-1013`.
- P2 extra: every sealed ARC question with K != 4 or non-letter original labels, 28 questions (7 with K != 4, 22 with numeric labels; the two groups overlap).

## 7. Cost estimate (stored per-request timings) and job plan

- Sealed ARC, from the ClusterB run (1,172 questions):
  - probe 49.9 s
  - R 314.3 s (mean action 268.2 ms x 1,172)
  - Text 1,227.8 s
  - C2C 485.8 s
  - total 2,077.8 s
- Held-out OBQA, from E9B on ClusterA (744 questions): probe 25.2 + R 152.2 + Text 594.9 + C2C 202.7 + Text+fact 561.0 = 1,536.0 s.
- Total 3,613.8 slot-seconds (60.2 slot-minutes). One slot is 2 GPUs, because the frozen Runtime puts the helper on cuda:0 and the receiver on cuda:1.
- 2 nodes give 4 slots, about 15.1 min of production per slot.
- Preflight takes about 30 s per part. Cold model load took up to 187 s in E9B, and a warm reload about 25 s. The gate takes 1-3 min.
- Expected per-slot wall time is about 22-25 min, against a 50 min walltime. The drivers stop cleanly at T+46 min.
- **One debug job of 2 nodes is enough, so job 2 is not planned.** The driver resumes, so a second job could finish a partial run only as the one allowed resubmission for a non-scientific failure.
