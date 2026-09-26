"""Task 2 - E6 end-to-end replay (node B of job 7638030): fixed Text+fact vs the Text+fact policy.

e6/PROTOCOL_FREEZE_E6.md section 6: same protocol as E3 - arm rotation by question ordinal, no warm-up,
cold requests kept, one outer timer per request, versions (a) all requests and (b) cold questions
excluded, 2,000 seed-0 paired bootstrap resamples, classification only.
"""
import sys
sys.dont_write_bytecode = True
from common_r2a import *      # noqa: F401,F403
import numpy as np

STOP = []


def stop(c, m):
    if not c:
        STOP.append(m)


rows = jl(E7 / 'e6replay/records_e6/e6_replay_requests.jsonl')
ids = read(E7 / 'e6replay/inputs/obqa_panel_ids.json')
GOLD = {r['id']: r['gold'] for r in jl(E7 / 'e6replay/inputs/evaluation_existing_gold.jsonl') if r['dataset'] == 'obqa'}
E6RES = read(GPU / 'e6/analysis/E6_RESULTS.json')

VER = read(E7 / 'REPLAY_VERIFICATION.json')['e6replay']
stop(VER['complete'] and VER['marker'] == 'COMPLETE', 'e6replay: not COMPLETE')
stop(VER['runtime_failures'] == 0, 'e6replay: runtime failures')
stop(len(rows) == 256 and len({r['key'] for r in rows}) == 256, 'e6replay: not 256 distinct requests')
stop(len(ids) == len(set(ids)) == 128, 'e6replay: panel is not 128 distinct ids')

rec = {(r['id'], r['arm']): r for r in rows}
fx = {i: rec[i, 'fixed_TF'] for i in ids}
po = {i: rec[i, 'policy_TF'] for i in ids}

for i in ids:
    f, p = fx[i], po[i]
    stop(abs(sum(f['parts_ms'].values()) - f['latency_ms']) < 1e-7, f'{i}: fixed parts do not sum')
    stop(abs(sum(p['parts_ms'].values()) - p['latency_ms']) < 1e-7, f'{i}: policy parts do not sum')
    stop(not f['runtime_failure'] and not p['runtime_failure'], f'{i}: runtime failure')
    stop(f['selected'] == 'TF' and not f['omitted'], f'{i}: fixed arm omitted')
    stop(p['q'] == E6RES['certified_q'] and p['threshold'] == E6RES['certified_threshold'],
         f'{i}: replay q/threshold differ from the certified E6 values')
    stop(p['omitted'] == (p['ProbeMax'] <= p['threshold']), f'{i}: omission does not match the threshold')
    stop(p['omitted'] == (p['selected'] == 'R'), f'{i}: selected/omitted inconsistent')

idx_a = bidx(128)
d_a = [fx[i]['latency_ms'] - po[i]['latency_ms'] for i in ids]
A = paired(d_a, idx_a)
ff = min((fx[i] for i in ids), key=lambda r: r['attempt'])
pf = min((po[i] for i in ids), key=lambda r: r['attempt'])
excl = {ff['id'], pf['id']}
keep = [i for i in ids if i not in excl]
B = paired([fx[i]['latency_ms'] - po[i]['latency_ms'] for i in keep], bidx(len(keep)))

om = [i for i in ids if po[i]['omitted']]
changed = sum(po[i]['answer'] != fx[i]['answer'] for i in om)
c_pol = sum(po[i]['answer'] == GOLD[i] for i in ids)
c_fix = sum(fx[i]['answer'] == GOLD[i] for i in ids)
stop(len(om) == VER['omitted'], 'e6replay: omitted count differs from REPLAY_VERIFICATION.json')

row = dict(pair='large', task='OBQA', reference='Text+fact', N=128, q=E6RES['certified_q'],
           threshold=E6RES['certified_threshold'], omitted=len(om), coverage=round(len(om) / 128, 6),
           a_mean_saving_ms=A['mean'], a_CI_low=A['lo'], a_CI_high=A['hi'], a_class=A['cls'],
           a_median_saving_ms=A['median'],
           b_N=B['n'], b_excluded_ids=';'.join(sorted(excl)),
           b_mean_saving_ms=B['mean'], b_CI_low=B['lo'], b_CI_high=B['hi'], b_class=B['cls'],
           b_median_saving_ms=B['median'],
           mean_probe_ms=float(np.mean([po[i]['parts_ms']['probe_ms'] for i in ids])),
           mean_selector_ms=float(np.mean([po[i]['parts_ms']['selector_ms'] for i in ids])),
           mean_policy_latency_ms=float(np.mean([po[i]['latency_ms'] for i in ids])),
           mean_fixed_latency_ms=float(np.mean([fx[i]['latency_ms'] for i in ids])),
           changed_on_omitted=changed, changed_over_omitted=f'{changed}/{len(om)}',
           correct_policy=c_pol, correct_fixed=c_fix, accuracy_diff_answers=c_pol - c_fix,
           invalid_policy=sum(po[i]['invalid'] for i in ids), invalid_fixed=sum(fx[i]['invalid'] for i in ids),
           interpretation='classification only; no cross-hardware comparison', label=LABEL)
wcsv('E6REPLAY_summary.csv', [row])
wcsv('E6REPLAY_per_question.csv', [dict(
    id=i, panel_ordinal=po[i]['panel_ordinal'], ProbeMax=po[i]['ProbeMax'], omitted=int(po[i]['omitted']),
    fixed_ms=fx[i]['latency_ms'], policy_ms=po[i]['latency_ms'],
    saving_ms=fx[i]['latency_ms'] - po[i]['latency_ms'], probe_ms=po[i]['parts_ms']['probe_ms'],
    policy_answer=po[i]['answer'], fixed_answer=fx[i]['answer'], gold=GOLD[i],
    policy_correct=int(po[i]['answer'] == GOLD[i]), fixed_correct=int(fx[i]['answer'] == GOLD[i]),
    changed_vs_fixed=int(po[i]['answer'] != fx[i]['answer']), in_version_b=int(i in keep), label=LABEL)
    for i in ids])
json.dump(dict(stop_conditions=STOP, omitted_recomputed=len(om), omitted_recorded=VER['omitted'],
               selected_recorded=VER['selected']), open(RES / 'E6REPLAY_CHECKS.json', 'w'), indent=2)
print('STOP CONDITIONS:', STOP if STOP else 'none')
print(f"omitted {row['omitted']}/128  a={row['a_mean_saving_ms']:.1f} [{row['a_CI_low']:.1f},{row['a_CI_high']:.1f}] {row['a_class']}"
      f"  b(N={row['b_N']})={row['b_mean_saving_ms']:.1f} [{row['b_CI_low']:.1f},{row['b_CI_high']:.1f}] {row['b_class']}"
      f"  median={row['a_median_saving_ms']:.1f}  probe={row['mean_probe_ms']:.1f}"
      f"  changed={row['changed_over_omitted']}  correct {row['correct_policy']}/{row['correct_fixed']}")
