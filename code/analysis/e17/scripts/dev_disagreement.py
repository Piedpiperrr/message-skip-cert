"""Dev disagreement count per setting (o_R != o_b on the dev split, paper convention) for the 28 E17-5 settings.
E17_5b_binormal.csv has no dev-disagreement column; this is the count from the same cached dev records (cache/data28.pkl).
Cross-checked against E17_3_splits.csv (10 ARC settings) and the X3 dev_table.csv (2 Llama settings)."""
from e17_common import *

D = loadcache()['D']
arc = {(r['setting']): r for r in csvread(RES / 'E17_3_splits.csv') if r['split'] == 'dev'}
x3 = {r['setting']: r for r in csvread(X3 / 'results/analysis/dev_table.csv')}
rows, bad = [], 0
for s in ALL28:
    d = D[s]['dev']['d']
    r = dict(setting=sname(s), dev_N=len(d), dev_disagreements=int(d.sum()), dev_disagreement_rate=float(d.mean()),
             source='cache/data28.pkl dev split (o_R != o_b, V2, two INVALID = agreement)')
    if sname(s) in arc:
        a = arc[sname(s)]; ok = (int(a['N']), int(a['disagreements'])) == (r['dev_N'], r['dev_disagreements'])
        r['check'] = f"E17_3_splits.csv {a['disagreements']}/{a['N']} {'match' if ok else 'MISMATCH'}"; bad += not ok
    if s[0] == 'X3-Llama8B':
        a = x3[f"X3 {C.BENCH[s[1]]}/Text"]; ok = (int(a['N_dev']), int(a['dev_disagreements'])) == (r['dev_N'], r['dev_disagreements'])
        r['check'] = f"X3 dev_table.csv {a['dev_disagreements']}/{a['N_dev']} {'match' if ok else 'MISMATCH'}"; bad += not ok
    rows.append(r)
csvout('E17_5b_dev_disagreement.csv', rows)
print('mismatches:', bad)
