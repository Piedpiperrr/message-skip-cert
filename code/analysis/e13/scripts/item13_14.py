"""E13 follow-ups added after the preregistration hash (counting only).
Item 13: which settings the E9c helper-aware analysis covers (P2_R3_E9BC/analysis/E9C_RESULTS.json).
Item 14: reconcile the E8 D1 difference counts (analysis/development/D1_label_differences.csv) with Item 10."""
import csv, json, collections
from e13_common import *

E9 = ROOT / 'P2_R3_E9BC_20260920T061042Z/analysis/E9C_RESULTS.json'
E8 = ROOT / 'P2_R2_E8_20260920T012544Z'
LBL = 'POST-HOC follow-up added after the E13 preregistration hash; counting only'

# ---------------- Item 13
d = read(E9)
REF = {'T': 'Text', 'C': 'C2C', 'Tf': 'Text+fact'}
rows13 = [dict(row=i + 1, setting=r['setting'], pair=r['pair'], benchmark=r['dataset'], reference=REF[r['reference']],
               helper_prefill_variant=r.get('helper_prefill_variant', 'plain'), descriptive=r.get('descriptive', False),
               in_hypothesis_H=f"{r['pair']}/{r['dataset']}" in d['hypothesis_H']['populations'] and r['reference'] in ('T', 'C'),
               label=LBL) for i, r in enumerate(d['settings'])]
csvout(RES / 'item13_e9c_settings.csv', rows13)
distinct = {(r['pair'], r['benchmark'], r['reference']) for r in rows13}
print(len(rows13), 'rows,', len(distinct), 'distinct settings; Text+fact rows:', sum(r['reference'] == 'Text+fact' for r in rows13),
      '; H populations:', d['hypothesis_H']['n_populations'])

# ---------------- Item 14
e8 = list(csv.DictReader(open(E8 / 'analysis/development/D1_label_differences.csv')))
reps = {sp: {g['representative_id'] for g in read(E8 / f'splits/{sp}_groups.json')} for sp in ['fit', 'cal', 'dev']}
diff = [r for r in csv.DictReader(open(RES / 'item10_differing_outputs.csv')) if 'E8' in r['group']]
P = {'R': 'R', 'T': 'Text', 'C': 'C2C'}
rows14 = []
for r in e8:
    mine = [x for x in diff if x['pair'] == r['pair'] and x['path'] == P[r['action']]]
    bysp = collections.Counter(x['split'] for x in mine)
    rows14.append(dict(pair=r['pair'], action=P[r['action']], E8_N=int(r['N']), E8_differences=int(r['differences']),
                       E13_all_splits=len(mine), E13_fit=bysp['fit'], E13_cal=bysp['cal'], E13_dev=bysp['dev'],
                       E13_dev_representatives=sum(x['split'] == 'dev' and x['qid'] in reps['dev'] for x in mine),
                       match=len(mine) == int(r['differences']), E8_D1_sha256=r['D1_sha256'], label=LBL))
for pair in ['small', 'medium']:
    for ref in ['Text', 'C2C']:
        dv = [x for x in diff if x['pair'] == pair and x['split'] == 'dev' and x['qid'] in reps['dev'] and x['path'] in ('R', ref)]
        rows14.append(dict(pair=pair, action=f'setting {pair}/MMLU-Pro/{ref}: R + {ref} outputs on the 2,641 dev representatives',
                           E13_dev_representatives=len(dv), label=LBL))
csvout(RES / 'item14_d1_reconciliation.csv', rows14)
for r in rows14: print({k: v for k, v in r.items() if k not in ('label', 'E8_D1_sha256')})
print('D1 sha used by E13 Item 10:', __import__('parsers_r2').HASHES['D1'])
