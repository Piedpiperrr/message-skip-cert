"""P2_R1_EXP population adapters (CPU only, read-only on all existing folders).

Writes gold-free population files under records/populations/:
  E1  e1_obqa_test500.jsonl               official OpenBookQA test split (500), parquet order
  E4  e4_<pair>_<ds>.jsonl                7 development populations; R source pointer, V1 rotated query,
                                          V2 foreign helper message (position (i+floor(N/2)) mod N)
  E2b e2b_<setting>.jsonl                 query-only rows {id, question_stem, choice_labels, choice_text}
No gold / correctness / parsed answers are copied into any population file.
"""
import sys
sys.dont_write_bytecode = True
import json, hashlib, pathlib, collections
import pyarrow.parquet as pq

ROOT = pathlib.Path('$DATA_DIR')
NEW = pathlib.Path(__file__).resolve().parents[1]
OUT = NEW / 'records/populations'
DATA = ROOT / 'P2_10_20260911T122423Z/data'
BOUND = ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/splits'
MED = ROOT / 'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z'
MEDX = MED / 'execution_retry1_20260915T164957Z'
MMLU = ROOT / 'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z'
V2L = ROOT / 'P2_SCORING_V2_20260912T191445Z/labels/full_development_P2_SCORING_V2.jsonl'
RISK = ROOT / 'P2_RISK_CALIBRATION_BINARY_20260914T043954Z'
OBQA_TEST = pathlib.Path('$DATA_DIR/c2c_reproduction_assets/datasets/allenai--openbookqa/main/test-00000-of-00001.parquet')
Q4 = ['id', 'question_stem', 'choice_labels', 'choice_text']
SOURCES = collections.OrderedDict()


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def src(p, role):
    p = pathlib.Path(p)
    SOURCES[str(p)] = {'role': role, 'sha256': sha(p)}
    return p


def jl(p, role):
    with open(src(p, role)) as f:
        return [json.loads(l) for l in f if l.strip()]


def jload(p, role):
    with open(src(p, role)) as f:
        return json.load(f)


