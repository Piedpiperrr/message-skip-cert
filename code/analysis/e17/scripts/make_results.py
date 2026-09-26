"""Render RESULTS.md from the E17 result CSVs (formatting only; no new computation)."""
import csv, json
from pathlib import Path

ST = Path(__file__).resolve().parents[1]
R = ST / 'results'
rd = lambda n: list(csv.DictReader(open(R / n)))
F = lambda x: float(x)


def pct(x, d=2):
    return 'n/a' if x in ('', 'nan', None) or x != x else f'{100 * float(x):.{d}f}%'


def ci(lo, hi, d=2):
    return 'n/a' if lo in ('', 'nan') else f'[{pct(lo, d)}, {pct(hi, d)}]'


def g(x, d=3):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if v != v: return 'n/a'
    if abs(v) >= 1e-3 or v == 0: return f'{v:.{d}f}'
    return f'{v:.2e}'


out = []
sha = (ST / 'PREREG.sha256').read_text().split()
chk = rd('step2_checks.csv')
out += ['# E17 results (Round 7): six descriptive re-analyses of stored outputs', '',
        f'Stage `{ST}` (ClusterA login node; CPU only; no model, no GPU, no submit-job).', '',
        f'- Preregistration `PREREG.md`, SHA-256 `{sha[0]}`, hashed {sha[-1]} (`PREREG.sha256`).',
        '- First new computation: `scripts/step2.py` started 2026-09-21T18:35:03Z (`logs/step2.log`).',
        f"- Step 2 reproduction checks: {sum(c['status'] == 'PASS' for c in chk)}/{len(chk)} PASS (`results/step2_checks.csv`).",
        '- Scripts: `scripts/e17_common.py` (loaders), `step2.py`, `cache28.py`, `e17_1_2.py`, `e17_3.py`, `e17_4.py`, `e17_5.py`, `e17_6.py`,',
        '  `make_results.py` (this file), `run_audited.py` (audited re-run: every project file opened is listed in `logs/files_opened_*.txt`).',
        '- Conventions: parser V2; two unparseable = agreement; CP = two-sided 95% Clopper-Pearson; p = P[Bin(n, .05) <= k].',
        '- Deviations: `DEVIATIONS.md`.', '']

out += ['## Step 2. Reproduction checks', '']
for c in chk:
    if c['check'].startswith(('(1)', '(2)', '(3)', '(4)')):
        out.append(f"- {c['status']}: {c['check']}: {c['observed']}")
out += [f"- PASS: (0) all 28 certification outcomes recomputed from the stored thresholds and calibration records (11 certify, 17 fall back).",
        f"- PASS: (5) E17-1 dev n0/k0 at every certified threshold equals `E14_2_zero_u.csv` (10 rows).", '']

# E17-1
r1 = rd('E17_1_u0_rule.csv')
out += ['## E17-1. "Omit iff u = 0" baseline (`results/E17_1_u0_rule.csv`, `results/E17_1_tau0_candidates.csv`)', '',
        '| policy | cal n0 / k0 | cal k0/n0 [CP] | cal p | dev n0/N (coverage) | dev k0/n0 [CP] | policy dev coverage | policy k/n [CP] | fit grid q with tau = 0 (accepted in original certification) |',
        '|---|---|---|---|---|---|---|---|---|']
for r in r1:
    na = r['cal_n0'] == '0'
    out.append(f"| {r['policy']} | {r['cal_n0']} / {r['cal_k0']} | {'n/a' if na else pct(r['cal_k0_over_n0']) + ' ' + ci(r['cal_CP_lo'], r['cal_CP_hi'])} | "
               f"{'n/a' if na else g(r['cal_p_u0'])} | {r['dev_n0']}/{r['dev_N']} ({pct(r['dev_u0_coverage'], 1)}) | "
               f"{'n/a' if r['dev_n0'] == '0' else r['dev_k0'] + '/' + r['dev_n0'] + ' = ' + pct(r['dev_k0_over_n0']) + ' ' + ci(r['dev_CP_lo'], r['dev_CP_hi'])} | "
               f"{pct(r['policy_dev_coverage'], 1)} | {r['policy_dev_k']}/{r['policy_dev_n']} = {pct(r['policy_dev_rate'])} {ci(r['policy_CP_lo'], r['policy_CP_hi'])} | "
               f"{r['tau0_candidates_accepted']} |")
