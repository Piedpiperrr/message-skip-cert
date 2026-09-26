"""E15-2: busy GPU time saved.

Busy GPU time of one request = sum over both GPUs of the wall time of the GPU-side stages: probe prefill (+ last-position
projection), helper generation / helper prefill, C2C fuser projection, receiver prefill and decoding; tokenization,
parsing, routing and transfers excluded.

Qualification (per replay source x policy): every record of the policy arm and of its fixed arm must carry, per request,
separate timers for every stage that request runs:
  probe  -> probe['GPU_prefill_projection_event_ms'] (CUDA-event interval, read after torch.cuda.synchronize)
  helper -> trace entries role 'helper' (one per helper forward: prefill and each decode step)
  fuser  -> trace entries role 'fuser_0'..'fuser_35' (C2C only)
  receiver -> trace entries role 'receiver' (one per receiver forward: prefill and each decode step)
Trace entries are CUDA-event intervals recorded by forward pre/post hooks on the executing device and read after
torch.cuda.synchronize on both devices (P2_FROZEN_POLICY_E2E_VALIDATION.../src/native_adapter.py, execute.py). The nested
'receiver_backbone' entries (inside 'receiver') are not added, as in the replay's own GPU_forward_event_sum_ms.
Source preference: (a) original configuration, (b) second configuration (E3 repeats, E7).
Bootstrap: the original replay's stored indices (= numpy default_rng(0).integers(0, 128, (2000, 128)), panel-id order),
percentile 95% interval via np.quantile, as in the replay's own analysis (src/analyze.py).
"""
from e15_common import *

STAGES = {'R': ['receiver'], 'T': ['helper', 'receiver'], 'C': ['helper', 'fuser', 'receiver']}


def roles(rec):
    out = {}
    for t in rec.get('trace') or []:
        k = 'fuser' if t['role'].startswith('fuser_') else t['role']
        out[k] = out.get(k, 0) + 1
    return out


def qualifies(rec, policy):
    """-> '' if every stage of this request is separately timed, else the reason."""
    if not rec.get('trace'):
        return 'no per-stage timer (one action wall interval' + (', GPU_forward_event_sum_ms is one sum per request)' if rec.get('GPU_forward_event_sum_ms') is not None else ')')
    r = roles(rec)
    miss = [st for st in STAGES[rec['selected']] if not r.get(st)]
    if rec['selected'] == 'C' and r.get('fuser') != 36:
        miss.append(f"fuser count {r.get('fuser')}")
    if policy and 'GPU_prefill_projection_event_ms' not in (rec.get('probe') or {}):
        miss.append('probe prefill timer')
    return ('missing ' + ','.join(miss)) if miss else ''


def busy(rec, policy):
    b = sum(t['CUDA_event_ms'] for t in rec['trace'] if t['role'] in ('helper', 'receiver') or t['role'].startswith('fuser_'))
    return b + (rec['probe']['GPU_prefill_projection_event_ms'] if policy else 0.0)


# ---------------------------------------------------------------- qualification table, all sources x 8 policies
def sources(s):
    pair, task, ref = s
    ds, b = TASKDS[task], CODE[ref]
    ids, fx, po, f = original_replay(s)
    yield '(a) original configuration', fx, po, f
    for k, F in REP.items():
        if pair == 'large' and task != 'MMLU-Pro':
            f = F / 'large/records/e2e_requests.jsonl'; reqs = jl(f)
            fx = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'reference')}
            po = {r['id']: r for r in reqs if (r['dataset'], r['reference'], r['mode']) == (ds, b, 'policy')}
        elif pair == 'medium':
            f = F / 'medium/records/e2e_requests.jsonl'; reqs = jl(f)
            fx = {r['id']: r for r in reqs if (r['task'], r['arm']) == (ds, 'fixed_C')}
            po = {r['id']: r for r in reqs if (r['task'], r['arm']) == (ds, 'policy_C')}
        else:
            f = F / 'mmlu/records/four_arm_requests.jsonl'; reqs = jl(f)
            fx = {r['id']: r for r in reqs if r['arm'] == f'fixed_{b}'}
            po = {r['id']: r for r in reqs if r['arm'] == f'policy_{b}'}
        yield f'(b) second configuration E3 {k}', fx, po, f
    sub = {'large': 'large', 'medium': 'medium'}[pair] if task != 'MMLU-Pro' else 'mmlu'
    f = E7 / f'{sub}/records_e7/e7_requests.jsonl'
    reqs = [r for r in jl(f) if r['setting'] == f'{pair}/{ds}/{b}']
    fx = {r['id']: r for r in reqs if r['arm'] == 'fixed'}
    po = {r['id']: r for r in reqs if r['arm'] == 'original'}
    yield '(b) second configuration E7 (ORIGINAL arm vs FIXED)', fx, po, f


qual = []
for s in DEPLOY8:
    for name, fx, po, f in sources(s):
        assert len(fx) == len(po) == 128 and set(fx) == set(po), (name, sname(s))
        why = sorted(({qualifies(r, False) for r in fx.values()} | {qualifies(r, True) for r in po.values()}) - {''})
        qual.append(dict(setting=sname(s), source=name, n_fixed=len(fx), n_policy=len(po), qualifies=not why,
                         reason='; '.join(why) if why else 'every stage separately timed per request', path=str(f)))
        print(qual[-1]['setting'], qual[-1]['source'], qual[-1]['qualifies'], qual[-1]['reason'])
csvout('e15_2_qualification.csv', qual)

bysrc = {}
for r in qual:
    bysrc.setdefault(r['source'], []).append(r['qualifies'])
