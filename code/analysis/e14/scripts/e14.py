"""E14 (Round 6): CPU re-analysis of stored outputs, run exactly as preregistered in PREREG_E14.md.
Read-only on every existing P2_* folder; writes only under this stage (results/, logs/).

Reuses, unchanged:
  - P2_R4_E11_20260920T224016Z/scripts/e11_common.py  (cal/dev loader for all settings, raw-output locator)
  - P2_R2_CPU_20260919T220412Z/scripts/parsers_r2.py   (V2 parser and the official C2C extractor port used in E5-a/E11(b))
  - P2_R2_CPU_20260919T220412Z/followup/scripts/f1b_official_diffs.py :: official_branch, surface_pattern
    (the E5-a follow-up categorisation; only these two functions and their constants are exec'd, via ast)
Step 2 (reproduction checks) runs first; the script exits non-zero before any E14 number if a check fails.
"""
import ast, builtins, collections, datetime, io, json, os, pathlib, re, sys
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
ROOT = STAGE.parent
RES = STAGE / 'results'
LOGS = STAGE / 'logs'
sys.dont_write_bytecode = True
T_START = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

# ---- log every file opened for reading (for the "files read" list)
READ = []
_open = io.open


def _logopen(file, mode='r', *a, **k):
    if not any(c in mode for c in 'wax+'):
        p = os.path.abspath(os.fspath(file))
        if p not in READ: READ.append(p)
    return _open(file, mode, *a, **k)


builtins.open = _logopen
io.open = _logopen
if hasattr(pathlib, '_NormalAccessor'):
    pathlib._NormalAccessor.open = staticmethod(_logopen)

sys.path.insert(0, str(ROOT / 'P2_R4_E11_20260920T224016Z' / 'scripts'))
import numpy as np  # noqa: E402
from scipy.stats import beta  # noqa: E402
import e11_common as C  # noqa: E402

PR = C.PR
INV = C.INV
jl, read, csvread, csvout, pval = C.jl, C.read, C.csvread, C.csvout, C.pval
LABEL = 'POST-HOC re-analysis (E14, PREREG_E14.md); descriptive, not a new certificate'

SA = ROOT / 'P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z'
E9B = ROOT / 'P2_R3_E9BC_20260920T061042Z'
E5 = ROOT / 'P2_R2_CPU_20260919T220412Z'
E11 = ROOT / 'P2_R4_E11_20260920T224016Z'
BNDS = C.BND / 'summary/main_dev.csv'
MEDS = C.MED / 'summary/compact_summary.csv'
MMLUS = C.MMLU / 'summary/compact_table.csv'
E6S = C.E6 / 'analysis/E6_SUMMARY.csv'
F1C = E5 / 'followup/results/f1c_medium_obqa_C2C_dev.csv'

# ---- the E5-a follow-up categorisation functions, exec'd from their source
F1B = E5 / 'followup/scripts/f1b_official_diffs.py'
_tree = ast.parse(F1B.read_text())
_names = {'MATH', 'ANSWER_WORDS', 'STANDALONE', 'ANSWER_PATTERNS', 'LEAD_LABEL', 'LEAD_NUM', 'DECL'}
_keep = [n for n in _tree.body if (isinstance(n, ast.Assign) and any(getattr(t, 'id', None) in _names for t in n.targets))
         or (isinstance(n, ast.FunctionDef) and n.name in ('official_branch', 'surface_pattern'))]
assert len(_keep) == 9, len(_keep)
_ns = {'re': re}
exec(compile(ast.Module(body=_keep, type_ignores=[]), str(F1B), 'exec'), _ns)
official_branch, surface_pattern = _ns['official_branch'], _ns['surface_pattern']

CAT = {'C1': 'ambiguous/repeated letters read as the first letter',
       'C2': 'option text with a math substring (tan/sin/"/")',
       'C3': 'last-letter read (e.g. "A. 0 C")',
       'C4': 'other'}


