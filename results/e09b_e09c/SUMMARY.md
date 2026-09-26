# SUMMARY — P2_R3_E9BC_20260920T061042Z (E9b and E9c)

Paper A (ICLR 2027), ClusterA. E9b ran under `PROTOCOL_FREEZE_E9B.md` as amended by
`PROTOCOL_AMENDMENT_E9B.md`; E9c ran under `PROTOCOL_FREEZE_E9C.md`. Deviations are in `DEVIATIONS.md`.

| record | SHA-256 | UTC |
|---|---|---|
| `PROTOCOL_FREEZE_E9B.md` | `d211e4ad6eb267f389ec449482b21e4637e732383552678bea2f81d4cb8d0bbe` | 2026-09-20T06:21:01Z |
| `PROTOCOL_AMENDMENT_E9B.md` | `bd951a3fc35e4bb080db847f0aa4c87901791588687d86263bf609fb82d65506` | 2026-09-20T06:44:34Z |
| `PROTOCOL_FREEZE_E9C.md` | `38c4a26bd5cb8e7378949669197175e890a3c2f1c6588a3f431eb2490756c0df` | 2026-09-20T06:22:06Z |

## Population

The 744 **held-out OBQA questions never used by this study**; an earlier project stage (gate2b/gate2d,
2026-07-26/27) scored **small-pair** outputs on them. They are not sealed and are never described as such.
Checks C1 and C2 both PASS: no medium- or large-pair output, score, route or latency of these questions
exists in any project record, and no design choice of this study reads or references the gate2b
predictions, the gate2d scored targets, or these ids. Details in `PROTOCOL_AMENDMENT_E9B.md` §3-§5.

## Validation (bit for bit, before any main output)

8 saved OBQA fit rows per action per pair, comparing `raw_answer` and `generated_token_ids` exactly
(probes: `ProbeMax`, argmax and `probe_ids_sha256`). **Zero mismatches everywhere.**

| rank | pair | probe | R | Text | C2C | Text+fact |
|---|---|---|---|---|---|---|
| 0 | large | 0 | 0 | 0 | 0 | 0 |
| 1 | large | 0 | 0 | 0 | 0 | 0 |
| 2 | large | 0 | 0 | 0 | 0 | 0 |
| 3 | medium | 0 | 0 | — | 0 | — |

## E9b — frozen policies on the 744 held-out questions

Seal receipt `analysis/SEAL_RECEIPT.json` written **2026-09-20T10:36:51Z**, before the answer key was opened.
Test: exact binomial, H0: rho >= .05 at the frozen threshold. Interval: two-sided Clopper-Pearson 95%.
Accuracy interval: paired bootstrap, 2,000 resamples, seed 0, unit = question. No latency was measured.

| policy | omitted | changed | rate [CP 95%] | p | always-omit rate | accuracy policy / reference [95% of diff] |
|---|---:|---:|---|---|---:|---|
| medium / OBQA / C2C, q=.55 | 388 | 8 | 0.0206 [0.0089, 0.0402] | 2.52e-03 | 0.1747 | 0.6116 / 0.6089 [-0.0054, +0.0108] |
| medium / OBQA / C2C, q=.50 (exposure-free) | 346 | 6 | 0.0173 [0.0064, 0.0374] | 1.38e-03 | 0.1747 | 0.6116 / 0.6089 [-0.0040, +0.0094] |
| large / OBQA / Text, q=.80 | 595 | 12 | 0.0202 [0.0105, 0.0350] | 1.47e-04 | 0.0820 | 0.8602 / 0.8696 [-0.0188, -0.0013] |
| large / OBQA / C2C, q=.80 | 595 | 13 | 0.0218 [0.0117, 0.0371] | 3.65e-04 | 0.0833 | 0.8145 / 0.8024 [+0.0040, +0.0215] |
| large / OBQA / Text+fact, q=.75 | 558 | 16 | 0.0287 [0.0165, 0.0461] | 9.20e-03 | 0.1102 | 0.8965 / 0.9113 [-0.0255, -0.0054] |

**Every policy rejects H0: rho >= .05** (all p <= .05), so each frozen threshold keeps the conditional
change rate under 5% on this held-out population. The accuracy consequences differ by reference:
omitting **C2C** gains accuracy (+1.21 pp, interval excludes 0), while omitting **Text** (-0.94 pp) and
**Text+fact** (-1.48 pp) lose accuracy with intervals that also exclude 0; medium/OBQA/C2C is flat
(+0.27 pp, interval spans 0) at both q. Every policy is reported whatever its outcome.

The two medium rows share 455 correct by arithmetic, not by error: of the 42 questions that change omit
status between q=.55 and q=.50, only 2 have o_R != o_C, and they cancel (`10-920` gains, `11-359` loses).

## E9c — helper-aware gate score s_G = u_R + 1[argmax_H != argmax_R]

Development AUROC for receiver-reference disagreement; certification is the frozen family
(20 fit-quantile candidates of s_G, alpha=.05, per-candidate p<=.001, largest accepted q, separate family).

