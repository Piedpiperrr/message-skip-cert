#!/bin/bash
# One E20F slot = one GPU (CUDA_VISIBLE_DEVICES = local rank). Always exits 0 so one rank never kills the allocation.
set -u
GR="${PALS_RANKID:-${PMI_RANK:-0}}"
LR="${PALS_LOCAL_RANKID:-${PMI_LOCAL_RANK:-0}}"
export CUDA_VISIBLE_DEVICES=$LR
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1
export TMPDIR="/tmp/e20f.$GR"; mkdir -p "$TMPDIR"
echo "E20F SLOT phase=$E20F_PHASE tag=$E20F_TAG rank=$GR local=$LR gpu=$CUDA_VISIBLE_DEVICES host=$(hostname) $(date -u +%H:%M:%S)"
"$E20F_PY" -u "$E20F_DIR/src/e20f_exec.py" --phase "$E20F_PHASE" --job-tag "$E20F_TAG" --rank "$GR" --nranks "$E20F_NRANKS" \
          --job-start "$E20F_START" --deadline-epoch "$E20F_DEADLINE" > "$E20F_DIR/logs/jobs/E20F_${E20F_PHASE}_${E20F_TAG}_rank${GR}.log" 2>&1
echo "E20F phase=$E20F_PHASE rank=$GR exit=$? $(date -u +%H:%M:%S)"
exit 0
