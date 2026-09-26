"""E17-3: ARC split comparison (fit / cal / dev from the official train and validation splits; sealed test)."""
import numpy as np
from scipy.stats import fisher_exact, norm as N01
from e17_common import *

X = loadcache(); D, S = X['D'], X['S']
ARC10 = [('small', 'ARC', 'Text'), ('small', 'ARC', 'C2C'), ('medium', 'ARC', 'Text'), ('medium', 'ARC', 'C2C'),
         ('large', 'ARC', 'Text'), ('large', 'ARC', 'C2C'), ('X1-Llama', 'ARC', 'Text'), ('X1-Llama', 'ARC', 'C2C'),
         ('X2-OLMo', 'ARC', 'Text'), ('X3-Llama8B', 'ARC', 'Text')]
TEST = {('large', 'ARC', 'Text'): 'T', ('large', 'ARC', 'C2C'): 'C'}


def desc(s, sp, u, d, oR, ob, note=''):
    k, n = int(d.sum()), len(d); lo, hi = cp95(k, n)
    return dict(setting=sname(s), split=sp, N=n, disagreements=k, d=k / n, CP_lo=lo, CP_hi=hi,
                R_INVALID=sum(x == INV for x in oR), ref_INVALID=sum(x == INV for x in ob),
                median_u=float(np.median(u)), share_u0=float((np.asarray(u) == 0).mean()), note=note, label=LABEL)


def fisher(k1, n1, k2, n2):
    o, p = fisher_exact([[k1, n1 - k1], [k2, n2 - k2]], alternative='two-sided')
    return float(o), float(p)


rows, tests, pol = [], [], []
for s in ARC10:
    L = D[s]
    for sp in ['fit', 'cal', 'dev']:
        rows.append(desc(s, sp, L[sp]['u'], L[sp]['d'], L[sp]['oR'], L[sp]['ob']))
    kf, nf = int(L['fit']['d'].sum()), len(L['fit']['d'])
    kc, nc = int(L['cal']['d'].sum()), len(L['cal']['d'])
    kd, nd = int(L['dev']['d'].sum()), len(L['dev']['d'])
    t = dict(setting=sname(s), d_fit=kf / nf, d_cal=kc / nc, d_dev=kd / nd, d_cal_lt_d_dev=kc / nc < kd / nd)
    t['OR_cal_vs_dev'], t['fisher_p_cal_vs_dev'] = fisher(kc, nc, kd, nd)
    t['OR_fit_vs_cal'], t['fisher_p_fit_vs_cal'] = fisher(kf, nf, kc, nc)
    if s in TEST:
        b = TEST[s]; SR = S[b]['rows']
        u_all = np.array([x['u'] for x in SR], float)
        om = [x for x in SR if x['routed']]
        dt = np.array([x['oR_V2'] != x['oB_V2'] for x in om], bool)
        r = desc(s, 'test (sealed; R run only on omitted questions)', np.array([x['u'] for x in om]), dt,
                 [x['oR_V2'] for x in om], [x['oB_V2'] for x in om],
                 note=f'N = omitted questions of the sealed {s[2]} policy (u <= frozen tau); R was not executed on the other {len(SR) - len(om)}')
        r.update(test_all_N=len(SR), test_all_median_u=float(np.median(u_all)), test_all_share_u0=float((u_all == 0).mean()),
                 test_all_ref_INVALID=sum(x['oB_V2'] == INV for x in SR))
        rows.append(r)
        tau = S[b]['threshold']
        assert tau == C.tv(L['cuts'][GRID.index(S[b]['q'])])
        uf = np.concatenate([L['fit']['u'], L['cal']['u']]); dfc = np.concatenate([L['fit']['d'], L['cal']['d']])
        mm = uf <= tau
        k1, n1 = int(dfc[mm].sum()), int(mm.sum())
        t.update(train_matched_n=n1, train_matched_k=k1, test_n=len(dt), test_k=int(dt.sum()), d_test_matched=float(dt.mean()),
                 d_train_matched=k1 / n1)
        t['OR_train_vs_test_matched'], t['fisher_p_train_vs_test_matched'] = fisher(k1, n1, int(dt.sum()), len(dt))
        t['train_test_note'] = 'fit+cal restricted to u <= frozen tau, the region in which R was run on the test split'
    t['label'] = LABEL
    tests.append(t)

# Mantel-Haenszel common OR, dev vs cal (odds of disagreement in dev relative to cal), Robins-Breslow-Greenland CI
R_, S_, PR_, PS_QR, QS = [], [], [], [], []
for s in ARC10:
    L = D[s]
    a, b_ = int(L['dev']['d'].sum()), len(L['dev']['d']) - int(L['dev']['d'].sum())
    c, d_ = int(L['cal']['d'].sum()), len(L['cal']['d']) - int(L['cal']['d'].sum())
    n = a + b_ + c + d_
    Ri, Si, Pi, Qi = a * d_ / n, b_ * c / n, (a + d_) / n, (b_ + c) / n
    R_.append(Ri); S_.append(Si); PR_.append(Pi * Ri); PS_QR.append(Pi * Si + Qi * Ri); QS.append(Qi * Si)
