"""E22-2: direction of the changes (descriptive, no randomness).

For every development population and every action A in {Text, C2C, V1, V2}, using the frozen V2 parser conventions
(INVALID is a label; two INVALIDs agree; exactly one INVALID is a change; INVALID never equals gold):
  * changes on S- (o_A != o_R while o_R is wrong), split into wrong->right (o_A = gold) and wrong->wrong, with a
    two-sided 95% Clopper-Pearson interval on the wrong->right share;
  * changes on S+ (right->wrong);
  * how many of the S- and S+ changes have o_A = INVALID;
  * g_- of the null (E22-1's definition), which depends only on P(x) and gold, so it is one number per population.
The large/OBQA counts must reproduce E5 / the paper (Text 46/18, C2C 16/35, V1 48/66), else the item stops.
"""
import sys
import numpy as np
from e22_common import *
import e22_common as C

ACTIONS = ['Text', 'C2C', 'V1', 'V2']
E5REF = {('large/OBQA', 'Text'): (46, 18), ('large/OBQA', 'C2C'): (16, 35), ('large/OBQA', 'V1'): (48, 66)}
DEC = {(r['population'], r['action']): r for r in csvread(E5 / 'results' / 'e5c_change_decomposition.csv')}


def main():
    raw = load_raw()
    rows, checks = [], []
    stop = False
    for (P, Rw, _), nm in zip(raw, POPNAME):
        yR = P.yR
        gmv = g_minus(P.view(np.flatnonzero(~yR)))
        for a in ACTIONS:
            oA = Rw[a]
            ch = np.array([x != y for x, y in zip(oA, Rw['R'])], bool)
            yA = np.array([x == y for x, y in zip(oA, Rw['gold'])], bool)
            inv = np.array([x == INV for x in oA], bool)
            m_minus = ch & ~yR
            w2r = int((m_minus & yA).sum()); w2w = int((m_minus & ~yA).sum())
            r2w = int((ch & yR).sum())
            lo, hi = cp95(w2r, w2r + w2w)
            rows.append(dict(population=nm, N=P.N, action=a,
                             n_S_minus=int((~yR).sum()), n_S_plus=int(yR.sum()),
                             changes_S_minus=w2r + w2w, wrong_to_right=w2r, wrong_to_wrong=w2w,
                             wrong_to_right_share=fmt(w2r / (w2r + w2w)) if (w2r + w2w) else 'nan',
                             share_CP95_lo=fmt(lo), share_CP95_hi=fmt(hi),
                             changes_S_plus_right_to_wrong=r2w,
                             INVALID_among_S_minus_changes=int((m_minus & inv).sum()),
                             INVALID_among_S_plus_changes=int((ch & yR & inv).sum()),
                             null_g_minus=fmt(gmv), label=LABEL))
            # reproduction of E5 / the paper
            ok_c = str(w2r) == DEC[nm, a]['corrective'] and str(w2w) == DEC[nm, a]['neutral_both_wrong'] \
                and str(r2w) == DEC[nm, a]['harmful']
            checks.append(dict(population=nm, action=a, check='E5 e5c_change_decomposition',
                               expected=f"{DEC[nm, a]['corrective']}/{DEC[nm, a]['neutral_both_wrong']}/"
                                        f"{DEC[nm, a]['harmful']}",
                               obtained=f'{w2r}/{w2w}/{r2w}', pass_=str(ok_c), label=LABEL))
            stop |= not ok_c
            if (nm, a) in E5REF:
                e = E5REF[nm, a]; ok_p = (w2r, r2w) == e
                checks.append(dict(population=nm, action=a, check='paper large/OBQA direction counts',
                                   expected=f'{e[0]} wrong->right / {e[1]} right->wrong',
                                   obtained=f'{w2r} wrong->right / {r2w} right->wrong', pass_=str(ok_p), label=LABEL))
                stop |= not ok_p
        print(f'{nm:16s} g- {fmt(gmv)} | ' + ' | '.join(
            f"{r['action']} {r['wrong_to_right']}/{r['wrong_to_wrong']} "
            f"({r['wrong_to_right_share']}) R->W {r['changes_S_plus_right_to_wrong']} "
            f"INV {r['INVALID_among_S_minus_changes']}/{r['INVALID_among_S_plus_changes']}"
            for r in rows[-4:]), flush=True)
    csvout(RES / 'E22_2_directions.csv', rows)
    csvout(RES / 'E22_2_checks.csv', checks)
    print(f'{sum(c["pass_"] == "True" for c in checks)}/{len(checks)} reproduction checks pass')
    if stop:
        print('STOP: E22-2 does not reproduce E5 / the paper; see E22_2_checks.csv')
        sys.exit(2)


if __name__ == '__main__':
    main()
