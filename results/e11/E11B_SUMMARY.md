# E11-b — intersection of two extraction conventions

Stage: `$DATA_DIR/P2_R4_E11_20260920T224016Z`  
Preregistration: `PREREG_E11.md`, SHA-256 `48b0d405aa2c59db91f53ccd4b1fea372e3dfa3894095b01f44050046af84083`, recorded 2026-09-20T22:41:00Z (before anything was read or computed from the saved outputs).  
CPU-only re-analysis of already-saved model outputs on the ClusterA login node. No model was run, no GPU and no PBS job was used. POST-HOC re-analysis (reviewer R4/E11); does not change any primary decision.

## Scope

The official C2C evaluator's extraction (`rosetta/utils/evaluate.py::extract_answer_from_content`) reads
option letters A–D only, so it applies to the OBQA and ARC settings, not to MMLU-Pro (A–J).
Applicable: **19 settings** (12 main, 4 X1-Llama, 2 X2-OLMo, 1 Text+fact). The saved raw calibration and
development outputs are relabelled with it; the 20 fit-split thresholds are unchanged and are not refitted.

`X` is the E5-a exposure set: the 341 calibration questions whose raw outputs were reviewed with gold during
V2 parser rule development.

## Result — the intersection is SMALLER than the current deployed set

- deployed under frozen V2: **7** — medium/OBQA/C2C;medium/ARC/C2C;large/OBQA/Text;large/OBQA/C2C;large/ARC/Text;large/ARC/C2C;large/OBQA/Text+fact
- deployed under the official extractor: **6**
- **intersection (6)**: medium/OBQA/C2C;medium/ARC/C2C;large/OBQA/Text;large/OBQA/C2C;large/ARC/Text;large/OBQA/Text+fact
- **V2 only, i.e. flips to fallback under the official extractor (1)**: large/ARC/C2C
- official only (0): none

q under V2 → q under the official extractor, for the V2-deployed settings:

| setting | q (V2) | q (official) |
|---|---|---|
| medium/OBQA/C2C | 0.55 | 0.55 |
| medium/ARC/C2C | 0.6 | 0.6 |
| large/OBQA/Text | 0.8 | 0.8 |
| large/OBQA/C2C | 0.8 | 0.7 |
| large/ARC/Text | 0.95 | 0.95 |
| large/ARC/C2C | 0.9 | 0.0 |
| large/OBQA/Text+fact | 0.75 | 0.75 |

Both facts named in the preregistration reproduce: **large/ARC/C2C** flips to fallback and
**large/OBQA/C2C** drops to q = .70.

## Per-setting table

| setting | q V2 | q official | deployed under | cal rows differ | … inside X | … outside X | dev rows differ | cal d-label differs | E5-a reproduced |
|---|---|---|---|---|---|---|---|---|---|
| small/OBQA/Text | 0.0 | 0.0 | neither | 121 | 121 | 0 | 57 | 66 | True |
| small/OBQA/C2C | 0.0 | 0.0 | neither | 63 | 63 | 0 | 26 | 15 | True |
| small/ARC/Text | 0.0 | 0.0 | neither | 83 | 83 | 0 | 43 | 38 | True |
| small/ARC/C2C | 0.0 | 0.0 | neither | 53 | 53 | 0 | 35 | 5 | True |
| medium/OBQA/Text | 0.0 | 0.0 | neither | 16 | 3 | 13 | 11 | 5 | True |
| medium/OBQA/C2C | 0.55 | 0.55 | both | 53 | 10 | 43 | 25 | 22 | True |
| medium/ARC/Text | 0.0 | 0.0 | neither | 6 | 2 | 4 | 2 | 5 | True |
| medium/ARC/C2C | 0.6 | 0.6 | both | 19 | 9 | 10 | 16 | 9 | True |
| large/OBQA/Text | 0.8 | 0.8 | both | 2 | 2 | 0 | 0 | 1 | True |
| large/OBQA/C2C | 0.8 | 0.7 | both | 24 | 24 | 0 | 11 | 21 | True |
| large/ARC/Text | 0.95 | 0.95 | both | 0 | 0 | 0 | 0 | 0 | True |
| large/ARC/C2C | 0.9 | 0.0 | V2 only | 25 | 25 | 0 | 12 | 21 | True |
| X1-Llama/OBQA/Text | 0.0 | 0.0 | neither | 84 | 73 | 11 | 39 | 44 | True |
| X1-Llama/OBQA/C2C | 0.0 | 0.0 | neither | 156 | 72 | 84 | 72 | 97 | True |
| X1-Llama/ARC/Text | 0.0 | 0.0 | neither | 64 | 59 | 5 | 36 | 31 | True |
| X1-Llama/ARC/C2C | 0.0 | 0.0 | neither | 70 | 54 | 16 | 48 | 19 | True |
| X2-OLMo/OBQA/Text | 0.0 | 0.0 | neither | 101 | 18 | 83 | 43 | 53 | True |
| X2-OLMo/ARC/Text | 0.0 | 0.0 | neither | 57 | 17 | 40 | 34 | 34 | True |
| large/OBQA/Text+fact | 0.75 | 0.75 | both | 4 | 2 | 2 | 0 | 1 | n/a (not in E5-a) |

"cal rows differ" counts calibration questions on which the two conventions give a different label for the
receiver output or for the reference output (or both); "cal d-label differs" counts questions on which the
*disagreement* label itself flips. E5-a covered 12 of these 19 settings; every one of its official-extractor
counts (`o_R`, `o_ref`, d-total, d-in-X, d-outside-X, largest accepted q) reproduces exactly — asserted in
`scripts/e11b.py`, which exits non-zero on any mismatch.

Files: `results/E11b_two_conventions.csv`, `results/E11b_grid.csv` (19 x 2 x 20 tests),
`results/E11b_intersection.csv`.
