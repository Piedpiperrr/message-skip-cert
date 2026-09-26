"""E9c analysis (login node, CPU). AUROC, certification of s_G, and the H verdict.

Reads only machine answers o_R / o_T / o_C / o_Tf and the frozen probe scores. Gold is never
projected: load_actions() whitelists the three machine-answer fields and drops everything else.
"""
import sys, os, json, math, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e9_common import *
import numpy as np
from scipy.stats import binom, beta

ap = argparse.ArgumentParser(); ap.add_argument('--out', default=str(STAGE / 'analysis')); A = ap.parse_args()
OUT = Path(A.out); OUT.mkdir(parents=True, exist_ok=True)
GOLD_FIELDS_READ = []          # stays empty; asserted at the end

def tv(t):
    return float('inf') if t == 'Infinity' else float(t)

def thresholds_from_fit(vals):
    """Frozen rule: integer rank ceil(j*N/20); FP32 ties retained; q=1 is Infinity."""
    vals = sorted(vals); n = len(vals)
    return [vals[(j * n + 19) // 20 - 1] if j < 20 else 'Infinity' for j in range(1, 21)]

def auroc(score, label):
    """Mann-Whitney AUROC with midrank tie handling. Higher score should predict label==1."""
    s = np.asarray(score, float); y = np.asarray(label, int)
    n1 = int(y.sum()); n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return None
    order = np.argsort(s, kind='mergesort'); ranks = np.empty(len(s), float)
    sr = s[order]; i = 0; r = np.empty(len(s), float)
    while i < len(sr):
        j = i
        while j + 1 < len(sr) and sr[j + 1] == sr[i]:
            j += 1
        r[i:j + 1] = (i + j) / 2.0 + 1.0
        i = j + 1
    ranks[order] = r
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))

def tests(u, d, ths, N=None):
    """The frozen 20-candidate calibration family, unchanged except for the score vector u."""
    u = np.asarray(u, float); d = np.asarray(d, int); rr = []
    for q, t in zip(Q, ths):
        mask = u <= tv(t); n = int(mask.sum()); k = int(d[mask].sum())
        pv = float(binom.cdf(k, n, ALPHA)) if n else 1.0
        cp = float(beta.ppf(CP_LEVEL, k + 1, n - k)) if n and k < n else 1.0
        rr.append({'q': q, 'threshold': t if t == 'Infinity' else float(t), 'N': len(u), 'n_R': n, 'changed': k,
                   'conditional_risk': (k / n if n else None), 'p_value': pv, 'CP_upper_0_999': cp,
                   'accepted': pv <= P_CUTOFF, 'coverage': n / len(u) if len(u) else 0.0})
    acc = [r for r in rr if r['accepted']]
    return rr, (acc[-1] if acc else None)

# ---------------- loaders (machine answers only) ----------------
def load_probes(pair, ds):
    out = {s: {} for s in ['fit', 'cal', 'dev']}
    if ds == 'mmlu_pro':
        if pair == 'large':
            for sh in ['1', '2']:
                for s in ['fit', 'cal', 'dev']:
                    p = MM / 'shards' / sh / 'probes' / f'{s}.jsonl'
                    if p.exists():
                        for r in jl(p): out[s][r['id']] = r
        else:
            for lane in sorted(E8.glob(f'shards/{pair}/lane_*')):
                for s in ['fit', 'cal', 'dev']:
                    p = lane / 'probes' / f'{s}.jsonl'
                    if p.exists():
                        for r in jl(p): out[s][r['id']] = r
    elif pair == 'medium':
        for s in ['fit', 'cal', 'dev']:
            for r in jl(MED / f'probes/{ds}_{s}.jsonl'): out[s][r['id']] = r
    elif (pair, ds) == ('large', 'obqa'):
        for r in jl(ZERO / 'records/probe_records.jsonl'): out[r['split']][r['id']] = r
    else:
        for s in ['fit', 'cal', 'dev']:
            for r in jl(BOUND / f'records/{pair}_{ds}_{s}_probes.jsonl'): out[s][r['id']] = r
    return out

