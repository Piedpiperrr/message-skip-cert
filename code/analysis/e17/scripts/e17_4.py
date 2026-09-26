"""E17-4: audit of the sealed-ARC label differences between V2 and the official C2C extraction (E14-1);
E17-4b: official extraction for the held-out large OBQA Text and Text+fact policies (E9b)."""
import ast, re, json, collections
from e17_common import *

X = loadcache(); S = X['S']

# the E5-a follow-up official_branch function (the same exec'd subset E14 used)
F1B = ROOT / 'P2_R2_CPU_20260919T220412Z/followup/scripts/f1b_official_diffs.py'
tree = ast.parse(F1B.read_text())
names = {'MATH', 'ANSWER_WORDS', 'STANDALONE', 'ANSWER_PATTERNS', 'LEAD_LABEL', 'LEAD_NUM', 'DECL'}
keep = [n for n in tree.body if (isinstance(n, ast.Assign) and any(getattr(t, 'id', None) in names for t in n.targets))
        or (isinstance(n, ast.FunctionDef) and n.name in ('official_branch', 'surface_pattern'))]
ns = {'re': re}
exec(compile(ast.Module(body=keep, type_ignores=[]), str(F1B), 'exec'), ns)
official_branch = ns['official_branch']

LEAD = re.compile(r'^\s*([A-D])[.):]')
SECOND = re.compile(r'(?<![A-Za-z])([A-D])[.):]')
nz = lambda t: ' '.join((t or '').split()).lower()

rows = []
for b in ['C', 'T']:
    for x in S[b]['rows']:
        if not (x['routed'] and PR.official_applicable(x['legal'])): continue
        for side, raw, v2 in [('R', x['rawR'], x['oR_V2']), ('C2C' if b == 'C' else 'Text', x['rawB'], x['oB_V2'])]:
            of = PR.label_official(raw or '', x['legal'])
            if of == v2: continue
            m = LEAD.match(raw or '')
            L1 = m.group(1) if m else None
            after = (raw or '')[m.end():] if m else ''
            opt = x['choice_text'][list(x['legal']).index(L1)] if (m and L1 in x['legal']) else None
            c2 = bool(m and opt is not None and (nz(after) == nz(opt) or nz(after).startswith(nz(opt))))
            sec = [mm.group(0) for mm in SECOND.finditer(after)] if m else []
            c3 = bool(m) and not sec
            c5 = bool(m) and v2 == L1
            br, has_math, has_ans = official_branch(raw)
            rows.append(dict(policy=f'large/ARC/{C.REF[b]}', id=x['id'], side=side, raw_output=raw, V2_label=v2, official_label=of,
                             options=json.dumps({l: t for l, t in zip(x['legal'], x['choice_text'])}),
                             check_i_leading_single_letter=bool(m), letter_i=L1 or '',
                             check_ii_text_is_option=c2, option_text_of_letter=opt or '',
                             check_iii_no_second_letter_pattern=c3, second_patterns=';'.join(sec),
                             check_v_V2_equals_letter=c5,
                             iv_official_returned=of, iv_official_branch=br, iv_math_substrings=';'.join(has_math or []),
                             iv_answer_words=';'.join(has_ans or []),
                             official_matches_stated_option_better=(of != INV and of == L1 and v2 != L1),
                             all_i_ii_iii_v=bool(m) and c2 and c3 and c5, label=LABEL))
csvout('E17_4_audit.csv', rows)
n_i = sum(r['check_i_leading_single_letter'] for r in rows)
n_i2 = sum(r['check_i_leading_single_letter'] and r['check_ii_text_is_option'] for r in rows)
n_all = sum(r['all_i_ii_iii_v'] for r in rows)
print('rows', len(rows), collections.Counter((r['policy'], r['side']) for r in rows))
print('(i)', n_i, '(i)+(ii)', n_i2, '(i)+(ii)+(iii)+(v)', n_all)
print('official returned', collections.Counter(r['iv_official_returned'] for r in rows))
print('official branch', collections.Counter(r['iv_official_branch'] for r in rows))
print('math substrings', collections.Counter(s for r in rows for s in r['iv_math_substrings'].split(';') if s))
print('official matches stated option better than V2:', sum(r['official_matches_stated_option_better'] for r in rows))
for r in rows:
    if not r['all_i_ii_iii_v']:
        print('FAIL-ROW', r['id'], r['side'], 'i', r['check_i_leading_single_letter'], 'ii', r['check_ii_text_is_option'],
              'iii', r['check_iii_no_second_letter_pattern'], repr(r['second_patterns']), 'v', r['check_v_V2_equals_letter'],
              '| raw:', repr(r['raw_output'][:160]), '| opt:', repr(r['option_text_of_letter']))
