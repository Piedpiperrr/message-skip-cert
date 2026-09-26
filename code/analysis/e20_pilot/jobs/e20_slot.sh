#!/bin/bash
# One E20 slot = one GPU (CUDA_VISIBLE_DEVICES = local rank). Always exits 0 so one rank never kills the allocation.
set -u
GR="${PALS_RANKID:-${PMI_RANK:-0}}"
LR="${PALS_LOCAL_RANKID:-${PMI_LOCAL_RANK:-0}}"
export CUDA_VISIBLE_DEVICES=$LR
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1
export TMPDIR="/tmp/e20.$GR"; mkdir -p "$TMPDIR"
echo "E20 SLOT job=$E20_JOB rank=$GR local=$LR gpu=$CUDA_VISIBLE_DEVICES host=$(hostname) $(date -u +%H:%M:%S)"
"$E20_PY" -u "$E20_DIR/src/e20_exec.py" --job "$E20_JOB" --rank "$GR" --nranks "$E20_NRANKS" \
          --job-start "$E20_START" --deadline-epoch "$E20_DEADLINE" > "$E20_DIR/logs/jobs/E20P_${E20_JOB}_rank${GR}.log" 2>&1
echo "E20 job=$E20_JOB rank=$GR exit=$? $(date -u +%H:%M:%S)"
exit 0
