# E14 results (Round 6): sealed ARC under the official C2C extractor; zero-uncertainty questions among omitted questions

Stage `$DATA_DIR/P2_R6_E14_20260921T052241Z`. POST-HOC CPU re-analysis of stored outputs on the ClusterA login node. No model was run, no GPU and no PBS job was used.

| | |
|---|---|
| Preregistration | `PREREG_E14.md`, SHA-256 `b9877181ca0f0a27557066947a0d90ce25fef7ab81a57fa1a890a5de1ce46e32`, hashed 2026-09-21T05:23:00Z (`PREREG_E14.sha256`) |
| First E14 computation | 2026-09-21T05:31:11Z: first attempt, 8 min after the hash; it stopped after check (i) on a wrong module reference, before any E14-1/E14-2 number (see `DEVIATIONS.md`). Complete run 2026-09-21T05:31:25Z to 2026-09-21T05:32:19Z |
| Reproduction checks | 49 / 49 PASS (`results/E14_checks.csv`) |
| Deviations | `DEVIATIONS.md` |
| Scripts | `scripts/e14.py` (all computation), `scripts/make_results.py` (this file); log `logs/e14.log` |
| `__pycache__` | none created: `logs/pycache_before.txt` == `logs/pycache_after.txt` (PYTHONDONTWRITEBYTECODE=1) |

## 1. Reproduction checks (all PASS)

(i) sealed ARC, parser V2 as executed (`P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/records/e2e_requests.jsonl`, cross-checked with `records/paired_sealed_2344.jsonl` and `summary/primary_sealed.csv`); the stored runtime parse equals a re-parse with frozen V2 on all 4,688 outputs:

- large/ARC/Text: omitted / changed = 1100 / 20 (PASS)
- large/ARC/C2C: omitted / changed = 1047 / 11 (PASS)

(ii) dev omitted / changed at each E14-2 policy row: frozen deployment record = recomputation from the stored cal/dev outputs and ProbeMax scores (the calibration n / k at the same threshold also equals the stored calibration ledger row):

| policy | dev omitted | dev changed | cal omitted | cal changed | frozen dev record |
|---|---:|---:|---:|---:|---|
| large/OBQA/Text | 572 | 19 | 1064 | 18 | `P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/summary/main_dev.csv` |
| large/OBQA/C2C | 572 | 13 | 1064 | 22 | `P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/summary/main_dev.csv` |
| large/ARC/Text | 284 | 9 | 422 | 4 | `P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/summary/main_dev.csv` |
| large/ARC/C2C | 270 | 3 | 404 | 7 | `P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/summary/main_dev.csv` |
| medium/OBQA/C2C q=.55 | 390 | 11 | 739 | 19 | `P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/summary/compact_summary.csv` |
| medium/OBQA/C2C q=.50 | 355 | 7 | 665 | 10 | `P2_R2_CPU_20260919T220412Z/followup/results/f1c_medium_obqa_C2C_dev.csv` |
| medium/ARC/C2C | 189 | 4 | 290 | 1 | `P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/summary/compact_summary.csv` |
| large/MMLU-Pro/Text | 1069 | 40 | 2358 | 67 | `P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/summary/compact_table.csv` |
| large/MMLU-Pro/C2C | 1069 | 37 | 2358 | 75 | `P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/summary/compact_table.csv` |
| large/OBQA/Text+fact | 536 | 13 | 999 | 22 | `P2_R2_GPU_20260919T220941Z/e6/analysis/E6_SUMMARY.csv` |

The frozen thresholds equal the deployment files (`deployments/*.json`, `e6_deployment.json`, medium/MMLU-Pro summaries), and the thresholds used in E9b and in the sealed run equal them too (asserted).

