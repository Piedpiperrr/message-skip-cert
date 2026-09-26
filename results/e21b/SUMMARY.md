# E21B summary: option-rotation rerun of the frozen large-pair policies

**Writing rule (1) applies.** Every policy's Clopper-Pearson upper end is below 5%; the largest is 4.27%
(large/OBQA/Text+fact, 14/545). The run was complete by the cutoff: the last production output was at
2026-09-22T07:32:27Z, before 2026-09-22T23:00:00Z. Preflight passed.

## Provenance

| item | value |
|---|---|
| PREREG.md SHA-256 | `15ac70109105207ffd37b124149429ee4afb867c68a9b7928de16c7b0921617e`, hashed 2026-09-22T07:12:59Z (`PREREG.sha256`, which also holds the driver, rotation and statistics hashes) |
| job | ClusterA debug 7643984, select=2 (4 slots x 2 GPUs), 07:13:09Z-07:32:32Z, Exit_status 0, walltime used 00:19:18 |
| preflight gate | PASS at 07:17:43Z (`preflight/PREFLIGHT_GATE.json`, SHA `83de3363…ca41`) |
| first rotated output | 07:16:57Z (P3 smoke); production 07:18:18Z-07:32:27Z |
| manifest | `results/MANIFEST.json`, SHA `a807f587…c5a`, hashed 07:33:09Z, before any statistic (`results/MANIFEST.sha256`). ARC 4,688 records = 1,172 x (probe, R, Text, C2C); OBQA 3,720 = 744 x (probe, R, Text, C2C, Text+fact); 0 missing, 0 duplicate, 0 unexpected |
| statistics | `src/e21b_stats.py stats` (SHA `d757b573…71a2`, unchanged since the PREREG hash), run 07:33:21Z. Output: `results/E21B_RESULTS.json` (SHA `2377e66f…97cf1`) |
| gold | not read |

Preflight:
- **P1 (identity rotation vs stored outputs, 16 rows per population):**
  - Every arm was byte-identical on 16/16: Text helper, Text, C2C, and on OBQA also Text+fact helper and Text+fact.
  - R was byte-identical on 32/32, and u was bitwise equal on 32/32.
  - The probe input IDs and the builder-determined prompt lengths equal both the stored values and the frozen builders on every row.
- **P2:** 0 failures on 44 ARC rows (16 plus the 28 with K != 4 or numeric labels) and on 16 OBQA rows.
- **P3 (INVALID out of 16 rotated rows):** ARC R 0, Text 0, C2C 0; OBQA R 0, Text 0, C2C 1, Text+fact 0.

## Writing rule that applies (quoted verbatim from PREREG.md)

> (1) every policy has a CP upper end < 5% -> Sec. 6 (u = 0 paragraph) clause: "Under option rotation on the sealed ARC
>     and held-out OBQA questions, the five frozen large-pair policies omit X-Y% of questions (X'-Y'% in the original
>     order) and change A-B% of omitted answers (upper bounds below 5%; App. X)." Appendix table with all statistics.

Deciding numbers: the CP upper ends are 3.55%, 2.70%, 3.79%, 3.57% and 4.27%, all below 5%. No k/n exceeds 5%, so
rule (2) does not apply. Rule (4) does not apply: the run was complete and on time, and preflight passed.

Clause with the numbers filled in:

> Under option rotation on the sealed ARC and held-out OBQA questions, the five frozen large-pair policies omit
> 73.3-93.9% of questions (75.0-93.9% in the original order) and change 1.7-2.6% of omitted answers (upper bounds
> below 5%; App. X).

Where the numbers come from:
- X-Y is the range of n/N under rotation: 545/744 = 73.25% to 1,100/1,172 = 93.86%.
- X'-Y' is the same range in the original order: 558/744 = 75.00% to 1,100/1,172 = 93.86%.
- A-B is the range of k/n: 18/1,049 = 1.72% to 14/545 = 2.57%.

## Primary statistics (`results/primary_policies.csv`)

u_rot is the probe score on the rotated question. Omitted means u_rot <= tau, and k counts omitted questions where
R_rot != reference_rot. Answers are mapped back to the original option index, parser V2, INVALID as its own symbol.
p is the one-sided exact binomial P[Bin(n,.05) <= k]; it is descriptive, not a certificate.

