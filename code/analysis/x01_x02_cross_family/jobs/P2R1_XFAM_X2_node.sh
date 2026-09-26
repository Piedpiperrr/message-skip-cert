#!/bin/bash
# X2 full run: node shell (one per node via mpiexec); 4 single-GPU chains (receiver OLMo-2-7B); records only, gold never read.
set -uo pipefail
X=$DATA_DIR/P2_R1_XFAM_20260919T095058Z
source "$HOME/.config/ClusterB-storage.sh"
PY="$DATA_ROOT/software/envs/c2c_official/bin/python"
export XFAM_DEADLINE_EPOCH="$1" PBS_JOBID="$2"
RANK="${PALS_RANKID:-${PMI_RANK:-x}}"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false CUDA_DEVICE_ORDER=PCI_BUS_ID
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export TMPDIR="$X/cache/tmp" TMP="$X/cache/tmp" TEMP="$X/cache/tmp"
L="$X/logs/jobs/P2R1_XFAM_X2"; mkdir -p "$L" "$X/results/runs"
{ echo "NODE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) rank=$RANK host=$(hostname)"; nvidia-smi -L; } > "$L/node${RANK}.txt" 2>&1
cd "$X/src" || exit 3
PIDS=()
for g in 0 1 2 3; do
  c=$(printf '%02d' $((RANK * 4 + g)))
  [ -f "$X/records/work/run/chain_$c.jsonl" ] || continue
  ( export CUDA_VISIBLE_DEVICES=$g
    "$PY" run_x2.py --mode run --receiver olmo2_7b --rows "$X/records/work/run/chain_$c.jsonl" --out "$X/results/runs/chain_$c.jsonl"; echo "EXIT chain_$c $?" ) > "$L/chain_$c.log" 2>&1 &
  PIDS+=($!)
done
wait "${PIDS[@]}"
echo "NODE_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$L/node${RANK}.txt"