(iii) the official-extractor port (`P2_R2_CPU_20260919T220412Z/scripts/parsers_r2.py::label_official`, source `c2c_reproduction_assets/official_C2C/rosetta/utils/evaluate.py`, SHA-256 `b341338aecf1cf07a5cb61664b8dac5f2ff96b32622e54eb37b32604deeddf16`) on the 448 large/ARC/C2C calibration rows reproduces E11(b): the per-setting counts in `P2_R4_E11_20260920T224016Z/results/E11b_two_conventions.csv`, the 20-candidate OFFICIAL (n, k) ledger in `E11b_grid.csv`, and the label of every one of the 2 x 448 outputs (against `P2_R2_CPU_20260919T220412Z/followup/results/f1b_differences.csv`, 0 mismatches).

  Counts: `{"cal_N": 448, "all_applicable": true, "cal_o_R_differs": 0, "cal_o_ref_differs": 25, "cal_d_label_differs": 21, "cal_rows_label_differs": 25, "cal_INVALID_R_official": 0, "cal_INVALID_ref_official": 24}`

Also checked: E9b omitted / changed for all five held-out rows equal `E9B_RESULTS.json`; the three "known before" u = 0 counts (354/742, 217/299, 713/3,000) reproduce.

## 2. E14-1 — sealed ARC under the official C2C extractor

**Inclusion rule (as in E11(b)):** a question is included iff its displayed option labels are a subset of {A, B, C, D} (`parsers_r2.official_applicable`); the official extractor hard-codes A-D. Excluded: **3** of 1,172 sealed questions, all with five options A-E (TIMSS_1995_8_J7, TIMSS_2007_8_pg53, TIMSS_1995_8_N4); all three are omitted by both policies. Kept as in E11(b): the 4 three-option questions (A-C; an official read outside the set -> unparseable) and the 22 questions whose original labels were 1-4/1-3 (displayed and parsed as A-D/A-C, the labels the models saw). Label sets of the 1,172: {'ABCD': 1165, 'ABC': 4, 'ABCDE': 3}.

Routing: the frozen routing as executed (`selected == R`, identical to ProbeMax <= tau). Labels: the stored raw outputs of R (the policy request on omitted questions) and of the reference request. Convention: both unparseable = agreement; exactly one unparseable = change. CP = two-sided 95% Clopper-Pearson; p = P[Bin(n, .05) <= k] (one-sided exact, H0: rho >= .05; descriptive, not a certificate).

| policy | extractor | excluded (omitted) | n | k | k/n | CP 95% | p | k, both-unparseable = change | exactly one unparseable | questions with an R or reference label diff (by category) | rule branch |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| large/ARC/C2C | official | 3 | 1044 | 54 | 5.17% | [3.91%, 6.70%] | 0.635 | 54 | 44 | 44 (C1 0, C2 44, C3 0, other 0) | c |
| large/ARC/C2C | V2 (same subset) | 3 | 1044 | 11 | 1.05% | [0.53%, 1.88%] | 2.26e-12 | 11 | 0 |  | a (descriptive) |
| large/ARC/C2C | V2 (all 1,172, as executed) | 0 | 1047 | 11 | 1.05% | [0.53%, 1.87%] | 2e-12 | 11 |  |  |  |
| large/ARC/Text | official | 3 | 1097 | 20 | 1.82% | [1.12%, 2.80%] | 3.26e-08 | 20 | 0 | 0 (C1 0, C2 0, C3 0, other 0) | a (descriptive) |
| large/ARC/Text | V2 (same subset) | 3 | 1097 | 20 | 1.82% | [1.12%, 2.80%] | 3.26e-08 | 20 | 0 |  | a (descriptive) |
| large/ARC/Text | V2 (all 1,172, as executed) | 0 | 1100 | 20 | 1.82% | [1.11%, 2.79%] | 2.95e-08 | 20 |  |  |  |

Categories (E5-a follow-up): C1 = ambiguous or repeated letters read as the first letter; C2 = leading label + option text containing one of the extractor's math-indicator substrings (tan/sin/"/" and the rest of its list), so the official extractor returns nothing; C3 = last-letter read ("A. 0 C"); other. Every differing output, with its raw text, is in `results/E14_1_label_diffs.csv`; counts by transition / pattern / branch in `results/E14_1_label_diff_categories.csv`:

