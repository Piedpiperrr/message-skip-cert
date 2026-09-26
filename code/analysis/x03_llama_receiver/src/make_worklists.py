"""X3 work lists: the first 16 OBQA fit rows (paper split order) for the Step 2 Qwen3-8B check and for the smoke test (same rows).
Also: helper-message hash check of every OBQA/ARC population row against its saved large-pair Text record, and the row IDs against the
paper split files (BND splits/{ds}_{split}_ids.json, *_representatives.json). CPU only; gold is not read. -> notes/HELPER_AND_SPLIT_CHECK.json"""
import sys
sys.dont_write_bytecode = True
from xfam_common import *
W = X / 'records/work'; W.mkdir(parents=True, exist_ok=True)
fit = jl(POP / 'obqa_fit.jsonl')
def dump(name, rows):
    with open(W / name, 'w') as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    return sha(W / name)
out = dict(utc=utc(), validate_rows=dump('validate_rows.jsonl', fit[:16]), smoke_rows=dump('smoke_rows.jsonl', fit[:16]), ids=[r['id'] for r in fit[:16]])
chk = {}
for ds in DATASETS:
    for sp in ['fit', 'cal', 'dev']:
        rows = jl(POP / f'{ds}_{sp}.jsonl'); ids = read(BND / f'splits/{ds}_{sp}_ids.json'); reps = set(read(BND / f'splits/{ds}_{sp}_representatives.json'))
        ok_src = ok_sha = 0
        for r in rows:
            p, n = r['helper_source'].rsplit(':', 1); x = rawline(p, int(n))
            ok_src += x['id'] == r['id'] and x['action'] == 'text' and x['helper_message'] == r['helper_message']
            ok_sha += hashlib.sha256(r['helper_message'].encode()).hexdigest() == r['helper_message_sha256']
        chk[f'{ds}_{sp}'] = dict(n=len(rows), representatives=sum(r['representative'] for r in rows), ids_equal_split_file=[r['id'] for r in rows] == ids,
                                 representatives_equal=set(r['id'] for r in rows if r['representative']) == reps,
                                 helper_message_equals_saved_record=ok_src, helper_message_sha256_ok=ok_sha, file_sha256=sha(POP / f'{ds}_{sp}.jsonl'),
                                 gold_field_present=any('gold' in r or 'answerKey' in r for r in rows))
out['populations'] = chk
out['all_ok'] = all(v['ids_equal_split_file'] and v['representatives_equal'] and v['helper_message_equals_saved_record'] == v['n'] == v['helper_message_sha256_ok']
                    and not v['gold_field_present'] for v in chk.values())
save(X / 'notes/HELPER_AND_SPLIT_CHECK.json', out)
print(json.dumps({k: (v if k != 'populations' else {a: {c: d for c, d in b.items() if c != 'file_sha256'} for a, b in v.items()}) for k, v in out.items()}, indent=1))
