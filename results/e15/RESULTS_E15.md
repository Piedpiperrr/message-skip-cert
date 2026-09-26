# E15 results (login node, CPU only, no model, no PBS job)

Run directory: `P2_R6_E15_20260921T072336Z/` (ClusterA, repo root `$DATA_DIR`).
Preregistration: `PREREG_E15.md`, SHA-256 `d2e6fc2b3798084032ab4ad12b7d18c8538271ad72d9e71b0598038a59f6d45a`, hashed 2026-09-21T07:23:54Z
(`PREREG_E15.sha256`). First E15 computation: `scripts/step2_repro.py`, started 2026-09-21T07:30:54Z (`logs/step2.log`).
Before that, only record structure was inspected (field names, arm counts, source code). Label: POST-HOC re-analysis (E15);
does not change any primary decision.

Scripts: `scripts/e15_common.py` (loaders; reuses `P2_R5_E13_.../scripts/e13_settings.py` → `P2_R4_E11_.../scripts/e11_common.py`
→ E5 `r2_common` / R1 `common_r1`, `data_r1`, all unchanged), `scripts/step2_repro.py`, `scripts/e15_1.py`, `scripts/e15_2.py`,
`scripts/make_tables.py` (formatting only), `scripts/run_audited.py` (re-runs a script under a file-open audit hook).
All three analysis scripts were run twice. The second run used the audit hook, and its 13 result CSVs are byte-identical
to the first run's (`logs/run1/`). Every project file read is listed in `results/FILES_READ.txt` (228 files).
Nothing outside this folder was opened for writing (`logs/files_opened_*.txt`).

## Step 2. Reproduction checks: all pass

- (i) Certification, 25 settings (`results/step2_repro_certification.csv`): recomputed from the stored frozen fit thresholds and
  the calibration records. 8 deploy with the paper's q (medium OBQA/ARC C2C .55/.60; large OBQA Text/C2C .80/.80; large ARC
  Text/C2C .95/.90; large MMLU-Pro Text/C2C .40/.40), and 17 fall back. In all 25 settings the stored thresholds equal the
  fit-split order statistics ceil(j N_fit/20) of the stored fit scores. Split sizes used: OBQA 2,100/1,366/742,
  ARC 670/448/299, MMLU-Pro 3,000/6,000/2,641. ARC fit has 671 question ids in 670 groups, and the thresholds are the order
  statistics of the 670 group representatives.
- (ii) Table 2 savings (`results/step2_repro_table2.csv`): paired mean of (fixed − policy) latency over the 128 panel questions
  of the original-configuration replays: 346.3, 8.2, 517.1, 36.6, 717.6, 110.9, 79.7, 100.7 ms. All eight match to 0.1 ms.
- Component source check (`results/e15_1_checks.csv`): the per-question development records behind Table "Same-target
  baselines" (ii) reproduce its Ref / R / Policy columns to 0.1 ms and the T2 development coverage to 4 decimals for all 8
  deployed settings.

## E15-1. Predicting certification from the fit split alone

Summary (`results/e15_1_summary.csv`; per candidate `results/e15_1_candidates.csv`; per setting `results/e15_1_per_setting.csv`):
- x = **8/8** deployed settings predicted to deploy; y = **17/17** fallback settings predicted to fall back.
- Over the 8 settings where both deploy: median |q_hat − q| = **0** grid steps, max **1** (large OBQA C2C +1; large ARC Text −1;
  large MMLU-Pro C2C −1). Median |actual dev coverage − predicted coverage| = **.0272** (2.7 points).
- Saving error over the eight policies, measured = original-configuration replay mean (Table 2):
  - fit-predicted coverage times measured development latency gap: median |pred − meas| **15.4 ms**, median relative **.126**;
  - same formula with actual panel coverage: median |pred − meas| **15.3 ms**, median relative **.119**.
- **Paper rule: "predicts"** (x = 8 ≥ 7, y = 17 ≥ 15, median |q_hat − q| = 0 ≤ 1).