| policy | output | category | transition | V2 -> official | count |
|---|---|---|---|---|---:|
| large/ARC/C2C | reference | C2 | label->INVALID (leading_label_then_option_text, blocked_by_math_substring) | A->INVALID | 8 |
| large/ARC/C2C | reference | C2 | label->INVALID (leading_label_then_option_text, blocked_by_math_substring) | B->INVALID | 17 |
| large/ARC/C2C | reference | C2 | label->INVALID (leading_label_then_option_text, blocked_by_math_substring) | C->INVALID | 5 |
| large/ARC/C2C | reference | C2 | label->INVALID (leading_label_then_option_text, blocked_by_math_substring) | D->INVALID | 14 |

**Paper rule (C2C policy): branch (c).** Under the official extractor the sealed C2C change rate is 54/1044 = 5.17%, CP 95% [3.91%, 6.70%], p = 0.635: the point estimate is above 5%, so the paper states in Sec. 4.5, and wherever the abstract cites the sealed C2C result, that the sealed C2C result holds under our extractor only. All 44 label differences are C2C reference outputs of the form `X. <option text>` that the official extractor cannot read (V2 label -> unparseable, R parses), each of which counts as a change under the fixed convention. Text policy (descriptive): branch (a), 20/1097 = 1.82% [1.12%, 2.80%]; the two extractors give identical labels on all 1097 included omitted questions.

## 3. E14-2 — zero-uncertainty questions among omitted questions

u = 0 means ProbeMax == 0.0 exactly as stored. n = omitted; n0 / k0 = omitted with u = 0 and changes among them; n+ / k+ = omitted with u > 0 and changes among them. Every u = 0 question is omitted (no frozen tau is below 0; asserted). Labels: frozen parser V2, paper convention. CP = two-sided 95% Clopper-Pearson. Source of every row: `results/E14_2_zero_u.csv`.

### Development split

| policy | N | u=0 among all N | n | n0/n | k0/n0 [CP 95%] | k+/n+ [CP 95%] | rule triggers |
|---|---:|---:|---:|---:|---|---|---|
| large/OBQA/Text | 742 | 354 (47.7%) | 572 | 354/572 = 61.9% | 2/354 = 0.56% [0.07%, 2.03%] | 17/218 = 7.80% [4.61%, 12.19%] | none |
| large/OBQA/C2C | 742 | 354 (47.7%) | 572 | 354/572 = 61.9% | 1/354 = 0.28% [0.01%, 1.56%] | 12/218 = 5.50% [2.88%, 9.42%] | none |
| large/ARC/Text | 299 | 217 (72.6%) | 284 | 217/284 = 76.4% | 0/217 = 0.00% [0.00%, 1.69%] | 9/67 = 13.43% [6.33%, 23.97%] | k+/n+ CP lower > 5% |
| large/ARC/C2C | 299 | 217 (72.6%) | 270 | 217/270 = 80.4% | 1/217 = 0.46% [0.01%, 2.54%] | 2/53 = 3.77% [0.46%, 12.98%] | none |
| medium/OBQA/C2C q=.55 | 742 | 321 (43.3%) | 390 | 321/390 = 82.3% | 7/321 = 2.18% [0.88%, 4.44%] | 4/69 = 5.80% [1.60%, 14.18%] | none |
| medium/OBQA/C2C q=.50 (appendix only) | 742 | 321 (43.3%) | 355 | 321/355 = 90.4% | 7/321 = 2.18% [0.88%, 4.44%] | 0/34 = 0.00% [0.00%, 10.28%] | n0/n >= 90% |
| medium/ARC/C2C | 299 | 174 (58.2%) | 189 | 174/189 = 92.1% | 1/174 = 0.57% [0.01%, 3.16%] | 3/15 = 20.00% [4.33%, 48.09%] | n0/n >= 90% |
| large/MMLU-Pro/Text | 2641 | 645 (24.4%) | 1069 | 645/1069 = 60.3% | 8/645 = 1.24% [0.54%, 2.43%] | 32/424 = 7.55% [5.22%, 10.49%] | k+/n+ CP lower > 5% |
| large/MMLU-Pro/C2C | 2641 | 645 (24.4%) | 1069 | 645/1069 = 60.3% | 5/645 = 0.78% [0.25%, 1.80%] | 32/424 = 7.55% [5.22%, 10.49%] | k+/n+ CP lower > 5% |
| large/OBQA/Text+fact | 742 | 354 (47.7%) | 536 | 354/536 = 66.0% | 1/354 = 0.28% [0.01%, 1.56%] | 12/182 = 6.59% [3.45%, 11.23%] | none |

