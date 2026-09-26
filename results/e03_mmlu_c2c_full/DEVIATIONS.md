# Deviations of P2_R1_E3POL_MMLU_C2C_FULL_20260919T075315Z from the approved ClusterB rebuild

Copy of the approved scoped rebuild `P2_R1_E3_P2R1_MMLU_C2C_FULL_20260919T065245Z` (freeze f73e9b90e5a1937c890cfbe1cb0848d5e2aced318d9114d55c7083024047871e): all 2,641 MMLU-Pro development group representatives, fixed C2C vs C2C policy (q = .40, threshold unchanged), alternating first arm, 5,282 requests and 2,641 online probes.
- The rebuild's own changes from the original MMLU-Pro replay (job 186281, 2 GPUs on a shared ClusterB gpu-queue node, which satisfies the ≤ 4 GPU condition) are documented in `provenance/`: its DEVIATIONS, README, diffs, build script and prepare_freeze log.
- Runs in job P2R1_E3POL_B, on node 2; node 1 runs REPEAT3.
- Built 2026-09-19 by `e3_build/build_e3pol.py`. Exact changes vs the rebuild: `diffs/mmlu_full_ClusterA.diff`.
- Decided by the project lead on 2026-09-19: E3 runs on ClusterA debug, with harness-only edits.

**ClusterA harness edits** (all outside the timed region; `execute.py`, the native runtime, probe, parser, thresholds, panels, arm rotation, no warm-up and batch size 1 are byte-identical to the source folder)

1. **Allocation guards accept the ClusterA debug allocation** (`submit-job  -q debug -l select=2 -l walltime=00:55:00 -l fsreq=<fs>`).
   - queue `debug`; `nodect==2`.
   - `ngpus==0`: ClusterA does not schedule GPUs as a PBS resource; each exclusive node has 4 A100-40GB.
   - This host must be one of the job's 2 hosts in `exec_host`, `exec_vnode` and `PBS_NODEFILE`. The original required it to be the only host.
   - Walltime: cap ≤ 01:00:00, unchanged (the job requests 00:55:00).
   - Kept: owner, account, job state R, fsreq home+sharedfs, and CUDA device count == 2.
2. **GPU visibility:** `run_e3pol_node.sh` exports `CUDA_VISIBLE_DEVICES=0,1` and `CUDA_DEVICE_ORDER=PCI_BUS_ID`. As in the originals, the helper is on cuda:0 and the receiver and fuser on cuda:1. GPUs 2-3 stay idle and nothing else runs on the node.
3. **Deadlines:** each is anchored to the replay's own start (`R1E3_REPLAY_START_EPOCH`, set immediately before that replay) plus its original budget and margin. The originals anchored to PBS stime.
4. **Freeze-hash manifests** recomputed over the copies after these edits. The original hashes are in `diffs/`.
5. **Output paths:** the stage path points to this copy; `P2_RUN` = `<stage>/run_logs`; `TMPDIR` = `<stage>/tmp`; `records/` is a real, empty directory. No replay code uses multiprocessing, tempfile or sockets, so the long TMPDIR is safe (see P2_R1_EXP D4).
6. **Home-space fallback:** `evidence/pbs/home_check.txt` was regenerated on the ClusterA login node on 2026-09-19 (PASSED). `run_mmlu_stage2.pbs` falls back to this receipt when `check-home-space` fails on a compute node. Its test `rg -q` is replaced by `grep -q` because ripgrep is not installed on ClusterA (approved as harness-level by the requester on 2026-09-19).
7. **Launch:** one 2-node job; `mpiexec -n 2 --ppn 1 --cpu-bind none` starts one shell per node, and each shell runs `run_e3pol_node.sh` of its folder.
   - At the start, the node records its hardware configuration in `logs/node_hardware.txt`: GPU model, driver/CUDA, `nvidia-smi topo -m`, `lscpu`, affinity, the scheduler record, cgroup and tool availability.
   - Replay starts and ends go to `logs/replays.log`.
