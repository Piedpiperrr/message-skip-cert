"""E19-4: prospective prediction. The frozen E15-1 predictor (P2_R6_E15_.../scripts/e15_1.py) is executed byte-identical: its source is
exec'd with a substitute `e15_common` module whose inputs are redirected (settings list, loaders, output writer). Nothing in e15_1.py changes.
(1) verification: original 25 settings -> must reproduce E15's stored e15_1_candidates.csv / e15_1_per_setting.csv / e15_1_summary.csv;
(2) new settings: Llama-3.1-8B OBQA/ARC Text (X3) and strong-helper OBQA/ARC Text (E16-5). Text+fact and GSM8K: N/A rows.
Timing check for E15-1 and for the E17-5 binormal model."""
from e19_common import *
import types, glob, os, io

T0 = utc()
print('E19-4 start', T0)
E15D = ROOT / 'P2_R6_E15_20260921T072336Z'
SRC = E15D / 'scripts/e15_1.py'
FROZEN_SHA = 'd6bfc055f3db73af06e8c8e61bfcc9d277c54125ae74c5ed6db622c3e26ab485'   # recorded in PREREG_E19.md
code_sha = sha(SRC)
assert code_sha == FROZEN_SHA, code_sha
code = compile(open(SRC).read(), str(SRC), 'exec')
OUT = {}


def run_frozen(tag, overrides):
    mod = types.ModuleType('e15_common')
    mod.__dict__.update({k: v for k, v in E15.__dict__.items() if not k.startswith('__')})

    def csvout_redirect(name, rows):
        rows = list(rows)
        OUT[tag, name] = rows
        csvout(f'E19_4_{tag}_{name}', rows)
    mod.csvout = csvout_redirect
    mod.READ = []
    mod.__dict__.update(overrides)
    saved = sys.modules.get('e15_common')
    sys.modules['e15_common'] = mod
    try:
        ns = {'__name__': f'e15_1_{tag}'}
        buf = io.StringIO()
        _stdout = sys.stdout; sys.stdout = buf
        try:
            exec(code, ns)
        except KeyError as e:
            # the frozen script's summary block (after the per-setting loop) needs Table-2 saving fields for every deployed
            # setting; the new deployed settings (Llama) have none in its saving model -> keep its completed per-setting rows
            ns['__exc__'] = f'KeyError {e} raised in e15_1.py after the per-setting loop (summary block)'
            OUT[tag, 'e15_1_per_setting.csv'] = ns['per']
            OUT[tag, 'e15_1_candidates.csv'] = ns['cand']
            csvout(f'E19_4_{tag}_e15_1_per_setting.csv', ns['per'])
            csvout(f'E19_4_{tag}_e15_1_candidates.csv', ns['cand'])
        finally:
            sys.stdout = _stdout
        (STAGE / f'logs/e19_4_{tag}_stdout.log').write_text(buf.getvalue() + '\n' + ns.get('__exc__', 'completed without exception') + '\n')
    finally:
        sys.modules['e15_common'] = saved
    return ns


# ---------------------------------------------------------------- (1) verification on the original 25 settings
run_frozen('verify25', {})
CHK = []


def same_csv(stored, rows, cols=None):
    S = csvread(stored)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r))); w.writeheader(); w.writerows(rows)
    buf.seek(0)
    N = list(csv.DictReader(buf))
    if cols: S = [{c: r.get(c) for c in cols} for r in S]; N = [{c: r.get(c) for c in cols} for r in N]
    return S == N


for name in ['e15_1_candidates.csv', 'e15_1_per_setting.csv', 'e15_1_summary.csv', 'e15_1_checks.csv']:
    ok = same_csv(E15D / 'results' / name, OUT['verify25', name])
    CHK.append(dict(check=f'frozen e15_1.py re-run on the original 25 settings reproduces stored {name} (all columns, all rows)',
                    status='PASS' if ok else 'FAIL'))
    print(CHK[-1])

# ---------------------------------------------------------------- (2) new settings
SLL = [LLO, LLA]
MEDX = ROOT / 'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z'
STRONG = [('strong-helper', 'OBQA', 'Text'), ('strong-helper', 'ARC', 'Text')]
T5 = {(r['dataset'], r['id']): r for f in sorted((E16 / 'results/e16_5').glob('shard*.jsonl')) for r in jl(f)}


def nz(x): return INV if x in (None, INV) else x


