"""E16 populations and work lists (CPU, login node; no gold: the ARC test parquet is read for columns id and choices only).
Rows use the X3 driver format (dataset, split, id, representative, query, legal_labels, helper_message, helper_message_sha256, helper_source).
-> records/populations/{holdout744,arc_test}.jsonl, records/work/*.jsonl, notes/ROWS_MANIFEST.json"""
import sys
sys.dont_write_bytecode = True
import glob
from xfam_common import *
sys.path.insert(0, str(BND / 'src')); import receiver_prompt as brp
import pyarrow.parquet as pq
W = X / 'records/work'; W.mkdir(parents=True, exist_ok=True); PP = X / 'records/populations'; PP.mkdir(parents=True, exist_ok=True)


def dump(p, rows):
    with open(p, 'w') as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    return dict(n=len(rows), sha256=sha(p))


def row(ds, split, q, msg, src):
    qq = runtime_query(q); legal = brp.display_labels(len(qq['choice_text'])); assert legal == qq['choice_labels'], q['id']
    return dict(dataset=ds, split=split, id=q['id'], representative=True, query=qq, legal_labels=legal, helper_message=msg,
                helper_message_sha256=hashlib.sha256(msg.encode()).hexdigest() if isinstance(msg, str) else None, helper_source=src)


man = dict(utc=utc(), files={})
# ---- E16-1 populations
ho_ids = read(E9 / 'inputs/holdout_744_ids.json'); hq = {r['id']: r for r in jl(E9 / 'inputs/holdout_744_queries.jsonl')}
T9 = {r['id']: r for f in sorted(glob.glob(str(E9 / 'large/records/e9b_large_shard*.jsonl'))) for r in jl(f) if r['action'] == 'T'}
hold = [row('obqa', 'holdout744', hq[i], T9[i]['helper_message'], 'E9BC large/records e9b_large_shard*.jsonl action T') for i in ho_ids]
aq = sorted(jl(SEALED / 'inputs/test_queries_no_gold.jsonl'), key=lambda r: r['ordinal'])
TR = {r['id']: r for r in jl(SEALED / 'records/e2e_requests.jsonl') if r['reference'] == 'T' and r['mode'] == 'reference'}
arct = [row('arc', 'arc_test', q, TR[q['id']]['output']['helper_message'], 'SEALED records/e2e_requests.jsonl reference=T mode=reference') for q in aq]
man['files']['populations/holdout744.jsonl'] = dump(PP / 'holdout744.jsonl', hold); man['files']['populations/arc_test.jsonl'] = dump(PP / 'arc_test.jsonl', arct)
# numeric-label ARC test items (source labels), without the answer key
src = glob.glob(str(DATA_ROOT / 'hf_cache/hub/datasets--allenai--ai2_arc/snapshots/*/ARC-Challenge/test-00000-of-00001.parquet'))[0]
lab = {r['id']: r['choices']['label'] for r in pq.read_table(src, columns=['id', 'choices']).to_pylist()}
numeric = [r['id'] for r in arct if lab.get(r['id']) and all(x.isdigit() for x in lab[r['id']])]
k_not4 = [r['id'] for r in arct if len(r['legal_labels']) != 4]
man['arc_test_numeric_label_ids'] = numeric; man['arc_test_K_not_4_ids'] = k_not4; man['arc_test_source_labels_file'] = src
# ---- E16-1 work lists
x3pop = {ds: {sp: jl(X3 / f'records/populations/{ds}_{sp}.jsonl') for sp in ['fit', 'cal', 'dev']} for ds in ['obqa', 'arc']}
for ds in x3pop:
    for sp in x3pop[ds]: assert sha(X3 / f'records/populations/{ds}_{sp}.jsonl') == sha(XFAM / f'records/populations/{ds}_{sp}.jsonl')
v1 = x3pop['obqa']['fit'][:8] + x3pop['arc']['fit'][:8]
pick = list(dict.fromkeys(k_not4 + numeric)); byid = {r['id']: r for r in arct}
arc16 = [byid[i] for i in pick][:16]; arc16 += [r for r in arct if r['id'] not in {x['id'] for x in arc16}][:16 - len(arc16)]
man['files']['work/v1_llama_x3rows.jsonl'] = dump(W / 'v1_llama_x3rows.jsonl', v1)
man['files']['work/v5_llama_smoke.jsonl'] = dump(W / 'v5_llama_smoke.jsonl', hold[:16] + arc16)
e161 = hold + arct; h = (len(e161) + 1) // 2
man['files']['work/e16_1_shard0.jsonl'] = dump(W / 'e16_1_shard0.jsonl', e161[:h]); man['files']['work/e16_1_shard1.jsonl'] = dump(W / 'e16_1_shard1.jsonl', e161[h:])
# ---- E16-2 work lists (medium runtime query dicts)
medarc = [r for r in jl(MED / 'actions/arc_fit.jsonl') if r['action'] == 'R'][:16]
man['files']['work/v2_medium_arcfit.jsonl'] = dump(W / 'v2_medium_arcfit.jsonl', [dict(id=r['id'], query=r['query']) for r in medarc])
man['files']['work/v5_medium_smoke.jsonl'] = dump(W / 'v5_medium_smoke.jsonl', [dict(id=r['id'], query={k: r['query'][k] for k in ['question_stem', 'choice_labels', 'choice_text']}) for r in arc16])
man['files']['work/e16_2_arc_test.jsonl'] = dump(W / 'e16_2_arc_test.jsonl', [dict(id=q['id'], query={k: q[k] for k in ['question_stem', 'choice_labels', 'choice_text']}) for q in aq])
# ---- E16-5 work lists
medT = {r['id']: r for r in jl(MED / 'actions/obqa_fit.jsonl') if r['action'] == 'T'}
v3a = []
for r in x3pop['obqa']['fit'][:16]:
    m = medT[r['id']]['output']['helper_message']
    v3a.append(dict(r, helper_message=m, helper_message_sha256=hashlib.sha256(m.encode()).hexdigest(), helper_source='MEDIUM actions/obqa_fit.jsonl T (medium helper Qwen2.5-1.5B)'))
