# E8 — the MMLU-Pro column for the small and medium pairs

Stage: `$DATA_DIR/P2_R2_E8_20260920T012544Z`  
Protocol freeze: `PROTOCOL_FREEZE_E8.md`, SHA-256 `9a17d8a438a226aa556b699525f767ebf8217e682dca59a746891594dfee945e`, recorded 2026-09-20T01:38:41.395514+00:00 (before any new model output).  
Analysis completed: 2026-09-20T19:10:49.698963+00:00. Family: 4 settings x 20 candidates = **80 tests**, separate from every earlier family.

## 1. The four settings

| setting | dev disagree R vs ref | AUROC | q | dev coverage | changed/omitted | correct R / ref / policy | INVALID R / ref | re-split cert. rate | D1 differences (R/T/C) |
|---|---|---|---|---|---|---|---|---|---|
| small/MMLU-Pro/Text | 1235/2641 (46.76%) | 0.6438 | 0 (fallback) | 0.00% | 0/0 | 403 / 516 / 516 | 151 / 229 | 0.000 | 13/1/27 |
| small/MMLU-Pro/C2C | 1591/2641 (60.24%) | 0.6258 | 0 (fallback) | 0.00% | 0/0 | 403 / 462 / 462 | 151 / 420 | 0.000 | 13/1/27 |
| medium/MMLU-Pro/Text | 1128/2641 (42.71%) | 0.7166 | 0 (fallback) | 0.00% | 0/0 | 813 / 913 / 913 | 160 / 18 | 0.000 | 0/0/2 |
| medium/MMLU-Pro/C2C | 1410/2641 (53.39%) | 0.7652 | 0 (fallback) | 0.00% | 0/0 | 813 / 530 / 530 | 160 / 1124 | 0.000 | 0/0/2 |

Unit: the 2,641 development group representatives. Coverage = fraction of development questions the policy omits the reference call on (runs R instead); changed = of those, how many would have had a different answer. q = 0 means fallback (always run the reference), and then coverage and changed are 0 by construction.

## 2. Oracle headroom (development representatives)

| pair | acc R | acc Text | acc C2C | best fixed | oracle | gain over best fixed | gain over R |
|---|---|---|---|---|---|---|---|
| small | 15.26% | 19.54% | 17.49% | T 19.54% | 31.12% | 11.59% | 15.87% |
| medium | 30.78% | 34.57% | 20.07% | T 34.57% | 42.48% | 7.91% | 11.70% |

## 3. Calibration ledger — all 80 tests

Rule: on the 6,000 calibration representatives, at each of the 20 fit-quantile candidates (19 quantiles plus q=1), P[Bin(n, .05) <= k] <= .001; deploy the largest accepted q, otherwise fall back.

