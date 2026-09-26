#!/bin/bash
# One E10 slot = one GPU holding both the helper (Qwen2.5-7B) and the receiver (Qwen3-8B).
# A single Python process per rank runs preflight -> smoke -> cross-rank gate -> main, so the
# 31.6 GB of weights are loaded once.  Always exits 0 so one rank never kills the allocation.
set -u
GR="${PALS_RANKID:-${PMI_RANK:-0}}"
LR="${PALS_LOCAL_RANKID:-${PMI_LOCAL_RANK:-0}}"
export CUDA_VISIBLE_DEVICES=$LR
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TMPDIR="/tmp/e10.$GR"; mkdir -p "$TMPDIR"
echo "E10 SLOT rank=$GR local=$LR gpu=$CUDA_VISIBLE_DEVICES host=$(hostname) $(date -u +%H:%M:%S)"
"$E10_PY" -u "$E10_DIR/src/e10_exec.py" --rank "$GR" --nranks "$E10_NRANKS" \
          --phase all --deadline-epoch "$E10_DEADLINE"
echo "E10 rank=$GR exit=$? $(date -u +%H:%M:%S)"
exit 0
