#!/bin/bash
set -uo pipefail
X1=$DATA_DIR/P2_R1_XFAM_20260919T095058Z/x1
source "$HOME/.config/ClusterB-storage.sh"
export PY="$DATA_ROOT/software/envs/c2c_official/bin/python" XFAM_DEADLINE_EPOCH="$1" PBS_JOBID="$2" OUT="$X1/results/runs"
RANK="${PALS_RANKID:-${PMI_RANK:-x}}"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false CUDA_DEVICE_ORDER=PCI_BUS_ID
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export TMPDIR="$X1/../cache/tmp" TMP="$X1/../cache/tmp" TEMP="$X1/../cache/tmp"
L="$X1/logs/jobs/P2R1_XFAM_X1RUN"; mkdir -p "$L" "$OUT"
{ echo "NODE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) rank=$RANK host=$(hostname)"; nvidia-smi -L; } > "$L/node${RANK}.txt" 2>&1
cd "$X1/src" || exit 3
PIDS=()
for g in 0 1 2 3; do
  k=$(printf '%02d' $((RANK * 4 + g)))
  [ -f "$DATA_DIR/P2_R1_XFAM_20260919T095058Z/x1/jobs/P2R1_XFAM_X1RUN/chain_$k.sh" ] || continue
  ( export G=$g; bash "$DATA_DIR/P2_R1_XFAM_20260919T095058Z/x1/jobs/P2R1_XFAM_X1RUN/chain_$k.sh" ) > "$L/chain_$k.log" 2>&1 &
  PIDS+=($!)
done
wait "${PIDS[@]}"
echo "NODE_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$L/node${RANK}.txt"
