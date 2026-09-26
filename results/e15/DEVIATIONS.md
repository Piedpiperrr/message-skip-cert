# E15 deviations

Preregistration: `PREREG_E15.md`, SHA-256 `d2e6fc2b3798084032ab4ad12b7d18c8538271ad72d9e71b0598038a59f6d45a`, hashed
2026-09-21T07:23:54Z. No rule was changed after results were seen.

## A. Deviations from the preregistration

**None.** Both items were computed as written. E15-2 falls into the preregistered branch (2), in which no replay source
qualifies for all eight policies.

## B. Choices where the preregistration left room (recorded for completeness)

1. **N_fit for ARC = 670.** The stored thresholds are order statistics of the 670 fit group representatives
   (`P2_CONFIDENCE_REFERENCE_BOUNDARIES_.../splits/arc_fit_representatives.json`; `arc_fit_ids.json` has 671 question ids).
   The request said to use the stored split files, so 670 is used everywhere for ARC.
2. **c_b, c_R, c_s source (E15-1 saving model).** The per-question development records behind Table "Same-target baselines"
   (ii), read exactly as `audit_v2.py` reads them:
   - small/large OBQA/ARC: V2 label source pointers → `latency_ms`, with the probe cost from BND `records/{pair}_{ds}_{b}_routes.jsonl`
     `measured_selective_overhead_ms`;
   - medium: `execution_retry1.../actions/{ds}_dev.jsonl` and `probes/{ds}_dev.jsonl`;
   - MMLU-Pro: `summary/merged_numeric_rows.jsonl`.

   These reproduce the table's Ref / R / Policy columns to 0.1 ms. c_s is the mean development probe cost from the same
   records. The Appendix F 128-question component-panel probe means (E13 item 6) differ from these by at most 0.3 ms:
   43.37 vs 43.25, 43.07 vs 43.25, 33.10 vs 33.36, 33.20 vs 33.19 and 46.27 vs 46.24.
3. **Measured saving** in the error columns is the unrounded original-replay mean, which equals Table 2 to 0.1 ms.
4. **Panel-coverage version** of the saving model: computed for all eight policies. The formula does not depend on the
   prediction, and all eight were predicted to deploy in any case.
5. **"Actual dev coverage"**: the share of the full development population (742 / 299 / 2,641 representatives) at or
   below the deployed threshold. It equals the T2 development coverage for all eight settings.
6. **E15-2, "timed with CUDA synchronization".** The large-pair replays time each forward of the helper, the receiver and
   each fuser projector with CUDA events recorded by forward pre/post hooks on the executing device. The events are read
   after `torch.cuda.synchronize` on both GPUs; the probe has its own event interval between synchronizations
   (`native_adapter.py`, `execute.py`). I counted this as separate, per-request, synchronized timing. The stage mapping:
   - probe prefill = `GPU_prefill_projection_event_ms` (prefill + last-position projection);
   - helper = `helper` forward events (prefill and each decode step);
   - fuser = `fuser_0`–`fuser_35` events;
   - receiver prefill and decoding = `receiver` LM forward events.

   The nested `receiver_backbone` events are not added. The probe's label-probability step (not a listed stage) is
   excluded, and so is GPU work outside any hooked forward (for example, token selection between decode steps). The
   helper→receiver KV transfer runs outside every hooked forward (`P2_10.../runtime.py` `request`), so it is excluded, as
   the definition requires.
7. **E15-2, branch (2), "report what is available".** Busy time is reported from the highest-preference source that
   qualifies for each available policy: (a) the original configuration, for all four. The E3 repeats also qualify for
   the same four large-pair policies but were not computed, following the single-source rule.
8. **E15-2 bootstrap.** Reused the original replay's stored index matrices (`summary/{obqa,arc}_bootstrap_indices.npz`).
   The script asserts they equal `numpy.random.default_rng(0).integers(0, 128, (2000, 128))` in panel-id order. Intervals
   are `np.quantile(..., [.025, .975])`, the replay's own method, and the latency intervals reproduce its stored ones exactly.

## C. Incidents (no effect on any result)

- 2026-09-21T07:29:10Z: an inspection command imported numpy without `OPENBLAS_NUM_THREADS=1` and segfaulted (the known
  login-node OpenBLAS issue). This left `core.3918941` (16.6 MB, PID of that process) in the repo root. I deleted it
  within a minute. No other file was touched, but the repo-root directory mtime changed. All later commands set
  `OPENBLAS_NUM_THREADS=1`, `PYTHONDONTWRITEBYTECODE=1` and `ulimit -c 0`.
- The first run of `scripts/e15_2.py` (07:36:28Z) had an operator-precedence bug in the qualification check
  (`A | B - {''}`), which marked every source as non-qualifying. I fixed it and re-ran at 07:36:43Z; the buggy log is kept
  as `logs/e15_2_run1_precedence_bug.log`, and its output files were overwritten. The fix changes only the qualification
  bookkeeping, not any preregistered definition.
- The pycache folders of the reused script directories are unchanged (`logs/pycache_before.txt`, `logs/pycache_after.txt`).
  The `.pyc` paths in `logs/files_opened_*.txt` are the import system's cache lookups; nothing was written.