### Calibration split (p+ = P[Bin(n+, .05) <= k+], u > 0 part alone at the frozen threshold; descriptive)

| policy | N | u=0 among all N | n | n0/n | k0/n0 [CP 95%] | k+/n+ [CP 95%] | p+ |
|---|---:|---:|---:|---:|---|---|---|
| large/OBQA/Text | 1366 | 642 (47.0%) | 1064 | 642/1064 = 60.3% | 1/642 = 0.16% [0.00%, 0.86%] | 17/422 = 4.03% [2.36%, 6.37%] | 0.214 |
| large/OBQA/C2C | 1366 | 642 (47.0%) | 1064 | 642/1064 = 60.3% | 2/642 = 0.31% [0.04%, 1.12%] | 20/422 = 4.74% [2.92%, 7.22%] | 0.46 |
| large/ARC/Text | 448 | 321 (71.7%) | 422 | 321/422 = 76.1% | 0/321 = 0.00% [0.00%, 1.14%] | 4/101 = 3.96% [1.09%, 9.83%] | 0.427 |
| large/ARC/C2C | 448 | 321 (71.7%) | 404 | 321/404 = 79.5% | 2/321 = 0.62% [0.08%, 2.23%] | 5/83 = 6.02% [1.98%, 13.50%] | 0.765 |
| medium/OBQA/C2C q=.55 | 1366 | 601 (44.0%) | 739 | 601/739 = 81.3% | 7/601 = 1.16% [0.47%, 2.38%] | 12/138 = 8.70% [4.57%, 14.70%] | 0.979 |
| medium/OBQA/C2C q=.50 (appendix only) | 1366 | 601 (44.0%) | 665 | 601/665 = 90.4% | 7/601 = 1.16% [0.47%, 2.38%] | 3/64 = 4.69% [0.98%, 13.09%] | 0.601 |
| medium/ARC/C2C | 448 | 256 (57.1%) | 290 | 256/290 = 88.3% | 1/256 = 0.39% [0.01%, 2.16%] | 0/34 = 0.00% [0.00%, 10.28%] | 0.175 |
| large/MMLU-Pro/Text | 6000 | 1442 (24.0%) | 2358 | 1442/2358 = 61.2% | 14/1442 = 0.97% [0.53%, 1.62%] | 53/916 = 5.79% [4.36%, 7.50%] | 0.877 |
| large/MMLU-Pro/C2C | 6000 | 1442 (24.0%) | 2358 | 1442/2358 = 61.2% | 9/1442 = 0.62% [0.29%, 1.18%] | 66/916 = 7.21% [5.62%, 9.08%] | 0.999 |
| large/OBQA/Text+fact | 1366 | 642 (47.0%) | 999 | 642/999 = 64.3% | 2/642 = 0.31% [0.04%, 1.12%] | 20/357 = 5.60% [3.46%, 8.52%] | 0.747 |

### Held-out 744 OBQA questions (E9b)

| policy | N | u=0 among all N | n | n0/n | k0/n0 [CP 95%] | k+/n+ [CP 95%] |
|---|---:|---:|---:|---:|---|---|
| large/OBQA/Text | 744 | 346 (46.5%) | 595 | 346/595 = 58.2% | 1/346 = 0.29% [0.01%, 1.60%] | 11/249 = 4.42% [2.23%, 7.77%] |
| large/OBQA/C2C | 744 | 346 (46.5%) | 595 | 346/595 = 58.2% | 2/346 = 0.58% [0.07%, 2.07%] | 11/249 = 4.42% [2.23%, 7.77%] |
| medium/OBQA/C2C q=.55 | 744 | 306 (41.1%) | 388 | 306/388 = 78.9% | 5/306 = 1.63% [0.53%, 3.77%] | 3/82 = 3.66% [0.76%, 10.32%] |
| medium/OBQA/C2C q=.50 (appendix only) | 744 | 306 (41.1%) | 346 | 306/346 = 88.4% | 5/306 = 1.63% [0.53%, 3.77%] | 1/40 = 2.50% [0.06%, 13.16%] |
| large/OBQA/Text+fact | 744 | 346 (46.5%) | 558 | 346/558 = 62.0% | 1/346 = 0.29% [0.01%, 1.60%] | 15/212 = 7.08% [4.01%, 11.40%] |

