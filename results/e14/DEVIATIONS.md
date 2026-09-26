# E14 deviations and implementation choices

Preregistration: `PREREG_E14.md`, SHA-256 `b9877181ca0f0a27557066947a0d90ce25fef7ab81a57fa1a890a5de1ce46e32`,
hashed 2026-09-21T05:23:00Z. No analysis step or reporting rule was changed after any number was seen.

## A. Deviations from the preregistered text

None.

## B. Execution notes

1. **First run attempt.** The first run of `scripts/e14.py` started at 2026-09-21T05:31:11Z. It printed the step-2 (i) checks
   (all PASS: sealed 1,100 / 20 and 1,047 / 11) and then stopped with `AttributeError: module 'e11_common' has no attribute
   'route_mask'`, before check (ii) and before any E14-1 or E14-2 number. The one-token fix (`C.route_mask` ->
   `C.data_r1.route_mask`, the same function E11 uses) was made and the script was re-run from the start at 05:31:25Z. That
   re-run is the run reported. `logs/e14.log` holds only the re-run: the first attempt's console output was overwritten, and its
   content is quoted in this note.
2. **No `__pycache__`** was created anywhere (`logs/pycache_before.txt` == `logs/pycache_after.txt`, 26 pre-existing directories).
   No existing file was modified. All outputs are under this stage directory.

## C. Choices where the preregistration was silent (recorded for completeness)

- **E14-1 inclusion rule.** The E11(b) rule is `parsers_r2.official_applicable`: a question is included iff its displayed
  option labels are a subset of {A, B, C, D}. Excluded: 3 sealed questions with options A-E (TIMSS_1995_8_J7,
  TIMSS_2007_8_pg53, TIMSS_1995_8_N4). Both policies omit all three, and none of the three is a change under V2. Included as in
  E11(b):
  - the 4 three-option questions (A-C). `label_official` counts an extracted letter outside the question's option set as
    unparseable. No such read occurred: all 44 official-vs-V2 differences are on A-D questions.
  - the 22 questions whose original ARC labels were numeric (1-4 / 1-3). The sealed run displayed and parsed them as A-D / A-C
    (the P2-8 mapping, which is also what the ARC calibration data in E11(b) used).
- **E14-1 raw outputs.** On an omitted question, R's raw output is the stored raw output of that policy's own policy request
  (`selected == R`). Each sealed policy has its own R request, and each policy uses its own. The reference raw output is the stored
  reference request. Routing is taken as executed; `selected == R` was asserted to equal `ProbeMax <= tau` for every row.
- **E14-1 V2 labels.** V2 labels are the stored runtime parse. It equals a fresh V2 re-parse on all 4,688 outputs (check).
  Besides the preregistered "V2 on the same subset" row, the full-population V2 row (1,100 / 20; 1,047 / 11) is shown for
  reference.
- **E14-1 categories.** These are the E5-a follow-up categories (`P2_R2_CPU_20260919T220412Z/followup/`). They are computed with
  that stage's own `official_branch` and `surface_pattern` functions, exec'd from its source. The operational mapping:
  - C1 (ambiguous or repeated letters read as the first letter): V2 unparseable -> official label, official branch
    `answer_phrase_first_ABCD_char`, pattern `declaration_several_letters` or `repeated_declaration_same_letter`.
  - C2 (option text with tan/sin/"/"): V2 label -> official unparseable, branch `blocked_by_math_substring`. The block fires on
    any substring in the official extractor's math-indicator list (+ - * / = ^ x^ y^ z^ mod sqrt sin cos tan). Among the 44 sealed
    outputs, the first 80 characters contain: tan 16 (e.g. "dis*tan*ce", "subs*tan*ces"), - 10 (e.g. "->", "cold-blooded"), sin 7
    (e.g. "advertising"), + 4, / 4, cos 3 ("glucose"), mod 2 ("modification"). This is the same category as in E5-a, where the
    examples were *distant*, *using* and *70 km/h*.
  - C3 (last-letter read): V2 label -> a different official label, branch `standalone_pattern_*`.
  - Other: anything else. On the sealed set, all 44 differences are C2, on the C2C reference output. The Text policy has 0
    differences.
- **E14-2 labels on the held-out and sealed populations.** These are the stored change indicators of those runs: E9b
  `SEALED_ROUTES.jsonl` `changed`, and sealed `paired_sealed_2344.jsonl` `omission_changed`. Both are V2 with the paper's
  convention, and both reproduce the published omitted / changed counts (checks).
- **Per receiver x benchmark.** Qwen3-1.7B (medium) includes MMLU-Pro dev, from the E8 records. The medium pair has no deployed
  MMLU-Pro policy, but u is receiver-only and the dev records exist. For Qwen3-8B the MMLU-Pro fit-group count (713 / 3,000) is
  added as a reproduction of the "known before" value.
- **Additions (descriptive, not substitutions).** The calibration omitted / changed counts at each frozen threshold, checked
  against the stored calibration ledgers. The number of the 20 fit candidates that equal 0 for each policy (none of the deployed
  thresholds is 0). The "k with both-unparseable = change" column for every E14-1 row.

## D. Ambiguity reported both ways (decision for the authors)

- **The n0/n >= 90% trigger and the q = .50 row.** The preregistration says that the q = .50 row "goes to the appendix table
  only" for the main-text range sentence. The trigger itself reads "if n0/n >= 90% on dev for **any policy**". On dev,
  medium/OBQA/C2C at q = .50 has n0/n = 321/355 = 90.4%. Read literally, that meets the trigger. It is marked in
  `RESULTS_E14.md` as the appendix row. The deployed policy that meets the trigger is medium/ARC/C2C (174/189 = 92.1%). Whether
  the paper's sentence also names the q = .50 row is left to the authors. Nothing was computed differently because of this.