| setting | AUROC u_R | AUROC s_G | diff | q frozen | q under s_G | dev coverage | changed/omitted |
|---|---|---|---|---|---|---|---|
| small/obqa/T | 0.64143 | 0.69005 | +0.04862 | 0.0 | 0.0 | 0.0000 | None/0 |
| small/obqa/C | 0.70023 | 0.67980 | -0.02044 | 0.0 | 0.0 | 0.0000 | None/0 |
| small/arc/T | 0.63399 | 0.66619 | +0.03220 | 0.0 | 0.0 | 0.0000 | None/0 |
| small/arc/C | 0.64065 | 0.65585 | +0.01520 | 0.0 | 0.0 | 0.0000 | None/0 |
| medium/obqa/T | 0.78654 | 0.82732 | +0.04078 | 0.0 | 0.0 | 0.0000 | None/0 |
| medium/obqa/C | 0.84011 | 0.74486 | -0.09525 | 0.55 | 0.4 | 0.3922 | 5/291 |
| medium/arc/T | 0.74218 | 0.79165 | +0.04948 | 0.0 | 0.0 | 0.0000 | None/0 |
| medium/arc/C | 0.90974 | 0.80196 | -0.10778 | 0.6 | 0.5 | 0.4548 | 1/136 |
| large/obqa/T | 0.87273 | 0.90340 | +0.03067 | 0.8 | 0.8 | 0.8046 | 19/597 |
| large/obqa/C | 0.88265 | 0.85227 | -0.03038 | 0.8 | 0.75 | 0.7278 | 14/540 |
| large/arc/T | 0.95188 | 0.94308 | -0.00880 | 0.95 | 0.95 | 0.9331 | 5/279 |
| large/arc/C | 0.90883 | 0.88995 | -0.01887 | 0.9 | 0.85 | 0.8428 | 3/252 |
| large/mmlu_pro/T | 0.82147 | 0.77875 | -0.04272 | 0.4 | 0.35 | 0.3571 | 31/943 |
| large/mmlu_pro/C | 0.84640 | 0.76002 | -0.08638 | 0.4 | 0.3 | 0.3037 | 24/802 |
| large/obqa/Text+fact | 0.88859 | 0.92443 | +0.03584 | 0.75 | 0.8 | 0.8046 | 16/597 |
| large/obqa/Text+fact [with-fact prefill, descriptive] | 0.88859 | 0.94836 | +0.05976 | 0.75 | 0.85 | 0.8450 | 14/627 |

small/MMLU-Pro and medium/MMLU-Pro are **not available**: E8 stopped at 31 of 32 lanes, so the frozen
condition "if E8 has finished" was not met. They are reported as unavailable, not as results.

### Helper prefill cost on the frozen replay panels (batch 1)

| population | n | core ms | prefill ms | tokenize ms | label ms | input tokens |
|---|---:|---:|---:|---:|---:|---:|
| small/obqa | 128 | 17.37 | 16.46 | 0.46 | 0.37 | 137.2 |
| small/arc | 128 | 17.37 | 16.41 | 0.51 | 0.36 | 160.4 |
| medium/obqa | 128 | 20.24 | 19.33 | 0.46 | 0.37 | 137.2 |
| medium/arc | 128 | 20.51 | 19.54 | 0.52 | 0.37 | 160.4 |
| large/obqa | 128 | 25.90 | 24.97 | 0.47 | 0.37 | 137.2 |
| large/arc | 128 | 27.02 | 26.05 | 0.51 | 0.37 | 160.4 |
| large/mmlu_pro | 128 | 35.48 | 33.95 | 0.72 | 0.72 | 301.9 |

### Hypothesis H

Prediction: the helper-agreement gate raises development AUROC for Text-induced changes more than for
C2C-induced ones — mean gain larger for Text, and larger in at least 5 of 7 populations.

| | mean AUROC gain |
|---|---|
| Text | +0.02146 |
| C2C | -0.04913 |
| difference | +0.07059 |

Text gain exceeds C2C gain in **7 of 7** populations. **Verdict: SUPPORTED** (post hoc).

The gate helps Text-induced changes and hurts C2C-induced ones, the direction H predicts: Text-induced
changes follow the helper's own answer, which the receiver cannot see, while C2C-induced ones do not.

**No setting falls back under ProbeMax and deploys under s_G**, so the end-to-end replay of protocol E9C
is not triggered. No setting loses its deployment either. Several C2C settings become more conservative
under s_G (medium/OBQA/C2C .55 -> .40, medium/ARC/C2C .60 -> .50, large/OBQA/C2C .80 -> .75,
large/ARC/C2C .90 -> .85, large/MMLU-Pro .40 -> .35 and .30), while Text+fact rises .75 -> .80.

## Jobs

| job | machine | queue | resources | walltime | purpose | state |
|---|---|---|---|---|---|---|
| 7638751 | ClusterA | debug | select=2, 8x A100 40GB | 00:50:00 | E9b validation + main (large shards 0,2; medium) and all four E9c lanes | completed; rank 1 lost to a filename race |
| 7638821 | ClusterA | debug | select=1, 2 of 4 A100 used | 00:30:00 | E9b retry, large shard 1 of 3 | completed, 248/248 |

