"""E13 Item 3: retained gain of a helpful path under omission, the alpha sweep, and recomposed savings.

Settings: large/OBQA/Text, large/ARC/Text, large/MMLU-Pro/Text (loader: P2_R1_CPU data_r1.load_pair_dataset; calibration
ledger: common_r1.ledgers()), large/OBQA/Text+fact (E6 records and E6_LEDGER.csv; loading replicates e6_analyze.py).
Held-out: the 744 E9b OBQA questions (SEALED_ROUTES / SEALED_SCORES; gold opened exactly as e9b_decode.py does).
Rule: largest q with P[Bin(n, alpha) <= k] <= .001 (common_r1.deploy), same 20 frozen fit thresholds, original split.
Bootstrap: per (setting, split) one default_rng(0).integers(0, N, (2000, N)) matrix, shared by all alphas (paired).
Recomposed saving: variant latency = pre-action part of the policy request (input prep + probe + selector)
  + (omitted under the variant ? the policy request's action part (action + parse + cleanup) : the fixed arm's latency);
  version (b) = drop every question on which either arm made its first formal request (e3_metrics.py);
  bootstrap default_rng(0).integers(0, n_b, (2000, n_b)).
"""
import csv, json
import numpy as np
import pyarrow.parquet as pq
from e13_common import *
from common_r1 import ledgers, deploy, pval, thresholds, tv, GRID, BND, ZG, V2  # noqa: E402
from data_r1 import load_pair_dataset, route_mask  # noqa: E402

ALPHAS = [.01, .02, .03, .04, .05]
GPU = ROOT / 'P2_R2_GPU_20260919T220941Z'
E9 = ROOT / 'P2_R3_E9BC_20260920T061042Z'
FP = ROOT / 'P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z'
MP = ROOT / 'P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z'
E7 = ROOT / 'P2_R2_E7_20260919T231531Z'
REP = {k: ROOT / f'P2_R1_E3POL_{k}_20260919T075315Z' for k in ['REPEAT1', 'REPEAT2', 'REPEAT3']}
INV = 'INVALID'
NB = 2000

# ------------------------------------------------------------------ data
GOLD = E.gold_map()
L = ledgers()
S = {}
for task, key in [('OBQA', 'obqa'), ('ARC', 'arc'), ('MMLU-Pro', 'mmlu_pro')]:
    D = load_pair_dataset('large', task)
    cuts = thresholds(list(D['fit']['scores']['ProbeMax']))
    assert [str(a) for a in cuts] == [str(b) for b in D['stored_thresholds']]
    dv = D['dev']
    S[f'large/{task}/Text'] = dict(
        u=np.asarray(dv['scores']['ProbeMax'], float), oR=np.array(dv['ans']['R'], object), ob=np.array(dv['ans']['T'], object),
        g=np.array([GOLD[key, i] for i in dv['ids']], object), cuts=cuts,
        ledger=[dict(q=r['q'], n=r['n'], k=r['k']) for r in L[('large', task, 'Text')]], ids=list(dv['ids']))

# Text+fact (replicates e6_analyze.py loading)
lab = {}
for name in ['full_train', 'full_development']:
    for x in jl(V2 / f'labels/{name}_P2_SCORING_V2.jsonl'):
        if x['pair'] == 'large' and x['dataset'] == 'obqa':
            lab[x['id']] = x
probe = {r['id']: r for r in jl(ZG / 'records/probe_records.jsonl')}
e6 = {}
for f in sorted((GPU / 'e6/main').glob('e6_shard*.jsonl')):
    for r in jl(f):
        e6[r['id']] = r
dev_ids = read(BND / 'splits/obqa_dev_representatives.json')
TH = read(BND / 'thresholds/large_obqa.json')['thresholds']
led6 = [dict(q=float(r['q']), n=int(r['n']), k=int(r['k'])) for r in csv.DictReader((GPU / 'e6/analysis/E6_LEDGER.csv').open())]
S['large/OBQA/Text+fact'] = dict(
    u=np.array([probe[i]['ProbeMax'] for i in dev_ids], float),
    oR=np.array([lab[i]['o_R'] if lab[i]['valid_R'] else INV for i in dev_ids], object),
    ob=np.array([e6[i]['answer'] for i in dev_ids], object),
    g=np.array([lab[i]['gold'] for i in dev_ids], object), cuts=TH, ledger=led6, ids=dev_ids)
