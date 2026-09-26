#!/bin/bash
# E3 ClusterA node run for P2_R1_E3POL_REPEAT2_20260919T075315Z: three original E2E replays (large, medium, MMLU-Pro panels) one after another
# Started by the 2-node job script through mpiexec (one shell per node). Replays run one after another on THIS node,
# GPUs 0-1 only (helper cuda:0, receiver+fuser cuda:1); GPUs 2-3 stay idle and nothing else runs on the node. Records only.
set -uo pipefail
NEW=$DATA_DIR/P2_R1_E3POL_REPEAT2_20260919T075315Z
source "$HOME/.config/ClusterB-storage.sh"
export PATH="$PATH:/opt/pbs/bin"
export http_proxy=http://proxy.cluster.invalid:3128 https_proxy=http://proxy.cluster.invalid:3128
export HTTP_PROXY=http://proxy.cluster.invalid:3128 HTTPS_PROXY=http://proxy.cluster.invalid:3128
export CUDA_VISIBLE_DEVICES=0,1 CUDA_DEVICE_ORDER=PCI_BUS_ID
LOG="$NEW/logs"; mkdir -p "$LOG"
{
  echo "NODE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname) PBS_JOBID=${PBS_JOBID:-none} rank=${PALS_RANKID:-${PMI_RANK:-?}}"
  echo "## GPU model, driver, CUDA"
  nvidia-smi -L
  nvidia-smi --query-gpu=index,name,uuid,pci.bus_id,driver_version,vbios_version,memory.total,memory.used,utilization.gpu,clocks.max.sm,power.limit,persistence_mode,mig.mode.current --format=csv
  nvidia-smi | head -4
  grep -E "^(__version__|cuda|git_version)" "$DATA_ROOT/software/envs/c2c_official/lib/python3.10/site-packages/torch/version.py"
  echo "## GPU topology (nvidia-smi topo -m)"
  nvidia-smi topo -m
  echo "## CPU"
  lscpu
  echo "nproc=$(nproc) affinity=$(taskset -pc $$ 2>&1)"
  echo "## memory"; free -g
  echo "## scheduler"; job-status -f "$PBS_JOBID" | grep -E 'queue =|Resource_List|exec_vnode|exec_host'
  echo "## cgroup of this shell"; cat /proc/self/cgroup
  echo "## tools"; for t in job-status myquota rg grep; do echo "$t=$(command -v $t || echo MISSING)"; done
} > "$LOG/node_hardware.txt" 2>&1
for item in large:run_e2e.pbs medium:run_medium_stage2.pbs mmlu:run_mmlu_stage2.pbs; do
  stage=${item%%:*}; script=${item#*:}
  export R1E3_REPLAY_START_EPOCH=$(date +%s.%N)
  echo "REPLAY_START $stage utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) epoch=$R1E3_REPLAY_START_EPOCH host=$(hostname)" >> "$LOG/replays.log"
  bash "$NEW/$stage/$script"; rc=$?
  echo "REPLAY_END $stage exit=$rc utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG/replays.log"
  nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv >> "$LOG/replays.log" 2>&1
done
echo "NODE_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG/node_hardware.txt"