| setting | q | threshold | n | k | p | CP(.999) | accepted |
|---|---|---|---|---|---|---|---|
| small/MMLU-Pro/Text | 0.05 | 0.003398 | 280 | 102 | 1 | 0.4574 | False |
| small/MMLU-Pro/Text | 0.1 | 0.00703663 | 608 | 229 | 1 | 0.4393 | False |
| small/MMLU-Pro/Text | 0.15 | 0.0103211 | 868 | 307 | 1 | 0.4054 | False |
| small/MMLU-Pro/Text | 0.2 | 0.0141267 | 1166 | 411 | 1 | 0.3969 | False |
| small/MMLU-Pro/Text | 0.25 | 0.0183378 | 1459 | 514 | 1 | 0.3919 | False |
| small/MMLU-Pro/Text | 0.3 | 0.0222957 | 1703 | 607 | 1 | 0.3931 | False |
| small/MMLU-Pro/Text | 0.35 | 0.0275129 | 1972 | 707 | 1 | 0.3926 | False |
| small/MMLU-Pro/Text | 0.4 | 0.0339105 | 2256 | 811 | 1 | 0.3913 | False |
| small/MMLU-Pro/Text | 0.45 | 0.0417661 | 2564 | 916 | 1 | 0.387 | False |
| small/MMLU-Pro/Text | 0.5 | 0.0522282 | 2903 | 1044 | 1 | 0.3876 | False |
| small/MMLU-Pro/Text | 0.55 | 0.0647829 | 3243 | 1178 | 1 | 0.3898 | False |
| small/MMLU-Pro/Text | 0.6 | 0.0807204 | 3555 | 1326 | 1 | 0.3984 | False |
| small/MMLU-Pro/Text | 0.65 | 0.0989896 | 3841 | 1460 | 1 | 0.4046 | False |
| small/MMLU-Pro/Text | 0.7 | 0.124921 | 4141 | 1618 | 1 | 0.4144 | False |
| small/MMLU-Pro/Text | 0.75 | 0.15959 | 4465 | 1782 | 1 | 0.422 | False |
| small/MMLU-Pro/Text | 0.8 | 0.206652 | 4750 | 1952 | 1 | 0.4332 | False |
| small/MMLU-Pro/Text | 0.85 | 0.272227 | 5046 | 2122 | 1 | 0.4422 | False |
| small/MMLU-Pro/Text | 0.9 | 0.360915 | 5344 | 2323 | 1 | 0.4558 | False |
| small/MMLU-Pro/Text | 0.95 | 0.471546 | 5696 | 2570 | 1 | 0.4717 | False |
| small/MMLU-Pro/Text | 1 | Infinity | 6000 | 2805 | 1 | 0.4875 | False |
| small/MMLU-Pro/C2C | 0.05 | 0.003398 | 280 | 106 | 1 | 0.472 | False |
| small/MMLU-Pro/C2C | 0.1 | 0.00703663 | 608 | 268 | 1 | 0.5042 | False |
| small/MMLU-Pro/C2C | 0.15 | 0.0103211 | 868 | 397 | 1 | 0.5104 | False |
| small/MMLU-Pro/C2C | 0.2 | 0.0141267 | 1166 | 537 | 1 | 0.5062 | False |
| small/MMLU-Pro/C2C | 0.25 | 0.0183378 | 1459 | 685 | 1 | 0.5103 | False |
| small/MMLU-Pro/C2C | 0.3 | 0.0222957 | 1703 | 812 | 1 | 0.5145 | False |
| small/MMLU-Pro/C2C | 0.35 | 0.0275129 | 1972 | 945 | 1 | 0.5143 | False |
| small/MMLU-Pro/C2C | 0.4 | 0.0339105 | 2256 | 1078 | 1 | 0.5106 | False |
| small/MMLU-Pro/C2C | 0.45 | 0.0417661 | 2564 | 1247 | 1 | 0.5171 | False |
| small/MMLU-Pro/C2C | 0.5 | 0.0522282 | 2903 | 1427 | 1 | 0.5204 | False |
| small/MMLU-Pro/C2C | 0.55 | 0.0647829 | 3243 | 1615 | 1 | 0.5253 | False |
| small/MMLU-Pro/C2C | 0.6 | 0.0807204 | 3555 | 1798 | 1 | 0.5318 | False |
| small/MMLU-Pro/C2C | 0.65 | 0.0989896 | 3841 | 1980 | 1 | 0.5405 | False |
| small/MMLU-Pro/C2C | 0.7 | 0.124921 | 4141 | 2172 | 1 | 0.5486 | False |
| small/MMLU-Pro/C2C | 0.75 | 0.15959 | 4465 | 2394 | 1 | 0.5593 | False |
| small/MMLU-Pro/C2C | 0.8 | 0.206652 | 4750 | 2588 | 1 | 0.5672 | False |
| small/MMLU-Pro/C2C | 0.85 | 0.272227 | 5046 | 2795 | 1 | 0.5755 | False |
| small/MMLU-Pro/C2C | 0.9 | 0.360915 | 5344 | 3006 | 1 | 0.5835 | False |
| small/MMLU-Pro/C2C | 0.95 | 0.471546 | 5696 | 3257 | 1 | 0.5921 | False |
| small/MMLU-Pro/C2C | 1 | Infinity | 6000 | 3482 | 1 | 0.6 | False |
| medium/MMLU-Pro/Text | 0.05 | 0 | 690 | 64 | 1 | 0.1316 | False |
| medium/MMLU-Pro/Text | 0.1 | 0 | 690 | 64 | 1 | 0.1316 | False |
| medium/MMLU-Pro/Text | 0.15 | 3.57628e-07 | 883 | 92 | 1 | 0.1396 | False |
| medium/MMLU-Pro/Text | 0.2 | 3.69549e-06 | 1138 | 164 | 1 | 0.1788 | False |
| medium/MMLU-Pro/Text | 0.25 | 2.96235e-05 | 1440 | 248 | 1 | 0.2048 | False |
| medium/MMLU-Pro/Text | 0.3 | 0.000158489 | 1715 | 323 | 1 | 0.219 | False |
| medium/MMLU-Pro/Text | 0.35 | 0.000611484 | 2011 | 428 | 1 | 0.2422 | False |
| medium/MMLU-Pro/Text | 0.4 | 0.00247258 | 2361 | 538 | 1 | 0.2555 | False |
| medium/MMLU-Pro/Text | 0.45 | 0.00640786 | 2644 | 646 | 1 | 0.271 | False |
| medium/MMLU-Pro/Text | 0.5 | 0.0135667 | 2905 | 761 | 1 | 0.2879 | False |
| medium/MMLU-Pro/Text | 0.55 | 0.0249961 | 3198 | 879 | 1 | 0.2999 | False |
| medium/MMLU-Pro/Text | 0.6 | 0.0474259 | 3504 | 1031 | 1 | 0.3185 | False |
| medium/MMLU-Pro/Text | 0.65 | 0.0779886 | 3839 | 1208 | 1 | 0.3383 | False |
| medium/MMLU-Pro/Text | 0.7 | 0.121789 | 4135 | 1380 | 1 | 0.3568 | False |
| medium/MMLU-Pro/Text | 0.75 | 0.179952 | 4425 | 1541 | 1 | 0.3707 | False |
| medium/MMLU-Pro/Text | 0.8 | 0.245142 | 4756 | 1741 | 1 | 0.3879 | False |
| medium/MMLU-Pro/Text | 0.85 | 0.322728 | 5081 | 1946 | 1 | 0.4043 | False |
| medium/MMLU-Pro/Text | 0.9 | 0.398033 | 5374 | 2128 | 1 | 0.4168 | False |
| medium/MMLU-Pro/Text | 0.95 | 0.490857 | 5665 | 2325 | 1 | 0.4308 | False |
| medium/MMLU-Pro/Text | 1 | Infinity | 6000 | 2584 | 1 | 0.4506 | False |
| medium/MMLU-Pro/C2C | 0.05 | 0 | 690 | 29 | 0.1928 | 0.07109 | False |
| medium/MMLU-Pro/C2C | 0.1 | 0 | 690 | 29 | 0.1928 | 0.07109 | False |
| medium/MMLU-Pro/C2C | 0.15 | 3.57628e-07 | 883 | 62 | 0.9965 | 0.1007 | False |
| medium/MMLU-Pro/C2C | 0.2 | 3.69549e-06 | 1138 | 132 | 1 | 0.148 | False |
| medium/MMLU-Pro/C2C | 0.25 | 2.96235e-05 | 1440 | 245 | 1 | 0.2026 | False |
| medium/MMLU-Pro/C2C | 0.3 | 0.000158489 | 1715 | 360 | 1 | 0.2417 | False |
| medium/MMLU-Pro/C2C | 0.35 | 0.000611484 | 2011 | 510 | 1 | 0.2846 | False |
| medium/MMLU-Pro/C2C | 0.4 | 0.00247258 | 2361 | 713 | 1 | 0.3319 | False |
| medium/MMLU-Pro/C2C | 0.45 | 0.00640786 | 2644 | 874 | 1 | 0.3594 | False |
| medium/MMLU-Pro/C2C | 0.5 | 0.0135667 | 2905 | 1041 | 1 | 0.3863 | False |
| medium/MMLU-Pro/C2C | 0.55 | 0.0249961 | 3198 | 1225 | 1 | 0.41 | False |
| medium/MMLU-Pro/C2C | 0.6 | 0.0474259 | 3504 | 1433 | 1 | 0.4349 | False |
| medium/MMLU-Pro/C2C | 0.65 | 0.0779886 | 3839 | 1655 | 1 | 0.456 | False |
| medium/MMLU-Pro/C2C | 0.7 | 0.121789 | 4135 | 1857 | 1 | 0.4732 | False |
| medium/MMLU-Pro/C2C | 0.75 | 0.179952 | 4425 | 2067 | 1 | 0.4904 | False |
| medium/MMLU-Pro/C2C | 0.8 | 0.245142 | 4756 | 2303 | 1 | 0.5067 | False |
| medium/MMLU-Pro/C2C | 0.85 | 0.322728 | 5081 | 2539 | 1 | 0.5215 | False |
| medium/MMLU-Pro/C2C | 0.9 | 0.398033 | 5374 | 2770 | 1 | 0.5366 | False |
| medium/MMLU-Pro/C2C | 0.95 | 0.490857 | 5665 | 3003 | 1 | 0.5506 | False |
| medium/MMLU-Pro/C2C | 1 | Infinity | 6000 | 3267 | 1 | 0.5644 | False |

