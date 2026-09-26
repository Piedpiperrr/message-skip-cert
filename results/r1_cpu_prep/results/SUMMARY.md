# P2 R1 reviewer re-analyses (CPU only, saved records)

**POST-HOC sensitivity analysis (reviewer R1); does not change any primary decision.** Stage folder: `$DATA_DIR/P2_R1_CPU_20260919T045556Z`. Scripts: `src/`; tables: `results/*.csv`.

Conventions: q = 0 means fallback (always run the reference). Dev "chg/omit" is changed answers over development questions answered by R alone. Dev units: 742 OBQA, 299 ARC, 2,641 MMLU-Pro group representatives.

## 1. Sanity check: deployed q recomputed from ledgers

| Setting | Recomputed q | Expected q | Match | max abs diff in p / CP (recomputed from n,k) |
|---|---|---|---|---|
| small/OBQA/Text | 0 | 0 | True | 0e+00 / 0e+00 |
| small/OBQA/C2C | 0 | 0 | True | 0e+00 / 0e+00 |
| small/ARC/Text | 0 | 0 | True | 0e+00 / 0e+00 |
| small/ARC/C2C | 0 | 0 | True | 0e+00 / 0e+00 |
| medium/OBQA/Text | 0 | 0 | True | 0e+00 / 0e+00 |
| medium/OBQA/C2C | 0.55 | 0.55 | True | 0e+00 / 0e+00 |
| medium/ARC/Text | 0 | 0 | True | 0e+00 / 0e+00 |
| medium/ARC/C2C | 0.6 | 0.6 | True | 0e+00 / 0e+00 |
| large/OBQA/Text | 0.8 | 0.8 | True | 0e+00 / 0e+00 |
| large/OBQA/C2C | 0.8 | 0.8 | True | 0e+00 / 0e+00 |
| large/ARC/Text | 0.95 | 0.95 | True | 0e+00 / 0e+00 |
| large/ARC/C2C | 0.9 | 0.9 | True | 0e+00 / 0e+00 |
| large/MMLU-Pro/Text | 0.4 | 0.4 | True | 0e+00 / 0e+00 |
| large/MMLU-Pro/C2C | 0.4 | 0.4 | True | 0e+00 / 0e+00 |

Sources: `P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/summary/calibration_all_160.csv`, `P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/calibration/{obqa,arc}_{T,C}.csv`, `P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/calibration/40_test_ledger.csv` (280 rows). All 14 match; no STOP.

## 2. Calibration table

Selected q, or for fallback settings the grid point with the smallest p (ties: smallest q, all tied q listed).

| Setting | Basis | q | n_q | k_q | p | CP .999 UB | small: n_q at q=.05 / .10 |
|---|---|---|---|---|---|---|---|
| small/OBQA/Text | fallback min-p (tied q: 0.05) | 0.05 | 65 | 5 | 0.894 | 0.2317 | 65 / 142 |
| small/OBQA/C2C | fallback min-p (tied q: 0.05) | 0.05 | 65 | 2 | 0.363 | 0.1610 | 65 / 142 |
| small/ARC/Text | fallback min-p (tied q: 0.1) | 0.1 | 33 | 5 | 0.995 | 0.4186 | 18 / 33 |
| small/ARC/C2C | fallback min-p (tied q: 0.1) | 0.1 | 33 | 2 | 0.773 | 0.2963 | 18 / 33 |
| medium/OBQA/Text | fallback min-p (tied q: 0.05;0.1;0.15;0.2;0.25;0.3;0.35;0.4;0.45) | 0.05 | 601 | 36 | 0.884 | 0.0958 |  |
| medium/OBQA/C2C | selected | 0.55 | 739 | 19 | 0.000694 | 0.0491 |  |
| medium/ARC/Text | fallback min-p (tied q: 0.05;0.1;0.15;0.2;0.25;0.3;0.35;0.4;0.45;0.5;0.55) | 0.05 | 256 | 12 | 0.483 | 0.1025 |  |
| medium/ARC/C2C | selected | 0.6 | 290 | 1 | 5.64e-06 | 0.0314 |  |
| large/OBQA/Text | selected | 0.8 | 1064 | 18 | 1.16e-08 | 0.0330 |  |
| large/OBQA/C2C | selected | 0.8 | 1064 | 22 | 6.71e-07 | 0.0379 |  |
| large/ARC/Text | selected | 0.95 | 422 | 4 | 4.8e-06 | 0.0346 |  |
| large/ARC/C2C | selected | 0.9 | 404 | 7 | 0.00054 | 0.0478 |  |
| large/MMLU-Pro/Text | selected | 0.4 | 2358 | 67 | 1.34e-07 | 0.0406 |  |
| large/MMLU-Pro/C2C | selected | 0.4 | 2358 | 75 | 1.01e-05 | 0.0446 |  |

