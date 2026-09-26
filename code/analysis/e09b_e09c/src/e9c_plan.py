"""Builds the deterministic E9c lane plan (login node, no GPU, no gold).

One node, four GPUs, one lane per GPU. Required populations run first on every lane; the
descriptive Text+fact-with-fact variant and the E8-dependent MMLU-Pro populations run last so a
walltime overrun can only cost descriptive or conditional work.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e9_common import *
import pyarrow.parquet as pq

STAGE.joinpath('inputs').mkdir(exist_ok=True)
DS = Path('$DATA_DIR/c2c_reproduction_assets/datasets/allenai--openbookqa')
FACTS = STAGE / 'inputs/obqa_fact1.json'
if not FACTS.exists():
    save(FACTS, {r['id']: r['fact1'] for r in pq.read_table(DS / 'additional/train-00000-of-00001.parquet').to_pylist()})

def task(pair, ds, split, n, lo=0, hi=None, optional=False, variant='plain', facts=None):
    return {'pair': pair, 'dataset': ds, 'split': split, 'slice': [lo, n if hi is None else hi],
            'optional': optional, 'variant': variant, **({'facts': str(facts)} if facts else {})}

sizes = {}
for pair, ds in POPULATIONS + OPTIONAL_POPULATIONS:
    try:
        sizes[pair, ds] = {s: len(v) for s, v in reps(pair, ds).items()}
    except Exception as e:
        sizes[pair, ds] = {'error': f'{type(e).__name__}: {e}'}

E8_OK = e8_ready()
lanes = []

def pop_tasks(pair, ds, optional=False, lo=None, hi=None, variant='plain', facts=None):
    out = []
    for s in ['fit', 'cal', 'dev']:
        n = sizes[pair, ds][s]
        a, b = (0, n) if lo is None else (max(0, min(lo, n)), max(0, min(hi, n)))
        if b > a:
            out.append(task(pair, ds, s, n, a, b, optional, variant, facts))
    return out

# lane 0 / 1: small and medium helpers
for rank, pair in [(0, 'small'), (1, 'medium')]:
    t = pop_tasks(pair, 'obqa') + pop_tasks(pair, 'arc')
    if E8_OK:
        t += pop_tasks(pair, 'mmlu_pro', optional=True)
    lanes.append({'rank': rank, 'helper_pair': pair, 'tasks': t})

# lane 2 / 3: the large helper; MMLU-Pro split so the two 7B lanes finish together
mmn = sizes['large', 'mmlu_pro']
cut = {s: int(round(v * 0.42)) for s, v in mmn.items()}   # lane2 also carries OBQA+ARC
l2 = pop_tasks('large', 'obqa') + pop_tasks('large', 'arc')
l2 += [task('large', 'mmlu_pro', s, mmn[s], 0, cut[s]) for s in ['fit', 'cal', 'dev'] if cut[s] > 0]
l3 = [task('large', 'mmlu_pro', s, mmn[s], cut[s], mmn[s]) for s in ['fit', 'cal', 'dev'] if mmn[s] > cut[s]]
# descriptive Text+fact variant (helper prefill WITH the fact), last on both 7B lanes
ob = sizes['large', 'obqa']
l2 += [task('large', 'obqa', s, ob[s], 0, ob[s] // 2, True, 'with_fact', FACTS) for s in ['fit', 'cal', 'dev']]
l3 += [task('large', 'obqa', s, ob[s], ob[s] // 2, ob[s], True, 'with_fact', FACTS) for s in ['fit', 'cal', 'dev']]
lanes.append({'rank': 2, 'helper_pair': 'large', 'tasks': l2})
lanes.append({'rank': 3, 'helper_pair': 'large', 'tasks': l3})

plan = {'utc': utc(), 'nodes': 1, 'gpus_per_node': 4, 'lanes': lanes, 'sizes': {f'{a}/{b}': v for (a, b), v in sizes.items()},
        'E8_lanes_complete_at_plan_time': E8_OK,
        'required_populations': [f'{a}/{b}' for a, b in POPULATIONS],
        'conditional_populations': [f'{a}/{b}' for a, b in OPTIONAL_POPULATIONS],
        'rows_per_lane': [sum(t['slice'][1] - t['slice'][0] for t in l['tasks']) for l in lanes],
        'rows_per_lane_required': [sum(t['slice'][1] - t['slice'][0] for t in l['tasks'] if not t['optional']) for l in lanes],
        'gold_read': False, 'generation': False, 'receiver_forward': False, 'fuser_loaded': False}
save(STAGE / 'jobs/LANE_PLAN.json', plan)
for l, n, nr in zip(lanes, plan['rows_per_lane'], plan['rows_per_lane_required']):
    print('lane %d helper=%-6s tasks=%2d rows=%6d (required %6d)' % (l['rank'], l['helper_pair'], len(l['tasks']), n, nr))
print('total rows', sum(plan['rows_per_lane']), '| required', sum(plan['rows_per_lane_required']), '| E8 ready', E8_OK)