_L = {}


def load_new(s):
    if s in _L: return _L[s]
    if s[0] == 'X3-Llama8B':
        L = E17.load(s)
        out = dict(fit=L['fit'], cal=L['cal'], dev=L['dev'], cuts=L['cuts'], q0=L['q0'])
    else:
        ds = {'OBQA': 'obqa', 'ARC': 'arc'}[s[1]]
        out = {}
        for sp in ['fit', 'cal', 'dev']:
            reps = read(MEDX.parent / f'splits/{ds}_{sp}_representatives.json')
            Ra = {r['id']: r for r in jl(MEDX / f'actions/{ds}_{sp}.jsonl') if r['action'] == 'R'}
            Pm = {r['id']: r for r in jl(MEDX / f'probes/{ds}_{sp}.jsonl')}
            assert all(T5[ds, i].get('runtime_error') is None for i in reps)
            out[sp] = dict(ids=reps, u=np.array([Pm[i]['ProbeMax'] for i in reps], float),
                           oR=[nz(Ra[i]['answer']) for i in reps], ob=[nz(T5[ds, i]['T']['parsed']) for i in reps])
        cuts = C.thresholds(list(out['fit']['u']))
        stored = read(MEDX / f'thresholds/{ds}.json')['thresholds']
        assert [C.tv(x) for x in cuts] == [C.tv(x) for x in stored]
        out['cuts'] = cuts
        out['q0'] = 0.0   # E16-5 observed outcome: fallback on both benchmarks (E16_5_PRE_GOLD.json)
    _L[s] = out
    return out


class CW:
    """C with only `load` and `sname` redirected to the new settings; every other attribute is the real loader module."""
    def __getattr__(self, a): return getattr(C, a)
    def load(self, s): return load_new(s)
    def sname(self, s): return f'{s[0]}/{s[1]}/{s[2]}'


NEW = SLL + STRONG
# E16-5 reproduction checks (cal disagreement, fallback) against E16's gold-free file
pg = read(E16 / 'results/analysis_e16_5/E16_5_PRE_GOLD.json')['results']
for s in STRONG:
    ds = s[1].lower(); L = load_new(s)
    d = np.array([a != b for a, b in zip(L['cal']['oR'], L['cal']['ob'])])
    led = C.ledger_rows(L['cal']['u'], d, L['cuts'])
    q, _ = C.largest_accepted(led)
    CHK.append(dict(check=f'{s}: cal disagreements / deployed == E16_5_PRE_GOLD.json',
                    status='PASS' if (int(d.sum()), q) == (pg[ds]['cal_disagreements'], 0.0) and pg[ds]['deployed_q'] == 'fallback' else 'FAIL',
                    detail=f"{int(d.sum())} vs {pg[ds]['cal_disagreements']}; q={q}"))
    print(CHK[-1])
_ns_new = run_frozen('new', {'SET25': NEW, 'DEPLOY8': [], 'C': CW(), 'load_fit': lambda s: load_new(s)['fit'],
                   'sname': lambda s: f'{s[0]}/{s[1]}/{s[2]}'})
per = {r['setting']: r for r in OUT['new', 'e15_1_per_setting.csv']}
NS_NEW = _ns_new
CHK.append(dict(check='frozen e15_1.py on the new settings: per-setting loop completed (all 4 settings, 20 candidates each)',
                status='PASS' if len(per) == 4 and len(OUT['new', 'e15_1_candidates.csv']) == 80 else 'FAIL',
                detail=NS_NEW.get('__exc__', 'completed without exception')))

# saving model for the Llama settings (component latencies exist: X3 dev R/T/P latency_ms); same formula as e15_1.py
x3 = {}
for f in sorted(glob.glob(str(X3 / 'results/runs/chain_*.jsonl'))):
    for r in jl(f): x3[r['dataset'], r['id']] = r