Source: same ledgers as item 1; p and CP recomputed from (n_q, k_q). File: `results/item2_calibration_table.csv`.

## 3. Sensitivity of the certification rule and score (ledger n,k; dev at the same fit threshold)

Cell = deployed q (cal n/k at that q; dev coverage %, dev changed/omitted). "0" = fallback. (a) alpha .02 / .10, cutoff .001 per candidate. (b) Fixed-sequence: ascending q, level .02 each, stop at the first failure. (c) Entropy H(p) and margin 1-(p1-p2) from saved probe vectors: fit order statistics ceil(jN/20), ties included, q=1 fixed R, alpha .05, cutoff .001.

| Setting | Primary (ProbeMax) | alpha .02 | alpha .10 | Fixed-seq | Entropy | Margin |
|---|---|---|---|---|---|---|
| small/OBQA/Text | 0 | 0 | 0 | 0 | 0 | 0 |
| small/OBQA/C2C | 0 | 0 | 0 | 0 | 0 | 0 |
| small/ARC/Text | 0 | 0 | 0 | 0 | 0 | 0 |
| small/ARC/C2C | 0 | 0 | 0 | 0 | 0 | 0 |
| medium/OBQA/Text | 0 | 0 | 0.45 (cal 601/36; 43.3%, 18/321) | 0 | 0 | 0 |
| medium/OBQA/C2C | 0.55 (cal 739/19; 52.6%, 11/390) | 0 | 0.65 (cal 880/50; 64.8%, 25/481) | 0.55 (cal 739/19; 52.6%, 11/390) | 0.55 (cal 739/19; 52.4%, 11/389) | 0.55 (cal 739/19; 52.7%, 11/391) |
| medium/ARC/Text | 0 | 0 | 0 | 0 | 0 | 0 |
| medium/ARC/C2C | 0.6 (cal 290/1; 63.2%, 4/189) | 0 | 0.75 (cal 363/15; 73.2%, 7/219) | 0.6 (cal 290/1; 63.2%, 4/189) | 0.6 (cal 282/1; 62.5%, 3/187) | 0.6 (cal 286/1; 62.5%, 3/187) |
| large/OBQA/Text | 0.8 (cal 1064/18; 77.1%, 19/572) [historically tested] | 0.65 (cal 870/4; 62.0%, 6/460) | 0.9 (cal 1217/67; 91.1%, 44/676) | 0.8 (cal 1064/18; 77.1%, 19/572) | 0.8 (cal 1065/18; 77.1%, 18/572) [historically tested] | 0.8 (cal 1067/19; 77.1%, 19/572) |
| large/OBQA/C2C | 0.8 (cal 1064/22; 77.1%, 13/572) | 0.65 (cal 870/4; 62.0%, 1/460) | 0.95 (cal 1297/90; 94.7%, 45/703) | 0.85 (cal 1135/37; 82.6%, 22/613) | 0.8 (cal 1065/22; 77.1%, 13/572) | 0.8 (cal 1067/22; 77.1%, 13/572) |
| large/ARC/Text | 0.95 (cal 422/4; 95.0%, 9/284) | 0.8 (cal 359/0; 77.9%, 0/233) | 1 (cal 448/12; 100.0%, 15/299) | 1 (cal 448/12; 100.0%, 15/299) | 0.95 (cal 422/4; 95.0%, 9/284) | 0.95 (cal 421/4; 95.0%, 9/284) |
| large/ARC/C2C | 0.9 (cal 404/7; 90.3%, 3/270) | 0 | 1 (cal 448/21; 100.0%, 12/299) | 0.95 (cal 422/11; 95.0%, 6/284) | 0.9 (cal 404/7; 90.3%, 3/270) | 0.9 (cal 405/7; 90.3%, 3/270) |
| large/MMLU-Pro/Text | 0.4 (cal 2358/67; 40.5%, 40/1069) | 0 | 0.6 (cal 3568/276; 60.4%, 109/1596) | 0.45 (cal 2654/105; 45.6%, 56/1205) | 0.4 (cal 2358/68; 40.4%, 40/1068) | 0.4 (cal 2348/63; 40.5%, 40/1069) |
| large/MMLU-Pro/C2C | 0.4 (cal 2358/75; 40.5%, 37/1069) | 0.25 (cal 1542/9; 26.4%, 6/697) | 0.5 (cal 2948/186; 50.8%, 85/1341) | 0.4 (cal 2358/75; 40.5%, 37/1069) | 0.4 (cal 2358/74; 40.4%, 37/1068) | 0.4 (cal 2348/75; 40.5%, 38/1069) |

