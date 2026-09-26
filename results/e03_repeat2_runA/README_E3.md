# P2R1_REPEAT2: E3 timing repeat (records only)

- **What this job does:** it runs the three original E2E replays one after another in a single allocation: large (`large/`, copy of P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z), then medium (`medium/`, copy of P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z), then MMLU-Pro (`mmlu/`, copy of P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z).
  - Each replay is started by `run_e3_repeat.pbs` through its own original stage script. The script sets `R1E3_REPLAY_START_EPOCH` immediately before each replay.
  - A failed replay does not stop the next one.
- **Submission:** `submit-job  -q node-queue -l select=1 -l walltime=01:30:00 -l fsreq=<fs> -N P2R1_REPEAT2 [-W depend=afterany:<previous job>] run_e3_repeat.pbs` (see the JOBS record in the report).
- **Node:** this job runs on an **exclusive node**: ClusterB node-queue, `select=1`, which expands to `1:ngpus=8:ncpus=256:mem=960gb` with `place=scatter:excl`.
  - The replays use GPUs 0–1 only (`CUDA_VISIBLE_DEVICES=0,1`: helper on cuda:0, receiver and fuser on cuda:1). GPUs 2–7 stay idle.
  - The original replays ran on **shared nodes**: gpu-queue, `select=1:ngpus=2:ncpus=64:mem=240gb`, `place=pack:shared`. That was job 185809 on ClusterB-gpu-01 (large), 186020 on ClusterB-gpu-06 (medium) and 186281 on ClusterB-gpu-02 (MMLU-Pro).
  - The job writes its actual allocation (queue, Resource_List, exec_vnode) to `logs/job_env.txt`, and GPU snapshots between replays to `logs/replays.log`.
- **Records only:** no analysis runs inside the job.
  - Outputs go to `<stage>/records/`, `<stage>/evidence/`, `<stage>/run_logs/` and the stage's progress files.
  - The original post-run analyses (`large/src/analyze.py`, `medium/src/analyze.py`, `mmlu/src/analyze.py`) will be run later on the login node under a separate prompt.
- **Unchanged from the originals:** code, frozen thresholds, panels, arm rotation, and the timing boundary (`execute.py` and the native runtime are byte-identical). The approved edits are listed in `DEVIATIONS.md`, and the exact changes are in `diffs/{large,medium,mmlu}.diff`.
- **Build and checks:** built by `e3_build/build_e3.py`. A login-node dry check (no model loads) passed 38/38.
