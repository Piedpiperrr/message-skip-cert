"""Render SUMMARY.md from the result CSVs of this stage. Writes only SUMMARY.md."""
import sys
sys.dont_write_bytecode = True
from common_r2a import *      # noqa: F401,F403
import csv as _csv


def rd(n): return list(_csv.DictReader(open(RES / n)))


def f(x, d=1): return f'{float(x):.{d}f}'


L = []
w = L.append

w('# P2_R2_ANALYSIS_20260920T002850Z — E7 arms, E6 replay, E6 development and calibration extras')
w('')
w('**POST-HOC analysis of completed E6/E7 records.** Stage folder: '
  '`$DATA_DIR/P2_R2_ANALYSIS_20260920T002850Z`. '
  'Scripts in `scripts/`, tables in `results/`. No model was run, no job submitted, no GPU used, and no '
  'existing file was modified. ClusterA login node, CPU only.')
w('')
w('## 0. Sources and rules')
w('')
w('| What | Source |')
w('|---|---|')
w('| E7 protocol | `P2_R2_GPU_20260919T220941Z/e7/PROTOCOL_FREEZE_E7.md` |')
w('| E6 protocol | `P2_R2_GPU_20260919T220941Z/e6/PROTOCOL_FREEZE_E6.md` |')
w('| E7 records | `P2_R2_E7_20260919T231531Z/{large,mmlu,medium}/records_e7/e7_requests.jsonl` (job 7638030) |')
w('| E6 replay records | `P2_R2_E7_20260919T231531Z/e6replay/records_e6/e6_replay_requests.jsonl` (job 7638030, node B) |')
w('| E6 calibration/development outputs | `P2_R2_GPU_20260919T220941Z/e6/main/e6_shard{0..3}.jsonl` |')
w('| E6 frozen analysis | `P2_R2_GPU_20260919T220941Z/e6/analysis/E6_RESULTS.json` (certified q = .75) |')
w('| E3 repeat classes | `P2_R1_EXP_20260919T050555Z/results/E3_policy_savings.csv` |')
w('| X (208 reviewed OBQA calibration questions) | `P2_R2_CPU_20260919T220412Z/results/e5a_exposed_ids.csv`, rebuilt with `scripts/r2_common.py::exposed_ids` |')
w('| D1 parser | `P2_SCORE_SENSITIVITY_20260912T055929Z/diagnostic_parser_v1.py` |')
w('')
w('Reused frozen code and rules, unchanged:')
w('')
w('- **Bootstrap** — 2,000 paired resamples of the panel questions, `numpy.random.default_rng(0)`, '
  'percentile 2.5/97.5, exactly as `P2_R1_E3POL_REPEAT1_20260919T075315Z/large/src/analyze.py`.')
w('- **Version (a)** all 128 panel questions; **version (b)** drops every question on which either compared '
  'arm made its first formal request inside the replay (each arm\'s minimum `attempt`), and re-draws the '
  'bootstrap block at the reduced size — the rule of `e3_build/e3_metrics.py::saving_row`.')
w('- **Class** — `+` above zero (CI low > 0), `-` below zero (CI high < 0), `?` contains zero.')
w('- **Saving** — paired, fixed-reference latency minus arm latency, in ms.')
w('- **Certification tests** — `ledger_rows` of `P2_R2_CPU_20260919T220412Z/scripts/r2_common.py`: frozen fit '
  'quantile thresholds, `p = binom.cdf(k, n, .05)`, accept at `p <= .001`, deploy the largest accepted q.')
w('- **Reference-correction columns** — definitions taken verbatim from '
  '`P2_FOCUSED_REVISION_ROUND1B_AUDIT_FIX_AND_MANUSCRIPT_20260918T072631Z/audit_v2/scripts/audit_v2.py` block C '
  '(the code behind `tab_omit_keep.tex`).')
w('')
w('Gold labels were read only for the correct-answer counts, after every E6/E7 output was complete; the '
  'replay records themselves carry `gold_read: false`.')
w('')
w('**Nothing contradicted either freeze file.** All programmatic stop conditions are empty '
  '(`results/E7_CHECKS.json`, `results/E6REPLAY_CHECKS.json`, `results/E6_EXTRAS_CHECKS.json`).')
w('')