**Dev AUROC for R-vs-reference disagreement** (same dev units):

| Setting | ProbeMax | Entropy | Margin | D (item 4) |
|---|---|---|---|---|
| small/OBQA/Text | 0.641 | 0.644 | 0.640 | pending features |
| small/OBQA/C2C | 0.700 | 0.705 | 0.697 | pending features |
| small/ARC/Text | 0.634 | 0.639 | 0.630 | pending features |
| small/ARC/C2C | 0.641 | 0.658 | 0.633 | pending features |
| medium/OBQA/Text | 0.787 | 0.792 | 0.792 | no features |
| medium/OBQA/C2C | 0.840 | 0.848 | 0.848 | no features |
| medium/ARC/Text | 0.742 | 0.793 | 0.792 | no features |
| medium/ARC/C2C | 0.910 | 0.913 | 0.912 | no features |
| large/OBQA/Text | 0.873 | 0.877 | 0.876 | 0.763 |
| large/OBQA/C2C | 0.883 | 0.884 | 0.885 | 0.760 |
| large/ARC/Text | 0.952 | 0.953 | 0.952 | pending features |
| large/ARC/C2C | 0.909 | 0.931 | 0.932 | pending features |
| large/MMLU-Pro/Text | 0.821 | 0.822 | 0.822 | no features |
| large/MMLU-Pro/C2C | 0.846 | 0.849 | 0.846 | no features |

