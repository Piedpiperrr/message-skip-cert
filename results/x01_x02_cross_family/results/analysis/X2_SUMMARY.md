# X2 results (OLMo-2-1124-7B-Instruct receiver; Qwen2.5-7B saved Text messages; reference Text)

Generated 2026-09-19T19:43:57.486010+00:00 from `results/analysis/*.csv` (written by `src/analyze_x2.py`, as frozen in `PROTOCOL_FREEZE.md` SHA-256 1bc9fae4…).
Outputs: `results/runs/chain_00..07.jsonl` (job 7637635), hashed in `OUTPUT_HASHES.json` before gold was read. Certification and routes were hashed in `ROUTES_HASHES.json` before gold was read.

| setting | Dis./N | AUROC | Min UCB | q | Cov. (%) | Changed/R | Correct P/B |
|---|---|---|---|---|---|---|---|
| X2 obqa/Text | 172/742 | 0.790 | 0.118 | 0 | 0.0 | N/A | 516/516 |
| X2 arc/Text | 67/299 | 0.749 | 0.169 | 0 | 0.0 | N/A | 222/222 |
| X2 mmlu_pro/Text | 1112/2641 | 0.633 | 0.252 | 0 | 0.0 | N/A | 664/664 |

Certification: 60 tests (3 settings × 20 candidates), 0 accepted (`certification_ledger_60.csv`). All three settings fall back to fixed Text.

| benchmark | split | N | R correct | Text correct | R INVALID | Text INVALID |
|---|---|---|---|---|---|---|
| obqa | fit | 2100 | 1490 (71.0%) | 1483 (70.6%) | 67 (3.19%) | 114 (5.43%) |
| obqa | cal | 1366 | 939 (68.7%) | 947 (69.3%) | 59 (4.32%) | 81 (5.93%) |
| obqa | dev | 742 | 531 (71.6%) | 516 (69.5%) | 21 (2.83%) | 26 (3.50%) |
| arc | fit | 670 | 449 (67.0%) | 491 (73.3%) | 80 (11.94%) | 57 (8.51%) |
| arc | cal | 448 | 306 (68.3%) | 328 (73.2%) | 41 (9.15%) | 36 (8.04%) |
| arc | dev | 299 | 204 (68.2%) | 222 (74.2%) | 36 (12.04%) | 19 (6.35%) |
| mmlu_pro | fit | 3000 | 642 (21.4%) | 710 (23.7%) | 517 (17.23%) | 392 (13.07%) |
| mmlu_pro | cal | 6000 | 1295 (21.6%) | 1498 (25.0%) | 1025 (17.08%) | 785 (13.08%) |
| mmlu_pro | dev | 2641 | 591 (22.4%) | 664 (25.1%) | 450 (17.04%) | 363 (13.74%) |
