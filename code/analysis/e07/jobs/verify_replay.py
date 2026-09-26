"""Completion/integrity check of the formal E7 + E6 replay records. No analysis, no gold."""
import json, collections
from pathlib import Path
W = Path('$DATA_DIR/P2_R2_E7_20260919T231531Z')
EXPECT = {'large': 2048, 'mmlu': 1024, 'medium': 1024}
out = {}
for s, n in EXPECT.items():
    f = W / s / 'records_e7/e7_requests.jsonl'
    if not f.exists():
        out[s] = {'status': 'NO RECORDS'}
        continue
    rows = [json.loads(x) for x in f.open() if x.strip()]
    ident = [r['frozen_identity'] for r in rows if r.get('frozen_identity')]
    bad = [x for x in ident if not all(v for v in x.values() if v is not None)]
    arms = collections.Counter(r['arm'] for r in rows)
    pos = collections.Counter((r['arm'], r['order_position']) for r in rows)
    lat = collections.defaultdict(list)
    for r in rows:
        lat[r['arm']].append(r['latency_ms'])
    byq = collections.defaultdict(dict)
    for r in rows:
        byq[(r['setting'], r['id'])][r['arm']] = r
    reuse_diff = [k for k, v in byq.items()
                  if v['original']['omitted'] and v['reuse']['raw_answer'] != v['original']['raw_answer']]
    done = W / s / 'E7_REPLAY_COMPLETE.json'
    out[s] = dict(rows=len(rows), expected=n, complete=len(rows) == n,
                  marker=json.loads(done.read_text())['status'] if done.exists() else 'MISSING',
                  arms=dict(arms), position_cells_all_32=all(v == 32 * (n // 512) for v in pos.values()),
                  distinct_position_cells=len(pos),
                  position_cell_counts=sorted(set(pos.values())),
                  frozen_identity_checked=len(ident), frozen_identity_failures=len(bad),
                  invalid=sum(bool(r['invalid']) for r in rows),
                  runtime_failures=sum(bool(r['runtime_failure']) for r in rows),
                  omitted_per_arm={a: sum(1 for r in rows if r['arm'] == a and r['omitted'])
                                   for a in ['original', 'reuse', 'argmax']},
                  mean_latency_ms={a: round(sum(v) / len(v), 1) for a, v in sorted(lat.items())},
                  reuse_vs_original_output_differences=len(reuse_diff),
                  gold_read=any(r.get('gold_read') for r in rows))
f = W / 'e6replay/records_e6/e6_replay_requests.jsonl'
if f.exists():
    rows = [json.loads(x) for x in f.open() if x.strip()]
    done = W / 'e6replay/E6R_REPLAY_COMPLETE.json'
    lat = collections.defaultdict(list)
    for r in rows:
        lat[r['arm']].append(r['latency_ms'])
    out['e6replay'] = dict(rows=len(rows), expected=256, complete=len(rows) == 256,
                           marker=json.loads(done.read_text())['status'] if done.exists() else 'MISSING',
                           arms=dict(collections.Counter(r['arm'] for r in rows)),
                           selected={f"{a}|{b}": n for (a, b), n in collections.Counter((r['arm'], r['selected']) for r in rows).items()},
                           omitted=sum(bool(r['omitted']) for r in rows),
                           invalid=sum(bool(r['invalid']) for r in rows),
                           runtime_failures=sum(bool(r['runtime_failure']) for r in rows),
                           mean_latency_ms={a: round(sum(v) / len(v), 1) for a, v in sorted(lat.items())})
else:
    out['e6replay'] = {'status': 'NO RECORDS'}
(W / 'REPLAY_VERIFICATION.json').write_text(json.dumps(out, indent=2, default=str) + '\n')
for k, v in out.items():
    print(k, json.dumps(v, default=str))
