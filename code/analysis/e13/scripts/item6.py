"""E13 Item 6: what the probe cost consists of.

(A) Appendix F component panels = the 128-question development panels of P2_CONFIDENCE_REFERENCE_BOUNDARIES
    (records/panel_per_question.jsonl; per-question probe_selector_ms = probe_core_ms + ProbeMax_score_ms + selector_ms,
    run_boundaries.py:67). Components come from the same probe records the panel used (large/OBQA: ZG probe_records;
    others: BND {pair}_{ds}_dev_probes) and the selector time from records/{pair}_{ds}_{b}_routes.jsonl.
    Recorded timers (native probe code): tokenization_prefix (tokenization + prefix construction), prepare_transfer
    (host->device transfer, ends with a CUDA synchronize), prefill_projection (full prefill + last-position lm_head
    projection, one timer, ends with a synchronize; its GPU-event part is GPU_prefill_projection_event_ms),
    label_distribution (label probabilities, ends with a synchronize), ProbeMax_score, selector. Synchronization is not
    a separate timer: it sits at the end of each interval. Medium-pair and MMLU-Pro probe records store only the total.
(B) Reproduction: sealed ARC mean probe + selector (probe_timing_2344.jsonl) and MMLU-Pro original replay mean probe.
(C) End-to-end mean probe + selector (policy requests) from every replay; component means where the replay records them.
(D) E7 REUSE arm: what it saves on omitted requests.
"""
import csv, json
import numpy as np
from e13_common import *

BND = ROOT / 'P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z'
ZG = ROOT / 'P2_ZERO_GOLD_CONTROLS_20260914T065145Z'
MEDX = ROOT / 'P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z'
MMLU1 = ROOT / 'P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z'
FP = ROOT / 'P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z'
ME = ROOT / 'P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z'
MP = ROOT / 'P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z'
SA = ROOT / 'P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z'
E7 = ROOT / 'P2_R2_E7_20260919T231531Z'
REP = {k: ROOT / f'P2_R1_E3POL_{k}_20260919T075315Z' for k in ['REPEAT1', 'REPEAT2', 'REPEAT3']}
COMP = ['tokenization_prefix_ms', 'prepare_transfer_ms', 'prefill_projection_ms', 'label_distribution_ms']
m = lambda xs: float(np.mean(xs))
TN = {'obqa': 'OBQA', 'arc': 'ARC'}

# ---------------- (A) component panels
panel = [json.loads(l) for l in open(BND / 'records/panel_per_question.jsonl')]
rowsA = []
for pair in ['small', 'large']:
    for ds in ['obqa', 'arc']:
        pids = read(BND / f'inputs/{ds}_panel_ids.json')['dev']
        if (pair, ds) == ('large', 'obqa'):
            P = {r['id']: r for r in jl(ZG / 'records/probe_records.jsonl') if r['split'] == 'dev'}
        else:
            P = {r['id']: r for r in jl(BND / f'records/{pair}_{ds}_dev_probes.jsonl')}
        for b, bn in [('T', 'Text'), ('C', 'C2C')]:
            R = {r['id']: r for r in jl(BND / f'records/{pair}_{ds}_{b}_routes.jsonl')}
            pp = {r['id']: r for r in panel if (r['pair'], r['dataset'], r['reference'], r['policy']) == (pair, ds, b, 'ProbeMax')}
            core_ok = all(abs(sum(P[i][c] for c in COMP) - P[i]['probe_core_ms']) < 1e-6 for i in pids)
            tot = [P[i]['probe_core_ms'] + P[i]['ProbeMax_score_ms'] + R[i]['selector_ms'] for i in pids]
            meas = [R[i]['measured_selective_overhead_ms'] for i in pids]
            row = dict(panel=f'{pair}/{TN[ds]}', reference=bn, source='Appendix F component panel (BND, 128 dev-panel questions)', n=len(pids),
                       **{f'mean_{c}': m([P[i][c] for i in pids]) for c in COMP},
                       mean_GPU_prefill_projection_event_ms=m([P[i]['GPU_prefill_projection_event_ms'] for i in pids]),
                       mean_score_ms=m([P[i]['ProbeMax_score_ms'] for i in pids]), mean_selector_ms=m([R[i]['selector_ms'] for i in pids]),
                       mean_sum_ms=m(tot), mean_panel_probe_selector_ms=m([pp[i]['probe_selector_ms'] for i in pids]) if pp else '',
                       sum_equals_route_measured=bool(np.allclose(tot, meas)), probe_core_equals_4_components=core_ok,
                       prefill_projection_share_of_sum=m([P[i]['prefill_projection_ms'] for i in pids]) / m(tot),
                       n_cold_first_after_load=sum(bool(P[i].get('cold_first_after_load')) for i in pids), label=LABEL)
            rowsA.append(row)
