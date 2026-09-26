# E16 results (P2_R7_E16_20260921T184114Z)

PREREG.md sha256 17ca47138a351a80ac8d5282dacb39109330d433bf31b4d390cdfd384b25c02a (18:44:07Z); first E16 model output 18:58:58Z (Job A 7643015).

## E16-1 / E16-2: frozen policies out of sample (results/analysis_oos/OOS_RESULTS.json, oos_results.csv)
Seal 2026-09-21T19:11:41.638778+00:00 -> answer key first accessed 2026-09-21T19:11:44.049015+00:00 (DEVIATIONS D4).

| policy | N | omitted n (coverage; dev) | k | k/n [CP95] | p | always-omit (test) vs cal / dev disagreement | acc R / ref / policy | Delta acc [boot95] | INVALID R/ref | u==0 (all/omitted) | official k/n [CP95] (A-D) | branch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Llama-3.1-8B OBQA/Text (q=.60) on 744 held-out OBQA | 744 | 440 (0.5914; dev 438/742 = 0.5903) | 3 | 0.0068 [0.0014, 0.0198] | 3.71e-07 | 89/744 = 0.1196 vs 217/1366 = 0.1589 / 86/742 = 0.1159 | 0.8038 / 0.8306 / 0.8266 | -0.0040 [-0.0094, +0.0000] | 0/0 | 0/0 | 3/440 = 0.0068 [0.0014, 0.0198] (744 items) | passes (CP upper < 5%); p<=.001 True; p<=.025 True |
| Llama-3.1-8B ARC/Text (q=.70) on 1,172 ARC test | 1172 | 794 (0.6775; dev 206/299 = 0.6890) | 15 | 0.0189 [0.0106, 0.0310] | 4.4e-06 | 126/1172 = 0.1075 vs 40/448 = 0.0893 / 37/299 = 0.1237 | 0.8131 / 0.8473 / 0.8456 | -0.0017 [-0.0077, +0.0043] | 0/0 | 0/0 | 15/792 = 0.0189 [0.0106, 0.0310] (1169 items) | passes (CP upper < 5%); p<=.001 True; p<=.025 True |
| medium ARC/C2C (q=.60) on 1,172 ARC test | 1172 | 733 (0.6254; dev 189/299 = 0.6321) | 15 | 0.0205 [0.0115, 0.0335] | 3.13e-05 | 174/1172 = 0.1485 vs 55/448 = 0.1228 / 48/299 = 0.1605 | 0.7594 / 0.7218 / 0.7253 | +0.0034 [-0.0026, +0.0094] | 13/47 | 661/661 | 16/730 = 0.0219 [0.0126, 0.0353] (1169 items) | passes (CP upper < 5%); p<=.001 True; p<=.025 True |

## E16-5: strong-helper Text setting (results/analysis_e16_5/E16_5_RESULTS.json, ledger_40.csv; seal before gold in SEAL_RECEIPT.json)

| benchmark | cal dis. | dev dis. | dev AUROC | q | kappa | min p (q, k/n) | acc helper / R / Text / policy (dev) | G (pts) | retained | INVALID R/T (cal; dev) | resplit cert. | needed N_cal | pattern |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| obqa | 297/1366 = 0.2174 | 157/742 = 0.2116 | 0.7921 | fallback | 0.0 | 0.2583 (0.05, 26/601) | 0.8625 / 0.6604 / 0.7332 / 0.7332 | 7.28 | 1.0 | 14/0; 8/0 | 0.000 | {'min_p_q': 0.05, 'r': 0.04326123128119801, 'm': 9454, 'needed_N_cal': 21488} | consistent |
| arc | 55/448 = 0.1228 | 40/299 = 0.1338 | 0.8001 | fallback | 0.0 | 0.02625 (0.05, 6/256) | 0.8763 / 0.7258 / 0.7692 / 0.7692 | 4.35 | 1.0 | 3/1; 2/0 | 0.155 | {'min_p_q': 0.05, 'r': 0.0234375, 'm': 505, 'needed_N_cal': 884} | exception |

