# Deviations from PROTOCOL_FREEZE.md

## D1 — Queue and resource request: gpu-queue select=8 → node-queue select=1 (2026-09-19T05:46Z, before any model output)

- **What changed:** the job is submitted as `submit-job  -q node-queue -l select=1 -l walltime=04:00:00 -l fsreq=<fs> -N P2R1_E1E4 run_r1.pbs`. PROTOCOL_FREEZE.md §0 froze `-q gpu-queue -l select=8`.
- **Why:** submit-job rejected the gpu-queue submission at 05:24Z with `would exceed queue gpu-queue's per-project limit`, so no job was created (see logs/SUBMISSION_STATUS.md). The requester approved switching to node-queue with one node.
- **Script edit:** `src/run_r1.pbs` contains no `#SCHED` queue or select directives, because these were given on the submit-job command line. The only line naming the queue or select is the `# Submit:` comment on line 8, and it was updated to the new command. Nothing else in the script changed. Its SHA-256 goes from 6e71fe939d63e681461e8a9ca10947715d31e71ff8cba4817079eaa672cda0b1 (freeze) to 5bd9e28f200c8ea74f256ddf781f2c4f81ff60cc31dcc01546abf16746b068cb. Every other file hashed in PROTOCOL_FREEZE.md §8 still matches.
- **Effect on resources:** in node-queue, `select=1` expands to `1:ngpus=8:ncpus=256:mem=960gb` with `place=scatter:excl`. This is one exclusive 8×A100-40GB node, the same resources `select=8` gives in gpu-queue. The GPU map, populations, variants, settings, drivers and analysis are unchanged. The script still asserts that 8 GPUs are visible and logs the result in logs/job_env.txt.
- **Other decision (not a deviation):** the requester confirmed keeping the supplementary V0 run, as frozen.

## D2 — Job 187101 cancelled; E1, E4 and E2b move to ClusterA debug (2026-09-19T06:40Z, before any model output)

- **What changed:** job run017 (P2R1_E1E4, ClusterB node-queue select=1) was cancelled with `job-delete` at 2026-09-19T06:40Z. It had stayed Q ("Not Running: No available resources on nodes") since submission at 05:46:50Z. It never started: final state F, substate 91, "…and terminated". No model output exists in results/ or logs/.
- **Why:** the project lead changed the routing. E1, E4 and the E2b feature extraction will run on ClusterA debug from a separate ClusterA session in this same folder. ClusterB is reserved for the E3 timing jobs.
- **Scope:** no other file in this folder was changed. PROTOCOL_FREEZE.md, src/ and records/ are untouched by this entry.

## D3 — Run on ClusterA: one 2-node debug job, ClusterA job script, new GPU map, V0 first, reproduction checks added (2026-09-19T07:15Z, before any model output)

- **Machine and job:** ClusterA, queue debug, one job: `submit-job  -q debug -l select=2 -l walltime=00:55:00 -l fsreq=<fs> -N P2R1_E1E4_POL src/ClusterA/run_r1_ClusterA.pbs`. Two exclusive nodes, 4× A100-SXM4-40GB each. This replaces the ClusterB submission in §0 and D1.
- **Job scripts (new; frozen `src/run_r1.pbs` is neither used nor changed):**
  - `src/ClusterA/run_r1_ClusterA.pbs` starts one shell per node with `mpiexec -n 2 --ppn 1 --cpu-bind none`.
  - `src/ClusterA/node_r1_ClusterA.sh` runs four GPU chains per node in the background, pinned with `CUDA_VISIBLE_DEVICES`, then waits.
  - The environment is the frozen one: same exports, the-cluster proxy, HF offline, caches in `cache/`.
  - Logs go to `logs/ClusterA/`.
  - All harness changes are in `src/ClusterA/HARNESS_CHANGES.diff`.
