#!/bin/bash
# Submits the single E9c debug job, but only if a queue position is free.
# Regenerates the lane plan first so small/medium MMLU-Pro are included iff every E8 lane is complete.
set -u
export PATH="$PATH:/opt/pbs/bin"
S=$DATA_DIR/P2_R3_E9BC_20260920T061042Z
PY=$DATA_DIR/software/envs/c2c_official/bin/python
live=$(job-status -u "$USER" 2>/dev/null | grep -cE '^[0-9]+\.ClusterA')
echo "live jobs = $live"
if [ "${live:-2}" -ge 2 ]; then echo "BOTH POSITIONS TAKEN -- not submitting"; exit 2; fi
OPENBLAS_NUM_THREADS=1 "$PY" "$S/src/e9c_plan.py" || exit 1
PLAN_SHA=$(sha256sum "$S/jobs/LANE_PLAN.json" | awk '{print $1}')
cd "$S" || exit 1
JID=$(submit-job  -q debug -l select=1 -l walltime=00:50:00 \
      -l fsreq=<fs> -N E9C_MAIN run_e9c.pbs 2>&1)
rc=$?
echo "submit-job rc=$rc id=$JID"
"$PY" - "$JID" "$PLAN_SHA" "$rc" <<'PY'
import sys,json,datetime,subprocess,pathlib
S=pathlib.Path('$DATA_DIR/P2_R3_E9BC_20260920T061042Z')
jid,plan_sha,rc=sys.argv[1],sys.argv[2],int(sys.argv[3])
rec=dict(utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
         job_id=jid.strip(),submit_returncode=rc,machine='ClusterA',queue='debug',
         resources='select=1, 4x A100 40GB, walltime=00:50:00, fsreq=<fs>',
         purpose='E9c: validation (16 fit rows per pair) + helper prefills for all fit/cal/dev rows',
         lane_plan_sha256=plan_sha,
         protocol_freeze_E9C_sha256=open(S/'PROTOCOL_FREEZE_E9C.md.sha256').read().split()[0],
         E9B='not executed; gate failed')
p=S/'jobs/SUBMISSION.json'
hist=json.loads(p.read_text()) if p.exists() else []
hist.append(rec); p.write_text(json.dumps(hist,indent=2)+'\n')
print(json.dumps(rec,indent=1))
PY
