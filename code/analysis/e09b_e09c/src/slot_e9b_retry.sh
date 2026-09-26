#!/bin/bash
# Retry of the one E9B slot lost to a bookkeeping filename race: large pair, shard 1 of 3.
# A single rank per node, so the frozen adapter's evidence filename cannot collide.
set -u
GR="${PALS_RANKID:-${PMI_RANK:-0}}"
export CUDA_VISIBLE_DEVICES=0,1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export TMPDIR="/tmp/e9br.$$"; mkdir -p "$TMPDIR"
export P2_DEADLINE_EPOCH="$E9_E9B_DEADLINE"
echo "E9B RETRY SLOT rank=$GR pair=large gpus=0,1 shard=1/3 host=$(hostname)"
D="$E9_DIR/large"
"$E9_PY" -u "$E9_DIR/src/gpu_preflight2.py" || { echo "retry skipping: GPUs unusable"; exit 0; }
"$E9_PY" -u "$D/src/e9b_exec.py" --mode validate --actions 'probe,R,T,C,TF' --out "$D/records/VALIDATION_rank1.json"
rc=$?
if [ $rc -ne 0 ]; then echo "E9B retry VALIDATION FAILED rc=$rc -- main not run"; exit 0; fi
"$E9_PY" -u "$D/src/e9b_exec.py" --mode main --actions 'probe,R,T,C,TF' --shard 1 --nshards 3 \
    --out "$D/records/e9b_large_shard1.jsonl" --deadline-epoch "$E9_E9B_DEADLINE"
echo "E9B retry main exit=$?"
exit 0
