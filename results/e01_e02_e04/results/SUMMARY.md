# P2_R1_EXP results (ClusterA)

Generated 2026-09-19T09:06:16.185373+00:00 by `src/ClusterA/make_summary_ClusterA.py` from the CSVs named below. Jobs: 7634910 (E1 OURS, E4, E2b; ClusterA debug, 2 nodes) and 7635393 (E1FIX: E1 OFFICIAL rerun + large ARC R/C2C; D4, D5). Output hashes were computed before any gold read (`OUTPUT_HASHES.json`, frozen `analyze_r1.py`) and re-verified unchanged before the checks. Parser: frozen P2_SCORING_V2 `parse_answer` (INVALID kept in N, counted wrong). The frozen analysis ran through the adapter `src/ClusterA/analyze_r1_ClusterA.py` (D6); its own summary is `SUMMARY_analyze_r1.md`.

## 1. Reproduction checks (ClusterA vs saved ClusterB) — ALL PASS

Criteria were fixed before looking at the results (header of `src/ClusterA/repro_checks_ClusterA.py`). (a) PASS = V0 correct equals Table 1 R and parsed agreement N/N. (b) PASS = correct equals Table 1 and parsed agreement 299/299. (c) PASS = max |dp| of the historical D <= 1e-3 and no routing flips at its deployed threshold.

**(a) E4 V0 vs saved ClusterB R** (`repro_checks_a_e4_V0.csv`)

| pair | pop | N | Table 1 R | ClusterB saved R | ClusterA V0 | parsed agree | raw exact | result |
|---|---|---|---|---|---|---|---|---|
| small | obqa | 742 | 285 | 285 | 285 | 742/742 | 742/742 | PASS |
| small | arc | 299 | 110 | 110 | 110 | 299/299 | 299/299 | PASS |
| medium | obqa | 742 | 490 | 490 | 490 | 742/742 | 742/742 | PASS |
| medium | arc | 299 | 217 | 217 | 217 | 299/299 | 299/299 | PASS |
| large | obqa | 742 | 617 | 617 | 617 | 742/742 | 742/742 | PASS |
| large | arc | 299 | 268 | 268 | 268 | 299/299 | 299/299 | PASS |
| large | mmlu_pro | 2641 | 1282 | 1282 | 1282 | 2641/2641 | 2641/2641 | PASS |

**(b) E1FIX large ARC dev (299) vs saved ClusterB** (`repro_checks_b_large_arc.csv`; ClusterB source P2_9 `results/large/validation_cases.jsonl`)

| action | Table 1 | ClusterB saved | ClusterA | parsed agree | raw exact | result |
|---|---|---|---|---|---|---|
| R | 268 | 268 | 268 | 299/299 | 299/299 | PASS |
| C2C | 266 | 266 | 266 | 299/299 | 299/299 | PASS |

**(c) E2b large/OBQA dev features vs saved ClusterB features** (`repro_checks_c_features.csv`)

| N | dim | max abs dz | bit-identical vectors | max abs dp (hist. D) | routed ClusterA | routed ClusterB | flips | result |
|---|---|---|---|---|---|---|---|---|
| 742 | 8192 | 0.0 | 742 | 0.0 | 230 | 230 | 0 | PASS |

Per-question differences: `repro_mismatches.csv`.

## 2. E1 C2C port fidelity (official OBQA test, N=500)

Correct counts use the V2 parser; 'official eval.' is the official evaluator's own `is_correct` count. Small C2C OFFICIAL = task7 CSV (job 164991, reused, as frozen). Sources: `e1_accuracy.csv`, `e1_agreement.csv`, `e1_per_question.csv`, `e1_disagreements.csv`.

| pair | action | OFFICIAL correct | official eval. | OURS correct | parsed agree | raw exact | prompts identical (q0-2) |
|---|---|---|---|---|---|---|---|
| small | Receiver-only | 191 | 198 | 191 | 500/500 | 500/500 | True |
| small | C2C | 263 | 263 | 263 | 500/500 | 500/500 | True |
| medium | Receiver-only | 327 | 326 | 327 | 500/500 | 500/500 | True |
| medium | C2C | 317 | 321 | 317 | 500/500 | 500/500 | True |
| large | Receiver-only | 425 | 425 | 425 | 500/500 | 500/500 | True |
| large | C2C | 405 | 395 | 405 | 500/500 | 500/500 | True |

- small OFFICIAL: C2C 263 vs R 191 -> C2C above R
- small OURS: C2C 263 vs R 191 -> C2C above R
- medium OFFICIAL: C2C 317 vs R 327 -> C2C below R
- medium OURS: C2C 317 vs R 327 -> C2C below R
- large OFFICIAL: C2C 405 vs R 425 -> C2C below R
- large OURS: C2C 405 vs R 425 -> C2C below R

## 3. E4 null controls (receiver-only)

R = saved ClusterB development outputs (paper); V0 = unchanged rerun; V1 = options rotated by one; V2 = another question's helper message. Change rate = % of N with a different answer from R (INVALID as a symbol). Gain = (oracle - best single)/N in pp. Source: `e4_null_controls.csv`.