## E16-5 replay: not run (E16-5 falls back on both benchmarks).

## E16-3 probe numerics (results/analysis_e16_3/E16_3_RESULTS.json, receiver_benchmark.csv, settings_a.csv, settings_b.csv)
Job B 7643022 (exit 0, all tiers computed; MANIFEST_jobB.sha256 verified 20/20). bf16 re-prefill reproduces the stored u bitwise on every unit of every receiver x benchmark.

| receiver | bench | units | u==0 share | max exp(m) (u==0) | min exp(m) (u>0) | min gap (u==0) | m ties (units/values) | gap ties (units/values) | u32==0 share |
|---|---|---|---|---|---|---|---|---|---|
| qwen3_0_6b | arc | 1417 | 0 | - | 2.531e-07 | - | 2/1 | 1409/89 | 0 |
| qwen3_0_6b | mmlu_pro | 11641 | 0 | - | 9.988e-07 | - | 0/0 | 11537/461 | 0 |
| qwen3_0_6b | obqa | 4208 | 0 | - | 2.127e-07 | - | 103/51 | 4201/96 | 0 |
| qwen3_1_7b | arc | 1417 | 0.5709 | 9.466e-08 | 6.837e-08 | 16.75 | 50/25 | 1406/119 | 0.5702 |
| qwen3_1_7b | mmlu_pro | 11641 | 0.1179 | 9.988e-08 | 6.226e-08 | 16.75 | 11/5 | 11628/116 | 0.1185 |
| qwen3_1_7b | obqa | 4208 | 0.4461 | 9.803e-08 | 6.16e-08 | 16.75 | 306/147 | 4199/116 | 0.4484 |
| qwen3_8b | arc | 1417 | 0.7283 | 7.477e-08 | 6.038e-08 | 16.75 | 14/7 | 1392/147 | 0.7241 |
| qwen3_8b | mmlu_pro | 11641 | 0.2405 | 1.028e-07 | 6.455e-08 | 16.75 | 0/0 | 11625/162 | 0.2381 |
| qwen3_8b | obqa | 4208 | 0.486 | 1.079e-07 | 6.196e-08 | 16.75 | 116/58 | 4188/140 | 0.4819 |

(a) per setting: original q | q(m) | q(-gap) | dev coverage orig/m/-gap | changed/omitted m ; -gap | Jaccard m ; -gap

