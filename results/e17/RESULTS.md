# E17 results (Round 7): six descriptive re-analyses of stored outputs

Stage `$DATA_DIR/P2_R7_E17_20260921T183100Z` (ClusterA login node; CPU only; no model, no GPU, no submit-job).

- Preregistration `PREREG.md`, SHA-256 `2efda6906533bd16dd2bc3ff58ba6c0b9986543984a8fbb65ccb698f6d21863e`, hashed 2026-09-21T18:31:26Z (`PREREG.sha256`).
- First new computation: `scripts/step2.py` started 2026-09-21T18:35:03Z (`logs/step2.log`).
- Step 2 reproduction checks: 64/64 PASS (`results/step2_checks.csv`).
- Scripts: `scripts/e17_common.py` (loaders), `step2.py`, `cache28.py`, `e17_1_2.py`, `e17_3.py`, `e17_4.py`, `e17_5.py`, `e17_6.py`,
  `make_results.py` (this file), `run_audited.py` (audited re-run: every project file opened is listed in `logs/files_opened_*.txt`).
- Conventions: parser V2; two unparseable = agreement; CP = two-sided 95% Clopper-Pearson; p = P[Bin(n, .05) <= k].
- Deviations: `DEVIATIONS.md`.

## Step 2. Reproduction checks

- PASS: (1) large/OBQA/Text: dev omitted/changed vs E14_2_zero_u.csv: [572, 19]
- PASS: (1) large/OBQA/C2C: dev omitted/changed vs E14_2_zero_u.csv: [572, 13]
- PASS: (1) large/ARC/Text: dev omitted/changed vs E14_2_zero_u.csv: [284, 9]
- PASS: (1) large/ARC/C2C: dev omitted/changed vs E14_2_zero_u.csv: [270, 3]
- PASS: (1) large/MMLU-Pro/Text: dev omitted/changed vs E14_2_zero_u.csv: [1069, 40]
- PASS: (1) large/MMLU-Pro/C2C: dev omitted/changed vs E14_2_zero_u.csv: [1069, 37]
- PASS: (1) medium/OBQA/C2C q=.55: dev omitted/changed vs E14_2_zero_u.csv: [390, 11]
- PASS: (1) medium/OBQA/C2C q=.50: dev omitted/changed vs E14_2_zero_u.csv: [355, 7]
- PASS: (1) medium/OBQA/C2C q=.50: dev omitted/changed vs value in the E17 request: [355, 7]
- PASS: (1) medium/ARC/C2C: dev omitted/changed vs E14_2_zero_u.csv: [189, 4]
- PASS: (1) large/OBQA/Text+fact: dev omitted/changed vs E14_2_zero_u.csv: [536, 13]
- PASS: (1) large/OBQA/Text+fact: dev omitted/changed vs value in the E17 request: [536, 13]
- PASS: (1) X3 obqa/Text: frozen q (X3 dev_table.csv): 0.6
- PASS: (1) X3 obqa/Text: dev omitted/changed vs X3 dev_table.csv: [438, 7]
- PASS: (1) X3 obqa/Text: dev omitted/changed vs value in the E17 request: [438, 7]
- PASS: (1) X3 arc/Text: frozen q (X3 dev_table.csv): 0.7
- PASS: (1) X3 arc/Text: dev omitted/changed vs X3 dev_table.csv: [206, 4]
- PASS: (1) X3 arc/Text: dev omitted/changed vs value in the E17 request: [206, 4]
- PASS: (2) E14-2 dev n0/n range over the nine certified thresholds (%, 1 decimal): [60.3, 92.1]
- PASS: (3) E14-1 sealed C2C official k/n: [54, 1044]
- PASS: (3) E14-1 sealed C2C V2 k/n on the same subset: [11, 1044]
- PASS: (3) E14-1 sealed C2C label differences (outputs): 44
- PASS: (3) E14_1_label_diffs.csv rows: 44
- PASS: (4) large/ARC/Text cal q=1: k/n: [12, 448]
- PASS: (0) all 28 certification outcomes recomputed from the stored thresholds and calibration records (11 certify, 17 fall back).
- PASS: (5) E17-1 dev n0/k0 at every certified threshold equals `E14_2_zero_u.csv` (10 rows).

## E17-1. "Omit iff u = 0" baseline (`results/E17_1_u0_rule.csv`, `results/E17_1_tau0_candidates.csv`)

