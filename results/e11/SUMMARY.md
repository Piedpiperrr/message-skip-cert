# E11 — parser-convention robustness of the certification boundary (Round 4)

Stage: `$DATA_DIR/P2_R4_E11_20260920T224016Z`  
Preregistration: `PREREG_E11.md`, SHA-256 `48b0d405aa2c59db91f53ccd4b1fea372e3dfa3894095b01f44050046af84083`, recorded 2026-09-20T22:41:00Z (before anything was read or computed from the saved outputs).  
CPU-only re-analysis of already-saved model outputs on the ClusterA login node. No model was run, no GPU and no PBS job was used. POST-HOC re-analysis (reviewer R4/E11); does not change any primary decision.

## Preregistration

| | |
|---|---|
| file | `PREREG_E11.md` |
| SHA-256 | `48b0d405aa2c59db91f53ccd4b1fea372e3dfa3894095b01f44050046af84083` |
| recorded (UTC) | 2026-09-20T22:41:00Z |
| record | `PREREG_E11.sha256` |

Written and hashed before any saved output was read. The reporting rules in it were not changed after the
results were seen. Deviations: `DEVIATIONS.md`.

## Step 1 — reproduction check: **PASS**

All 26 settings reproduce. For every setting the full 20-row calibration ledger recomputed from the saved
records matches the stored ledger exactly (520 rows: n, k and the exact-binomial p-value), each deployed q
is recovered from the records, and the development disagreement count and AUROC match the published values
(Tables 2 and 6 for the 14 main settings, E8 `SUMMARY.md` section 1 for the four E8 settings,
E6 `E6_RESULTS.md` for Text+fact, and `P2_R1_XFAM_.../results/analysis/dev_table.csv` and
`.../x1/results/analysis/dev_table.csv` for the seven cross-family settings).

| setting | deployed q | cal n @ q | cal k @ q | cal p @ q | dev dis./N | dev AUROC | paper dis./N | paper AUROC | status |
|---|---|---|---|---|---|---|---|---|---|
| small/OBQA/Text | 0.0 | — | — | — | 339/742 | 0.64143 | 339/742 | 0.641 | PASS |
| small/OBQA/C2C | 0.0 | — | — | — | 350/742 | 0.70023 | 350/742 | 0.7 | PASS |
| small/ARC/Text | 0.0 | — | — | — | 145/299 | 0.63399 | 145/299 | 0.634 | PASS |
| small/ARC/C2C | 0.0 | — | — | — | 160/299 | 0.64065 | 160/299 | 0.641 | PASS |
| medium/OBQA/Text | 0.0 | — | — | — | 174/742 | 0.78654 | 174/742 | 0.787 | PASS |
| medium/OBQA/C2C | 0.55 | 739 | 19 | 0.000694187 | 131/742 | 0.84011 | 131/742 | 0.84 | PASS |
| medium/ARC/Text | 0.0 | — | — | — | 52/299 | 0.74218 | 52/299 | 0.742 | PASS |
| medium/ARC/C2C | 0.6 | 290 | 1 | 5.63703e-06 | 48/299 | 0.90974 | 48/299 | 0.91 | PASS |
| large/OBQA/Text | 0.8 | 1064 | 18 | 1.15505e-08 | 72/742 | 0.87273 | 72/742 | 0.873 | PASS |
| large/OBQA/C2C | 0.8 | 1064 | 22 | 6.7085e-07 | 60/742 | 0.88265 | 60/742 | 0.883 | PASS |
| large/ARC/Text | 0.95 | 422 | 4 | 4.8015e-06 | 15/299 | 0.95188 | 15/299 | 0.952 | PASS |
| large/ARC/C2C | 0.9 | 404 | 7 | 0.000539697 | 12/299 | 0.90883 | 12/299 | 0.909 | PASS |
| large/MMLU-Pro/Text | 0.4 | 2358 | 67 | 1.33558e-07 | 561/2641 | 0.82147 | 561/2641 | 0.821 | PASS |
| large/MMLU-Pro/C2C | 0.4 | 2358 | 75 | 1.0127e-05 | 756/2641 | 0.84640 | 756/2641 | 0.846 | PASS |
| small/MMLU-Pro/Text | 0.0 | — | — | — | 1235/2641 | 0.64385 | 1235/2641 | 0.6438 | PASS |
| small/MMLU-Pro/C2C | 0.0 | — | — | — | 1591/2641 | 0.62582 | 1591/2641 | 0.6258 | PASS |
| medium/MMLU-Pro/Text | 0.0 | — | — | — | 1128/2641 | 0.71655 | 1128/2641 | 0.7166 | PASS |
| medium/MMLU-Pro/C2C | 0.0 | — | — | — | 1410/2641 | 0.76524 | 1410/2641 | 0.7652 | PASS |
| X1-Llama/OBQA/Text | 0.0 | — | — | — | 191/742 | 0.69268 | 191/742 | 0.6927 | PASS |
| X1-Llama/OBQA/C2C | 0.0 | — | — | — | 427/742 | 0.61789 | 427/742 | 0.6179 | PASS |
| X1-Llama/ARC/Text | 0.0 | — | — | — | 88/299 | 0.67789 | 88/299 | 0.6779 | PASS |
| X1-Llama/ARC/C2C | 0.0 | — | — | — | 174/299 | 0.61457 | 174/299 | 0.6146 | PASS |
| X2-OLMo/OBQA/Text | 0.0 | — | — | — | 172/742 | 0.78964 | 172/742 | 0.7896 | PASS |
| X2-OLMo/ARC/Text | 0.0 | — | — | — | 67/299 | 0.74916 | 67/299 | 0.7492 | PASS |
| X2-OLMo/MMLU-Pro/Text | 0.0 | — | — | — | 1112/2641 | 0.63261 | 1112/2641 | 0.6326 | PASS |
| large/OBQA/Text+fact | 0.75 | 999 | 22 | 4.83045e-06 | 76/742 | 0.88859 | 76/742 | 0.88859 | PASS |

