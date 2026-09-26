"""E19 Step 0: reproduction checks (run before PREREG_E19.md and before any new computation).
(a) dev omitted / changed of the 12 policy rows vs E14's reproduction values (E14_2_zero_u.csv dev rows = RESULTS_E14 table (ii))
    and, for the two Llama rows (not in E14), vs X3 results/analysis/dev_table_pre_gold.csv.
(b) Table 2 mean saving of the eight Qwen large/medium policies from their per-request replay records vs E15's REPRO values;
    E16-4 Llama savings (all requests) 318.6 / 418.9 ms; Text+fact replay 343.4 [297.7, 386.0] ms.
(c) E14's dev u = 0 counts n0 / n at the deployed thresholds (10 rows).
"""
from e19_common import *

T0 = utc()
CHECKS = []


def check(item, name, expected, observed, source):
    ok = expected == observed
    CHECKS.append(dict(item=item, check=name, expected=json.dumps(expected), observed=json.dumps(observed),
                       status='PASS' if ok else 'FAIL', source=str(source)))
    print(f"[{'PASS' if ok else 'FAIL'}] ({item}) {name}: expected {expected} observed {observed}")


E14Z = {(r['policy'], r['population']): r for r in csvread(E14 / 'results/E14_2_zero_u.csv')}
X3D = {r['setting']: r for r in csvread(X3 / 'results/analysis/dev_table_pre_gold.csv')}
E14KEY = {'large/OBQA/Text+fact': 'large/OBQA/Text+fact'}
# (a)
for key, s, q in POL12:
    D = dev(key)
    obs = [int(D['m'].sum()), int(D['d'][D['m']].sum())]
    if key.startswith('Llama'):
        r = X3D['X3 obqa/Text' if s[1] == 'OBQA' else 'X3 arc/Text']
        exp = [int(r['dev_omitted']), int(r['dev_changed'])]
        check('a', f'dev omitted/changed {key} (q={q})', exp, obs, X3 / 'results/analysis/dev_table_pre_gold.csv')
        check('a', f'frozen tau {key}', float(r['threshold']), D['tau'], X3 / 'results/analysis/dev_table_pre_gold.csv')
    else:
        r = E14Z[key, 'dev']
        exp = [int(r['n']), int(r['k'])]
        check('a', f'dev omitted/changed {key} (q={q})', exp, obs, E14 / 'results/E14_2_zero_u.csv')
# the two values quoted in the request
check('a', 'request value Text+fact 536/13', [536, 13], [int(dev('large/OBQA/Text+fact')['m'].sum()),
      int(dev('large/OBQA/Text+fact')['d'][dev('large/OBQA/Text+fact')['m']].sum())], 'request')
check('a', 'request value medium OBQA C2C q=.50 355/7', [355, 7], [int(dev('medium/OBQA/C2C q=.50')['m'].sum()),
      int(dev('medium/OBQA/C2C q=.50')['d'][dev('medium/OBQA/C2C q=.50')['m']].sum())], 'request')

# (b)
T2 = {'large/MMLU-Pro/Text': 346.3, 'large/MMLU-Pro/C2C': 8.2, 'large/OBQA/Text': 517.1, 'large/OBQA/C2C': 36.6,
      'large/ARC/Text': 717.6, 'large/ARC/C2C': 110.9, 'medium/OBQA/C2C q=.55': 79.7, 'medium/ARC/C2C': 100.7}
e15 = {r['setting']: r for r in csvread(ROOT / 'P2_R6_E15_20260921T072336Z/results/step2_repro_table2.csv')}
for key in QWEN8:
    s, q = POLD[key]
    assert T2[key] == float(e15[C.sname(s)]['expected_ms'])
    R = replay(key)
    d = np.array([R['fx'][i]['latency_ms'] - R['po'][i]['latency_ms'] for i in R['ids']])
    check('b', f'Table 2 saving {key} (ms, 1 dp)', T2[key], round(float(d.mean()), 1), R['source'])
    check('b', f'Table 2 saving {key} == E15 recomputed (unrounded)', float(e15[C.sname(s)]['recomputed_ms']), float(d.mean()), R['source'])
for key, exp_mean, exp_ci in [('Llama-3.1-8B/OBQA/Text', 318.6, [261.1, 372.1]), ('Llama-3.1-8B/ARC/Text', 418.9, [361.7, 473.7]),
                              ('large/OBQA/Text+fact', 343.4, [297.7, 386.0])]:
    R = replay(key)
    d = np.array([R['fx'][i]['latency_ms'] - R['po'][i]['latency_ms'] for i in R['ids']])
    lo, hi = ci(d[bidx(len(d))].mean(axis=1))
    check('b', f'replay saving {key}, all requests (ms, 1 dp)', exp_mean, round(float(d.mean()), 1), R['source'])
    check('b', f'replay saving {key}, 95% paired bootstrap (1 dp)', exp_ci, [round(lo, 1), round(hi, 1)], R['source'])
# extra (not required): the full 2,641-question MMLU-Pro C2C replay, vs its stored analysis
R = replay_full_mmlu_c2c()
d = np.array([R['fx'][i]['latency_ms'] - R['po'][i]['latency_ms'] for i in R['ids']])
lo, hi = ci(d[bidx(len(d))].mean(axis=1))
fr = csvread(FULL / 'results/e3_full_saving.csv')[0]
check('b-extra', 'full MMLU-Pro C2C replay saving (all 2,641) vs results/e3_full_saving.csv (ms, 3 dp)',
      [round(float(fr['a_mean_ms']), 3), round(float(fr['a_CI_low']), 3), round(float(fr['a_CI_high']), 3)],
      [round(float(d.mean()), 3), round(lo, 3), round(hi, 3)], R['source'])

# (c)
for key, s, q in POL12[:10]:
    D = dev(key)
    z = D['u'] == 0.0
    r = E14Z[key, 'dev']
    check('c', f'dev u=0 n0/n {key}', [int(r['n0']), int(r['n'])], [int((D['m'] & z).sum()), int(D['m'].sum())],
          E14 / 'results/E14_2_zero_u.csv')

csvout('step0_repro_checks.csv', CHECKS)
nf = sum(c['status'] == 'FAIL' for c in CHECKS)
json.dump(dict(start_utc=T0, end_utc=utc(), n_checks=len(CHECKS), n_fail=nf, files_read=READ),
          open(STAGE / 'logs/step0_run.json', 'w'), indent=1)
print('Step 0 done', T0, utc(), 'checks', len(CHECKS), 'FAIL', nf)
sys.exit(1 if nf else 0)