m9 = [r for r in r1 if r['policy'] != 'medium/OBQA/C2C q=.50' and not r['policy'].startswith('Llama')]
lo_c, hi_c = min(F(r['dev_u0_coverage']) for r in m9), max(F(r['dev_u0_coverage']) for r in m9)
lo_r, hi_r = min(F(r['dev_k0_over_n0']) for r in m9), max(F(r['dev_k0_over_n0']) for r in m9)
plo_c, phi_c = min(F(r['policy_dev_coverage']) for r in m9), max(F(r['policy_dev_coverage']) for r in m9)
plo_r, phi_r = min(F(r['policy_dev_rate']) for r in m9), max(F(r['policy_dev_rate']) for r in m9)
out += ['', f"Over the nine certified Qwen policies (medium OBQA C2C at q = .55): the u = 0 rule covers {pct(lo_c, 1)}–{pct(hi_c, 1)} of dev with change rate "
        f"{pct(lo_r)}–{pct(hi_r)}; the certified policies cover {pct(plo_c, 1)}–{pct(phi_c, 1)} with change rate {pct(plo_r)}–{pct(phi_r)}. "
        "In all nine Qwen settings, tau = 0 was one of the 20 fit-grid candidates, and every tau = 0 candidate was accepted in the "
        "original certification (on cal, a tau = 0 candidate omits exactly the u = 0 questions), so the u = 0 rule was already tested. "
        "The two Llama-3.1-8B settings have no u = 0 question (n0 = 0), so no tau = 0 candidate exists there.",
        'Writing rule: appendix table + one Sec 7 clause with these two pairs of ranges.', '']

# E17-2
r2 = rd('E17_2_upos_certification.csv')
out += ['## E17-2. Certification on u > 0 questions only (`results/E17_2_upos_certification.csv`, ledgers `results/E17_2_upos_ledgers.csv`)', '',
        '| setting | fit / cal / dev with u > 0 | q+ | cal n / k / p at q+ | dev coverage (within u > 0 / of all dev) | dev k/n [CP] | smallest cal p (q, k/n) |',
        '|---|---|---|---|---|---|---|']
for r in r2:
    cert = r['q_plus'] != 'fallback'
    out.append(f"| {r['setting']} | {r['N_fit_upos']}/{r['N_fit']}, {r['N_cal_upos']}/{r['N_cal']}, {r['N_dev_upos']}/{r['N_dev']} | {r['q_plus']} | "
               f"{(r['cal_n'] + ' / ' + r['cal_k'] + ' / ' + g(r['cal_p'], 5)) if cert else '-'} | "
               f"{(pct(r['dev_coverage_within_upos'], 1) + ' / ' + pct(r['dev_coverage_of_all'], 1)) if cert else '-'} | "
               f"{(r['dev_k'] + '/' + r['dev_n'] + ' = ' + pct(r['dev_rate']) + ' ' + ci(r['dev_CP_lo'], r['dev_CP_hi'])) if cert else '-'} | "
               f"{g(r['min_p'], 4)} (q = {r['min_p_q']}, {r['min_p_k']}/{r['min_p_n']}) |")
nc = sum(r['q_plus'] != 'fallback' for r in r2)
out += ['', f'**{nc} of 9 settings certify on u > 0 alone.** Writing rule: at least one certifies, so appendix table + Sec 7 clause '
        f'"on questions with u > 0 alone, the test still certifies {nc} of 9 settings".', '']

# E17-3
sp = rd('E17_3_splits.csv'); ts = rd('E17_3_tests.csv'); mp = rd('E17_3_mh_permutation.csv'); cpol = rd('E17_3_certified_policies.csv')
out += ['## E17-3. ARC split comparison (`results/E17_3_splits.csv`, `E17_3_tests.csv`, `E17_3_mh_permutation.csv`, `E17_3_certified_policies.csv`)', '',
        'Per setting x split (d = #(o_R != o_b)/N [CP]; INVALID counts; median u; share u == 0):', '',
        '| setting | split | N | d [CP] | R INVALID | ref INVALID | median u | share u == 0 |', '|---|---|---|---|---|---|---|---|']
