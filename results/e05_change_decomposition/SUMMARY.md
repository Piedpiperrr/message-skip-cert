# P2_R2_CPU_20260919T220412Z — E5 re-analysis (CPU, saved records only)

**POST-HOC re-analysis (reviewer R2/E5); does not change any primary decision.** Stage folder: `$DATA_DIR/P2_R2_CPU_20260919T220412Z`. Scripts: `scripts/`; tables: `results/*.csv`.
No existing file was modified; no model was run, no job submitted, no GPU used.

## Step 0 — pre-registration (written before any computation)

- `PREREG_R2_E5.md` (verbatim copy of the PRE-REGISTERED RULES block)
- SHA-256: `b2cf79db674416b0e8bd6ad0b4b9859495ac5e1889a1009bcf8fdc4ad79e26d8`
- Recorded (UTC): **2026-09-19T22:04:21Z** — before any number below was computed.

Conventions: q = 0 means fallback (always run the reference). All tests are P[Bin(n, .05) <= k] <= .001 at 20 grid points, deploy = largest accepted q. "Frozen fit thresholds" are the stored ones; INVALID is a label and counts as a disagreement against a valid label.

## E5-a Parser exposure

**X (`results/e5a_exposed_ids.csv`): 341 distinct calibration questions** (208 OBQA, 133 ARC, 0 MMLU-Pro). Counted the way the A8 audit counted them — per (pair, benchmark) — the same set is **355** reviews: large/OBQA 30, small/OBQA 186, large/ARC 26, small/ARC 113; 341 distinct questions because some were reviewed for both pairs.

**Selection rule: NOT random — selected by output content.** A record entered the parser-development review set iff the saved run-time parser and the D1 diagnostic parser disagreed on answer/validity/correctness, or the D1 parse was flagged ambiguous (plus one named single case). Source: `P2_SCORE_SENSITIVITY_20260912T055929Z/analyze_sensitivity.py` lines 136-141 and `case_review.jsonl`. Because selection is content-based, X is enriched for parse-hard outputs; the disagreement rates below differ sharply between X and C \ X and must be reported as such.

Where the reviewed questions landed (all were train-split rows at review time; no split existed yet):

| benchmark | reviewed questions | in calibration | in fit | in development |
|---|---|---|---|---|
| obqa | 629 | 208 | 323 | 98 |
| arc | 390 | 133 | 186 | 71 |

MMLU-Pro: **no MMLU-Pro question was reviewed** during parser development — the V2 parser was frozen 2026-09-12T19:19:38Z and the first MMLU-Pro output was produced 2026-09-16T15:27Z, so no MMLU-Pro output existed. |C ∩ X| = 0 for both MMLU-Pro settings and for X2-OLMo/MMLU-Pro.

### The 20 tests on C \ X with the frozen fit thresholds (`results/e5a_clean_tests.csv`, full grid in `results/e5a_clean_ledger_all_q.csv`)

| setting | N_cal | cal ∩ X | N clean | orig q | clean n/k at orig q | clean p | orig q accepted on C\X? | largest clean accepted q |
|---|---|---|---|---|---|---|---|---|
| small/OBQA/Text | 1366 | 208 | 1158 | 0.0 | — | — | n/a (fallback: no deployed q) | 0.0 |
| small/OBQA/C2C | 1366 | 208 | 1158 | 0.0 | — | — | n/a (fallback: no deployed q) | 0.0 |
| small/ARC/Text | 448 | 133 | 315 | 0.0 | — | — | n/a (fallback: no deployed q) | 0.0 |
| small/ARC/C2C | 448 | 133 | 315 | 0.0 | — | — | n/a (fallback: no deployed q) | 0.0 |
| medium/OBQA/Text | 1366 | 208 | 1158 | 0.0 | — | — | n/a (fallback: no deployed q) | 0.0 |
| medium/OBQA/C2C | 1366 | 208 | 1158 | 0.55 | 640/18 | 0.00439643 | False | 0.5 |
| medium/ARC/Text | 448 | 133 | 315 | 0.0 | — | — | n/a (fallback: no deployed q) | 0.0 |
| medium/ARC/C2C | 448 | 133 | 315 | 0.6 | 210/1 | 0.000252953 | True | 0.6 |
| large/OBQA/Text | 1366 | 208 | 1158 | 0.8 | 908/17 | 7.81388e-07 | True | 0.8 |
| large/OBQA/C2C | 1366 | 208 | 1158 | 0.8 | 908/19 | 5.36037e-06 | True | 0.8 |
| large/ARC/Text | 448 | 133 | 315 | 0.95 | 297/2 | 3.34985e-05 | True | 0.95 |
| large/ARC/C2C | 448 | 133 | 315 | 0.9 | 282/2 | 6.56192e-05 | True | 0.9 |
| large/MMLU-Pro/Text | 6000 | 0 | 6000 | 0.4 | 2358/67 | 1.33558e-07 | True | 0.4 |
| large/MMLU-Pro/C2C | 6000 | 0 | 6000 | 0.4 | 2358/75 | 1.0127e-05 | True | 0.4 |
| X1-Llama/OBQA/Text | 1366 | 208 | 1158 | 0.0 | — | — | n/a (fallback: no deployed q) | 0.0 |
| X1-Llama/OBQA/C2C | 1366 | 208 | 1158 | 0.0 | — | — | n/a (fallback: no deployed q) | 0.0 |
| X1-Llama/ARC/Text | 448 | 133 | 315 | 0.0 | — | — | n/a (fallback: no deployed q) | 0.0 |
| X1-Llama/ARC/C2C | 448 | 133 | 315 | 0.0 | — | — | n/a (fallback: no deployed q) | 0.0 |
| X2-OLMo/OBQA/Text | 1366 | 208 | 1158 | 0.0 | — | — | n/a (fallback: no deployed q) | 0.0 |
| X2-OLMo/ARC/Text | 448 | 133 | 315 | 0.0 | — | — | n/a (fallback: no deployed q) | 0.0 |
| X2-OLMo/MMLU-Pro/Text | 6000 | 0 | 6000 | 0.0 | — | — | n/a (fallback: no deployed q) | 0.0 |

