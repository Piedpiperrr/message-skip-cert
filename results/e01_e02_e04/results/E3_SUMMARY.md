# E3 on ClusterA: latency replays (records analysed on the login node)

Generated 2026-09-19T09:35:17.665093+00:00 by `src/ClusterA/e3/make_e3_summary.py` from the `E3_*.csv` files in this folder (written by `src/ClusterA/e3/e3_metrics.py`). Jobs: 7635399 (P2R1_E3POL_A, debug; REPEAT1 + REPEAT2) and 7635512 (P2R1_E3POL_B, debug-2; REPEAT3 + MMLU_C2C_FULL); both exit 0. Each replay's ORIGINAL `src/analyze.py` was also run unchanged through a path-redirecting adapter (`src/ClusterA/e3/run_original_analyses.py`, D7). Its outputs are in `<E3 folder>/results/<stage>/` (FULL: `results/`), and its version-(a) mean and interval equal the values below in every cell (`E3_verdict.json`: a_equals_original_all = True).

**Rules (fixed before any ClusterA E3 run):**
- Paired saving = fixed − policy latency (ms).
- (a) all questions, with the original replay's seed-0 bootstrap indices (2,000 resamples, 95% percentile interval).
- (b) excludes every question on which either arm made its first formal request after model load, with `default_rng(0)` indices over the remaining questions. This is the P2_R1_CPU item5 method that produced the ClusterB reference classes.
- Class on (b): + if low > 0, − if high < 0, ? otherwise.
- First-request column = each arm's first formal request latency, fixed / policy (ms); * = the replay's global first request after model load.

## REPEAT1 (source: `E3_policy_savings.csv`; records `P2_R1_E3POL_REPEAT1_20260919T075315Z/<stage>/records/`)

| policy | (a) mean [95% CI] | (a) median | (b) N | (b) mean [95% CI] | (b) median | class (b) | ClusterB (b) | first request fixed / policy |
|---|---|---|---|---|---|---|---|---|
| large/OBQA/Text | 395.5 [325.3, 458.3] | 524.8 | 127 | 419.6 [370.7, 468.7] | 525.3 | + | + | 1139.4 / 3811.7* |
| large/OBQA/C2C | 29.4 [14.9, 45.5] | 14.6 | 127 | 27.4 [13.8, 42.3] | 14.3 | + | + | 512.9 / 228.8 |
| large/ARC/Text | 573.5 [536.0, 608.7] | 592.2 | 127 | 573.2 [535.8, 609.6] | 590.5 | + | + | 847.2 / 226.6 |
| large/ARC/C2C | 91.4 [68.9, 116.2] | 47.4 | 127 | 92.4 [70.2, 115.8] | 47.5 | + | + | 188.6 / 226.2 |
| medium/OBQA/C2C | 49.9 [35.8, 65.5] | 59.7 | 127 | 47.3 [34.0, 61.9] | 58.6 | + | + | 708.5* / 328.3 |
| medium/ARC/C2C | 79.2 [58.5, 104.5] | 61.9 | 127 | 79.3 [57.6, 104.3] | 61.9 | + | + | 265.8 / 202.4 |
| large/MMLU-Pro/Text | 261.4 [191.1, 331.5] | -20.9 | 127 | 260.8 [189.9, 333.9] | -21.0 | + | + | 1658.2* / 1323.7 |
| large/MMLU-Pro/C2C | -0.1 [-23.4, 27.8] | -39.4 | 127 | -0.0 [-24.5, 28.3] | -41.3 | ? | ? | 792.2 / 805.5 |

## REPEAT2 (source: `E3_policy_savings.csv`; records `P2_R1_E3POL_REPEAT2_20260919T075315Z/<stage>/records/`)

