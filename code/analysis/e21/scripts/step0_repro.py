"""E21 Step 0: reproduction checks (a)-(g) before PREREG.md is hashed; (h) is scripts/step0h_exposure_scan.py.
(a) frozen change-rate test recomputed from stored calibration outputs (E17 ledger on the E17 loader) vs the stored ledgers
    (R1 common_r1.ledgers(): BND / MED / MMLU calibration CSVs; E6_LEDGER.csv; X3 certification_ledger_40.csv); largest accepted = frozen q;
    the p-values quoted in the request.
(b) dev omitted/changed at the frozen q (vs E19 REPRO values) and dev accuracies (gold) vs the request / E13 PAPER_DEV.
(c) out-of-sample omitted/changed at the frozen q (held-out 744, E16 routes, sealed ARC), also vs the stored route flags.
(d) dev AUROC (ties 1/2, E17.auroc = sklearn) vs the paper (3 dp, |diff| <= 5e-4) and vs the stored unrounded values.
(e) E13-3 gain retention at alpha = .05. (f) E19-1 panel savings (net, all requests) of the six E21-1 policies.
(g) E5-c change decomposition of V1 vs R on large/OBQA.
"""
from e21_common import *
import common_r1

T0 = utc()
CHECKS = []


def check(item, name, expected, observed, source, ok=None):
    ok = (expected == observed) if ok is None else ok
    CHECKS.append(dict(item=item, check=name, expected=json.dumps(expected, default=str), observed=json.dumps(observed, default=str),
                       status='PASS' if ok else 'FAIL', source=str(source)))
    print(f"[{'PASS' if ok else 'FAIL'}] ({item}) {name}: expected {expected} observed {observed}", flush=True)


# ------------------------------------------------------------------ (a)
KEYS11 = ['large/OBQA/Text', 'large/OBQA/C2C', 'large/ARC/Text', 'large/ARC/C2C', 'large/MMLU-Pro/Text', 'large/MMLU-Pro/C2C',
          'medium/OBQA/C2C q=.55', 'medium/ARC/C2C', 'large/OBQA/Text+fact', 'Llama-3.1-8B/OBQA/Text', 'Llama-3.1-8B/ARC/Text']
STORED = common_r1.ledgers()
E6L = ROOT / 'P2_R2_GPU_20260919T220941Z/e6/analysis/E6_LEDGER.csv'
X3L = E19.X3 / 'results/analysis/certification_ledger_40.csv'
x3rows = csvread(X3L)
KNOWN_P = {'large/OBQA/Text+fact': (22, 999, '4.8e-06'), 'medium/OBQA/C2C q=.55': (19, 739, '6.9e-04'),
           'Llama-3.1-8B/OBQA/Text': (21, 800, '5.7e-04'), 'Llama-3.1-8B/ARC/Text': (4, 320, '3.15e-04')}
LEDGER_OUT = []
for key in KEYS11:
    s, q = POLD[key]
    L = E17.load(s)
    rows = E17.ledger(L['cal']['u'], L['cal']['d'], L['cuts'])
    qd, _ = E17.deployed(rows)
    check('a', f'{key}: largest accepted candidate = frozen q', q, qd, 'recomputed: E17.ledger on E17.load cal split')
    if key == 'large/OBQA/Text+fact':
        st = [dict(q=float(r['q']), n=int(r['n']), k=int(r['k'])) for r in csvread(E6L)]
        src = E6L
    elif key.startswith('Llama'):
        tag = 'obqa/Text' if 'OBQA' in key else 'arc/Text'
        st = [dict(q=float(r['q']), n=int(r['n']), k=int(r['k'])) for r in x3rows if r['setting'] == tag]
        src = X3L
    else:
        st = [dict(q=r['q'], n=r['n'], k=r['k']) for r in STORED[s]]
        src = STORED[s][0]['source']
    check('a', f'{key}: 20 calibration rows (q, n, k) = stored ledger', [(r['q'], r['n'], r['k']) for r in st],
          [(r['q'], r['n'], r['k']) for r in rows], src)
    fr = next(r for r in rows if abs(r['q'] - q) < 1e-9)
    if key in KNOWN_P:
        k, n, ps = KNOWN_P[key]
        sig = len(ps.split('e')[0].replace('.', '')) - 1
        check('a', f'{key}: frozen-q row k/n and p (request value)', [k, n, ps], [fr['k'], fr['n'], f"{fr['p']:.{sig}e}"], 'request')
    for r in rows:
        LEDGER_OUT.append(dict(policy=key, q=r['q'], threshold=r['threshold'], n=r['n'], k=r['k'], p=r['p'], accepted=r['accepted'],
                               frozen_q=q, label=LABEL))