SAV = {}
for s, meas_key in [(LLO, 'Llama-3.1-8B/OBQA/Text'), (LLA, 'Llama-3.1-8B/ARC/Text')]:
    ds = s[1].lower(); L = load_new(s)
    rr = [x3[ds, i] for i in L['dev']['ids']]
    cb = float(np.mean([r['T']['latency_ms'] for r in rr])); cR = float(np.mean([r['R']['latency_ms'] for r in rr]))
    cs = float(np.mean([r['P']['latency_ms'] for r in rr]))
    R = replay(meas_key)
    meas = float(np.mean([R['fx'][i]['latency_ms'] - R['po'][i]['latency_ms'] for i in R['ids']]))
    kp = float(np.mean([route_R(R['po'][i]) for i in R['ids']]))
    p = per[f'{s[0]}/{s[1]}/{s[2]}']
    pcov = float(p['predicted_fit_coverage']) if p['predicted_fit_coverage'] not in ('', None) else None
    pf = pcov * (cb - cR) - cs if pcov is not None else 0.0
    pp = kp * (cb - cR) - cs
    SAV[s] = dict(c_b_mean_ms=cb, c_R_mean_ms=cR, c_s_mean_ms=cs, gap_ms=cb - cR, panel_coverage=kp, measured_saving_ms=meas,
                  measured_source=R['source'] + ' (E16-4, second configuration, all requests)',
                  pred_saving_fitcov_ms=pf, abs_err_fitcov_ms=abs(pf - meas), rel_err_fitcov=abs(pf - meas) / abs(meas),
                  pred_saving_panelcov_ms=pp, abs_err_panelcov_ms=abs(pp - meas), rel_err_panelcov=abs(pp - meas) / abs(meas),
                  component_source='X3 results/runs/chain_*.jsonl dev T/R/P latency_ms (X3 run, not a latency replay)')


# ---------------------------------------------------------------- timing
def minutc(files, pred=lambda r: True):
    m = None
    for f in files:
        for r in jl(f):
            if pred(r) and r.get('utc'):
                t = r['utc']
                m = t if m is None or t < m else m
    return m


