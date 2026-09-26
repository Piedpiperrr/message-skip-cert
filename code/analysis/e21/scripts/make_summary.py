"""Builds SUMMARY.md, results/E21_1_appendix_table.csv and SCRIPT_HASHES.md from the stage's own outputs (no new statistic)."""
import csv, json, hashlib, glob, os
from pathlib import Path

S = Path(__file__).resolve().parents[1]
R = S / 'results'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
rd = lambda p: list(csv.DictReader(open(p)))
F = lambda x, d=4: 'N/A' if x in (None, '', 'N/A', 'NONE') else (f'{float(x):.{d}f}' if not isinstance(x, str) or x.replace('.', '', 1).replace('-', '', 1).replace('e', '', 1).isdigit() else x)
PC = lambda x, d=1: 'N/A' if x in (None, '', 'N/A') else f'{100 * float(x):.{d}f}%'
CERT = json.load(open(S / 'CERT.json'))
ph, pt = (S / 'PREREG.sha256').read_text().split()[0], (S / 'PREREG.sha256').read_text().split()[-1]
ch, ct = (S / 'CERT.sha256').read_text().split()[0], (S / 'CERT.sha256').read_text().split()[-1]
logs = {Path(f).stem.replace('_run', ''): json.load(open(f)) for f in glob.glob(str(S / 'logs/*_run.json'))}
DEV = {(r['setting'], r['eps'], r['policy']): r for r in rd(R / 'E21_1_dev.csv')}
OOS = {(r['setting'], r['eps'], r['policy']): r for r in rd(R / 'E21_1_oos.csv')}
PAN = {(r['setting'], r['eps']): r for r in rd(R / 'E21_1_panel.csv')}
SUM = {(r['setting'], r['eps']): r for r in rd(R / 'E21_1_cert_summary.csv')}
R1 = json.load(open(R / 'E21_1_writing_rule.json'))
R2 = json.load(open(R / 'E21_2_writing_rule.json'))
R3 = json.load(open(R / 'E21_3a_writing_rule.json'))
AU = rd(R / 'E21_2_auroc.csv')
ROT = rd(R / 'E21_3a_rotation.csv')
GATE = rd(R / 'E21_3a_gate_checks.csv')
REPRO = rd(R / 'step0_repro_checks.csv')
SET6 = ['large/OBQA/Text', 'large/ARC/Text', 'large/MMLU-Pro/Text', 'large/OBQA/Text+fact', 'Llama-3.1-8B/OBQA/Text', 'Llama-3.1-8B/ARC/Text']
NOM = {'large/OBQA/Text', 'large/OBQA/Text+fact'}

