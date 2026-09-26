# E3 on ClusterA: each arm's first formal request (report only; nothing new computed)

Sources: `P2_R1_EXP_20260919T050555Z/results/E3_policy_savings.csv` and `E3_full_mmlu_c2c.csv` (columns fixed_/policy_first_{id, attempt, ms, global_cold}, written by `src/ClusterA/e3/e3_metrics.py`: the arm's record with the minimum attempt counter), and `E3_SUMMARY.md`.
- attempt = request order within the replay. * = the replay's global first request after model load.
- The first question is the same in all three repeats.

| replay | policy | first question | attempt fixed / policy | REPEAT1 fixed / policy ms | REPEAT2 | REPEAT3 |
|---|---|---|---|---|---|---|
| large | OBQA/Text | 9-782 | 2 / 1 | 1139.4 / 3811.7* | 1041.8 / 936.5* | 1083.6 / 3384.3* |
| large | OBQA/C2C | 9-782 | 4 / 3 | 512.9 / 228.8 | 395.8 / 236.0 | 587.8 / 230.7 |
| large | ARC/Text | Mercury_7207358 | 514 / 513 | 847.2 / 226.6 | 864.5 / 231.6 | 852.3 / 229.4 |
| large | ARC/C2C | Mercury_7207358 | 516 / 515 | 188.6 / 226.2 | 188.3 / 234.9 | 185.7 / 228.7 |
| medium | OBQA/C2C | 9-782 | 1 / 2 | 708.5* / 328.3 | 665.9* / 327.6 | 736.6* / 321.4 |
| medium | ARC/C2C | Mercury_7207358 | 257 / 258 | 265.8 / 202.4 | 268.8 / 201.6 | 260.6 / 197.6 |
| MMLU-Pro | Text | test:3074 | 1 / 2 | 1658.2* / 1323.7 | 1703.9* / 1257.6 | 1622.4* / 1249.5 |
| MMLU-Pro | C2C | test:3074 | 3 / 4 | 792.2 / 805.5 | 770.9 / 785.5 | 767.0 / 783.1 |

Full MMLU-Pro C2C replay (MMLU_C2C_FULL): first question test:3261, attempt 1 / 2, fixed 4201.7* / policy 680.1 ms.

- In the large and medium replays, the ARC rows are the first ARC requests. They come after the OBQA requests in the same replay (attempts 513-516 and 257-258), not right after model load.
