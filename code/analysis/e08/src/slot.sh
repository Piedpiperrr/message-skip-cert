#!/bin/bash
# One E8 slot = one GPU pair (helper on the first visible GPU, receiver+fuser on the second).
# ClusterA node has 4 A100; local rank 0 -> GPUs 0,1 and local rank 1 -> GPUs 2,3.
set -u
LR="${PALS_LOCAL_RANKID:-${PMI_LOCAL_RANK:-0}}"
GR="${PALS_RANKID:-${PMI_RANK:-0}}"
case "$LR" in
  0) export CUDA_VISIBLE_DEVICES=0,1 ;;
  1) export CUDA_VISIBLE_DEVICES=2,3 ;;
  *) echo "unexpected local rank $LR" >&2; exit 2 ;;
esac
export E8_SLOT="r${GR}"
# even global rank -> small, odd -> medium (two slots per node, both pairs on every node)
if [ $((GR % 2)) -eq 0 ]; then export E8_PAIR=small; else export E8_PAIR=medium; fi
if [ -n "${E8_FORCE_PAIR:-}" ]; then export E8_PAIR="$E8_FORCE_PAIR"; fi
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 MKL_NUM_THREADS=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="${E8_TMPDIR:-/tmp/e8_${PBS_JOBID%%.*}_${GR}}"
mkdir -p "$TMPDIR"
cd "$E8_DIR/src"
echo "SLOT start rank=$GR local=$LR pair=$E8_PAIR gpus=$CUDA_VISIBLE_DEVICES host=$(hostname)"
exec "$E8_PY" -u "$1"
