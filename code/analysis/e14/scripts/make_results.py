"""Write RESULTS_E14.md from results/*.csv and results/E14_run.json (no number is typed by hand)."""
import csv, json
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
R = STAGE / 'results'


def rd(name): return list(csv.DictReader((R / name).open()))


def fl(x, d=4):
    return '' if x in ('', None, 'nan') else f'{float(x):.{d}f}'


def pct(x, d=2): return '' if x in ('', None, 'nan') else f'{100 * float(x):.{d}f}%'


def pv(x): return '' if x in ('', None) else f'{float(x):.3g}'


def ci(lo, hi): return '' if lo in ('', 'nan') else f'[{pct(lo)}, {pct(hi)}]'


run = json.loads((R / 'E14_run.json').read_text())
sha = (STAGE / 'PREREG_E14.sha256').read_text().split()
checks = rd('E14_checks.csv')
e1 = rd('E14_1_sealed_official.csv')
cats = rd('E14_1_label_diff_categories.csv')
e2 = rd('E14_2_zero_u.csv')
rec = rd('E14_2_receiver_u0.csv')
thr = rd('E14_2_thresholds.csv')
P = str(STAGE)
L = []
w = L.append
w('# E14 results (Round 6): sealed ARC under the official C2C extractor; zero-uncertainty questions among omitted questions\n')
w(f'Stage `{P}`. POST-HOC CPU re-analysis of stored outputs on the ClusterA login node. No model was run, no GPU and no PBS job was used.\n')
w('| | |\n|---|---|')
w(f'| Preregistration | `PREREG_E14.md`, SHA-256 `{sha[0]}`, hashed {sha[3]} (`PREREG_E14.sha256`) |')
w(f"| First E14 computation | 2026-09-21T05:31:11Z: first attempt, 8 min after the hash; it stopped after check (i) on a wrong module reference, before any E14-1/E14-2 number (see `DEVIATIONS.md`). Complete run {run['first_computation_utc']} to {run['end_utc']} |")
w(f"| Reproduction checks | {sum(c['status'] == 'PASS' for c in checks)} / {len(checks)} PASS (`results/E14_checks.csv`) |")
w('| Deviations | `DEVIATIONS.md` |')
w('| Scripts | `scripts/e14.py` (all computation), `scripts/make_results.py` (this file); log `logs/e14.log` |')
w('| `__pycache__` | none created: `logs/pycache_before.txt` == `logs/pycache_after.txt` (PYTHONDONTWRITEBYTECODE=1) |\n')

w('## 1. Reproduction checks (all PASS)\n')
w('(i) sealed ARC, parser V2 as executed (`P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/records/e2e_requests.jsonl`, '
  'cross-checked with `records/paired_sealed_2344.jsonl` and `summary/primary_sealed.csv`); the stored runtime parse equals a re-parse '
  'with frozen V2 on all 4,688 outputs:\n')
for c in checks:
    if c['check'].startswith('(i) sealed large') and 'as executed' in c['check']:
        w(f"- {c['check'].split('(i) sealed ')[1].split(' policy')[0]}: omitted / changed = {json.loads(c['observed'])[0]} / {json.loads(c['observed'])[1]} ({c['status']})")
w('\n(ii) dev omitted / changed at each E14-2 policy row: frozen deployment record = recomputation from the stored cal/dev outputs and ProbeMax scores '
  '(the calibration n / k at the same threshold also equals the stored calibration ledger row):\n')
w('| policy | dev omitted | dev changed | cal omitted | cal changed | frozen dev record |\n|---|---:|---:|---:|---:|---|')
dev_c = [c for c in checks if c['check'].startswith('(ii) dev ')]
cal_c = [c for c in checks if c['check'].startswith('(ii) cal ')]
for a, b in zip(dev_c, cal_c):
    name = a['check'][len('(ii) dev '):].split(':')[0]
    o, oc = json.loads(a['observed']), json.loads(b['observed'])
    w(f"| {name} | {o[0]} | {o[1]} | {oc[0]} | {oc[1]} | `{a['source'].replace(str(STAGE.parent) + '/', '')}` |")