Main-text sentence (Sec. 5), filled in from these numbers:
"On the 25 settings with fit-split reference outputs, a plug-in rule that uses the fit split's shadow reference outputs and
ProbeMax scores but no labels predicts the certification boundary: it predicts deployment in 8/8 deployed settings and fallback
in 17/17 fallback settings, with a median grid-step error of 0 (maximum 1), a median coverage error of 2.7 percentage points,
and a median saving error of 15.4 ms (12.6%)." (The saving error is the preregistered primary version, fit-predicted
coverage; with the panel coverage it is 15.3 ms (11.9%).)

Note for reading the coverage column: because the thresholds are fit order statistics, the predicted fit coverage at q_hat
equals q_hat whenever there are no ties at the threshold (e.g. .8000). The coverage error is therefore mostly the shift
from the fit split to the development split. It is also inflated by 1/20 when q_hat ≠ q.

## E15-2. Busy GPU time saved

- Qualification (`results/e15_2_qualification.csv`): **no replay source qualifies for all eight policies.**
  - (a) Original configuration: qualifies for the 4 large OBQA/ARC policies (ClusterB, `P2_FROZEN_POLICY_E2E_VALIDATION_.../records/e2e_requests.jsonl`).
    Every request carries per-forward CUDA-event intervals for the helper, the receiver and each of the 36 fuser projectors,
    plus a probe prefill+projection event, all read after `torch.cuda.synchronize` on both GPUs. The medium replay
    (`P2_MEDIUM_PAIR_E2E_STAGE2_.../records/e2e_requests.jsonl`) and the MMLU-Pro replay
    (`P2_MMLU_PRO_E2E_STAGE2_.../records/four_arm_requests.jsonl`) record one wall interval for the whole action
    (`complete_native_action_decode_parser_ms`) and no per-stage timer.
  - (b) E3 repeats: the large-pair records qualify for the same 4 policies; the medium and MMLU-Pro records do not (one action
    interval). E7: no per-stage timer for any policy. The large E7 records hold one `GPU_forward_event_sum_ms` per request;
    the medium and MMLU-Pro E7 records hold none.
- **Paper-rule branch (2).** Sec. 7: replace "We measure latency, not the helper compute omission also saves," with
  "busy GPU time is available for 4 of eight policies (Appendix)", and keep "and the same-target baselines have component
  estimates only". Sec. 4.4 is unchanged: its conditional statements belong to branch (1), and nothing else changes.
- Available values, from the highest-preference qualifying source, (a) original configuration. Paired bootstrap over the same
  128 questions, seed 0, 2,000 resamples, using the replay's stored index matrices; the latency intervals reproduce the
  replay's stored intervals exactly.
  - large/OBQA/Text: busy saving 513.5 [448.7, 574.2]; latency 517.1 [447.8, 583.6]; D −3.6 [−9.9, 8.3]; ratio .993
  - large/OBQA/C2C: busy 32.3 [14.4, 51.8]; latency 36.6 [18.0, 56.8]; D −4.3 [−6.3, −3.2]; ratio .882
  - large/ARC/Text: busy 705.2 [659.1, 750.0]; latency 717.6 [670.6, 763.2]; D −12.4 [−13.2, −11.6]; ratio .983
  - large/ARC/C2C: busy 106.6 [77.8, 138.2]; latency 110.9 [82.0, 142.8]; D −4.3 [−4.6, −3.9]; ratio .961
  - medium OBQA/ARC C2C, large MMLU-Pro Text/C2C: not available (no qualifying replay source).
  The ratio is reported for all four because every latency-saving interval lies above zero.
  Range for the appendix: Text 513.5–705.2 ms, C2C 32.3–106.6 ms (large pair only).
- Check (`results/e15_2_checks.csv`): on every fixed request, busy time equals the replay's own `GPU_forward_event_sum_ms`
  (max |diff| 0.0 ms). On policy requests it exceeds it by 0.90–0.99 ms, which is the probe's last-position projection; the
  exception is the cold first OBQA/Text probe (+49.5 ms).