Checks (`results/item3_input_checks.csv`): for all 14 settings, the ProbeMax fit thresholds equal the stored ones, ledger n/k are reproduced from the saved scores, and dev disagreement, AUROC, coverage and changed/omitted equal Table tab:dev_full. The historical ProbeEntropy ledger (`P2_ZERO_GOLD_CONTROLS_20260914T065145Z/summary/calibration_new_60.csv`; H/ln4, rank-equivalent) is reproduced exactly: q=.80, cal 1065/18, dev 18/572. Probe sources are listed per setting in the checks CSV (P2_ZERO_GOLD_CONTROLS records/probe_records.jsonl; P2_CONFIDENCE_REFERENCE_BOUNDARIES records/*_{fit,cal,dev}_probes.jsonl; medium probes/*.jsonl; MMLU-Pro shards/{1,2}/probes/*.jsonl). Answers come from P2_SCORING_V2 labels/, medium actions/, and MMLU-Pro summary/merged_numeric_rows.jsonl.

## 4. Learned control D (refit exactly as fit_head.py; fit split only; target 1[o_R != o_b])

| Setting | Deployed q | cal n/k | Dev | cal AUROC | Note |
|---|---|---|---|---|---|
| small/OBQA/Text | 0 | - | pending features | 0.567 |  |
| small/OBQA/C2C | 0 | - | pending features | 0.618 |  |
| small/ARC/Text | 0 | - | pending features | 0.513 |  |
| small/ARC/C2C | 0 | - | pending features | 0.678 |  |
| large/OBQA/Text | 0.3 | 380/6 | 31.0%, 6/230 | 0.768 | historically tested |
| large/OBQA/C2C | 0.55 | 698/15 | 53.8%, 13/399 | 0.771 |  |
| large/ARC/Text | 0.9 | 401/7 | pending features | 0.856 |  |
| large/ARC/C2C | 0.65 | 303/4 | pending features | 0.843 |  |

LR = {'penalty': 'l2', 'C': 1, 'solver': 'lbfgs', 'max_iter': 1000, 'random_state': 0, 'class_weight': None} on E1 z features (`P2_E1_DIRECTION_20260913T053456Z/FEATURE_INDEX.csv`; 8192-d large, 2048-d small); dev features exist only for large/OBQA (`P2_RISK_CALIBRATION_BINARY_20260914T043954Z/features/dev`). All 8 fits converged with no warnings. ARC fit uses the 670 fit representatives (same unit as the ProbeMax thresholds). Reproduction of the historical large/OBQA/Text head: target identical = True; max |dP| vs `models/disagreement.joblib` = 6.9e-16 (fit) / 7.5e-16 (cal); ledger identical to `summary/calibration_100.csv` = True; thresholds differ from `models/thresholds.json` by at most 4.7e-16 (float noise). The dev result 6/230 matches the paper.

## 5. Cold / first requests on the existing replays (paired saving = fixed minus policy, ms)

(i) paper mean [95%]; (ii) excluding every question on which either arm made its first formal request; (iii) 5% trimmed mean (5% cut from each tail, scipy trim_mean) of the paired differences. Seed 0, 2,000 resamples: (i) and (iii) use each replay's saved index file; (ii) uses default_rng(0).integers(0,N,(2000,N)) over the remaining units.

| Replay / ref | First request: fixed arm (ms) | First request: policy arm (ms) | (i) paper | Reproduces | (ii) excl. first (N) | (iii) 5% trimmed |
|---|---|---|---|---|---|---|
| large/OBQA/Text | 9-782: 1357.1 | 9-782: 2827.9 (cold) | 517.1 [447.8, 583.6] | True | 532.8 [470.9, 594.7] (127) | 533.3 [464.4, 597.8] |
| large/OBQA/C2C | 9-782: 728.0 | 9-782: 298.2 | 36.6 [18.0, 56.8] | True | 33.5 [16.5, 51.7] (127) | 26.5 [8.6, 47.6] |
| large/ARC/Text | Mercury_7207358: 1069.5 | Mercury_7207358: 296.0 | 717.6 [670.6, 763.2] | True | 717.2 [670.1, 761.8] (127) | 730.5 [682.5, 771.9] |
| large/ARC/C2C | Mercury_7207358: 233.3 | Mercury_7207358: 294.0 | 110.9 [82.0, 142.8] | True | 112.3 [83.7, 142.3] (127) | 100.7 [70.9, 133.5] |
| medium/OBQA/C2C | 9-782: 3269.2 (cold) | 9-782: 813.8 | 79.7 [48.1, 129.1] | True | 61.0 [43.9, 79.9] (127) | 56.2 [38.3, 76.1] |
| medium/ARC/C2C | Mercury_7207358: 342.3 | Mercury_7207358: 256.1 | 100.7 [74.5, 133.1] | True | 100.8 [73.0, 132.8] (127) | 82.4 [59.1, 109.5] |
| large/MMLU-Pro/Text | test:3074: 5232.8 (cold) | test:3074: 1806.6 | 346.3 [249.8, 443.0] | True | 322.1 [234.8, 412.5] (127) | 292.4 [201.6, 388.0] |
| large/MMLU-Pro/C2C | test:3074: 1179.2 | test:3074: 946.9 | 8.2 [-20.5, 44.0] | True | 6.5 [-23.3, 41.1] (127) | -23.3 [-39.0, -0.4] |
| large/ARC-sealed-test/Text | Mercury_7175875: 1159.9 | Mercury_7175875: 2925.4 (cold) | 685.6 [669.6, 700.8] | True | 687.7 [672.0, 703.2] (1171) | 700.8 [684.5, 716.8] |
| large/ARC-sealed-test/C2C | Mercury_7175875: 794.4 | Mercury_7175875: 325.5 | 90.9 [81.0, 101.0] | True | 90.6 [81.0, 100.2] (1171) | 78.0 [68.2, 87.8] |

"(cold)" marks the single first request after model load in that job (`cold_first_request` / `first_formal_request_global`); every other arm's first request came after other arms had already run in the same residency. In each replay both arms of a pair made their first request on the same question, so (ii) drops one unit. Sources: `P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z/records/e2e_requests.jsonl`, `P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z/records/e2e_requests.jsonl`, `P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z/records/four_arm_requests.jsonl`, `P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/records/e2e_requests.jsonl` (sealed test uses 1,172 group representatives). All four arms of every panel: `results/item5_arm_first_requests.csv`.

## 6. MMLU-Pro panel accuracy (128 questions; paired bootstrap, seed 0, 2,000)

| Ref | Policy / fixed correct | Delta acc (pp) | 95% interval (pp) | Benefit / harm questions |
|---|---|---|---|---|
| Text | 65/63 | +1.56 | [0.00, 3.91] | 2 / 0 |
| C2C | 55/55 | +0.00 | [0.00, 0.00] | 0 / 0 |

Source: `P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z/records/paired_per_question.jsonl`; indices `protocol/bootstrap_indices.npz` (verified equal to default_rng(0)).

## 7. Provenance (read-only)

**Key timestamps** (`results/item7_key_timestamps.csv`):

| Fact | Value |
|---|---|
| freeze_file | P2_RISK_CALIBRATION_BINARY_20260914T043954Z/frozen_config.json mtime 2026-09-14T04:41:36Z; contains alpha=0.05, p_cutoff=0.001, delta=0.1, q_grid(20); families=['D', 'R', 'Diff', 'H', 'Random']; 'ProbeMax' present: False |
| probemax_first_frozen | P2_ZERO_GOLD_CONTROLS_20260914T065145Z/frozen_config.json mtime 2026-09-14T07:01:57Z (families ['D', 'R2100', 'ProbeMax', 'ProbeEntropy', 'WordD']); earliest file mentioning ProbeMax: P2_ZERO_GOLD_CONTROLS_20260914T065145Z/src/common.py 2026-09-14T06:54:18Z |
| obqa_split_created | P2_RISK_CALIBRATION_BINARY_20260914T043954Z/SPLIT_FREEZE.json utc 2026-09-14T04:41:35.950162+00:00 (Python random.Random(0), shuffle lexicographically sorted representatives; labels_read=False) |
| arc_split_created | P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/SPLIT_FREEZE.json utc 2026-09-14T16:52:46.089022+00:00 (outcomes_used=False) |
| mmlu_split_protocol | P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json utc 2026-09-16T00:39:11.257382+00:00 |
| medium_protocol | P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/MEDIUM_PAIR_PROTOCOL_FREEZE.json utc 2026-09-15T14:54:02.955834+00:00 |
| first_cal_statistic_any | P2_RISK_CALIBRATION_BINARY_20260914T043954Z/inputs/candidate_cal.jsonl mtime 2026-09-14T04:50:18Z; P2_RISK_CALIBRATION_BINARY_20260914T043954Z/summary/calibration_100.csv mtime 2026-09-14T04:51:30Z (large/OBQA/Text only) |
| V2_frozen | P2_SCORING_V2_20260912T191445Z/RULE_FREEZE_V2.json frozen_utc 2026-09-12T19:19:38.860954+00:00; disclosure: Revision followed review of exposed cases, gold and old/D1 outcomes; NOT globally blinded. |
| planning_prompt | P2_POST_E2E_METHOD_REVIEW_20260914T034957Z/NEXT_EXPERIMENT_ClusterB_PROMPT_ZH.md mtime 2026-09-14T03:56:40Z: proposed fit2100/cal1366 split stratified by f_R (R vs Text flip); implemented split was unstratified/label-independent |

**Per setting: before 2026-09-14T04:41:36Z, was any statistic or threshold test computed on that setting's calibration split?**

| Setting | Status | Evidence | Superset (full-train) exposure before the freeze |
|---|---|---|---|
| small/OBQA/Text | NONE FOUND | OBQA cal split did not exist before 2026-09-14T04:41:35.950162+00:00; cal-split R-vs-Text d first written 2026-09-14T17:12:51Z (P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/inputs/small_obqa_cal_machine_d.jsonl), after BOUNDARIES protocol freeze 2026-09-14T16:52:46.105623+00:00 | SUPERSET only (full-train stats containing the 1366 later-cal questions): SCORE_SENSITIVITY 2026-09-12T06:07Z, SCORING_V2 2026-09-12T19:23Z, V2_BASELINES_FFR_E0 2026-09-13T04:35Z, E1_DIRECTION 2026-09-13T06:51Z; parser case review touched 186 later-cal questions (record level, incl. gold) |
| small/OBQA/C2C | NONE FOUND | OBQA cal split did not exist before 2026-09-14T04:41:35.950162+00:00; cal-split R-vs-C2C d first written 2026-09-14T17:12:51Z (P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/inputs/small_obqa_cal_machine_d.jsonl), after BOUNDARIES protocol freeze 2026-09-14T16:52:46.105623+00:00 | SUPERSET only (full-train stats containing the 1366 later-cal questions): SCORE_SENSITIVITY 2026-09-12T06:07Z, SCORING_V2 2026-09-12T19:23Z, V2_BASELINES_FFR_E0 2026-09-13T04:35Z, E1_DIRECTION 2026-09-13T06:51Z; parser case review touched 186 later-cal questions (record level, incl. gold) |
| small/ARC/Text | NONE FOUND | ARC cal split did not exist before 2026-09-14T16:52:46.089022+00:00; cal-split R-vs-Text d first written 2026-09-14T17:13:37Z (P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/inputs/small_arc_cal_machine_d.jsonl), after BOUNDARIES protocol freeze 2026-09-14T16:52:46.105623+00:00 | SUPERSET only (full-train stats containing the 448 later-cal questions): SCORE_SENSITIVITY 2026-09-12T06:07Z, SCORING_V2 2026-09-12T19:23Z, V2_BASELINES_FFR_E0 2026-09-13T04:35Z, E1_DIRECTION 2026-09-13T06:51Z; parser case review touched 113 later-cal questions (record level, incl. gold) |
| small/ARC/C2C | NONE FOUND | ARC cal split did not exist before 2026-09-14T16:52:46.089022+00:00; cal-split R-vs-C2C d first written 2026-09-14T17:13:37Z (P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/inputs/small_arc_cal_machine_d.jsonl), after BOUNDARIES protocol freeze 2026-09-14T16:52:46.105623+00:00 | SUPERSET only (full-train stats containing the 448 later-cal questions): SCORE_SENSITIVITY 2026-09-12T06:07Z, SCORING_V2 2026-09-12T19:23Z, V2_BASELINES_FFR_E0 2026-09-13T04:35Z, E1_DIRECTION 2026-09-13T06:51Z; parser case review touched 113 later-cal questions (record level, incl. gold) |
| medium/OBQA/Text | NONE FOUND | medium protocol frozen 2026-09-15T14:54:02.955834+00:00; medium cal answers produced 2026-09-15 (execution_retry1/actions/*_cal.jsonl utc) - all after 2026-09-14T04:41:36Z | none (no medium-pair outputs existed before freeze) |
| medium/OBQA/C2C | NONE FOUND | medium protocol frozen 2026-09-15T14:54:02.955834+00:00; medium cal answers produced 2026-09-15 (execution_retry1/actions/*_cal.jsonl utc) - all after 2026-09-14T04:41:36Z | none (no medium-pair outputs existed before freeze) |
| medium/ARC/Text | NONE FOUND | medium protocol frozen 2026-09-15T14:54:02.955834+00:00; medium cal answers produced 2026-09-15 (execution_retry1/actions/*_cal.jsonl utc) - all after 2026-09-14T04:41:36Z | none (no medium-pair outputs existed before freeze) |
| medium/ARC/C2C | NONE FOUND | medium protocol frozen 2026-09-15T14:54:02.955834+00:00; medium cal answers produced 2026-09-15 (execution_retry1/actions/*_cal.jsonl utc) - all after 2026-09-14T04:41:36Z | none (no medium-pair outputs existed before freeze) |
| large/OBQA/C2C | NONE FOUND | OBQA cal split did not exist before 2026-09-14T04:41:35.950162+00:00; cal-split R-vs-C2C d first written 2026-09-14T17:06:29Z (P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/inputs/large_obqa_cal_machine_d.jsonl), after BOUNDARIES protocol freeze 2026-09-14T16:52:46.105623+00:00; between 04:41 and 16:52 only large/OBQA/Text (R/Text) was computed on this cal split (RISK_CALIBRATION_BINARY, GOLD_BUDGET, ZERO_GOLD_CONTROLS) | SUPERSET only (full-train stats containing the 1366 later-cal questions): SCORE_SENSITIVITY 2026-09-12T06:07Z, SCORING_V2 2026-09-12T19:23Z, V2_BASELINES_FFR_E0 2026-09-13T04:35Z, E1_DIRECTION 2026-09-13T06:51Z, E1_E2E_OBQA 2026-09-13T17:46-20:01Z; parser case review touched 30 later-cal questions (record level, incl. gold) |
| large/ARC/Text | NONE FOUND | ARC cal split did not exist before 2026-09-14T16:52:46.089022+00:00; cal-split R-vs-Text d first written 2026-09-14T17:10:05Z (P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/inputs/large_arc_cal_machine_d.jsonl), after BOUNDARIES protocol freeze 2026-09-14T16:52:46.105623+00:00 | SUPERSET only (full-train stats containing the 448 later-cal questions): SCORE_SENSITIVITY 2026-09-12T06:07Z, SCORING_V2 2026-09-12T19:23Z, V2_BASELINES_FFR_E0 2026-09-13T04:35Z, E1_DIRECTION 2026-09-13T06:51Z; parser case review touched 26 later-cal questions (record level, incl. gold) |
| large/ARC/C2C | NONE FOUND | ARC cal split did not exist before 2026-09-14T16:52:46.089022+00:00; cal-split R-vs-C2C d first written 2026-09-14T17:10:05Z (P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/inputs/large_arc_cal_machine_d.jsonl), after BOUNDARIES protocol freeze 2026-09-14T16:52:46.105623+00:00 | SUPERSET only (full-train stats containing the 448 later-cal questions): SCORE_SENSITIVITY 2026-09-12T06:07Z, SCORING_V2 2026-09-12T19:23Z, V2_BASELINES_FFR_E0 2026-09-13T04:35Z, E1_DIRECTION 2026-09-13T06:51Z; parser case review touched 26 later-cal questions (record level, incl. gold) |
| large/MMLU-Pro/Text | NONE FOUND | MMLU-Pro split/protocol frozen 2026-09-16T00:39:11.257382+00:00; cal answers produced 2026-09-16T15:27-19:01Z (shards/*/actions/cal.jsonl) - all after 2026-09-14T04:41:36Z | none (no MMLU-Pro outputs existed before freeze) |
| large/MMLU-Pro/C2C | NONE FOUND | MMLU-Pro split/protocol frozen 2026-09-16T00:39:11.257382+00:00; cal answers produced 2026-09-16T15:27-19:01Z (shards/*/actions/cal.jsonl) - all after 2026-09-14T04:41:36Z | none (no MMLU-Pro outputs existed before freeze) |

**Pre-freeze statistics on populations that contain the later calibration questions (never restricted to them)** (`results/item7_prefreeze_superset_exposure.csv`):

| mtime (UTC) | File | What |
|---|---|---|
| 2026-09-12T06:07:59Z | `P2_SCORE_SENSITIVITY_20260912T055929Z/pairwise_answer_agreement.csv` | R-vs-Text/C2C answer agreement on FULL train (3466 OBQA/1119 ARC), saved(V1)+diagnostic parser, small+large |
| 2026-09-12T06:07:59Z | `P2_SCORE_SENSITIVITY_20260912T055929Z/case_review.jsonl` | record-level parser case review incl. gold (V2 rule development) |
| 2026-09-12T19:23:32Z | `P2_SCORING_V2_20260912T191445Z/pairwise_agreement.csv` | R-vs-Text/C2C agreement on FULL train, V2 parser, small+large |
| 2026-09-12T19:23:32Z | `P2_SCORING_V2_20260912T191445Z/action_summary.csv` | per-action correctness on FULL train, V2, small+large |
| 2026-09-13T04:26:14Z | `P2_V2_BASELINES_FFR_E0_20260913T000052Z/flip_metrics.csv` | 5-fold OOF R-vs-action flip AUC/AP on FULL train, small+large x OBQA/ARC |
| 2026-09-13T04:26:14Z | `P2_V2_BASELINES_FFR_E0_20260913T000052Z/decision_metrics.csv` | 5-fold OOF router decisions/accuracy on FULL train, small+large x OBQA/ARC |
| 2026-09-13T06:51:31Z | `P2_E1_DIRECTION_20260913T053456Z/summary/flip_metrics.csv` | 5-fold OOF flip AUC on FULL train (E1 features), small+large x OBQA/ARC |
| 2026-09-13T20:01:06Z | `P2_E1_E2E_OBQA_20260913T174210Z/FINAL_RECEIPT.json` | large/OBQA only: routers fit on FULL train (R,T,C,A), evaluated on dev |
| 2026-09-12T06:07:59Z | `P2_SCORE_SENSITIVITY_20260912T055929Z/case_review.jsonl` | unique later-cal questions reviewed: large/arc=26; large/obqa=30; small/arc=113; small/obqa=186 |

**First production of calibration-split R/Text/C2C answers (small and large pairs)** (`results/item7_cal_answer_production.csv`):

| Pair/task | Source | Cal rows (3 actions) | Job(s) | Row utc first-last / file mtime |
|---|---|---|---|---|
| large/ARC | `P2_9_20260911T045010Z/results/large/train_cases.jsonl` | 1344 | run003 | 2026-09-11T05:04:45.307964+00:00 - 2026-09-11T05:37:09.705906+00:00 / 2026-09-11T05:37:12Z |
| large/OBQA | `P2_6_20260910T164138Z/results/train_cases.jsonl` | 4098 | run004 | n/a (no per-row utc) - n/a / 2026-09-11T03:44:06Z |
| small/ARC | `P2_9_20260911T045010Z/results/small/train_cases.jsonl` | 1344 | run003 | 2026-09-11T05:47:18.903437+00:00 - 2026-09-11T06:25:44.483867+00:00 / 2026-09-11T06:25:47Z |
| small/OBQA | `P2_5_20260910T072811Z/results/train_cases.jsonl` | 4098 | run005;run006 | n/a (no per-row utc) - n/a / 2026-09-10T08:50:29Z |

PBS windows for the OBQA rows, which have no per-row utc: small/OBQA ClusterA 7602469 ran 07:33:13-08:29:25 and 7602485 ran 08:30:34-09:07:21 on 2026-09-10 (`P2_5_20260910T072811Z/evidence/job_*.json`); large/OBQA ClusterB 185359 ran 02:04:43-04:04:54 on 2026-09-11 (`P2_6_20260910T164138Z/evidence/job_185359.json`). No P2_1-P2_4 output contains any calibration-split question.

**Parser V2 timing:** V2 was frozen 2026-09-12T19:19:38Z (`P2_SCORING_V2_20260912T191445Z/RULE_FREEZE_V2.json`). That is before the first calibration-split disagreement statistic, 2026-09-14T04:50:18Z (large/OBQA/Text, `P2_RISK_CALIBRATION_BINARY_20260914T043954Z/inputs/candidate_cal.jsonl`). For the other small/large settings, the first calibration-split statistic was written 2026-09-14T17:06-17:13Z (`P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/inputs/*_cal_machine_d.jsonl`). However, V2 rules were revised after a record-level review of exposed cases, including gold (RULE_FREEZE_V2 says "NOT globally blinded"). That review covered 355 train questions that later fell into calibration splits (large/OBQA 30, large/ARC 26, small/OBQA 186, small/ARC 113), before any split existed.