| policy | cal n0 / k0 | cal k0/n0 [CP] | cal p | dev n0/N (coverage) | dev k0/n0 [CP] | policy dev coverage | policy k/n [CP] | fit grid q with tau = 0 (accepted in original certification) |
|---|---|---|---|---|---|---|---|---|
| large/OBQA/Text [nominal] | 642 / 1 | 0.16% [0.00%, 0.86%] | 1.74e-13 | 354/742 (47.7%) | 2/354 = 0.56% [0.07%, 2.03%] | 77.1% | 19/572 = 3.32% [2.01%, 5.14%] | 0.05:acc;0.10:acc;0.15:acc;0.20:acc;0.25:acc;0.30:acc;0.35:acc;0.40:acc;0.45:acc |
| large/OBQA/C2C [nominal] | 642 / 2 | 0.31% [0.04%, 1.12%] | 3.02e-12 | 354/742 (47.7%) | 1/354 = 0.28% [0.01%, 1.56%] | 77.1% | 13/572 = 2.27% [1.22%, 3.86%] | 0.05:acc;0.10:acc;0.15:acc;0.20:acc;0.25:acc;0.30:acc;0.35:acc;0.40:acc;0.45:acc |
| large/ARC/Text | 321 / 0 | 0.00% [0.00%, 1.14%] | 7.07e-08 | 217/299 (72.6%) | 0/217 = 0.00% [0.00%, 1.69%] | 95.0% | 9/284 = 3.17% [1.46%, 5.93%] | 0.05:acc;0.10:acc;0.15:acc;0.20:acc;0.25:acc;0.30:acc;0.35:acc;0.40:acc;0.45:acc;0.50:acc;0.55:acc;0.60:acc;0.65:acc;0.70:acc |
| large/ARC/C2C | 321 / 2 | 0.62% [0.08%, 2.23%] | 1.13e-05 | 217/299 (72.6%) | 1/217 = 0.46% [0.01%, 2.54%] | 90.3% | 3/270 = 1.11% [0.23%, 3.21%] | 0.05:acc;0.10:acc;0.15:acc;0.20:acc;0.25:acc;0.30:acc;0.35:acc;0.40:acc;0.45:acc;0.50:acc;0.55:acc;0.60:acc;0.65:acc;0.70:acc |
| large/MMLU-Pro/Text | 1442 / 14 | 0.97% [0.53%, 1.62%] | 2.09e-17 | 645/2641 (24.4%) | 8/645 = 1.24% [0.54%, 2.43%] | 40.5% | 40/1069 = 3.74% [2.69%, 5.06%] | 0.05:acc;0.10:acc;0.15:acc;0.20:acc |
| large/MMLU-Pro/C2C | 1442 / 9 | 0.62% [0.29%, 1.18%] | 1.92e-21 | 645/2641 (24.4%) | 5/645 = 0.78% [0.25%, 1.80%] | 40.5% | 37/1069 = 3.46% [2.45%, 4.74%] | 0.05:acc;0.10:acc;0.15:acc;0.20:acc |
| medium/OBQA/C2C q=.55 | 601 / 7 | 1.16% [0.47%, 2.38%] | 3.16e-07 | 321/742 (43.3%) | 7/321 = 2.18% [0.88%, 4.44%] | 52.6% | 11/390 = 2.82% [1.42%, 4.99%] | 0.05:acc;0.10:acc;0.15:acc;0.20:acc;0.25:acc;0.30:acc;0.35:acc;0.40:acc;0.45:acc |
| medium/OBQA/C2C q=.50 | 601 / 7 | 1.16% [0.47%, 2.38%] | 3.16e-07 | 321/742 (43.3%) | 7/321 = 2.18% [0.88%, 4.44%] | 47.8% | 7/355 = 1.97% [0.80%, 4.02%] | 0.05:acc;0.10:acc;0.15:acc;0.20:acc;0.25:acc;0.30:acc;0.35:acc;0.40:acc;0.45:acc |
| medium/ARC/C2C | 256 / 1 | 0.39% [0.01%, 2.16%] | 2.87e-05 | 174/299 (58.2%) | 1/174 = 0.57% [0.01%, 3.16%] | 63.2% | 4/189 = 2.12% [0.58%, 5.33%] | 0.05:acc;0.10:acc;0.15:acc;0.20:acc;0.25:acc;0.30:acc;0.35:acc;0.40:acc;0.45:acc;0.50:acc;0.55:acc |
| large/OBQA/Text+fact q=.75 | 642 / 2 | 0.31% [0.04%, 1.12%] | 3.02e-12 | 354/742 (47.7%) | 1/354 = 0.28% [0.01%, 1.56%] | 72.2% | 13/536 = 2.43% [1.30%, 4.11%] | 0.05:acc;0.10:acc;0.15:acc;0.20:acc;0.25:acc;0.30:acc;0.35:acc;0.40:acc;0.45:acc |
| Llama-3.1-8B/OBQA/Text | 0 / 0 | n/a | n/a | 0/742 (0.0%) | n/a | 59.0% | 7/438 = 1.60% [0.64%, 3.27%] | none |
| Llama-3.1-8B/ARC/Text | 0 / 0 | n/a | n/a | 0/299 (0.0%) | n/a | 68.9% | 4/206 = 1.94% [0.53%, 4.90%] | none |