**Outcome.** 7 of the 8 deployed q values survive. **medium/OBQA/C2C is NOT certified without the exposed questions**: at its deployed q = 0.55 the clean calibration set gives n/k = 640/18, p = 4.40e-03 > 1e-3. Its largest clean-accepted q is 0.50. All 13 originally-fallback settings remain fallback on C \ X (no new passes to report), and both MMLU-Pro settings are untouched (|C ∩ X| = 0).

Development recomputed at the largest clean-accepted q, as pre-registered (`results/e5a_dev_at_clean_q.csv`):

| setting | q | dev coverage % | changed/omitted | note |
|---|---|---|---|---|
| medium/OBQA/C2C | 0.55 | 52.6 | 11/390 | ORIGINAL frozen deployment |
| medium/OBQA/C2C | 0.5 | 47.8 | 7/355 | largest clean-accepted q (C \ X) |

### Disagreement rate in X ∩ C vs C \ X (`results/e5a_disagreement_X_vs_clean.csv`)

| setting | X ∩ C | rate | C \ X | rate | full C rate |
|---|---|---|---|---|---|
| small/OBQA/Text | 151/208 | 0.7260 | 447/1158 | 0.3860 | 0.4378 |
| small/OBQA/C2C | 150/208 | 0.7212 | 490/1158 | 0.4231 | 0.4685 |
| small/ARC/Text | 87/133 | 0.6541 | 146/315 | 0.4635 | 0.5201 |
| small/ARC/C2C | 107/133 | 0.8045 | 147/315 | 0.4667 | 0.5670 |
| medium/OBQA/Text | 62/208 | 0.2981 | 286/1158 | 0.2470 | 0.2548 |
| medium/OBQA/C2C | 38/208 | 0.1827 | 204/1158 | 0.1762 | 0.1772 |
| medium/ARC/Text | 25/133 | 0.1880 | 42/315 | 0.1333 | 0.1496 |
| medium/ARC/C2C | 16/133 | 0.1203 | 39/315 | 0.1238 | 0.1228 |
| large/OBQA/Text | 28/208 | 0.1346 | 115/1158 | 0.0993 | 0.1047 |
| large/OBQA/C2C | 24/208 | 0.1154 | 103/1158 | 0.0889 | 0.0930 |
| large/ARC/Text | 5/133 | 0.0376 | 7/315 | 0.0222 | 0.0268 |
| large/ARC/C2C | 10/133 | 0.0752 | 11/315 | 0.0349 | 0.0469 |
| large/MMLU-Pro/Text | — | — | 1295/6000 | 0.2158 | 0.2158 |
| large/MMLU-Pro/C2C | — | — | 1748/6000 | 0.2913 | 0.2913 |
| X1-Llama/OBQA/Text | 98/208 | 0.4712 | 274/1158 | 0.2366 | 0.2723 |
| X1-Llama/OBQA/C2C | 160/208 | 0.7692 | 639/1158 | 0.5518 | 0.5849 |
| X1-Llama/ARC/Text | 65/133 | 0.4887 | 95/315 | 0.3016 | 0.3571 |
| X1-Llama/ARC/C2C | 110/133 | 0.8271 | 163/315 | 0.5175 | 0.6094 |
| X2-OLMo/OBQA/Text | 51/208 | 0.2452 | 269/1158 | 0.2323 | 0.2343 |
| X2-OLMo/ARC/Text | 25/133 | 0.1880 | 70/315 | 0.2222 | 0.2121 |
| X2-OLMo/MMLU-Pro/Text | — | — | 2457/6000 | 0.4095 | 0.4095 |