def write(name, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    assert not p.exists(), f'refusing to overwrite {p}'
    with open(p, 'w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    return p


def labels(k):
    return [chr(65 + i) for i in range(k)]


def rotate(q):
    """V1: option i moves to position (i+1) mod K; labels re-assigned by position."""
    k = len(q['choice_text'])
    assert q['choice_labels'] == labels(k)
    t = list(q['choice_text'])
    rot = [t[k - 1]] + t[:k - 1]
    for i in range(k):
        assert rot[(i + 1) % k] == t[i]
    v = dict(q)
    v['choice_text'] = rot
    if 'choices' in q:
        assert list(q['choices']['label']) == labels(k) and list(q['choices']['text']) == t
        v['choices'] = {'label': labels(k), 'text': rot}
    # displayed label at position p shows original option (p-1) mod K
    back = {labels(k)[p]: labels(k)[(p - 1) % k] for p in range(k)}
    return v, back


manifest = {'files': {}, 'counts': {}, 'rules': {}}

# ------------------------------------------------------------------ E1
tab = pq.read_table(src(OBQA_TEST, 'E1 official OpenBookQA test split (main config, rev 388097ea)')).to_pylist()
assert len(tab) == 500
e1 = []
for i, r in enumerate(tab):
    assert list(r['choices']['label']) == list('ABCD')
    e1.append({'official_index': i, 'id': r['id'], 'question_stem': r['question_stem'],
               'choice_labels': list('ABCD'), 'choice_text': list(r['choices']['text']),
               'choices': {'label': list('ABCD'), 'text': list(r['choices']['text'])}})
assert len({r['id'] for r in e1}) == 500
manifest['files']['e1_obqa_test500.jsonl'] = str(write('e1_obqa_test500.jsonl', e1))
manifest['counts']['e1_obqa_test500'] = len(e1)

# ------------------------------------------------------------------ frozen dev orders and query rows
dev_ids = {}
for ds in ['obqa', 'arc']:
    a = jload(BOUND / f'{ds}_dev_ids.json', 'frozen development ID order')
    b = jload(MED / f'splits/{ds}_dev_ids.json', 'medium development ID order')
    assert a == b and len(set(a)) == len(a)
    dev_ids[ds] = a
p210 = {'obqa': {r['id']: r for r in jl(DATA / 'obqa_dev.jsonl', 'P2_10 OBQA dev rows (query fields only used)')},
        'arc': {r['id']: r for r in jl(DATA / 'arc_validation.jsonl', 'P2_10 ARC validation rows (query fields only used)')}}
medq = {}
for ds in ['obqa', 'arc']:
    medq[ds] = {}
    for s in ['train', 'dev']:
        for r in jl(MED / f'inputs/{ds}_{s}_queries.jsonl', 'medium query-only inputs'):
            assert set(r) == set(Q4)
            medq[ds][r['id']] = r
    for i in dev_ids[ds]:
        x, y = p210[ds][i], medq[ds][i]
        assert all(x[k] == y[k] for k in Q4), (ds, i)
risk_dev = jl(RISK / 'inputs/dev_queries.jsonl', 'historical D dev query rows (large/OBQA dev)')
assert [r['id'] for r in risk_dev] == dev_ids['obqa'] and all(r == medq['obqa'][r['id']] for r in risk_dev)

mm_all = {r['id']: {k: r[k] for k in Q4} for r in jl(MMLU / 'inputs/queries_only.jsonl', 'MMLU-Pro query-only inputs') if r['source_split'] == 'test'}
mm_groups = {s: jload(MMLU / f'splits/{s}_groups.json', 'MMLU-Pro frozen group splits') for s in ['fit', 'cal', 'dev']}
mm_reps = {s: [g['representative_id'] for g in mm_groups[s]] for s in mm_groups}
assert [len(mm_reps[s]) for s in ['fit', 'cal', 'dev']] == [3000, 6000, 2641]
assert len(set(sum(mm_reps.values(), []))) == 11641

# ------------------------------------------------------------------ E4
def query_only(row):
    return {k: row[k] for k in ['question_stem', 'choice_labels', 'choice_text', 'choices'] if k in row}


e4 = collections.OrderedDict()
v2 = jl(V2L, 'frozen V2 development labels: R/Text raw source pointers (small/large)')
bykey = {(r['pair'], r['dataset'], r['id']): r for r in v2}
raw_lines = {}


def raw(path, line):
    if path not in raw_lines:
        with open(src(path, 'saved development raw action outputs')) as f:
            raw_lines[path] = f.read().split('\n')
    return json.loads(raw_lines[path][line - 1])


for pair in ['small', 'large']:
    for ds in ['obqa', 'arc']:
        rows = []
        for i in dev_ids[ds]:
            lab = bykey[(pair, ds, i)]
            sR, sT = lab['source_R'], lab['source_T']
            xR, xT = raw(sR['source_path'], sR['source_line']), raw(sT['source_path'], sT['source_line'])
            assert xR['id'] == i and xR['action'] == 'receiver_only' and xT['id'] == i and xT['action'] == 'text'
            assert isinstance(xT['helper_message'], str)
            rows.append({'id': i, 'query': query_only(p210[ds][i]),
                         'R_source': {'path': sR['source_path'], 'line': sR['source_line'], 'action': 'receiver_only'},
                         'own_helper_message': xT['helper_message'],
                         'own_T_source': {'path': sT['source_path'], 'line': sT['source_line']}})
        e4[(pair, ds)] = rows
for ds in ['obqa', 'arc']:
    path = MEDX / f'actions/{ds}_dev.jsonl'
    recs = jl(path, 'medium saved development action outputs')
    idx = {}
    for n, x in enumerate(recs, start=1):
        assert (x['id'], x['action']) not in idx
        idx[(x['id'], x['action'])] = (n, x)
    rows = []
    for i in dev_ids[ds]:
        nR, xR = idx[(i, 'R')]
        nT, xT = idx[(i, 'T')]
        assert xR['query'] == medq[ds][i] == xT['query']
        rows.append({'id': i, 'query': dict(medq[ds][i]),
                     'R_source': {'path': str(path), 'line': nR, 'action': 'R'},
                     'own_helper_message': xT['output']['helper_message'],
                     'own_T_source': {'path': str(path), 'line': nT}})
    e4[('medium', ds)] = rows
path = MMLU / 'shards/2/actions/dev.jsonl'
recs = jl(path, 'MMLU-Pro saved development action outputs')
idx = {}
for n, x in enumerate(recs, start=1):
    assert (x['id'], x['action']) not in idx
    idx[(x['id'], x['action'])] = (n, x)
rows = []
for i in mm_reps['dev']:
    nR, xR = idx[(i, 'R')]
    nT, xT = idx[(i, 'T')]
    assert xR['query'] == mm_all[i] == xT['query']
    rows.append({'id': i, 'query': dict(mm_all[i]),
                 'R_source': {'path': str(path), 'line': nR, 'action': 'R'},
                 'own_helper_message': xT['output']['helper_message'],
                 'own_T_source': {'path': str(path), 'line': nT}})
e4[('large', 'mmlu_pro')] = rows

for (pair, ds), rows in e4.items():
    N = len(rows)
    out = []
    for pos, r in enumerate(rows):
        j = (pos + N // 2) % N
        v1q, back = rotate(r['query'])
        out.append({'pair': pair, 'dataset': ds, 'pos': pos, 'N': N, 'id': r['id'], 'legal_labels': r['query']['choice_labels'],
                    'query': r['query'], 'R_source': r['R_source'],
                    'v1_query': v1q, 'v1_display_to_original': back,
                    'v2_message_pos': j, 'v2_message_id': rows[j]['id'], 'v2_helper_message': rows[j]['own_helper_message'],
                    'v2_message_source': rows[j]['own_T_source']})
    assert all(o['v2_message_id'] != o['id'] for o in out)
    name = f'e4_{pair}_{ds}.jsonl'
    manifest['files'][name] = str(write(name, out))
    manifest['counts'][f'e4_{pair}_{ds}'] = N

# ------------------------------------------------------------------ E2b
e2b = collections.OrderedDict()
e2b['small_obqa_dev'] = [medq['obqa'][i] for i in dev_ids['obqa']]
e2b['small_arc_dev'] = [medq['arc'][i] for i in dev_ids['arc']]
e2b['large_arc_dev'] = [medq['arc'][i] for i in dev_ids['arc']]
for ds in ['obqa', 'arc']:
    for s in ['fit', 'cal', 'dev']:
        ids = jload(MED / f'splits/{ds}_{s}_ids.json', 'medium frozen split IDs (all rows)')
        e2b[f'medium_{ds}_{s}'] = [medq[ds][i] for i in ids]
for s in ['fit', 'cal', 'dev']:
    e2b[f'large_mmlu_pro_{s}'] = [mm_all[i] for i in mm_reps[s]]
expect = {'small_obqa_dev': 742, 'small_arc_dev': 299, 'large_arc_dev': 299, 'medium_obqa_fit': 2100, 'medium_obqa_cal': 1366,
          'medium_obqa_dev': 742, 'medium_arc_fit': 671, 'medium_arc_cal': 448, 'medium_arc_dev': 299,
          'large_mmlu_pro_fit': 3000, 'large_mmlu_pro_cal': 6000, 'large_mmlu_pro_dev': 2641}
for k, rows in e2b.items():
    assert len(rows) == expect[k], (k, len(rows))
    assert all(set(r) == set(Q4) for r in rows)
    name = f'e2b_{k}.jsonl'
    manifest['files'][name] = str(write(name, [{kk: r[kk] for kk in Q4} for r in rows]))
    manifest['counts'][f'e2b_{k}'] = len(rows)

manifest['rules'] = {
    'E4_order': 'frozen development order: OBQA/ARC = P2_CONFIDENCE_REFERENCE_BOUNDARIES splits/<ds>_dev_ids.json (== medium splits); MMLU-Pro = P2_MMLU_PRO_BREADTH_STAGE1 splits/dev_groups.json representative order',
    'V1': 'choice_text rotated so original option i sits at position (i+1) mod K; labels re-assigned by position (A..); parsed displayed label L at position p maps back to original label at index (p-1) mod K',
    'V2': 'position i carries helper_message of position (i + floor(N/2)) mod N from the same pair/population saved Text outputs',
    'E2b_rows': 'exactly {id, question_stem, choice_labels, choice_text}; MMLU-Pro group representatives; medium fit/cal/dev all rows (ARC fit 671 rows incl. MEA_2012_5_8)',
}
manifest['file_sha256'] = {pathlib.Path(p).name: sha(p) for p in manifest['files'].values()}
manifest['sources'] = SOURCES
(OUT / 'POPULATION_MANIFEST.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
print(json.dumps(manifest['counts'], indent=1))
