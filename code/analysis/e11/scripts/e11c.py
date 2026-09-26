"""E11-c: Rule D, a DEPLOYABLE INVALID-routing rule. Omission set at tau = {u <= tau and o_R parses};
the controlled quantity rho_D(tau) = P(o_R != o_b | omitted) is unchanged. Frozen thresholds, alpha, delta."""
from e11_common import *
import pyarrow as pa, pyarrow.parquet as pq
pa.set_cpu_count(1); pa.set_io_thread_count(1)

REVIEW = ROOT / 'P2_MMLU_PRO_BREADTH_PROTOCOL_AND_COST_REVIEW_20260915T224801Z'
_gold = {}
for nm in ['full_train', 'full_development']:
    for r in jl(V2 / f'labels/{nm}_P2_SCORING_V2.jsonl'):
        _gold[r['dataset'], r['id']] = r['gold']          # gold is a property of the question, not the pair
for r in pq.read_table(REVIEW / 'dataset/test-00000-of-00001.parquet', columns=['question_id', 'answer'],
                       use_threads=False).to_pylist():
    _gold['mmlu_pro', 'test:' + str(r['question_id'])] = r['answer']
GOLD_SRC = f"{V2}/labels/full_{{train,development}}_P2_SCORING_V2.jsonl (gold) ; {REVIEW}/dataset/test-00000-of-00001.parquet (MMLU-Pro answer)"


def rule_d_mask(u, q, t, parses):
    if q == 0: return np.zeros(len(u), bool)
    m = np.ones(len(u), bool) if q == 1 else (u <= tv(t))
    return m & parses


rows, grid = [], []
for s in ALL26:
    D = load(s)
    ds = D['benchmark']
    P_ = {}
    for sp in ['cal', 'dev']:
        oR = np.array(D[sp]['oR'], object); ob = np.array(D[sp]['ob'], object)
        P_[sp] = dict(u=D[sp]['u'], oR=oR, ob=ob, parses=oR != INV,
                      dis=np.array([a != b for a, b in zip(oR, ob)], bool),
                      gold=np.array([_gold[ds, i] for i in D[sp]['ids']], object))
    c = P_['cal']
    led = []
    for q, t in zip(GRID, D['cuts']):
        m = rule_d_mask(c['u'], q, t, c['parses'])
        n = int(m.sum()); k = int(c['dis'][m].sum())
        led.append(dict(q=q, threshold=t, n=n, k=k, p=pval(k, n), CP=cp999(k, n), accepted=pval(k, n) <= .001))
        grid.append(dict(setting=sname(s), q=q, threshold=t, N_cal=len(c['u']),
                         n_ruleD=n, k_ruleD=k, p=f'{pval(k, n):.6g}', CP999=f'{cp999(k, n):.6g}',
                         accepted=led[-1]['accepted'], label=LABEL))
    qD, accD = largest_accepted(led)
    r0 = next((r for r in led if abs(r['q'] - qD) < 1e-9), None) if qD > 0 else None

    d = P_['dev']
    mdev = rule_d_mask(d['u'], qD, D['cuts'][GRID.index(qD)] if qD > 0 else None, d['parses']) if qD > 0 \
        else np.zeros(len(d['u']), bool)
    pol = np.where(mdev, d['oR'], d['ob'])
    npars = int(d['parses'].sum())
    q0 = D['q0']
    verdict = ('new certification (Rule D certifies where ProbeMax alone does not)' if qD > 0 and q0 == 0 else
               'lost certification under Rule D' if qD == 0 and q0 > 0 else
               'unchanged' if qD == q0 else f'still certified, q changes {q0} -> {qD}')
    rows.append(dict(setting=sname(s), original_q=q0, ruleD_q=qD if qD > 0 else 'no candidate accepted',
                     ruleD_all_accepted_q=';'.join(f'{x:g}' for x in accD) or 'none',
                     cal_N=len(c['u']), cal_receiver_parses=int(c['parses'].sum()),
                     cal_n_at_ruleD_q=r0['n'] if r0 else '', cal_k_at_ruleD_q=r0['k'] if r0 else '',
                     cal_p_at_ruleD_q=f"{r0['p']:.6g}" if r0 else '', cal_CP999_at_ruleD_q=f"{r0['CP']:.6g}" if r0 else '',
                     dev_N=len(d['u']), dev_receiver_parses=npars,
                     dev_omitted=int(mdev.sum()),
                     dev_coverage_pct_of_all=f'{100 * mdev.mean():.2f}',
                     dev_coverage_pct_of_parseable=f'{100 * mdev.sum() / npars:.2f}' if npars else '',
                     dev_changed_over_omitted=f'{int(d["dis"][mdev].sum())}/{int(mdev.sum())}',
                     dev_conditional_change_rate=f'{d["dis"][mdev].mean():.5f}' if mdev.sum() else '',
                     dev_policy_equals_reference=f'{100 * (pol == d["ob"]).mean():.2f}',
                     dev_accuracy_policy_vs_gold=f'{100 * (pol == d["gold"]).mean():.2f}',
                     dev_accuracy_reference_vs_gold=f'{100 * (d["ob"] == d["gold"]).mean():.2f}',
                     dev_accuracy_receiver_only_vs_gold=f'{100 * (d["oR"] == d["gold"]).mean():.2f}',
                     dev_correct_policy=int((pol == d['gold']).sum()), dev_correct_reference=int((d['ob'] == d['gold']).sum()),
                     verdict=verdict, gold_source=GOLD_SRC, label=LABEL))
    print(f"{sname(s):26s} q0={q0:<5} qD={qD!s:<5} cov {rows[-1]['dev_coverage_pct_of_all']}%/"
          f"{rows[-1]['dev_coverage_pct_of_parseable']}% chg {rows[-1]['dev_changed_over_omitted']:<10} "
          f"accP/B {rows[-1]['dev_accuracy_policy_vs_gold']}/{rows[-1]['dev_accuracy_reference_vs_gold']}  {verdict}")

csvout(RES / 'E11c_ruleD.csv', rows)
csvout(RES / 'E11c_ruleD_grid.csv', grid)
new = [r['setting'] for r in rows if r['verdict'].startswith('new certification')]
lost = [r['setting'] for r in rows if r['verdict'].startswith('lost')]
chg = [r['setting'] for r in rows if r['verdict'].startswith('still certified')]
print(f'\nNEW under Rule D  ({len(new)}): {new}')
print(f'LOST under Rule D ({len(lost)}): {lost}')
print(f'q changed        ({len(chg)}): {chg}')
csvout(RES / 'E11c_verdicts.csv', [dict(category=k, n=len(v), settings=';'.join(v) or 'none', label=LABEL) for k, v in
                                   [('new certification under Rule D', new), ('lost certification under Rule D', lost),
                                    ('certified under both, q changed', chg),
                                    ('unchanged', [r['setting'] for r in rows if r['verdict'] == 'unchanged'])]])