## 4. Re-split stability (200 re-drawn fit/calibration splits, E5-b rule)

| setting | original | certification rate | match rate | verdict | median q | median dev coverage % |
|---|---|---|---|---|---|---|
| small/MMLU-Pro/Text | fallback q=0 | 0.000 | 1.000 | stable |  |  |
| small/MMLU-Pro/C2C | fallback q=0 | 0.000 | 1.000 | stable |  |  |
| medium/MMLU-Pro/Text | fallback q=0 | 0.000 | 1.000 | stable |  |  |
| medium/MMLU-Pro/C2C | fallback q=0 | 0.000 | 1.000 | stable |  |  |

Seed 0 reproduces the frozen split: **True**.

## 5. Labels under the earlier parser D1

| pair | action | N | differences | rate | V2 INVALID | D1 INVALID | V2 valid / D1 invalid | D1 valid / V2 invalid | both valid, different |
|---|---|---|---|---|---|---|---|---|---|
| small | R | 12032 | 13 | 0.11% | 744 | 757 | 13 | 0 | 0 |
| small | T | 12032 | 1 | 0.01% | 1093 | 1094 | 1 | 0 | 0 |
| small | C | 12032 | 27 | 0.22% | 1952 | 1979 | 27 | 0 | 0 |
| medium | R | 12032 | 0 | 0.00% | 674 | 674 | 0 | 0 | 0 |
| medium | T | 12032 | 0 | 0.00% | 67 | 67 | 0 | 0 | 0 |
| medium | C | 12032 | 2 | 0.02% | 5098 | 5100 | 2 | 0 | 0 |

