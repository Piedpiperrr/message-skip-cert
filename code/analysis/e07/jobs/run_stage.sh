#!/bin/bash
# run_stage.sh <stage> <script> <log-name>   -- one stage, one python process, GPUs already selected.
set -uo pipefail
source $DATA_DIR/P2_R2_E7_20260919T231531Z/jobs/stage_env.sh
stage=$1; script=$2; logname=$3
export TMPDIR="$W/$stage/tmp"; export TMP="$TMPDIR" TEMP="$TMPDIR"
export P2_RUN="$W/$stage/run_logs"
mkdir -p "$TMPDIR" "$P2_RUN" "$W/logs"
# stage-local deadline guards: each stage's own stop_check() reads its own variable
DEADLINE=$(python3 -c "import time,os;print(time.time()+float(os.environ.get('STAGE_BUDGET','2400')))")
export P2_DEADLINE_EPOCH=$DEADLINE P2_MEDIUM_DEADLINE=$DEADLINE MMLU_DEADLINE_EPOCH=$DEADLINE
echo "STAGE_START $stage $script utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname) CUDA=$CUDA_VISIBLE_DEVICES" >> "$W/logs/$logname.log"
cd "$W/$stage" || exit 93
nice -n 10 "$PY" -u "src/$script" "${@:4}" >> "$W/logs/$logname.log" 2>&1
rc=$?
echo "STAGE_END $stage $script exit=$rc utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$W/logs/$logname.log"
exit $rc
