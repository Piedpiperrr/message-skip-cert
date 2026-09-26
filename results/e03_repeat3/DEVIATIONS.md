# Deviations of P2_R1_E3POL_REPEAT3_20260919T075315Z from the original replays

Copies of the ORIGINAL stage folders: `large/` = P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z (job 185809), `medium/` = P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z (job 186020), `mmlu/` = P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z (job 186281, 128-question four-arm panels).
All three originals used 2 GPUs on a shared ClusterB gpu-queue node (select=1:ngpus=2), which satisfies the ≤ 4 GPU condition.
Runs in job P2R1_E3POL_B (node 1; node 2 = MMLU_C2C_FULL). Built 2026-09-19 by `e3_build/build_e3pol.py`, adapted from the ClusterB E3 build `P2_R1_E3_P2R1_REPEAT1_20260919T064808Z/e3_build/build_e3.py`. Exact changes: `diffs/{large,medium,mmlu}.diff`.
Decided by the project lead on 2026-09-19: E3 runs on ClusterA debug, with harness-only edits.

**ClusterA harness edits** (all outside the timed region; `execute.py`, the native runtime, probe, parser, thresholds, panels, arm rotation, no warm-up and batch size 1 are byte-identical to the source folder)

1. **Allocation guards accept the ClusterA debug allocation** (`submit-job  -q debug -l select=2 -l walltime=00:55:00 -l fsreq=<fs>`).
   - queue `debug`; `nodect==2`.
   - `ngpus==0`: ClusterA does not schedule GPUs as a PBS resource; each exclusive node has 4 A100-40GB.
   - This host must be one of the job's 2 hosts in `exec_host`, `exec_vnode` and `PBS_NODEFILE`. The original required it to be the only host.
   - Walltime: large requires exactly `00:55:00` (original `00:30:00`); medium cap ≤ 3300 s (original ≤ 900 s; the replay's own 900 s budget is kept); MMLU-Pro cap ≤ 01:00:00 (unchanged).
   - Kept: owner, account, job state R, fsreq home+sharedfs, and CUDA device count == 2.
2. **GPU visibility:** `run_e3pol_node.sh` exports `CUDA_VISIBLE_DEVICES=0,1` and `CUDA_DEVICE_ORDER=PCI_BUS_ID`. As in the originals, the helper is on cuda:0 and the receiver and fuser on cuda:1. GPUs 2-3 stay idle and nothing else runs on the node.
3. **Deadlines:** each is anchored to the replay's own start (`R1E3_REPLAY_START_EPOCH`, set immediately before that replay) plus its original budget and margin. The originals anchored to PBS stime.
4. **Freeze-hash manifests** recomputed over the copies after these edits. The original hashes are in `diffs/`.
5. **Output paths:** the stage path points to this copy; `P2_RUN` = `<stage>/run_logs`; `TMPDIR` = `<stage>/tmp`; `records/` is a real, empty directory. No replay code uses multiprocessing, tempfile or sockets, so the long TMPDIR is safe (see P2_R1_EXP D4).
6. **Home-space fallback:** `evidence/pbs/home_check.txt` was regenerated on the ClusterA login node on 2026-09-19 (PASSED). The medium and MMLU-Pro stage scripts fall back to this receipt when `check-home-space` fails on a compute node. Their test `rg -q` is replaced by `grep -q` because ripgrep is not installed on ClusterA (approved as harness-level by the requester on 2026-09-19). Large uses `-s` and is unchanged.
7. **Launch:** one 2-node job; `mpiexec -n 2 --ppn 1 --cpu-bind none` starts one shell per node, and each shell runs `run_e3pol_node.sh` of its folder.
   - At the start, the node records its hardware configuration in `logs/node_hardware.txt`: GPU model, driver/CUDA, `nvidia-smi topo -m`, `lscpu`, affinity, the scheduler record, cgroup and tool availability.
   - Replay starts and ends go to `logs/replays.log`.
8. **Records only:** no analysis runs in the job. The medium and MMLU-Pro originals already analysed only after the job.
9. **Checks:** a login-node dry check passed 125/125 over all four E3POL folders (`logs/dry_check_login.txt`; script and fixture in `e3_build/`). It covered:
   - `bash -n` and Python compile;
   - freeze verification without weights (large: PROTOCOL and IMPLEMENTATION freezes, plus SOURCE_INDEX sizes and hashes of files under 50 MB);
   - guard accept/reject against the real ClusterA 2-node debug job record (job 7634910): accepts either node; rejects a foreign host, a 1-node record, a ClusterB-style queue/ngpus record, and 01:30:00;
   - deadline and date-stop edits, model paths, and job dispatch for ranks 0 and 1.

10. **Large replay: cgroup check made non-fatal (approved as harness-level by the requester on 2026-09-19).**
   - The original `pbs_entry.py` asserted a ClusterB cgroup path (`/jobs/<id>`); the ClusterA compute-node cgroup layout could not be observed from the login node.
   - Both the original match and a ClusterA-style match (a path component equal to the job id, or starting with `<id>.`) are recorded in `evidence/pbs/allocation.json` and `execution_clearance.json` (`cgroup_match_fatal: false`).
   - `common.compute()` no longer requires the match. This is the policy the medium and MMLU-Pro guards already use ("cgroup spelling is nonfatal").
   - The host prefix check is now `x3` (ClusterA compute) instead of `ClusterB-gpu`, in `pbs_entry.py` and `common.compute()`.
11. **ROOT path fix:** `src/common.py` `ROOT=P.parent` → `ROOT=P.parent.parent` (each stage copy sits one level below the project root). Every input path resolves to the same read-only files.
12. **Large records-only phases:** `supervise.py` runs `validate_sources.py` and `execute.py` only; the original `analyze.py` and `render.py` run later on the login node.
13. **MMLU-Pro date stop** moved from 2026-09-20 00:00 UTC to 2026-09-23 00:00 UTC; the check expression is unchanged.

**Deadlines:** large own start + 1800 − 60 s; medium own start + 900 − 45 s; MMLU-Pro own start + 3600 − 45 s.

**Recomputed manifests (original → copy):**
   - large: `IMPLEMENTATION_FREEZE.json` 227383220ead… → 0ebafe82ece3…
   - medium: `MEDIUM_PAIR_E2E_STAGE2_FREEZE.json` ad65edf75f08… → 7d026aca8873…
   - mmlu: `MMLU_PRO_E2E_STAGE2_FREEZE.json` e13529cf9eff… → 00a890265acc…
   - Large `PROTOCOL_FREEZE.json` is unchanged and still matches.
   - Medium `frozen_files` and `runtime_source_hashes` entries are remapped to this copy.

**Planned node time**
- ClusterB allocations: large 952 s + medium 334 s + MMLU-Pro 574 s = 31.0 min, model loading included.
- Plus 6 Python starts × 1–1.5 min (large: `pbs_entry` → execv `supervise` → `validate_sources` → `execute`; medium: `pbs_entry`; MMLU-Pro: `pbs_entry`).
- Total ≈ 37–40 min, planned 40 min. The limit is 50 min and the job walltime 55 min.

**Queue actually used (added 2026-09-19T08:25Z; author addendum "use other ClusterA queues when they help"):** job P2R1_E3POL_B runs in `debug-2` (run020, submitted 08:19:31Z; this folder = node 1 (rank 0)).
- Why debug-2: `queue-c` allows 1 running job per project, and that slot was held by another project job (7634845, 24 h walltime). `queue-p` had no free nodes: a test job stayed Q ("Insufficient amount of resource: queue_tags") and was deleted. `debug-2` ran a 1-node test job at once (7635494, exit 0), and E3POL_A had taken the debug slot.
- The only extra harness change (allowed by the addendum) is that the E3 guards accept the queue actually used: `debug` → `debug-2` in `large/src/pbs_entry.py`, `medium/src/guard_checks.py`, `mmlu/src/guard_checks.py`. Manifests were re-hashed; the diff is in `diffs/queue_debug_2.diff`.
- Dry check with a debug-2 fixture: 52/52 passed (`logs/dry_check_login_debug_2.txt`).
- The job-script comment line now reads `-q debug-2`.
- Host: see `logs/node_hardware.txt` once the job starts (appended below when known).
- **Hosts (added 2026-09-19T09:04Z):** job 7635512 started 08:42:48Z in `debug-2` on compute-node (node 1, REPEAT3) + compute-node (node 2, MMLU_C2C_FULL). This folder: compute-node (`logs/node_hardware.txt`). Guards passed; `strict_cgroup_match: true`.

**Analysis (login node, 2026-09-19T09:30Z; P2_R1_EXP DEVIATIONS D7).**
- The original `src/analyze.py` of each replay ran unchanged through `e3_build/run_original_analyses.py`. Exact substitutions (in `diffs/analysis_adapter_<stage>.diff`):
  - Outputs go to `<stage>/results/` (linked from `results/<stage>`) instead of the stage's `summary/`, `records/`, `evidence/` and top-level files. The medium and MMLU-Pro write helpers assert that outputs stay inside the stage.
  - large: `common.compute()` is skipped, since it asserts a compute hostname. The adapter asserts the records' job_id equals `execution_clearance.json`.
  - MMLU-Pro/FULL: the job ledger is read from `job-status -x -f -F json` (`results/.../RESOURCE_LEDGER_from_qstat.json`) instead of the login-node supervisor's RESOURCE_LEDGER.json.
- Latency metrics use `e3_build/e3_metrics.py`, i.e. P2_R1_CPU item5 logic.
- No record file was modified.
