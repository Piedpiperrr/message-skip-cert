# E22 SUMMARY (Paper A, round 10)

> **E22-1 stop LIFTED by the authors, 2026-09-22T20:48:54Z (DEVIATIONS.md D3).** The preregistered Monte Carlo
> identity check flagged one of the fourteen cells (medium/ARC C2C, +3.28 SE against a 3-SE threshold; the other
> thirteen <= 1.57 SE). A diagnostic over 400 seeds of the identical design showed the sampler is unbiased (mean
> deviation -0.026 SE, grand mean gain 14.5840 vs expectation 14.5854) and that seed 0 - E9-a's stored seed - is
> the most extreme of the 400; with 14 cells a two-sided 3-SE check false-alarms with probability about 3.7%.
> **The numbers below are the preregistered ones, unchanged, and may be used in the paper.**
>
> Ranges and medians are over all seven populations for Text, with large/ARC Text flagged undetermined (lower
> bound; appendix scaled ratio 0.990); M, K, T_sig and C_sig exclude it, as preregistered.
>
> **E22-2 is complete**: its preregistered reproduction gate passes (31/31, incl. large/OBQA Text 46/18,
> C2C 16/35, V1 48/66). Step 0 REPRO: 301 of 301 checks pass (REPRO.md).

Label: POST HOC (E22, PREREG.md); stored outputs only; does not change any primary decision

## E22-1 summary quantities (gain over R)

- **M** = 6 of the 6 determined Text cells: small/OBQA, small/ARC, medium/OBQA, medium/ARC, large/OBQA, large/MMLU-Pro
- **K** = 2 of the 6 determined Text cells: small/OBQA, large/OBQA
- **T_sig** = 2 of the 6 determined Text cells: small/OBQA, large/OBQA
- **C_sig** = 0 of the 5 determined medium/large C2C cells: none
- undetermined Text cells: large/ARC (n_- = 11 > elig_- = 10; ratio 0.900 is a lower bound, appendix scaled ratio * n_-/elig_- = 0.990)
- undetermined C2C cells: none
- Text stratified range (7): 0.787 to 0.969 (unstratified 0.498 to 0.861)
- C2C stratified range (5 medium/large): 1.077 to 1.475 (unstratified 0.986 to 1.705)

### Medians (stratified, 95% bootstrap interval)

- Text over the 7 populations: **0.840** [0.769, 0.936] (unstratified point median 0.742)
- C2C over the 7 populations: **1.201** [0.947, 1.331] (unstratified point median 1.125)
- C2C over the 5 medium/large cells: **1.222** [1.059, 1.448] (unstratified point median 1.246)

## Per cell (both designs)

| population | ref | undet. | stratified ratio [95%] | unstratified ratio [95%] |
|---|---|---|---|---|
| small/OBQA | Text | no | 0.803 [0.687, 0.940] | 0.719 [0.606, 0.845] |
| small/ARC | Text | no | 0.840 [0.680, 1.074] | 0.851 [0.671, 1.080] |
| medium/OBQA | Text | no | 0.969 [0.859, 1.115] | 0.800 [0.680, 0.945] |
| medium/ARC | Text | no | 0.787 [0.601, 1.004] | 0.742 [0.505, 1.057] |
| large/OBQA | Text | no | 0.809 [0.702, 0.924] | 0.547 [0.443, 0.665] |
| large/ARC | Text | yes | 0.900 [0.538, 1.056] | 0.498 [0.263, 0.778] |
| large/MMLU-Pro | Text | no | 0.893 [0.806, 1.006] | 0.861 [0.769, 0.969] |
| small/OBQA | C2C | no | 0.801 [0.694, 0.923] | 0.686 [0.584, 0.804] |
| small/ARC | C2C | no | 0.856 [0.691, 1.078] | 0.747 [0.598, 0.953] |
| medium/OBQA | C2C | no | 1.201 [0.984, 1.517] | 1.125 [0.880, 1.464] |
| medium/ARC | C2C | no | 1.475 [0.964, 2.844] | 1.705 [1.019, 3.449] |
| large/OBQA | C2C | no | 1.077 [0.823, 1.558] | 1.313 [0.882, 2.175] |
| large/ARC | C2C | no | 1.351 [0.800, 3.151] | 0.986 [0.490, 2.970] |
| large/MMLU-Pro | C2C | no | 1.222 [1.067, 1.406] | 1.246 [1.071, 1.447] |

## Active writing constraints

**R3** — branch 3: the abstract, Contribution 1 (title included), the Sec. 4.1 heading and the conclusion must state that whether the null separates Text from C2C depends on how it is matched, giving K, C_sig and both ranges.
  Deciding numbers: K = 2 (>= 4 is False), C_sig = 0.

**R2 (Text)**
- "exceeds the null" allowed only for the M = 6 populations: small/OBQA, small/ARC, medium/OBQA, medium/ARC, large/OBQA, large/MMLU-Pro.
- "significantly" allowed only for the K = 2 populations: small/OBQA, large/OBQA.
- M < 7, so the sentence must name the other populations with their ratios: none; plus the undetermined cell(s) large/ARC

**R2 (C2C)**
- "at the null's level" / "nothing beyond answer volatility" allowed only for: medium/OBQA, medium/ARC, large/OBQA, large/ARC, large/MMLU-Pro; excluded and to be named: none.
- "matches or exceeds" / "reach" allowed: False. Use "are not significantly below" instead.
- "intervals above 1" allowed only for: large/MMLU-Pro.
- small-pair C2C under both designs: small/OBQA stratified 0.801 [0.694, 0.923], unstratified 0.686 [0.584, 0.804]; small/ARC stratified 0.856 [0.691, 1.078], unstratified 0.747 [0.598, 0.953].
- The abstract keeps one sentence on the per-path null in every branch.

**R1** — `results/E22_1_appendix_table.csv` (every cell, both designs, undetermined flagged), `results/E22_2_directions.csv` (E22-2 appendix table), `results/E22_1_table1_cells.csv` (the main-text per-path table with both designs and both medians).

## E22-2 ranges over the seven populations (R4: only ranges may be cited in the main text)

| action | wrong->right share | right->wrong changes | INVALID among S- / S+ changes |
|---|---|---|---|
| Text | 0.384 to 0.909 | 4 to 129 | 0 to 18 / 0 to 14 |
| C2C | 0.281 to 0.667 | 6 to 204 | 0 to 10 / 0 to 8 |
| V1 | 0.338 to 1.000 | 14 to 228 | 0 to 8 / 0 to 13 |
| V2 | 0.370 to 0.875 | 4 to 127 | 0 to 23 / 0 to 13 |
| null g_- | 0.343 to 0.900 | - | - |

## E22-2: wrong->right share minus g_- (percentage points)

Subtraction from `results/E22_2_directions.csv`; see `results/E22_2_share_minus_g.csv` (DEVIATIONS D4).

| population | g_- | Text | C2C | V1 | V2 |
|---|---|---|---|---|---|
| small/OBQA | 0.414 | +10.1 | +10.4 | -0.3 | +5.6 |
| small/ARC | 0.436 | +8.3 | +7.1 | -2.2 | +9.9 |
| medium/OBQA | 0.637 | +1.9 | -10.7 | -3.1 | +0.4 |
| medium/ARC | 0.634 | +17.2 | -19.9 | -5.8 | +6.2 |
| large/OBQA | 0.690 | +16.2 | -5.0 | -1.4 | +1.5 |
| large/ARC | 0.900 | +0.9 | -23.3 | +10.0 | -2.5 |
| large/MMLU-Pro | 0.343 | +4.1 | -6.2 | -0.5 | +2.7 |
