"""E20F Step 4 (login node; gold never read): certification from fit + calibration outputs ONLY, with the paper's function (e20f_cert.py:
common_r1 thresholds / pval / cp999 / deploy + data_r1 route_mask + analyze_x3 ledger_rows). Certification reads only fit s2 (the 500 fit
receiver-only s2 values -> 20 thresholds) and calibration s2 + change. Refuses to run if any dev/test output exists or if any fit / calibration
question lacks an error-free row. Writes CERT_E20F.json and CERT_E20F.sha256 (SHA-256 + UTC) at once.
Calibration statistics: 20 candidates (q, tau, n, k, p, accepted, .999 CP upper bound); deployed q or fallback; disagreement k/2,000;
INVALID R / reference; always-omit change rate (q = 1 row); max empirical TPR/FPR over the 20 candidates against C(pi, alpha) =
(1 - pi)(1 - alpha)/(pi alpha), pi = agreement share (E17-5(a) definition); if fallback, the E5-b needed_m rule. Fit (E1) is descriptive only.
usage: e20f_cert_run.py [--dry-run]"""
import sys, json, glob, argparse, pathlib, datetime, math
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e20f_common as FC
from e20f_cert import thresholds, pval, cp999, deploy, GRID, ledger_rows, needed_m, FUNC_SOURCES
from e20_extract import changed, INVALID                                     # pilot module
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true'); a = ap.parse_args()
B = FC.base(a.dry_run); RES = B / 'results'
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
assert not (B / 'CERT_E20F.json').exists(), 'CERT_E20F.json already exists'
dt = list((B / 'records/devtest').glob('*')) if (B / 'records/devtest').exists() else []
assert not dt, f'dev/test outputs already exist: {dt[:3]}'
man = sorted(glob.glob(str(RES / 'OUTPUTS_HASH_fitcal_j*.txt'))); assert man
for hp in man:
    for ln in pathlib.Path(hp).read_text().splitlines():
        if ln.startswith('#'): continue
        h, p = ln.split('  ', 1)
        if p == 'results/E20F_fitcal_rows.jsonl' and hp != man[-1]: continue     # re-merged by a later job; checked in its own manifest
        assert FC.sha(B / p) == h, (hp, p)
rows = FC.jl(RES / 'E20F_fitcal_rows.jsonl')
S = {}
for sp in ['fit', 'cal']:
    rr = [r for r in rows if r['split'] == sp]
    assert len(rr) == FC.N_SPLIT[sp] and all(r['llama'] is not None and r['helper'] is not None for r in rr), f'{sp} incomplete'
    S[sp] = dict(ids=[r['id'] for r in rr], s2=np.array([r['llama']['R']['s2'] for r in rr], float),
                 oR=[r['llama']['R']['answer'] for r in rr], oT=[r['llama']['T']['answer'] for r in rr])
    S[sp]['d'] = np.array([changed(u, v) for u, v in zip(S[sp]['oR'], S[sp]['oT'])], bool)
    assert np.isfinite(S[sp]['s2']).all()
cuts = thresholds(list(S['fit']['s2']))                                          # fit s2 only
C = S['cal']; led = ledger_rows(C['s2'], C['d'], cuts); q, acc = deploy(led)
N, K = len(C['d']), int(C['d'].sum()); A_, Dn = N - K, K
pi = A_ / N; Cpi = (1 - pi) * (1 - .05) / (pi * .05) if 0 < pi < 1 else None
best = -1.0
for r in led:
    if r['n'] == 0 or Dn == 0 or A_ == 0: continue
    best = max(best, float('inf') if r['k'] == 0 else ((r['n'] - r['k']) / A_) / (r['k'] / Dn))
F = S['fit']
cert = dict(utc=utc(), experiment='E20-full', setting='SQuAD v1.1 | helper Qwen2.5-7B-Instruct Text message | receiver Llama-3.1-8B-Instruct | score s2',
            dry_run=a.dry_run, gold_read=False, N_fit=len(F['ids']), N_cal=N,
            ledger=[dict(q=r['q'], tau=r['threshold'], n=r['n'], k=r['k'], p=r['p'], CP999_upper=r['CP999'], accepted=r['accepted']) for r in led],
            accepted_q=acc, deployed_q=q, deployed=q > 0, threshold=(cuts[GRID.index(q)] if q > 0 else None),
            deployed_row=(led[GRID.index(q)] if q > 0 else None),
            cal=dict(disagreements=K, n=N, disagreement_rate=K / N, invalid_R=sum(v == INVALID for v in C['oR']), invalid_ref=sum(v == INVALID for v in C['oT']),
                     always_omit_change_rate=led[-1]['k'] / led[-1]['n'], always_omit_k=led[-1]['k'], always_omit_n=led[-1]['n'],
                     max_TPR_over_FPR='inf' if math.isinf(best) else best, C_pi_alpha=Cpi, pi=pi, max_ge_C=bool(Cpi is not None and best >= Cpi),
                     min_p=min(r['p'] for r in led), min_p_q=min(led, key=lambda r: (r['p'], r['q']))['q']),
            needed_N_cal=(needed_m(led, N) if q == 0 else None),
            fit_descriptive_E1=dict(note='fit reference outputs (E1) are never used by certification', disagreements=int(F['d'].sum()), n=len(F['d']),
                                    invalid_R=sum(v == INVALID for v in F['oR']), invalid_ref=sum(v == INVALID for v in F['oT'])),
            inputs=dict(rows_file='results/E20F_fitcal_rows.jsonl', rows_sha256=FC.sha(RES / 'E20F_fitcal_rows.jsonl'),
                        manifests={pathlib.Path(p).name: FC.sha(p) for p in man}),
            code=dict(e20f_cert_run=FC.sha(__file__), e20f_cert=FC.sha(pathlib.Path(__file__).parent / 'e20f_cert.py'),
                      paper_functions={k: FC.sha(v) for k, v in FUNC_SOURCES.items()}))
cp = B / 'CERT_E20F.json'
cp.write_text(json.dumps(cert, indent=1, allow_nan=False) + '\n')
(B / 'CERT_E20F.sha256').write_text(f'{FC.sha(cp)}  CERT_E20F.json\nhashed_utc: {utc()}\n')
print(json.dumps({k: cert[k] for k in ['deployed_q', 'threshold', 'accepted_q', 'cal', 'needed_N_cal']}, indent=1))
for r in cert['ledger']: print(r)
print((B / 'CERT_E20F.sha256').read_text())
