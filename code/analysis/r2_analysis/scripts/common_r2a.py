"""Shared helpers for P2_R2_ANALYSIS. Read-only on every existing P2_* folder; writes only under this stage.

Bootstrap is the frozen E3 rule (see P2_R1_E3POL_REPEAT1_20260919T075315Z/e3_build/e3_metrics.py and
.../large/src/analyze.py): 2,000 paired resamples of the panel questions, np.random.default_rng(0),
percentile 2.5/97.5.  Version (a) = all panel questions; version (b) = drop every question on which
either compared arm made its first formal request within the replay (each arm's minimum `attempt`).
"""
import csv, hashlib, json, pathlib
import numpy as np

ROOT = pathlib.Path('$DATA_DIR')
STAGE = pathlib.Path(__file__).resolve().parents[1]
RES = STAGE / 'results'
E7 = ROOT / 'P2_R2_E7_20260919T231531Z'
GPU = ROOT / 'P2_R2_GPU_20260919T220941Z'
CPU = ROOT / 'P2_R2_CPU_20260919T220412Z'
R1CPU = ROOT / 'P2_R1_CPU_20260919T045556Z'
EXP = ROOT / 'P2_R1_EXP_20260919T050555Z'
REVIEW = ROOT / 'P2_MMLU_PRO_BREADTH_PROTOCOL_AND_COST_REVIEW_20260915T224801Z'
LABEL = 'POST-HOC analysis of completed E6/E7 records; changes no frozen decision'
INV = 'INVALID'


def jl(p):
    with open(p) as f:
        return [json.loads(s) for s in f if s.strip()]


def read(p): return json.loads(pathlib.Path(p).read_text())


def sha(p):
    h = hashlib.sha256()
    with pathlib.Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def wcsv(name, rows):
    p = RES / name
    p.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(p, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return p


def bidx(n):
    """The frozen E3 bootstrap index block for a panel of n questions."""
    return np.random.default_rng(0).integers(0, n, size=(2000, n))


def ci(boot): return [float(x) for x in np.quantile(boot, [.025, .975])]


def cls(lo, hi): return '+' if lo > 0 else '-' if hi < 0 else '?'


def paired(d, idx):
    d = np.asarray(d, float)
    lo, hi = ci(d[idx].mean(axis=1))
    return dict(n=len(d), mean=float(d.mean()), lo=lo, hi=hi, median=float(np.median(d)), cls=cls(lo, hi))
