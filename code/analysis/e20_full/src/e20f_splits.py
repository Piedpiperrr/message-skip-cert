"""E20F G2 (login node, no model): full-run split files from the rebuilt SQuAD pool order (pool/inputs/POOL_ORDER_squad.txt, produced by the
byte-identical frozen e20_pool.py). Reads only the id, question and context columns of the pinned SQuAD train parquet (the answers column is
never read), builds each item exactly as e20_pool.py does (question.strip(), passage = context.strip()), and writes inputs/FULL_<split>.jsonl
with only id, question, passage: pool positions [400,900) fit, [900,2900) cal, [2900,3900) dev, [3900,4900) test. Checks: the first 400
reconstructed items serialize byte-identically to the pilot's PILOT_squad.jsonl lines; all sets disjoint; <= 300 words. -> notes/SPLITS_E20F.json"""
import json, hashlib, pathlib, datetime
import pyarrow as pa
pa.set_cpu_count(1); pa.set_io_thread_count(1)
import pyarrow.parquet as pq
S = pathlib.Path(__file__).resolve().parents[1]; P = S.parent / 'P2_R8_E20P_20260921T224653Z'
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
man = json.loads((S / 'pool/notes/DOWNLOAD_MANIFEST.json').read_text())['squad']
assert man['revision'] == '7b6d24c440a36b6815f21b70d25016731768db1f'
(fn, v), = man['files'].items(); assert sha(v['path']) == v['sha256']
rows = pq.read_table(v['path'], columns=['id', 'question', 'context'], use_threads=False).to_pylist()
item = {}
for x in rows:
    assert x['id'] not in item
    item[x['id']] = dict(id=x['id'], question=x['question'].strip(), passage=x['context'].strip())
order = (S / 'pool/inputs/POOL_ORDER_squad.txt').read_text().split('\n')[:-1]
assert len(order) == 86830 and len(set(order)) == len(order)
line = lambda i: json.dumps(item[i], ensure_ascii=False) + '\n'
pilot_lines = (P / 'inputs/PILOT_squad.jsonl').read_text().splitlines(keepends=True)
assert [line(i) for i in order[:400]] == pilot_lines, 'reconstruction differs from the pilot file'
SPL = {'fit': (400, 900), 'cal': (900, 2900), 'dev': (2900, 3900), 'test': (3900, 4900)}
out = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), source=dict(repo='rajpurkar/squad', revision=man['revision'], file=fn,
           sha256=v['sha256'], columns_read=['id', 'question', 'context']), gold_read=False,
           pool_order=dict(path='pool/inputs/POOL_ORDER_squad.txt', sha256=sha(S / 'pool/inputs/POOL_ORDER_squad.txt'), n=len(order)),
           pilot_reconstruction_byte_identical=True, splits={})
ids = {'pilot': set(order[:400])}
for sp, (a, b) in SPL.items():
    p = S / f'inputs/FULL_{sp}.jsonl'; p.write_text(''.join(line(i) for i in order[a:b]))
    ids[sp] = set(order[a:b]); assert all(len(item[i]['passage'].split()) <= 300 for i in order[a:b])
    out['splits'][sp] = dict(pool_positions=[a, b], n=b - a, path=str(p.relative_to(S)), sha256=sha(p), first_id=order[a], last_id=order[b - 1])
names = list(ids); out['pairwise_intersections'] = {f'{x}&{y}': len(ids[x] & ids[y]) for i, x in enumerate(names) for y in names[i + 1:]}
out['all_disjoint'] = all(v == 0 for v in out['pairwise_intersections'].values())
(S / 'notes/SPLITS_E20F.json').write_text(json.dumps(out, indent=1) + '\n')
(S / 'notes/FULL_IDS_4500.txt').write_text(''.join(i + '\n' for i in order[400:4900]))
print(json.dumps(out['splits'], indent=0)); print('disjoint', out['all_disjoint'], out['pairwise_intersections'])