# medium and MMLU-Pro panels: totals only
for ds in ['obqa', 'arc']:
    pids = read(ME / f'inputs/{ds}_panel_ids.json')
    P = {r['id']: r for sp in ['fit', 'cal', 'dev'] for r in jl(MEDX / f'probes/{ds}_{sp}.jsonl')}
    rowsA.append(dict(panel=f'medium/{TN[ds]}', reference='(probe only)', source=f'{MEDX.name}/probes (total latency_ms only; components not recorded)',
                      n=len(pids), mean_sum_ms=m([P[i]['latency_ms'] for i in pids]), label=LABEL))
pids = np.load(MP / 'protocol/bootstrap_indices.npz')['ids'].tolist()
P = {}
for sh in ['1', '2']:
    for f in sorted((MMLU1 / f'shards/{sh}/probes').glob('*.jsonl')):
        for r in jl(f):
            P[r['id']] = r
rowsA.append(dict(panel='large/MMLU-Pro', reference='(probe only)', source='MMLU-Pro stage-1 shard probes (total latency_ms only; components not recorded)',
                  n=len(pids), mean_sum_ms=m([P[i]['latency_ms'] for i in pids]), label=LABEL))
csvout(RES / 'item6_component_panels.csv', rowsA)
for r in rowsA: print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k not in ('label', 'source')})

# ---------------- (B) reproduction
repro = []
st = jl(SA / 'records/probe_timing_2344.jsonl')
for b, exp in [('T', 42.55), ('C', 40.51)]:
    v = m([r['probe_ms'] + r['selector_ms'] for r in st if r['reference'] == b])
    repro.append(dict(item=6, check=f'sealed ARC mean probe+selector {b}', expected=exp, got=round(v, 2), ok=round(v, 2) == exp))
pt = list(csv.DictReader(open(MP / 'summary/probe_timing.csv')))
for b, exp in [('Text', 48.4), ('C2C', 46.1)]:
    v = m([float(r['online_probe_ms']) + float(r['selector_ms']) for r in pt if r['reference'] == b])
    repro.append(dict(item=6, check=f'MMLU-Pro original replay mean probe(+selector) {b}', expected=exp, got=round(v, 1), ok=round(v, 1) == exp))
csvout(RES / 'item6_repro_checks.csv', repro)
for r in repro: print(r)


# ---------------- (C) end-to-end probe + selector from the replays
def pre(r):
    p = r['parts_ms']
    return sum(v for k, v in p.items() if 'probe' in k or k.startswith('selector'))


rowsC = []


def add(replay, setting, recs):
    pol = recs
    row = dict(replay=replay, setting=setting, n=len(pol), mean_probe_plus_selector_ms=m([pre(r) for r in pol]),
               median_probe_plus_selector_ms=float(np.median([pre(r) for r in pol])))
    pr = [r['probe'] for r in pol if isinstance(r.get('probe'), dict) and 'prefill_projection_ms' in r['probe']]
    if len(pr) == len(pol):
        for c in COMP + ['GPU_prefill_projection_event_ms', 'score_ms']:
            row[f'mean_{c}'] = m([p[c] for p in pr])
        row['prefill_projection_share'] = row['mean_prefill_projection_ms'] / row['mean_probe_plus_selector_ms']
    row['label'] = LABEL
    rowsC.append(row)


