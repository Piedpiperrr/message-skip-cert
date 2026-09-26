# E13 (Round 5) — CPU re-analysis of saved records

Stage: `P2_R5_E13_20260921T031606Z`. POST-HOC re-analysis; changes no primary decision. No model run, no GPU, no job
submitted. Nothing outside this folder was created or modified: no input file is newer than the preregistration, and
the set of `__pycache__` directories is unchanged (`logs/pycache_{before,after}.txt`).

| | |
|---|---|
| Preregistration | `PREREG_E13.md`, SHA-256 `2cc25a61f8ba57a2e129319e9aee1dad3c3df93321377130e38da109b92d3b3e`, recorded 2026-09-21T03:16:48Z (`PREREG_E13.sha256`) |
| Deviations | `DEVIATIONS.md` (4 deviations from the literal text, plus the choices made where the preregistration was silent) |
| Status | all 12 items done; every reproduction check passes (`results/item*_repro_checks.csv`) |

Directory names: every name in the request was correct. Other folders used: E9b/E9c = `P2_R3_E9BC_20260920T061042Z`;
original ClusterB replays = `P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z` (large), `P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z`,
`P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z`; sealed ARC = `P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z`; Appendix F
component panels = `P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z`; E7 and E6-replay records = `P2_R2_E7_20260919T231531Z`.

## Item 1 — best-fixed headroom of the rate-matched null

Reproduction: all pass. The per-draw null gains reproduce the E9-a means exactly (28 of 28), and the gain-over-R
bootstrap array is identical to `e9a_bootstrap_ratios.npy`. Joint ratios .664 … .970, median .761 [.676, .885]; real
gains 213/94/103/31/53/12/276; real best-fixed headroom 132/49/70/27/25/6/239.

Joint design (H in questions; H_null over the same 1,000 draws; best-fixed ratio with the E9-a question bootstrap):

| population | H_real | mean H_null [2.5, 97.5] | best-fixed ratio [95%] | gain-over-R ratio [95%] |
|---|---|---|---|---|
| small/OBQA | 132 | 138.09 [128, 148] | 1.046 [0.883, 1.211] | 0.664 [0.573, 0.759] |
| small/ARC | 49 | 56.31 [49, 64] | 1.149 [0.922, 1.490] | 0.737 [0.605, 0.893] |
| medium/OBQA | 70 | 90.87 [83, 97] | 1.298 [0.994, 1.587] | 0.903 [0.769, 1.048] |
| medium/ARC (under-matched) | 27 | 25.64 [22, 28] | 0.950 [0.630, 1.405] | 0.845 [0.567, 1.144] |
| large/OBQA | 25 | 40.09 [34, 46] | 1.603 [1.071, 2.498] | 0.761 [0.613, 0.935] |
| large/ARC | 6 | 7.60 [6, 9] | 1.267 [0.513, 3.764] | 0.641 [0.369, 0.900] |
| large/MMLU-Pro | 239 | 260.79 [244, 273] | 1.091 [0.956, 1.217] | 0.970 [0.877, 1.079] |
| **median of 7** | | | **1.149 [1.000, 1.316]** | 0.761 [0.676, 0.885] |

Medians of the best-fixed ratio for the other designs: independent 1.111 [0.954, 1.251]; per-reference Text 1.235
[0.964, 1.357]; per-reference C2C 1.306 [1.117, 1.642]. Full table: `results/item1_best_fixed_headroom.csv`,
`results/item1_bootstrap_intervals.csv`.

Decomposition (joint; correct counts; best-fixed null accuracy minus correct(R), mean over draws, and the share of
draws in which R itself is the best fixed action):

