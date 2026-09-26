"""E21-1 calibration stage (PREREG.md). For each of the six helpful Text settings, on the whole calibration set C:
frozen change-rate test (E17.ledger, must reproduce the frozen q), and per candidate tau_j (20 frozen fit-quantile thresholds, omit iff
u <= tau_j via route_mask) the lost-correction count k_L, gained count k_W, p_eps = P[Bin(N, eps) <= k_L], accept iff p <= .001, for
eps = .01 and .02. q_L, q_joint (accepted by both), D_all / D_seq / D_dep / D_need, feasibility, and the C \\ X check. Writes CERT.json
and CERT.sha256 (hash + UTC). No dev / out-of-sample / panel quantity is computed here."""
from e21_common import *
import math

T0 = utc()
print('E21-1 cert start (first E21 statistic)', T0, flush=True)
PREREG_SHA = sha(STAGE21 / 'PREREG.md')
assert PREREG_SHA == (STAGE21 / 'PREREG.sha256').read_text().split()[0]
assert not (STAGE21 / 'CERT.json').exists(), 'CERT.json exists'
for e in EPS:
    assert NMIN[e] == math.ceil(math.log(DELTA) / math.log(1 - e)) and (1 - e) ** NMIN[e] <= DELTA < (1 - e) ** (NMIN[e] - 1)
_, _, XSET, _, _, _ = C.exposed_ids()


def certify(u, oR, ob, y, d, cuts, q_frozen):
    N = len(u)
    led = E17.ledger(u, d, cuts)
    q_chg, _ = E17.deployed(led)
    cands, prev_kL, masks = [], -1, []
    for r in led:
        m = E17.mask(u, r['q'], r['threshold'])
        masks.append(m)
        L = m & (ob == y) & (oR != y)
        W = m & (oR == y) & (ob != y)
        kL, kW = int(L.sum()), int(W.sum())
        assert kL >= prev_kL
        prev_kL = kL
        c = dict(q=r['q'], tau=r['threshold'], n_omitted=r['n'], k_changed=r['k'], p_change=r['p'], accepted_change=bool(r['accepted']),
                 k_L=kL, k_W=kW, D_in_mask=int(d[m].sum()))
        for e in EPS:
            p = p_eps(kL, N, e)
            c[f'p_eps{e}'] = p
            c[f'accepted_L_eps{e}'] = bool(p <= DELTA)
            c[f'accepted_joint_eps{e}'] = bool(p <= DELTA and r['accepted'])
        cands.append(c)
    jf = GRID.index(q_frozen)
    out = dict(N=N, q_change_test=q_chg, D_all=int(d.sum()), candidates=cands)
    for e in EPS:
        acc = [c[f'accepted_L_eps{e}'] for c in cands]
        first_rej = next((j for j, a in enumerate(acc) if not a), None)
        assert all(acc[:first_rej]) and not any(acc[first_rej:]) if first_rej is not None else all(acc)   # prefix
        qL = max((c['q'] for c in cands if c[f'accepted_L_eps{e}']), default=None)
        jj = [j for j, c in enumerate(cands) if c[f'accepted_joint_eps{e}']]
        qj = cands[jj[-1]]['q'] if jj else None
        D_seq = cands[first_rej]['D_in_mask'] if first_rej is not None else out['D_all']
        need_mask = (masks[first_rej] & masks[jf]) if first_rej is not None else masks[jf]
        out[f'eps{e}'] = dict(eps=e, N_min=NMIN[e], feasible=bool(N >= NMIN[e]),
                              status=('feasible' if N >= NMIN[e] else 'infeasible at eps'),
                              q_L=qL, q_joint=qj, tau_joint=(cands[jj[-1]]['tau'] if jj else None),
                              first_L_rejected_q=(cands[first_rej]['q'] if first_rej is not None else None),
                              n_L_accepted=int(sum(acc)), n_joint_accepted=len(jj),
                              D_seq=int(D_seq), D_dep=(cands[jj[-1]]['D_in_mask'] if jj else None), D_need=int(d[need_mask].sum()),
                              k_L_at_frozen=cands[jf]['k_L'], p_at_frozen=cands[jf][f'p_eps{e}'])
    return out


