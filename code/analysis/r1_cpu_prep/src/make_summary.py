"""Render results/SUMMARY.md (one table per item) from the result CSVs. POST-HOC."""
from common_r1 import *

R = P / 'results'
def c(name): return csvread(R / name)
def f(x, d=1): return f'{float(x):.{d}f}'
def qs(x): return '0' if float(x) == 0 else f'{float(x):.2f}'.rstrip('0').rstrip('.') if float(x) < 1 else '1'
def key(r): return (r['pair'], r['task'], r['reference'])
def lab(s): return f'{s[0]}/{s[1]}/{s[2]}'

L = []
w = L.append
w('# P2 R1 reviewer re-analyses (CPU only, saved records)\n')
w(f'**{LABEL}.** Stage folder: `{P}`. Scripts: `src/`; tables: `results/*.csv`.\n')
w('Conventions: q = 0 means fallback (always run the reference). Dev "chg/omit" is changed answers over development questions answered by R alone. Dev units: 742 OBQA, 299 ARC, 2,641 MMLU-Pro group representatives.\n')

# Item 1
w('## 1. Sanity check: deployed q recomputed from ledgers\n')
w('| Setting | Recomputed q | Expected q | Match | max abs diff in p / CP (recomputed from n,k) |\n|---|---|---|---|---|')
for r in c('item1_deployed_q_check.csv'):
    w(f"| {lab(key(r))} | {qs(r['recomputed_q'])} | {qs(r['expected_q'])} | {r['match']} | {float(r['max_abs_p_diff']):.0e} / {float(r['max_abs_CP_diff']):.0e} |")
w('\nSources: `P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/summary/calibration_all_160.csv`, `P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/calibration/{obqa,arc}_{T,C}.csv`, `P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/calibration/40_test_ledger.csv` (280 rows). All 14 match; no STOP.\n')

# Item 2
w('## 2. Calibration table\n')
w('Selected q, or for fallback settings the grid point with the smallest p (ties: smallest q, all tied q listed).\n')
w('| Setting | Basis | q | n_q | k_q | p | CP .999 UB | small: n_q at q=.05 / .10 |\n|---|---|---|---|---|---|---|---|')
for r in c('item2_calibration_table.csv'):
    extra = f"{r['n_q0.05']} / {r['n_q0.10']}" if r['pair'] == 'small' else ''
    basis = 'selected' if r['basis'] == 'selected' else f"fallback min-p (tied q: {r['min_p_tied_q']})"
    w(f"| {lab(key(r))} | {basis} | {qs(r['q'])} | {r['n_q']} | {r['k_q']} | {float(r['p']):.3g} | {float(r['CP_upper_0999']):.4f} | {extra} |")
w('\nSource: same ledgers as item 1; p and CP recomputed from (n_q, k_q). File: `results/item2_calibration_table.csv`.\n')

# Items 3-4
S3 = {}
for r in c('item3_sensitivity.csv'): S3[key(r), r['variant']] = r
S4 = {key(r): r for r in c('item4_learned_D.csv')}
AUC = {(key(r), r['score']): float(r['dev_AUROC']) for r in c('item3_dev_auroc.csv')}
def cell(r):
    if r is None: return 'n/a'
    q = float(r['deployed_q'])
    if q == 0: return '0'
    cal = f"{r['cal_n']}/{r['cal_k']}"
    dev = f"{f(r['dev_coverage_pct'])}%, {r['dev_changed_over_omitted']}" if r.get('dev_changed_over_omitted') not in (None, '') else 'dev pending features'
    return f"{qs(q)} (cal {cal}; {dev})"
w('## 3. Sensitivity of the certification rule and score (ledger n,k; dev at the same fit threshold)\n')
w('Cell = deployed q (cal n/k at that q; dev coverage %, dev changed/omitted). "0" = fallback. (a) alpha .02 / .10, cutoff .001 per candidate. (b) Fixed-sequence: ascending q, level .02 each, stop at the first failure. (c) Entropy H(p) and margin 1-(p1-p2) from saved probe vectors: fit order statistics ceil(jN/20), ties included, q=1 fixed R, alpha .05, cutoff .001.\n')
w('| Setting | Primary (ProbeMax) | alpha .02 | alpha .10 | Fixed-seq | Entropy | Margin |\n|---|---|---|---|---|---|---|')
for s in SETTINGS:
    ent = cell(S3.get((s, 'Entropy')))
    if s == ('large', 'OBQA', 'Text'): ent += ' [historically tested]'
    prim = cell(S3.get((s, 'primary_ProbeMax'))) + (' [historically tested]' if s == ('large', 'OBQA', 'Text') else '')
    w(f"| {lab(s)} | {prim} | {cell(S3.get((s, 'alpha_0.02')))} | {cell(S3.get((s, 'alpha_0.10')))} | {cell(S3.get((s, 'fixed_sequence_0.02')))} | {ent} | {cell(S3.get((s, 'Margin')))} |")
