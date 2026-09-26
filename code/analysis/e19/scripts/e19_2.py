"""E19-2: INVALID among the changes on omitted questions, per policy x split, plus a pooled out-of-sample row per policy.
Convention: two INVALIDs = agreement; exactly one INVALID = change. Sources as PREREG_E19.md (E19-2)."""
from e19_common import *
import collections

T0 = utc()
print('E19-2 start', T0)


def nz(x): return INV if x in (None, INV) else x


def classify(pairs):
    """pairs: list of (o_R, o_ref) on omitted questions -> counts."""
    n = len(pairs)
    both = sum(a != b and a != INV and b != INV for a, b in pairs)
    onlyR = sum(a == INV and b != INV for a, b in pairs)
    onlyB = sum(b == INV and a != INV for a, b in pairs)
    bothinv = sum(a == INV and b == INV for a, b in pairs)
    k = both + onlyR + onlyB
    assert k == sum(a != b for a, b in pairs)
    return dict(n_omitted=n, k=k, both_parse_differ=both, only_R_INVALID=onlyR, only_ref_INVALID=onlyB,
                exactly_one_INVALID=onlyR + onlyB, share_exactly_one_INVALID=((onlyR + onlyB) / k if k else float('nan')),
                both_INVALID_agreement=bothinv)


ROWS, CHK = [], []
SPL = collections.defaultdict(list)   # policy -> list of (split, pairs)
# dev
for key, s, q in POL12:
    D = dev(key)
    pairs = [(nz(a), nz(b)) for a, b, m in zip(D['oR'], D['ob'], D['m']) if m]
    ROWS.append(dict(policy=key, split='dev', **classify(pairs), source='E17 loader (e17_common.load) -> E13/E11 frozen V2 labels'))
# held-out 744 OBQA (E9b)
HK = {'large/OBQA/Text': 'large_obqa_T_q80', 'large/OBQA/C2C': 'large_obqa_C_q80', 'medium/OBQA/C2C q=.55': 'medium_obqa_C_q55',
      'medium/OBQA/C2C q=.50': 'medium_obqa_C_q50', 'large/OBQA/Text+fact': 'large_obqa_TF_q75'}
HO = collections.defaultdict(list)
for r in jl(E9B / 'analysis/SEALED_ROUTES.jsonl'): HO[r['policy']].append(r)
e9b = {r['policy']: r for r in read(E9B / 'analysis/E9B_RESULTS.json')['policies']}
for key, pk in HK.items():
    rr = HO[pk]
    tau = dev(key)['tau']
    assert len(rr) == 744 and all(r['threshold'] == tau for r in rr), key
    pairs = [(nz(r['R_answer']), nz(r['reference_answer'])) for r in rr if r['omitted']]
    c = classify(pairs)
    CHK.append(dict(check=f'held-out {key}: n/k == E9B_RESULTS.json', expected=[e9b[pk]['omitted'], e9b[pk]['changed']],
                    observed=[c['n_omitted'], c['k']]))
    ROWS.append(dict(policy=key, split='held-out 744 OBQA (E9b)', **c, source=str(E9B / 'analysis/SEALED_ROUTES.jsonl')))
    SPL[key].append(pairs)
# sealed ARC
paired = collections.defaultdict(list)
for r in jl(SA / 'records/paired_sealed_2344.jsonl'): paired[r['reference']].append(r)
prim = {r['reference']: r for r in csvread(SA / 'summary/primary_sealed.csv')}
for key, b in [('large/ARC/Text', 'T'), ('large/ARC/C2C', 'C')]:
    rr = paired[b]
    assert len(rr) == 1172
    pairs = [(nz(r['policy_answer']), nz(r['reference_answer'])) for r in rr if r['routed']]
    c = classify(pairs)
    CHK.append(dict(check=f'sealed {key}: n/k == primary_sealed.csv', expected=[int(prim[b]['routed']), int(prim[b]['changed_among_routed'])],
                    observed=[c['n_omitted'], c['k']]))
    ROWS.append(dict(policy=key, split='sealed ARC 1,172', **c, source=str(SA / 'records/paired_sealed_2344.jsonl')))
    SPL[key].append(pairs)