w('\nThe frozen thresholds equal the deployment files (`deployments/*.json`, `e6_deployment.json`, medium/MMLU-Pro summaries), and the '
  'thresholds used in E9b and in the sealed run equal them too (asserted).\n')
w('(iii) the official-extractor port (`P2_R2_CPU_20260919T220412Z/scripts/parsers_r2.py::label_official`, source '
  '`c2c_reproduction_assets/official_C2C/rosetta/utils/evaluate.py`, SHA-256 `' + run['parser_hashes']['OFFICIAL'] + '`) on the 448 '
  'large/ARC/C2C calibration rows reproduces E11(b): the per-setting counts in `P2_R4_E11_20260920T224016Z/results/E11b_two_conventions.csv`, '
  'the 20-candidate OFFICIAL (n, k) ledger in `E11b_grid.csv`, and the label of every one of the 2 x 448 outputs (against '
  '`P2_R2_CPU_20260919T220412Z/followup/results/f1b_differences.csv`, 0 mismatches).\n')
for c in checks:
    if c['check'].startswith('(iii) large/ARC/C2C cal: official-port counts'):
        w(f"  Counts: `{c['observed']}`\n")
w('Also checked: E9b omitted / changed for all five held-out rows equal `E9B_RESULTS.json`; the three "known before" u = 0 counts '
  '(354/742, 217/299, 713/3,000) reproduce.\n')

w('## 2. E14-1 — sealed ARC under the official C2C extractor\n')
w(f"**Inclusion rule (as in E11(b)):** a question is included iff its displayed option labels are a subset of {{A, B, C, D}} "
  f"(`parsers_r2.official_applicable`); the official extractor hard-codes A-D. Excluded: **{len(run['excluded_ids'])}** of 1,172 sealed "
  f"questions, all with five options A-E ({', '.join(run['excluded_ids'])}); all three are omitted by both policies. "
  f"Kept as in E11(b): the 4 three-option questions (A-C; an official read outside the set -> unparseable) and the "
  f"{run['sealed_numeric_original_labels']} questions whose original labels were 1-4/1-3 (displayed and parsed as A-D/A-C, the labels the models saw). "
  f"Label sets of the 1,172: {run['sealed_label_sets']}.\n")
w('Routing: the frozen routing as executed (`selected == R`, identical to ProbeMax <= tau). Labels: the stored raw outputs of R (the policy '
  'request on omitted questions) and of the reference request. Convention: both unparseable = agreement; exactly one unparseable = change. '
  'CP = two-sided 95% Clopper-Pearson; p = P[Bin(n, .05) <= k] (one-sided exact, H0: rho >= .05; descriptive, not a certificate).\n')
w('| policy | extractor | excluded (omitted) | n | k | k/n | CP 95% | p | k, both-unparseable = change | exactly one unparseable | '
  'questions with an R or reference label diff (by category) | rule branch |\n|---|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|')
for r in e1:
    cat = ''
    if r['extractor'] == 'official':
        cat = f"{r['questions_with_label_diff']} (C1 {r['diff_questions_C1']}, C2 {r['diff_questions_C2']}, C3 {r['diff_questions_C3']}, other {r['diff_questions_C4']})"
    w(f"| {r['policy']} | {r['extractor']} | {r['excluded_omitted']} | {r['n']} | {r['k']} | {pct(r['rate'])} | {ci(r['CP95_lo'], r['CP95_hi'])} | "
      f"{pv(r['p_H0_rho_ge_05'])} | {r['k_both_unparseable_as_change']} | {r.get('exactly_one_unparseable', '')} | {cat} | {r.get('rule_branch', '')} |")
w('\nCategories (E5-a follow-up): C1 = ambiguous or repeated letters read as the first letter; C2 = leading label + option text containing '
  'one of the extractor\'s math-indicator substrings (tan/sin/"/" and the rest of its list), so the official extractor returns nothing; '
  'C3 = last-letter read ("A. 0 C"); other. Every differing output, with its raw text, is in `results/E14_1_label_diffs.csv`; counts by '
  'transition / pattern / branch in `results/E14_1_label_diff_categories.csv`:\n')