w('\n**Dev AUROC for R-vs-reference disagreement** (same dev units):\n')
w('| Setting | ProbeMax | Entropy | Margin | D (item 4) |\n|---|---|---|---|---|')
for s in SETTINGS:
    d = S4.get(s); dauc = f"{float(d['dev_AUROC']):.3f}" if d and d.get('dev_AUROC') else ('pending features' if d else 'no features')
    w(f"| {lab(s)} | {AUC[s, 'ProbeMax']:.3f} | {AUC[s, 'Entropy']:.3f} | {AUC[s, 'Margin']:.3f} | {dauc} |")
w('\nChecks (`results/item3_input_checks.csv`): for all 14 settings, the ProbeMax fit thresholds equal the stored ones, ledger n/k are reproduced from the saved scores, and dev disagreement, AUROC, coverage and changed/omitted equal Table tab:dev_full. The historical ProbeEntropy ledger (`P2_ZERO_GOLD_CONTROLS_20260914T065145Z/summary/calibration_new_60.csv`; H/ln4, rank-equivalent) is reproduced exactly: q=.80, cal 1065/18, dev 18/572. Probe sources are listed per setting in the checks CSV (P2_ZERO_GOLD_CONTROLS records/probe_records.jsonl; P2_CONFIDENCE_REFERENCE_BOUNDARIES records/*_{fit,cal,dev}_probes.jsonl; medium probes/*.jsonl; MMLU-Pro shards/{1,2}/probes/*.jsonl). Answers come from P2_SCORING_V2 labels/, medium actions/, and MMLU-Pro summary/merged_numeric_rows.jsonl.\n')

w('## 4. Learned control D (refit exactly as fit_head.py; fit split only; target 1[o_R != o_b])\n')
w('| Setting | Deployed q | cal n/k | Dev | cal AUROC | Note |\n|---|---|---|---|---|---|')
CH = {key(r): r for r in c('item4_fit_checks.csv')}
for s in [(p, t, r) for p in ['small', 'large'] for t in ['OBQA', 'ARC'] for r in ['Text', 'C2C']]:
    d = S4[s]; q = float(d['deployed_q'])
    dev = f"{f(d['dev_coverage_pct'])}%, {d['dev_changed_over_omitted']}" if d.get('dev_status') == 'evaluated' else 'pending features'
    note = 'historically tested' if s == ('large', 'OBQA', 'Text') else ''
    w(f"| {lab(s)} | {qs(q)} | {(d['cal_n'] + '/' + d['cal_k']) if q > 0 else '-'} | {dev} | {float(CH[s]['cal_AUROC']):.3f} | {note} |")
h = CH[('large', 'OBQA', 'Text')]
w(f"\nLR = {read(BIN / 'frozen_config.json')['LR']} on E1 z features (`P2_E1_DIRECTION_20260913T053456Z/FEATURE_INDEX.csv`; 8192-d large, 2048-d small); dev features exist only for large/OBQA (`P2_RISK_CALIBRATION_BINARY_20260914T043954Z/features/dev`). All 8 fits converged with no warnings. ARC fit uses the 670 fit representatives (same unit as the ProbeMax thresholds). Reproduction of the historical large/OBQA/Text head: target identical = {h['target_equals_historical']}; max |dP| vs `models/disagreement.joblib` = {float(h['max_abs_prob_diff_vs_historical_fit']):.1e} (fit) / {float(h['max_abs_prob_diff_vs_historical_cal']):.1e} (cal); ledger identical to `summary/calibration_100.csv` = {h['ledger_equals_historical']}; thresholds differ from `models/thresholds.json` by at most 4.7e-16 (float noise). The dev result 6/230 matches the paper.\n")

# Item 5
w('## 5. Cold / first requests on the existing replays (paired saving = fixed minus policy, ms)\n')
w('(i) paper mean [95%]; (ii) excluding every question on which either arm made its first formal request; (iii) 5% trimmed mean (5% cut from each tail, scipy trim_mean) of the paired differences. Seed 0, 2,000 resamples: (i) and (iii) use each replay\'s saved index file; (ii) uses default_rng(0).integers(0,N,(2000,N)) over the remaining units.\n')
w('| Replay / ref | First request: fixed arm (ms) | First request: policy arm (ms) | (i) paper | Reproduces | (ii) excl. first (N) | (iii) 5% trimmed |\n|---|---|---|---|---|---|---|')
for r in c('item5_cold_request_sensitivity.csv'):
    fc = ' (cold)' if r['fixed_first_global_cold'] == 'True' else ''
    pc = ' (cold)' if r['policy_first_global_cold'] == 'True' else ''
    w(f"| {r['pair']}/{r['task']}/{r['reference']} | {r['fixed_first_id']}: {f(r['fixed_first_ms'])}{fc} | {r['policy_first_id']}: {f(r['policy_first_ms'])}{pc} | {f(r['i_mean_ms'])} [{f(r['i_CI_low'])}, {f(r['i_CI_high'])}] | {r['i_reproduces_paper']} | {f(r['ii_mean_ms'])} [{f(r['ii_CI_low'])}, {f(r['ii_CI_high'])}] ({r['ii_N']}) | {f(r['iii_trimmed_mean_ms'])} [{f(r['iii_CI_low'])}, {f(r['iii_CI_high'])}] |")
