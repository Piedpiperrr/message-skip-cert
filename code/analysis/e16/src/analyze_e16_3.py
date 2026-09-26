"""E16-3 analysis (CPU, login node), as PREREG.md. Inputs: Job B prefills results/e163/<receiver>_<dtype>_*.jsonl (verified against
results/MANIFEST_jobB.sha256); settings (23 = E11/E13 ALL26 minus the 3 X2-OLMo settings) with frozen labels, stored u, frozen fit thresholds
and original q from P2_R4_E11 e11_common.load / P2_R5_E13 e13_settings.load_fit. Receiver per setting: small and X1-Llama -> Qwen3-0.6B,
medium -> Qwen3-1.7B, large and Text+fact -> Qwen3-8B. No gold is used anywhere in E16-3.
(a) bf16 label logits l (as deployed): m = logsumexp(non-top l) - logsumexp(all l) in float64; gap = l_(1) - l_(2). Full 20-candidate procedure
    with s = m and s = -gap (fit order statistics of s, route iff s <= t, same test). Jaccard of the dev omitted set vs the original policy.
(b) fp32 u32: frozen numeric tau applied to u32 (cal k/n/p of that candidate, dev coverage, changed/omitted, Jaccard); full procedure with
    fp32 fit quantiles. MATERIAL CHANGE as defined in PREREG.md. Units without a computed prefill -> that setting/receiver-benchmark is "not computed"."""
import sys
sys.dont_write_bytecode = True
import csv, glob, math, collections
from xfam_common import *
sys.path.insert(0, str(ROOT / 'P2_R1_CPU_20260919T045556Z/src'))
from common_r1 import thresholds, pval, cp999, deploy, GRID, tv
from data_r1 import route_mask
sys.path.insert(0, str(ROOT / 'P2_R5_E13_20260921T031606Z/scripts'))
import e13_settings as E13
C = E13.C
import numpy as np
from scipy.stats import beta
A = X / 'results/analysis_e16_3'; A.mkdir(parents=True, exist_ok=True)
man = X / 'results/MANIFEST_jobB.sha256'
for line in man.read_text().splitlines():
    if line.strip() and not line.startswith('#'):
        h, p = line.split(None, 1); assert sha(X / 'results' / p.strip()) == h, p
REC = {'small': 'qwen3_0_6b', 'X1-Llama': 'qwen3_0_6b', 'medium': 'qwen3_1_7b', 'large': 'qwen3_8b'}
SET23 = [s for s in C.ALL26 if s[0] != 'X2-OLMo']; assert len(SET23) == 23
new = collections.defaultdict(dict)   # (receiver, dtype) -> (ds, id) -> record
for f in sorted(glob.glob(str(X / 'results/e163/*.jsonl'))):
    for r in jl(f):
        if r.get('runtime_error') is None: new[(r['receiver'], r['dtype'])][(r['dataset'], r['id'])] = r


def cp95(k, n): return (float(beta.ppf(.025, k, n - k + 1)) if k > 0 else 0.0, float(beta.ppf(.975, k + 1, n - k)) if k < n else 1.0) if n else (float('nan'),) * 2


def lse(x): x = np.asarray(x, np.float64); m = x.max(); return float(m + np.log(np.exp(x - m).sum()))


def scores(rec):
    l = np.array(list(rec['label_logits'].values()), np.float64); o = np.sort(l)[::-1]; top = int(np.argmax(l))
    return lse(np.delete(l, top)) - lse(l), float(o[0] - o[1])


def ledger(u, d, cuts):
    out = []
    for q, t in zip(GRID, cuts):
        m = route_mask(u, q, t); n = int(m.sum()); k = int(d[m].sum()); out.append(dict(q=q, threshold=t, n=n, k=k, p=pval(k, n), accepted=pval(k, n) <= .001))
    return out


def jac(a, b): return (len(a & b) / len(a | b)) if (a | b) else 1.0


def load(s):
    L = C.load(s); F = E13.load_fit(s); ds = C.BENCH[s[1]]
    fit_u = F['u'] if F is not None else np.asarray(C.load_main()['large', 'OBQA']['fit']['scores']['ProbeMax'], float)
    fit_ids = F['ids'] if F is not None else C.load_main()['large', 'OBQA']['fit']['ids']
    return ds, L, fit_ids, fit_u