| policy | q (tau) | N | u_rot = 0 | omitted n (coverage; original) | k | k/n [CP 95%] | p | k at u_rot = 0 / u_rot > 0 | original k/n [CP 95%] |
|---|---|---|---|---|---|---|---|---|---|
| large/ARC/Text | .95 (0.01800704002380371) | 1,172 | 845 (72.1%) | 1,100 (93.9%; 93.9%) | 27 | 2.45% [1.62, 3.55] | 1.52e-05 | 0/845 ; 27/255 | 20/1,100 = 1.82% [1.11, 2.79] |
| large/ARC/C2C | .90 (0.0007095932960510254) | 1,172 | 845 (72.1%) | 1,049 (89.5%; 89.3%) | 18 | 1.72% [1.02, 2.70] | 1.94e-08 | 3/845 ; 15/204 | 11/1,047 = 1.05% [0.53, 1.87] |
| large/OBQA/Text | .80 (0.001170039176940918) | 744 | 343 (46.1%) | 582 (78.2%; 80.0%) | 13 | 2.23% [1.19, 3.79] | 5.40e-04 | 1/343 ; 12/239 | 12/595 = 2.02% [1.05, 3.50] |
| large/OBQA/C2C | .80 (0.001170039176940918) | 744 | 343 (46.1%) | 582 (78.2%; 80.0%) | 12 | 2.06% [1.07, 3.57] | 2.22e-04 | 1/343 ; 11/239 | 13/595 = 2.18% [1.17, 3.71] |
| large/OBQA/Text+fact | .75 (0.0002611875534057617) | 744 | 343 (46.1%) | 545 (73.3%; 75.0%) | 14 | 2.57% [1.41, 4.27] | 3.38e-03 | 2/343 ; 12/202 | 16/558 = 2.87% [1.65, 4.61] |

The original-format k/n values are the stored numbers quoted in the PREREG. `e21b_stats.py` recomputed each one
from the stored outputs and got the same value (columns `orig_k_recomputed_from_stored` and
`orig_n_recomputed_from_stored`). The original CP intervals are computed by the same function.

## Secondary statistics (descriptive)

R_rot (mapped back) vs stored R_orig (`results/secondary_R_agreement.csv`). On sealed ARC, R_orig exists only for the
1,100 questions omitted at the frozen Text tau.

| population | subset | agree / n |
|---|---|---|
| sealed ARC | all with stored R | 1,052/1,100 = 95.6% |
| sealed ARC | u_orig = 0 | 826/837 = 98.7% |
| sealed ARC | u_orig > 0 | 226/263 = 85.9% |
| held-out OBQA | all | 641/744 = 86.2% |
| held-out OBQA | u_orig = 0 | 339/346 = 98.0% |
| held-out OBQA | u_orig > 0 | 302/398 = 75.9% |

u_orig = 0 questions that keep u_rot = 0 (`results/secondary_u0.csv`):

| population | u_rot = 0 among u_orig = 0 | u_rot = 0 among all |
|---|---|---|
| sealed ARC | 753/837 = 90.0% | 845/1,172 |
| held-out OBQA | 269/346 = 77.7% | 343/744 |

Reference answer under rotation (mapped back) vs original, per reference (`results/secondary_b_agreement.csv`):

| population | reference | agree / N |
|---|---|---|
| sealed ARC | Text | 1,122/1,172 = 95.7% |
| sealed ARC | C2C | 1,056/1,172 = 90.1% |
| held-out OBQA | Text | 659/744 = 88.6% |
| held-out OBQA | C2C | 589/744 = 79.2% |
| held-out OBQA | Text+fact | 686/744 = 92.2% |

INVALID counts per arm (`results/invalid_counts.csv`). The sealed ARC original R has only 1,100 stored outputs.

| population | arm | rotated | original |
|---|---|---|---|
| sealed ARC | R | 1/1,172 | 0/1,100 |
| sealed ARC | Text | 0/1,172 | 0/1,172 |
| sealed ARC | C2C | 2/1,172 | 1/1,172 |
| held-out OBQA | R | 0/744 | 1/744 |
| held-out OBQA | Text | 0/744 | 0/744 |
| held-out OBQA | C2C | 1/744 | 3/744 |
| held-out OBQA | Text+fact | 0/744 | 0/744 |

## Sanity check (not in the PREREG; nothing written to results)

Large/ARC/Text omits exactly 1,100 questions both under rotation and in the original order. A read-only check shows
this is a coincidence of totals, not a copy of the stored scores:
- 1,056 questions are omitted in both orders, 44 only under rotation and 44 only in the original order.
- u_rot equals the stored u bitwise on 757/1,172 ARC and 273/744 OBQA questions, nearly all of them with u = 0.
