"""Write results/SUMMARY.md from the result CSVs (no new computation; every number is copied from a named CSV)."""
import csv, json, pathlib, datetime
NEW = pathlib.Path(__file__).resolve().parents[2]
RES = NEW / 'results'
rd = lambda n: list(csv.DictReader(open(RES / n)))


def md(rows, cols, heads=None):
    s = '| ' + ' | '.join(heads or cols) + ' |\n|' + '---|' * len(cols) + '\n'
    for r in rows:
        s += '| ' + ' | '.join(str(r.get(c, '')) for c in cols) + ' |\n'
    return s


A, B, C = rd('repro_checks_a_e4_V0.csv'), rd('repro_checks_b_large_arc.csv'), rd('repro_checks_c_features.csv')
E1A, E1G, E4, D = rd('e1_accuracy.csv'), rd('e1_agreement.csv'), rd('e4_null_controls.csv'), rd('d_certification.csv')
allpass = all(r['result'] == 'PASS' for r in A + B + C)
for r in A + B:
    r['agree'] = f"{r['parsed_agreement']}/{r['N']}"; r['exact'] = f"{r['raw_exact_match']}/{r['N']}"

# E1 compact: one row per pair x action
acc = {(r['pair'], r['action'], r['path']): r for r in E1A}
e1 = []
for g in E1G:
    o, u = acc[(g['pair'], g['action'], 'OFFICIAL')], acc[(g['pair'], g['action'], 'OURS')]
    e1.append(dict(pair=g['pair'], action=g['action'], off=o['correct_v2_of_500'], off_eval=o.get('correct_official_evaluator_reported', ''),
                   ours=u['correct_v2_of_500'], agree=f"{g['parsed_answer_agreement']}/{g['n_compared']}", exact=f"{g['raw_output_exact_match']}/{g['n_compared']}",
                   prompts=g['rendered_prompts_byte_identical_first3'], src=o['source']))
direc = []
for pair in ['small', 'medium', 'large']:
    for path in ['OFFICIAL', 'OURS']:
        r_, c_ = int(acc[(pair, 'Receiver-only', path)]['correct_v2_of_500']), int(acc[(pair, 'C2C', path)]['correct_v2_of_500'])
        direc.append(f"{pair} {path}: C2C {c_} vs R {r_} -> C2C {'above' if c_ > r_ else 'below' if c_ < r_ else 'equal to'} R")
e4 = []
for r in E4:
    N = int(r['N'])
    e4.append(dict(pop=f"{r['pair']}/{r['population']}", N=N, R=r['R_correct_paper_saved'], V0=r['V0_supp_same_job_R_replay_correct'], V1=r['V1_perm_correct'],
                   V2=r['V2_irrelevant_msg_correct'], c0=f"{100 * int(r['V0_supp_answer_change_vs_saved_R']) / N:.2f}", c1=r['answer_change_rate_R_vs_V1_pct'],
                   c2=r['answer_change_rate_R_vs_V2_pct'], orc=r['oracle_R_V1_V2'], best=r['best_of_R_V1_V2'], gain=r['oracle_gain_R_V1_V2_pp'],
                   porc=r['paper_oracle_R_T_C'], pgain=r['paper_oracle_gain_pp'], t1=r['matches_table1']))
for r in D:
    r['setting'] = f"{r['pair']}/{r['task']}/{r['reference']}" + (' *' if r['historically_tested'] else '')
    r['caln'] = f"{r['cal_n']}/{r['cal_k']}" if r['cal_n'] not in ('', '-') else '-'
    r['cov'] = r['dev_coverage_pct']; r['co'] = r['dev_changed_over_omitted']
    r['auc'] = f"{float(r['dev_AUROC']):.3f}" if r['dev_AUROC'] else ''
    r['new'] = ('q,cal: ' + ('unchanged' if 'unchanged' in r['status_q_cal'] else 'NEW') + '; dev: ' + ('unchanged' if 'unchanged' in r['status_dev'] else 'NEW'))

