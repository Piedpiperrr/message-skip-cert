#!/bin/bash
# E7 full replay, node A: large/OBQA (Text, C2C) and large/ARC (Text, C2C) panels.
# GPUs 0,1 only (helper cuda:0, receiver+fuser cuda:1); nothing else runs on this node.
set -uo pipefail
W=$DATA_DIR/P2_R2_E7_20260919T231531Z
export CUDA_VISIBLE_DEVICES=0,1 STAGE_BUDGET=2400
{ echo "NODE_A_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname) PBS_JOBID=${PBS_JOBID:-none}"
  nvidia-smi -L; nvidia-smi --query-gpu=index,name,uuid,driver_version,memory.total --format=csv
  echo "## torch"; grep -E "^(__version__|cuda)" "$DATA_ROOT/software/envs/c2c_official/lib/python3.10/site-packages/torch/version.py" 2>/dev/null
  echo "## scheduler"; job-status -f "$PBS_JOBID" | grep -E 'queue =|Resource_List|exec_host'
} > "$W/logs/nodeA_hardware.txt" 2>&1
E7_KIND=large bash "$W/jobs/run_stage.sh" large execute_e7.py e7_full_large
echo "RC_large=$? NODE_A_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$W/logs/nodeA_hardware.txt"
