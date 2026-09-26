"""E21-1 evaluation (PREREG.md), run only after CERT.json is written and hashed (CERT.sha256 verified here).
For each setting x eps with q_joint != NONE, the policy pi omits iff u <= tau_joint (route_mask), and the frozen policy for comparison:
dev: coverage, L / W counts, change rate among omitted [two-sided 95% CP], dAcc = acc(pi) - acc(b) [paired bootstrap over questions,
default_rng(0).integers(0, N, (2000, N)), percentiles 2.5/97.5], G_dev (points), retention (acc(pi)-acc(R))/(acc(b)-acc(R)).
out of sample (descriptive): N_test, coverage, k_L, k_L/N_test [CP95], CP upper < eps, W, dAcc [bootstrap, same scheme], retention where
acc(R) is available (not on sealed ARC). panel: E19-1 recomposition (omitted at the frozen tau per the logged route but u > tau_joint ->
saving_i = -probe_i, the request's logged probe stage time; otherwise fixed_i - policy_i), mean with the E19 bootstrap; and the frozen saving.
Writing rule (a)/(b)/(c) evaluated as written."""
from e21_common import *
from fractions import Fraction

T0 = utc()
hcert = (STAGE21 / 'CERT.sha256').read_text().split()
assert sha(STAGE21 / 'CERT.json') == hcert[0], 'CERT.json changed after hashing'
CERT = read(STAGE21 / 'CERT.json')
print('E21-1 eval start', T0, 'CERT', hcert[0], 'hashed', hcert[-1], flush=True)


def evaluate(oR, ob, y, m, R_avail=None):
    N = len(y)
    if R_avail is not None:
        assert R_avail[m].all()
    pol = np.where(m, oR, ob)
    yR = np.array([a == b for a, b in zip(oR, y)], bool) if (R_avail is None or R_avail.all()) else None
    yb = ob == y
    yp = pol == y
    L = m & yb & np.array([a != b for a, b in zip(oR, y)], bool)
    W = m & np.array([a == b for a, b in zip(oR, y)], bool) & ~yb
    n = int(m.sum())
    k = int(np.array([a != b for a, b in zip(oR[m], ob[m])], bool).sum())
    lo, hi = cp95(k, n)
    idx = bidx(N)
    dl = (yp.astype(float) - yb.astype(float))
    dlo, dhi = ci(dl[idx].mean(axis=1))
    kL = int(L.sum())
    Llo, Lhi = cp95(kL, N)
    out = dict(N=N, omitted=n, coverage=n / N, k_L=kL, k_L_over_N=kL / N, k_L_CP95_lo=Llo, k_L_CP95_hi=Lhi, k_W=int(W.sum()),
               changed=k, change_rate=(k / n if n else float('nan')), change_CP95_lo=lo, change_CP95_hi=hi,
               correct_b=int(yb.sum()), correct_policy=int(yp.sum()), dAcc=float(dl.mean()), dAcc_CI95_lo=dlo, dAcc_CI95_hi=dhi)
    if yR is not None:
        cR, cb, cp = int(yR.sum()), int(yb.sum()), int(yp.sum())
        out.update(correct_R=cR, G_pts=100 * (cb - cR) / N, G_frac=Fraction(cb - cR, N),
                   retention=((cp - cR) / (cb - cR) if cb != cR else float('nan')))
    else:
        out.update(correct_R='not stored (R executed only where the frozen policy omitted)', G_pts=None, G_frac=None, retention='N/A')
    return out


def panel(key, tau_j):
    R = replay(key)
    ids = R['ids']
    fixed = np.array([R['fx'][i]['latency_ms'] for i in ids])
    polv = np.array([R['po'][i]['latency_ms'] for i in ids])
    u = np.array([u_of(R['po'][i]) for i in ids], float)
    om = np.array([route_R(R['po'][i]) for i in ids], bool)
    pr = np.array([probe_ms(R['po'][i]) for i in ids])
    tau_f = dev(key)['tau']
    assert int((om != (u <= tau_f)).sum()) == 0
    s = fixed - polv
    re = om & ~(u <= C.tv(tau_j))
    s2 = np.where(re, -pr, s)
    idx = bidx(len(ids))
    return dict(panel_N=len(ids), panel_omitted_frozen=int(om.sum()), panel_omitted_joint=int((om & ~re).sum()), panel_rerouted=int(re.sum()),
                frozen_saving_ms=float(s.mean()), frozen_CI95=ci(s[idx].mean(axis=1)),
                joint_saving_ms=float(s2.mean()), joint_CI95=ci(s2[idx].mean(axis=1)), panel_source=R['source'], panel_config=R['config'],
                probe_source='logged per request (' + ('parts_ms.probe_ms' if 'probe_ms' in R['po'][ids[0]]['parts_ms'] else 'parts_ms.online_probe_ms') + ')')


