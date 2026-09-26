"""E22 (Round 10) CPU re-analysis of stored development outputs.

Read-only on every existing P2_* folder; writes only under this stage.

Everything is reused unchanged:
  * loaders and samplers: P2_R3_E9A_20260920T043713Z/scripts/e9a_common.py (E9-a), which imports the E5-c loaders
    (P2_R2_CPU_20260919T220412Z/scripts/r2_common.py -> P2_R1_CPU_20260919T045556Z/src/{common_r1,data_r1}.py);
  * the stratification idea and stream convention: P2_R5_E13_20260921T031606Z/scripts/item2.py (Item 2).
The only new code is `strat_perref` (E9-a's Inst.per_reference run inside each stratum with that stratum's own
n_s(b) and eligible set) and the E22-2 counting in e22_2.py.
"""
import sys
from pathlib import Path
import numpy as np
from scipy.stats import beta

STAGE = Path(__file__).resolve().parents[1]
ROOT = STAGE.parent
RES = STAGE / 'results'
E9A = ROOT / 'P2_R3_E9A_20260920T043713Z'
E13 = ROOT / 'P2_R5_E13_20260921T031606Z'
E5 = ROOT / 'P2_R2_CPU_20260919T220412Z'
EXPDIR = ROOT / 'P2_R1_EXP_20260919T050555Z'
sys.dont_write_bytecode = True
sys.path.insert(0, str(E9A / 'scripts'))
import e9a_common as E  # noqa: E402  (E.RES points at the E9-a folder and is never written to)
from r2_common import csvout, jl, read, csvread, INV, load_main  # noqa: E402

LABEL = ('POST HOC (E22, PREREG.md); stored outputs only; does not change any primary decision')
# E9-a's seed, stored in its scripts: numpy.random.default_rng(0) in e9a_main.py and e9a_boot.py.
SEED = 0
NREP = E.NREP            # 1,000 null draws
NBOOT = E.NBOOT          # 2,000 bootstrap resamples of questions
NBOOT_NULL = E.NBOOT_NULL  # 100 null draws inside each resample
POPNAME = E.POPNAME
# the five medium/large C2C cells of PREREG E22-1 (populations 3..7 in the E9-a order)
MEDLARGE = [2, 3, 4, 5, 6]
REFNAME = {'T': 'Text', 'C': 'C2C'}


def fmt(x, n=3):
    return E.fmt(x, n)


def cp95(k, n):
    """Two-sided 95% Clopper-Pearson (verbatim from P2_R7_E17_20260921T183100Z/scripts/e17_common.py)."""
    if n == 0:
        return (float('nan'), float('nan'))
    return (0.0 if k == 0 else float(beta.ppf(.025, k, n - k + 1)),
            1.0 if k == n else float(beta.ppf(.975, k + 1, n - k)))


def strata(P, idx):
    """S- = o_R != gold (INVALID counts as wrong), S+ = o_R = gold.  Drawn in this order (E13 Item 2 convention)."""
    yR = P.yR[idx]
    return [('S_minus', idx[~yR]), ('S_plus', idx[yR])]


def strat_perref(P, idx, rng, which, D):
    """E9-a's Inst.per_reference run inside each stratum with that stratum's own n_s(b) and eligible set;
    the two strata are pooled into one null action.  Returns (gain, {stratum: meta})."""
    g = np.zeros(D, int)
    meta = {}
    for name, sub in strata(P, idx):
        v = P.view(sub)
        n_s = v.mT if which == 'T' else v.mC
        gs = v.per_reference(rng, which, D)
        g = g + gs
        meta[name] = dict(n=len(sub), n_changed=n_s, elig=v.E, drawn=min(n_s, v.E),
                          under=n_s > v.E, inst=v, gain=gs)
    return g, meta


def g_minus(v):
    """mean over the eligible questions of |P(x) & {gold}| / |P(x)|  (v = the S- instance)."""
    if v.E == 0:
        return float('nan')
    j = v.elig
    return float((v.pcor[j].sum(axis=1) / v.psize[j]).mean())


def load_raw():
    """E9-a's seven Pop objects plus the raw development answer lists the E22-2 counting needs.
    Sources and parsing are identical to e9a_common.Pop (= E5-c e5c.py): V1/V2 are the E4 null controls with V1
    mapped back to the original option order, and INVALID is a symbol that never equals gold."""
    GOLD, NULL, main = E.gold_map(), E.null_answers(), load_main()
    out = []
    for pair, ds in E.POPS:
        P = E.Pop(pair, ds, main, GOLD, NULL)
        D = main[pair, E.TASKNAME[ds]]['dev']
        raw = dict(gold=[GOLD[ds, i] for i in P.ids],
                   R=list(D['ans']['R']), Text=list(D['ans']['T']), C2C=list(D['ans']['C']),
                   V1=[NULL[pair, ds, 'V1'].get(i, INV) for i in P.ids],
                   V2=[NULL[pair, ds, 'V2'].get(i, INV) for i in P.ids])
        out.append((P, raw, main[pair, E.TASKNAME[ds]]))
    return out