def load_actions(pair, ds):
    """Machine answers only. 'gold', 'y_*' and every correctness field are dropped here."""
    lab = {}
    if ds == 'mmlu_pro':
        base = [MM / 'shards' / sh for sh in ['1', '2']] if pair == 'large' else sorted(E8.glob(f'shards/{pair}/lane_*'))
        for d in base:
            for s in ['fit', 'cal', 'dev']:
                p = d / 'actions' / f'{s}.jsonl'
                if p.exists():
                    for r in jl(p):
                        lab.setdefault(r['id'], {})['o_' + r['action']] = (r['answer'] if not r['invalid'] else 'INVALID')
    elif pair == 'medium':
        for s in ['fit', 'cal', 'dev']:
            for r in jl(MED / f'actions/{ds}_{s}.jsonl'):
                lab.setdefault(r['id'], {})['o_' + r['action']] = (r['answer'] if not r['invalid'] else 'INVALID')
    else:
        for f in ['full_train', 'full_development']:
            with (V2 / f'labels/{f}_P2_SCORING_V2.jsonl').open() as fh:
                for line in fh:
                    r = json.loads(line)
                    if r['pair'] == pair and r['dataset'] == ds:
                        lab[r['id']] = {k: r[k] for k in ('o_R', 'o_T', 'o_C')}   # gold never projected
                    del r
    return lab

def load_helper(pair, ds, variant='plain'):
    out = {}
    for p in sorted((STAGE / 'records').glob(f'{pair}_{ds}_*_{variant}_rank*.jsonl')):
        for r in jl(p):
            out[r['id']] = r
    return out

def load_textfact():
    """o_Tf on calibration and development from the frozen E6 shards (no gold)."""
    lab = {}
    for p in sorted(E6.glob('main/e6_shard*.jsonl')):
        for r in jl(p):
            lab[r['id']] = 'INVALID' if str(r['invalid']) == 'True' else r['answer']
    return lab

# ---------------- per-setting analysis ----------------
def analyse(pair, ds, ref, probes, actions, helper, rp, frozen_q, label_key=None, tf=None):
    tag = f'{pair}/{ds}/{ref}'
    missing = {s: [i for i in rp[s] if i not in helper] for s in ['fit', 'cal', 'dev']}
    if any(missing.values()):
        return {'setting': tag, 'status': 'INCOMPLETE',
                'missing_helper_prefills': {s: len(v) for s, v in missing.items()}}, None
    def vec(s):
        ids = rp[s]
        uR = np.array([probes[s][i]['ProbeMax'] for i in ids], float)
        dis = np.array([helper[i]['argmax_helper_label'] != probes[s][i]['argmax_probe_label'] for i in ids], int)
        return ids, uR, uR + dis, dis
    fit_ids, fit_uR, fit_sG, fit_dis = vec('fit')
    ths_sG = thresholds_from_fit(list(fit_sG))
    ths_uR = thresholds_from_fit(list(fit_uR))
    out = {'setting': tag, 'status': 'OK', 'pair': pair, 'dataset': ds, 'reference': ref,
           'frozen_q_under_ProbeMax': frozen_q, 'N_fit': len(fit_ids),
           'helper_disagreement_rate_fit': float(fit_dis.mean())}
    per = {}
    for s in ['cal', 'dev']:
        ids, uR, sG, dis = vec(s)
        if tf is not None:
            d = np.array([int(actions[i]['o_R'] != tf[i]) for i in ids], int)
        else:
            d = np.array([int(actions[i]['o_R'] != actions[i]['o_' + ref]) for i in ids], int)
        per[s] = (ids, uR, sG, d, dis)
        out[f'N_{s}'] = len(ids)
        out[f'disagreement_{s}'] = int(d.sum())
        out[f'helper_disagreement_rate_{s}'] = float(dis.mean())
        out[f'AUROC_uR_{s}'] = auroc(uR, d)
        out[f'AUROC_sG_{s}'] = auroc(sG, d)
        a, b = out[f'AUROC_uR_{s}'], out[f'AUROC_sG_{s}']
        out[f'AUROC_diff_{s}'] = None if (a is None or b is None) else b - a
    ids, uR, sG, d, dis = per['cal']
    rr, chosen = tests(sG, d, ths_sG)
    out['q_sG'] = chosen['q'] if chosen else 0.0
    out['threshold_sG'] = chosen['threshold'] if chosen else None
    out['cal_omitted_at_q_sG'] = chosen['n_R'] if chosen else 0
    out['cal_changed_at_q_sG'] = chosen['changed'] if chosen else None
    out['cal_p_at_q_sG'] = chosen['p_value'] if chosen else None
    out['accepted_q_sG'] = [r['q'] for r in rr if r['accepted']]
    ids, uR, sG, d, dis = per['dev']
    if out['q_sG'] > 0:
        m = sG <= tv(out['threshold_sG'])
        out['dev_coverage_at_q_sG'] = float(m.mean())
        out['dev_omitted_at_q_sG'] = int(m.sum())
        out['dev_changed_at_q_sG'] = int(d[m].sum())
    else:
        out['dev_coverage_at_q_sG'] = 0.0; out['dev_omitted_at_q_sG'] = 0; out['dev_changed_at_q_sG'] = None
    out['newly_deployed_under_sG'] = bool(frozen_q == 0 and out['q_sG'] > 0)
    out['lost_deployment_under_sG'] = bool(frozen_q > 0 and out['q_sG'] == 0)
    return out, rr

