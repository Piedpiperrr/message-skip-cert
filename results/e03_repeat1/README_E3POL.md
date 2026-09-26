# P2_R1_E3POL_REPEAT1_20260919T075315Z: E3 timing repeat on ClusterA (records only)

- **Replays:** the three original E2E replays run one after another on one ClusterA node: large (`large/`), then medium (`medium/`), then MMLU-Pro panels (`mmlu/`). A failed replay does not stop the next one.
- **Job:** P2R1_E3POL_A (node 1; node 2 = REPEAT2). The job script is in this folder: `P2R1_E3POL_A.pbs`.
- **Node script:** `run_e3pol_node.sh`. GPUs 0-1 only; hardware configuration in `logs/node_hardware.txt`.
- **Outputs:** `<stage>/records/`, `<stage>/evidence/`, `<stage>/run_logs/`, and the progress files. The original post-run analyses run later on the login node under a separate prompt.
- **Changes:** see `DEVIATIONS.md`; exact diffs in `diffs/`.