- Component accounting records (descriptive, `results/e15_2_component_descriptive.csv`): busy time cannot be formed. The
  historical R/Text/C2C development request records store one total latency per request, and only the probe records hold a
  GPU-event interval. For comparison, the component-recomposed latency savings (Table baselines (ii), Ref − Policy) are
  68.3, 105.4, 515.6, 20.0, 705.9, 93.0, 345.3 and 26.7 ms (medium OBQA C2C, medium ARC C2C, large OBQA Text/C2C,
  large ARC Text/C2C, large MMLU-Pro Text/C2C).

## E15-1 per setting (results/e15_1_per_setting.csv)

| setting | actual | q | predicted | q_hat | steps (q_hat-q) | dev cov | pred fit cov | abs cov err | measured saving (ms) | pred saving, fit cov (ms) | pred saving, panel cov (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| small/OBQA/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| small/OBQA/C2C | fallback | - | fallback | - |  |  |  |  |  |  |  |
| small/ARC/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| small/ARC/C2C | fallback | - | fallback | - |  |  |  |  |  |  |  |
| medium/OBQA/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| medium/OBQA/C2C | deploy | 0.55 | deploy | 0.55 | 0 | 0.526 | 0.551 | 0.025 | 79.7 | 64.7 | 58.4 |
| medium/ARC/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| medium/ARC/C2C | deploy | 0.60 | deploy | 0.60 | 0 | 0.632 | 0.610 | 0.022 | 100.7 | 98.9 | 97.0 |
| large/OBQA/Text | deploy | 0.80 | deploy | 0.80 | 0 | 0.771 | 0.800 | 0.029 | 517.1 | 536.6 | 506.1 |
| large/OBQA/C2C | deploy | 0.80 | deploy | 0.85 | 1 | 0.771 | 0.850 | 0.079 | 36.6 | 26.6 | 19.0 |
| large/ARC/Text | deploy | 0.95 | deploy | 0.90 | -1 | 0.950 | 0.900 | 0.050 | 717.6 | 670.6 | 700.4 |
| large/ARC/C2C | deploy | 0.90 | deploy | 0.90 | 0 | 0.903 | 0.900 | 0.003 | 110.9 | 88.9 | 88.6 |
| large/MMLU-Pro/Text | deploy | 0.40 | deploy | 0.40 | 0 | 0.405 | 0.400 | 0.005 | 346.3 | 360.9 | 335.4 |
| large/MMLU-Pro/C2C | deploy | 0.40 | deploy | 0.35 | -1 | 0.405 | 0.352 | 0.053 | 8.2 | -7.7 | -5.1 |
| small/MMLU-Pro/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| small/MMLU-Pro/C2C | fallback | - | fallback | - |  |  |  |  |  |  |  |
| medium/MMLU-Pro/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| medium/MMLU-Pro/C2C | fallback | - | fallback | - |  |  |  |  |  |  |  |
| X1-Llama/OBQA/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| X1-Llama/OBQA/C2C | fallback | - | fallback | - |  |  |  |  |  |  |  |
| X1-Llama/ARC/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| X1-Llama/ARC/C2C | fallback | - | fallback | - |  |  |  |  |  |  |  |
| X2-OLMo/OBQA/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| X2-OLMo/ARC/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |
| X2-OLMo/MMLU-Pro/Text | fallback | - | fallback | - |  |  |  |  |  |  |  |

## E15-1 saving model inputs (8 policies)

| setting | mean c_b | mean c_R | gap | mean c_s | pred fit cov | panel cov | measured | pred (fit) | abs err | rel err | pred (panel) | abs err | rel err |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| medium/OBQA/C2C | 394.5 | 216.4 | 178.0 | 33.4 | 0.5510 | 0.5156 | 79.7 | 64.7 | 14.9 | 0.187 | 58.4 | 21.2 | 0.266 |
| medium/ARC/C2C | 445.5 | 229.1 | 216.4 | 33.2 | 0.6104 | 0.6016 | 100.7 | 98.9 | 1.8 | 0.018 | 97.0 | 3.7 | 0.037 |
| large/OBQA/Text | 978.5 | 253.6 | 724.9 | 43.2 | 0.8000 | 0.7578 | 517.1 | 536.6 | 19.5 | 0.038 | 506.1 | 11.1 | 0.021 |
| large/OBQA/C2C | 335.8 | 253.6 | 82.2 | 43.2 | 0.8500 | 0.7578 | 36.6 | 26.6 | 10.0 | 0.272 | 19.0 | 17.5 | 0.480 |
| large/ARC/Text | 1060.8 | 267.6 | 793.2 | 43.3 | 0.9000 | 0.9375 | 717.6 | 670.6 | 47.0 | 0.066 | 700.4 | 17.3 | 0.024 |
| large/ARC/C2C | 414.4 | 267.6 | 146.8 | 43.3 | 0.9000 | 0.8984 | 110.9 | 88.9 | 22.1 | 0.199 | 88.6 | 22.3 | 0.201 |
| large/MMLU-Pro/Text | 1292.0 | 274.2 | 1017.8 | 46.2 | 0.4000 | 0.3750 | 346.3 | 360.9 | 14.6 | 0.042 | 335.4 | 10.9 | 0.031 |
| large/MMLU-Pro/C2C | 383.9 | 274.2 | 109.7 | 46.2 | 0.3517 | 0.3750 | 8.2 | -7.7 | 15.9 | 1.930 | -5.1 | 13.3 | 1.619 |

## E15-1 summary (results/e15_1_summary.csv)

- n_settings: 25
- n_deployed: 8
- n_fallback: 17
- x_deployed_predicted_deploy: 8
- y_fallback_predicted_fallback: 17
- n_both_deploy: 8
- median_abs_grid_steps: 0.0
- max_abs_grid_steps: 1
- median_abs_coverage_error: 0.02722821203953285
- median_abs_saving_err_fitcov_ms: 15.414283008781744
- median_rel_saving_err_fitcov: 0.12641523261093335
- median_abs_saving_err_panelcov_ms: 15.311992023503567
- median_rel_saving_err_panelcov: 0.11887688104011149
- paper_rule: predicts

## E15-2 source qualification (results/e15_2_qualification.csv)

| setting | source | qualifies | reason |
|---|---|---|---|
| medium/OBQA/C2C | (a) original configuration | False | no per-stage timer (one action wall interval) |
| medium/OBQA/C2C | (b) second configuration E3 REPEAT1 | False | no per-stage timer (one action wall interval) |
| medium/OBQA/C2C | (b) second configuration E3 REPEAT2 | False | no per-stage timer (one action wall interval) |
| medium/OBQA/C2C | (b) second configuration E3 REPEAT3 | False | no per-stage timer (one action wall interval) |
| medium/OBQA/C2C | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval) |
| medium/ARC/C2C | (a) original configuration | False | no per-stage timer (one action wall interval) |
| medium/ARC/C2C | (b) second configuration E3 REPEAT1 | False | no per-stage timer (one action wall interval) |
| medium/ARC/C2C | (b) second configuration E3 REPEAT2 | False | no per-stage timer (one action wall interval) |
| medium/ARC/C2C | (b) second configuration E3 REPEAT3 | False | no per-stage timer (one action wall interval) |
| medium/ARC/C2C | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval) |
| large/OBQA/Text | (a) original configuration | True | every stage separately timed per request |
| large/OBQA/Text | (b) second configuration E3 REPEAT1 | True | every stage separately timed per request |
| large/OBQA/Text | (b) second configuration E3 REPEAT2 | True | every stage separately timed per request |
| large/OBQA/Text | (b) second configuration E3 REPEAT3 | True | every stage separately timed per request |
| large/OBQA/Text | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval, GPU_forward_event_sum_ms is one sum per request) |
| large/OBQA/C2C | (a) original configuration | True | every stage separately timed per request |
| large/OBQA/C2C | (b) second configuration E3 REPEAT1 | True | every stage separately timed per request |
| large/OBQA/C2C | (b) second configuration E3 REPEAT2 | True | every stage separately timed per request |
| large/OBQA/C2C | (b) second configuration E3 REPEAT3 | True | every stage separately timed per request |
| large/OBQA/C2C | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval, GPU_forward_event_sum_ms is one sum per request) |
| large/ARC/Text | (a) original configuration | True | every stage separately timed per request |
| large/ARC/Text | (b) second configuration E3 REPEAT1 | True | every stage separately timed per request |
| large/ARC/Text | (b) second configuration E3 REPEAT2 | True | every stage separately timed per request |
| large/ARC/Text | (b) second configuration E3 REPEAT3 | True | every stage separately timed per request |
| large/ARC/Text | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval, GPU_forward_event_sum_ms is one sum per request) |
| large/ARC/C2C | (a) original configuration | True | every stage separately timed per request |
| large/ARC/C2C | (b) second configuration E3 REPEAT1 | True | every stage separately timed per request |
| large/ARC/C2C | (b) second configuration E3 REPEAT2 | True | every stage separately timed per request |
| large/ARC/C2C | (b) second configuration E3 REPEAT3 | True | every stage separately timed per request |
| large/ARC/C2C | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval, GPU_forward_event_sum_ms is one sum per request) |
| large/MMLU-Pro/Text | (a) original configuration | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/Text | (b) second configuration E3 REPEAT1 | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/Text | (b) second configuration E3 REPEAT2 | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/Text | (b) second configuration E3 REPEAT3 | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/Text | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/C2C | (a) original configuration | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/C2C | (b) second configuration E3 REPEAT1 | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/C2C | (b) second configuration E3 REPEAT2 | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/C2C | (b) second configuration E3 REPEAT3 | False | no per-stage timer (one action wall interval) |
| large/MMLU-Pro/C2C | (b) second configuration E7 (ORIGINAL arm vs FIXED) | False | no per-stage timer (one action wall interval) |