assert [str(a) for a in TH] == [str(b) for b in S['large/OBQA/Text']['cuts']]
assert all(GOLD['obqa', i] == lab[i]['gold'] for i in dev_ids)

# held-out (E9b)
DSP = E.ROOT.parent.parent / 'c2c_reproduction_assets/datasets/allenai--openbookqa/main/train-00000-of-00001.parquet'
tb = pq.read_table(DSP, columns=['id', 'answerKey'])
HGOLD = dict(zip(tb.column('id').to_pylist(), tb.column('answerKey').to_pylist()))
routes = jl(E9 / 'analysis/SEALED_ROUTES.jsonl')
pop = [r['id'] for r in jl(E9 / 'inputs/holdout_744_queries.jsonl')]
HO = {}
for sname, pol in [('large/OBQA/Text', 'large_obqa_T_q80'), ('large/OBQA/Text+fact', 'large_obqa_TF_q75')]:
    rr = {r['id']: r for r in routes if r['policy'] == pol}
    assert len(rr) == 744 == len(pop)
    HO[sname] = dict(u=np.array([rr[i]['ProbeMax'] for i in pop], float), oR=np.array([rr[i]['R_answer'] for i in pop], object),
                     ob=np.array([rr[i]['reference_answer'] for i in pop], object), g=np.array([HGOLD[i] for i in pop], object),
                     frozen_omitted=np.array([rr[i]['omitted'] for i in pop], bool), frozen_thr=rr[pop[0]]['threshold'],
                     frozen_policy=np.array([rr[i]['policy_answer'] for i in pop], object))


# ------------------------------------------------------------------ helpers
def evaluate(d, om, idx):
    yR, yb = d['oR'] == d['g'], d['ob'] == d['g']
    pol = np.where(om, d['oR'], d['ob'])
    yp = pol == d['g']
    N = len(yR)
    G = (yb.sum() - yR.sum()) / N; P = (yp.sum() - yR.sum()) / N
    corr = yb & ~yR
    Gs = yb[idx].mean(1) - yR[idx].mean(1); Ps = yp[idx].mean(1) - yR[idx].mean(1)
    ok = Gs != 0
    rs = Ps[ok] / Gs[ok]
    pc = lambda a: (float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5)))
    return dict(N=N, correct_R=int(yR.sum()), correct_b=int(yb.sum()), correct_policy=int(yp.sum()),
                acc_policy_pct=100 * yp.mean(), acc_R_pct=100 * yR.mean(), acc_b_pct=100 * yb.mean(),
                omitted=int(om.sum()), changed=int((d['oR'] != d['ob'])[om].sum()), kappa=om.mean(),
                G_pts=100 * G, G_lo=100 * pc(Gs)[0], G_hi=100 * pc(Gs)[1],
                P_pts=100 * P, P_lo=100 * pc(Ps)[0], P_hi=100 * pc(Ps)[1],
                retention=P / G if G else float('nan'), ret_lo=pc(rs)[0], ret_hi=pc(rs)[1],
                share_boot_G_le_0=float((Gs <= 0).mean()), n_boot_G_eq_0_undefined=int((~ok).sum()),
                corrections_total=int(corr.sum()), corrections_lost_omitted=int((corr & om).sum()),
                corrections_kept_routed=int((corr & ~om).sum()))


def variant(sname, a):
    rows = S[sname]['ledger']
    q, acc = deploy(rows, alpha=a)
    if q == 0:
        r0 = rows[0]
        return 0.0, None, r0, pval(r0['k'], r0['n'], a)
    r = next(x for x in rows if x['q'] == q)
    return q, S[sname]['cuts'][GRID.index(q)], r, pval(r['k'], r['n'], a)


# ------------------------------------------------------------------ reproduction checks
repro = []
PAPER_DEV = {'large/OBQA/Text': (617, 645, 638), 'large/ARC/Text': (268, 274, 270), 'large/MMLU-Pro/Text': (1282, 1319, 1321),
             'large/OBQA/Text+fact': (617, 670, 660)}