all8 = [k for k, v in bysrc.items() if len(v) == 8 and all(v)]
e3_all8 = all(all(bysrc[k]) for k in bysrc if k.startswith('(b) second configuration E3'))
avail = sorted({r['setting'] for r in qual if r['qualifies']}, key=lambda x: [sname(s) for s in DEPLOY8].index(x))
print('sources qualifying for all eight:', all8, '| E3 repeats jointly:', e3_all8, '| policies with any qualifying source:', avail)

# ---------------------------------------------------------------- busy-time savings where available
# (highest-preference qualifying source per policy; in this run that is the original configuration for all available ones)
rows, checks = [], []
for s in DEPLOY8:
    if sname(s) not in avail:
        rows.append(dict(setting=sname(s), source='none qualifies', busy_available=False, label=LABEL))
        continue
    src = next(r for r in qual if r['setting'] == sname(s) and r['qualifies'])
    assert src['source'].startswith('(a)')
    ids, fx, po, f = original_replay(s)
    ds = TASKDS[s[1]]
    z = np.load(FP / f'summary/{ds}_bootstrap_indices.npz'); READ.append(str(FP / f'summary/{ds}_bootstrap_indices.npz'))
    assert z['ids'].tolist() == ids and int(z['seed']) == 0
    idx = z['indices']
    assert (idx == np.random.default_rng(0).integers(0, 128, size=(2000, 128))).all()
    bf = np.array([busy(fx[i], False) for i in ids]); bp = np.array([busy(po[i], True) for i in ids])
    lf = np.array([fx[i]['latency_ms'] for i in ids]); lp = np.array([po[i]['latency_ms'] for i in ids])
    bs, ls = bf - bp, lf - lp
    D = bs - ls
    ci = lambda v: [float(x) for x in np.quantile(v[idx].mean(axis=1), [.025, .975])]
    # consistency with the replay's own per-request GPU_forward_event_sum_ms (same hooks; adds only the probe projection)
    dfx = max(abs(busy(fx[i], False) - fx[i]['GPU_forward_event_sum_ms']) for i in ids)
    extra = [busy(po[i], True) - po[i]['GPU_forward_event_sum_ms'] for i in ids]
    checks.append(dict(setting=sname(s), max_abs_busy_minus_GPU_forward_event_sum_fixed_ms=dfx,
                       policy_busy_minus_GPU_forward_event_sum_min_ms=min(extra), policy_busy_minus_GPU_forward_event_sum_max_ms=max(extra),
                       note='policy difference = probe prefill+projection event minus the probe backbone trace entry'))
    lci = ci(ls)
    stg = lambda recs, pol, role: float(np.mean([sum(t['CUDA_event_ms'] for t in r['trace'] if (t['role'].startswith('fuser_') if role == 'fuser' else t['role'] == role)) for r in recs]))
    row = dict(setting=sname(s), source=src['source'], path=str(f), N=len(ids), n_omitted=int(sum(po[i]['selected'] == 'R' for i in ids)),
               busy_available=True,
               mean_busy_fixed_ms=float(bf.mean()), mean_busy_policy_ms=float(bp.mean()),
               busy_saving_ms=float(bs.mean()), busy_saving_CI_low=ci(bs)[0], busy_saving_CI_high=ci(bs)[1],
               mean_latency_fixed_ms=float(lf.mean()), mean_latency_policy_ms=float(lp.mean()),
               latency_saving_ms=float(ls.mean()), latency_saving_CI_low=lci[0], latency_saving_CI_high=lci[1],
               D_ms=float(D.mean()), D_CI_low=ci(D)[0], D_CI_high=ci(D)[1],
               ratio_busy_over_latency=float(bs.mean() / ls.mean()) if lci[0] > 0 else 'not reported (latency CI not above 0)',
               fixed_helper_ms=stg(fx.values(), False, 'helper'), fixed_fuser_ms=stg(fx.values(), False, 'fuser'),
               fixed_receiver_ms=stg(fx.values(), False, 'receiver'),
               policy_probe_ms=float(np.mean([po[i]['probe']['GPU_prefill_projection_event_ms'] for i in ids])),
               policy_helper_ms=stg(po.values(), True, 'helper'), policy_fuser_ms=stg(po.values(), True, 'fuser'),
               policy_receiver_ms=stg(po.values(), True, 'receiver'), label=LABEL)
    rows.append(row)
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items() if k not in ('label', 'path')})
for c in checks: print(c)

# ---------------------------------------------------------------- component accounting records (descriptive only)
comp = []
for s in DEPLOY8:
    comp.append(dict(setting=sname(s), component_recomposed_latency_saving_ms=None,
                     component_busy_time='not computable: component request records store one total latency per request '
                                         '(historical R/Text/C2C dev requests); only the probe records hold a GPU-event interval',
                     label=LABEL))
per1 = {r['setting']: r for r in csvread(RES / 'e15_1_per_setting.csv')}
for c in comp:
    c['component_recomposed_latency_saving_ms'] = float(per1[c['setting']]['component_recomposed_saving_ms'])

X = len(avail)
summ = dict(sources_qualifying_for_all_eight=';'.join(all8) if all8 else 'none', paper_rule_branch='(1)' if all8 else '(2)',
            X_policies_with_busy_time=X, policies_with_busy_time=';'.join(avail),
            sec7_phrase=(f'busy GPU time is available for {X} of eight policies (Appendix)' if not all8 else 'range clause (rule 1)'),
            label=LABEL)
print(summ)
csvout('e15_2_busy_savings.csv', rows)
csvout('e15_2_checks.csv', checks)
csvout('e15_2_component_descriptive.csv', comp)
csvout('e15_2_summary.csv', [summ])
csvout('e15_2_files_read.csv', [dict(path=p) for p in dict.fromkeys(READ)])