### Sealed ARC test (1,172)

| policy | N | u=0 among all N | n | n0/n | k0/n0 [CP 95%] | k+/n+ [CP 95%] |
|---|---:|---:|---:|---:|---|---|
| large/ARC/Text | 1172 | 837 (71.4%) | 1100 | 837/1100 = 76.1% | 0/837 = 0.00% [0.00%, 0.44%] | 20/263 = 7.60% [4.71%, 11.50%] |
| large/ARC/C2C | 1172 | 837 (71.4%) | 1047 | 837/1047 = 79.9% | 0/837 = 0.00% [0.00%, 0.44%] | 11/210 = 5.24% [2.64%, 9.18%] |

### Per receiver x benchmark (u is receiver-only; identical for Text and C2C, asserted)

| receiver | benchmark | split | u = 0 | share |
|---|---|---|---:|---:|
| Qwen3-1.7B (medium) | OBQA | dev | 321/742 | 43.3% |
| Qwen3-1.7B (medium) | ARC | dev | 174/299 | 58.2% |
| Qwen3-1.7B (medium) | MMLU-Pro | dev | 324/2641 | 12.3% |
| Qwen3-8B (large) | OBQA | dev | 354/742 | 47.7% |
| Qwen3-8B (large) | ARC | dev | 217/299 | 72.6% |
| Qwen3-8B (large) | MMLU-Pro | dev | 645/2641 | 24.4% |
| Qwen3-8B (large) | MMLU-Pro | fit (groups) | 713/3000 | 23.8% |

### Frozen thresholds (`results/E14_2_thresholds.csv`)

| policy | q | tau | tau == 0 | fit candidates (of 20) equal to 0 |
|---|---:|---:|---|---:|
| large/OBQA/Text | 0.8 | 0.00117004 | False | 9 |
| large/OBQA/C2C | 0.8 | 0.00117004 | False | 9 |
| large/ARC/Text | 0.95 | 0.018007 | False | 14 |
| large/ARC/C2C | 0.9 | 0.000709593 | False | 14 |
| medium/OBQA/C2C q=.55 | 0.55 | 1.3113e-06 | False | 9 |
| medium/OBQA/C2C q=.50 | 0.5 | 2.38419e-07 | False | 9 |
| medium/ARC/C2C | 0.6 | 3.57628e-07 | False | 11 |
| large/MMLU-Pro/Text | 0.4 | 3.83854e-05 | False | 4 |
| large/MMLU-Pro/C2C | 0.4 | 3.83854e-05 | False | 4 |
| large/OBQA/Text+fact | 0.75 | 0.000261188 | False | 9 |

**tau == 0 for no policy.** Several lower fit candidates are exactly 0 (column 5), but no deployed threshold is.

### Paper rule outcomes (dev)

- Main-text sentence, over the nine deployed thresholds on dev: n0/n ranges 60.3% (large/MMLU-Pro/Text, 645/1069) to 92.1% (medium/ARC/C2C, 174/189); k0/n0 ranges 0.0% (large/ARC/Text, 0/217) to 2.2% (medium/OBQA/C2C q=.55, 7/321); k+/n+ ranges 3.8% (large/ARC/C2C, 2/53) to 20.0% (medium/ARC/C2C, 3/15).
- dev k+/n+ CP lower end > 5% (paper names the policy and states that its certificate rests on the zero-uncertainty questions): **large/ARC/Text** (9/67, CP lower 6.33%); **large/MMLU-Pro/Text** (32/424, CP lower 5.22%); **large/MMLU-Pro/C2C** (32/424, CP lower 5.22%).
- dev n0/n >= 90% (paper states the certificate mostly covers questions the receiver treats as certain): **medium/OBQA/C2C q=.50** (the q = .50 appendix row) (321/355 = 90.4%); **medium/ARC/C2C** (174/189 = 92.1%).
- Always: the appendix table (the four population tables above).

