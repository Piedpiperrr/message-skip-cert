"""E13 Item 9: calibration cost payback for the 8 deployed policies (arithmetic on measured means only).

Means from the three ClusterA E3 repeats, version (b) (questions on which either arm made its first formal request dropped,
e3_metrics.py rule), computed per repeat and then averaged over the three repeats:
  probe      = probe + selector part of the policy request (all version-(b) questions)
  R request  = action part of the policy request (latency - input prep - probe - selector) on omitted questions
  ref request= fixed-arm latency (all version-(b) questions)
C_s = N_fit * probe + N_cal * (probe + R request);  C_a = C_s + N_cal * ref request.
Saving per query = mean of the three E3 (b) mean savings (E3_policy_savings.csv, recomputed here and checked);
large/MMLU-Pro/C2C uses the full 2,641-question replay (b) saving. W = C / saving (queries).
"""
import csv
import numpy as np
from e13_common import *

REP = {k: ROOT / f'P2_R1_E3POL_{k}_20260919T075315Z' for k in ['REPEAT1', 'REPEAT2', 'REPEAT3']}
FULL = ROOT / 'P2_R1_E3POL_MMLU_C2C_FULL_20260919T075315Z/results/e3_full_saving.csv'
E3S = ROOT / 'P2_R1_EXP_20260919T050555Z/results/E3_policy_savings.csv'
NN = {'OBQA': (2100, 1366), 'ARC': (670, 448), 'MMLU-Pro': (3000, 6000)}


def pre(r):
    return sum(v for k, v in r['parts_ms'].items() if 'probe' in k or k.startswith('selector'))


def pre_all(r):
    return sum(v for k, v in r['parts_ms'].items() if k.startswith('input_prep') or 'probe' in k or k.startswith('selector'))


def streams(F):
    reqs = jl(F / 'large/records/e2e_requests.jsonl')
    for ds, task in [('obqa', 'OBQA'), ('arc', 'ARC')]:
        ids = read(F / f'large/inputs/{ds}_panel_ids.json')
        for b, ref in [('T', 'Text'), ('C', 'C2C')]:
            yield ('large', task, ref), ids, {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'reference')}, \
                {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'policy')}
    reqs = jl(F / 'medium/records/e2e_requests.jsonl')
    for ds, task in [('obqa', 'OBQA'), ('arc', 'ARC')]:
        ids = read(F / f'medium/inputs/{ds}_panel_ids.json')
        yield ('medium', task, 'C2C'), ids, {r['id']: r for r in reqs if (r['task'], r['arm']) == (ds, 'fixed_C')}, \
            {r['id']: r for r in reqs if (r['task'], r['arm']) == (ds, 'policy_C')}
    reqs = jl(F / 'mmlu/records/four_arm_requests.jsonl')
    ids = read(F / 'mmlu/inputs/candidate_e2e128_ids.json')
    for b, ref in [('T', 'Text'), ('C', 'C2C')]:
        yield ('large', 'MMLU-Pro', ref), ids, {r['id']: r for r in reqs if r['arm'] == f'fixed_{b}'}, \
            {r['id']: r for r in reqs if r['arm'] == f'policy_{b}'}


e3 = {(r['repeat'], r['pair'], r['task'], r['reference']): float(r['b_mean_ms']) for r in csv.DictReader(open(E3S))}
per = {}
repro = []
for rep, F in REP.items():
    for s, ids, fx, po in streams(F):
        ff = min(fx.values(), key=lambda r: r['attempt']); pf = min(po.values(), key=lambda r: r['attempt'])
        keep = [i for i in ids if i not in {ff['id'], pf['id']}]
        om = [i for i in keep if po[i]['selected'] == 'R']
        sav = float(np.mean([fx[i]['latency_ms'] - po[i]['latency_ms'] for i in keep]))
        per[rep, s] = dict(probe=float(np.mean([pre(po[i]) for i in keep])),
                           R=float(np.mean([po[i]['latency_ms'] - pre_all(po[i]) for i in om])),
                           ref=float(np.mean([fx[i]['latency_ms'] for i in keep])), saving=sav, n_b=len(keep), n_omitted=len(om))
        repro.append(dict(item=9, check=f'{rep} {"/".join(s)} E3 (b) mean saving', expected=round(e3[(rep,) + s], 6), got=round(sav, 6),
                          ok=abs(e3[(rep,) + s] - sav) < 1e-6))
full = float(next(csv.DictReader(open(FULL)))['b_mean_ms'])
repro.append(dict(item=9, check='large/MMLU-Pro/C2C full replay (b) saving', expected=22.0, got=round(full, 1), ok=round(full, 1) == 22.0))

rows = []
for s in sorted({k[1] for k in per}, key=lambda s: (s[0] != 'large', s[1], s[2])):
    M = {k: float(np.mean([per[r, s][k] for r in REP])) for k in ['probe', 'R', 'ref', 'saving']}
    nf, nc = NN[s[1]]
    Cs = nf * M['probe'] + nc * (M['probe'] + M['R'])
    Ca = Cs + nc * M['ref']
    sav = full if s == ('large', 'MMLU-Pro', 'C2C') else M['saving']
    per_rep_W = [(nf * per[r, s]['probe'] + nc * (per[r, s]['probe'] + per[r, s]['R'])) / sav for r in REP]
    rows.append(dict(policy='/'.join(s), N_fit=nf, N_cal=nc, mean_probe_ms=M['probe'], mean_R_request_ms=M['R'], mean_ref_request_ms=M['ref'],
                     C_shadow_ms=Cs, C_standalone_ms=Ca, C_shadow_h=Cs / 3.6e6, C_standalone_h=Ca / 3.6e6,
                     saving_per_query_ms=sav, saving_source='full 2,641-question replay (b)' if s == ('large', 'MMLU-Pro', 'C2C') else 'mean of 3 ClusterA E3 repeats (b)',
                     W_shadow_queries=Cs / sav if sav > 0 else float('nan'), W_standalone_queries=Ca / sav if sav > 0 else float('nan'),
                     W_shadow_range_over_repeat_means=f'{min(per_rep_W):.0f}-{max(per_rep_W):.0f} (same saving)',
                     n_b_per_repeat=';'.join(str(per[r, s]['n_b']) for r in REP), n_omitted_per_repeat=';'.join(str(per[r, s]['n_omitted']) for r in REP),
                     label=LABEL))
    print(f"{rows[-1]['policy']:22s} probe={M['probe']:.2f} R={M['R']:.1f} ref={M['ref']:.1f} Cs={Cs/1000:.1f}s Ca={Ca/1000:.1f}s "
          f"saving={sav:.1f} W_s={rows[-1]['W_shadow_queries']:.0f} W_a={rows[-1]['W_standalone_queries']:.0f}")
csvout(RES / 'item9_payback.csv', rows)
csvout(RES / 'item9_repro_checks.csv', repro)
print('repro failures:', [r for r in repro if not r['ok']])
