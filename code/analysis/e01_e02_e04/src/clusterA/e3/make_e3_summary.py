"""Write P2_R1_EXP_20260919T050555Z/results/E3_SUMMARY.md from the E3_*.csv files (no new computation)."""
import csv, json, pathlib, datetime
RES = pathlib.Path('$DATA_DIR/P2_R1_EXP_20260919T050555Z/results')
rd = lambda n: list(csv.DictReader(open(RES / n)))
f1 = lambda x: f'{float(x):.1f}'


def md(rows, cols, heads):
    s = '| ' + ' | '.join(heads) + ' |\n|' + '---|' * len(cols) + '\n'
    for r in rows:
        s += '| ' + ' | '.join(str(r[c]) for c in cols) + ' |\n'
    return s


S, V, FU, I, HW = rd('E3_policy_savings.csv'), json.load(open(RES / 'E3_verdict.json')), rd('E3_full_mmlu_c2c.csv')[0], rd('E3_integrity.csv'), rd('E3_hardware.csv')
D, A, RT, C = rd('E3_repeat_mmlu_diagnosis.csv'), rd('E3_repeat_mmlu_arm_latency.csv'), rd('E3_repeat1_vs_repeat2_ratios.csv'), rd('E3_classification.csv')
for r in S + [FU]:
    r['pol'] = f"{r['pair']}/{r['task']}/{r['reference']}"
    r['a'] = f"{f1(r['a_mean_ms'])} [{f1(r['a_CI_low'])}, {f1(r['a_CI_high'])}]"; r['b'] = f"{f1(r['b_mean_ms'])} [{f1(r['b_CI_low'])}, {f1(r['b_CI_high'])}]"
    r['am'] = f1(r['a_median_ms']); r['bm'] = f1(r['b_median_ms'])
    r['first'] = f"{f1(r['fixed_first_ms'])}{'*' if r['fixed_first_global_cold'] == 'True' else ''} / {f1(r['policy_first_ms'])}{'*' if r['policy_first_global_cold'] == 'True' else ''}"
out = [f"# E3 on ClusterA: latency replays (records analysed on the login node)\n\nGenerated {datetime.datetime.now(datetime.timezone.utc).isoformat()} by `src/ClusterA/e3/make_e3_summary.py` from the `E3_*.csv` files in this folder "
       "(written by `src/ClusterA/e3/e3_metrics.py`). Jobs: 7635399 (P2R1_E3POL_A, debug; REPEAT1 + REPEAT2) and 7635512 (P2R1_E3POL_B, debug-2; REPEAT3 + MMLU_C2C_FULL); both exit 0. "
       "Each replay's ORIGINAL `src/analyze.py` was also run unchanged through a path-redirecting adapter (`src/ClusterA/e3/run_original_analyses.py`, D7). Its outputs are in `<E3 folder>/results/<stage>/` "
       "(FULL: `results/`), and its version-(a) mean and interval equal the values below in every cell (`E3_verdict.json`: a_equals_original_all = "
       f"{V['a_equals_original_all']}).\n\n"
       "**Rules (fixed before any ClusterA E3 run):**\n"
       "- Paired saving = fixed − policy latency (ms).\n"
       "- (a) all questions, with the original replay's seed-0 bootstrap indices (2,000 resamples, 95% percentile interval).\n"
       "- (b) excludes every question on which either arm made its first formal request after model load, with `default_rng(0)` indices over the remaining questions. This is the P2_R1_CPU item5 method that produced the ClusterB reference classes.\n"
       "- Class on (b): + if low > 0, − if high < 0, ? otherwise.\n"
       "- First-request column = each arm's first formal request latency, fixed / policy (ms); * = the replay's global first request after model load.\n"]
for rep in ['REPEAT1', 'REPEAT2', 'REPEAT3']:
    rows = [r for r in S if r['repeat'] == rep]
    out.append(f"\n## {rep} (source: `E3_policy_savings.csv`; records `{rows[0]['source'].split('/iclr2027_p2/')[1].split('/')[0]}/<stage>/records/`)\n\n")
    out.append(md(rows, ['pol', 'a', 'am', 'b_N', 'b', 'bm', 'b_class', 'ClusterB_class_b', 'first'],
                  ['policy', '(a) mean [95% CI]', '(a) median', '(b) N', '(b) mean [95% CI]', '(b) median', 'class (b)', 'ClusterB (b)', 'first request fixed / policy']))
