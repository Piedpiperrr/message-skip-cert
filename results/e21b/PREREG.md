E21B-PREREG v1 (Paper A, round 9). Post hoc robustness check. Reported whatever the result, if complete by the deadline.
Question: do the frozen large-pair policies keep a low change rate when the answer options are reordered?
Models, revisions, dtype (bf16), greedy decoding, token limits (helper 256, receiver 64), chat templates, prompt
builders, parser V2 (two INVALIDs agree; exactly one INVALID = change) and ProbeMax: exactly as frozen. No re-calibration.
Rotation: the E4 V1 permutation of option contents (labels stay in their displayed positions), applied to the question
before every prompt builder; the helper (Text, Text+fact) and the C2C path see the rotated question; the Text+fact
fact line is unchanged. Every label is mapped back to the original option index for cross-format comparisons.
If V1's permutation depends on a random draw, it is derived from the question id exactly as E4 did (rule recorded in
INPUTS.md). Questions with other than 4 options or non-letter labels are rotated by the same V1 rule over their own
options.
Populations: sealed ARC test (all 1,172 questions of the sealed run) and held-out OBQA (744).
Policies and frozen thresholds (tau exactly as stored; no new thresholds):
  large/ARC/Text [q=.95], large/ARC/C2C [q=.90, tau=0.0007095932960510254], on sealed ARC;
  large/OBQA/Text [q=.80], large/OBQA/C2C [q=.80], large/OBQA/Text+fact [q=.75], on held-out OBQA.
Runs under rotation, all questions: receiver probe u_rot; receiver-only R_rot; Text_rot (fresh helper message);
C2C_rot; Text+fact_rot (OBQA only).
Primary statistics per policy: N; share with u_rot = 0; omitted n = #{u_rot <= tau}; coverage n/N (next to the
original-format coverage);
k = #{omitted and o_R_rot != o_b_rot}; k/n with a two-sided 95% Clopper-Pearson interval; one-sided exact binomial
p for H0: rho >= .05 (descriptive only; not a certificate); k split by u_rot = 0 / u_rot > 0.
Next to each: the stored original-format numbers (sealed Text 20/1100, C2C 11/1047; held-out Text 12/595,
C2C 13/595, Text+fact 16/558).
Secondary (descriptive): R_rot (mapped back) vs stored R_orig agreement, overall and split by u_orig = 0 / > 0 (on
sealed ARC R_orig exists only for questions omitted at the frozen tau; report on that subset); share of u_orig = 0
questions with u_rot = 0; b_rot (mapped back) vs b_orig agreement per reference; INVALID counts per arm.
Writing rules:
 (1) every policy has a CP upper end < 5% -> Sec. 6 (u = 0 paragraph) clause: "Under option rotation on the sealed ARC
     and held-out OBQA questions, the five frozen large-pair policies omit X-Y% of questions (X'-Y'% in the original
     order) and change A-B% of omitted answers (upper bounds below 5%; App. X)." Appendix table with all statistics.
 (2) any policy with k/n > 5% -> Sec. 6 Limitations sentence naming it: "Under option rotation, <policy> omits X% of
     questions (X'% in the original order) and changes Y% [CI] of omitted answers; the certificate covers the deployed
     prompt format, not reorderings of it." Appendix table. The abstract's out-of-sample clause adds "in the deployed
     option order". No other text softens this sentence.
 (3) otherwise (all k/n <= 5%, some CP upper end >= 5%) -> Sec. 6 clause with the numbers: "omit X-Y% of questions
     (X'-Y'% in the original order) and change A-B% of omitted answers (upper bounds up to Z%)". Appendix table.
 (4) production outputs not all written by 2026-09-22 18:00 CDT (judged by the manifest's last output timestamp,
     recorded before any statistic is computed), or any preflight STOP -> no numbers in the paper; the provenance table
     gets the row "Option-rotation rerun of the large-pair policies: not completed (<reason>)". Late outputs are still
     analysed under this PREREG and placed unchanged in the supplementary material.
END E21B-PREREG
