#!/bin/bash
# Submits the single packed E9B+E9C debug job, only if a queue position is free.
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
JID=$(submit-job  -q debug -l select=2 -l walltime=00:50:00 \
      -l fsreq=<fs> -N E9BC run_e9bc.pbs 2>&1)
rc=$?
echo "submit-job rc=$rc id=$JID"
"$PY" - "$JID" "$PLAN_SHA" "$rc" <<'PY'
import sys,json,datetime,pathlib
S=pathlib.Path('$DATA_DIR/P2_R3_E9BC_20260920T061042Z')
jid,plan_sha,rc=sys.argv[1],sys.argv[2],int(sys.argv[3])
g=lambda f: open(S/f).read().split()[0]
rec=dict(utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
         job_id=jid.strip(),submit_returncode=rc,machine='ClusterA',queue='debug',
         resources='select=2, 8x A100 40GB, walltime=00:50:00, fsreq=<fs>',
         purpose='phase 1 E9B (validation then 744 held-out rows, large+medium); phase 2 E9C helper prefills',
         lane_plan_sha256=plan_sha,
         protocol_freeze_E9B_sha256=g('PROTOCOL_FREEZE_E9B.md.sha256'),
         protocol_amendment_E9B_sha256=g('PROTOCOL_AMENDMENT_E9B.md.sha256'),
         protocol_freeze_E9C_sha256=g('PROTOCOL_FREEZE_E9C.md.sha256'))
p=S/'jobs/SUBMISSION.json'
hist=json.loads(p.read_text()) if p.exists() else []
hist.append(rec);p.write_text(json.dumps(hist,indent=2)+'\n')
print(json.dumps(rec,indent=1))
PY