The exposed questions disagree far more often than the rest (for example small/OBQA/Text .726 vs .386, X1-Llama/ARC/C2C .827 vs .518), exactly as expected from content-based selection. Removing X therefore *lowers* the measured risk almost everywhere; medium/OBQA/C2C still loses its threshold because it also loses calibration mass.

### Independent-parser check (`results/e5a_independent_parser.csv`, grid in `results/e5a_independent_parser_grid.csv`)

Parsers re-run on the saved raw calibration outputs of R and each reference:
- **V2**: `$DATA_DIR/P2_SCORING_V2_20260912T191445Z/scoring_v2.py` (sha256 `d05978f400cf69aa…`)
- **OFFICIAL**: `$DATA_DIR/c2c_reproduction_assets/official_C2C/rosetta/utils/evaluate.py` (sha256 `b341338aecf1cf07…`)
- **D1**: `$DATA_DIR/P2_SCORE_SENSITIVITY_20260912T055929Z/diagnostic_parser_v1.py` (sha256 `6619cafdd9cffb98…`)
- **OFFICIAL** is the official C2C evaluator's `extract_answer_from_content`, executed from the official source; it hard-codes the option set A-D, so it is **not applicable to MMLU-Pro** (up to 10 options) — reported as n/a rather than forced.
- **D1** is the pre-V2 parser version in the repo history (frozen 2026-09-12T06:02:33Z, before V2 at 19:19:38Z).
- Validation: on the X1 C2C calibration rows the run records store the official evaluator's own `official_pred`; our re-execution matches it on **1366/1366 OBQA and 448/448 ARC** rows (`results/e5a_official_pred_crosscheck.csv`).

**D1 vs V2: zero differences in d_b on every one of the 21 calibration sets.** The pre-V2 parser would have produced the identical disagreement labels, so no deployed q depends on the V2 revision.

Official-evaluator labels (differences are counted as rows whose disagreement label d_b changes):

| setting | o_R diff | o_ref diff | d_b diff (in X / in C\X) | n/k at orig q | p | orig q accepted? | largest accepted q |
|---|---|---|---|---|---|---|---|
| small/OBQA/Text | 61 | 78 | 66 (66 / 0) | — | — | n/a (fallback) | 0.0 |
| small/OBQA/C2C | 61 | 2 | 15 (15 / 0) | — | — | n/a (fallback) | 0.0 |
| small/ARC/Text | 50 | 51 | 38 (38 / 0) | — | — | n/a (fallback) | 0.0 |
| small/ARC/C2C | 50 | 3 | 5 (5 / 0) | — | — | n/a (fallback) | 0.0 |
| medium/OBQA/Text | 15 | 1 | 5 (0 / 5) | — | — | n/a (fallback) | 0.0 |
| medium/OBQA/C2C | 15 | 41 | 22 (4 / 18) | 739/18 | 0.000331749 | True | 0.55 |
| medium/ARC/Text | 6 | 0 | 5 (2 / 3) | — | — | n/a (fallback) | 0.0 |
| medium/ARC/C2C | 6 | 17 | 9 (5 / 4) | 290/3 | 0.000249165 | True | 0.6 |
| large/OBQA/Text | 2 | 0 | 1 (1 / 0) | 1064/18 | 1.15505e-08 | True | 0.8 |
| large/OBQA/C2C | 2 | 22 | 21 (21 / 0) | 1064/39 | 0.0231238 | False | 0.7 |
| large/ARC/Text | 0 | 0 | 0 (0 / 0) | 422/4 | 4.8015e-06 | True | 0.95 |
| large/ARC/C2C | 0 | 25 | 21 (21 / 0) | 404/27 | 0.946938 | False | 0.0 |
| large/MMLU-Pro/Text | n/a (A-D only) | n/a (A-D only) | n/a (A-D only) (n/a / n/a) | — | — | n/a |  |
| large/MMLU-Pro/C2C | n/a (A-D only) | n/a (A-D only) | n/a (A-D only) (n/a / n/a) | — | — | n/a |  |
| X1-Llama/OBQA/Text | 61 | 37 | 44 (37 / 7) | — | — | n/a (fallback) | 0.0 |
| X1-Llama/OBQA/C2C | 61 | 102 | 97 (19 / 78) | — | — | n/a (fallback) | 0.0 |
| X1-Llama/ARC/Text | 50 | 26 | 31 (26 / 5) | — | — | n/a (fallback) | 0.0 |
| X1-Llama/ARC/C2C | 50 | 25 | 19 (4 / 15) | — | — | n/a (fallback) | 0.0 |
| X2-OLMo/OBQA/Text | 54 | 80 | 53 (11 / 42) | — | — | n/a (fallback) | 0.0 |
| X2-OLMo/ARC/Text | 36 | 34 | 34 (13 / 21) | — | — | n/a (fallback) | 0.0 |
| X2-OLMo/MMLU-Pro/Text | n/a (A-D only) | n/a (A-D only) | n/a (A-D only) (n/a / n/a) | — | — | n/a |  |

