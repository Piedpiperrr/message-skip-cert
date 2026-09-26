# E6 "Text+fact" — every pre-registered quantity of `PROTOCOL_FREEZE_E6.md` section 5

Run: ClusterA job `7637959` (debug, 2 nodes, 4 shards of 527 rows), 2026-09-19. All 2108 rows completed
(`e6/main/*.status.json`: `n_done == n_requested == 527` on every shard, `errors: []`, `PASS: true`,
`flag_off_byte_identical_5_fit_rows: true`, `gold_read: false`). Analysis `src/e6_analyze.py`, outputs
`e6/analysis/E6_RESULTS.json`, `E6_LEDGER.csv`, `E6_SUMMARY.csv`. Gold was read only here, after every
E6 output existed, as section 5 item 7 requires. Every reused source was hash-verified against the
table in section 3, and the per-row input identity was checked on **all 2108 used rows**, not a sample
(2108/2108 `probe_ids_sha256`, `id` and `legal_labels` matches).

## 3. Certified q and the 20-row ledger

**Certified q = 0.75**, threshold **2.611875534057617e-04** (frozen fit quantile, not refitted).
Accepted candidates: q = 0.05 … 0.75 (15 of 20). The first non-acceptance is q = 0.80
(n = 1064, k = 33, p = 1.63e-03 > 1e-3). Full ledger in `e6/analysis/E6_LEDGER.csv`:

| q | threshold | n | k | p | CP .999 upper | accepted |
|---|---|---|---|---|---|---|
| 0.50 | 1.1920928955078125e-07 | 683 | 2 | 4.16e-13 | 0.0163 | yes |
| 0.65 | 7.987022399902344e-06 | 870 | 11 | 2.38e-09 | 0.0292 | yes |
| 0.70 | 4.5418739318847656e-05 | 932 | 16 | 1.20e-07 | 0.0347 | yes |
| **0.75** | **2.611875534057617e-04** | **999** | **22** | **4.83e-06** | **0.0404** | **yes** |
| 0.80 | 1.170039176940918e-03 | 1064 | 33 | 1.63e-03 | 0.0511 | no |
| 0.85 | 8.580565452575684e-03 | 1135 | 57 | 0.549 | 0.0735 | no |

## 1, 2, 4, 5, 6, 7

| quantity | calibration (N = 1366) | development (N = 742) |
|---|---|---|
| 1. disagreement R vs Text+fact | 170 (0.12445) | 76 (0.10243) |
| — for reference, R vs frozen Text | 143 (0.10469) | 72 (0.09704) |
| 2. AUROC of ProbeMax on R-vs-Text+fact disagreement | 0.90838 | 0.88859 |
| — for reference, on R-vs-Text disagreement | 0.91856 | 0.87273 |
| 4. coverage at q = .75 (omitted / N) | 999/1366 (73.13%) | 536/742 (72.24%) |
| 4. changed / omitted at q = .75 | 22/999 | 13/536 |
| 5. accuracy, R | 1113 (0.8148) | 617 (0.8315) |
| 5. accuracy, frozen Text | 1178 (0.8624) | 645 (0.8693) |
| 5. accuracy, Text+fact | 1215 (0.8895) | 670 (0.9030) |
| 6. INVALID, R / Text / Text+fact (parser V2) | 2 / 0 / 2 | 0 / 0 / 0 |
| 6. runtime failures (distinct from INVALID) | 0 / 0 | 0 / 0 |
| 7. corrective vs R, whole split | 122 | 62 |
| 7. harmful vs R, whole split | 20 | 9 |
| 7. neutral (both wrong), whole split | 28 | 5 |
| 7. corrective / harmful / neutral on omitted questions only | 18 / 2 / 2 | 11 / 1 / 1 |

Text+fact is deployable, not a fallback: it changes the receiver-only answer on 12.4% of calibration
questions overall, but on only 2.2% (22/999) of the questions the certified policy omits, which is
what the test controls. Its accuracy is above both R (+7.5 pp on development) and the frozen Text
action (+3.4 pp on development), and its corrective changes outnumber the harmful ones roughly 6:1 on
both splits. The probe ranks Text+fact disagreements about as well as it ranks Text disagreements
(AUROC 0.908 / 0.889 vs 0.919 / 0.873).

## 6 (freeze section 6). End-to-end replay

`q = 0.75 > 0`, so the conditional replay is required. It was added to **node B of the E7 replay job**
(`P2_R2_E7_20260919T231531Z`, job `7638030`, 2 nodes, debug, 00:50:00) as a fourth sequential stage,
after MMLU-Pro and the medium pair: node B's budget is ~16 min of E7 replay plus ~3 min for the 256 E6
requests plus model loads, inside the 50-minute cap. Driver `e6replay/src/execute_e6replay.py`
(frozen 128-question OBQA panel, arms `fixed_TF` and `policy_TF` rotated by question ordinal, E3
protocol, batch size 1, no warm-up, cold requests kept, zero retries). Deployment file
`e6replay/protocol/e6_deployment.json` carries q and the threshold above. The analysis of the replay
(classification only: above zero / crosses zero / below zero, 2000 seed-0 paired bootstrap resamples,
versions (a) all requests and (b) cold questions excluded) comes in a later prompt.