| population | R | Text − R | C2C − R | mean N1 − R | mean N2 − R | best-fixed null − R | draws with R best |
|---|---|---|---|---|---|---|---|
| small/OBQA | 285 | +61 | +81 | −5.18 | −5.21 | 3.36 | .536 |
| small/ARC | 110 | +16 | +45 | +8.91 | +10.18 | 12.92 | .005 |
| medium/OBQA | 490 | +33 | −4 | −5.25 | −3.79 | 2.10 | .531 |
| medium/ARC | 217 | +4 | −15 | −4.15 | −3.64 | 0.57 | .759 |
| large/OBQA | 617 | +28 | −19 | −10.40 | −8.74 | 0.23 | .926 |
| large/ARC | 268 | +6 | −2 | −4.34 | −3.61 | 0.10 | .949 |
| large/MMLU-Pro | 1282 | +37 | −49 | −2.04 | −3.01 | 6.92 | .295 |

Reading under the preregistered rules. The joint best-fixed median is 1.149, which is at least .5 and at least 1.
The abstract therefore keeps "oracle headroom is weak evidence for useful communication content" with the median.
The text says the null produces at least as much headroom as the real paths (median ratio 1.149) and explains the
mechanism in one sentence. The real paths raise the best fixed action (Text − R = +4 to +61 questions). The
content-free changes do not: the mean best-fixed null accuracy is 0.1–12.9 questions above R, and R is itself the
best fixed action in up to 95% of draws. The gain-over-R ratio (.761) moves to Appendix J as the secondary quantity.
Six of the seven per-population best-fixed ratios are above 1; medium/ARC is .950 and carries the under-matched flag.

## Item 2 — joint null stratified by whether R is correct

`results/item2_stratified_ratios.csv`, `item2_strata.csv`, `item2_bootstrap_intervals.csv`.

| population | best-fixed [95%] | gain over R [95%] | under-matched stratum (ratio is a lower bound) |
|---|---|---|---|
| small/OBQA | 0.787 [0.709, 0.873] | 0.729 [0.640, 0.826] | none |
| small/ARC | 0.725 [0.592, 0.873] | 0.754 [0.626, 0.904] | none |
| medium/OBQA | 0.996 [0.884, 1.124] | 0.938 [0.791, 1.083] | R incorrect (158 needed / 150 eligible) |
| medium/ARC | 0.939 [0.626, 1.126] | 0.849 [0.583, 1.058] | R correct (36 / 32) |
| large/OBQA | 1.084 [0.946, 1.280] | 0.877 [0.755, 1.005] | none |
| large/ARC | 0.967 [0.537, 1.500] | 0.750 [0.429, 1.084] | R incorrect (14 / 10) |
| large/MMLU-Pro | 1.023 [0.923, 1.108] | 0.956 [0.866, 1.058] | none |
| **median** | **0.967 [0.800, 1.040]** | **0.849 [0.733, 0.937]** | |

Stratified best-fixed median 0.967, not below .5, so the abstract is not changed by Item 2. Section 4.1 gives the
median in one sentence. Eligible counts per stratum are in `item2_strata.csv`.

## Item 3 — retained gain under omission

Reproduction: all pass. Development correct answers R/b/policy: 617/645/638, 268/274/270, 1282/1319/1321,
617/670/660. At alpha = .02: q = .65 (6/460), q = .80 (0/233), fallback. Held-out: 86.02/86.96 and 89.65/91.13;
595/12 and 558/16.

At alpha = .05 (G, P in accuracy points; paired bootstrap, 2,000, seed 0; corrections total/lost/kept):

| setting | split | G [95%] | P [95%] | retention [95%] | share G ≤ 0 | corrections |
|---|---|---|---|---|---|---|
| large/OBQA/Text | dev | 3.77 [1.62, 5.93] | 2.83 [1.08, 4.58] | 0.750 [0.467, 1.067] | 0 | 46/13/33 |
| large/OBQA/Text | held-out | 3.90 [1.88, 5.78] | 2.96 [1.21, 4.57] | 0.759 [0.500, 0.958] | 0 | 41/9/32 |
| large/ARC/Text | dev | 2.01 [−0.33, 4.68] | 0.67 [−1.00, 2.34] | **0.333 [−1.000, 1.400]** | .068 | 10/6/4 |
| large/MMLU-Pro/Text | dev | 1.40 [0.19, 2.58] | 1.48 [0.23, 2.61] | 1.054 [0.717, 1.858] | .015 | 166/12/154 |
| large/OBQA/Text+fact | dev | 7.14 [4.85, 9.43] | 5.80 [3.77, 7.82] | 0.811 [0.686, 0.927] | 0 | 62/11/51 |
| large/OBQA/Text+fact | held-out | 8.06 [5.91, 10.22] | 6.59 [4.57, 8.47] | 0.817 [0.706, 0.933] | 0 | 67/13/54 |

