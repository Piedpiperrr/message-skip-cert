"""E21-2 (PREREG.md): AUROC on unsaturated questions. d = 1[o_R != o_b] (frozen V2 labels, two INVALIDs agree), score u (stored ProbeMax).
AUROC = e17_common.auroc (sklearn roc_auc_score; ties 1/2). (ii) bootstrap: default_rng(0).integers(0, n, (2000, n)) over the u > 0 questions,
single-class resamples dropped and counted, percentile interval np.quantile(.025, .975). (iii)/(iv) m = E16-3 float64 score from the bf16
prefill label logits (functions lse/scores verbatim from analyze_e16_3.py); the prefill's ProbeMax must equal the stored u bitwise.
Held-out OBQA 744: SEALED_ROUTES (ProbeMax, R_answer, reference_answer) and the E16 Llama routes; E16-3 m is not stored there
(only fit/cal/dev units were prefilled; held-out records hold float32 p_labels only) -> (iii)/(iv) "not stored"."""
from e21_common import *

T0 = utc()
print('E21-2 start', T0, flush=True)
PAPER_AUC = {'medium/OBQA/C2C q=.55': .840, 'medium/ARC/C2C': .910, 'large/OBQA/Text': .873, 'large/OBQA/C2C': .883,
             'large/ARC/Text': .952, 'large/ARC/C2C': .909, 'large/MMLU-Pro/Text': .821, 'large/MMLU-Pro/C2C': .846,
             'large/OBQA/Text+fact': .889, 'Llama-3.1-8B/OBQA/Text': .8745, 'Llama-3.1-8B/ARC/Text': .8804, 'SQuAD/Llama (s2)': .811}
E171 = {(r['setting'], float(r['q'])): r for r in csvread(ROOT / 'P2_R7_E17_20260921T183100Z/results/E17_1_u0_rule.csv')}
MREC = {}


def boot_auc(d, s):
    n = len(d)
    idx = np.random.default_rng(0).integers(0, n, (2000, n))
    vals, dropped = [], 0
    for ix in idx:
        dd = d[ix]
        if dd.all() or not dd.any():
            dropped += 1
            continue
        vals.append(E17.auroc(dd, s[ix]))
    return ([float(x) for x in np.quantile(vals, [.025, .975])] if vals else [float('nan')] * 2), dropped


def block(d, u, m=None, full=True):
    z = u == 0.0
    r = dict(n=len(d), n_pos=int(d.sum()), auroc_all=E17.auroc(d, u))
    if full:
        dp, up = d[~z], u[~z]
        (lo, hi), dropped = boot_auc(dp, up)
        r.update(upos_n=int((~z).sum()), upos_pos=int(dp.sum()), auroc_upos=E17.auroc(dp, up), auroc_upos_CI95_lo=lo, auroc_upos_CI95_hi=hi,
                 auroc_upos_boot_dropped=dropped)
    r.update(u0_n=int(z.sum()), u0_pos=int(d[z].sum()), share_u0=float(z.mean()),
             share_dis_upos=(float(d[~z].sum() / d.sum()) if d.sum() else float('nan')),
             u0_change_rate=(float(d[z].sum() / z.sum()) if z.any() else float('nan')))
    if m is not None:
        r.update(auroc_m_all=E17.auroc(d, m), auroc_m_u0=(E17.auroc(d[z], m[z]) if 0 < d[z].sum() < z.sum() else 'N/A'),
                 m_distinct_values=int(len(np.unique(m))), m_units_in_ties=int(len(m) - len(np.unique(m))))
    return r


ROWS, CHECKS = [], []
for key in POL9:
    D = dev(key)
    s = setting_of(key)
    rec = REC[s[0]]
    if rec not in MREC:
        MREC[rec] = m_records(rec)
    R, fsrc = MREC[rec]
    ds = BENCH[s[1]]
    pre = [R[(ds, i)] for i in D['ids']]
    assert all(p['ProbeMax'] == u for p, u in zip(pre, D['u'])), key
    m = np.array([m_of(p) for p in pre], float)
    r = block(D['d'], D['u'], m)
    ok = abs(r['auroc_all'] - PAPER_AUC[key]) <= 5e-4
    e1 = E171[C.sname(s), D['q']]
    ok6 = (int(e1['dev_n0']), int(e1['dev_k0'])) == (r['u0_n'], r['u0_pos'])
    CHECKS += [dict(check=f'{key} (i) vs paper {PAPER_AUC[key]} (|diff|<=5e-4)', observed=r['auroc_all'], status='PASS' if ok else 'FAIL'),
               dict(check=f'{key} (vi) u=0 block n0/k0 vs E17_1_u0_rule.csv', observed=[r['u0_n'], r['u0_pos']],
                    expected=[int(e1['dev_n0']), int(e1['dev_k0'])], status='PASS' if ok6 else 'FAIL')]
    ROWS.append(dict(row=key, kind='policy', population='dev', **r, m_source=fsrc, paper_auroc=PAPER_AUC[key], label=LABEL))