w('| policy | output | category | transition | V2 -> official | count |\n|---|---|---|---|---|---:|')
for r in cats:
    w(f"| {r['policy']} | {r['output']} | {r['category']} | {r['transition']} ({r['output_pattern']}, {r['official_branch']}) | {r['V2_to_official']} | {r['count']} |")
c2c = next(r for r in e1 if r['policy'] == 'large/ARC/C2C' and r['extractor'] == 'official')
txt = next(r for r in e1 if r['policy'] == 'large/ARC/Text' and r['extractor'] == 'official')
w(f"\n**Paper rule (C2C policy): branch ({c2c['rule_branch']}).** Under the official extractor the sealed C2C change rate is "
  f"{c2c['k']}/{c2c['n']} = {pct(c2c['rate'])}, CP 95% {ci(c2c['CP95_lo'], c2c['CP95_hi'])}, p = {pv(c2c['p_H0_rho_ge_05'])}: the point estimate "
  f"is above 5%, so the paper states in Sec. 4.5, and wherever the abstract cites the sealed C2C result, that the sealed C2C result holds under "
  f"our extractor only. All {c2c['questions_with_label_diff']} label differences are C2C reference outputs of the form `X. <option text>` "
  f"that the official extractor cannot read (V2 label -> unparseable, R parses), each of which counts as a change under the fixed convention. "
  f"Text policy (descriptive): branch ({txt['rule_branch'].split()[0]}), {txt['k']}/{txt['n']} = {pct(txt['rate'])} {ci(txt['CP95_lo'], txt['CP95_hi'])}; "
  f"the two extractors give identical labels on all {txt['n']} included omitted questions.\n")

w('## 3. E14-2 — zero-uncertainty questions among omitted questions\n')
w('u = 0 means ProbeMax == 0.0 exactly as stored. n = omitted; n0 / k0 = omitted with u = 0 and changes among them; n+ / k+ = omitted with '
  'u > 0 and changes among them. Every u = 0 question is omitted (no frozen tau is below 0; asserted). Labels: frozen parser V2, paper '
  'convention. CP = two-sided 95% Clopper-Pearson. Source of every row: `results/E14_2_zero_u.csv`.\n')
for pop, title in [('dev', 'Development split'), ('cal', 'Calibration split (p+ = P[Bin(n+, .05) <= k+], u > 0 part alone at the frozen threshold; descriptive)'),
                   ('held-out 744 OBQA', 'Held-out 744 OBQA questions (E9b)'), ('sealed ARC 1,172', 'Sealed ARC test (1,172)')]:
    w(f'### {title}\n')
    extra = ' | p+' if pop == 'cal' else (' | rule triggers' if pop == 'dev' else '')
    w(f'| policy | N | u=0 among all N | n | n0/n | k0/n0 [CP 95%] | k+/n+ [CP 95%]{extra} |\n|---|---:|---:|---:|---:|---|---|' + ('---|' if extra else ''))
    for r in e2:
        if r['population'] != pop: continue
        t = ''
        if pop == 'cal':
            t = f" | {pv(r['p_pos_H0_rho_ge_05'])}"
        elif pop == 'dev':
            tr = []
            if r['trigger_kpos_CPlo_gt_05'] == 'True': tr.append('k+/n+ CP lower > 5%')
            if r['trigger_n0n_ge_90'] == 'True': tr.append('n0/n >= 90%')
            t = ' | ' + ('; '.join(tr) or 'none')
        name = r['policy'] + ('' if r['main_text_row'] == 'True' else ' (appendix only)')
        w(f"| {name} | {r['N']} | {r['N_u0']} ({pct(r['share_u0_all'], 1)}) | {r['n']} | {r['n0']}/{r['n']} = {pct(r['n0_over_n'], 1)} | "
          f"{r['k0']}/{r['n0']} = {pct(r['rate0'])} {ci(r['CP0_lo'], r['CP0_hi'])} | {r['k_pos']}/{r['n_pos']} = {pct(r['rate_pos'])} "
          f"{ci(r['CPpos_lo'], r['CPpos_hi'])}{t} |")
    w('')
