# P2_R1_E3POL_MMLU_C2C_FULL_20260919T075315Z: E3 MMLU-Pro C2C full-population replay on ClusterA (records only)

- **Replay:** the approved 2,641-question, 2-arm replay: fixed C2C vs C2C policy q = .40, 5,282 requests and 2,641 online ProbeMax probes.
- **Job:** P2R1_E3POL_B, node 2. The job script is `P2_R1_E3POL_REPEAT3_20260919T075315Z/P2R1_E3POL_B.pbs`.
- **Node script:** `run_e3pol_node.sh`. GPUs 0-1 only; hardware configuration in `logs/node_hardware.txt`.
- **Outputs:** `records/`, `evidence/`, `run_logs/`. The file names `four_arm_requests.jsonl` and `two_policy_probes.jsonl` are kept from the rebuild. The generalized `src/analyze.py` runs later on the login node.
- **Changes:** see `DEVIATIONS.md` and `provenance/`.
