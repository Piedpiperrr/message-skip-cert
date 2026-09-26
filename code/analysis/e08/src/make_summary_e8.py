"""E8 SUMMARY.md: every table and path from the frozen analysis outputs. Reads only this stage."""
from common_e8 import *
OUT=P/'analysis';A=read(P/'ANALYSIS_COMPLETE_E8.json');NV=read(P/'NUMERICAL_VALIDATION_E8.json')
led=read(OUT/'calibration/80_test_ledger.json');dep=read(OUT/'deployments/deployment_configs.json')
comp=A['compact'];orc=A['oracle'];stab=A['resplit'];d1=A['D1']
feas=read(P/'feasibility/CPU_FEASIBILITY.json');est=read(P/'feasibility/GPU_HOUR_ESTIMATE_REFINED.json')
val=sorted((P/'validation').glob('*/VALIDATION_*.json'))
def pct(x):return '' if x is None else f'{100*x:.2f}%'
def num(x,n=4):return '' if x is None else (f'{x:.{n}g}' if isinstance(x,float) else str(x))
L=[];w=L.append
w('# E8 — the MMLU-Pro column for the small and medium pairs')
w('')
w(f'Stage: `{P}`  ')
w(f'Protocol freeze: `PROTOCOL_FREEZE_E8.md`, SHA-256 `{read(P/"FREEZE_INDEX_E8.json")["PROTOCOL_FREEZE_E8_sha256"]}`, '
  f'recorded {read(P/"FREEZE_INDEX_E8.json")["freeze_utc"]} (before any new model output).  ')
w(f'Analysis completed: {A["utc"]}. Family: 4 settings x 20 candidates = **80 tests**, separate from every earlier family.')
w('')
w('## 1. The four settings')
w('')
w('| setting | dev disagree R vs ref | AUROC | q | dev coverage | changed/omitted | correct R / ref / policy | INVALID R / ref | re-split cert. rate | D1 differences (R/T/C) |')
w('|---|---|---|---|---|---|---|---|---|---|')
for m in comp:
    s=m['setting'];st=next(x for x in stab if x['setting']==s)
    ref='T' if m['reference']=='Text' else 'C'
    dd={x['pair']:x for x in d1 if x['pair']==m['pair']}
    dr=[x for x in d1 if x['pair']==m['pair']]
    dmap={x['action']:x['differences'] for x in dr}
    w(f"| {s} | {m['R_reference_disagreement_count']}/{m['N']} ({pct(m['R_reference_disagreement_prevalence'])}) | "
      f"{num(m['AUROC'])} | {m['q']:g}{' (fallback)' if m['q']==0 else ''} | {pct(m['coverage'])} | "
      f"{m['changed_over_omitted']} | {m['correct_R']} / {m['correct_reference']} / {m['correct_policy']} | "
      f"{m['invalid_R']} / {m['invalid_Text'] if ref=='T' else m['invalid_C2C']} | "
      f"{st['certification_rate']:.3f} | {dmap.get('R')}/{dmap.get('T')}/{dmap.get('C')} |")
w('')
w('Unit: the 2,641 development group representatives. Coverage = fraction of development questions the policy omits the '
  'reference call on (runs R instead); changed = of those, how many would have had a different answer. q = 0 means fallback '
  '(always run the reference), and then coverage and changed are 0 by construction.')
w('')
w('## 2. Oracle headroom (development representatives)')
w('')
w('| pair | acc R | acc Text | acc C2C | best fixed | oracle | gain over best fixed | gain over R |')
w('|---|---|---|---|---|---|---|---|')
for o in orc:
    w(f"| {o['pair']} | {pct(o['accuracy_R'])} | {pct(o['accuracy_Text'])} | {pct(o['accuracy_C2C'])} | "
      f"{o['best_fixed_action']} {pct(o['best_fixed_accuracy'])} | {pct(o['oracle_accuracy'])} | "
      f"{pct(o['oracle_gain_over_best_fixed'])} | {pct(o['oracle_gain_over_R'])} |")
