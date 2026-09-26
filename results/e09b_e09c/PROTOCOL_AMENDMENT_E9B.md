# PROTOCOL AMENDMENT — E9B

Stage `P2_R3_E9BC_20260920T061042Z`, Paper A (ICLR 2027), ClusterA.
Written on the ClusterA login node **after** the E9B gate found prior use of the 744 questions and
**before any E9B model output existed**. `PROTOCOL_FREEZE_E9B.md` is unmodified; this file amends it.

Original frozen protocol: `PROTOCOL_FREEZE_E9B.md`,
SHA-256 `d211e4ad6eb267f389ec449482b21e4637e732383552678bea2f81d4cb8d0bbe`, frozen 2026-09-20T06:21:01Z.

## 1. Amendment (verbatim, as issued)

Amendment to E9B, written after the gate found prior use of the 744 questions and before any E9B model
output existed. Reason: an earlier project stage produced small-pair outputs on these questions
(2026-07-26) and scored them against the answer key (2026-07-27). The evaluated policies belong to the
medium and large pairs, which have no output on these questions, and no design choice of this study used
them. Change 1: the gate "no model output or gold label ever produced or read" is replaced by checks C1
and C2. Change 2: the population is described as "held-out OBQA questions never used by this study; an
earlier project stage scored small-pair outputs on them", never as sealed. Everything else in
PROTOCOL_FREEZE_E9B.md is unchanged: policies and thresholds, runs, frozen prompts, parser, decoding,
runtimes, the sealing order (project only id, question, choices, and fact1 for Text+fact; write and hash
all scores, routes, and outputs before decoding the answer key), statistics, and the commitment to report
every policy whatever its outcome.

## 2. Population identity

The 744 ids were derived twice, independently, and agree exactly:

- **A.** The authoritative complete split-assignment manifest
  `…/gate2b_labelblind_staging_hardened_gpu_v2_20260726/split_manifest.tsv`
  (4,952 data rows; SHA-256 `eb8a633f9be310694d9f213bce58932168d57f9f19138446ed924096aec89332`, the same
  "complete assignment identity" cited by the 2026-08-03 lineage audit). Its 744 rows with
  `assigned_role = untouched_final_holdout` give `source_row_index`, mapped to `id` in the OBQA train
  parquet (SHA-256 `98148f8a…5cd8b`) reading **only** columns `id, question_stem, choices`.
- **B.** All 4,957 train ids, minus the 5 `excluded_rows.tsv` ids, minus the 4,208 ids staged into P2
  (`…BOUNDARIES…/inputs/obqa_{train,dev}_queries.jsonl`).

`A == B`, |A| = |B| = 744, all K = 4. `answerKey` was never requested or loaded.

- `inputs/holdout_744_ids.json` SHA-256 `5129d91c60e6d9656520face24e09f470cb61271a996681338530c22d2147249`
- `inputs/holdout_744_queries.jsonl` SHA-256 `b0c6dd2c1696a89b5d7f88213b38a4b70a64e1025916841ebcf650a9919e2b25`
  (id, question_stem, choice_labels, choice_text only)

## 3. Check C1 — verdict: **PASS**

*No output, score, route or latency of the medium pair (Qwen2.5-1.5B-Instruct → Qwen3-1.7B) or the large
pair (Qwen2.5-7B-Instruct → Qwen3-8B), under any action, exists for any of the 744 questions in any
project record, in any stage.*

What was searched:

1. Every `.jsonl` and `.csv` file under the P2 project root — **1,759 files, 0 unreadable** — parsing the
   `id` field of every record and intersecting with the 744. **0 files matched.**
2. A first, deliberately looser pass also matched `question_id`, `example_id`, `qid`, `row_id` and
   returned 8 files. All 8 were resolved as **false positives**: in every one, `question_id` is the exact
   row-index sequence `0..N-1` (verified programmatically per file), not a question id, and the 744
   include short numeric OBQA train ids such as `10` that collide with those indices.
   - The five `P2_R1_EXP_20260919T050555Z/results/e1/official/{large_C,large_R,medium_C,medium_R,small_R}__clean/*openbookqa*_cot.csv`
     files have 500 rows each; all 500 rows of each map to the OBQA **test** split, which is disjoint
     from the train split the holdout is drawn from. Holdout rows contained: **0**.
   - The three `P2_R1_XFAM_20260919T095058Z/x1/...` files are shards of the X1 cross-family run. X1's
     frozen population (`records/populations/*.jsonl`, 17,267 rows over OBQA/ARC/MMLU-Pro) was checked by
     **exact id**: holdout intersection **0**. Every `*rows*.jsonl` fed to the official evaluator in that
     stage: holdout intersection **0**. X1's models are `meta-llama/Llama-3.2-1B-Instruct` →
     `Qwen/Qwen3-0.6B`, neither the medium nor the large pair.
3. The whole gate-2 chain (`~/analysis/channel_selection_gate*/` and `$DATA_ROOT/gate2*/`) was searched for
   the strings `Qwen2.5-7B-Instruct`, `Qwen3-8B`, `Qwen2.5-1.5B-Instruct`, `Qwen3-1.7B`:
   **zero occurrences**. Its four frozen channels are all small-pair
   (`frozen_channel_config_manifest.tsv`: helper `Qwen2.5-0.5B-Instruct`, receiver `Qwen3-0.6B`).

