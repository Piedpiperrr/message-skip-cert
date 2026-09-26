"""E19-1: saving decomposition (u == 0 omitted / u > 0 omitted / routed) and the recomposed "omit only if u == 0" saving.
Replays and bindings as PREREG_E19.md (resolved paths, E19-1)."""
from e19_common import *

T0 = utc()
print('E19-1 start', T0)
# frozen thresholds (dev loader = deployment values, Step 0 (a))
TAU = {k: dev(k)['tau'] for k in POLD}


def decompose(name, key, R, cfg):
    ids, fx, po = R['ids'], R['fx'], R['po']
    N = len(ids)
    tau = TAU[key]
    rec_thr = [po[i].get('threshold') for i in ids]
    thr_src = 'record threshold field' if all(t is not None for t in rec_thr) else 'frozen deployment threshold (record has no threshold field)'
    if all(t is not None for t in rec_thr):
        assert all(t == tau for t in rec_thr), (name, 'record threshold != frozen tau')
    fixed = np.array([fx[i]['latency_ms'] for i in ids])
    pol = np.array([po[i]['latency_ms'] for i in ids])
    u = np.array([u_of(po[i]) for i in ids], float)
    om = np.array([route_R(po[i]) for i in ids], bool)
    pr = np.array([probe_ms(po[i]) for i in ids])
    pfield = 'parts_ms.probe_ms' if 'probe_ms' in po[ids[0]]['parts_ms'] else 'parts_ms.online_probe_ms'
    for i in ids:
        assert not fx[i].get('runtime_failure') and not po[i].get('runtime_failure'), (name, i)
    mism = int((om != (u <= tau)).sum())
    s = fixed - pol
    z = u == 0.0
    g0, gp, gr = om & z, om & ~z, ~om
    A0, Ap, B = s[g0].sum() / N, s[gp].sum() / N, s[gr].sum() / N
    net = s.mean()
    assert abs(A0 + Ap + B - net) < 1e-9
    idx = bidx(N)
    lo, hi = ci(s[idx].mean(axis=1))
    s2 = np.where(gp, -pr, s)
    rlo, rhi = ci(s2[idx].mean(axis=1))
    # bootstrap intervals of the parts (descriptive)
    parts_boot = {}
    for nm, g in [('A0', g0), ('Apos', gp), ('B', gr)]:
        parts_boot[nm] = ci((np.where(g, s, 0.0)[idx]).mean(axis=1))
    gross = Ap / (A0 + Ap) if (A0 + Ap) != 0 else float('nan')
    return dict(row=name, policy=key, configuration=cfg, N=N, tau=tau, tau_source=thr_src,
                u_source='policy request probe.ProbeMax (online probe of this replay, as stored)',
                route_source="policy request 'selected' (omitted iff == 'R')",
                route_mismatches_vs_u_le_tau=mism,
                n_omitted=int(om.sum()), n_u0_omitted=int(g0.sum()), n_upos_omitted=int(gp.sum()), n_routed=int(gr.sum()),
                n_u0_routed=int((gr & z).sum()),
                part_u0_ms=A0, part_u0_CI95_lo=parts_boot['A0'][0], part_u0_CI95_hi=parts_boot['A0'][1],
                part_upos_ms=Ap, part_upos_CI95_lo=parts_boot['Apos'][0], part_upos_CI95_hi=parts_boot['Apos'][1],
                part_routed_ms=B, part_routed_CI95_lo=parts_boot['B'][0], part_routed_CI95_hi=parts_boot['B'][1],
                net_ms=net, net_CI95_lo=lo, net_CI95_hi=hi, net_interval_excludes_0=(lo > 0 or hi < 0),
                gross_share_upos=gross, upos_share_of_net=(Ap / net if net != 0 else float('nan')),
                mean_saving_u0_omitted_ms=(s[g0].mean() if g0.any() else float('nan')),
                mean_saving_upos_omitted_ms=(s[gp].mean() if gp.any() else float('nan')),
                mean_saving_routed_ms=(s[gr].mean() if gr.any() else float('nan')),
                recomposed_u0_only_ms=s2.mean(), recomposed_CI95_lo=rlo, recomposed_CI95_hi=rhi,
                recomposed_label='recomposed (not a replay): omitted u>0 questions assigned policy_i = fixed_i + probe_i',
                probe_source=f'logged per request ({pfield})', mean_probe_upos_omitted_ms=(pr[gp].mean() if gp.any() else float('nan')),
                source=R['source'], label=LABEL)


ROWS = []
for key in QWEN8 + ['large/OBQA/Text+fact', 'Llama-3.1-8B/OBQA/Text', 'Llama-3.1-8B/ARC/Text']:
    R = replay(key)
    ROWS.append(decompose(key, key, R, R['config']))
R = replay_full_mmlu_c2c()
ROWS.append(decompose('large/MMLU-Pro/C2C (full 2,641)', 'large/MMLU-Pro/C2C', R, R['config']))
for r in ROWS:
    print(f"{r['row']:34s} N={r['N']} u0 {r['part_u0_ms']:.1f} ({r['n_u0_omitted']}) u+ {r['part_upos_ms']:.1f} ({r['n_upos_omitted']}) "
          f"routed {r['part_routed_ms']:.1f} ({r['n_routed']}) net {r['net_ms']:.1f} [{r['net_CI95_lo']:.1f},{r['net_CI95_hi']:.1f}] "
          f"gross {r['gross_share_upos']:.3f} rec {r['recomposed_u0_only_ms']:.1f} [{r['recomposed_CI95_lo']:.1f},{r['recomposed_CI95_hi']:.1f}] mism {r['route_mismatches_vs_u_le_tau']}")