# controls: (i) and (v)
for key in ['Llama-3.1-8B/OBQA/Text', 'Llama-3.1-8B/ARC/Text']:
    D = dev(key)
    r = block(D['d'], D['u'], full=False)
    CHECKS.append(dict(check=f'{key} (i) vs paper {PAPER_AUC[key]}', observed=r['auroc_all'], status='PASS' if abs(r['auroc_all'] - PAPER_AUC[key]) <= 5e-4 else 'FAIL'))
    ROWS.append(dict(row=key, kind='control', population='dev', **{k: r[k] for k in ('n', 'n_pos', 'auroc_all', 'u0_n', 'share_u0', 'share_dis_upos')},
                     paper_auroc=PAPER_AUC[key], label=LABEL))
SQ = squad_dev()
r = block(SQ['d'], SQ['s2'], full=False)
CHECKS.append(dict(check='SQuAD/Llama (s2) (i) vs paper .811', observed=r['auroc_all'], status='PASS' if abs(r['auroc_all'] - .811) <= 5e-4 else 'FAIL'))
ROWS.append(dict(row='SQuAD/Llama (s2)', kind='control', population='dev', **{k: r[k] for k in ('n', 'n_pos', 'auroc_all', 'u0_n', 'share_u0', 'share_dis_upos')},
                 paper_auroc=.811, score='s2 (u = 0 means s2 == 0.0)', label=LABEL))
# held-out OBQA 744
routes = jl(E9 / 'analysis/SEALED_ROUTES.jsonl')
pop = [x['id'] for x in jl(E9 / 'inputs/holdout_744_queries.jsonl')]
for key, pol in [('medium/OBQA/C2C q=.55', 'medium_obqa_C_q55'), ('large/OBQA/Text', 'large_obqa_T_q80'), ('large/OBQA/C2C', 'large_obqa_C_q80'),
                 ('large/OBQA/Text+fact', 'large_obqa_TF_q75')]:
    rr = {x['id']: x for x in routes if x['policy'] == pol}
    u = np.array([rr[i]['ProbeMax'] for i in pop], float)
    d = np.array([rr[i]['R_answer'] != rr[i]['reference_answer'] for i in pop], bool)
    r = block(d, u)
    ROWS.append(dict(row=key, kind='policy', population='held-out OBQA 744', **r, auroc_m_all='not stored', auroc_m_u0='not stored',
                     m_note='E16-3 m exists only for fit/cal/dev units; held-out records store float32 p_labels only',
                     source=str(E9 / 'analysis/SEALED_ROUTES.jsonl'), label=LABEL))
O = oos('Llama-3.1-8B/OBQA/Text')
d = np.array([a != b for a, b in zip(O['oR'], O['ob'])], bool)
ROWS.append(dict(row='Llama-3.1-8B/OBQA/Text', kind='control', population='held-out OBQA 744 (E16-1)', n=len(d), n_pos=int(d.sum()),
                 auroc_all=E17.auroc(d, O['u']), source=O['source'], label=LABEL))

# ------------------------------------------------------------------ writing rule
P9 = [r for r in ROWS if r['kind'] == 'policy' and r['population'] == 'dev']
ii = [r['auroc_upos'] for r in P9]
iii = [r['auroc_m_all'] for r in P9]
i_ = [r['auroc_all'] for r in P9]
vi = [r['u0_change_rate'] for r in P9]
RULE = dict(ii_min=min(ii), ii_min_policy=P9[int(np.argmin(ii))]['row'], ii_max=max(ii), ii_max_policy=P9[int(np.argmax(ii))]['row'],
            ii_median=float(np.median(ii)), iii_median=float(np.median(iii)), i_median=float(np.median(i_)),
            vi_min=min(vi), vi_max=max(vi), label=LABEL)
X, Y = f"{RULE['ii_min']:.3f}", f"{RULE['ii_max']:.3f}"
RULE['always'] = (f"Sec. 6 (u = 0 paragraph): AUROC on u > 0 over the nine policies ranges {X}-{Y} (median {RULE['ii_median']:.3f}); "
                  f"AUROC of the float64 score m on all dev questions has median {RULE['iii_median']:.3f}.")
if RULE['ii_median'] >= .80:
    RULE['branch'] = 'median(ii) >= .80'
    RULE['sentence'] = f'the probe also ranks disagreements among unsaturated questions (AUROC {X}-{Y} on u > 0)'
elif RULE['ii_median'] < .70:
    RULE['branch'] = 'median(ii) < .70'
    RULE['sentence'] = (f"the ranking mostly separates the saturated block, where the reference changes {100 * RULE['vi_min']:.2f}-{100 * RULE['vi_max']:.2f}% "
                        f"of answers (from (vi)), from the rest (AUROC {X}-{Y} on u > 0 alone)")
else:
    RULE['branch'] = 'otherwise (.70 <= median(ii) < .80)'
    RULE['sentence'] = (f"on unsaturated questions alone the AUROC is {X}-{Y} (median {RULE['ii_median']:.3f}), lower than on all questions "
                        f"(median {RULE['i_median']:.3f})")
for r in ROWS:
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k not in ('label', 'm_source', 'source', 'm_note')}, flush=True)
print(json.dumps(RULE, indent=1))
for c in CHECKS:
    print(c)
csvout('E21_2_auroc.csv', ROWS)
csvout('E21_2_checks.csv', CHECKS)
jdump(RES / 'E21_2_writing_rule.json', RULE)
run_log('e21_2.py', T0, dict(n_fail=sum(c['status'] == 'FAIL' for c in CHECKS)))
print('E21-2 done', utc())