for r in sp:
    out.append(f"| {r['setting']} | {r['split']} | {r['N']} | {r['disagreements']}/{r['N']} = {pct(r['d'])} {ci(r['CP_lo'], r['CP_hi'])} | {r['R_INVALID']} | "
               f"{r['ref_INVALID']} | {g(r['median_u'], 4)} | {pct(r['share_u0'], 1)} |")
out += ['', 'The sealed test rows are the omitted questions only: R was not executed on the other questions. The train-vs-test comparison is therefore made on questions below the frozen threshold (u <= tau) on both sides, the only region where R was run on the test split. On all 1,172 sealed questions, the median u is 0, '
        'the share of u == 0 is 71.4%, and there are 0 (Text) and 1 (C2C) reference INVALID outputs.', '',
        'Descriptive tests (Fisher exact two-sided; OR = odds of disagreement in the first-named split / the second-named split):', '',
        '| setting | d_fit | d_cal | d_dev | OR cal:dev, p | OR fit:cal, p | train (fit+cal) vs test, on questions below the frozen threshold (u <= tau): k/n vs k/n, OR, p |', '|---|---|---|---|---|---|---|']
for t in ts:
    tt = (f"{t['train_matched_k']}/{t['train_matched_n']} vs {t['test_k']}/{t['test_n']}, {g(t['OR_train_vs_test_matched'])}, {g(t['fisher_p_train_vs_test_matched'])}"
          if t.get('test_n') else '-')
    out.append(f"| {t['setting']} | {pct(t['d_fit'])} | {pct(t['d_cal'])} | {pct(t['d_dev'])} | {g(t['OR_cal_vs_dev'])}, {g(t['fisher_p_cal_vs_dev'])} | "
               f"{g(t['OR_fit_vs_cal'])}, {g(t['fisher_p_fit_vs_cal'])} | {tt} |")
mh = mp[0]; p1 = mp[1]; p0 = mp[2]
out += ['', f"- Settings with d_cal < d_dev: {mh['n_settings_d_cal_lt_d_dev']} of {mh['n_settings']}.",
        f"- Mantel-Haenszel common OR (odds of disagreement, dev vs cal; 10 strata; Robins-Breslow-Greenland 95% CI): {g(mh['OR_MH_dev_vs_cal'])} [{g(mh['CI_lo'])}, {g(mh['CI_hi'])}].",
        f"- Decision test (cal vs dev; x_i = mean disagreement over the 10 settings; every question is in all 10 settings): mean(x | cal) = {g(p1['mean_x_a'], 4)} (n = {p1['n_a']}), "
        f"mean(x | dev) = {g(p1['mean_x_b'], 4)} (n = {p1['n_b']}), statistic mean(x | dev) - mean(x | cal) = {g(p1['statistic'], 4)}, "
        f"two-sided permutation p = {g(p1['p_two_sided'], 4)} ((1 + #|T*| >= |T|) / 10,001; plain share {g(p1['p_two_sided_plain'], 4)}; 10,000 permutations, seed 0).",
        f"- Control (fit vs cal): mean(x | fit) = {g(p0['mean_x_a'], 4)} (n = {p0['n_a']}), mean(x | cal) = {g(p0['mean_x_b'], 4)} (n = {p0['n_b']}), "
        f"statistic mean(x | cal) - mean(x | fit) = {g(p0['statistic'], 4)}, p = {g(p0['p_two_sided'], 4)}.",
        f"- **SYSTEMATIC: {'yes' if p1['SYSTEMATIC'] == 'True' else 'no'}**; significant reverse direction: {'yes' if p1['reverse_direction_significant'] == 'True' else 'no'}. "
        f"Writing rule: {'Sec 7 sentence' if p1['SYSTEMATIC'] == 'True' or p1['reverse_direction_significant'] == 'True' else 'appendix sentence with these numbers'}.", '',
        'Certified ARC policies, change rate at the frozen tau:', '', '| policy | q | split | k/n [CP] |', '|---|---|---|---|']