# ---- coverage / change rate of the u = 0 part and u > 0 increment (stored, no recomputation)
E14Z = csvread(E14 / 'results/E14_2_zero_u.csv')
E171 = {r['setting']: r for r in csvread(ROOT / 'P2_R7_E17_20260921T183100Z/results/E17_1_u0_rule.csv')}
OOSP = read(E16 / 'results/analysis_oos/OOS_PRE_GOLD.json')['results']
POP = {'dev': 'dev', 'held-out 744 OBQA': 'held-out', 'sealed ARC 1,172': 'sealed'}
COV = []
for r in E14Z:
    if r['population'] not in POP: continue
    N, n0, k0, npos, kpos = (int(r[c]) for c in ('N', 'n0', 'k0', 'n_pos', 'k_pos'))
    COV.append(dict(policy=r['policy'], population=POP[r['population']], N=N, u0_n0=n0, u0_coverage=n0 / N, u0_k0=k0,
                    u0_change_rate=(k0 / n0 if n0 else float('nan')), upos_n=npos, upos_coverage=npos / N, upos_k=kpos,
                    upos_change_rate=(kpos / npos if npos else float('nan')),
                    source=str(E14 / 'results/E14_2_zero_u.csv')))
for key, s in [('Llama-3.1-8B/OBQA/Text', LLO), ('Llama-3.1-8B/ARC/Text', LLA)]:
    r = E171[f'{s[0]}/{s[1]}/{s[2]}']
    N, n0, k0 = int(r['dev_N']), int(r['dev_n0']), int(r['dev_k0'])
    n, k = int(r['policy_dev_n']), int(r['policy_dev_k'])
    COV.append(dict(policy=key, population='dev', N=N, u0_n0=n0, u0_coverage=n0 / N, u0_k0=k0, u0_change_rate=float('nan'),
                    upos_n=n - n0, upos_coverage=(n - n0) / N, upos_k=k - k0, upos_change_rate=(k - k0) / (n - n0),
                    source=str(ROOT / 'P2_R7_E17_20260921T183100Z/results/E17_1_u0_rule.csv')))
for key, pk, pop in [('Llama-3.1-8B/OBQA/Text', 'Llama-3.1-8B OBQA/Text (q=.60) on 744 held-out OBQA', 'held-out (E16-1)'),
                     ('Llama-3.1-8B/ARC/Text', 'Llama-3.1-8B ARC/Text (q=.70) on 1,172 ARC test', 'ARC test (E16-1)'),
                     ('medium/ARC/C2C', 'medium ARC/C2C (q=.60) on 1,172 ARC test', 'ARC test (E16-2)')]:
    r = OOSP[pk]
    N, n, k, n0 = r['N'], r['omitted_n'], r['changed_k'], r['u0_omitted']
    COV.append(dict(policy=key, population=pop, N=N, u0_n0=n0, u0_coverage=n0 / N, u0_k0=(0 if n0 == 0 else 'not stored'),
                    u0_change_rate=(float('nan') if n0 == 0 else 'not stored'), upos_n=n - n0, upos_coverage=(n - n0) / N,
                    upos_k=(k if n0 == 0 else 'not stored'), upos_change_rate=(k / n if n0 == 0 else 'not stored'),
                    source=str(E16 / 'results/analysis_oos/OOS_PRE_GOLD.json') + ' (u0_omitted, omitted_n, changed_k)'))
for r in COV: r['label'] = LABEL

# ---- writing rule
q9 = [r for r in ROWS if r['row'] in QWEN9]
exc = [r for r in q9 if r['net_interval_excludes_0']]
oth = [r for r in q9 if not r['net_interval_excludes_0']]
gs = [r['gross_share_upos'] for r in exc]
rule = dict(n_qwen9=len(q9), n_net_interval_excludes_0=len(exc),
            policies_net_interval_excludes_0=';'.join(r['row'] for r in exc),
            policies_net_interval_includes_0=';'.join(r['row'] for r in oth),
            gross_share_min=min(gs), gross_share_min_policy=min(exc, key=lambda r: r['gross_share_upos'])['row'],
            gross_share_max=max(gs), gross_share_max_policy=max(exc, key=lambda r: r['gross_share_upos'])['row'],
            policies_gross_share_ge_50=';'.join(r['row'] for r in exc if r['gross_share_upos'] >= .5) or 'none',
            others_gross_share=';'.join(f"{r['row']}={r['gross_share_upos']:.4f}" for r in oth), label=LABEL)
print(rule)
csvout('E19_1_decomposition.csv', ROWS)
csvout('E19_1_u0_coverage_change.csv', COV)
csvout('E19_1_writing_rule.csv', [rule])
json.dump(dict(start_utc=T0, end_utc=utc(), files_read=READ), open(STAGE / 'logs/e19_1_run.json', 'w'), indent=1)
print('E19-1 done', utc())
