# E21 inputs (P2_R9_E21_20260922T065220Z)

Paths are relative to the project root `iclr2027_p2/`. Nothing below is modified. Every value here was checked in Step 0 (REPRO.md).

## Frozen deployed q and tau (certification records)

The PREREG's one "[frozen q]" (large/MMLU-Pro/Text) was replaced by **[.40, tau = 3.838539123535156e-05]** from
`P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/deployments/deployment_configs.json` (sha256 df1be1b8cdad3222d5f9a5b25259597ff69316df73fc9078698f91f42c8a564a;
`deployments.T`: q 0.4, threshold 3.838539123535156e-05, chosen calibration 67/2358, p 1.335577911279424e-07, accepted_q .05-.40).
Every other bracketed q in the PREREG was checked against the stored records and the recomputed test (REPRO (a)). All agree:

| setting | PREREG bracket | stored q | stored tau | certification record (sha256) | recomputed cal k/n at frozen q |
|---|---|---|---|---|---|
| large/OBQA/Text | .80 | 0.8 | 0.001170039176940918 | `P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/deployments/large_obqa_T.json` (6f4f7baa8054e9e6e50397d07492408d0e381bdee3c45a526a8a877b7441814b) | 18/1064 |
| large/OBQA/C2C | (none) | 0.8 | 0.001170039176940918 | `.../deployments/large_obqa_C.json` (507a9c099e1836ab75cad162605a86f7e4dfd97d3bed1e8823d1a4f13dab641e) | see results/step0_recomputed_calibration_ledgers.csv |
| large/ARC/Text | .95 | 0.95 | 0.01800704002380371 | `.../deployments/large_arc_T.json` (30028f08c5423f324ec9762e9a91d2228bcbd0ad4decd2ea067a3c2f615a865c) | 4/422 |
| large/ARC/C2C | (none) | 0.9 | 0.0007095932960510254 | `.../deployments/large_arc_C.json` (a3391054c494b06edab5e67df330283ea611f34db5cdf2c14953c593221a18b5) | idem |
| large/MMLU-Pro/Text | [frozen q] -> .40 | 0.4 | 3.838539123535156e-05 | `P2_MMLU_PRO_BREADTH_STAGE1_20260916T002337Z/deployments/deployment_configs.json` T (df1be1b8cdad3222d5f9a5b25259597ff69316df73fc9078698f91f42c8a564a) | 67/2358 |
| large/MMLU-Pro/C2C | (none) | 0.4 | 3.838539123535156e-05 | same file, C | idem |
| medium/OBQA/C2C | .55 | 0.55 | 1.3113021850585938e-06 | `P2_MEDIUM_PAIR_BOUNDARY_EXTENSION_STAGE1_20260915T144407Z/execution_retry1_20260915T164957Z/deployments/obqa_C.json` (b8035cb6fe74f6a4bf738343e08f0efb4e01d5bbbf4da97f1f99b425f5589050) | 19/739 |
| medium/ARC/C2C | (none) | 0.6 | 3.5762786865234375e-07 | same folder, `deployments/arc_C.json` (dee8cb8c7e71f067c9b4cbdf3e53f3ec2dfaad575507f5584043a24395d660b5) | idem |
| large/OBQA/Text+fact | .75 | 0.75 | 0.0002611875534057617 | `P2_R2_GPU_20260919T220941Z/e6/analysis/E6_RESULTS.json` certified_q / certified_threshold (d4e2d6bd96ccda1791cdac8fcfcfdc2f6381fca56744eae0bb24c5ab33867cf9); ledger `e6/analysis/E6_LEDGER.csv` (f7b60722c59c3dba26d3eaf421b9ce03377744b9dd4a5c9d6aee1965da9bd89a) | 22/999 |
| Llama-3.1-8B/OBQA/Text | .60 | 0.6 | 0.009371757507324219 | `P2_R6_X3_20260921T052602Z/results/analysis/X3_PRE_GOLD.json` table (27ea14ab5c467e13c055c02fe4788040fa011e24c466676c1d1f294f0916a794); ledger `certification_ledger_40.csv` (3ea4aae33a2e881707eb4bd37a6525133c581b8333f6e4606db23bd26558eff6) | 21/800 |
| Llama-3.1-8B/ARC/Text | .70 | 0.7 | 0.014996349811553955 | same X3 files | 4/320 |
| SQuAD/Llama (control, s2) | (none) | 0.35 | 0.09916318852268603 | `P2_R8_E20F_20260922T003652Z/CERT_E20F.json` (3a370c00daec66bbb42647e96192851168be58bad35675d9167e2f238320dc5f) | not recomputed (control; only (i), (v) used) |