- **Stop rule:** `R1_DEADLINE_EPOCH` = job start + 50 min (55-min walltime minus 5 min). This replaces start + 3 h 45 min. The drivers' stop logic is unchanged.
- **GPU map.** Physical GPU index per node, `CUDA_DEVICE_ORDER=PCI_BUS_ID`. Durations are planned minutes, not measurements; the basis is given below.

  | node / GPU | chain | planned min |
  |---|---|---|
  | 1 / 0 | OBQA prefetch (CPU, as frozen) → E1 OFFICIAL chain A (large C2C, small R) → E4 large OBQA+ARC V2 | ~32 |
  | 1 / 1 | OBQA prefetch → E1 OFFICIAL chain B (large R, medium R, medium C2C) → CPU `render_official_prompts.py` | ~25 GPU + ~8 CPU |
  | 1 / 2-3 | E1 OURS on the 500 OBQA test questions, R and C2C: large → medium → small (helper GPU2, receiver+fuser GPU3) | ~27 |
  | 2 / 0 | E4 large MMLU-Pro dev (2,641): V0, V1 | ~31 |
  | 2 / 1 | E4 large OBQA dev + ARC dev: V0, V1 → E4 large MMLU-Pro V2 | ~38 |
  | 2 / 2 | E4 small, then medium, OBQA dev + ARC dev: V0, V1, V2 | ~37 |
  | 2 / 3 | E2b large (OBQA dev reproduction, MMLU-Pro fit/cal/dev, ARC dev) → medium (OBQA/ARC fit/cal/dev) → small (OBQA/ARC dev) | ~30 |

  - E1 OFFICIAL chains A and B are unchanged. The clean evaluator now sees the node's 4 GPUs instead of 8, and `gpu_ids` [0]/[1] still selects the physical GPU.
  - Large OBQA+ARC V2 moved from node 2 GPU 1 to node 1 GPU 0 so that every chain fits the budget.
- **Basis for planned minutes:**
  - ClusterB per-request means from the saved outputs:
    - receiver-only: large 254/268/274 ms (OBQA/ARC/MMLU-Pro), small 233/338 ms, medium 216/229 ms;
    - C2C: large 336, medium 394, small 282 ms.
  - Feature wall time per item: large 58–63 ms and small 45–48 ms (P2_E1_DIRECTION). task7 official small C2C: 4 min 30 s for 500 questions.
  - Assumptions, where no ClusterB record exists:
    - V2 ≈ 1.5× R;
    - large MMLU-Pro features ≈ 80 ms/item (mean prompt 279 vs 117 tokens);
    - medium features ≈ 47 ms/item;
    - official large-pair runs estimated.
  - Overheads: +10% for per-record fsync, and ~1.5 min cold start plus model load per Python process.
- **V0 first:** V0 runs in the same process as V1 (and V2), first in each question's variant loop (`--variants V0,V1[,V2]`). It no longer runs as a separate pass afterwards.
  - Because E4 output names follow the variant list, the files are `results/e4/<pair>_<ds>__V0-V1.jsonl`, `__V2.jsonl` or `__V0-V1-V2.jsonl`, instead of `__V1-V2.jsonl` plus `__V0.jsonl`.
  - V0 is now also a reproduction check against the saved ClusterB R outputs for all 7 populations.
- **Reproduction checks added:**
  - (a) V0 on all 7 E4 populations, as above.
  - (b) E2b large/OBQA dev (742) re-extraction, to compare against the saved ClusterB features in `P2_RISK_CALIBRATION_BINARY_20260914T043954Z/features/dev`.
    - Its rows are the frozen `e2b_small_obqa_dev.jsonl` (SHA-256 fcf0743c…), reached through a new relative symlink `records/populations/e2b_large_obqa_dev.jsonl`.
    - The ids and their order equal the saved feature index.
  - (c) Not included: the large-pair ARC dev R+C2C rerun through E1 OURS. `e1_ours.py` is fixed to `e1_obqa_test500.jsonl` (it asserts 500 rows and reads `official_index`). Running ARC would need a driver change, which goes beyond harness, so it awaits a decision.
- **One harness edit to a frozen file:**
  - `src/extract_harness_r1.py` `require_compute()` now also accepts ClusterA compute hostnames (`x3…`). Login nodes are still refused.
  - SHA-256 12f2a963… → 4916764d…
  - Every other file hashed in §8 is unchanged (run_r1.pbs as in D1).
  - The requester accepted both E2b harness changes (host check, population symlink) on 2026-09-19.
