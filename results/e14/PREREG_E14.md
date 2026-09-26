E14 preregistration. Written before any E14 computation. Analysis will not change after seeing numbers.
If an item cannot be done as written, the closest operational version is used and recorded in DEVIATIONS.md.

E14-1 Sealed ARC under the official C2C answer extractor.
- Population: the 1,172 sealed ARC-Challenge test questions, with exactly the same inclusion rule that E11(b) used
  for the official extractor (E11(b) excluded questions with an option labelled E; questions with other label
  sets, e.g. 1-4 or three options, are handled exactly as in E11(b)). State the rule and report how many questions
  are excluded and why.
- Routing: the frozen routing of each sealed policy as executed (routing depends only on the probe score).
- Labels: re-read the stored raw outputs of the receiver-only path R and of the reference path (C2C for the
  C2C policy, Text for the Text policy) with the official C2C extractor port used in E11(b). Also report parser V2
  labels on the same subset.
- Decision convention, fixed now for both extractors: two unparseable outputs count as agreement (the paper's
  convention); exactly one unparseable output counts as a change. The rule below is applied to k under this
  convention only. Also report, descriptively, k when two unparseable outputs count as a change.
- For each policy x extractor: omitted n, changed k, k/n, two-sided 95% Clopper-Pearson interval, one-sided exact
  binomial p for H0: rho >= .05 (descriptive, not a new certificate). Also the number of omitted questions whose
  R label or reference label differs between the two extractors, split by the categories used in the E5-a
  follow-up (ambiguous or repeated letters read as the first letter; option text with tan/sin/"/"; last-letter
  reads such as "A. 0 C"; other).
- Paper rule (C2C policy; the Text policy is reported the same way, descriptively):
  (a) official-extractor CP upper end < 5%: the paper states the sealed C2C change rate under the official
      extractor with its interval;
  (b) point estimate <= 5% and CP upper end >= 5%: the paper states that under the official extractor the sealed
      test does not establish a rate below 5%;
  (c) point estimate > 5%: the paper states in Sec. 4.5, and wherever the abstract cites the sealed C2C result,
      that the sealed C2C result holds under our extractor only.

E14-2 Zero-uncertainty questions among omitted questions.
- Policies (frozen thresholds): large/OBQA/Text, large/OBQA/C2C, large/ARC/Text, large/ARC/C2C,
  medium/OBQA/C2C (q=.55; also q=.50), medium/ARC/C2C, large/MMLU-Pro/Text, large/MMLU-Pro/C2C,
  large/OBQA/Text+fact (q=.75).
- Populations: calibration split and dev split for all; the 744 held-out OBQA questions for the five held-out
  thresholds; the sealed ARC test for the two sealed policies.
- Zero uncertainty: u == 0.0 exactly as stored (FP32).
- For each policy x population: N; share of all N questions with u = 0; omitted n; n0 = omitted with u = 0 and
  k0 = changes among them; n+ = omitted with u > 0 and k+ = changes among them; k0/n0 and k+/n+ with two-sided
  95% Clopper-Pearson intervals; n0/n. On the calibration split also the one-sided exact binomial p for
  H0: rho >= .05 on the u > 0 omitted part alone at the frozen threshold (descriptive, not a certificate).
- Per receiver (Qwen3-1.7B, Qwen3-8B) x benchmark: share of dev questions with u = 0, and whether the frozen
  threshold tau equals 0 for any policy.
- Known before this preregistration: the paper already reports that the large receiver has u = 0 on 354/742 OBQA
  and 217/299 ARC dev questions and on 713/3,000 MMLU-Pro fit groups. The share among omitted questions and the
  change rates below have not been computed before.
- Paper rule: always an appendix table with all numbers and one main-text sentence giving the range of n0/n and
  of k0/n0 and k+/n+ on dev over the nine deployed thresholds (medium/OBQA/C2C at q=.55; the q=.50 row goes to the
  appendix table only). If for any policy the dev k+/n+ has CP lower end > 5%, the paper names that policy
  and states that its certificate rests on the zero-uncertainty questions. If n0/n >= 90% on dev for any policy,
  the paper states that for that policy the certificate mostly covers questions the receiver treats as certain,
  next to the existing sentence on possible benchmark contamination.
- Nothing else in the paper changes because of E14.