## 4. Check C2 — verdict: **PASS**

*No P2 artifact among parser V2 and the D1 rules, ProbeMax and the score choice, alpha/delta/grid, the fit
thresholds, the calibration and development records, or the Text+fact protocol reads, hashes or references
the gate2b predictions, the gate2d scored targets, or the 744 question ids, other than the files that
define the split itself.*

What was searched: `grep -rI` over the whole P2 tree for `gate2b`, `gate2d`, `scored_holdout`,
`prediction_freeze`, `untouched_final_holdout`, `label_generation_execution`, and the gate2d scored-target
SHA-256 `bac2aa2b…75e7`. Results:

- Each design-choice artifact was checked individually and contains **0** such references:
  `P2_SCORING_V2_20260912T191445Z/scoring_v2.py`;
  `…BOUNDARIES…/frozen_config.json` (ProbeMax, score choice, alpha=.05, delta, q-grid, p<=.001);
  `…BOUNDARIES…/src/run_boundaries.py`; `…MEDIUM_PAIR…/MEDIUM_PAIR_PROTOCOL_FREEZE.json`;
  `…MMLU_PRO_BREADTH_STAGE1…/MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json`;
  `P2_R2_GPU_20260919T220941Z/e6/PROTOCOL_FREEZE_E6.md` (Text+fact).
- **0** matches anywhere under `…BOUNDARIES…/{thresholds,deployments,records,summary}`,
  `…MEDIUM_PAIR…`, `…MMLU_PRO_BREADTH_STAGE1…`, `P2_ZERO_GOLD_CONTROLS…`, `P2_SCORING_V2…`,
  `P2_R2_GPU_20260919T220941Z`.
- The only P2 files that reference gate2b/gate2d at all are the three E5 post-hoc provenance-fact files
  `P2_R2_CPU_20260919T220412Z/{scripts/facts.py, results/facts_F1_F4.csv, SUMMARY.md}`. They cite the
  split-defining records (`gate2b_staging_report.md`, `split_summary.tsv`, `excluded_rows.tsv`,
  `gate2c …/source_access_receipt.json`) and cite `gate2d …/final_holdout_report.md` **for the role counts
  3466/742/744 and the 5 exclusions only** — no outcome value. E5 is labelled post hoc and changes no
  primary decision.
- The `prediction_freeze.jsonl` matches in `P2_FINAL_SEALED_ARC_CONFIRMATION…` and the supplement
  packages are P2's own sealed-ARC prediction freeze, an unrelated artifact with a similar generic name.

## 5. Check C3 — every earlier use of the 744

| stage | date | models | actions on the 744 | gold read |
|---|---|---|---|---|
| `gate2b_labelblind_staging_hardened_gpu_v2_20260726` | 2026-07-26 | none (no inference; `inference_or_generation_executed=false`) | split construction + label-blind feature staging | no |
| `gate2b_label_generation_execution_gpu_v2_20260726` | 2026-07-26 | small pair Qwen2.5-0.5B-Instruct → Qwen3-0.6B; `qwen3_0.6b+qwen2.5_0.5b_Fuser`; task9 soft-prefix k8 ckpt | 20,908 label-blind prediction records over the 4,952-row eligible universe, which includes all 744: `NoComm`, `Text`, `HiddenPrefix`, `KVCache` | no (label-blind) |
| `gate2b_train_dev_scoring_execution_20260726` | 2026-07-26 | none (scoring only) | scored `router_train`/`router_dev` with **zero** holdout rows; holdout gold not opened | no |
| `gate2c_selector_development_v5_20260727` | 2026-07-27 | none (CPU selector) | holdout feature rows decoded for role filtering only: 744 decoded, **0 retained, 0 used**; no fit/transform/metric | no |
| `gate2d_final_holdout_evaluation_20260727` | 2026-07-27 | consumed the stage-2 small-pair predictions | one-shot scoring of all 744 → `y_NoComm, y_Text, y_HiddenPrefix, y_KVCache`, plus routing/predictive/uncertainty metrics | **yes** |
| `aug03_w66_holdout_lineage_reconciliation` | 2026-08-03 | none | identity/lineage audit; whole-file stat+SHA only, no row, target or metric opened | no |

Net: the answer key of the 744 was opened exactly once, by gate2d on 2026-07-27, against **small-pair**
outputs. No medium- or large-pair output has ever existed for these questions.

## 6. Disclosure

During the original gate check on 2026-09-20 (before this amendment, and before any E9B model output),
this session opened `gate2d_final_holdout_evaluation_20260727/final_holdout_report.md` and
`scored_holdout_targets.tsv` to establish the verdict, and thereby read two aggregate small-pair accuracy
values from that report and the header plus the first two data rows of the scored-target table. This is
recorded for completeness. It concerns small-pair channel outcomes only; it touches none of the medium- or
large-pair policies, thresholds or statistics that E9B evaluates, and no E9B quantity is derived from it.

## 7. Population wording required from here on

"Held-out OBQA questions never used by this study; an earlier project stage scored small-pair outputs on
them." The words *sealed*, *untouched* and *first evaluation* are not to be used for this population in
any E9B output, report, figure or manuscript text.
