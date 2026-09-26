"""E20F: RESULTS_E20F.md from CERT_E20F.json, STATS_E20F.json, results/ACCURACY_E20F.json (all hash-checked) and the writing-rule branch of
PREREG_E20F.md: (7) if CERT or STATS was written after 2026-09-23T11:00:00Z (Sep 23 06:00 CDT); else (3) fallback; else, with dev coverage >= .10
and the dev omitted-change two-sided 95% CP lower bound <= .05: (1) test pass, (1a) inconclusive, (1b) fail; otherwise (2). Rule (5) = dev G
interval includes 0 or G <= kappa*alpha. usage: e20f_results.py [--dry-run]"""
import sys, json, argparse, pathlib, datetime
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e20f_common as FC

ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true'); a = ap.parse_args()
B = FC.base(a.dry_run)
cert, hc = FC.load_cert(a.dry_run); hs = FC.check_hashfile(B / 'STATS_E20F.sha256', 'STATS_E20F.json')
S = json.loads((B / 'STATS_E20F.json').read_text()); A = json.loads((B / 'results/ACCURACY_E20F.json').read_text())
DL = '2026-09-23T11:00:00+00:00'
f = lambda x, n=4: 'N/A' if x is None else (f'{x:.{n}f}' if isinstance(x, float) else str(x))
ci = lambda v: f'[{f(v[0])}, {f(v[1])}]' if v and v[0] is not None else '[N/A]'
dv, t = S['dev'], S['test']
if cert['utc'] > DL or S['utc'] > DL: br = '(7)'
elif not cert['deployed']: br = '(3)'
elif dv['coverage'] >= .10 and dv['omitted_change_CP95'][0] <= .05:
    br = {'pass': '(1)', 'inconclusive': '(1a)', 'fail': '(1b)'}.get((t or {}).get('verdict'), 'undetermined: test incomplete')
else: br = '(2)'
L = ['# RESULTS_E20F — E20-full (SQuAD v1.1, helper Qwen2.5-7B-Instruct Text, receiver Llama-3.1-8B-Instruct, score s2)', '',
     f'CERT_E20F.json {hc} ({cert["utc"]}); STATS_E20F.json {hs} ({S["utc"]}); accuracy {A["utc"]}. Writing-rule branch: **{br}**; '
     f'rule (5) triggered: **{A["rule5_redundancy_triggered"]}**.', '', '## Calibration (fit 500 -> 20 thresholds; calibration 2,000)', '',
     '| q | tau | n | k | p | .999 CP up | accepted |', '|---|---|---|---|---|---|---|']
L += [f"| {r['q']:.2f} | {r['tau']} | {r['n']} | {r['k']} | {r['p']:.3g} | {r['CP999_upper']:.4f} | {r['accepted']} |" for r in cert['ledger']]
c = cert['cal']
L += ['', f"Deployed q = **{cert['deployed_q'] if cert['deployed'] else 'fallback'}** (threshold {cert['threshold']}). Disagreement {c['disagreements']}/{c['n']}; "
      f"INVALID R {c['invalid_R']}, reference {c['invalid_ref']}; always-omit change rate {f(c['always_omit_change_rate'])}; max TPR/FPR {c['max_TPR_over_FPR']} "
      f"vs C = {f(c['C_pi_alpha'])}; needed N_cal (if fallback): {cert['needed_N_cal']}.", '', '## Dev (1,000)', '',
      f"d = {dv['disagreements']}/{dv['n']} = {f(dv['d'])} {ci(dv['d_CP95'])}; AUROC s2 {f(dv['AUROC_s2'])} {ci(dv['AUROC_s2_CI95'])} (>= .80: {dv['AUROC_ge_080']}); "
      f"coverage {f(dv['coverage'])}; omitted changes {dv['omitted_changes']}/{dv['omitted']} = {f(dv['omitted_change_rate'])} {ci(dv['omitted_change_CP95'])}; "
      f"split {dv['omitted_changes_split']}; INVALID R {dv['invalid_R']}, reference {dv['invalid_ref']}; binormal P(certify) from dev at N_cal 2,000 = "
      f"{f(dv['binormal_P_certify_at_Ncal2000'], 3)}.", '', f"Surface (omitted dev): {S['surface']['omitted_dev']}", '', f"Surface (all dev): {S['surface']['all_dev']}",
      '', f"Lengths: {S['lengths']}", '', '## Test', '', f"{t}", '', '## Accuracy', '']
for sp, x in A['splits'].items():
    L.append(f"- {sp}: R {x['R_correct']}/{x['n']} {ci(x['CI95']['R'])}; Text {x['Text_correct']}/{x['n']} {ci(x['CI95']['Text'])}; policy {x['policy_correct']}/{x['n']} "
             f"{ci(x['CI95']['policy'])}; G {f(x['G'])} {ci(x['CI95']['G'])}; changes {x['changes']}; omitted changes {x['omitted_changes']}")
rs = S['resplits']
L += ['', f"kappa*alpha = {f(A['kappa_alpha']['value'])} vs dev G {f(A['kappa_alpha']['G_dev'])}.", '', '## Re-splits, prediction, value', '',
      f"Re-splits: agreement {f(rs['agreement_with_original'], 3)}, certification rate {f(rs['certification_rate'], 3)}, same q {f(rs['same_q_share'], 3)}, "
      f"median q {rs['median_q']}, median dev coverage {f(rs['median_dev_coverage'])}.", '',
      f"Pilot binormal prediction P@2000 = {S['prediction']['pilot_P_at_2000']} (conservative {S['prediction']['pilot_conservative_P_at_2000']}); outcome: "
      f"{S['prediction']['outcome']}.", '', f"Value estimate (ms): {S['value_estimate_ms']}"]
(B / 'RESULTS_E20F.md').write_text('\n'.join(L) + '\n'); print('\n'.join(L))