out.append(f"\n## Verdict: **{V['verdict']}**\n\n" + (('Mismatches: ' + '; '.join(V['mismatches'])) if V['mismatches'] else 'Every policy has the ClusterB version-(b) class in all three repeats.') +
           " The ClusterB classes were recomputed from `P2_R1_CPU_20260919T045556Z/results/item5_cold_request_sensitivity.csv` (ii) and equal the stated reference classes.\n\n")
out.append(md(C, ['pair', 'task', 'reference', 'ClusterB_b', 'REPEAT1', 'REPEAT2', 'REPEAT3'], ['pair', 'task', 'reference', 'ClusterB (b) mean [CI]', 'REPEAT1', 'REPEAT2', 'REPEAT3']))
FU['ac'] = FU['a_class']
out.append("\n## MMLU_C2C_FULL (2,641 development group representatives; fixed C2C vs C2C policy q = .40; source `E3_full_mmlu_c2c.csv`)\n\n"
           + md([FU], ['a', 'ac', 'am', 'b_N', 'b', 'b_class', 'bm', 'first', 'b_excluded_ids'],
                ['(a) mean [95% CI]', 'class (a)', '(a) median', '(b) N', '(b) mean [95% CI]', 'class (b)', '(b) median', 'first request fixed / policy', '(b) excluded']) +
           "\n(a) uses the frozen indices `protocol/bootstrap_indices.npz` = default_rng(0).integers(0,2641,(2000,2641)), asserted equal.\n")
for r in I:
    r['pol'] = f"{r['pair']}/{r['task']}/{r['reference']}"
out.append("\n## Integrity (source `E3_integrity.csv`, from the original analyses' identity outputs; large same-run comparison from the records)\n\n"
           + md(I, ['repeat', 'pol', 'probe_score_and_route_match', 'R_routed_match_dev_R_raw', 'reference_routed_match_same_run_fixed_raw', 'all_match'],
                ['run', 'policy', 'probe score + input hash + route = frozen dev', 'R-routed raw = dev R', 'reference-routed raw = same-run fixed', 'all']))
out.append("\n## REPEAT1 MMLU-Pro replay duration (report only; nothing excluded; sources `E3_repeat_mmlu_diagnosis.csv`, `E3_repeat_mmlu_arm_latency.csv`, `E3_repeat1_vs_repeat2_ratios.csv`)\n\n"
           + md(D, ['repeat', 'host', 'replay_wall_min', 'startup_total_s', 'asset_hash_recheck_s', 'request_span_min', 'sum_request_latency_min', 'gaps_over_1s', 'max_gap_between_requests_s'],
                ['run', 'node', 'replay wall (min)', 'startup (s)', 'weight-hash recheck (s)', 'request span (min)', 'sum of request latencies (min)', 'inter-request gaps > 1 s', 'max gap (s)'])
           + '\n' + md(A, ['repeat', 'arm', 'median_ms', 'p90_ms', 'max_ms', 'mean_ms'], ['run', 'arm', 'median ms', 'p90 ms', 'max ms', 'mean ms'])
           + '\nREPEAT1 / REPEAT2 per arm:\n\n' + md(RT, ['arm', 'median_ratio_R1_over_R2', 'p90_ratio', 'mean_ratio'], ['arm', 'median ratio', 'p90 ratio', 'mean ratio'])
           + "\n- The extra time is between requests (gap = next record time − previous record time − next request latency), outside the timed region. Timed latencies and savings are close to REPEAT2/REPEAT3 (see the REPEAT tables).\n"
           "- The same node's large and medium replays had 1 and 0 gaps over 1 s.\n"
           "- `run_logs/entry.log` and `outer.log` contain no warning or error lines.\n"
           "- The cause is not identifiable from the saved logs.\n")
out.append("\n## Hardware (source `E3_hardware.csv`, from each node's `logs/node_hardware.txt`)\n\n"
           + md(HW, ['folder', 'host', 'gpu_count', 'gpu_model', 'driver', 'cuda_driver_api', 'torch', 'torch_cuda', 'topo_GPU0_row', 'cpu_model', 'cpus', 'sockets', 'cores_per_socket', 'threads_per_core'],
                ['folder', 'node', 'GPUs', 'GPU model', 'driver', 'CUDA (driver)', 'torch', 'torch CUDA', 'topology GPU0 row', 'CPU', 'CPUs', 'sockets', 'cores/socket', 'threads/core']))
(RES / 'E3_SUMMARY.md').write_text(''.join(out))
print(''.join(out)[:3000])