ROWS, OOSROWS, PANROWS = [], [], []
RES_ALL = {}
for name, key, nominal, oosname in SET6:
    S = CERT['settings'][name]
    qf, tau_f = S['q_frozen'], S['tau_frozen']
    Xd = split_arrays(key, 'dev')
    Dk = dev(key)
    assert Xd['ids'] == Dk['ids'] and (E17.mask(Xd['u'], qf, tau_f) == Dk['m']).all()
    O = oos(key)
    frozen_dev = evaluate(Xd['oR'], Xd['ob'], Xd['y'], Dk['m'])
    frozen_oos = evaluate(O['oR'], O['ob'], O['y'], E17.mask(O['u'], qf, tau_f), O['R_available']) if O else None
    if O:
        assert (E17.mask(O['u'], qf, tau_f) == O['frozen_omitted']).all()
    for e in EPS:
        c = S[f'eps{e}']
        base = dict(setting=name, nominal=nominal, eps=e, N_cal=S['N'], N_min=c['N_min'], cal_status=c['status'], q_frozen=qf,
                    q_L=c['q_L'] if c['q_L'] is not None else 'NONE', q_joint=c['q_joint'] if c['q_joint'] is not None else 'NONE',
                    tau_joint=c['tau_joint'], D_all=S['D_all'], D_seq=c['D_seq'], D_dep=c['D_dep'] if c['D_dep'] is not None else 'N/A',
                    D_need=c['D_need'], CX_q_joint=S['C_minus_X'][f'eps{e}']['q_joint'] if S['C_minus_X'][f'eps{e}']['q_joint'] is not None else 'NONE')
        rec = dict(base=base)
        for tag, ev in [('frozen', frozen_dev)] + ([('joint', evaluate(Xd['oR'], Xd['ob'], Xd['y'], E17.mask(Xd['u'], c['q_joint'], c['tau_joint'])))]
                                                   if c['q_joint'] is not None else []):
            ROWS.append(dict(**base, policy=tag, q_policy=(qf if tag == 'frozen' else c['q_joint']),
                             **{k: v for k, v in ev.items() if k != 'G_frac'}, label=LABEL))
            rec[f'dev_{tag}'] = ev
        if c['q_joint'] is None:
            ROWS.append(dict(**base, policy='joint', q_policy='NONE', note='q_joint = NONE -> N/A', label=LABEL))
        # out of sample
        if O is None:
            OOSROWS.append(dict(**base, population='none (MMLU-Pro: no unused data)', policy='joint', note='N/A', label=LABEL))
        else:
            for tag, ev in [('frozen', frozen_oos)] + ([('joint', evaluate(O['oR'], O['ob'], O['y'], E17.mask(O['u'], c['q_joint'], c['tau_joint']),
                                                                          O['R_available']))] if c['q_joint'] is not None else []):
                OOSROWS.append(dict(**base, population=O['name'], policy=tag, q_policy=(qf if tag == 'frozen' else c['q_joint']),
                                    **{k: v for k, v in ev.items() if k != 'G_frac'}, CP_upper_lt_eps=bool(ev['k_L_CP95_hi'] < e),
                                    kL_rate_gt_eps=bool(ev['k_L_over_N'] > e), source=O['source'], label=LABEL))
                rec[f'oos_{tag}'] = ev
            if c['q_joint'] is None:
                OOSROWS.append(dict(**base, population=O['name'], policy='joint', q_policy='NONE', note='q_joint = NONE -> N/A', label=LABEL))
        # panel
        if c['q_joint'] is not None:
            P = panel(key, c['tau_joint'])
            if c['q_joint'] == qf:
                assert P['panel_rerouted'] == 0 and P['joint_saving_ms'] == P['frozen_saving_ms']
            rec['panel'] = P
            PANROWS.append(dict(**base, **{k: v for k, v in P.items() if not k.endswith('CI95')},
                                joint_CI95_lo=P['joint_CI95'][0], joint_CI95_hi=P['joint_CI95'][1],
                                frozen_CI95_lo=P['frozen_CI95'][0], frozen_CI95_hi=P['frozen_CI95'][1],
                                recomposed_label='recomposed (not a replay): omitted at frozen tau but u > tau_joint -> policy_i = fixed_i + probe_i',
                                label=LABEL))
        else:
            PANROWS.append(dict(**base, note='q_joint = NONE -> N/A', label=LABEL))
        RES_ALL[name, e] = rec
        dj = rec.get('dev_joint')
        print(f"{name:24s} eps={e} q_joint={base['q_joint']} " + (
            f"dev cov {dj['coverage']:.4f} L/W {dj['k_L']}/{dj['k_W']} chg {dj['changed']}/{dj['omitted']} dAcc {dj['dAcc']:+.4f} "
            f"[{dj['dAcc_CI95_lo']:+.4f},{dj['dAcc_CI95_hi']:+.4f}] G {dj['G_pts']:.3f} ret {dj['retention']:.3f}" if dj else 'N/A'), flush=True)

