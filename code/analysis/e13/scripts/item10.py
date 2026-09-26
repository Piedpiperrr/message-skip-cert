"""E13 Item 10: is the earlier parser D1 (P2_SCORE_SENSITIVITY/diagnostic_parser_v1.py::parse_explicit, frozen
2026-09-12T06:02:33Z) functionally identical to the final parser (P2_SCORING_V2/scoring_v2.py::parse_answer)?

Both parsers are run (via the E5 wrappers parsers_r2.label_d1 / label_v2; INVALID when not valid) on every saved raw
multiple-choice output of every source that enters the paper (list in item10_scope.csv). The re-executed V2 label is
checked against the label stored with each output. Answer-change labels 1[o_R != o_b] are recomputed under D1 and V2
for every receiver/reference pairing the paper uses (replays: policy-arm R output vs fixed-arm output on omitted questions).
"""
import csv, json, collections, re
from pathlib import Path
import numpy as np
from e13_common import *
import parsers_r2 as PR  # noqa: E402

INV = 'INVALID'
V2L = ROOT / 'P2_SCORING_V2_20260912T191445Z/labels'
BND = ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
MED = ROOT / 'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z'
MMLU = ROOT / 'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z'
E8 = ROOT / 'P2_R2_E8_20260920T012544Z'
XF = ROOT / 'P2_R1_XFAM_20260919T095058Z'
GPU = ROOT / 'P2_R2_GPU_20260919T220941Z'
E9 = ROOT / 'P2_R3_E9BC_20260920T061042Z'
SA = ROOT / 'P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z'
FP = ROOT / 'P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z'
ME = ROOT / 'P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z'
MP = ROOT / 'P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z'
E7 = ROOT / 'P2_R2_E7_20260919T231531Z'
REP = {k: ROOT / f'P2_R1_E3POL_{k}_20260919T075315Z' for k in ['REPEAT1', 'REPEAT2', 'REPEAT3']}
FULL = ROOT / 'P2_R1_E3POL_MMLU_C2C_FULL_20260919T075315Z'
EXP = ROOT / 'P2_R1_EXP_20260919T050555Z'

OUT = []          # every output: dict(group, split, bench, pair, path, qid, raw, legal, stored)
LAB = collections.defaultdict(dict)   # label group -> {(qid, path): row index}
LPAIRS = {}       # label group -> list of (pathR, pathB)
scope = []


def add(group, split, bench, pair, path, qid, raw, legal, stored, lg=None):
    OUT.append(dict(group=group, split=split, bench=bench, pair=pair, path=path, qid=str(qid), raw=raw or '', legal=tuple(legal),
                    stored=stored))
    if lg is not None:
        LAB[lg][str(qid), path] = len(OUT) - 1


def stored_ans(parsed_or_answer, valid=None):
    if isinstance(parsed_or_answer, dict):
        return parsed_or_answer['answer'] if parsed_or_answer.get('valid') else INV
    if valid is False:
        return INV
    return parsed_or_answer if parsed_or_answer not in (None, '') else INV


# ---------------- legal labels
LEGAL = {}
for f in V2L.glob('*.jsonl'):
    for r in jl(f):
        LEGAL[r['dataset'], str(r['id'])] = tuple(r['legal_labels'])
for r in jl(E8 / 'inputs/queries_only.jsonl'):
    LEGAL['mmlu_pro', str(r['id'])] = tuple(r['choice_labels'])
for r in jl(E9 / 'inputs/holdout_744_queries.jsonl'):
    LEGAL['obqa', str(r['id'])] = tuple(r['choice_labels'])
for r in jl(SA / 'inputs/test_queries_no_gold.jsonl'):
    LEGAL['arc', str(r['id'])] = tuple(r['choice_labels'])

# ---------------- 1. V2 label index: small/large x OBQA/ARC (train = fit+cal, development, P2_10 panels)
split_of = {}
for ds in ['obqa', 'arc']:
    for sp in ['fit', 'cal', 'dev']:
        for i in read(BND / f'splits/{ds}_{sp}_ids.json'):
            split_of[ds, str(i)] = sp
rawcache = {}


def rawline(src):
    p = src['source_path']
    if p not in rawcache:
        rawcache[p] = {i: json.loads(s) for i, s in enumerate(open(p), 1)}
    return rawcache[p][src['source_line']]


