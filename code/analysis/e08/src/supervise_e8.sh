#!/bin/bash
# Keeps one E8 main job queued behind the running one until every lane is complete.
# Uses the guarded launcher (run_main_guarded.pbs) after three jobs were lost to a node whose
# GPUs were held by a foreign process. Stops on: all lanes complete, the research deadline,
# the submission cap, or two consecutive submissions that collected nothing.
set -u
E8=$DATA_DIR/P2_R2_E8_20260920T012544Z
echo $$ > $E8/logs/supervisor.pid
MAXJOBS=${MAXJOBS:-6}
DEADLINE=$(date -u -d '2026-09-22T01:00:00Z' +%s)
LOG=$E8/logs/supervisor.log
rows() { cat $E8/shards/*/lane_*/probes/*.jsonl 2>/dev/null | wc -l; }
n=0; barren=0; lastrows=$(rows)
while :; do
  done_lanes=$(ls $E8/shards/*/lane_*/LANE_COMPLETE.json 2>/dev/null | wc -l)
  if [ "$done_lanes" -ge 32 ]; then echo "$(date -u +%FT%TZ) ALL_LANES_COMPLETE" >> $LOG; break; fi
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then echo "$(date -u +%FT%TZ) DEADLINE_REACHED lanes=$done_lanes" >> $LOG; break; fi
  if [ "$n" -ge "$MAXJOBS" ]; then echo "$(date -u +%FT%TZ) JOB_CAP_REACHED lanes=$done_lanes" >> $LOG; break; fi
  if [ "$barren" -ge 2 ]; then echo "$(date -u +%FT%TZ) STOPPED_TWO_BARREN_JOBS lanes=$done_lanes rows=$(rows)" >> $LOG; break; fi
  live=$(job-status -u "$USER" 2>/dev/null | grep -cE 'E8_MAIN')
  if [ "${live:-0}" -lt 2 ]; then
    now=$(rows)
    if [ "$n" -gt 0 ]; then
      if [ "$now" -le "$lastrows" ]; then barren=$((barren+1)); echo "$(date -u +%FT%TZ) BARREN_JOB rows=$now (was $lastrows) streak=$barren" >> $LOG;
      else barren=0; fi
    fi
    lastrows=$now
    id=$(cd $E8 && submit-job  -q debug -l select=2 -l walltime=00:50:00 \
         -l fsreq=<fs> -N E8_MAIN run_main_guarded.pbs 2>&1)
    n=$((n+1))
    echo "$(date -u +%FT%TZ) SUBMIT #$n $id lanes=$done_lanes rows=$now" >> $LOG
  fi
  sleep 120
done
echo "$(date -u +%FT%TZ) SUPERVISOR_EXIT submissions=$n rows=$(rows) lanes=$(ls $E8/shards/*/lane_*/LANE_COMPLETE.json 2>/dev/null | wc -l)" >> $LOG
