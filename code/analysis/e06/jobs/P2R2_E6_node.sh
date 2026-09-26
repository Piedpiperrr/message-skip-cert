#!/bin/bash
# E6 main: two shards per node, one per GPU pair (helper cuda:0, receiver cuda:1 inside each pair).
set -uo pipefail
W=$DATA_DIR/P2_R2_GPU_20260919T220941Z
RANK=${PALS_RANKID:-${PMI_RANK:-0}}
source "$HOME/.config/ClusterB-storage.sh"
export PATH="$PATH:/opt/pbs/bin"
export http_proxy=http://proxy.cluster.invalid:3128 https_proxy=http://proxy.cluster.invalid:3128
export HTTP_PROXY=http://proxy.cluster.invalid:3128 HTTPS_PROXY=http://proxy.cluster.invalid:3128
export CUDA_DEVICE_ORDER=PCI_BUS_ID HF_HUB_OFFLINE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export TMPDIR=$W/tmp; mkdir -p "$TMPDIR" "$W/logs" "$W/e6/main"
PY=$DATA_ROOT/software/envs/c2c_official/bin/python
A=$((RANK*2)); B=$((RANK*2+1))
{ echo "E6_NODE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname) rank=$RANK shards=$A,$B PBS_JOBID=${PBS_JOBID:-none}"; nvidia-smi -L; } > "$W/logs/e6_node_rank$RANK.txt" 2>&1
CUDA_VISIBLE_DEVICES=0,1 $PY "$W/src/e6_run.py" --mode main --shard $A --nshards 4 --helper-gpu 0 --receiver-gpu 1 \
    --out "$W/e6/main/e6_shard$A.jsonl" > "$W/logs/e6_shard$A.log" 2>&1 &
P1=$!
CUDA_VISIBLE_DEVICES=2,3 $PY "$W/src/e6_run.py" --mode main --shard $B --nshards 4 --helper-gpu 0 --receiver-gpu 1 \
    --out "$W/e6/main/e6_shard$B.jsonl" > "$W/logs/e6_shard$B.log" 2>&1 &
P2=$!
wait $P1; R1=$?
wait $P2; R2=$?
echo "EXIT shard$A=$R1 shard$B=$R2 END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$W/logs/e6_node_rank$RANK.txt"
