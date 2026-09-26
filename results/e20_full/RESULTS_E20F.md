# RESULTS_E20F — E20-full (SQuAD v1.1, helper Qwen2.5-7B-Instruct Text, receiver Llama-3.1-8B-Instruct, score s2)

CERT_E20F.json 3a370c00daec66bbb42647e96192851168be58bad35675d9167e2f238320dc5f (2026-09-22T03:24:07.954380+00:00); STATS_E20F.json 2bc035b318149295280cc8dd90561f4e46b9ad8a029f74dce264ad85387e2494 (2026-09-22T03:30:53.103165+00:00); accuracy 2026-09-22T03:31:23.507956+00:00. Writing-rule branch: **(1)**; rule (5) triggered: **True**.

## Calibration (fit 500 -> 20 thresholds; calibration 2,000)

| q | tau | n | k | p | .999 CP up | accepted |
|---|---|---|---|---|---|---|
| 0.05 | 0.0001884278490466445 | 111 | 2 | 0.08 | 0.0971 | False |
| 0.10 | 0.0006554688769126827 | 212 | 3 | 0.00573 | 0.0602 | False |
| 0.15 | 0.0016052512879751882 | 307 | 3 | 0.000122 | 0.0419 | True |
| 0.20 | 0.004921390939931944 | 409 | 4 | 8.3e-06 | 0.0357 | True |
| 0.25 | 0.01608877676397299 | 519 | 7 | 7.89e-06 | 0.0374 | True |
| 0.30 | 0.04211308820549682 | 592 | 11 | 6.06e-05 | 0.0427 | True |
| 0.35 | 0.09916318852268603 | 721 | 17 | 0.000252 | 0.0466 | True |
| 0.40 | 0.166573346248371 | 847 | 29 | 0.0173 | 0.0581 | False |
| 0.45 | 0.2302543160507652 | 952 | 40 | 0.145 | 0.0660 | False |
| 0.50 | 0.2979597218615335 | 1063 | 48 | 0.26 | 0.0683 | False |
| 0.55 | 0.34983122956832974 | 1166 | 58 | 0.519 | 0.0725 | False |
| 0.60 | 0.3980109588447856 | 1261 | 72 | 0.887 | 0.0801 | False |
| 0.65 | 0.43266033023539413 | 1322 | 76 | 0.903 | 0.0800 | False |
| 0.70 | 0.4685384488104992 | 1390 | 85 | 0.973 | 0.0836 | False |
| 0.75 | 0.5110182494710932 | 1501 | 107 | 1 | 0.0941 | False |
| 0.80 | 0.5592014973727238 | 1607 | 138 | 1 | 0.1095 | False |
| 0.85 | 0.6146540659205175 | 1696 | 158 | 1 | 0.1169 | False |
| 0.90 | 0.6863088045251209 | 1806 | 196 | 1 | 0.1329 | False |
| 0.95 | 0.7918738875991826 | 1908 | 236 | 1 | 0.1486 | False |
| 1.00 | Infinity | 2000 | 302 | 1 | 0.1772 | False |

Deployed q = **0.35** (threshold 0.09916318852268603). Disagreement 302/2000; INVALID R 0, reference 0; always-omit change rate 0.1510; max TPR/FPR 18.02277188849627 vs C = 3.3793; needed N_cal (if fallback): None.

## Dev (1,000)

d = 154/1000 = 0.1540 [0.1322, 0.1779]; AUROC s2 0.8109 [0.7714, 0.8477] (>= .80: True); coverage 0.3960; omitted changes 16/396 = 0.0404 [0.0233, 0.0648]; split {'both_parse': 16, 'only_R_INVALID': 0, 'only_ref_INVALID': 0}; INVALID R 0, reference 0; binormal P(certify) from dev at N_cal 2,000 = 0.749.

Surface (omitted dev): {'n': 396, 'change_rate_normalized': 0.04040404040404041, 'raw_string_change_rate': 0.04040404040404041, 'containment_as_agreement_change_rate': 0.0025252525252525255, 'n_changes': 16, 'containment_share_of_changes': 0.9375, 'median_token_F1_among_changes': 0.5166666666666666, 'extraction_beyond_normalization_share': 0.005050505050505051, 'n_outputs': 792}

