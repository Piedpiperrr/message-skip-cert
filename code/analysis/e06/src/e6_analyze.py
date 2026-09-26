"""E6 analysis, exactly the seven pre-registered quantities of e6/PROTOCOL_FREEZE_E6.md section 5.

Read-only on every P2_* source; writes only under e6/analysis/.  Gold is read here, after all E6
model outputs are complete (2108/2108 rows, status PASS), as section 5 item 7 requires.
"""
import json, hashlib, sys
from pathlib import Path
import numpy as np

W = Path(__file__).resolve().parents[1]
ROOT = W.parent
BND = ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
ZG = ROOT / 'P2_ZERO_GOLD_CONTROLS_20260914T065145Z'
V2 = ROOT / 'P2_SCORING_V2_20260912T191445Z'
sys.path.insert(0, str(ROOT / 'P2_R1_CPU_20260919T045556Z/src'))
sys.dont_write_bytecode = True
from common_r1 import read, jl, csvout, tv, pval, cp999, GRID  # noqa: E402

INV = 'INVALID'
OUT = W / 'e6/analysis'
OUT.mkdir(parents=True, exist_ok=True)


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ---- source hash gate (section 3: verify every reused source before use) -------------------------
SRC = {
 'R_train': (V2 / 'labels/full_train_P2_SCORING_V2.jsonl', 'a26986635c944974a5263e08457cb181489a32aec84da450fd514f9155dbf911'),
 'R_dev': (V2 / 'labels/full_development_P2_SCORING_V2.jsonl', '6fde2e0a58f9be88ef14edf7aeab0ac7202b594a17b94d1d18f034f8984d9aa8'),
 'probes': (ZG / 'records/probe_records.jsonl', '2ecc6bd323be2868415042ff346c1d500ff98b796c25ea0f73ad755d234f1a7b'),
 'thresholds': (BND / 'thresholds/large_obqa.json', 'e874e2d8aeb5d10450d4110725e09b5652a5c4d53e874739d16fd526ce735268'),
 'cal_reps': (BND / 'splits/obqa_cal_representatives.json', '8b33a4d168131c5a0095c5eabcdea2f2b3bb272dfae8a41ab2a7e0e05d5ebaed'),
 'dev_reps': (BND / 'splits/obqa_dev_representatives.json', '80d1bbdd9148df3037401881533a2137b0d4ce9ee90a8ebb424fb413440bfbab'),
 'fit_reps': (BND / 'splits/obqa_fit_representatives.json', '1559bc9668d88a986df0967b96fdf14c995f02f622b126f396819b69b58c4028'),
 'q_train': (BND / 'inputs/obqa_train_queries.jsonl', '56a89982c5fbf8fc08edc322d08a11eaba5ef05ac3b0dfeb662ddb96477ea767'),
 'q_dev': (BND / 'inputs/obqa_dev_queries.jsonl', '23c6a8039b63d176a63c820114a20def2ce6a785d8b8cd86a3b510ed68928094'),
}
hashes = {}
for k, (p, want) in SRC.items():
    got = sha(p)
    hashes[k] = {'path': str(p), 'sha256': got, 'expected': want, 'match': got == want}
    assert got == want, (k, got, want)

# ---- load ----------------------------------------------------------------------------------------
cal_ids = read(SRC['cal_reps'][0])
dev_ids = read(SRC['dev_reps'][0])
assert len(cal_ids) == 1366 and len(dev_ids) == 742

lab = {}
for name, key in [('full_train', 'R_train'), ('full_development', 'R_dev')]:
    for x in jl(SRC[key][0]):
        if x['pair'] == 'large' and x['dataset'] == 'obqa':
            lab[x['id']] = x

probe = {r['id']: r for r in jl(SRC['probes'][0])}
queries = {}
for key in ['q_train', 'q_dev']:
    for r in jl(SRC[key][0]):
        queries[r['id']] = r

e6 = {}
for f in sorted((W / 'e6/main').glob('e6_shard*.jsonl')):
    for r in jl(f):
        assert r['id'] not in e6
        e6[r['id']] = r
