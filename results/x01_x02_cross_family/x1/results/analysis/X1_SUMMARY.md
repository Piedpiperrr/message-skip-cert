# X1 summary: Llama-3.2-1B-Instruct → Qwen3-0.6B, OBQA and ARC

Freeze: `PROTOCOL_FREEZE_X1.md` (sha 3b2d12c9…). Deviations: `../DEVIATIONS.md` C11–C17. Analysis: `src/analyze_x1.py` (sha 70469553…, as frozen), stdout in `results/analysis_stdout.txt`.
Order: OUTPUT_HASHES.json 20:45:24Z, then ROUTES_HASHES.json 20:45:25Z, then gold.

## Development table (dev representatives; source `dev_table.csv`, `certification_ledger_80.csv`)

| setting | Dis./N | AUROC | min UCB | q | coverage | changed/omitted | correct P/B |
|---|---|---|---|---|---|---|---|
| OBQA/Text | 191/742 | .693 | .095 | 0 | 0% | N/A | 333/333 |
| OBQA/C2C | 427/742 | .618 | .325 | 0 | 0% | N/A | 358/358 |
| ARC/Text | 88/299 | .678 | .296 | 0 | 0% | N/A | 145/145 |
| ARC/C2C | 174/299 | .615 | .247 | 0 | 0% | N/A | 146/146 |

Accepted tests: 0 of 80. All four settings fall back to the fixed reference.

## Accuracy and INVALID rates, % (representatives; source `accuracy_invalid_per_split.csv`)

| split | N | R acc | R inv | Text acc | Text inv | C2C acc | C2C inv |
|---|---|---|---|---|---|---|---|
| OBQA fit | 2100 | 39.6 | 4.7 | 50.0 | 3.2 | 46.3 | 7.0 |
| OBQA cal | 1366 | 39.1 | 4.5 | 49.5 | 2.7 | 47.5 | 7.5 |
| OBQA dev | 742 | 38.4 | 3.4 | 44.9 | 2.7 | 48.2 | 6.9 |
| ARC fit | 670 | 37.2 | 8.8 | 49.6 | 4.3 | 54.8 | 5.4 |
| ARC cal | 448 | 38.8 | 11.2 | 53.3 | 5.8 | 56.9 | 5.6 |
| ARC dev | 299 | 36.8 | 10.7 | 48.5 | 4.7 | 48.8 | 5.7 |

R values are the small pair's saved outputs (same receiver).