- small/OBQA/Text: fallback | fallback | fallback | 0.0000/0.0000/0.0000 | 0/0 [nan, nan] ; 0/0 [nan, nan] | None ; None
- small/OBQA/C2C: fallback | fallback | fallback | 0.0000/0.0000/0.0000 | 0/0 [nan, nan] ; 0/0 [nan, nan] | None ; None
- small/ARC/Text: fallback | fallback | fallback | 0.0000/0.0000/0.0000 | 0/0 [nan, nan] ; 0/0 [nan, nan] | None ; None
- small/ARC/C2C: fallback | fallback | fallback | 0.0000/0.0000/0.0000 | 0/0 [nan, nan] ; 0/0 [nan, nan] | None ; None
- medium/OBQA/Text: fallback | fallback | fallback | 0.0000/0.0000/0.0000 | 0/0 [nan, nan] ; 0/0 [nan, nan] | None ; None
- medium/OBQA/C2C: 0.55 | 0.55 | 0.5 | 0.5256/0.5243/0.4811 | 11/389 [0.0142, 0.0500] ; 7/357 [0.0079, 0.0400] | 0.9974358974358974 ; 0.9153846153846154
- medium/ARC/Text: fallback | fallback | fallback | 0.0000/0.0000/0.0000 | 0/0 [nan, nan] ; 0/0 [nan, nan] | None ; None
- medium/ARC/C2C: 0.6 | 0.6 | 0.6 | 0.6321/0.6254/0.6254 | 3/187 [0.0033, 0.0462] ; 3/187 [0.0033, 0.0462] | 0.9894179894179894 ; 0.9894179894179894
- large/OBQA/Text: 0.8 | 0.8 | 0.8 | 0.7709/0.7709/0.7749 | 19/572 [0.0201, 0.0514] ; 19/575 [0.0200, 0.0511] | 1.0 ; 0.9947826086956522
- large/OBQA/C2C: 0.8 | 0.8 | 0.8 | 0.7709/0.7709/0.7749 | 13/572 [0.0122, 0.0386] ; 13/575 [0.0121, 0.0384] | 1.0 ; 0.9947826086956522
- large/ARC/Text: 0.95 | 0.95 | 0.95 | 0.9498/0.9498/0.9498 | 9/284 [0.0146, 0.0593] ; 9/284 [0.0146, 0.0593] | 1.0 ; 1.0
- large/ARC/C2C: 0.9 | 0.9 | 0.9 | 0.9030/0.9030/0.9030 | 3/270 [0.0023, 0.0321] ; 3/270 [0.0023, 0.0321] | 1.0 ; 1.0
- large/MMLU-Pro/Text: 0.4 | 0.4 | 0.4 | 0.4048/0.4048/0.4123 | 40/1069 [0.0269, 0.0506] ; 41/1089 [0.0272, 0.0507] | 1.0 ; 0.9816345270890725
- large/MMLU-Pro/C2C: 0.4 | 0.4 | 0.4 | 0.4048/0.4048/0.4123 | 37/1069 [0.0245, 0.0474] ; 40/1089 [0.0264, 0.0497] | 1.0 ; 0.9816345270890725
- small/MMLU-Pro/Text: fallback | fallback | fallback | 0.0000/0.0000/0.0000 | 0/0 [nan, nan] ; 0/0 [nan, nan] | None ; None
- small/MMLU-Pro/C2C: fallback | fallback | fallback | 0.0000/0.0000/0.0000 | 0/0 [nan, nan] ; 0/0 [nan, nan] | None ; None
- medium/MMLU-Pro/Text: fallback | fallback | fallback | 0.0000/0.0000/0.0000 | 0/0 [nan, nan] ; 0/0 [nan, nan] | None ; None
- medium/MMLU-Pro/C2C: fallback | fallback | fallback | 0.0000/0.0000/0.0000 | 0/0 [nan, nan] ; 0/0 [nan, nan] | None ; None
- X1-Llama/OBQA/Text: fallback | fallback | fallback | 0.0000/0.0000/0.0000 | 0/0 [nan, nan] ; 0/0 [nan, nan] | None ; None
- X1-Llama/OBQA/C2C: fallback | fallback | fallback | 0.0000/0.0000/0.0000 | 0/0 [nan, nan] ; 0/0 [nan, nan] | None ; None
- X1-Llama/ARC/Text: fallback | fallback | fallback | 0.0000/0.0000/0.0000 | 0/0 [nan, nan] ; 0/0 [nan, nan] | None ; None
- X1-Llama/ARC/C2C: fallback | fallback | fallback | 0.0000/0.0000/0.0000 | 0/0 [nan, nan] ; 0/0 [nan, nan] | None ; None
- large/OBQA/Text+fact: 0.75 | 0.75 | 0.75 | 0.7224/0.7224/0.7237 | 13/536 [0.0130, 0.0411] ; 13/537 [0.0130, 0.0410] | 1.0 ; 0.9981378026070763

(b) certified policies under u32 (frozen tau): cal k/n p | accepted | dev coverage u32 vs orig | changed/omitted [CP] | Jaccard | q full fp32 | MATERIAL

