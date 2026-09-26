"""E21 (Round 9) post hoc CPU analyses of stored outputs. Read-only on every earlier P2_* folder; writes only under this stage.

Loaders reused unchanged (imported, never modified):
  - P2_R8_E19_.../scripts/e19_common.py :: dev(key) (frozen dev arrays + omitted mask), replay(key) (panel replays), POLD, QWEN9,
    tau_of, bidx, ci, probe_ms, u_of, route_R; through it E17 e17_common (load, ledger, deployed, mask, auroc, cp95, pval,
    load_sealed) -> E13 e13_settings -> E11 e11_common (exposed_ids = X) -> E5 r2_common -> R1 common_r1 / data_r1.
  - P2_R3_E9A_.../scripts/e9a_common.py :: gold_map (OBQA dev / ARC validation / MMLU-Pro gold, as e5c.py), null_answers (E4 V1/V2
    answers mapped back to the original option order).
  - E16-3 score m: the functions lse() and scores() are taken verbatim (ast extraction + exec) from P2_R7_E16_.../src/analyze_e16_3.py;
    importing that script would re-run it and rewrite E16 files.
  - SQuAD: e20_extract.changed (E20 pilot module, as E20F uses it).
Gold sources: OBQA/ARC fit/cal/dev = P2_SCORING_V2 labels full_train/full_development, pair large, field gold (as analyze_x3.py);
MMLU-Pro = e9a_common.gold_map (MMLU-Pro parquet); held-out 744 OBQA = openbookqa train parquet answerKey (as E13 item3 / E16);
sealed ARC / E16 ARC test = P2_FINAL_SEALED_ARC_CONFIRMATION/inputs/evaluation_gold_after_prediction_freeze.jsonl field gold (as E16).
"""
import sys, os, ast, json, csv, hashlib, datetime
from pathlib import Path

STAGE21 = Path(__file__).resolve().parents[1]
ROOT = STAGE21.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'P2_R8_E19_20260921T224942Z' / 'scripts'))
from e19_common import *  # noqa: F401,F403,E402
import e19_common as E19  # noqa: E402
sys.path.insert(0, str(ROOT / 'P2_R3_E9A_20260920T043713Z' / 'scripts'))
import e9a_common as E9A  # noqa: E402
import numpy as np  # noqa: E402
from scipy.stats import binom  # noqa: E402

RES = STAGE21 / 'results'
LOGS = STAGE21 / 'logs'
LABEL = 'POST HOC (E21, PREREG.md); stored outputs only; creates no deployment and changes no count in the paper'
DATA_ROOT = ROOT.parent.parent
E16 = ROOT / 'P2_R7_E16_20260921T184114Z'
E20F = ROOT / 'P2_R8_E20F_20260922T003652Z'
E4DIR = ROOT / 'P2_R1_EXP_20260919T050555Z'
SEALED = ROOT / 'P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z'
E9 = ROOT / 'P2_R3_E9BC_20260920T061042Z'
OBQA_TRAIN_PARQUET = DATA_ROOT / 'c2c_reproduction_assets/datasets/allenai--openbookqa/main/train-00000-of-00001.parquet'


def csvout(name, rows):
    """writes under this stage's results/ only (e19_common.csvout would write into E19)."""
    RES.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    with open(RES / name, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)) if rows else ['empty'])
        w.writeheader()
        w.writerows(rows)


def jdump(p, obj):
    with open(p, 'w') as f:
        json.dump(obj, f, indent=1, default=lambda x: x.item() if hasattr(x, 'item') else str(x))


def run_log(name, T0, extra=None):
    LOGS.mkdir(parents=True, exist_ok=True)
    d = dict(start_utc=T0, end_utc=utc(), script=name, script_sha256=sha(STAGE21 / 'scripts' / name),
             common_sha256=sha(STAGE21 / 'scripts' / 'e21_common.py'), files_read=list(E19.READ))
    if extra:
        d.update(extra)
    jdump(LOGS / (Path(name).stem + '_run.json'), d)


# ------------------------------------------------------------------ settings
# E21-1: (row name, E19 policy key, nominal flag, out-of-sample population)
SET6 = [('large/OBQA/Text', 'large/OBQA/Text', True, 'held-out OBQA 744'),
        ('large/ARC/Text', 'large/ARC/Text', False, 'sealed ARC 1,172'),
        ('large/MMLU-Pro/Text', 'large/MMLU-Pro/Text', False, None),
        ('large/OBQA/Text+fact', 'large/OBQA/Text+fact', True, 'held-out OBQA 744'),
        ('Llama-3.1-8B/OBQA/Text', 'Llama-3.1-8B/OBQA/Text', False, 'held-out OBQA 744 (E16-1)'),
        ('Llama-3.1-8B/ARC/Text', 'Llama-3.1-8B/ARC/Text', False, 'ARC test 1,172 (E16-1)')]