## 6. Validation and smoke

- **(a) medium**: 16 saved OBQA fit rows reproduced bit for bit = **True** (action mismatches 0, probe mismatches 0); sources `$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/actions/obqa_fit.jsonl`, `$DATA_DIR/P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/probes/obqa_fit.jsonl`.
- **(c) medium smoke**: 16 MMLU-Pro fit rows, INVALID R/T/C = 0/0/3 (threshold 4 per action, exceeded: none); 2.2663 s/row measured.
- **(a) small**: 16 saved OBQA fit rows reproduced bit for bit = **True** (action mismatches 0, probe mismatches 0); sources `$DATA_DIR/P2_10_20260911T122423Z/results/small/obqa/train_cases.jsonl`, `$DATA_DIR/P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/records/small_obqa_fit_probes.jsonl`.
- **(c) small smoke**: 16 MMLU-Pro fit rows, INVALID R/T/C = 1/2/2 (threshold 4 per action, exceeded: none); 2.2327 s/row measured.
- **(b) large control**: 16 saved large-pair MMLU-Pro fit rows reproduced bit for bit with the unchanged large configuration = **True** (action mismatches 0, probe mismatches 0).

Compared fields: `raw_answer`, `generated_token_ids`, `receiver_input_tokens`, `helper_message`, `helper_generated_token_ids`, `helper_input_tokens`; probes compared on exact `ProbeMax`, exact `p_labels`, `probe_ids`, `probe_ids_sha256`, `rendered_sha256`, `input_tokens`, `last_valid_position`. No gold was read.

