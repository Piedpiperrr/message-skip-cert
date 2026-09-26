"""E13 Item 8: AUROC tie handling. Explicit pairwise Mann-Whitney statistic (tied positive-negative pairs credit 1/2)
vs the function used in the paper (sklearn.metrics.roc_auc_score), for large/ARC/Text and medium/ARC/C2C (required) and,
as a check, every one of the 26 settings. Also the share of positive-negative pairs with tied scores."""
import numpy as np
from e13_settings import *
from e13_common import csvout, RES, LABEL
from sklearn.metrics import roc_auc_score

INVENTORY = [
    ('14 main settings (small/medium/large x OBQA/ARC, large MMLU-Pro)', 'sklearn.metrics.roc_auc_score',
     'P2_CONFIDENCE_REFERENCE_BOUNDARIES/src/analyze.py rank(); P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1/execution_retry1/src/analyze.py rank(); '
     'P2_MMLU_PRO_BREADTH_STAGE1/src/analyze.py; reproduced by P2_R1_CPU/src/item3.py'),
    ('4 small/medium MMLU-Pro (E8)', 'sklearn.metrics.roc_auc_score', 'P2_R2_E8/src/analyze_e8.py metrics()'),
    ('7 cross-family (X1 Llama, X2 OLMo)', 'sklearn.metrics.roc_auc_score', 'P2_R1_XFAM/src/analyze_x2.py; x1/src/analyze_x1.py'),
    ('large/OBQA/Text+fact (E6)', 'hand-written Mann-Whitney with mid-ranks', 'P2_R2_GPU/src/e6_analyze.py auroc()'),
    ('GSM8K (E10), u / s2 / s3', 'hand-written Mann-Whitney with mid-ranks', 'P2_R4_E10/src/e10_seal.py auroc()'),
    ('helper-aware s_G (E9c)', 'hand-written Mann-Whitney with mid-ranks', 'P2_R3_E9BC/src/e9c_analyze.py auroc()'),
]
TIE_RULE = ('sklearn.roc_auc_score builds the ROC curve with one point per distinct score value (tied scores move together) '
            'and integrates it with the trapezoidal rule, which equals the Mann-Whitney U / (n1 n0) with each tied '
            'positive-negative pair credited 1/2; the mid-rank functions give the same statistic by construction.')


def mw(d, u):
    d = np.asarray(d, bool); u = np.asarray(u, float)
    pos, neg = u[d], u[~d]
    gt = (pos[:, None] > neg[None, :]).sum(); eq = (pos[:, None] == neg[None, :]).sum()
    n = len(pos) * len(neg)
    return (gt + .5 * eq) / n, eq / n, gt / n, (gt + eq) / n


rows = []
for s in ALL26:
    L = C.load(s)
    dv = L['dev']; d = dis(dv); u = np.asarray(dv['u'], float)
    sk = float(roc_auc_score(d, u))
    a, tie, strict, lenient = mw(d, u)
    rows.append(dict(setting=C.sname(s), required=C.sname(s) in ('large/ARC/Text', 'medium/ARC/C2C'), dev_N=len(d), dev_disagreements=int(d.sum()),
                     AUROC_sklearn=sk, AUROC_explicit_MW_ties_half=a, abs_diff=abs(sk - a), share_tied_pos_neg_pairs=tie,
                     AUROC_ties_credit_0=strict, AUROC_ties_credit_1=lenient, label=LABEL))
    print(f"{rows[-1]['setting']:24s} sklearn={sk:.6f} MW={a:.6f} diff={abs(sk - a):.2e} tied={tie:.4f} [ties0 {strict:.4f}, ties1 {lenient:.4f}]")
csvout(RES / 'item8_auroc_ties.csv', rows)
csvout(RES / 'item8_auroc_inventory.csv', [dict(settings=a, function=b, source=c, tie_rule=TIE_RULE, label=LABEL) for a, b, c in INVENTORY])
print('max abs diff over 26 settings:', max(r['abs_diff'] for r in rows))
