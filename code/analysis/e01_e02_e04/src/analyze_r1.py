"""P2_R1_EXP CPU analysis: E1 fidelity, E4 null controls, E2b feature inventory -> results/SUMMARY.md + CSVs.

Order: (1) hash every model-output file into results/OUTPUT_HASHES.json, (2) only then read gold labels.
Primary parser everywhere: frozen P2_SCORING_V2 parse_answer (INVALID kept in N, counted wrong).
"""
import sys
sys.dont_write_bytecode = True
import ast, csv, glob, json, pathlib, collections, traceback
import numpy as np
from common_r1 import *

RES = NEW / 'results'
BOUND = ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/splits'
V2L = ROOT / 'P2_SCORING_V2_20260912T191445Z/labels/full_development_P2_SCORING_V2.jsonl'
T1 = ROOT / 'P2_FOCUSED_REVISION_ROUND1_CPU_EVIDENCE_AUDIT_20260918T065337Z/outputs/T1_complementarity.csv'
MMLU_GOLD = ROOT / 'P2_MMLU_PRO_BREADTH_PROTOCOL_AND_COST_REVIEW_20260915T224801Z/dataset/test-00000-of-00001.parquet'
OBQA_TEST = DATA_ROOT / 'c2c_reproduction_assets/datasets/allenai--openbookqa/main/test-00000-of-00001.parquet'
TASK7_CSV = pathlib.Path('$HOME_DIR/c2c_reproduction_control/task7_full500/results/openbookqa_c2c_full500/Rosetta_openbookqa_generate_20260714_082810_cot.csv')
CLEAN = DATA_ROOT / 'c2c_reproduction_assets/official_C2C'
parse = parser()
NOTES = []