| policy | (a) mean [95% CI] | (a) median | (b) N | (b) mean [95% CI] | (b) median | class (b) | ClusterB (b) | first request fixed / policy |
|---|---|---|---|---|---|---|---|---|
| large/OBQA/Text | 427.6 [376.4, 474.4] | 532.7 | 127 | 430.2 [380.9, 479.9] | 532.8 | + | + | 1041.8 / 936.5* |
| large/OBQA/C2C | 30.3 [15.7, 46.5] | 14.4 | 127 | 29.3 [14.9, 44.2] | 14.3 | + | + | 395.8 / 236.0 |
| large/ARC/Text | 585.4 [546.7, 622.9] | 608.7 | 127 | 585.0 [547.0, 621.8] | 608.4 | + | + | 864.5 / 231.6 |
| large/ARC/C2C | 90.5 [67.3, 115.4] | 49.2 | 127 | 91.6 [68.5, 115.7] | 49.3 | + | + | 188.3 / 234.9 |
| medium/OBQA/C2C | 52.2 [37.7, 67.9] | 63.9 | 127 | 50.0 [36.4, 65.2] | 63.7 | + | + | 665.9* / 327.6 |
| medium/ARC/C2C | 82.4 [61.4, 108.4] | 66.3 | 127 | 82.5 [60.1, 108.4] | 66.2 | + | + | 268.8 / 201.6 |
| large/MMLU-Pro/Text | 262.4 [192.3, 331.1] | -32.5 | 127 | 261.0 [189.7, 335.1] | -32.7 | + | + | 1703.9* / 1257.6 |
| large/MMLU-Pro/C2C | 2.4 [-20.3, 30.6] | -39.6 | 127 | 2.6 [-21.1, 30.5] | -40.4 | ? | ? | 770.9 / 785.5 |

## REPEAT3 (source: `E3_policy_savings.csv`; records `P2_R1_E3POL_REPEAT3_20260919T075315Z/<stage>/records/`)

| policy | (a) mean [95% CI] | (a) median | (b) N | (b) mean [95% CI] | (b) median | class (b) | ClusterB (b) | first request fixed / policy |
|---|---|---|---|---|---|---|---|---|
| large/OBQA/Text | 401.8 [335.6, 460.6] | 531.6 | 127 | 423.1 [373.6, 471.5] | 531.9 | + | + | 1083.6 / 3384.3* |
| large/OBQA/C2C | 30.4 [15.5, 46.6] | 14.5 | 127 | 27.8 [13.9, 42.5] | 14.5 | + | + | 587.8 / 230.7 |
| large/ARC/Text | 574.2 [536.3, 611.2] | 595.9 | 127 | 573.8 [535.2, 610.6] | 593.8 | + | + | 852.3 / 229.4 |
| large/ARC/C2C | 90.2 [66.9, 115.8] | 47.7 | 127 | 91.2 [68.9, 115.1] | 48.0 | + | + | 185.7 / 228.7 |
| medium/OBQA/C2C | 48.5 [34.3, 64.4] | 57.7 | 127 | 45.6 [32.5, 60.1] | 55.2 | + | + | 736.6* / 321.4 |
| medium/ARC/C2C | 76.5 [56.5, 101.2] | 61.6 | 127 | 76.6 [55.4, 101.1] | 61.5 | + | + | 260.6 / 197.6 |
| large/MMLU-Pro/Text | 263.5 [193.5, 333.7] | -31.6 | 127 | 262.7 [191.1, 336.5] | -31.8 | + | + | 1622.4* / 1249.5 |
| large/MMLU-Pro/C2C | 2.6 [-20.1, 30.4] | -35.6 | 127 | 2.8 [-20.7, 30.8] | -36.1 | ? | ? | 767.0 / 783.1 |

## Verdict: **CONSISTENT**

Every policy has the ClusterB version-(b) class in all three repeats. The ClusterB classes were recomputed from `P2_R1_CPU_20260919T045556Z/results/item5_cold_request_sensitivity.csv` (ii) and equal the stated reference classes.

| pair | task | reference | ClusterB (b) mean [CI] | REPEAT1 | REPEAT2 | REPEAT3 |
|---|---|---|---|---|---|---|
| large | OBQA | Text | + (532.8 [470.9, 594.7]) | + | + | + |
| large | OBQA | C2C | + (33.5 [16.5, 51.7]) | + | + | + |
| large | ARC | Text | + (717.2 [670.1, 761.8]) | + | + | + |
| large | ARC | C2C | + (112.3 [83.7, 142.3]) | + | + | + |
| medium | OBQA | C2C | + (61.0 [43.9, 79.9]) | + | + | + |
| medium | ARC | C2C | + (100.8 [73.0, 132.8]) | + | + | + |
| large | MMLU-Pro | Text | + (322.1 [234.8, 412.5]) | + | + | + |
| large | MMLU-Pro | C2C | ? (6.5 [-23.3, 41.1]) | ? | ? | ? |