**Two deployed thresholds do not survive the official parser**: large/OBQA/C2C (39/1064 changed, p = 2.31e-02; largest accepted q 0.70) and large/ARC/C2C (27/404, p = 0.947; **fallback**). Both large/Text settings keep their q (large/ARC/Text has zero label differences), the medium C2C settings keep theirs, and the 13 fallbacks stay fallback. For the large pair every official-vs-V2 label difference lies inside X (21 of 21 for both C2C settings), i.e. exactly on the reviewed questions.

## E5-b Re-split stability (seeds 1..200)

Re-splits redraw fit/calibration from fit ∪ calibration with the frozen rule, sizes and grouping; development is untouched; all settings of a benchmark share the re-splits. OBQA/ARC: sorted representatives, `random.Random(seed).shuffle`, first 2100 (OBQA) / 670 (ARC) to fit. MMLU-Pro: the frozen category-quota + SHA-256 ordering rule of `build_candidates.py`, reseeded by its seed string. **Seed 0 reproduces the frozen split exactly for all three benchmarks** (obqa=True, arc=True, mmlu_pro=True; `results/e5b_seed0_check.csv`).
Saved reference outputs exist on the fit rows of all 21 settings, so no setting was skipped.

| setting | orig outcome | cert. rate | match rate | stability | median q [IQR] | median dev cov % | median dev changed/omitted | needed m (m·N_cal/n) |
|---|---|---|---|---|---|---|---|---|
| small/OBQA/Text | fallback q=0 | 0.000 | 1.000 | stable | — | — | — | not attainable (r >= .05) |
| small/OBQA/C2C | fallback q=0 | 0.000 | 1.000 | stable | — | — | — | 1037 (21793) |
| small/ARC/Text | fallback q=0 | 0.000 | 1.000 | stable | — | — | — | not attainable (r >= .05) |
| small/ARC/C2C | fallback q=0 | 0.000 | 1.000 | stable | — | — | — | not attainable (r >= .05) |
| medium/OBQA/Text | fallback q=0 | 0.000 | 1.000 | stable | — | — | — | not attainable (r >= .05) |
| medium/OBQA/C2C | deploy q=0.55 | 1.000 | 1.000 | stable | 0.55 [0.5, 0.55] | 52.43 | 11/389 | 220 (500) |
| medium/ARC/Text | fallback q=0 | 0.000 | 1.000 | stable | — | — | — | 45333 (79333) |
| medium/ARC/C2C | deploy q=0.6 | 0.960 | 0.960 | stable | 0.6 [0.6, 0.6] | 62.54 | 3/187 | 135 (209) |
| large/OBQA/Text | deploy q=0.8 | 1.000 | 1.000 | stable | 0.8 [0.8, 0.8] | 77.76 | 19/577 | 135 (229) |
| large/OBQA/C2C | deploy q=0.8 | 1.000 | 1.000 | stable | 0.8 [0.8, 0.85] | 78.44 | 16/582 | 135 (212) |
| large/ARC/Text | deploy q=0.95 | 1.000 | 1.000 | stable | 0.9 [0.9, 0.95] | 90.3 | 3/270 | 135 (168) |
| large/ARC/C2C | deploy q=0.9 | 1.000 | 1.000 | stable | 0.9 [0.9, 0.9] | 90.3 | 3/270 | 135 (168) |
| large/MMLU-Pro/Text | deploy q=0.4 | 1.000 | 1.000 | stable | 0.4 [0.4, 0.4] | 40.86 | 41/1079 | 181 (753) |
| large/MMLU-Pro/C2C | deploy q=0.4 | 1.000 | 1.000 | stable | 0.4 [0.35, 0.4] | 40.25 | 37/1063 | 135 (525) |
| X1-Llama/OBQA/Text | fallback q=0 | 0.000 | 1.000 | stable | — | — | — | 779 (7494) |
| X1-Llama/OBQA/C2C | fallback q=0 | 0.000 | 1.000 | stable | — | — | — | not attainable (r >= .05) |
| X1-Llama/ARC/Text | fallback q=0 | 0.000 | 1.000 | stable | — | — | — | not attainable (r >= .05) |
| X1-Llama/ARC/C2C | fallback q=0 | 0.000 | 1.000 | stable | — | — | — | 986 (13386) |
| X2-OLMo/OBQA/Text | fallback q=0 | 0.000 | 1.000 | stable | — | — | — | not attainable (r >= .05) |
| X2-OLMo/ARC/Text | fallback q=0 | 0.000 | 1.000 | stable | — | — | — | 417 (3975) |
| X2-OLMo/MMLU-Pro/Text | fallback q=0 | 0.000 | 1.000 | stable | — | — | — | not attainable (r >= .05) |