Over the nine certified Qwen policies (medium OBQA C2C at q = .55): the u = 0 rule covers 24.4%–72.6% of dev with change rate 0.00%–2.18%; the certified policies cover 40.5%–95.0% with change rate 1.11%–3.74%. In all nine Qwen settings, tau = 0 was one of the 20 fit-grid candidates, and every tau = 0 candidate was accepted in the original certification (on cal, a tau = 0 candidate omits exactly the u = 0 questions), so the u = 0 rule was already tested. The two Llama-3.1-8B settings have no u = 0 question (n0 = 0), so no tau = 0 candidate exists there.
Writing rule: appendix table + one Sec 7 clause with these two pairs of ranges.

## E17-2. Certification on u > 0 questions only (`results/E17_2_upos_certification.csv`, ledgers `results/E17_2_upos_ledgers.csv`)

| setting | fit / cal / dev with u > 0 | q+ | cal n / k / p at q+ | dev coverage (within u > 0 / of all dev) | dev k/n [CP] | smallest cal p (q, k/n) |
|---|---|---|---|---|---|---|
| large/OBQA/Text | 1051/2100, 724/1366, 388/742 | fallback | - | - | - | 0.0020 (q = 0.2, 1/165) |
| large/OBQA/C2C | 1051/2100, 724/1366, 388/742 | 0.35 | 257 / 3 / 9.67e-04 | 31.4% / 16.4% | 1/122 = 0.82% [0.02%, 4.48%] | 7.06e-04 (q = 0.3, 2/228) |
| large/ARC/Text | 176/670, 127/448, 82/299 | fallback | - | - | - | 0.1285 (q = 0.25, 0/40) |
| large/ARC/C2C | 176/670, 127/448, 82/299 | fallback | - | - | - | 0.0660 (q = 0.35, 0/53) |
| large/MMLU-Pro/Text | 2287/3000, 4558/6000, 1996/2641 | fallback | - | - | - | 0.1498 (q = 0.1, 17/445) |
| large/MMLU-Pro/C2C | 2287/3000, 4558/6000, 1996/2641 | fallback | - | - | - | 0.1498 (q = 0.1, 17/445) |
| medium/OBQA/C2C | 1145/2100, 765/1366, 421/742 | fallback | - | - | - | 0.6014 (q = 0.05, 3/64) |
| medium/ARC/C2C | 291/670, 192/448, 125/299 | fallback | - | - | - | 0.1748 (q = 0.1, 0/34) |
| large/OBQA/Text+fact | 1051/2100, 724/1366, 388/742 | fallback | - | - | - | 0.0643 (q = 0.15, 2/117) |

**1 of 9 settings certify on u > 0 alone.** Writing rule: at least one certifies, so appendix table + Sec 7 clause "on questions with u > 0 alone, the test still certifies 1 of 9 settings".

## E17-3. ARC split comparison (`results/E17_3_splits.csv`, `E17_3_tests.csv`, `E17_3_mh_permutation.csv`, `E17_3_certified_policies.csv`)

