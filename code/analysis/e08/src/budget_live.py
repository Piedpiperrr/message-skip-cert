"""Running budget receipt measured from the E8 records themselves (warm-up rows excluded)."""
from common_e8 import *
import glob,collections,statistics
rowsout={};tot=0.
for pair in ['small','medium']:
    lat=collections.defaultdict(list);n_rows=set()
    for f in glob.glob(str(P/f'shards/{pair}/lane_*/actions/*.jsonl'))+glob.glob(str(P/f'shards/{pair}/lane_*/probes/*.jsonl')):
        for line in open(f):
            try:r=json.loads(line)
            except Exception:continue
            lat[r['action']].append((r['ordinal'],r['latency_ms']))
            if r['action']=='P':n_rows.add((r['lane'],r['id']))
    if not lat:continue
    # every recorded request counts; no warm-up filter (the earlier filtered sample was not
    # representative -- the Text helper's token use rises well past the first 400 rows)
    v={a:[x for o,x in lat[a]] for a in 'RTCP'}
    s=sum(statistics.mean(v[a]) for a in 'RTCP')/1000
    done=len(n_rows);tot+=s*12032
    rowsout[pair]=dict(pair=pair,rows_complete=done,rows_remaining=12032-done,
        measured_mean_latency_ms={a:round(statistics.mean(v[a]),1) for a in 'RTCP'},
        sample_rows=min(len(x) for x in v.values()),warmup_rows_excluded_per_lane=0,
        seconds_per_row=round(s,4),projected_pair_wall_hours=round(s*12032/3600,3),
        productive_GPU_hours=round(2*s*12032/3600,2),
        remaining_pair_wall_hours=round(s*(12032-done)/3600,3))
out=dict(utc=utc(),basis='E8 live records, all recorded requests',per_pair=rowsout,
    total_productive_GPU_hours=round(2*tot/3600,2),
    total_pair_wall_hours=round(tot/3600,3),
    remaining_pair_wall_hours=round(sum(r['remaining_pair_wall_hours'] for r in rowsout.values()),3),
    estimate_at_freeze_productive_GPU_hours=27.57,
    refined_estimate_productive_GPU_hours=read(P/'feasibility/GPU_HOUR_ESTIMATE_REFINED.json')['totals']['productive_GPU_hours'],
    limit_GPU_hours=30)
out['overrun_vs_limit_GPU_hours']=round(out['total_productive_GPU_hours']-30,2)
save(P/'feasibility/BUDGET_LIVE.json',out)
print(json.dumps({k:v for k,v in out.items() if k!='per_pair'},indent=1))
for p,r in rowsout.items():print(p,r['rows_complete'],'rows done,',r['seconds_per_row'],'s/row,',r['productive_GPU_hours'],'GPU-h')