## MMLU_C2C_FULL (2,641 development group representatives; fixed C2C vs C2C policy q = .40; source `E3_full_mmlu_c2c.csv`)

| (a) mean [95% CI] | class (a) | (a) median | (b) N | (b) mean [95% CI] | class (b) | (b) median | first request fixed / policy | (b) excluded |
|---|---|---|---|---|---|---|---|---|
| 23.3 [14.5, 32.2] | + | -37.3 | 2640 | 22.0 [14.0, 30.5] | + | -37.3 | 4201.7* / 680.1 | test:3261 |

(a) uses the frozen indices `protocol/bootstrap_indices.npz` = default_rng(0).integers(0,2641,(2000,2641)), asserted equal.

## Integrity (source `E3_integrity.csv`, from the original analyses' identity outputs; large same-run comparison from the records)

| run | policy | probe score + input hash + route = frozen dev | R-routed raw = dev R | reference-routed raw = same-run fixed | all |
|---|---|---|---|---|---|
| REPEAT1 | large/OBQA/Text | 128/128 | 97/97 | 31/31 | True |
| REPEAT1 | large/OBQA/C2C | 128/128 | 97/97 | 31/31 | True |
| REPEAT1 | large/ARC/Text | 128/128 | 120/120 | 8/8 | True |
| REPEAT1 | large/ARC/C2C | 128/128 | 115/115 | 13/13 | True |
| REPEAT1 | medium/OBQA/C2C | 128/128 | 66/66 | 62/62 | True |
| REPEAT1 | medium/ARC/C2C | 128/128 | 77/77 | 51/51 | True |
| REPEAT1 | large/MMLU-Pro/Text | 128/128 | 48/48 | 80/80 | True |
| REPEAT1 | large/MMLU-Pro/C2C | 128/128 | 48/48 | 80/80 | True |
| REPEAT2 | large/OBQA/Text | 128/128 | 97/97 | 31/31 | True |
| REPEAT2 | large/OBQA/C2C | 128/128 | 97/97 | 31/31 | True |
| REPEAT2 | large/ARC/Text | 128/128 | 120/120 | 8/8 | True |
| REPEAT2 | large/ARC/C2C | 128/128 | 115/115 | 13/13 | True |
| REPEAT2 | medium/OBQA/C2C | 128/128 | 66/66 | 62/62 | True |
| REPEAT2 | medium/ARC/C2C | 128/128 | 77/77 | 51/51 | True |
| REPEAT2 | large/MMLU-Pro/Text | 128/128 | 48/48 | 80/80 | True |
| REPEAT2 | large/MMLU-Pro/C2C | 128/128 | 48/48 | 80/80 | True |
| REPEAT3 | large/OBQA/Text | 128/128 | 97/97 | 31/31 | True |
| REPEAT3 | large/OBQA/C2C | 128/128 | 97/97 | 31/31 | True |
| REPEAT3 | large/ARC/Text | 128/128 | 120/120 | 8/8 | True |
| REPEAT3 | large/ARC/C2C | 128/128 | 115/115 | 13/13 | True |
| REPEAT3 | medium/OBQA/C2C | 128/128 | 66/66 | 62/62 | True |
| REPEAT3 | medium/ARC/C2C | 128/128 | 77/77 | 51/51 | True |
| REPEAT3 | large/MMLU-Pro/Text | 128/128 | 48/48 | 80/80 | True |
| REPEAT3 | large/MMLU-Pro/C2C | 128/128 | 48/48 | 80/80 | True |
| MMLU_C2C_FULL | large/MMLU-Pro/C2C | 2641/2641 | 1069/1069 | 1572/1572 | True |

## REPEAT1 MMLU-Pro replay duration (report only; nothing excluded; sources `E3_repeat_mmlu_diagnosis.csv`, `E3_repeat_mmlu_arm_latency.csv`, `E3_repeat1_vs_repeat2_ratios.csv`)

