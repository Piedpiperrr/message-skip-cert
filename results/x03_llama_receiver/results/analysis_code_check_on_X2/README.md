Code check of src/analyze_x3.py on the published X2 (OLMo) outputs (P2_R1_XFAM_20260919T095058Z/results/runs/chain_*.jsonl), run 2026-09-21
before any X3 output existed (X3A_ROOT=X2 folder, X3A_NO_MANIFEST=1). Every value below equals the recorded one:
- X2_SUMMARY.md: OBQA 172/742, AUROC .790, min UCB .118, fallback; ARC 67/299, .749, .169, fallback; R/Text correct per split (fit/cal/dev) identical.
- E11a_bothparse_diagnostic.csv (X2-OLMo OBQA/ARC): N_cal/N_dev both-parse 1260/698, 386/258; q .45 / .40; AUROC .85476 / .88131; coverage 44.41 / 34.11 %; 5/310, 0/88.
- e5b_resplit_stability.csv (X2-OLMo OBQA/ARC): certification rate 0.000, agreement 1.000; seed 0 reproduces the frozen split.
- item5_argmax_recert.csv (X2-OLMo OBQA/ARC): agreement .9516/.9017; fallback; min-p q/k/n .15/13/191 and .05/0/19; dev disagreements 165/65; AUROC .8079/.7654; INVALID-reference share .1575/.2923.
Not covered by this check: the deploying branch of the re-split loop (X2 has no deploying re-split).