Per-seed detail: `results/e5b_resplit_per_seed.csv`. Needed-m columns use the grid point with the smallest ORIGINAL p-value, r = k/n there, the smallest m with BinomCDF(floor(r·m); m, .05) <= .001, and m·N_cal/n.

**Every setting is stable (match rate >= .80).** All 8 originally deploying settings certify in >= 96% of re-splits (7 at 100%, medium/ARC/C2C at 96.0%); all 13 fallbacks fall back in 100% of re-splits. The medium-pair statement **"only C2C can be omitted" holds as a property of the pair**: medium C2C is stable-deploy on both OBQA (1.000) and ARC (0.960) and medium Text is stable-fallback on both (1.000). Fallbacks should still be worded "not certified at alpha = .05 with n calibration questions".

## E5-c Null control (7 development populations, INVALID = incorrect)

| population | N | R | oracle{R,T,C} | gain over R (q / pp) | oracle{R,V1,V2} | gain over R (q / pp) | matched-null gain mean [2.5, 97.5] | rho |
|---|---|---|---|---|---|---|---|---|
| small/OBQA | 742 | 285 | 498 | +213 / +28.71 | 488 | +203 / +27.36 | 146.03 [135.0, 157.0] | 0.686 |
| small/ARC | 299 | 110 | 204 | +94 / +31.44 | 200 | +90 / +30.10 | 69.34 [62.0, 75.0] | 0.738 |
| medium/OBQA | 742 | 490 | 593 | +103 / +13.88 | 596 | +106 / +14.29 | 82.71 [76.0, 90.0] | 0.803 |
| medium/ARC | 299 | 217 | 248 | +31 / +10.37 | 245 | +28 / +9.36 | 23.91 [21.0, 27.0] | 0.771 |
| large/OBQA | 742 | 617 | 670 | +53 / +7.14 | 679 | +62 / +8.36 | 37.31 [31.0, 44.0] | 0.704 |
| large/ARC | 299 | 268 | 280 | +12 / +4.01 | 277 | +9 / +3.01 | 6.77 [5.0, 9.0] | 0.564 |
| large/MMLU-Pro | 2641 | 1282 | 1558 | +276 / +10.45 | 1599 | +317 / +12.00 | 244.06 [232.0, 256.0] | 0.884 |

Rate-matched null: 1000 repetitions, numpy default_rng(0), one fresh stream per population; m_Text / m_C2C drawn without replacement from the questions with a non-empty P(x). No population was under-matched (eligible pool vs m: small/OBQA 590 vs 339/350; small/ARC 231 vs 145/160; medium/OBQA 253 vs 174/131; medium/ARC 73 vs 52/48; large/OBQA 166 vs 72/60; large/ARC 27 vs 15/12; large/MMLU-Pro 1115 vs 561/756).

**rho >= 0.8 in 2 of 7 populations; median rho = 0.738.** The pre-registered condition (>= 4 of 7) is NOT met, so contribution 1 and the abstract must be rewritten to "rate-matched content-free perturbations reproduce 73.8% (median) of the headroom" and the "six of seven" statement removed. The main-text null comparison uses gain over R and absolute counts, as pre-registered.

Change decomposition vs R (`results/e5c_change_decomposition.csv`): changed = corrective + harmful + neutral(both wrong).