def wcsv(name, rows):
    p = RES / name
    if not rows:
        p.write_text('empty\n'); return p
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(p, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    return p


def v2(raw, legal):
    p = parse(raw if isinstance(raw, str) else '', legal)
    return p['answer'] if p['valid'] else INV


# ---------------------------------------------------------------- (1) hash outputs before any gold read
out_files = sorted(set(glob.glob(str(RES / 'e1/**/*.jsonl'), recursive=True) + glob.glob(str(RES / 'e1/**/*_cot.csv'), recursive=True)
                       + glob.glob(str(RES / 'e1/**/*.json'), recursive=True) + glob.glob(str(RES / 'e4/*.jsonl'))
                       + glob.glob(str(RES / 'e4/*.json'))))
hashes = {str(pathlib.Path(p).relative_to(NEW)): sha(p) for p in out_files}
feat = sorted(glob.glob(str(RES / 'e2b/*/features/*/*.npz')))
h = hashlib.sha256()
for p in feat:
    h.update(pathlib.Path(p).relative_to(NEW).as_posix().encode()); h.update(sha(p).encode())
hashes['e2b_feature_files_aggregate'] = {'n_files': len(feat), 'sha256_of_(path,sha256)_list': h.hexdigest()}
hashes['_task7_small_C2C_csv_reused'] = {str(TASK7_CSV): sha(TASK7_CSV)} if TASK7_CSV.exists() else 'MISSING'
save(RES / 'OUTPUT_HASHES.json', {'utc': utc(), 'note': 'computed before any gold label was read', 'files': hashes})
print('HASHED', len(out_files), 'files +', len(feat), 'feature files', flush=True)

# ---------------------------------------------------------------- (2) gold (after hashing)
import pyarrow.parquet as pq
obqa_test = pq.read_table(OBQA_TEST).to_pylist()
E1_GOLD = {i: r['answerKey'] for i, r in enumerate(obqa_test)}
DEV_GOLD = {}
for ds, fn in [('obqa', 'obqa_dev.jsonl'), ('arc', 'arc_validation.jsonl')]:
    for r in jl(P210 / 'data' / fn):
        DEV_GOLD[(ds, r['id'])] = r['gold_answer']
for r in pq.read_table(MMLU_GOLD, columns=['question_id', 'answer']).to_pylist():
    DEV_GOLD[('mmlu_pro', 'test:' + str(r['question_id']))] = r['answer']

# legacy (official evaluator) parser: P2_10 protocol_min copy, verified identical to the clean clone's function
src_p210 = (P210 / 'protocol_min.py').read_text()
src_off = (CLEAN / 'rosetta/utils/evaluate.py').read_text()


def fsrc(text, name):
    for n in ast.parse(text).body:
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return ast.get_source_segment(text, n)


LEGACY_IDENTICAL = fsrc(src_p210, 'extract_answer_from_content') == fsrc(src_off, 'extract_answer_from_content')
sys.path.insert(0, str(P210))
import protocol_min
legacy = protocol_min.extract_answer_from_content

# ================================================================ E1
e1_acc, e1_agree, e1_dis, e1_pq = [], [], [], []
pop = jl(POP / 'e1_obqa_test500.jsonl')
official_runs = {}
for chain in ['A', 'B']:
    p = RES / f'e1/official/RUNS_chain{chain}.jsonl'
    if p.exists():
        for r in jl(p):
            if r.get('valid'):
                official_runs[r['run']] = r
prefetch = json.loads((RES / 'e1/official/PREFETCH_STATUS.json').read_text()) if (RES / 'e1/official/PREFETCH_STATUS.json').exists() else {}


def read_official(csvp):
    with open(csvp, newline='') as f:
        rows = list(csv.DictReader(f))
    d = {}
    for r in rows:
        i = int(r['question_id'])
        q = pop[i]
        assert r['question'] == q['question_stem'] and [r[k] for k in 'ABCD'] == q['choice_text'], i
        d[i] = {'raw': r['cot_output'], 'official_pred': r['pred'] or None, 'official_is_correct': r['is_correct'] == 'True'}
    return d


ours = {}
for pair in ['small', 'medium', 'large']:
    p = RES / f'e1/ours/{pair}.jsonl'
    for r in (jl(p) if p.exists() else []):
        ours[(pair, r['action'], r['official_index'])] = r
prompts_ours = {}
for pair in ['small', 'medium', 'large']:
    p = RES / f'e1/prompts/ours_{pair}.json'
    if p.exists():
        for r in json.loads(p.read_text()):
            prompts_ours[(pair, r['action'], r['official_index'])] = r
prompts_off = {}
p = RES / 'e1/prompts/official.json'
if p.exists():
    for rec in json.loads(p.read_text()):
        for r in rec.get('prompts', []):
            prompts_off[(rec['run'], r['question_id'])] = r

for pair in ['small', 'medium', 'large']:
    for a in ['R', 'C']:
        run = f'{pair}_{a}'
        if run == 'small_C':
            csvp, kind = TASK7_CSV, 'task7 (runtime-patch evaluator, job 164991, reused)'
        elif run in official_runs:
            csvp = pathlib.Path(official_runs[run]['detail']); kind = official_runs[run]['kind'] + ' clone evaluator (this job)'
        else:
            csvp, kind = None, 'MISSING'
        off = {}
        if csvp is not None and csvp.exists():
            try:
                off = read_official(csvp)
            except Exception:
                NOTES.append(f'E1 {run}: official CSV failed validation: {traceback.format_exc(limit=1)}'); off = {}
        o = {i: ours[(pair, a, i)] for i in range(500) if (pair, a, i) in ours}
        for path, d in [('OFFICIAL', off), ('OURS', o)]:
            raws = {i: (x['raw'] if path == 'OFFICIAL' else x.get('raw_output')) for i, x in d.items()}
            ans = {i: v2(raws[i], list('ABCD')) for i in raws}
            leg = {i: legacy((raws[i] or '').strip()) if raws[i] else None for i in raws}
            row = {'pair': pair, 'action': 'Receiver-only' if a == 'R' else 'C2C', 'path': path, 'n_available': len(d),
                   'correct_v2_of_500': sum(ans[i] == E1_GOLD[i] for i in ans), 'invalid_v2': sum(ans[i] == INV for i in ans),
                   'correct_legacy_parser_of_500': sum(leg[i] == E1_GOLD[i] for i in leg),
                   'source': kind if path == 'OFFICIAL' else f'results/e1/ours/{pair}.jsonl'}
            if path == 'OFFICIAL':
                row['correct_official_evaluator_reported'] = sum(x['official_is_correct'] for x in d.values())
                row['official_csv'] = str(csvp) if csvp else None
            e1_acc.append(row)
        for i in range(500):
            xo, xu = off.get(i), o.get(i)
            e1_pq.append({'pair': pair, 'action': a, 'official_index': i, 'id': pop[i]['id'], 'gold': E1_GOLD[i],
                          'official_raw': xo['raw'] if xo else None, 'official_parsed_v2': v2(xo['raw'], list('ABCD')) if xo else None,
                          'official_pred_official_evaluator': xo['official_pred'] if xo else None,
                          'ours_raw': xu.get('raw_output') if xu else None, 'ours_parsed_v2': v2(xu.get('raw_output'), list('ABCD')) if xu else None,
                          'ours_runtime_error': bool(xu.get('runtime_error')) if xu else None})
        both = sorted(set(off) & set(o))
        agree = sum(v2(off[i]['raw'], list('ABCD')) == v2(o[i].get('raw_output'), list('ABCD')) for i in both)
        exact = sum(off[i]['raw'] == o[i].get('raw_output') for i in both)
        dis = []
        for i in both:
            ao, au = v2(off[i]['raw'], list('ABCD')), v2(o[i].get('raw_output'), list('ABCD'))
            if ao != au or off[i]['raw'] != o[i].get('raw_output'):
                e1_dis.append({'pair': pair, 'action': a, 'official_index': i, 'id': pop[i]['id'], 'parsed_official': ao, 'parsed_ours': au,
                               'parsed_differs': ao != au, 'raw_official': off[i]['raw'], 'raw_ours': o[i].get('raw_output'), 'gold': E1_GOLD[i]})
                if ao != au:
                    dis.append(f"{i}:{pop[i]['id']}")
        # rendered prompt identity, first 3 questions
        ident, detail = [], []
        for i in range(3):
            po, pu = prompts_off.get((run, i)), prompts_ours.get((pair, a, i))
            if po is None or pu is None:
                ident.append(None); detail.append(f'q{i}: missing'); continue
            same_text = po['rendered'] == pu['rendered']
            same_ids = po['rendered_input_ids'] == pu['rendered_input_ids']
            ident.append(same_text and same_ids); detail.append(f'q{i}: text={same_text} ids={same_ids}')
        e1_agree.append({'pair': pair, 'action': 'Receiver-only' if a == 'R' else 'C2C', 'n_compared': len(both),
                         'parsed_answer_agreement': agree, 'raw_output_exact_match': exact,
                         'rendered_prompts_byte_identical_first3': (all(ident) if ident and None not in ident else 'incomplete'),
                         'prompt_detail': '; '.join(detail), 'parsed_disagreement_ids': ' '.join(dis)})
wcsv('e1_accuracy.csv', e1_acc)
wcsv('e1_agreement.csv', e1_agree)
wcsv('e1_disagreements.csv', e1_dis)
wcsv('e1_per_question.csv', e1_pq)

# ================================================================ E4
t1 = {(r['pair'], r['task']): r for r in csv.DictReader(open(T1))}
v2lab = {(r['pair'], r['dataset'], r['id']): r for r in jl(V2L)}
_lines = {}


def rawline(path, line):
    if path not in _lines:
        with open(path) as f:
            _lines[path] = f.read().split('\n')
    return json.loads(_lines[path][line - 1])


def saved_action(pair, ds, rid, legal, act, rsrc):
    """Paper's saved development raw output for action act in {R,T,C}; re-parsed with the frozen parser."""
    if pair in ('small', 'large') and ds in ('obqa', 'arc'):
        lab = v2lab[(pair, ds, rid)]
        s = lab['source_' + act]
        x = rawline(s['source_path'], s['source_line'])
        assert x['id'] == rid and x['action'] == {'R': 'receiver_only', 'T': 'text', 'C': 'c2c'}[act]
        o = v2(x['raw_answer'], legal)
        stored = lab['o_' + act] if lab['valid_' + act] else INV
        return o, stored
    path = pathlib.Path(rsrc['path'])
    if (path, act) not in _idx:
        for n, x in enumerate(jl(path), start=1):
            _idx[(path, x['action'])] = _idx.get((path, x['action']), {})
            _idx[(path, x['action'])][x['id']] = x
    x = _idx[(path, act)][rid]
    o = v2(x['output']['raw_answer'], legal)
    return o, x['answer'] if not x.get('invalid') else INV


_idx = {}
e4_rows = []
for pair, ds in [('small', 'obqa'), ('small', 'arc'), ('medium', 'obqa'), ('medium', 'arc'), ('large', 'obqa'), ('large', 'arc'), ('large', 'mmlu_pro')]:
    try:
        rows = jl(POP / f'e4_{pair}_{ds}.jsonl')
        N = len(rows)
        vpath = RES / f'e4/{pair}_{ds}__V1-V2.jsonl'
        V = collections.defaultdict(dict)
        for x in (jl(vpath) if vpath.exists() else []):
            V[x['variant']][x['pos']] = x
        v0path = RES / f'e4/{pair}_{ds}__V0.jsonl'
        for x in (jl(v0path) if v0path.exists() else []):
            V['V0'][x['pos']] = x
        rec = collections.defaultdict(dict)
        mism = collections.Counter()
        for r in rows:
            g = DEV_GOLD[('mmlu_pro' if ds == 'mmlu_pro' else ds, r['id'])]
            assert g in r['legal_labels']
            for act in 'RTC':
                o, stored = saved_action(pair, ds, r['id'], r['legal_labels'], act, r['R_source'])
                mism[act] += o != stored
                rec[r['pos']][act] = o
            rec[r['pos']]['gold'] = g
            for v in ['V1', 'V2', 'V0']:
                if r['pos'] in V[v]:
                    rec[r['pos']][v] = V[v][r['pos']].get('parsed_original', INV)
        y = lambda p, k: int(rec[p].get(k) == rec[p]['gold'])
        pos_all = range(N)
        complete12 = all('V1' in rec[p] and 'V2' in rec[p] for p in pos_all)
        c = {k: sum(y(p, k) for p in pos_all) for k in ['R', 'T', 'C', 'V1', 'V2', 'V0']}
        inv = {k: sum(rec[p].get(k) == INV for p in pos_all) for k in ['R', 'T', 'C', 'V1', 'V2', 'V0']}
        orc = lambda ks: sum(any(y(p, k) for k in ks) for p in pos_all)
        o_rv = orc(['R', 'V1', 'V2']); best_rv = max(c['R'], c['V1'], c['V2'])
        o_rtc = orc(['R', 'T', 'C']); best_rtc = max(c['R'], c['T'], c['C'])
        chg = lambda k: sum(rec[p].get('R') != rec[p].get(k) for p in pos_all if k in rec[p])
        n_v = lambda k: sum(k in rec[p] for p in pos_all)
        t = t1.get((pair, ds), {})
        row = {'pair': pair, 'population': ds, 'N': N, 'V1_V2_complete': complete12, 'n_V1': n_v('V1'), 'n_V2': n_v('V2'), 'n_V0_supp': n_v('V0'),
               'R_correct_paper_saved': c['R'], 'V1_perm_correct': c['V1'], 'V2_irrelevant_msg_correct': c['V2'],
               'R_invalid': inv['R'], 'V1_invalid': inv['V1'], 'V2_invalid': inv['V2'],
               'oracle_R_V1_V2': o_rv, 'best_of_R_V1_V2': best_rv, 'oracle_gain_R_V1_V2_pp': round(100 * (o_rv - best_rv) / N, 2),
               'oracle_R_V1': orc(['R', 'V1']), 'oracle_R_V2': orc(['R', 'V2']),
               'answer_change_R_vs_V1': chg('V1'), 'answer_change_rate_R_vs_V1_pct': round(100 * chg('V1') / max(1, n_v('V1')), 2),
               'answer_change_R_vs_V2': chg('V2'), 'answer_change_rate_R_vs_V2_pct': round(100 * chg('V2') / max(1, n_v('V2')), 2),
               'T_correct_paper': c['T'], 'C_correct_paper': c['C'], 'paper_oracle_R_T_C': o_rtc, 'paper_best_fixed': best_rtc,
               'paper_oracle_gain_pp': round(100 * (o_rtc - best_rtc) / N, 2),
               'table1_oracle': t.get('oracle_correct'), 'table1_gain_pp': t.get('headroom_pp'),
               'matches_table1': (str(o_rtc) == t.get('oracle_correct') and f'{100 * (o_rtc - best_rtc) / N:.2f}' == t.get('headroom_pp')) if t else 'no T1 row',
               'reparse_vs_stored_mismatch_R_T_C': f"{mism['R']}/{mism['T']}/{mism['C']}",
               'V0_supp_same_job_R_replay_correct': c['V0'] if n_v('V0') else None,
               'V0_supp_answer_change_vs_saved_R': chg('V0') if n_v('V0') else None}
        e4_rows.append(row)
    except Exception:
        NOTES.append(f'E4 {pair}/{ds} failed: {traceback.format_exc(limit=2)}')
wcsv('e4_null_controls.csv', e4_rows)

# ================================================================ E2b
e2b_rows = []
settings = [('small', 'small_obqa_dev'), ('small', 'small_arc_dev'), ('large', 'large_arc_dev')] + \
           [('medium', f'medium_{d}_{s}') for d in ['obqa', 'arc'] for s in ['fit', 'cal', 'dev']] + \
           [('large', f'large_mmlu_pro_{s}') for s in ['fit', 'cal', 'dev']]
for pair, st in settings:
    rows = jl(POP / f'e2b_{st}.jsonl')
    files = sorted(glob.glob(str(RES / f'e2b/{pair}/features/{st}/*.npz')))
    dims, ok_ids, finite, norm1 = set(), 0, True, True
    for f in files:
        with np.load(f, allow_pickle=False) as z:
            v = z['z']; m = json.loads(str(z['meta']))
        dims.add(v.shape[0]); finite &= bool(np.isfinite(v).all()); norm1 &= bool(abs(np.linalg.norm(v) - 1) < 1e-5)
        ok_ids += m['id'] == rows[m['row']]['id']
    e2b_rows.append({'setting': st.rsplit('_', 1)[0], 'split': st.rsplit('_', 1)[1], 'pair': pair, 'expected': len(rows), 'written': len(files),
                     'dimension': '/'.join(map(str, sorted(dims))) or None, 'ids_match_population_order': ok_ids, 'all_finite': finite,
                     'unit_norm': norm1, 'dir': str(RES / f'e2b/{pair}/features/{st}')})
wcsv('e2b_features.csv', e2b_rows)

# ================================================================ SUMMARY.md


def md(rows, cols):
    if not rows:
        return '_no rows_\n'
    s = '| ' + ' | '.join(cols) + ' |\n|' + '---|' * len(cols) + '\n'
    for r in rows:
        s += '| ' + ' | '.join(str(r.get(c, '')) for c in cols) + ' |\n'
    return s


S = [f'# P2_R1_EXP summary\n\nGenerated {utc()} by src/analyze_r1.py. Folder: `{NEW}`.\n',
     'All counts from files in this folder (hashes in results/OUTPUT_HASHES.json, computed before gold was read). '
     'Primary parser: frozen P2_SCORING_V2 (sha d05978f4...), INVALID kept in N and counted wrong.\n',
     f'\n## E1 C2C port fidelity (official OBQA test, N=500)\n\nOfficial dataset prefetch: {json.dumps({k: prefetch.get(k) for k in ["clean_usable", "config", "n", "rows_identical_in_order_to_local_parquet"]})}. '
     f'Legacy (official) parser source identical to P2_10 copy: {LEGACY_IDENTICAL}.\n\n',
     md(e1_acc, ['pair', 'action', 'path', 'n_available', 'correct_v2_of_500', 'invalid_v2', 'correct_legacy_parser_of_500', 'correct_official_evaluator_reported', 'source']),
     '\nOURS vs OFFICIAL per pair x action (parsed with P2_SCORING_V2 on both raw outputs):\n\n',
     md(e1_agree, ['pair', 'action', 'n_compared', 'parsed_answer_agreement', 'raw_output_exact_match', 'rendered_prompts_byte_identical_first3', 'prompt_detail']),
     '\nParsed-answer disagreement IDs (official_index:OBQA id):\n\n' + ''.join(f"- {r['pair']} {r['action']}: {r['parsed_disagreement_ids'] or 'none'}\n" for r in e1_agree),
     '\nFull per-question differences: results/e1_disagreements.csv. Raw outputs: results/e1/ours/*.jsonl, results/e1/official/*/..._cot.csv (small C2C: task7 CSV).\n',
     '\n## E4 null controls (receiver-only, content-free input changes)\n\nR = paper saved development outputs; V1 = options rotated by one (answers mapped back); V2 = Text-reference prompt carrying the helper message of position (i+floor(N/2)) mod N. '
     'Oracle gain = (oracle - best single) / N in percentage points. V0 = supplementary same-job unchanged R replay (not requested).\n\n',
     md(e4_rows, ['pair', 'population', 'N', 'V1_V2_complete', 'R_correct_paper_saved', 'V1_perm_correct', 'V2_irrelevant_msg_correct', 'oracle_R_V1_V2', 'oracle_gain_R_V1_V2_pp',
                  'answer_change_rate_R_vs_V1_pct', 'answer_change_rate_R_vs_V2_pct', 'paper_oracle_R_T_C', 'paper_oracle_gain_pp', 'matches_table1']),
     '\nSupplementary columns (invalid counts, pairwise oracles, V0 replay, re-parse checks): results/e4_null_controls.csv.\n',
     '\n## E2b D features\n\n', md(e2b_rows, ['setting', 'split', 'pair', 'expected', 'written', 'dimension', 'ids_match_population_order', 'all_finite', 'unit_norm']),
     '\n## Notes\n\n' + (''.join(f'- {n}\n' for n in NOTES) or '- none\n')]
(RES / 'SUMMARY.md').write_text(''.join(S))
print(''.join(S))
