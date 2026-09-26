#!/bin/bash
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# [scheduler directive removed for anonymity]
# E18: teacher-forced pre-answer score over the stored E10 GSM8K receiver-only outputs (ClusterA debug, 1 node, 4 A100 40GB).
#   One receiver (Qwen3-8B bf16) per GPU, one process per GPU started once:
#   preflight (37 fit rows) -> cross-rank gate -> production (1,800 R rows, sharded j % 4) -> merge + hash.
#   No gold is read anywhere in this job.
# Submit:
#   submit-job  -q debug -l select=1 -l walltime=00:40:00 -l fsreq=<fs> job.sh
set -uo pipefail
export E18_DIR=$DATA_DIR/P2_R8_E18_20260922T003446Z
source "$HOME/.config/ClusterB-storage.sh"
export PATH="$PATH:/opt/pbs/bin"
export http_proxy=http://proxy.cluster.invalid:3128 https_proxy=http://proxy.cluster.invalid:3128
export HTTP_PROXY=http://proxy.cluster.invalid:3128 HTTPS_PROXY=http://proxy.cluster.invalid:3128
export CUDA_DEVICE_ORDER=PCI_BUS_ID OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
PY="$DATA_ROOT/software/envs/c2c_official/bin/python"
TAG="${PBS_JOBID%%.*}"
LOG="$E18_DIR/logs"; mkdir -p "$LOG" "$E18_DIR/records"
{
  echo "JOB_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname) PBS_JOBID=${PBS_JOBID:-none}"
  echo "PREREG=$(awk 'NR==1{print $1}' "$E18_DIR/PREREG_E18.sha256")"
  echo "SCORE_PY=$(sha256sum "$E18_DIR/src/e18_score.py" | awk '{print $1}')"
  echo "MERGE_PY=$(sha256sum "$E18_DIR/src/e18_merge.py" | awk '{print $1}')"
  nvidia-smi -L
  job-status -f "$PBS_JOBID" | grep -E 'queue =|Resource_List|exec_vnode' || true
} > "$LOG/e18_${TAG}_env.txt" 2>&1

for R in 0 1 2 3; do
  ( export CUDA_VISIBLE_DEVICES=$R TMPDIR=/tmp/e18.$R; mkdir -p "$TMPDIR"
    "$PY" -u "$E18_DIR/src/e18_score.py" --rank $R --nranks 4 > "$LOG/e18_${TAG}_rank$R.log" 2>&1
    echo "rank=$R exit=$? $(date -u +%H:%M:%S)" >> "$LOG/e18_${TAG}_env.txt" ) &
done
wait
if [ -f "$E18_DIR/records/PREFLIGHT.json" ] && [ "$(ls "$E18_DIR"/records/scores_rank*.status.json 2>/dev/null | wc -l)" -eq 4 ]; then
  "$PY" -u "$E18_DIR/src/e18_merge.py" --records "$E18_DIR/records" --dest "$E18_DIR" >> "$LOG/e18_${TAG}_env.txt" 2>&1
fi
echo "JOB_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG/e18_${TAG}_env.txt"