Sealed ARC: R was not run on routed questions, so retention is not computable there; not approximated. The large/ARC/Text
retention at alpha = .05 is below .5, so the text must say so. Retention range at alpha = .05: 0.333 to 1.054
(development), 0.759 to 0.817 (held-out).

Tolerance sweep (development; held-out for the OBQA settings). Full columns, including calibration n/k/p:
`results/item3_alpha_sweep.csv`.

| setting | alpha | q | κ | changed/omitted | κα (pts) | retention [95%] | held-out ch/om, acc, retention |
|---|---|---|---|---|---|---|---|
| OBQA/Text (G 3.77) | .01 | fallback | 0 | 0/0 | 0.00 | 1 | 0/0, 86.96, 1 |
| | .02 | .65 | .620 | 6/460 | 1.24 | 1.000 [0.833, 1.278] | 3/485, 86.83, 0.966 [0.846, 1.095] |
| | .03 | .75 | .722 | 15/536 | 2.17 | 0.893 [0.650, 1.250] | 7/558, 86.69, 0.931 [0.765, 1.120] |
| | .04 | .80 | .771 | 19/572 | 3.08 | 0.750 [0.467, 1.067] | 12/595, 86.02, 0.759 [0.500, 0.958] |
| | .05 | .80 | .771 | 19/572 | 3.85 | 0.750 [0.467, 1.067] | 12/595, 86.02, 0.759 [0.500, 0.958] |
| ARC/Text (G 2.01) | .01 | fallback | 0 | 0/0 | 0.00 | 1 | |
| | .02 | .80 | .779 | 0/233 | 1.56 | 1.000 [1.000, 1.000] | |
| | .03 | .85 | .849 | 1/254 | 2.55 | 0.833 [0.000, 1.000] | |
| | .04 | .95 | .950 | 9/284 | 3.80 | 0.333 [−1.000, 1.400] | |
| | .05 | .95 | .950 | 9/284 | 4.75 | 0.333 [−1.000, 1.400] | |
| MMLU-Pro/Text (G 1.40) | .01, .02 | fallback | 0 | 0/0 | 0.00 | 1 | |
| | .03 | .30 | .307 | 16/812 | 0.92 | 0.973 [0.667, 1.333] | |
| | .04 | .35 | .360 | 31/952 | 1.44 | 1.054 [0.749, 1.667] | |
| | .05 | .40 | .405 | 40/1069 | 2.02 | 1.054 [0.717, 1.858] | |
| OBQA/Text+fact (G 7.14) | .01 | fallback | 0 | 0/0 | 0.00 | 1 | 0/0, 91.13, 1 |
| | .02 | .55 | .536 | 1/398 | 1.07 | 0.981 [0.935, 1.000] | 2/404, 90.86, 0.967 [0.914, 1.000] |
| | .03 | .65 | .620 | 3/460 | 1.86 | 0.943 [0.878, 1.000] | 7/485, 90.46, 0.917 [0.831, 1.000] |
| | .04 | .70 | .664 | 7/493 | 2.66 | 0.887 [0.794, 0.964] | 10/522, 90.32, 0.900 [0.808, 1.000] |
| | .05 | .75 | .722 | 13/536 | 3.61 | 0.811 [0.686, 0.927] | 16/558, 89.65, 0.817 [0.706, 0.933] |

Largest alpha on the grid with κα < G, and the saving at that alpha. The saving is recomposed from the per-request
timings of existing replays, version (b); it is not a new replay. `results/item3_recomposed_savings.csv`.