rb_rows, set_a, set_b, cert = [], [], [], {}
# ---- per receiver x benchmark: (a) statistics over all units of the three splits; (b) u32 == 0 share
units = collections.defaultdict(dict)   # (receiver, ds) -> id -> stored u
for s in SET23:
    ds, L, fit_ids, fit_u = load(s); rec = REC[s[0]]
    for i, u in zip(fit_ids, fit_u): units[(rec, ds)][i] = float(u)
    for sp in ['cal', 'dev']:
        for i, u in zip(L[sp]['ids'], L[sp]['u']): units[(rec, ds)][i] = float(u)
for (rec, ds), U in sorted(units.items()):
    B = new[(rec, 'bf16')]; F32 = new[(rec, 'fp32')]
    have = [i for i in U if (ds, i) in B]; have32 = [i for i in U if (ds, i) in F32]
    row = dict(receiver=rec, benchmark=ds, units=len(U), bf16_computed=len(have), fp32_computed=len(have32))
    if len(have) == len(U):
        ms, gs = zip(*[scores(B[(ds, i)]) for i in have]); ms, gs = np.array(ms), np.array(gs); u = np.array([U[i] for i in have])
        z = u == 0; row.update(bf16_u_equal_stored=int(sum(B[(ds, i)]['ProbeMax'] == U[i] for i in have)), share_u0=float(z.mean()),
                               max_exp_m_u0=float(np.exp(ms[z]).max()) if z.any() else None, min_exp_m_upos=float(np.exp(ms[~z]).min()) if (~z).any() else None,
                               min_gap_u0=float(gs[z].min()) if z.any() else None,
                               m_units_in_ties=int(sum(c for c in collections.Counter(ms.tolist()).values() if c > 1)), m_tied_values=int(sum(1 for c in collections.Counter(ms.tolist()).values() if c > 1)),
                               gap_units_in_ties=int(sum(c for c in collections.Counter(gs.tolist()).values() if c > 1)), gap_tied_values=int(sum(1 for c in collections.Counter(gs.tolist()).values() if c > 1)))
    else:
        row.update(a_status='not computed (bf16 prefill incomplete)')
    if len(have32) == len(U):
        row.update(share_u32_0=float(np.mean([F32[(ds, i)]['ProbeMax'] == 0 for i in have32])))
    else:
        row.update(b_status=f'not computed (fp32 prefill {len(have32)}/{len(U)})')
    rb_rows.append(row)
# ---- per setting
for s in SET23:
    ds, L, fit_ids, fit_u = load(s); rec = REC[s[0]]; name = C.sname(s); q0 = L['q0']; cuts0 = L['cuts']
    d = {sp: np.array([a != b for a, b in zip(L[sp]['oR'], L[sp]['ob'])], bool) for sp in ['cal', 'dev']}
    dev_ids = L['dev']['ids']; orig_om = set(np.array(dev_ids)[route_mask(L['dev']['u'], q0, cuts0[GRID.index(q0)])]) if q0 > 0 else set()
    B = new[(rec, 'bf16')]; F32 = new[(rec, 'fp32')]
    need = list(fit_ids) + list(L['cal']['ids']) + dev_ids
    # (a)
    ra = dict(setting=name, original_q=q0 if q0 > 0 else 'fallback')
    if all((ds, i) in B for i in need):
        for lab, fn in [('m', lambda i: scores(B[(ds, i)])[0]), ('neg_gap', lambda i: -scores(B[(ds, i)])[1])]:
            sf = np.array([fn(i) for i in fit_ids]); sc = np.array([fn(i) for i in L['cal']['ids']]); sd = np.array([fn(i) for i in dev_ids])
            cuts = thresholds(list(sf)); led = ledger(sc, d['cal'], cuts); q, _ = deploy(led)
            md = route_mask(sd, q, cuts[GRID.index(q)]) if q > 0 else np.zeros(len(sd), bool); n, k = int(md.sum()), int(d['dev'][md].sum()); lo, hi = cp95(k, n)
            ra.update({f'q_{lab}': q if q > 0 else 'fallback', f'dev_coverage_{lab}': n / len(sd), f'dev_changed_{lab}': k, f'dev_omitted_{lab}': n, f'dev_CP95_{lab}': [lo, hi],
                       f'jaccard_{lab}': (jac(set(np.array(dev_ids)[md]), orig_om) if q0 > 0 else None)})
        ra['original_dev_coverage'] = len(orig_om) / len(dev_ids)
    else:
        ra['status'] = 'not computed (bf16 prefill incomplete)'
    set_a.append(ra)
    # (b)
    rbx = dict(setting=name, original_q=q0 if q0 > 0 else 'fallback', original_tau=cuts0[GRID.index(q0)] if q0 > 0 else None)
    if all((ds, i) in F32 for i in need):
        uf = np.array([F32[(ds, i)]['ProbeMax'] for i in fit_ids]); uc = np.array([F32[(ds, i)]['ProbeMax'] for i in L['cal']['ids']]); ud = np.array([F32[(ds, i)]['ProbeMax'] for i in dev_ids])
        if q0 > 0:
            t0 = cuts0[GRID.index(q0)]; mc = route_mask(uc, q0, t0); n, k = int(mc.sum()), int(d['cal'][mc].sum())
            md = route_mask(ud, q0, t0); nd, kd = int(md.sum()), int(d['dev'][md].sum()); lo, hi = cp95(kd, nd)
            rbx.update(cal_n_frozen_tau=n, cal_k_frozen_tau=k, cal_p_frozen_tau=pval(k, n), frozen_tau_still_accepted=pval(k, n) <= .001,
                       dev_coverage_u32=nd / len(ud), dev_coverage_original=len(orig_om) / len(dev_ids), dev_changed_u32=kd, dev_omitted_u32=nd, dev_CP95_u32=[lo, hi],
                       jaccard_u32=jac(set(np.array(dev_ids)[md]), orig_om))
        cuts = thresholds(list(uf)); q, _ = deploy(ledger(uc, d['cal'], cuts)); rbx['q_full_procedure_fp32'] = q if q > 0 else 'fallback'
        reasons = []
        if q0 > 0:
            if not rbx['frozen_tau_still_accepted']: reasons.append('frozen tau not accepted on cal under u32')
            if q != q0: reasons.append(f'full procedure q {q0} -> {q if q > 0 else "fallback"}')
            if abs(rbx['dev_coverage_u32'] - rbx['dev_coverage_original']) > .05: reasons.append('dev coverage moved > 5 points')
        elif q > 0: reasons.append('fallback setting becomes certified')
        rbx['MATERIAL_CHANGE'] = bool(reasons); rbx['material_reasons'] = reasons
    else:
        rbx['status'] = f'not computed (fp32 prefill incomplete: {sum((ds, i) in F32 for i in need)}/{len(need)})'
    set_b.append(rbx)