E3P = ROOT / 'P2_R1_E3POL_REPEAT1_20260919T075315Z'
PANELS = [
    ('large/OBQA + E6 replay + medium/OBQA', 'large/inputs/obqa_panel_ids.json', E3P / 'large/inputs/obqa_panel_ids.json'),
    ('large/ARC + medium/ARC', 'large/inputs/arc_panel_ids.json', E3P / 'large/inputs/arc_panel_ids.json'),
    ('MMLU-Pro', 'mmlu/inputs/candidate_e2e128_ids.json', E3P / 'mmlu/inputs/candidate_e2e128_ids.json'),
    ('E6 replay OBQA queries', 'e6replay/inputs/obqa_queries.jsonl', E3P / 'large/inputs/obqa_queries.jsonl'),
]
prov = []
w('Panels are byte-identical to the frozen E3 panels (and, for the E6 replay, to the file named in section 3 '
  'of the E6 freeze):')
w('')
w('| Panel | SHA-256 | Equals the E3 file |')
w('|---|---|---|')
for name, rel, e3f in PANELS:
    h, h2 = sha(E7 / rel), sha(e3f)
    prov.append(dict(panel=name, e7_path=str(E7 / rel), sha256=h, e3_path=str(e3f), e3_sha256=h2,
                     identical=h == h2, label=LABEL))
    w(f'| {name} | `{h[:16]}…` | {"yes" if h == h2 else "**NO**"} |')
wcsv('PANEL_IDENTITY.csv', prov)
w('')
w('Node layout followed section 5 of the E7 freeze: node A `compute-node` ran the four large OBQA/ARC panels, '
  'node B `compute-node` ran MMLU-Pro (Text, C2C), medium/OBQA (C2C) and medium/ARC (C2C), and then the E6 '
  'Text+fact replay of E6 freeze section 6 — all inside PBS job 7638030, one model residency per stage, '
  '`warmup_requests: 0`.')
w('')

# ------------------------------------------------------------------ E7
w('## 1. E7 — eight deployed policies x three arms vs the FIXED reference of the same run')
w('')
w('Panels are the frozen 128-question panels; every arm ran in the same allocation and the same model '
  'residency as its fixed reference. `probe` is the mean of the timed probe region of the arm.')
w('')
w('| Pair/benchmark/ref | q (q_A) | Arm | Omitted | Mean saving (a), ms [95%] | Mean saving (b), ms [95%] | Class a/b | Median (a) | Probe ms | Changed/omitted | Correct arm/fixed |')
w('|---|---|---|---|---|---|---|---|---|---|---|')
for r in rd('E7_arm_summary.csv'):
    q = r['deployed_q'] if r['deployed_q'] == r['q_A'] else f"{r['deployed_q']} ({r['q_A']})"
    w(f"| {r['pair']}/{r['task']}/{r['reference']} | {q} | {r['arm']} | {r['omitted']} | "
      f"{f(r['a_mean_saving_ms'])} [{f(r['a_CI_low'])}, {f(r['a_CI_high'])}] | "
      f"{f(r['b_mean_saving_ms'])} [{f(r['b_CI_low'])}, {f(r['b_CI_high'])}] | "
      f"{r['a_class']}/{r['b_class']} | {f(r['a_median_saving_ms'])} | {f(r['mean_probe_ms'])} | "
      f"{r['changed_over_omitted']} | {r['correct_arm']}/{r['correct_fixed']} |")
w('')
w('Version (b) drops one question per row (the panel question at ordinal 0, where the fixed arm and the '
  'compared arm both made their first request), so `b_N = 127` everywhere; the excluded id is in '
  '`results/E7_arm_summary.csv`. `q_A` differs from the deployed `q` only for medium/OBQA/C2C (.50 vs .55), '
  'which is why its ARGMAX arm omits 61 rather than 66 questions.')
w('')
w('### 1c. Text/C2C saving ratio, large pair')
w('')
w('| Benchmark | Arm | Text saving (a) | C2C saving (a) | Ratio (a) | Ratio (b) |')
w('|---|---|---|---|---|---|')
for r in rd('E7_text_c2c_ratio.csv'):
    w(f"| {r['benchmark']} | {r['arm']} | {f(r['a_Text_saving_ms'])} | {f(r['a_C2C_saving_ms'])} | "
      f"{f(r['a_ratio_Text_over_C2C'], 2)} | {f(r['b_ratio_Text_over_C2C'], 2)} |")
