"""E13: fit / cal / dev arrays for all 26 settings, reusing the E11 loader (P2_R4_E11_20260920T224016Z/scripts/e11_common.py)
unchanged for cal/dev and adding the fit split from the same sources (Text+fact has no fit-split reference outputs)."""
import sys
from pathlib import Path
import numpy as np

STAGE = Path(__file__).resolve().parents[1]
ROOT = STAGE.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'P2_R4_E11_20260920T224016Z' / 'scripts'))
import e11_common as C  # noqa: E402

ALL26 = C.ALL26
FACT = C.FACT


def load_fit(s):
    """-> dict(ids, u, oR, ob) on the fit split (frozen representatives), or None for Text+fact."""
    pair, task, ref = s
    ds = C.BENCH[task]
    if s == FACT:
        return None
    if s in C.SETTINGS:
        D = C.load_main()[pair, task]['fit']
        return dict(ids=D['ids'], u=np.asarray(D['scores']['ProbeMax'], float), oR=list(D['ans']['R']),
                    ob=list(D['ans'][C.CODE[ref]]))
    if s in C.E8SET:
        rec = C._e8(pair)
        ids = [g['representative_id'] for g in C.read(C.E8 / 'splits/fit_groups.json')]
        return dict(ids=ids, u=np.array([rec[i]['u'] for i in ids], float), oR=[rec[i]['R'] for i in ids],
                    ob=[rec[i][C.CODE[ref]] for i in ids])
    if pair == 'X2-OLMo':
        D = C.load_x2()[ds]['fit']
        return dict(ids=D['ids'], u=np.asarray(D['u'], float), oR=list(D['oR']), ob=list(D['oT']))
    D = C.load_x1()[ds]['fit']
    return dict(ids=D['ids'], u=np.asarray(D['u'], float), oR=list(D['oR']), ob=list(D['oT' if ref == 'Text' else 'oC']))


def dis(split):
    return np.array([a != b for a, b in zip(split['oR'], split['ob'])], bool)