ACT = {'R': 'receiver_only', 'T': 'text', 'C': 'c2c', 'A': 'acw'}
V2IDX = {}
for fname, kind in [('full_train', 'train'), ('full_development', 'dev'), ('panel_development', 'panel_dev'), ('panel_train', 'panel_train')]:
    for r in jl(V2L / f'{fname}_P2_SCORING_V2.jsonl'):
        ds, i = r['dataset'], str(r['id'])
        sp = split_of[ds, i] if kind == 'train' else ('dev' if kind == 'dev' else f'panel ({kind[6:]}, P2_10 cost panel)')
        lg = f"V2idx|{r['pair']}|{ds}|{sp}"
        for a in 'RTCA':
            rec = rawline(r['source_' + a])
            assert str(rec['id']) == i and rec['action'] == ACT[a], (fname, i, a, rec['action'])
            path = {'R': 'R', 'T': 'Text', 'C': 'C2C', 'A': 'ACW (P2_10 fourth action; not a paper path)'}[a]
            add('small/large OBQA/ARC (V2 label index)', sp, ds, r['pair'], path, i, rec.get('raw_answer'), r['legal_labels'],
                stored_ans(r['o_' + a], r['valid_' + a]), lg)
            if kind in ('train', 'dev'):
                V2IDX[r['pair'], ds, i, a] = len(OUT) - 1
        LPAIRS[lg] = [('R', 'Text'), ('R', 'C2C')]
scope.append(dict(source='P2_SCORING_V2 label index -> P2_5/P2_6/P2_9 train/dev cases and P2_10 cases', included=True))

# ---------------- 2. medium OBQA/ARC
for ds in ['obqa', 'arc']:
    for sp in ['fit', 'cal', 'dev']:
        for r in jl(MED / f'actions/{ds}_{sp}.jsonl'):
            lg = f'medium|{ds}|{sp}'
            path = {'R': 'R', 'T': 'Text', 'C': 'C2C'}[r['action']]
            add('medium OBQA/ARC', sp, ds, 'medium', path, r['id'], (r.get('output') or {}).get('raw_answer'), r['query']['choice_labels'],
                stored_ans(r.get('answer')), lg)
            LPAIRS[lg] = [('R', 'Text'), ('R', 'C2C')]
scope.append(dict(source=str(MED.relative_to(ROOT)) + '/actions', included=True))

# ---------------- 3. large MMLU-Pro
for sh in ['1', '2']:
    for f in sorted((MMLU / f'shards/{sh}/actions').glob('*.jsonl')):
        for r in jl(f):
            lg = f"mmlu_large|{r['split']}"
            path = {'R': 'R', 'T': 'Text', 'C': 'C2C'}[r['action']]
            add('large MMLU-Pro', r['split'], 'mmlu_pro', 'large', path, r['id'], (r.get('output') or {}).get('raw_answer'),
                r['query']['choice_labels'], stored_ans(r.get('answer')), lg)
            LPAIRS[lg] = [('R', 'Text'), ('R', 'C2C')]
scope.append(dict(source=str(MMLU.relative_to(ROOT)) + '/shards/{1,2}/actions', included=True))

# ---------------- 4. E8 small/medium MMLU-Pro
for pair in ['small', 'medium']:
    for d in sorted((E8 / 'shards' / pair).glob('lane_*')):
        for rel in read(d / 'LANE_COMPLETE.json')['files']:
            for r in jl(d / rel):
                if r['action'] == 'P':
                    continue
                lg = f"E8|{pair}|{r['split']}"
                path = {'R': 'R', 'T': 'Text', 'C': 'C2C'}[r['action']]
                add('small/medium MMLU-Pro (E8)', r['split'], 'mmlu_pro', pair, path, r['id'], (r.get('output') or {}).get('raw_answer'),
                    r['query']['choice_labels'], stored_ans(r.get('answer')), lg)
                LPAIRS[lg] = [('R', 'Text'), ('R', 'C2C')]
scope.append(dict(source='P2_R2_E8/shards/{small,medium}/lane_*/ (actions R/T/C)', included=True))

# ---------------- 5. X2 OLMo
for f in sorted((XF / 'results/runs').glob('chain_*.jsonl')):
    for r in jl(f):
        ds = r['dataset']; lg = f"X2|{ds}|{r['split']}"
        for a, path in [('R', 'R'), ('T', 'Text')]:
            add('X2 OLMo (cross-family)', r['split'], ds, 'X2-OLMo', path, r['id'], r[a].get('raw'), LEGAL[ds, str(r['id'])],
                INV if r.get('runtime_error') is not None else stored_ans(r[a]['parsed']), lg)
        LPAIRS[lg] = [('R', 'Text')]
