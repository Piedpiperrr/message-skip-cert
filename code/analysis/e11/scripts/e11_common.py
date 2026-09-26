"""E11 (Round 4) CPU re-analysis. Read-only on all existing P2_* folders; writes only under this stage.
Reuses the E5 modules (r2_common, rawio, parsers_r2) and extends them to all 26 settings."""
import sys, json, collections
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
ROOT = STAGE.parent
E5 = ROOT / 'P2_R2_CPU_20260919T220412Z'
sys.path.insert(0, str(E5 / 'scripts'))
sys.dont_write_bytecode = True

import numpy as np
from r2_common import (read, jl, csvread, csvout, tv, pval, cp999, thresholds, GRID, SETTINGS, EXPECTED_Q,
                       BND, MED, MMLU, V2, TASK, REF, XFAM, X1, BENCH, INV, sname,
                       exposed_ids, ledger_rows, load_main, load_x1, load_x2)  # noqa: F401
import data_r1  # noqa: E402
import rawio    # noqa: E402
import parsers_r2 as PR  # noqa: E402

E8 = ROOT / 'P2_R2_E8_20260920T012544Z'
E6 = ROOT / 'P2_R2_GPU_20260919T220941Z' / 'e6'
LABEL = 'POST-HOC re-analysis (reviewer R4/E11); does not change any primary decision'
RES = STAGE / 'results'

E8SET = [(p, 'MMLU-Pro', r) for p in ['small', 'medium'] for r in ['Text', 'C2C']]
XSET = [('X1-Llama', 'OBQA', 'Text'), ('X1-Llama', 'OBQA', 'C2C'), ('X1-Llama', 'ARC', 'Text'), ('X1-Llama', 'ARC', 'C2C'),
        ('X2-OLMo', 'OBQA', 'Text'), ('X2-OLMo', 'ARC', 'Text'), ('X2-OLMo', 'MMLU-Pro', 'Text')]
FACT = ('large', 'OBQA', 'Text+fact')
MAIN18 = list(SETTINGS) + E8SET
ALL26 = MAIN18 + XSET + [FACT]
Q0 = dict(EXPECTED_Q)
Q0.update({s: 0.0 for s in E8SET})
Q0.update({s: 0.0 for s in XSET})
Q0[FACT] = 0.75
CODE = {'Text': 'T', 'C2C': 'C'}

_cache = {}


def _e8(pair):
    """E8 raw lane records -> id -> dict(split,u,R,T,C, raw_R/raw_T/raw_C, legal)."""
    key = 'e8', pair
    if key in _cache: return _cache[key]
    meta = {r['id']: r for r in jl(E8 / 'inputs/queries_only.jsonl') if r['source_split'] == 'test'}
    rec = {}
    for d in sorted((E8 / 'shards' / pair).glob('lane_*')):
        comp = read(d / 'LANE_COMPLETE.json')
        for rel in comp['files']:
            for r in jl(d / rel):
                rr = rec.setdefault(r['id'], dict(split=r['split'], legal=tuple(meta[r['id']]['choice_labels'])))
                a = r['action']
                if a == 'P':
                    rr['u'] = r['ProbeMax']
                else:
                    rr[a] = r['answer']
                    rr['raw_' + a] = r['output']['raw_answer'] or ''
    _cache[key] = rec
    return rec


def _e6():
    """E6 Text+fact rows -> (id,split) -> dict(answer, raw)."""
    if 'e6' in _cache: return _cache['e6']
    out = {}
    for f in sorted((E6 / 'main').glob('e6_shard*.jsonl')):
        for r in jl(f):
            assert r['action'] == 'text_plus_fact' and not r['runtime_failure']
            out[r['id'], r['split']] = dict(answer=r['answer'], raw=r['raw_answer'] or '')
    _cache['e6'] = out
    return out


def _xcuts(csvpath, setting):
    rr = [r for r in csvread(csvpath) if r['setting'] == setting]
    assert len(rr) == 20, (csvpath, setting, len(rr))
    return [r['threshold'] for r in rr]