- **Not run in this job:** `analyze_r1.py`.
- **Protocol content unchanged:** populations, variants, prompts, generation settings, parser, models and fusers, feature computation, metrics.

## D4 — E1 OFFICIAL rerun with a short node-local TMPDIR (prepared 2026-09-19T07:50Z, not yet submitted)

- **Cause:** in job 7634910, all 10 official-evaluator runs (5 runs × clean + patch) exited 1 before loading any model.
  - `unified_evaluator.py` calls `mp.Manager()`, which binds a Unix socket under TMPDIR.
  - The frozen TMPDIR (`$NEW/cache/tmp`) gives a socket path of about 138 bytes, which is over the AF_UNIX limit: `OSError: AF_UNIX path too long`.
  - A login-node check reproduced the failure with the frozen TMPDIR. `/tmp/p2r1_<id>` (about 49 bytes) worked.
- **What changed:** TMPDIR, TMP and TEMP are set to `/tmp/p2r1_<numeric PBS job id>` (node-local) only for the two `e1_official.py --chain` processes and the evaluator subprocesses they start. Nothing else changes: the evaluators, configs (built by the unchanged `make_config`), chains A and B, and the clean-then-patch fallback are all as frozen.
- **Failed attempt archived unchanged** before the rerun (SHA-256 identical before and after; list in `results/e1/official/_failed_7634910/ARCHIVE_SHA256SUMS.txt`):
  - `records/e1_official_configs/*.yaml` → `records/e1_official_configs/_failed_7634910/`
  - `results/e1/official/{*__clean,*__patch,RUNS_chainA.jsonl,RUNS_chainB.jsonl,PREFETCH_STATUS.json}` → `results/e1/official/_failed_7634910/`
  - `results/e1/prompts/official.json` (task7 config only) → `results/e1/official/_failed_7634910/prompts/official.json`
  - `logs/e1_official_eval_gpu{0,1}.log` stay in place. The rerun appends new sections, each headed `===== <run> <kind> <utc> =====`.
- **Job:** `submit-job  -q debug -l select=1 -l walltime=00:40:00 -l fsreq=<fs> -N P2R1_E1FIX_POL src/ClusterA/run_e1fix_ClusterA.pbs`.
  - Sequence: OBQA prefetch (as frozen), then chain A on GPU 0 and chain B on GPU 1, then `render_official_prompts.py` (CPU).
  - `R1_DEADLINE_EPOCH` = job start + 35 min.
  - Logs go to `logs/ClusterA_e1fix/`. Diff: `src/ClusterA/E1FIX_CHANGES.diff`.
  - The job-environment log also records, as logging only, whether `job-status`, `myquota` and `rg` exist on the compute node, the cgroup of the job shell and of an mpiexec rank, and a compute-node `check-home-space` run. This is evidence for the prepared E3 ClusterA guards.
- **Protocol unchanged.**

## D5 — Large-pair ARC dev R+C2C reproduction through E1 OURS (prepared 2026-09-19T07:50Z, not yet submitted; supersedes D3 (c))

- **What changed:** `src/e1_ours.py` gains `--population {e1_obqa_test500 (default), e4_large_arc}`.
  - With `e4_large_arc` (large pair only), the rows are the frozen `records/populations/e4_large_arc.jsonl`: the saved `query` plus `id`, with `official_index=None`.
  - Parsing uses each row's `legal_labels`. Three ARC questions have A–C and one has A–E.
  - Outputs go to separate files: `results/e1/ours/large__e4_large_arc.jsonl`, `large__e4_large_arc_environment.json`, and `results/e1/prompts/ours_large__e4_large_arc.json`.
  - The default call is unchanged: same rows, labels, output paths and record fields.
  - SHA-256 91eb3d8b… → 5e92c42c…; diff in `src/ClusterA/E1FIX_CHANGES.diff`.
  - The E1 OURS runs of job 7634910 all started before this edit (last start 07:34:36Z, edit 07:39:46Z), so they used the frozen file.
