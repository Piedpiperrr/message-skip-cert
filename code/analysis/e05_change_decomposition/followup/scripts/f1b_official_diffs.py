"""E5 follow-up (b): every V2-vs-official label difference on the calibration outputs, categorised.

For each of the 21 settings and each of the two outputs (R and the setting's reference) this
re-parses the SAVED raw calibration outputs with the frozen V2 parser and with the official C2C
evaluator's `extract_answer_from_content`, and records, for every row where the two labels differ:
which output changed, the transition (label->INVALID / INVALID->label / label->other label), the
surface pattern of the raw output, and which branch of the official extractor produced its label.
Read-only; writes only under followup/results/.
"""
import collections, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'scripts'))
sys.dont_write_bytecode = True
import numpy as np  # noqa: E402
from r2_common import (ALL21, BENCH, EXPECTED_Q, GRID, INV, LABEL, sname, csvout, exposed_ids,  # noqa: E402
                       load_main, load_x1, load_x2, ledger_rows, csvread, XFAM, X1)
import parsers_r2 as PR  # noqa: E402
import rawio  # noqa: E402

RES = HERE / 'results'
MATH = ['+', '-', '*', '/', '=', '^', 'x^', 'y^', 'z^', 'mod', 'sqrt', 'sin', 'cos', 'tan']
ANSWER_WORDS = ['jibu', 'answer', 'choice', 'option', 'response', 'correct', 'sahihi']
STANDALONE = [r'\b([A-D])(?:\s*[.,!?:)]?\s*$)', r'\b([A-D])(?:\s*[.,!?:)]\s)', r'(?:^|\s)([A-D])(?:\s*$)']
ANSWER_PATTERNS = [r'Answer:\s*(.*)', r'Your answer:\s*(.*)', r'The answer is\s*(.*)',
                   r'Correct answer is\s*(.*)', r'Correct answer is:\s*(.*)', r'Correct answer:\s*(.*)',
                   r'Jibu lako:\s*(.*)', r'Jibu:\s*(.*)', r'Jibu sahihi:\s*(.*)',
                   r'Response:\s*(.*)', r'Choice:\s*(.*)', r'Option:\s*(.*)']


def official_branch(text):
    """Which branch of extract_answer_from_content decided this output, and why."""
    t = (text or '').strip()
    if not t:
        return 'empty_text', None, None
    has_math = [m for m in MATH if m in t]
    has_ans = [w for w in ANSWER_WORDS if w in t.lower()]
    for p in ANSWER_PATTERNS:
        m = re.search(p, t, re.IGNORECASE)
        if m:
            for ch in m.group(1).strip():
                if ch in 'ABCD':
                    return 'answer_phrase_first_ABCD_char', has_math, has_ans
    for j, p in enumerate(STANDALONE, 1):
        if re.findall(p, t, re.IGNORECASE):
            if has_math and not has_ans:
                continue
            return f'standalone_pattern_{j}_last_match', has_math, has_ans
    if re.findall(r'\b([A-D])\b', t, re.IGNORECASE):
        if has_math and not has_ans:
            return 'blocked_by_math_substring', has_math, has_ans
        return 'fallback_last_word_boundary_letter', has_math, has_ans
    if any(c in 'ABCD' for c in t):
        return 'reverse_scan_any_ABCD_char', has_math, has_ans
    return 'no_ABCD_character_found', has_math, has_ans


LEAD_LABEL = re.compile(r'^\s*\(?([A-Za-z])\)?[.):]\s')
LEAD_NUM = re.compile(r'^\s*\(?([0-9])\)?[.):]?\s')
DECL = re.compile(r'(?:the\s+)?(?:correct\s+|final\s+)?answer\s+is\s*:?\s*(.{0,24})', re.I)


def surface_pattern(text, legal):
    """A description of the raw output's form, independent of either parser."""
    t = (text or '').strip()
    if not t:
        return 'empty_output'
    decls = list(DECL.finditer(t))
    d = decls[0] if decls else None
    if d:
        tail = d.group(1)
        letters = re.findall(r'\b([A-Za-z])\b', tail)
        up = [x.upper() for x in letters]
        if len(set(up)) > 1:
            return 'declaration_several_letters'
        if up and up[0] not in legal:
            return 'declaration_letter_outside_option_set'
        if up:
            return ('repeated_declaration_same_letter' if len(decls) > 1 else 'declaration_single_letter')
        if re.search(r'\b[0-9]\b', tail):
            return 'declaration_numeric_option'
        return 'declaration_answer_text_without_letter'
    m = LEAD_LABEL.match(t)
    if m:
        lab = m.group(1).upper()
        if lab not in legal:
            return 'leading_letter_outside_option_set'
        rest = t[m.end():].strip()
        return 'leading_label_then_option_text' if rest else 'leading_label_only'
    if LEAD_NUM.match(t):
        return 'leading_numeric_option_label'
    if re.fullmatch(r'\(?([A-Za-z])\)?[.)]?', t):
        return 'bare_letter'
    return 'answer_text_without_letter'