EPS = [.01, .02]
DELTA = .001
NMIN = {.01: 688, .02: 342}
# E21-2 nine deployed Qwen-receiver policies (E19 keys) and receivers of the E16-3 prefill
POL9 = ['medium/OBQA/C2C q=.55', 'medium/ARC/C2C', 'large/OBQA/Text', 'large/OBQA/C2C', 'large/ARC/Text', 'large/ARC/C2C',
        'large/MMLU-Pro/Text', 'large/MMLU-Pro/C2C', 'large/OBQA/Text+fact']
assert sorted(POL9) == sorted(QWEN9)
REC = {'medium': 'qwen3_1_7b', 'large': 'qwen3_8b'}
BENCH = {'OBQA': 'obqa', 'ARC': 'arc', 'MMLU-Pro': 'mmlu_pro'}


# ------------------------------------------------------------------ gold
_g = {}


def gold():
    """(dataset, id) -> gold label for fit/cal/dev of OBQA/ARC (V2 labels, pair large) and all MMLU-Pro test ids (gold_map)."""
    if 'main' in _g:
        return _g['main']
    G = {}
    for nm in ['full_train', 'full_development']:
        for r in jl(C.V2 / f'labels/{nm}_P2_SCORING_V2.jsonl'):
            if r['pair'] == 'large':
                G[(r['dataset'], r['id'])] = r['gold']
    import pyarrow as pa
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    GM = E9A.gold_map()
    for (ds, i), g in GM.items():
        if ds == 'mmlu_pro':
            G[(ds, i)] = g
        else:  # dev / validation gold from P2_10 must equal the V2 gold field
            assert G[(ds, i)] == g, (ds, i)
    _g['main'] = G
    return G


def gold_heldout():
    if 'ho' not in _g:
        import pyarrow.parquet as pq
        tb = pq.read_table(OBQA_TRAIN_PARQUET, columns=['id', 'answerKey'], use_threads=False)
        _g['ho'] = dict(zip(tb.column('id').to_pylist(), tb.column('answerKey').to_pylist()))
    return _g['ho']


def gold_arc_test():
    if 'arc' not in _g:
        _g['arc'] = {r['id']: r['gold'] for r in jl(SEALED / 'inputs/evaluation_gold_after_prediction_freeze.jsonl')}
    return _g['arc']


def setting_of(key):
    return POLD[key][0]


def split_arrays(key, sp):
    """cal or dev split of a setting with gold: dict(ids, u, oR, ob, d, y) (frozen V2 labels, INVALID-normalized)."""
    s = setting_of(key)
    L = E17.load(s)
    X = L[sp]
    ds = BENCH[s[1]]
    G = gold()
    y = np.array([G[(ds, i)] for i in X['ids']], object)
    return dict(ids=list(X['ids']), u=np.asarray(X['u'], float), oR=np.array(X['oR'], object), ob=np.array(X['ob'], object),
                d=np.asarray(X['d'], bool), y=y, cuts=L['cuts'])