w('')
w('## 3. Calibration ledger — all 80 tests')
w('')
w('Rule: on the 6,000 calibration representatives, at each of the 20 fit-quantile candidates (19 quantiles plus q=1), '
  'P[Bin(n, .05) <= k] <= .001; deploy the largest accepted q, otherwise fall back.')
w('')
w('| setting | q | threshold | n | k | p | CP(.999) | accepted |')
w('|---|---|---|---|---|---|---|---|')
for r in led:
    w(f"| {r['setting']} | {r['q']:g} | {num(r['threshold'],6) if r['threshold']!='Infinity' else 'Infinity'} | "
      f"{r['routed']} | {r['changed']} | {r['p_value']:.4g} | {r['CP_upper_0_999']:.4g} | {r['accepted']} |")
w('')
w('## 4. Re-split stability (200 re-drawn fit/calibration splits, E5-b rule)')
w('')
w('| setting | original | certification rate | match rate | verdict | median q | median dev coverage % |')
w('|---|---|---|---|---|---|---|')
for s in stab:
    w(f"| {s['setting']} | {s['original_outcome']} | {s['certification_rate']:.3f} | {s['match_rate']:.3f} | "
      f"{s['stable']} | {num(s['median_q'])} | {num(s['median_dev_coverage_pct'])} |")
w(f"\nSeed 0 reproduces the frozen split: **{stab[0]['seed0_reproduces_frozen_split']}**.")
w('')
w('## 5. Labels under the earlier parser D1')
w('')
w('| pair | action | N | differences | rate | V2 INVALID | D1 INVALID | V2 valid / D1 invalid | D1 valid / V2 invalid | both valid, different |')
w('|---|---|---|---|---|---|---|---|---|---|')
for r in d1:
    w(f"| {r['pair']} | {r['action']} | {r['N']} | {r['differences']} | {pct(r['difference_rate'])} | {r['V2_INVALID']} | "
      f"{r['D1_INVALID']} | {r['V2_valid_D1_invalid']} | {r['D1_valid_V2_invalid']} | {r['both_valid_different_label']} |")
w('')
w('## 6. Validation and smoke')
w('')
for f in val:
    d=read(f)
    if 'a_obqa_bit_for_bit' in d:
        a=d['a_obqa_bit_for_bit'];c=d['c_smoke']
        w(f"- **(a) {d['pair']}**: 16 saved OBQA fit rows reproduced bit for bit = **{a['all_bit_for_bit']}** "
          f"(action mismatches {len(a['action_mismatches'])}, probe mismatches {len(a['probe_mismatches'])}); "
          f"sources `{'`, `'.join(a['sources'])}`.")
        w(f"- **(c) {d['pair']} smoke**: 16 MMLU-Pro fit rows, INVALID R/T/C = "
          f"{c['invalid_counts']['R']}/{c['invalid_counts']['T']}/{c['invalid_counts']['C']} (threshold 4 per action, "
          f"exceeded: {c['exceeded'] or 'none'}); {c['measured_seconds_per_row']} s/row measured.")
    if 'b_large_mmlu_bit_for_bit' in d:
        b=d['b_large_mmlu_bit_for_bit']
        w(f"- **(b) large control**: 16 saved large-pair MMLU-Pro fit rows reproduced bit for bit with the unchanged large "
          f"configuration = **{b['all_bit_for_bit']}** (action mismatches {len(b['action_mismatches'])}, "
          f"probe mismatches {len(b['probe_mismatches'])}).")
w('')
w('Compared fields: `raw_answer`, `generated_token_ids`, `receiver_input_tokens`, `helper_message`, '
  '`helper_generated_token_ids`, `helper_input_tokens`; probes compared on exact `ProbeMax`, exact `p_labels`, '
  '`probe_ids`, `probe_ids_sha256`, `rendered_sha256`, `input_tokens`, `last_valid_position`. No gold was read.')