# medium OBQA C2C also at q=.50 (frozen tau of that candidate), under (b)(i)
s = ('medium', 'OBQA', 'C2C'); ds, L, fit_ids, fit_u = load(s); F32 = new[('qwen3_1_7b', 'fp32')]
if all((ds, i) in F32 for i in list(L['cal']['ids']) + L['dev']['ids']):
    t50 = L['cuts'][GRID.index(.5)]; d = {sp: np.array([a != b for a, b in zip(L[sp]['oR'], L[sp]['ob'])], bool) for sp in ['cal', 'dev']}
    uc = np.array([F32[(ds, i)]['ProbeMax'] for i in L['cal']['ids']]); ud = np.array([F32[(ds, i)]['ProbeMax'] for i in L['dev']['ids']])
    mc = route_mask(uc, .5, t50); n, k = int(mc.sum()), int(d['cal'][mc].sum()); md = route_mask(ud, .5, t50); nd, kd = int(md.sum()), int(d['dev'][md].sum())
    om50 = set(np.array(L['dev']['ids'])[route_mask(L['dev']['u'], .5, t50)])
    set_b.append(dict(setting='medium/OBQA/C2C at q=.50', original_q=.5, original_tau=t50, cal_n_frozen_tau=n, cal_k_frozen_tau=k, cal_p_frozen_tau=pval(k, n),
                      frozen_tau_still_accepted=pval(k, n) <= .001, dev_coverage_u32=nd / len(ud), dev_coverage_original=len(om50) / len(ud), dev_changed_u32=kd, dev_omitted_u32=nd,
                      dev_CP95_u32=list(cp95(kd, nd)), jaccard_u32=jac(set(np.array(L['dev']['ids'])[md]), om50)))
env = {pathlib.Path(f).name: {k: v for k, v in read(f).items() if k in ('receiver', 'dtype', 'sdpa_kernels_first_row', 'sdp_flags', 'tf32', 'attn_implementation')}
       for f in sorted(glob.glob(str(X / 'results/e163/*.env.json')))}
out = dict(utc=utc(), receiver_benchmark=rb_rows, settings_a=set_a, settings_b=set_b, prefill_env=env)
save(A / 'E16_3_RESULTS.json', out)
for n_, rows in [('receiver_benchmark.csv', rb_rows), ('settings_a.csv', set_a), ('settings_b.csv', set_b)]:
    with open(A / n_, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r))); w.writeheader(); w.writerows(rows)
print(json.dumps(out, indent=1, default=str)[:20000])
