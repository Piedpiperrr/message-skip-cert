# Deviations from the original replays (all outside the timed region; exact changes in diffs/*.diff)

Approved by the project lead on 2026-09-19 (option (b) of the E3 report).

1. **Allocation guards accept the E3 allocation**: queue node-queue, 1 node, 8 requested and 8 allocated GPUs. All other guards are kept: owner, account, state R, single host (exec_host and nodefile), fsreq, strict cgroup match, and CUDA device count == 2.
   - The walltime guard also had to accept the submitted 01:30:00. Large: `walltime=='00:30:00'` becomes `=='01:30:00'`. Medium: budget `<=900` becomes `<=5400`. MMLU-Pro: cap `<=01:00:00` becomes `<=01:30:00`.
   - The walltime change is a necessary consequence of the approved submission walltime; the approval did not list it by name.
2. **GPU visibility**: `run_e3_repeat.pbs` exports `CUDA_VISIBLE_DEVICES=0,1` and `CUDA_DEVICE_ORDER=PCI_BUS_ID`. As in the originals, the helper is on cuda:0 and the receiver and fuser on cuda:1. GPUs 2–7 stay idle.
3. **Deadlines**: each is anchored to the replay's own start (`R1E3_REPLAY_START_EPOCH`, set immediately before that replay) plus its original budget and margin: large 1800−60 s, medium 900−45 s, MMLU-Pro 3600−45 s. The originals anchored to PBS stime.
4. **MMLU-Pro date stop** moved from 2026-09-20 00:00 UTC to 2026-09-23 00:00 UTC. The check expression is unchanged (PBS stime + job walltime).
5. **Freeze-hash manifests recomputed** over the copies after these edits. Original hashes appear in the diffs.
   - Large: `IMPLEMENTATION_FREEZE.json`. `PROTOCOL_FREEZE.json` is unchanged and still matches.
   - Medium: `frozen_files` and `runtime_source_hashes` entries for the original folder are remapped to this copy, and `PBS_script_sha256` is updated.
   - MMLU-Pro: `frozen_files` and `PBS_script_sha256`.
   - External source hashes are unchanged; all of them still matched on 2026-09-19.
6. **Records only**: the large `supervise.py` phases are reduced to `validate_sources.py` + `execute.py` (analyze/render are dropped). Medium and MMLU-Pro already ran analysis only after the job.
7. **Output paths**: the stage path in each stage script points to this copy; `P2_RUN` becomes `<stage>/run_logs`; `TMPDIR` becomes `<stage>/tmp`. MMLU-Pro `records/` is a real directory here; the original was a symlink into `runs/`.
8. **Path fix, not in the approved list**: `src/common.py` `ROOT=P.parent` becomes `ROOT=P.parent.parent`, because each stage copy sits one level below the project root. Every input path still resolves to the same read-only files. No behaviour changes.
9. **Home-space receipt**: `<stage>/evidence/pbs/home_check.txt` was regenerated on the login node on 2026-09-19. The original stage scripts fall back to it when `myquota` is unavailable on compute nodes.
10. **Checks not run**: medium `src/test_preflight.py` was not run, because it asserts the original gpu-queue 00:15:00 fixture. A login-node dry check replaced it and passed 38/38: freeze verification without weights, guard accept/reject on a node-queue record, AST, `bash -n`.
Cancelled while queued (never ran); E3 moves to ClusterA debug by decision of the project lead.
