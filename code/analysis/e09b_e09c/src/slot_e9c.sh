#!/bin/bash
# E9C phase: the frozen 4-lane plan, one GPU per lane (the first GPU of this slot's pair).
set -u
GR="${PALS_RANKID:-${PMI_RANK:-0}}"
LR="${PALS_LOCAL_RANKID:-${PMI_LOCAL_RANK:-0}}"
case "$LR" in 0) GPU=0 ;; 1) GPU=2 ;; *) echo "unexpected local rank $LR"; exit 0 ;; esac
export CUDA_VISIBLE_DEVICES=$GPU E9_RANK="$GR"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export TMPDIR="/tmp/e9c.$$"; mkdir -p "$TMPDIR"
echo "E9C SLOT rank=$GR gpu=$GPU host=$(hostname)"
"$E9_PY" -u "$E9_DIR/src/gpu_preflight.py" || { echo "E9C rank=$GR skipping: GPU unusable"; exit 0; }
"$E9_PY" -u "$E9_DIR/src/e9c_prefill.py" --rank "$GR" --plan "$E9_DIR/jobs/LANE_PLAN.json" \
         --out "$E9_DIR/records" --deadline-epoch "$E9_E9C_DEADLINE"
echo "E9C rank=$GR exit=$? (reported as 0 so siblings are not killed)"
exit 0
