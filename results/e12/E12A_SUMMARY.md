# E12-a: per-query latency distribution from existing records

Prereg `PREREG_E12.md` sha256 `edbefec351c9d381fa50f3d51e34843547174f6f3fc640e61a921cc5a6b23229`, frozen 20260920T225858Z. Login node, CPU only, no job, no model.

## Method (reused unchanged, not re-derived)

- Version **(a)** = all paired panel questions. Version **(b)** = drop every question on which *either*
  compared arm made its first formal request in that replay (each arm's minimum `attempt`). This is the
  frozen E3 rule, taken from `P2_R1_E3POL_REPEAT1_20260919T075315Z/e3_build/e3_metrics.py` (`saving_row`)
  and `P2_R2_ANALYSIS_20260920T002850Z/scripts/common_r2a.py`. (a) and (b) are kept separate everywhere.
- **Pairing is by question id** (records are keyed into dicts by `record["id"]`), never by position in the log.
- **omitted / routed use the recorded routing decision**, not the score: omitted <=> `selected == "R"`.
  E7 and E6 records also carry an explicit `omitted` field; the frozen check
  `omitted == (selected == "R")` in `e7_analysis.py:89` is re-asserted here for every such record.
- Quantiles are `numpy.percentile` defaults (linear interpolation). Paired difference d = fixed - policy,
  so **d < 0 means the query was slower under the policy**.
- Machines are never merged: rows carry `machine` (ClusterB / ClusterA / ClusterA-E7).

## Coverage

Every replay in scope stores per-request timings; **none stores only aggregates**. 58 arm-streams x 2 versions = 116 rows in `results/E12A_per_arm_quantiles.csv`:

| replay | machine | arms | settings |
|---|---|---|---|
| ClusterB | ClusterB | POLICY | 8 |
| E3_REPEAT1 | ClusterA | POLICY | 8 |
| E3_REPEAT2 | ClusterA | POLICY | 8 |
| E3_REPEAT3 | ClusterA | POLICY | 8 |
| E3_MMLU_C2C_FULL | ClusterA | POLICY | 1 |
| E7 | ClusterA-E7 | ARGMAX, ORIGINAL, REUSE | 8 |
| E6_REPLAY | ClusterA-E7 | POLICY | 1 |

## Reproduction check (step 2a) — PASS

Recomputed ClusterA E3 version-(b) paired mean savings, all three repeats, against the supplied ranges:

| setting | expected range | repeat1 | repeat2 | repeat3 | in range |
|---|---|---|---|---|---|
| large/OBQA/Text | [419.6, 430.2] | 419.62 | 430.16 | 423.1 | True |
| large/OBQA/C2C | [27.4, 29.3] | 27.41 | 29.26 | 27.82 | True |
| large/ARC/Text | [573.2, 585.0] | 573.15 | 584.99 | 573.8 | True |
| large/ARC/C2C | [91.2, 92.4] | 92.4 | 91.56 | 91.23 | True |
| medium/OBQA/C2C | [45.6, 50.0] | 47.28 | 49.98 | 45.63 | True |
| medium/ARC/C2C | [76.6, 82.5] | 79.31 | 82.53 | 76.58 | True |
| large/MMLU-Pro/Text | [260.8, 262.7] | 260.82 | 260.96 | 262.68 | True |
| large/MMLU-Pro/C2C | [-0.0, 2.8] | -0.03 | 2.55 | 2.76 | True |

All 8 land inside their range (`results/E12A_reproduction_gate.csv`, `E12A_CHECKS.json`).

## Findings

**1. p99 is never worse under the policy.** In no replay, setting, arm or version does the policy p99
exceed the fixed reference p99 (58 rows checked).

**2. p90 is worse under the policy for 2 of the 8 settings, both currently classified as a positive saving.**
Version (b), 13 of 58 rows:

| replay | setting | arm | policy p90 | fixed p90 | policy p99 | fixed p99 |
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

- `medium/OBQA/C2C` has a worse p90 in **every** replay and every arm, on both machines.
- `large/MMLU-Pro/Text` has a worse p90 on **ClusterA only** (all 3 E3 repeats and all 3 E7 arms); on ClusterB
  its p90 is better (1613.4 vs 1644.1 ms). Machine-dependent, so the two are reported separately.
- Version (a) vs (b) matters here: 5 rows flip, all `large/MMLU-Pro/Text`, all from "not worse" in (a) to
  "worse" in (b) (E3_REPEAT1, E3_REPEAT3, and all three E7 arms). Dropping the cold request removes a large
  fixed-arm outlier and lowers the fixed p90.

**3. The paired median is negative in 16 of 58 rows, including settings with a large positive mean saving.**

| replay | setting | arm | mean saving (ms) | median saving (ms) | frac slower |
|---|---|---|---|---|---|
| E3_MMLU_C2C_FULL | large/MMLU-Pro-FULL/C2C | POLICY | 22.0 | -37.3 | 0.836 |
| E3_REPEAT1 | large/MMLU-Pro/C2C | POLICY | -0.0 | -41.3 | 0.835 |
| E3_REPEAT2 | large/MMLU-Pro/C2C | POLICY | 2.6 | -40.4 | 0.835 |
| E3_REPEAT3 | large/MMLU-Pro/C2C | POLICY | 2.8 | -36.1 | 0.835 |
| E7 | large/MMLU-Pro/C2C | ARGMAX | 85.6 | -33.6 | 0.622 |
| E7 | large/MMLU-Pro/C2C | ORIGINAL | 4.5 | -36.1 | 0.835 |
| E7 | large/MMLU-Pro/C2C | REUSE | 6.9 | -34.2 | 0.827 |
| ClusterB | large/MMLU-Pro/C2C | POLICY | 6.5 | -43.7 | 0.835 |
| E3_REPEAT1 | large/MMLU-Pro/Text | POLICY | 260.8 | -21.0 | 0.606 |
| E3_REPEAT2 | large/MMLU-Pro/Text | POLICY | 261.0 | -32.7 | 0.606 |
| E3_REPEAT3 | large/MMLU-Pro/Text | POLICY | 262.7 | -31.8 | 0.598 |
| E7 | large/MMLU-Pro/Text | ARGMAX | 342.3 | -32.2 | 0.622 |
| E7 | large/MMLU-Pro/Text | ORIGINAL | 261.2 | -33.4 | 0.622 |
| E7 | large/MMLU-Pro/Text | REUSE | 265.2 | -29.7 | 0.622 |
| ClusterB | large/MMLU-Pro/Text | POLICY | 322.1 | -41.3 | 0.622 |
| E7 | medium/OBQA/C2C | ARGMAX | 123.0 | -20.7 | 0.520 |

`large/MMLU-Pro/Text` is the sharpest case: mean saving +260.8 to +262.7 ms on ClusterA E3 (a certified
positive saving) while the **paired median is -21.0 to -31.8 ms and 59.8-60.6% of queries are slower**.

**4. Mechanism: routed queries are slower under the policy essentially always; all saving comes from omitted queries.**
Across every replay and arm, the fraction of *routed* queries that are slower under the policy is 0.846-1.000
(usually exactly 1.00), and the routed paired median is -25 to -45 ms — the probe cost, paid on top of the
same reference work. On *omitted* queries the policy is faster except in `large/MMLU-Pro/C2C`, where even
omitting is not enough: omitted frac slower 0.542-0.596 for the POLICY/ORIGINAL/REUSE arms (the ARGMAX arm is
0.000 there, because it answers from the probe instead of generating).

**5. ARGMAX (largest mean saving) behaves the same way.** Its tail is not systematically worse than the other
E7 arms: it shows the same two worse-p90 settings and no worse p99. Where it helps most (`large/ARC/Text`
p90 32.6 ms vs 1007.0 ms fixed) it helps by answering from the probe on omitted queries; its routed queries
are still slower 100% of the time, and on `medium/OBQA/C2C` it turns the paired median negative (-20.7 ms)
while keeping a +123.0 ms mean.

## Reporting rules triggered (fixed in advance by the prereg)

- "If the policy's p90 or p99 is worse than the fixed reference for any setting currently classified as a
  positive saving" — **TRIGGERED** by `medium/OBQA/C2C` (everywhere) and `large/MMLU-Pro/Text` (ClusterA).
  The main text must report those tail numbers, say that a positive mean saving can coexist with a worse
  tail, and reword Contribution 4 to name the mean explicitly.
- The "tails are not worse" branch does **not** apply.
- The paired median must be given alongside the mean for at least the two example settings; the medians for
  all 8 deployed policies, all replays, are in `results/E12A_reproduction.csv`.

## Files

- `results/E12A_per_arm_quantiles.csv` — every quantity in the prereg, one row per replay/setting/arm/version,
  with `all_`, `om_` (omitted) and `rt_` (routed) blocks.
- `results/E12A_<REPLAY>.csv` — the same rows split per replay.
- `results/E12A_reproduction.csv`, `results/E12A_reproduction_gate.csv`, `results/E12A_CHECKS.json`.
- Script: `scripts/e12a_tails.py` (reads every P2_* folder read-only).
