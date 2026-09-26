"""E17 (Round 7) CPU re-analysis. Read-only on every existing P2_* folder; writes only under this stage.

Loaders reused unchanged: E13 e13_settings (-> E11 e11_common.load / load_fit, -> E5 r2_common, R1 common_r1/data_r1) for the
26 Qwen/X1/X2 settings; the X3 records are read exactly as P2_R6_X3.../src/analyze_x3.py reads them (representatives,
u = P.ProbeMax, answers = parsed or INVALID on runtime error, thresholds = fit order statistics).
"""
import sys, json, csv, glob
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
ROOT = STAGE.parent
RES = STAGE / 'results'
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'P2_R5_E13_20260921T031606Z' / 'scripts'))
import numpy as np  # noqa: E402
from scipy.stats import beta, binom  # noqa: E402
from e13_settings import C, load_fit  # noqa: E402

INV = 'INVALID'
GRID = C.GRID
LABEL = 'POST-HOC descriptive re-analysis (E17, PREREG.md); does not change any deployed policy'
X3 = ROOT / 'P2_R6_X3_20260921T052602Z'
SA = ROOT / 'P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z'
E9B = ROOT / 'P2_R3_E9BC_20260920T061042Z'
E14 = ROOT / 'P2_R6_E14_20260921T052241Z'
X3SET = [('X3-Llama8B', 'OBQA', 'Text'), ('X3-Llama8B', 'ARC', 'Text')]
ALL28 = list(C.MAIN18) + [C.FACT] + list(C.XSET) + X3SET
Q0 = dict(C.Q0)
Q0[('X3-Llama8B', 'OBQA', 'Text')] = 0.60
Q0[('X3-Llama8B', 'ARC', 'Text')] = 0.70


def sname(s): return f'{s[0]}/{s[1]}/{s[2]}'


def norm(x): return INV if x is None else x


def jl(p):
    with open(p) as f:
        return [json.loads(s) for s in f if s.strip()]


def read(p): return json.loads(Path(p).read_text())


def csvread(p): return list(csv.DictReader(open(p)))


