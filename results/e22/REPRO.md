# E22 REPRO (step 0)

Every check re-derives a stored number from the stored outputs and compares it with what is on record.
The E9-a and E13 Item-2 scripts were re-executed **unchanged**; only the directory they write to was
redirected into this stage (`results/step0/e9a_rerun/`, `results/step0/e13_rerun/`). No earlier result
directory was written to.

**301 of 301 checks pass.**

| group | pass / total |
|---|---|
| 0a | 34 / 34 |
| 0b | 20 / 20 |
| 0c | 133 / 133 |
| 0d | 114 / 114 |

## What each group covers

- **0a** — E9-a's unstratified per-reference design re-run with its stored seed (`numpy.random.default_rng(0)`, recorded in `e9a_main.py` and `e9a_boot.py`): all 14 point ratios, the two point medians over the seven populations (Text 0.742, C2C 1.125) and all 16 bootstrap intervals including the two stored median intervals (Text [0.644, 0.840], C2C [0.895, 1.349]) reproduce exactly to 3 decimals. The seed WAS stored, so the 0.01 tolerance clause did not apply.
- **0b** — the stratified-joint variant is E13 Item 2 (`P2_R5_E13_20260921T031606Z/scripts/item2.py`, outputs `results/item2_stratified_ratios.csv`). Its stored medians are 0.849 (gain over R) and 0.967 (best fixed); both the median of the seven stored per-population ratios and a full re-run of `item2.point()` reproduce them, and every per-population ratio matches.
- **0c** — the real gain over R per reference-population cell, recomputed from the loaders, equals E9-a's stored `real_gain_R_Text` / `real_gain_R_C2C` (listed in `results/step0/step0_real_gains.csv`), and the E5 change decomposition (`P2_R2_CPU_20260919T220412Z/results/e5c_change_decomposition.csv`) reproduces for all seven populations and all four actions, including large/OBQA Text 46 / 18, C2C 16 / 35, V1 48 / 66.
- **0d** — Table 1 (`P2_FINAL_ABSTRACT_REVISION_20260918T193147Z/paper/tab_main_complementarity.tex`): N, correct R / Text / C2C, oracle and gain (pp) for all seven rows; tab:null: correct R / V1 / V2 and the percentage changed by V1 and V2; tab:overlap: a, b, c, c_same, with n(Text) = a + c and n(C2C) = b + c (72 and 60 on large/OBQA) and the eligible counts, including the 73 eligible questions on medium/ARC.

## Real gains per cell (0c)

| population | reference | real gain over R | stored E9-a |
|---|---|---|---|
| small/OBQA | Text | 136 | 136 |
| small/OBQA | C2C | 147 | 147 |
| small/ARC | Text | 55 | 55 |
| small/ARC | C2C | 69 | 69 |
| medium/OBQA | Text | 82 | 82 |
| medium/OBQA | C2C | 44 | 44 |
| medium/ARC | Text | 25 | 25 |
| medium/ARC | C2C | 10 | 10 |
| large/OBQA | Text | 46 | 46 |
| large/OBQA | C2C | 16 | 16 |
| large/ARC | Text | 10 | 10 |
| large/ARC | C2C | 4 | 4 |
| large/MMLU-Pro | Text | 166 | 166 |
| large/MMLU-Pro | C2C | 155 | 155 |

## Convention recorded for E22-1

P(x) is built exactly as E9-a builds it (`e9a_common.Pop.__init__`): the SET of answers of V1 (mapped back to the original option order) and V2 at x that differ from o_R(x), so V1 = V2 counts once. **INVALID is INCLUDED in P(x)** as an ordinary pool member and never equals gold, so it contributes 0 to g_-. Seed: E9-a's stored seed, `numpy.random.default_rng(0)`, one fresh stream per population.

Full per-check tables: `results/step0/step0_checks_point.csv`, `results/step0/step0_checks_boot.csv`.
