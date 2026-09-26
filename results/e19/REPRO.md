# E19 Step 0: reproduction checks

Run 2026-09-21T22:53:19Z to 22:54:28Z (`scripts/step0_repro.py`, log `logs/step0.log`, every row in `results/step0_repro_checks.csv`).
ClusterA login node, CPU only. No new E19 quantity was computed before these checks, and PREREG_E19.md was hashed after them (22:59:37Z).

**Result: 49 / 49 PASS.** No E19 item is skipped for a failed reproduction.

## (a) Dev omitted / changed, 12 policy rows: 12/12 PASS

Recomputed from the stored dev outputs, ProbeMax and frozen thresholds (E17 loader -> E13 -> E11). Expected values: E14 (`P2_R6_E14_20260921T052241Z/results/E14_2_zero_u.csv`,
dev rows = RESULTS_E14 table (ii)); for the two Llama rows, which E14 does not cover: X3 `results/analysis/dev_table_pre_gold.csv`.

| policy | expected | recomputed |
|---|---|---|
| large/OBQA/Text q=.80 | 572/19 | 572/19 |
| large/OBQA/C2C q=.80 | 572/13 | 572/13 |
| large/ARC/Text q=.95 | 284/9 | 284/9 |
| large/ARC/C2C q=.90 | 270/3 | 270/3 |
| large/MMLU-Pro/Text q=.40 | 1069/40 | 1069/40 |
| large/MMLU-Pro/C2C q=.40 | 1069/37 | 1069/37 |
| medium/OBQA/C2C q=.55 | 390/11 | 390/11 |
| medium/OBQA/C2C q=.50 | 355/7 | 355/7 |
| medium/ARC/C2C q=.60 | 189/4 | 189/4 |
| large/OBQA/Text+fact q=.75 | 536/13 | 536/13 |
| Llama-3.1-8B/OBQA/Text q=.60 (tau 0.009371757507324219) | 438/7 | 438/7 |
| Llama-3.1-8B/ARC/Text q=.70 (tau 0.014996349811553955) | 206/4 | 206/4 |

## (b) Replay savings: 8/8 Qwen + 2/2 Llama + Text+fact PASS

Paired mean of (fixed − policy) `latency_ms` over the 128 panel questions, all requests kept.

| policy | replay | expected (ms) | recomputed (ms) |
|---|---|---|---|
| large/OBQA/Text | original (Table 2) | 517.1 | 517.1 (517.1263 = E15) |
| large/OBQA/C2C | original | 36.6 | 36.6 |
| large/ARC/Text | original | 717.6 | 717.6 |
| large/ARC/C2C | original | 110.9 | 110.9 |
| large/MMLU-Pro/Text | original | 346.3 | 346.3 |
| large/MMLU-Pro/C2C | original | 8.2 | 8.2 |
| medium/OBQA/C2C q=.55 | original | 79.7 | 79.7 |
| medium/ARC/C2C | original | 100.7 | 100.7 |
| Llama-3.1-8B/OBQA/Text | second (E16-4) | 318.6 [261.1, 372.1] | 318.6 [261.1, 372.1] |
| Llama-3.1-8B/ARC/Text | second (E16-4) | 418.9 [361.7, 473.7] | 418.9 [361.7, 473.7] |
| large/OBQA/Text+fact | second (E6 replay) | 343.4 [297.7, 386.0] | 343.4 [297.7, 386.0] |

In addition (not required), the full 2,641-question MMLU-Pro C2C replay reproduces its stored analysis (`results/e3_full_saving.csv`): 23.346 [14.541, 32.163] ms.
The unrounded Table 2 values also equal E15's `step2_repro_table2.csv` recomputed values exactly.

## (c) Dev u = 0 counts n0 / n at the deployed thresholds: 10/10 PASS (vs E14_2_zero_u.csv)

354/572, 354/572, 217/284, 217/270, 645/1069, 645/1069, 321/390 (medium OBQA C2C q=.55), 321/355 (q=.50), 174/189, 354/536 (Text+fact).