## 4. Files read by the computation

Every file opened for reading by `scripts/e14.py` is logged in `results/E14_files_read.txt` (148 paths, including the two Python-environment files opened by the interpreter). The code modules imported (not data): `P2_R4_E11_20260920T224016Z/scripts/e11_common.py`, `P2_R2_CPU_20260919T220412Z/scripts/{r2_common,rawio,parsers_r2}.py`, `P2_R1_CPU_20260919T045556Z/src/{common_r1,data_r1}.py`; exec'd from source: `scoring_v2.py`, `diagnostic_parser_v1.py` (loaded by parsers_r2, unused here), the official `evaluate.py::extract_answer_from_content`, and `f1b_official_diffs.py::{official_branch, surface_pattern}`.

```
$DATA_DIR/software/envs/c2c_official/lib/python310.zip
$DATA_DIR/software/envs/c2c_official/lib/python3.10/site-packages/numpy-2.2.6.dist-info/direct_url.json
$DATA_DIR/c2c_reproduction_assets/official_C2C/rosetta/utils/evaluate.py
$DATA_DIR/P2_SCORING_V2_20260912T191445Z/scoring_v2.py
$DATA_DIR/P2_SCORE_SENSITIVITY_20260912T055929Z/diagnostic_parser_v1.py
$DATA_DIR/P2_R2_CPU_20260919T220412Z/followup/scripts/f1b_official_diffs.py
$DATA_DIR/P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/frozen_config.json
$DATA_DIR/P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/inputs/test_queries_no_gold.jsonl
$DATA_DIR/P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/records/e2e_requests.jsonl
$DATA_DIR/P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/records/paired_sealed_2344.jsonl
$DATA_DIR/P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/summary/primary_sealed.csv
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/summary/main_dev.csv
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/summary/compact_summary.csv
$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/summary/compact_table.csv
$DATA_DIR/P2_R2_GPU_20260919T220941Z/e6/analysis/E6_SUMMARY.csv
$DATA_DIR/P2_R2_CPU_20260919T220412Z/followup/results/f1c_medium_obqa_C2C_dev.csv
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/deployments/large_obqa_T.json
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/deployments/large_obqa_C.json
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/deployments/large_arc_T.json
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/deployments/large_arc_C.json
$DATA_DIR/P2_R3_E9BC_20260920T061042Z/large/protocol/e6_deployment.json
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/summary/calibration_all_160.csv
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/calibration/obqa_T.csv
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/calibration/obqa_C.csv
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/calibration/arc_T.csv
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/calibration/arc_C.csv
$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/calibration/40_test_ledger.csv
$DATA_DIR/P2_R2_GPU_20260919T220941Z/e6/analysis/E6_LEDGER.csv
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/records/small_obqa_fit_probes.jsonl
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/records/small_obqa_cal_probes.jsonl
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/records/small_obqa_dev_probes.jsonl
$DATA_DIR/P2_SCORING_V2_20260912T191445Z/labels/full_train_P2_SCORING_V2.jsonl
$DATA_DIR/P2_SCORING_V2_20260912T191445Z/labels/full_development_P2_SCORING_V2.jsonl
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/splits/obqa_fit_representatives.json
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/splits/obqa_cal_representatives.json
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/splits/obqa_dev_representatives.json
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/thresholds/small_obqa.json
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/records/small_arc_fit_probes.jsonl
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/records/small_arc_cal_probes.jsonl
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/records/small_arc_dev_probes.jsonl
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/splits/arc_fit_representatives.json
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/splits/arc_cal_representatives.json
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/splits/arc_dev_representatives.json
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/thresholds/small_arc.json
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/probes/obqa_fit.jsonl
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/actions/obqa_fit.jsonl
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/splits/obqa_fit_representatives.json
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/probes/obqa_cal.jsonl
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/actions/obqa_cal.jsonl
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/splits/obqa_cal_representatives.json
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/probes/obqa_dev.jsonl
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/actions/obqa_dev.jsonl
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/splits/obqa_dev_representatives.json
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/splits/obqa_dev_ids.json
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/thresholds/obqa.json
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/probes/arc_fit.jsonl
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/actions/arc_fit.jsonl
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/splits/arc_fit_representatives.json
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/probes/arc_cal.jsonl
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/actions/arc_cal.jsonl
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/splits/arc_cal_representatives.json
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/probes/arc_dev.jsonl
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/actions/arc_dev.jsonl
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/splits/arc_dev_representatives.json
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/splits/arc_dev_ids.json
$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/thresholds/arc.json
$DATA_DIR/P2_ZERO_GOLD_CONTROLS_20260914T065145Z/records/probe_records.jsonl
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/thresholds/large_obqa.json
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/records/large_arc_fit_probes.jsonl
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/records/large_arc_cal_probes.jsonl
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/records/large_arc_dev_probes.jsonl
$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/thresholds/large_arc.json
$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/summary/merged_numeric_rows.jsonl
$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/shards/1/probes/cal.jsonl
$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/shards/1/probes/fit.jsonl
$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/shards/2/probes/cal.jsonl
$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/shards/2/probes/dev.jsonl
$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/splits/fit_groups.json
$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/splits/cal_groups.json
$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/splits/dev_groups.json
$DATA_DIR/P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/thresholds/fit_thresholds.json
$DATA_DIR/P2_R2_GPU_20260919T220941Z/e6/main/e6_shard0.jsonl
$DATA_DIR/P2_R2_GPU_20260919T220941Z/e6/main/e6_shard1.jsonl
$DATA_DIR/P2_R2_GPU_20260919T220941Z/e6/main/e6_shard2.jsonl
$DATA_DIR/P2_R2_GPU_20260919T220941Z/e6/main/e6_shard3.jsonl
$DATA_DIR/P2_9_20260911T045010Z/results/large/train_cases.jsonl
$DATA_DIR/P2_R4_E11_20260920T224016Z/results/E11b_two_conventions.csv
$DATA_DIR/P2_R4_E11_20260920T224016Z/results/E11b_grid.csv
$DATA_DIR/P2_R2_CPU_20260919T220412Z/followup/results/f1b_differences.csv
$DATA_DIR/P2_R2_CPU_20260919T220412Z/results/e5a_parser_sources.csv
$DATA_DIR/P2_R3_E9BC_20260920T061042Z/analysis/SEALED_ROUTES.jsonl
$DATA_DIR/P2_R3_E9BC_20260920T061042Z/analysis/E9B_RESULTS.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/inputs/queries_only.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_00/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_00/actions/fit.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_00/probes/fit.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_01/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_01/actions/fit.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_01/probes/fit.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_02/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_02/actions/fit.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_02/probes/fit.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_03/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_03/actions/fit.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_03/probes/fit.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_04/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_04/actions/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_04/actions/fit.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_04/probes/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_04/probes/fit.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_05/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_05/actions/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_05/probes/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_06/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_06/actions/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_06/probes/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_07/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_07/actions/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_07/probes/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_08/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_08/actions/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_08/probes/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_09/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_09/actions/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_09/probes/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_10/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_10/actions/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_10/probes/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_11/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_11/actions/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_11/probes/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_12/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_12/actions/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_12/actions/dev.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_12/probes/cal.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_12/probes/dev.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_13/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_13/actions/dev.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_13/probes/dev.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_14/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_14/actions/dev.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_14/probes/dev.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_15/LANE_COMPLETE.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_15/actions/dev.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/medium/lane_15/probes/dev.jsonl
$DATA_DIR/P2_R2_E8_20260920T012544Z/splits/cal_groups.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/splits/dev_groups.json
$DATA_DIR/P2_R2_E8_20260920T012544Z/analysis/thresholds/medium_fit_thresholds.json
```
