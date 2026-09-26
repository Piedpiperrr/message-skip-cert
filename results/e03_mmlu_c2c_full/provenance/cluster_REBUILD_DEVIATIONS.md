# Deviations from the original MMLU-Pro replay (P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z)

Approved by the project lead on 2026-09-19 (scoped rebuild (c), plus the allocation edits in (b)). The timed region is unchanged: `timed_arm()`, native runtime, probe, parser and threshold. Exact changes are in `diffs/mmlu_full_code.diff` and `diffs/mmlu_full_regenerated_artifacts.diff`.

**Scoped rebuild**

1. **Question list:** all 2,641 development group representatives, in frozen Stage-1 order. The original used the 128-question panel.
   - `inputs/candidate_e2e128_ids.json` is replaced by `inputs/panel_ids.json`.
   - `inputs/panel_queries.jsonl` and `protocol/PANEL_MANIFEST.json` are regenerated from Stage-1 queries and `dev_groups.json`. The Stage-1 freeze hash of `dev_groups.json` is asserted.
2. **Arms:** `common.ARMS=['fixed_C','policy_C']`, and `order_for` rotates modulo `len(ARMS)`, which alternates the first arm per question. `protocol/FOUR_ARM_SCHEDULE.json` is replaced by `protocol/ARM_SCHEDULE.json`. The freeze deployments list C only (q = .40, threshold unchanged).
3. **Counts derived from the list length** in `execute.py`, `analyze.py` and `pbs_entry.py` (JOB_WORK_COMPLETE). They replace the 128/512/256/1024 literals and the Text reference.
4. **Bootstrap:** `protocol/bootstrap_indices.npz` = `default_rng(0).integers(0,2641,size=(2000,2641))`, seed 0, 2,000 resamples.
5. **New freeze and preflight:** `src/prepare_freeze.py` was adapted to write the new freeze and run the CPU preflight. It ran on the login node before any request.

**Allocation edits, as in the REPEAT jobs**

6. The allocation guard accepts node-queue, 1 node, 8 requested and 8 allocated GPUs. The walltime cap stays at the original ≤01:00:00, which matches the submitted walltime. All other guards are kept.
7. `run_e3_full.pbs` exports `CUDA_VISIBLE_DEVICES=0,1` and `CUDA_DEVICE_ORDER=PCI_BUS_ID`.
8. The deadline is the replay's own start plus the original 3600 s budget, minus the original 45 s margin. The date stop moves to 2026-09-23 00:00 UTC; the check expression is unchanged.
9. **Output paths:** `P2_STAGE` points to this folder, `P2_RUN` is `run_logs/`, `TMPDIR` is `tmp/`, and `records/` is a real directory. A fresh login-node home-space receipt is in `evidence/pbs/home_check.txt`.

**Kept as-is (flag for the later analysis prompt)**

- The output file names `records/four_arm_requests.jsonl` and `records/two_policy_probes.jsonl` are kept for code compatibility, even though they now hold 2 arms and 1 policy. The freeze keeps its file name `MMLU_PRO_E2E_STAGE2_FREEZE.json`.
- The post-run tools `monitor_resources.py`, `supervise_stage2.py`, `validate_results_cpu.py` and `finalize_reports.py` were copied unmodified. They still contain the original 128-question, four-arm assumptions and are not used by the job.
Cancelled while queued (never ran); E3 moves to ClusterA debug by decision of the project lead.