Per setting x split (d = #(o_R != o_b)/N [CP]; INVALID counts; median u; share u == 0):

| setting | split | N | d [CP] | R INVALID | ref INVALID | median u | share u == 0 |
|---|---|---|---|---|---|---|---|
| small/ARC/Text | fit | 670 | 344/670 = 51.34% [47.49%, 55.19%] | 59 | 76 | 0.0300 | 0.0% |
| small/ARC/Text | cal | 448 | 233/448 = 52.01% [47.27%, 56.72%] | 50 | 51 | 0.0377 | 0.0% |
| small/ARC/Text | dev | 299 | 145/299 = 48.49% [42.70%, 54.32%] | 32 | 21 | 0.0431 | 0.0% |
| small/ARC/C2C | fit | 670 | 360/670 = 53.73% [49.87%, 57.56%] | 59 | 5 | 0.0300 | 0.0% |
| small/ARC/C2C | cal | 448 | 254/448 = 56.70% [51.97%, 61.34%] | 50 | 1 | 0.0377 | 0.0% |
| small/ARC/C2C | dev | 299 | 160/299 = 53.51% [47.68%, 59.27%] | 32 | 5 | 0.0431 | 0.0% |
| medium/ARC/Text | fit | 670 | 134/670 = 20.00% [17.03%, 23.23%] | 5 | 0 | 0.0000 | 56.6% |
| medium/ARC/Text | cal | 448 | 67/448 = 14.96% [11.78%, 18.60%] | 3 | 0 | 0.0000 | 57.1% |
| medium/ARC/Text | dev | 299 | 52/299 = 17.39% [13.27%, 22.17%] | 2 | 0 | 0.0000 | 58.2% |
| medium/ARC/C2C | fit | 670 | 107/670 = 15.97% [13.28%, 18.97%] | 5 | 24 | 0.0000 | 56.6% |
| medium/ARC/C2C | cal | 448 | 55/448 = 12.28% [9.38%, 15.68%] | 3 | 14 | 0.0000 | 57.1% |
| medium/ARC/C2C | dev | 299 | 48/299 = 16.05% [12.08%, 20.71%] | 2 | 12 | 0.0000 | 58.2% |
| large/ARC/Text | fit | 670 | 32/670 = 4.78% [3.29%, 6.68%] | 0 | 0 | 0.0000 | 73.7% |
| large/ARC/Text | cal | 448 | 12/448 = 2.68% [1.39%, 4.63%] | 0 | 0 | 0.0000 | 71.7% |
| large/ARC/Text | dev | 299 | 15/299 = 5.02% [2.83%, 8.14%] | 0 | 0 | 0.0000 | 72.6% |
| large/ARC/Text | test (sealed; R run only on omitted questions) | 1100 | 20/1100 = 1.82% [1.11%, 2.79%] | 0 | 0 | 0.0000 | 76.1% |
| large/ARC/C2C | fit | 670 | 31/670 = 4.63% [3.17%, 6.50%] | 0 | 2 | 0.0000 | 73.7% |
| large/ARC/C2C | cal | 448 | 21/448 = 4.69% [2.92%, 7.08%] | 0 | 1 | 0.0000 | 71.7% |
| large/ARC/C2C | dev | 299 | 12/299 = 4.01% [2.09%, 6.91%] | 0 | 0 | 0.0000 | 72.6% |
| large/ARC/C2C | test (sealed; R run only on omitted questions) | 1047 | 11/1047 = 1.05% [0.53%, 1.87%] | 0 | 0 | 0.0000 | 79.9% |
| X1-Llama/ARC/Text | fit | 670 | 210/670 = 31.34% [27.84%, 35.01%] | 59 | 29 | 0.0300 | 0.0% |
| X1-Llama/ARC/Text | cal | 448 | 160/448 = 35.71% [31.27%, 40.35%] | 50 | 26 | 0.0377 | 0.0% |
| X1-Llama/ARC/Text | dev | 299 | 88/299 = 29.43% [24.33%, 34.95%] | 32 | 14 | 0.0431 | 0.0% |
| X1-Llama/ARC/C2C | fit | 670 | 403/670 = 60.15% [56.33%, 63.88%] | 59 | 36 | 0.0300 | 0.0% |
| X1-Llama/ARC/C2C | cal | 448 | 273/448 = 60.94% [56.25%, 65.48%] | 50 | 25 | 0.0377 | 0.0% |
| X1-Llama/ARC/C2C | dev | 299 | 174/299 = 58.19% [52.38%, 63.85%] | 32 | 17 | 0.0431 | 0.0% |
| X2-OLMo/ARC/Text | fit | 670 | 147/670 = 21.94% [18.86%, 25.27%] | 80 | 57 | 0.0194 | 0.0% |
| X2-OLMo/ARC/Text | cal | 448 | 95/448 = 21.21% [17.51%, 25.29%] | 41 | 36 | 0.0270 | 0.0% |
| X2-OLMo/ARC/Text | dev | 299 | 67/299 = 22.41% [17.81%, 27.56%] | 36 | 19 | 0.0295 | 0.0% |
| X3-Llama8B/ARC/Text | fit | 670 | 58/670 = 8.66% [6.64%, 11.05%] | 0 | 0 | 0.0015 | 0.0% |
| X3-Llama8B/ARC/Text | cal | 448 | 40/448 = 8.93% [6.46%, 11.96%] | 0 | 0 | 0.0017 | 0.0% |
| X3-Llama8B/ARC/Text | dev | 299 | 37/299 = 12.37% [8.86%, 16.65%] | 0 | 0 | 0.0022 | 0.0% |

The sealed test rows are the omitted questions only: R was not executed on the other questions. The train-vs-test comparison is therefore made on questions below the frozen threshold (u <= tau) on both sides, the only region where R was run on the test split. On all 1,172 sealed questions, the median u is 0, the share of u == 0 is 71.4%, and there are 0 (Text) and 1 (C2C) reference INVALID outputs.

Descriptive tests (Fisher exact two-sided; OR = odds of disagreement in the first-named split / the second-named split):

| setting | d_fit | d_cal | d_dev | OR cal:dev, p | OR fit:cal, p | train (fit+cal) vs test, on questions below the frozen threshold (u <= tau): k/n vs k/n, OR, p |
|---|---|---|---|---|---|---|
| small/ARC/Text | 51.34% | 52.01% | 48.49% | 1.151, 0.370 | 0.974, 0.855 | - |
| small/ARC/C2C | 53.73% | 56.70% | 53.51% | 1.137, 0.409 | 0.887, 0.358 | - |
| medium/ARC/Text | 20.00% | 14.96% | 17.39% | 0.835, 0.414 | 1.422, 0.032 | - |
| medium/ARC/C2C | 15.97% | 12.28% | 16.05% | 0.732, 0.159 | 1.358, 0.099 | - |
| large/ARC/Text | 4.78% | 2.68% | 5.02% | 0.521, 0.110 | 1.822, 0.085 | 23/1059 vs 20/1100, 1.199, 0.645 |
| large/ARC/C2C | 4.63% | 4.69% | 4.01% | 1.176, 0.719 | 0.986, 1.000 | 13/1007 vs 11/1047, 1.232, 0.684 |
| X1-Llama/ARC/Text | 31.34% | 35.71% | 29.43% | 1.332, 0.081 | 0.822, 0.136 | - |
| X1-Llama/ARC/C2C | 60.15% | 60.94% | 58.19% | 1.121, 0.493 | 0.968, 0.803 | - |
| X2-OLMo/ARC/Text | 21.94% | 21.21% | 22.41% | 0.932, 0.717 | 1.044, 0.824 | - |
| X3-Llama8B/ARC/Text | 8.66% | 8.93% | 12.37% | 0.694, 0.141 | 0.967, 0.914 | - |

- Settings with d_cal < d_dev: 5 of 10.
- Mantel-Haenszel common OR (odds of disagreement, dev vs cal; 10 strata; Robins-Breslow-Greenland 95% CI): 0.980 [0.871, 1.101].
- Decision test (cal vs dev; x_i = mean disagreement over the 10 settings; every question is in all 10 settings): mean(x | cal) = 0.2701 (n = 448), mean(x | dev) = 0.2669 (n = 299), statistic mean(x | dev) - mean(x | cal) = -0.0032, two-sided permutation p = 0.8232 ((1 + #|T*| >= |T|) / 10,001; plain share 0.8232; 10,000 permutations, seed 0).
- Control (fit vs cal): mean(x | fit) = 0.2725 (n = 670), mean(x | cal) = 0.2701 (n = 448), statistic mean(x | cal) - mean(x | fit) = -0.0024, p = 0.8278.
- **SYSTEMATIC: no**; significant reverse direction: no. Writing rule: appendix sentence with these numbers.

Certified ARC policies, change rate at the frozen tau:

| policy | q | split | k/n [CP] |
|---|---|---|---|
| large/ARC/Text | 0.95 | cal | 4/422 = 0.95% [0.26%, 2.41%] |
| large/ARC/Text | 0.95 | dev | 9/284 = 3.17% [1.46%, 5.93%] |
| large/ARC/Text | 0.95 | test (sealed) | 20/1100 = 1.82% [1.11%, 2.79%] |
| large/ARC/C2C | 0.9 | cal | 7/404 = 1.73% [0.70%, 3.54%] |
| large/ARC/C2C | 0.9 | dev | 3/270 = 1.11% [0.23%, 3.21%] |
| large/ARC/C2C | 0.9 | test (sealed) | 11/1047 = 1.05% [0.53%, 1.87%] |
| medium/ARC/C2C | 0.6 | cal | 1/290 = 0.34% [0.01%, 1.91%] |
| medium/ARC/C2C | 0.6 | dev | 4/189 = 2.12% [0.58%, 5.33%] |
| Llama-3.1-8B/ARC/Text | 0.7 | cal | 4/320 = 1.25% [0.34%, 3.17%] |
| Llama-3.1-8B/ARC/Text | 0.7 | dev | 4/206 = 1.94% [0.53%, 4.90%] |

## E17-4. Audit of the 44 sealed-ARC V2 vs official label differences (`results/E17_4_audit.csv`, full table for the supplement)

- Rows: 44; all on the large/ARC/C2C C2C output.
- (i) starts with one option letter A-D followed by '.', ')' or ':': 44/44; (i)+(ii) the rest is that option's text: 44/44; (i)+(ii)+(iii)+(v) (no second letter pattern; V2 label = that letter): 44/44.
- Rows failing any check: 0.
- (iv) official extractor output: {"INVALID": 44}; branch {"blocked_by_math_substring": 44} (rows containing each math-indicator substring: "tan" 17, "-" 10, "sin" 7, "+" 4, "/" 4, "cos" 3, "mod" 2; a row can contain several).
- Rows where the official label matches the stated option better than V2: 0.
- Writing rule: all 44 pass (i)+(ii)+(iii)+(v), so App I + Sec 4.5 clause ("in all 44, the output names one option letter followed by that option's own text; the official extractor rejects it").

### E17-4b. Official extraction for the Text certificates (`results/E17_4b_official_text.csv`)

| policy | extractor | n (A-D items) | k | k/n [CP] | CP upper >= 5% |
|---|---|---|---|---|---|
| held-out large/OBQA/Text q=.80 | official | 595 | 11 | 1.85% [0.93%, 3.28%] | False |
| held-out large/OBQA/Text q=.80 | V2 | 595 | 12 | 2.02% [1.05%, 3.50%] | False |
| held-out large/OBQA/Text+fact q=.75 | official | 558 | 16 | 2.87% [1.65%, 4.61%] | False |
| held-out large/OBQA/Text+fact q=.75 | V2 | 558 | 16 | 2.87% [1.65%, 4.61%] | False |
| sealed large/ARC/Text (restated from E14-1) | official | 1097 | 20 | 1.82% [1.12%, 2.80%] | False |

All 744 held-out OBQA items are A-D. No Text policy has an official-extraction CP upper bound >= 5%, so no Text policy is named in Sec 4.5.

## E17-5. Feasibility and a binormal model of the boundary

### (a) Population feasibility (`results/E17_5a_feasibility.csv`)

| setting | observed | pi | C | max TPR/FPR | max >= C | some candidate k/n <= .05 |
|---|---|---|---|---|---|---|
| small/OBQA/Text | fallback | 0.562 | 14.794 | 9.344 | False | False |
| small/OBQA/C2C | fallback | 0.531 | 16.749 | 27.769 | True | True |
| small/ARC/Text | fallback | 0.480 | 20.591 | 6.069 | False | False |
| small/ARC/C2C | fallback | 0.433 | 24.876 | 22.258 | False | False |
| medium/OBQA/Text | fallback | 0.745 | 6.495 | 5.365 | False | False |
| medium/OBQA/C2C | certify | 0.823 | 4.091 | 18.270 | True | True |
| medium/ARC/Text | fallback | 0.850 | 3.341 | 3.576 | True | True |
| medium/ARC/C2C | certify | 0.877 | 2.659 | 40.445 | True | True |
| large/OBQA/Text | certify | 0.895 | 2.222 | 85.005 | True | True |
| large/OBQA/C2C | certify | 0.907 | 1.948 | 34.902 | True | True |
| large/ARC/Text | certify | 0.973 | 0.523 | inf | True | True |
| large/ARC/C2C | certify | 0.953 | 0.934 | 8.779 | True | True |
| large/MMLU-Pro/Text | certify | 0.784 | 5.230 | 28.074 | True | True |
| large/MMLU-Pro/C2C | certify | 0.709 | 7.811 | 70.024 | True | True |
| small/MMLU-Pro/Text | fallback | 0.532 | 16.681 | 1.614 | False | False |
| small/MMLU-Pro/C2C | fallback | 0.420 | 26.274 | 2.270 | False | False |
| medium/MMLU-Pro/Text | fallback | 0.569 | 14.372 | 7.399 | False | False |
| medium/MMLU-Pro/C2C | fallback | 0.456 | 22.712 | 27.247 | True | True |
| large/OBQA/Text+fact | certify | 0.876 | 2.701 | 48.399 | True | True |
| X1-Llama/OBQA/Text | fallback | 0.728 | 7.111 | 23.952 | True | True |
| X1-Llama/OBQA/C2C | fallback | 0.415 | 26.774 | 6.918 | False | False |
| X1-Llama/ARC/Text | fallback | 0.643 | 10.556 | 8.611 | False | False |
| X1-Llama/ARC/C2C | fallback | 0.391 | 29.640 | 49.920 | True | True |
| X2-OLMo/OBQA/Text | fallback | 0.766 | 5.813 | 5.354 | False | False |
| X2-OLMo/ARC/Text | fallback | 0.788 | 5.113 | inf | True | True |
| X2-OLMo/MMLU-Pro/Text | fallback | 0.591 | 13.176 | 3.020 | False | False |
| X3-Llama8B/OBQA/Text | certify | 0.841 | 3.588 | inf | True | True |
| X3-Llama8B/ARC/Text | certify | 0.911 | 1.863 | inf | True | True |

max TPR/FPR >= C in 17/28 settings: all 11 certified settings and 6 fallback settings (small/OBQA/C2C, medium/ARC/Text, medium/MMLU-Pro/C2C, X1-Llama/OBQA/Text, X1-Llama/ARC/C2C, X2-OLMo/ARC/Text). The equivalence with "some candidate has k/n <= .05" holds in all 28.

### (b) Binormal model (`results/E17_5b_binormal.csv`; inputs `results/E17_5_inputs.csv`)

| setting | observed | prevalence (cal) | AUROC dev / cal | N_fit / N_cal | P(certify) dev-AUROC | modal q, median coverage | P(certify) cal-AUROC | AUROC at P = .5 | share u == 0 (cal) |
|---|---|---|---|---|---|---|---|---|---|
| small/OBQA/Text | fallback | 0.4378 | 0.641 / 0.645 | 2100 / 1366 | 0.0000 | - | 0.0000 | 0.9233 | 0.0% |
| small/OBQA/C2C | fallback | 0.4685 | 0.700 / 0.707 | 2100 / 1366 | 0.0000 | - | 0.0000 | 0.9301 | 0.0% |
| small/ARC/Text | fallback | 0.5201 | 0.634 / 0.644 | 670 / 448 | 0.0000 | - | 0.0000 | 0.9887 | 0.0% |
| small/ARC/C2C | fallback | 0.5670 | 0.641 / 0.707 | 670 / 448 | 0.0000 | - | 0.0000 | 0.9926 | 0.0% |
| medium/OBQA/Text | fallback | 0.2548 | 0.787 / 0.791 | 2100 / 1366 | 0.0060 | 0.1, 0.105 | 0.0105 | 0.8696 | 44.0% |
| medium/OBQA/C2C | certify | 0.1772 | 0.840 / 0.836 | 2100 / 1366 | 0.6080 | 0.3, 0.302 | 0.5605 | 0.8295 | 44.0% |
| medium/ARC/Text | fallback | 0.1496 | 0.742 / 0.775 | 670 / 448 | 0.0000 | - | 0.0050 | 0.9018 | 57.1% |
| medium/ARC/C2C | certify | 0.1228 | 0.910 / 0.904 | 670 / 448 | 0.7485 | 0.6, 0.602 | 0.6925 | 0.8852 | 57.1% |
| large/OBQA/Text | certify | 0.1047 | 0.873 / 0.919 | 2100 / 1366 | 0.9995 | 0.7, 0.697 | 1.0000 | 0.7700 | 47.0% |
| large/OBQA/C2C | certify | 0.0930 | 0.883 / 0.905 | 2100 / 1366 | 1.0000 | 0.8, 0.762 | 1.0000 | 0.7553 | 47.0% |
| large/ARC/Text | certify | 0.0268 | 0.952 / 0.946 | 670 / 448 | 1.0000 | 0.95, 0.953 | 1.0000 | 0.6294 | 71.7% |
| large/ARC/C2C | certify | 0.0469 | 0.909 / 0.901 | 670 / 448 | 0.9950 | 0.9, 0.892 | 0.9890 | 0.7700 | 71.7% |
| large/MMLU-Pro/Text | certify | 0.2158 | 0.821 / 0.814 | 3000 / 6000 | 0.9875 | 0.25, 0.252 | 0.9605 | 0.7797 | 24.0% |
| large/MMLU-Pro/C2C | certify | 0.2913 | 0.846 / 0.840 | 3000 / 6000 | 0.9610 | 0.2, 0.198 | 0.9210 | 0.8139 | 24.0% |
| small/MMLU-Pro/Text | fallback | 0.4675 | 0.644 / 0.640 | 3000 / 6000 | 0.0000 | - | 0.0000 | 0.8705 | 0.0% |
| small/MMLU-Pro/C2C | fallback | 0.5803 | 0.626 / 0.615 | 3000 / 6000 | 0.0000 | - | 0.0000 | 0.8998 | 0.0% |
| medium/MMLU-Pro/Text | fallback | 0.4307 | 0.717 / 0.726 | 3000 / 6000 | 0.0000 | - | 0.0000 | 0.8598 | 11.5% |
| medium/MMLU-Pro/C2C | fallback | 0.5445 | 0.765 / 0.756 | 3000 / 6000 | 0.0000 | - | 0.0000 | 0.8901 | 11.5% |
| large/OBQA/Text+fact | certify | 0.1245 | 0.889 / 0.908 | 2100 / 1366 | 1.0000 | 0.7, 0.664 | 1.0000 | 0.7885 | 47.0% |
| X1-Llama/OBQA/Text | fallback | 0.2723 | 0.693 / 0.722 | 2100 / 1366 | 0.0000 | - | 0.0000 | 0.8744 | 0.0% |
| X1-Llama/OBQA/C2C | fallback | 0.5849 | 0.618 / 0.663 | 2100 / 1366 | 0.0000 | - | 0.0000 | 0.9545 | 0.0% |
| X1-Llama/ARC/Text | fallback | 0.3571 | 0.678 / 0.688 | 670 / 448 | 0.0000 | - | 0.0000 | 0.9652 | 0.0% |
| X1-Llama/ARC/C2C | fallback | 0.6094 | 0.615 / 0.689 | 670 / 448 | 0.0000 | - | 0.0000 | 0.9965 | 0.0% |
| X2-OLMo/OBQA/Text | fallback | 0.2343 | 0.790 / 0.774 | 2100 / 1366 | 0.0180 | 0.1, 0.112 | 0.0045 | 0.8598 | 0.0% |
| X2-OLMo/ARC/Text | fallback | 0.2121 | 0.749 / 0.705 | 670 / 448 | 0.0000 | - | 0.0000 | 0.9301 | 0.0% |
| X2-OLMo/MMLU-Pro/Text | fallback | 0.4095 | 0.633 / 0.651 | 3000 / 6000 | 0.0000 | - | 0.0000 | 0.8539 | 0.0% |
| X3-Llama8B/OBQA/Text | certify | 0.1589 | 0.874 / 0.865 | 2100 / 1366 | 0.9745 | 0.55, 0.499 | 0.9410 | 0.8188 | 0.0% |
| X3-Llama8B/ARC/Text | certify | 0.0893 | 0.880 / 0.914 | 670 / 448 | 0.7195 | 0.65, 0.637 | 0.9260 | 0.8520 | 0.0% |

Agreement with the observed outcome: **28/28** (dev AUROC, main run); 28/28 (cal AUROC, sensitivity). Disagreements: none. AUROC at which P(certify) = .5: range 0.6294–0.9965 over the 28 settings (28 with a value); .80 falls in this range.
Writing rule: agreement 28 >= 24, so Sec 5 uses the first wording ('a binormal score with each setting's disagreement rate and AUROC reproduces 28 of 28 outcomes; ...'), with no exceptions to name.

### (c) Grid for a figure (`results/E17_5c_grid.csv`, `results/E17_5c_contour.csv`)

AUROC at which P(certify) = .5, linear interpolation between grid AUROCs, per (N_fit, N_cal) and prevalence:

| prevalence | (670, 448) | (2100, 1366) | (3000, 6000) |
|---|---|---|---|
| 0.02 | <= 0.6 | <= 0.6 | <= 0.6 |
| 0.03 | 0.6696 | <= 0.6 | <= 0.6 |
| 0.05 | 0.7771 | 0.6519 | <= 0.6 |
| 0.075 | 0.8299 | 0.7233 | 0.6398 |
| 0.1 | 0.8635 | 0.7647 | 0.6806 |
| 0.15 | 0.9024 | 0.8132 | 0.7330 |
| 0.2 | 0.9219 | 0.8421 | 0.7708 |
| 0.3 | 0.9533 | 0.8818 | 0.8195 |
| 0.4 | 0.9689 | 0.9158 | 0.8533 |
| 0.5 | > 0.98 | 0.9317 | 0.8758 |
| 0.6 | > 0.98 | 0.9585 | 0.9106 |

## E17-6. MMLU-Pro per category (`results/E17_6_mmlu_categories.csv`)

| path | category | N_cal | cal disagreement | q (delta = .001) | dev coverage | dev k/n [CP] | q (delta = .001/14) |
|---|---|---|---|---|---|---|---|
| Text | biology | 327 | 33/327 = 10.1% | 0.6 | 64.6% | 1/93 = 1.08% [0.03%, 5.85%] | fallback |
| Text | business | 401 | 91/401 = 22.7% | fallback | - | - | fallback |
| Text | chemistry | 583 | 161/583 = 27.6% | fallback | - | - | fallback |
| Text | computer science | 211 | 48/211 = 22.7% | fallback | - | - | fallback |
| Text | economics | 432 | 63/432 = 14.6% | 0.45 | 51.1% | 0/97 = 0.00% [0.00%, 3.73%] | fallback |
| Text | engineering | 499 | 101/499 = 20.2% | 0.35 | 46.4% | 5/102 = 4.90% [1.61%, 11.07%] | fallback |
| Text | health | 352 | 66/352 = 18.8% | fallback | - | - | fallback |
| Text | history | 197 | 24/197 = 12.2% | fallback | - | - | fallback |
| Text | law | 495 | 128/495 = 25.9% | fallback | - | - | fallback |
| Text | math | 693 | 202/693 = 29.1% | fallback | - | - | fallback |
| Text | other | 476 | 115/476 = 24.2% | fallback | - | - | fallback |
| Text | philosophy | 257 | 48/257 = 18.7% | fallback | - | - | fallback |
| Text | physics | 667 | 157/667 = 23.5% | fallback | - | - | fallback |
| Text | psychology | 410 | 58/410 = 14.1% | fallback | - | - | fallback |
| C2C | biology | 327 | 48/327 = 14.7% | fallback | - | - | fallback |
| C2C | business | 401 | 155/401 = 38.7% | fallback | - | - | fallback |
| C2C | chemistry | 583 | 279/583 = 47.9% | fallback | - | - | fallback |
| C2C | computer science | 211 | 55/211 = 26.1% | fallback | - | - | fallback |
| C2C | economics | 432 | 60/432 = 13.9% | fallback | - | - | fallback |
| C2C | engineering | 499 | 207/499 = 41.5% | fallback | - | - | fallback |
| C2C | health | 352 | 67/352 = 19.0% | 0.45 | 47.7% | 0/74 = 0.00% [0.00%, 4.86%] | fallback |
| C2C | history | 197 | 28/197 = 14.2% | fallback | - | - | fallback |
| C2C | law | 495 | 135/495 = 27.3% | fallback | - | - | fallback |
| C2C | math | 693 | 252/693 = 36.4% | fallback | - | - | fallback |
| C2C | other | 476 | 89/476 = 18.7% | 0.5 | 48.1% | 2/101 = 1.98% [0.24%, 6.97%] | fallback |
| C2C | philosophy | 257 | 61/257 = 23.7% | fallback | - | - | fallback |
| C2C | physics | 667 | 272/667 = 40.8% | fallback | - | - | fallback |
| C2C | psychology | 410 | 40/410 = 9.8% | 0.65 | 65.2% | 1/118 = 0.85% [0.02%, 4.63%] | 0.6 |

- Text: 3/14 categories certify at delta = .001 per candidate; 0/14 with delta = .001/14.

- C2C: 3/14 categories certify at delta = .001 per candidate; 1/14 with delta = .001/14.

Writing rule: App K, one sentence with both counts; nothing in the main text.