| setting | alpha | q | κ | retention | recomposed saving, ms [95%] — ClusterB original; ClusterA E3 R1, R2, R3 |
|---|---|---|---|---|---|
| large/OBQA/Text | .04 | .80 (same policy as alpha = .05) | .771 | 0.750 | 532.9 [470.9, 594.6]; 420.3 [371.7, 469.4], 429.5 [379.0, 479.2], 422.5 [373.0, 471.3] |
| large/ARC/Text | .02 | .80 | .779 | 1.000 | 587.3 [520.1, 651.6]; 469.3 [414.9, 520.5], 479.5 [424.2, 532.4], 471.2 [416.9, 522.2] |
| large/MMLU-Pro/Text | .03 | .30 | .307 | 0.973 | 247.0 [163.2, 332.0]; 197.1 [127.7, 267.2], 199.3 [130.7, 268.9], 199.8 [130.6, 269.5] |
| large/OBQA/Text+fact | .05 | .75 | .722 | 0.811 | 342.7 [299.8, 385.7] (E6 replay, the only replay of this setting) |

## Item 4 — can a small paired sample predict certification?

Reproduction: dev AUROC .873, .952, .910, .742, .790, .821, all pass. AUROC function: `sklearn.metrics.roc_auc_score`.
Its trapezoidal ROC treats tied scores as one threshold, which equals Mann–Whitney with tied pairs credited ½. No
sample had "no agreement"; 2 draws at n = 100 had "no disagreement" (large/ARC/C2C).

| n | overall mean match | settings ≥ .8 | deployed (9): mean, ≥ .8 | fallback (17): mean, ≥ .8 | range over settings |
|---|---|---|---|---|---|
| 100 | .880 | 21/26 | .929, 8/9 | .854, 13/17 | .280–1.000 |
| 200 | **.911** | 21/26 | .950, 8/9 | .890, 13/17 | .145–1.000 |
| 400 | .924 | 23/26 | .967, 8/9 | .902, 15/17 | .020–1.000 |

Settings that miss most at n = 200: medium/ARC/Text .145 (fallback; median sample AUROC .829, above the dev AUROC
.742), medium/OBQA/Text .530 (fallback; .797), large/MMLU-Pro/Text .665 (deployed; .814), X2-OLMo/OBQA .785
(fallback). Without the Text+fact row, which was sampled from development and is flagged: .907, 20 of 25. Per-setting
table, including the sample disagreement rate (median, IQR): `results/item4_per_setting.csv`.

Reading: the n = 200 match share is .911, not below .80. Section 5 reports .911 (range .145–1.000) in place of
"say in advance", and says that the .80 cut was read off the same settings' development sets.

File times. E8: the earliest files holding a certification decision, a p-value or a development AUROC for the four
settings are `analysis/calibration/80_test_ledger.csv`, `80_test_ledger.json` and
`analysis/deployments/deployment_configs.json`, all modified **2026-09-20T19:10:30Z**. Every earlier keyword match is
code, protocol text or counts. E10: `analysis/SEALED_CAL_TESTS.jsonl`, **2026-09-21T00:11:26Z**.

## Item 5 — OLMo recertification with the probe's argmax (separate post-hoc family)

Reproduction: original dev disagreement 172/742, 67/299, 1112/2641, and all three original tests fall back. All pass.

| setting | argmax = native R on cal | result | smallest-p candidate (q, n, k, p) | dev coverage | dev AUROC (new label) | INVALID-reference share of dev disagreements |
|---|---|---|---|---|---|---|
| OLMo/OBQA | .952 | fallback | .15, 191, 13, .901 | 0 (0/0) | .808 | .158 (26/165) |
| OLMo/ARC | .902 | fallback | .05, 19, 0, .377 | 0 | .765 | .292 (19/65) |
| OLMo/MMLU-Pro | .811 | fallback | .05, 241, 34, 1.000 | 0 | .653 | .312 (363/1165) |
| Llama/OBQA/Text, C2C | .949 | fallback, fallback | .10, 142, 2, .025; .05, 65, 11, 1.000 | 0 | .701, .627 | .109, .118 |
| Llama/ARC/Text, C2C | .877 | fallback, fallback | .10, 33, 1, .504; .10, 33, 2, .773 | 0 | .667, .612 | .157, .097 |

