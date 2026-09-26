# E11 deviations from `PREREG_E11.md`

Preregistration SHA-256 `48b0d405aa2c59db91f53ccd4b1fea372e3dfa3894095b01f44050046af84083`,
recorded 2026-09-20T22:41:00Z, before anything was read or computed from the saved outputs.

## 1. One ARC development question is outside the official extractor's option set (E11-b)

The preregistration says the official C2C evaluator's extraction "reads option letters A-D only, so it
applies to the OBQA and ARC settings, not to MMLU-Pro (A-J)". That is true of every calibration question,
but **one of the 299 ARC development questions has five options (A-E)**. The official extractor cannot be
applied to it without forcing it outside its own option set, so that single row is excluded from the
official relabelling on the ARC development splits and is counted in the new column
`dev_rows_official_not_applicable_excluded` of `results/E11b_two_conventions.csv`, where it is 1 for each
of the nine ARC settings in E11-b (small/ARC/Text, small/ARC/C2C, medium/ARC/Text, medium/ARC/C2C,
large/ARC/Text, large/ARC/C2C, X1-Llama/ARC/Text, X1-Llama/ARC/C2C, X2-OLMo/ARC/Text) and 0 everywhere else.

Reason and effect: certification in E11-b is computed on the **calibration** split only, and every
calibration question in every setting is A-D (asserted in `scripts/e11b.py`, which fails otherwise). So no
accepted q, no deploy status and no intersection-set membership is affected. The exclusion touches only the
descriptive development-side label-difference counts, each by at most one row.

## 2. Both readings of "the accuracy of the Rule-D policy against the reference" are reported (E11-c)

The phrase admits two readings: agreement of the Rule-D policy's answer with the reference answer, and the
policy's accuracy against gold set beside the reference's. Rather than pick one, `results/E11c_ruleD.csv`
carries both: `dev_policy_equals_reference` (policy answer == reference answer, %) and
`dev_accuracy_policy_vs_gold` / `dev_accuracy_reference_vs_gold` / `dev_accuracy_receiver_only_vs_gold`
(against gold, the same quantity as "Correct P/B" in the paper's Table 6). The per-setting table in
`E11C_SUMMARY.md` shows the gold-based pair. No new gold was opened: development gold for all 26 settings
had already been read and published in earlier stages.

## 3. Reported additions beyond the preregistered minimum (not substitutions)

- Step 1 asked for the 8 deployed policies and at least 4 fallback settings. All 26 settings were checked,
  and the match is against the whole 20-row stored ledger per setting (520 rows), not only the deployed row.
- The 9th certified policy, large/OBQA/Text+fact (E6, q = .75), is reported alongside the 8 deployed
  policies throughout. The preregistration counts 8 deployed policies; Text+fact is a separate
  certification within the 26 settings in scope and is treated the same way everywhere.
- E11-a reports development coverage on the both-parse subset with two denominators (retained both-parse
  questions, matching E5-e, and all development questions).

## Everything else

None. No threshold, deployment, replay, latency number or frozen protocol was revised. No model was run, no
GPU and no PBS job was used; all work was CPU table lookup, relabelling and exact binomial tests on the
ClusterA login node.
