#!/bin/bash
# E6 smoke (16 fit rows, GPUs 0+1) and E7 validation (16 fit rows per receiver, GPUs 2 and 3), in parallel on one node.
set -uo pipefail
W=$DATA_DIR/P2_R2_GPU_20260919T220941Z
source "$HOME/.config/ClusterB-storage.sh"
export PATH="$PATH:/opt/pbs/bin"
export http_proxy=http://proxy.cluster.invalid:3128 https_proxy=http://proxy.cluster.invalid:3128
export HTTP_PROXY=http://proxy.cluster.invalid:3128 HTTPS_PROXY=http://proxy.cluster.invalid:3128
export CUDA_DEVICE_ORDER=PCI_BUS_ID HF_HUB_OFFLINE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export TMPDIR=$W/tmp; mkdir -p "$TMPDIR" "$W/logs" "$W/e6/smoke" "$W/e7/validation"
export P2R2_W=$W
PY=$DATA_ROOT/software/envs/c2c_official/bin/python
{ echo "NODE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname) PBS_JOBID=${PBS_JOBID:-none}"; nvidia-smi -L; } > "$W/logs/smoke_node.txt" 2>&1
CUDA_VISIBLE_DEVICES=0,1 $PY "$W/src/e6_run.py" --mode smoke --helper-gpu 0 --receiver-gpu 1 \
    --out "$W/e6/smoke/e6_smoke.jsonl" > "$W/logs/e6_smoke.log" 2>&1 &
P1=$!
CUDA_VISIBLE_DEVICES=2 $PY "$W/src/e7_validate.py" large  "$W/e7/validation/E7_VALIDATION_large.json"  > "$W/logs/e7_val_large.log" 2>&1 &
P2=$!
CUDA_VISIBLE_DEVICES=3 $PY "$W/src/e7_validate.py" medium "$W/e7/validation/E7_VALIDATION_medium.json" > "$W/logs/e7_val_medium.log" 2>&1 &
P3=$!
wait $P1; R1=$?
wait $P2; R2=$?
wait $P3; R3=$?
echo "EXIT e6_smoke=$R1 e7_val_large=$R2 e7_val_medium=$R3" >> "$W/logs/smoke_node.txt"
echo "NODE_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$W/logs/smoke_node.txt"
