"""E20F certification functions = the paper's, unchanged (as used for X3 Llama-8B and by E16/E17):
P2_R1_CPU_20260919T045556Z/src/common_r1.py thresholds / pval / cp999 / deploy / GRID / tv and data_r1.py route_mask (imported, hashes
checked); ledger_rows = verbatim copy of P2_R6_X3_20260921T052602Z/src/analyze_x3.py ledger_rows (= r2_common.ledger_rows), and needed_m =
verbatim copy of P2_R7_E16_20260921T184114Z/src/analyze_e16_5.py needed_m (E5-b rule); both copies are asserted equal to the source text.
Run as a script: G4 reproduction on the stored X3 Llama-8B OBQA fit + calibration records (q = .60; 21 changes among 800 omitted;
p = 5.7e-4) -> notes/G4_CERT_REPRO.json."""
import sys, json, hashlib, pathlib, ast, glob
sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[2]
R1 = ROOT / 'P2_R1_CPU_20260919T045556Z/src'
X3 = ROOT / 'P2_R6_X3_20260921T052602Z'
E16 = ROOT / 'P2_R7_E16_20260921T184114Z/src/analyze_e16_5.py'
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
sys.path.insert(0, str(R1))
from common_r1 import thresholds, pval, cp999, deploy, GRID, tv   # noqa: E402
from data_r1 import route_mask                                     # noqa: E402
import numpy as np                                                 # noqa: E402
from scipy.stats import binom                                      # noqa: E402

FUNC_SOURCES = {'common_r1.py': str(R1 / 'common_r1.py'), 'data_r1.py': str(R1 / 'data_r1.py'), 'analyze_x3.py': str(X3 / 'src/analyze_x3.py'),
                'analyze_e16_5.py': str(E16)}


def ledger_rows(u_cal, d_cal, cuts, keep=None):   # = r2_common.ledger_rows (E5-b / E11-a / E13)
    if keep is not None: u_cal, d_cal = u_cal[keep], d_cal[keep]
    rows = []
    for q, t in zip(GRID, cuts):
        m = route_mask(u_cal, q, t); n = int(m.sum()); k = int(d_cal[m].sum())
        rows.append(dict(q=q, threshold=t, N=len(u_cal), n=n, k=k, p=pval(k, n), CP999=cp999(k, n), accepted=pval(k, n) <= .001))
    return rows


def needed_m(rows, N_cal):   # E5-b rule (P2_R2_CPU scripts/e5b.py needed_m)
    best = min(rows, key=lambda r: (r['p'], r['q'])); n, k = best['n'], best['k']
    if n == 0: return dict(min_p_q=best['q'], needed='unreachable (n=0 at the smallest-p candidate)')
    r = k / n
    if r >= .05: return dict(min_p_q=best['q'], r=r, needed='unreachable (r >= .05)')
    m = 1
    while m < 2_000_000 and binom.cdf(int(np.floor(r * m)), m, .05) > .001: m += 1
    return dict(min_p_q=best['q'], r=r, m=m, needed_N_cal=round(m * N_cal / n)) if m < 2_000_000 else dict(min_p_q=best['q'], r=r, needed='unreachable (m > 2e6)')


def _src(path, name):
    t = pathlib.Path(path).read_text(); fn = next(n for n in ast.walk(ast.parse(t)) if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(t, fn)


_me = pathlib.Path(__file__).read_text()
for _name, _path in [('ledger_rows', X3 / 'src/analyze_x3.py'), ('needed_m', E16)]:
    assert _src(_path, _name) == _src(__file__, _name), f'{_name} copy differs from {_path}'

if __name__ == '__main__':
    S = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(X3 / 'src'))
    from xfam_common import jl                                     # noqa: E402
    out = {}
    for f in sorted(glob.glob(str(X3 / 'results/runs/chain_*.jsonl'))):
        for r in jl(f):
            if r['dataset'] == 'obqa': assert r['id'] not in out; out[r['id']] = r
    ans = lambda r, a: (r[a]['parsed'] if r.get('runtime_error') is None else 'INVALID')   # = analyze_x3 ans
    D = {}
    for sp in ['fit', 'cal']:
        reps = [r['id'] for r in jl(X3 / f'records/populations/obqa_{sp}.jsonl') if r['representative']]
        rr = [out[i] for i in reps]
        D[sp] = dict(n=len(rr), u=np.array([r['P']['ProbeMax'] for r in rr], float),
                     d=np.array([ans(r, 'R') for r in rr], object) != np.array([ans(r, 'T') for r in rr], object))
    cuts = thresholds(list(D['fit']['u'])); led = ledger_rows(D['cal']['u'], D['cal']['d'], cuts); q, acc = deploy(led)
    row = led[GRID.index(q)]
    stored = [l.split(',') for l in (X3 / 'results/analysis/certification_ledger_40.csv').read_text().splitlines() if l.startswith('obqa/Text,')]
    st = next(s for s in stored if float(s[1]) == q)
    ok = q == .6 and row['n'] == 800 and row['k'] == 21 and abs(row['p'] - 5.7e-4) < 5e-5 and repr(row['p']) == st[6] and \
        all(repr(r['p']) == s[6] and str(r['n']) == s[4] and str(r['k']) == s[5] for r, s in zip(led, stored))
    res = dict(N_fit=D['fit']['n'], N_cal=D['cal']['n'], deployed_q=q, accepted=acc, n=row['n'], k=row['k'], p=row['p'],
               all_20_rows_equal_stored_csv=all(repr(r['p']) == s[6] and str(r['n']) == s[4] and str(r['k']) == s[5] for r, s in zip(led, stored)),
               PASS=bool(ok), function_files={k: dict(path=v, sha256=sha(v)) for k, v in FUNC_SOURCES.items()},
               this_module=dict(path=str(pathlib.Path(__file__).resolve()), sha256=sha(__file__)))
    (S / 'notes/G4_CERT_REPRO.json').write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps({k: v for k, v in res.items() if k != 'function_files'}, indent=0))
    sys.exit(0 if ok else 1)
