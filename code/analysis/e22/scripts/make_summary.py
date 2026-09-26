"""E22 step 3: the summary quantities of the PREREG (M, K, T_sig, C_sig, ranges, medians) and which
R2 / R3 writing constraints they activate.  Reads only this stage's E22-1 / E22-2 outputs and the stored E9-a
values; writes SUMMARY.md and the table CSVs.  Run after MANIFEST.sha256 is written."""
import json
import numpy as np
from e22_common import *
import e22_common as C

PT = {(r['population'], r['reference']): r for r in csvread(RES / 'E22_1_point.csv')}
BT = {(r['design'], r['population']): r for r in csvread(RES / 'E22_1_bootstrap_intervals.csv')}
SCI = {(r['design'], r['population']): r for r in csvread(E9A / 'results' / 'e9a_bootstrap_intervals.csv')}
MEDLARGE_POPS = [POPNAME[i] for i in MEDLARGE]


def cell(pop, ref):
    p = PT[pop, ref]
    s = BT[f'stratified per-reference {ref}', pop]
    u = SCI[f'per-reference {ref}', pop]
    return dict(pop=pop, ref=ref, und=p['undetermined'] == 'yes',
                s_r=float(p['stratified_ratio']), s_lo=float(s['ci_lo_2_5']), s_hi=float(s['ci_hi_97_5']),
                u_r=float(p['unstratified_ratio_stored_E9a']), u_lo=float(u['ci_lo_2_5']), u_hi=float(u['ci_hi_97_5']))


def med(design, pop):
    r = BT[design, pop]
    return r['boot_mean'], r['ci_lo_2_5'], r['ci_hi_97_5']


