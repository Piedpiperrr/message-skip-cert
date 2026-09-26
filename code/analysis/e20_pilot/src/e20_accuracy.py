"""E20P Step 6 (login node), ONLY after SELECTION_E20P.json is hashed: descriptive pilot accuracy with gold (does not change the selection).
Exact match after the same normalization (e20_extract.normalize_text) against any gold alias; INVALID is incorrect. Alias fields as stored:
SQuAD answers.text; NQ-passage (MRQA) answers; TriviaQA answer.value + answer.aliases + answer.normalized_aliases; NQ-Open answer.
Gold row for an id = the first file row with that id (the pool's tie-break). Writes results/ACCURACY_E20P.json, logs/GOLD_FIRST_OPENED.utc.
usage: e20_accuracy.py [--dry-run --manifest <synthetic manifest>]"""
import sys, json, argparse, pathlib
sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from e20_exec_common import *
from e20_extract import INVALID, normalize_text
import pyarrow as pa
pa.set_cpu_count(1); pa.set_io_thread_count(1)
import pyarrow.parquet as pq

ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--manifest', default=None); a = ap.parse_args()
MANP = pathlib.Path(a.manifest) if a.manifest else STAGE / 'notes/DOWNLOAD_MANIFEST.json'
assert not a.dry_run or MANP.resolve() != (STAGE / 'notes/DOWNLOAD_MANIFEST.json').resolve(), 'dry run must not open the real gold files'
RES = (STAGE / 'notes/dryrun/results') if a.dry_run else (STAGE / 'results')
TOP = RES if a.dry_run else STAGE
h, name = (TOP / 'SELECTION_E20P.sha256').read_text().split('\n')[0].split('  ')
assert name == 'SELECTION_E20P.json' and sha(TOP / name) == h, 'SELECTION_E20P.json missing or changed since it was hashed'
gl = (RES if a.dry_run else STAGE / 'logs') / 'GOLD_FIRST_OPENED.utc'
if not gl.exists(): gl.write_text(utc() + f'  (after SELECTION_E20P.json sha256 {h})\n')
MAN = json.loads(MANP.read_text())
IDCOL = {'squad': 'id', 'nqp': 'qid', 'triviaqa': 'question_id', 'nqopen': 'question'}
GCOL = {'squad': 'answers', 'nqp': 'answers', 'triviaqa': 'answer', 'nqopen': 'answer'}


def aliases(ds, g):
    if ds == 'squad': return list(g['text'])
    if ds == 'triviaqa': return [g['value']] + list(g['aliases']) + list(g['normalized_aliases'])
    return list(g)


rows = {}
for j in ['A', 'B']:
    p = RES / f'E20P_job{j}_rows.jsonl'
    if p.exists():
        for r in jl(p): rows.setdefault(r['dataset'], []).append(r)
out = dict(utc=utc(), selection_sha256=h, settings=[])
for ds in DATASETS:
    if ds not in rows: continue
    want = {r['id'] for r in rows[ds]}; gold = {}
    for fn in sorted(MAN[ds]['files']):
        v = MAN[ds]['files'][fn]; assert sha(v['path']) == v['sha256']
        cols = [IDCOL[ds], GCOL[ds]] + (['subset'] if ds == 'nqp' else [])
        for x in pq.read_table(v['path'], columns=cols, use_threads=False).to_pylist():
            if ds == 'nqp' and x['subset'] != 'NaturalQuestionsShort': continue
            iid = hashlib.sha256(x['question'].encode('utf-8')).hexdigest() if ds == 'nqopen' else x[IDCOL[ds]]
            if iid in want and iid not in gold: gold[iid] = {normalize_text(t) for t in aliases(ds, x[GCOL[ds]])} - {''}
    assert want <= set(gold), 'gold missing for some pilot ids'
    for rc in RECEIVERS:
        R = [x for x in rows[ds] if x[rc] is not None and x[rc].get('runtime_error') is None]
        acc = lambda path: sum(x[rc][path]['answer'] != INVALID and x[rc][path]['answer'] in gold[x['id']] for x in R) / len(R)
        out['settings'].append(dict(dataset=NAME[ds], receiver=rc, n=len(R), acc_R=acc('R'), acc_Text=acc('T'), gain_Text_minus_R=acc('T') - acc('R')))
        print(json.dumps(out['settings'][-1]), flush=True)
save(RES / 'ACCURACY_E20P.json', out)