# ------------------------------------------------------------------ E21-1 lines and appendix table
lines1, app = [], []
cnt = {(d['setting'], str(d['eps'])): d for d in R1['counted_detail']}
for s in SET6:
    for e in ['0.01', '0.02']:
        c, dj, df = SUM[s, e], DEV.get((s, e, 'joint')), DEV[(s, e, 'frozen')]
        oj, of_, p = OOS.get((s, e, 'joint')), OOS.get((s, e, 'frozen')), PAN[s, e]
        has = dj is not None and dj.get('coverage') not in (None, '')
        D4 = f"{c['D_all']}/{c['D_seq']}/{c['D_dep']}/{c['D_need']}"
        if has:
            dev_s = (f"dev cov {PC(dj['coverage'])} | dev L/W {dj['k_L']}/{dj['k_W']} | dAcc {100 * float(dj['dAcc']):+.2f} pts "
                     f"[{100 * float(dj['dAcc_CI95_lo']):+.2f}, {100 * float(dj['dAcc_CI95_hi']):+.2f}] | G_dev {float(dj['G_pts']):.2f} pts | "
                     f"retention {float(dj['retention']):.3f}")
        else:
            dev_s = 'dev N/A (q_joint NONE)'
        if oj is not None and oj.get('k_L') not in (None, ''):
            ret = oj['retention'] if oj['retention'] in ('N/A',) else f"{float(oj['retention']):.3f}"
            oos_s = (f"OOS {oj['population']}: N {oj['N']} cov {PC(oj['coverage'])} k_L/N {oj['k_L']}/{oj['N']} = {PC(oj['k_L_over_N'], 2)} "
                     f"[{PC(oj['k_L_CP95_lo'], 2)}, {PC(oj['k_L_CP95_hi'], 2)}] (<eps {oj['CP_upper_lt_eps']}) W {oj['k_W']} "
                     f"dAcc {100 * float(oj['dAcc']):+.2f} [{100 * float(oj['dAcc_CI95_lo']):+.2f}, {100 * float(oj['dAcc_CI95_hi']):+.2f}] ret {ret}")
        elif s == 'large/MMLU-Pro/Text':
            oos_s = 'OOS N/A (MMLU-Pro: no unused data)'
        else:
            oos_s = 'OOS N/A (q_joint NONE)'
        pan_s = (f"panel {float(p['joint_saving_ms']):.1f} ms [{float(p['joint_CI95_lo']):.1f}, {float(p['joint_CI95_hi']):.1f}] "
                 f"(frozen {float(p['frozen_saving_ms']):.1f} [{float(p['frozen_CI95_lo']):.1f}, {float(p['frozen_CI95_hi']):.1f}]; "
                 f"{p['panel_rerouted']}/{p['panel_omitted_frozen']} re-routed)" if p.get('joint_saving_ms') else 'panel N/A')
        cx = CERT['settings'][s]['C_minus_X']
        cx_s = f"C\\X (N {cx['N']}, change-test q {cx['q_change_test']}): q_joint {cx['eps' + e]['q_joint'] if cx['eps' + e]['q_joint'] is not None else 'NONE'}"
        cd = cnt[s, e]
        lines1.append(f"{s}{' [nominal]' if s in NOM else ''} eps={e}: N {c['N']} | N_min {c['N_min']} ({c['status']}) | q_frozen {c['q_frozen']} | "
                      f"q_L {c['q_L']} | q_joint {c['q_joint']} | D {D4} | {dev_s} | {oos_s} | {pan_s} | {cx_s} | counted: {cd['counted']}")
        app.append(dict(setting=s, nominal=s in NOM, eps=e, N=c['N'], N_min=c['N_min'], cal_status=c['status'], q_frozen=c['q_frozen'],
                        tau_frozen=c['tau_frozen'], q_L=c['q_L'], q_joint=c['q_joint'], tau_joint=c['tau_joint'], first_L_rejected_q=c['first_L_rejected_q'],
                        k_L_at_frozen=c['k_L_at_frozen'], p_at_frozen=c['p_at_frozen'], D_all=c['D_all'], D_seq=c['D_seq'], D_dep=c['D_dep'], D_need=c['D_need'],
                        dev_coverage=dj['coverage'] if has else 'N/A', dev_k_L=dj['k_L'] if has else 'N/A', dev_k_W=dj['k_W'] if has else 'N/A',
                        dev_changed=dj['changed'] if has else 'N/A', dev_omitted=dj['omitted'] if has else 'N/A',
                        dev_change_CP95=f"[{float(dj['change_CP95_lo']):.4f}, {float(dj['change_CP95_hi']):.4f}]" if has else 'N/A',
                        dev_dAcc=dj['dAcc'] if has else 'N/A', dev_dAcc_CI95=f"[{float(dj['dAcc_CI95_lo']):.4f}, {float(dj['dAcc_CI95_hi']):.4f}]" if has else 'N/A',
                        G_dev_pts=df['G_pts'], dev_retention=dj['retention'] if has else 'N/A',
                        frozen_dev_coverage=df['coverage'], frozen_dev_k_L=df['k_L'], frozen_dev_k_W=df['k_W'], frozen_dev_changed=df['changed'],
                        frozen_dev_omitted=df['omitted'], frozen_dev_dAcc=df['dAcc'],
                        frozen_dev_dAcc_CI95=f"[{float(df['dAcc_CI95_lo']):.4f}, {float(df['dAcc_CI95_hi']):.4f}]", frozen_dev_retention=df['retention'],
                        oos=oos_s, frozen_oos=(f"k_L/N {of_['k_L']}/{of_['N']} [{float(of_['k_L_CP95_lo']):.4f}, {float(of_['k_L_CP95_hi']):.4f}] "
                                               f"cov {float(of_['coverage']):.4f} dAcc {float(of_['dAcc']):+.4f}") if of_ and of_.get('k_L') else 'N/A',
                        panel=pan_s, CX_N=cx['N'], CX_q_change_test=cx['q_change_test'], CX_q_joint=cx['eps' + e]['q_joint'],
                        counted=cd['counted'], counted_why=cd['why']))
