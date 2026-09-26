# E13 preregistration (Round 5, 2026-09-20 evening CDT)

All items are post-hoc re-analyses of saved development, held-out and replay records. No model is run.
Bootstrap intervals use seed 0 and 2,000 resamples of questions (question groups for MMLU-Pro) unless
stated otherwise. "Setting" = pair, benchmark, reference. Change indicator and parser are the frozen ones.

## Item 1. Oracle headroom of the rate-matched null, measured against the best fixed action

Reviewer point: the paper defines headroom as oracle accuracy minus the best fixed action, but the
rate-matched ratio (median 76.1%) uses oracle gain over receiver-only R.

For each of the 7 populations (small/medium/large x OBQA/ARC, large/MMLU-Pro) and each E9a design
(independent, per-reference Text, per-reference C2C, joint), for every one of the same 1,000 null draws:
  H_null = correct(oracle over {R, N_1, N_2}) - max{correct(R), correct(N_1), correct(N_2)}
  (per-reference designs: oracle over {R, N} minus max{correct(R), correct(N)})
and the real counterpart
  H_real = correct(oracle over {R, Text, C2C}) - max{correct(R), correct(Text), correct(C2C)}
  (per-reference: oracle over {R, b} minus max{correct(R), correct(b)}).
Report per population and design: H_real; mean, 2.5th and 97.5th percentile of H_null over draws; the
ratio mean(H_null)/H_real; a question-level 95% interval for the ratio with exactly the E9a protocol
(2,000 bootstraps x 100 null draws); the median ratio over populations with its interval (populations
resampled separately, as in E9a); and, as a decomposition, mean correct(N_1), correct(N_2) and the mean
best-fixed null accuracy minus correct(R), next to correct(Text), correct(C2C) minus correct(R).
Medium/ARC keeps its under-matched flag.

Reporting rules for Item 1 (fixed in advance):
- The paper will use the best-fixed ratio of the joint design as its headline number for headroom
  (abstract, introduction, Contribution 1, Section 4.1, conclusion), because that is how headroom is
  defined in the paper. The gain-over-R ratio stays in Appendix J as a secondary quantity, and every
  place that gives a number names which of the two it is.
- If the joint best-fixed median ratio is >= .5, the abstract keeps "oracle headroom is weak evidence
  for useful communication content" and gives the median. If it is < .5, the abstract instead says
  "content-free input changes produce X% (median) of the oracle headroom" without "weak evidence".
- If the median is >= 1, the text says the null produces at least as much headroom as the real paths
  (median ratio X) and explains in one sentence that real paths raise the best fixed action while
  content-free changes do not. No capping at 1, no adjectives such as "most" or "much".
- Per-population ratios above 1 or below the gain-over-R ratio are reported as they are.

## Item 2. Joint null also matched on where the changes fall (stratified by whether R is correct)

Reviewer point: the null matches the number and overlap of changes but not whether they fall on
questions R answers incorrectly.

Stratify each population's questions by whether R is correct. Within each stratum, run the joint
design of E9a with that stratum's own counts a, b, c and c_same (the same sampler, the same forced-agreement
rule, uniform draws from P(x) among questions with nonempty P(x)), and take the union of the two strata
as one draw. 1,000 draws, seed 0; intervals as in E9a. Report both ratios (best-fixed as in Item 1, and
gain over R as in E9a), per population and median, plus per stratum the number of eligible questions
and whether it is under-matched (then the ratio is a lower bound, flagged).

Reporting rules for Item 2:
- Appendix J reports the full table. Section 4.1 gives the stratified best-fixed median in one sentence,
  whatever it is.
- If the stratified best-fixed median is < .5, the abstract's headroom sentence adds the stratified
  median in parentheses.

## Item 3. How much of a helpful path's gain omission keeps, and at which tolerance

Reviewer point: the certificate bounds answer changes, not the gain a helpful path adds; kappa*alpha
exceeds the Text gain in all three large-pair Text settings at alpha = .05.

Settings: large/OBQA/Text, large/ARC/Text, large/MMLU-Pro/Text, large/OBQA/Text+fact.
For each, on the development set and, where R and the reference were both run on every question, on the
744 held-out OBQA questions (large Text, Text+fact):
  G = acc(b) - acc(R);  P = acc(policy) - acc(R);  retention = P / G;
  reference corrections (b correct, R wrong): total, lost (omitted), kept (routed);
with paired bootstrap 95% intervals for G, P and retention (percentile; report the share of resamples
with G <= 0, if any). The sealed ARC run did not execute R on routed questions; state that retention is
not computable there and do not approximate it.

