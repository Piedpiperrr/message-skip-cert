# P2R1_MMLU_C2C_FULL: E3 MMLU-Pro C2C replay on all 2,641 development group representatives (records only)

- **What this is:** a copy of P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z with the approved scoped rebuild.
  - Question list: all 2,641 MMLU-Pro development group representatives, in frozen Stage-1 `splits/dev_groups.json` order.
  - Arms: fixed C2C and C2C policy only. Which arm runs first alternates per question (even ordinal fixed_C first, odd ordinal policy_C first; 1321/1320).
  - Frozen threshold unchanged: q = .40, threshold 3.838539123535156e-05.
  - Asserted counts are derived from the list length: 5,282 requests and 2,641 online ProbeMax probes.
  - Bootstrap indices: `numpy.random.default_rng(0).integers(0,2641,size=(2000,2641))`.
- **New freeze:** `MMLU_PRO_E2E_STAGE2_FREEZE.json` (sha256 f73e9b90e5a1937c890cfbe1cb0848d5e2aced318d9114d55c7083024047871e). `src/prepare_freeze.py` wrote it on the login node on 2026-09-19, before any request. The same run did the model-free CPU preflight: parser and tokenizer checks for K=3..10, 8 synthetic wrapper cases, and native runtime byte-identical to Stage 1. Log: `logs/prepare_freeze_login.log`.
- **Submission:** `submit-job  -q node-queue -l select=1 -l walltime=01:00:00 -l fsreq=<fs> -N P2R1_MMLU_C2C_FULL -W depend=afterany:<P2R1_REPEAT3 job> run_e3_full.pbs`
- **Node:** this job runs on an **exclusive node**: ClusterB node-queue, `select=1`, which expands to `1:ngpus=8:ncpus=256:mem=960gb` with `place=scatter:excl`.
  - The replay uses GPUs 0–1 only (`CUDA_VISIBLE_DEVICES=0,1`: helper on cuda:0, receiver and fuser on cuda:1). GPUs 2–7 stay idle.
  - The original MMLU-Pro replay (job 186281) ran on a **shared node**: gpu-queue, `select=1:ngpus=2:ncpus=64:mem=240gb`, `place=pack:shared`, ClusterB-gpu-02.
  - The job writes its actual allocation to `logs/job_env.txt`.
- **Records only:** outputs go to `records/`, `evidence/` and `run_logs/`. The generalized `src/analyze.py` runs later on the login node under a separate prompt.
- **Checks:** login dry check passed 12/12. A synthetic model-free run of the generalized `execute.main()` in a scratch mirror completed 5,282 requests and 2,641 probes with alternating first arm. The mirror was then removed; nothing was written here.
