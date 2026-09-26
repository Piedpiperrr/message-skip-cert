# E12 summary (Round 4)

| | |
|---|---|
| Preregistration | `PREREG_E12.md` |
| SHA-256 | `edbefec351c9d381fa50f3d51e34843547174f6f3fc640e61a921cc5a6b23229` |
| Frozen (UTC) | 20260920T225858Z (recorded 2026-09-20T22:59:21Z in `PREREG_E12.sha256`) |
| Reproduction check | **PASS** — all 8 ClusterA E3 version-(b) means inside the supplied ranges |
| E12-a | **done** (login node, CPU, no job) |
| E12-b | **stopped before submission** — no batched serving path exists; see `E12B_STATUS.md` |

## Reproduction check (step 2a)

| setting | expected | r1 | r2 | r3 | in range |
|---|---|---|---|---|---|
| large/OBQA/Text | [419.6, 430.2] | 419.62 | 430.16 | 423.1 | True |
| large/OBQA/C2C | [27.4, 29.3] | 27.41 | 29.26 | 27.82 | True |
| large/ARC/Text | [573.2, 585.0] | 573.15 | 584.99 | 573.8 | True |
| large/ARC/C2C | [91.2, 92.4] | 92.4 | 91.56 | 91.23 | True |
| medium/OBQA/C2C | [45.6, 50.0] | 47.28 | 49.98 | 45.63 | True |
| medium/ARC/C2C | [76.6, 82.5] | 79.31 | 82.53 | 76.58 | True |
| large/MMLU-Pro/Text | [260.8, 262.7] | 260.82 | 260.96 | 262.68 | True |
| large/MMLU-Pro/C2C | [-0.0, 2.8] | -0.03 | 2.55 | 2.76 | True |

Pairing is **by question id**, not by log position. Version (a)/(b) are the frozen E3 definitions
(version (b) drops the question of each arm's first formal request) and are kept separate everywhere.
"omitted" vs "routed" uses the **recorded routing decision** (`selected == "R"` <=> omitted).

## E12-a headline

1. **p99 is never worse** under the policy — no setting, arm, replay or version.
2. **p90 is worse** under the policy for 2 of the 8 settings, both currently classified as a positive
   saving: `medium/OBQA/C2C` (every replay, every arm, both machines) and `large/MMLU-Pro/Text`
   (ClusterA only — all 3 E3 repeats and all 3 E7 arms; better on ClusterB).
3. **The paired median is negative** in 16 of 58 version-(b) rows, including `large/MMLU-Pro/Text`,
   whose mean saving is +260.8 to +262.7 ms on ClusterA E3 while its median is **-21.0 to -31.8 ms** and
   **59.8-60.6% of queries are slower**.
4. **Mechanism**: routed queries are slower under the policy in 0.846-1.000 of cases (routed paired median
   -25 to -45 ms, the probe cost). The entire saving comes from omitted queries.

### Prereg reporting rule triggered

The branch "if the policy's p90 or p99 is worse ... for any setting currently classified as a positive
saving" **fires**. Per the prereg, the main text must report those tail numbers, state that a positive mean
saving can coexist with a worse tail, and reword Contribution 4 to name the mean explicitly. The
"tails are not worse" branch does not apply.

### Worse-p90 settings, version (b)

| replay | setting | arm | pol p90 | fix p90 | pol p99 | fix p99 |
|---|---|---|---|---|---|---|
| E3_REPEAT1 | large/MMLU-Pro/Text | POLICY | 1346.6 | 1345.6 | 1680.9 | 1729.6 |
| E3_REPEAT2 | large/MMLU-Pro/Text | POLICY | 1345.3 | 1332.8 | 1641.6 | 1716.7 |
| E3_REPEAT3 | large/MMLU-Pro/Text | POLICY | 1370.0 | 1364.9 | 1654.4 | 1741.9 |
| E7 | large/MMLU-Pro/Text | ARGMAX | 1343.3 | 1337.4 | 1686.1 | 1720.5 |
| E7 | large/MMLU-Pro/Text | ORIGINAL | 1341.2 | 1337.4 | 1665.3 | 1720.5 |
| E7 | large/MMLU-Pro/Text | REUSE | 1339.3 | 1337.4 | 1662.9 | 1720.5 |
| E3_REPEAT1 | medium/OBQA/C2C | POLICY | 363.0 | 358.6 | 455.8 | 499.8 |
| E3_REPEAT2 | medium/OBQA/C2C | POLICY | 368.1 | 366.8 | 460.7 | 509.2 |
| E3_REPEAT3 | medium/OBQA/C2C | POLICY | 355.5 | 354.9 | 445.7 | 492.5 |
| E7 | medium/OBQA/C2C | ARGMAX | 362.7 | 361.7 | 462.4 | 505.0 |
| E7 | medium/OBQA/C2C | ORIGINAL | 363.9 | 361.7 | 453.5 | 505.0 |
| E7 | medium/OBQA/C2C | REUSE | 363.0 | 361.7 | 457.2 | 505.0 |
| ClusterB | medium/OBQA/C2C | POLICY | 470.0 | 462.9 | 595.1 | 643.7 |

Full per-replay/arm tables, both versions, with omitted/routed splits: `E12A_SUMMARY.md` and
`results/E12A_per_arm_quantiles.csv` (+ one CSV per replay).

## E12-b

Not submitted, and **not because of the queue**: `job-status -u user` was empty (0 jobs; both debug
positions free). The deployed implementation has no batched serving path at any level — the probe
asserts batch 1, the vendor `runner.request(row, action)` is single-row, and the official C2C
`fuse_and_generate` hard-codes a scalar `instruction_length` and `base[layer, 0]`. Building one means
re-implementing the certified C2C fuser, past the one-job / 50-minute budget. The batch-8 vs batch-1
identity check was not run because there is no batch-8 path to compare against. Options in
`E12B_STATUS.md`; the prereg's own fallback is to report E12-a only and keep Section 7 unchanged.

## Files

- `PREREG_E12.md`, `PREREG_E12.sha256` — preregistration and its hash (written before any timing file was read).
- `E12A_SUMMARY.md`, `results/` — E12-a results.
- `E12B_STATUS.md` — why E12-b stopped, with options.
- `DEVIATIONS.md` — deviations (E12-a: none).
- `scripts/e12a_tails.py`, `scripts/e12a_report.py` — read every `P2_*` folder read-only.
