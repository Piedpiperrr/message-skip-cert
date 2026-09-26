# E11 preregistration (Round 4, 2026-09-20)

## Motivation

Reviewer concern: the certified quantity, and therefore the deploy/fallback boundary, may be
contingent on the answer-parsing convention. Two specific sub-concerns:
(i) unparseable outputs are assigned a single INVALID label and therefore count as answer changes;
(ii) an equally defensible alternative extraction (the official C2C evaluator's) changes which
settings certify. A third question is whether a *deployable* rule that never reads the reference
output can recover certification where INVALID drives the disagreement.

## Scope

26 certification settings in total:

- 18 main settings: 3 Qwen pairs (small, medium, large) x {Text, C2C} x {OBQA, ARC, MMLU-Pro}
- 7 cross-family settings: X2 OLMo (Text; OBQA, ARC, MMLU-Pro), X1 Llama (Text + C2C; OBQA, ARC)
- 1 informed-helper setting: large/OBQA/Text+fact
  Nothing about the frozen protocol changes: same fit split, same 20 candidate quantiles computed
  from ProbeMax on the fit split, same alpha = .05, same delta = .001, same exact binomial test of
  H0: rho(tau) >= alpha, same Bonferroni over the 20 candidates. Each of E11-a, E11-b and E11-c is a
  separate post hoc family and is labelled as such in the paper.

## Step 1. Reproduction check (before any new analysis)

From the saved records, recompute and print, for the 8 deployed policies and for at least 4
fallback settings: the calibration n and k at the originally deployed candidate, the resulting
exact-binomial p-value, the deployed quantile q, the development disagreement rate and the
development AUROC. These must match the values already in the paper (Tables 2 and 6) exactly.
If any of them does not match, STOP and report before doing anything else.

## Step 2. E11-a: INVALID decomposition and both-parse diagnostic

For every one of the 26 settings, on the calibration split and on the development split,
decompose each question into exactly one of four cells:
  (1) both outputs parse and the labels differ   -> disagreement
  (2) both outputs parse and the labels agree    -> agreement
  (3) exactly one output is INVALID              -> disagreement under the frozen convention
  (4) both outputs are INVALID                   -> agreement under the frozen convention
Report, per setting and per split: N, the four cell counts, the fraction of disagreements that
come from cell (3), and separately the receiver-only INVALID rate and the reference INVALID rate.

Both-parse diagnostic: restrict the calibration and development splits to questions in cells (1)
and (2), keep the 20 fit-split thresholds unchanged, and redo the 20 exact binomial tests.
Report, per setting: the number of retained calibration and development questions, the largest
accepted quantile q (or "no candidate accepted"), the development disagreement rate, the
development AUROC, the development coverage and the conditional change rate at the accepted q.
This diagnostic is NOT deployable, because the filter reads the reference output. It is labelled
as a diagnostic everywhere it appears.

### Reporting rules for E11-a (fixed in advance)

- If all 8 currently deployed policies still certify on the both-parse subset: the main text states
  that the deploy side of the boundary holds under both treatments of unparseable outputs, with the
  range of cell-(3) shares across the 18 main settings given as a number.
- If any currently deployed policy no longer certifies on the both-parse subset: the main text names
  that setting and states that its certification depends in part on counting unparseable outputs as
  changes. The deployment itself and all reported replays are unchanged; the original threshold and
  numbers stay, with the diagnostic reported next to them.
- If a setting that currently falls back certifies on the both-parse subset: describe only, do not
  deploy, and report how many settings this applies to. (This already holds for the three OLMo
  settings from E5-e; re-report them here under the same treatment for consistency.)
- Whatever the outcome, the main text reports the share of measured disagreement that is driven by
  exactly one INVALID output, separately for the 18 main settings and for the 7 cross-family settings.
- Whatever the outcome, the paper states the asymmetry explicitly: when the *reference* output is
  unparseable, a policy that omits the path really does change what the deployed system returns, so
  counting it as a change is correct accounting rather than a parser artifact. The parser question
  bites only where the *receiver* output is unparseable.

## Step 3. E11-b: intersection of two extraction conventions

The official C2C evaluator's answer extraction reads option letters A-D only, so it applies to the
OBQA and ARC settings, not to MMLU-Pro (A-J). Applicable settings: 12 main (3 pairs x {Text, C2C} x
{OBQA, ARC}), 4 X1 Llama, 2 X2 OLMo (OBQA, ARC), 1 Text+fact = 19 settings.

For each applicable setting, relabel the saved raw calibration and development outputs with the
official extractor, keep the 20 fit-split thresholds unchanged, and redo the 20 exact binomial tests.
Report per setting: the largest accepted q under our frozen parser V2, the largest accepted q under
the official extractor, and whether the setting is deployed under (i) V2 only, (ii) official only,
(iii) both, (iv) neither. Report the intersection set explicitly. Also report, per setting, the
number of rows whose label differs between the two conventions, split by whether the row is inside
the E5-a exposure set X (341 reviewed calibration questions) or outside it.

E5-a already did this for the large pair; those numbers must be reproduced exactly here before the
remaining settings are added. If they do not reproduce, STOP and report.

### Reporting rules for E11-b (fixed in advance)

- If the intersection equals the current set of deployed settings among the 19: the main text states
  that the boundary is unchanged under a second, equally standard extraction convention.
- If the intersection is smaller: the main text names every setting that flips and under which
  convention, the boundary table carries a marker for them, and Section 7 states that a different but
  equally standard extraction changes the outcome for those settings. (large/ARC/C2C is already known
  to flip and large/OBQA/C2C is already known to drop to q = .70; both must appear in the main text.)
- If the intersection is larger: describe only, do not deploy.
- We state which convention we recommend to an operator and why, in one sentence, in Section 7.

## Step 4. E11-c: deployable INVALID routing rule (Rule D)

Rule D: if the receiver-only output does not parse, route to the reference; otherwise apply the
usual threshold rule. Rule D reads only the receiver's own output, never the reference's, so it is
deployable. It costs nothing extra: parsing the receiver output is already part of the policy.

Under Rule D the omission set at threshold tau becomes {x : u(x) <= tau and o_R(x) parses}, and the
controlled quantity is unchanged: rho_D(tau) = P(o_R != o_b | omitted under Rule D). Certification
uses the same 20 fit-split thresholds, the same alpha, delta and Bonferroni correction, applied to
the calibration split. This is a separate family of 26 x 20 tests and is labelled a post hoc
analysis.

For each of the 26 settings report: the largest accepted q under Rule D, the calibration n and k and
p-value at that q, the development coverage expressed both as a fraction of all development
questions and as a fraction of development questions whose receiver output parses, the conditional
change rate, and the accuracy of the Rule-D policy against the reference.

### Reporting rules for E11-c (fixed in advance)

- If Rule D certifies settings that ProbeMax alone cannot certify: the main text states how many and
  which. If those include OLMo settings, the abstract's and Contribution 3's statement that all seven
  cross-family settings fall back is rewritten to say that they fall back under the frozen rule and
  that routing unparseable receiver outputs to the reference, a rule that reads only the receiver,
  certifies X of them. The "Answer format matters" paragraph in Section 4.3 is expanded accordingly.
- If Rule D certifies nothing new: the main text states in one sentence that a deployable
  INVALID-routing rule also does not extend the certified set, reported alongside the helper-aware
  gate result from E9c.
- If Rule D causes a currently deployed setting to lose certification: report it as is. The frozen
  deployments and all replays are unchanged.
- Coverage loss under Rule D is reported as is, including the large losses expected where the
  receiver INVALID rate is high, and is described as a cost of answer format rather than of
  communication.

## What does not change

No threshold, deployment, replay, latency number or frozen protocol is revised by E11. E11 produces
diagnostics and one additional post hoc rule. All three parts are reported whatever the outcome.
