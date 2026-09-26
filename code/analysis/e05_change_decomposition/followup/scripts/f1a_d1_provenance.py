"""E5 follow-up (a): provenance of the D1 diagnostic parser.

Answers, from files only: when and how D1 was developed, which records it was developed on, whether
any gold label or calibration-split output was inspected before the D1 freeze, and whether the
gold-labelled review of the 341 questions happened after it.  Read-only; writes only under followup/.
"""
import ast, collections, datetime, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'scripts'))
sys.dont_write_bytecode = True
from r2_common import ROOT, read, jl, csvout, csvread, BND, LABEL, exposed_ids  # noqa: E402

SENS = ROOT / 'P2_SCORE_SENSITIVITY_20260912T055929Z'
D1 = SENS / 'diagnostic_parser_v1.py'
RULES = SENS / 'DIAGNOSTIC_RULES_V1_ZH.md'
FREEZE = SENS / 'RULE_FREEZE_V1.json'
ANALYSIS = SENS / 'analyze_sensitivity.py'
REVIEW = SENS / 'case_review.jsonl'
V2FREEZE = ROOT / 'P2_SCORING_V2_20260912T191445Z/RULE_FREEZE_V2.json'
RES = HERE / 'results'


def mtime(p):
    return datetime.datetime.fromtimestamp(Path(p).stat().st_mtime, datetime.timezone.utc).isoformat()


def lineno(path, pattern):
    """1-based line numbers of every line matching `pattern`."""
    return [i for i, s in enumerate(Path(path).read_text().splitlines(), 1) if re.search(pattern, s)]


fz = read(FREEZE)
done = read(SENS / 'ANALYSIS_COMPLETE.json')
v2 = read(V2FREEZE)

# ---- 1. how D1 was developed: signature, and the cases it was tuned against -------------------------
src = D1.read_text()
tree = ast.parse(src)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'parse_explicit')
signature = [a.arg for a in fn.args.args]
cases = next(n for n in tree.body if isinstance(n, ast.Assign)
             and getattr(n.targets[0], 'id', None) == 'SYNTHETIC_CASES')
synthetic = ast.literal_eval(cases.value)
known = fz['known_case_disclosed_by_user']

# ---- 2. which records D1 was APPLIED to, after the freeze --------------------------------------------
cfg = read(SENS / 'sources/P2_10_frozen_config.json')
applied = []
for ds, splits in cfg['data'].items():
    for sp, spec in splits.items():
        applied.append(dict(benchmark=ds, split=sp, n_questions=spec['n'], source=spec['source'], label=LABEL))
pairs = sorted({p for p in ['large', 'small']})
srcindex = read(SENS / 'SOURCE_INDEX.json')

# ---- 3. the review set, recomputed ------------------------------------------------------------------
recs, allrev, X, CAL, FIT, DEV = exposed_ids()
rev_rows = jl(REVIEW)
# three nested units: review rows (one per action), pair-question reviews, distinct questions
triples = set()
rows_per = collections.Counter()
per_action = collections.Counter()
for r in rev_rows:
    ds, i = r['dataset'], str(r['id'])
    if r['split'] == 'train' and i in CAL[ds]:
        triples.add((r['pair'], ds, i))
        rows_per[(r['pair'], ds)] += 1
        per_action[r['action']] += 1
per_pair_bench = collections.Counter((p, d) for p, d, i in triples)
distinct = {(d, i) for p, d, i in triples}
gold_in_review = sum(1 for r in rev_rows if 'gold_for_statistics' in r)

# ---- 4. timestamps ----------------------------------------------------------------------------------
cal_split_file = BND / 'splits/obqa_cal_representatives.json'
timeline = [
    dict(utc='2026-09-12T06:01:03Z', event='D1 source written', path=str(D1),
         evidence='file mtime', label=LABEL),
    dict(utc=fz['frozen_utc'], event='D1 FROZEN (rule doc + code hashes recorded)', path=str(FREEZE),
         evidence="RULE_FREEZE_V1.json field 'frozen_utc'; gold_statistics_started=%s" % fz['gold_statistics_started'],
         label=LABEL),
    dict(utc=mtime(ANALYSIS), event='analysis script written (applies frozen D1, reads gold)',
         path=str(ANALYSIS), evidence='file mtime; line 123 calls parse_explicit(txt,legal), line 120/123 compare to gold',
         label=LABEL),
    dict(utc=done['completed_utc'], event='case_review.jsonl written (gold-labelled review of %d records)' % done['review_records'],
         path=str(REVIEW), evidence="ANALYSIS_COMPLETE.json 'completed_utc'; 'gold_statistics_first_started_after'=%s" % done['gold_statistics_first_started_after'],
         label=LABEL),
    dict(utc=v2['frozen_utc'], event='V2 parser frozen', path=str(V2FREEZE),
         evidence="RULE_FREEZE_V2.json 'frozen_utc'", label=LABEL),
    dict(utc=mtime(cal_split_file), event='calibration/fit/development split first created',
         path=str(cal_split_file), evidence='file mtime in P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z',
         label=LABEL),
]

