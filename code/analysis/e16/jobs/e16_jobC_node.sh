#!/bin/bash
# E16 Job C node shell. Rank 0: 16-row check, then (only on PASS) the E16-4 replay (replay_llama/run_e2e.pbs -> pbs_entry -> supervise -> validate_sources, execute).
set -uo pipefail
X=$DATA_DIR/P2_R7_E16_20260921T184114Z
export PBS_JOBID="$1"
RANK="${PALS_RANKID:-${PMI_RANK:-x}}"
[ "$RANK" = "0" ] || { echo "rank $RANK idle $(hostname)" > "$X/logs/jobs/jobC_rank${RANK}.txt"; exit 0; }
source "$HOME/.config/ClusterB-storage.sh"
export PATH="$PATH:/opt/pbs/bin"
export http_proxy=http://proxy.cluster.invalid:3128 https_proxy=http://proxy.cluster.invalid:3128 HTTP_PROXY=http://proxy.cluster.invalid:3128 HTTPS_PROXY=http://proxy.cluster.invalid:3128
export CUDA_VISIBLE_DEVICES=0,1 CUDA_DEVICE_ORDER=PCI_BUS_ID
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
unset PYTHONPATH
L="$X/logs/jobs/jobC"; mkdir -p "$L" "$X/results/e16_4"
{ echo "NODE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname)"; nvidia-smi -L; nvidia-smi topo -m; } > "$L/node0.txt" 2>&1
cd "$X/src" || exit 3
P2_DEADLINE_EPOCH=$(( $(date +%s) + 900 )) "$DATA_ROOT/software/envs/c2c_official/bin/python" check_e164.py > "$L/check_e164.log" 2>&1
rc=$?; echo "CHECK_EXIT=$rc $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$L/node0.txt"
if [ "$rc" -eq 0 ]; then
  export R1E3_REPLAY_START_EPOCH=$(date +%s.%N)
  echo "REPLAY_START utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) epoch=$R1E3_REPLAY_START_EPOCH" >> "$L/node0.txt"
  bash "$X/replay_llama/run_e2e.pbs"; echo "REPLAY_END exit=$? utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$L/node0.txt"
else
  echo "REPLAY_NOT_RUN (16-row check did not pass)" >> "$L/node0.txt"
fi