## E15-2 busy GPU time, original configuration (results/e15_2_busy_savings.csv)

| setting | N | omitted | busy saving ms [95%] | latency saving ms [95%] | D ms [95%] | busy/latency |
|---|---|---|---|---|---|---|
| medium/OBQA/C2C | - | - | not available (no qualifying replay source) | - | - | - |
| medium/ARC/C2C | - | - | not available (no qualifying replay source) | - | - | - |
| large/OBQA/Text | 128 | 97 | 513.5 [448.7, 574.2] | 517.1 [447.8, 583.6] | -3.6 [-9.9, 8.3] | 0.993 |
| large/OBQA/C2C | 128 | 97 | 32.3 [14.4, 51.8] | 36.6 [18.0, 56.8] | -4.3 [-6.3, -3.2] | 0.882 |
| large/ARC/Text | 128 | 120 | 705.2 [659.1, 750.0] | 717.6 [670.6, 763.2] | -12.4 [-13.2, -11.6] | 0.983 |
| large/ARC/C2C | 128 | 115 | 106.6 [77.8, 138.2] | 110.9 [82.0, 142.8] | -4.3 [-4.6, -3.9] | 0.961 |
| large/MMLU-Pro/Text | - | - | not available (no qualifying replay source) | - | - | - |
| large/MMLU-Pro/C2C | - | - | not available (no qualifying replay source) | - | - | - |

### Stage means per request (ms; CUDA-event intervals)

| setting | fixed: helper | fixed: fuser | fixed: receiver | fixed busy | policy: probe | policy: helper | policy: fuser | policy: receiver | policy busy |
|---|---|---|---|---|---|---|---|---|---|
| large/OBQA/Text | 737.6 | 0.0 | 265.4 | 1003.0 | 53.4 | 174.6 | 0.0 | 261.5 | 489.5 |
| large/OBQA/C2C | 25.6 | 72.0 | 253.0 | 350.6 | 40.4 | 6.2 | 17.1 | 254.6 | 318.3 |
| large/ARC/Text | 807.3 | 0.0 | 263.2 | 1070.5 | 40.5 | 53.6 | 0.0 | 271.2 | 365.3 |
| large/ARC/C2C | 26.5 | 71.1 | 331.9 | 429.6 | 40.4 | 2.7 | 7.2 | 272.7 | 323.0 |