| run | node | replay wall (min) | startup (s) | weight-hash recheck (s) | request span (min) | sum of request latencies (min) | inter-request gaps > 1 s | max gap (s) |
|---|---|---|---|---|---|---|---|---|
| REPEAT1 | compute-node | 22.28 | 30.0 | 44.5 | 20.75 | 5.27 | 181 | 19.392 |
| REPEAT2 | compute-node | 6.38 | 27.9 | 30.6 | 5.31 | 5.19 | 0 | 0.209 |
| REPEAT3 | compute-node | 6.3 | 28.9 | 22.3 | 5.35 | 5.23 | 0 | 0.082 |

| run | arm | median ms | p90 ms | max ms | mean ms |
|---|---|---|---|---|---|
| REPEAT1 | fixed_T | 1061.9 | 1358.7 | 1801.8 | 1079.6 |
| REPEAT1 | policy_T | 973.4 | 1344.8 | 1938.8 | 818.2 |
| REPEAT1 | fixed_C | 226.7 | 409.5 | 1232.5 | 286.6 |
| REPEAT1 | policy_C | 267.6 | 380.2 | 805.5 | 286.8 |
| REPEAT2 | fixed_T | 1043.1 | 1338.7 | 1863.5 | 1068.7 |
| REPEAT2 | policy_T | 950.8 | 1344.3 | 1895.7 | 806.2 |
| REPEAT2 | fixed_C | 215.9 | 413.8 | 1230.4 | 279.6 |
| REPEAT2 | policy_C | 250.4 | 376.8 | 785.5 | 277.2 |
| REPEAT3 | fixed_T | 1045.1 | 1375.0 | 1842.1 | 1075.9 |
| REPEAT3 | policy_T | 950.6 | 1368.9 | 1903.2 | 812.4 |
| REPEAT3 | fixed_C | 217.3 | 414.9 | 1220.1 | 281.8 |
| REPEAT3 | policy_C | 252.9 | 380.9 | 783.1 | 279.2 |

REPEAT1 / REPEAT2 per arm:

| arm | median ratio | p90 ratio | mean ratio |
|---|---|---|---|
| fixed_T | 1.02 | 1.01 | 1.01 |
| policy_T | 1.02 | 1.0 | 1.01 |
| fixed_C | 1.05 | 0.99 | 1.03 |
| policy_C | 1.07 | 1.01 | 1.03 |

- The extra time is between requests (gap = next record time − previous record time − next request latency), outside the timed region. Timed latencies and savings are close to REPEAT2/REPEAT3 (see the REPEAT tables).
- The same node's large and medium replays had 1 and 0 gaps over 1 s.
- `run_logs/entry.log` and `outer.log` contain no warning or error lines.
- The cause is not identifiable from the saved logs.

## Hardware (source `E3_hardware.csv`, from each node's `logs/node_hardware.txt`)

| folder | node | GPUs | GPU model | driver | CUDA (driver) | torch | torch CUDA | topology GPU0 row | CPU | CPUs | sockets | cores/socket | threads/core |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REPEAT1 | compute-node | 4 | NVIDIA A100-SXM4-40GB | 580.65.06 | 13.0 | 2.6.0+cu124 | 12.4 | X NV4 NV4 NV4 | x86-64 CPU (model redacted) | 64 | 1 | 32 | 2 |
| REPEAT2 | compute-node | 4 | NVIDIA A100-SXM4-40GB | 580.65.06 | 13.0 | 2.6.0+cu124 | 12.4 | X NV4 NV4 NV4 | x86-64 CPU (model redacted) | 64 | 1 | 32 | 2 |
| REPEAT3 | compute-node | 4 | NVIDIA A100-SXM4-40GB | 580.65.06 | 13.0 | 2.6.0+cu124 | 12.4 | X NV4 NV4 NV4 | x86-64 CPU (model redacted) | 64 | 1 | 32 | 2 |
| MMLU_C2C_FULL | compute-node | 4 | NVIDIA A100-SXM4-40GB | 580.65.06 | 13.0 | 2.6.0+cu124 | 12.4 | X NV4 NV4 NV4 | x86-64 CPU (model redacted) | 64 | 1 | 32 | 2 |
