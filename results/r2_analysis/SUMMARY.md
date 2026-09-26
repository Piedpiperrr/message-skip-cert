# P2_R2_ANALYSIS_20260920T002850Z — E7 arms, E6 replay, E6 development and calibration extras

**POST-HOC analysis of completed E6/E7 records.** Stage folder: `$DATA_DIR/P2_R2_ANALYSIS_20260920T002850Z`. Scripts in `scripts/`, tables in `results/`. No model was run, no job submitted, no GPU used, and no existing file was modified. ClusterA login node, CPU only.

## 0. Sources and rules

| What | Source |
|---|---|
| E7 protocol | `P2_R2_GPU_20260919T220941Z/e7/PROTOCOL_FREEZE_E7.md` |
| E6 protocol | `P2_R2_GPU_20260919T220941Z/e6/PROTOCOL_FREEZE_E6.md` |
| E7 records | `P2_R2_E7_20260919T231531Z/{large,mmlu,medium}/records_e7/e7_requests.jsonl` (job 7638030) |
| E6 replay records | `P2_R2_E7_20260919T231531Z/e6replay/records_e6/e6_replay_requests.jsonl` (job 7638030, node B) |
| E6 calibration/development outputs | `P2_R2_GPU_20260919T220941Z/e6/main/e6_shard{0..3}.jsonl` |
| E6 frozen analysis | `P2_R2_GPU_20260919T220941Z/e6/analysis/E6_RESULTS.json` (certified q = .75) |
| E3 repeat classes | `P2_R1_EXP_20260919T050555Z/results/E3_policy_savings.csv` |
| X (208 reviewed OBQA calibration questions) | `P2_R2_CPU_20260919T220412Z/results/e5a_exposed_ids.csv`, rebuilt with `scripts/r2_common.py::exposed_ids` |
| D1 parser | `P2_SCORE_SENSITIVITY_20260912T055929Z/diagnostic_parser_v1.py` |

Reused frozen code and rules, unchanged:

