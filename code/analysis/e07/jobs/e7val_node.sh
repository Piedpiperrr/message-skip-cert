#!/bin/bash
# E7 pre-replay checks on one node: 16-row validation with the new driver (task 4a) and a
# 4-question-per-panel smoke replay with all arms (task 4b).  Two GPU pairs run in parallel:
#   pair 0,1 -> large validation, large smoke, MMLU-Pro smoke
#   pair 2,3 -> medium validation, medium smoke, E6 replay smoke
set -uo pipefail
W=$DATA_DIR/P2_R2_E7_20260919T231531Z
R=$W/jobs/run_stage.sh
mkdir -p "$W/logs" "$W/validation" "$W/smoke"
{ echo "NODE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname) PBS_JOBID=${PBS_JOBID:-none}"
  nvidia-smi -L; } > "$W/logs/val_node.txt" 2>&1

(
  export CUDA_VISIBLE_DEVICES=0,1 STAGE_BUDGET=1500
  E7_KIND=large bash "$R" large e7_validate2.py e7val_large "$W/validation/E7_VALIDATION2_large.json"
  echo "RC_val_large=$?" >> "$W/logs/val_node.txt"
  E7_KIND=large E7_RECORDS=records_e7_smoke E7_NPANEL=4 E7_SMOKE=1 bash "$R" large execute_e7.py e7smoke_large
  echo "RC_smoke_large=$?" >> "$W/logs/val_node.txt"
  E7_KIND=mmlu E7_RECORDS=records_e7_smoke E7_NPANEL=4 E7_SMOKE=1 bash "$R" mmlu execute_e7.py e7smoke_mmlu
  echo "RC_smoke_mmlu=$?" >> "$W/logs/val_node.txt"
) &
A=$!
(
  export CUDA_VISIBLE_DEVICES=2,3 STAGE_BUDGET=1500
  E7_KIND=medium bash "$R" medium e7_validate2.py e7val_medium "$W/validation/E7_VALIDATION2_medium.json"
  echo "RC_val_medium=$?" >> "$W/logs/val_node.txt"
  E7_KIND=medium E7_RECORDS=records_e7_smoke E7_NPANEL=4 E7_SMOKE=1 bash "$R" medium execute_e7.py e7smoke_medium
  echo "RC_smoke_medium=$?" >> "$W/logs/val_node.txt"
  E6R_RECORDS=records_e6_smoke E6R_NPANEL=4 bash "$R" e6replay execute_e6replay.py e6smoke
  echo "RC_smoke_e6=$?" >> "$W/logs/val_node.txt"
) &
B=$!
wait $A; RA=$?
wait $B; RB=$?
echo "PAIR_EXITS A=$RA B=$RB NODE_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$W/logs/val_node.txt"