CERT = dict(prereg_sha256=PREREG_SHA, start_utc=T0, delta=DELTA, eps=EPS, N_min=NMIN, label=LABEL,
            definitions='L = u<=tau & o_b==y & o_R!=y; W = u<=tau & o_R==y & o_b!=y; p_eps = binom.cdf(k_L, N, eps); accept p<=.001; '
                        'change test = e17_common.ledger (P[Bin(n,.05)<=k]<=.001); joint = both; q = largest accepted; masks = data_r1.route_mask',
            settings={})
ROWS, SUMROWS = [], []
for name, key, nominal, oosname in SET6:
    s, qf = POLD[key]
    X = split_arrays(key, 'cal')
    ds = BENCH[s[1]]
    tau_f = X['cuts'][GRID.index(qf)]
    res = certify(X['u'], X['oR'], X['ob'], X['y'], X['d'], X['cuts'], qf)
    assert res['q_change_test'] == qf, (name, res['q_change_test'], qf)
    keep = np.array([i not in XSET[ds] for i in X['ids']], bool)
    rx = certify(X['u'][keep], X['oR'][keep], X['ob'][keep], X['y'][keep], X['d'][keep], X['cuts'], qf)
    CERT['settings'][name] = dict(policy_key=key, nominal=nominal, q_frozen=qf, tau_frozen=tau_f, calibration_ids_sha256=hashlib.sha256(
        json.dumps(X['ids']).encode()).hexdigest(), INVALID_R=int((X['oR'] == INV).sum()), INVALID_b=int((X['ob'] == INV).sum()), **res,
        C_minus_X=dict(N=rx['N'], n_removed=int((~keep).sum()), q_change_test=rx['q_change_test'],
                       **{f'eps{e}': {k: rx[f'eps{e}'][k] for k in ('feasible', 'q_L', 'q_joint', 'tau_joint', 'D_need')} for e in EPS}))
    for c in res['candidates']:
        ROWS.append(dict(setting=name, N=res['N'], **c, label=LABEL))
    for e in EPS:
        r = res[f'eps{e}']
        SUMROWS.append(dict(setting=name, nominal=nominal, eps=e, N=res['N'], N_min=NMIN[e], status=r['status'], q_frozen=qf, tau_frozen=tau_f,
                            q_L=r['q_L'] if r['q_L'] is not None else 'NONE', q_joint=r['q_joint'] if r['q_joint'] is not None else 'NONE',
                            tau_joint=r['tau_joint'], first_L_rejected_q=r['first_L_rejected_q'], D_all=res['D_all'], D_seq=r['D_seq'],
                            D_dep=r['D_dep'] if r['D_dep'] is not None else 'N/A', D_need=r['D_need'], k_L_at_frozen=r['k_L_at_frozen'],
                            p_at_frozen=r['p_at_frozen'], CX_N=rx['N'], CX_removed=int((~keep).sum()), CX_q_change=rx['q_change_test'],
                            CX_q_L=rx[f'eps{e}']['q_L'] if rx[f'eps{e}']['q_L'] is not None else 'NONE',
                            CX_q_joint=rx[f'eps{e}']['q_joint'] if rx[f'eps{e}']['q_joint'] is not None else 'NONE', label=LABEL))
        print(f"{name:24s} eps={e} N={res['N']} {r['status']} q_frozen={qf} q_L={r['q_L']} q_joint={r['q_joint']} "
              f"D_all/seq/dep/need={res['D_all']}/{r['D_seq']}/{r['D_dep']}/{r['D_need']} kL@frozen={r['k_L_at_frozen']} "
              f"C\\X: N={rx['N']} q_chg={rx['q_change_test']} q_joint={rx[f'eps{e}']['q_joint']}", flush=True)
CERT['end_utc'] = utc()
CERT['script_sha256'] = sha(STAGE21 / 'scripts/e21_1_cert.py')
CERT['common_sha256'] = sha(STAGE21 / 'scripts/e21_common.py')
jdump(STAGE21 / 'CERT.json', CERT)
h = sha(STAGE21 / 'CERT.json')
(STAGE21 / 'CERT.sha256').write_text(f'{h}  CERT.json\nutc {utc()}\n')
csvout('E21_1_cert_candidates.csv', ROWS)
csvout('E21_1_cert_summary.csv', SUMROWS)
run_log('e21_1_cert.py', T0, dict(cert_sha256=h))
print('CERT.json', h, utc())
