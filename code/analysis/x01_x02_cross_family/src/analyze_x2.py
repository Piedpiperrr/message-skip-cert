"""X2 certification and development analysis, exactly as PROTOCOL_FREEZE.md sections 5-6 (CPU, login node).

Order: (1) hash every output file; (2) scores, thresholds, certification and routes WITHOUT gold, written and hashed;
(3) only then read gold for accuracy. Rule functions (thresholds, pval, cp999, deploy, route_mask) are imported unchanged
from P2_R1_CPU_20260919T045556Z/src/common_r1.py and data_r1.py (the paper's rules as used in the R1 reanalysis).
usage: analyze_x2.py <outputs glob relative to this folder, e.g. 'results/runs/*.jsonl'>
"""
import sys
sys.dont_write_bytecode = True
import glob, csv, math
from xfam_common import *
sys.path.insert(0, str(ROOT / 'P2_R1_CPU_20260919T045556Z/src'))
from common_r1 import thresholds, pval, cp999, deploy, GRID
from data_r1 import route_mask
import numpy as np
from sklearn.metrics import roc_auc_score

A = X / 'results/analysis'; A.mkdir(parents=True, exist_ok=True)
files = sorted(glob.glob(str(X / sys.argv[1])))
assert files
save(A / 'OUTPUT_HASHES.json', dict(utc=utc(), note='computed before any gold read', files={str(pathlib.Path(f).relative_to(X)): sha(f) for f in files}))
out = {}
for f in files:
    for r in jl(f):
        k = (r['dataset'], r['id']); assert k not in out, k; out[k] = r


def wcsv(name, rows):
    with open(A / name, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r))); w.writeheader(); w.writerows(rows)


INV = 'INVALID'
ans = lambda r, a: (r[a]['parsed'] if r.get('runtime_error') is None else INV)
units, ledger, table, routes_rows, missing = {}, [], [], [], {}
for ds in DATASETS:
    U = {}
    for sp in ['fit', 'cal', 'dev']:
        rows = [r for r in jl(POP / f'{ds}_{sp}.jsonl') if r['representative']]
        missing[f'{ds}_{sp}'] = [r['id'] for r in rows if (ds, r['id']) not in out or out[(ds, r['id'])].get('runtime_error')]
        U[sp] = [out[(ds, r['id'])] for r in rows if (ds, r['id']) in out]
    units[ds] = U
    assert not any(missing[f'{ds}_{sp}'] for sp in ['fit', 'cal', 'dev']), ('incomplete or failed outputs', ds, {s: len(missing[f'{ds}_{s}']) for s in ['fit', 'cal', 'dev']})
    u = {sp: np.array([r['P']['ProbeMax'] for r in U[sp]]) for sp in U}
    d = {sp: np.array([ans(r, 'R') != ans(r, 'T') for r in U[sp]]) for sp in U}
    cuts = thresholds(list(u['fit']))
    led = []
    for q, t in zip(GRID, cuts):
        m = route_mask(u['cal'], q, t); n = int(m.sum()); k = int(d['cal'][m].sum())
        led.append(dict(q=q, threshold=t, N=len(u['cal']), n=n, k=k, p=pval(k, n), CP=cp999(k, n), accepted=pval(k, n) <= .001))
    q, acc = deploy(led)
    t = cuts[GRID.index(q)] if q > 0 else None
    md = route_mask(u['dev'], q, t); n = int(md.sum()); k = int(d['dev'][md].sum())
    for r in led: ledger.append(dict(setting=f'{ds}/Text', **r))
    auc = roc_auc_score(d['dev'], u['dev']) if 0 < d['dev'].sum() < len(d['dev']) else float('nan')
    table.append(dict(setting=f'X2 {ds}/Text', N_dev=len(u['dev']), dis=int(d['dev'].sum()), dis_over_N=f"{int(d['dev'].sum())}/{len(u['dev'])}", AUROC=auc,
                      min_UCB=min(r['CP'] for r in led), q=q, threshold=t, accepted_q=';'.join(f'{x:g}' for x in acc),
                      coverage_pct=100 * n / len(u['dev']), changed_over_omitted=f'{k}/{n}' if n else 'N/A'))
    for r, m in zip(U['dev'], md):
        routes_rows.append(dict(dataset=ds, id=r['id'], ProbeMax=r['P']['ProbeMax'], route='R' if m else 'Text', o_R=ans(r, 'R'), o_T=ans(r, 'T')))
wcsv('certification_ledger_60.csv', ledger); wcsv('dev_routes.csv', routes_rows); wcsv('dev_table_pre_gold.csv', table)
save(A / 'ROUTES_HASHES.json', dict(utc=utc(), note='routes and certification written before any gold read',
                                    files={n: sha(A / n) for n in ['certification_ledger_60.csv', 'dev_routes.csv', 'dev_table_pre_gold.csv']}))
print('PRE-GOLD', json.dumps(table, indent=1, default=str), flush=True)

# ---------------- gold (only after the hashes above)
gold = {}
for name in ['full_train', 'full_development']:
    for r in jl(V2L / f'{name}_P2_SCORING_V2.jsonl'):
        if r['pair'] == 'large': gold[(r['dataset'], r['id'])] = r['gold']
import pyarrow.parquet as pq
for r in pq.read_table(ROOT / 'P2_MMLU_PRO_BREADTH_PROTOCOL_AND_COST_REVIEW_20260915T224801Z/dataset/test-00000-of-00001.parquet', columns=['question_id', 'answer']).to_pylist():
    gold[('mmlu_pro', 'test:' + str(r['question_id']))] = r['answer']
acc_rows = []
for row, ds in zip(table, DATASETS):
    U = units[ds]
    routed = {x['id']: x['route'] == 'R' for x in routes_rows if x['dataset'] == ds}
    g = lambda r: gold[(ds, r['id'])]
    pol = sum((ans(r, 'R') if routed[r['id']] else ans(r, 'T')) == g(r) for r in U['dev'])
    ref = sum(ans(r, 'T') == g(r) for r in U['dev'])
    row.update(correct_policy=pol, correct_reference=ref, correct_P_over_B=f'{pol}/{ref}')
    for sp in ['fit', 'cal', 'dev']:
        n = len(U[sp])
        acc_rows.append(dict(dataset=ds, split=sp, N=n, R_correct=sum(ans(r, 'R') == g(r) for r in U[sp]), T_correct=sum(ans(r, 'T') == g(r) for r in U[sp]),
                             R_invalid=sum(ans(r, 'R') == INV for r in U[sp]), T_invalid=sum(ans(r, 'T') == INV for r in U[sp])))
        a_ = acc_rows[-1]; a_.update(R_acc_pct=100 * a_['R_correct'] / n, T_acc_pct=100 * a_['T_correct'] / n, R_invalid_pct=100 * a_['R_invalid'] / n, T_invalid_pct=100 * a_['T_invalid'] / n)
wcsv('dev_table.csv', table); wcsv('accuracy_invalid_per_split.csv', acc_rows)
print('TABLE', json.dumps(table, indent=1, default=str)); print('ACC', json.dumps(acc_rows, indent=1))
