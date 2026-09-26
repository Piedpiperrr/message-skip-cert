"""Items 5-6 (POST-HOC): cold/first-request sensitivity of paired latency savings on the EXISTING replays;
MMLU-Pro panel accuracy interval. Bootstrap = each replay's saved seed-0 indices (default_rng(0).integers(0,n,(2000,n)))."""
import numpy as np
from scipy.stats import trim_mean
from common_r1 import *

FP = ROOT / 'P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z'
ME = ROOT / 'P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z'
MP = ROOT / 'P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z'
SA = ROOT / 'P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z'
PAPER = {('medium', 'OBQA', 'C2C'): (79.7, 48.1, 129.1), ('medium', 'ARC', 'C2C'): (100.7, 74.5, 133.1),
         ('large', 'OBQA', 'Text'): (517.1, 447.8, 583.6), ('large', 'OBQA', 'C2C'): (36.6, 18.0, 56.8),
         ('large', 'ARC', 'Text'): (717.6, 670.6, 763.2), ('large', 'ARC', 'C2C'): (110.9, 82.0, 142.8),
         ('large', 'MMLU-Pro', 'Text'): (346.3, 249.8, 443.0), ('large', 'MMLU-Pro', 'C2C'): (8.2, -20.5, 44.0),
         ('large', 'ARC-sealed-test', 'Text'): (685.6, 669.6, 700.8), ('large', 'ARC-sealed-test', 'C2C'): (90.9, 81.0, 101.0)}
TRIM = .05  # scipy.stats.trim_mean: cut 5% from EACH tail


def ci(boot): return [float(x) for x in np.quantile(boot, [.025, .975])]


def load_idx(path, ids):
    b = np.load(path, allow_pickle=False); assert b['ids'].tolist() == ids
    idx = b['indices']; n = len(ids); assert np.array_equal(idx, np.random.default_rng(0).integers(0, n, size=(2000, n)))
    return idx


def replays():
    """Yield (setting, population, ids(unit order), fixed{id:req}, policy{id:req}, idx_path, correctness or None)."""
    reqs = jl(FP / 'records/e2e_requests.jsonl')
    for ds in ['obqa', 'arc']:
        ids = read(FP / f'inputs/{ds}_panel_ids.json')
        for b in ['T', 'C']:
            fx = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'reference')}
            po = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'policy')}
            yield ('large', TASK[ds], REF[b]), f'dev panel 128 ({FP.name})', ids, fx, po, FP / f'summary/{ds}_bootstrap_indices.npz', FP / 'records/e2e_requests.jsonl'
    reqs = jl(ME / 'records/e2e_requests.jsonl')
    for ds in ['obqa', 'arc']:
        ids = read(ME / f'inputs/{ds}_panel_ids.json')
        fx = {r['id']: r for r in reqs if (r['task'], r['arm']) == (ds, 'fixed_C')}
        po = {r['id']: r for r in reqs if (r['task'], r['arm']) == (ds, 'policy_C')}
        yield ('medium', TASK[ds], 'C2C'), f'dev panel 128 ({ME.name})', ids, fx, po, ME / f'summary/{ds}_bootstrap_indices.npz', ME / 'records/e2e_requests.jsonl'
    reqs = jl(MP / 'records/four_arm_requests.jsonl')
    ids = np.load(MP / 'protocol/bootstrap_indices.npz')['ids'].tolist()
    for b in ['T', 'C']:
        fx = {r['id']: r for r in reqs if r['arm'] == f'fixed_{b}'}
        po = {r['id']: r for r in reqs if r['arm'] == f'policy_{b}'}
        yield ('large', 'MMLU-Pro', REF[b]), f'dev panel 128 ({MP.name})', ids, fx, po, MP / 'protocol/bootstrap_indices.npz', MP / 'records/four_arm_requests.jsonl'
    reqs = jl(SA / 'records/e2e_requests.jsonl')
    ids = read(SA / 'inputs/representative_ids.json')
    for b in ['T', 'C']:
        fx = {r['id']: r for r in reqs if (r['reference'], r['mode']) == (b, 'reference')}
        po = {r['id']: r for r in reqs if (r['reference'], r['mode']) == (b, 'policy')}
        yield ('large', 'ARC-sealed-test', REF[b]), f'sealed test 1172 ({SA.name})', ids, fx, po, SA / 'summary/paired_bootstrap_indices.npz', SA / 'records/e2e_requests.jsonl'


def attempt(r): return r['attempt']


def cold_flag(r): return bool(r.get('cold_first_request') or r.get('first_formal_request_global'))