PAPER_A02 = {'large/OBQA/Text': (.65, 6, 460), 'large/ARC/Text': (.80, 0, 233), 'large/MMLU-Pro/Text': (0.0, None, None)}
idx_dev = {s: np.random.default_rng(0).integers(0, len(S[s]['u']), (NB, len(S[s]['u']))) for s in S}
idx_ho = np.random.default_rng(0).integers(0, 744, (NB, 744))
for s in S:
    q, t, r, p = variant(s, .05)
    om = route_mask(S[s]['u'], q, t) if q else np.zeros(len(S[s]['u']), bool)
    ev = evaluate(S[s], om, idx_dev[s])
    got = (ev['correct_R'], ev['correct_b'], ev['correct_policy'])
    repro.append(dict(item=3, check=f'{s} dev correct R/b/policy at alpha=.05', expected='/'.join(map(str, PAPER_DEV[s])),
                      got='/'.join(map(str, got)), ok=got == PAPER_DEV[s]))
for s, (qe, ke, ne) in PAPER_A02.items():
    q, t, r, p = variant(s, .02)
    if qe == 0:
        repro.append(dict(item=3, check=f'{s} alpha=.02 deployed q', expected='fallback', got=q, ok=q == 0))
    else:
        om = route_mask(S[s]['u'], q, t); k = int((S[s]['oR'] != S[s]['ob'])[om].sum())
        repro.append(dict(item=3, check=f'{s} alpha=.02 q (dev changed/omitted)', expected=f'{qe} ({ke}/{ne})',
                          got=f'{q} ({k}/{int(om.sum())})', ok=(q, k, int(om.sum())) == (qe, ke, ne)))
PAPER_HO = {'large/OBQA/Text': (86.02, 86.96, 595, 12), 'large/OBQA/Text+fact': (89.65, 91.13, 558, 16)}
for s, (ap, ar, no, nc) in PAPER_HO.items():
    d = HO[s]; q, t, r, p = variant(s, .05)
    om = route_mask(d['u'], q, t)
    assert np.array_equal(om, d['frozen_omitted']) and tv(t) == d['frozen_thr']
    pol = np.where(om, d['oR'], d['ob']); assert np.array_equal(pol, d['frozen_policy'])
    got = (round(100 * (pol == d['g']).mean(), 2), round(100 * (d['ob'] == d['g']).mean(), 2), int(om.sum()), int((d['oR'] != d['ob'])[om].sum()))
    repro.append(dict(item=3, check=f'{s} held-out acc policy/ref, omitted/changed', expected=f'{ap}/{ar}, {no}/{nc}',
                      got=f'{got[0]}/{got[1]}, {got[2]}/{got[3]}', ok=got == (ap, ar, no, nc)))
csvout(RES / 'item3_repro_checks.csv', repro)
for r in repro: print(r)
if not all(r['ok'] for r in repro):
    raise SystemExit('Item 3 reproduction check FAILED: stop')

# ------------------------------------------------------------------ sweep (dev + held-out)
sweep = []
for s in S:
    for a in ALPHAS:
        q, t, r, p = variant(s, a)
        om = route_mask(S[s]['u'], q, t) if q else np.zeros(len(S[s]['u']), bool)
        ev = evaluate(S[s], om, idx_dev[s])
        row = dict(setting=s, alpha=a, deployed_q=q if q else 'fallback', threshold=t if q else '',
                   cal_n=r['n'], cal_k=r['k'], cal_p=p, cal_row_note='' if q else 'fallback: q=.05 candidate shown',
                   **{f'dev_{k}': v for k, v in ev.items()})
        row['dev_kappa_alpha_pts'] = 100 * ev['kappa'] * a
        row['dev_kappa_alpha_lt_G'] = row['dev_kappa_alpha_pts'] < ev['G_pts']
        if s in HO:
            d = HO[s]
            omh = route_mask(d['u'], q, t) if q else np.zeros(744, bool)
            eh = evaluate(d, omh, idx_ho)
            row.update({f'ho_{k}': v for k, v in eh.items()})
        sweep.append(row)
        print(f"{s:22s} a={a:.2f} q={row['deployed_q']!s:8s} n/k/p={r['n']}/{r['k']}/{p:.2e} kappa={ev['kappa']:.3f} "
              f"ch/om={ev['changed']}/{ev['omitted']} ka={row['dev_kappa_alpha_pts']:.2f} G={ev['G_pts']:.2f} P={ev['P_pts']:.2f} "
              f"ret={ev['retention']:.3f} [{ev['ret_lo']:.3f},{ev['ret_hi']:.3f}] Gle0={ev['share_boot_G_le_0']:.3f}"
              + (f" | HO {row['ho_changed']}/{row['ho_omitted']} acc={row['ho_acc_policy_pct']:.2f} ret={row['ho_retention']:.3f} "
                 f"[{row['ho_ret_lo']:.3f},{row['ho_ret_hi']:.3f}]" if s in HO else ''))
