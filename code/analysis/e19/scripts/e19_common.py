"""E19 (Round 8) CPU re-analysis of stored outputs. Read-only on every existing P2_* folder; writes only under this stage.

Loaders reused unchanged (imported, never modified):
  - P2_R7_E17_.../scripts/e17_common.py :: load (dev/cal/fit arrays for the Qwen settings via E13 -> E11 loaders, and the
    X3 Llama-3.1-8B records read as analyze_x3.py reads them), mask, cp95, pval
  - P2_R6_E15_.../scripts/e15_common.py :: original_replay (the Table 2 original-configuration replays), component_dev
Every project file opened for reading is logged through an audit hook (READ).
"""
import sys, os, json, csv, hashlib, datetime
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
ROOT = STAGE.parent
RES = STAGE / 'results'
sys.dont_write_bytecode = True

READ = []


def _audit(event, args):
    if event != 'open':
        return
    p, mode, flags = (list(args) + [None, None, None])[:3]
    if not isinstance(p, (str, os.PathLike)):
        return
    if isinstance(mode, str):
        if any(c in mode for c in 'wax+'):
            return
    elif isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT):
        return
    ap = os.path.abspath(os.fspath(p))
    if ap not in READ:
        READ.append(ap)


sys.addaudithook(_audit)

sys.path.insert(0, str(ROOT / 'P2_R6_E15_20260921T072336Z' / 'scripts'))
sys.path.insert(0, str(ROOT / 'P2_R7_E17_20260921T183100Z' / 'scripts'))
import numpy as np  # noqa: E402
import e17_common as E17  # noqa: E402
import e15_common as E15  # noqa: E402

C = E17.C
GRID = C.GRID
INV = 'INVALID'
LABEL = 'POST-HOC re-analysis (E19, PREREG_E19.md); descriptive; does not change any deployed policy'

E7 = ROOT / 'P2_R2_E7_20260919T231531Z'
E16 = ROOT / 'P2_R7_E16_20260921T184114Z'
E14 = ROOT / 'P2_R6_E14_20260921T052241Z'
X3 = ROOT / 'P2_R6_X3_20260921T052602Z'
FULL = ROOT / 'P2_R1_E3POL_MMLU_C2C_FULL_20260919T075315Z'
SA = ROOT / 'P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z'
E9B = ROOT / 'P2_R3_E9BC_20260920T061042Z'

LLO, LLA = ('X3-Llama8B', 'OBQA', 'Text'), ('X3-Llama8B', 'ARC', 'Text')
# the 12 policy rows (11 deployed policies + medium OBQA C2C at the q = .50 sensitivity threshold)
POL12 = [
    ('large/OBQA/Text', ('large', 'OBQA', 'Text'), .80),
    ('large/OBQA/C2C', ('large', 'OBQA', 'C2C'), .80),
    ('large/ARC/Text', ('large', 'ARC', 'Text'), .95),
    ('large/ARC/C2C', ('large', 'ARC', 'C2C'), .90),
    ('large/MMLU-Pro/Text', ('large', 'MMLU-Pro', 'Text'), .40),
    ('large/MMLU-Pro/C2C', ('large', 'MMLU-Pro', 'C2C'), .40),
    ('medium/OBQA/C2C q=.55', ('medium', 'OBQA', 'C2C'), .55),
    ('medium/OBQA/C2C q=.50', ('medium', 'OBQA', 'C2C'), .50),
    ('medium/ARC/C2C', ('medium', 'ARC', 'C2C'), .60),
    ('large/OBQA/Text+fact', C.FACT, .75),
    ('Llama-3.1-8B/OBQA/Text', LLO, .60),
    ('Llama-3.1-8B/ARC/Text', LLA, .70),
]
POLD = {k: (s, q) for k, s, q in POL12}
QWEN8 = ['large/OBQA/Text', 'large/OBQA/C2C', 'large/ARC/Text', 'large/ARC/C2C', 'large/MMLU-Pro/Text',
         'large/MMLU-Pro/C2C', 'medium/OBQA/C2C q=.55', 'medium/ARC/C2C']
