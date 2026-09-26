# E13 deviations and implementation choices

Preregistration: `PREREG_E13.md`, SHA-256 `2cc25a61f8ba57a2e129319e9aee1dad3c3df93321377130e38da109b92d3b3e`,
recorded 2026-09-21T03:16:48Z. No reporting rule was changed after results were seen.

## A. Deviations from the literal text of the preregistration

1. **Item 3, recomposed saving: what counts as "probe latency" and "action latency".** The per-request records split
   each request into input preparation, probe, selector, action, parse and cleanup (the parts sum exactly to the
   request latency in every replay). I used probe latency = input preparation + probe + selector (everything before
   the action), and action latency = action + parse + cleanup. That way probe + action equals the measured latency of
   the policy request. Input preparation and selector are about 0.003 ms each; parse and cleanup are below 1 ms.
   Check: at alpha = .05 the recomposed saving reproduces the measured version (b) saving within 1 ms in all
   13 replay × setting cells (for example 532.9 vs 532.8 ms, 342.7 vs 342.5 ms).
2. **Item 3, fallback variants.** A fallback variant has no threshold, and the deployed system is then the fixed arm
   (saving 0, no probe). The recomposed-saving table still gives the preregistered formula value (probe still run,
   nothing omitted, so the saving is minus the mean pre-action part), and labels it that way in the `note` column.
3. **Item 10, scope of "every saved raw output".** Covered: every raw multiple-choice output that enters a paper number,
   273,819 outputs in total (`results/item10_scope.csv`). This includes fit, calibration, development, the P2_10 panels,
   held-out, sealed ARC, all replays, the E4 null controls and the E1 port check. Left out: E10 GSM8K (numeric answers,
   so neither multiple-choice parser applies) and the earlier exploratory stages (P2_1–P2_4, P2_7, P2_8,
   P2_E1_DIRECTION, gold-budget and baseline stages), which feed no number in the paper.
4. **Item 11, tokenizers loaded.** The helper and receiver tokenizers (Qwen2.5-7B-Instruct, Qwen3-8B) were loaded on
   CPU from local files so that their chat templates could render the prompts. No model weights were loaded and no
   model was run.

## B. Choices where the preregistration was silent (recorded for completeness)

- **Item 1:** the same 1,000 draws and the same 2,000 × 100 bootstrap as E9-a. The extended samplers make the same
  random calls in the same order: the gain-over-R bootstrap array is identical to `e9a_bootstrap_ratios.npy`, and an
  explicit per-draw reconstruction of the null answer vectors gave 0 mismatches in 7,000 joint draws. Resamples with
  real headroom 0 are undefined, as in E9-a (large/ARC joint: 4 of 2,000).
- **Item 2:** one fresh `default_rng(0)` per population, drawing stratum "R incorrect" first and then "R correct", with
  1,000 draws each. Bootstrap: one `default_rng(0)` stream over 2,000 question resamples; strata are re-formed inside
  each resample, with 100 draws per stratum. The under-matched flag is applied per stratum, as preregistered. The
  "lower bound" reading holds for the gain ratio, and for the best-fixed ratio when the R-correct stratum is
  under-matched. When the R-incorrect stratum is under-matched (medium/OBQA, large/ARC), its direction for the
  best-fixed ratio is not guaranteed analytically.
- **Item 3:** one `default_rng(0).integers(0, N, (2000, N))` index matrix per setting and split, shared by all alphas.
  Retention intervals are percentiles over resamples with G ≠ 0; the share with G ≤ 0 is reported (large/ARC/Text
  dev .068, large/MMLU-Pro/Text dev .015, others 0).
- **Item 3, "largest alpha with κα < G":** a fallback has κ = 0 and meets the condition trivially. Both the literal
  answer and the largest *deployed* alpha are given (`results/item3_largest_alpha.csv`). In all four settings the two
  are the same.
- **Item 4:** one fresh `default_rng(0)` per (setting, n), 200 × `rng.choice(N, n, replace=False)`. The AUROC is
  `sklearn.metrics.roc_auc_score`, the paper's function. Text+fact is sampled from the development split and flagged,
  as preregistered. GSM8K is not included: it has no ProbeMax and no fit-split reference outputs. The overall mean is
  also given without the Text+fact row (n = 200: .907, 20 of 25 settings ≥ .8).
- **Item 4, file times:** mtimes have 1-second resolution on this file system. Found by a keyword scan of every file,
  then manual inspection (log `logs/item4_filetime_scan.txt`). For E10 the same query is answered for its only
  setting (GSM8K/Text).
- **Item 5:** fallback settings have no deployed candidate. n / k / p are given at the smallest-p candidate and at
  q = .05.
- **Item 6:** the Appendix F component panels are the 128-question development panels of
  P2_CONFIDENCE_REFERENCE_BOUNDARIES (small and large, OBQA and ARC). The medium-pair and MMLU-Pro probe records store
  the total only. The probe code has no separate timer for synchronization (a CUDA synchronize ends each interval) or
  for the last-position projection (one timer covers full prefill + projection). For E7 REUSE, the ORIGINAL − REUSE
  difference in the action part on omitted questions is added as a descriptive number; E7 records do not split the
  receiver-only request into prefill and decoding.
- **Item 9:** "mean probe" = probe + selector part of the policy request. The receiver-only request = policy latency
  minus input preparation, probe and selector on omitted version-(b) questions. Means are computed per repeat and
  then averaged over the three repeats. The per-repeat E3 (b) savings recomputed here equal `E3_policy_savings.csv`
  (24 of 24).
- **Item 10:** the P2_10 fourth action (ACW) is not a paper path; it is parsed and reported separately. E1 rows (OBQA
  test questions, not in the stored option-set index) use A–D. E4 outputs are parsed with their displayed option labels.

## C. Items added after the preregistration hash (requested 2026-09-21T04:32:05Z; counting only, no new computation)

- **Item 13** (which settings the E9c helper-aware analysis covers) and **Item 14** (reconciling the E8 D1 counts with
  Item 10). Neither is in `PREREG_E13.md`: both were requested after the E13 report and are factual counts of saved
  records. Script `scripts/item13_14.py`; outputs `results/item13_e9c_settings.csv`, `results/item14_d1_reconciliation.csv`.
- Answers to the earlier NEEDS FROM US (no action taken): no D1 relabel check on E8 (the nine certified policies are
  unaffected); Table 7 matches `results/item7_resplit_all.csv`.
