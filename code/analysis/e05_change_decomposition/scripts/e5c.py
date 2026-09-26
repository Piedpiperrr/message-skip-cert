"""E5-c: null control on the 7 development populations. INVALID is a symbol and counts as incorrect."""
from r2_common import *
import numpy as np
import collections

EXP = ROOT / 'P2_R1_EXP_20260919T050555Z'
P210 = ROOT / 'P2_10_20260911T122423Z'
MMLU_PARQUET = ROOT / 'P2_MMLU_PRO_BREADTH_PROTOCOL_AND_COST_REVIEW_20260915T224801Z/dataset/test-00000-of-00001.parquet'
POPS = [('small', 'obqa'), ('small', 'arc'), ('medium', 'obqa'), ('medium', 'arc'),
        ('large', 'obqa'), ('large', 'arc'), ('large', 'mmlu_pro')]
TASKNAME = {'obqa': 'OBQA', 'arc': 'ARC', 'mmlu_pro': 'MMLU-Pro'}
NREP = 1000

# ---------------- gold
GOLD = {}
for ds, fn in [('obqa', 'obqa_dev.jsonl'), ('arc', 'arc_validation.jsonl')]:
    for r in jl(P210 / 'data' / fn):
        GOLD[ds, r['id']] = r['gold_answer']
import pyarrow.parquet as pq
for r in pq.read_table(MMLU_PARQUET, columns=['question_id', 'answer']).to_pylist():
    GOLD['mmlu_pro', 'test:' + str(r['question_id'])] = r['answer']

# ---------------- V1 / V2 null-control answers (parsed back to the original option order)
NULL = collections.defaultdict(dict)
for f in sorted((EXP / 'results/e4').glob('*.jsonl')):
    for r in jl(f):
        NULL[r['pair'], r['dataset'], r['variant']][r['id']] = r.get('parsed_original') or INV

main = load_main()
rows, decomp, per_pop_draws = [], [], []
for pair, ds in POPS:
    D = main[pair, TASKNAME[ds]]['dev']
    ids = D['ids']
    N = len(ids)
    g = [GOLD[ds, i] for i in ids]
    o = dict(R=list(D['ans']['R']), Text=list(D['ans']['T']), C2C=list(D['ans']['C']),
             V1=[NULL[pair, ds, 'V1'].get(i, INV) for i in ids], V2=[NULL[pair, ds, 'V2'].get(i, INV) for i in ids])
    missing = {k: sum(1 for i in ids if i not in NULL[pair, ds, k]) for k in ['V1', 'V2']}
    y = {k: np.array([a == b for a, b in zip(v, g)], bool) for k, v in o.items()}
    orc = lambda ks: int(np.any(np.stack([y[k] for k in ks]), axis=0).sum())
    oR = int(y['R'].sum())
    o_rtc, o_rv = orc(['R', 'Text', 'C2C']), orc(['R', 'V1', 'V2'])

    # (b) change decomposition vs R
    for b in ['Text', 'C2C', 'V1', 'V2']:
        ch = np.array([x != r for x, r in zip(o[b], o['R'])], bool)
        corr = int((ch & ~y['R'] & y[b]).sum()); harm = int((ch & y['R'] & ~y[b]).sum())
        neut = int((ch & ~y['R'] & ~y[b]).sum())
        decomp.append(dict(population=f'{pair}/{TASKNAME[ds]}', N=N, action=b, correct=int(y[b].sum()),
                           changed=int(ch.sum()), corrective=corr, harmful=harm, neutral_both_wrong=neut, label=LABEL))

    # (c) rate-matched null
    Pset = []
    for j in range(N):
        s = {o['V1'][j], o['V2'][j]} - {o['R'][j]}
        Pset.append(sorted(s))
    elig = np.array([j for j in range(N) if Pset[j]], int)
    rng = np.random.default_rng(0)
    m = {b: int(sum(1 for x, r in zip(o[b], o['R']) if x != r)) for b in ['Text', 'C2C']}
    under = {b: m[b] > len(elig) for b in m}
    gains, oracles = [], []
    yR = y['R']
    for _ in range(NREP):
        ystar = {}
        for b in ['Text', 'C2C']:
            take = min(m[b], len(elig))
            pick = rng.choice(elig, size=take, replace=False) if take else np.array([], int)
            yy = yR.copy()
            for j in pick:
                cand = Pset[j]
                a = cand[rng.integers(len(cand))] if len(cand) > 1 else cand[0]
                yy[j] = (a == g[j])
            ystar[b] = yy
        orc_star = int(np.any(np.stack([yR, ystar['Text'], ystar['C2C']]), axis=0).sum())
        oracles.append(orc_star); gains.append(orc_star - oR)
    gains = np.array(gains); oracles = np.array(oracles)
    real_gain = o_rtc - oR
    rho = float(gains.mean() / real_gain) if real_gain else float('nan')
    rows.append(dict(population=f'{pair}/{TASKNAME[ds]}', N=N, R_correct=oR,
                     Text_correct=int(y['Text'].sum()), C2C_correct=int(y['C2C'].sum()),
                     V1_correct=int(y['V1'].sum()), V2_correct=int(y['V2'].sum()),
                     oracle_R_Text_C2C=o_rtc, gain_over_R_questions=real_gain, gain_over_R_pp=f'{100 * real_gain / N:.2f}',
                     oracle_R_V1_V2=o_rv, gain_R_V1_V2_questions=o_rv - oR, gain_R_V1_V2_pp=f'{100 * (o_rv - oR) / N:.2f}',
                     m_Text=m['Text'], m_C2C=m['C2C'], n_eligible_P_nonempty=len(elig),
                     under_matched='Text' if under['Text'] else ('C2C' if under['C2C'] else 'no'),
                     matched_null_oracle_mean=f'{oracles.mean():.2f}',
                     matched_null_gain_mean=f'{gains.mean():.2f}',
                     matched_null_gain_p2_5=f'{np.percentile(gains, 2.5):.1f}',
                     matched_null_gain_p97_5=f'{np.percentile(gains, 97.5):.1f}',
                     matched_null_gain_mean_pp=f'{100 * gains.mean() / N:.2f}',
                     rho=f'{rho:.3f}', missing_V1=missing['V1'], missing_V2=missing['V2'], label=LABEL))
    print(rows[-1]['population'], 'real', o_rtc, f'(+{real_gain})', 'null{R,V1,V2}', o_rv, f'(+{o_rv - oR})',
          'matched', rows[-1]['matched_null_gain_mean'], f"[{rows[-1]['matched_null_gain_p2_5']},{rows[-1]['matched_null_gain_p97_5']}]",
          'rho', rows[-1]['rho'], 'under-matched' if any(under.values()) else '')

rhos = [float(r['rho']) for r in rows]
print('median rho', np.median(rhos), '; rho>=0.8 in', sum(r >= .8 for r in rhos), 'of 7')
csvout(RES / 'e5c_null_control.csv', rows)
csvout(RES / 'e5c_change_decomposition.csv', decomp)
csvout(RES / 'e5c_meta.csv', [dict(median_rho=f'{np.median(rhos):.3f}', n_pops_rho_ge_0_8=sum(r >= .8 for r in rhos),
                                   repetitions=NREP, rng='numpy default_rng(0), one fresh stream per population',
                                   label=LABEL)])