freeze_t = datetime.datetime.fromisoformat(fz['frozen_utc'])
review_t = datetime.datetime.fromisoformat(done['completed_utc'])
split_t = datetime.datetime.fromisoformat(mtime(cal_split_file))

out = dict(
    label=LABEL,
    D1=dict(path=str(D1), sha256=fz['code_sha256'], version=fz['version'], frozen_utc=fz['frozen_utc'],
            rules_doc=str(RULES), rules_sha256=fz['rule_sha256'],
            input_signature=signature, declared_input_signature=fz['input_signature'],
            docstring_line1=src.splitlines()[0],
            parse_explicit_def_line=fn.lineno,
            synthetic_cases_line=cases.lineno, n_synthetic_cases=len(synthetic),
            declared_synthetic_checks=fz['synthetic_checks'],
            known_case_disclosed_by_user=known,
            revision_policy=fz['revision_policy']),
    developed_on=dict(
        project_records_used=0,
        material='%d synthetic (text, legal_labels, expected) triples inside diagnostic_parser_v1.py '
                 'lines %d-%d, plus the single real output "%s" that the user disclosed before the freeze'
                 % (len(synthetic), cases.lineno, cases.lineno + len(synthetic), known),
        gold_used_in_development=False,
        gold_evidence="parse_explicit(text, legal_labels) takes no gold (line %d); "
                      "RULE_FREEZE_V1.json gold_statistics_started=false; "
                      "ANALYSIS_COMPLETE.json gold_statistics_first_started_after=%s"
                      % (fn.lineno, done['gold_statistics_first_started_after']),
        calibration_outputs_used_in_development=False,
        calibration_evidence='no calibration split existed on 2026-09-12: the fit/calibration/development '
                             'split files were first written %s, %.1f days after the D1 freeze'
                             % (mtime(cal_split_file), (split_t - freeze_t).total_seconds() / 86400.)),
    applied_after_freeze=dict(pairs=pairs, benchmarks=sorted(cfg['data']),
                              splits={ds: sorted(sp) for ds, sp in cfg['data'].items()},
                              unique_source_records=done['unique_source_records'],
                              source_index_entries=len(srcindex),
                              review_records=done['review_records'],
                              changed_records=done['changed_unique_source_records'],
                              ambiguous_records=done['ambiguous_unique_source_records'],
                              selection_rule_line=lineno(ANALYSIS, r"if changed or diag\['ambiguous'\]")[0],
                              selection_rule=Path(ANALYSIS).read_text().splitlines()[
                                  lineno(ANALYSIS, r"if changed or diag\['ambiguous'\]")[0] - 1].strip()),
    review_after_freeze=dict(
        case_review_written_utc=done['completed_utc'],
        after_D1_freeze=bool(review_t > freeze_t),
        seconds_after_freeze=(review_t - freeze_t).total_seconds(),
        records_with_gold_field=gold_in_review,
        distinct_calibration_questions=len(distinct),
        pair_question_reviews=sum(per_pair_bench.values()),
        review_rows_one_per_action=sum(rows_per.values()),
        per_pair_benchmark={f'{p}/{d}': n for (p, d), n in sorted(per_pair_bench.items())},
        review_rows_per_pair_benchmark={f'{p}/{d}': n for (p, d), n in sorted(rows_per.items())},
        review_rows_per_action=dict(sorted(per_action.items())),
        matches_e5a_exposed_ids=len(distinct) == len(csvread(HERE.parent / 'results/e5a_exposed_ids.csv'))),
    timeline=timeline)

RES.mkdir(parents=True, exist_ok=True)
(RES / 'f1a_d1_provenance.json').write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
csvout(RES / 'f1a_timeline.csv', timeline)
csvout(RES / 'f1a_applied_records.csv', applied)
csvout(RES / 'f1a_synthetic_cases.csv',
       [dict(n=i + 1, text=t, legal_labels=l, expected=e, label=LABEL)
        for i, (t, l, e) in enumerate(synthetic)])
print(json.dumps({k: out[k] for k in ['developed_on', 'review_after_freeze']}, indent=1, ensure_ascii=False))