## 7. Completeness

- 12032 rows x 4 requests x 2 pairs = 96,256 requests; duplicate keys 0, missing IDs 0, input-hash mismatches 0, re-parsed actions 72192.
- Splits: fit 3000 / calibration 6000 / development 2641 group representatives; group leakage 0.
- Gold opened only after the deployment configuration of every setting was written: `analysis/GOLD_OPENED.json`.

## 8. Models, fusers and budget

| pair | helper | receiver | fuser | projectors |
|---|---|---|---|---|
| small | `Qwen/Qwen2.5-0.5B-Instruct` @ `7ae55760` | `Qwen/Qwen3-0.6B` @ `c1899de2` | `nics-efc/C2C_Fuser` @ `8704f555` (`qwen3_0.6b+qwen2.5_0.5b_Fuser/final`) | 28 |
| medium | `Qwen/Qwen2.5-1.5B-Instruct` @ `989aa798` | `Qwen/Qwen3-1.7B` @ `70d244cc` | `nics-efc/C2C_Fuser` @ `f01fc325` (`qwen3_1.7b+qwen2.5_1.5b_Fuser/final`) | 28 |

Refined budget estimate: **29.17 productive GPU-hours** (14.583 pair-wall hours), 6 main debug jobs. `feasibility/GPU_HOUR_ESTIMATE_REFINED.json`.

## 9. Paths

- protocol freeze: `$DATA_DIR/P2_R2_E8_20260920T012544Z/PROTOCOL_FREEZE_E8.md`
- freeze index: `$DATA_DIR/P2_R2_E8_20260920T012544Z/FREEZE_INDEX_E8.json`
- budget authorization: `$DATA_DIR/P2_R2_E8_20260920T012544Z/BUDGET_AUTHORIZATION_E8.json`
- CPU feasibility: `$DATA_DIR/P2_R2_E8_20260920T012544Z/feasibility/CPU_FEASIBILITY.json`
- budget estimate: `$DATA_DIR/P2_R2_E8_20260920T012544Z/feasibility/GPU_HOUR_ESTIMATE.json`
- refined budget: `$DATA_DIR/P2_R2_E8_20260920T012544Z/feasibility/GPU_HOUR_ESTIMATE_REFINED.json`
- lane manifest: `$DATA_DIR/P2_R2_E8_20260920T012544Z/splits/E8_LANES.json`
- records: `$DATA_DIR/P2_R2_E8_20260920T012544Z/shards/<pair>/lane_NN/{actions,probes}/<split>.jsonl`
- thresholds: `$DATA_DIR/P2_R2_E8_20260920T012544Z/analysis/thresholds/<pair>_fit_thresholds.json`
- 80-test ledger: `$DATA_DIR/P2_R2_E8_20260920T012544Z/analysis/calibration/80_test_ledger.csv`
- deployments: `$DATA_DIR/P2_R2_E8_20260920T012544Z/analysis/deployments/deployment_configs.json`
- development table: `$DATA_DIR/P2_R2_E8_20260920T012544Z/analysis/development/split_summaries.csv`
- compact 4 settings: `$DATA_DIR/P2_R2_E8_20260920T012544Z/analysis/development/compact_4_settings.csv`
- oracle: `$DATA_DIR/P2_R2_E8_20260920T012544Z/analysis/development/oracle_headroom.csv`
- re-split stability: `$DATA_DIR/P2_R2_E8_20260920T012544Z/analysis/development/resplit_stability.csv`
- D1 differences: `$DATA_DIR/P2_R2_E8_20260920T012544Z/analysis/development/D1_label_differences.csv`
- merged rows: `$DATA_DIR/P2_R2_E8_20260920T012544Z/analysis/merged/<pair>_rows.jsonl`
- numerical validation: `$DATA_DIR/P2_R2_E8_20260920T012544Z/NUMERICAL_VALIDATION_E8.json`
- analysis receipt: `$DATA_DIR/P2_R2_E8_20260920T012544Z/ANALYSIS_COMPLETE_E8.json`
