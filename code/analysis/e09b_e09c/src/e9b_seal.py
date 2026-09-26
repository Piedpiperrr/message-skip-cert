"""E9B step 1 (login node, CPU): assemble scores, routes and outputs on the 744 held-out questions,
write them, and hash them. NO GOLD IS READ HERE. e9b_decode.py may only run after this."""
import sys, os, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e9b_common import *
from pathlib import Path

OUT = STAGE / 'analysis'; OUT.mkdir(parents=True, exist_ok=True)

def load(pair):
    recs = {}
    for p in sorted((STAGE / pair / 'records').glob(f'e9b_{pair}_shard*.jsonl')):
        for r in jl(p):
            recs.setdefault(r['id'], {})[r['action']] = r
    return recs

large, medium = load('large'), load('medium')
pop = [r['id'] for r in population()]
missing = {'large': {}, 'medium': {}}
for pair, recs, acts in [('large', large, ACTIONS['large']), ('medium', medium, ACTIONS['medium'])]:
    for a in acts:
        miss = [i for i in pop if a not in recs.get(i, {})]
        if miss: missing[pair][a] = len(miss)
if any(missing.values()):
    print('INCOMPLETE — not sealing:', json.dumps(missing)); sys.exit(3)

scores, routes, outputs = [], [], []
for i in pop:
    for pair, recs in [('large', large), ('medium', medium)]:
        pr = recs[i]['probe']
        scores.append({'id': i, 'pair': pair, 'ProbeMax': pr['ProbeMax'],
                       'argmax_probe_label': pr['argmax_probe_label'],
                       'probe_ids_sha256': pr['probe_ids_sha256'], 'input_tokens': pr['input_tokens']})
        for a in ACTIONS[pair]:
            if a == 'probe': continue
            r = recs[i][a]
            raw = r['output']['raw_answer'] if pair == 'medium' else r['raw_answer']
            ids = r['output']['generated_token_ids'] if pair == 'medium' else r['generated_token_ids']
            outputs.append({'id': i, 'pair': pair, 'action': a, 'raw_answer': raw,
                            'generated_token_ids': ids, 'answer': r['answer'], 'invalid': r['invalid'],
                            'latency_ms': r['latency_ms']})

def ans(pair, i, a):
    recs = large if pair == 'large' else medium
    return recs[i][a]['answer']

for pol in POLICIES:
    pair, act, th = pol['pair'], pol['action'], pol['threshold']
    recs = large if pair == 'large' else medium
    for i in pop:
        u = recs[i]['probe']['ProbeMax']
        omitted = u <= th
        routes.append({'id': i, 'policy': pol['key'], 'pair': pair, 'reference': act, 'q': pol['q'],
                       'threshold': th, 'ProbeMax': u, 'route': 'R' if omitted else act,
                       'omitted': bool(omitted),
                       'policy_answer': ans(pair, i, 'R') if omitted else ans(pair, i, act),
                       'reference_answer': ans(pair, i, act), 'R_answer': ans(pair, i, 'R'),
                       'changed': int(ans(pair, i, 'R') != ans(pair, i, act))})

writejl = lambda p, rows: Path(p).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
writejl(OUT / 'SEALED_SCORES.jsonl', scores)
writejl(OUT / 'SEALED_ROUTES.jsonl', routes)
writejl(OUT / 'SEALED_OUTPUTS.jsonl', outputs)
def sha(p):
    h = hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
import datetime
receipt = {'utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
           'population': 'held_out_744', 'N': len(pop),
           'files': {f: sha(OUT / f) for f in ['SEALED_SCORES.jsonl', 'SEALED_ROUTES.jsonl', 'SEALED_OUTPUTS.jsonl']},
           'counts': {'scores': len(scores), 'routes': len(routes), 'outputs': len(outputs)},
           'policies': [p['key'] for p in POLICIES],
           'gold_read': False, 'answer_key_opened': False,
           'note': 'written and hashed before the answer key was decoded, as PROTOCOL_FREEZE_E9B.md requires'}
Path(OUT / 'SEAL_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
