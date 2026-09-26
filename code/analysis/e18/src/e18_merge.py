"""E18 merge: per-shard score files -> SCORES_E18.parquet, SHA-256 -> SCORES_HASH.txt.  No gold."""
import sys, json, glob, hashlib, datetime, argparse
sys.dont_write_bytecode = True
from pathlib import Path
import numpy as np
import pyarrow as pa, pyarrow.parquet as pq

ap = argparse.ArgumentParser()
ap.add_argument('--records', required=True)
ap.add_argument('--dest', required=True)
ap.add_argument('--nranks', type=int, default=4)
a = ap.parse_args()
REC, DEST = Path(a.records), Path(a.dest)
E10 = Path('$DATA_DIR/P2_R4_E10_20260920T225954Z')
SPL = {s: json.loads((E10 / f'splits/gsm8k_{s}_ids.json').read_text()) for s in ['fit', 'cal', 'dev']}

st = [json.loads(Path(p).read_text()) for p in sorted(glob.glob(str(REC / 'scores_rank*.status.json')))]
assert len(st) == a.nranks and all(s['complete'] for s in st), st
rows = [json.loads(l) for p in sorted(glob.glob(str(REC / 'scores_rank*.jsonl'))) for l in open(p) if l.strip()]
by = {(r['split'], r['question_id']): r for r in rows}
order = [(s, i) for s in ['fit', 'cal', 'dev'] for i in SPL[s]]
assert len(rows) == len(by) == 1800 and set(by) == set(order), (len(rows), len(by))
rows = [by[k] for k in order]
cols = {'split': [r['split'] for r in rows], 'question_id': [r['question_id'] for r in rows],
        'L': [r['L'] for r in rows], 'n_gen_tokens': [r['n_gen_tokens'] for r in rows],
        'n_pos_32': [r['n_pos_32'] for r in rows], 'argmax_match_32': [r['argmax_match_32'] for r in rows]}
for i in range(64):
    cols['d%02d' % (i + 1)] = [r['one_minus_maxp'][i] if i < len(r['one_minus_maxp']) else np.nan for r in rows]
tb = pa.table({k: pa.array(v, type=pa.float64()) if k.startswith('d') else pa.array(v) for k, v in cols.items()})
out = DEST / 'SCORES_E18.parquet'
pq.write_table(tb, out)
h = hashlib.sha256(out.read_bytes()).hexdigest()
t = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
(DEST / 'SCORES_HASH.txt').write_text('%s  SCORES_E18.parquet\nutc: %s\nrows: %d\ndry_run: %s\n'
                                      % (h, t, len(rows), any(r.get('DRY_RUN') for r in rows)))
print('MERGED', len(rows), 'rows ->', out, h, t)