csvout(RES / 'item3_alpha_sweep.csv', sweep)

largest = []
for s in S:
    rr = [r for r in sweep if r['setting'] == s]
    ok = [r for r in rr if r['dev_kappa_alpha_lt_G']]
    okd = [r for r in ok if r['deployed_q'] != 'fallback']
    b = ok[-1] if ok else None; bd = okd[-1] if okd else None
    largest.append(dict(setting=s, G_pts=rr[0]['dev_G_pts'],
                        largest_alpha_kappa_alpha_lt_G=b['alpha'] if b else 'none',
                        its_q=b['deployed_q'] if b else '', its_kappa=b['dev_kappa'] if b else '',
                        its_retention=b['dev_retention'] if b else '', its_ret_lo=b['dev_ret_lo'] if b else '',
                        its_ret_hi=b['dev_ret_hi'] if b else '',
                        largest_deployed_alpha_kappa_alpha_lt_G=bd['alpha'] if bd else 'none',
                        deployed_q=bd['deployed_q'] if bd else '', deployed_kappa=bd['dev_kappa'] if bd else '',
                        deployed_retention=bd['dev_retention'] if bd else '', label=LABEL))
csvout(RES / 'item3_largest_alpha.csv', largest)
for x in largest: print(x)


# ------------------------------------------------------------------ recomposed savings
def pre(r):
    p = r['parts_ms']
    return sum(v for k, v in p.items() if k.startswith('input_prep') or 'probe' in k or k.startswith('selector'))


def act(r):
    return r['latency_ms'] - pre(r)


def streams(sname):
    """(replay label, ids, fixed{id:rec}, policy{id:rec}, source)."""
    out = []
    if sname in ('large/OBQA/Text', 'large/ARC/Text'):
        ds = 'obqa' if 'OBQA' in sname else 'arc'
        for lab_, F, sub in [('original (ClusterB)', FP, '')] + [(k, v, 'large/') for k, v in REP.items()]:
            reqs = jl(F / f'{sub}records/e2e_requests.jsonl')
            ids = read(F / f'{sub}inputs/{ds}_panel_ids.json')
            fx = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, 'T', 'reference')}
            po = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, 'T', 'policy')}
            out.append((lab_, ids, fx, po, F / f'{sub}records/e2e_requests.jsonl'))
    elif sname == 'large/MMLU-Pro/Text':
        ids = np.load(MP / 'protocol/bootstrap_indices.npz')['ids'].tolist()
        for lab_, F, sub in [('original (ClusterB)', MP, '')] + [(k, v, 'mmlu/') for k, v in REP.items()]:
            reqs = jl(F / f'{sub}records/four_arm_requests.jsonl')
            fx = {r['id']: r for r in reqs if r['arm'] == 'fixed_T'}
            po = {r['id']: r for r in reqs if r['arm'] == 'policy_T'}
            out.append((lab_, ids, fx, po, F / f'{sub}records/four_arm_requests.jsonl'))
    else:
        reqs = jl(E7 / 'e6replay/records_e6/e6_replay_requests.jsonl')
        ids = read(E7 / 'e6replay/inputs/obqa_panel_ids.json')
        fx = {r['id']: r for r in reqs if r['arm'] == 'fixed_TF'}
        po = {r['id']: r for r in reqs if r['arm'] == 'policy_TF'}
        out.append(('E6 replay (ClusterA; only replay of this setting)', ids, fx, po, E7 / 'e6replay/records_e6/e6_replay_requests.jsonl'))
    return out