QWEN9 = QWEN8 + ['large/OBQA/Text+fact']


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jl(p):
    with open(p) as f:
        return [json.loads(s) for s in f if s.strip()]


def read(p):
    with open(p) as f:
        return json.load(f)


def csvread(p):
    with open(p) as f:
        return list(csv.DictReader(f))


def csvout(name, rows):
    RES.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    with open(RES / name, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)


cp95, pval = E17.cp95, E17.pval


def tau_of(s, q, cuts):
    return {round(g, 4): t for g, t in zip(GRID, cuts)}[round(q, 4)]


_dev = {}


def dev(key):
    """dev split of a policy row -> dict(ids, u, oR, ob, d, m (omitted mask), tau). Labels: frozen V2, INVALID-normalized."""
    if key in _dev:
        return _dev[key]
    s, q = POLD[key]
    L = E17.load(s)
    t = tau_of(s, q, L['cuts'])
    X = L['dev']
    m = E17.mask(X['u'], q, t)
    _dev[key] = dict(ids=list(X['ids']), u=np.asarray(X['u'], float), oR=list(X['oR']), ob=list(X['ob']),
                     d=np.asarray(X['d'], bool), m=np.asarray(m, bool), tau=C.tv(t), q=q)
    return _dev[key]


# ------------------------------------------------------------------ replays
def replay(key):
    """-> dict(ids (panel order), fx{id: rec}, po{id: rec}, source, config, probe_field). Paired by question id."""
    s, q = POLD[key]
    if key in QWEN8:
        ids, fx, po, f = E15.original_replay(s)
        return dict(ids=list(ids), fx=fx, po=po, source=str(f), config='original (Table 2)')
    if key.startswith('Llama'):
        ds = 'obqa' if s[1] == 'OBQA' else 'arc'
        f = E16 / 'replay_llama/records/e2e_requests.jsonl'
        reqs = jl(f)
        ids = read(E16 / f'replay_llama/inputs/{ds}_panel_ids.json')
        fx = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, 'T', 'reference')}
        po = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, 'T', 'policy')}
        assert len(ids) == 128 and set(ids) == set(fx) == set(po)
        return dict(ids=list(ids), fx=fx, po=po, source=str(f), config='second (E16-4, ClusterA)')
    if key == 'large/OBQA/Text+fact':
        f = E7 / 'e6replay/records_e6/e6_replay_requests.jsonl'
        rows = jl(f)
        ids = read(E7 / 'e6replay/inputs/obqa_panel_ids.json')
        rec = {(r['id'], r['arm']): r for r in rows}
        fx = {i: rec[i, 'fixed_TF'] for i in ids}
        po = {i: rec[i, 'policy_TF'] for i in ids}
        assert len(ids) == 128
        return dict(ids=list(ids), fx=fx, po=po, source=str(f), config='second (E6 replay, ClusterA)')
    raise KeyError(key)


def replay_full_mmlu_c2c():
    f = FULL / 'records/four_arm_requests.jsonl'
    reqs = jl(f)
    ids = np.load(FULL / 'protocol/bootstrap_indices.npz')['ids'].tolist()
    fx = {r['id']: r for r in reqs if r['arm'] == 'fixed_C'}
    po = {r['id']: r for r in reqs if r['arm'] == 'policy_C'}
    assert len(ids) == 2641 and set(ids) == set(fx) == set(po)
    return dict(ids=list(ids), fx=fx, po=po, source=str(f), config='second (E3 full population, ClusterA)')


def probe_ms(r):
    p = r['parts_ms']
    return p['probe_ms'] if 'probe_ms' in p else p['online_probe_ms']


def u_of(r):
    return r['probe']['ProbeMax']


def route_R(r):
    return r['selected'] == 'R'


def thr_of(r, key=None):
    return r.get('threshold')


def bidx(n):
    return np.random.default_rng(0).integers(0, n, size=(2000, n))


def ci(b):
    return [float(x) for x in np.quantile(b, [.025, .975])]
