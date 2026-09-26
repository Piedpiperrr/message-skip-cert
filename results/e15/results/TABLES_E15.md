## E15-1 per setting (results/e15_1_per_setting.csv)

| setting | actual | q | predicted | q_hat | steps (q_hat-q) | dev cov | pred fit cov | abs cov err | measured saving (ms) | pred saving, fit cov (ms) | pred saving, panel cov (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| small/OBQA/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| small/OBQA/C2C | fallback | - | fallback | - |  |  |  |  |  |  |  |
| small/ARC/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| small/ARC/C2C | fallback | - | fallback | - |  |  |  |  |  |  |  |
| medium/OBQA/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| medium/OBQA/C2C | deploy | 0.55 | deploy | 0.55 | 0 | 0.526 | 0.551 | 0.025 | 79.7 | 64.7 | 58.4 |
| medium/ARC/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| medium/ARC/C2C | deploy | 0.60 | deploy | 0.60 | 0 | 0.632 | 0.610 | 0.022 | 100.7 | 98.9 | 97.0 |
| large/OBQA/Text | deploy | 0.80 | deploy | 0.80 | 0 | 0.771 | 0.800 | 0.029 | 517.1 | 536.6 | 506.1 |
| large/OBQA/C2C | deploy | 0.80 | deploy | 0.85 | 1 | 0.771 | 0.850 | 0.079 | 36.6 | 26.6 | 19.0 |
| large/ARC/Text | deploy | 0.95 | deploy | 0.90 | -1 | 0.950 | 0.900 | 0.050 | 717.6 | 670.6 | 700.4 |
| large/ARC/C2C | deploy | 0.90 | deploy | 0.90 | 0 | 0.903 | 0.900 | 0.003 | 110.9 | 88.9 | 88.6 |
| large/MMLU-Pro/Text | deploy | 0.40 | deploy | 0.40 | 0 | 0.405 | 0.400 | 0.005 | 346.3 | 360.9 | 335.4 |
| large/MMLU-Pro/C2C | deploy | 0.40 | deploy | 0.35 | -1 | 0.405 | 0.352 | 0.053 | 8.2 | -7.7 | -5.1 |
| small/MMLU-Pro/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| small/MMLU-Pro/C2C | fallback | - | fallback | - |  |  |  |  |  |  |  |
| medium/MMLU-Pro/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| medium/MMLU-Pro/C2C | fallback | - | fallback | - |  |  |  |  |  |  |  |
| X1-Llama/OBQA/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| X1-Llama/OBQA/C2C | fallback | - | fallback | - |  |  |  |  |  |  |  |
| X1-Llama/ARC/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| X1-Llama/ARC/C2C | fallback | - | fallback | - |  |  |  |  |  |  |  |
| X2-OLMo/OBQA/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| X2-OLMo/ARC/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| X2-OLMo/MMLU-Pro/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |

## E15-1 saving model inputs (8 policies)

| setting | mean c_b | mean c_R | gap | mean c_s | pred fit cov | panel cov | measured | pred (fit) | abs err | rel err | pred (panel) | abs err | rel err |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| medium/OBQA/C2C | 394.5 | 216.4 | 178.0 | 33.4 | 0.5510 | 0.5156 | 79.7 | 64.7 | 14.9 | 0.187 | 58.4 | 21.2 | 0.266 |
| medium/ARC/C2C | 445.5 | 229.1 | 216.4 | 33.2 | 0.6104 | 0.6016 | 100.7 | 98.9 | 1.8 | 0.018 | 97.0 | 3.7 | 0.037 |
| large/OBQA/Text | 978.5 | 253.6 | 724.9 | 43.2 | 0.8000 | 0.7578 | 517.1 | 536.6 | 19.5 | 0.038 | 506.1 | 11.1 | 0.021 |
| large/OBQA/C2C | 335.8 | 253.6 | 82.2 | 43.2 | 0.8500 | 0.7578 | 36.6 | 26.6 | 10.0 | 0.272 | 19.0 | 17.5 | 0.480 |
| large/ARC/Text | 1060.8 | 267.6 | 793.2 | 43.3 | 0.9000 | 0.9375 | 717.6 | 670.6 | 47.0 | 0.066 | 700.4 | 17.3 | 0.024 |
| large/ARC/C2C | 414.4 | 267.6 | 146.8 | 43.3 | 0.9000 | 0.8984 | 110.9 | 88.9 | 22.1 | 0.199 | 88.6 | 22.3 | 0.201 |
| large/MMLU-Pro/Text | 1292.0 | 274.2 | 1017.8 | 46.2 | 0.4000 | 0.3750 | 346.3 | 360.9 | 14.6 | 0.042 | 335.4 | 10.9 | 0.031 |
| large/MMLU-Pro/C2C | 383.9 | 274.2 | 109.7 | 46.2 | 0.3517 | 0.3750 | 8.2 | -7.7 | 15.9 | 1.930 | -5.1 | 13.3 | 1.619 |

## E15-1 summary (results/e15_1_summary.csv)

- n_settings: 25
- n_deployed: 8
- n_fallback: 17
- x_deployed_predicted_deploy: 8
- y_fallback_predicted_fallback: 17
- n_both_deploy: 8
- median_abs_grid_steps: 0.0
- max_abs_grid_steps: 1
- median_abs_coverage_error: 0.02722821203953285
- median_abs_saving_err_fitcov_ms: 15.414283008781744
- median_rel_saving_err_fitcov: 0.12641523261093335
- median_abs_saving_err_panelcov_ms: 15.311992023503567
- median_rel_saving_err_panelcov: 0.11887688104011149
- paper_rule: predicts

## E15-2 source qualification (results/e15_2_qualification.csv)

| setting | source | qualifies | reason |
|---|---|---|---|
| medium/OBQA/C2C | (a) original configuration | False | no per-stage timer (one action wall interval) |
| medium/OBQA/C2C | (b) second configuration E3 REPEAT1 | False | no per-stage timer (one action wall interval) |
| medium/OBQA/C2C | (b) second configuration E3 REPEAT2 | False | no per-stage timer (one action wall interval) |
| medium/OBQA/C2C | (b) second configuration E3 REPEAT3 | False | no per-stage timer (one action wall interval) |
| medium/OBQA/C2C | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval) |
| medium/ARC/C2C | (a) original configuration | False | no per-stage timer (one action wall interval) |
| medium/ARC/C2C | (b) second configuration E3 REPEAT1 | False | no per-stage timer (one action wall interval) |
| medium/ARC/C2C | (b) second configuration E3 REPEAT2 | False | no per-stage timer (one action wall interval) |
| medium/ARC/C2C | (b) second configuration E3 REPEAT3 | False | no per-stage timer (one action wall interval) |
| medium/ARC/C2C | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval) |
| large/OBQA/Text | (a) original configuration | True | every stage separately timed per request |
| large/OBQA/Text | (b) second configuration E3 REPEAT1 | True | every stage separately timed per request |
| large/OBQA/Text | (b) second configuration E3 REPEAT2 | True | every stage separately timed per request |
| large/OBQA/Text | (b) second configuration E3 REPEAT3 | True | every stage separately timed per request |
| large/OBQA/Text | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval, GPU_forward_event_sum_ms is one sum per request) |
| large/OBQA/C2C | (a) original configuration | True | every stage separately timed per request |
| large/OBQA/C2C | (b) second configuration E3 REPEAT1 | True | every stage separately timed per request |
| large/OBQA/C2C | (b) second configuration E3 REPEAT2 | True | every stage separately timed per request |
| large/OBQA/C2C | (b) second configuration E3 REPEAT3 | True | every stage separately timed per request |
| large/OBQA/C2C | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval, GPU_forward_event_sum_ms is one sum per request) |
| large/ARC/Text | (a) original configuration | True | every stage separately timed per request |
| large/ARC/Text | (b) second configuration E3 REPEAT1 | True | every stage separately timed per request |
| large/ARC/Text | (b) second configuration E3 REPEAT2 | True | every stage separately timed per request |
| large/ARC/Text | (b) second configuration E3 REPEAT3 | True | every stage separately timed per request |
| large/ARC/Text | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval, GPU_forward_event_sum_ms is one sum per request) |
| large/ARC/C2C | (a) original configuration | True | every stage separately timed per request |
| large/ARC/C2C | (b) second configuration E3 REPEAT1 | True | every stage separately timed per request |
| large/ARC/C2C | (b) second configuration E3 REPEAT2 | True | every stage separately timed per request |
| large/ARC/C2C | (b) second configuration E3 REPEAT3 | True | every stage separately timed per request |
| large/ARC/C2C | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval, GPU_forward_event_sum_ms is one sum per request) |
| large/MMLU-Pro/Text | (a) original configuration | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/Text | (b) second configuration E3 REPEAT1 | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/Text | (b) second configuration E3 REPEAT2 | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/Text | (b) second configuration E3 REPEAT3 | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/Text | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/C2C | (a) original configuration | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/C2C | (b) second configuration E3 REPEAT1 | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/C2C | (b) second configuration E3 REPEAT2 | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/C2C | (b) second configuration E3 REPEAT3 | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/C2C | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval) |