scope.append(dict(source='P2_R1_XFAM/results/runs/chain_*.jsonl (R, Text)', included=True))

# ---------------- 6. X1 Llama helper (R = small pair's R, already counted in the V2 index)
for kind, key, path in [('text', 'T', 'Text'), ('c2c', 'C', 'C2C')]:
    for f in sorted((XF / 'x1/results/runs').glob(f'{kind}_chain_*.jsonl')):
        for r in jl(f):
            ds = r['dataset']; lg = f"X1|{ds}|{r['split']}"
            add('X1 Llama helper (cross-family)', r['split'], ds, 'X1-Llama', path, r['id'], r[key].get('raw'), LEGAL[ds, str(r['id'])],
                INV if r.get('runtime_error') is not None else stored_ans(r[key]['parsed']), lg)
            ix = V2IDX.get(('small', ds, str(r['id']), 'R'))
            if ix is not None:
                LAB[lg][str(r['id']), 'R'] = ix
            LPAIRS[lg] = [('R', 'Text'), ('R', 'C2C')]
scope.append(dict(source='P2_R1_XFAM/x1/results/runs/{text,c2c}_chain_*.jsonl (Text, C2C; R reused from the small pair)', included=True))

# ---------------- 7. E6 Text+fact
for f in sorted((GPU / 'e6/main').glob('e6_shard*.jsonl')):
    for r in jl(f):
        lg = f"E6|{r['split']}"
        add('large OBQA Text+fact (E6)', r['split'], 'obqa', 'large', 'Text+fact', r['id'], r.get('raw_answer'), LEGAL['obqa', str(r['id'])],
            stored_ans(r['answer']), lg)
        LAB[lg][str(r['id']), 'R'] = V2IDX['large', 'obqa', str(r['id']), 'R']
        LPAIRS[lg] = [('R', 'Text+fact')]
scope.append(dict(source='P2_R2_GPU/e6/main/e6_shard*.jsonl (Text+fact; R reused from the V2 index)', included=True))

# ---------------- 8. E9b held-out (744)
for r in jl(E9 / 'analysis/SEALED_OUTPUTS.jsonl'):
    lg = f"E9b|{r['pair']}"
    path = {'R': 'R', 'T': 'Text', 'C': 'C2C', 'TF': 'Text+fact'}[r['action']]
    add('held-out OBQA 744 (E9b)', 'held-out', 'obqa', r['pair'], path, r['id'], r.get('raw_answer'), LEGAL['obqa', str(r['id'])],
        stored_ans(r['answer']), lg)
    LPAIRS[lg] = [('R', 'Text'), ('R', 'C2C'), ('R', 'Text+fact')]
scope.append(dict(source='P2_R3_E9BC/analysis/SEALED_OUTPUTS.jsonl', included=True))


# ---------------- 9. replays and sealed ARC (panels): policy R output vs fixed output on omitted questions
def add_replay(group, setting, bench, pair, recs_fixed, recs_policy, extra=None):
    lg = f'{group}|{setting}'
    for arm, recs in [('fixed', recs_fixed), ('policy', recs_policy)] + (extra or []):
        for r in recs:
            raw = (r.get('output') or {}).get('raw_answer') if isinstance(r.get('output'), dict) else None
            if raw is None:
                raw = r.get('raw_answer')
            sel = r.get('selected')
            if arm != 'fixed' and r.get('probe_argmax_answer'):
                continue  # ARGMAX arm on omitted questions: no receiver output exists
            path = f'{arm}:' + ('R' if (arm != 'fixed' and sel == 'R') else 'ref')
            st = stored_ans(r['parsed']) if isinstance(r.get('parsed'), dict) else stored_ans(r.get('answer'))
            add(group, 'panel (replay)', bench, pair, path, r['id'], raw, LEGAL[bench, str(r['id'])], st, lg)
    LPAIRS[lg] = [(f'{a}:R', 'fixed:ref') for a in ['policy'] + [e[0] for e in (extra or [])]]