| population | N | action | correct | changed | corrective | harmful | neutral (both wrong) |
|---|---|---|---|---|---|---|---|
| small/OBQA | 742 | Text | 346 | 339 | 136 | 75 | 128 |
| small/OBQA | 742 | C2C | 366 | 350 | 147 | 66 | 137 |
| small/OBQA | 742 | V1 | 290 | 558 | 164 | 159 | 235 |
| small/OBQA | 742 | V2 | 316 | 213 | 78 | 47 | 88 |
| small/ARC | 299 | Text | 126 | 145 | 55 | 39 | 51 |
| small/ARC | 299 | C2C | 155 | 160 | 69 | 24 | 67 |
| small/ARC | 299 | V1 | 123 | 209 | 65 | 52 | 92 |
| small/ARC | 299 | V2 | 130 | 89 | 38 | 18 | 33 |
| medium/OBQA | 742 | Text | 523 | 174 | 82 | 49 | 43 |
| medium/OBQA | 742 | C2C | 486 | 131 | 44 | 48 | 39 |
| medium/OBQA | 742 | V1 | 482 | 183 | 66 | 74 | 43 |
| medium/OBQA | 742 | V2 | 507 | 152 | 66 | 49 | 37 |
| medium/ARC | 299 | Text | 221 | 52 | 25 | 21 | 6 |
| medium/ARC | 299 | C2C | 202 | 48 | 10 | 25 | 13 |
| medium/ARC | 299 | V1 | 216 | 53 | 19 | 20 | 14 |
| medium/ARC | 299 | V2 | 220 | 36 | 16 | 13 | 7 |
| large/OBQA | 742 | Text | 645 | 72 | 46 | 18 | 8 |
| large/OBQA | 742 | C2C | 598 | 60 | 16 | 35 | 9 |
| large/OBQA | 742 | V1 | 599 | 137 | 48 | 66 | 23 |
| large/OBQA | 742 | V2 | 624 | 68 | 31 | 24 | 13 |
| large/ARC | 299 | Text | 274 | 15 | 10 | 4 | 1 |
| large/ARC | 299 | C2C | 266 | 12 | 4 | 6 | 2 |
| large/ARC | 299 | V1 | 260 | 20 | 6 | 14 | 0 |
| large/ARC | 299 | V2 | 271 | 12 | 7 | 4 | 1 |
| large/MMLU-Pro | 2641 | Text | 1319 | 561 | 166 | 129 | 266 |
| large/MMLU-Pro | 2641 | C2C | 1233 | 756 | 155 | 204 | 397 |
| large/MMLU-Pro | 2641 | V1 | 1286 | 914 | 232 | 228 | 454 |
| large/MMLU-Pro | 2641 | V2 | 1306 | 535 | 151 | 127 | 257 |

## E5-e Cross-family INVALID (7 settings)

Disagreement decomposition; two INVALIDs count as agreement (`results/e5e_disagreement_split.csv`):

| setting | split | N | disagreements | both valid & different | only R INVALID | only ref INVALID | R INVALID % | ref INVALID % |
|---|---|---|---|---|---|---|---|---|
| X1-Llama/OBQA/Text | cal | 1366 | 372 | 302 | 47 | 23 | 4.47 | 2.71 |
| X1-Llama/OBQA/Text | dev | 742 | 191 | 158 | 19 | 14 | 3.37 | 2.70 |
| X1-Llama/OBQA/C2C | cal | 1366 | 799 | 650 | 54 | 95 | 4.47 | 7.47 |
| X1-Llama/OBQA/C2C | dev | 742 | 427 | 359 | 21 | 47 | 3.37 | 6.87 |
| X1-Llama/ARC/Text | cal | 448 | 160 | 108 | 38 | 14 | 11.16 | 5.80 |
| X1-Llama/ARC/Text | dev | 299 | 88 | 62 | 22 | 4 | 10.70 | 4.68 |
| X1-Llama/ARC/C2C | cal | 448 | 273 | 208 | 45 | 20 | 11.16 | 5.58 |
| X1-Llama/ARC/C2C | dev | 299 | 174 | 127 | 31 | 16 | 10.70 | 5.69 |
| X2-OLMo/OBQA/Text | cal | 1366 | 320 | 248 | 25 | 47 | 4.32 | 5.93 |
| X2-OLMo/OBQA/Text | dev | 742 | 172 | 131 | 18 | 23 | 2.83 | 3.50 |
| X2-OLMo/ARC/Text | cal | 448 | 95 | 48 | 26 | 21 | 9.15 | 8.04 |
| X2-OLMo/ARC/Text | dev | 299 | 67 | 40 | 22 | 5 | 12.04 | 6.35 |
| X2-OLMo/MMLU-Pro/Text | cal | 6000 | 2457 | 1489 | 604 | 364 | 17.08 | 13.08 |
| X2-OLMo/MMLU-Pro/Text | dev | 2641 | 1112 | 675 | 262 | 175 | 17.04 | 13.74 |