# ---------------- run ----------------
BOUNDDEP = lambda pair, ds, b: rd(BOUND / f'deployments/{pair}_{ds}_{b}.json')['q']
def frozen_q(pair, ds, ref):
    if ds == 'mmlu_pro':
        if pair == 'large':
            return rd(MM / 'deployments/deployment_configs.json')['deployments'][ref]['q']
        p = E8 / 'analysis/deployments/deployment_configs.json'
        if not p.exists():
            return None
        dep = rd(p)['deployments']
        # E8 names its deployments '<pair>/Text' and '<pair>/C2C'; the large MMLU-Pro stage uses 'T'/'C'.
        # Reporting-only lookup: it sets the displayed frozen q and the deployed/fallback flags, and
        # enters no AUROC, certification, coverage or changed/omitted quantity.
        k = ref if ref in dep else f'{pair}/' + ('Text' if ref == 'T' else 'C2C')
        return dep[k]['q']
    if pair == 'medium':
        return rd(MED / f'deployments/{ds}_{ref}.json')['q']
    return BOUNDDEP(pair, ds, ref)

rows, ledgers, latency = [], {}, []
pops = list(POPULATIONS) + ([p for p in OPTIONAL_POPULATIONS if load_helper(*p)] if True else [])
for pair, ds in pops:
    helper = load_helper(pair, ds)
    if not helper:
        rows.append({'setting': f'{pair}/{ds}/*', 'status': 'NO_HELPER_PREFILLS'}); continue
    probes, actions, rp = load_probes(pair, ds), load_actions(pair, ds), reps(pair, ds)
    for ref in ['T', 'C']:
        r, led = analyse(pair, ds, ref, probes, actions, helper, rp, frozen_q(pair, ds, ref))
        rows.append(r)
        if led: ledgers[f'{pair}/{ds}/{ref}'] = led
    # replay-panel helper-prefill component latency (batch 1, as measured in the main run)
    if ds == 'mmlu_pro':
        pan = rd(MM / 'splits/candidate_e2e128_ids.json') if pair == 'large' else rd(E8 / 'splits/candidate_e2e128_ids.json')
    else:
        pan = rd(BOUND / f'inputs/{ds}_panel_ids.json')['dev']
    got = [helper[i] for i in pan if i in helper]
    if got:
        latency.append({'population': f'{pair}/{ds}', 'panel_n': len(pan), 'measured_n': len(got),
                        **{f'mean_{k}': float(np.mean([g[k] for g in got])) for k in
                           ['tokenization_prefix_ms', 'prepare_transfer_ms', 'prefill_projection_ms',
                            'label_distribution_ms', 'helper_probe_core_ms', 'GPU_prefill_projection_event_ms']},
                        'mean_input_tokens': float(np.mean([g['input_tokens'] for g in got]))})

