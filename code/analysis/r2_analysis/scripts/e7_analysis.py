"""Task 1 - E7 analysis, exactly as frozen in e7/PROTOCOL_FREEZE_E7.md section 3.

8 deployed policies x 3 policy arms (ORIGINAL, REUSE, ARGMAX) against the FIXED reference arm of the
SAME run.  Reuses the frozen E3 bootstrap (2,000 paired resamples, seed 0) and the frozen E3 cold rule.
Gold is read only for the correct-answer counts (the replay itself recorded gold_read=false).
"""
import sys
sys.dont_write_bytecode = True
from common_r2a import *      # noqa: F401,F403
import numpy as np

ARMS = ['original', 'reuse', 'argmax']
# (pair, task, reference, stage folder, `setting` field, panel-id source, gold source)
POLICIES = [
    ('large', 'OBQA', 'Text', 'large', 'large/obqa/T', 'obqa'),
    ('large', 'OBQA', 'C2C', 'large', 'large/obqa/C', 'obqa'),
    ('large', 'ARC', 'Text', 'large', 'large/arc/T', 'arc'),
    ('large', 'ARC', 'C2C', 'large', 'large/arc/C', 'arc'),
    ('medium', 'OBQA', 'C2C', 'medium', 'medium/obqa/C', 'obqa'),
    ('medium', 'ARC', 'C2C', 'medium', 'medium/arc/C', 'arc'),
    ('large', 'MMLU-Pro', 'Text', 'mmlu', 'large/mmlu_pro/T', 'mmlu_pro'),
    ('large', 'MMLU-Pro', 'C2C', 'mmlu', 'large/mmlu_pro/C', 'mmlu_pro'),
]

STOP = []


def stop(cond, msg):
    if not cond:
        STOP.append(msg)


# ---------------------------------------------------------------- records
recs = {}
for st in ['large', 'mmlu', 'medium']:
    rows = jl(E7 / f'{st}/records_e7/e7_requests.jsonl')
    stop(len({r['key'] for r in rows}) == len(rows), f'{st}: duplicate request keys')
    for r in rows:
        recs[r['setting'], r['id'], r['arm']] = r

VER = read(E7 / 'REPLAY_VERIFICATION.json')
for st in ['large', 'mmlu', 'medium']:
    stop(VER[st]['complete'] and VER[st]['marker'] == 'COMPLETE', f'{st}: replay not COMPLETE')
    stop(VER[st]['runtime_failures'] == 0, f'{st}: runtime failures')
    stop(VER[st]['gold_read'] is False, f'{st}: gold was read during the replay')

# ---------------------------------------------------------------- panels and gold
PANEL, GOLD = {}, {}
for ds in ['obqa', 'arc']:
    PANEL['large', ds] = read(E7 / f'large/inputs/{ds}_panel_ids.json')
    PANEL['medium', ds] = read(E7 / f'medium/inputs/{ds}_panel_ids.json')
PANEL['large', 'mmlu_pro'] = read(E7 / 'mmlu/inputs/candidate_e2e128_ids.json')

for r in jl(E7 / 'large/inputs/evaluation_existing_gold.jsonl'):
    GOLD[r['dataset'], r['id']] = r['gold']
for r in jl(E7 / 'medium/inputs/existing_gold_ANALYSIS_ONLY.jsonl'):
    GOLD.setdefault((r['task'], r['id']), r['gold'])
    stop(GOLD[r['task'], r['id']] == r['gold'], f"gold disagreement for {r['task']}/{r['id']}")
import pyarrow.parquet as pq       # noqa: E402
for r in pq.read_table(REVIEW / 'dataset/test-00000-of-00001.parquet',
                       columns=['question_id', 'answer']).to_pylist():
    GOLD['mmlu_pro', f"test:{r['question_id']}"] = r['answer']

# ---------------------------------------------------------------- per-question rows and per-arm summaries
per_q, summ, ratio_rows, probe_rows = [], [], [], []
diffs = []           # every REUSE output that differs from the native R output of the same question
SAV = {}             # (pair, task, reference, arm) -> dict(a=..., b=...)

