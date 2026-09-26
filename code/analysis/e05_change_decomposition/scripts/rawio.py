"""Locate the SAVED RAW calibration outputs (R and each reference) for every setting. Read-only."""
from r2_common import *
import functools

P5 = ROOT / 'P2_5_20260910T072811Z/results/train_cases.jsonl'
P6 = ROOT / 'P2_6_20260910T164138Z/results/train_cases.jsonl'
P9L = ROOT / 'P2_9_20260911T045010Z/results/large/train_cases.jsonl'
P9S = ROOT / 'P2_9_20260911T045010Z/results/small/train_cases.jsonl'
MMLUS = ROOT / 'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z'
ACT = {'R': 'receiver_only', 'Text': 'text', 'C2C': 'c2c'}
CODE = {'Text': 'T', 'C2C': 'C'}


@functools.lru_cache(maxsize=None)
def _rawfile(path):
    """line number (1-based) -> record"""
    return {i: json.loads(s) for i, s in enumerate(Path(path).open(), 1)}


@functools.lru_cache(maxsize=None)
def _v2labels(pair, ds):
    out = {}
    for name in ['full_train', 'full_development']:
        for r in jl(V2 / f'labels/{name}_P2_SCORING_V2.jsonl'):
            if r['pair'] == pair and r['dataset'] == ds:
                out[r['id']] = r
    return out


@functools.lru_cache(maxsize=None)
def _medium(ds, split):
    out = {}
    for r in jl(MED / f'actions/{ds}_{split}.jsonl'):
        out[r['id'], r['action']] = r
    return out


@functools.lru_cache(maxsize=None)
def _mmlu(split):
    out = {}
    for sh in ['1', '2']:
        f = MMLUS / f'shards/{sh}/actions/{split}.jsonl'
        if f.exists():
            for r in jl(f):
                out[r['id'], r['action']] = r
    return out


@functools.lru_cache(maxsize=None)
def _x2rows():
    out = {}
    for f in sorted((XFAM / 'results/runs').glob('chain_*.jsonl')):
        for r in jl(f):
            out[r['dataset'], r['id']] = r
    return out


@functools.lru_cache(maxsize=None)
def _x1rows():
    T, C = {}, {}
    for f in sorted((X1 / 'results/runs').glob('text_chain_*.jsonl')):
        for r in jl(f):
            T[r['dataset'], r['id']] = r
    for f in sorted((X1 / 'results/runs').glob('c2c_chain_*.jsonl')):
        for r in jl(f):
            C[r['dataset'], r['id']] = r
    return T, C


@functools.lru_cache(maxsize=None)
def legal_labels(bench, qid):
    if bench == 'mmlu_pro':
        r = _mmlu('cal').get((qid, 'R')) or _mmlu('fit').get((qid, 'R'))
        return tuple(r['query']['choice_labels'])
    lab = _v2labels('large', bench).get(qid) or _v2labels('small', bench).get(qid)
    return tuple(lab['legal_labels'])


def raw_cal(setting, ids):
    """-> dict action -> list of raw strings aligned with ids ('' when the run failed), plus a source note.
    Actions are 'R' and the setting's reference."""
    pair, task, ref = setting
    ds = BENCH[task]
    if pair in ('small', 'large') and task != 'MMLU-Pro':
        lab = _v2labels(pair, ds)
        out = {}
        for a, code in [('R', 'R'), (ref, CODE[ref])]:
            vals = []
            for i in ids:
                s = lab[i]['source_' + code]
                rec = _rawfile(s['source_path'])[s['source_line']]
                assert str(rec['id']) == str(i) and rec['action'] == ACT[a if a == 'R' else ref], (i, rec['id'], rec['action'])
                vals.append(rec.get('raw_answer') or '')
            out[a] = vals
        return out, 'V2 label source pointers into P2_5/P2_6/P2_9 train_cases.jsonl'
    if pair == 'medium':
        M = _medium(ds, 'cal')
        out = {}
        for a, code in [('R', 'R'), (ref, CODE[ref])]:
            out[a] = [(M[i, code]['output'] or {}).get('raw_answer') or '' for i in ids]
        return out, str(MED / f'actions/{ds}_cal.jsonl')
    if pair == 'large' and task == 'MMLU-Pro':
        M = _mmlu('cal')
        out = {}
        for a, code in [('R', 'R'), (ref, CODE[ref])]:
            out[a] = [(M[i, code]['output'] or {}).get('raw_answer') or '' for i in ids]
        return out, str(MMLUS / 'shards/{1,2}/actions/cal.jsonl')
    if pair == 'X2-OLMo':
        R = _x2rows()
        return ({'R': [R[ds, i]['R']['raw'] or '' for i in ids],
                 'Text': [R[ds, i]['T']['raw'] or '' for i in ids]},
                str(XFAM / 'results/runs/chain_*.jsonl'))
    # X1: R from the small pair's saved outputs, reference from the X1 runs
    lab = _v2labels('small', ds)
    T, C = _x1rows()
    rr = []
    for i in ids:
        s = lab[i]['source_R']
        rr.append(_rawfile(s['source_path'])[s['source_line']].get('raw_answer') or '')
    src = T if ref == 'Text' else C
    key = 'T' if ref == 'Text' else 'C'
    return ({'R': rr, ref: [src[ds, i][key]['raw'] or '' for i in ids]},
            f"small-pair raw for R; {X1}/results/runs/{'text' if ref == 'Text' else 'c2c'}_chain_*.jsonl for {ref}")


def official_pred_x1(ds, ids):
    """X1 C2C rows also store the official evaluator's own prediction."""
    _, C = _x1rows()
    return [C[ds, i]['C'].get('official_pred') for i in ids]