man['files']['work/v3a_medium_own_messages.jsonl'] = dump(W / 'v3a_medium_own_messages.jsonl', v3a)
man['files']['work/v3b_strong_smoke.jsonl'] = dump(W / 'v3b_strong_smoke.jsonl', x3pop['obqa']['fit'][:8] + x3pop['arc']['fit'][:8])
e165 = [r for ds in ['obqa', 'arc'] for sp in ['fit', 'cal', 'dev'] for r in x3pop[ds][sp]]; h = (len(e165) + 1) // 2
man['files']['work/e16_5_shard0.jsonl'] = dump(W / 'e16_5_shard0.jsonl', e165[:h]); man['files']['work/e16_5_shard1.jsonl'] = dump(W / 'e16_5_shard1.jsonl', e165[h:])
# ---- V4 work lists: 16 fit rows per receiver x benchmark, >= 8 with stored u > 0 (first 8 with u > 0, then first 8 others)
mm = {sp: jl(XFAM / f'records/populations/mmlu_pro_{sp}.jsonl') for sp in ['fit', 'cal', 'dev']}
Q = {'obqa': x3pop['obqa']['fit'], 'arc': [r for r in x3pop['arc']['fit'] if r['representative']], 'mmlu_pro': mm['fit']}


def stored_u(rec, ds):
    if rec == 'qwen3_0_6b' and ds != 'mmlu_pro': return {r['id']: (r['ProbeMax'], r.get('probe_ids_sha256')) for r in jl(BND / f'records/small_{ds}_fit_probes.jsonl')}
    if rec == 'qwen3_1_7b' and ds != 'mmlu_pro': return {r['id']: (r['ProbeMax'], r.get('probe_ids_sha256')) for r in jl(MED / f'probes/{ds}_fit.jsonl')}
    if rec == 'qwen3_8b' and ds == 'obqa': return {r['id']: (r['ProbeMax'], r['probe_ids_sha256']) for r in jl(ZG / 'records/probe_records.jsonl') if r['split'] == 'fit'}
    if rec == 'qwen3_8b' and ds == 'arc': return {r['id']: (r['ProbeMax'], r['probe_ids_sha256']) for r in jl(BND / 'records/large_arc_fit_probes.jsonl')}
    if rec == 'qwen3_8b': return {r['id']: (r['ProbeMax'], r.get('probe_ids_sha256')) for f in sorted(glob.glob(str(MMLU / 'shards/*/probes/fit.jsonl'))) for r in jl(f)}
    return {r['id']: (r['u'], None) for r in jl(E8 / f"analysis/merged/{'small' if rec == 'qwen3_0_6b' else 'medium'}_rows.jsonl") if r['split'] == 'fit'}


man['v4'] = {}
for rec in ['qwen3_0_6b', 'qwen3_1_7b', 'qwen3_8b']:
    for ds in ['obqa', 'arc', 'mmlu_pro']:
        su = stored_u(rec, ds); rows = [r for r in Q[ds] if r['id'] in su]
        pos = [r for r in rows if su[r['id']][0] > 0][:8]; rest = [r for r in rows if r not in pos][:16 - len(pos)]
        sel = [dict(r, stored_u=su[r['id']][0], stored_probe_ids_sha256=su[r['id']][1]) for r in pos + rest]
        man['files'][f'work/v4_{rec}_{ds}.jsonl'] = dump(W / f'v4_{rec}_{ds}.jsonl', sel)
        man['v4'][f'{rec}/{ds}'] = dict(n=len(sel), n_u_pos=sum(x['stored_u'] > 0 for x in sel), stored_rows=len(su))
save(X / 'notes/ROWS_MANIFEST.json', man)
print(json.dumps({k: v for k, v in man.items() if k != 'files'}, indent=1)); print({k: v['n'] for k, v in man['files'].items()})
