#!/bin/bash
# E16 Job B node shell (E16-3 prefills; plan notes/JOBB_PLAN.json). Records only; gold never read.
set -uo pipefail
X=$DATA_DIR/P2_R7_E16_20260921T184114Z
source "$HOME/.config/ClusterB-storage.sh"
PY="$DATA_ROOT/software/envs/c2c_official/bin/python"
export XFAM_DEADLINE_EPOCH="$1" PBS_JOBID="$2"
RANK="${PALS_RANKID:-${PMI_RANK:-x}}"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false CUDA_DEVICE_ORDER=PCI_BUS_ID
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export http_proxy=http://proxy.cluster.invalid:3128 https_proxy=http://proxy.cluster.invalid:3128 HTTP_PROXY=http://proxy.cluster.invalid:3128 HTTPS_PROXY=http://proxy.cluster.invalid:3128
unset PYTHONPATH
export TMPDIR="$X/cache/tmp" TMP="$X/cache/tmp" TEMP="$X/cache/tmp"
L="$X/logs/jobs/jobB"; mkdir -p "$L" "$X/results/e163"
{ echo "NODE_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) rank=$RANK host=$(hostname)"; nvidia-smi -L; } > "$L/node${RANK}.txt" 2>&1
cd "$X/src" || exit 3
PIDS=()
  [ "$RANK" = "0" ] && ( export CUDA_VISIBLE_DEVICES=0; "$PY" e16_probe.py --receiver qwen3_8b --dtype fp32 --mode run --rows $DATA_DIR/P2_R7_E16_20260921T184114Z/records/work/jobB/q8b_fp32_s0.jsonl --out "$X/results/e163/qwen3_8b_fp32_q8b_fp32_s0.jsonl"; echo "EXIT qwen3_8b fp32 $?" ) > "$L/node0_gpu0.log" 2>&1 &
  [ "$RANK" = "0" ] && PIDS+=($!)
  [ "$RANK" = "0" ] && ( export CUDA_VISIBLE_DEVICES=1; "$PY" e16_probe.py --receiver qwen3_8b --dtype fp32 --mode run --rows $DATA_DIR/P2_R7_E16_20260921T184114Z/records/work/jobB/q8b_fp32_s1.jsonl --out "$X/results/e163/qwen3_8b_fp32_q8b_fp32_s1.jsonl"; echo "EXIT qwen3_8b fp32 $?" ) > "$L/node0_gpu1.log" 2>&1 &
  [ "$RANK" = "0" ] && PIDS+=($!)
  [ "$RANK" = "0" ] && ( export CUDA_VISIBLE_DEVICES=2; "$PY" e16_probe.py --receiver qwen3_8b --dtype fp32 --mode run --rows $DATA_DIR/P2_R7_E16_20260921T184114Z/records/work/jobB/q8b_fp32_s2.jsonl --out "$X/results/e163/qwen3_8b_fp32_q8b_fp32_s2.jsonl"; echo "EXIT qwen3_8b fp32 $?" ) > "$L/node0_gpu2.log" 2>&1 &
  [ "$RANK" = "0" ] && PIDS+=($!)
  [ "$RANK" = "0" ] && ( export CUDA_VISIBLE_DEVICES=3; "$PY" e16_probe.py --receiver qwen3_8b --dtype fp32 --mode run --rows $DATA_DIR/P2_R7_E16_20260921T184114Z/records/work/jobB/q8b_fp32_s3.jsonl --out "$X/results/e163/qwen3_8b_fp32_q8b_fp32_s3.jsonl"; echo "EXIT qwen3_8b fp32 $?" ) > "$L/node0_gpu3.log" 2>&1 &
  [ "$RANK" = "0" ] && PIDS+=($!)
  [ "$RANK" = "1" ] && ( export CUDA_VISIBLE_DEVICES=0; "$PY" e16_probe.py --receiver qwen3_8b --dtype fp32 --mode run --rows $DATA_DIR/P2_R7_E16_20260921T184114Z/records/work/jobB/q8b_fp32_s4.jsonl --out "$X/results/e163/qwen3_8b_fp32_q8b_fp32_s4.jsonl"; echo "EXIT qwen3_8b fp32 $?" ) > "$L/node1_gpu0.log" 2>&1 &
  [ "$RANK" = "1" ] && PIDS+=($!)
  [ "$RANK" = "1" ] && ( export CUDA_VISIBLE_DEVICES=1; "$PY" e16_probe.py --receiver qwen3_8b --dtype bf16 --mode run --rows $DATA_DIR/P2_R7_E16_20260921T184114Z/records/work/jobB/q8b_bf16.jsonl --out "$X/results/e163/qwen3_8b_bf16_q8b_bf16.jsonl"; echo "EXIT qwen3_8b bf16 $?"; "$PY" e16_probe.py --receiver qwen3_1_7b --dtype bf16 --mode run --rows $DATA_DIR/P2_R7_E16_20260921T184114Z/records/work/jobB/q17b_bf16.jsonl --out "$X/results/e163/qwen3_1_7b_bf16_q17b_bf16.jsonl"; echo "EXIT qwen3_1_7b bf16 $?" ) > "$L/node1_gpu1.log" 2>&1 &
  [ "$RANK" = "1" ] && PIDS+=($!)
  [ "$RANK" = "1" ] && ( export CUDA_VISIBLE_DEVICES=2; "$PY" e16_probe.py --receiver qwen3_1_7b --dtype fp32 --mode run --rows $DATA_DIR/P2_R7_E16_20260921T184114Z/records/work/jobB/q17b_fp32.jsonl --out "$X/results/e163/qwen3_1_7b_fp32_q17b_fp32.jsonl"; echo "EXIT qwen3_1_7b fp32 $?" ) > "$L/node1_gpu2.log" 2>&1 &
  [ "$RANK" = "1" ] && PIDS+=($!)
  [ "$RANK" = "1" ] && ( export CUDA_VISIBLE_DEVICES=3; "$PY" e16_probe.py --receiver qwen3_0_6b --dtype bf16 --mode run --rows $DATA_DIR/P2_R7_E16_20260921T184114Z/records/work/jobB/q06b_bf16.jsonl --out "$X/results/e163/qwen3_0_6b_bf16_q06b_bf16.jsonl"; echo "EXIT qwen3_0_6b bf16 $?"; "$PY" e16_probe.py --receiver qwen3_0_6b --dtype fp32 --mode run --rows $DATA_DIR/P2_R7_E16_20260921T184114Z/records/work/jobB/q06b_fp32.jsonl --out "$X/results/e163/qwen3_0_6b_fp32_q06b_fp32.jsonl"; echo "EXIT qwen3_0_6b fp32 $?" ) > "$L/node1_gpu3.log" 2>&1 &
  [ "$RANK" = "1" ] && PIDS+=($!)
wait "${PIDS[@]}"
echo "NODE_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$L/node${RANK}.txt"
