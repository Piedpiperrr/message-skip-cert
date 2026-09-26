#!/bin/bash
# E16 Job A node shell (one per node via mpiexec). Records only; gold never read.
set -uo pipefail
X=$DATA_DIR/P2_R7_E16_20260921T184114Z
source "$HOME/.config/ClusterB-storage.sh"
PY="$DATA_ROOT/software/envs/c2c_official/bin/python"
DEADLINE="$1"; export XFAM_DEADLINE_EPOCH="$1" P2_MEDIUM_DEADLINE="$1" PBS_JOBID="$2"
RANK="${PALS_RANKID:-${PMI_RANK:-x}}"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false CUDA_DEVICE_ORDER=PCI_BUS_ID
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export http_proxy=http://proxy.cluster.invalid:3128 https_proxy=http://proxy.cluster.invalid:3128 HTTP_PROXY=http://proxy.cluster.invalid:3128 HTTPS_PROXY=http://proxy.cluster.invalid:3128
unset PYTHONPATH
export TMPDIR="$X/cache/tmp" TMP="$X/cache/tmp" TEMP="$X/cache/tmp"
L="$X/logs/jobs/jobA"; M="$X/results/markers"; mkdir -p "$L" "$M" "$X/results/verification" "$X/results/e16_1" "$X/results/e16_2" "$X/results/e16_5" "$X/results/v4"
{ echo "NODE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) rank=$RANK host=$(hostname)"; nvidia-smi -L; } > "$L/node${RANK}.txt" 2>&1
cd "$X/src" || exit 3
V="$X/results/verification"
waitgates() { for g in "$@"; do while [ ! -f "$M/$g" ]; do sleep 10; [ "$(date +%s)" -gt "$DEADLINE" ] && return 9; done; [ "$(cat "$M/$g")" = "0" ] || return 1; done; return 0; }
PIDS=()
if [ "$RANK" = "0" ]; then
  ( export CUDA_VISIBLE_DEVICES=0
    "$PY" run_e16.py --mode smoke --receiver llama31_8b --rows ../records/work/v1_llama_x3rows.jsonl --out "$V/v1_llama.jsonl" && "$PY" check_v.py v1 "$V/v1_llama.jsonl" V1
    echo $? > "$M/v1.gate"
    waitgates v1.gate v5llama.gate && "$PY" run_e16.py --mode run --receiver llama31_8b --rows ../records/work/e16_1_shard0.jsonl --out "$X/results/e16_1/shard0.jsonl"
    echo "EXIT e16_1_shard0 $?" ) > "$L/gpu0_e16_1.log" 2>&1 &
  PIDS+=($!)
  ( export CUDA_VISIBLE_DEVICES=1
    "$PY" run_e16.py --mode smoke --receiver llama31_8b --rows ../records/work/v5_llama_smoke.jsonl --out "$V/v5_llama_smoke.jsonl" && "$PY" check_v.py smoke "$V/v5_llama_smoke.jsonl" V5_llama
    echo $? > "$M/v5llama.gate"
    waitgates v1.gate v5llama.gate && "$PY" run_e16.py --mode run --receiver llama31_8b --rows ../records/work/e16_1_shard1.jsonl --out "$X/results/e16_1/shard1.jsonl"
    echo "EXIT e16_1_shard1 $?" ) > "$L/gpu1_e16_1.log" 2>&1 &
  PIDS+=($!)
  ( export CUDA_VISIBLE_DEVICES=2,3
    "$PY" e16_medium.py --v2 ../records/work/v2_medium_arcfit.jsonl --smoke ../records/work/v5_medium_smoke.jsonl --rows ../records/work/e16_2_arc_test.jsonl --outdir "$X/results/e16_2"
    echo "EXIT e16_2 $?" ) > "$L/gpu23_e16_2.log" 2>&1 &
  PIDS+=($!)
else
  ( export CUDA_VISIBLE_DEVICES=0
    "$PY" run_e16.py --mode smoke --receiver qwen3_1_7b --rows ../records/work/v3a_medium_own_messages.jsonl --out "$V/v3a_qwen3_1_7b.jsonl" && "$PY" check_v.py v3a "$V/v3a_qwen3_1_7b.jsonl" V3a
    echo $? > "$M/v3a.gate"
    waitgates v3a.gate v3b.gate && "$PY" run_e16.py --mode run --receiver qwen3_1_7b --text-only --rows ../records/work/e16_5_shard0.jsonl --out "$X/results/e16_5/shard0.jsonl"
    echo "EXIT e16_5_shard0 $?" ) > "$L/gpu0_e16_5.log" 2>&1 &
  PIDS+=($!)
  ( export CUDA_VISIBLE_DEVICES=1
    "$PY" run_e16.py --mode smoke --receiver qwen3_1_7b --rows ../records/work/v3b_strong_smoke.jsonl --out "$V/v3b_strong_smoke.jsonl" && "$PY" check_v.py smoke "$V/v3b_strong_smoke.jsonl" V3b
    echo $? > "$M/v3b.gate"
    waitgates v3a.gate v3b.gate && "$PY" run_e16.py --mode run --receiver qwen3_1_7b --text-only --rows ../records/work/e16_5_shard1.jsonl --out "$X/results/e16_5/shard1.jsonl"
    echo "EXIT e16_5_shard1 $?" ) > "$L/gpu1_e16_5.log" 2>&1 &
  PIDS+=($!)
  ( export CUDA_VISIBLE_DEVICES=2
    "$PY" e16_probe.py --receiver qwen3_8b --dtype bf16 --mode v4 --rows ../records/work/v4_qwen3_8b_all.jsonl --out "$X/results/v4/v4_qwen3_8b.jsonl"; echo "EXIT v4_qwen3_8b $?" ) > "$L/gpu2_v4.log" 2>&1 &
  PIDS+=($!)
  ( export CUDA_VISIBLE_DEVICES=3
    "$PY" e16_probe.py --receiver qwen3_0_6b --dtype bf16 --mode v4 --rows ../records/work/v4_qwen3_0_6b_all.jsonl --out "$X/results/v4/v4_qwen3_0_6b.jsonl"; echo "EXIT v4_qwen3_0_6b $?"
    "$PY" e16_probe.py --receiver qwen3_1_7b --dtype bf16 --mode v4 --rows ../records/work/v4_qwen3_1_7b_all.jsonl --out "$X/results/v4/v4_qwen3_1_7b.jsonl"; echo "EXIT v4_qwen3_1_7b $?" ) > "$L/gpu3_v4.log" 2>&1 &
  PIDS+=($!)
fi
wait "${PIDS[@]}"
echo "NODE_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$L/node${RANK}.txt"
