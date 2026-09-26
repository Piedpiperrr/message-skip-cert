"""Build SUMMARY.md from the result CSVs (no numbers are re-derived here)."""
from r2_common import *

S = STAGE / 'SUMMARY.md'
PRE_SHA = 'b2cf79db674416b0e8bd6ad0b4b9859495ac5e1889a1009bcf8fdc4ad79e26d8'
PRE_UTC = '2026-09-19T22:04:21Z'
R = lambda n: csvread(RES / n)
out = []
w = out.append


def table(header, rows):
    w('| ' + ' | '.join(header) + ' |')
    w('|' + '|'.join(['---'] * len(header)) + '|')
    for r in rows:
        w('| ' + ' | '.join(str(x) for x in r) + ' |')
    w('')


w('# P2_R2_CPU_20260919T220412Z — E5 re-analysis (CPU, saved records only)')
w('')
w(f'**{LABEL}.** Stage folder: `{STAGE}`. Scripts: `scripts/`; tables: `results/*.csv`.')
w('No existing file was modified; no model was run, no job submitted, no GPU used.')
w('')
w('## Step 0 — pre-registration (written before any computation)')
w('')
w(f'- `PREREG_R2_E5.md` (verbatim copy of the PRE-REGISTERED RULES block)')
w(f'- SHA-256: `{PRE_SHA}`')
w(f'- Recorded (UTC): **{PRE_UTC}** — before any number below was computed.')
w('')
w('Conventions: q = 0 means fallback (always run the reference). All tests are '
  'P[Bin(n, .05) <= k] <= .001 at 20 grid points, deploy = largest accepted q. '
  '"Frozen fit thresholds" are the stored ones; INVALID is a label and counts as a disagreement against a valid label.')
w('')

# ---------------- E5-a
w('## E5-a Parser exposure')
w('')
ex = R('e5a_exposed_ids.csv')
mem = R('e5a_review_split_membership.csv')
w(f'**X (`results/e5a_exposed_ids.csv`): {len(ex)} distinct calibration questions** '
  f"({sum(1 for r in ex if r['benchmark'] == 'OBQA')} OBQA, {sum(1 for r in ex if r['benchmark'] == 'ARC')} ARC, 0 MMLU-Pro). "
  'Counted the way the A8 audit counted them — per (pair, benchmark) — the same set is '
  '**355** reviews: large/OBQA 30, small/OBQA 186, large/ARC 26, small/ARC 113; 341 distinct questions because '
  'some were reviewed for both pairs.')
w('')
w('**Selection rule: NOT random — selected by output content.** A record entered the parser-development review set iff the '
  'saved run-time parser and the D1 diagnostic parser disagreed on answer/validity/correctness, or the D1 parse was '
  'flagged ambiguous (plus one named single case). Source: '
  '`P2_SCORE_SENSITIVITY_20260912T055929Z/analyze_sensitivity.py` lines 136-141 and `case_review.jsonl`. '
  'Because selection is content-based, X is enriched for parse-hard outputs; the disagreement rates below differ '
  'sharply between X and C \\ X and must be reported as such.')
w('')
w('Where the reviewed questions landed (all were train-split rows at review time; no split existed yet):')
w('')
table(['benchmark', 'reviewed questions', 'in calibration', 'in fit', 'in development'],
      [[r['benchmark'], r['reviewed_questions_total'], r['in_calibration'], r['in_fit'], r['in_development']] for r in mem])
w('MMLU-Pro: **no MMLU-Pro question was reviewed** during parser development — the V2 parser was frozen '
  '2026-09-12T19:19:38Z and the first MMLU-Pro output was produced 2026-09-16T15:27Z, so no MMLU-Pro output existed. '
  '|C ∩ X| = 0 for both MMLU-Pro settings and for X2-OLMo/MMLU-Pro.')
w('')
w('### The 20 tests on C \\ X with the frozen fit thresholds (`results/e5a_clean_tests.csv`, full grid in `results/e5a_clean_ledger_all_q.csv`)')
w('')
cl = R('e5a_clean_tests.csv')
table(['setting', 'N_cal', 'cal ∩ X', 'N clean', 'orig q', 'clean n/k at orig q', 'clean p', 'orig q accepted on C\\X?', 'largest clean accepted q'],
      [[r['setting'], r['N_cal'], r['exposed_in_cal'], r['N_clean'], r['orig_q'],
        f"{r['clean_n']}/{r['clean_k']}" if r['clean_n'] else '—',
        r['clean_p'] or '—', r['orig_q_accepted_on_clean'], r['largest_clean_accepted_q']] for r in cl])