# ------------------------------------------------------------------ out-of-sample populations (u, o_R, o_b, gold)
def oos(key):
    """-> dict(name, ids, u, oR (None where not executed), ob, y, frozen_omitted, R_available (bool array), source)."""
    if key in ('large/OBQA/Text', 'large/OBQA/Text+fact'):
        pol = {'large/OBQA/Text': 'large_obqa_T_q80', 'large/OBQA/Text+fact': 'large_obqa_TF_q75'}[key]
        f = E9 / 'analysis/SEALED_ROUTES.jsonl'
        rr = {r['id']: r for r in jl(f) if r['policy'] == pol}
        pop = [r['id'] for r in jl(E9 / 'inputs/holdout_744_queries.jsonl')]
        assert len(rr) == 744 == len(pop)
        H = gold_heldout()
        return dict(name='held-out OBQA 744', ids=pop, u=np.array([rr[i]['ProbeMax'] for i in pop], float),
                    oR=np.array([rr[i]['R_answer'] for i in pop], object), ob=np.array([rr[i]['reference_answer'] for i in pop], object),
                    y=np.array([H[i] for i in pop], object), frozen_omitted=np.array([rr[i]['omitted'] for i in pop], bool),
                    frozen_thr=rr[pop[0]]['threshold'], R_available=np.ones(744, bool), source=str(f))
    if key.startswith('Llama'):
        k = 'llama_obqa' if 'OBQA' in key else 'llama_arc'
        f = E16 / f'results/analysis_oos/routes_{k}.jsonl'
        R = jl(f)
        ids = [r['id'] for r in R]
        G = gold_heldout() if k == 'llama_obqa' else gold_arc_test()
        return dict(name='held-out OBQA 744 (E16-1)' if k == 'llama_obqa' else 'ARC test 1,172 (E16-1)', ids=ids,
                    u=np.array([r['u'] for r in R], float), oR=np.array([r['o_R'] for r in R], object),
                    ob=np.array([r['o_ref'] for r in R], object), y=np.array([G[i] for i in ids], object),
                    frozen_omitted=np.array([r['omitted'] for r in R], bool), frozen_thr=None, R_available=np.ones(len(R), bool),
                    source=str(f))
    if key == 'large/ARC/Text':
        S = E17.load_sealed('T')
        G = gold_arc_test()
        rows = S['rows']
        return dict(name='sealed ARC 1,172', ids=[r['id'] for r in rows], u=np.array([r['u'] for r in rows], float),
                    oR=np.array([r['oR_V2'] for r in rows], object), ob=np.array([r['oB_V2'] for r in rows], object),
                    y=np.array([G[r['id']] for r in rows], object), frozen_omitted=np.array([r['routed'] for r in rows], bool),
                    frozen_thr=S['threshold'], R_available=np.array([r['routed'] for r in rows], bool),
                    source=str(SEALED / 'records/e2e_requests.jsonl') + ' (e17_common.load_sealed)')
    return None


# ------------------------------------------------------------------ SQuAD control (E20F dev rows; score s2; change = e20_extract.changed)
def squad_dev():
    sys.path.insert(0, str(ROOT / 'P2_R8_E20P_20260921T224653Z' / 'src'))
    from e20_extract import changed
    f = E20F / 'results/E20F_devtest_rows.jsonl'
    hf = sorted(E20F.glob('results/OUTPUTS_HASH_devtest_j*.txt'))[-1]
    hh = {p: h for h, p in (ln.split('  ', 1) for ln in hf.read_text().splitlines() if ln and not ln.startswith('#'))}
    assert sha(f) == hh['results/E20F_devtest_rows.jsonl']
    rr = [r for r in jl(f) if r['split'] == 'dev']
    assert len(rr) == 1000 and all(r['llama'] is not None and r['helper'] is not None for r in rr)
    L = [r['llama'] for r in rr]
    oR, oT = [x['R']['answer'] for x in L], [x['T']['answer'] for x in L]
    return dict(ids=[r['id'] for r in rr], s2=np.array([x['R']['s2'] for x in L], float),
                d=np.array([changed(a, b) for a, b in zip(oR, oT)], bool), source=str(f))


# ------------------------------------------------------------------ E16-3 score m (verbatim functions)
def _e16_scores():
    src = (E16 / 'src/analyze_e16_3.py').read_text()
    ns = {'np': np}
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name in ('lse', 'scores'):
            exec(compile(ast.Module([node], []), str(E16 / 'src/analyze_e16_3.py'), 'exec'), ns)
    return ns['scores']


E16_SCORES = None


def m_records(receiver):
    """(dataset, id) -> bf16 E16-3 prefill record of `receiver` (manifest-verified)."""
    f = E16 / f"results/e163/{receiver}_bf16_{ {'qwen3_8b': 'q8b', 'qwen3_1_7b': 'q17b'}[receiver]}_bf16.jsonl"
    man = {}
    for line in (E16 / 'results/MANIFEST_jobB.sha256').read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            h, p = line.split(None, 1)
            man[p.strip()] = h
    rel = str(f.relative_to(E16 / 'results'))
    assert sha(f) == man[rel], rel
    out = {}
    for r in jl(f):
        if r.get('runtime_error') is None:
            out[(r['dataset'], r['id'])] = r
    return out, str(f)


def m_of(rec):
    global E16_SCORES
    if E16_SCORES is None:
        E16_SCORES = _e16_scores()
    return E16_SCORES(rec)[0]


# ------------------------------------------------------------------ small helpers
def p_eps(k, N, eps):
    return float(binom.cdf(k, N, eps))


def fmt(x, d=4):
    if x is None:
        return 'N/A'
    if isinstance(x, float):
        return 'n/a' if x != x else f'{x:.{d}f}'
    return str(x)