def csvout(name, rows):
    RES.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    with open(RES / name, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader(); w.writerows(rows)


def cp95(k, n):
    if n == 0: return (float('nan'), float('nan'))
    return (0.0 if k == 0 else float(beta.ppf(.025, k, n - k + 1)), 1.0 if k == n else float(beta.ppf(.975, k + 1, n - k)))


def pval(k, n): return float(binom.cdf(k, n, .05)) if n else 1.0


def rate(k, n): return k / n if n else float('nan')


_x3 = {}


def _x3load(ds):
    if ds in _x3: return _x3[ds]
    out = {}
    for f in sorted(glob.glob(str(X3 / 'results/runs/chain_*.jsonl'))):
        for r in jl(f):
            if r['dataset'] == ds:
                assert r['id'] not in out; out[r['id']] = r
    ans = lambda r, a: (r[a]['parsed'] if r.get('runtime_error') is None else INV)
    D = {}
    for sp in ['fit', 'cal', 'dev']:
        reps = [r['id'] for r in jl(X3 / f'records/populations/{ds}_{sp}.jsonl') if r['representative']]
        rr = [out[i] for i in reps]
        D[sp] = dict(ids=reps, u=np.array([r['P']['ProbeMax'] for r in rr], float),
                     oR=[norm(ans(r, 'R')) for r in rr], ob=[norm(ans(r, 'T')) for r in rr],
                     rawR=[r['R']['raw'] for r in rr], rawb=[r['T']['raw'] for r in rr])
    D['cuts'] = C.thresholds(list(D['fit']['u']))
    _x3[ds] = D
    return D


def load(s):
    """-> dict(fit=..., cal=..., dev=..., cuts, q0); each split dict(ids, u (np), oR, ob, d (np bool)).
    Text+fact: fit carries u only (no fit reference outputs; oR/ob/d None)."""
    pair, task, ref = s
    if pair == 'X3-Llama8B':
        D = _x3load(C.BENCH[task])
        out = {sp: dict(ids=D[sp]['ids'], u=D[sp]['u'], oR=D[sp]['oR'], ob=D[sp]['ob']) for sp in ['fit', 'cal', 'dev']}
        out['cuts'] = D['cuts']
    else:
        L = C.load(s)
        out = {sp: dict(ids=L[sp]['ids'], u=np.asarray(L[sp]['u'], float), oR=[norm(x) for x in L[sp]['oR']],
                        ob=[norm(x) for x in L[sp]['ob']]) for sp in ['cal', 'dev']}
        if s == C.FACT:
            M = C.load_main()['large', 'OBQA']['fit']
            out['fit'] = dict(ids=M['ids'], u=np.asarray(M['scores']['ProbeMax'], float), oR=None, ob=None)
        else:
            F = load_fit(s)
            out['fit'] = dict(ids=F['ids'], u=np.asarray(F['u'], float), oR=[norm(x) for x in F['oR']], ob=[norm(x) for x in F['ob']])
        out['cuts'] = L['cuts']
    for sp in ['fit', 'cal', 'dev']:
        X = out[sp]
        X['d'] = None if X['oR'] is None else np.array([a != b for a, b in zip(X['oR'], X['ob'])], bool)
    out['q0'] = Q0[s]
    return out


def mask(u, q, t): return C.data_r1.route_mask(np.asarray(u, float), q, t)


def ledger(u, d, cuts, delta=.001):
    rows = []
    for q, t in zip(GRID, cuts):
        m = mask(u, q, t); n = int(m.sum()); k = int(d[m].sum())
        rows.append(dict(q=q, threshold=t, n=n, k=k, p=pval(k, n), accepted=pval(k, n) <= delta))
    return rows


def deployed(rows):
    acc = [r for r in rows if r['accepted']]
    return (acc[-1]['q'] if acc else 0.0), (acc[-1] if acc else None)


def auroc(d, u):
    from sklearn.metrics import roc_auc_score
    d = np.asarray(d, bool)
    return float(roc_auc_score(d, u)) if 0 < d.sum() < len(d) else float('nan')


# ------------------------------------------------------------ sealed ARC test (as in P2_R6_E14.../scripts/e14.py)
PR = C.PR
_sealed = {}


def load_sealed(b):
    """b in {'T','C'} -> dict(threshold, q, rows=[dict(id, legal, choice_text, u, routed, rawR, rawB, oR_V2, oB_V2)]).
    R was executed only on the questions the policy omitted (selected == R); oR_V2 is None elsewhere."""
    if b in _sealed: return _sealed[b]
    if 'reqs' not in _sealed:
        _sealed['cfg'] = read(SA / 'frozen_config.json')
        _sealed['queries'] = jl(SA / 'inputs/test_queries_no_gold.jsonl')
        _sealed['RR'] = {(r['id'], r['reference'], r['mode']): r for r in jl(SA / 'records/e2e_requests.jsonl')}
        _sealed['reqs'] = True
    cfg, RR = _sealed['cfg'], _sealed['RR']
    thr = cfg['thresholds'][b]['threshold']
    rows = []
    for q in _sealed['queries']:
        i, L = q['id'], tuple(q['choice_labels'])
        p, r = RR[i, b, 'policy'], RR[i, b, 'reference']
        routed = p['selected'] == 'R'
        assert routed == (p['probe']['ProbeMax'] <= thr) and r['selected'] == b
        oP = p['parsed']['answer'] if p['parsed']['valid'] else INV
        oB = r['parsed']['answer'] if r['parsed']['valid'] else INV
        rows.append(dict(id=i, legal=L, choice_text=list(q['choice_text']), u=p['probe']['ProbeMax'], routed=routed,
                         rawR=p['output']['raw_answer'] if routed else None, rawB=r['output']['raw_answer'],
                         oR_V2=oP if routed else None, oB_V2=oB))
    _sealed[b] = dict(threshold=thr, q=cfg['thresholds'][b]['q'], rows=rows)
    return _sealed[b]


def loadcache():
    import pickle
    with open(STAGE / 'cache/data28.pkl', 'rb') as f:
        return pickle.load(f)


# certified policies (key, setting, frozen q)
CERT = [('large/OBQA/Text [nominal]', ('large', 'OBQA', 'Text'), .80), ('large/OBQA/C2C [nominal]', ('large', 'OBQA', 'C2C'), .80),
        ('large/ARC/Text', ('large', 'ARC', 'Text'), .95), ('large/ARC/C2C', ('large', 'ARC', 'C2C'), .90),
        ('large/MMLU-Pro/Text', ('large', 'MMLU-Pro', 'Text'), .40), ('large/MMLU-Pro/C2C', ('large', 'MMLU-Pro', 'C2C'), .40),
        ('medium/OBQA/C2C q=.55', ('medium', 'OBQA', 'C2C'), .55), ('medium/OBQA/C2C q=.50', ('medium', 'OBQA', 'C2C'), .50),
        ('medium/ARC/C2C', ('medium', 'ARC', 'C2C'), .60), ('large/OBQA/Text+fact q=.75', C.FACT, .75),
        ('Llama-3.1-8B/OBQA/Text', X3SET[0], .60), ('Llama-3.1-8B/ARC/Text', X3SET[1], .70)]


def f(x, d=4):
    if x is None or x == '': return ''
    if isinstance(x, float) and x != x: return 'n/a'
    return f'{x:.{d}f}' if isinstance(x, float) else str(x)