## E15-2 busy GPU time, original configuration (results/e15_2_busy_savings.csv)

| setting | N | omitted | busy saving ms [95%] | latency saving ms [95%] | D ms [95%] | busy/latency |
|---|---|---|---|---|---|---|
| medium/OBQA/C2C | - | - | not available (no qualifying replay source) | - | - | - |
| medium/ARC/C2C | - | - | not available (no qualifying replay source) | - | - | - |
| large/OBQA/Text | 128 | 97 | 513.5 [448.7, 574.2] | 517.1 [447.8, 583.6] | -3.6 [-9.9, 8.3] | 0.993 |
| large/OBQA/C2C | 128 | 97 | 32.3 [14.4, 51.8] | 36.6 [18.0, 56.8] | -4.3 [-6.3, -3.2] | 0.882 |
| large/ARC/Text | 128 | 120 | 705.2 [659.1, 750.0] | 717.6 [670.6, 763.2] | -12.4 [-13.2, -11.6] | 0.983 |
| large/ARC/C2C | 128 | 115 | 106.6 [77.8, 138.2] | 110.9 [82.0, 142.8] | -4.3 [-4.6, -3.9] | 0.961 |
| large/MMLU-Pro/Text | - | - | not available (no qualifying replay source) | - | - | - |
| large/MMLU-Pro/C2C | - | - | not available (no qualifying replay source) | - | - | - |

### Stage means per request (ms; CUDA-event intervals)

| setting | fixed: helper | fixed: fuser | fixed: receiver | fixed busy | policy: probe | policy: helper | policy: fuser | policy: receiver | policy busy |
|---|---|---|---|---|---|---|---|---|---|
| large/OBQA/Text | 737.6 | 0.0 | 265.4 | 1003.0 | 53.4 | 174.6 | 0.0 | 261.5 | 489.5 |
| large/OBQA/C2C | 25.6 | 72.0 | 253.0 | 350.6 | 40.4 | 6.2 | 17.1 | 254.6 | 318.3 |
| large/ARC/Text | 807.3 | 0.0 | 263.2 | 1070.5 | 40.5 | 53.6 | 0.0 | 271.2 | 365.3 |
| large/ARC/C2C | 26.5 | 71.1 | 331.9 | 429.6 | 40.4 | 2.7 | 7.2 | 272.7 | 323.0 |