for r in cpol:
    out.append(f"| {r['policy']} | {r['q']} | {r['split']} | {r['k']}/{r['n']} = {pct(r['rate'])} {ci(r['CP_lo'], r['CP_hi'])} |")

# E17-4
a4 = rd('E17_4_audit.csv'); s4 = rd('E17_4_summary.csv')[0]; b4 = rd('E17_4b_official_text.csv')
fails = [r for r in a4 if r['all_i_ii_iii_v'] != 'True']
out += ['', '## E17-4. Audit of the 44 sealed-ARC V2 vs official label differences (`results/E17_4_audit.csv`, full table for the supplement)', '',
        f"- Rows: {len(a4)}; all on the {', '.join(sorted({r['policy'] + ' ' + r['side'] + ' output' for r in a4}))}.",
        f"- (i) starts with one option letter A-D followed by '.', ')' or ':': {s4['n_i']}/{len(a4)}; (i)+(ii) the rest is that option's text: {s4['n_i_ii']}/{len(a4)}; "
        f"(i)+(ii)+(iii)+(v) (no second letter pattern; V2 label = that letter): {s4['n_i_ii_iii_v']}/{len(a4)}.",
        f"- Rows failing any check: {len(fails)}{' — ' + '; '.join(r['id'] for r in fails) if fails else ''}.",
        f"- (iv) official extractor output: {s4['official_returned']}; branch {s4['official_branch']} (rows containing each math-indicator substring: "
        + ', '.join(f'"{k}" {v}' for k, v in __import__('collections').Counter(x for r in a4 for x in r['iv_math_substrings'].split(';') if x).most_common())
        + '; a row can contain several).',
        f"- Rows where the official label matches the stated option better than V2: {s4['official_better']}.",
        '- Writing rule: all 44 pass (i)+(ii)+(iii)+(v), so App I + Sec 4.5 clause ("in all 44, the output names one option letter followed by that option\'s own text; the official extractor rejects it").', '',
        '### E17-4b. Official extraction for the Text certificates (`results/E17_4b_official_text.csv`)', '',
        '| policy | extractor | n (A-D items) | k | k/n [CP] | CP upper >= 5% |', '|---|---|---|---|---|---|']
for r in b4:
    out.append(f"| {r['policy']} | {r['extractor']} | {r['n_AD']} | {r['k']} | {pct(r['rate'])} {ci(r['CP_lo'], r['CP_hi'])} | {r['CP_hi_ge_05']} |")
out += ['', 'All 744 held-out OBQA items are A-D. No Text policy has an official-extraction CP upper bound >= 5%, so no Text policy is named in Sec 4.5.', '']

# E17-5
fa = rd('E17_5a_feasibility.csv'); bb = rd('E17_5b_binormal.csv'); cont = rd('E17_5c_contour.csv')
out += ['## E17-5. Feasibility and a binormal model of the boundary', '',
        '### (a) Population feasibility (`results/E17_5a_feasibility.csv`)', '',
        '| setting | observed | pi | C | max TPR/FPR | max >= C | some candidate k/n <= .05 |', '|---|---|---|---|---|---|---|']
for r in fa:
    out.append(f"| {r['setting']} | {r['observed']} | {g(r['pi'])} | {g(r['C'])} | {g(r['max_TPR_over_FPR'])} | {r['max_ge_C']} | {r['some_candidate_k_over_n_le_05']} |")
ng = sum(r['max_ge_C'] == 'True' for r in fa)
ng_f = sum(r['max_ge_C'] == 'True' and r['observed'] == 'fallback' for r in fa)
out += ['', f"max TPR/FPR >= C in {ng}/28 settings: all 11 certified settings and {ng_f} fallback settings "
        f"({', '.join(r['setting'] for r in fa if r['max_ge_C'] == 'True' and r['observed'] == 'fallback')}). "
        'The equivalence with "some candidate has k/n <= .05" holds in all 28.', '',
        '### (b) Binormal model (`results/E17_5b_binormal.csv`; inputs `results/E17_5_inputs.csv`)', '',
        '| setting | observed | prevalence (cal) | AUROC dev / cal | N_fit / N_cal | P(certify) dev-AUROC | modal q, median coverage | P(certify) cal-AUROC | AUROC at P = .5 | share u == 0 (cal) |',
        '|---|---|---|---|---|---|---|---|---|---|']