for lab_, F, sub in [('original (ClusterB)', FP, '')] + [(k, v, 'large/') for k, v in REP.items()]:
    reqs = jl(F / f'{sub}records/e2e_requests.jsonl')
    for ds in ['obqa', 'arc']:
        for b, bn in [('T', 'Text'), ('C', 'C2C')]:
            add(lab_, f'large/{TN[ds]}/{bn}', [r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'policy')])
for lab_, F, sub in [('original (ClusterB)', ME, '')] + [(k, v, 'medium/') for k, v in REP.items()]:
    reqs = jl(F / f'{sub}records/e2e_requests.jsonl')
    for ds in ['obqa', 'arc']:
        add(lab_, f'medium/{TN[ds]}/C2C', [r for r in reqs if (r['task'], r['arm']) == (ds, 'policy_C')])
for lab_, F, sub in [('original (ClusterB)', MP, '')] + [(k, v, 'mmlu/') for k, v in REP.items()]:
    reqs = jl(F / f'{sub}records/four_arm_requests.jsonl')
    for b, bn in [('T', 'Text'), ('C', 'C2C')]:
        add(lab_, f'large/MMLU-Pro/{bn}', [r for r in reqs if r['arm'] == f'policy_{b}'])
reqs = jl(SA / 'records/e2e_requests.jsonl')
for b, bn in [('T', 'Text'), ('C', 'C2C')]:
    add('sealed ARC test (ClusterB)', f'large/ARC-sealed/{bn}', [r for r in reqs if (r['reference'], r['mode']) == (b, 'policy')])
for stg in ['large', 'mmlu', 'medium']:
    reqs = jl(E7 / f'{stg}/records_e7/e7_requests.jsonl')
    for s_ in sorted({r['setting'] for r in reqs}):
        add('E7 ORIGINAL arm (ClusterA)', s_, [r for r in reqs if r['setting'] == s_ and r['arm'] == 'original'])
add('E6 replay (ClusterA)', 'large/OBQA/Text+fact', [r for r in jl(E7 / 'e6replay/records_e6/e6_replay_requests.jsonl') if r['arm'] == 'policy_TF'])
csvout(RES / 'item6_e2e_probe_cost.csv', rowsC)
for r in rowsC: print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items() if k != 'label'})

# ---------------- (D) E7 REUSE
rowsD = []
for stg in ['large', 'mmlu', 'medium']:
    reqs = jl(E7 / f'{stg}/records_e7/e7_requests.jsonl')
    for s_ in sorted({r['setting'] for r in reqs}):
        o = {r['id']: r for r in reqs if r['setting'] == s_ and r['arm'] == 'original'}
        u = {r['id']: r for r in reqs if r['setting'] == s_ and r['arm'] == 'reuse'}
        om = [i for i in o if o[i]['omitted']]
        assert all(u[i]['omitted'] for i in om)
        act = lambda r: r['latency_ms'] - pre(r)
        rowsD.append(dict(setting=s_, n_omitted=len(om),
                          mean_probe_ms_original=m([pre(o[i]) for i in om]), mean_probe_ms_reuse=m([pre(u[i]) for i in om]),
                          mean_action_ms_original_omitted=m([act(o[i]) for i in om]), mean_action_ms_reuse_omitted=m([act(u[i]) for i in om]),
                          mean_action_saving_reuse_ms=m([act(o[i]) - act(u[i]) for i in om]),
                          mean_request_saving_reuse_ms=m([o[i]['latency_ms'] - u[i]['latency_ms'] for i in om]),
                          reuse_cache_cropped_to_len_R_minus_1=all(u[i]['output'].get('cache_cropped_to') == u[i]['output']['receiver_input_tokens'] - 1 for i in om),
                          receiver_only_prefill_vs_decode_split='not recorded (E7 records hold one wall interval for the action incl. decode and parser, and a GPU-event sum over all forwards)',
                          label=LABEL))
csvout(RES / 'item6_e7_reuse.csv', rowsD)
for r in rowsD: print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items() if k != 'label'})
