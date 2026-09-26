# E12 preregistration (Round 4, 2026-09-20)

## E12-a: per-query latency distribution from existing records

No new compute. For every replay already recorded, and for each arm within it, compute from the
stored per-request timings:

- the per-query latency quantiles p50, p90 and p99 for the policy and for the fixed reference;
- the paired per-query difference (fixed minus policy) at the 10th, 50th and 90th percentiles;
- the fraction of queries that are slower under the policy than under the fixed reference;
- the same three quantities restricted to omitted queries and to routed queries separately.

Scope: the 8 deployed policies in the original ClusterB replays; the same 8 in each of the 3 ClusterA
E3 repeats; the FIXED, ORIGINAL, REUSE and ARGMAX arms of E7; the E6 Text+fact replay; and the full
development MMLU-Pro C2C replay. Report version (a) with cold requests retained and version (b) with
the first post-load request removed, exactly as E3 did. Do not merge numbers across machines.

### Reporting rules for E12-a (fixed in advance)

- Whatever the numbers show, the main text states explicitly that the reported saving is a mean of
  paired per-query differences, and gives the paired median alongside it for at least the two
  settings used as examples.
- If the policy's p90 or p99 is worse than the fixed reference for any setting currently classified
  as a positive saving: the main text reports that setting's tail numbers and says that a positive
  mean saving can coexist with a worse tail. Contribution 4 is reworded to name the mean explicitly.
- If the tails are not worse: the main text says so in one sentence and gives the range.
- The ARGMAX arm is reported with the same quantities, because it is the implementation where the
  mean saving is largest, and the question of whether its tail behaves differently is the same
  question.

## E12-b: one replay at a second batch size

Two already-deployed policies, chosen in advance: large/OBQA/Text, which has the largest measured
saving, and large/MMLU-Pro/C2C, whose saving classification is the one marked as not established on
the original panel. Frozen thresholds and frozen 128-question panels, unchanged.

Four arms, rotated within a single allocation so that they share the same machine state:
  (1) fixed reference, batch size 1
  (2) policy, batch size 1
  (3) fixed reference, batch size 8
  (4) policy, batch size 8
At batch size 8 the requests of an arm are served in groups of 8 in panel order. For the policy, the
probe is batched over the group, and the reference is then batched over whichever members of that
group are routed, so a routed group may be smaller than 8. No warm-up. Cold requests retained.
Three repeats of the whole rotation. One policy per node, 2 cards per node (helper on GPU0,
receiver and fuser on GPU1), matching the placement used in E3.

Estimator at batch size 1: paired mean saving with a paired bootstrap interval (seed 0, 2,000
resamples), as in E3, giving the in-run control. Estimator at batch size 8: wall-clock time to
complete the whole 128-question panel, reported for each of the 3 repeats, plus the per-query mean
obtained by dividing by 128. Classification at batch size 8: faster if the policy panel time is
below the fixed reference panel time in all 3 repeats, slower if above in all 3, otherwise not
established.

This is a second serving configuration. Its numbers are reported on their own and are never merged
with, or subtracted from, the paper's batch-size-one numbers.

### Reporting rules for E12-b (fixed in advance)

- If both policies keep their batch-size-one classification at batch size 8: the main text adds one
  sentence saying the saving classification for these two settings survives a second batch size, and
  Section 7 keeps the serving-stack limitation unchanged.
- If a classification changes at batch size 8: the main text reports both batch sizes for that
  setting, Contribution 4 is narrowed to state the batch size, and Section 7 says that the saving
  classification is batch-size dependent, with the observed direction.
- If the job cannot run before the deadline below: the paper reports E12-a only, and Section 7 keeps
  the existing statement that latency is measured at batch size one.

## Budget and deadline

E12-a has no budget. E12-b: stop and report if it would need more than one debug job or more than
50 minutes of work. If E12-b has not produced results by 2026-09-23 12:00 CDT, report E12-a only.