def large_replay(F, sub, group):
    reqs = jl(F / f'{sub}records/e2e_requests.jsonl')
    for ds in ['obqa', 'arc']:
        for b, bn in [('T', 'Text'), ('C', 'C2C')]:
            add_replay(group, f'large/{ds}/{bn}', ds, 'large',
                       [r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'reference')],
                       [r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'policy')])


def medium_replay(F, sub, group):
    reqs = jl(F / f'{sub}records/e2e_requests.jsonl')
    for ds in ['obqa', 'arc']:
        add_replay(group, f'medium/{ds}/C2C', ds, 'medium', [r for r in reqs if (r['task'], r['arm']) == (ds, 'fixed_C')],
                   [r for r in reqs if (r['task'], r['arm']) == (ds, 'policy_C')])


def mmlu_replay(path, group, refs=('T', 'C')):
    reqs = jl(path)
    for b in refs:
        add_replay(group, f'large/mmlu_pro/{b}', 'mmlu_pro', 'large', [r for r in reqs if r['arm'] == f'fixed_{b}'],
                   [r for r in reqs if r['arm'] == f'policy_{b}'])


large_replay(FP, '', 'replay: original large (ClusterB)')
medium_replay(ME, '', 'replay: original medium (ClusterB)')
mmlu_replay(MP / 'records/four_arm_requests.jsonl', 'replay: original MMLU-Pro (ClusterB)')
for k, F in REP.items():
    large_replay(F, 'large/', f'replay: E3 {k} (ClusterA)')
    medium_replay(F, 'medium/', f'replay: E3 {k} (ClusterA)')
    mmlu_replay(F / 'mmlu/records/four_arm_requests.jsonl', f'replay: E3 {k} (ClusterA)')
mmlu_replay(FULL / 'records/four_arm_requests.jsonl', 'replay: E3 full 2,641 MMLU-Pro C2C (ClusterA)', refs=('C',))
for stg in ['large', 'mmlu', 'medium']:
    reqs = jl(E7 / f'{stg}/records_e7/e7_requests.jsonl')
    for s_ in sorted({r['setting'] for r in reqs}):
        bench = s_.split('/')[1]
        rr = [r for r in reqs if r['setting'] == s_]
        add_replay('replay: E7 (ClusterA)', s_, bench, s_.split('/')[0], [r for r in rr if r['arm'] == 'fixed'],
                   [r for r in rr if r['arm'] == 'original'],
                   extra=[('reuse', [r for r in rr if r['arm'] == 'reuse']), ('argmax', [r for r in rr if r['arm'] == 'argmax'])])
e6r = jl(E7 / 'e6replay/records_e6/e6_replay_requests.jsonl')
add_replay('replay: E6 Text+fact (ClusterA)', 'large/obqa/Text+fact', 'obqa', 'large', [r for r in e6r if r['arm'] == 'fixed_TF'],
           [r for r in e6r if r['arm'] == 'policy_TF'])
sa = jl(SA / 'records/e2e_requests.jsonl')
for b, bn in [('T', 'Text'), ('C', 'C2C')]:
    add_replay('sealed ARC test (1,172 groups)', f'large/arc-sealed/{bn}', 'arc', 'large',
               [r for r in sa if (r['reference'], r['mode']) == (b, 'reference')], [r for r in sa if (r['reference'], r['mode']) == (b, 'policy')])
for g in ['FP', 'ME', 'MP', 'E3POL x3', 'E3POL MMLU full', 'E7', 'E6 replay', 'sealed ARC']:
    scope.append(dict(source=f'replay/sealed records: {g}', included=True))

# ---------------- 10. null controls (E4) and the E1 port check (secondary paths)
for f in sorted((EXP / 'results/e4').glob('*.jsonl')):
    for r in jl(f):
        ds = r['dataset']
        add('null controls V0/V1/V2 (E4; displayed option order)', 'dev', ds, r['pair'], r['variant'], r['id'], r.get('raw_output'),
            LEGAL[ds, str(r['id'])], stored_ans(r.get('parsed_displayed')))
e1 = list(csv.DictReader(open(EXP / 'results/e1_per_question.csv')))
e1_legal_fallback = 0
for r in e1:
    lg_ = LEGAL.get(('obqa', r['id']))
    if lg_ is None:
        lg_ = ('A', 'B', 'C', 'D'); e1_legal_fallback += 1
    add('E1 port check (official harness)', 'OBQA test (E1)', 'obqa', r['pair'], f"official:{r['action']}", r['id'], r['official_raw'], lg_,
        stored_ans(r['official_parsed_v2']))
    if r['ours_runtime_error'] != 'True':
        add('E1 port check (ours)', 'OBQA test (E1)', 'obqa', r['pair'], f"ours:{r['action']}", r['id'], r['ours_raw'], lg_,
            stored_ans(r['ours_parsed_v2']))