Valid-only diagnostic — frozen fit thresholds, the same 20 tests restricted to questions where **both** outputs parse. **Descriptive only; not deployable** (the filter uses the reference output, which is what omission avoids). Grid in `results/e5e_valid_only_grid.csv`.

| setting | cal valid-only / N | valid-only deployed q | dev valid-only / N | dev disagreement (valid-only vs all) | valid-only AUROC |
|---|---|---|---|---|---|
| X1-Llama/OBQA/Text | 1282/1366 | 0.0 | 703/742 | 0.2248 vs 0.2574 | 0.726 |
| X1-Llama/OBQA/C2C | 1210/1366 | 0.0 | 670/742 | 0.5358 vs 0.5755 | 0.648 |
| X1-Llama/ARC/Text | 384/448 | 0.0 | 263/299 | 0.2357 vs 0.2943 | 0.683 |
| X1-Llama/ARC/C2C | 378/448 | 0.0 | 251/299 | 0.5060 vs 0.5819 | 0.637 |
| X2-OLMo/OBQA/Text | 1260/1366 | 0.45 | 698/742 | 0.1877 vs 0.2318 | 0.855 |
| X2-OLMo/ARC/Text | 386/448 | 0.4 | 258/299 | 0.1550 vs 0.2241 | 0.881 |
| X2-OLMo/MMLU-Pro/Text | 4611/6000 | 0.05 | 2016/2641 | 0.3348 vs 0.4211 | 0.701 |

**All three OLMo benchmarks certify on valid-only questions** (OBQA q = 0.45, ARC q = 0.40, MMLU-Pro q = 0.05), so by the pre-registered rule the paper states that the OLMo fallback is **driven by answer format** and withdraws the size statement for those benchmarks. The four Llama (X1) settings still fall back valid-only, so for them the paper keeps "not accuracy or size alone" and reports the INVALID share.

## Checks

- **All 21/21 settings reproduce the frozen calibration ledgers exactly** (20 grid points each, n and k, frozen thresholds on the full calibration set) before any subset was removed: `results/validation_checks.csv`.
- Seed 0 of the E5-b re-split rule reproduces the frozen fit/calibration split for OBQA, ARC and MMLU-Pro.
- E5-c oracle counts reproduce `P2_R1_EXP_20260919T050555Z/results/e4_null_controls.csv` for all 7 populations (both oracle{R,Text,C2C} and oracle{R,V1,V2}).
- The official-extractor re-implementation matches the evaluator-produced `official_pred` on all 1,814 X1 C2C calibration rows.

## Facts F1-F4 (`results/facts_F1_F4.csv`)

**F1. How the 4,208-question OBQA pool was drawn from the 4,957-question official training split**

Two steps, both label-blind. (1) Exclusion: 5 of 4,957 rows removed as DUPLICATE_EXACT_CONTENT_WITHIN_TRAIN (exact-content aliases; each maps to a retained row), leaving 4,952 eligible rows. (2) Deterministic hash split, no RNG: per row split_digest = SHA256(b"gate2b-split-v1\0" + row_fingerprint_bytes); rows sorted by (split_digest, dataset_id, raw example_id); first floor(70%) -> router_train (3,466), next floor(15%) -> router_dev (742), remainder -> untouched_final_holdout (744). The 4,208-question pool = router_train + router_dev; the 744 holdout rows are excluded from it. It is a deterministic content-hash partition, not a random sample and not a difficulty/answer filter.

Sources: $HOME_DIR/analysis/channel_selection_gate2/gate2b_labelblind_staging_hardened_gpu_v2_20260726/gate2b_staging_report.md (section "Deterministic split"); $HOME_DIR/analysis/channel_selection_gate2/gate2b_labelblind_staging_hardened_gpu_v2_20260726/split_summary.tsv; $HOME_DIR/analysis/channel_selection_gate2/gate2b_labelblind_staging_hardened_gpu_v2_20260726/excluded_rows.tsv (5 rows); $DATA_DIR/gate2c_train_dev_question_staging_v1_20260727/source_access_receipt.json (source_parquet_rows 4957, train_dev_rows_selected 4208); $DATA_DIR/gate2d_final_holdout_evaluation_20260727/final_holdout_report.md (3466/742/744, excluded 5); staged into P2 via P2_5_20260910T072811Z/prepare_p2_5.py (reads router_{train,dev}_questions.arrow)

**F2. Why MMLU-Pro was run for the large pair only**

