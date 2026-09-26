#!/bin/bash
# One lane per GPU. Always exits 0 so a bad GPU skips its lane instead of killing the job.
set -u
GR="${PALS_RANKID:-${PMI_RANK:-0}}"
LR="${PALS_LOCAL_RANKID:-${PMI_LOCAL_RANK:-0}}"
export CUDA_VISIBLE_DEVICES=$LR E9_RANK="$GR"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export TMPDIR="/tmp/e9c.$$"; mkdir -p "$TMPDIR"     # short TMPDIR (AF_UNIX path limit)
echo "SLOT rank=$GR local=$LR gpu=$LR host=$(hostname)"
"$E9_PY" -u "$E9_DIR/src/gpu_preflight.py" || { echo "SLOT rank=$GR skipping: GPU unusable"; exit 0; }
"$E9_PY" -u "$E9_DIR/src/e9c_prefill.py" --rank "$GR" --plan "$E9_DIR/jobs/LANE_PLAN.json" \
         --out "$E9_DIR/records" --deadline-epoch "$E9_DEADLINE_EPOCH"
echo "SLOT rank=$GR executor exit=$? (reported as 0 so siblings are not killed)"
exit 0