def load(s):
    """-> dict(cuts, q0, benchmark, cal=dict(ids,u,oR,ob), dev=dict(...)).  Labels are frozen parser V2 with 'INVALID'."""
    if s in _cache: return _cache[s]
    pair, task, ref = s
    ds = BENCH[task]
    out = dict(benchmark=ds, q0=Q0[s], setting=sname(s))
    if s == FACT:
        D = load_main()['large', 'OBQA']
        E = _e6()
        for sp in ['cal', 'dev']:
            ids = D[sp]['ids']
            out[sp] = dict(ids=ids, u=np.asarray(D[sp]['scores']['ProbeMax'], float),
                           oR=list(D[sp]['ans']['R']), ob=[E[i, sp]['answer'] for i in ids])
        out['cuts'] = D['stored_thresholds']
    elif s in SETTINGS:
        D = load_main()[pair, task]
        for sp in ['cal', 'dev']:
            out[sp] = dict(ids=D[sp]['ids'], u=np.asarray(D[sp]['scores']['ProbeMax'], float),
                           oR=list(D[sp]['ans']['R']), ob=list(D[sp]['ans'][CODE[ref]]))
        out['cuts'] = D['stored_thresholds']
    elif s in E8SET:
        rec = _e8(pair)
        for sp in ['cal', 'dev']:
            ids = [g['representative_id'] for g in read(E8 / f'splits/{sp}_groups.json')]
            out[sp] = dict(ids=ids, u=np.array([rec[i]['u'] for i in ids], float),
                           oR=[rec[i]['R'] for i in ids], ob=[rec[i][CODE[ref]] for i in ids])
        out['cuts'] = [t['threshold'] for t in read(E8 / f'analysis/thresholds/{pair}_fit_thresholds.json')['thresholds']]
    elif pair == 'X2-OLMo':
        D = load_x2()[ds]
        for sp in ['cal', 'dev']:
            out[sp] = dict(ids=D[sp]['ids'], u=np.asarray(D[sp]['u'], float), oR=list(D[sp]['oR']), ob=list(D[sp]['oT']))
        out['cuts'] = _xcuts(XFAM / 'results/analysis/certification_ledger_60.csv', f'{ds}/Text')
    else:  # X1-Llama
        D = load_x1()[ds]
        k = 'oT' if ref == 'Text' else 'oC'
        for sp in ['cal', 'dev']:
            out[sp] = dict(ids=D[sp]['ids'], u=np.asarray(D[sp]['u'], float), oR=list(D[sp]['oR']), ob=list(D[sp][k]))
        out['cuts'] = _xcuts(X1 / 'results/analysis/certification_ledger_80.csv', f'{ds}/{ref}')
    assert len(out['cuts']) == 20
    _cache[s] = out
    return out


# ---------------------------------------------------------------- raw outputs (for E11-b)
def legal_for(s, ids):
    pair, task, ref = s
    ds = BENCH[task]
    if s in E8SET:
        rec = _e8(pair)
        return [rec[i]['legal'] for i in ids]
    return [rawio.legal_labels(ds, i) for i in ids]


def raw(s, split, ids):
    """-> dict('R' -> [raw...], ref -> [raw...]), source note. Extends rawio.raw_cal to the dev split and the new settings."""
    pair, task, ref = s
    ds = BENCH[task]
    if split == 'cal' and s not in E8SET and s != FACT:
        return rawio.raw_cal(s, ids)
    if s == FACT:
        D = load_main()['large', 'OBQA']
        lab = rawio._v2labels('large', 'obqa')
        rr = []
        for i in ids:
            src = lab[i]['source_R']
            rr.append(rawio._rawfile(src['source_path'])[src['source_line']].get('raw_answer') or '')
        E = _e6()
        return {'R': rr, ref: [E[i, split]['raw'] for i in ids]}, f'V2 large/obqa source_R pointers; {E6}/main/e6_shard*.jsonl for Text+fact'
    if s in E8SET:
        rec = _e8(pair)
        return ({'R': [rec[i]['raw_R'] for i in ids], ref: [rec[i]['raw_' + CODE[ref]] for i in ids]},
                str(E8 / f'shards/{pair}/lane_*/actions/*.jsonl'))
    # dev split of the pre-E8 settings
    if pair in ('small', 'large') and task != 'MMLU-Pro':
        lab = rawio._v2labels(pair, ds)
        out = {}
        for a, code in [('R', 'R'), (ref, CODE[ref])]:
            vals = []
            for i in ids:
                src = lab[i]['source_' + code]
                r = rawio._rawfile(src['source_path'])[src['source_line']]
                assert str(r['id']) == str(i) and r['action'] == rawio.ACT[a if a == 'R' else ref]
                vals.append(r.get('raw_answer') or '')
            out[a] = vals
        return out, 'V2 label source pointers into P2_5/P2_6/P2_9 train/development cases'
    if pair == 'medium':
        M = rawio._medium(ds, 'dev')
        return ({a: [(M[i, c]['output'] or {}).get('raw_answer') or '' for i in ids]
                 for a, c in [('R', 'R'), (ref, CODE[ref])]}, str(MED / f'actions/{ds}_dev.jsonl'))
    if pair == 'large' and task == 'MMLU-Pro':
        M = rawio._mmlu('dev')
        return ({a: [(M[i, c]['output'] or {}).get('raw_answer') or '' for i in ids]
                 for a, c in [('R', 'R'), (ref, CODE[ref])]}, str(MMLU / 'shards/2/actions/dev.jsonl'))
    if pair == 'X2-OLMo':
        R = rawio._x2rows()
        return ({'R': [R[ds, i]['R']['raw'] or '' for i in ids], 'Text': [R[ds, i]['T']['raw'] or '' for i in ids]},
                str(XFAM / 'results/runs/chain_*.jsonl'))
    lab = rawio._v2labels('small', ds)
    T, C = rawio._x1rows()
    rr = []
    for i in ids:
        src = lab[i]['source_R']
        rr.append(rawio._rawfile(src['source_path'])[src['source_line']].get('raw_answer') or '')
    src = T if ref == 'Text' else C
    key = CODE[ref]
    return ({'R': rr, ref: [src[ds, i][key]['raw'] or '' for i in ids]},
            f"small-pair raw for R; X1 {'text' if ref == 'Text' else 'c2c'}_chain_*.jsonl for {ref}")


def auroc(d, u):
    from sklearn.metrics import roc_auc_score
    d = np.asarray(d, bool)
    return float(roc_auc_score(d, u)) if 0 < d.sum() < len(d) else float('nan')


def largest_accepted(rows):
    acc = [r['q'] for r in rows if r['accepted']]
    return (acc[-1] if acc else 0.0), acc
