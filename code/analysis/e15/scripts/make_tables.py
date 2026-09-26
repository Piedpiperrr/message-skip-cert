"""Render the E15 result CSVs as markdown tables (results/TABLES_E15.md). Formatting only, no new computation."""
import csv
from pathlib import Path

RES = Path(__file__).resolve().parents[1] / 'results'
rd = lambda n: list(csv.DictReader(open(RES / n)))
f = lambda x, k=1: '' if x in ('', None) else f'{float(x):.{k}f}'
out = []

out += ['## E15-1 per setting (results/e15_1_per_setting.csv)', '',
        '| setting | actual | q | predicted | q_hat | steps (q_hat-q) | dev cov | pred fit cov | abs cov err | measured saving (ms) | pred saving, fit cov (ms) | pred saving, panel cov (ms) |',
        '|---|---|---|---|---|---|---|---|---|---|---|---|']
for r in rd('e15_1_per_setting.csv'):
    out.append(f"| {r['setting']} | {r['actual_outcome']} | {f(r['actual_q'],2) if float(r['actual_q'])>0 else '-'} | {r['predicted_outcome']} | "
               f"{f(r['q_hat'],2) if float(r['q_hat'])>0 else '-'} | {r.get('grid_steps_qhat_minus_q','')} | {f(r.get('actual_dev_coverage'),3)} | "
               f"{f(r['predicted_fit_coverage'],3)} | {f(r.get('abs_coverage_error'),3)} | {f(r.get('measured_saving_ms'))} | "
               f"{f(r.get('pred_saving_fitcov_ms'))} | {f(r.get('pred_saving_panelcov_ms'))} |")
out += ['', '## E15-1 saving model inputs (8 policies)', '',
        '| setting | mean c_b | mean c_R | gap | mean c_s | pred fit cov | panel cov | measured | pred (fit) | abs err | rel err | pred (panel) | abs err | rel err |',
        '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
for r in rd('e15_1_per_setting.csv'):
    if r.get('c_b_mean_ms'):
        out.append(f"| {r['setting']} | {f(r['c_b_mean_ms'])} | {f(r['c_R_mean_ms'])} | {f(r['gap_ms'])} | {f(r['c_s_mean_ms'])} | "
                   f"{f(r['predicted_fit_coverage'],4)} | {f(r['panel_coverage'],4)} | {f(r['measured_saving_ms'])} | {f(r['pred_saving_fitcov_ms'])} | "
                   f"{f(r['abs_err_fitcov_ms'])} | {f(r['rel_err_fitcov'],3)} | {f(r['pred_saving_panelcov_ms'])} | {f(r['abs_err_panelcov_ms'])} | {f(r['rel_err_panelcov'],3)} |")
s = rd('e15_1_summary.csv')[0]
out += ['', '## E15-1 summary (results/e15_1_summary.csv)', ''] + [f'- {k}: {v}' for k, v in s.items() if k != 'label']

out += ['', '## E15-2 source qualification (results/e15_2_qualification.csv)', '', '| setting | source | qualifies | reason |', '|---|---|---|---|']
for r in rd('e15_2_qualification.csv'):
    out.append(f"| {r['setting']} | {r['source']} | {r['qualifies']} | {r['reason']} |")
out += ['', '## E15-2 busy GPU time, original configuration (results/e15_2_busy_savings.csv)', '',
        '| setting | N | omitted | busy saving ms [95%] | latency saving ms [95%] | D ms [95%] | busy/latency |', '|---|---|---|---|---|---|---|']
for r in rd('e15_2_busy_savings.csv'):
    if r['busy_available'] == 'True':
        rt = r['ratio_busy_over_latency']
        out.append(f"| {r['setting']} | {r['N']} | {r['n_omitted']} | {f(r['busy_saving_ms'])} [{f(r['busy_saving_CI_low'])}, {f(r['busy_saving_CI_high'])}] | "
                   f"{f(r['latency_saving_ms'])} [{f(r['latency_saving_CI_low'])}, {f(r['latency_saving_CI_high'])}] | "
                   f"{f(r['D_ms'])} [{f(r['D_CI_low'])}, {f(r['D_CI_high'])}] | {f(rt,3) if rt[0].isdigit() else rt} |")
    else:
        out.append(f"| {r['setting']} | - | - | not available (no qualifying replay source) | - | - | - |")
out += ['', '### Stage means per request (ms; CUDA-event intervals)', '',
        '| setting | fixed: helper | fixed: fuser | fixed: receiver | fixed busy | policy: probe | policy: helper | policy: fuser | policy: receiver | policy busy |',
        '|---|---|---|---|---|---|---|---|---|---|']
for r in rd('e15_2_busy_savings.csv'):
    if r['busy_available'] == 'True':
        out.append(f"| {r['setting']} | {f(r['fixed_helper_ms'])} | {f(r['fixed_fuser_ms'])} | {f(r['fixed_receiver_ms'])} | {f(r['mean_busy_fixed_ms'])} | "
                   f"{f(r['policy_probe_ms'])} | {f(r['policy_helper_ms'])} | {f(r['policy_fuser_ms'])} | {f(r['policy_receiver_ms'])} | {f(r['mean_busy_policy_ms'])} |")
(RES / 'TABLES_E15.md').write_text('\n'.join(out) + '\n')
print('\n'.join(out))