assert len(e6) == 2108, len(e6)

# ---- per-row input identity on EVERY used row (section 3) -----------------------------------------
ident = {'probe_ids_sha256_match': 0, 'answer_id_match': 0, 'legal_labels_match': 0, 'n': 0}
for i in cal_ids + dev_ids:
    src = queries[i]
    assert probe[i]['probe_ids_sha256'] == hashlib.sha256(
        np.array([probe[i]['probe_ids']], dtype=np.int64).tobytes()).hexdigest()
    ident['probe_ids_sha256_match'] += 1
    ident['answer_id_match'] += (lab[i]['id'] == i)
    ident['legal_labels_match'] += (list(lab[i]['legal_labels']) == list(src['choice_labels']))
    ident['n'] += 1
assert ident['answer_id_match'] == ident['n'] == ident['legal_labels_match'] == 2108


def answers(ids, suffix):
    return np.array([lab[i][f'o_{suffix}'] if lab[i][f'valid_{suffix}'] else INV for i in ids], dtype=object)


def tf_answers(ids):
    return np.array([e6[i]['answer'] for i in ids], dtype=object)


def gold(ids):
    return np.array([lab[i]['gold'] for i in ids], dtype=object)


data = {}
for split, ids in [('cal', cal_ids), ('dev', dev_ids)]:
    assert all(e6[i]['split'] == split for i in ids)
    data[split] = dict(ids=ids, u=np.array([probe[i]['ProbeMax'] for i in ids], float),
                       oR=answers(ids, 'R'), oT=answers(ids, 'T'), oF=tf_answers(ids), g=gold(ids))

# ---- 1. disagreement R vs Text+fact ---------------------------------------------------------------
for s in data:
    d = data[s]
    d['dF'] = (d['oR'] != d['oF'])
    d['dT'] = (d['oR'] != d['oT'])


def auroc(score, y):
    y = np.asarray(y, bool); s = np.asarray(score, float)
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return None
    r = np.empty(len(s), float)
    order = np.argsort(s, kind='mergesort'); ss = s[order]
    i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


# ---- 3. 20-row ledger on calibration with the FROZEN fit quantiles ---------------------------------
TH = read(SRC['thresholds'][0])
cuts = TH['thresholds']
assert TH['q'] == GRID and TH['N_fit'] == 2100


def mask(u, q, t):
    if q == 0: return np.zeros(len(u), bool)
    if q == 1: return np.ones(len(u), bool)
    return u <= tv(t)


ledger = []
for q, t in zip(GRID, cuts):
    m = mask(data['cal']['u'], q, t)
    n = int(m.sum()); k = int(data['cal']['dF'][m].sum())
    p = pval(k, n)
    ledger.append(dict(q=q, threshold=t, N=len(data['cal']['u']), n=n, k=k, p=p,
                       CP_upper_0_999=cp999(k, n), accepted=bool(p <= .001)))
acc = [r['q'] for r in ledger if r['accepted']]
q_star = acc[-1] if acc else 0.0
t_star = dict(zip(GRID, cuts))[q_star] if q_star else None

# ---- 4/5/6/7 -------------------------------------------------------------------------------------
res = {'utc_source_hashes': hashes, 'per_row_identity': ident,
       'n_rows': {'cal': len(cal_ids), 'dev': len(dev_ids)},
       'certified_q': q_star, 'certified_threshold': t_star, 'accepted_q': acc,
       'fallback': q_star == 0.0, 'ledger': ledger}