# Text+fact (large/OBQA): primary = helper prefill WITHOUT the fact; with-fact is descriptive.
tf = load_textfact()
if tf:
    probes, actions, rp = load_probes('large', 'obqa'), load_actions('large', 'obqa'), reps('large', 'obqa')
    for variant in ['plain', 'with_fact']:
        helper = load_helper('large', 'obqa', variant)
        if not helper:
            continue
        rp2 = {s: [i for i in rp[s] if (s == 'fit' or i in tf)] for s in ['fit', 'cal', 'dev']}
        r, led = analyse('large', 'obqa', 'Tf', probes, actions, helper, rp2, 0.75, tf=tf)
        r['setting'] = 'large/obqa/Text+fact' + ('' if variant == 'plain' else ' [with-fact prefill, descriptive]')
        r['helper_prefill_variant'] = variant
        r['descriptive'] = variant == 'with_fact'
        rows.append(r)
        if led: ledgers[r['setting']] = led

# ---------------- hypothesis H ----------------
byp = {}
for r in rows:
    if r.get('status') == 'OK' and r.get('reference') in ('T', 'C') and r.get('AUROC_diff_dev') is not None:
        byp.setdefault(f"{r['pair']}/{r['dataset']}", {})[r['reference']] = r['AUROC_diff_dev']
both = {k: v for k, v in byp.items() if 'T' in v and 'C' in v}
dT = [v['T'] for v in both.values()]; dC = [v['C'] for v in both.values()]
larger = sum(v['T'] > v['C'] for v in both.values())
H = {'populations': sorted(both), 'n_populations': len(both),
     'mean_AUROC_gain_Text': float(np.mean(dT)) if dT else None,
     'mean_AUROC_gain_C2C': float(np.mean(dC)) if dC else None,
     'mean_gain_difference_Text_minus_C2C': float(np.mean(dT) - np.mean(dC)) if dT else None,
     'populations_where_Text_gain_exceeds_C2C': larger,
     'per_population': {k: {'Text': v['T'], 'C2C': v['C'], 'Text_larger': bool(v['T'] > v['C'])} for k, v in sorted(both.items())},
     'prediction': 'mean AUROC gain larger for Text AND larger in at least 5 of 7 populations',
     'criterion_mean_met': bool(dT and np.mean(dT) > np.mean(dC)),
     'criterion_count_met': bool(len(both) == 7 and larger >= 5),
     'analysis_status': 'post hoc'}
H['verdict'] = ('SUPPORTED' if (H['criterion_mean_met'] and H['criterion_count_met'])
                else 'NOT_SUPPORTED' if len(both) == 7 else 'INCOMPLETE')

newly = [r['setting'] for r in rows if r.get('newly_deployed_under_sG')]
save(OUT / 'E9C_RESULTS.json', {'utc': utc(), 'settings': rows, 'hypothesis_H': H,
                                'helper_prefill_panel_latency': latency,
                                'newly_deployed_under_sG': newly,
                                'lost_deployment_under_sG': [r['setting'] for r in rows if r.get('lost_deployment_under_sG')],
                                'q_grid': Q, 'alpha': ALPHA, 'p_cutoff': P_CUTOFF,
                                'family': 'separate family; 20 candidates per setting',
                                'gold_read': False, 'gold_fields_projected': GOLD_FIELDS_READ,
                                'analysis_label': 'post hoc'})
save(OUT / 'E9C_LEDGERS.json', ledgers)
assert not GOLD_FIELDS_READ
for r in rows:
    if r.get('status') == 'OK':
        print('%-46s AUROC u_R %-8s s_G %-8s diff %-9s | q %.2f (was %s) cov %.3f ch/om %s/%s' % (
            r['setting'], round(r['AUROC_uR_dev'], 5) if r['AUROC_uR_dev'] is not None else 'NA',
            round(r['AUROC_sG_dev'], 5) if r['AUROC_sG_dev'] is not None else 'NA',
            round(r['AUROC_diff_dev'], 5) if r['AUROC_diff_dev'] is not None else 'NA',
            r['q_sG'], r['frozen_q_under_ProbeMax'], r['dev_coverage_at_q_sG'],
            r['dev_changed_at_q_sG'], r['dev_omitted_at_q_sG']))
    else:
        print('%-46s %s' % (r['setting'], r.get('status')))
print('\nH:', json.dumps(H, indent=1))
print('newly deployed under s_G:', newly)