def iso(t):  # normalise to ...Z seconds
    return datetime.datetime.fromisoformat(t.replace('Z', '+00:00')).astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def mt(p): return datetime.datetime.fromtimestamp(os.path.getmtime(p), datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


E15_HASH = '2026-09-21T07:23:54Z'
E17_HASH = '2026-09-21T18:31:26Z'
x3smoke = minutc([X3 / 'results/smoke/smoke_llama31_8b.jsonl'])
FIRST = {}
for s in SLL:
    ds = s[1].lower()
    runs = minutc(sorted(glob.glob(str(X3 / 'results/runs/chain_*.jsonl'))), lambda r, ds=ds: r['dataset'] == ds)
    FIRST[s] = (min(iso(runs), iso(x3smoke)), f'min(X3 runs {ds} {iso(runs)}, X3 smoke (Llama-3.1-8B, both datasets) {iso(x3smoke)})')
for s in STRONG:
    ds = s[1].lower()
    t = minutc(sorted((E16 / 'results/e16_5').glob('shard*.jsonl')), lambda r, ds=ds: r['dataset'] == ds)
    smoke = E16 / 'records/work/v3b_strong_smoke.jsonl'
    gate = E16 / 'results/markers/v3b.gate'
    FIRST[s] = ('2026-09-21T18:58:58.000000Z', f'conservative: E16 RESULTS.md "first E16 model output 18:58:58Z (Job A)"; E16-5 records {ds} '
                f'min utc {iso(t)}; V3b strong-helper smoke (8 OBQA + 8 ARC fit rows) gate marker mtime {mt(gate)}; '
                f'records/work/v3b_strong_smoke.jsonl (mtime {mt(smoke)}) is its input worklist (helper messages only, no receiver output)')
e6m = sorted((ROOT / 'P2_R2_GPU_20260919T220941Z/e6/main').glob('e6_shard*.jsonl'))
e10m = sorted((ROOT / 'P2_R4_E10_20260920T225954Z/records').glob('main_rank*.jsonl')) + sorted((ROOT / 'P2_R4_E10_20260920T225954Z/records').glob('smoke_rank*.jsonl'))
e10t = minutc(e10m)
NA = {'large/OBQA/Text+fact': f"no utc field in e6/main records; earliest shard mtime {min(mt(p) for p in e6m)}",
      'large/GSM8K/Text (E10)': f"E10 records min utc {iso(e10t) if e10t else 'n/a'}; earliest file mtime {min(mt(p) for p in e10m)}"}


def before(a, b):  # a < b for ISO strings with Z
    fa = datetime.datetime.fromisoformat(a.replace('Z', '+00:00')); fb = datetime.datetime.fromisoformat(b.replace('Z', '+00:00'))
    return fa < fb


b5 = {r['setting']: r for r in csvread(E16 / 'results/analysis_e16_5/E17_5_on_E16_5_binormal.csv')}
ROWS = []
for s in NEW:
    nm = f'{s[0]}/{s[1]}/{s[2]}'
    p = per[nm]
    first, fsrc = FIRST[s]
    row = dict(predictor='E15-1 fit-split plug-in (frozen e15_1.py)', setting=nm, actual_outcome=p['actual_outcome'], actual_q=p['actual_q'],
               predicted_outcome=p['predicted_outcome'], q_hat=p['q_hat'], correct=p['outcome_match'],
               grid_steps_qhat_minus_q=p.get('grid_steps_qhat_minus_q', ''), actual_dev_coverage=p.get('actual_dev_coverage', ''),
               predicted_fit_coverage=p['predicted_fit_coverage'], abs_coverage_error=p.get('abs_coverage_error', ''),
               predictor_hash_utc=E15_HASH, predictor_hash_source='P2_R6_E15_.../PREREG_E15.sha256 (rule text); e15_1.py mtime ' + mt(SRC),
               first_output_utc=first, first_output_source=fsrc, prospective=before(E15_HASH, first))
    row.update(SAV.get(s, {}))
    ROWS.append(row)
for nm, why in NA.items():
    ROWS.append(dict(predictor='E15-1 fit-split plug-in (frozen e15_1.py)', setting=nm, actual_outcome='deploy (q=.75)' if 'fact' in nm else 'see E10',
                     predicted_outcome='N/A (no fit-split reference outputs)', correct='N/A', first_output_source=why, prospective='N/A'))
# E17-5 binormal timing on the E16-5 settings
for s in STRONG:
    nm = f'strong-helper/{s[1]}/Text (E16-5)'
    b = b5[nm]
    first, fsrc = FIRST[s]
    ROWS.append(dict(predictor='E17-5 binormal (dev AUROC; certify iff P(certify) >= .5)', setting=nm, actual_outcome=('deploy' if b['observed'] == 'certify' else 'fallback'),
                     predicted_outcome=('deploy' if float(b['P_certify_devAUROC']) >= .5 else 'fallback'),
                     P_certify=b['P_certify_devAUROC'],
                     correct=(('deploy' if float(b['P_certify_devAUROC']) >= .5 else 'fallback') == ('deploy' if b['observed'] == 'certify' else 'fallback')),
                     predictor_hash_utc=E17_HASH, predictor_hash_source='P2_R7_E17_.../PREREG.sha256',
                     first_output_utc=first, first_output_source=fsrc, prospective=before(E17_HASH, first),
                     prediction_source=str(E16 / 'results/analysis_e16_5/E17_5_on_E16_5_binormal.csv')))
for r in ROWS: r['label'] = LABEL
summ = []
for pred in ['E15-1 fit-split plug-in (frozen e15_1.py)', 'E17-5 binormal (dev AUROC; certify iff P(certify) >= .5)']:
    rr = [r for r in ROWS if r['predictor'] == pred and r['correct'] != 'N/A']
    pro = [r for r in rr if r['prospective'] is True]
    non = [r for r in rr if r['prospective'] is False]
    summ.append(dict(predictor=pred, prospective_correct=sum(r['correct'] in (True, 'True') for r in pro), prospective_n=len(pro),
                     prospective_settings=';'.join(r['setting'] for r in pro),
                     nonprospective_correct=sum(r['correct'] in (True, 'True') for r in non), nonprospective_n=len(non),
                     nonprospective_settings=';'.join(r['setting'] for r in non), label=LABEL))
for r in ROWS: print({k: v for k, v in r.items() if k not in ('label',)})
for r in summ: print(r)
CHK.append(dict(check='e15_1.py SHA-256 == value recorded in PREREG_E19.md', status='PASS' if code_sha == FROZEN_SHA else 'FAIL', detail=code_sha))
csvout('E19_4_prospective.csv', ROWS)
csvout('E19_4_summary.csv', summ)
csvout('E19_4_checks.csv', CHK)
assert all(c['status'] == 'PASS' for c in CHK), CHK
json.dump(dict(start_utc=T0, end_utc=utc(), e15_1_sha256=code_sha, files_read=READ), open(STAGE / 'logs/e19_4_run.json', 'w'), indent=1)
print('E19-4 done', utc())