# ------------------------------------------------------------------ (b)
E19DEV = {'large/OBQA/Text': [572, 19], 'large/OBQA/C2C': [572, 13], 'large/ARC/Text': [284, 9], 'large/ARC/C2C': [270, 3],
          'large/MMLU-Pro/Text': [1069, 40], 'large/MMLU-Pro/C2C': [1069, 37], 'medium/OBQA/C2C q=.55': [390, 11],
          'medium/ARC/C2C': [189, 4], 'large/OBQA/Text+fact': [536, 13], 'Llama-3.1-8B/OBQA/Text': [438, 7],
          'Llama-3.1-8B/ARC/Text': [206, 4]}
for key in KEYS11:
    D = dev(key)
    check('b', f'{key}: dev omitted/changed at frozen q', E19DEV[key], [int(D['m'].sum()), int(D['d'][D['m']].sum())],
          E19.STAGE / 'REPRO.md')
# accuracies: R / reference / frozen policy (request values; ARC, MMLU-Pro and Text+fact policy from E13 item3 PAPER_DEV)
ACC = {'large/OBQA/Text': [617, 645, 638], 'large/ARC/Text': [268, 274, 270], 'large/MMLU-Pro/Text': [1282, 1319, 1321],
       'large/OBQA/Text+fact': [617, 670, 660], 'Llama-3.1-8B/OBQA/Text': [603, 636, 638], 'Llama-3.1-8B/ARC/Text': [239, 260, 258]}
DEVACC = {}
for name, key, nominal, _ in SET6:
    X = split_arrays(key, 'dev')
    D = dev(key)
    assert X['ids'] == D['ids']
    pol = np.where(D['m'], X['oR'], X['ob'])
    obs = [int((X['oR'] == X['y']).sum()), int((X['ob'] == X['y']).sum()), int((pol == X['y']).sum())]
    DEVACC[key] = obs
    check('b', f'{key}: dev correct R / reference / frozen policy', ACC[key], obs,
          'request; P2_R5_E13.../scripts/item3.py PAPER_DEV')

# ------------------------------------------------------------------ (c)
EXPO = {'large/OBQA/Text': [595, 12], 'large/OBQA/Text+fact': [558, 16], 'Llama-3.1-8B/OBQA/Text': [440, 3],
        'Llama-3.1-8B/ARC/Text': [794, 15], 'large/ARC/Text': [1100, 20]}
for key, exp in EXPO.items():
    O = oos(key)
    tau = dev(key)['tau']
    m = O['u'] <= tau
    check('c', f'{key}: {O["name"]} omit iff u <= frozen tau equals stored route flag', 0, int((m != O['frozen_omitted']).sum()), O['source'])
    assert O['R_available'][m].all()
    ch = int(np.array([a != b for a, b in zip(O['oR'][m], O['ob'][m])]).sum())
    check('c', f'{key}: {O["name"]} omitted/changed at frozen q', exp, [int(m.sum()), ch], O['source'])

# ------------------------------------------------------------------ (d)
PAPER_AUC = {'medium/OBQA/C2C q=.55': .840, 'medium/ARC/C2C': .910, 'large/OBQA/Text': .873, 'large/OBQA/C2C': .883,
             'large/ARC/Text': .952, 'large/ARC/C2C': .909, 'large/MMLU-Pro/Text': .821, 'large/MMLU-Pro/C2C': .846,
             'large/OBQA/Text+fact': .889, 'Llama-3.1-8B/OBQA/Text': .8745, 'Llama-3.1-8B/ARC/Text': .8804}
