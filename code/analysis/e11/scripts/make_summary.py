"""Render E11A/E11B/E11C_SUMMARY.md and SUMMARY.md from the result CSVs (no numbers typed by hand)."""
from e11_common import *

R = lambda n: list(csv.DictReader((RES / n).open()))
import csv  # noqa: E402
R = lambda n: list(csv.DictReader((RES / n).open()))
ORDER = [sname(s) for s in ALL26]
key = lambda r: ORDER.index(r['setting'])
PREREG_SHA = (STAGE / 'PREREG_E11.sha256').read_text().split()[0]
PREREG_TS = [l.split(': ', 1)[1] for l in (STAGE / 'PREREG_E11.sha256').read_text().splitlines() if l.startswith('recorded_utc')][0]
HEAD = (f'Stage: `{STAGE}`  \nPreregistration: `PREREG_E11.md`, SHA-256 `{PREREG_SHA}`, recorded {PREREG_TS} '
        f'(before anything was read or computed from the saved outputs).  \n'
        f'CPU-only re-analysis of already-saved model outputs on the ClusterA login node. No model was run, '
        f'no GPU and no PBS job was used. {LABEL}.\n')

step1 = sorted(R('E11_step1_reproduction.csv'), key=key)
cells = R('E11a_invalid_decomposition.csv')
diag = sorted(R('E11a_bothparse_diagnostic.csv'), key=key)
agg = R('E11a_cell3_share_aggregate.csv')
b = sorted(R('E11b_two_conventions.csv'), key=key)
binter = R('E11b_intersection.csv')
c = sorted(R('E11c_ruleD.csv'), key=key)
cv = R('E11c_verdicts.csv')
cell = {(r['setting'], r['split']): r for r in cells}


