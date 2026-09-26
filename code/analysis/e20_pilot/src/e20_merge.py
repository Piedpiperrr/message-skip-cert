"""E20P merge (end of each job, CPU): per-rank helper / receiver files -> results/E20P_job<J>_rows.jsonl (one row per question, pilot order),
results/MERGE_job<J>.json (completeness, errors, first output time), results/OUTPUTS_HASH_job<J>.txt (SHA-256 of every output file + UTC).
usage: e20_merge.py --job {A,B} [--dry-run]"""
import sys, json, glob, argparse, pathlib, os
sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from e20_exec_common import *

ap = argparse.ArgumentParser(); ap.add_argument('--job', required=True, choices=['A', 'B']); ap.add_argument('--dry-run', action='store_true')
a = ap.parse_args()
BASE = (STAGE / 'notes/dryrun') if a.dry_run else (STAGE / 'records')
RES = (STAGE / 'notes/dryrun/results') if a.dry_run else (STAGE / 'results')
OUT = BASE / f'job{a.job}'; RES.mkdir(parents=True, exist_ok=True)
G = json.loads((OUT / 'GATE.json').read_text()) if (OUT / 'GATE.json').exists() else dict(PASS=False, reason='no GATE.json')


def collect(pat):
    d = {}
    for f in sorted(glob.glob(str(OUT / pat))):
        for r in jl(f):
            k = (r['dataset'], r['id']); assert k not in d, ('duplicate', f, k); d[k] = r
    return d


H = collect('helper_rank*.jsonl'); RC = {rc: collect(f'recv_{rc}_rank*.jsonl') for rc in RECEIVERS}
summ = dict(job=a.job, utc=utc(), gate_PASS=G.get('PASS'), gate_reason=G.get('reason'), datasets_kept=G.get('datasets_kept'),
            n_per_dataset=G.get('n_per_dataset'), per_dataset={})
rows_path = RES / f'E20P_job{a.job}_rows.jsonl'
if G.get('PASS'):
    with open(rows_path, 'w') as f:
        for ds in G['datasets_kept']:
            exp = [it['id'] for it in jl(PILOT(ds))[:G['n_per_dataset']]]
            st = dict(expected=len(exp), helper=0, helper_errors=0, **{rc: 0 for rc in RECEIVERS}, **{rc + '_errors': 0 for rc in RECEIVERS})
            for i in exp:
                h = H.get((ds, i)); row = dict(dataset=ds, id=i, helper=h)
                st['helper'] += h is not None; st['helper_errors'] += bool(h and h.get('runtime_error'))
                for rc in RECEIVERS:
                    r = RC[rc].get((ds, i)); row[rc] = r
                    st[rc] += r is not None; st[rc + '_errors'] += bool(r and r.get('runtime_error'))
                f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
            st['complete'] = st['helper'] == st['expected'] and all(st[rc] == st['expected'] for rc in RECEIVERS) and \
                not st['helper_errors'] and not any(st[rc + '_errors'] for rc in RECEIVERS)
            summ['per_dataset'][ds] = st
    summ['rows_file'] = str(rows_path.relative_to(STAGE))
summ['rank_status'] = {pathlib.Path(p).name: {k: v for k, v in json.loads(pathlib.Path(p).read_text()).items() if k != 'errors'}
                       for p in sorted(glob.glob(str(OUT / 'status_rank*.json')))}
utcs = [r['utc'] for f in sorted(glob.glob(str(OUT / 'smoke_rank*.jsonl'))) for r in jl(f)] + [r['utc'] for r in H.values()]
summ['first_e20_output_utc'] = min(utcs) if utcs else None
pf = OUT / 'PREFLIGHT.json'
summ['preflight_first_output_utc'] = json.loads(pf.read_text()).get('first_output_utc') if pf.exists() else None
save(RES / f'MERGE_job{a.job}.json', summ)
files = sorted([p for p in OUT.rglob('*') if p.is_file() and not p.name.endswith('.tmp')]) + \
    [p for p in [rows_path, RES / f'MERGE_job{a.job}.json'] if p.exists()]
with open(RES / f'OUTPUTS_HASH_job{a.job}.txt', 'w') as f:
    for p in files: f.write(f'{sha(p)}  {p.relative_to(STAGE)}\n')
    f.write(f'# utc={utc()} job={os.environ.get("PBS_JOBID", "none")} E20P job {a.job}\n')
print(json.dumps({k: v for k, v in summ.items() if k != 'rank_status'}, indent=1))
