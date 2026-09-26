"""E17 Step 2: reproduction checks. Exits non-zero (and nothing new is computed) if any check fails."""
import sys, json
from e17_common import *

CH = []


def check(name, expected, observed, source):
    ok = expected == observed
    CH.append(dict(check=name, expected=json.dumps(expected), observed=json.dumps(observed), status='PASS' if ok else 'FAIL', source=source))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: expected {expected} observed {observed}")


E142 = {(r['policy'], r['population']): r for r in csvread(E14 / 'results/E14_2_zero_u.csv')}
X3T = {r['setting']: r for r in csvread(X3 / 'results/analysis/dev_table.csv')}
POL = [('large/OBQA/Text', ('large', 'OBQA', 'Text'), .80), ('large/OBQA/C2C', ('large', 'OBQA', 'C2C'), .80),
       ('large/ARC/Text', ('large', 'ARC', 'Text'), .95), ('large/ARC/C2C', ('large', 'ARC', 'C2C'), .90),
       ('large/MMLU-Pro/Text', ('large', 'MMLU-Pro', 'Text'), .40), ('large/MMLU-Pro/C2C', ('large', 'MMLU-Pro', 'C2C'), .40),
       ('medium/OBQA/C2C q=.55', ('medium', 'OBQA', 'C2C'), .55), ('medium/OBQA/C2C q=.50', ('medium', 'OBQA', 'C2C'), .50),
       ('medium/ARC/C2C', ('medium', 'ARC', 'C2C'), .60), ('large/OBQA/Text+fact', C.FACT, .75),
       ('X3 obqa/Text', X3SET[0], .60), ('X3 arc/Text', X3SET[1], .70)]
EXPL = {'X3 obqa/Text': [438, 7], 'X3 arc/Text': [206, 4], 'large/OBQA/Text+fact': [536, 13], 'medium/OBQA/C2C q=.50': [355, 7]}

# (0) all 28 certification outcomes recomputed from stored cuts + cal records
L28 = {}
for s in ALL28:
    L = load(s); L28[s] = L
    q, _ = deployed(ledger(L['cal']['u'], L['cal']['d'], L['cuts']))
    check(f'(0) {sname(s)}: certification recomputed (deployed q; 0 = fallback)', L['q0'], q, 'stored thresholds + cal records')
    if s in X3SET:
        check(f'(0) {sname(s)}: thresholds = fit order statistics (X3 analyze_x3 rule)', True, True, 'by construction')
print('certified', sum(L28[s]['q0'] > 0 for s in ALL28), 'fallback', sum(L28[s]['q0'] == 0 for s in ALL28))

# (1) frozen deployment and dev omitted/changed for the 9 certified Qwen policies (+ q=.50 row) and the 2 Llama policies
n0n = {}
for key, s, q in POL:
    L = L28[s]
    t = L['cuts'][GRID.index(q)]
    m = mask(L['dev']['u'], q, t); n, k = int(m.sum()), int(L['dev']['d'][m].sum())
    if key.startswith('X3'):
        r = X3T[key]
        check(f'(1) {key}: frozen q (X3 dev_table.csv)', float(r['deployed_q']), q, str(X3 / 'results/analysis/dev_table.csv'))
        check(f'(1) {key}: dev omitted/changed vs X3 dev_table.csv', [int(r['dev_omitted']), int(r['dev_changed'])], [n, k],
              str(X3 / 'results/analysis/dev_table.csv'))
    else:
        r = E142[key, 'dev']
        check(f'(1) {key}: dev omitted/changed vs E14_2_zero_u.csv', [int(r['n']), int(r['k'])], [n, k], str(E14 / 'results/E14_2_zero_u.csv'))
    if key in EXPL:
        check(f'(1) {key}: dev omitted/changed vs value in the E17 request', EXPL[key], [n, k], 'E17 request text')
    z = L['dev']['u'] == 0
    n0n[key] = (int((m & z).sum()), n, int(L['dev']['d'][m & z].sum()), int(z.sum()), int(L['dev']['d'][z].sum()))

# (2) E14-2 dev n0/n range over the nine certified thresholds (medium OBQA C2C at q=.55)
nine = ['large/OBQA/Text', 'large/OBQA/C2C', 'large/ARC/Text', 'large/ARC/C2C', 'large/MMLU-Pro/Text', 'large/MMLU-Pro/C2C',
        'medium/OBQA/C2C q=.55', 'medium/ARC/C2C', 'large/OBQA/Text+fact']
rr = [n0n[k][0] / n0n[k][1] for k in nine]
check('(2) E14-2 dev n0/n range over the nine certified thresholds (%, 1 decimal)', [60.3, 92.1],
      [round(100 * min(rr), 1), round(100 * max(rr), 1)], 'recomputed; E14 RESULTS_E14.md')

# (3) E14-1 sealed ARC C2C, official extraction vs V2 on the same subset
S = load_sealed('C')
inc = [x for x in S['rows'] if x['routed'] and PR.official_applicable(x['legal'])]
oRo = [PR.label_official(x['rawR'] or '', x['legal']) for x in inc]
oBo = [PR.label_official(x['rawB'] or '', x['legal']) for x in inc]
kof = sum(a != b for a, b in zip(oRo, oBo)); kv2 = sum(x['oR_V2'] != x['oB_V2'] for x in inc)
ndiff = sum((a != x['oR_V2']) + (b != x['oB_V2']) for a, b, x in zip(oRo, oBo, inc))
check('(3) E14-1 sealed C2C official k/n', [54, 1044], [kof, len(inc)], f'{SA}/records/e2e_requests.jsonl')
check('(3) E14-1 sealed C2C V2 k/n on the same subset', [11, 1044], [kv2, len(inc)], f'{SA}/records/e2e_requests.jsonl')
check('(3) E14-1 sealed C2C label differences (outputs)', 44, ndiff, str(E14 / 'results/E14_1_label_diffs.csv'))
e14d = csvread(E14 / 'results/E14_1_label_diffs.csv')
check('(3) E14_1_label_diffs.csv rows', 44, len(e14d), str(E14 / 'results/E14_1_label_diffs.csv'))

# (4) calibration disagreement for large/ARC/Text always-omit (q = 1)
L = L28['large', 'ARC', 'Text']
q1 = ledger(L['cal']['u'], L['cal']['d'], L['cuts'])[-1]
check('(4) large/ARC/Text cal q=1: k/n', [12, 448], [q1['k'], q1['n']], 'stored cal records')

# (5) E17-1 dev n0/k0 (u == 0 rule) equal the E14-2 dev n0/k0 at each certified threshold
for key in nine + ['medium/OBQA/C2C q=.50']:
    r = E142[key, 'dev']
    n0, n, k0, N0, K0 = n0n[key]
    check(f'(5) {key}: dev u=0 rule n0/k0 == E14-2 n0/k0 (and every u=0 question is omitted)', [int(r['n0']), int(r['k0']), int(r['n0'])],
          [N0, K0, n0], str(E14 / 'results/E14_2_zero_u.csv'))

csvout('step2_checks.csv', CH)
bad = [c for c in CH if c['status'] == 'FAIL']
print('FAILED:', len(bad), 'of', len(CH))
sys.exit(1 if bad else 0)
