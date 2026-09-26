#!/bin/bash
# One-off login-node loop (requester decision 2026-09-19): submit P2R1_E3POL_A, then P2R1_E3POL_B, each exactly once,
# only when a ClusterA debug position is free for this user (never more than 1 running + 1 queued), then exit.
# Every 2 min: job-status -u $USER. A submit-job failure is logged and the loop exits without retrying.
# Start: nohup setsid bash autosubmit_e3pol.sh >> <log> 2>&1 < /dev/null &
set -u
P=$DATA_DIR
LOGDIR="$P/P2_R1_EXP_20260919T050555Z/logs/ClusterA"
JOBS=("P2R1_E3POL_A|$P/P2_R1_E3POL_REPEAT1_20260919T075315Z|P2R1_E3POL_A.pbs"
      "P2R1_E3POL_B|$P/P2_R1_E3POL_REPEAT3_20260919T075315Z|P2R1_E3POL_B.pbs")
MAX_SECONDS=$((24 * 3600))   # safety: never linger on the login node for more than 24 h
START=$(date +%s)
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
echo "$(ts) AUTOSUBMIT_START pid=$$ host=$(hostname)"
for spec in "${JOBS[@]}"; do
  IFS='|' read -r name dir script <<< "$spec"
  receipt="$dir/logs/${name}_submit_receipt.txt"
  if [ -e "$receipt" ]; then echo "$(ts) $name already has a receipt ($receipt); not resubmitting; exit"; exit 3; fi
  while true; do
    if [ $(( $(date +%s) - START )) -gt $MAX_SECONDS ]; then echo "$(ts) MAX_LIFETIME reached before submitting $name; exit"; exit 4; fi
    out=$(job-status -u "$USER" 2>&1); rc=$?
    if [ $rc -ne 0 ]; then echo "$(ts) job-status rc=$rc (will retry job-status in 120 s): $out"; sleep 120; continue; fi
    running=$(awk '$1 ~ /^[0-9]+\./ && ($10=="R" || $10=="E" || $10=="B") {n++} END {print n+0}' <<< "$out")
    queued=$(awk '$1 ~ /^[0-9]+\./ && !($10=="R" || $10=="E" || $10=="B") {n++} END {print n+0}' <<< "$out")
    echo "$(ts) job-status: running=$running queued=$queued (waiting to submit $name)"
    if [ "$queued" -eq 0 ] && [ "$running" -le 1 ]; then
      sub=$(cd "$dir" && submit-job  -q debug -l select=2 -l walltime=00:55:00 -l fsreq=<fs> -N "$name" "$script" 2>&1); qrc=$?
      if [ $qrc -ne 0 ] || ! grep -qE '^[0-9]+\.ClusterA-pbs' <<< "$sub"; then
        echo "$(ts) SUBMIT_FAILED $name rc=$qrc: $sub"; echo "$(ts) exiting without retry"; exit 2
      fi
      printf '%s\n%s\n' "$sub" "$(ts)" > "$receipt"
      echo "$(ts) SUBMITTED $name -> $sub"
      sleep 120
      break
    fi
    sleep 120
  done
done
echo "$(ts) AUTOSUBMIT_DONE (both jobs submitted once); exit"