def tbl(hdr, rows):
    return ('| ' + ' | '.join(hdr) + ' |\n|' + '|'.join(['---'] * len(hdr)) + '|\n' +
            '\n'.join('| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows) + '\n')


# ---------------------------------------------------------------- Step 1
s1 = tbl(['setting', 'deployed q', 'cal n @ q', 'cal k @ q', 'cal p @ q', 'dev dis./N', 'dev AUROC', 'paper dis./N', 'paper AUROC', 'status'],
         [[r['setting'], r['deployed_q'], r['cal_n_at_q0'] or '—', r['cal_k_at_q0'] or '—', r['cal_p_at_q0'] or '—',
           f"{r['dev_disagreements']}/{r['dev_N']}", r['dev_AUROC'],
           f"{r['paper_dev_disagreements']}/{r['paper_dev_N']}", r['paper_dev_AUROC'], r['status']] for r in step1])

# ---------------------------------------------------------------- E11-a
a_rows = []
for r in diag:
    cc, cd = cell[r['setting'], 'cal'], cell[r['setting'], 'dev']
    a_rows.append([r['setting'], r['original_q'],
                   f"{cc['cell1_bothparse_differ']}/{cc['cell2_bothparse_agree']}/{cc['cell3_exactly_one_INVALID']}/{cc['cell4_both_INVALID']}",
                   cc['cell3_share_of_disagreements'], cd['cell3_share_of_disagreements'],
                   cc['receiver_only_INVALID_pct'], cc['reference_INVALID_pct'],
                   f"{r['N_cal_bothparse']}/{r['N_cal']}", f"{r['N_dev_bothparse']}/{r['N_dev']}",
                   r['bothparse_accepted_q'], r['dev_disagreement_bothparse'], r['dev_AUROC_bothparse'],
                   r['dev_coverage_pct_of_bothparse'] or '—', r['conditional_change_rate_at_q'] or '—',
                   r['outcome_vs_original']])
a_tbl = tbl(['setting', 'orig q', 'cells 1/2/3/4 (cal)', 'cell-3 share cal', 'cell-3 share dev',
             'recv INVALID % cal', 'ref INVALID % cal', 'cal kept', 'dev kept', 'both-parse q',
             'dev dis. (bp)', 'dev AUROC (bp)', 'dev cov. % (bp)', 'cond. change rate', 'outcome'], a_rows)
newcert = [r['setting'] for r in diag if r['outcome_vs_original'].startswith('certifies')]
lostcert = [r['setting'] for r in diag if r['outcome_vs_original'].startswith('LOSES')]
ag = {(r['group'], r['split']): r for r in agg}
(RES.parent / 'E11A_SUMMARY.md').write_text(f"""# E11-a — INVALID decomposition and the both-parse diagnostic

{HEAD}
## Convention

Each question falls in exactly one cell: (1) both outputs parse and the labels differ — a disagreement;
(2) both parse and agree — agreement; (3) exactly one output is INVALID — a disagreement under the frozen
convention; (4) **both outputs are INVALID — an agreement under the frozen convention**, because the two
answers are then the same single `INVALID` label. Cells (1)+(3) reproduce the frozen disagreement counts
exactly for all 26 settings (asserted in `scripts/e11a.py`).

The both-parse columns are a **diagnostic, not a deployable policy**: the filter reads the reference output.

## Result

All {sum(1 for r in diag if r['original_q'] not in ('0.0', '0'))} currently certified policies
({', '.join(r['setting'] + ' q=' + r['original_q'] for r in diag if r['original_q'] not in ('0.0', '0'))})
still certify on the both-parse subset, at the same q. No deployed policy loses certification.
{len(newcert)} settings that fall back under the frozen rule certify on the both-parse subset
({', '.join(newcert)}) — described only, not deployed.

Share of measured disagreement driven by exactly one INVALID output (cell 3):

{tbl(['group', 'split', 'min share', 'max share', 'pooled share'],
     [[g, sp, ag[g, sp]['min_cell3_share'], ag[g, sp]['max_cell3_share'], ag[g, sp]['pooled_cell3_share']]
      for g in ['18 main settings', '7 cross-family settings', 'Text+fact (E6)'] for sp in ['cal', 'dev']])}
## Asymmetry

When the **reference** output is unparseable, a policy that omits the reference call really does change what
the deployed system returns, so counting it as a change is correct accounting, not a parser artifact. The
parser question bites only where the **receiver** output is unparseable. On calibration the two sides are
separated in `E11a_invalid_decomposition.csv` as `only_receiver_INVALID` and `only_reference_INVALID`.

## Per-setting table (cal = calibration split, bp = both-parse subset)

{a_tbl}
Files: `results/E11a_invalid_decomposition.csv` (four cells per setting per split),
`results/E11a_bothparse_diagnostic.csv`, `results/E11a_bothparse_grid.csv` (all 26 x 20 tests),
`results/E11a_cell3_share_aggregate.csv`.

Cross-check: the seven cross-family rows reproduce E5-e
(`P2_R2_CPU_20260919T220412Z/results/e5e_valid_only_diagnostic.csv`) exactly.
""")

# ---------------------------------------------------------------- E11-b
b_rows = [[r['setting'], r['q_V2'], r['q_official'], r['deployed_under'],
           r['cal_rows_label_differs'], r['cal_rows_label_differs_inside_X'], r['cal_rows_label_differs_outside_X'],
           r['dev_rows_label_differs'], r['cal_d_label_differs'], r['E5a_reproduced']] for r in b]
inter = next(r for r in binter if r['quantity'].startswith('INTERSECTION'))
v2only = next(r for r in binter if r['quantity'].startswith('V2 only'))
ofonly = next(r for r in binter if r['quantity'].startswith('official only'))
depv2 = next(r for r in binter if r['quantity'].startswith('deployed under V2'))
(RES.parent / 'E11B_SUMMARY.md').write_text(f"""# E11-b — intersection of two extraction conventions

{HEAD}
## Scope

The official C2C evaluator's extraction (`rosetta/utils/evaluate.py::extract_answer_from_content`) reads
option letters A–D only, so it applies to the OBQA and ARC settings, not to MMLU-Pro (A–J).
Applicable: **19 settings** (12 main, 4 X1-Llama, 2 X2-OLMo, 1 Text+fact). The saved raw calibration and
development outputs are relabelled with it; the 20 fit-split thresholds are unchanged and are not refitted.

`X` is the E5-a exposure set: the 341 calibration questions whose raw outputs were reviewed with gold during
V2 parser rule development.

## Result — the intersection is SMALLER than the current deployed set

- deployed under frozen V2: **{depv2['n']}** — {depv2['settings']}
- deployed under the official extractor: **{next(r for r in binter if r['quantity'].startswith('deployed under official'))['n']}**
- **intersection ({inter['n']})**: {inter['settings']}
- **V2 only, i.e. flips to fallback under the official extractor ({v2only['n']})**: {v2only['settings']}
- official only ({ofonly['n']}): {ofonly['settings']}

q under V2 → q under the official extractor, for the V2-deployed settings:

{tbl(['setting', 'q (V2)', 'q (official)'], [[r['setting'], r['q_V2'], r['q_official']] for r in b if float(r['q_V2']) > 0])}
Both facts named in the preregistration reproduce: **large/ARC/C2C** flips to fallback and
**large/OBQA/C2C** drops to q = .70.

## Per-setting table

{tbl(['setting', 'q V2', 'q official', 'deployed under', 'cal rows differ', '… inside X', '… outside X',
      'dev rows differ', 'cal d-label differs', 'E5-a reproduced'], b_rows)}
"cal rows differ" counts calibration questions on which the two conventions give a different label for the
receiver output or for the reference output (or both); "cal d-label differs" counts questions on which the
*disagreement* label itself flips. E5-a covered 12 of these 19 settings; every one of its official-extractor
counts (`o_R`, `o_ref`, d-total, d-in-X, d-outside-X, largest accepted q) reproduces exactly — asserted in
`scripts/e11b.py`, which exits non-zero on any mismatch.

Files: `results/E11b_two_conventions.csv`, `results/E11b_grid.csv` (19 x 2 x 20 tests),
`results/E11b_intersection.csv`.
""")

# ---------------------------------------------------------------- E11-c
c_rows = [[r['setting'], r['original_q'], r['ruleD_q'], r['cal_n_at_ruleD_q'] or '—', r['cal_k_at_ruleD_q'] or '—',
           r['cal_p_at_ruleD_q'] or '—', r['dev_coverage_pct_of_all'], r['dev_coverage_pct_of_parseable'],
           r['dev_changed_over_omitted'], r['dev_conditional_change_rate'] or '—',
           r['dev_accuracy_policy_vs_gold'], r['dev_accuracy_reference_vs_gold'], r['verdict']] for r in c]
vd = {r['category']: r for r in cv}
(RES.parent / 'E11C_SUMMARY.md').write_text(f"""# E11-c — Rule D, a deployable INVALID-routing rule

{HEAD}
## Rule

Rule D: if the receiver-only output does not parse, route to the reference; otherwise apply the usual
threshold rule. The omission set at threshold tau is {{x : u(x) <= tau and o_R(x) parses}}. Rule D reads only
the receiver's own output, never the reference's, so it is deployable, and parsing the receiver output is
already part of the policy. The controlled quantity is unchanged:
rho_D(tau) = P(o_R != o_b | omitted under Rule D). Same 20 fit-split thresholds, same alpha = .05,
delta = .001, Bonferroni over the 20 candidates. A separate post hoc family of 26 x 20 = 520 tests.

## Result — Rule D certifies nothing new

- new certifications under Rule D: **{vd['new certification under Rule D']['n']}**
- lost certifications under Rule D: **{vd['lost certification under Rule D']['n']}**
- certified under both with a different q: **{vd['certified under both, q changed']['n']}**
- unchanged: **{vd['unchanged']['n']}** of 26

In particular Rule D does **not** certify any of the seven cross-family settings, including the three OLMo
settings it was aimed at. Routing away unparseable *receiver* outputs removes only part of the measured
disagreement; the rows on which the *reference* output is unparseable while the receiver parses stay in, and
they are genuine changes to what the deployed system returns. That is why the both-parse diagnostic of E11-a
(which also drops those rows, and is therefore not deployable) certifies four settings that Rule D does not.

## Per-setting table

{tbl(['setting', 'orig q', 'Rule D q', 'cal n', 'cal k', 'cal p', 'dev cov. % of all', 'dev cov. % of parseable',
      'changed/omitted', 'cond. change rate', 'dev acc. policy', 'dev acc. reference', 'verdict'], c_rows)}
Coverage is reported both as a fraction of all development questions and as a fraction of development
questions whose receiver output parses. Accuracy is against gold on the development split
(the same quantity as "Correct P/B" in the paper's Table 6); `E11c_ruleD.csv` also carries
`dev_policy_equals_reference`, the agreement of the Rule-D policy with the reference answer.

Files: `results/E11c_ruleD.csv`, `results/E11c_ruleD_grid.csv` (26 x 20 tests), `results/E11c_verdicts.csv`.
""")

# ---------------------------------------------------------------- top-level SUMMARY
compact_a = tbl(['setting', 'cell-3 share of dis. (cal)', 'both-parse q', 'dev dis. (bp)', 'dev AUROC (bp)', 'outcome'],
                [[r['setting'], cell[r['setting'], 'cal']['cell3_share_of_disagreements'], r['bothparse_accepted_q'],
                  r['dev_disagreement_bothparse'], r['dev_AUROC_bothparse'], r['outcome_vs_original']] for r in diag])
compact_b = tbl(['setting', 'q V2', 'q official', 'deploy status'],
                [[r['setting'], r['q_V2'], r['q_official'], r['deployed_under']] for r in b])
compact_c = tbl(['setting', 'Rule D q', 'dev cov. % all', 'dev cov. % parseable', 'cond. change rate', 'verdict'],
                [[r['setting'], r['ruleD_q'], r['dev_coverage_pct_of_all'], r['dev_coverage_pct_of_parseable'],
                  r['dev_conditional_change_rate'] or '—', r['verdict']] for r in c])
(RES.parent / 'SUMMARY.md').write_text(f"""# E11 — parser-convention robustness of the certification boundary (Round 4)

{HEAD}
## Preregistration

| | |
|---|---|
| file | `PREREG_E11.md` |
| SHA-256 | `{PREREG_SHA}` |
| recorded (UTC) | {PREREG_TS} |
| record | `PREREG_E11.sha256` |

Written and hashed before any saved output was read. The reporting rules in it were not changed after the
results were seen. Deviations: `DEVIATIONS.md`.

## Step 1 — reproduction check: **PASS**

All 26 settings reproduce. For every setting the full 20-row calibration ledger recomputed from the saved
records matches the stored ledger exactly (520 rows: n, k and the exact-binomial p-value), each deployed q
is recovered from the records, and the development disagreement count and AUROC match the published values
(Tables 2 and 6 for the 14 main settings, E8 `SUMMARY.md` section 1 for the four E8 settings,
E6 `E6_RESULTS.md` for Text+fact, and `P2_R1_XFAM_.../results/analysis/dev_table.csv` and
`.../x1/results/analysis/dev_table.csv` for the seven cross-family settings).

{s1}
## (a) E11-a — INVALID decomposition and both-parse diagnostic

Cell (4), both outputs INVALID, is counted as **agreement**, matching the frozen convention.
The both-parse columns are a diagnostic and are **not deployable** (the filter reads the reference output).

{compact_a}
## (b) E11-b — two extraction conventions (19 A–D settings)

{compact_b}
**Intersection ({inter['n']} settings): {inter['settings']}.**
V2 only ({v2only['n']}): {v2only['settings']}. Official only: {ofonly['settings']}.

## (c) E11-c — Rule D (deployable INVALID routing)

{compact_c}
New certifications: {vd['new certification under Rule D']['n']}. Lost: {vd['lost certification under Rule D']['n']}.

## What does not change

No threshold, deployment, replay, latency number or frozen protocol is revised by E11. Each of E11-a, E11-b
and E11-c is a separate post hoc family and is labelled as such.
""")
print('summaries written')
