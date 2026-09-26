"""E8 GPU-hour estimate from the two prescribed logs:
   (1) the large-pair MMLU-Pro Stage1 run, (2) the medium-pair OBQA/ARC run.
Per-action pair-scaling factors come from the frozen cross-pair timing table
(P2_MMLU_PRO_BREADTH_PROTOCOL_AND_COST_REVIEW/evidence/HISTORICAL_TIMING_SUMMARY.json),
which measured small/medium/large on the SAME OBQA and ARC rows. No new measurement."""
import json,statistics,collections,datetime
from pathlib import Path
E8=Path(__file__).resolve().parents[1];ROOT=E8.parent
MMLU=ROOT/'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z'
MED=ROOT/'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z'
REVIEW=ROOT/'P2_MMLU_PRO_BREADTH_PROTOCOL_AND_COST_REVIEW_20260915T224801Z'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()

# (1) large-pair MMLU-Pro measured per-action latency (both shards, all splits)
lat=collections.defaultdict(list)
for sh in ['1','2']:
    for d in ['actions','probes']:
        for f in sorted((MMLU/f'shards/{sh}/{d}').glob('*.jsonl')):
            with f.open() as fh:
                for line in fh:
                    r=json.loads(line);lat[r['action']].append(r['latency_ms'])
large_mmlu={a:statistics.mean(v) for a,v in lat.items()}
large_n={a:len(v) for a,v in lat.items()}
ledger=json.loads((MMLU/'RESOURCE_LEDGER.json').read_text())
large_wall=sum(j['progress']['wall_seconds'] for j in ledger['jobs'].values())
large_rows=sum(j['progress']['complete_rows'] for j in ledger['jobs'].values())

# (2) medium-pair OBQA/ARC measured wall
medled=json.loads((MED/'RESOURCE_LEDGER.json').read_text())['replacement_attempt']
med_wall=json.loads((MED/'INFERENCE_COMPLETE.json').read_text())['wall_seconds']
med_requests=medled['formal_action_success_count']+medled['formal_probe_success_count']

# cross-pair per-action scaling on the shared OBQA/ARC rows
hist=json.loads((REVIEW/'evidence/HISTORICAL_TIMING_SUMMARY.json').read_text())
H={(r['pair'],r['action'],r['dataset']):r['latency_ms'] for r in hist if 'pair' in r}
ACT={'R':'R','T':'Text','C':'C2C'}
scale={}
for pair in ['small','medium']:
    scale[pair]={}
    for code,name in ACT.items():
        ratios=[H[pair,name,ds]/H['large',name,ds] for ds in ['obqa','arc'] if (pair,name,ds) in H and ('large',name,ds) in H]
        scale[pair][code]=sum(ratios)/len(ratios)
    # ProbeMax: only medium is tabulated against a large MMLU-Pro probe; keep 1.0 (probe is ~2% of a row)
    scale[pair]['P']=1.0

N_ROWS=12032
rows=[]
total_pair_seconds=0.
for pair in ['small','medium']:
    per_row_ms=sum(large_mmlu[a]*scale[pair][a] for a in ['R','T','C','P'])
    secs=per_row_ms*N_ROWS/1000.
    total_pair_seconds+=secs
    rows.append(dict(pair=pair,per_row_projected_ms=round(per_row_ms,1),
        per_action_projected_ms={a:round(large_mmlu[a]*scale[pair][a],1) for a in ['R','T','C','P']},
        scaling_vs_large={a:round(scale[pair][a],4) for a in ['R','T','C','P']},
        rows=N_ROWS,projected_pair_wall_seconds=round(secs,1),projected_pair_wall_hours=round(secs/3600,3),
        projected_GPU_hours_2_GPUs=round(2*secs/3600,3)))

WALL=3000          # 00:50:00 debug cap
STARTUP=400        # cold import + weights + mechanical smoke + margin, per pair process
USABLE=WALL-STARTUP
SLOTS_PER_NODE=2   # 4 A100 per ClusterA node, one helper GPU + one receiver/fuser GPU per run
est={'utc':utc(),
 'inputs':{'large_MMLU_Pro':{'source':str(MMLU/'RESOURCE_LEDGER.json'),
    'mean_latency_ms':{a:round(v,1) for a,v in large_mmlu.items()},'n_requests':large_n,
    'measured_wall_seconds':round(large_wall,1),'rows':large_rows,
    'measured_seconds_per_row':round(large_wall/large_rows,4),
    'allocation_GPU_hours':ledger['actual_GPUh'],'machine':'ClusterB A100'},
  'medium_OBQA_ARC':{'source':str(MED/'RESOURCE_LEDGER.json'),
    'measured_wall_seconds':round(med_wall,1),'requests':med_requests,
    'measured_seconds_per_request':round(med_wall/med_requests,4),
    'allocation_GPU_hours':medled['actual_GPU_allocation_hours'],'machine':'ClusterB A100'},
  'cross_pair_scaling_source':str(REVIEW/'evidence/HISTORICAL_TIMING_SUMMARY.json')},
 'projection':rows,
 'totals':{'projected_pair_wall_hours_both_pairs':round(total_pair_seconds/3600,3),
   'projected_productive_GPU_hours_both_pairs':round(2*total_pair_seconds/3600,3)},
 'debug_queue_packing':{'walltime_cap_seconds':WALL,'startup_reserve_seconds_per_process':STARTUP,
   'usable_collection_seconds_per_slot':USABLE,'pair_slots_per_node':SLOTS_PER_NODE}}
for nodes in [1,2]:
    slots=nodes*SLOTS_PER_NODE
    jobs=-(-int(total_pair_seconds)//(slots*USABLE))
    est['debug_queue_packing'][f'select_{nodes}']=dict(nodes=nodes,GPUs=nodes*4,pair_slots=slots,
        pair_seconds_per_job=slots*USABLE,main_jobs_needed=jobs,
        allocated_GPU_hours=round(jobs*nodes*4*WALL/3600,2))
best=est['debug_queue_packing']['select_2']
est['gate']={'limit_GPU_hours':30,'limit_debug_jobs':6,
  'estimate_productive_GPU_hours':est['totals']['projected_productive_GPU_hours_both_pairs'],
  'estimate_allocated_GPU_hours_select2':best['allocated_GPU_hours'],
  'estimate_main_debug_jobs_select2':best['main_jobs_needed'],
  'note':'productive = 2 GPUs x pair-wall; allocated = every GPU in the reservation x walltime cap'}
(E8/'feasibility').mkdir(exist_ok=True)
(E8/'feasibility/GPU_HOUR_ESTIMATE.json').write_text(json.dumps(est,indent=2)+'\n')
print(json.dumps({'totals':est['totals'],'select_1':est['debug_queue_packing']['select_1'],
                  'select_2':best,'gate':est['gate'],'projection':rows},indent=2))
