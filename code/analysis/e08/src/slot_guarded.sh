#!/bin/bash
# Non-frozen wrapper around src/slot.sh. Two jobs' worth of slots were lost when one rank hit a
# node whose GPUs were held by a foreign process: the rank died and mpiexec killed its siblings.
# This wrapper (1) waits for this slot's GPUs to become usable and (2) always exits 0, so a bad
# slot skips its work instead of aborting the whole job. Nothing scientific changes: the frozen
# executor still runs unmodified, and unclaimed lanes are simply picked up by a later job.
set -u
GR="${PALS_RANKID:-${PMI_RANK:-0}}"
LR="${PALS_LOCAL_RANKID:-${PMI_LOCAL_RANK:-0}}"
case "$LR" in 0) GPUS=0,1 ;; 1) GPUS=2,3 ;; *) echo "unexpected local rank $LR"; exit 0 ;; esac
export CUDA_VISIBLE_DEVICES=$GPUS E8_SLOT="r${GR}"
# Pair assignment: rank parity by default, but if one pair has no unfinished lanes left this slot
# joins the other pair instead of exiting idle. Lane locking already allows any number of slots per
# pair, so this only changes which frozen lane a slot claims, never what is computed.
remaining () { local pair=$1 n=0 d; for d in "$E8_DIR"/shards/"$pair"/lane_*; do
    [ -e "$d" ] || { n=$((n+1)); continue; }
    [ -f "$d/LANE_COMPLETE.json" ] || n=$((n+1)); done
  local have; have=$(ls -d "$E8_DIR"/shards/"$pair"/lane_* 2>/dev/null | wc -l)
  echo $(( n + (16 - have) )); }
RS=$(remaining small); RM=$(remaining medium)
if [ $((GR % 2)) -eq 0 ]; then MINE=small; OTHER=medium; else MINE=medium; OTHER=small; fi
if [ "$MINE" = small ] && [ "$RS" -eq 0 ]; then MINE=medium; fi
if [ "$MINE" = medium ] && [ "$RM" -eq 0 ]; then MINE=small; fi
export E8_PAIR=$MINE
echo "PAIRPICK rank=$GR remaining small=$RS medium=$RM -> $E8_PAIR"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
echo "GUARD rank=$GR local=$LR pair=$E8_PAIR gpus=$GPUS host=$(hostname)"
nvidia-smi --query-compute-apps=pid,used_memory,gpu_uuid --format=csv 2>&1 | head -8
"$E8_PY" -u "$E8_DIR/src/gpu_preflight.py"
rc=$?
if [ $rc -ne 0 ]; then
  echo "GUARD rank=$GR skipping: GPUs unusable on $(hostname) (exit $rc); siblings continue"
  exit 0
fi
bash "$E8_DIR/src/slot.sh" "$E8_DIR/src/execute_e8.py"
rc=$?
echo "GUARD rank=$GR executor exit=$rc (reported as 0 so siblings are not killed)"
exit 0
