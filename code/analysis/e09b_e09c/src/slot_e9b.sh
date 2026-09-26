#!/bin/bash
# One E9B slot = 2 GPUs (helper cuda:0, receiver cuda:1), as the frozen runtimes require.
# ranks 0,1,2 -> large pair thirds of the 744 rows; rank 3 -> medium pair, all 744.
# Validation runs first inside the slot; main runs only if it passed. Always exits 0.
set -u
GR="${PALS_RANKID:-${PMI_RANK:-0}}"
LR="${PALS_LOCAL_RANKID:-${PMI_LOCAL_RANK:-0}}"
case "$LR" in 0) GPUS=0,1 ;; 1) GPUS=2,3 ;; *) echo "unexpected local rank $LR"; exit 0 ;; esac
export CUDA_VISIBLE_DEVICES=$GPUS
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export TMPDIR="/tmp/e9b.$$"; mkdir -p "$TMPDIR"
export P2_DEADLINE_EPOCH="$E9_E9B_DEADLINE" P2_MEDIUM_DEADLINE="$E9_E9B_DEADLINE"
if [ "$GR" -lt 3 ]; then PAIR=large; ACTS='probe,R,T,C,TF'; SH=$GR; NSH=3
else PAIR=medium; ACTS='probe,R,C'; SH=0; NSH=1; fi
echo "E9B SLOT rank=$GR pair=$PAIR gpus=$GPUS shard=$SH/$NSH host=$(hostname)"
D="$E9_DIR/$PAIR"
"$E9_PY" -u "$E9_DIR/src/gpu_preflight2.py" || { echo "E9B rank=$GR skipping: GPUs unusable"; exit 0; }
V="$D/records/VALIDATION_rank${GR}.json"
"$E9_PY" -u "$D/src/e9b_exec.py" --mode validate --actions "$ACTS" --out "$V"
rc=$?
if [ $rc -ne 0 ]; then echo "E9B rank=$GR VALIDATION FAILED rc=$rc -- main not run"; exit 0; fi
"$E9_PY" -u "$D/src/e9b_exec.py" --mode main --actions "$ACTS" --shard "$SH" --nshards "$NSH" \
    --out "$D/records/e9b_${PAIR}_shard${SH}.jsonl" --deadline-epoch "$E9_E9B_DEADLINE"
echo "E9B rank=$GR main exit=$? (reported as 0 so siblings are not killed)"
exit 0
