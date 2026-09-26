"""E13 (Round 5) CPU re-analysis. Read-only on every existing P2_* folder; writes only under this stage.

Items 1-2 reuse the E9-a samplers (P2_R3_E9A_20260920T043713Z/scripts/e9a_common.py) unchanged. XInst below is a
subclass whose *_x methods make exactly the same random-number calls in the same order as the E9-a methods, so the
same seed gives the same null draws; they additionally return, per draw, the change in the number of correct answers
of each null path relative to R (dN = correct(N) - correct(R)), which the best-fixed headroom needs.
"""
import sys
from pathlib import Path
import numpy as np

STAGE = Path(__file__).resolve().parents[1]
ROOT = STAGE.parent
RES = STAGE / 'results'
E9A = ROOT / 'P2_R3_E9A_20260920T043713Z'
sys.dont_write_bytecode = True
sys.path.insert(0, str(E9A / 'scripts'))
import e9a_common as E  # noqa: E402  (E.RES points at the E9-a folder: never written to)
from r2_common import csvout, jl, read  # noqa: E402

LABEL = 'POST-HOC re-analysis (reviewer R5/E13); does not change any primary decision'


def fmt(x, n=3):
    return E.fmt(x, n)


class XInst(E.Inst):
    """E9-a Inst plus per-draw correctness deltas of the null paths."""

    def __init__(self, *a):
        super().__init__(*a)
        self.cR = int(self.yR.sum())
        self.cT = int(self.yT.sum())
        self.cC = int(self.yC.sum())

    def _delta(self, cor, jj):
        # a changed slot contributes correct(draw) - correct(R) (a pool member never equals o_R)
        return cor.sum(axis=1) - self.yR[jj].sum(axis=1)

    def per_reference_x(self, rng, which, D):
        m = self.mT if which == 'T' else self.mC
        jj = self._pick(rng, m, D)
        if jj.shape[1] == 0:
            return np.zeros(D, int), np.zeros(D, int)
        cor, _, _ = self._one_draw(rng, jj)
        return (cor & self.need[jj]).sum(axis=1), self._delta(cor, jj)

    def independent_x(self, rng, D):
        add = np.zeros((D, self.M), bool)
        dN = []
        for m in (self.mT, self.mC):
            jj = self._pick(rng, m, D)
            if jj.shape[1] == 0:
                dN.append(np.zeros(D, int))
                continue
            cor, _, _ = self._one_draw(rng, jj)
            np.logical_or.at(add, (np.arange(D)[:, None], jj), cor)
            dN.append(self._delta(cor, jj))
        return (add & self.need).sum(axis=1), dN[0], dN[1]

    def joint_x(self, rng, D):
        """Same as E.Inst.joint; returns (gain, dN1, dN2, forced, K, a, b, c, cs, under_matched).
        N1 = V_T*: changed on the a Text-only and all c both-slots (draw i1).
        N2 = V_C*: changed on the b C2C-only slots (i1), the c_same both-slots (i1), the c - c_same slots (i2)."""
        a, b, c, cs = self.a, self.b, self.c, self.c_same
        K = a + b + c
        under = K > self.E
        if under:
            K2 = self.E
            raw = [a * K2 / K, b * K2 / K, c * K2 / K]
            fl = [int(np.floor(x)) for x in raw]
            for i in np.argsort([-(raw[i] - fl[i]) for i in range(3)])[:K2 - sum(fl)]:
                fl[i] += 1
            a, b, c = fl
            cs = min(cs, c) if c else 0
            K = K2
        jj = self._pick(rng, K, D)
        z = np.zeros(D, int)
        if K == 0:
            return z, z, z, z, 0, a, b, c, cs, under
        cor1, i1, sz = self._one_draw(rng, jj)
        flag = cor1.copy()
        yRj = self.yR[jj].astype(int)
        c1 = cor1.astype(int)
        lo = a + b + cs
        if K > lo:
            s = sz[:, lo:]
            i2 = (i1[:, lo:] + 1 + (rng.random((jj.shape[0], K - lo)) * np.maximum(s - 1, 0)).astype(int)) % np.maximum(s, 1)
            cor2 = self.pcor[jj[:, lo:], i2]
            flag[:, lo:] |= cor2
            forced = (s == 1).sum(axis=1)
            d2_tail = cor2.astype(int).sum(axis=1) - yRj[:, lo:].sum(axis=1)
        else:
            forced = np.zeros(jj.shape[0], int)
            d2_tail = np.zeros(jj.shape[0], int)
        d = c1 - yRj
        dN1 = d[:, :a].sum(axis=1) + d[:, a + b:].sum(axis=1)
        dN2 = d[:, a:lo].sum(axis=1) + d2_tail
        return (flag & self.need[jj]).sum(axis=1), dN1, dN2, forced, K, a, b, c, cs, under


def xview(P, idx=None):
    if idx is None:
        idx = np.arange(P.N)
    return XInst(P.yR[idx], P.yT[idx], P.yC[idx], P.chT[idx], P.chC[idx], P.same_TC[idx], P.psize[idx], P.pcor[idx])


def h_best_fixed_2(cR, gain, dN1, dN2):
    """oracle{R,N1,N2} - max{correct(R), correct(N1), correct(N2)} = gain - max(0, dN1, dN2)."""
    return gain - np.maximum(0, np.maximum(dN1, dN2))


def h_best_fixed_1(cR, gain, dN):
    return gain - np.maximum(0, dN)


def real_h(v):
    """Real best-fixed headroom (joint/independent: {R,Text,C2C}; per-reference: {R,b})."""
    orc = v.cR + v.real_TC
    return dict(TC=orc - max(v.cR, v.cT, v.cC),
                T=v.cR + v.real_T - max(v.cR, v.cT),
                C=v.cR + v.real_C - max(v.cR, v.cC))