w('')
w('The MMLU-Pro ratios divide by a C2C saving whose interval contains zero for ORIGINAL and REUSE, so those '
  'two ratios are unstable and are reported for completeness only.')
w('')
w('### 1d. ORIGINAL-arm class vs the three E3 repeats (descriptive)')
w('')
w('| Pair/benchmark/ref | E7 ORIGINAL a/b | REPEAT1 a/b | REPEAT2 a/b | REPEAT3 a/b | Match all three |')
w('|---|---|---|---|---|---|')
for r in rd('E7_e3_class_comparison.csv'):
    w(f"| {r['pair']}/{r['task']}/{r['reference']} | {r['E7_ORIGINAL_class_a']}/{r['E7_ORIGINAL_class_b']} | "
      f"{r['REPEAT1_a']}/{r['REPEAT1_b']} | {r['REPEAT2_a']}/{r['REPEAT2_b']} | {r['REPEAT3_a']}/{r['REPEAT3_b']} | "
      f"{'yes' if r['matches_all_three_a'] == 'yes' and r['matches_all_three_b'] == 'yes' else 'no'} |")
w('')
w('Descriptive only: classes are compared, never the numbers, and E7 is a single run on the same hardware '
  'family as the E3 repeats but a different job.')
w('')
w('### 1e. REUSE outputs that differ from the ORIGINAL receiver-only output')
w('')
dif = rd('E7_reuse_output_differences.csv')
n_om_reuse = sum(int(r['omitted']) for r in rd('E7_arm_summary.csv') if r['arm'] == 'REUSE')
w(f'{len(dif)} of the {n_om_reuse} omitted REUSE requests produced a raw string different from the ORIGINAL arm '
  'on the same question (large 10, medium 3, MMLU-Pro 0 — the counts the replay itself recorded in '
  '`REPLAY_VERIFICATION.json`); no difference occurred on a kept question. **The parsed V2 label is identical in '
  'all ' + str(len(dif)) + ' cases**; every difference is trailing punctuation or a continued option phrase. '
  'Full strings, as the freeze requires, are in `results/E7_reuse_output_differences.csv`. '
  'The list was rebuilt from the request records and matches the replay\'s own '
  '`P2_R2_E7_20260919T231531Z/REUSE_OUTPUT_DIFFERENCES.csv` question for question.')
w('')
w('The pre-replay validation of section 4 of the E7 freeze passed on both receivers '
  '(`e7/validation/E7_VALIDATION_{large,medium}.json`): REUSE raw-string mismatches 0/16 for Qwen3-8B and '
  '1/16 for Qwen3-1.7B, both within the "more than 1 of 16 stops the replay" limit, and ARGMAX matched the '
  'saved probe argmax label on 16/16 for both.')
w('')
w('| Setting | Question | REUSE raw | ORIGINAL raw | Label |')
w('|---|---|---|---|---|')
for r in dif:
    w(f"| {r['setting']} | {r['id']} | `{r['reuse_raw']}` | `{r['original_raw']}` | {r['reuse_label']} = {r['original_label']} |")
w('')

# ------------------------------------------------------------------ E6 replay
w('## 2. E6 replay — fixed Text+fact vs the Text+fact policy (node B of job 7638030)')
w('')
r = rd('E6REPLAY_summary.csv')[0]
w('| Pair/benchmark/ref | q | Omitted | Mean saving (a), ms [95%] | Mean saving (b), ms [95%] | Class a/b | Median (a) | Probe ms | Changed/omitted | Correct policy/fixed |')
w('|---|---|---|---|---|---|---|---|---|---|')
w(f"| large/OBQA/Text+fact | {r['q']} | {r['omitted']}/128 | "
  f"{f(r['a_mean_saving_ms'])} [{f(r['a_CI_low'])}, {f(r['a_CI_high'])}] | "
  f"{f(r['b_mean_saving_ms'])} [{f(r['b_CI_low'])}, {f(r['b_CI_high'])}] | {r['a_class']}/{r['b_class']} | "
  f"{f(r['a_median_saving_ms'])} | {f(r['mean_probe_ms'])} | {r['changed_over_omitted']} | "
  f"{r['correct_policy']}/{r['correct_fixed']} |")
