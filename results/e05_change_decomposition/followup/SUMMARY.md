# E5 follow-up (a) D1 provenance, (b) official-extractor differences, (c) medium/OBQA/C2C at q = .50

**POST-HOC re-analysis (reviewer R2/E5); does not change any primary decision.** Login node, CPU only,
read-only on every existing folder. Scripts `followup/scripts/`, tables `followup/results/`. The
stage's own `SUMMARY.md`, `PREREG_R2_E5.md`, `scripts/` and `results/` were not modified.

## (a) D1 provenance — `results/f1a_d1_provenance.json`, `f1a_timeline.csv`, `f1a_synthetic_cases.csv`

**When.** `P2_SCORE_SENSITIVITY_20260912T055929Z/diagnostic_parser_v1.py` was written
2026-09-12T06:01:03Z and **frozen 2026-09-12T06:02:33.598062Z**
(`RULE_FREEZE_V1.json`, field `frozen_utc`; `version` = `D1_EXPLICIT_20260912`, `code_sha256`
`6619cafdd9cffb98…`, rule doc `DIAGNOSTIC_RULES_V1_ZH.md` `rule_sha256` `933c3a6715263ff5…`).

**How, and on which records.** D1 was **not developed on any project record**. Its entry point is
`parse_explicit(text, legal_labels)` (`diagnostic_parser_v1.py` line 13; docstring line 1:
"D1：保守显式答案诊断。仅 text、legal_labels；不使用 gold、动作或题目"), and
`RULE_FREEZE_V1.json` records `input_signature = ["text", "legal_labels"]`. The material it was
written against is:

- **24 synthetic (text, legal_labels, expected) triples** inside the parser itself,
  `diagnostic_parser_v1.py` lines 75-99 (`SYNTHETIC_CASES`; `RULE_FREEZE_V1.json`
  `synthetic_checks = 24`), listed in `results/f1a_synthetic_cases.csv`; and
- **one real output, `C. 70 km/h`**, disclosed by the user *before* the freeze
  (`RULE_FREEZE_V1.json` field `known_case_disclosed_by_user`). Its record is
  `evidence/known_unit_case.json` (large / ARC / train / `Mercury_415080` / c2c).

**Gold before the freeze: no.** `RULE_FREEZE_V1.json` records `gold_statistics_started: false`, and
`ANALYSIS_COMPLETE.json` records `gold_statistics_first_started_after:
"2026-09-12T06:02:33.598062+00:00"` — the freeze instant itself. D1 never receives gold: gold is only
used afterwards, in the analysis script, to *score* D1's output
(`analyze_sensitivity.py` line 123: `diag=parse_explicit(txt,legal);diag['correct']=bool(diag['valid'] and diag['answer']==gold)`).

**Calibration-split outputs before the freeze: none could have been.** No fit/calibration/development
split existed on 2026-09-12. The split files were first written 2026-09-14T16:52:45Z in
`P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/splits/` — **2.5 days after** the D1 freeze. Every
record D1 was applied to was a `train` (OBQA) or `train`/`validation` (ARC) row at the time
(`analyze_sensitivity.py` line 144, `for split in C['data'][ds]`).

**Records D1 was applied to, after the freeze** (`results/f1a_applied_records.csv`): pairs `large` and
`small`; benchmarks `obqa` (train 3466, dev 742) and `arc` (train 1119, validation 299); sources = the
historical R/T/C successes of P2_5 / P2_6 / P2_9 plus the P2-10 AC and cost-panel records, 18 entries in
`SOURCE_INDEX.json`, **49 616 unique source records**.

