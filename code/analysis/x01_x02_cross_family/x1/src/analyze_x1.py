"""X1 certification and development analysis, exactly as PROTOCOL_FREEZE_X1.md (CPU). Four settings: OBQA/Text, OBQA/C2C, ARC/Text, ARC/C2C.
R answers = the small pair's saved R outputs (paper labels o_R / valid_R); scores = the small pair's saved ProbeMax records;
reference answers = X1 outputs (Text: receiver outputs; C2C: official-evaluator outputs), parsed with frozen V2 (INVALID a label;
a failed request counts as INVALID). Order: (1) hash outputs; (2) certification + routes without gold, written and hashed; (3) gold.
Rule functions imported unchanged from P2_R1_CPU (thresholds, pval, cp999, deploy, route_mask).
usage: analyze_x1.py '<Text outputs glob>' '<C2C outputs glob>' '<helper outputs glob>'   (globs relative to x1/)"""
import sys
sys.dont_write_bytecode = True
import glob, csv
from x1_common import *
sys.path.insert(0, str(ROOT / 'P2_R1_CPU_20260919T045556Z/src'))
from common_r1 import thresholds, pval, cp999, deploy, GRID
from data_r1 import route_mask
import numpy as np
from sklearn.metrics import roc_auc_score

A = X1 / 'results/analysis'; A.mkdir(parents=True, exist_ok=True)
G = {k: sorted(glob.glob(str(X1 / g))) for k, g in zip(['Text', 'C2C', 'helper'], sys.argv[1:4])}
assert all(G.values()), G
save(A / 'OUTPUT_HASHES.json', dict(utc=utc(), note='computed before any gold read', files={k: {str(pathlib.Path(f).relative_to(X1)): sha(f) for f in v} for k, v in G.items()}))
INV = 'INVALID'
ref = {'Text': {}, 'C2C': {}}
for f in G['Text']:
    for r in jl(f):
        k = (r['dataset'], r['id']); assert k not in ref['Text']; ref['Text'][k] = r['T']['parsed'] if r['runtime_error'] is None else INV
for f in G['C2C']:
    for r in jl(f):
        k = (r['dataset'], r['id']); assert k not in ref['C2C']; ref['C2C'][k] = r['C']['parsed'] if r['runtime_error'] is None else INV
lab = {}
for name in ['full_train', 'full_development']:
    for x in jl(V2L / f'{name}_P2_SCORING_V2.jsonl'):
        if x['pair'] == 'small': lab[(x['dataset'], x['id'])] = x
oR = lambda ds, i: lab[(ds, i)]['o_R'] if lab[(ds, i)]['valid_R'] else INV
score = {}
for ds in DS1:
    for sp in ['fit', 'cal', 'dev']:
        for r in jl(BND / f'records/small_{ds}_{sp}_probes.jsonl'): score[(ds, r['id'])] = r['ProbeMax']
units = {ds: {sp: [r['id'] for r in jl(X1POP / f'{ds}_{sp}.jsonl') if r['representative']] for sp in ['fit', 'cal', 'dev']} for ds in DS1}
missing = {f'{ds}/{b}/{sp}': [i for i in units[ds][sp] if (ds, i) not in ref[b]] for ds in DS1 for b in ['Text', 'C2C'] for sp in ['fit', 'cal', 'dev']}
assert not any(missing.values()), {k: len(v) for k, v in missing.items() if v}


def wcsv(name, rows):
    with open(A / name, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r))); w.writeheader(); w.writerows(rows)


ledger, table, routes = [], [], []
for ds in DS1:
    for b in ['Text', 'C2C']:
        u = {sp: np.array([score[(ds, i)] for i in units[ds][sp]]) for sp in units[ds]}
        d = {sp: np.array([oR(ds, i) != ref[b][(ds, i)] for i in units[ds][sp]]) for sp in units[ds]}
        cuts = thresholds(list(u['fit'])); led = []
        for q, t in zip(GRID, cuts):
            m = route_mask(u['cal'], q, t); n = int(m.sum()); k = int(d['cal'][m].sum())
            led.append(dict(q=q, threshold=t, N=len(u['cal']), n=n, k=k, p=pval(k, n), CP=cp999(k, n), accepted=pval(k, n) <= .001))
        q, acc = deploy(led); t = cuts[GRID.index(q)] if q > 0 else None
        md = route_mask(u['dev'], q, t); n = int(md.sum()); k = int(d['dev'][md].sum())
        for r in led: ledger.append(dict(setting=f'{ds}/{b}', **r))
        auc = roc_auc_score(d['dev'], u['dev']) if 0 < d['dev'].sum() < len(d['dev']) else float('nan')
        table.append(dict(setting=f'X1 {ds}/{b}', N_dev=len(u['dev']), dis_over_N=f"{int(d['dev'].sum())}/{len(u['dev'])}", AUROC=auc, min_UCB=min(r['CP'] for r in led),
                          q=q, threshold=t, accepted_q=';'.join(f'{x:g}' for x in acc), coverage_pct=100 * n / len(u['dev']), changed_over_omitted=f'{k}/{n}' if n else 'N/A'))
        for i, m in zip(units[ds]['dev'], md):
            routes.append(dict(setting=f'{ds}/{b}', id=i, ProbeMax=score[(ds, i)], route='R' if m else b, o_R=oR(ds, i), o_ref=ref[b][(ds, i)]))
wcsv('certification_ledger_80.csv', ledger); wcsv('dev_routes.csv', routes); wcsv('dev_table_pre_gold.csv', table)
save(A / 'ROUTES_HASHES.json', dict(utc=utc(), note='routes and certification written before any gold read',
                                    files={n: sha(A / n) for n in ['certification_ledger_80.csv', 'dev_routes.csv', 'dev_table_pre_gold.csv']}))
print('PRE-GOLD', json.dumps(table, indent=1, default=str), flush=True)
# ---------------- gold (after the hashes above)
gold = {(ds, i): lab[(ds, i)]['gold'] for (ds, i) in lab}
for row in table:
    ds, b = row['setting'].split()[1].split('/')
    rt = {x['id']: x['route'] == 'R' for x in routes if x['setting'] == f'{ds}/{b}'}
    pol = sum((oR(ds, i) if rt[i] else ref[b][(ds, i)]) == gold[(ds, i)] for i in units[ds]['dev'])
    rf = sum(ref[b][(ds, i)] == gold[(ds, i)] for i in units[ds]['dev'])
    row.update(correct_policy=pol, correct_reference=rf, correct_P_over_B=f'{pol}/{rf}')
accr = []
for ds in DS1:
    for sp in ['fit', 'cal', 'dev']:
        ids = units[ds][sp]; n = len(ids); row = dict(dataset=ds, split=sp, N=n)
        for name, get in [('R', lambda i: oR(ds, i)), ('Text', lambda i: ref['Text'][(ds, i)]), ('C2C', lambda i: ref['C2C'][(ds, i)])]:
            c = sum(get(i) == gold[(ds, i)] for i in ids); v = sum(get(i) == INV for i in ids)
            row.update({f'{name}_correct': c, f'{name}_acc_pct': 100 * c / n, f'{name}_invalid': v, f'{name}_invalid_pct': 100 * v / n})
        accr.append(row)
wcsv('dev_table.csv', table); wcsv('accuracy_invalid_per_split.csv', accr)
print('TABLE', json.dumps(table, indent=1, default=str)); print('ACC', json.dumps(accr, indent=1))