for pair, task, ref, st, setting, ds in POLICIES:
    ids = PANEL[('large' if pair == 'large' else 'medium'), ds] if ds != 'mmlu_pro' else PANEL['large', 'mmlu_pro']
    stop(len(ids) == len(set(ids)) == 128, f'{setting}: panel is not 128 distinct ids')
    idx_a = bidx(128)
    fx = {i: recs[setting, i, 'fixed'] for i in ids}
    for arm in ARMS:
        ar = {i: recs[setting, i, arm] for i in ids}
        # ---- freeze-consistency checks
        for i in ids:
            f, a = fx[i], ar[i]
            stop(abs(sum(f['parts_ms'].values()) - f['latency_ms']) < 1e-7, f'{setting}/{i}: fixed parts do not sum')
            stop(abs(sum(a['parts_ms'].values()) - a['latency_ms']) < 1e-7, f'{setting}/{i}/{arm}: parts do not sum')
            stop(not f['runtime_failure'] and not a['runtime_failure'], f'{setting}/{i}/{arm}: runtime failure')
            stop(f['selected'] == a['reference'] and not f['omitted'], f'{setting}/{i}: fixed arm omitted')
            thr = a['threshold_A'] if arm == 'argmax' else a['threshold']
            stop(a['omitted'] == (a['ProbeMax'] <= thr), f'{setting}/{i}/{arm}: omission does not match its threshold')
            stop(a['omitted'] == (a['selected'] == 'R'), f'{setting}/{i}/{arm}: selected/omitted inconsistent')
            # freeze 2.2/2: the kept KV cache is consumed only on omitted questions; on kept
            # questions arm (3) runs the reference exactly as arm (2), so the flag is False there.
            stop((a['probe_KV_reuse'] is True) == (arm == 'reuse' and a['omitted']),
                 f'{setting}/{i}/{arm}: probe_KV_reuse flag')
            stop((a['probe_argmax_answer'] is True) == (arm == 'argmax' and a['omitted']),
                 f'{setting}/{i}/{arm}: probe_argmax_answer flag')
            o = recs[setting, i, 'original']
            stop(a['ProbeMax'] == o['ProbeMax'], f'{setting}/{i}/{arm}: ProbeMax differs from ORIGINAL')
            stop(a['probe']['probe_ids_sha256'] == o['probe']['probe_ids_sha256'],
                 f'{setting}/{i}/{arm}: probe input hash differs from ORIGINAL')
            stop(a['probe']['argmax_probe_label'] == o['probe']['argmax_probe_label'],
                 f'{setting}/{i}/{arm}: probe argmax label differs from ORIGINAL')
            if arm == 'reuse':
                stop(a['omitted'] == o['omitted'], f'{setting}/{i}: REUSE and ORIGINAL omit differently')
                if a['raw_answer'] != o['raw_answer']:
                    diffs.append(dict(setting=setting, panel=f'{pair}/{task}', id=i, omitted=a['omitted'],
                                      reuse_raw=a['raw_answer'], original_raw=o['raw_answer'],
                                      reuse_label=a['answer'], original_label=o['answer'], label=LABEL))
            if arm == 'argmax' and a['omitted']:
                stop(a['answer'] == a['probe']['argmax_probe_label'],
                     f'{setting}/{i}: ARGMAX answer is not the probe argmax label')
        # ---- version (a)
        d_a = [fx[i]['latency_ms'] - ar[i]['latency_ms'] for i in ids]
        A = paired(d_a, idx_a)
        # ---- version (b): drop the question of each arm's first formal request (frozen E3 rule)
        ff = min((fx[i] for i in ids), key=lambda r: r['attempt'])
        af = min((ar[i] for i in ids), key=lambda r: r['attempt'])
        excl = {ff['id'], af['id']}
        keep = [i for i in ids if i not in excl]
        B = paired([fx[i]['latency_ms'] - ar[i]['latency_ms'] for i in keep], bidx(len(keep)))
        # ---- panel quantities (gold read here, for accuracy only)
        om = [i for i in ids if ar[i]['omitted']]
        changed = sum(ar[i]['answer'] != fx[i]['answer'] for i in om)
        g = lambda r, i: int(r['answer'] == GOLD[ds, i])       # noqa: E731
        c_arm = sum(g(ar[i], i) for i in ids)
        c_fix = sum(g(fx[i], i) for i in ids)
        probe = float(np.mean([ar[i]['parts_ms']['probe_ms'] for i in ids]))
        sel = float(np.mean([ar[i]['parts_ms']['selector_ms'] for i in ids]))
        SAV[pair, task, ref, arm] = dict(a=A, b=B)
        summ.append(dict(pair=pair, task=task, reference=ref, arm=arm.upper(), setting=setting, N=128,
                         deployed_q=ar[ids[0]]['deployed_q'], q_A=ar[ids[0]]['q_A'],
                         omitted=len(om), coverage=round(len(om) / 128, 6),
                         a_mean_saving_ms=A['mean'], a_CI_low=A['lo'], a_CI_high=A['hi'], a_class=A['cls'],
                         a_median_saving_ms=A['median'],
                         b_N=B['n'], b_excluded_ids=';'.join(sorted(excl)),
                         b_mean_saving_ms=B['mean'], b_CI_low=B['lo'], b_CI_high=B['hi'], b_class=B['cls'],
                         b_median_saving_ms=B['median'],
                         mean_probe_ms=probe, mean_selector_ms=sel,
                         mean_arm_latency_ms=float(np.mean([ar[i]['latency_ms'] for i in ids])),
                         mean_fixed_latency_ms=float(np.mean([fx[i]['latency_ms'] for i in ids])),
                         changed_on_omitted=changed, changed_over_omitted=f'{changed}/{len(om)}',
                         correct_arm=c_arm, correct_fixed=c_fix, accuracy_diff_answers=c_arm - c_fix,
                         invalid_arm=sum(ar[i]['invalid'] for i in ids),
                         invalid_fixed=sum(fx[i]['invalid'] for i in ids), label=LABEL))
        probe_rows.append(dict(setting=setting, arm=arm.upper(), mean_probe_ms=probe,
                               median_probe_ms=float(np.median([ar[i]['parts_ms']['probe_ms'] for i in ids])),
                               mean_selector_ms=sel, label=LABEL))
        for i in ids:
            per_q.append(dict(pair=pair, task=task, reference=ref, arm=arm.upper(), id=i,
                              panel_ordinal=ar[i]['panel_ordinal'], order_position=ar[i]['order_position'],
                              ProbeMax=ar[i]['ProbeMax'], omitted=int(ar[i]['omitted']),
                              fixed_ms=fx[i]['latency_ms'], arm_ms=ar[i]['latency_ms'],
                              saving_ms=fx[i]['latency_ms'] - ar[i]['latency_ms'],
                              probe_ms=ar[i]['parts_ms']['probe_ms'],
                              arm_answer=ar[i]['answer'], fixed_answer=fx[i]['answer'], gold=GOLD[ds, i],
                              arm_correct=g(ar[i], i), fixed_correct=g(fx[i], i),
                              changed_vs_fixed=int(ar[i]['answer'] != fx[i]['answer']),
                              in_version_b=int(i in keep), label=LABEL))