# E16 out-of-sample
OOSP = read(E16 / 'results/analysis_oos/OOS_PRE_GOLD.json')['results']
for key, f, pk, sp in [('Llama-3.1-8B/OBQA/Text', 'routes_llama_obqa.jsonl', 'Llama-3.1-8B OBQA/Text (q=.60) on 744 held-out OBQA', 'held-out 744 OBQA (E16-1)'),
                       ('Llama-3.1-8B/ARC/Text', 'routes_llama_arc.jsonl', 'Llama-3.1-8B ARC/Text (q=.70) on 1,172 ARC test', 'ARC test 1,172 (E16-1)'),
                       ('medium/ARC/C2C', 'routes_medium_arc_C.jsonl', 'medium ARC/C2C (q=.60) on 1,172 ARC test', 'ARC test 1,172 (E16-2)')]:
    rr = jl(E16 / 'results/analysis_oos' / f)
    pairs = [(nz(r['o_R']), nz(r['o_ref'])) for r in rr if r['omitted']]
    c = classify(pairs)
    CHK.append(dict(check=f'{sp} {key}: n/k == OOS_PRE_GOLD.json', expected=[OOSP[pk]['omitted_n'], OOSP[pk]['changed_k']],
                    observed=[c['n_omitted'], c['k']]))
    CHK.append(dict(check=f'{sp} {key}: INVALID R/ref among omitted == OOS_PRE_GOLD.json',
                    expected=[OOSP[pk]['INVALID_R_omitted'], OOSP[pk]['INVALID_ref_omitted']],
                    observed=[sum(a == INV for a, _ in pairs), sum(b == INV for _, b in pairs)]))
    ROWS.append(dict(policy=key, split=sp, **c, source=str(E16 / 'results/analysis_oos' / f)))
    SPL[key].append(pairs)
# pooled out-of-sample
for key, s, q in POL12:
    if SPL[key]:
        pairs = [p for ps in SPL[key] for p in ps]
        ROWS.append(dict(policy=key, split='pooled out-of-sample', **classify(pairs),
                         source='+'.join(r['split'] for r in ROWS if r['policy'] == key and r['split'] not in ('dev', 'pooled out-of-sample'))))
    else:
        ROWS.append(dict(policy=key, split='pooled out-of-sample', n_omitted='none (no out-of-sample test)', source=''))
for r in ROWS: r['label'] = LABEL
for c in CHK:
    c['status'] = 'PASS' if c['expected'] == c['observed'] else 'FAIL'
    c['expected'], c['observed'] = json.dumps(c['expected']), json.dumps(c['observed'])
    print(c)
assert all(c['status'] == 'PASS' for c in CHK)

# writing rule: the 11 deployed policies (q=.50 row excluded), dev or pooled OOS share of exactly-one-INVALID >= 50%
DEP11 = [k for k, _, _ in POL12 if k != 'medium/OBQA/C2C q=.50']
trig = [(r['policy'], r['split'], r['share_exactly_one_INVALID']) for r in ROWS
        if r['policy'] in DEP11 and r['split'] in ('dev', 'pooled out-of-sample') and isinstance(r.get('k'), int)
        and r['k'] > 0 and r['share_exactly_one_INVALID'] >= .5]
shares = [r['share_exactly_one_INVALID'] for r in ROWS if r['policy'] in DEP11 and r['split'] in ('dev', 'pooled out-of-sample')
          and isinstance(r.get('k'), int) and r['k'] > 0]
rule = dict(triggered=bool(trig), triggers=';'.join(f'{p} [{s}] {x:.3f}' for p, s, x in trig) or 'none',
            range_min=min(shares), range_max=max(shares), label=LABEL)
print(rule)
for r in ROWS:
    if isinstance(r.get('k'), int):
        print(f"{r['policy']:24s} {r['split']:28s} n={r['n_omitted']} k={r['k']} both={r['both_parse_differ']} onlyR={r['only_R_INVALID']} onlyRef={r['only_ref_INVALID']} share1={r['share_exactly_one_INVALID']:.3f}")
csvout('E19_2_invalid_changes.csv', ROWS)
csvout('E19_2_checks.csv', CHK)
csvout('E19_2_writing_rule.csv', [rule])
json.dump(dict(start_utc=T0, end_utc=utc(), files_read=READ), open(STAGE / 'logs/e19_2_run.json', 'w'), indent=1)
print('E19-2 done', utc())