- **Bootstrap** — 2,000 paired resamples of the panel questions, `numpy.random.default_rng(0)`, percentile 2.5/97.5, exactly as `P2_R1_E3POL_REPEAT1_20260919T075315Z/large/src/analyze.py`.
- **Version (a)** all 128 panel questions; **version (b)** drops every question on which either compared arm made its first formal request inside the replay (each arm's minimum `attempt`), and re-draws the bootstrap block at the reduced size — the rule of `e3_build/e3_metrics.py::saving_row`.
- **Class** — `+` above zero (CI low > 0), `-` below zero (CI high < 0), `?` contains zero.
- **Saving** — paired, fixed-reference latency minus arm latency, in ms.
- **Certification tests** — `ledger_rows` of `P2_R2_CPU_20260919T220412Z/scripts/r2_common.py`: frozen fit quantile thresholds, `p = binom.cdf(k, n, .05)`, accept at `p <= .001`, deploy the largest accepted q.
- **Reference-correction columns** — definitions taken verbatim from `P2_FOCUSED_REVISION_ROUND1B_AUDIT_FIX_AND_MANUSCRIPT_20260918T072631Z/audit_v2/scripts/audit_v2.py` block C (the code behind `tab_omit_keep.tex`).

Gold labels were read only for the correct-answer counts, after every E6/E7 output was complete; the replay records themselves carry `gold_read: false`.

**Nothing contradicted either freeze file.** All programmatic stop conditions are empty (`results/E7_CHECKS.json`, `results/E6REPLAY_CHECKS.json`, `results/E6_EXTRAS_CHECKS.json`).

Panels are byte-identical to the frozen E3 panels (and, for the E6 replay, to the file named in section 3 of the E6 freeze):

| Panel | SHA-256 | Equals the E3 file |
|---|---|---|
| large/OBQA + E6 replay + medium/OBQA | `6ebbd7604ce342d4…` | yes |
| large/ARC + medium/ARC | `1fdb3fccdfa12769…` | yes |
| MMLU-Pro | `0aff4667135fd51c…` | yes |
| E6 replay OBQA queries | `cbaee992cee5b5b9…` | yes |

Node layout followed section 5 of the E7 freeze: node A `compute-node` ran the four large OBQA/ARC panels, node B `compute-node` ran MMLU-Pro (Text, C2C), medium/OBQA (C2C) and medium/ARC (C2C), and then the E6 Text+fact replay of E6 freeze section 6 — all inside PBS job 7638030, one model residency per stage, `warmup_requests: 0`.

## 1. E7 — eight deployed policies x three arms vs the FIXED reference of the same run

Panels are the frozen 128-question panels; every arm ran in the same allocation and the same model residency as its fixed reference. `probe` is the mean of the timed probe region of the arm.

| Pair/benchmark/ref | q (q_A) | Arm | Omitted | Mean saving (a), ms [95%] | Mean saving (b), ms [95%] | Class a/b | Median (a) | Probe ms | Changed/omitted | Correct arm/fixed |
|---|---|---|---|---|---|---|---|---|---|---|
| large/OBQA/Text | 0.8 | ORIGINAL | 97 | 436.3 [378.6, 503.2] | 415.0 [366.7, 462.9] | +/+ | 521.5 | 33.8 | 3/97 | 112/113 |
| large/OBQA/Text | 0.8 | REUSE | 97 | 437.8 [378.1, 506.0] | 414.8 [366.8, 462.8] | +/+ | 521.7 | 33.5 | 3/97 | 112/113 |
| large/OBQA/Text | 0.8 | ARGMAX | 97 | 589.7 [518.0, 670.3] | 566.5 [503.8, 627.0] | +/+ | 716.2 | 32.1 | 3/97 | 112/113 |
| large/OBQA/C2C | 0.8 | ORIGINAL | 97 | 31.2 [16.7, 47.3] | 28.4 [14.9, 42.8] | +/+ | 7.0 | 32.0 | 2/97 | 102/101 |
| large/OBQA/C2C | 0.8 | REUSE | 97 | 31.0 [16.5, 47.0] | 28.2 [14.7, 42.7] | +/+ | 15.3 | 33.4 | 2/97 | 102/101 |
| large/OBQA/C2C | 0.8 | ARGMAX | 97 | 182.9 [158.2, 208.1] | 179.8 [155.6, 204.0] | +/+ | 210.4 | 32.0 | 2/97 | 102/101 |
| large/ARC/Text | 0.95 | ORIGINAL | 120 | 565.6 [528.6, 601.4] | 565.2 [528.4, 600.9] | +/+ | 592.2 | 32.0 | 3/120 | 117/117 |
| large/ARC/Text | 0.95 | REUSE | 120 | 564.4 [527.5, 599.6] | 563.9 [527.3, 599.8] | +/+ | 588.9 | 33.3 | 3/120 | 117/117 |
| large/ARC/Text | 0.95 | ARGMAX | 120 | 762.7 [717.4, 804.3] | 762.3 [717.7, 803.7] | +/+ | 794.6 | 31.9 | 3/120 | 117/117 |
| large/ARC/C2C | 0.9 | ORIGINAL | 115 | 91.9 [69.5, 116.6] | 92.9 [70.8, 116.1] | +/+ | 49.2 | 31.9 | 3/115 | 115/114 |
| large/ARC/C2C | 0.9 | REUSE | 115 | 90.5 [68.3, 115.0] | 91.6 [69.6, 114.7] | +/+ | 48.6 | 33.3 | 3/115 | 115/114 |
| large/ARC/C2C | 0.9 | ARGMAX | 115 | 280.8 [252.7, 310.4] | 281.8 [253.2, 310.4] | +/+ | 251.7 | 31.9 | 3/115 | 115/114 |
| medium/OBQA/C2C | 0.55 (0.5) | ORIGINAL | 66 | 50.1 [36.0, 65.6] | 47.6 [34.2, 62.2] | +/+ | 60.3 | 26.4 | 1/66 | 94/93 |
| medium/OBQA/C2C | 0.55 (0.5) | REUSE | 66 | 49.9 [35.7, 65.6] | 47.0 [33.7, 62.1] | +/+ | 60.8 | 26.2 | 1/66 | 94/93 |
| medium/OBQA/C2C | 0.55 (0.5) | ARGMAX | 61 | 125.2 [98.3, 154.9] | 123.0 [95.7, 151.9] | +/+ | -18.0 | 26.2 | 0/61 | 93/93 |
| medium/ARC/C2C | 0.6 | ORIGINAL | 77 | 77.9 [57.4, 103.0] | 78.0 [56.4, 102.8] | +/+ | 62.0 | 26.3 | 1/77 | 85/85 |
| medium/ARC/C2C | 0.6 | REUSE | 77 | 78.2 [57.5, 103.5] | 78.3 [56.6, 103.2] | +/+ | 62.9 | 26.3 | 1/77 | 85/85 |
| medium/ARC/C2C | 0.6 | ARGMAX | 77 | 189.5 [155.4, 225.4] | 189.1 [153.5, 224.9] | +/+ | 237.4 | 26.3 | 0/77 | 85/85 |
| large/MMLU-Pro/Text | 0.4 | ORIGINAL | 48 | 275.2 [199.6, 348.5] | 261.2 [189.6, 334.8] | +/+ | -33.4 | 41.8 | 3/48 | 65/63 |
| large/MMLU-Pro/Text | 0.4 | REUSE | 48 | 280.0 [203.5, 354.2] | 265.2 [193.5, 339.5] | +/+ | -29.1 | 40.8 | 3/48 | 65/63 |
| large/MMLU-Pro/Text | 0.4 | ARGMAX | 48 | 356.5 [265.1, 446.7] | 342.3 [253.7, 434.4] | +/+ | -32.2 | 40.8 | 3/48 | 65/63 |
| large/MMLU-Pro/C2C | 0.4 | ORIGINAL | 48 | 4.6 [-18.0, 32.6] | 4.5 [-19.0, 32.3] | ?/? | -36.1 | 40.8 | 0/48 | 55/55 |
| large/MMLU-Pro/C2C | 0.4 | REUSE | 48 | 6.9 [-15.8, 35.4] | 6.9 [-16.6, 34.9] | ?/? | -34.2 | 40.7 | 0/48 | 55/55 |
| large/MMLU-Pro/C2C | 0.4 | ARGMAX | 48 | 85.0 [50.3, 122.8] | 85.6 [49.7, 125.5] | +/+ | -33.5 | 40.7 | 0/48 | 55/55 |

Version (b) drops one question per row (the panel question at ordinal 0, where the fixed arm and the compared arm both made their first request), so `b_N = 127` everywhere; the excluded id is in `results/E7_arm_summary.csv`. `q_A` differs from the deployed `q` only for medium/OBQA/C2C (.50 vs .55), which is why its ARGMAX arm omits 61 rather than 66 questions.

### 1c. Text/C2C saving ratio, large pair

| Benchmark | Arm | Text saving (a) | C2C saving (a) | Ratio (a) | Ratio (b) |
|---|---|---|---|---|---|
| OBQA | ORIGINAL | 436.3 | 31.2 | 13.99 | 14.62 |
| OBQA | REUSE | 437.8 | 31.0 | 14.14 | 14.73 |
| OBQA | ARGMAX | 589.7 | 182.9 | 3.22 | 3.15 |
| ARC | ORIGINAL | 565.6 | 91.9 | 6.16 | 6.08 |
| ARC | REUSE | 564.4 | 90.5 | 6.24 | 6.16 |
| ARC | ARGMAX | 762.7 | 280.8 | 2.72 | 2.71 |
| MMLU-Pro | ORIGINAL | 275.2 | 4.6 | 59.46 | 57.84 |
| MMLU-Pro | REUSE | 280.0 | 6.9 | 40.69 | 38.47 |
| MMLU-Pro | ARGMAX | 356.5 | 85.0 | 4.19 | 4.00 |

The MMLU-Pro ratios divide by a C2C saving whose interval contains zero for ORIGINAL and REUSE, so those two ratios are unstable and are reported for completeness only.

### 1d. ORIGINAL-arm class vs the three E3 repeats (descriptive)

| Pair/benchmark/ref | E7 ORIGINAL a/b | REPEAT1 a/b | REPEAT2 a/b | REPEAT3 a/b | Match all three |
|---|---|---|---|---|---|
| large/OBQA/Text | +/+ | +/+ | +/+ | +/+ | yes |
| large/OBQA/C2C | +/+ | +/+ | +/+ | +/+ | yes |
| large/ARC/Text | +/+ | +/+ | +/+ | +/+ | yes |
| large/ARC/C2C | +/+ | +/+ | +/+ | +/+ | yes |
| medium/OBQA/C2C | +/+ | +/+ | +/+ | +/+ | yes |
| medium/ARC/C2C | +/+ | +/+ | +/+ | +/+ | yes |
| large/MMLU-Pro/Text | +/+ | +/+ | +/+ | +/+ | yes |
| large/MMLU-Pro/C2C | ?/? | ?/? | ?/? | ?/? | yes |

Descriptive only: classes are compared, never the numbers, and E7 is a single run on the same hardware family as the E3 repeats but a different job.

### 1e. REUSE outputs that differ from the ORIGINAL receiver-only output

13 of the 668 omitted REUSE requests produced a raw string different from the ORIGINAL arm on the same question (large 10, medium 3, MMLU-Pro 0 — the counts the replay itself recorded in `REPLAY_VERIFICATION.json`); no difference occurred on a kept question. **The parsed V2 label is identical in all 13 cases**; every difference is trailing punctuation or a continued option phrase. Full strings, as the freeze requires, are in `results/E7_reuse_output_differences.csv`. The list was rebuilt from the request records and matches the replay's own `P2_R2_E7_20260919T231531Z/REUSE_OUTPUT_DIFFERENCES.csv` question for question.

The pre-replay validation of section 4 of the E7 freeze passed on both receivers (`e7/validation/E7_VALIDATION_{large,medium}.json`): REUSE raw-string mismatches 0/16 for Qwen3-8B and 1/16 for Qwen3-1.7B, both within the "more than 1 of 16 stops the replay" limit, and ARGMAX matched the saved probe argmax label on 16/16 for both.

| Setting | Question | REUSE raw | ORIGINAL raw | Label |
|---|---|---|---|---|
| large/obqa/T | 12-1066 | `The correct answer is C` | `The correct answer is C.` | C = C |
| large/obqa/T | 10-580 | `The correct answer is C` | `The correct answer is C.` | C = C |
| large/obqa/T | 10-681 | `The correct answer is D.` | `The correct answer is D` | D = D |
| large/obqa/C | 12-1066 | `The correct answer is C` | `The correct answer is C.` | C = C |
| large/obqa/C | 10-580 | `The correct answer is C` | `The correct answer is C.` | C = C |
| large/obqa/C | 10-681 | `The correct answer is D.` | `The correct answer is D` | D = D |
| large/arc/T | Mercury_400934 | `The correct answer is C.` | `The correct answer is C` | C = C |
| large/arc/T | Mercury_7143518 | `The correct answer is D.` | `The correct answer is D` | D = D |
| large/arc/C | Mercury_400934 | `The correct answer is C.` | `The correct answer is C` | C = C |
| large/arc/C | Mercury_7143518 | `The correct answer is D.` | `The correct answer is D` | D = D |
| medium/obqa/C | 13-71 | `The correct answer is A. heaviness` | `The correct answer is A.` | A = A |
| medium/obqa/C | 10-681 | `The correct answer is D.` | `D. changing location` | D = D |
| medium/arc/C | Mercury_177398 | `The correct answer is B. velocity` | `The correct answer is B.` | B = B |

## 2. E6 replay — fixed Text+fact vs the Text+fact policy (node B of job 7638030)

| Pair/benchmark/ref | q | Omitted | Mean saving (a), ms [95%] | Mean saving (b), ms [95%] | Class a/b | Median (a) | Probe ms | Changed/omitted | Correct policy/fixed |
|---|---|---|---|---|---|---|---|---|---|
| large/OBQA/Text+fact | 0.75 | 92/128 | 343.4 [297.7, 386.0] | 342.5 [299.3, 385.4] | +/+ | 448.5 | 32.1 | 5/92 | 116/121 |

Mean latency: fixed Text+fact 726.5 ms, policy 383.1 ms. No INVALID parse and no runtime failure in either arm. The replay ran at the certified q = 0.75 and threshold 0.0002611875534057617, exactly the values in `e6/analysis/E6_RESULTS.json`. Classification only, as section 6 of the E6 freeze requires; no number here is compared with any other machine.

The policy answers 116 of 128 panel questions correctly against 121 for fixed Text+fact (-5 answers). That is a descriptive panel count, not a certified quantity — the risk test controls answer changes, not correctness.

## 3. E6 development and calibration extras

### 3a. Development (742 OBQA group representatives), at the certified q = .75

| Setting | Omitted/N | Policy correct | Fixed Text+fact correct | Delta accuracy (pp) [95%] |
|---|---|---|---|---|
| large/OBQA/Text+fact | 536/742 | 660 | 670 | -1.35 [-2.29, -0.54] |

Reference-correction table, columns exactly as `tab_omit_keep.tex`:

| Setting | Omitted/N | Lost | Kept | Gained | Net | Other | Unused (omit/keep) |
|---|---|---|---|---|---|---|---|
| large/OBQA/Text+fact (other = C2C) | 536/742 | 11/62 | 51/62 | 1 | -10 | 1 | 12/14 |
| large/OBQA/Text+fact (other = Text) | 536/742 | 11/62 | 51/62 | 1 | -10 | 1 | 12/11 |

The paper's three actions are R, Text and C2C; E6 substitutes Text+fact for Text, so *other* and *unused* need a third action. The first row takes **C2C** as the other communication action (the direct substitution into the paper's table); the second takes the original **Text** action. Lost/kept/gained/net do not depend on that choice. For reference, the frozen paper row for the same population against plain Text at q = .80 is `572/742 | 13/46 | 33/46 | 6 | -7 | 1 | 14/18`.