Decision record exists: Plan C (large pair only) was chosen on GPU budget and calendar grounds, then authorized by the user. Stage1 cost: Plan A (small+medium+large) 154.40 GPUh / 77.20 wall h, Plan B 105.96 / 52.98, Plan C 52.14 / 26.07, Plan D 155.39 / 77.69; only C was rated MODERATE_RISK, A/B/D HIGH_RISK, and only C fit before the deadline. C keeps the complete population (12,032 rows / 11,641 groups) and 6,000 calibration groups rather than shrinking calibration to pay for more pairs. The recorded cost of C: it uses the already-stronger large regime and therefore cannot speak to cross-scale behaviour on MMLU-Pro. Authorization: "Work user instruction: GO MMLU-Pro Plan C, exactly two Stage1 PBS jobs, no E2E".

Sources: P2_MMLU_PRO_BREADTH_PROTOCOL_AND_COST_REVIEW_20260915T224801Z/POPULATION_PLAN_COMPARISON.md (size, benefit/weakness and cost tables); P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json (field "authorization")

**F3. Why thinking was disabled, with the file/line that sets it**

Inherited verbatim from the official C2C evaluator, which renders every chat prompt with enable_thinking=False; the project protocol copies that setting so its prompts stay byte-identical to the official pipeline. Official: script/evaluation/unified_evaluator.py:427 (also 856, 868, 926). Project runtimes: P2_5_20260910T072811Z/protocol_min.py:249 and P2_10_20260911T122423Z/protocol_min.py:249 (apply_chat_template(..., add_generation_prompt=True, enable_thinking=False)); medium P2_MEDIUM_PAIR_.../execution_retry1_.../src/native_runtime.py:124 and :143; MMLU-Pro P2_MMLU_PRO_BREADTH_STAGE1_.../src/native_runtime.py:153 and :172; cross-family P2_R1_XFAM_.../src/run_x2.py:85-86. Recorded as a frozen config field enable_thinking=false (P2_5_20260910T072811Z/frozen_config.json:92).

Sources: $DATA_DIR/c2c_reproduction_assets/official_C2C/script/evaluation/unified_evaluator.py:427; P2_5_20260910T072811Z/protocol_min.py:249; P2_5_20260910T072811Z/frozen_config.json:92

**F4. HF model revisions (commit hashes) of the small-pair and large-pair helpers and receivers**

small helper Qwen/Qwen2.5-0.5B-Instruct @ 7ae557604adf67be50417f59c2c2f167def9a775; small receiver Qwen/Qwen3-0.6B @ c1899de289a04d12100db370d81485cdf75e47ca; large helper Qwen/Qwen2.5-7B-Instruct @ a09a35458c702b33eeacc393d103063234e8bc28; large receiver Qwen/Qwen3-8B @ b968826d9c46dd6066d109eabc6255188de91218. C2C fuser (large/MMLU-Pro) nics-efc/C2C_Fuser @ f01fc3258b305e280e04c7238f4f2cf31b7dc70d; small-pair fuser config recorded as qwen3_0.6b+qwen2.5_0.5b_Fuser__8704f555c6b4a60b764de7d755e6f1daf21a57ef.

Sources: P2_5_20260910T072811Z/frozen_config.json ("models"); P2_6_20260910T164138Z/frozen_config.json ("models"); P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/MODEL_SOURCE_INDEX.json; P2_R1_EXP_20260919T050555Z/records/fuser_configs/

## Files

- `results/e5a_clean_ledger_all_q.csv`
- `results/e5a_clean_tests.csv`
- `results/e5a_dev_at_clean_q.csv`
- `results/e5a_disagreement_X_vs_clean.csv`
- `results/e5a_exposed_ids.csv`
- `results/e5a_independent_parser.csv`
- `results/e5a_independent_parser_grid.csv`
- `results/e5a_official_pred_crosscheck.csv`
- `results/e5a_parser_sources.csv`
- `results/e5a_review_split_membership.csv`
- `results/e5b_resplit_per_seed.csv`
- `results/e5b_resplit_stability.csv`
- `results/e5b_seed0_check.csv`
- `results/e5c_change_decomposition.csv`
- `results/e5c_meta.csv`
- `results/e5c_null_control.csv`
- `results/e5e_disagreement_split.csv`
- `results/e5e_valid_only_diagnostic.csv`
- `results/e5e_valid_only_grid.csv`
- `results/facts_F1_F4.csv`
- `results/validation_checks.csv`

Scripts: `scripts/e5a.py`, `scripts/e5a_c.py`, `scripts/e5a_dev.py`, `scripts/e5b.py`, `scripts/e5c.py`, `scripts/e5e.py`, `scripts/facts.py`, `scripts/make_summary.py`, `scripts/parsers_r2.py`, `scripts/r2_common.py`, `scripts/rawio.py`, `scripts/validate.py`.