**The gold-labelled review happened after the freeze.** `case_review.jsonl` was written in the single
analysis run that completed **2026-09-12T06:07:59.451238Z**, i.e. **325.9 s after** the freeze
(`ANALYSIS_COMPLETE.json` `completed_utc`; file mtime identical). Its selection rule is
`analyze_sensitivity.py` line 135:
`if changed or diag['ambiguous'] or key=='P2_10|large|arc|train|Mercury_415080|c2c':`, and every one of
its 1663 records carries the `gold_for_statistics` field (line 137). Restricted to rows that later fell
into a calibration split, this is **341 distinct questions / 355 pair-question reviews** (large/OBQA 30,
small/OBQA 186, large/ARC 26, small/ARC 113), which is 543 review rows once the per-action rows
(receiver_only 122, text 142, c2c 65, acw 214) are counted separately. The 341 figure matches
`results/e5a_exposed_ids.csv` exactly. For orientation, V2 was frozen later still, at
2026-09-12T19:19:38.860954Z.

## (b) Official-extractor label differences — `results/f1b_*.csv`

Per-setting counts (`f1b_per_setting.csv`) reproduce the `o_R diff` / `o_ref diff` / `d_b diff` columns
of the stage `SUMMARY.md` exactly. Across all 18 A-D settings there are **1124 label differences**
(R: 580, reference: 544) and only **four categories**; `f1b_categories.csv` has them per setting,
`f1b_differences.csv` has every row, `f1b_categories_overall.csv` the totals.

| transition | output pattern | why the official extractor differs | rows | settings | V2 -> official |
|---|---|---|---|---|---|
| INVALID -> label | `The correct answer is A/B/C/D` (several letters) | matches `correct answer is (.*)` and returns the **first** A-D character of the remainder | 1051 | 16 | A x856, B x29, C x166 |
| label -> INVALID | `X. <option text>` (leading label then option text) | the option text contains a "math indicator" substring (`tan` in *dis**tan**t*, `sin` in *u**sin**g*, `/` in *70 km/h*), so both the standalone and the fallback branch are suppressed | 61 | 8 | A x11, B x13, C x10, D x27 |
| INVALID -> label | repeated `The correct answer is B. The correct answer is B. …` | same answer-phrase branch; V2 treats the repetition as unresolved | 10 | 2 | B x8, C x1, D x1 |
| label -> other label | `X. <option text ending in a letter>` | standalone pattern 1 takes the **last** A-D at the end of the text, which is inside the option text | 2 | 1 | A->C x1, D->C x1 |

Two raw examples per category (first 80 characters) are the `example_1` / `example_2` columns of
`f1b_categories.csv` and `f1b_categories_overall.csv`, e.g. `The correct answer is A/B/C/D.`,
`D. disguise itself as just some junk on the bottom of the ta`, `A. 0°C`, `D. 120°C`.

Per setting, for the ones named in the question (full table in `f1b_categories.csv`):

| setting | output | transition | pattern | n | V2 -> official |
|---|---|---|---|---|---|
| large/OBQA/Text | R | INVALID->label | several letters | 2 | INVALID->A x2 |
| large/OBQA/C2C | reference | label->INVALID | leading label + option text | 20 | A x2, B x5, C x1, D x12 |
| large/OBQA/C2C | reference | INVALID->label | several letters | 2 | INVALID->A x2 |
| large/OBQA/C2C | R | INVALID->label | several letters | 2 | INVALID->A x2 |
| large/ARC/C2C | reference | label->INVALID | leading label + option text | 23 | A x3, B x7, C x5, D x8 |
| large/ARC/C2C | reference | label->other label | leading label, option text ends in a letter | 2 | A->C x1, D->C x1 |
| medium/OBQA/C2C | reference | INVALID->label | several letters | 40 | INVALID->A x40 |
| medium/OBQA/C2C | R | INVALID->label | several letters | 13 | INVALID->A x12, INVALID->B x1 |
| medium/OBQA/C2C | R | label->INVALID | leading label + option text | 2 | A->INVALID x2 |
| medium/OBQA/C2C | reference | label->INVALID | leading label + option text | 1 | C->INVALID x1 |
| medium/ARC/C2C | reference | INVALID->label | several letters | 14 | INVALID->A x14 |
| medium/ARC/C2C | reference | label->INVALID | leading label + option text | 3 | C x1, D x2 |
| medium/ARC/C2C | R | label->INVALID | leading label + option text | 3 | A x1, C x1, D x1 |
| medium/ARC/C2C | R | INVALID->label | several letters | 3 | INVALID->A x3 |

