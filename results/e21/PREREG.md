E21-PREREG v1 (Paper A, round 9). Post hoc analyses of stored outputs. Reported whatever the result.
Exposure: gold labels of every split used here have been read before (calibration: ProbeMax selection on large/OBQA;
parser review of 341 calibration questions). eps, the 20% coverage bar and the gain conditions below were fixed with
development lost-correction counts known for some settings; no calibration lost-correction count is known to the
authors (REPRO h reports whether any earlier result file contains one).

E21-1 Label-light certificate of the accuracy loss (six helpful Text policies).
 Settings (frozen deployed q in brackets): large/OBQA/Text [.80, reused certificate], large/ARC/Text [.95],
 large/MMLU-Pro/Text [.40, tau = 3.838539123535156e-05], large/OBQA/Text+fact [.75], Llama-3.1-8B/OBQA/Text [.60], Llama-3.1-8B/ARC/Text [.70].
 Calibration set C of each setting (size N = |C|, all calibration questions, not only omitted ones).
 For candidate tau_j (the setting's 20 frozen fit-quantile thresholds):
   L_i(tau) = 1[u_i <= tau and o_b,i = y_i and o_R,i != y_i]   (lost correction)
   W_i(tau) = 1[u_i <= tau and o_R,i = y_i and o_b,i != y_i]   (gained answer)
   Accuracy loss acc(b) - acc(pi_tau) = Pr(L) - Pr(W) <= Pr(L).
   k_L(tau) = sum_i L_i(tau). Test H0: Pr(L) >= eps. p_eps(tau) = P[Binomial(N, eps) <= k_L(tau)]. Accept iff p <= .001.
 Two families per setting: eps = .01 (primary) and eps = .02 (secondary), 20 tests each, Bonferroni .02 per family.
 Joint certificate at eps: candidates accepted by BOTH the paper's frozen change-rate test (rho <= .05; recomputed from
 stored calibration outputs; its largest accepted candidate must reproduce the frozen q) AND the L-test at eps.
 q_joint(eps) = largest such candidate, or NONE. Family-wise error of the joint certificate <= .04 per setting and eps
 (.06 per setting if both eps are read).
 Labels needed: D_all = # calibration disagreements (o_R != o_b); D_seq(eps) = # calibration disagreements with
 u <= tau of the first REJECTED candidate in increasing order (all disagreements if none rejected; k_L is monotone in
 tau, so accepted candidates form a prefix); D_dep(eps) = # calibration disagreements with u <= tau_joint(eps);
 D_need(eps) = # calibration disagreements with u <= min(tau of the first L-rejected candidate, tau_frozen) (the labels
 the joint procedure actually needs, since tau_joint <= tau_frozen; all disagreements up to tau_frozen if none rejected).
 Descriptive check: q_joint recomputed on C \ X (the 341 parser-reviewed calibration questions removed).
 Feasibility: N_min(eps) = min N with (1-eps)^N <= .001 -> 688 for .01, 342 for .02. N < N_min -> "infeasible at eps".
 Evaluation (only after CERT.json with every k_L, p, q_L, q_joint is written and hashed):
  dev: coverage, dev L and W counts, change rate among omitted [two-sided 95% Clopper-Pearson], dAcc = acc(pi)-acc(b)
  [paired question bootstrap, 2,000 resamples, seed 0], G_dev = acc(b)-acc(R) in points, retention
  (acc(pi)-acc(R))/(acc(b)-acc(R)); same numbers for the frozen policy.
  out of sample (descriptive): held-out OBQA 744 (large/OBQA/Text, Text+fact, Llama/OBQA); ARC test 1,172 (Llama/ARC,
  E16 run); sealed ARC 1,172 (large/ARC/Text; R stored only for questions omitted at the frozen tau, which covers every
  tau_joint <= tau_frozen; retention N/A there). Report N_test, coverage, k_L, k_L/N_test [CP 95%], whether the CP upper
  end is < eps, W, dAcc [bootstrap], retention where acc(R) is available. MMLU-Pro: N/A (no unused data).
  panel: recomposed mean saving vs the fixed reference at q_joint with the E19-1 method and data sources (panel questions
  omitted at the frozen tau but with u > tau_joint get policy latency := that question's fixed-reference latency + that
  request's probe latency, E19-1 fallback rule if no per-request probe latency), paired bootstrap 95% (2,000, seed 0);
  also the frozen policy's saving from the same source. q_joint = frozen q -> identical to frozen.
  All dev / OOS / panel numbers are for pi at tau_joint(eps); q_joint = NONE -> N/A.
 Writing rules ("counted" = joint certificate, dev coverage >= 20%, and eps at most half of G_dev):
  (a) >= 1 setting counted at eps = .01 (i.e. G_dev >= 2 points) -> Sec. 4.3 sentence: "With gold labels on at most K
      calibration questions (the lowest-uncertainty receiver-reference disagreements), the same test also certifies, at
      a threshold no higher than the deployed one, an accuracy loss of at most one point for A of the six helpful Text
      paths (B of them nominal), at X-Y% development coverage, retaining Z-W% of the gain (App. X)." K = range of
      D_need over the A settings; A counts settings meeting the definition; B counts large/OBQA/Text and Text+fact
      among them. Any counted setting whose dev or out-of-sample k_L/N exceeds eps is named in the same sentence with
      that rate. Abstract: at most one clause, the authors' choice by space.
  (b) else >= 1 setting counted at eps = .02 (i.e. G_dev >= 4 points) -> the same sentence with "two points", naming
      the settings, plus "none at one point".
  (c) else -> "Labels on the omitted disagreements suffice for a direct test of the accuracy loss, but at our calibration
      sizes it certifies no helpful policy at >= 20% coverage with a loss bound (one or two points) at most half its
      gain (App. X)."
  Always: appendix table of all 6 settings x 2 eps (candidates, q_L, q_joint, D_all/D_seq/D_dep/D_need, dev, OOS,
  panel, C \ X check), including certificates that are not counted; infeasible settings named with their N; settings
  whose OOS CP upper end is >= eps named in the appendix; the post hoc status, the exposure statement and the
  family-wise bounds stated; large/OBQA/Text and Text+fact flagged as nominal (their calibration labels were used when
  ProbeMax was selected).

E21-2 AUROC on unsaturated questions.
 Nine deployed Qwen-receiver policies: medium/OBQA/C2C [q=.55], medium/ARC/C2C, large/OBQA/Text, large/OBQA/C2C,
 large/ARC/Text, large/ARC/C2C, large/MMLU-Pro/Text, large/MMLU-Pro/C2C, large/OBQA/Text+fact. Controls: Llama/OBQA,
 Llama/ARC, SQuAD/Llama (its frozen score s2).
 Positive class d = 1[o_R != o_b] on the setting's dev questions; score u (larger = more uncertain).
  (i) AUROC on all dev questions, ties counted 1/2 (must reproduce the paper's dev AUROC to 5e-4);
  (ii) AUROC on u > 0 questions only, ties 1/2, with n, # positives, and a 95% percentile interval from a bootstrap
      that resamples the u > 0 questions (2,000, seed 0; resamples with an empty class are dropped and counted);
  (iii) AUROC on all dev questions using the E16-3 float64 score m (log of the non-maximum label mass; larger m = more
      uncertain) instead of u, remaining ties 1/2;
  (iv) AUROC of m inside the u = 0 block (N/A if one class is empty), with the block's n and # positives, no interval;
  (v) share of dev questions with u = 0 and share of dev disagreements with u > 0;
  (vi) change rate inside the u = 0 block (must reproduce E17-1: 0 to 2.18% over the nine policies).
 Held-out OBQA 744 (descriptive): (i)-(v) for medium/OBQA/C2C, large/OBQA/Text, large/OBQA/C2C, Text+fact; (i) for
 Llama/OBQA. Controls: (i) and (v) only.
 Writing rules: Sec. 6 (u = 0 paragraph) always gives the range and median of (ii) over the nine policies and the
 median of (iii).
  median(ii) >= .80 -> "the probe also ranks disagreements among unsaturated questions (AUROC X-Y on u > 0)".
  median(ii) < .70 -> add to Contribution 3 / Sec. 4.2: "the ranking mostly separates the saturated block, where the
      reference changes V-W% of answers (from (vi)), from the rest (AUROC X-Y on u > 0 alone)".
  otherwise -> "on unsaturated questions alone the AUROC is X-Y (median Z), lower than on all questions (median W)".

E21-3a Option-rotation stability of the receiver at u = 0 (stored V1 outputs).
 Gate: confirm from the E4 code and its protocol that V1 = the receiver alone with the SAME prompt except that option
 contents are permuted (labels stay in place), same decoding, and that each V1 label can be mapped back to the original
 option content. If V1 is not a pure permutation of option contents, E21-3a stops and is reported as not done.
 Populations: dev of small/OBQA, small/ARC, medium/OBQA, medium/ARC, large/OBQA, large/ARC, large/MMLU-Pro.
 c = 1[V1 mapped back != R] (two INVALIDs agree; exactly one INVALID = change). Report n, # changes, rate [CP 95%],
 split by the receiver's original u = 0 vs u > 0; the same on each deployed policy's omitted dev questions (nine
 policies above; label these lines "the receiver's own answer change under rotation, not the policy's change rate");
 a parseable-only rate; and, only if V1's own probe score was stored, the share of u = 0 questions that stay at u = 0
 under rotation (else "not stored").
 Writing rules: if the u = 0 rotation-change rate has a CP upper end < 5% in all five receiver populations behind
 deployed Qwen policies (medium/OBQA, medium/ARC, large/OBQA, large/ARC, large/MMLU-Pro) -> Sec. 6 clause "at u = 0
 the receiver keeps its answer under option rotation (changes X-Y%), so these confident answers follow option content,
 not position". Otherwise -> Sec. 6 gives the numbers, names the populations that fail, and Limitations adds "part of
 the receiver's confident answers follow option position; the certificate covers the deployed prompt format". Neither branch is used to argue about
 training-data contamination.
END E21-PREREG