No OLMo setting certifies. Under the rule, Section 4.3 says the deployable argmax rule also certifies no OLMo setting,
and the sentence "We read this as evidence about answer format, not about model families" is removed.
`results/item5_argmax_recert.csv`.

## Item 6 — what the probe cost consists of

Reproduction: sealed ARC 42.55 / 40.51 ms; MMLU-Pro panel 48.4 / 46.1 ms; all pass.

Appendix F component panels (128 development-panel questions; mean ms). Tokenization covers prefix construction. The
transfer timer ends with a synchronize. Prefill+projection is one timer covering full prefill and the last-position
projection; its GPU-event part is in parentheses. Synchronization has no separate timer.

| panel | tokenization | transfer | prefill+projection (GPU) | label probs | score | selector | sum | prefill share |
|---|---|---|---|---|---|---|---|---|
| small/OBQA | 0.868 | 0.127 | 31.248 (31.131) | 0.556 | 0.079 | 0.001 | 32.879 | .950 |
| small/ARC | 0.930 | 0.125 | 31.170 (31.057) | 0.546 | 0.079 | 0.000 | 32.849 | .949 |
| large/OBQA | 0.837 | 0.115 | 41.794 (41.729) | 0.545 | 0.076 | 0.001 | 43.366 | .964 |
| large/ARC | 0.876 | 0.125 | 41.445 (41.330) | 0.542 | 0.078 | 0.001 | 43.067 | .962 |
| medium/OBQA, medium/ARC, large/MMLU-Pro | components not recorded | | | | | | 33.10, 33.20, 46.27 | |

End-to-end mean probe + selector (policy requests, `results/item6_e2e_probe_cost.csv`): ClusterB large 42.1–57.6 ms,
MMLU-Pro 48.4/46.1, medium 36.7/33.5, sealed ARC 42.55/40.51. ClusterA E3 large 32.2–57.0 (the 57.0 and 53.0 OBQA/Text
means include first-request outliers; medians 32.3–33.1), MMLU-Pro 40.8–44.3, medium 25.8–26.9; E7 ORIGINAL 26.3–41.8;
E6 replay 32.1. Where recorded, prefill+projection is 91–97% of the end-to-end probe cost.

E7 REUSE. It keeps the probe's KV cache and continues the receiver-only answer from it, cropped to len(R) − 1. It
therefore saves the receiver's prefill of the R prompt except its final token (E7 freeze §2.1). Measured on omitted
questions, the action part is shorter by 0.1–1.7 ms (large OBQA/ARC), 5.9–6.3 ms (MMLU-Pro) and −0.4–0.8 ms
(medium). The whole request changes by −1.3 to +6.3 ms, because keeping the cache adds up to 1.4 ms to the probe.
Receiver-only request split into prefill and decoding: **not recorded** in the E7 records, which keep one wall
interval for action + decode + parse, plus a GPU-event sum. `results/item6_e7_reuse.csv`.

## Item 7 — re-split stability

All 25 settings with fit and calibration outputs already have 200-seed records (E5-b: 14 main + 7 cross-family; E8: 4).
The deploy shares recounted from the per-seed files equal the recorded ones (25 of 25). Deploy share: medium/OBQA/C2C
1.00, medium/ARC/C2C .96, large OBQA/ARC Text and C2C and large MMLU-Pro Text and C2C 1.00 each; all 17 fallback
settings .00. No setting was added in E13. Without fit-split reference outputs: large/OBQA/Text+fact, and E10
GSM8K/Text (its fit split has receiver-only outputs only). `results/item7_resplit_all.csv`.

## Item 8 — AUROC tie handling

Function per source (`results/item8_auroc_inventory.csv`):
- `sklearn.metrics.roc_auc_score`: the 14 main settings, the 4 E8 settings and the 7 cross-family settings.
- Hand-written mid-rank Mann–Whitney: E6 Text+fact, E10 GSM8K, E9c s_G.

