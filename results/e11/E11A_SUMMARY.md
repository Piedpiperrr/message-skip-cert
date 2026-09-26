# E11-a — INVALID decomposition and the both-parse diagnostic

Stage: `$DATA_DIR/P2_R4_E11_20260920T224016Z`  
Preregistration: `PREREG_E11.md`, SHA-256 `48b0d405aa2c59db91f53ccd4b1fea372e3dfa3894095b01f44050046af84083`, recorded 2026-09-20T22:41:00Z (before anything was read or computed from the saved outputs).  
CPU-only re-analysis of already-saved model outputs on the ClusterA login node. No model was run, no GPU and no PBS job was used. POST-HOC re-analysis (reviewer R4/E11); does not change any primary decision.

## Convention

Each question falls in exactly one cell: (1) both outputs parse and the labels differ — a disagreement;
(2) both parse and agree — agreement; (3) exactly one output is INVALID — a disagreement under the frozen
convention; (4) **both outputs are INVALID — an agreement under the frozen convention**, because the two
answers are then the same single `INVALID` label. Cells (1)+(3) reproduce the frozen disagreement counts
exactly for all 26 settings (asserted in `scripts/e11a.py`).

The both-parse columns are a **diagnostic, not a deployable policy**: the filter reads the reference output.

## Result

All 9 currently certified policies
(medium/OBQA/C2C q=0.55, medium/ARC/C2C q=0.6, large/OBQA/Text q=0.8, large/OBQA/C2C q=0.8, large/ARC/Text q=0.95, large/ARC/C2C q=0.9, large/MMLU-Pro/Text q=0.4, large/MMLU-Pro/C2C q=0.4, large/OBQA/Text+fact q=0.75)
still certify on the both-parse subset, at the same q. No deployed policy loses certification.
4 settings that fall back under the frozen rule certify on the both-parse subset
(medium/MMLU-Pro/C2C, X2-OLMo/OBQA/Text, X2-OLMo/ARC/Text, X2-OLMo/MMLU-Pro/Text) — described only, not deployed.

Share of measured disagreement driven by exactly one INVALID output (cell 3):

| group | split | min share | max share | pooled share |
|---|---|---|---|---|
| 18 main settings | cal | 0.0000 | 0.7068 | 0.2740 |
| 18 main settings | dev | 0.0000 | 0.7092 | 0.2636 |
| 7 cross-family settings | cal | 0.1865 | 0.4947 | 0.3179 |
| 7 cross-family settings | dev | 0.1593 | 0.4030 | 0.3043 |
| Text+fact (E6) | cal | 0.0235 | 0.0235 | 0.0235 |
| Text+fact (E6) | dev | 0.0000 | 0.0000 | 0.0000 |

## Asymmetry

When the **reference** output is unparseable, a policy that omits the reference call really does change what
the deployed system returns, so counting it as a change is correct accounting, not a parser artifact. The
parser question bites only where the **receiver** output is unparseable. On calibration the two sides are
separated in `E11a_invalid_decomposition.csv` as `only_receiver_INVALID` and `only_reference_INVALID`.

## Per-setting table (cal = calibration split, bp = both-parse subset)

