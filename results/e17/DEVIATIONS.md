# E17 deviations and implementation choices

Preregistration: `PREREG.md`, SHA-256 `2efda6906533bd16dd2bc3ff58ba6c0b9986543984a8fbb65ccb698f6d21863e`, hashed 2026-09-21T18:31:26Z.
First new computation 2026-09-21T18:35:03Z (`scripts/step2.py`). No analysis or writing rule was changed after any number was seen.

## A. Departures from the preregistered text

1. **E17-3: test split disagreement exists only on the omitted questions.** The sealed ARC run executed R only on the
   questions each policy omitted (`selected == R`). On routed questions only the reference was run, so o_R is not stored.
   Consequences:
   - The per-split row "test" gives d over the omitted questions of that setting's own sealed policy: Text 1,100 of 1,172,
     C2C 1,047 of 1,172.
   - Median u, share u == 0 and reference INVALID are given both on that subset and on all 1,172 (`test_all_*` columns).
   - The preregistered Fisher test "fit+cal vs test" is computed on the matched region only: fit+cal restricted to
     u <= the frozen tau, the region in which R was run on test (1,059 / 1,007 fit+cal questions). An unrestricted fit+cal
     rate cannot be compared with a test rate observed only below tau.
   - Everything else in E17-3 (cal vs dev, fit vs cal, MH, both permutation tests) is as preregistered, and none of it uses
     the test split.

## B. Choices where the preregistration was silent

- **Loaders.** The 26 Qwen/X1/X2 settings use the E13 → E11 loaders unchanged (`e11_common.load`, `e13_settings.load_fit`).
  X3 (Llama-3.1-8B) is read the way `P2_R6_X3.../src/analyze_x3.py` reads it:
  - representatives from `records/populations/{ds}_{split}.jsonl`;
  - u = `P.ProbeMax`; answers = `parsed`, INVALID on runtime error;
  - thresholds = fit order statistics.

  That script is not imported, because it runs its analysis at import. Text+fact has no fit reference outputs, so its fit
  split carries u only (the large-OBQA fit probe scores); E17-2 needs only fit u, and E17-5 needs only N_fit.
  Unparseable answers are normalized to `INVALID` (None → INVALID) before comparing. Step 2 check (0) confirms that all 28
  certification outcomes reproduce with these loaders. `cache/data28.pkl` is a pickle of the loaded arrays, reused by the
  item scripts.
- **E17-1.** "p" is P[Bin(n0, .05) <= k0] on cal. It is n/a when n0 = 0 (Llama). "tau = 0 candidates" are the fit-grid
  thresholds exactly equal to 0.0. A tau = 0 candidate omits exactly the u = 0 calibration questions; this equality is
  asserted per row in `E17_1_tau0_candidates.csv` (`equals_u0_rule_on_cal`).
- **E17-2.** Candidates = `thresholds()` (the same fit order-statistic function) applied to fit u > 0, with q = 1 omitting
  every cal question with u > 0. When a setting falls back, the smallest-p candidate is listed as descriptive.
- **E17-3.**
  - Fisher ORs are odds of disagreement in the first-named split over the second (`OR_cal_vs_dev` = cal:dev).
  - The MH OR is dev vs cal, with the Robins-Breslow-Greenland 95% CI, computed by hand because statsmodels is not in the env.
  - Permutation p is (1 + #{|T*| >= |T|}) / 10,001; the plain share #/10,000 is also given. The labels are permuted with
    `numpy.random.default_rng(0).permutation`, 10,000 times.
  - The control statistic is mean(x | cal) − mean(x | fit).
  - All 747 cal+dev and all 1,118 fit+cal ARC questions appear in all 10 settings, so x_i always averages 10 indicators.
- **E17-4.** Checks on the differing output's full raw text:
  - (i) regex `^\s*([A-D])[.):]`.
  - (ii) the text after that match, with whitespace collapsed and lowercased, equals that option's text or starts with it.
  - (iii) no match of `(?<![A-Za-z])[A-D][.):]` in the text after the first match.
  - (v) V2 label == letter (i).
  - (iv) the official label from `parsers_r2.label_official`; the branch and the math-indicator substrings come from the
    E5-a follow-up `official_branch` function, exec'd from source as in E14.

  E17-4b: V2 labels re-parsed from the stored E9b raw outputs equal the stored answers (0 mismatches). All 744 held-out
  items are A-D.
- **E17-5.**
  - AUROC is `sklearn.metrics.roc_auc_score` (ties count 1/2). Prevalence is the cal disagreement rate under the paper
    convention.
  - N_cal for the MMLU-Pro settings is the n of the q = 1 test (6,000 in all seven). N_fit is the number of fit units
    (670 / 2,100 / 3,000).
  - Simulations: disagreement ~ Bernoulli(prevalence) per question. The RNG is a fresh `default_rng(0)` for each setting
    and run (main, sensitivity), each bisection step (common random numbers across steps) and each grid cell. Draws come
    in chunks of 250 simulations.
  - Modal q and median coverage are over the certified simulations.
  - Bisection: AUROC in [.5, .9999], stopped when the interval is narrower than .001; the midpoint is reported.
  - (c) contour: the first upward crossing of P = .5 along the 9 grid AUROCs, linearly interpolated. "<= .60" / "> .98"
    when there is no crossing inside the grid.
  - (a) ratio = inf when FPR = 0; candidates with n = 0 are skipped.
- **E17-6.** Category = the group's `category` field in the MMLU-Pro split files (`splits/{fit,cal,dev}_groups.json`).
  Per-category thresholds use the same `thresholds()` function on that category's fit groups. Both delta = .001 and
  delta = .001/14 are reported.

## C. Execution notes

- All scripts were re-run under a file-open audit hook (`scripts/run_audited.py`). The files opened are listed in
  `logs/files_opened_*.txt`, and the re-run outputs are compared byte-for-byte with the first run (`logs/run1/`).
- `__pycache__` state of the reused script folders: `logs/pycache_before.txt` vs `logs/pycache_after.txt`.
- No existing result file was modified. All outputs are under this stage directory.