def category(old, new, text, legal):
    trans = 'label->INVALID' if new == INV else 'INVALID->label' if old == INV else 'label->other label'
    br = official_branch(text)[0]
    pat = surface_pattern(text, legal)
    if trans == 'INVALID->label' and br == 'answer_phrase_first_ABCD_char' and \
            pat in ('declaration_several_letters', 'repeated_declaration_same_letter'):
        c = 'C1'
    elif trans == 'label->INVALID' and br == 'blocked_by_math_substring':
        c = 'C2'
    elif trans == 'label->other label' and br.startswith('standalone_pattern'):
        c = 'C3'
    else:
        c = 'C4'
    return c, trans, pat, br


def norm(x): return INV if x is None else x


def cp95(k, n):
    if n == 0: return (float('nan'), float('nan'))
    lo = 0.0 if k == 0 else float(beta.ppf(.025, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(.975, k + 1, n - k))
    return lo, hi


def rate(k, n): return k / n if n else float('nan')


def f(x, d=4): return '' if x is None or (isinstance(x, float) and x != x) else (f'{x:.{d}f}' if isinstance(x, float) else str(x))


CHECKS = []


def check(name, expected, observed, source):
    ok = expected == observed
    CHECKS.append(dict(check=name, expected=json.dumps(expected), observed=json.dumps(observed),
                       status='PASS' if ok else 'FAIL', source=source))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: expected {expected} observed {observed}")
    return ok


RES.mkdir(exist_ok=True); LOGS.mkdir(exist_ok=True)
print('E14 first computation UTC', T_START)

# =====================================================================================================
# Step 2 (i): sealed ARC, parser V2, as executed
# =====================================================================================================
cfg = read(SA / 'frozen_config.json')
queries = jl(SA / 'inputs/test_queries_no_gold.jsonl')
assert len(queries) == 1172
reqs = jl(SA / 'records/e2e_requests.jsonl')
assert len(reqs) == 4688
RR = {(r['id'], r['reference'], r['mode']): r for r in reqs}
paired = {(r['id'], r['reference']): r for r in jl(SA / 'records/paired_sealed_2344.jsonl')}
prim = {r['reference']: r for r in csvread(SA / 'summary/primary_sealed.csv')}
SEALED = {}
v2_reparse_mismatch = 0
for b, (en, ek) in [('T', (1100, 20)), ('C', (1047, 11))]:
    thr = cfg['thresholds'][b]['threshold']
    rows = []
    for q in queries:
        i, L = q['id'], tuple(q['choice_labels'])
        p, r = RR[i, b, 'policy'], RR[i, b, 'reference']
        routed = p['selected'] == 'R'
        assert routed == (p['probe']['ProbeMax'] <= thr) and r['selected'] == b
        rawR = p['output']['raw_answer'] if routed else None
        rawB = r['output']['raw_answer']
        oP = p['parsed']['answer'] if p['parsed']['valid'] else INV
        oB = r['parsed']['answer'] if r['parsed']['valid'] else INV
        # the stored runtime parse is the frozen V2 parser (sha asserted at run time); re-parse to confirm
        if PR.label_v2(p['output']['raw_answer'], list(L)) != oP: v2_reparse_mismatch += 1
        if PR.label_v2(rawB, list(L)) != oB: v2_reparse_mismatch += 1
        z = paired[i, b]
        assert z['routed'] == int(routed) and z['ProbeMax'] == p['probe']['ProbeMax']
        assert z['policy_answer'] == oP and z['reference_answer'] == oB and z['omission_changed'] == int(routed and oP != oB)
        rows.append(dict(id=i, legal=L, u=p['probe']['ProbeMax'], routed=routed, rawR=rawR, rawB=rawB,
                         oR_V2=oP if routed else None, oB_V2=oB))
    n = sum(x['routed'] for x in rows)
    k = sum(x['routed'] and x['oR_V2'] != x['oB_V2'] for x in rows)
    check(f'(i) sealed large/ARC/{C.REF[b]} policy, parser V2 as executed: omitted/changed', [en, ek], [n, k],
          f'{SA}/records/e2e_requests.jsonl')
    check(f'(i) sealed large/ARC/{C.REF[b]} policy: same as summary/primary_sealed.csv', [int(prim[b]['routed']), int(prim[b]['changed_among_routed'])],
          [n, k], f'{SA}/summary/primary_sealed.csv')
    SEALED[b] = dict(rows=rows, threshold=thr, q=cfg['thresholds'][b]['q'])
check('(i) sealed: stored runtime parse == re-parse with frozen V2 (4688 outputs)', 0, v2_reparse_mismatch,
      f'{SA}/records/e2e_requests.jsonl; {PR.V2_SRC}')
check('(i) V2 parser sha256 = sealed frozen_config parser_sha256', cfg['parser_sha256'], PR.HASHES['V2'], str(PR.V2_SRC))

# =====================================================================================================
# Step 2 (ii): dev omitted / changed at every E14-2 policy row, frozen deployment records vs recomputation
# =====================================================================================================
POL = [  # key, setting, q, main-text row
    ('large/OBQA/Text', ('large', 'OBQA', 'Text'), .80, True),
    ('large/OBQA/C2C', ('large', 'OBQA', 'C2C'), .80, True),
    ('large/ARC/Text', ('large', 'ARC', 'Text'), .95, True),
    ('large/ARC/C2C', ('large', 'ARC', 'C2C'), .90, True),
    ('medium/OBQA/C2C q=.55', ('medium', 'OBQA', 'C2C'), .55, True),
    ('medium/OBQA/C2C q=.50', ('medium', 'OBQA', 'C2C'), .50, False),
    ('medium/ARC/C2C', ('medium', 'ARC', 'C2C'), .60, True),
    ('large/MMLU-Pro/Text', ('large', 'MMLU-Pro', 'Text'), .40, True),
    ('large/MMLU-Pro/C2C', ('large', 'MMLU-Pro', 'C2C'), .40, True),
    ('large/OBQA/Text+fact', C.FACT, .75, True),
]
bnd = {(r['pair'], r['dataset'], r['reference']): r for r in csvread(BNDS)}
med = {(r['task'], r['reference_code']): r for r in csvread(MEDS)}
mml = {r['reference']: r for r in csvread(MMLUS) if r['split'] == 'dev'}
e6s = {r['split']: r for r in csvread(E6S)}
f1c = {float(r['q']): r for r in csvread(F1C)}


def frozen_dev(key, s, q):
    pair, task, ref = s
    code = C.CODE.get(ref)
    if key == 'large/OBQA/Text+fact':
        r = e6s['dev']; return int(r['omitted']), int(r['changed_on_omitted']), None, str(E6S)
    if key == 'medium/OBQA/C2C q=.50':
        r = f1c[0.5]; return int(r['omitted']), int(r['changed_on_omitted']), float(r['threshold']), str(F1C)
    if pair == 'large' and task == 'MMLU-Pro':
        r = mml[ref]; return int(r['routed']), int(r['changed']), float(r['threshold']), str(MMLUS)
    if pair == 'large':
        r = bnd['large', task.lower(), code]; return int(r['n_R']), int(r['changed']), None, str(BNDS)
    r = med[task.lower(), code]; return int(r['route_to_R_count']), int(r['changed']), float(r['threshold']), str(MEDS)


# frozen thresholds in the deployment records (for the threshold identity check)
DEPTHR = {'large/OBQA/Text': read(C.BND / 'deployments/large_obqa_T.json')['threshold'],
          'large/OBQA/C2C': read(C.BND / 'deployments/large_obqa_C.json')['threshold'],
          'large/ARC/Text': read(C.BND / 'deployments/large_arc_T.json')['threshold'],
          'large/ARC/C2C': read(C.BND / 'deployments/large_arc_C.json')['threshold'],
          'large/OBQA/Text+fact': read(E9B / 'large/protocol/e6_deployment.json')['threshold']}
from common_r1 import ledgers  # noqa: E402
STORED = ledgers()
STORED[C.FACT] = [dict(q=float(r['q']), n=int(r['n']), k=int(r['k'])) for r in csvread(C.E6 / 'analysis/E6_LEDGER.csv')]

DATA = {}
none_mixed = []
for key, s, q in [(a, b, c) for a, b, c, _ in POL]:
    D = C.load(s)
    thr = {round(g, 4): t for g, t in zip(C.GRID, D['cuts'])}[round(q, 4)]
    DATA[key] = dict(s=s, q=q, tau=C.tv(thr), cuts=D['cuts'])
    for sp in ['cal', 'dev']:
        u = np.asarray(D[sp]['u'], float)
        oR, ob = [norm(x) for x in D[sp]['oR']], [norm(x) for x in D[sp]['ob']]
        d = np.array([a != b for a, b in zip(oR, ob)], bool)
        d_raw = np.array([a != b for a, b in zip(D[sp]['oR'], D[sp]['ob'])], bool)
        if (d != d_raw).any(): none_mixed.append((key, sp, int((d != d_raw).sum())))
        m = C.data_r1.route_mask(u, q, thr)
        DATA[key][sp] = dict(ids=D[sp]['ids'], u=u, d=d, m=m, oR=oR, ob=ob)
    en, ek, ethr, src = frozen_dev(key, s, q)
    m, d = DATA[key]['dev']['m'], DATA[key]['dev']['d']
    check(f'(ii) dev {key}: omitted/changed, frozen record vs recomputed', [en, ek], [int(m.sum()), int(d[m].sum())], src)
    if ethr is not None: check(f'(ii) {key}: threshold in frozen record', ethr, DATA[key]['tau'], src)
    if key in DEPTHR: check(f'(ii) {key}: threshold in deployment json', DEPTHR[key], DATA[key]['tau'], 'deployments json')
    st = {round(r['q'], 4): r for r in STORED[s]}[round(q, 4)]
    mc, dc = DATA[key]['cal']['m'], DATA[key]['cal']['d']
    check(f'(ii) cal {key}: omitted/changed, stored calibration ledger vs recomputed', [st['n'], st['k']],
          [int(mc.sum()), int(dc[mc].sum())], 'stored calibration ledgers (common_r1.ledgers(), E6_LEDGER.csv)')
check('(ii) no row mixes None and "INVALID" as the unparseable label (V2 labels as loaded)', [], none_mixed, 'e11_common.load')

# =====================================================================================================
# Step 2 (iii): official-extractor port reproduces E11(b) labels on large/ARC/C2C calibration rows
# =====================================================================================================
s = ('large', 'ARC', 'C2C')
D = C.load(s)
ids = D['cal']['ids']
rawd, rsrc = C.raw(s, 'cal', ids)
legal = C.legal_for(s, ids)
app = [PR.official_applicable(L) for L in legal]
oR2, ob2 = list(D['cal']['oR']), list(D['cal']['ob'])
oRo = [PR.label_official(t, L) for t, L in zip(rawd['R'], legal)]
obo = [PR.label_official(t, L) for t, L in zip(rawd['C2C'], legal)]
dV2 = np.array([a != b for a, b in zip(oR2, ob2)], bool)
dOF = np.array([a != b for a, b in zip(oRo, obo)], bool)
e11 = next(r for r in csvread(E11 / 'results/E11b_two_conventions.csv') if r['setting'] == 'large/ARC/C2C')
obs = dict(cal_N=len(ids), all_applicable=all(app),
           cal_o_R_differs=sum(a != b for a, b in zip(oR2, oRo)), cal_o_ref_differs=sum(a != b for a, b in zip(ob2, obo)),
           cal_d_label_differs=int((dV2 != dOF).sum()),
           cal_rows_label_differs=sum((a != b) or (c != e) for a, b, c, e in zip(oR2, oRo, ob2, obo)),
           cal_INVALID_R_official=sum(a == INV for a in oRo), cal_INVALID_ref_official=sum(a == INV for a in obo))
exp = {k: (int(e11[k]) if k != 'all_applicable' else True) for k in obs}
exp['all_applicable'] = True
check('(iii) large/ARC/C2C cal: official-port counts == E11b_two_conventions.csv', exp, obs, f'{E11}/results/E11b_two_conventions.csv')
grid = [(int(r['n']), int(r['k'])) for r in csvread(E11 / 'results/E11b_grid.csv')
        if r['setting'] == 'large/ARC/C2C' and r['convention'] == 'OFFICIAL']
led = C.ledger_rows(D['cal']['u'], dOF, D['cuts'])
check('(iii) large/ARC/C2C cal: 20-candidate OFFICIAL ledger (n,k) == E11b_grid.csv', grid, [(r['n'], r['k']) for r in led],
      f'{E11}/results/E11b_grid.csv')
# per-row labels: official label == f1b-listed official label on differing rows, == V2 label elsewhere
f1b = {(r['id'], r['output']): r['official_label'] for r in csvread(E5 / 'followup/results/f1b_differences.csv')
       if r['setting'] == 'large/ARC/C2C'}
bad = 0
for i, a2, ao, b2, bo in zip(ids, oR2, oRo, ob2, obo):
    bad += ao != f1b.get((i, 'R'), norm(a2))
    bad += bo != f1b.get((i, 'reference'), norm(b2))
check(f'(iii) large/ARC/C2C cal: per-row official labels (2 x {len(ids)}) == E5-a follow-up f1b_differences.csv', 0, bad,
      f'{E5}/followup/results/f1b_differences.csv')
check('(iii) official extractor source sha256 == E5-a record',
      next(r['sha256'] for r in csvread(E5 / 'results/e5a_parser_sources.csv') if r['parser'] == 'OFFICIAL'),
      PR.HASHES['OFFICIAL'], str(PR.OFFICIAL_SRC))

csvout(RES / 'E14_checks.csv', CHECKS)
if any(c['status'] == 'FAIL' for c in CHECKS):
    print('REPRODUCTION CHECK FAILED - stopping before any E14 number')
    (RES / 'E14_files_read.txt').write_text('\n'.join(READ) + '\n')
    sys.exit(2)
print('all reproduction checks PASS\n')

# =====================================================================================================
# E14-1: sealed ARC under the official C2C extractor
# =====================================================================================================
E141, DIFFS = [], []
ex_ids = [q['id'] for q in queries if not PR.official_applicable(q['choice_labels'])]
ex_sets = collections.Counter(''.join(q['choice_labels']) for q in queries if not PR.official_applicable(q['choice_labels']))
labsets = collections.Counter(''.join(q['choice_labels']) for q in queries)
numeric_orig = sum(q['original_choice_labels'] != q['choice_labels'] for q in queries)
for b in ['C', 'T']:
    pol = f'large/ARC/{C.REF[b]}'
    rows = SEALED[b]['rows']
    om = [x for x in rows if x['routed']]
    inc = [x for x in om if PR.official_applicable(x['legal'])]
    excl = len(om) - len(inc)
    three = sum(len(x['legal']) == 3 for x in inc)
    for x in inc:
        x['oR_OF'] = PR.label_official(x['rawR'] or '', x['legal'])
        x['oB_OF'] = PR.label_official(x['rawB'] or '', x['legal'])
    qdiff = collections.defaultdict(set)
    for x in inc:
        for out, old, new, text in [('R', x['oR_V2'], x['oR_OF'], x['rawR']), ('reference', x['oB_V2'], x['oB_OF'], x['rawB'])]:
            if old == new: continue
            c, trans, pat, br = category(old, new, text, x['legal'])
            qdiff[x['id']].add(c)
            DIFFS.append(dict(policy=pol, id=x['id'], output=out, V2_label=old, official_label=new, transition=trans,
                              output_pattern=pat, official_branch=br, category=c, category_name=CAT[c],
                              legal_labels=''.join(x['legal']), u=x['u'], raw_first80=(text or '')[:80]))
    pdiffs = [d for d in DIFFS if d['policy'] == pol]
    for ext, kR, kB in [('official', 'oR_OF', 'oB_OF'), ('V2 (same subset)', 'oR_V2', 'oB_V2')]:
        n = len(inc)
        k = sum(x[kR] != x[kB] for x in inc)
        k2 = sum((x[kR] != x[kB]) or (x[kR] == INV and x[kB] == INV) for x in inc)
        one_inv = sum((x[kR] == INV) != (x[kB] == INV) for x in inc)
        both_inv = sum(x[kR] == INV and x[kB] == INV for x in inc)
        lo, hi = cp95(k, n)
        br = 'a' if hi < .05 else ('b' if k / n <= .05 else 'c')
        E141.append(dict(policy=pol, extractor=ext, N_sealed=len(rows), omitted_all=len(om),
                         excluded_omitted=excl, excluded_reason='option labelled E (5 options A-E); official extractor reads A-D only',
                         omitted_3option_included=three, n=n, k=k, rate=rate(k, n), CP95_lo=lo, CP95_hi=hi,
                         p_H0_rho_ge_05=pval(k, n), k_both_unparseable_as_change=k2,
                         exactly_one_unparseable=one_inv, both_unparseable=both_inv,
                         R_unparseable=sum(x[kR] == INV for x in inc), ref_unparseable=sum(x[kB] == INV for x in inc),
                         rule_branch=br + ('' if b == 'C' and ext == 'official' else ' (descriptive)'),
                         questions_with_label_diff=len(qdiff) if ext == 'official' else '',
                         **({f'diff_questions_{c}': sum(c in v for v in qdiff.values()) for c in CAT} if ext == 'official' else {}),
                         **({f'diff_outputs_{c}_{o}': sum(d['category'] == c and d['output'] == o for d in pdiffs)
                             for c in CAT for o in ('R', 'reference')} if ext == 'official' else {}),
                         label=LABEL))
    # full-population V2 (reproduction value, for reference)
    E141.append(dict(policy=pol, extractor='V2 (all 1,172, as executed)', N_sealed=len(rows), omitted_all=len(om),
                     excluded_omitted=0, n=len(om), k=sum(x['oR_V2'] != x['oB_V2'] for x in om),
                     rate=rate(sum(x['oR_V2'] != x['oB_V2'] for x in om), len(om)),
                     CP95_lo=cp95(sum(x['oR_V2'] != x['oB_V2'] for x in om), len(om))[0],
                     CP95_hi=cp95(sum(x['oR_V2'] != x['oB_V2'] for x in om), len(om))[1],
                     p_H0_rho_ge_05=pval(sum(x['oR_V2'] != x['oB_V2'] for x in om), len(om)),
                     k_both_unparseable_as_change=sum((x['oR_V2'] != x['oB_V2']) or (x['oR_V2'] == INV and x['oB_V2'] == INV) for x in om),
                     label=LABEL))
csvout(RES / 'E14_1_sealed_official.csv', E141)
csvout(RES / 'E14_1_label_diffs.csv', DIFFS)
detail = collections.Counter((d['policy'], d['output'], d['category'], d['transition'], d['output_pattern'], d['official_branch'],
                              f"{d['V2_label']}->{d['official_label']}") for d in DIFFS)
csvout(RES / 'E14_1_label_diff_categories.csv',
       [dict(policy=k[0], output=k[1], category=k[2], category_name=CAT[k[2]], transition=k[3], output_pattern=k[4],
             official_branch=k[5], V2_to_official=k[6], count=n, label=LABEL) for k, n in sorted(detail.items())])
for r in E141:
    print(f"E14-1 {r['policy']:16s} {r['extractor']:28s} n={r['n']} k={r['k']} rate={f(r['rate'])} "
          f"CP=[{f(r['CP95_lo'])},{f(r['CP95_hi'])}] p={r['p_H0_rho_ge_05']:.3g} k2={r['k_both_unparseable_as_change']} "
          f"branch={r.get('rule_branch', '')} qdiff={r.get('questions_with_label_diff', '')}")

# =====================================================================================================
# E14-2: zero-uncertainty questions among omitted questions
# =====================================================================================================
HO = collections.defaultdict(list)
for r in jl(E9B / 'analysis/SEALED_ROUTES.jsonl'): HO[r['policy']].append(r)
e9b = {r['policy']: r for r in read(E9B / 'analysis/E9B_RESULTS.json')['policies']}
HOKEY = {'medium/OBQA/C2C q=.55': 'medium_obqa_C_q55', 'medium/OBQA/C2C q=.50': 'medium_obqa_C_q50',
         'large/OBQA/Text': 'large_obqa_T_q80', 'large/OBQA/C2C': 'large_obqa_C_q80', 'large/OBQA/Text+fact': 'large_obqa_TF_q75'}
SEKEY = {'large/ARC/Text': 'T', 'large/ARC/C2C': 'C'}


def zstats(key, pop, u, d, m, main):
    u, d, m = np.asarray(u, float), np.asarray(d, bool), np.asarray(m, bool)
    z = u == 0.0
    assert not (z & ~m).any(), (key, pop, 'a u=0 question is not omitted')
    n, n0, npos = int(m.sum()), int((m & z).sum()), int((m & ~z).sum())
    k0, kpos = int(d[m & z].sum()), int(d[m & ~z].sum())
    assert n0 + npos == n
    l0, h0 = cp95(k0, n0); lp, hp = cp95(kpos, npos)
    return dict(policy=key, population=pop, main_text_row=main, N=len(u), N_u0=int(z.sum()), share_u0_all=float(z.mean()),
                n=n, k=int(d[m].sum()), n0=n0, k0=k0, rate0=rate(k0, n0), CP0_lo=l0, CP0_hi=h0,
                n_pos=npos, k_pos=kpos, rate_pos=rate(kpos, npos), CPpos_lo=lp, CPpos_hi=hp,
                n0_over_n=rate(n0, n), p_pos_H0_rho_ge_05=(pval(kpos, npos) if pop == 'cal' else ''),
                trigger_kpos_CPlo_gt_05=(pop == 'dev' and lp > .05), trigger_n0n_ge_90=(pop == 'dev' and rate(n0, n) >= .90),
                label=LABEL)


E142 = []
for key, s, q, main in POL:
    for sp in ['cal', 'dev']:
        X = DATA[key][sp]
        E142.append(zstats(key, sp, X['u'], X['d'], X['m'], main))
    if key in HOKEY:
        rr = HO[HOKEY[key]]
        assert len(rr) == 744 and all(abs(r['threshold'] - DATA[key]['tau']) == 0 for r in rr), key
        z = zstats(key, 'held-out 744 OBQA', [r['ProbeMax'] for r in rr], [r['changed'] for r in rr], [r['omitted'] for r in rr], main)
        check(f'E9b {key}: omitted/changed == E9B_RESULTS.json', [e9b[HOKEY[key]]['omitted'], e9b[HOKEY[key]]['changed']],
              [z['n'], z['k']], f'{E9B}/analysis/E9B_RESULTS.json')
        E142.append(z)
    if key in SEKEY:
        b = SEKEY[key]
        assert SEALED[b]['threshold'] == DATA[key]['tau'], key
        rr = [paired[q['id'], b] for q in queries]
        E142.append(zstats(key, 'sealed ARC 1,172', [r['ProbeMax'] for r in rr], [r['omission_changed'] for r in rr],
                           [r['routed'] for r in rr], main))
csvout(RES / 'E14_2_zero_u.csv', E142)
for r in E142:
    print(f"E14-2 {r['policy']:22s} {r['population']:18s} N={r['N']} u0={r['N_u0']} ({f(r['share_u0_all'])}) n={r['n']} "
          f"n0={r['n0']} k0={r['k0']} n+={r['n_pos']} k+={r['k_pos']} n0/n={f(r['n0_over_n'])} "
          f"k0/n0={f(r['rate0'])}[{f(r['CP0_lo'])},{f(r['CP0_hi'])}] k+/n+={f(r['rate_pos'])}[{f(r['CPpos_lo'])},{f(r['CPpos_hi'])}] "
          f"p+={r['p_pos_H0_rho_ge_05'] if r['p_pos_H0_rho_ge_05'] == '' else format(r['p_pos_H0_rho_ge_05'], '.3g')}")

# per receiver x benchmark: share of dev questions with u = 0 (u is receiver-only: identical for Text and C2C)
REC = []
for pair, model in [('medium', 'Qwen3-1.7B'), ('large', 'Qwen3-8B')]:
    for task in ['OBQA', 'ARC', 'MMLU-Pro']:
        uT, uC = (np.asarray(C.load((pair, task, r))['dev']['u'], float) for r in ('Text', 'C2C'))
        assert np.array_equal(uT, uC), (pair, task)
        REC.append(dict(receiver=model, pair=pair, benchmark=task, split='dev', N=len(uT), N_u0=int((uT == 0).sum()),
                        share_u0=float((uT == 0).mean()), label=LABEL))
fitMM = np.asarray(C.load_main()['large', 'MMLU-Pro']['fit']['scores']['ProbeMax'], float)
REC.append(dict(receiver='Qwen3-8B', pair='large', benchmark='MMLU-Pro', split='fit (groups)', N=len(fitMM),
                N_u0=int((fitMM == 0).sum()), share_u0=float((fitMM == 0).mean()), label=LABEL))
csvout(RES / 'E14_2_receiver_u0.csv', REC)
known = {('large', 'OBQA', 'dev'): [354, 742], ('large', 'ARC', 'dev'): [217, 299], ('large', 'MMLU-Pro', 'fit (groups)'): [713, 3000]}
for r in REC:
    if (r['pair'], r['benchmark'], r['split']) in known:
        check(f"known-before value: {r['pair']}/{r['benchmark']} {r['split']} u=0 count / N",
              known[r['pair'], r['benchmark'], r['split']], [r['N_u0'], r['N']], 'paper (PREREG_E14.md "Known before")')
    print(f"receiver {r['receiver']:10s} {r['benchmark']:8s} {r['split']:12s} u=0 {r['N_u0']}/{r['N']} = {f(r['share_u0'])}")

THR = [dict(policy=k, q=DATA[k]['q'], tau=DATA[k]['tau'], tau_is_0=DATA[k]['tau'] == 0.0,
            fit_candidates_equal_0=sum(C.tv(t) == 0.0 for t in DATA[k]['cuts']),
            largest_q_with_candidate_0=max([g for g, t in zip(C.GRID, DATA[k]['cuts']) if C.tv(t) == 0.0], default=''),
            label=LABEL) for k, *_ in POL]
csvout(RES / 'E14_2_thresholds.csv', THR)
for r in THR: print(f"tau {r['policy']:22s} q={r['q']} tau={r['tau']!r} tau==0:{r['tau_is_0']} fit candidates ==0: {r['fit_candidates_equal_0']}")

csvout(RES / 'E14_checks.csv', CHECKS)
T_END = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
json.dump(dict(first_computation_utc=T_START, end_utc=T_END, excluded_ids=ex_ids, excluded_label_sets=dict(ex_sets),
               sealed_label_sets=dict(labsets), sealed_numeric_original_labels=numeric_orig,
               checks_failed=[c for c in CHECKS if c['status'] == 'FAIL'], files_read=READ,
               parser_hashes=PR.HASHES, raw_source_iii=rsrc),
          _open(RES / 'E14_run.json', 'w'), indent=1)
(RES / 'E14_files_read.txt').write_text('\n'.join(READ) + '\n')
print('done', T_END, 'failed checks:', sum(c['status'] == 'FAIL' for c in CHECKS))