summ = [dict(item='E17-4', n_rows=len(rows), n_i=n_i, n_i_ii=n_i2, n_i_ii_iii_v=n_all,
             official_returned=json.dumps(collections.Counter(r['iv_official_returned'] for r in rows)),
             official_branch=json.dumps(collections.Counter(r['iv_official_branch'] for r in rows)),
             official_better=sum(r['official_matches_stated_option_better'] for r in rows), label=LABEL)]

# ---------------------------------------------------------------- E17-4b (E9b held-out 744 OBQA)
Q = {r['id']: r for r in jl(E9B / 'inputs/holdout_744_queries.jsonl')}
OUT = {(r['id'], r['pair'], r['action']): r for r in jl(E9B / 'analysis/SEALED_OUTPUTS.jsonl')}
ROUT = collections.defaultdict(list)
for r in jl(E9B / 'analysis/SEALED_ROUTES.jsonl'): ROUT[r['policy']].append(r)
E9R = {p['policy']: p for p in read(E9B / 'analysis/E9B_RESULTS.json')['policies']}
b4 = []
for pol, act, key in [('large_obqa_T_q80', 'T', 'held-out large/OBQA/Text q=.80'), ('large_obqa_TF_q75', 'TF', 'held-out large/OBQA/Text+fact q=.75')]:
    rr = [r for r in ROUT[pol] if r['omitted']]
    app = [r for r in rr if PR.official_applicable(Q[r['id']]['choice_labels'])]
    kv, ko, v2mis, ndiff = 0, 0, 0, 0
    for r in app:
        L = Q[r['id']]['choice_labels']
        oR, oB = OUT[r['id'], 'large', 'R'], OUT[r['id'], 'large', act]
        v2R, v2B = PR.label_v2(oR['raw_answer'] or '', L), PR.label_v2(oB['raw_answer'] or '', L)
        v2mis += (v2R != norm(r['R_answer'])) + (v2B != norm(r['reference_answer']))
        ofR, ofB = PR.label_official(oR['raw_answer'] or '', L), PR.label_official(oB['raw_answer'] or '', L)
        kv += v2R != v2B; ko += ofR != ofB; ndiff += (ofR != v2R) + (ofB != v2B)
    for ext, k in [('official', ko), ('V2', kv)]:
        lo, hi = cp95(k, len(app))
        b4.append(dict(policy=key, extractor=ext, omitted=len(rr), n_AD=len(app), k=k, rate=k / len(app), CP_lo=lo, CP_hi=hi,
                       p_H0_rho_ge_05=pval(k, len(app)), CP_hi_ge_05=hi >= .05, label_differences_outputs=ndiff if ext == 'official' else '',
                       V2_reparse_mismatches=v2mis if ext == 'V2' else '', stored_V2=f"{E9R[pol]['omitted']}/{E9R[pol]['changed']}", label=LABEL))
e141 = [r for r in csvread(E14 / 'results/E14_1_sealed_official.csv') if r['policy'] == 'large/ARC/Text' and r['extractor'] == 'official'][0]
b4.append(dict(policy='sealed large/ARC/Text (restated from E14-1)', extractor='official', n_AD=int(e141['n']), k=int(e141['k']),
               rate=float(e141['rate']), CP_lo=float(e141['CP95_lo']), CP_hi=float(e141['CP95_hi']), p_H0_rho_ge_05=float(e141['p_H0_rho_ge_05']),
               CP_hi_ge_05=float(e141['CP95_hi']) >= .05, label=LABEL))
csvout('E17_4b_official_text.csv', b4)
csvout('E17_4_summary.csv', summ)
for r in b4: print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k != 'label'})