Surface (all dev): {'n': 1000, 'change_rate_normalized': 0.154, 'raw_string_change_rate': 0.235, 'containment_as_agreement_change_rate': 0.06, 'n_changes': 154, 'containment_share_of_changes': 0.6103896103896104, 'median_token_F1_among_changes': 0.5, 'extraction_beyond_normalization_share': 0.003, 'n_outputs': 2000}

Lengths: {'dev': {'median_words_R': 2.0, 'median_words_ref': 2.0, 'cap32_hits_R': 6, 'cap32_hits_ref': 2, 'helper_tokens_median': 36.0, 'helper_cap256_share': 0.0, 'helper_cap256_n': 0, 'n': 1000}, 'cal': {'median_words_R': 2.0, 'median_words_ref': 2.0, 'cap32_hits_R': 10, 'cap32_hits_ref': 11, 'helper_tokens_median': 36.0, 'helper_cap256_share': 0.0, 'helper_cap256_n': 0, 'n': 2000}}

## Test

{'n_questions': 1000, 'omitted': 364, 'changed': 9, 'change_rate': 0.024725274725274724, 'CP95': [0.011366909897879422, 0.046415908959540175], 'p': 0.01210665625765064, 'p_le_001': False, 'coverage': 0.364, 'verdict': 'pass', 'disagreements_all': 155, 'invalid_R': 0, 'invalid_ref': 0, 'omitted_changes_split': {'both_parse': 9, 'only_R_INVALID': 0, 'only_ref_INVALID': 0}, 'surface_omitted': {'n': 364, 'change_rate_normalized': 0.024725274725274724, 'raw_string_change_rate': 0.03296703296703297, 'containment_as_agreement_change_rate': 0.0027472527472527475, 'n_changes': 9, 'containment_share_of_changes': 0.8888888888888888, 'median_token_F1_among_changes': 0.5, 'extraction_beyond_normalization_share': 0.0013736263736263737, 'n_outputs': 728}, 'lengths': {'median_words_R': 2.0, 'median_words_ref': 2.0, 'cap32_hits_R': 3, 'cap32_hits_ref': 3, 'helper_tokens_median': 36.0, 'helper_cap256_share': 0.0, 'helper_cap256_n': 0, 'n': 1000}}

## Accuracy

- dev: R 659/1000 [0.6290, 0.6890]; Text 669/1000 [0.6390, 0.6990]; policy 673/1000 [0.6440, 0.7030]; G 0.0100 [-0.0090, 0.0290]; changes {'n': 154, 'reference_corrects': 49, 'reference_breaks': 39, 'both_wrong': 66, 'both_right': 0}; omitted changes {'n': 16, 'reference_corrects': 4, 'reference_breaks': 8, 'both_wrong': 4, 'both_right': 0}
- test: R 664/1000 [0.6350, 0.6940]; Text 682/1000 [0.6540, 0.7120]; policy 686/1000 [0.6580, 0.7150]; G 0.0180 [-0.0000, 0.0380]; changes {'n': 155, 'reference_corrects': 54, 'reference_breaks': 36, 'both_wrong': 65, 'both_right': 0}; omitted changes {'n': 9, 'reference_corrects': 2, 'reference_breaks': 6, 'both_wrong': 1, 'both_right': 0}

kappa*alpha = 0.0198 vs dev G 0.0100.

## Re-splits, prediction, value

Re-splits: agreement 1.000, certification rate 1.000, same q 0.460, median q 0.375, median dev coverage 0.4150.

Pilot binormal prediction P@2000 = 0.975 (conservative 0.081); outcome: deployed.

Value estimate (ms): {'note': 'estimate from recorded per-row wall-clock on ClusterA A100 (pilot definition), sequential execution assumed; not a replay', 'policy_mean': 198.46488996921107, 'policy_CI95': [167.16113872225395, 229.92771075362106], 'always_omit_mean': 785.3696485492401, 'always_omit_CI95': [773.2634660017735, 796.9782533655292], 'helper_mean': 772.468580708839, 'receiver_only_mean': 153.50968252425082, 'receiver_with_message_mean': 166.4107503646519}
