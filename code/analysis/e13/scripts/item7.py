"""E13 Item 7: re-split stability for every setting that has fit and calibration outputs.
Sources: E5-b (P2_R2_CPU_20260919T220412Z/results/e5b_resplit_{stability,per_seed}.csv; 14 main + 7 cross-family) and
E8 (P2_R2_E8_20260920T012544Z/analysis/development/resplit_{stability,per_seed}.csv; 4 small/medium MMLU-Pro).
Deploy shares are recounted from the per-seed files (seeds 1..200). Settings without fit-split reference outputs are listed."""
import csv, json
from e13_common import *

E5 = ROOT / 'P2_R2_CPU_20260919T220412Z/results'
E8 = ROOT / 'P2_R2_E8_20260920T012544Z/analysis/development'
E10 = ROOT / 'P2_R4_E10_20260920T225954Z'
rows, repro = [], []
for src, stab, per, key_rate in [('E5-b', E5 / 'e5b_resplit_stability.csv', E5 / 'e5b_resplit_per_seed.csv', 'cert_rate'),
                                 ('E8', E8 / 'resplit_stability.csv', E8 / 'resplit_per_seed.csv', 'certification_rate')]:
    ps = list(csv.DictReader(open(per)))
    for r in csv.DictReader(open(stab)):
        s = r['setting']
        seeds = [x for x in ps if x['setting'] == s and int(x['seed']) >= 1]
        n_dep = sum(float(x['q']) > 0 for x in seeds if x['q'] not in ('', 'None'))
        rows.append(dict(setting=s, source=src, original_outcome=r.get('orig_outcome') or r.get('original_outcome'),
                         n_seeds=len(seeds), deploy_share=n_dep / len(seeds), deploy_share_recorded=float(r[key_rate]),
                         recount_matches_record=abs(n_dep / len(seeds) - float(r[key_rate])) < 1e-12,
                         median_q=r.get('median_q', ''), IQR_q=r.get('IQR_q', ''), added_in_E13='no', source_file=str(stab), label=LABEL))
med = next(r for r in rows if r['setting'] == 'medium/ARC/C2C')
repro.append(dict(item=7, check='medium/ARC/C2C re-split deploy share (Table 7)', expected=0.96, got=round(med['deploy_share'], 2),
                  ok=round(med['deploy_share'], 2) == 0.96))
fb = [r for r in rows if r['original_outcome'].startswith('fallback')]
repro.append(dict(item=7, check='all fallback settings re-split deploy share (Table 7)', expected='0.00 for all',
                  got=f"max {max(r['deploy_share'] for r in fb):.2f} over {len(fb)}", ok=max(r['deploy_share'] for r in fb) == 0))
# settings without fit-split reference outputs
e10 = [json.loads(l) for f in sorted((E10 / 'records').glob('main_rank*.jsonl')) for l in open(f)]
fitT = sum(1 for r in e10 if r['split'] == 'fit' and r['action'] == 'T')
nofit = [dict(setting='large/OBQA/Text+fact', reason='E6 ran Text+fact on calibration and development only (no fit-split reference outputs)', label=LABEL),
         dict(setting='large/GSM8K/Text (E10)', reason=f'E10 fit split has receiver-only outputs only ({fitT} Text outputs on fit); no re-split possible', label=LABEL)]
csvout(RES / 'item7_resplit_all.csv', rows)
csvout(RES / 'item7_no_fit_outputs.csv', nofit)
csvout(RES / 'item7_repro_checks.csv', repro)
for r in rows: print(r['setting'], r['original_outcome'], r['n_seeds'], f"{r['deploy_share']:.3f}", r['recount_matches_record'])
for r in repro: print(r)
print(nofit)
