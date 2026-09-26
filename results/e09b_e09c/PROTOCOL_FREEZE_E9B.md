# PROTOCOL FREEZE — E9b (sealed check of the frozen OBQA policies on the 744-question holdout)

Paper A (ICLR 2027), ClusterA. Stage `P2_R3_E9BC_20260920T061042Z`.
Frozen on the ClusterA login node **before any E9b model output existed**, and — as recorded in
section 4 — no E9b model output was ever produced, because the protocol's own gate failed.

## 1. Protocol (verbatim, as issued)

Population: the 744 OBQA questions of the untouched holdout. Gate: before any model output, search all
project records and confirm that no model output, score, or gold label of these questions was ever
produced or read. If any was, stop E9b and report. Frozen policies (thresholds unchanged):
medium/OBQA/C2C at q=.55 (and, reported alongside, its exposure-free q=.50 threshold); large/OBQA/Text
at q=.80; large/OBQA/C2C at q=.80; large/OBQA/Text+fact at q=.75. Runs: for each pair, receiver-only R
and the ProbeMax probe; large: Text, C2C, Text+fact; medium: C2C. Frozen prompts, parser, decoding, and
runtimes. Sealing: project only id, question, and choices (plus fact1 for the Text+fact helper); write
and hash all scores, routes, and outputs before decoding the answer key. Statistics per policy: omitted
n, changed k, conditional change rate with a two-sided Clopper-Pearson 95% interval, and the exact
binomial p-value of the single prespecified test H0: rho >= .05 at the frozen threshold; the change rate
of always omitting (receiver alone on all 744); accuracy of policy and reference with a paired bootstrap
interval (2,000 resamples, seed 0). No latency is measured. Every policy is reported whatever its outcome.

## 2. Concrete bindings that would have been used

