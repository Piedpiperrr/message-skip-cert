#!/bin/bash
# E7 full replay, node B: MMLU-Pro (Text, C2C), medium/OBQA (C2C), medium/ARC (C2C),
# then the E6 Text+fact replay (E6 freeze section 6; certified q = 0.75 > 0).
# One stage at a time, GPUs 0,1 only; nothing else runs on this node.
set -uo pipefail
W=$DATA_DIR/P2_R2_E7_20260919T231531Z
export CUDA_VISIBLE_DEVICES=0,1 STAGE_BUDGET=2400
{ echo "NODE_B_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname) PBS_JOBID=${PBS_JOBID:-none}"
  nvidia-smi -L; nvidia-smi --query-gpu=index,name,uuid,driver_version,memory.total --format=csv
  echo "## scheduler"; job-status -f "$PBS_JOBID" | grep -E 'queue =|Resource_List|exec_host'
} > "$W/logs/nodeB_hardware.txt" 2>&1
E7_KIND=mmlu bash "$W/jobs/run_stage.sh" mmlu execute_e7.py e7_full_mmlu
echo "RC_mmlu=$?" >> "$W/logs/nodeB_hardware.txt"
E7_KIND=medium bash "$W/jobs/run_stage.sh" medium execute_e7.py e7_full_medium
echo "RC_medium=$?" >> "$W/logs/nodeB_hardware.txt"
bash "$W/jobs/run_stage.sh" e6replay execute_e6replay.py e6_full
echo "RC_e6replay=$? NODE_B_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$W/logs/nodeB_hardware.txt"