w('\n"(cold)" marks the single first request after model load in that job (`cold_first_request` / `first_formal_request_global`); every other arm\'s first request came after other arms had already run in the same residency. In each replay both arms of a pair made their first request on the same question, so (ii) drops one unit. Sources: `P2_FROZEN_POLICY_E2E_VALIDATION_20260914T174120Z/records/e2e_requests.jsonl`, `P2_MEDIUM_PAIR_E2E_STAGE2_20260915T205303Z/records/e2e_requests.jsonl`, `P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z/records/four_arm_requests.jsonl`, `P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/records/e2e_requests.jsonl` (sealed test uses 1,172 group representatives). All four arms of every panel: `results/item5_arm_first_requests.csv`.\n')

# Item 6
w('## 6. MMLU-Pro panel accuracy (128 questions; paired bootstrap, seed 0, 2,000)\n')
w('| Ref | Policy / fixed correct | Delta acc (pp) | 95% interval (pp) | Benefit / harm questions |\n|---|---|---|---|---|')
for r in c('item6_mmlu_pro_panel_accuracy.csv'):
    w(f"| {r['reference']} | {r['policy_correct']}/{r['fixed_correct']} | {float(r['delta_acc_pp']):+.2f} | [{float(r['CI95_low_pp']):.2f}, {float(r['CI95_high_pp']):.2f}] | {r['benefit']} / {r['harm']} |")
w('\nSource: `P2_MMLU_PRO_E2E_STAGE2_20260916T212147Z/records/paired_per_question.jsonl`; indices `protocol/bootstrap_indices.npz` (verified equal to default_rng(0)).\n')

# Item 7
w('## 7. Provenance (read-only)\n')
w('**Key timestamps** (`results/item7_key_timestamps.csv`):\n')
w('| Fact | Value |\n|---|---|')
for r in c('item7_key_timestamps.csv'):
    w(f"| {r['fact']} | {r['value'].replace(str(ROOT) + '/', '')} |")
w('\n**Per setting: before 2026-09-14T04:41:36Z, was any statistic or threshold test computed on that setting\'s calibration split?**\n')
w('| Setting | Status | Evidence | Superset (full-train) exposure before the freeze |\n|---|---|---|---|')
for r in c('item7_provenance_by_setting.csv'):
    w(f"| {lab(key(r))} | {r['status_before_freeze']} | {r['evidence'].replace(str(ROOT) + '/', '')} | {r['superset_exposure']} |")
w('\n**Pre-freeze statistics on populations that contain the later calibration questions (never restricted to them)** (`results/item7_prefreeze_superset_exposure.csv`):\n')
w('| mtime (UTC) | File | What |\n|---|---|---|')
for r in c('item7_prefreeze_superset_exposure.csv'):
    w(f"| {r['mtime']} | `{r['path'].replace(str(ROOT) + '/', '')}` | {r['what']} |")
w('\n**First production of calibration-split R/Text/C2C answers (small and large pairs)** (`results/item7_cal_answer_production.csv`):\n')
w('| Pair/task | Source | Cal rows (3 actions) | Job(s) | Row utc first-last / file mtime |\n|---|---|---|---|---|')
for r in c('item7_cal_answer_production.csv'):
    w(f"| {r['pair']}/{r['task']} | `{r['source_path'].replace(str(ROOT) + '/', '')}` | {r['cal_rows']} | {r['jobs']} | {r['row_utc_first']} - {r['row_utc_last']} / {r['file_mtime']} |")
w('\nPBS windows for the OBQA rows, which have no per-row utc: small/OBQA ClusterA 7602469 ran 07:33:13-08:29:25 and 7602485 ran 08:30:34-09:07:21 on 2026-09-10 (`P2_5_20260910T072811Z/evidence/job_*.json`); large/OBQA ClusterB 185359 ran 02:04:43-04:04:54 on 2026-09-11 (`P2_6_20260910T164138Z/evidence/job_185359.json`). No P2_1-P2_4 output contains any calibration-split question.\n')
w('**Parser V2 timing:** V2 was frozen 2026-09-12T19:19:38Z (`P2_SCORING_V2_20260912T191445Z/RULE_FREEZE_V2.json`). That is before the first calibration-split disagreement statistic, 2026-09-14T04:50:18Z (large/OBQA/Text, `P2_RISK_CALIBRATION_BINARY_20260914T043954Z/inputs/candidate_cal.jsonl`). For the other small/large settings, the first calibration-split statistic was written 2026-09-14T17:06-17:13Z (`P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/inputs/*_cal_machine_d.jsonl`). However, V2 rules were revised after a record-level review of exposed cases, including gold (RULE_FREEZE_V2 says "NOT globally blinded"). That review covered 355 train questions that later fell into calibration splits (large/OBQA 30, large/ARC 26, small/OBQA 186, small/ARC 113), before any split existed.\n')
(R / 'SUMMARY.md').write_text('\n'.join(L) + '\n')
print('\n'.join(L))