One earlier `submit-job` at 2026-09-20T08:26:58Z was rejected by the per-user queued-job limit; nothing was
submitted and no GPU time was used (`jobs/SUBMISSION.json`).

## Gold discipline

No gold label was read in either GPU job or anywhere in E9c. For E9b the answer key was opened exactly
once, by `src/e9b_decode.py`, after `analysis/SEAL_RECEIPT.json` recorded the SHA-256 of the sealed
scores, routes and outputs; `e9b_decode.py` re-verifies those three hashes before reading it.


---

# EXTENSION — the four E8 settings (2026-09-20)

E8 completed all 32 lanes (cleanup job 7639377), so the E9C freeze's own condition "small/medium
MMLU-Pro **if** E8 has finished" is met. Verified before running: 32/32 lanes, and for both pairs all
3,000 fit / 6,000 calibration / 2,641 development representatives have a probe and complete R/T/C
actions, with 0 missing. The E8 session is not running. `src/e9c_plan.py` was re-run unchanged and
added exactly three tasks to lane 0 and three to lane 1 (23,282 prefills); job `7639412` ran them,
0 skipped. One recorded change to `src/e9c_analyze.py` was needed; see `DEVIATIONS.md`.

## The four new settings

| setting | AUROC u_R | AUROC s_G | diff | q frozen | q under s_G | dev coverage | changed/omitted |
|---|---|---|---|---|---|---|---|
| small/mmlu_pro/T | 0.64385 | 0.68031 | +0.03646 | 0.0 | 0.0 | 0.0000 | None/0 |
| small/mmlu_pro/C | 0.62582 | 0.61865 | -0.00717 | 0.0 | 0.0 | 0.0000 | None/0 |
| medium/mmlu_pro/T | 0.71655 | 0.70070 | -0.01585 | 0.0 | 0.0 | 0.0000 | None/0 |
| medium/mmlu_pro/C | 0.76524 | 0.72714 | -0.03810 | 0.0 | 0.0 | 0.0000 | None/0 |

All four fall back under ProbeMax (frozen q = 0.0, `fixed_reference`) **and** under s_G: no candidate
q was accepted for any of them, so development coverage is 0 and nothing is omitted. **No setting
falls back under ProbeMax and deploys under s_G, so no end-to-end replay is triggered.**

Helper-agreement rate on these populations is high — 0.332-0.362 for the small helper and 0.574-0.606
for the medium helper — so s_G lifts a third to well over half of all questions above every finite
threshold, which is why no candidate certifies.

## Helper prefill cost per pair (batch 1, frozen 128-question MMLU-Pro panel)

| population | n | core ms | prefill ms | tokenize ms | label ms | input tokens |
|---|---:|---:|---:|---:|---:|---:|
| large/mmlu_pro | 128 | 35.48 | 33.95 | 0.72 | 0.72 | 301.9 |
| small/mmlu_pro | 128 | 17.87 | 16.34 | 0.73 | 0.72 | 301.9 |
| medium/mmlu_pro | 128 | 20.79 | 19.27 | 0.71 | 0.73 | 301.9 |

## Hypothesis check

**Prespecified, seven populations (unchanged):** mean AUROC gain Text **+0.02146**, C2C **-0.04913**,
difference **+0.07059**; Text larger in **7 of 7**. Verdict **SUPPORTED**. Preserved verbatim in
`analysis/E9C_RESULTS_7pop_original.json`, and re-verified field by field after the code change.

**Extension, nine populations (not a prespecified rule):** mean AUROC gain Text **+0.01898**, C2C
**-0.04324**, difference **+0.06222**; Text larger in **9 of 9**.

| population | Text gain | C2C gain | Text larger |
|---|---|---|---|
| large/arc | -0.00880 | -0.01887 | True |
| large/mmlu_pro | -0.04272 | -0.08638 | True |
| large/obqa | +0.03067 | -0.03038 | True |
| medium/arc | +0.04948 | -0.10778 | True |
| medium/mmlu_pro *(new)* | -0.01585 | -0.03810 | True |
| medium/obqa | +0.04078 | -0.09525 | True |
| small/arc | +0.03220 | +0.01520 | True |
| small/mmlu_pro *(new)* | +0.03646 | -0.00717 | True |
| small/obqa | +0.04862 | -0.02044 | True |

Nothing contradicts the earlier verdict: both new populations also have a larger Text gain than C2C
gain, so the direction holds in 9 of 9. `E9C_RESULTS.json` reports `"verdict": "INCOMPLETE"` for the
enlarged set because the hashed script applies its count rule only when there are exactly seven
populations; that is the script declining to restate a seven-population rule over nine, not a failure
of the hypothesis. The analysis remains labelled post hoc.

| job | machine | queue | resources | walltime | purpose | state |
|---|---|---|---|---|---|---|
| 7639412 | ClusterA | debug | select=1, 2 of 4 A100 40GB | 00:30:00 | E9c extension prefills, small and medium MMLU-Pro | completed, 23,282/23,282 |
