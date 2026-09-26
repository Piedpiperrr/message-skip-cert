"""E20F merge (end of each job, CPU; derived from the pilot's src/e20_merge.py): all helper / receiver rows of a phase (every job so far) ->
results/E20F_<phase>_rows.jsonl (one row per question: split, id, helper, llama; split and file order), results/MERGE_<phase>_j<tag>.json
(completeness per split, errors, duplicates, first output time) and results/OUTPUTS_HASH_<phase>_j<tag>.txt (SHA-256 of every file of the
phase + the merged rows + UTC). A question counts once: the first row without a runtime error.
usage: e20f_merge.py --phase {fitcal,devtest} --job-tag TAG [--dry-run]"""
import sys, json, glob, argparse, pathlib, os, datetime
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e20f_common as FC

ap = argparse.ArgumentParser(); ap.add_argument('--phase', required=True, choices=['fitcal', 'devtest']); ap.add_argument('--job-tag', required=True)
ap.add_argument('--dry-run', action='store_true'); a = ap.parse_args()
B = FC.base(a.dry_run); OUT = B / 'records' / a.phase; RES = B / 'results'; RES.mkdir(parents=True, exist_ok=True)
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()


def collect(pat):
    d, dup, err = {}, 0, 0
    for f in sorted(OUT.glob(pat)):
        for r in FC.jl(f):
            if r.get('runtime_error') is not None: err += 1; continue
            if r['id'] in d: dup += 1; continue
            d[r['id']] = r
    return d, dup, err


H, hdup, herr = collect('helper_*.jsonl'); L, ldup, lerr = collect('recv_llama_*.jsonl')
splits = FC.phase_splits(a.phase, a.dry_run)
summ = dict(phase=a.phase, job=a.job_tag, utc=utc(), splits=splits, helper_error_rows=herr, llama_error_rows=lerr, helper_duplicate_ok_rows=hdup,
            llama_duplicate_ok_rows=ldup, per_split={})
rows_path = RES / f'E20F_{a.phase}_rows.jsonl'
with open(rows_path, 'w') as f:
    for sp in splits:
        ids = [it['id'] for it in FC.split_items(sp)]
        st = dict(expected=len(ids), helper=sum(i in H for i in ids), llama=sum(i in L for i in ids))
        st['complete'] = st['helper'] == st['llama'] == st['expected']
        summ['per_split'][sp] = st
        for i in ids:
            f.write(json.dumps(dict(split=sp, id=i, helper=H.get(i), llama=L.get(i)), ensure_ascii=False, allow_nan=False) + '\n')
summ['complete'] = all(v['complete'] for v in summ['per_split'].values())
summ['rows_file'] = str(rows_path.relative_to(B))
summ['plans'] = {pathlib.Path(p).name: {k: v for k, v in json.loads(pathlib.Path(p).read_text()).items() if k not in ('assign', 'helper_needed')}
                 for p in sorted(glob.glob(str(OUT / 'PLAN_j*.json')))}
summ['rank_status'] = {pathlib.Path(p).name: {k: v for k, v in json.loads(pathlib.Path(p).read_text()).items() if k != 'errors'}
                       for p in sorted(glob.glob(str(OUT / 'status_j*_rank*.json')))}
utcs = [r['utc'] for r in H.values()] + [r['utc'] for r in L.values()]
summ['first_output_utc'] = min(utcs) if utcs else None
summ['preflight_first_output_utc'] = {pathlib.Path(p).name: json.loads(pathlib.Path(p).read_text()).get('first_output_utc')
                                      for p in sorted(glob.glob(str(OUT / 'PREFLIGHT_j*.json')))}
mp = RES / f'MERGE_{a.phase}_j{a.job_tag}.json'
mp.write_text(json.dumps(summ, indent=1) + '\n')
files = sorted([p for p in OUT.rglob('*') if p.is_file() and not p.name.endswith('.tmp')]) + [rows_path, mp]
with open(RES / f'OUTPUTS_HASH_{a.phase}_j{a.job_tag}.txt', 'w') as f:
    for p in files: f.write(f'{FC.sha(p)}  {p.relative_to(B)}\n')
    f.write(f'# utc={utc()} job={os.environ.get("PBS_JOBID", "none")} E20F {a.phase}\n')
print(json.dumps({k: v for k, v in summ.items() if k not in ('rank_status', 'plans')}, indent=1))
