"""E17-5 on the two E16-5 settings (announced in the E17 pre-registration: "the 2 E16-5 settings are added later from E16 outputs with the same
code"). The E17-5 functions draws/run/summarize/bisect (P2_R7_E17_20260921T183100Z/scripts/e17_5.py) and ledger/auroc (e17_common.py) are
imported unchanged; the per-setting lines of e17_5.py's __main__ block for (a) and (b) are repeated verbatim here with the E16-5 inputs.
Nothing is written into the E17 folder. Inputs (E16-5, gold-free): medium-pair ProbeMax u and the 20 medium thresholds; labels
d = o_R(medium) != o_Text(strong: Qwen2.5-7B messages -> Qwen3-1.7B); N_fit/N_cal = the E16-5 fit/cal representatives; prevalence = cal
disagreement rate; AUROC_dev / AUROC_cal via e17_common.auroc. 2,000 simulations, seed 0; bisection 1,000 simulations per step.
-> results/analysis_e16_5/E17_5_on_E16_5_{inputs,feasibility,binormal}.csv + .json"""
import sys
sys.dont_write_bytecode = True
import csv, time
from xfam_common import *
sys.path.insert(0, str(ROOT / 'P2_R7_E17_20260921T183100Z/scripts'))
import e17_5 as E175
from e17_common import ledger, auroc
import numpy as np
A = X / 'results/analysis_e16_5'
T = {(r['dataset'], r['id']): r for f in sorted((X / 'results/e16_5').glob('shard*.jsonl')) for r in jl(f)}
man = X / 'results/MANIFEST_jobA.sha256'
for line in man.read_text().splitlines():
    if line.strip() and not line.startswith('#'):
        h, p = line.split(None, 1); assert sha(X / 'results' / p.strip()) == h, p
e16_5 = read(A / 'E16_5_PRE_GOLD.json')['results']
IN, FA, OUT = [], [], []
for ds in ['obqa', 'arc']:
    L = {}
    for sp in ['fit', 'cal', 'dev']:
        reps = read(MED.parent / f'splits/{ds}_{sp}_representatives.json')
        Ra = {r['id']: r for r in jl(MED / f'actions/{ds}_{sp}.jsonl') if r['action'] == 'R'}; Pm = {r['id']: r for r in jl(MED / f'probes/{ds}_{sp}.jsonl')}
        L[sp] = dict(u=np.array([Pm[i]['ProbeMax'] for i in reps], float), d=np.array([Ra[i]['answer'] != T[(ds, i)]['T']['parsed'] for i in reps], bool))
    cuts = read(MED / f'thresholds/{ds}.json')['thresholds']
    name = f'strong-helper/{ds.upper() if ds == "obqa" else "ARC"}/Text (E16-5)'
    # ---- verbatim from e17_5.py __main__ (a)/(b) inputs, with the E16-5 arrays
    cu, cd = L['cal']['u'], L['cal']['d']
    led = ledger(cu, cd, cuts)
    Nc = len(cu)
    prev = float(cd.mean())
    IN.append(dict(setting=name, observed='fallback' if e16_5[ds]['deployed_q'] == 'fallback' else 'certify', q0=0.0 if e16_5[ds]['deployed_q'] == 'fallback' else e16_5[ds]['deployed_q'],
                   N_fit=len(L['fit']['u']), N_cal=Nc, prevalence_cal=prev, AUROC_dev=auroc(L['dev']['d'], L['dev']['u']), AUROC_cal=auroc(cd, cu),
                   share_u0_cal=float((cu == 0).mean()), share_u0_dev=float((L['dev']['u'] == 0).mean())))
    Aa, Dn = int((~cd).sum()), int(cd.sum())
    pi = 1 - prev; Cc = (1 - pi) * (1 - E175.A_) / (pi * E175.A_)
    best, anyle = -1.0, False
    for r in led:
        if r['n'] == 0: continue
        tpr, fpr = (r['n'] - r['k']) / Aa, r['k'] / Dn
        ratio = float('inf') if fpr == 0 else tpr / fpr
        best = max(best, ratio); anyle |= r['k'] / r['n'] <= E175.A_
    FA.append(dict(setting=name, observed=IN[-1]['observed'], pi=pi, C=Cc, max_TPR_over_FPR=best, max_ge_C=best >= Cc, some_candidate_k_over_n_le_05=anyle,
                   equivalence_holds=(best >= Cc) == anyle))
    r = IN[-1]; row = dict(r); t0 = time.time()
    for tag, a in [('dev', r['AUROC_dev']), ('cal', r['AUROC_cal'])]:
        dr = E175.draws(np.random.default_rng(0), 2000, r['N_fit'], r['N_cal'], r['prevalence_cal'])
        P, mode, mc = E175.summarize(*E175.run(dr, r['prevalence_cal'], a, r['N_fit'], r['N_cal']))
        row.update({f'P_certify_{tag}AUROC': P, f'modal_q_{tag}AUROC': mode, f'median_coverage_when_certified_{tag}AUROC': mc, f'predicted_{tag}AUROC': 'certify' if P >= .5 else 'fallback'})
        row[f'agree_{tag}AUROC'] = row[f'predicted_{tag}AUROC'] == r['observed']
    txt, val, steps = E175.bisect(r['prevalence_cal'], r['N_fit'], r['N_cal'])
    row.update(AUROC_at_P50=txt, AUROC_at_P50_value=val, bisection_steps=';'.join(f'{a:.4f}:{p:.3f}' for a, p in steps))
    OUT.append(row); print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items() if k != 'bisection_steps'}, f'{time.time() - t0:.1f}s', flush=True)
for n_, rows in [('E17_5_on_E16_5_inputs.csv', IN), ('E17_5_on_E16_5_feasibility.csv', FA), ('E17_5_on_E16_5_binormal.csv', OUT)]:
    with open(A / n_, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r))); w.writeheader(); w.writerows(rows)
save(A / 'E17_5_on_E16_5.json', dict(utc=utc(), e17_5_source_sha256=sha(ROOT / 'P2_R7_E17_20260921T183100Z/scripts/e17_5.py'),
                                     e17_common_sha256=sha(ROOT / 'P2_R7_E17_20260921T183100Z/scripts/e17_common.py'), inputs=IN, feasibility=FA, binormal=OUT))
print(json.dumps(FA, indent=1, default=str))