w('**Outcome.** 7 of the 8 deployed q values survive. **medium/OBQA/C2C is NOT certified without the exposed '
  'questions**: at its deployed q = 0.55 the clean calibration set gives n/k = 640/18, p = 4.40e-03 > 1e-3. Its largest '
  'clean-accepted q is 0.50. All 13 originally-fallback settings remain fallback on C \\ X (no new passes to report), '
  'and both MMLU-Pro settings are untouched (|C ∩ X| = 0).')
w('')
dv = R('e5a_dev_at_clean_q.csv')
w('Development recomputed at the largest clean-accepted q, as pre-registered (`results/e5a_dev_at_clean_q.csv`):')
w('')
table(['setting', 'q', 'dev coverage %', 'changed/omitted', 'note'],
      [[r['setting'], r['q'], r['coverage_pct'], f"{r['changed']}/{r['omitted']}", r['note']] for r in dv])
w('### Disagreement rate in X ∩ C vs C \\ X (`results/e5a_disagreement_X_vs_clean.csv`)')
w('')
dg = R('e5a_disagreement_X_vs_clean.csv')
table(['setting', 'X ∩ C', 'rate', 'C \\ X', 'rate', 'full C rate'],
      [[r['setting'], f"{r['dis_X']}/{r['n_X']}" if r['n_X'] != '0' else '—', r['rate_X'] or '—',
        f"{r['dis_clean']}/{r['n_clean']}", r['rate_clean'], r['rate_full']] for r in dg])
w('The exposed questions disagree far more often than the rest (for example small/OBQA/Text .726 vs .386, '
  'X1-Llama/ARC/C2C .827 vs .518), exactly as expected from content-based selection. Removing X therefore *lowers* '
  'the measured risk almost everywhere; medium/OBQA/C2C still loses its threshold because it also loses calibration mass.')
w('')
w('### Independent-parser check (`results/e5a_independent_parser.csv`, grid in `results/e5a_independent_parser_grid.csv`)')
w('')
ip = R('e5a_independent_parser.csv')
ps = R('e5a_parser_sources.csv')
w('Parsers re-run on the saved raw calibration outputs of R and each reference:')
for r in ps:
    w(f"- **{r['parser']}**: `{r['path']}` (sha256 `{r['sha256'][:16]}…`)")
w('- **OFFICIAL** is the official C2C evaluator\'s `extract_answer_from_content`, executed from the official source; it '
  'hard-codes the option set A-D, so it is **not applicable to MMLU-Pro** (up to 10 options) — reported as n/a rather than forced.')
w('- **D1** is the pre-V2 parser version in the repo history (frozen 2026-09-12T06:02:33Z, before V2 at 19:19:38Z).')
w('- Validation: on the X1 C2C calibration rows the run records store the official evaluator\'s own `official_pred`; '
  'our re-execution matches it on **1366/1366 OBQA and 448/448 ARC** rows (`results/e5a_official_pred_crosscheck.csv`).')
w('')
w('**D1 vs V2: zero differences in d_b on every one of the 21 calibration sets.** The pre-V2 parser would have produced '
  'the identical disagreement labels, so no deployed q depends on the V2 revision.')
w('')
w('Official-evaluator labels (differences are counted as rows whose disagreement label d_b changes):')
w('')
table(['setting', 'o_R diff', 'o_ref diff', 'd_b diff (in X / in C\\X)', 'n/k at orig q', 'p', 'orig q accepted?', 'largest accepted q'],
      [[r['setting'], r['OFFICIAL_o_R_diff'], r['OFFICIAL_o_ref_diff'],
        f"{r['OFFICIAL_d_diff_total']} ({r['OFFICIAL_d_diff_in_X']} / {r['OFFICIAL_d_diff_in_clean']})",
        f"{r['OFFICIAL_n_at_orig_q']}/{r['OFFICIAL_k_at_orig_q']}" if r['OFFICIAL_n_at_orig_q'] else '—',
        r['OFFICIAL_p_at_orig_q'] or '—', r['OFFICIAL_orig_q_accepted'], r['OFFICIAL_largest_accepted_q']] for r in ip])
