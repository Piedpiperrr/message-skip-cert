# P2_R1_EXP summary

Generated 2026-09-19T09:00:22.821174+00:00 by src/analyze_r1.py. Folder: `$DATA_DIR/P2_R1_EXP_20260919T050555Z`.
All counts from files in this folder (hashes in results/OUTPUT_HASHES.json, computed before gold was read). Primary parser: frozen P2_SCORING_V2 (sha d05978f4...), INVALID kept in N and counted wrong.

## E1 C2C port fidelity (official OBQA test, N=500)

Official dataset prefetch: {"clean_usable": true, "config": "main", "n": 500, "rows_identical_in_order_to_local_parquet": 500}. Legacy (official) parser source identical to P2_10 copy: True.

| pair | action | path | n_available | correct_v2_of_500 | invalid_v2 | correct_legacy_parser_of_500 | correct_official_evaluator_reported | source |
|---|---|---|---|---|---|---|---|---|
| small | Receiver-only | OFFICIAL | 500 | 191 | 28 | 198 | 198 | clean clone evaluator (this job) |
| small | Receiver-only | OURS | 500 | 191 | 28 | 198 |  | results/e1/ours/small.jsonl |
| small | C2C | OFFICIAL | 500 | 263 | 0 | 263 | 263 | task7 (runtime-patch evaluator, job 164991, reused) |
| small | C2C | OURS | 500 | 263 | 0 | 263 |  | results/e1/ours/small.jsonl |
| medium | Receiver-only | OFFICIAL | 500 | 327 | 7 | 326 | 326 | clean clone evaluator (this job) |
| medium | Receiver-only | OURS | 500 | 327 | 7 | 326 |  | results/e1/ours/medium.jsonl |
| medium | C2C | OFFICIAL | 500 | 317 | 6 | 321 | 321 | clean clone evaluator (this job) |
| medium | C2C | OURS | 500 | 317 | 6 | 321 |  | results/e1/ours/medium.jsonl |
| large | Receiver-only | OFFICIAL | 500 | 425 | 0 | 425 | 425 | clean clone evaluator (this job) |
| large | Receiver-only | OURS | 500 | 425 | 0 | 425 |  | results/e1/ours/large.jsonl |
| large | C2C | OFFICIAL | 500 | 405 | 2 | 395 | 395 | clean clone evaluator (this job) |
| large | C2C | OURS | 500 | 405 | 2 | 395 |  | results/e1/ours/large.jsonl |

OURS vs OFFICIAL per pair x action (parsed with P2_SCORING_V2 on both raw outputs):

| pair | action | n_compared | parsed_answer_agreement | raw_output_exact_match | rendered_prompts_byte_identical_first3 | prompt_detail |
|---|---|---|---|---|---|---|
| small | Receiver-only | 500 | 500 | 500 | True | q0: text=True ids=True; q1: text=True ids=True; q2: text=True ids=True |
| small | C2C | 500 | 500 | 500 | True | q0: text=True ids=True; q1: text=True ids=True; q2: text=True ids=True |
| medium | Receiver-only | 500 | 500 | 500 | True | q0: text=True ids=True; q1: text=True ids=True; q2: text=True ids=True |
| medium | C2C | 500 | 500 | 500 | True | q0: text=True ids=True; q1: text=True ids=True; q2: text=True ids=True |
| large | Receiver-only | 500 | 500 | 500 | True | q0: text=True ids=True; q1: text=True ids=True; q2: text=True ids=True |
| large | C2C | 500 | 500 | 500 | True | q0: text=True ids=True; q1: text=True ids=True; q2: text=True ids=True |

Parsed-answer disagreement IDs (official_index:OBQA id):

- small Receiver-only: none
- small C2C: none
- medium Receiver-only: none
- medium C2C: none
- large Receiver-only: none
- large C2C: none

Full per-question differences: results/e1_disagreements.csv. Raw outputs: results/e1/ours/*.jsonl, results/e1/official/*/..._cot.csv (small C2C: task7 CSV).

## E4 null controls (receiver-only, content-free input changes)

R = paper saved development outputs; V1 = options rotated by one (answers mapped back); V2 = Text-reference prompt carrying the helper message of position (i+floor(N/2)) mod N. Oracle gain = (oracle - best single) / N in percentage points. V0 = supplementary same-job unchanged R replay (not requested).

| pair | population | N | V1_V2_complete | R_correct_paper_saved | V1_perm_correct | V2_irrelevant_msg_correct | oracle_R_V1_V2 | oracle_gain_R_V1_V2_pp | answer_change_rate_R_vs_V1_pct | answer_change_rate_R_vs_V2_pct | paper_oracle_R_T_C | paper_oracle_gain_pp | matches_table1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| small | obqa | 742 | True | 285 | 290 | 316 | 488 | 23.18 | 75.2 | 28.71 | 498 | 17.79 | True |
| small | arc | 299 | True | 110 | 123 | 130 | 200 | 23.41 | 69.9 | 29.77 | 204 | 16.39 | True |
| medium | obqa | 742 | True | 490 | 482 | 507 | 596 | 11.99 | 24.66 | 20.49 | 593 | 9.43 | True |
| medium | arc | 299 | True | 217 | 216 | 220 | 245 | 8.36 | 17.73 | 12.04 | 248 | 9.03 | True |
| large | obqa | 742 | True | 617 | 599 | 624 | 679 | 7.41 | 18.46 | 9.16 | 670 | 3.37 | True |
| large | arc | 299 | True | 268 | 260 | 271 | 277 | 2.01 | 6.69 | 4.01 | 280 | 2.01 | True |
| large | mmlu_pro | 2641 | True | 1282 | 1286 | 1306 | 1599 | 11.09 | 34.61 | 20.26 | 1558 | 9.05 | True |

Supplementary columns (invalid counts, pairwise oracles, V0 replay, re-parse checks): results/e4_null_controls.csv.

## E2b D features

| setting | split | pair | expected | written | dimension | ids_match_population_order | all_finite | unit_norm |
|---|---|---|---|---|---|---|---|---|
| small_obqa | dev | small | 742 | 742 | 2048 | 742 | True | True |
| small_arc | dev | small | 299 | 299 | 2048 | 299 | True | True |
| large_arc | dev | large | 299 | 299 | 8192 | 299 | True | True |
| medium_obqa | fit | medium | 2100 | 2100 | 4096 | 2100 | True | True |
| medium_obqa | cal | medium | 1366 | 1366 | 4096 | 1366 | True | True |
| medium_obqa | dev | medium | 742 | 742 | 4096 | 742 | True | True |
| medium_arc | fit | medium | 671 | 671 | 4096 | 671 | True | True |
| medium_arc | cal | medium | 448 | 448 | 4096 | 448 | True | True |
| medium_arc | dev | medium | 299 | 299 | 4096 | 299 | True | True |
| large_mmlu_pro | fit | large | 3000 | 3000 | 8192 | 3000 | True | True |
| large_mmlu_pro | cal | large | 6000 | 6000 | 8192 | 6000 | True | True |
| large_mmlu_pro | dev | large | 2641 | 2641 | 8192 | 2641 | True | True |

## Notes

- none