The identity `policy - reference = gained - lost` holds: 660 - 670 = 1 - 11. Other development counts: R 617, Text 645, C2C 598 correct; changed on omitted 13.

### 3b. Calibration relabelled with D1

| Variant | o_R D1 vs V2 | o_Text+fact D1 vs V2 | Answer-change labels differing from V2 | n/k at q=.75 | p | q=.75 accepted | Largest accepted q |
|---|---|---|---|---|---|---|---|
| D1 both sides (E5-a (c) rule) | 0 | 0 | 0 | 999/22 | 4.83045e-06 | True | 0.75 |
| D1 on Text+fact only, V2 on R | 0 | 0 | 0 | 999/22 | 4.83045e-06 | True | 0.75 |

The task names the Text+fact side; both variants are given because the answer-change label needs both sides, and E5-a (c) relabels both. The pre-V2 D1 parser reproduces every V2 label on both sides of all 1,366 calibration rows, so the ledger is bit-identical to the frozen one (`e6/analysis/E6_LEDGER.csv` at q = .75: n = 999, k = 22, p = 4.83045e-06, accepted). **q = .75 is still accepted, and .75 is still the largest accepted q.**

### 3c. Calibration after removing X (the 208 reviewed OBQA questions), as in E5-a

| Setting | N_cal | cal ∩ X | N clean | n/k at q=.75 | p | CP .999 | q=.75 accepted on C\X | Largest accepted q |
|---|---|---|---|---|---|---|---|---|
| large/OBQA/Text+fact | 1366 | 208 | 1158 | 852/20 | 6.63109e-05 | 0.044178 | True | 0.75 |