- **Run:** in the same job as D4, on GPUs 2-3 (helper = GPU2, receiver + fuser = GPU3). It uses the same runner as E1 OURS (`runtime.Runner(frozen pair config)`) and makes one R request and one C2C request per question. The results are to be compared with the saved ClusterB large ARC outputs (`P2_9_20260911T045010Z/results/large/validation_cases.jsonl`).
- **Protocol unchanged.**

**D4/D5 execution record (added 2026-09-19T08:25Z):** P2R1_E1FIX_POL = run018, queue `debug`, host compute-node. It ran 08:06–08:16Z (walltime 00:09:34) and exited 0.

## D6 — Analysis on the login node (2026-09-19T08:47–09:10Z, after jobs 7634910 and 7635393 ended)

- **Frozen `src/analyze_r1.py` (unchanged, SHA-256 29028eab…)** runs through `src/ClusterA/analyze_r1_ClusterA.py`. The adapter asserts the frozen hash and applies two exact-string substitutions in memory:
  1. E4 variant files are loaded from every `results/e4/<pair>_<ds>__V*.jsonl`, because D3 named them by variant list (`__V0-V1`, `__V2`, `__V0-V1-V2`) instead of `__V1-V2` + `__V0`. Each record carries its own `variant` and `pos`, and duplicates are asserted absent.
  2. Its summary is written to `results/SUMMARY_analyze_r1.md` instead of `results/SUMMARY.md`.
  - Everything else is the frozen code: hash-before-gold order, parser, metrics and CSV names.
  - It ran with OPENBLAS/OMP/MKL threads = 1: the first attempt crashed at import (OpenBLAS could not create 64 threads under the login-node limits) before writing anything.
- **New analysis scripts** (read records only; write only `results/` CSVs):
  - `src/ClusterA/repro_checks_ClusterA.py`: reproduction checks (a)–(c). Its PASS criteria were fixed in its header before any result was seen. It re-verifies `OUTPUT_HASHES.json` first.
  - `src/ClusterA/d_certification_ClusterA.py`: learned control D for 14 settings, using P2_R1_CPU's code and frozen LR.
    - Settings computed in P2_R1_CPU keep their q, threshold and cal n/k. Their pending dev metrics use the saved P2_R1_CPU models on the ClusterA E2b dev features.
    - 6 new settings (medium, MMLU-Pro) are fitted on E2b features; their models are in `results/d_models/`.
  - `src/ClusterA/make_summary_ClusterA.py`: writes `results/SUMMARY.md` from the CSVs.
- **Protocol unchanged.** No record file was modified: the 61 hashed output files were re-verified.

## D7 — E3 analysis on the login node (2026-09-19T09:26–09:40Z, after jobs 7635399 and 7635512 ended with exit 0)

- **Original analyses:** each replay's `src/analyze.py` ran unchanged through `src/ClusterA/e3/run_original_analyses.py`, which applies exact-string substitutions only (diffs in each E3 folder's `diffs/analysis_adapter_<stage>.diff`):
  - Outputs go to `<stage>/results/` (linked as `<E3 folder>/results/<stage>`). The medium and MMLU-Pro write helpers assert that outputs stay inside the stage folder.
  - large: `common.compute()` (a compute-hostname assert) is skipped; the adapter asserts the record job_id equals `execution_clearance.json`.
  - MMLU-Pro/FULL: the job ledger (job_state F, job_id) comes from `job-status -x -f -F json` instead of the login-node supervisor's RESOURCE_LEDGER.json.
  - All 10 stage analyses exited 0, so every original assertion held.
  - A first attempt wrote to `<E3 folder>/results/<stage>/`. The medium and MMLU-Pro guards refused it, and those partial outputs (analysis outputs only) were removed before the rerun.
- **Metrics:** `src/ClusterA/e3/e3_metrics.py` applies the rules fixed before the runs, using P2_R1_CPU item5 logic. Version (a) equals the original analyses' outputs in all 25 cells.
  - `src/ClusterA/e3/make_e3_summary.py` writes `results/E3_SUMMARY.md` and reads `results/E3_*.csv`.
- **Records:** none modified (no file under any `records/` changed after 09:15Z).
