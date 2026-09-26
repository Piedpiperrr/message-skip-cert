# E11-c — Rule D, a deployable INVALID-routing rule

Stage: `$DATA_DIR/P2_R4_E11_20260920T224016Z`  
Preregistration: `PREREG_E11.md`, SHA-256 `48b0d405aa2c59db91f53ccd4b1fea372e3dfa3894095b01f44050046af84083`, recorded 2026-09-20T22:41:00Z (before anything was read or computed from the saved outputs).  
CPU-only re-analysis of already-saved model outputs on the ClusterA login node. No model was run, no GPU and no PBS job was used. POST-HOC re-analysis (reviewer R4/E11); does not change any primary decision.

## Rule

Rule D: if the receiver-only output does not parse, route to the reference; otherwise apply the usual
threshold rule. The omission set at threshold tau is {x : u(x) <= tau and o_R(x) parses}. Rule D reads only
the receiver's own output, never the reference's, so it is deployable, and parsing the receiver output is
already part of the policy. The controlled quantity is unchanged:
rho_D(tau) = P(o_R != o_b | omitted under Rule D). Same 20 fit-split thresholds, same alpha = .05,
delta = .001, Bonferroni over the 20 candidates. A separate post hoc family of 26 x 20 = 520 tests.

## Result — Rule D certifies nothing new

- new certifications under Rule D: **0**
- lost certifications under Rule D: **0**
- certified under both with a different q: **0**
- unchanged: **26** of 26

In particular Rule D does **not** certify any of the seven cross-family settings, including the three OLMo
settings it was aimed at. Routing away unparseable *receiver* outputs removes only part of the measured
disagreement; the rows on which the *reference* output is unparseable while the receiver parses stay in, and
they are genuine changes to what the deployed system returns. That is why the both-parse diagnostic of E11-a
(which also drops those rows, and is therefore not deployable) certifies four settings that Rule D does not.

## Per-setting table

| setting | orig q | Rule D q | cal n | cal k | cal p | dev cov. % of all | dev cov. % of parseable | changed/omitted | cond. change rate | dev acc. policy | dev acc. reference | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| small/OBQA/Text | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 46.63 | 46.63 | unchanged |
| small/OBQA/C2C | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 49.33 | 49.33 | unchanged |
| small/ARC/Text | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 42.14 | 42.14 | unchanged |
| small/ARC/C2C | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 51.84 | 51.84 | unchanged |
| medium/OBQA/Text | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 70.49 | 70.49 | unchanged |
| medium/OBQA/C2C | 0.55 | 0.55 | 738 | 19 | 0.000712772 | 52.56 | 53.13 | 11/390 | 0.02821 | 66.31 | 65.50 | unchanged |
| medium/ARC/Text | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 73.91 | 73.91 | unchanged |
| medium/ARC/C2C | 0.6 | 0.6 | 290 | 1 | 5.63703e-06 | 63.21 | 63.64 | 4/189 | 0.02116 | 67.89 | 67.56 | unchanged |
| large/OBQA/Text | 0.8 | 0.8 | 1064 | 18 | 1.15505e-08 | 77.09 | 77.09 | 19/572 | 0.03322 | 85.98 | 86.93 | unchanged |
| large/OBQA/C2C | 0.8 | 0.8 | 1064 | 22 | 6.7085e-07 | 77.09 | 77.09 | 13/572 | 0.02273 | 81.54 | 80.59 | unchanged |
| large/ARC/Text | 0.95 | 0.95 | 422 | 4 | 4.8015e-06 | 94.98 | 94.98 | 9/284 | 0.03169 | 90.30 | 91.64 | unchanged |
| large/ARC/C2C | 0.9 | 0.9 | 404 | 7 | 0.000539697 | 90.30 | 90.30 | 3/270 | 0.01111 | 89.30 | 88.96 | unchanged |
| large/MMLU-Pro/Text | 0.4 | 0.4 | 2357 | 66 | 7.45874e-08 | 40.44 | 40.53 | 39/1068 | 0.03652 | 50.06 | 49.94 | unchanged |
| large/MMLU-Pro/C2C | 0.4 | 0.4 | 2357 | 74 | 6.31358e-06 | 40.44 | 40.53 | 36/1068 | 0.03371 | 47.63 | 46.69 | unchanged |
| small/MMLU-Pro/Text | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 19.54 | 19.54 | unchanged |
| small/MMLU-Pro/C2C | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 17.49 | 17.49 | unchanged |
| medium/MMLU-Pro/Text | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 34.57 | 34.57 | unchanged |
| medium/MMLU-Pro/C2C | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 20.07 | 20.07 | unchanged |
| X1-Llama/OBQA/Text | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 44.88 | 44.88 | unchanged |
| X1-Llama/OBQA/C2C | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 48.25 | 48.25 | unchanged |
| X1-Llama/ARC/Text | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 48.49 | 48.49 | unchanged |
| X1-Llama/ARC/C2C | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 48.83 | 48.83 | unchanged |
| X2-OLMo/OBQA/Text | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 69.54 | 69.54 | unchanged |
| X2-OLMo/ARC/Text | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 74.25 | 74.25 | unchanged |
| X2-OLMo/MMLU-Pro/Text | 0.0 | no candidate accepted | — | — | — | 0.00 | 0.00 | 0/0 | — | 25.14 | 25.14 | unchanged |
| large/OBQA/Text+fact | 0.75 | 0.75 | 999 | 22 | 4.83045e-06 | 72.24 | 72.24 | 13/536 | 0.02425 | 88.95 | 90.30 | unchanged |

Coverage is reported both as a fraction of all development questions and as a fraction of development
questions whose receiver output parses. Accuracy is against gold on the development split
(the same quantity as "Correct P/B" in the paper's Table 6); `E11c_ruleD.csv` also carries
`dev_policy_equals_reference`, the agreement of the Rule-D policy with the reference answer.

Files: `results/E11c_ruleD.csv`, `results/E11c_ruleD_grid.csv` (26 x 20 tests), `results/E11c_verdicts.csv`.