E175 = {r['setting']: float(r['AUROC_dev']) for r in csvread(ROOT / 'P2_R7_E17_20260921T183100Z/results/E17_5_inputs.csv')}
for key, pv in PAPER_AUC.items():
    D = dev(key)
    a = E17.auroc(D['d'], D['u'])
    check('d', f'{key}: dev AUROC vs paper {pv} (|diff| <= 5e-4)', pv, round(a, 6), 'paper tab_dev_full.tex / request', ok=abs(a - pv) <= 5e-4)
    check('d', f'{key}: dev AUROC vs stored unrounded (E17_5_inputs.csv)', E175[C.sname(setting_of(key))], a,
          ROOT / 'P2_R7_E17_20260921T183100Z/results/E17_5_inputs.csv', ok=abs(a - E175[C.sname(setting_of(key))]) < 1e-12)
SQ = squad_dev()
a = E17.auroc(SQ['d'], SQ['s2'])
st = read(E20F / 'STATS_E20F.json')['dev']['AUROC_s2']
check('d', 'SQuAD/Llama (s2): dev AUROC vs paper .811 (|diff| <= 5e-4)', .811, round(a, 6), 'request', ok=abs(a - .811) <= 5e-4)
check('d', 'SQuAD/Llama (s2): dev AUROC vs STATS_E20F.json dev.AUROC_s2', st, a, E20F / 'STATS_E20F.json', ok=abs(a - st) < 1e-12)
check('d', 'SQuAD/Llama dev disagreements (E20F: 154/1000)', [154, 1000], [int(SQ['d'].sum()), len(SQ['d'])], E20F / 'RESULTS_E20F.md')

# ------------------------------------------------------------------ (e)
RET = {'large/OBQA/Text': .750, 'large/ARC/Text': .333, 'large/MMLU-Pro/Text': 1.054, 'large/OBQA/Text+fact': .811}
for key, rv in RET.items():
    cR, cb, cp = DEVACC[key]
    check('e', f'{key}: E13-3 gain retention at alpha=.05 (3 dp)', rv, round((cp - cR) / (cb - cR), 3), 'request / E13 item3_alpha_sweep.csv')

# ------------------------------------------------------------------ (f)
E191 = {r['row']: r for r in csvread(E19.RES / 'E19_1_decomposition.csv')}
for name, key, _, _ in SET6:
    R = replay(key)
    s = np.array([R['fx'][i]['latency_ms'] - R['po'][i]['latency_ms'] for i in R['ids']])
    lo, hi = ci(s[bidx(len(s))].mean(axis=1))
    r = E191[key]
    check('f', f'{key}: E19-1 panel net saving [95% CI] (ms, unrounded)', [float(r['net_ms']), float(r['net_CI95_lo']), float(r['net_CI95_hi'])],
          [float(s.mean()), lo, hi], R['source'],
          ok=max(abs(float(r['net_ms']) - s.mean()), abs(float(r['net_CI95_lo']) - lo), abs(float(r['net_CI95_hi']) - hi)) < 1e-9)

# ------------------------------------------------------------------ (g)  (e5c.py logic: raw saved R, V1 parsed_original or INVALID)
NULL = E9A.null_answers()
GM = E9A.gold_map()
Dm = C.load_main()['large', 'OBQA']['dev']
ids = Dm['ids']
g = [GM['obqa', i] for i in ids]
oR = list(Dm['ans']['R'])
v1 = [NULL['large', 'obqa', 'V1'].get(i, INV) for i in ids]
yR = np.array([a == b for a, b in zip(oR, g)]); y1 = np.array([a == b for a, b in zip(v1, g)])
ch = np.array([a != b for a, b in zip(v1, oR)])
check('g', 'E5-c large/OBQA V1 vs R: correct, changed, corrective, harmful', [599, 137, 48, 66],
      [int(y1.sum()), int(ch.sum()), int((ch & ~yR & y1).sum()), int((ch & yR & ~y1).sum())],
      ROOT / 'P2_R2_CPU_20260919T220412Z/results/e5c_change_decomposition.csv')

csvout('step0_repro_checks.csv', CHECKS)
csvout('step0_recomputed_calibration_ledgers.csv', LEDGER_OUT)
nf = sum(c['status'] == 'FAIL' for c in CHECKS)
run_log('step0_repro.py', T0, dict(n_checks=len(CHECKS), n_fail=nf))
print('Step 0 done', T0, utc(), 'checks', len(CHECKS), 'FAIL', nf)