scope.append(dict(source='P2_R1_EXP results/e4 (null controls) and results/e1_per_question.csv (port check)', included=True,
                  note=f'E1: {e1_legal_fallback} rows without a stored option set used A-D (OBQA has four options)'))
scope.append(dict(source='P2_R4_E10 GSM8K', included=False, note='numeric short answers; neither multiple-choice parser applies'))
scope.append(dict(source='earlier exploratory stages (P2_1..P2_4, P2_7, P2_8, P2_E1_DIRECTION, gold-budget and baseline stages)', included=False,
                  note='not an input to any number in the paper; the paper-facing labels of P2_5/P2_6/P2_9/P2_10 are covered through the V2 index'))

# ---------------- parse
print('outputs:', len(OUT))
for o in OUT:
    o['v2'] = PR.label_v2(o['raw'], o['legal'])
    o['d1'] = PR.label_d1(o['raw'], o['legal'])
    o['diff'] = o['v2'] != o['d1']
    o['stored_ok'] = (o['stored'] is None) or (o['stored'] == o['v2'])

# ---------------- summaries
by = collections.defaultdict(lambda: [0, 0, 0])
for o in OUT:
    k = (o['group'], o['split'], o['pair'], o['bench'], o['path'])
    by[k][0] += 1; by[k][1] += o['diff']; by[k][2] += (not o['stored_ok'])
rows = [dict(group=k[0], split=k[1], pair=k[2], benchmark=k[3], path=k[4], n_outputs=v[0], n_parse_differs=v[1],
             n_rerun_V2_ne_stored=v[2], label=LABEL) for k, v in sorted(by.items())]
csvout(RES / 'item10_parse_differences.csv', rows)

diffs = [o for o in OUT if o['diff']]
ex = []
for o in diffs:
    rv2 = PR._v2.parse_answer(o['raw'], o['legal']); rd1 = PR._d1.parse_explicit(o['raw'], o['legal'])
    ex.append(dict(group=o['group'], split=o['split'], pair=o['pair'], benchmark=o['bench'], path=o['path'], qid=o['qid'],
                   V2=o['v2'], V2_reason=rv2['reason'], D1=o['d1'], D1_reason=rd1['reason'],
                   kind=('D1 INVALID, V2 valid' if o['d1'] == INV else ('D1 valid, V2 INVALID' if o['v2'] == INV else 'both valid, different letter')),
                   raw=o['raw'][:400].replace('\n', ' | '), label=LABEL))
csvout(RES / 'item10_differing_outputs.csv', ex)

# label changes
lrows = []
for lg, pairs in LPAIRS.items():
    for pa, pb in pairs:
        n = nd = 0; ex_ids = []
        qs = {q for (q, p) in LAB[lg] if p == pa} & {q for (q, p) in LAB[lg] if p == pb}
        for q in qs:
            a, b = OUT[LAB[lg][q, pa]], OUT[LAB[lg][q, pb]]
            n += 1
            if (a['v2'] != b['v2']) != (a['d1'] != b['d1']):
                nd += 1; ex_ids.append(q)
        if n:
            lrows.append(dict(label_group=lg, pair_R=pa, pair_b=pb, n_questions=n, n_change_label_differs=nd,
                              ids=';'.join(sorted(ex_ids)[:20]), label=LABEL))
csvout(RES / 'item10_label_changes.csv', lrows)
csvout(RES / 'item10_scope.csv', scope)

tot = len(OUT); nd = len(diffs)
print('total outputs', tot, 'differ', nd, 'rerun-V2 != stored', sum(not o['stored_ok'] for o in OUT))
print(collections.Counter((e['group'], e['split'], e['kind']) for e in ex).most_common(60))
print('label rows', len(lrows), 'label differences', sum(r['n_change_label_differs'] for r in lrows))
for r in lrows:
    if r['n_change_label_differs']:
        print(r)
cal = [o for o in OUT if o['split'] == 'cal']
print('calibration outputs', len(cal), 'differ', sum(o['diff'] for o in cal))