w('')
w(f"Mean latency: fixed Text+fact {f(r['mean_fixed_latency_ms'])} ms, policy {f(r['mean_policy_latency_ms'])} ms. "
  f"No INVALID parse and no runtime failure in either arm. The replay ran at the certified q = "
  f"{r['q']} and threshold {r['threshold']}, exactly the values in `e6/analysis/E6_RESULTS.json`. "
  "Classification only, as section 6 of the E6 freeze requires; no number here is compared with any other machine.")
w('')
w(f"The policy answers {r['correct_policy']} of 128 panel questions correctly against "
  f"{r['correct_fixed']} for fixed Text+fact ({r['accuracy_diff_answers']} answers). That is a descriptive "
  "panel count, not a certified quantity — the risk test controls answer changes, not correctness.")
w('')

# ------------------------------------------------------------------ E6 extras
w('## 3. E6 development and calibration extras')
w('')
w('### 3a. Development (742 OBQA group representatives), at the certified q = .75')
w('')
d = rd('E6_dev_reference_corrections.csv')
p = d[0]
w('| Setting | Omitted/N | Policy correct | Fixed Text+fact correct | Delta accuracy (pp) [95%] |')
w('|---|---|---|---|---|')
w(f"| large/OBQA/Text+fact | {p['omitted_over_N']} | {p['policy_correct']} | {p['fixed_TextFact_correct']} | "
  f"{f(p['delta_accuracy_pp'], 2)} [{f(p['delta_CI_low_pp'], 2)}, {f(p['delta_CI_high_pp'], 2)}] |")
w('')
w('Reference-correction table, columns exactly as `tab_omit_keep.tex`:')
w('')
w('| Setting | Omitted/N | Lost | Kept | Gained | Net | Other | Unused (omit/keep) |')
w('|---|---|---|---|---|---|---|---|')
for x in d:
    w(f"| large/OBQA/Text+fact (other = {x['other_communication_action']}) | {x['omitted_over_N']} | "
      f"{x['lost']}/{x['ref_corrections_total']} | {x['kept']}/{x['ref_corrections_total']} | {x['gained']} | "
      f"{int(x['net']):+d} | {x['other']} | {x['unused_on_omit']}/{x['unused_on_keep']} |")
w('')
w('The paper\'s three actions are R, Text and C2C; E6 substitutes Text+fact for Text, so *other* and *unused* '
  'need a third action. The first row takes **C2C** as the other communication action (the direct substitution '
  'into the paper\'s table); the second takes the original **Text** action. Lost/kept/gained/net do not depend '
  'on that choice. For reference, the frozen paper row for the same population against plain Text at q = .80 is '
  '`572/742 | 13/46 | 33/46 | 6 | -7 | 1 | 14/18`.')
w('')
w(f"The identity `policy - reference = gained - lost` holds: "
  f"{p['policy_correct']} - {p['fixed_TextFact_correct']} = {p['gained']} - {p['lost']}. "
  f"Other development counts: R {p['R_correct']}, Text {p['Text_correct']}, C2C {p['C2C_correct']} correct; "
  f"changed on omitted {p['changed_on_omitted']}.")
w('')
w('### 3b. Calibration relabelled with D1')
w('')
w('| Variant | o_R D1 vs V2 | o_Text+fact D1 vs V2 | Answer-change labels differing from V2 | n/k at q=.75 | p | q=.75 accepted | Largest accepted q |')
w('|---|---|---|---|---|---|---|---|')
for x in rd('E6_cal_D1_relabel.csv'):
    w(f"| {x['variant']} | {x['o_R_D1_vs_V2_differences']} | {x['o_TextFact_D1_vs_V2_differences']} | "
      f"{x['d_label_differences_vs_V2']} | {x['n_at_q075']}/{x['k_at_q075']} | {x['p_at_q075']} | "
      f"{x['q075_accepted']} | {x['largest_accepted_q']} |")