w('**Two deployed thresholds do not survive the official parser**: large/OBQA/C2C (39/1064 changed, p = 2.31e-02; '
  'largest accepted q 0.70) and large/ARC/C2C (27/404, p = 0.947; **fallback**). Both large/Text settings keep their q '
  '(large/ARC/Text has zero label differences), the medium C2C settings keep theirs, and the 13 fallbacks stay fallback. '
  'For the large pair every official-vs-V2 '
  'label difference lies inside X (21 of 21 for both C2C settings), i.e. exactly on the reviewed questions.')
w('')

# ---------------- E5-b
w('## E5-b Re-split stability (seeds 1..200)')
w('')
s0 = R('e5b_seed0_check.csv')
w('Re-splits redraw fit/calibration from fit ∪ calibration with the frozen rule, sizes and grouping; development is '
  'untouched; all settings of a benchmark share the re-splits. OBQA/ARC: sorted representatives, `random.Random(seed).shuffle`, '
  'first 2100 (OBQA) / 670 (ARC) to fit. MMLU-Pro: the frozen category-quota + SHA-256 ordering rule of `build_candidates.py`, '
  'reseeded by its seed string. **Seed 0 reproduces the frozen split exactly for all three benchmarks** '
  f"({', '.join(r['benchmark'] + '=' + r['seed0_reproduces_frozen_split'] for r in s0)}; `results/e5b_seed0_check.csv`).")
w('Saved reference outputs exist on the fit rows of all 21 settings, so no setting was skipped.')
w('')
sb = R('e5b_resplit_stability.csv')
table(['setting', 'orig outcome', 'cert. rate', 'match rate', 'stability', 'median q [IQR]', 'median dev cov %', 'median dev changed/omitted', 'needed m (m·N_cal/n)'],
      [[r['setting'], r['orig_outcome'], r['cert_rate'], r['match_rate'], r['stable'],
        (r['median_q'] + ' ' + r['IQR_q']) if r['median_q'] else '—',
        r['median_dev_coverage_pct'] or '—',
        (r['median_dev_changed'] + '/' + r['median_dev_omitted']) if r['median_dev_changed'] else '—',
        f"{r['needed_m']}" + (f" ({r['needed_m_scaled_to_N_cal']})" if r['needed_m_scaled_to_N_cal'] else '')] for r in sb])
w('Per-seed detail: `results/e5b_resplit_per_seed.csv`. Needed-m columns use the grid point with the smallest ORIGINAL '
  'p-value, r = k/n there, the smallest m with BinomCDF(floor(r·m); m, .05) <= .001, and m·N_cal/n.')
w('')
w('**Every setting is stable (match rate >= .80).** All 8 originally deploying settings certify in >= 96% of re-splits '
  '(7 at 100%, medium/ARC/C2C at 96.0%); all 13 fallbacks fall back in 100% of re-splits. The medium-pair statement '
  '**"only C2C can be omitted" holds as a property of the pair**: medium C2C is stable-deploy on both OBQA (1.000) and '
  'ARC (0.960) and medium Text is stable-fallback on both (1.000). Fallbacks should still be worded '
  '"not certified at alpha = .05 with n calibration questions".')
w('')

# ---------------- E5-c
w('## E5-c Null control (7 development populations, INVALID = incorrect)')
w('')
nc = R('e5c_null_control.csv')
meta = R('e5c_meta.csv')[0]
table(['population', 'N', 'R', 'oracle{R,T,C}', 'gain over R (q / pp)', 'oracle{R,V1,V2}', 'gain over R (q / pp)',
       'matched-null gain mean [2.5, 97.5]', 'rho'],
      [[r['population'], r['N'], r['R_correct'], r['oracle_R_Text_C2C'],
        f"+{r['gain_over_R_questions']} / +{r['gain_over_R_pp']}", r['oracle_R_V1_V2'],
        f"+{r['gain_R_V1_V2_questions']} / +{r['gain_R_V1_V2_pp']}",
        f"{r['matched_null_gain_mean']} [{r['matched_null_gain_p2_5']}, {r['matched_null_gain_p97_5']}]", r['rho']] for r in nc])
w(f"Rate-matched null: {meta['repetitions']} repetitions, {meta['rng']}; m_Text / m_C2C drawn without replacement from the "
  'questions with a non-empty P(x). No population was under-matched '
  f"(eligible pool vs m: {'; '.join(r['population'] + ' ' + r['n_eligible_P_nonempty'] + ' vs ' + r['m_Text'] + '/' + r['m_C2C'] for r in nc)}).")