Disagreement rate between R and Text+fact: 0.1731 on X (36/208), 0.1157 on C\X (134/1158), 0.1245 on the full calibration split. X is content-selected (records where the run-time and D1 parsers disagreed, or D1 flagged the parse ambiguous), so it is enriched for parse-hard outputs; the rates are reported separately for that reason. The full 20-row clean ledger is in `results/E6_cal_without_X_ledger.csv`.

## 4. Files

| CSV | Contents |
|---|---|
| `results/E7_arm_summary.csv` | 24 rows: 8 policies x 3 arms, versions (a) and (b), classes, medians, probe cost, changed/omitted, correct counts |
| `results/E7_per_question.csv` | 3,072 rows: per question and arm — ProbeMax, omitted, both latencies, saving, probe ms, both answers, gold, version-(b) membership |
| `results/E7_text_c2c_ratio.csv` | Text/C2C saving ratios per benchmark and arm, versions (a) and (b) |
| `results/E7_probe_cost.csv` | mean and median probe and selector cost per setting and arm |
| `results/E7_reuse_output_differences.csv` | every REUSE output differing from the ORIGINAL output, with both raw strings and both parsed labels |
| `results/E7_e3_class_comparison.csv` | ORIGINAL-arm class vs the three E3 repeats, versions (a) and (b) |
| `results/E7_CHECKS.json` | stop conditions (empty) and omitted counts recomputed vs REPLAY_VERIFICATION.json |
| `results/E6REPLAY_summary.csv` | E6 replay: savings (a)/(b), classes, median, probe cost, changed/omitted, correct counts |
| `results/E6REPLAY_per_question.csv` | 128 rows of the E6 replay panel |
| `results/E6REPLAY_CHECKS.json` | stop conditions (empty) and omitted count vs REPLAY_VERIFICATION.json |
| `results/E6_dev_reference_corrections.csv` | development table 3a, both choices of the third action |
| `results/E6_cal_D1_relabel.csv` | D1 relabelling of the calibration outputs and the redone q = .75 test |
| `results/E6_cal_without_X.csv` | the q = .75 test and the largest accepted q on C\X |
| `results/E6_cal_without_X_ledger.csv` | all 20 clean-ledger rows next to the full-C rows |
| `results/E6_EXTRAS_CHECKS.json` | stop conditions (empty) |
| `results/PANEL_IDENTITY.csv` | SHA-256 of every panel file used here next to the frozen E3 file |

Scripts: `scripts/common_r2a.py` (shared helpers and the frozen bootstrap), `scripts/e7_analysis.py`, `scripts/e6replay_analysis.py`, `scripts/e6_extras.py`, `scripts/make_summary.py`.

