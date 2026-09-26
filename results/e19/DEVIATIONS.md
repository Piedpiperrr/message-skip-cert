# E19 deviations and execution notes

Preregistration: `PREREG_E19.md`, SHA-256 `60519cfeb40fd308770a145e87619c1901606a7c746701ffa65a423ca4c85241`, hashed 2026-09-21T22:59:37Z.
First new computation: `scripts/e19_1.py`, 2026-09-21T23:03:55Z. No analysis step or writing rule was changed after any number was seen.

## A. Deviations from PREREG_E19.md

1. **E19-1 / E19-2 / E19-5, Llama and E16-2 stored counts.** The PREREG names `results/analysis_oos/OOS_RESULTS.json` as the source of the
   E16 out-of-sample u = 0 counts. I read the gold-free `OOS_PRE_GOLD.json` instead, because OOS_RESULTS.json also carries accuracy (gold)
   aggregates. The fields used (`N`, `omitted_n`, `changed_k`, `u0_omitted`, INVALID counts) are the same. The numbers match the values
   OOS_RESULTS.json showed when it was displayed once during path resolution, before the PREREG.
2. **E19-4, frozen predictor on the new settings.** `e15_1.py` was executed byte-identical (SHA-256 `d6bfc055...ab485`, asserted).
   - For the four new settings it completed its per-setting loop and its 80-row candidate table.
   - It then raised `KeyError: 'abs_err_fitcov_ms'` in its summary block (e15_1.py line 94). That block needs a saving-model entry for
     every deployed setting, and the saving model covers only E15's eight Table 2 policies.
   - The completed per-setting rows and candidates were taken from the exec namespace (`results/E19_4_new_e15_1_*.csv`). The Llama saving
     error was computed outside the frozen file with the same formula (`scripts/e19_4.py`).
   - The prediction itself (q_hat, predicted outcome, predicted coverage) is the frozen code's output.
   - Verification: the same harness on E15's 25 settings reproduces all four stored E15-1 CSVs, all rows and all columns.
3. **E19-4, first-output time of the E16-5 settings.** The PREREG says "min utc over the E16-5 records per dataset" (18:59:19Z OBQA,
   19:03:45Z ARC). I used the earlier, conservative 18:58:58Z instead. That is E16's recorded first model output (Job A), which includes the
   V3b strong-helper smoke; the smoke's outputs have no utc field, and its gate marker is at 18:59:06Z. The worklist
   `records/work/v3b_strong_smoke.jsonl` (mtime 18:47:14Z) holds inputs only, no receiver output. The prospective classification is the
   same either way, because both hash times (07:23:54Z, 18:31:26Z) are earlier.
4. **E19-4, first-output time of the Llama settings.** The X3 smoke run (06:42:22Z) was included in addition to the X3 runs (06:46:12Z).
   This is conservative, and both times precede the E15 hash (07:23:54Z).
5. **E19-7, scope.** In addition to the listed file types, `*.tsv` and `*.yaml` files were searched. The concurrent stage
   `P2_R8_E20P_20260921T224653Z` (another session, created 22:46Z) was included and was not modified.

## B. Execution notes

- **E19-6 check script.**
  - Run 1 (log kept as `logs/e19_6_run1_literal_checks.log`) had three FAILs, all caused by over-literal string matching, not by mismatches:
    - the probe prefix is stored in BOUNDARIES `frozen_config.json["prefix"]`, not as a literal in `run_boundaries.py`;
    - the parser source writes the single quote as `\x27`;
    - the parser source writes `due\s+to` and `based\s+on` where the Markdown says "due to" / "based on".
  - The checks were changed to test equivalence.
  - Run 2 crashed while writing a CSV, after the Markdown was written; the cause was a missing path-map entry for the new prefix hash.
  - Run 3 is the reported run: 25/25 PASS. No template text changed between runs.
- **Gold.** No E19 quantity uses a gold field. Some frozen record files that the reused loaders open also carry gold columns (V2 label
  files, `P2_6 .../dev_cases.jsonl`, the Table 2 replay input folders); those columns are never read into any E19 array. Files viewed
  during orientation, before the PREREG, that contain accuracy aggregates: E16 `RESULTS.md` and `OOS_RESULTS.json`, E9BC `SUMMARY.md`,
  E17 `RESULTS.md`. None of their accuracy values is used.
- **No `__pycache__`** was created (`logs/pycache_before.txt` == `logs/pycache_after.txt`; PYTHONDONTWRITEBYTECODE=1). No file outside
  this stage was written. OPENBLAS_NUM_THREADS=1 and `ulimit -c 0` were set for every Python call.
- Each script logs the project files it opened for reading (`logs/*_run.json`, `files_read`).