def get(s, main, x1, x2):
    pair, task, ref = s
    if pair in ('small', 'medium', 'large'):
        D = main[pair, task]
        oR = [x if x is not None else INV for x in D['cal']['ans']['R']]
        ob = [x if x is not None else INV for x in D['cal']['ans']['T' if ref == 'Text' else 'C']]
        return BENCH[task], D['cal']['ids'], D['cal']['scores']['ProbeMax'], oR, ob, D['stored_thresholds'], EXPECTED_Q[s]
    if pair == 'X2-OLMo':
        ds = BENCH[task]; D = x2[ds]
        cuts = [r['threshold'] for r in csvread(XFAM / 'results/analysis/certification_ledger_60.csv')
                if r['setting'] == f'{ds}/Text']
        return ds, D['cal']['ids'], np.array(D['cal']['u']), D['cal']['oR'], D['cal']['oT'], cuts, 0.0
    ds = BENCH[task]; D = x1[ds]
    ob = D['cal']['oT'] if ref == 'Text' else D['cal']['oC']
    cuts = [r['threshold'] for r in csvread(X1 / 'results/analysis/certification_ledger_80.csv')
            if r['setting'] == f'{ds}/{ref}']
    return ds, D['cal']['ids'], np.array(D['cal']['u']), D['cal']['oR'], ob, cuts, 0.0


recs, allrev, X, CAL, FIT, DEV = exposed_ids()
main, x1, x2 = load_main(), load_x1(), load_x2()

per_setting, diffs, label_sets, census = [], [], [], []
for s in ALL21:
    ds, ids, u, oR, ob, cuts, q0 = get(s, main, x1, x2)
    raw, src = rawio.raw_cal(s, ids)
    ref = s[2]
    legal = [rawio.legal_labels(ds, i) for i in ids]
    union = sorted({x for L in legal for x in L})
    readable = all(PR.official_applicable(L) for L in legal)
    label_sets.append(dict(setting=sname(s), benchmark=ds, distinct_label_sets=len({tuple(L) for L in legal}),
                           union_of_labels=''.join(union), max_options=max(len(L) for L in legal),
                           official_hardcodes='A-D', official_can_read_every_label_set=readable, label=LABEL))
    row = dict(setting=sname(s), benchmark=ds, N_cal=len(ids), reference=ref,
               official_applicable=readable, raw_source=src, label=LABEL)
    if not readable:
        row.update(R_label_diffs='n/a (A-D only)', ref_label_diffs='n/a (A-D only)', d_label_diffs='n/a (A-D only)')
        per_setting.append(row)
        continue
    for which, key in [('R', 'R'), ('reference', ref)]:
        c = collections.Counter(surface_pattern(t, L) for t, L in zip(raw[key], legal))
        for pat, n in sorted(c.items(), key=lambda x: -x[1]):
            census.append(dict(setting=sname(s), output=which, output_pattern=pat, rows=n,
                               N_cal=len(ids), label=LABEL))
    dV2 = np.array([a != b for a, b in zip(oR, ob)], bool)
    newR = [PR.label_official(t, L) for t, L in zip(raw['R'], legal)]
    newb = [PR.label_official(t, L) for t, L in zip(raw[ref], legal)]
    dOF = np.array([a != b for a, b in zip(newR, newb)], bool)
    changed_d = dOF != dV2
    ex = np.array([i in X[ds] for i in ids], bool)
    nR = nb = 0
    for k, (i, L) in enumerate(zip(ids, legal)):
        for which, old, new, text in [('R', oR[k], newR[k], raw['R'][k]), (ref, ob[k], newb[k], raw[ref][k])]:
            if old == new:
                continue
            if which == 'R': nR += 1
            else: nb += 1
            trans = ('label->INVALID' if new == INV else 'INVALID->label' if old == INV else 'label->other label')
            br, hm, ha = official_branch(text)
            diffs.append(dict(setting=sname(s), benchmark=ds, output=('R' if which == 'R' else 'reference'),
                              reference=ref, id=i, V2_label=old, official_label=new, transition=trans,
                              output_pattern=surface_pattern(text, L), official_branch=br,
                              math_substrings='|'.join(hm or []), answer_words='|'.join(ha or []),
                              changes_disagreement_label=bool(changed_d[k]), in_exposed_X=bool(ex[k]),
                              legal_labels=''.join(L), raw_first80=(text or '')[:80], label=LABEL))
    led = ledger_rows(u, dOF, cuts)
    r0 = next((r for r in led if abs(r['q'] - q0) < 1e-9), None)
    acc = [r['q'] for r in led if r['accepted']]
    row.update(R_label_diffs=nR, ref_label_diffs=nb, total_label_diffs=nR + nb,
               d_label_diffs=int(changed_d.sum()), d_diffs_in_X=int(changed_d[ex].sum()),
               d_diffs_in_clean=int(changed_d[~ex].sum()), orig_q=q0,
               official_n_at_orig_q=(r0['n'] if r0 else ''), official_k_at_orig_q=(r0['k'] if r0 else ''),
               official_largest_accepted_q=(acc[-1] if acc else 0.0))
    per_setting.append(row)