8. **Records only:** no analysis runs in the job. The generalized `src/analyze.py` runs later on the login node.
9. **Checks:** a login-node dry check passed 125/125 over all four E3POL folders (`logs/dry_check_login.txt`; script and fixture in `e3_build/`). It covered:
   - `bash -n` and Python compile;
   - freeze verification without weights (large: PROTOCOL and IMPLEMENTATION freezes, plus SOURCE_INDEX sizes and hashes of files under 50 MB);
   - guard accept/reject against the real ClusterA 2-node debug job record (job 7634910): accepts either node; rejects a foreign host, a 1-node record, a ClusterB-style queue/ngpus record, and 01:30:00;
   - deadline and date-stop edits, model paths, and job dispatch for ranks 0 and 1.

**Carried over unchanged from the rebuild** (already approved there):
- deadline = own start + 3600 − 45 s;
- MMLU-Pro date stop 2026-09-23 00:00 UTC;
- the folder stays flat, so `ROOT=P.parent` needs no path fix;
- `P2_RUN` = `run_logs/` and `TMPDIR` = `tmp/`.

**Recomputed freeze:** `MMLU_PRO_E2E_STAGE2_FREEZE.json` f73e9b90… (approved rebuild) → ccf65bbaa94b12d56031d37bda1f5b0a806f08e1639a9cf1c1f8139a242a3836.
- Only `frozen_files` changed (`src/guard_checks.py`, `run_mmlu_stage2.pbs`), together with `PBS_script_sha256` and an `E3_manifest_recomputed` note.
- `evidence/FREEZE_RECEIPT.json` is the rebuild's receipt for f73e9b90…, kept unchanged.

**Planned node time**
- 5,282 requests × ~0.345 s = 30.4 min. The original C-arm means were 340.8 ms (fixed_C) and 332.6 ms (policy_C, including its probe), plus about 8 ms of logging per request.
- Plus the original replay's non-request time of 188 s (574 s allocation − 386 s of requests: guards, weight hashing, model load).
- Plus 1 Python start of 1–1.5 min.
- Total ≈ 35 min. The limit is 50 min and the job walltime 55 min.

**Queue actually used (added 2026-09-19T08:25Z; author addendum "use other ClusterA queues when they help"):** job P2R1_E3POL_B runs in `debug-2` (run020, submitted 08:19:31Z; this folder = node 2 (rank 1)).
- Why debug-2: `queue-c` allows 1 running job per project, and that slot was held by another project job (7634845, 24 h walltime). `queue-p` had no free nodes: a test job stayed Q ("Insufficient amount of resource: queue_tags") and was deleted. `debug-2` ran a 1-node test job at once (7635494, exit 0), and E3POL_A had taken the debug slot.
- The only extra harness change (allowed by the addendum) is that the E3 guards accept the queue actually used: `debug` → `debug-2` in `src/guard_checks.py`. Manifests were re-hashed; the diff is in `diffs/queue_debug_2.diff`.
- Dry check with a debug-2 fixture: 52/52 passed (`logs/dry_check_login_debug_2.txt`).
- The job-script comment line now reads `-q debug-2`.
- Host: see `logs/node_hardware.txt` once the job starts (appended below when known).
- **Hosts (added 2026-09-19T09:04Z):** job 7635512 started 08:42:48Z in `debug-2` on compute-node (node 1, REPEAT3) + compute-node (node 2, MMLU_C2C_FULL). This folder: compute-node (`logs/node_hardware.txt`). `evidence/ALLOCATION_GUARD.json` status PASS.

**Analysis (login node, 2026-09-19T09:30Z; P2_R1_EXP DEVIATIONS D7).**
- The original `src/analyze.py` of each replay ran unchanged through `e3_build/run_original_analyses.py`. Exact substitutions (in `diffs/analysis_adapter_<stage>.diff`):
  - Outputs go to `<stage>/results/` (linked from `results/<stage>`) instead of the stage's `summary/`, `records/`, `evidence/` and top-level files. The medium and MMLU-Pro write helpers assert that outputs stay inside the stage.
  - large: `common.compute()` is skipped, since it asserts a compute hostname. The adapter asserts the records' job_id equals `execution_clearance.json`.
  - MMLU-Pro/FULL: the job ledger is read from `job-status -x -f -F json` (`results/.../RESOURCE_LEDGER_from_qstat.json`) instead of the login-node supervisor's RESOURCE_LEDGER.json.
- Latency metrics use `e3_build/e3_metrics.py`, i.e. P2_R1_CPU item5 logic.
- No record file was modified.