Both give tied pairs credit ½. Explicit pairwise Mann–Whitney vs the paper's value:
- large/ARC/Text: 0.951878 vs 0.951878 (0.05% of positive–negative pairs tied).
- medium/ARC/C2C: 0.909736 vs 0.909736 (1.57% tied).

Across all 26 settings the largest difference is 1.1e-16.

## Item 9 — calibration cost payback

Means from the ClusterA E3 repeats, version (b). W = C / mean saving per query. `results/item9_payback.csv`.

| policy | probe | R request | ref request | saving/query | W shadow | W standalone |
|---|---|---|---|---|---|---|
| large/OBQA/Text | 32.69 | 205.9 | 808.2 | 424.3 | 930 | 3,532 |
| large/OBQA/C2C | 32.77 | 204.8 | 283.9 | 28.2 | 13,965 | 27,733 |
| large/ARC/Text | 32.57 | 215.1 | 869.5 | 577.3 | 230 | 905 |
| large/ARC/C2C | 32.54 | 215.6 | 349.3 | 91.7 | 1,449 | 3,156 |
| medium/OBQA/C2C | 26.20 | 165.0 | 305.8 | 47.6 | 6,637 | 15,406 |
| medium/ARC/C2C | 26.14 | 184.3 | 355.1 | 79.5 | 1,406 | 3,408 |
| large/MMLU-Pro/Text | 41.91 | 216.7 | 1070.1 | 261.5 | 6,415 | 30,969 |
| large/MMLU-Pro/C2C | 42.02 | 216.7 | 278.8 | 22.0 (full 2,641 replay) | 76,205 | 152,171 |

## Item 10 — earlier parser D1 vs final parser V2

Both parsers were run on 273,819 saved raw outputs (`results/item10_scope.csv`). The re-run V2 label equals the
stored label on all 273,819. The two parsers disagree on **48** outputs, and in every case D1 returns INVALID while
V2 returns a letter.

- **By split:** fit 17, calibration 26, development 4, P2_10 train panel 1. Held-out, sealed ARC, all replays, E4 and
  E1: 0.
- **By setting:** E8 small MMLU-Pro 41 (R 13, Text 1, C2C 27) and E8 medium MMLU-Pro C2C 2; small-pair C2C on
  OBQA/ARC fit 4 and on the P2_10 train panel 1.
- **Calibration:** identical on all 59,164 calibration outputs outside E8; different on 26 of 37,176 E8 calibration
  outputs.