Tolerance sweep: alpha in {.01, .02, .03, .04, .05}, same per-candidate delta = .001, the same 20 fit
thresholds, the original calibration split, the same exact binomial test. For each alpha and setting:
deployed q (or fallback), calibration n / k / p, development coverage kappa, changed/omitted, kappa*alpha
in points, development accuracy of the policy, G, P, retention with interval, and held-out
changed/omitted, accuracy and retention for the OBQA settings (held-out routes at the alpha-variant
threshold, derived from the frozen held-out scores). Identify, per setting, the largest alpha on this grid
for which kappa*alpha < G on development.

Recomposed saving for each alpha-variant threshold (not a new replay): on each existing 128-question
panel replay of that setting (the original replay and each of the 3 ClusterA E3 repeats, version (b),
reported separately and never merged), the variant omits a subset of the questions the alpha = .05
policy omitted. Per question, variant latency = probe latency of the policy request + (omitted under
the variant ? the policy request's action latency : the fixed arm's latency on that question). Paired
mean saving (fixed minus variant) with a paired bootstrap interval. If the per-request records do not
separate probe and action latency, STOP this sub-item and report.

Reporting rules for Item 3:
- Section 4.3 reports retention with intervals at alpha = .05 for all four settings (development) and
  for the two held-out OBQA settings, and, for each setting, the largest alpha on the grid with
  kappa*alpha below the gain, with its coverage, retention and recomposed saving range. Whatever the
  numbers are. If any retention at alpha = .05 is below .5, the text says so for that setting.
- Contribution 3 and Section 5 state that the certificate bounds answer changes, not retained gain, and
  give the retention range at alpha = .05.
- Recomposed savings are labelled as recomposed from the per-request timings of an existing replay.

## Item 4. Can a small paired sample predict the certification outcome?

Reviewer point: Section 5 says three quantities "on a small paired sample say in advance where this is
worth trying", but the AUROC-near-.80 separation was read off full development sets of the same settings.

Prediction rule, taken as written in the paper before this analysis: predict "deploy" if the ProbeMax
AUROC for receiver-reference disagreement, estimated on the sample, is >= .80, otherwise "fallback".
If a sample has no disagreement, predict deploy; if it has no agreement, predict fallback; count how
often each happens. AUROC is computed with the same function as the paper's development AUROC; report
which function and how it treats tied scores.

For every setting with receiver and reference outputs and scores on the fit split, and for
n in {100, 200, 400}: draw 200 samples of n fit questions without replacement (seed 0), apply the rule,
and compare with the setting's actual certification outcome on the original split. Settings without
fit-split reference outputs (expected: Text+fact) use the development split instead, flagged.
Report per setting: actual outcome, development AUROC, median and IQR of the sample AUROC, share of
draws whose prediction matches the outcome; and overall: mean match share over settings, number of
settings with match share >= .8, separately for deployed and fallback settings, per n.
Also report, as a secondary descriptive line, the sample disagreement rate (median, IQR) per setting.

Factual query for the same item: report the UTC modification time of the earliest file in
P2_R2_E8_20260920T012544Z/ that contains a certification decision, a p-value or a development AUROC for
any of the four small/medium MMLU-Pro settings, and the same for P2_R4_E10_20260920T225954Z/.

Reporting rules for Item 4:
- Section 5 replaces "say in advance" by the measured match share at n = 200 (overall and range over
  settings), and says the .80 cut was read off the same settings' development sets.
- If the overall match share at n = 200 is below .80, Section 5 and the conclusion drop any claim that
  the diagnostics predict certification, and describe the AUROC separation as a pattern in these
  settings only.

## Item 5. OLMo recertification with the probe's argmax as the receiver's answer

Reviewer point: the answer-format explanation for the OLMo fallback rests on a non-deployable filter.
Answering omitted questions with the probe's argmax is deployable and has no receiver-side parse failure.