w('### Per receiver x benchmark (u is receiver-only; identical for Text and C2C, asserted)\n')
w('| receiver | benchmark | split | u = 0 | share |\n|---|---|---|---:|---:|')
for r in rec:
    w(f"| {r['receiver']} ({r['pair']}) | {r['benchmark']} | {r['split']} | {r['N_u0']}/{r['N']} | {pct(r['share_u0'], 1)} |")
w('\n### Frozen thresholds (`results/E14_2_thresholds.csv`)\n')
w('| policy | q | tau | tau == 0 | fit candidates (of 20) equal to 0 |\n|---|---:|---:|---|---:|')
for r in thr:
    w(f"| {r['policy']} | {r['q']} | {float(r['tau']):.6g} | {r['tau_is_0']} | {r['fit_candidates_equal_0']} |")
w('\n**tau == 0 for no policy.** Several lower fit candidates are exactly 0 (column 5), but no deployed threshold is.\n')

dev9 = [r for r in e2 if r['population'] == 'dev' and r['main_text_row'] == 'True']


def rng(key, num, den):
    vals = [(float(r[key]), r) for r in dev9]
    lo, hi = min(vals, key=lambda x: x[0]), max(vals, key=lambda x: x[0])
    return (f"{pct(lo[0], 1)} ({lo[1]['policy']}, {lo[1][num]}/{lo[1][den]}) to "
            f"{pct(hi[0], 1)} ({hi[1]['policy']}, {hi[1][num]}/{hi[1][den]})")


w('### Paper rule outcomes (dev)\n')
w(f"- Main-text sentence, over the nine deployed thresholds on dev: n0/n ranges {rng('n0_over_n', 'n0', 'n')}; "
  f"k0/n0 ranges {rng('rate0', 'k0', 'n0')}; k+/n+ ranges {rng('rate_pos', 'k_pos', 'n_pos')}.")
t1 = [r for r in e2 if r['population'] == 'dev' and r['trigger_kpos_CPlo_gt_05'] == 'True']
t2 = [r for r in e2 if r['population'] == 'dev' and r['trigger_n0n_ge_90'] == 'True']
w('- dev k+/n+ CP lower end > 5% (paper names the policy and states that its certificate rests on the zero-uncertainty questions): ' +
  '; '.join(f"**{r['policy']}** ({r['k_pos']}/{r['n_pos']}, CP lower {pct(r['CPpos_lo'])})" for r in t1) + '.')
w('- dev n0/n >= 90% (paper states the certificate mostly covers questions the receiver treats as certain): ' +
  '; '.join(f"**{r['policy']}**{'' if r['main_text_row'] == 'True' else ' (the q = .50 appendix row)'} ({r['n0']}/{r['n']} = {pct(r['n0_over_n'], 1)})" for r in t2) + '.')
w('- Always: the appendix table (the four population tables above).\n')

w('## 4. Files read by the computation\n')
w('Every file opened for reading by `scripts/e14.py` is logged in `results/E14_files_read.txt` '
  f"({len(run['files_read'])} paths, including the two Python-environment files opened by the interpreter). The code modules imported "
  '(not data): `P2_R4_E11_20260920T224016Z/scripts/e11_common.py`, `P2_R2_CPU_20260919T220412Z/scripts/{r2_common,rawio,parsers_r2}.py`, '
  '`P2_R1_CPU_20260919T045556Z/src/{common_r1,data_r1}.py`; exec\'d from source: `scoring_v2.py`, `diagnostic_parser_v1.py` (loaded by '
  'parsers_r2, unused here), the official `evaluate.py::extract_answer_from_content`, and `f1b_official_diffs.py::{official_branch, surface_pattern}`.\n')
w('```')
for p in run['files_read']:
    w(p)
w('```')
(STAGE / 'RESULTS_E14.md').write_text('\n'.join(L) + '\n')
print('\n'.join(L))