out5, arms = [], []
for s, pop, ids, fx, po, ipath, rpath in replays():
    assert len(fx) == len(po) >= len(ids) and set(ids) <= set(fx)
    idx = load_idx(ipath, ids)
    d = np.array([fx[i]['latency_ms'] - po[i]['latency_ms'] for i in ids])  # paired saving = fixed - policy
    # (i) paper
    m1, c1 = float(d.mean()), ci(d[idx].mean(axis=1))
    pp = PAPER[s]; repro = (round(m1, 1), round(c1[0], 1), round(c1[1], 1)) == pp
    # each arm's first formal request (execution order = attempt counter within the replay job)
    firsts = {}
    for arm, recs in [('fixed', fx), ('policy', po)]:
        f = min(recs.values(), key=attempt)
        firsts[arm] = f
        arms.append(dict(pair=s[0], task=s[1], reference=s[2], arm=f'{arm}_{s[2]}', first_request_id=f['id'], first_request_attempt=f['attempt'],
                         first_request_latency_ms=f['latency_ms'], arm_median_latency_ms=float(np.median([r['latency_ms'] for r in recs.values()])),
                         first_request_is_global_cold_after_load=cold_flag(f), first_request_in_primary_units=f['id'] in set(ids),
                         source=str(rpath), label=LABEL))
    # (ii) exclude every question on which either arm made its first formal request
    excl = {firsts['fixed']['id'], firsts['policy']['id']}
    keep = [i for i in ids if i not in excl]
    d2 = np.array([fx[i]['latency_ms'] - po[i]['latency_ms'] for i in keep]); n2 = len(keep)
    idx2 = np.random.default_rng(0).integers(0, n2, size=(2000, n2))
    m2, c2 = float(d2.mean()), ci(d2[idx2].mean(axis=1))
    # (iii) 5% trimmed mean (per tail) of paired differences, all units, same paper indices
    m3 = float(trim_mean(d, TRIM)); c3 = ci(np.array([trim_mean(d[row], TRIM) for row in idx]))
    out5.append(dict(pair=s[0], task=s[1], reference=s[2], population=pop, N=len(ids),
                     fixed_first_id=firsts['fixed']['id'], fixed_first_ms=firsts['fixed']['latency_ms'], fixed_first_global_cold=cold_flag(firsts['fixed']),
                     policy_first_id=firsts['policy']['id'], policy_first_ms=firsts['policy']['latency_ms'], policy_first_global_cold=cold_flag(firsts['policy']),
                     i_mean_ms=m1, i_CI_low=c1[0], i_CI_high=c1[1], i_reproduces_paper=repro, paper_value=f'{pp[0]} [{pp[1]}, {pp[2]}]',
                     ii_excluded_ids=';'.join(sorted(excl & set(ids))), ii_N=n2, ii_mean_ms=m2, ii_CI_low=c2[0], ii_CI_high=c2[1],
                     iii_trim_per_tail=TRIM, iii_trimmed_mean_ms=m3, iii_CI_low=c3[0], iii_CI_high=c3[1],
                     bootstrap='seed 0, 2000 resamples; (i),(iii) paper indices ' + str(ipath) + '; (ii) default_rng(0).integers(0,N_ii,(2000,N_ii)) over remaining units',
                     source=str(rpath), label=LABEL))
    print(s, f'(i) {m1:.1f} [{c1[0]:.1f},{c1[1]:.1f}] repro={repro} | (ii) N={n2} {m2:.1f} [{c2[0]:.1f},{c2[1]:.1f}] | (iii) {m3:.1f} [{c3[0]:.1f},{c3[1]:.1f}]',
          '| first fixed', firsts['fixed']['id'], f"{firsts['fixed']['latency_ms']:.1f}", '| first policy', firsts['policy']['id'], f"{firsts['policy']['latency_ms']:.1f}")
csvout(P / 'results/item5_cold_request_sensitivity.csv', out5)
csvout(P / 'results/item5_arm_first_requests.csv', arms)

# Item 6: MMLU-Pro panel accuracy, paired bootstrap of policy-minus-reference correctness (same seed-0 indices)
pq = jl(MP / 'records/paired_per_question.jsonl')
ids = np.load(MP / 'protocol/bootstrap_indices.npz')['ids'].tolist(); idx = load_idx(MP / 'protocol/bootstrap_indices.npz', ids)
out6 = []
for label in ['Text', 'C2C']:
    by = {r['id']: r for r in pq if r['reference'] == label}; assert len(by) == 128
    diff = np.array([by[i]['policy_correct'] - by[i]['fixed_correct'] for i in ids], float)
    lo, hi = ci(diff[idx].mean(axis=1))
    out6.append(dict(reference=label, N=128, policy_correct=int(sum(by[i]['policy_correct'] for i in ids)), fixed_correct=int(sum(by[i]['fixed_correct'] for i in ids)),
                     delta_acc_pp=100 * diff.mean(), CI95_low_pp=100 * lo, CI95_high_pp=100 * hi, benefit=int((diff > 0).sum()), harm=int((diff < 0).sum()),
                     seed=0, resamples=2000, unit='paired panel question', source=str(MP / 'records/paired_per_question.jsonl'), label=LABEL))
    print('item6', out6[-1])
csvout(P / 'results/item6_mmlu_pro_panel_accuracy.csv', out6)