# ---------------------------------------------------------------- Text/C2C saving ratio (large pair)
for task in ['OBQA', 'ARC', 'MMLU-Pro']:
    for arm in ARMS:
        t = SAV['large', task, 'Text', arm]
        c = SAV['large', task, 'C2C', arm]
        ratio_rows.append(dict(pair='large', benchmark=task, arm=arm.upper(),
                               a_Text_saving_ms=t['a']['mean'], a_C2C_saving_ms=c['a']['mean'],
                               a_ratio_Text_over_C2C=t['a']['mean'] / c['a']['mean'],
                               b_Text_saving_ms=t['b']['mean'], b_C2C_saving_ms=c['b']['mean'],
                               b_ratio_Text_over_C2C=t['b']['mean'] / c['b']['mean'],
                               note='ratio of paired mean savings; C2C denominator near zero on MMLU-Pro',
                               label=LABEL))

# ---------------------------------------------------------------- descriptive E3 class comparison
e3 = [r for r in csv.DictReader(open(EXP / 'results/E3_policy_savings.csv'))]
e3_rows = []
for pair, task, ref, st, setting, ds in POLICIES:
    o = SAV[pair, task, ref, 'original']
    row = dict(pair=pair, task=task, reference=ref, E7_ORIGINAL_class_a=o['a']['cls'], E7_ORIGINAL_class_b=o['b']['cls'])
    ma, mb = [], []
    for rep in ['REPEAT1', 'REPEAT2', 'REPEAT3']:
        r = next(x for x in e3 if x['repeat'] == rep and (x['pair'], x['task'], x['reference']) == (pair, task, ref))
        ca = cls(float(r['a_CI_low']), float(r['a_CI_high']))
        cb = r['b_class']
        row[f'{rep}_a'] = ca
        row[f'{rep}_b'] = cb
        ma.append(ca == o['a']['cls'])
        mb.append(cb == o['b']['cls'])
    row.update(matches_all_three_a='yes' if all(ma) else 'no', matches_all_three_b='yes' if all(mb) else 'no',
               source=str(EXP / 'results/E3_policy_savings.csv'), label='descriptive only; no cross-run equality claimed')
    e3_rows.append(row)