cat = collections.Counter((d['setting'], d['output'], d['transition'], d['output_pattern'], d['official_branch'])
                          for d in diffs)
examples = collections.defaultdict(list)
for d in diffs:
    k = (d['setting'], d['output'], d['transition'], d['output_pattern'], d['official_branch'])
    if len(examples[k]) < 2:
        examples[k].append(d)
pairs = collections.defaultdict(collections.Counter)
for d in diffs:
    k = (d['setting'], d['output'], d['transition'], d['output_pattern'], d['official_branch'])
    pairs[k]['%s->%s' % (d['V2_label'], d['official_label'])] += 1
cats = []
for k, n in sorted(cat.items(), key=lambda x: (x[0][0], -x[1])):
    e = examples[k]
    cats.append(dict(setting=k[0], output=k[1], transition=k[2], output_pattern=k[3], official_branch=k[4],
                     count=n, V2_to_official=' '.join('%s x%d' % (a, b) for a, b in sorted(pairs[k].items())),
                     example_1=e[0]['raw_first80'], example_2=(e[1]['raw_first80'] if len(e) > 1 else ''),
                     math_substrings=e[0]['math_substrings'], label=LABEL))

RES.mkdir(parents=True, exist_ok=True)
csvout(RES / 'f1b_per_setting.csv', per_setting)
csvout(RES / 'f1b_differences.csv', diffs)
csvout(RES / 'f1b_categories.csv', cats)
csvout(RES / 'f1b_label_sets.csv', label_sets)
csvout(RES / 'f1b_pattern_census.csv', census)
overall = collections.Counter((d['transition'], d['output_pattern'], d['official_branch']) for d in diffs)
opairs = collections.defaultdict(collections.Counter)
oex = collections.defaultdict(list)
for d in diffs:
    k = (d['transition'], d['output_pattern'], d['official_branch'])
    opairs[k]['%s->%s' % (d['V2_label'], d['official_label'])] += 1
    if len(oex[k]) < 2:
        oex[k].append(d['raw_first80'])
csvout(RES / 'f1b_categories_overall.csv',
       [dict(transition=a, output_pattern=b, official_branch=c, count=n,
             V2_to_official=' '.join('%s x%d' % (x, y) for x, y in sorted(opairs[a, b, c].items())),
             settings=len({d['setting'] for d in diffs
                           if (d['transition'], d['output_pattern'], d['official_branch']) == (a, b, c)}),
             example_1=oex[a, b, c][0], example_2=(oex[a, b, c][1] if len(oex[a, b, c]) > 1 else ''),
             label=LABEL)
        for (a, b, c), n in sorted(overall.items(), key=lambda x: -x[1])])
print(json.dumps(dict(total_label_differences=len(diffs),
                      settings_with_differences=sorted({d['setting'] for d in diffs}),
                      official_readable_all_label_sets=[r['setting'] for r in label_sets
                                                        if not r['official_can_read_every_label_set']],
                      transitions=dict(collections.Counter(d['transition'] for d in diffs))), indent=1))