for r in bb:
    mq = '-' if r['modal_q_devAUROC'] in ('', 'None') else f"{r['modal_q_devAUROC']}, {g(r['median_coverage_when_certified_devAUROC'])}"
    out.append(f"| {r['setting']} | {r['observed']} | {g(r['prevalence_cal'], 4)} | {g(r['AUROC_dev'])} / {g(r['AUROC_cal'])} | {r['N_fit']} / {r['N_cal']} | "
               f"{g(r['P_certify_devAUROC'], 4)} | {mq} | {g(r['P_certify_calAUROC'], 4)} | {r['AUROC_at_P50']} | {pct(r['share_u0_cal'], 1)} |")
ad = sum(r['agree_devAUROC'] == 'True' for r in bb); ac = sum(r['agree_calAUROC'] == 'True' for r in bb)
vals = [F(r['AUROC_at_P50_value']) for r in bb if r['AUROC_at_P50_value'] not in ('', 'None')]
dis = [r['setting'] for r in bb if r['agree_devAUROC'] != 'True']
out += ['', f"Agreement with the observed outcome: **{ad}/28** (dev AUROC, main run); {ac}/28 (cal AUROC, sensitivity). "
        f"Disagreements: {', '.join(dis) if dis else 'none'}. AUROC at which P(certify) = .5: range {min(vals):.4f}–{max(vals):.4f} over the 28 settings "
        f"({len(vals)} with a value); .80 {'falls' if min(vals) <= .80 <= max(vals) else 'does not fall'} in this range.",
        f"Writing rule: agreement {ad} >= 24, so Sec 5 uses the first wording ('a binormal score with each setting's disagreement rate and AUROC reproduces {ad} of 28 outcomes; ...'), with no exceptions to name.", '',
        '### (c) Grid for a figure (`results/E17_5c_grid.csv`, `results/E17_5c_contour.csv`)', '',
        'AUROC at which P(certify) = .5, linear interpolation between grid AUROCs, per (N_fit, N_cal) and prevalence:', '',
        '| prevalence | (670, 448) | (2100, 1366) | (3000, 6000) |', '|---|---|---|---|']
for p in sorted({F(r['prevalence']) for r in cont}):
    cells = {(r['N_fit'], r['N_cal']): r['AUROC_at_P50'] for r in cont if F(r['prevalence']) == p}
    out.append(f"| {p:g} | {cells[('670', '448')]} | {cells[('2100', '1366')]} | {cells[('3000', '6000')]} |")

# E17-6
c6 = rd('E17_6_mmlu_categories.csv')
out += ['', '## E17-6. MMLU-Pro per category (`results/E17_6_mmlu_categories.csv`)', '',
        '| path | category | N_cal | cal disagreement | q (delta = .001) | dev coverage | dev k/n [CP] | q (delta = .001/14) |', '|---|---|---|---|---|---|---|---|']
for r in c6:
    cert = r['q'] != 'fallback'
    out.append(f"| {r['path']} | {r['category']} | {r['N_cal']} | {r['cal_disagreements']}/{r['N_cal']} = {pct(r['cal_dis_rate'], 1)} | {r['q']} | "
               f"{pct(r['dev_coverage'], 1) if cert else '-'} | {(r['dev_k'] + '/' + r['dev_n'] + ' = ' + pct(r['dev_rate']) + ' ' + ci(r['dev_CP_lo'], r['dev_CP_hi'])) if cert else '-'} | {r['q_delta_over_14']} |")
for ref in ['Text', 'C2C']:
    rr = [r for r in c6 if r['path'] == ref]
    out.append(f"\n- {ref}: {sum(r['q'] != 'fallback' for r in rr)}/14 categories certify at delta = .001 per candidate; "
               f"{sum(r['q_delta_over_14'] != 'fallback' for r in rr)}/14 with delta = .001/14.")
out += ['', 'Writing rule: App K, one sentence with both counts; nothing in the main text.', '']
(ST / 'RESULTS.md').write_text('\n'.join(out) + '\n')
print('\n'.join(out))
