# P2_R2_GPU Phase 1 feasibility (login node, read-only, 2026-09-19)

## E6
- Dataset: `allenai/openbookqa`, config `additional`, revision `388097ea7776314e93a529163e0fea805b8a6454`
  (local parquet under `c2c_reproduction_assets/datasets/allenai--openbookqa/additional/`).
- `fact1` coverage: cal 1366/1366, dev 742/742, first 16 fit 16/16. 0 missing ids, 0 empty facts,
  0 `question_stem` mismatches against the frozen queries. Full record: `e6/E6_COVERAGE.json`.
- Helper Text prompt builder: `legacy_methods.T2THelperBundle.run` ->
  `protocol_min.format_openbook(example, use_template=False)` (patched by `arc_runtime_adapter` to
  `arc_protocol.helper_body`) -> `build_prompt(..., use_template=False)` = `question + "\n\nChoices:\n" + choices`,
  wrapped by `legacy_methods.BACKGROUND_PROMPT`.
- Saved large-pair OBQA Text outputs: helper message mean 28.6 tokens, max 159 (train 3466 rows) /
  max 54 (dev 742 rows). Text action mean 1004.9 ms (train) and 978.5 ms (dev) on the historical run;
  801.9 ms on ClusterA for the 128-question panel Text reference arm (job 7635399).
- GPU-time estimate for 2108 helper+receiver rows: ~28-35 min on one GPU pair; measured on the E6
  smoke (ClusterA, 16 fit rows) at 754.6 ms/row -> ~6.4 min per 527-row shard plus ~2.5 min model load.

## E7
- Native R prompt vs ProbeMax probe input: **exact token prefix in 640/640 cases** (5 panels x 128),
  Qwen3-8B (large OBQA, large ARC, MMLU-Pro) and Qwen3-1.7B (medium OBQA, medium ARC). The probe input
  is the R prompt followed by exactly 4 tokens `[785, 4396, 4226, 374]`. Record: `e7/E7_PREFIX_CHECK.json`.
- No longest-common-prefix shortfall exists, so no LCP statistics are needed.

## E7 replay node budget (from the E3 ClusterA logs, job 7635399)
Per-request overhead outside the timed region: large 0.019 s, medium 0.013 s, MMLU-Pro 0.01 s in
repeats 2 and 3. Repeat 1 saw 1.82 s/request of node-local contention on compute-node and is the
pessimistic case. With 4 arms per deployed policy:
- node A (large OBQA + large ARC, 2048 requests): ~663 s timed + ~60 s overhead/load ~= 13 min.
- node B (MMLU-Pro + medium OBQA + medium ARC, 2048 requests): ~842 s timed + ~90 s ~= 16 min.
Both fit 50 min with margin, so the node split of the task description is kept and no job split is needed.