| population | N | R | V0 | V1 | V2 | chg R-V0 % | chg R-V1 % | chg R-V2 % | oracle{R,V1,V2} | best | gain pp | paper oracle{R,T,C} | paper gain pp | = Table 1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| small/obqa | 742 | 285 | 285 | 290 | 316 | 0.00 | 75.2 | 28.71 | 488 | 316 | 23.18 | 498 | 17.79 | True |
| small/arc | 299 | 110 | 110 | 123 | 130 | 0.00 | 69.9 | 29.77 | 200 | 130 | 23.41 | 204 | 16.39 | True |
| medium/obqa | 742 | 490 | 490 | 482 | 507 | 0.00 | 24.66 | 20.49 | 596 | 507 | 11.99 | 593 | 9.43 | True |
| medium/arc | 299 | 217 | 217 | 216 | 220 | 0.00 | 17.73 | 12.04 | 245 | 220 | 8.36 | 248 | 9.03 | True |
| large/obqa | 742 | 617 | 617 | 599 | 624 | 0.00 | 18.46 | 9.16 | 679 | 624 | 7.41 | 670 | 3.37 | True |
| large/arc | 299 | 268 | 268 | 260 | 271 | 0.00 | 6.69 | 4.01 | 277 | 271 | 2.01 | 280 | 2.01 | True |
| large/mmlu_pro | 2641 | 1282 | 1282 | 1286 | 1306 | 0.00 | 34.61 | 20.26 | 1599 | 1306 | 11.09 | 1558 | 9.05 | True |

## 4. Learned control D (POST-HOC, reviewer R1; 14 settings)

Code: P2_R1_CPU `data_r1`/`common_r1`, frozen LR of `fit_head.py`, fit split only, target 1[o_R != o_b], fit-split order-statistic thresholds, deploy = largest q with P[Bin(n,.05) <= k] <= .001 (0 = fallback). '*' = historically tested (P2_RISK_CALIBRATION_BINARY). 'unchanged' = copied from P2_R1_CPU `results/item4_learned_D.csv`; 'NEW' = this analysis (`src/ClusterA/d_certification_ClusterA.py`). Source: `d_certification.csv`; new-setting ledgers and fit checks: `d_certification_new_ledgers.csv`, `d_certification_new_fit_checks.csv`.

| setting | deployed q | cal n/k | dev N | dev coverage % | dev changed/omitted | dev AUROC | status |
|---|---|---|---|---|---|---|---|
| small/OBQA/Text | 0.0 | - | 742 | 0.0 | N/A (fallback) | 0.553 | q,cal: unchanged; dev: NEW |
| small/OBQA/C2C | 0.0 | - | 742 | 0.0 | N/A (fallback) | 0.638 | q,cal: unchanged; dev: NEW |
| small/ARC/Text | 0.0 | - | 299 | 0.0 | N/A (fallback) | 0.548 | q,cal: unchanged; dev: NEW |
| small/ARC/C2C | 0.0 | - | 299 | 0.0 | N/A (fallback) | 0.628 | q,cal: unchanged; dev: NEW |
| medium/OBQA/Text | 0.0 | - | 742 | 0.0 | N/A (fallback) | 0.686 | q,cal: NEW; dev: NEW |
| medium/OBQA/C2C | 0.0 | - | 742 | 0.0 | N/A (fallback) | 0.750 | q,cal: NEW; dev: NEW |
| medium/ARC/Text | 0.0 | - | 299 | 0.0 | N/A (fallback) | 0.695 | q,cal: NEW; dev: NEW |
| medium/ARC/C2C | 0.0 | - | 299 | 0.0 | N/A (fallback) | 0.712 | q,cal: NEW; dev: NEW |
| large/OBQA/Text * | 0.3 | 380/6 | 742 | 30.997304582210244 | 6/230 | 0.763 | q,cal: unchanged; dev: unchanged |
| large/OBQA/C2C | 0.55 | 698/15 | 742 | 53.77358490566038 | 13/399 | 0.760 | q,cal: unchanged; dev: unchanged |
| large/ARC/Text | 0.9 | 401/7 | 299 | 90.97 | 7/272 | 0.878 | q,cal: unchanged; dev: NEW |
| large/ARC/C2C | 0.65 | 303/4 | 299 | 64.88 | 4/194 | 0.772 | q,cal: unchanged; dev: NEW |
| large/MMLU-Pro/Text | 0.05 | 291/1 | 2641 | 4.85 | 5/128 | 0.640 | q,cal: NEW; dev: NEW |
| large/MMLU-Pro/C2C | 0.0 | - | 2641 | 0.0 | N/A (fallback) | 0.743 | q,cal: NEW; dev: NEW |

## Other outputs

- `e2b_features.csv`: inventory of the E2b feature files (frozen analyze_r1.py).
- `SUMMARY_analyze_r1.md`: the frozen script's own summary.