sR, sS = sum(R_), sum(S_)
OR = sR / sS
var = sum(PR_) / (2 * sR ** 2) + sum(PS_QR) / (2 * sR * sS) + sum(QS) / (2 * sS ** 2)
z = N01.ppf(.975)
mh = dict(OR_MH_dev_vs_cal=OR, CI_lo=float(np.exp(np.log(OR) - z * np.sqrt(var))), CI_hi=float(np.exp(np.log(OR) + z * np.sqrt(var))),
          n_settings_d_cal_lt_d_dev=sum(t['d_cal_lt_d_dev'] for t in tests), n_settings=len(tests))


# permutation tests on per-question mean disagreement over the 10 settings
def xbar(split):
    acc = {}
    for s in ARC10:
        for i, d in zip(D[s][split]['ids'], D[s][split]['d']):
            acc.setdefault(i, []).append(int(d))
    return acc


def perm(sp_a, sp_b):
    """statistic = mean(x | sp_b) - mean(x | sp_a); two-sided, 10,000 permutations of the split labels, seed 0."""
    A, B = xbar(sp_a), xbar(sp_b)
    assert not (set(A) & set(B)), 'a question is in both splits'
    ids = list(A) + list(B)
    cnt = {len(v) for v in list(A.values()) + list(B.values())}
    x = np.array([np.mean(A[i]) for i in A] + [np.mean(B[i]) for i in B])
    lab = np.array([0] * len(A) + [1] * len(B))
    T = x[lab == 1].mean() - x[lab == 0].mean()
    rng = np.random.default_rng(0)
    Tb = np.empty(10000)
    for j in range(10000):
        pl = rng.permutation(lab)
        Tb[j] = x[pl == 1].mean() - x[pl == 0].mean()
    ge = int((np.abs(Tb) >= abs(T) - 1e-12).sum())
    return dict(contrast=f'{sp_b} - {sp_a}', n_a=len(A), n_b=len(B), settings_per_question=sorted(cnt),
                mean_x_a=float(x[lab == 0].mean()), mean_x_b=float(x[lab == 1].mean()), statistic=float(T),
                n_perm=10000, n_abs_ge=ge, p_two_sided=(ge + 1) / 10001, p_two_sided_plain=ge / 10000, label=LABEL)


P1 = perm('cal', 'dev'); P0 = perm('fit', 'cal')
syst = P1['p_two_sided'] < .05 and P1['mean_x_a'] < P1['mean_x_b']
rev = P1['p_two_sided'] < .05 and P1['mean_x_a'] > P1['mean_x_b']
P1['SYSTEMATIC'] = syst; P1['reverse_direction_significant'] = rev

# certified ARC policies: change rate at the frozen tau on cal, dev, test
for key, s, q in [('large/ARC/Text', ('large', 'ARC', 'Text'), .95), ('large/ARC/C2C', ('large', 'ARC', 'C2C'), .90),
                  ('medium/ARC/C2C', ('medium', 'ARC', 'C2C'), .60), ('Llama-3.1-8B/ARC/Text', X3SET[1], .70)]:
    L = D[s]; t = L['cuts'][GRID.index(q)]
    for sp in ['cal', 'dev']:
        m = mask(L[sp]['u'], q, t); n, k = int(m.sum()), int(L[sp]['d'][m].sum()); lo, hi = cp95(k, n)
        pol.append(dict(policy=key, q=q, split=sp, n=n, k=k, rate=k / n, CP_lo=lo, CP_hi=hi, label=LABEL))
    if s in TEST:
        om = [x for x in S[TEST[s]]['rows'] if x['routed']]
        k, n = sum(x['oR_V2'] != x['oB_V2'] for x in om), len(om); lo, hi = cp95(k, n)
        pol.append(dict(policy=key, q=q, split='test (sealed)', n=n, k=k, rate=k / n, CP_lo=lo, CP_hi=hi, label=LABEL))

csvout('E17_3_splits.csv', rows)
csvout('E17_3_tests.csv', tests)
csvout('E17_3_mh_permutation.csv', [dict(item='MH common OR (dev vs cal)', **mh, label=LABEL), dict(item='permutation cal vs dev', **P1),
                                     dict(item='permutation fit vs cal (control)', **P0)])
csvout('E17_3_certified_policies.csv', pol)
for r in rows: print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k not in ('label', 'note')})
for t in tests: print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in t.items() if k not in ('label', 'train_test_note')})
print(mh); print(P1); print(P0)
for p in pol: print(p)