S = [f"# P2_R1_EXP results (ClusterA)\n\nGenerated {datetime.datetime.now(datetime.timezone.utc).isoformat()} by `src/ClusterA/make_summary_ClusterA.py` from the CSVs named below. "
     "Jobs: 7634910 (E1 OURS, E4, E2b; ClusterA debug, 2 nodes) and 7635393 (E1FIX: E1 OFFICIAL rerun + large ARC R/C2C; D4, D5). "
     "Output hashes were computed before any gold read (`OUTPUT_HASHES.json`, frozen `analyze_r1.py`) and re-verified unchanged before the checks. "
     "Parser: frozen P2_SCORING_V2 `parse_answer` (INVALID kept in N, counted wrong). The frozen analysis ran through the adapter `src/ClusterA/analyze_r1_ClusterA.py` (D6); its own summary is `SUMMARY_analyze_r1.md`.\n",
     f"\n## 1. Reproduction checks (ClusterA vs saved ClusterB) — {'ALL PASS' if allpass else 'NOT ALL PASS'}\n\n"
     "Criteria were fixed before looking at the results (header of `src/ClusterA/repro_checks_ClusterA.py`). "
     "(a) PASS = V0 correct equals Table 1 R and parsed agreement N/N. "
     "(b) PASS = correct equals Table 1 and parsed agreement 299/299. "
     "(c) PASS = max |dp| of the historical D <= 1e-3 and no routing flips at its deployed threshold.\n\n"
     "**(a) E4 V0 vs saved ClusterB R** (`repro_checks_a_e4_V0.csv`)\n\n",
     md(A, ['pair', 'population', 'N', 'table1_R', 'ClusterB_saved_R_correct', 'ClusterA_V0_correct', 'agree', 'exact', 'result'],
        ['pair', 'pop', 'N', 'Table 1 R', 'ClusterB saved R', 'ClusterA V0', 'parsed agree', 'raw exact', 'result']),
     "\n**(b) E1FIX large ARC dev (299) vs saved ClusterB** (`repro_checks_b_large_arc.csv`; ClusterB source P2_9 `results/large/validation_cases.jsonl`)\n\n",
     md(B, ['action', 'table1', 'ClusterB_saved_correct', 'ClusterA_correct', 'agree', 'exact', 'result'],
        ['action', 'Table 1', 'ClusterB saved', 'ClusterA', 'parsed agree', 'raw exact', 'result']),
     "\n**(c) E2b large/OBQA dev features vs saved ClusterB features** (`repro_checks_c_features.csv`)\n\n",
     md(C, ['N', 'dim', 'max_abs_dz', 'n_vectors_bit_identical', 'max_abs_dp_historical_D', 'routed_ClusterA', 'routed_ClusterB', 'routing_decision_flips', 'result'],
        ['N', 'dim', 'max abs dz', 'bit-identical vectors', 'max abs dp (hist. D)', 'routed ClusterA', 'routed ClusterB', 'flips', 'result']),
     "\nPer-question differences: `repro_mismatches.csv`.\n",
     "\n## 2. E1 C2C port fidelity (official OBQA test, N=500)\n\n"
     "Correct counts use the V2 parser; 'official eval.' is the official evaluator's own `is_correct` count. "
     "Small C2C OFFICIAL = task7 CSV (job 164991, reused, as frozen). Sources: `e1_accuracy.csv`, `e1_agreement.csv`, `e1_per_question.csv`, `e1_disagreements.csv`.\n\n",
     md(e1, ['pair', 'action', 'off', 'off_eval', 'ours', 'agree', 'exact', 'prompts'],
        ['pair', 'action', 'OFFICIAL correct', 'official eval.', 'OURS correct', 'parsed agree', 'raw exact', 'prompts identical (q0-2)']),
     '\n' + ''.join(f'- {d}\n' for d in direc),
     "\n## 3. E4 null controls (receiver-only)\n\n"
     "R = saved ClusterB development outputs (paper); V0 = unchanged rerun; V1 = options rotated by one; V2 = another question's helper message. "
     "Change rate = % of N with a different answer from R (INVALID as a symbol). Gain = (oracle - best single)/N in pp. Source: `e4_null_controls.csv`.\n\n",
     md(e4, ['pop', 'N', 'R', 'V0', 'V1', 'V2', 'c0', 'c1', 'c2', 'orc', 'best', 'gain', 'porc', 'pgain', 't1'],
        ['population', 'N', 'R', 'V0', 'V1', 'V2', 'chg R-V0 %', 'chg R-V1 %', 'chg R-V2 %', 'oracle{R,V1,V2}', 'best', 'gain pp', 'paper oracle{R,T,C}', 'paper gain pp', '= Table 1']),
     "\n## 4. Learned control D (POST-HOC, reviewer R1; 14 settings)\n\n"
     "Code: P2_R1_CPU `data_r1`/`common_r1`, frozen LR of `fit_head.py`, fit split only, target 1[o_R != o_b], fit-split order-statistic thresholds, "
     "deploy = largest q with P[Bin(n,.05) <= k] <= .001 (0 = fallback). '*' = historically tested (P2_RISK_CALIBRATION_BINARY). "
     "'unchanged' = copied from P2_R1_CPU `results/item4_learned_D.csv`; 'NEW' = this analysis (`src/ClusterA/d_certification_ClusterA.py`). "
     "Source: `d_certification.csv`; new-setting ledgers and fit checks: `d_certification_new_ledgers.csv`, `d_certification_new_fit_checks.csv`.\n\n",
     md(D, ['setting', 'deployed_q', 'caln', 'dev_N', 'cov', 'co', 'auc', 'new'],
        ['setting', 'deployed q', 'cal n/k', 'dev N', 'dev coverage %', 'dev changed/omitted', 'dev AUROC', 'status']),
     "\n## Other outputs\n\n- `e2b_features.csv`: inventory of the E2b feature files (frozen analyze_r1.py).\n"
     "- `SUMMARY_analyze_r1.md`: the frozen script's own summary.\n"]
(RES / 'SUMMARY.md').write_text(''.join(S))
print(''.join(S))