| setting | orig q | cells 1/2/3/4 (cal) | cell-3 share cal | cell-3 share dev | recv INVALID % cal | ref INVALID % cal | cal kept | dev kept | both-parse q | dev dis. (bp) | dev AUROC (bp) | dev cov. % (bp) | cond. change rate | outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| small/OBQA/Text | 0.0 | 495/750/103/18 | 0.1722 | 0.1504 | 4.47 | 5.71 | 1245/1366 | 685/742 | no candidate accepted | 0.42044 | 0.65068 | — | — | unchanged |
| small/OBQA/C2C | 0.0 | 578/726/62/0 | 0.0969 | 0.0714 | 4.47 | 0.07 | 1304/1366 | 717/742 | no candidate accepted | 0.45328 | 0.70725 | — | — | unchanged |
| small/ARC/Text | 0.0 | 168/197/65/18 | 0.2790 | 0.2276 | 11.16 | 11.38 | 365/448 | 256/299 | no candidate accepted | 0.43750 | 0.65600 | — | — | unchanged |
| small/ARC/C2C | 0.0 | 203/194/51/0 | 0.2008 | 0.2062 | 11.16 | 0.22 | 397/448 | 264/299 | no candidate accepted | 0.48106 | 0.64469 | — | — | unchanged |
| medium/OBQA/Text | 0.0 | 332/1018/16/0 | 0.0460 | 0.0517 | 1.02 | 0.15 | 1350/1366 | 733/742 | no candidate accepted | 0.22510 | 0.77947 | — | — | unchanged |
| medium/OBQA/C2C | 0.55 | 194/1121/48/3 | 0.1983 | 0.1374 | 1.02 | 2.93 | 1315/1366 | 721/742 | 0.55 | 0.15673 | 0.84916 | 53.81 | 0.02320 | unchanged |
| medium/ARC/Text | 0.0 | 64/381/3/0 | 0.0448 | 0.0385 | 0.67 | 0.00 | 445/448 | 297/299 | no candidate accepted | 0.16835 | 0.73648 | — | — | unchanged |
| medium/ARC/C2C | 0.6 | 42/391/13/2 | 0.2364 | 0.2917 | 0.67 | 3.12 | 433/448 | 285/299 | 0.6 | 0.11930 | 0.90368 | 65.61 | 0.01070 | unchanged |
| large/OBQA/Text | 0.8 | 141/1223/2/0 | 0.0140 | 0.0000 | 0.15 | 0.00 | 1364/1366 | 742/742 | 0.8 | 0.09704 | 0.87273 | 77.09 | 0.03322 | unchanged |
| large/OBQA/C2C | 0.8 | 121/1239/6/0 | 0.0472 | 0.0000 | 0.15 | 0.29 | 1360/1366 | 742/742 | 0.8 | 0.08086 | 0.88265 | 77.09 | 0.02273 | unchanged |
| large/ARC/Text | 0.95 | 12/436/0/0 | 0.0000 | 0.0000 | 0.00 | 0.00 | 448/448 | 299/299 | 0.95 | 0.05017 | 0.95188 | 94.98 | 0.03169 | unchanged |
| large/ARC/C2C | 0.9 | 20/427/1/0 | 0.0476 | 0.0000 | 0.00 | 0.22 | 447/448 | 299/299 | 0.9 | 0.04013 | 0.90883 | 90.30 | 0.01111 | unchanged |
| large/MMLU-Pro/Text | 0.4 | 1277/4704/18/1 | 0.0139 | 0.0107 | 0.28 | 0.05 | 5981/6000 | 2634/2641 | 0.4 | 0.21071 | 0.82216 | 40.51 | 0.03561 | unchanged |
| large/MMLU-Pro/C2C | 0.4 | 1686/4249/62/3 | 0.0355 | 0.0291 | 0.28 | 0.85 | 5935/6000 | 2617/2641 | 0.4 | 0.28047 | 0.84949 | 40.73 | 0.03189 | unchanged |
| small/MMLU-Pro/Text | 0.0 | 2181/3061/624/134 | 0.2225 | 0.2219 | 6.22 | 8.65 | 5242/6000 | 2314/2641 | no candidate accepted | 0.41530 | 0.66365 | — | — | unchanged |
| small/MMLU-Pro/C2C | 0.0 | 2259/2470/1223/48 | 0.3512 | 0.3388 | 6.22 | 15.77 | 4729/6000 | 2086/2641 | no candidate accepted | 0.50431 | 0.69073 | — | — | unchanged |
| medium/MMLU-Pro/Text | 0.0 | 2280/3388/304/28 | 0.1176 | 0.1294 | 5.48 | 0.52 | 5668/6000 | 2479/2641 | no candidate accepted | 0.39613 | 0.71259 | — | — | unchanged |
| medium/MMLU-Pro/C2C | 0.0 | 958/2427/2309/306 | 0.7068 | 0.7092 | 5.48 | 43.20 | 3385/6000 | 1499/2641 | 0.15 | 0.27352 | 0.76932 | 25.42 | 0.02887 | certifies under both-parse (was fallback) |
| X1-Llama/OBQA/Text | 0.0 | 302/980/70/14 | 0.1882 | 0.1728 | 4.47 | 2.71 | 1282/1366 | 703/742 | no candidate accepted | 0.22475 | 0.72578 | — | — | unchanged |
| X1-Llama/OBQA/C2C | 0.0 | 650/560/149/7 | 0.1865 | 0.1593 | 4.47 | 7.47 | 1210/1366 | 670/742 | no candidate accepted | 0.53582 | 0.64843 | — | — | unchanged |
| X1-Llama/ARC/Text | 0.0 | 108/276/52/12 | 0.3250 | 0.2955 | 11.16 | 5.80 | 384/448 | 263/299 | no candidate accepted | 0.23574 | 0.68255 | — | — | unchanged |
| X1-Llama/ARC/C2C | 0.0 | 208/170/65/5 | 0.2381 | 0.2701 | 11.16 | 5.58 | 378/448 | 251/299 | no candidate accepted | 0.50598 | 0.63710 | — | — | unchanged |
| X2-OLMo/OBQA/Text | 0.0 | 248/1012/72/34 | 0.2250 | 0.2384 | 4.32 | 5.93 | 1260/1366 | 698/742 | 0.45 | 0.18768 | 0.85476 | 44.41 | 0.01613 | certifies under both-parse (was fallback) |
| X2-OLMo/ARC/Text | 0.0 | 48/338/47/15 | 0.4947 | 0.4030 | 9.15 | 8.04 | 386/448 | 258/299 | 0.4 | 0.15504 | 0.88131 | 34.11 | 0.00000 | certifies under both-parse (was fallback) |
| X2-OLMo/MMLU-Pro/Text | 0.0 | 1489/3122/968/421 | 0.3940 | 0.3930 | 17.08 | 13.08 | 4611/6000 | 2016/2641 | 0.05 | 0.33482 | 0.70119 | 3.87 | 0.02564 | certifies under both-parse (was fallback) |
| large/OBQA/Text+fact | 0.75 | 166/1196/4/0 | 0.0235 | 0.0000 | 0.15 | 0.15 | 1362/1366 | 742/742 | 0.75 | 0.10243 | 0.88859 | 72.24 | 0.02425 | unchanged |

Files: `results/E11a_invalid_decomposition.csv` (four cells per setting per split),
`results/E11a_bothparse_diagnostic.csv`, `results/E11a_bothparse_grid.csv` (all 26 x 20 tests),
`results/E11a_cell3_share_aggregate.csv`.

Cross-check: the seven cross-family rows reproduce E5-e
(`P2_R2_CPU_20260919T220412Z/results/e5e_valid_only_diagnostic.csv`) exactly.
