"""Item 7 (POST-HOC, read-only provenance). Timestamps are read from files (internal utc fields where present, else mtime)."""
import os, datetime, collections
from common_r1 import *

FREEZE = '2026-09-14T04:41:36Z'  # P2_RISK_CALIBRATION_BINARY frozen_config.json mtime


def mt(p): return datetime.datetime.fromtimestamp(os.stat(p).st_mtime, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


BINF = BIN / 'frozen_config.json'; cfg = read(BINF)
ZGF = ZG / 'frozen_config.json'
MEDP = ROOT / 'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z'
facts = dict(
    freeze_file=f"{BINF} mtime {mt(BINF)}; contains alpha={cfg['alpha']}, p_cutoff={cfg['p_cutoff']}, delta={cfg['delta']}, q_grid(20); families={cfg['families']}; 'ProbeMax' present: {'ProbeMax' in BINF.read_text()}",
    probemax_first_frozen=f"{ZGF} mtime {mt(ZGF)} (families {read(ZGF)['families']}); earliest file mentioning ProbeMax: {ZG/'src/common.py'} {mt(ZG/'src/common.py')}",
    obqa_split_created=f"{BIN/'SPLIT_FREEZE.json'} utc {read(BIN/'SPLIT_FREEZE.json')['utc']} ({read(BIN/'SPLIT_FREEZE.json')['rng']}; labels_read={read(BIN/'SPLIT_FREEZE.json')['labels_read']})",
    arc_split_created=f"{BND/'SPLIT_FREEZE.json'} utc {read(BND/'SPLIT_FREEZE.json')['utc']} (outcomes_used={read(BND/'SPLIT_FREEZE.json')['outcomes_used']})",
    mmlu_split_protocol=f"{MMLU/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json'} utc {read(MMLU/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json')['utc']}",
    medium_protocol=f"{MEDP/'MEDIUM_PAIR_PROTOCOL_FREEZE.json'} utc {read(MEDP/'MEDIUM_PAIR_PROTOCOL_FREEZE.json')['utc']}",
    first_cal_statistic_any=f"{BIN/'inputs/candidate_cal.jsonl'} mtime {mt(BIN/'inputs/candidate_cal.jsonl')}; {BIN/'summary/calibration_100.csv'} mtime {mt(BIN/'summary/calibration_100.csv')} (large/OBQA/Text only)",
    V2_frozen=f"{V2/'RULE_FREEZE_V2.json'} frozen_utc {read(V2/'RULE_FREEZE_V2.json')['frozen_utc']}; disclosure: {read(V2/'RULE_FREEZE_V2.json')['exposure_disclosure']}",
    planning_prompt=f"{ROOT/'P2_POST_E2E_METHOD_REVIEW_20260914T034957Z/NEXT_EXPERIMENT_ClusterB_PROMPT_ZH.md'} mtime {mt(ROOT/'P2_POST_E2E_METHOD_REVIEW_20260914T034957Z/NEXT_EXPERIMENT_ClusterB_PROMPT_ZH.md')}: proposed fit2100/cal1366 split stratified by f_R (R vs Text flip); implemented split was unstratified/label-independent",
)
cal = {ds: set(read(BND / f'splits/{ds}_cal_ids.json')) for ds in ['obqa', 'arc']}

# Superset (full-train) pre-freeze statistics that include later-cal questions; never restricted to the cal split
superset = [
    (ROOT / 'P2_SCORE_SENSITIVITY_20260912T055929Z/pairwise_answer_agreement.csv', 'R-vs-Text/C2C answer agreement on FULL train (3466 OBQA/1119 ARC), saved(V1)+diagnostic parser, small+large'),
    (ROOT / 'P2_SCORE_SENSITIVITY_20260912T055929Z/case_review.jsonl', 'record-level parser case review incl. gold (V2 rule development)'),
    (V2 / 'pairwise_agreement.csv', 'R-vs-Text/C2C agreement on FULL train, V2 parser, small+large'),
    (V2 / 'action_summary.csv', 'per-action correctness on FULL train, V2, small+large'),
    (ROOT / 'P2_V2_BASELINES_FFR_E0_20260913T000052Z/flip_metrics.csv', '5-fold OOF R-vs-action flip AUC/AP on FULL train, small+large x OBQA/ARC'),
    (ROOT / 'P2_V2_BASELINES_FFR_E0_20260913T000052Z/decision_metrics.csv', '5-fold OOF router decisions/accuracy on FULL train, small+large x OBQA/ARC'),
    (E1 / 'summary/flip_metrics.csv', '5-fold OOF flip AUC on FULL train (E1 features), small+large x OBQA/ARC'),
    (ROOT / 'P2_E1_E2E_OBQA_20260913T174210Z/FINAL_RECEIPT.json', 'large/OBQA only: routers fit on FULL train (R,T,C,A), evaluated on dev'),
]
cr = jl(ROOT / 'P2_SCORE_SENSITIVITY_20260912T055929Z/case_review.jsonl')
review_q = collections.defaultdict(set)
for r in cr:
    if r['split'] == 'train' and str(r['id']) in cal[r['dataset']]: review_q[r['pair'], r['dataset']].add(r['id'])

rows = []
for s in SETTINGS:
    pair, task, ref = s
    if s == ('large', 'OBQA', 'Text'): continue
    if task == 'MMLU-Pro':
        status = 'NONE FOUND'; why = f"MMLU-Pro split/protocol frozen {read(MMLU/'MMLU_PRO_STAGE1_PROTOCOL_FREEZE.json')['utc']}; cal answers produced 2026-09-16T15:27-19:01Z (shards/*/actions/cal.jsonl) - all after {FREEZE}"; sup = 'none (no MMLU-Pro outputs existed before freeze)'
    elif pair == 'medium':
        status = 'NONE FOUND'; why = f"medium protocol frozen {read(MEDP/'MEDIUM_PAIR_PROTOCOL_FREEZE.json')['utc']}; medium cal answers produced 2026-09-15 (execution_retry1/actions/*_cal.jsonl utc) - all after {FREEZE}"; sup = 'none (no medium-pair outputs existed before freeze)'
    else:
        ds = task.lower()
        split_time = read(BIN / 'SPLIT_FREEZE.json')['utc'] if ds == 'obqa' else read(BND / 'SPLIT_FREEZE.json')['utc']
        status = 'NONE FOUND'
        why = (f"{task} cal split did not exist before {split_time}; cal-split R-vs-{ref} d first written "
               f"{mt(BND / f'inputs/{pair}_{ds}_cal_machine_d.jsonl')} ({BND / f'inputs/{pair}_{ds}_cal_machine_d.jsonl'}), after BOUNDARIES protocol freeze {read(BND/'PROTOCOL_FREEZE.json')['utc']}")
        if s == ('large', 'OBQA', 'C2C'): why += '; between 04:41 and 16:52 only large/OBQA/Text (R/Text) was computed on this cal split (RISK_CALIBRATION_BINARY, GOLD_BUDGET, ZERO_GOLD_CONTROLS)'
        sup = (f"SUPERSET only (full-train stats containing the {len(cal[ds])} later-cal questions): SCORE_SENSITIVITY 2026-09-12T06:07Z, SCORING_V2 2026-09-12T19:23Z, "
               f"V2_BASELINES_FFR_E0 2026-09-13T04:35Z, E1_DIRECTION 2026-09-13T06:51Z" + (', E1_E2E_OBQA 2026-09-13T17:46-20:01Z' if (pair, ds) == ('large', 'obqa') else '') +
               f"; parser case review touched {len(review_q[pair, ds])} later-cal questions (record level, incl. gold)")
    rows.append(dict(pair=pair, task=task, reference=ref, status_before_freeze=status, evidence=why, superset_exposure=sup, label=LABEL))
csvout(P / 'results/item7_provenance_by_setting.csv', rows)

# First production of cal-split R/Text/C2C answers (small, large): V2 label source pointers restricted to cal ids
prod = []
src = collections.defaultdict(set); jobs = collections.defaultdict(set)
with (V2 / 'labels/full_train_P2_SCORING_V2.jsonl').open() as f:
    for line in f:
        r = json.loads(line)
        if r['id'] in cal[r['dataset']]:
            for a in 'RTC': src[r['pair'], r['dataset']].add(r['source_' + a]['source_path']); jobs[r['pair'], r['dataset']].add(r['source_' + a]['job_id'])
for (pair, ds), paths in sorted(src.items()):
    for p in sorted(paths):
        rr = [json.loads(l) for l in open(p)]
        sel = [x for x in rr if str(x['id']) in cal[ds]]
        utcs = sorted(x['utc'] for x in sel if x.get('utc'))
        prod.append(dict(pair=pair, task=TASK[ds], source_path=p, cal_rows=len(sel), jobs=';'.join(sorted(jobs[pair, ds])),
                         row_utc_first=utcs[0] if utcs else 'n/a (no per-row utc)', row_utc_last=utcs[-1] if utcs else 'n/a', file_mtime=mt(p), parser_at_production='original saved scoring ("old" in SCORING_V2; pre-D1/V2); V2 labels built 2026-09-12T19:23Z', label=LABEL))
csvout(P / 'results/item7_cal_answer_production.csv', prod)
save_rows = [dict(fact=k, value=v) for k, v in facts.items()]
csvout(P / 'results/item7_key_timestamps.csv', save_rows)
for r in save_rows: print(r)
for r in rows: print(r['pair'], r['task'], r['reference'], r['status_before_freeze'])
for r in prod: print({k: v for k, v in r.items() if k != 'label'})
csvout(P / 'results/item7_prefreeze_superset_exposure.csv',
       [dict(path=str(p), mtime=mt(p), before_freeze=mt(p) < FREEZE, what=w, restricted_to_cal_split=False, label=LABEL) for p, w in superset] +
       [dict(path=str(ROOT / 'P2_SCORE_SENSITIVITY_20260912T055929Z/case_review.jsonl'), mtime=mt(ROOT / 'P2_SCORE_SENSITIVITY_20260912T055929Z/case_review.jsonl'), before_freeze=True,
             what='unique later-cal questions reviewed: ' + '; '.join(f'{a}/{b}={len(v)}' for (a, b), v in sorted(review_q.items())), restricted_to_cal_split=False, label=LABEL)])