wcsv('E7_arm_summary.csv', summ)
wcsv('E7_per_question.csv', per_q)
wcsv('E7_text_c2c_ratio.csv', ratio_rows)
wcsv('E7_probe_cost.csv', probe_rows)
wcsv('E7_reuse_output_differences.csv', diffs or [dict(setting='(none)', panel='', id='', omitted='',
                                                       reuse_raw='', original_raw='', reuse_label='',
                                                       original_label='', label=LABEL)])
wcsv('E7_e3_class_comparison.csv', e3_rows)

tot = {}
for r in summ:
    st = recs[r['setting'], PANEL['large', 'mmlu_pro'][0] if 'mmlu' in r['setting'] else
              PANEL[('large' if r['pair'] == 'large' else 'medium'),
                    {'OBQA': 'obqa', 'ARC': 'arc'}[r['task']]][0], 'fixed']['stage']
    tot.setdefault(st, {}).setdefault(r['arm'].lower(), 0)
    tot[st][r['arm'].lower()] += r['omitted']
json.dump(dict(stop_conditions=STOP, n_reuse_output_differences=len(diffs),
               omitted_per_stage_recomputed=tot,
               reuse_differences_all_on_omitted=all(d['omitted'] for d in diffs),
               omitted_per_stage_recorded={st: VER[st]['omitted_per_arm'] for st in ['large', 'mmlu', 'medium']}),
          open(RES / 'E7_CHECKS.json', 'w'), indent=2)
print('STOP CONDITIONS:', STOP if STOP else 'none')
print('reuse output differences:', len(diffs))
for r in summ:
    print(f"{r['pair']}/{r['task']}/{r['reference']:4s} {r['arm']:8s} om={r['omitted']:3d} "
          f"a={r['a_mean_saving_ms']:8.1f} [{r['a_CI_low']:8.1f},{r['a_CI_high']:8.1f}] {r['a_class']} "
          f"b={r['b_mean_saving_ms']:8.1f} [{r['b_CI_low']:8.1f},{r['b_CI_high']:8.1f}] {r['b_class']} "
          f"med={r['a_median_saving_ms']:8.1f} probe={r['mean_probe_ms']:6.1f} "
          f"ch={r['changed_on_omitted']}/{r['omitted']} corr={r['correct_arm']}/{r['correct_fixed']}")