w('')
w(f"**rho >= 0.8 in {meta['n_pops_rho_ge_0_8']} of 7 populations; median rho = {meta['median_rho']}.** The pre-registered "
  'condition (>= 4 of 7) is NOT met, so contribution 1 and the abstract must be rewritten to '
  f"\"rate-matched content-free perturbations reproduce {float(meta['median_rho']) * 100:.1f}% (median) of the headroom\" "
  'and the "six of seven" statement removed. The main-text null comparison uses gain over R and absolute counts, as pre-registered.')
w('')
w('Change decomposition vs R (`results/e5c_change_decomposition.csv`): changed = corrective + harmful + neutral(both wrong).')
w('')
cd = R('e5c_change_decomposition.csv')
table(['population', 'N', 'action', 'correct', 'changed', 'corrective', 'harmful', 'neutral (both wrong)'],
      [[r['population'], r['N'], r['action'], r['correct'], r['changed'], r['corrective'], r['harmful'], r['neutral_both_wrong']] for r in cd])

# ---------------- E5-e
w('## E5-e Cross-family INVALID (7 settings)')
w('')
sp = R('e5e_disagreement_split.csv')
w('Disagreement decomposition; two INVALIDs count as agreement (`results/e5e_disagreement_split.csv`):')
w('')
table(['setting', 'split', 'N', 'disagreements', 'both valid & different', 'only R INVALID', 'only ref INVALID', 'R INVALID %', 'ref INVALID %'],
      [[r['setting'], r['split'], r['N'], r['disagreements'], r['both_valid_and_different'], r['only_R_INVALID'],
        r['only_reference_INVALID'], r['R_INVALID_pct'], r['ref_INVALID_pct']] for r in sp])
vo = R('e5e_valid_only_diagnostic.csv')
w('Valid-only diagnostic — frozen fit thresholds, the same 20 tests restricted to questions where **both** outputs parse. '
  '**Descriptive only; not deployable** (the filter uses the reference output, which is what omission avoids). '
  'Grid in `results/e5e_valid_only_grid.csv`.')
w('')
table(['setting', 'cal valid-only / N', 'valid-only deployed q', 'dev valid-only / N', 'dev disagreement (valid-only vs all)', 'valid-only AUROC'],
      [[r['setting'], f"{r['N_cal_valid_only']}/{r['N_cal']}", r['valid_only_deployed_q'],
        f"{r['N_dev_valid_only']}/{r['N_dev']}", f"{r['dev_disagreement_valid_only']} vs {r['dev_disagreement_all']}",
        r['valid_only_AUROC']] for r in vo])
w('**All three OLMo benchmarks certify on valid-only questions** (OBQA q = 0.45, ARC q = 0.40, MMLU-Pro q = 0.05), so by '
  'the pre-registered rule the paper states that the OLMo fallback is **driven by answer format** and withdraws the size '
  'statement for those benchmarks. The four Llama (X1) settings still fall back valid-only, so for them the paper keeps '
  '"not accuracy or size alone" and reports the INVALID share.')
w('')

# ---------------- facts
w('## Checks')
w('')
vc = R('validation_checks.csv')
w(f"- **All {sum(1 for r in vc if r['n_k_reproduced'] == 'True')}/{len(vc)} settings reproduce the frozen calibration ledgers exactly** "
  '(20 grid points each, n and k, frozen thresholds on the full calibration set) before any subset was removed: '
  '`results/validation_checks.csv`.')
w('- Seed 0 of the E5-b re-split rule reproduces the frozen fit/calibration split for OBQA, ARC and MMLU-Pro.')
w('- E5-c oracle counts reproduce `P2_R1_EXP_20260919T050555Z/results/e4_null_controls.csv` for all 7 populations '
  '(both oracle{R,Text,C2C} and oracle{R,V1,V2}).')
w('- The official-extractor re-implementation matches the evaluator-produced `official_pred` on all 1,814 X1 C2C '
  'calibration rows.')
w('')
w('## Facts F1-F4 (`results/facts_F1_F4.csv`)')
w('')
for r in R('facts_F1_F4.csv'):
    w(f"**{r['fact']}. {r['question']}**")
    w('')
    w(r['answer'])
    w('')
    w(f"Sources: {r['sources']}")
    w('')

w('## Files')
w('')
for p in sorted(RES.glob('*.csv')):
    w(f'- `results/{p.name}`')
w('')
w('Scripts: ' + ', '.join(f'`scripts/{p.name}`' for p in sorted((STAGE / "scripts").glob("*.py"))) + '.')
S.write_text('\n'.join(out) + '\n')
print('wrote', S, len(out), 'lines')