def main():
    T = [cell(p, 'Text') for p in POPNAME]
    Call = [cell(p, 'C2C') for p in POPNAME]
    C5 = [cell(p, 'C2C') for p in MEDLARGE_POPS]

    detT = [c for c in T if not c['und']]
    det5 = [c for c in C5 if not c['und']]
    M = [c['pop'] for c in detT if c['s_r'] < 1 and c['u_r'] < 1]
    K = [c['pop'] for c in detT if c['s_hi'] < 1 and c['u_hi'] < 1]
    Tsig = [c['pop'] for c in detT if c['s_hi'] < 1]
    Csig = [c['pop'] for c in det5 if c['s_hi'] < 1 or c['u_hi'] < 1]
    notM = [(c['pop'], c['s_r'], c['u_r']) for c in detT if c['pop'] not in M]

    rngT = (min(c['s_r'] for c in T), max(c['s_r'] for c in T))
    rngC5 = (min(c['s_r'] for c in C5), max(c['s_r'] for c in C5))
    rngT_u = (min(c['u_r'] for c in T), max(c['u_r'] for c in T))
    rngC5_u = (min(c['u_r'] for c in C5), max(c['u_r'] for c in C5))

    # R2 C2C conditions on the five medium/large cells
    at_null = [c['pop'] for c in C5 if c['s_hi'] >= 1 and c['u_hi'] >= 1]
    not_at_null = [c['pop'] for c in C5 if not (c['s_hi'] >= 1 and c['u_hi'] >= 1)]
    reach = all(c['s_r'] >= 1 and c['u_r'] >= 1 for c in C5)
    above1 = [c['pop'] for c in C5 if c['s_lo'] > 1 and c['u_lo'] > 1]

    # R3 branch
    if len(K) >= 4 and len(Csig) == 0:
        r3 = 'branch 1: "the null separates the paths" stays as written.'
    elif len(K) >= 4 and len(Csig) in (1, 2):
        r3 = (f'branch 2: write "separates Text from {5 - len(Csig)} of the five certified C2C paths" and name the '
              f'others ({", ".join(Csig)}).')
    else:
        r3 = ('branch 3: the abstract, Contribution 1 (title included), the Sec. 4.1 heading and the conclusion must '
              'state that whether the null separates Text from C2C depends on how it is matched, giving K, C_sig and '
              'both ranges.')

    trows = []
    for c in T + Call:
        trows.append(dict(population=c['pop'], reference=c['ref'], undetermined='yes' if c['und'] else 'no',
                          stratified_ratio=fmt(c['s_r']), stratified_CI95=f"[{fmt(c['s_lo'])}, {fmt(c['s_hi'])}]",
                          unstratified_ratio=fmt(c['u_r']), unstratified_CI95=f"[{fmt(c['u_lo'])}, {fmt(c['u_hi'])}]",
                          label=LABEL))
    for nm, design, pop in [('MEDIAN Text of 7', 'stratified per-reference Text', 'MEDIAN of 7'),
                            ('MEDIAN C2C of 7', 'stratified per-reference C2C', 'MEDIAN of 7'),
                            ('MEDIAN C2C of the 5 medium/large', 'stratified per-reference C2C',
                             'MEDIAN of the 5 medium/large')]:
        ref = 'Text' if 'Text' in nm else 'C2C'
        sp = [c['s_r'] for c in (T if ref == 'Text' else (C5 if '5' in nm else Call))]
        up = [c['u_r'] for c in (T if ref == 'Text' else (C5 if '5' in nm else Call))]
        b, lo, hi = med(design, pop)
        ur = (SCI[f'per-reference {ref}', 'MEDIAN of 7'] if '5' not in nm else None)
        trows.append(dict(population=nm, reference=ref, undetermined='',
                          stratified_ratio=fmt(np.median(sp)), stratified_CI95=f'[{lo}, {hi}]',
                          unstratified_ratio=fmt(np.median(up)),
                          unstratified_CI95=(f"[{ur['ci_lo_2_5']}, {ur['ci_hi_97_5']}]" if ur else
                                             'not stored (E9-a reports no median over the 5 medium/large cells)'),
                          label=LABEL))
    csvout(RES / 'E22_1_appendix_table.csv', trows)
    csvout(RES / 'E22_1_table1_cells.csv', [r for r in trows])

    q = dict(M=len(M), M_populations=M, M_of=len(detT), K=len(K), K_populations=K, K_of=len(detT),
             T_sig=len(Tsig), T_sig_populations=Tsig, T_sig_of=len(detT),
             C_sig=len(Csig), C_sig_populations=Csig, C_sig_of=len(det5),
             undetermined_Text=[c['pop'] for c in T if c['und']],
             undetermined_C2C_medium_large=[c['pop'] for c in C5 if c['und']],
             undetermined_C2C_all=[c['pop'] for c in Call if c['und']],
             Text_range_stratified=[fmt(rngT[0]), fmt(rngT[1])],
             Text_range_unstratified=[fmt(rngT_u[0]), fmt(rngT_u[1])],
             C2C5_range_stratified=[fmt(rngC5[0]), fmt(rngC5[1])],
             C2C5_range_unstratified=[fmt(rngC5_u[0]), fmt(rngC5_u[1])],
             R2_C2C_at_null_allowed=at_null, R2_C2C_at_null_excluded=not_at_null,
             R2_C2C_reach_allowed=bool(reach), R2_C2C_intervals_above_1=above1,
             R2_Text_not_in_M=notM, R3=r3,
             medians=dict(Text7=med('stratified per-reference Text', 'MEDIAN of 7'),
                          C2C7=med('stratified per-reference C2C', 'MEDIAN of 7'),
                          C2C5=med('stratified per-reference C2C', 'MEDIAN of the 5 medium/large')))
    (RES / 'E22_writing_rules.json').write_text(json.dumps(q, indent=1))

    L = ['# E22 SUMMARY (Paper A, round 10)', '', f'Label: {LABEL}', '',
         '## E22-1 summary quantities (gain over R)', '',
         f'- **M** = {len(M)} of the {len(detT)} determined Text cells: {", ".join(M) if M else "none"}',
         f'- **K** = {len(K)} of the {len(detT)} determined Text cells: {", ".join(K) if K else "none"}',
         f'- **T_sig** = {len(Tsig)} of the {len(detT)} determined Text cells: {", ".join(Tsig) if Tsig else "none"}',
         f'- **C_sig** = {len(Csig)} of the {len(det5)} determined medium/large C2C cells: '
         f'{", ".join(Csig) if Csig else "none"}',
         f'- undetermined Text cells: {", ".join(c["pop"] for c in T if c["und"]) or "none"}',
         f'- undetermined C2C cells: {", ".join(c["pop"] for c in Call if c["und"]) or "none"}',
         f'- Text stratified range (7): {fmt(rngT[0])} to {fmt(rngT[1])} '
         f'(unstratified {fmt(rngT_u[0])} to {fmt(rngT_u[1])})',
         f'- C2C stratified range (5 medium/large): {fmt(rngC5[0])} to {fmt(rngC5[1])} '
         f'(unstratified {fmt(rngC5_u[0])} to {fmt(rngC5_u[1])})', '',
         '### Medians (stratified, 95% bootstrap interval)', '']
    for nm, design, pop in [('Text over the 7 populations', 'stratified per-reference Text', 'MEDIAN of 7'),
                            ('C2C over the 7 populations', 'stratified per-reference C2C', 'MEDIAN of 7'),
                            ('C2C over the 5 medium/large cells', 'stratified per-reference C2C',
                             'MEDIAN of the 5 medium/large')]:
        ref = 'Text' if 'Text' in nm else 'C2C'
        src = T if ref == 'Text' else (C5 if '5 medium/large' in nm else Call)
        b, lo, hi = med(design, pop)
        L.append(f'- {nm}: **{fmt(np.median([c["s_r"] for c in src]))}** [{lo}, {hi}] '
                 f'(unstratified point median {fmt(np.median([c["u_r"] for c in src]))})')
    L += ['', '## Per cell (both designs)', '',
          '| population | ref | undet. | stratified ratio [95%] | unstratified ratio [95%] |', '|---|---|---|---|---|']
    for c in T + Call:
        L.append(f'| {c["pop"]} | {c["ref"]} | {"yes" if c["und"] else "no"} | {fmt(c["s_r"])} '
                 f'[{fmt(c["s_lo"])}, {fmt(c["s_hi"])}] | {fmt(c["u_r"])} [{fmt(c["u_lo"])}, {fmt(c["u_hi"])}] |')
    L += ['', '## Active writing constraints', '', f'**R3** — {r3}',
          f'  Deciding numbers: K = {len(K)} (>= 4 is {len(K) >= 4}), C_sig = {len(Csig)}.', '',
          '**R2 (Text)**',
          f'- "exceeds the null" allowed only for the M = {len(M)} populations: {", ".join(M) if M else "none"}.',
          f'- "significantly" allowed only for the K = {len(K)} populations: {", ".join(K) if K else "none"}.',
          ('- M < 7, so the sentence must name the other populations with their ratios: '
           + ('; '.join(f'{p} (stratified {fmt(a)}, unstratified {fmt(b_)})' for p, a, b_ in notM) or 'none')
           + (f'; plus the undetermined cell(s) {", ".join(c["pop"] for c in T if c["und"])}'
              if any(c['und'] for c in T) else '')) if len(M) < 7 else '- M = 7, no population has to be named.',
          '', '**R2 (C2C)**',
          f'- "at the null\'s level" / "nothing beyond answer volatility" allowed only for: '
          f'{", ".join(at_null) if at_null else "no cell"}; excluded and to be named: '
          f'{", ".join(not_at_null) if not_at_null else "none"}.',
          f'- "matches or exceeds" / "reach" allowed: {reach}. '
          + ('' if reach else 'Use "are not significantly below" instead.'),
          f'- "intervals above 1" allowed only for: {", ".join(above1) if above1 else "no cell"}.',
          f'- small-pair C2C under both designs: '
          + '; '.join(f'{c["pop"]} stratified {fmt(c["s_r"])} [{fmt(c["s_lo"])}, {fmt(c["s_hi"])}], '
                      f'unstratified {fmt(c["u_r"])} [{fmt(c["u_lo"])}, {fmt(c["u_hi"])}]'
                      for c in Call[:2]) + '.',
          '- The abstract keeps one sentence on the per-path null in every branch.', '',
          '**R1** — `results/E22_1_appendix_table.csv` (every cell, both designs, undetermined flagged), '
          '`results/E22_2_directions.csv` (E22-2 appendix table), `results/E22_1_table1_cells.csv` '
          '(the main-text per-path table with both designs and both medians).', '']

    d2 = csvread(RES / 'E22_2_directions.csv')
    L += ['## E22-2 ranges over the seven populations (R4: only ranges may be cited in the main text)', '',
          '| action | wrong->right share | right->wrong changes | INVALID among S- / S+ changes |', '|---|---|---|---|']
    for a in ['Text', 'C2C', 'V1', 'V2']:
        rr = [r for r in d2 if r['action'] == a]
        sh = [float(r['wrong_to_right_share']) for r in rr]
        r2w = [int(r['changes_S_plus_right_to_wrong']) for r in rr]
        i1 = [int(r['INVALID_among_S_minus_changes']) for r in rr]
        i2 = [int(r['INVALID_among_S_plus_changes']) for r in rr]
        L.append(f'| {a} | {fmt(min(sh))} to {fmt(max(sh))} | {min(r2w)} to {max(r2w)} | '
                 f'{min(i1)} to {max(i1)} / {min(i2)} to {max(i2)} |')
    gm = [float(r['null_g_minus']) for r in d2 if r['action'] == 'Text']
    L.append(f'| null g_- | {fmt(min(gm))} to {fmt(max(gm))} | - | - |')
    (STAGE / 'SUMMARY.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L[:24]))


if __name__ == '__main__':
    main()