w('')
w('## 7. Completeness')
w('')
w(f"- {NV['rows_per_pair']} rows x 4 requests x 2 pairs = 96,256 requests; duplicate keys {NV['duplicate_request_keys']}, "
  f"missing IDs {NV['missing_IDs']}, input-hash mismatches {NV['input_hash_mismatches']}, "
  f"re-parsed actions {NV['reparsed_actions']}.")
w(f"- Splits: fit {NV['fit_reps']} / calibration {NV['cal_reps']} / development {NV['dev_reps']} group representatives; "
  f"group leakage {NV['group_leakage']}.")
w(f"- Gold opened only after the deployment configuration of every setting was written: `analysis/GOLD_OPENED.json`.")
w('')
w('## 8. Models, fusers and budget')
w('')
w('| pair | helper | receiver | fuser | projectors |')
w('|---|---|---|---|---|')
for pair in ['small','medium']:
    m=read(P/f'MODEL_SOURCE_INDEX_{pair}.json')['models']
    w(f"| {pair} | `{m['helper']['repo_id']}` @ `{m['helper']['revision'][:8]}` | `{m['receiver']['repo_id']}` @ "
      f"`{m['receiver']['revision'][:8]}` | `{m['fuser']['repo_id']}` @ `{m['fuser']['revision'][:8]}` "
      f"(`{m['fuser']['subfolder']}`) | {m['fuser']['projector_count']} |")
w('')
w(f"Refined budget estimate: **{est['totals']['productive_GPU_hours']} productive GPU-hours** "
  f"({est['totals']['pair_wall_hours']} pair-wall hours), {est['packing']['main_debug_jobs_estimated']} main debug jobs. "
  f"`feasibility/GPU_HOUR_ESTIMATE_REFINED.json`.")
w('')
w('## 9. Paths')
w('')
for k,v in [('protocol freeze','PROTOCOL_FREEZE_E8.md'),('freeze index','FREEZE_INDEX_E8.json'),
  ('budget authorization','BUDGET_AUTHORIZATION_E8.json'),
  ('CPU feasibility','feasibility/CPU_FEASIBILITY.json'),('budget estimate','feasibility/GPU_HOUR_ESTIMATE.json'),
  ('refined budget','feasibility/GPU_HOUR_ESTIMATE_REFINED.json'),('lane manifest','splits/E8_LANES.json'),
  ('records','shards/<pair>/lane_NN/{actions,probes}/<split>.jsonl'),
  ('thresholds','analysis/thresholds/<pair>_fit_thresholds.json'),
  ('80-test ledger','analysis/calibration/80_test_ledger.csv'),
  ('deployments','analysis/deployments/deployment_configs.json'),
  ('development table','analysis/development/split_summaries.csv'),
  ('compact 4 settings','analysis/development/compact_4_settings.csv'),
  ('oracle','analysis/development/oracle_headroom.csv'),
  ('re-split stability','analysis/development/resplit_stability.csv'),
  ('D1 differences','analysis/development/D1_label_differences.csv'),
  ('merged rows','analysis/merged/<pair>_rows.jsonl'),
  ('numerical validation','NUMERICAL_VALIDATION_E8.json'),('analysis receipt','ANALYSIS_COMPLETE_E8.json')]:
    w(f'- {k}: `{P}/{v}`')
rp=P/'REPLAY_E8'
if rp.exists() and (rp/'REPLAY_CLASS.json').exists():
    rc=read(rp/'REPLAY_CLASS.json')
    w('')
    w('## 10. End-to-end replay')
    w('')
    w(f"Settings replayed: {', '.join(rc['settings'])}; class: **{rc['class']}**. `{rp}`")
(P/'SUMMARY.md').write_text('\n'.join(L)+'\n')
print('SUMMARY.md written',len(L),'lines')