- **Kinds:** 24 outputs enumerate every option label and then give one answer ("The correct answer is A/B/C/D. The
  correct answer is A."); 20 use an embedded selection ("The correct answer to this question is D."); 4 put a
  declaration after an explanation.
- **Answer-change labels:** 40 differ between D1 and V2. E8 small MMLU-Pro: Text fit 4, Text cal 7, C2C fit 7, C2C
  cal 13, C2C dev 4; E8 medium C2C cal 1. Small OBQA/ARC C2C: fit 3, P2_10 train panel 1. None is in the calibration
  or development split of the 14 main, cross-family or Text+fact settings (`results/item10_label_changes.csv`).

Rule differences, D1 → V2 (sources diffed):
1. V2 adds embedded-selection, choice-verb ("I choose X") and reverse ("option X is correct") patterns.
2. V2 disregards an earlier enumeration of exactly all labels when later single selections agree.
3. V2 drops formula, unit, article and conditional cases as non-selections; D1 marked them as issues, giving INVALID.
4. V2 ignores explanation continuations after "answer is" and separates negated declarations.
5. V2 starts a new resolution scope at the last final/correction selection; D1 resolved only when the very last event
   was one.
6. V2 adds more hedge words (unless, assuming, suppose, hypothetically) and applies them to the marker itself.
7. V2 normalises curly quotes, requires a leading label at position 0, and adds a refusal rule.
8. V2 returns illegal_label when any selected letter falls outside the displayed set.

Wording for Appendix C (ii): "identical on every calibration output of the 14 main, 7 cross-family and Text+fact
settings (59,164); they differ on 48 of 273,819 saved outputs elsewhere (43 in the E8 small/medium MMLU-Pro settings,
26 of them calibration; 5 small-pair C2C fit/panel outputs), all of the kind 'D1 INVALID, V2 a letter'".

## Item 11 — prompts and parser rules

Written to `PROMPTS_AND_PARSER.md`, using OBQA fit question 14-1371 and MMLU-Pro fit question test:3284 with the large
pair. It holds the helper Text instruction, the receiver's Text-reading prompt, the receiver-only prompt, the probe
input and the Text+fact addition (OBQA only), each rendered by the model's chat template, plus the final parser's
rules and regexes.

All 13 rendering checks pass: equality with the saved E6 helper messages; the saved token counts (111/258/132; 124/247
for Text+fact); the saved probe ids; and, for MMLU-Pro, exact equality with the decoded saved native input ids. The
anonymity scan passes: no user, path, project, allocation or machine string (`results/item11_checks.csv`).

## Item 12 — GSM8K other scores

**Not stored.** The E10 development-split records hold only the scalar `s2`, `s3`, `u` and the log-probabilities of
the extracted answer tokens (`rescore.answer_token_logprobs`). Per-token log-probabilities of the whole generation
(`gen_logprobs`) exist only for the 16 smoke rows. Stopped as preregistered.

## Follow-ups added after the preregistration hash (counting only; see DEVIATIONS.md §C)

### Item 13 — settings covered by the E9c helper-aware analysis

`P2_R3_E9BC_20260920T061042Z/analysis/E9C_RESULTS.json` has 20 rows but only 19 distinct settings, because Text+fact
appears twice (`results/item13_e9c_settings.csv`):
- **14 main settings:** small, medium and large on OBQA and ARC, each with Text and C2C, plus large MMLU-Pro Text and C2C.
- **4 E8 settings:** small and medium MMLU-Pro, each with Text and C2C.
- **large/OBQA/Text+fact, twice.** The primary row uses the helper prefill *without* the fact, as the E9c freeze §3
  specifies (it is the large/OBQA prefill). The second row, "[with-fact prefill, descriptive]", uses the with-fact
  prefill.

Neither Text+fact row enters hypothesis H. In the extended results file H is computed over 9 pair × benchmark
populations (Text vs C2C). In the original 7-population file it is computed over 7.

### Item 14 — E8 "D1 differs on 0 to 27 development answers per setting" vs Item 10's 4 development differences

**Item 10 is right for the development split.** The E8 numbers are right as totals over all splits; the error is only
in calling them development counts.

- **Same D1 version, same comparison.** Both analyses use D1 SHA-256 `6619cafd…cfab` and compare the frozen V2 label
  with the D1 label output by output.
- **Different population.** E8's `analysis/development/D1_label_differences.csv` counts every E8 question of the pair
  across fit, calibration and development: N = 12,032 per pair and action, including non-representatives. The file
  sits in `development/`, and the E8 SUMMARY places its column "D1 differences (R/T/C)" in the development table.
- **Per action, not per setting.** E8 counts per action (R/T/C), so the shared R count appears in both the Text row
  and the C2C row of a pair.
- **Exact reconciliation.** Item 10's per-split counts sum to the E8 totals:
  - small R 13 = fit 6 + cal 7.
  - small Text 1 = cal 1.
  - small C2C 27 = fit 7 + cal 16 + dev 4.
  - medium R 0, medium Text 0.
  - medium C2C 2 = cal 2.
- **On the 2,641 development representatives, per setting (R + reference outputs):** small/MMLU-Pro/Text 0,
  small/MMLU-Pro/C2C 4 (all four are C2C outputs), medium/MMLU-Pro/Text 0, medium/MMLU-Pro/C2C 0. The correct
  wording is therefore "0 to 4 development answers per setting" (4 in total). The alternative is "0 to 27 answers per
  action over all 12,032 questions".