Stored ledgers compared row by row (20 rows, q/n/k) in REPRO (a): `P2_CONFIDENCE_REFERENCE_BOUNDARIES_.../summary/calibration_all_160.csv`
(b3038de19871c55222e69243299c1da7e459c382cc688d8d22ca5e20a7a896cc), `P2_MEDIUM_PAIR_.../execution_retry1_.../calibration/{obqa,arc}_C.csv` (ebe6361f6c78ad92777b14f7c58c899f28739c157d9bcac21e61640aff14838b, 2398f6e5f980c2290fa277176f65e0b7f8ded83757e6371fbaacf971ef9ba878),
`P2_MMLU_PRO_BREADTH_STAGE1_.../calibration/40_test_ledger.csv` (217c761e4b6fac176a096a68f4661f9975622d6f1a018daad5aa645d0a2c3518), E6_LEDGER.csv, X3 certification_ledger_40.csv.

## Data (all read through reused loaders; see scripts/e21_common.py docstring)

- fit/cal/dev u (stored ProbeMax), o_R, o_b (frozen parser V2, INVALID-normalized), the 20 frozen fit-quantile thresholds:
  `P2_R7_E17_20260921T183100Z/scripts/e17_common.py` `load` (-> E13 `e13_settings` -> E11 `e11_common.load` -> E5 `r2_common` ->
  R1 `data_r1.load_pair_dataset`; X3 records for Llama). Omission rule: `data_r1.route_mask` (omit iff u <= tau; q = 1 omits all).
  Change-rate test: `e17_common.ledger` / `deployed` (P[Bin(n, .05) <= k] <= .001, largest accepted q).
- dev arrays at the frozen q and panel replays: `P2_R8_E19_20260921T224942Z/scripts/e19_common.py` `dev`, `replay`, `bidx`, `ci`, `probe_ms`.
- X (341 parser-reviewed calibration questions: 208 OBQA, 133 ARC, 0 MMLU-Pro): `e11_common.exposed_ids` (= E5 r2_common).
- gold: OBQA/ARC fit/cal/dev `P2_SCORING_V2_20260912T191445Z/labels/full_{train,development}_P2_SCORING_V2.jsonl` (pair large, field gold; as
  analyze_x3.py), checked equal to `e9a_common.gold_map` on dev; MMLU-Pro `e9a_common.gold_map` (MMLU-Pro parquet);
  held-out 744 OBQA `c2c_reproduction_assets/datasets/allenai--openbookqa/main/train-00000-of-00001.parquet` answerKey (as E13 item3 / E16);
  sealed ARC and the E16 ARC test: `P2_FINAL_SEALED_ARC_CONFIRMATION_20260914T211958Z/inputs/evaluation_gold_after_prediction_freeze.jsonl` field gold (as E16).
- out of sample: held-out 744 `P2_R3_E9BC_20260920T061042Z/analysis/SEALED_ROUTES.jsonl` (policies large_obqa_T_q80, large_obqa_C_q80,
  large_obqa_TF_q75, medium_obqa_C_q55; ProbeMax, R_answer, reference_answer); Llama `P2_R7_E16_20260921T184114Z/results/analysis_oos/routes_llama_{obqa,arc}.jsonl`;
  sealed ARC `e17_common.load_sealed('T')` (records/e2e_requests.jsonl; R stored only where routed to R).
- E16-3 score m: `P2_R7_E16_20260921T184114Z/results/e163/qwen3_{8b,1_7b}_bf16_*.jsonl` (manifest `results/MANIFEST_jobB.sha256` checked),
  m = logsumexp(non-top label logits) - logsumexp(all), float64, via `lse`/`scores` extracted verbatim from `src/analyze_e16_3.py`.
- SQuAD control: `P2_R8_E20F_20260922T003652Z/results/E20F_devtest_rows.jsonl` (hash checked against OUTPUTS_HASH_devtest), s2 = `R.s2`,
  change = `e20_extract.changed` (pilot module).
- E4 V1: `P2_R1_EXP_20260919T050555Z/results/e4/*.jsonl` via `e9a_common.null_answers` (parsed_original, INVALID on missing/failed).