with open(R / 'E21_1_appendix_table.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(app[0]))
    w.writeheader(); w.writerows(app)

# ------------------------------------------------------------------ E21-2 lines
lines2 = []
for r in AU:
    if r['kind'] == 'policy' and r['population'] == 'dev':
        iv = r['auroc_m_u0'] if r['auroc_m_u0'] == 'N/A' else f"{float(r['auroc_m_u0']):.3f}"
        lines2.append(f"{r['row']}: (i) {float(r['auroc_all']):.4f} | (ii) {float(r['auroc_upos']):.3f} [{float(r['auroc_upos_CI95_lo']):.3f}, "
                      f"{float(r['auroc_upos_CI95_hi']):.3f}] {r['upos_pos']}/{r['upos_n']} | (iii) {float(r['auroc_m_all']):.3f} | (iv) {iv} "
                      f"{r['u0_pos']}/{r['u0_n']} | (v) u=0 share {PC(r['share_u0'])}, dis. with u>0 {PC(r['share_dis_upos'])} | (vi) {PC(r['u0_change_rate'], 2)}")
    elif r['kind'] == 'policy':
        lines2.append(f"{r['row']} [held-out OBQA 744]: (i) {float(r['auroc_all']):.4f} | (ii) {float(r['auroc_upos']):.3f} [{float(r['auroc_upos_CI95_lo']):.3f}, "
                      f"{float(r['auroc_upos_CI95_hi']):.3f}] {r['upos_pos']}/{r['upos_n']} | (iii) not stored | (iv) not stored "
                      f"({r['u0_pos']}/{r['u0_n']} in u=0) | (v) u=0 share {PC(r['share_u0'])}, dis. with u>0 {PC(r['share_dis_upos'])}")
    else:
        v = (f" | (v) u=0 share {PC(r['share_u0'])}, dis. with u>0 {PC(r['share_dis_upos'])}" if r.get('share_u0') else '')
        lines2.append(f"{r['row']} [control, {r['population']}]: (i) {float(r['auroc_all']):.4f} ({r['n_pos']}/{r['n']}){v}")

# ------------------------------------------------------------------ E21-3a lines
rot = {(r['population'], r['line']): r for r in ROT}
lines3 = []
for p in ['small/OBQA', 'small/ARC', 'medium/OBQA', 'medium/ARC', 'large/OBQA', 'large/ARC', 'large/MMLU-Pro']:
    def g(l):
        r = rot[p, l]
        return f"n {r['n']}, {r['changes']}, " + ('N/A' if r['n'] == '0' else f"{PC(r['rate'])} [{PC(r['CP95_lo'])}, {PC(r['CP95_hi'])}]")
    lines3.append(f"{p}: u=0 {g('V1 vs R, u = 0')} | u>0 {g('V1 vs R, u > 0')} | all {g('V1 vs R, all')} | parseable-only all "
                  f"{g('V1 vs R, all, parseable-only (R and V1 both parse)')} | V0 vs R (drift) {rot[p, 'supplementary: V0 (same-job unchanged replay) vs R, all']['changes']}/{rot[p, 'supplementary: V0 (same-job unchanged replay) vs R, all']['n']}")
for r in ROT:
    if r.get('policy') and '[omitted]' in r['line']:
        pol = r['policy']
        z = next(x for x in ROT if x.get('policy') == pol and '[omitted, u = 0]' in x['line'])
        zp = next(x for x in ROT if x.get('policy') == pol and '[omitted, u > 0]' in x['line'])
        lines3.append(f"{pol} omitted dev (the receiver's own answer change under rotation, not the policy's change rate): {r['changes']}/{r['n']} = {PC(r['rate'])} "
                      f"[{PC(r['CP95_lo'])}, {PC(r['CP95_hi'])}]; u=0 {z['changes']}/{z['n']}; u>0 {zp['changes']}/{zp['n']} = {PC(zp['rate'])}")

# ------------------------------------------------------------------ SUMMARY.md
npass = sum(r['status'] == 'PASS' for r in REPRO)
first = logs['e21_1_cert']['start_utc']
out = [f'# E21 SUMMARY (P2_R9_E21_20260922T065220Z)', '',
       'Post hoc analyses of stored outputs (ClusterA login node, CPU only; no model forward pass). E21 creates no deployment and changes no count in the paper.', '',
       '## Timeline and hashes', '',
       f'- Step 0 REPRO {logs["step0_repro"]["start_utc"]} - {logs["step0_repro"]["end_utc"]} ((a)-(g) {npass}/{len(REPRO)} PASS; (h) search, see REPRO.md).',
       f'- PREREG.md sha256 `{ph}` written/hashed {pt} (verbatim; the one "[frozen q]" replaced by [.40, tau = 3.838539123535156e-05], cited in INPUTS.md).',
       f'- First E21 statistic: {first} (start of scripts/e21_1_cert.py).',
       f'- CERT.json sha256 `{ch}` hashed {ct}; E21-1 evaluation {logs["e21_1_eval"]["start_utc"]} - {logs["e21_1_eval"]["end_utc"]} (verified CERT hash first).',
       f'- E21-2 {logs["e21_2"]["start_utc"]} - {logs["e21_2"]["end_utc"]}; E21-3a {logs["e21_3a"]["start_utc"]} - {logs["e21_3a"]["end_utc"]}.',
       '- Script hashes: SCRIPT_HASHES.md.', '',
       '## E21-1 label-light certificate of the accuracy loss', '',
       f"**Writing rule branch: {R1['branch']}.** Quoted sentence with the numbers filled in (Sec. 4.3):", '',
       f"> {R1['sentence']}", '',
       f"Deciding numbers: counted at eps = .01 = {', '.join(R1['A'])} (A = {R1['A_n']}; B = {R1['B']} nominal: large/OBQA/Text and Text+fact); "
       f"K = range of D_need over them = {R1['K']} (D_need {R1['D_need']}); dev coverage {', '.join(f'{x:.1f}%' for x in R1['coverage_pct'])}; "
       f"retention {', '.join(f'{x:.1f}%' for x in R1['retention_pct'])}; no counted setting has dev or out-of-sample k_L/N > eps "
       f"({'none' if not R1['exceed_eps'] else '; '.join(R1['exceed_eps'])}). Abstract: at most one clause, authors' choice.", '',
       '"Counted" per setting x eps (joint certificate, dev coverage >= 20%, eps <= G_dev/2):', '']
out += [f"- {d['setting']} eps={d['eps']}: counted {d['counted']} ({d['why']})" for d in R1['counted_detail']]
out += ['', f"Infeasible (N < N_min): {'; '.join(R1['infeasible'])}.",
        f"Out-of-sample CP upper end >= eps (appendix): {'; '.join(R1['oos_CP_upper_ge_eps']) or 'none'}.",
        'Family-wise error of each joint certificate <= .04 per setting and eps (.02 change-rate family + .02 L family), .06 per setting if both eps are read. '
        'large/OBQA/Text and Text+fact are nominal (their calibration labels were used when ProbeMax was selected). '
        'Exposure: as the PREREG states, and REPRO (h) found that an earlier result file (E6_RESULTS.md / E6_RESULTS.json) already contained the Text+fact '
        'calibration lost-correction count at the deployed q = .75 (18 of 999 omitted) and over the whole split (122); the recomputed k_L at tau_frozen is 18. '
        'No such count exists for the other five settings.', '',
        'Appendix table (all 6 settings x 2 eps; also results/E21_1_appendix_table.csv; D = D_all/D_seq/D_dep/D_need; dAcc = acc(pi) - acc(b); '
        'panel = recomposed mean saving vs the fixed reference, not a replay):', '']
out += [f'- {l}' for l in lines1]
out += ['', 'Frozen-policy dev numbers for comparison are in results/E21_1_dev.csv (policy = frozen) and the appendix CSV (frozen_dev_*); '
        'frozen out-of-sample rows in results/E21_1_oos.csv.', '',
        '## E21-2 AUROC on unsaturated questions', '',
        f"**Writing rule branch: {R2['branch']}.** Sec. 6 (always): {R2['always']}", '',
        f"> {R2['sentence']}", '',
        f"Deciding numbers: median (ii) = {R2['ii_median']:.4f} (range {R2['ii_min']:.4f} {R2['ii_min_policy']} - {R2['ii_max']:.4f} {R2['ii_max_policy']}); "
        f"median (i) = {R2['i_median']:.4f}; median (iii) = {R2['iii_median']:.4f}. (i) reproduces the paper to 5e-4 for all 9 policies and 3 controls; "
        f"(vi) = {100 * R2['vi_min']:.2f}-{100 * R2['vi_max']:.2f}% over the nine policies, reproducing E17-1 (n0/k0 match E17_1_u0_rule.csv).", '']
out += [f'- {l}' for l in lines2]
out += ['', 'Held-out (iii)/(iv): not stored. E16-3 prefilled bf16 label logits only for fit/cal/dev units; the held-out records store float32 p_labels only.', '',
        '## E21-3a option-rotation stability at u = 0', '',
        '**Gate: PASS.** Code/protocol: `P2_R1_EXP_.../PROTOCOL_FREEZE.md` sec. 6 ("V1 perm: the option list is rotated by one position, so original option i sits at '
        'position (i+1) mod K, and labels are re-assigned by position"; "The parsed displayed label at position p maps back to the original label at index '
        '(p-1) mod K. INVALID stays INVALID"); `src/prepare_populations.py` rotate() (only choice_text / choices.text change, labels fixed, back map); '
        '`src/e4_null.py` (V1 = `runner.request(v1_query, "receiver_only")`, the same call as the unchanged V0 replay; generation config asserted equal to the '
        'frozen receiver config, greedy, max_new_tokens 64). Programmatic checks (results/E21_3a_gate_checks.csv): '
        f"{sum(g['status'] == 'PASS' for g in GATE)}/{len(GATE)} PASS: every population row is a pure one-position rotation of option contents with labels, stem and "
        'other fields unchanged; every V1 record maps back with its own map; rendered V1 prompts equal V0 prompts with option contents rotated; one generation config. '
        'V1 records carry no probe score, so the share of u = 0 questions that stay at u = 0 under rotation is not stored.', '',
        f"**Writing rule branch: {R3['branch']}.** Failing populations (u = 0 CP upper >= 5%): {', '.join(R3['failing_populations'])}.", '',
        f"> {R3['sentence']}", '',
        'Neither branch is used to argue about training-data contamination.', '']
out += [f'- {l}' for l in lines3]
out += ['', '## Files', '',
        '- PREREG.md / PREREG.sha256, INPUTS.md, REPRO.md, CERT.json / CERT.sha256, DEVIATIONS.md, SCRIPT_HASHES.md',
        '- results/: step0_repro_checks.csv, step0_recomputed_calibration_ledgers.csv, step0h_exposure_hits.json, E21_1_cert_candidates.csv, '
        'E21_1_cert_summary.csv, E21_1_dev.csv, E21_1_oos.csv, E21_1_panel.csv, E21_1_appendix_table.csv, E21_1_writing_rule.json, E21_2_auroc.csv, '
        'E21_2_checks.csv, E21_2_writing_rule.json, E21_3a_gate_checks.csv, E21_3a_rotation.csv, E21_3a_writing_rule.json',
        '- logs/: one log and one *_run.json (start/end UTC, script and common-module sha256, every file read) per script']
(S / 'SUMMARY.md').write_text('\n'.join(out) + '\n')

# ------------------------------------------------------------------ SCRIPT_HASHES.md
sh = ['# Script hashes (sha256) of every script run for E21', '', '| script | sha256 | run |', '|---|---|---|']
for f in sorted(glob.glob(str(S / 'scripts/*.py'))):
    n = Path(f).name
    lg = logs.get(Path(f).stem)
    sh.append(f"| scripts/{n} | {sha(f)} | {(lg['start_utc'] + ' - ' + lg['end_utc']) if lg else 'see note'} |")
    if lg:
        assert lg['script_sha256'] == sha(f), n
(S / 'SCRIPT_HASHES.md').write_text('\n'.join(sh) + '\n')
print('\n'.join(lines1)); print(); print('\n'.join(lines2)); print(); print('\n'.join(lines3))