For the three OLMo settings (and, as a secondary line, the four Llama-pair settings, whose receiver is
the small pair's): o_A(x) = argmax over option labels of the saved probe probabilities; change label
1[o_A != o_Text] with the frozen parser on the reference side (INVALID reference answers stay INVALID and
count as changes). Same ProbeMax scores, same 20 fit thresholds, same test; a separate post-hoc family.
Report per setting: agreement of o_A with the native receiver answer on calibration; deployed q or
fallback with calibration n / k / p; development coverage, changed/omitted, AUROC of u for the new label;
and the share of development disagreements that involve an INVALID reference answer.
If the saved probe records contain only the score u and not per-option probabilities or the argmax
label, STOP this item and report; do not recompute probes.

Reporting rules for Item 5:
- If any OLMo setting certifies: Section 4.3 says in one sentence that answering from the probe, a
  deployable rule, certifies it on development data (post hoc, no held-out test, no replay). The count
  "all seven cross-family settings fall back" stays, qualified as "under the prespecified policy".
- If none certifies: Section 4.3 says that the deployable argmax rule also certifies no OLMo setting,
  and the sentence "We read this as evidence about answer format, not about model families" is removed.

## Item 6. What the probe cost consists of

From the existing component panel records (Appendix F: tokenization and prefix construction, transfer,
full prefill, last-position projection, label probabilities, score, selector, synchronization), report
the mean of each component and of their sum per receiver and benchmark panel, and the mean end-to-end
probe-plus-selector cost from the replays for comparison. From the E7 records, report for the REUSE arm
what part of an omitted request it saves (the receiver prefill) and the mean receiver-only request
latency split into prefill and decoding, if recorded; otherwise say "not recorded".

Reporting rule: Appendix F reports the breakdown; Section 4.4 gives the forward-pass share in one clause.

## Item 7. Re-split stability for every setting

Report the share of the 200 re-drawn fit/calibration splits that deploy, for every setting that has
them (expected: the 14 main settings of Table 6, the 7 cross-family settings, the 4 small/medium
MMLU-Pro settings), from existing E5-b and E8 records. For any setting with fit and calibration outputs
but no re-split record, run the E5-b procedure unchanged (seeds 1 to 200) and flag it as added in E13.
List settings without fit-split outputs (expected: Text+fact). Reporting rule: Appendix D adds the
missing rows; the main text states exactly which settings the re-split claim covers.

## Item 8. AUROC tie handling

Name the function used for every development AUROC in the paper and state how it treats tied scores.
Recompute large/ARC/Text and medium/ARC/C2C development AUROC with an explicit Mann-Whitney statistic
that gives tied pairs credit 1/2 and report both values. Reporting rule: Appendix C, "Score ties", adds
one sentence.

## Item 9. Calibration cost payback

For each of the 8 deployed policies: calibration cost in shadow mode, C_s = N_fit x mean probe +
N_cal x (mean probe + mean receiver-only request), where reference outputs come from traffic the deployed
system serves anyway; and standalone, C_a = C_s + N_cal x mean reference request. Means from the ClusterA
E3 repeats, version (b) (receiver-only request = policy action latency on omitted questions; reference
request = fixed arm). Break-even workload W = C / mean saving per query, using the mean E3 (b) saving;
for large/MMLU-Pro/C2C use the full 2,641-question replay (b), 22.0 ms. N_fit / N_cal: OBQA 2,100 / 1,366;
ARC 670 / 448; MMLU-Pro 3,000 / 6,000. Reporting rule: Appendix F gives W for both modes in one sentence
or a small table. Arithmetic on measured means only.

## Item 10. Is the earlier parser functionally identical to the final parser?

Run the earlier parser (D1, frozen 2026-09-12T06:02:33Z) and the final parser on every saved raw output
of every split, setting and path (fit, calibration, development, held-out, sealed, panels). Report the
number of outputs whose parsed answer differs, by split and setting, the kinds of output involved, and
whether any difference changes an answer-change label. Also diff the two sources and summarize the rule
differences. Reporting rule: Appendix C (ii) states exactly where the two agree ("identical on all N
saved outputs" or "identical on every calibration output; they differ on M outputs elsewhere, of kind K").

## Item 11. Exact prompts and parser rules for an appendix

Copy, verbatim, the helper's Text instruction, the receiver's Text-reading prompt, the receiver-only
prompt, the probe prefix, and the Text+fact addition, each as rendered for one example question (use
one OBQA fit question and one MMLU-Pro fit question), plus the final parser's rules in plain language
with its regular expressions. Write them to PROMPTS_AND_PARSER.md. Check that nothing in that file
contains a user name, a file-system path, a project or allocation name, or a machine name.

## Item 12. GSM8K: other label-free scores (exploratory)

Only if per-token log-probabilities of the receiver-only generations are stored in the E10 records:
compute, on the development split, the AUROC for receiver-Text disagreement of (i) the mean token
probability of the first 16 generated tokens, (ii) the minimum token probability over the generation,
(iii) the mean token probability over the whole generation (should reproduce s2, AUROC .6444).
No threshold, no test, no certification. If not stored, say so and stop.
Reporting rule: Appendix P lists the AUROCs in one sentence. If any exceeds .80, Section 7 adds one
sentence naming it as a direction that was not tested for certification.

## Budget and deadline
Login-node CPU only. Report whatever is complete by 2026-09-22 12:00 CDT; items not complete by then
are not used in the paper.