Settings with differences beyond the ones named: large/ARC/Text has **none** (0 label differences);
medium/OBQA/Text (16), medium/ARC/Text (6), all four small-pair settings (139, 63, 101, 53), all four
X1-Llama settings (98, 163, 76, 75) and both A-D X2-OLMo settings (134, 70) do, all falling in the same
four categories.

**Patterns that do not occur.** The census over *all* A-D calibration outputs
(`f1b_pattern_census.csv`, 32 652 outputs) finds **zero** rows with a numeric option label (ARC 1-4),
zero with a letter outside the question's option set (e.g. option E), and 17 with answer text and no
letter — none of which produce a V2-vs-official difference. The surface forms that do occur are
`declaration_single_letter` 27 873, `declaration_several_letters` 2141,
`leading_label_then_option_text` 1632, `bare_letter` 970, `repeated_declaration_same_letter` 16,
`declaration_answer_text_without_letter` 3.

**Can the official extractor read every label set it was given?** **No.**
`extract_answer_from_content` hard-codes the option set A-D in all three of its stages
(`{'A','B','C','D'}` membership, `[A-D]` character classes). For the 18 OBQA/ARC settings every
calibration question has exactly the label set A-D, so it is applicable there
(`f1b_label_sets.csv`, `official_can_read_every_label_set = True`). For the three MMLU-Pro settings
(large/MMLU-Pro/Text, large/MMLU-Pro/C2C, X2-OLMo/MMLU-Pro/Text) the questions carry up to 10 options
(labels A-J), so the extractor cannot express labels E-J and those settings are reported n/a rather
than forced — as in the stage `SUMMARY.md`.

## (c) medium/OBQA/C2C on development at the clean q = .50 — `results/f1c_medium_obqa_C2C_dev.csv`

Same definitions as the paper's reference-correction table (`tab:omit_keep`). Running the same code at
the original q = .55 reproduces the published row exactly (390/742, lost 1/44, kept 43/44, gained 7,
net +6, other 11, unused 12/89), so the q = .50 row below is on the same footing.

| | q = .55 (frozen deployment) | **q = .50 (largest clean-accepted)** |
|---|---|---|
| threshold | 1.3113021850585938e-06 | **2.384185791015625e-07** |
| omitted / N | 390/742 (52.56%) | **355/742 (47.84%)** |
| changed on omitted | 11 | **7** |
| correct, policy | 492 | **490** |
| correct, reference (C2C) | 486 | **486** |
| correct, R | 490 | 490 |
| reference corrections | 44 | 44 |
| lost | 1/44 | **1/44** |
| kept | 43/44 | **43/44** |
| gained | 7 | **5** |
| net | +6 | **+4** |
| other | 11 | **9** |
| unused (omit/keep) | 12/89 | **10/93** |

The identity *policy − reference correct answers = gained − lost* holds at both q values.

## Convention recorded for E5-b (answer E5-3)

Re-seeding MMLU-Pro through the hash salt is the accepted convention. Concretely
(`scripts/e5b.py` lines 83-98): OBQA and ARC re-splits shuffle the lexicographically sorted
representatives with `random.Random(seed)`; MMLU-Pro has no shuffle step in its frozen rule, so a
re-split re-seeds `build_candidates.py`'s SHA-256 ordering by extending the frozen seed string —
`seedstr = MMLU_SEED` for seed 0 and `f'{MMLU_SEED}|resplit{seed}'` otherwise, with
`MMLU_SEED = 'P2_MMLU_PRO_BREADTH_20260915_v1'`, ordering within each category quota by
`sha256(seedstr + '|split_fit|' + group_hash)`. Seed 0 therefore reduces to the frozen rule and
reproduces the frozen split exactly on all three benchmarks (`results/e5b_seed0_check.csv`), which is
the check that makes the extension legitimate.
