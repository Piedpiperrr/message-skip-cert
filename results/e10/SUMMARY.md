# E10 — short-answer demonstration (GSM8K, large pair, Text reference)

**Outcome: no threshold certifies.** The procedure falls back to always communicating.
PREREG_E10 §"Reporting rules" therefore applies the negative-result rule: the main text states
this plainly, reports the disagreement rate and the AUROC, and the title, abstract and
contribution list are explicitly narrowed to two-agent multiple-choice communication.

## Sealing

| item | value |
|---|---|
| PREREG_E10.md sha256 | `a07185d35c84533e8a4d5c9054a60ab868a11a709c3f9ffb15276de532e0d785` @ 2026-09-20T23:00:28Z |
| src/e10_extract.py sha256 | `c7f5a0f2452da787c7af1620da668f3a9824094046b3d8766b58c81831ba984c` @ 2026-09-20T23:01:04Z |
| src/e10_prompts.py sha256 | `8d5809beb9451e1670a468a3213ccc8435fdc24694c0ddf8d7742c2a86c2afc7` |
| step-5 seal (analysis/SEAL_RECEIPT.json) | `49b31f3561c1c885f61e234d92603c7ac5c1051e4967abb3017f8569c9dda8c8` @ **2026-09-21T00:11:27Z** |
| gold first opened | **2026-09-21T00:11:35Z** (analysis/GOLD_DECODE.utc) |

The extractor was written and hashed before any model output existed and passed 12/12 synthetic
cases. The seal receipt fixes the sha256 of all eight record shards and of every analysis output;
`src/e10_decode.py` re-verifies all of them before opening the answer column, and did so.

Dataset: `openai/gsm8k`, config `main`, train split, revision
`740312add88f781978c0658806c59bc2815b9866` (Hub API sha == local snapshot; parquet sha256
`ea82612ea9582142387730c793eb67d3b12849002bc0b7fa6f8efafa7351419d`), 7,473 rows, 0 duplicate
question strings. Splits 400 fit / 1,000 cal / 400 dev by ascending sha256 of the question
string, formed from question text only (SPLIT_FREEZE_E10.json).

Pre-flight: all 8 ranks reproduced 16 stored OBQA fit rows bit for bit on the receiver-only and
Text paths (128 + 128 rows, 0 mismatches), through the unchanged frozen 64-token code paths.
Teacher-forced re-scoring check on 16 smoke questions: exact retokenisation 16/16, maximum
absolute difference between re-scored and generation log-probabilities **0.0**.

## Certification

20 candidate quantiles of u on the fit split; exact binomial test of H0: rho(tau) >= .05 on the
1,000 calibration questions; accept at p <= .001 per candidate (20 tests, family-wise bound .02).

**No candidate accepted.** Smallest p-value **1.000** at candidate q = 0.05, with calibration
n = 954 and k = 146. Every candidate gives p = 1.000.

The reason is that the preregistered score is degenerate on this task. 18 of the 20 fit
quantile thresholds are exactly 0.0; the 19th is 1.19e-07; the 20th is +inf. 378 of 400 fit
questions have u exactly 0.0, and 97.8% are below 1e-3. With ties retained as the frozen rule
requires, candidates q = .05 through q = .90 all select the same 954 calibration questions at a
conditional change rate of 0.1530, and q = 1 selects all 1,000 at 0.1740 — all far above
alpha = .05.

Mechanically: u is built from the log-probabilities of the answer tokens under greedy decoding.
After the receiver has written a full worked derivation, the number it restates at the end is
fully determined by its own preceding text, so those tokens carry essentially no residual
uncertainty and their log-probabilities round to 0.0 in fp32. The property claimed in
PREREG_E10 — that the score "reduces to ProbeMax when the answer is a single label token" — is
exactly what fails to transfer: with A/B/C/D the receiver has genuine uncertainty among the
labels, whereas with a number it has just derived it has none. This is a property of the score,
not a defect of the pipeline: s2, the same computation over the entire generated continuation,
is well behaved (0.0163 to 0.1952) and ranks disagreements better than u.

## Required reporting

**Accuracy** (gold read only after the seal above)

