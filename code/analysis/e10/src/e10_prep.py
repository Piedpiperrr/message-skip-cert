"""E10 step 2: form the three GSM8K splits from question text only.

Only the 'question' column of the train parquet is read.  The 'answer' column is never
materialised in this process (pyarrow column projection).  No model, no tokenizer.
"""
import json, hashlib, datetime, sys
from pathlib import Path
import pyarrow.parquet as pq

STAGE = Path(__file__).resolve().parents[1]
SNAP = Path('$DATA_DIR/cache/huggingface/hub/'
            'datasets--openai--gsm8k/snapshots/740312add88f781978c0658806c59bc2815b9866')
TRAIN = SNAP / 'main/train-00000-of-00001.parquet'
REV = '740312add88f781978c0658806c59bc2815b9866'

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

sf = pq.ParquetFile(TRAIN)
cols = sf.schema_arrow.names
assert 'question' in cols and 'answer' in cols, cols
tb = pq.read_table(TRAIN, columns=['question'])          # <- gold column deliberately excluded
qs = tb.column('question').to_pylist()
assert len(qs) == sf.metadata.num_rows

rows = [{'id': 'gsm8k_train_%05d' % i, 'row': i, 'question': q,
         'qhash': hashlib.sha256(q.encode('utf-8')).hexdigest()} for i, q in enumerate(qs)]
# Preregistration: "Sort by content hash of the question string".  Ties broken by id so the
# order is total and reproducible.
rows.sort(key=lambda r: (r['qhash'], r['id']))

dups = len(rows) - len({r['question'] for r in rows})
splits = {'fit': rows[:400], 'cal': rows[400:1400], 'dev': rows[1400:1800]}
assert sum(len(v) for v in splits.values()) == 1800
sel = {r['id'] for v in splits.values() for r in v}
assert len(sel) == 1800

(STAGE / 'inputs').mkdir(exist_ok=True)
(STAGE / 'splits').mkdir(exist_ok=True)
for s, v in splits.items():
    (STAGE / f'splits/gsm8k_{s}_ids.json').write_text(json.dumps([r['id'] for r in v], indent=1) + '\n')
with (STAGE / 'inputs/gsm8k_queries.jsonl').open('w') as f:
    for s, v in splits.items():
        for r in v:
            f.write(json.dumps({'id': r['id'], 'row': r['row'], 'split': s,
                                'question': r['question'], 'qhash': r['qhash']},
                               ensure_ascii=False) + '\n')
(STAGE / 'inputs/gsm8k_pool_order.json').write_text(json.dumps(
    {'n_pool': len(rows), 'order_rule': 'sha256(question utf-8) ascending, ties by id',
     'first_10': [r['id'] for r in rows[:10]], 'ids_sha256':
     hashlib.sha256(json.dumps([r['id'] for r in rows]).encode()).hexdigest()}, indent=2) + '\n')

freeze = {'utc': utc(), 'dataset': 'openai/gsm8k', 'config': 'main', 'split': 'train',
          'revision': REV, 'revision_source': 'huggingface.co/api/datasets/openai/gsm8k sha, '
          'verified 2026-09-20 against the local snapshot directory name',
          'train_parquet': str(TRAIN), 'train_parquet_sha256': sha(TRAIN),
          'train_rows': len(rows), 'exact_duplicate_questions': dups,
          'columns_in_file': cols, 'columns_read': ['question'], 'gold_read': False,
          'splits': {s: {'n': len(v), 'first': v[0]['id'], 'last': v[-1]['id']} for s, v in splits.items()},
          'files': {f: sha(STAGE / f) for f in
                    ['inputs/gsm8k_queries.jsonl', 'inputs/gsm8k_pool_order.json',
                     'splits/gsm8k_fit_ids.json', 'splits/gsm8k_cal_ids.json',
                     'splits/gsm8k_dev_ids.json']}}
(STAGE / 'SPLIT_FREEZE_E10.json').write_text(json.dumps(freeze, indent=2) + '\n')
print(json.dumps({k: v for k, v in freeze.items() if k != 'files'}, indent=2))
print('files:', json.dumps(freeze['files'], indent=1))