## (a) E11-a — INVALID decomposition and both-parse diagnostic

Cell (4), both outputs INVALID, is counted as **agreement**, matching the frozen convention.
The both-parse columns are a diagnostic and are **not deployable** (the filter reads the reference output).

| setting | cell-3 share of dis. (cal) | both-parse q | dev dis. (bp) | dev AUROC (bp) | outcome |
|---|---|---|---|---|---|
| small/OBQA/Text | 0.1722 | no candidate accepted | 0.42044 | 0.65068 | unchanged |
| small/OBQA/C2C | 0.0969 | no candidate accepted | 0.45328 | 0.70725 | unchanged |
| small/ARC/Text | 0.2790 | no candidate accepted | 0.43750 | 0.65600 | unchanged |
| small/ARC/C2C | 0.2008 | no candidate accepted | 0.48106 | 0.64469 | unchanged |
| medium/OBQA/Text | 0.0460 | no candidate accepted | 0.22510 | 0.77947 | unchanged |
| medium/OBQA/C2C | 0.1983 | 0.55 | 0.15673 | 0.84916 | unchanged |
| medium/ARC/Text | 0.0448 | no candidate accepted | 0.16835 | 0.73648 | unchanged |
| medium/ARC/C2C | 0.2364 | 0.6 | 0.11930 | 0.90368 | unchanged |
| large/OBQA/Text | 0.0140 | 0.8 | 0.09704 | 0.87273 | unchanged |
| large/OBQA/C2C | 0.0472 | 0.8 | 0.08086 | 0.88265 | unchanged |
| large/ARC/Text | 0.0000 | 0.95 | 0.05017 | 0.95188 | unchanged |
| large/ARC/C2C | 0.0476 | 0.9 | 0.04013 | 0.90883 | unchanged |
| large/MMLU-Pro/Text | 0.0139 | 0.4 | 0.21071 | 0.82216 | unchanged |
| large/MMLU-Pro/C2C | 0.0355 | 0.4 | 0.28047 | 0.84949 | unchanged |
| small/MMLU-Pro/Text | 0.2225 | no candidate accepted | 0.41530 | 0.66365 | unchanged |
| small/MMLU-Pro/C2C | 0.3512 | no candidate accepted | 0.50431 | 0.69073 | unchanged |
| medium/MMLU-Pro/Text | 0.1176 | no candidate accepted | 0.39613 | 0.71259 | unchanged |
| medium/MMLU-Pro/C2C | 0.7068 | 0.15 | 0.27352 | 0.76932 | certifies under both-parse (was fallback) |
| X1-Llama/OBQA/Text | 0.1882 | no candidate accepted | 0.22475 | 0.72578 | unchanged |
| X1-Llama/OBQA/C2C | 0.1865 | no candidate accepted | 0.53582 | 0.64843 | unchanged |
| X1-Llama/ARC/Text | 0.3250 | no candidate accepted | 0.23574 | 0.68255 | unchanged |
| X1-Llama/ARC/C2C | 0.2381 | no candidate accepted | 0.50598 | 0.63710 | unchanged |
| X2-OLMo/OBQA/Text | 0.2250 | 0.45 | 0.18768 | 0.85476 | certifies under both-parse (was fallback) |
| X2-OLMo/ARC/Text | 0.4947 | 0.4 | 0.15504 | 0.88131 | certifies under both-parse (was fallback) |
| X2-OLMo/MMLU-Pro/Text | 0.3940 | 0.05 | 0.33482 | 0.70119 | certifies under both-parse (was fallback) |
| large/OBQA/Text+fact | 0.0235 | 0.75 | 0.10243 | 0.88859 | unchanged |