| split | receiver-only | Text | oracle{receiver, Text} |
|---|---|---|---|
| fit (n=400) | 0.8600 | — | — |
| cal (n=1000) | 0.8880 | 0.8760 | 0.9510 |
| dev (n=400) | 0.8775 | 0.8650 | 0.9475 |

The Text path **does not improve accuracy over the receiver alone** (-1.2 points on calibration,
-1.25 on development). PREREG_E10 §"Reporting rules" applies: the paper says so, and states that
this setting demonstrates the machinery in a non-label answer space and is not evidence about
informative messages. The oracle is reported for context: 0.9475 on dev, so the two paths are
genuinely complementary (33 dev questions receiver-only-correct, 28 Text-correct).

**Disagreement rate** (normalized exact match between the two paths): calibration **0.1740**,
development **0.1925**.

**INVALID rate per path**: 0 on every path and split — fit R 0/400, cal R 0/1000, cal T 0/1000,
dev R 0/400, dev T 0/400. The frozen extractor returned a number for all 3,200 generations.

**Development AUROC** (against the dev disagreement indicator): u **0.5795**, s2 **0.6444**,
s3 **0.5680**. The whole-continuation score s2 carries more signal than the preregistered u,
but neither is near a usable level. s2 and s3 are descriptive only and were not used for
certification.

**Accepted quantile**: none. Fallback = always communicate. Smallest p-value 1.000 at q = 0.05,
calibration n = 954, k = 146.

**Development coverage and conditional change rate**: coverage **0.0** (the fallback omits
nothing), so the conditional change rate is undefined. The always-omit change rate on dev, i.e.
the rate that would apply at q = 1, is **0.1925**.

**Policy vs the Text reference on development**: the fallback policy *is* the Text reference, so
accuracy 0.8650 vs 0.8650, difference **+0.0000**, paired bootstrap 95% interval
**[0.0000, 0.0000]** (seed 0, 2,000 resamples, paired by question). The interval is degenerate
because the two arms are identical question by question, not because of a bootstrap artefact.

**Questions where u = 1 because the answer was INVALID**: **0** (fit 0, cal 0, dev 0).

## Per-split INVALID counts and extractor behaviour on real outputs

| split / path | n | INVALID | "after last answer is" | "last number" fallback | hit 320-token cap | mean gen tokens |
|---|---|---|---|---|---|---|
| fit R  |  400 | 0 | 338 |  62 |  43 | 215.2 |
| cal R  | 1000 | 0 | 851 | 149 | 106 | 208.6 |
| cal T  | 1000 | 0 | 994 |   6 |   5 | 139.3 |
| dev R  |  400 | 0 | 339 |  61 |  49 | 210.7 |
| dev T  |  400 | 0 | 398 |   2 |   1 | 140.6 |

Extractor limitation, reported and **not fixed** as PREREG_E10 requires: on 15.2% of
receiver-only generations (62/400 fit, 149/1000 cal, 61/400 dev) the string "answer is" never
appeared and the extractor fell back to the last number in the generation. This tracks the
320-token truncation rate closely (43, 106 and 49 generations respectively ended at the cap
without finishing), so the dominant failure mode is a solution cut off before its final sentence,
whose last number is then a mid-derivation intermediate. The Text path is barely affected
(6/1000 and 2/400) because the helper's background sentence shortens the receiver's solution.

## Contamination

GSM8K is likely present in the pretraining data of both models; receiver-only accuracy of 0.86 to
0.89 is consistent with that. As PREREG_E10 states, the certified quantity is defined relative to
the deployed path rather than to gold, so contamination affects the reported accuracies but not
the target being controlled.

## Latency replay

Not run. It was conditional on a threshold certifying, and none did.

## Cost

Three ClusterA debug jobs, 6.72 GPU-hours of the 8 GPU-hour budget (7640152 aborted after 3.4 min
in the pre-flight, 7640159 the main 47-minute run on 2 nodes, 7640195 a 1-node job for the last
3 development Text rows). 3,200 generations plus 1,800 teacher-forced re-scoring passes, batch
size one throughout, 0 runtime errors.

See DEVIATIONS.md for every departure from the preregistration.