def score(r):
    return r['probe']['ProbeMax'] if isinstance(r.get('probe'), dict) else r['ProbeMax']


rec_rows = []
for s in S:
    q05, t05, _, _ = variant(s, .05)
    for lab_, ids, fx, po, src in streams(s):
        assert set(ids) <= set(fx) and set(ids) <= set(po) and len(ids) == 128
        ff = min(fx.values(), key=lambda r: r['attempt']); pf = min(po.values(), key=lambda r: r['attempt'])
        excl = {ff['id'], pf['id']}; keep = [i for i in ids if i not in excl]; nb = len(keep)
        idx = np.random.default_rng(0).integers(0, nb, (NB, nb))
        u = np.array([score(po[i]) for i in keep])
        om05_rec = np.array([po[i]['selected'] == 'R' for i in keep])
        assert np.array_equal(om05_rec, u <= tv(t05)), (s, lab_)
        fixed = np.array([fx[i]['latency_ms'] for i in keep]); polm = np.array([po[i]['latency_ms'] for i in keep])
        pr = np.array([pre(po[i]) for i in keep]); ac = np.array([act(po[i]) for i in keep])
        meas = fixed - polm
        for a in ALPHAS:
            q, t, _, _ = variant(s, a)
            if q:
                omv = u <= tv(t)
                assert not (omv & ~om05_rec).any()          # variant omits a subset of the alpha=.05 omissions
                var = pr + np.where(omv, ac, fixed)
                d = fixed - var
                bs = d[idx].mean(1)
                rec_rows.append(dict(setting=s, replay=lab_, alpha=a, deployed_q=q, version='b', n_b=nb,
                                     b_excluded_ids=';'.join(sorted(excl)), omitted_under_variant=int(omv.sum()),
                                     omitted_under_alpha05=int(om05_rec.sum()),
                                     recomposed_mean_saving_ms=float(d.mean()), CI_lo=float(np.percentile(bs, 2.5)),
                                     CI_hi=float(np.percentile(bs, 97.5)),
                                     measured_alpha05_b_saving_ms=float(meas.mean()),
                                     mean_pre_action_ms=float(pr.mean()), source=str(src),
                                     note='recomposed from the per-request timings of an existing replay (not a new replay)', label=LABEL))
            else:
                d = -pr; bs = d[idx].mean(1)
                rec_rows.append(dict(setting=s, replay=lab_, alpha=a, deployed_q='fallback', version='b', n_b=nb,
                                     b_excluded_ids=';'.join(sorted(excl)), omitted_under_variant=0,
                                     omitted_under_alpha05=int(om05_rec.sum()),
                                     recomposed_mean_saving_ms=float(d.mean()), CI_lo=float(np.percentile(bs, 2.5)),
                                     CI_hi=float(np.percentile(bs, 97.5)), measured_alpha05_b_saving_ms=float(meas.mean()),
                                     mean_pre_action_ms=float(pr.mean()), source=str(src),
                                     note='fallback: the deployed system is the fixed arm (saving 0, no probe); the value shown is the '
                                          'prereg formula (probe still run, nothing omitted) = -mean pre-action part', label=LABEL))
            print(f"{s:22s} {lab_:30s} a={a:.2f} q={rec_rows[-1]['deployed_q']!s:8s} om={rec_rows[-1]['omitted_under_variant']:3d}/"
                  f"{rec_rows[-1]['omitted_under_alpha05']:3d} save={rec_rows[-1]['recomposed_mean_saving_ms']:8.1f} "
                  f"[{rec_rows[-1]['CI_lo']:.1f},{rec_rows[-1]['CI_hi']:.1f}] meas05={meas.mean():.1f}")
csvout(RES / 'item3_recomposed_savings.csv', rec_rows)