- medium/OBQA/C2C (tau 1.3113e-06): 19/745 p=0.000592 | True | 0.5350 vs 0.5256 | 11/397 [0.0139, 0.0490] | 0.9724 | 0.55 | False
- medium/ARC/C2C (tau 3.57628e-07): 2/288 p=5.02e-05 | True | 0.6254 vs 0.6321 | 3/187 [0.0033, 0.0462] | 0.9894 | 0.6 | False
- large/OBQA/Text (tau 0.00117004): 19/1066 p=3.21e-08 | True | 0.7709 vs 0.7709 | 19/572 [0.0201, 0.0514] | 0.9896 | 0.8 | False
- large/OBQA/C2C (tau 0.00117004): 22/1066 p=6.31e-07 | True | 0.7709 vs 0.7709 | 13/572 [0.0122, 0.0386] | 0.9896 | 0.8 | False
- large/ARC/Text (tau 0.018007): 4/421 p=5.01e-06 | True | 0.9465 vs 0.9498 | 9/283 [0.0146, 0.0595] | 0.9965 | 0.95 | False
- large/ARC/C2C (tau 0.000709593): 7/405 p=0.000521 | True | 0.8997 vs 0.9030 | 3/269 [0.0023, 0.0322] | 0.9963 | 0.9 | False
- large/MMLU-Pro/Text (tau 3.83854e-05): 66/2349 p=8.99e-08 | True | 0.4014 vs 0.4048 | 40/1060 [0.0271, 0.0510] | 0.9768 | 0.4 | False
- large/MMLU-Pro/C2C (tau 3.83854e-05): 73/2349 p=4.48e-06 | True | 0.4014 vs 0.4048 | 36/1060 [0.0239, 0.0467] | 0.9768 | 0.4 | False
- large/OBQA/Text+fact (tau 0.000261188): 23/999 p=1.12e-05 | True | 0.7224 vs 0.7224 | 13/536 [0.0130, 0.0411] | 0.9963 | 0.75 | False
- medium/OBQA/C2C at q=.50 (tau 2.38419e-07): 10/673 p=1.13e-06 | True | 0.4852 vs 0.4784 | 7/360 [0.0079, 0.0397] | 0.9697 | None | None
- 14 fallback settings under the full fp32 procedure: 14/14 remain fallback; MATERIAL CHANGE in any setting: False

## E17-5 on the two E16-5 settings (results/analysis_e16_5/E17_5_on_E16_5*.csv/.json; E17 code imported unchanged)

- strong-helper/OBQA/Text (E16-5): N_fit 2100, N_cal 1366, prevalence 0.2174, AUROC dev 0.7921 / cal 0.7901; P(certify) dev 0.0400, cal 0.0365; AUROC at P=.5 0.8530; (a) max TPR/FPR 6.144 vs C 5.279 (max >= C: True); observed fallback
- strong-helper/ARC/Text (E16-5): N_fit 670, N_cal 448, prevalence 0.1228, AUROC dev 0.8001 / cal 0.8336; P(certify) dev 0.0485, cal 0.1445; AUROC at P=.5 0.8852; (a) max TPR/FPR 5.831 vs C 2.659 (max >= C: True); observed fallback

## E16-4 Llama-3.1-8B latency replay (results/e16_4/E16_4_RESULTS.json, e16_4_savings.csv; Job C 7643092; MANIFEST_jobC.sha256 17/17)
16-row check before the replay: PASS {'runtime_ok': 16, 'u_equal': 16, 'probe_ids_equal': 16, 'R_equal': 16, 'T_equal': 16, 'live_helper_message_equals_stored': 16, 'all_equal': 16}. Replay: 512 requests (2 panels x 128 x 2 arms), E3 protocol, D7 rotation; first request after model load obqa|9-782|policy_T = 1346.5 ms.

| policy | omitted | (a) mean [95%] ms | (b) mean [95%] ms | class (b) | median (a)/(b) | share slower (a)/(b) | first requests: fixed / policy (ms) | frozen identity |
|---|---|---|---|---|---|---|---|---|
| Llama-3.1-8B OBQA/Text | 76/128 | 318.6 [261.1, 372.1] | 325.5 [269.3, 376.4] (N 127, excl. 9-782) | positive | 479.8 / 479.9 | 0.391 / 0.386 | 785.0 (#2) / 1346.5 (#1) | 128/128 |
| Llama-3.1-8B ARC/Text | 88/128 | 418.9 [361.7, 473.7] | 417.6 [359.8, 473.4] (N 127, excl. Mercury_7207358) | positive | 534.5 / 525.7 | 0.266 / 0.268 | 790.6 (#258) / 203.0 (#257) | 128/128 |
