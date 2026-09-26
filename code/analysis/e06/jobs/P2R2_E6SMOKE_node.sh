#!/bin/bash
set -uo pipefail
W=$DATA_DIR/P2_R2_GPU_20260919T220941Z
source "$HOME/.config/ClusterB-storage.sh"
export PATH="$PATH:/opt/pbs/bin"
export http_proxy=http://proxy.cluster.invalid:3128 https_proxy=http://proxy.cluster.invalid:3128
export HTTP_PROXY=http://proxy.cluster.invalid:3128 HTTPS_PROXY=http://proxy.cluster.invalid:3128
export CUDA_DEVICE_ORDER=PCI_BUS_ID HF_HUB_OFFLINE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export TMPDIR=$W/tmp; mkdir -p "$TMPDIR" "$W/logs" "$W/e6/smoke"
PY=$DATA_ROOT/software/envs/c2c_official/bin/python
{ echo "E6SMOKE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname) PBS_JOBID=${PBS_JOBID:-none}"; nvidia-smi -L; } > "$W/logs/e6_smoke_node.txt" 2>&1
CUDA_VISIBLE_DEVICES=0,1 $PY "$W/src/e6_run.py" --mode smoke --helper-gpu 0 --receiver-gpu 1 \
    --out "$W/e6/smoke/e6_smoke.jsonl" > "$W/logs/e6_smoke.log" 2>&1
echo "EXIT=$? END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$W/logs/e6_smoke_node.txt"