# ------------------------------------------------------------------ writing rule
def counted(name, e):
    rec = RES_ALL[name, e]
    dj = rec.get('dev_joint')
    if dj is None:
        return False, 'no joint certificate'
    cov_ok = dj['coverage'] >= .20
    gain_ok = 2 * Fraction(str(e)) <= dj['G_frac']          # eps <= G_dev / 2 (G as a fraction of N)
    return (cov_ok and gain_ok), f"cov {dj['coverage']:.4f} (>= .20: {cov_ok}); G_dev {dj['G_pts']:.3f} pts (eps <= G/2: {gain_ok})"


RULE = dict(label=LABEL)
detail = []
for name, *_ in SET6:
    for e in EPS:
        ok, why = counted(name, e)
        detail.append(dict(setting=name, eps=e, counted=ok, why=why))
RULE['counted_detail'] = detail


def sentence(e, words):
    A = [d['setting'] for d in detail if d['eps'] == e and d['counted']]
    recs = [RES_ALL[a, e] for a in A]
    Dn = [r['base']['D_need'] for r in recs]
    cov = [100 * r['dev_joint']['coverage'] for r in recs]
    ret = [100 * r['dev_joint']['retention'] for r in recs]
    B = sum(a in ('large/OBQA/Text', 'large/OBQA/Text+fact') for a in A)
    over = []
    for a, r in zip(A, recs):
        if r['dev_joint']['k_L_over_N'] > e:
            over.append(f"{a} (dev k_L/N = {r['dev_joint']['k_L']}/{r['dev_joint']['N']} = {r['dev_joint']['k_L_over_N']:.4f})")
        if 'oos_joint' in r and r['oos_joint']['k_L_over_N'] > e:
            over.append(f"{a} (out-of-sample k_L/N = {r['oos_joint']['k_L']}/{r['oos_joint']['N']} = {r['oos_joint']['k_L_over_N']:.4f})")
    K = f"{min(Dn)}" if min(Dn) == max(Dn) else f"{min(Dn)}-{max(Dn)}"
    s = (f"With gold labels on at most {K} calibration questions (the lowest-uncertainty receiver-reference disagreements), the same test also "
         f"certifies, at a threshold no higher than the deployed one, an accuracy loss of at most {words} for {len(A)} of the six helpful Text "
         f"paths ({B} of them nominal), at {min(cov):.1f}-{max(cov):.1f}% development coverage, retaining {min(ret):.1f}-{max(ret):.1f}% of the gain"
         + (f" ({'; '.join(over)} exceed eps)" if over else '') + " (App. X).")
    return dict(A=A, A_n=len(A), B=B, K=K, D_need=Dn, coverage_pct=cov, retention_pct=ret, exceed_eps=over, sentence=s)


A01 = [d for d in detail if d['eps'] == .01 and d['counted']]
A02 = [d for d in detail if d['eps'] == .02 and d['counted']]
if A01:
    RULE.update(branch='(a)', **sentence(.01, 'one point'))
elif A02:
    RULE.update(branch='(b)', **sentence(.02, 'two points'))
    RULE['sentence'] += ' Settings: ' + ', '.join(RULE['A']) + '; none at one point.'
else:
    RULE.update(branch='(c)', sentence='Labels on the omitted disagreements suffice for a direct test of the accuracy loss, but at our calibration '
                                        'sizes it certifies no helpful policy at >= 20% coverage with a loss bound (one or two points) at most half its gain (App. X).')
RULE['infeasible'] = [f"{n} (N = {CERT['settings'][n]['N']}) at eps = {e}" for n, *_ in SET6 for e in EPS if not CERT['settings'][n][f'eps{e}']['feasible']]
RULE['oos_CP_upper_ge_eps'] = [f"{r['setting']} eps={r['eps']} {r['population']}: k_L/N = {r['k_L']}/{r['N']} CP95 upper {r['k_L_CP95_hi']:.4f}"
                               for r in OOSROWS if r.get('policy') == 'joint' and 'k_L_CP95_hi' in r and not r['CP_upper_lt_eps']]
print(json.dumps({k: v for k, v in RULE.items() if k != 'counted_detail'}, indent=1, default=str))
for d in detail:
    print(d)
csvout('E21_1_dev.csv', ROWS)
csvout('E21_1_oos.csv', OOSROWS)
csvout('E21_1_panel.csv', PANROWS)
jdump(RES / 'E21_1_writing_rule.json', RULE)
run_log('e21_1_eval.py', T0, dict(cert_sha256=hcert[0]))
print('E21-1 eval done', utc())