for s in ('cal', 'dev'):
    d = data[s]
    n = len(d['ids'])
    blk = {'N': n,
           'disagreement_R_vs_TextFact': {'count': int(d['dF'].sum()), 'rate': float(d['dF'].mean())},
           'disagreement_R_vs_Text': {'count': int(d['dT'].sum()), 'rate': float(d['dT'].mean())},
           'AUROC_ProbeMax_on_R_vs_TextFact': auroc(d['u'], d['dF']),
           'AUROC_ProbeMax_on_R_vs_Text': auroc(d['u'], d['dT']),
           'accuracy': {k: {'correct': int((d[v] == d['g']).sum()), 'rate': float((d[v] == d['g']).mean())}
                        for k, v in [('R', 'oR'), ('Text', 'oT'), ('Text+fact', 'oF')]},
           'INVALID': {k: {'count': int((d[v] == INV).sum()), 'rate': float((d[v] == INV).mean())}
                       for k, v in [('R', 'oR'), ('Text', 'oT'), ('Text+fact', 'oF')]},
           'runtime_failures': {'R_or_Text': int(sum(bool(lab[i]['runtime_failure']) for i in d['ids'])),
                                'Text+fact': int(sum(bool(e6[i]['runtime_failure']) for i in d['ids']))}}
    corrF = (d['oF'] == d['g']) & (d['oR'] != d['g'])
    harmF = (d['oR'] == d['g']) & (d['oF'] != d['g'])
    neutral = d['dF'] & ~corrF & ~harmF
    blk['change_vs_R_whole_split'] = {'changed': int(d['dF'].sum()), 'corrective': int(corrF.sum()),
                                      'harmful': int(harmF.sum()), 'neutral_both_wrong': int(neutral.sum())}
    if q_star:
        m = mask(d['u'], q_star, t_star)
        blk['at_deployed_q'] = {'q': q_star, 'threshold': t_star, 'omitted': int(m.sum()),
                                'coverage_rate': float(m.mean()), 'kept': int((~m).sum()),
                                'changed_on_omitted': int(d['dF'][m].sum()),
                                'corrective_on_omitted': int(corrF[m].sum()),
                                'harmful_on_omitted': int(harmF[m].sum()),
                                'neutral_on_omitted': int(neutral[m].sum())}
    else:
        blk['at_deployed_q'] = {'q': 0.0, 'threshold': None, 'omitted': 0, 'coverage_rate': 0.0,
                                'kept': n, 'changed_on_omitted': 0, 'corrective_on_omitted': 0,
                                'harmful_on_omitted': 0, 'neutral_on_omitted': 0,
                                'note': 'fallback: the reference always runs, nothing is omitted'}
    res[s] = blk

(OUT / 'E6_RESULTS.json').write_text(json.dumps(res, indent=2, allow_nan=False) + '\n')
csvout(OUT / 'E6_LEDGER.csv', ledger)
csvout(OUT / 'E6_SUMMARY.csv', [
    dict(split=s, N=res[s]['N'],
         disagree_R_vs_TF=res[s]['disagreement_R_vs_TextFact']['count'],
         disagree_rate=round(res[s]['disagreement_R_vs_TextFact']['rate'], 6),
         AUROC=round(res[s]['AUROC_ProbeMax_on_R_vs_TextFact'], 6),
         acc_R=res[s]['accuracy']['R']['correct'], acc_Text=res[s]['accuracy']['Text']['correct'],
         acc_TF=res[s]['accuracy']['Text+fact']['correct'],
         inv_R=res[s]['INVALID']['R']['count'], inv_Text=res[s]['INVALID']['Text']['count'],
         inv_TF=res[s]['INVALID']['Text+fact']['count'],
         corrective=res[s]['change_vs_R_whole_split']['corrective'],
         harmful=res[s]['change_vs_R_whole_split']['harmful'],
         omitted=res[s]['at_deployed_q']['omitted'],
         changed_on_omitted=res[s]['at_deployed_q']['changed_on_omitted'])
    for s in ('cal', 'dev')])
print(json.dumps({k: res[k] for k in ('certified_q', 'accepted_q', 'fallback')}))
print('cal', res['cal']['disagreement_R_vs_TextFact'], 'AUROC', res['cal']['AUROC_ProbeMax_on_R_vs_TextFact'])
print('dev', res['dev']['disagreement_R_vs_TextFact'], 'AUROC', res['dev']['AUROC_ProbeMax_on_R_vs_TextFact'])
print('WROTE', OUT)
