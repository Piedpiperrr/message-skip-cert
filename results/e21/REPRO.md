# E21 Step 0: reproduction checks

Run 2026-09-22T06:56:57Z to 2026-09-22T06:58:41Z (`scripts/step0_repro.py` sha256 cb91868f4381a9da3f11bcf4b64109a58f4e6896c8f864d214a45b6009bbc750, `scripts/e21_common.py` sha256 76c4ba0fac920779654eb4bdf3379289f7086a778cc467f0a49947fb4724005f;
log `logs/step0.log`; every row also in `results/step0_repro_checks.csv`; recomputed ledgers in `results/step0_recomputed_calibration_ledgers.csv`).
ClusterA login node, CPU only. No E21 statistic was computed before these checks; PREREG.md was hashed after them.

**Result (a)-(g): 89 / 89 PASS.** (h) is a search, reported below (it finds one earlier file with calibration lost-correction counts, for Text+fact).


## (a) frozen change-rate test recomputed from stored calibration outputs (E17 ledger on the E17 loader) vs stored ledgers; largest accepted = frozen q; request p-values: 26/26 PASS

| check | expected | obtained | status | source |
|---|---|---|---|---|
| large/OBQA/Text: largest accepted candidate = frozen q | 0.8 | 0.8 | PASS | recomputed: E17.ledger on E17.load cal split |
| large/OBQA/Text: 20 calibration rows (q, n, k) = stored ledger | [[0.05, 642, 1], [0.1, 642, 1], [0.15, 642, 1], [0.2, 642, 1], [0.25, 642, 1], [0.3, 642, 1], [0.35, 642, 1], [0.4, 642, 1], [0.45, 642, 1], [0.5, 683, 1], [0.5 ...(20 rows; identical) | [[0.05, 642, 1], [0.1, 642, 1], [0.15, 642, 1], [0.2, 642, 1], [0.25, 642, 1], [0.3, 642, 1], [0.35, 642, 1], [0.4, 642, 1], [0.45, 642, 1], [0.5, 683, 1], [0.5 ...(20 rows; identical) | PASS | P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/summary/calibration_all_160.csv |
| large/OBQA/C2C: largest accepted candidate = frozen q | 0.8 | 0.8 | PASS | recomputed: E17.ledger on E17.load cal split |
| large/OBQA/C2C: 20 calibration rows (q, n, k) = stored ledger | [[0.05, 642, 2], [0.1, 642, 2], [0.15, 642, 2], [0.2, 642, 2], [0.25, 642, 2], [0.3, 642, 2], [0.35, 642, 2], [0.4, 642, 2], [0.45, 642, 2], [0.5, 683, 2], [0.5 ...(20 rows; identical) | [[0.05, 642, 2], [0.1, 642, 2], [0.15, 642, 2], [0.2, 642, 2], [0.25, 642, 2], [0.3, 642, 2], [0.35, 642, 2], [0.4, 642, 2], [0.45, 642, 2], [0.5, 683, 2], [0.5 ...(20 rows; identical) | PASS | P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/summary/calibration_all_160.csv |
| large/ARC/Text: largest accepted candidate = frozen q | 0.95 | 0.95 | PASS | recomputed: E17.ledger on E17.load cal split |
| large/ARC/Text: 20 calibration rows (q, n, k) = stored ledger | [[0.05, 321, 0], [0.1, 321, 0], [0.15, 321, 0], [0.2, 321, 0], [0.25, 321, 0], [0.3, 321, 0], [0.35, 321, 0], [0.4, 321, 0], [0.45, 321, 0], [0.5, 321, 0], [0.5 ...(20 rows; identical) | [[0.05, 321, 0], [0.1, 321, 0], [0.15, 321, 0], [0.2, 321, 0], [0.25, 321, 0], [0.3, 321, 0], [0.35, 321, 0], [0.4, 321, 0], [0.45, 321, 0], [0.5, 321, 0], [0.5 ...(20 rows; identical) | PASS | P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/summary/calibration_all_160.csv |
| large/ARC/C2C: largest accepted candidate = frozen q | 0.9 | 0.9 | PASS | recomputed: E17.ledger on E17.load cal split |
| large/ARC/C2C: 20 calibration rows (q, n, k) = stored ledger | [[0.05, 321, 2], [0.1, 321, 2], [0.15, 321, 2], [0.2, 321, 2], [0.25, 321, 2], [0.3, 321, 2], [0.35, 321, 2], [0.4, 321, 2], [0.45, 321, 2], [0.5, 321, 2], [0.5 ...(20 rows; identical) | [[0.05, 321, 2], [0.1, 321, 2], [0.15, 321, 2], [0.2, 321, 2], [0.25, 321, 2], [0.3, 321, 2], [0.35, 321, 2], [0.4, 321, 2], [0.45, 321, 2], [0.5, 321, 2], [0.5 ...(20 rows; identical) | PASS | P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/summary/calibration_all_160.csv |
| large/MMLU-Pro/Text: largest accepted candidate = frozen q | 0.4 | 0.4 | PASS | recomputed: E17.ledger on E17.load cal split |
| large/MMLU-Pro/Text: 20 calibration rows (q, n, k) = stored ledger | [[0.05, 1442, 14], [0.1, 1442, 14], [0.15, 1442, 14], [0.2, 1442, 14], [0.25, 1542, 17], [0.3, 1817, 26], [0.35, 2105, 43], [0.4, 2358, 67], [0.45, 2654, 105],  ...(20 rows; identical) | [[0.05, 1442, 14], [0.1, 1442, 14], [0.15, 1442, 14], [0.2, 1442, 14], [0.25, 1542, 17], [0.3, 1817, 26], [0.35, 2105, 43], [0.4, 2358, 67], [0.45, 2654, 105],  ...(20 rows; identical) | PASS | P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/calibration/40_test_ledger.csv |
| large/MMLU-Pro/C2C: largest accepted candidate = frozen q | 0.4 | 0.4 | PASS | recomputed: E17.ledger on E17.load cal split |
| large/MMLU-Pro/C2C: 20 calibration rows (q, n, k) = stored ledger | [[0.05, 1442, 9], [0.1, 1442, 9], [0.15, 1442, 9], [0.2, 1442, 9], [0.25, 1542, 9], [0.3, 1817, 24], [0.35, 2105, 45], [0.4, 2358, 75], [0.45, 2654, 118], [0.5, ...(20 rows; identical) | [[0.05, 1442, 9], [0.1, 1442, 9], [0.15, 1442, 9], [0.2, 1442, 9], [0.25, 1542, 9], [0.3, 1817, 24], [0.35, 2105, 45], [0.4, 2358, 75], [0.45, 2654, 118], [0.5, ...(20 rows; identical) | PASS | P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/calibration/40_test_ledger.csv |
| medium/OBQA/C2C q=.55: largest accepted candidate = frozen q | 0.55 | 0.55 | PASS | recomputed: E17.ledger on E17.load cal split |
| medium/OBQA/C2C q=.55: 20 calibration rows (q, n, k) = stored ledger | [[0.05, 601, 7], [0.1, 601, 7], [0.15, 601, 7], [0.2, 601, 7], [0.25, 601, 7], [0.3, 601, 7], [0.35, 601, 7], [0.4, 601, 7], [0.45, 601, 7], [0.5, 665, 10], [0. ...(20 rows; identical) | [[0.05, 601, 7], [0.1, 601, 7], [0.15, 601, 7], [0.2, 601, 7], [0.25, 601, 7], [0.3, 601, 7], [0.35, 601, 7], [0.4, 601, 7], [0.45, 601, 7], [0.5, 665, 10], [0. ...(20 rows; identical) | PASS | P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/calibration/obqa_C.csv |
| medium/OBQA/C2C q=.55: frozen-q row k/n and p (request value) | [19, 739, "6.9e-04"] | [19, 739, "6.9e-04"] | PASS | request |
| medium/ARC/C2C: largest accepted candidate = frozen q | 0.6 | 0.6 | PASS | recomputed: E17.ledger on E17.load cal split |
| medium/ARC/C2C: 20 calibration rows (q, n, k) = stored ledger | [[0.05, 256, 1], [0.1, 256, 1], [0.15, 256, 1], [0.2, 256, 1], [0.25, 256, 1], [0.3, 256, 1], [0.35, 256, 1], [0.4, 256, 1], [0.45, 256, 1], [0.5, 256, 1], [0.5 ...(20 rows; identical) | [[0.05, 256, 1], [0.1, 256, 1], [0.15, 256, 1], [0.2, 256, 1], [0.25, 256, 1], [0.3, 256, 1], [0.35, 256, 1], [0.4, 256, 1], [0.45, 256, 1], [0.5, 256, 1], [0.5 ...(20 rows; identical) | PASS | P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/calibration/arc_C.csv |
| large/OBQA/Text+fact: largest accepted candidate = frozen q | 0.75 | 0.75 | PASS | recomputed: E17.ledger on E17.load cal split |
| large/OBQA/Text+fact: 20 calibration rows (q, n, k) = stored ledger | [[0.05, 642, 2], [0.1, 642, 2], [0.15, 642, 2], [0.2, 642, 2], [0.25, 642, 2], [0.3, 642, 2], [0.35, 642, 2], [0.4, 642, 2], [0.45, 642, 2], [0.5, 683, 2], [0.5 ...(20 rows; identical) | [[0.05, 642, 2], [0.1, 642, 2], [0.15, 642, 2], [0.2, 642, 2], [0.25, 642, 2], [0.3, 642, 2], [0.35, 642, 2], [0.4, 642, 2], [0.45, 642, 2], [0.5, 683, 2], [0.5 ...(20 rows; identical) | PASS | P2_R2_GPU_20260919T220941Z/e6/analysis/E6_LEDGER.csv |
| large/OBQA/Text+fact: frozen-q row k/n and p (request value) | [22, 999, "4.8e-06"] | [22, 999, "4.8e-06"] | PASS | request |
| Llama-3.1-8B/OBQA/Text: largest accepted candidate = frozen q | 0.6 | 0.6 | PASS | recomputed: E17.ledger on E17.load cal split |
| Llama-3.1-8B/OBQA/Text: 20 calibration rows (q, n, k) = stored ledger | [[0.05, 57, 0], [0.1, 110, 0], [0.15, 192, 0], [0.2, 259, 0], [0.25, 311, 0], [0.3, 397, 1], [0.35, 457, 2], [0.4, 533, 6], [0.45, 595, 7], [0.5, 671, 12], [0.5 ...(20 rows; identical) | [[0.05, 57, 0], [0.1, 110, 0], [0.15, 192, 0], [0.2, 259, 0], [0.25, 311, 0], [0.3, 397, 1], [0.35, 457, 2], [0.4, 533, 6], [0.45, 595, 7], [0.5, 671, 12], [0.5 ...(20 rows; identical) | PASS | P2_R6_X3_20260921T052602Z/results/analysis/certification_ledger_40.csv |
| Llama-3.1-8B/OBQA/Text: frozen-q row k/n and p (request value) | [21, 800, "5.7e-04"] | [21, 800, "5.7e-04"] | PASS | request |
| Llama-3.1-8B/ARC/Text: largest accepted candidate = frozen q | 0.7 | 0.7 | PASS | recomputed: E17.ledger on E17.load cal split |
| Llama-3.1-8B/ARC/Text: 20 calibration rows (q, n, k) = stored ledger | [[0.05, 19, 0], [0.1, 44, 0], [0.15, 77, 0], [0.2, 89, 0], [0.25, 113, 0], [0.3, 129, 0], [0.35, 147, 0], [0.4, 172, 0], [0.45, 205, 0], [0.5, 218, 1], [0.55, 2 ...(20 rows; identical) | [[0.05, 19, 0], [0.1, 44, 0], [0.15, 77, 0], [0.2, 89, 0], [0.25, 113, 0], [0.3, 129, 0], [0.35, 147, 0], [0.4, 172, 0], [0.45, 205, 0], [0.5, 218, 1], [0.55, 2 ...(20 rows; identical) | PASS | P2_R6_X3_20260921T052602Z/results/analysis/certification_ledger_40.csv |
| Llama-3.1-8B/ARC/Text: frozen-q row k/n and p (request value) | [4, 320, "3.15e-04"] | [4, 320, "3.15e-04"] | PASS | request |

## (b) dev omitted/changed at the frozen q (expected = E19 REPRO.md values) and dev correct counts (expected = request / E13 item3 PAPER_DEV): 17/17 PASS

| check | expected | obtained | status | source |
|---|---|---|---|---|
| large/OBQA/Text: dev omitted/changed at frozen q | [572, 19] | [572, 19] | PASS | P2_R8_E19_20260921T224942Z/REPRO.md |
| large/OBQA/C2C: dev omitted/changed at frozen q | [572, 13] | [572, 13] | PASS | P2_R8_E19_20260921T224942Z/REPRO.md |
| large/ARC/Text: dev omitted/changed at frozen q | [284, 9] | [284, 9] | PASS | P2_R8_E19_20260921T224942Z/REPRO.md |
| large/ARC/C2C: dev omitted/changed at frozen q | [270, 3] | [270, 3] | PASS | P2_R8_E19_20260921T224942Z/REPRO.md |
| large/MMLU-Pro/Text: dev omitted/changed at frozen q | [1069, 40] | [1069, 40] | PASS | P2_R8_E19_20260921T224942Z/REPRO.md |
| large/MMLU-Pro/C2C: dev omitted/changed at frozen q | [1069, 37] | [1069, 37] | PASS | P2_R8_E19_20260921T224942Z/REPRO.md |
| medium/OBQA/C2C q=.55: dev omitted/changed at frozen q | [390, 11] | [390, 11] | PASS | P2_R8_E19_20260921T224942Z/REPRO.md |
| medium/ARC/C2C: dev omitted/changed at frozen q | [189, 4] | [189, 4] | PASS | P2_R8_E19_20260921T224942Z/REPRO.md |
| large/OBQA/Text+fact: dev omitted/changed at frozen q | [536, 13] | [536, 13] | PASS | P2_R8_E19_20260921T224942Z/REPRO.md |
| Llama-3.1-8B/OBQA/Text: dev omitted/changed at frozen q | [438, 7] | [438, 7] | PASS | P2_R8_E19_20260921T224942Z/REPRO.md |
| Llama-3.1-8B/ARC/Text: dev omitted/changed at frozen q | [206, 4] | [206, 4] | PASS | P2_R8_E19_20260921T224942Z/REPRO.md |
| large/OBQA/Text: dev correct R / reference / frozen policy | [617, 645, 638] | [617, 645, 638] | PASS | request; P2_R5_E13.../scripts/item3.py PAPER_DEV |
| large/ARC/Text: dev correct R / reference / frozen policy | [268, 274, 270] | [268, 274, 270] | PASS | request; P2_R5_E13.../scripts/item3.py PAPER_DEV |
| large/MMLU-Pro/Text: dev correct R / reference / frozen policy | [1282, 1319, 1321] | [1282, 1319, 1321] | PASS | request; P2_R5_E13.../scripts/item3.py PAPER_DEV |
| large/OBQA/Text+fact: dev correct R / reference / frozen policy | [617, 670, 660] | [617, 670, 660] | PASS | request; P2_R5_E13.../scripts/item3.py PAPER_DEV |
| Llama-3.1-8B/OBQA/Text: dev correct R / reference / frozen policy | [603, 636, 638] | [603, 636, 638] | PASS | request; P2_R5_E13.../scripts/item3.py PAPER_DEV |
| Llama-3.1-8B/ARC/Text: dev correct R / reference / frozen policy | [239, 260, 258] | [239, 260, 258] | PASS | request; P2_R5_E13.../scripts/item3.py PAPER_DEV |

## (c) out-of-sample omitted/changed at the frozen q; omit iff u <= frozen tau equals the stored route flag: 10/10 PASS

| check | expected | obtained | status | source |
|---|---|---|---|---|
| large/OBQA/Text: held-out OBQA 744 omit iff u <= frozen tau equals stored route flag | 0 | 0 | PASS | P2_R3_E9BC_20260920T061042Z/analysis/SEALED_ROUTES.jsonl |
| large/OBQA/Text: held-out OBQA 744 omitted/changed at frozen q | [595, 12] | [595, 12] | PASS | P2_R3_E9BC_20260920T061042Z/analysis/SEALED_ROUTES.jsonl |
| large/OBQA/Text+fact: held-out OBQA 744 omit iff u <= frozen tau equals stored route flag | 0 | 0 | PASS | P2_R3_E9BC_20260920T061042Z/analysis/SEALED_ROUTES.jsonl |
| large/OBQA/Text+fact: held-out OBQA 744 omitted/changed at frozen q | [558, 16] | [558, 16] | PASS | P2_R3_E9BC_20260920T061042Z/analysis/SEALED_ROUTES.jsonl |
| Llama-3.1-8B/OBQA/Text: held-out OBQA 744 (E16-1) omit iff u <= frozen tau equals stored route flag | 0 | 0 | PASS | P2_R7_E16_20260921T184114Z/results/analysis_oos/routes_llama_obqa.jsonl |
| Llama-3.1-8B/OBQA/Text: held-out OBQA 744 (E16-1) omitted/changed at frozen q | [440, 3] | [440, 3] | PASS | P2_R7_E16_20260921T184114Z/results/analysis_oos/routes_llama_obqa.jsonl |
| Llama-3.1-8B/ARC/Text: ARC test 1,172 (E16-1) omit iff u <= frozen tau equals stored route flag | 0 | 0 | PASS | P2_R7_E16_20260921T184114Z/results/analysis_oos/routes_llama_arc.jsonl |
| Llama-3.1-8B/ARC/Text: ARC test 1,172 (E16-1) omitted/changed at frozen q | [794, 15] | [794, 15] | PASS | P2_R7_E16_20260921T184114Z/results/analysis_oos/routes_llama_arc.jsonl |
| large/ARC/Text: sealed ARC 1,172 omit iff u <= frozen tau equals stored route flag | 0 | 0 | PASS | P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/records/e2e_requests.jsonl (e17_common.load_sealed) |
| large/ARC/Text: sealed ARC 1,172 omitted/changed at frozen q | [1100, 20] | [1100, 20] | PASS | P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/records/e2e_requests.jsonl (e17_common.load_sealed) |

## (d) dev AUROC, ties 1/2 (E17.auroc = sklearn roc_auc_score): paper value (3 dp, |diff| <= 5e-4) and stored unrounded value (|diff| < 1e-12): 25/25 PASS

| check | expected | obtained | status | source |
|---|---|---|---|---|
| medium/OBQA/C2C q=.55: dev AUROC vs paper 0.84 (|diff| <= 5e-4) | 0.84 | 0.840107 | PASS | paper tab_dev_full.tex / request |
| medium/OBQA/C2C q=.55: dev AUROC vs stored unrounded (E17_5_inputs.csv) | 0.8401069451905898 | 0.8401069451905898 | PASS | P2_R7_E17_20260921T183100Z/results/E17_5_inputs.csv |
| medium/ARC/C2C: dev AUROC vs paper 0.91 (|diff| <= 5e-4) | 0.91 | 0.909736 | PASS | paper tab_dev_full.tex / request |
| medium/ARC/C2C: dev AUROC vs stored unrounded (E17_5_inputs.csv) | 0.9097360557768924 | 0.9097360557768924 | PASS | P2_R7_E17_20260921T183100Z/results/E17_5_inputs.csv |
| large/OBQA/Text: dev AUROC vs paper 0.873 (|diff| <= 5e-4) | 0.873 | 0.87273 | PASS | paper tab_dev_full.tex / request |
| large/OBQA/Text: dev AUROC vs stored unrounded (E17_5_inputs.csv) | 0.8727300995024876 | 0.8727300995024876 | PASS | P2_R7_E17_20260921T183100Z/results/E17_5_inputs.csv |
| large/OBQA/C2C: dev AUROC vs paper 0.883 (|diff| <= 5e-4) | 0.883 | 0.882649 | PASS | paper tab_dev_full.tex / request |
| large/OBQA/C2C: dev AUROC vs stored unrounded (E17_5_inputs.csv) | 0.8826490713587488 | 0.8826490713587488 | PASS | P2_R7_E17_20260921T183100Z/results/E17_5_inputs.csv |
| large/ARC/Text: dev AUROC vs paper 0.952 (|diff| <= 5e-4) | 0.952 | 0.951878 | PASS | paper tab_dev_full.tex / request |
| large/ARC/Text: dev AUROC vs stored unrounded (E17_5_inputs.csv) | 0.9518779342723005 | 0.9518779342723005 | PASS | P2_R7_E17_20260921T183100Z/results/E17_5_inputs.csv |
| large/ARC/C2C: dev AUROC vs paper 0.909 (|diff| <= 5e-4) | 0.909 | 0.908827 | PASS | paper tab_dev_full.tex / request |
| large/ARC/C2C: dev AUROC vs stored unrounded (E17_5_inputs.csv) | 0.9088269454123112 | 0.9088269454123112 | PASS | P2_R7_E17_20260921T183100Z/results/E17_5_inputs.csv |
| large/MMLU-Pro/Text: dev AUROC vs paper 0.821 (|diff| <= 5e-4) | 0.821 | 0.821468 | PASS | paper tab_dev_full.tex / request |
| large/MMLU-Pro/Text: dev AUROC vs stored unrounded (E17_5_inputs.csv) | 0.8214679315782257 | 0.8214679315782257 | PASS | P2_R7_E17_20260921T183100Z/results/E17_5_inputs.csv |
| large/MMLU-Pro/C2C: dev AUROC vs paper 0.846 (|diff| <= 5e-4) | 0.846 | 0.8464 | PASS | paper tab_dev_full.tex / request |
| large/MMLU-Pro/C2C: dev AUROC vs stored unrounded (E17_5_inputs.csv) | 0.8463998007101454 | 0.8463998007101454 | PASS | P2_R7_E17_20260921T183100Z/results/E17_5_inputs.csv |
| large/OBQA/Text+fact: dev AUROC vs paper 0.889 (|diff| <= 5e-4) | 0.889 | 0.888593 | PASS | paper tab_dev_full.tex / request |
| large/OBQA/Text+fact: dev AUROC vs stored unrounded (E17_5_inputs.csv) | 0.8885925399083293 | 0.8885925399083293 | PASS | P2_R7_E17_20260921T183100Z/results/E17_5_inputs.csv |
| Llama-3.1-8B/OBQA/Text: dev AUROC vs paper 0.8745 (|diff| <= 5e-4) | 0.8745 | 0.874486 | PASS | paper tab_dev_full.tex / request |
| Llama-3.1-8B/OBQA/Text: dev AUROC vs stored unrounded (E17_5_inputs.csv) | 0.8744859614293817 | 0.8744859614293817 | PASS | P2_R7_E17_20260921T183100Z/results/E17_5_inputs.csv |
| Llama-3.1-8B/ARC/Text: dev AUROC vs paper 0.8804 (|diff| <= 5e-4) | 0.8804 | 0.880442 | PASS | paper tab_dev_full.tex / request |
| Llama-3.1-8B/ARC/Text: dev AUROC vs stored unrounded (E17_5_inputs.csv) | 0.8804415102125026 | 0.8804415102125026 | PASS | P2_R7_E17_20260921T183100Z/results/E17_5_inputs.csv |
| SQuAD/Llama (s2): dev AUROC vs paper .811 (|diff| <= 5e-4) | 0.811 | 0.810852 | PASS | request |
| SQuAD/Llama (s2): dev AUROC vs STATS_E20F.json dev.AUROC_s2 | 0.8108516778729544 | 0.8108516778729544 | PASS | P2_R8_E20F_20260922T003652Z/STATS_E20F.json |
| SQuAD/Llama dev disagreements (E20F: 154/1000) | [154, 1000] | [154, 1000] | PASS | P2_R8_E20F_20260922T003652Z/RESULTS_E20F.md |

## (e) E13-3 gain retention at alpha = .05 (dev, frozen policy): (correct policy - correct R) / (correct reference - correct R): 4/4 PASS

| check | expected | obtained | status | source |
|---|---|---|---|---|
| large/OBQA/Text: E13-3 gain retention at alpha=.05 (3 dp) | 0.75 | 0.75 | PASS | request / E13 item3_alpha_sweep.csv |
| large/ARC/Text: E13-3 gain retention at alpha=.05 (3 dp) | 0.333 | 0.333 | PASS | request / E13 item3_alpha_sweep.csv |
| large/MMLU-Pro/Text: E13-3 gain retention at alpha=.05 (3 dp) | 1.054 | 1.054 | PASS | request / E13 item3_alpha_sweep.csv |
| large/OBQA/Text+fact: E13-3 gain retention at alpha=.05 (3 dp) | 0.811 | 0.811 | PASS | request / E13 item3_alpha_sweep.csv |

## (f) E19-1 panel net saving of the six E21-1 policies (paired mean of fixed - policy latency_ms, all requests; E19 bootstrap): 6/6 PASS

| check | expected | obtained | status | source |
|---|---|---|---|---|
| large/OBQA/Text: E19-1 panel net saving [95% CI] (ms, unrounded) | [517.1262959393061, 447.76240365922604, 583.5989186702591] | [517.1262959393061, 447.76240365922604, 583.5989186702591] | PASS | P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z/records/e2e_requests.jsonl |
| large/ARC/Text: E19-1 panel net saving [95% CI] (ms, unrounded) | [717.6287613056047, 670.6139493022874, 763.2107882986928] | [717.6287613056047, 670.6139493022874, 763.2107882986928] | PASS | P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z/records/e2e_requests.jsonl |
| large/MMLU-Pro/Text: E19-1 panel net saving [95% CI] (ms, unrounded) | [346.3156871330284, 249.8286115142946, 442.9725224629692] | [346.3156871330284, 249.8286115142946, 442.9725224629692] | PASS | P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z/records/four_arm_requests.jsonl |
| large/OBQA/Text+fact: E19-1 panel net saving [95% CI] (ms, unrounded) | [343.4279101056745, 297.7048677665607, 385.9620618798999] | [343.4279101056745, 297.7048677665607, 385.9620618798999] | PASS | P2_R2_E7_20260919T231531Z/e6replay/records_e6/e6_replay_requests.jsonl |
| Llama-3.1-8B/OBQA/Text: E19-1 panel net saving [95% CI] (ms, unrounded) | [318.60086990127456, 261.09326909677293, 372.13898995200907] | [318.60086990127456, 261.09326909677293, 372.13898995200907] | PASS | P2_R7_E16_20260921T184114Z/replay_llama/records/e2e_requests.jsonl |
| Llama-3.1-8B/ARC/Text: E19-1 panel net saving [95% CI] (ms, unrounded) | [418.89480087957054, 361.6965100735797, 473.7328009223802] | [418.89480087957054, 361.6965100735797, 473.7328009223802] | PASS | P2_R7_E16_20260921T184114Z/replay_llama/records/e2e_requests.jsonl |

## (g) E5-c change decomposition of V1 vs R on large/OBQA dev (V1 mapped back to original labels; e5c.py logic): 1/1 PASS

| check | expected | obtained | status | source |
|---|---|---|---|---|
| E5-c large/OBQA V1 vs R: correct, changed, corrective, harmful | [599, 137, 48, 66] | [599, 137, 48, 66] | PASS | P2_R2_CPU_20260919T220412Z/results/e5c_change_decomposition.csv |

## (h) Exposure search: earlier result files with a computed calibration lost-correction count

Method: `scripts/step0h_exposure_scan.py` (log `logs/step0h.log`, hits `results/step0h_exposure_hits.json`) read 13,466 result-type text files
(.csv/.json/.md/.txt/.tex <= 5 MB) in every earlier P2_* folder, skipping raw model-record .jsonl files and model/tokenizer/dataset folders.
Keywords: corrections_lost, lost_correct(ion), corrective, harmful, reference_corrects/breaks, corrections_kept, corrections_total, lost gain.
55 files matched. Each was classified by hand:

**Found: one earlier result, for large/OBQA/Text+fact only.**
- `P2_R2_GPU_20260919T220941Z/e6/E6_RESULTS.md` line 44 and `P2_R2_GPU_20260919T220941Z/e6/analysis/E6_RESULTS.json`
  (`/cal/at_deployed_q/corrective_on_omitted` = 18, `harmful_on_omitted` = 2): on the calibration split at the deployed q = .75
  (999 omitted), 18 omitted questions have Text+fact correct and R wrong. This is k_L(tau_frozen) for Text+fact.
  The same files give the whole calibration split: corrective 122, harmful 20 (`/cal/change_vs_R_whole_split`). That equals k_L at the
  q = 1.00 candidate (tau = Infinity). `E6_SUMMARY.csv` (row split=cal) repeats 122 / 20.
- So the PREREG sentence "no calibration lost-correction count is known to the authors" does not hold for Text+fact. That setting is
  already flagged nominal in the PREREG. No other setting has one.

**Not calibration lost-correction counts** (development, held-out or test only, or other quantities):
- dev at deployed q: `P2_FOCUSED_REVISION_ROUND1_CPU_EVIDENCE_AUDIT_20260918T065337Z/outputs/T3_omit_keep_help_harm.csv` and its
  ROUND1B copy (N = 742/299/2641 = dev; omit_Rwrong_refright); `P2_R5_E13_20260921T031606Z/results/item3_alpha_sweep.csv`
  (dev_ and ho_corrections_lost_omitted; its cal_n/cal_k columns are change counts, not lost corrections);
  `P2_R2_ANALYSIS_20260920T002850Z/results/E6_dev_reference_corrections.csv` (dev); `P2_R2_CPU_20260919T220412Z/results/e5c_change_decomposition.csv`
  and its SUMMARY.md (dev); the dev half of the E6 files above.
- SQuAD (not an E21 setting): `P2_R8_E20F_20260922T003652Z/results/ACCURACY_E20F.json`, RESULTS_E20F.md and the notes/dryrun copies (dev and test only).
- Keyword in unrelated text: literature evidence in P2_1 (workshop.txt, cipher_commit.json, interlat_acl.txt), paper .tex snapshots
  (methods/results .tex in several folders), `P2_E1_DIRECTION_20260913T053456Z/frozen_config.json` (a description string), one helper message
  (`P2_E1_E2E_OBQA_.../records/train_fixed/0154_T.json`, "harmful substances"), dev record JSONs in P2_E1_E2E_OBQA and P2_6 dev_matrix.csv,
  OBQA fact text (`P2_R3_E9BC_.../inputs/obqa_fact1.json`), official-evaluator CSVs of E1 (question text), `P2_RISK_CALIBRATION_BINARY_.../paper/14_binary_risk_protocol_limits.tex`
  (a sentence), the E5 PREREG (definition of X).
- Also noted, not lost-correction counts: whole-split calibration accuracy counts exist for Llama (`P2_R6_X3_.../results/analysis/accuracy_per_split.csv`:
  cal R 1070 / Text 1149 of 1366 on OBQA; 377 / 395 of 448 on ARC) and for Text+fact (E6_RESULTS: 1113 / 1178 / 1215 of 1366).
