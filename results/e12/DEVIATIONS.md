# E12 deviations from PREREG_E12.md

## E12-a

**None.** Every quantity listed in the prereg was computed, for every replay and arm in scope, in
both version (a) and version (b), with the frozen E3 definitions reused unchanged.

Two choices the prereg did not fix, recorded for completeness (neither is a departure from it):

- **Quantile estimator**: `numpy.percentile` defaults (linear interpolation). The prereg names p50,
  p90, p99, p10 but not an estimator. Note that with N = 128 (or 126-127 in version (b)) the p99 is
  interpolated between the top two observations and is therefore a weak statistic; the p99 finding
  reported ("never worse") is a negative result, so this does not soften it.
- **`large/MMLU-Pro-FULL`** is the label used for the full 2,641-question development MMLU-Pro C2C
  replay, to keep it visibly distinct from the 128-question MMLU-Pro panel in the same tables. The
  prereg lists it as "the full development MMLU-Pro C2C replay"; it is the same replay.

Nothing was changed after seeing results. The reporting rules in the prereg were evaluated as
written: the "p90 or p99 worse for a setting classified as a positive saving" branch fires, and the
"tails are not worse" branch does not.

## E12-b

**Not run, and not submitted.** This is the prereg's own "cannot run" branch, but the reason is not
the deadline and not the queue: the deployed implementation has no batched serving path, and
building one would mean re-implementing the official C2C fuser inside certified code. The evidence
and the three options are in `E12B_STATUS.md`.

Specifically **not** done, and deliberately so:

- No job was submitted, although both ClusterA debug positions were free.
- The batch-8 vs batch-1 output identity check on 8 panel questions (step 3b) was **not** run,
  because there is no batch-8 path to compare against. Writing one today would fail that check by
  construction (padded batched attention does not reproduce unpadded single-sequence logits
  bit-for-bit), which would be a property of new code rather than of the deployed system.
- No threshold, panel or frozen protocol was changed, and nothing under any existing `P2_*` folder
  was modified. All E12 output is under `P2_R4_E12_20260920T225858Z/`.

## Incidental (not a prereg deviation)

An early exploratory command was run with the system `/usr/bin/python3` from inside
`P2_R1_E3POL_REPEAT1_20260919T075315Z/`. It segfaulted on the known ClusterA login-node OpenBLAS/numpy
import failure and left a core dump (`core.2491270`, 6.4 MB) in that folder. The core file was
deleted; no data file in that folder was read-modified or written, and the folder now has zero files
newer than the start of this session. All later work used
`$DATA_ROOT/software/envs/c2c_official/bin/python` with `OPENBLAS_NUM_THREADS=1`.