| item | binding |
|---|---|
| population | `untouched_final_holdout`, 744 rows of the gate2b split (`SHA256(b'gate2b-split-v1\0' + row_fingerprint)`, sort by `(split_digest, dataset_id, raw example_id)`, remainder after 3,466 router_train + 742 router_dev) |
| source parquet | `$DATA_DIR, SHA-256 `98148f8a54e62eb862346a75192d5fb824d6cbb68f2f59aecd793d39ecb5cd8b`, 4,957 rows |
| medium helper | Qwen/Qwen2.5-1.5B-Instruct @ `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` |
| medium receiver | Qwen/Qwen3-1.7B @ `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` |
| medium fuser | nics-efc/C2C_Fuser @ `f01fc3258b305e280e04c7238f4f2cf31b7dc70d`, `qwen3_1.7b+qwen2.5_1.5b_Fuser/final` |
| large helper | Qwen/Qwen2.5-7B-Instruct @ `a09a35458c702b33eeacc393d103063234e8bc28` |
| large receiver | Qwen/Qwen3-8B @ `b968826d9c46dd6066d109eabc6255188de91218` |
| large fuser | nics-efc/C2C_Fuser @ `f01fc3258b305e280e04c7238f4f2cf31b7dc70d`, `qwen3_8b+qwen2.5_7b_Fuser/final` |
| frozen thresholds | medium/OBQA/C2C q=.55 `1.3113021850585938e-06` (`P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/deployments/obqa_C.json`); exposure-free q=.50 from `P2_R2_CPU_20260919T220412Z/followup/results/f1c_medium_obqa_C2C_dev.json`; large/OBQA/Text and /C2C q=.80 `1.170039176940918e-03` (`P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/deployments/large_obqa_{T,C}.json`); large/OBQA/Text+fact q=.75 `2.611875534057617e-04` (`P2_R2_GPU_20260919T220941Z/e6/analysis/E6_RESULTS.json`) |
| parser | `P2_SCORING_V2_20260912T191445Z/scoring_v2.py`, SHA-256 `d05978f400cf69aa6bddc56168a260ac3ea9158abaa640e9331602dc9bfcc2f9` |
| probe construction | `P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/src/run_boundaries.py`, prefix `"The correct answer is"` separately encoded, `enable_thinking=False`, bf16/sdpa/batch 1, FP32 label logsumexp+softmax, u = 1 - max p |
| Text+fact helper line | `Useful fact: <fact1>` from `allenai/openbookqa` config `additional`, per `P2_R2_GPU_20260919T220941Z/e6/PROTOCOL_FREEZE_E6.md` |
| statistics | Clopper-Pearson two-sided 95%; exact binomial p of H0: rho >= .05; paired bootstrap 2,000 resamples, seed 0, unit = question |

## 3. Gate search actually performed (2026-09-20, ClusterA login node)

Searched, and what each returned:

1. `P2_R2_CPU_20260919T220412Z/{SUMMARY.md,results/facts_F1_F4.csv,scripts/facts.py}` — E5 fact F1, the
   provenance the task points at. Confirms the 744 rows are the remainder of the gate2b split and are
   excluded from P2's 4,208-question OBQA pool.
2. `gate2c_train_dev_question_staging_v1_20260727/source_access_receipt.json` —
   `holdout_rows_converted_to_python = 0`, `holdout_rows_persisted = 0`, `holdout_rows_preprocessed = 0`.
   The P2 pool itself never staged a holdout row.
3. Full-text search of the P2 project tree (`grep -rI` over `*.py, *.md, *.json, *.csv`) for
   `gate2d`, `final_holdout`, `holdout`. Only three files reference gate2d, all of them the F1 split-count
   citation; no P2 artifact contains a holdout outcome.
4. `gate2b_labelblind_staging_hardened_gpu_v2_20260726/{gold_access_audit.txt,frozen_channel_config_manifest.tsv}` —
   the staging step read no gold, and the four frozen channels are `NoComm` (receiver only), `Text`,
   `HiddenPrefix` and `KVCache` (`c2c_projected_kv`), run with helper Qwen2.5-0.5B-Instruct and receiver
   Qwen3-0.6B — **the P2 small pair** — plus the `qwen3_0.6b+qwen2.5_0.5b_Fuser`.
5. `gate2b_label_generation_execution_gpu_v2_20260726/label_generation_report.md` — the authorized ClusterA
   run produced and froze **20,908 label-blind prediction records over the full 4,952-row eligible
   universe**, which includes all 744 holdout rows.
6. `gate2d_final_holdout_evaluation_20260727/` — `input_scoring_receipt.json` records
   `query_count = 744`, `final_holdout_targets_consumed = true`,
   `answerKey_loaded_inside_authorized_scorer = true`; `scored_holdout_targets.tsv` (744 data rows,
   SHA-256 `bac2aa2b…75e7`) holds per-question `y_NoComm, y_Text, y_HiddenPrefix, y_KVCache`;
   `final_holdout_report.md`, `routing_metrics.json`, `predictive_metrics.json` and
   `uncertainty_and_tests.json` report metrics computed on them.
7. `$HOME_DIR/analysis/aug03_w66_holdout_lineage_reconciliation/` — a prior authorized audit of
   exactly this question (2026-08-03). Disposition `HOLDOUT_LINEAGE_CONFLICT_CONFIRMED`; membership
   identity `IDENTICAL`; claim-scope results: "The 744-example final holdout remains sealed" —
   `CONTRADICTED_BY_HISTORY`; "No result from the final holdout exists" — `CONTRADICTED_BY_HISTORY`.
   The later MDCR audit records `currently_untouched_holdout_exists = false`.

## 4. Gate verdict

**FAILED — E9b is stopped and reported; no E9b model output was produced.**

Model outputs of these 744 questions were produced on 2026-07-26, and per-question scores derived from
the gold answer key were produced and read on 2026-07-27, by the Gate-2 channel-selection study, using
one of this paper's own model pairs and channels that correspond to this paper's receiver-only, Text and
C2C actions. The population is therefore not an untouched holdout for the project, and the protocol's own
instruction ("If any was, stop E9b and report") applies. Nothing in section 2 was executed: no prompt was
rendered, no model was loaded, no route, score or output file exists for these rows in this stage.

Task-scoped non-access by P2 remains true — P2 never staged, ran or scored these rows — but it does not
restore project-global untouched status, exactly as the 2026-08-03 audit already recorded.

Re-running E9b would require an explicit, informed decision by the requester (see `SUMMARY.md`,
"NEEDS FROM US"); it is not taken here.