## (b) E11-b — two extraction conventions (19 A–D settings)

| setting | q V2 | q official | deploy status |
|---|---|---|---|
| small/OBQA/Text | 0.0 | 0.0 | neither |
| small/OBQA/C2C | 0.0 | 0.0 | neither |
| small/ARC/Text | 0.0 | 0.0 | neither |
| small/ARC/C2C | 0.0 | 0.0 | neither |
| medium/OBQA/Text | 0.0 | 0.0 | neither |
| medium/OBQA/C2C | 0.55 | 0.55 | both |
| medium/ARC/Text | 0.0 | 0.0 | neither |
| medium/ARC/C2C | 0.6 | 0.6 | both |
| large/OBQA/Text | 0.8 | 0.8 | both |
| large/OBQA/C2C | 0.8 | 0.7 | both |
| large/ARC/Text | 0.95 | 0.95 | both |
| large/ARC/C2C | 0.9 | 0.0 | V2 only |
| X1-Llama/OBQA/Text | 0.0 | 0.0 | neither |
| X1-Llama/OBQA/C2C | 0.0 | 0.0 | neither |
| X1-Llama/ARC/Text | 0.0 | 0.0 | neither |
| X1-Llama/ARC/C2C | 0.0 | 0.0 | neither |
| X2-OLMo/OBQA/Text | 0.0 | 0.0 | neither |
| X2-OLMo/ARC/Text | 0.0 | 0.0 | neither |
| large/OBQA/Text+fact | 0.75 | 0.75 | both |

**Intersection (6 settings): medium/OBQA/C2C;medium/ARC/C2C;large/OBQA/Text;large/OBQA/C2C;large/ARC/Text;large/OBQA/Text+fact.**
V2 only (1): large/ARC/C2C. Official only: none.

## (c) E11-c — Rule D (deployable INVALID routing)

| setting | Rule D q | dev cov. % all | dev cov. % parseable | cond. change rate | verdict |
|---|---|---|---|---|---|
| small/OBQA/Text | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| small/OBQA/C2C | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| small/ARC/Text | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| small/ARC/C2C | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| medium/OBQA/Text | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| medium/OBQA/C2C | 0.55 | 52.56 | 53.13 | 0.02821 | unchanged |
| medium/ARC/Text | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| medium/ARC/C2C | 0.6 | 63.21 | 63.64 | 0.02116 | unchanged |
| large/OBQA/Text | 0.8 | 77.09 | 77.09 | 0.03322 | unchanged |
| large/OBQA/C2C | 0.8 | 77.09 | 77.09 | 0.02273 | unchanged |
| large/ARC/Text | 0.95 | 94.98 | 94.98 | 0.03169 | unchanged |
| large/ARC/C2C | 0.9 | 90.30 | 90.30 | 0.01111 | unchanged |
| large/MMLU-Pro/Text | 0.4 | 40.44 | 40.53 | 0.03652 | unchanged |
| large/MMLU-Pro/C2C | 0.4 | 40.44 | 40.53 | 0.03371 | unchanged |
| small/MMLU-Pro/Text | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| small/MMLU-Pro/C2C | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| medium/MMLU-Pro/Text | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| medium/MMLU-Pro/C2C | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| X1-Llama/OBQA/Text | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| X1-Llama/OBQA/C2C | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| X1-Llama/ARC/Text | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| X1-Llama/ARC/C2C | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| X2-OLMo/OBQA/Text | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| X2-OLMo/ARC/Text | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| X2-OLMo/MMLU-Pro/Text | no candidate accepted | 0.00 | 0.00 | — | unchanged |
| large/OBQA/Text+fact | 0.75 | 72.24 | 72.24 | 0.02425 | unchanged |

New certifications: 0. Lost: 0.

## What does not change

No threshold, deployment, replay, latency number or frozen protocol is revised by E11. Each of E11-a, E11-b
and E11-c is a separate post hoc family and is labelled as such.