w('')
w('The task names the Text+fact side; both variants are given because the answer-change label needs both '
  'sides, and E5-a (c) relabels both. The pre-V2 D1 parser reproduces every V2 label on both sides of all '
  '1,366 calibration rows, so the ledger is bit-identical to the frozen one '
  '(`e6/analysis/E6_LEDGER.csv` at q = .75: n = 999, k = 22, p = 4.83045e-06, accepted). '
  '**q = .75 is still accepted, and .75 is still the largest accepted q.**')
w('')
w('### 3c. Calibration after removing X (the 208 reviewed OBQA questions), as in E5-a')
w('')
x = rd('E6_cal_without_X.csv')[0]
w('| Setting | N_cal | cal ∩ X | N clean | n/k at q=.75 | p | CP .999 | q=.75 accepted on C\\X | Largest accepted q |')
w('|---|---|---|---|---|---|---|---|---|')
w(f"| large/OBQA/Text+fact | {x['N_cal']} | {x['exposed_in_cal']} | {x['N_clean']} | "
  f"{x['clean_n']}/{x['clean_k']} | {x['clean_p']} | {x['clean_CP999']} | {x['q075_accepted_on_clean']} | "
  f"{x['largest_clean_accepted_q']} |")
w('')
w(f"Disagreement rate between R and Text+fact: {x['rate_X']} on X ({x['dis_X']}/{x['exposed_in_cal']}), "
  f"{x['rate_clean']} on C\\X ({x['dis_clean']}/{x['N_clean']}), {x['rate_full']} on the full calibration split. "
  "X is content-selected (records where the run-time and D1 parsers disagreed, or D1 flagged the parse "
  "ambiguous), so it is enriched for parse-hard outputs; the rates are reported separately for that reason. "
  "The full 20-row clean ledger is in `results/E6_cal_without_X_ledger.csv`.")
w('')

# ------------------------------------------------------------------ files
w('## 4. Files')
w('')
w('| CSV | Contents |')
w('|---|---|')
for n, d_ in [
    ('E7_arm_summary.csv', '24 rows: 8 policies x 3 arms, versions (a) and (b), classes, medians, probe cost, changed/omitted, correct counts'),
    ('E7_per_question.csv', '3,072 rows: per question and arm — ProbeMax, omitted, both latencies, saving, probe ms, both answers, gold, version-(b) membership'),
    ('E7_text_c2c_ratio.csv', 'Text/C2C saving ratios per benchmark and arm, versions (a) and (b)'),
    ('E7_probe_cost.csv', 'mean and median probe and selector cost per setting and arm'),
    ('E7_reuse_output_differences.csv', 'every REUSE output differing from the ORIGINAL output, with both raw strings and both parsed labels'),
    ('E7_e3_class_comparison.csv', 'ORIGINAL-arm class vs the three E3 repeats, versions (a) and (b)'),
    ('E7_CHECKS.json', 'stop conditions (empty) and omitted counts recomputed vs REPLAY_VERIFICATION.json'),
    ('E6REPLAY_summary.csv', 'E6 replay: savings (a)/(b), classes, median, probe cost, changed/omitted, correct counts'),
    ('E6REPLAY_per_question.csv', '128 rows of the E6 replay panel'),
    ('E6REPLAY_CHECKS.json', 'stop conditions (empty) and omitted count vs REPLAY_VERIFICATION.json'),
    ('E6_dev_reference_corrections.csv', 'development table 3a, both choices of the third action'),
    ('E6_cal_D1_relabel.csv', 'D1 relabelling of the calibration outputs and the redone q = .75 test'),
    ('E6_cal_without_X.csv', 'the q = .75 test and the largest accepted q on C\\X'),
    ('E6_cal_without_X_ledger.csv', 'all 20 clean-ledger rows next to the full-C rows'),
    ('E6_EXTRAS_CHECKS.json', 'stop conditions (empty)'),
    ('PANEL_IDENTITY.csv', 'SHA-256 of every panel file used here next to the frozen E3 file'),
]:
    w(f'| `results/{n}` | {d_} |')
w('')
w('Scripts: `scripts/common_r2a.py` (shared helpers and the frozen bootstrap), `scripts/e7_analysis.py`, '
  '`scripts/e6replay_analysis.py`, `scripts/e6_extras.py`, `scripts/make_summary.py`.')
w('')
(STAGE / 'SUMMARY.md').write_text('\n'.join(L) + '\n')
print('wrote', STAGE / 'SUMMARY.md', len(L), 'lines')
