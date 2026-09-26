# P2 R3 / E9-a — matched-null designs for the oracle headroom (CPU re-analysis)

Stage: `P2_R3_E9A_20260920T043713Z`  
Label: POST-HOC re-analysis (reviewer R3/E9-a); does not change any primary decision.

CPU re-analysis of saved outputs only: no model was run, nothing was submitted to a queue, and no file outside this folder was written or modified.

## 0. Pre-registration

The rules block was copied verbatim into `PREREG_E9A.md` before any number was computed.

- SHA-256: `59b245da817afce520cef49a3708cf937d88f0edee922d4ecbdcc099b33fcfb6`
- Bytes: 601
- Recorded (UTC): 2026-09-20T04:37:13Z
- Record: `results/e9a_prereg_record.json`

## 1. Design and definitions

All definitions are reused unchanged from the E5-c code (`P2_R2_CPU_20260919T220412Z/scripts/e5c.py`), which this stage imports through `r2_common`:

- **Pool** `P(x)` = the distinct answers of the V1 and V2 null controls at question `x` that differ from `o_R(x)`; `|P(x)| <= 2` by construction. A question is *eligible* when `P(x)` is nonempty.
- **Oracle** over a set of answer sources = the number of questions where at least one source is correct.
- **Gain** = oracle count minus the number of questions `R` gets right.
- **INVALID is a symbol and counts as incorrect**, both as an answer and as a pool member.
- **Ratio** = mean null gain / real gain.

The four designs, each with 1000 draws and `numpy.random.default_rng(0)` (one fresh stream per population):

1. **Per-reference Text** — real: gain over `R` of the oracle over {R, Text}; null: the same with `V_T*`, which changes exactly `m_Text` receiver answers (that many eligible questions drawn uniformly without replacement, each given a uniform draw from its pool, `o_R` kept elsewhere). **Per-reference C2C** is the same with `m_C2C`.
2. **Independent (E5-c)** — `V_T*` and `V_C*` drawn independently as above; oracle over {R, V_T*, V_C*}; real = oracle over {R, Text, C2C}.
3. **Joint-matched** — `a + b + c` distinct eligible questions drawn uniformly without replacement and roles assigned at random: on the `a` Text-only questions `V_T*` is a pool draw and `V_C* = o_R`; on the `b` C2C-only questions the reverse; on `c_same` of the both-questions a single pool draw serves as both; on the remaining `c - c_same` both-questions `V_T*` and `V_C*` are two different pool draws when `|P(x)| >= 2`, and are forced to the same answer when `|P(x)| = 1` (these forced cases are counted). Oracle over {R, V_T*, V_C*}; real = oracle over {R, Text, C2C}.

## 2. Ratios with question-level 95% intervals

Point estimates are the 1000-draw ratios (`results/e9a_ratios.csv`); intervals are the 2.5/97.5 percentiles of 2000 question-level bootstrap resamples with 100 null draws inside each resample (`results/e9a_bootstrap_intervals.csv`).

| population      | N    | independent (E5-c)   | per-ref Text         | per-ref C2C          | joint-matched        | forced-same/draw | under-matched |
|-----------------|------|----------------------|----------------------|----------------------|----------------------|------------------|---------------|
| small/OBQA      | 742  | 0.686 [0.595, 0.782] | 0.719 [0.606, 0.845] | 0.686 [0.584, 0.804] | 0.664 [0.573, 0.759] | 84.28            | no            |
| small/ARC       | 299  | 0.738 [0.608, 0.889] | 0.851 [0.671, 1.080] | 0.747 [0.598, 0.953] | 0.737 [0.605, 0.893] | 37.02            | no            |
| medium/OBQA     | 742  | 0.805 [0.692, 0.937] | 0.800 [0.680, 0.945] | 1.125 [0.880, 1.464] | 0.903 [0.769, 1.048] | 20.89            | no            |
| medium/ARC      | 299  | 0.772 [0.535, 1.060] | 0.742 [0.505, 1.057] | 1.705 [1.019, 3.449] | 0.845 [0.567, 1.144] | 8.27             | yes           |
| large/OBQA      | 742  | 0.701 [0.578, 0.856] | 0.547 [0.443, 0.665] | 1.313 [0.882, 2.175] | 0.761 [0.613, 0.935] | 3.74             | no            |
| large/ARC       | 299  | 0.562 [0.334, 0.803] | 0.498 [0.263, 0.778] | 0.986 [0.490, 2.970] | 0.641 [0.369, 0.900] | 1.00             | no            |
| large/MMLU-Pro  | 2641 | 0.884 [0.800, 0.981] | 0.861 [0.769, 0.969] | 1.246 [1.071, 1.447] | 0.970 [0.877, 1.079] | 133.30           | no            |
| **MEDIAN of 7** |      | 0.738 [0.659, 0.825] | 0.742 [0.644, 0.840] | 1.125 [0.895, 1.349] | 0.761 [0.676, 0.885] |                  |               |

The median row resamples each population independently inside every bootstrap iteration and takes the median of that iteration's 7 ratios, so the interval is the interval of the median, not the spread of the 7 point estimates.

### Pre-registered reading

The joint-matched median ratio is **0.761** (95% interval [0.676, 0.885]), which is at least .5. Under the pre-registered rules the abstract therefore keeps "oracle headroom is weak evidence for useful communication content" with the number 0.761. The whole interval lies above .5, so the decision does not depend on the resampling. The main text reports this joint-matched ratio with its interval; the independent (E5-c) and per-reference designs go to the appendix. "At most the remainder" is removed everywhere.

### Null-gain distributions

`results/e9a_null_draw_distribution.csv` holds the mean, SD and 2.5/50/97.5 percentiles of the 1000 null gains for every population and design (the spread of the null itself, as distinct from the bootstrap interval of the ratio).

## 3. Overlap between the two references

`a` = questions changed by Text only, `b` = by C2C only, `c` = by both, `c_same` = the both-questions where Text and C2C give the same answer, and `(a+c)(b+c)/N` = the number of both-questions expected if the two references changed answers independently (`results/e9a_overlap.csv`).

| population     | N    | a (Text only) | b (C2C only) | c (both) | c_same | (a+c)(b+c)/N | c / expected | a+b+c | eligible |
|----------------|------|---------------|--------------|----------|--------|--------------|--------------|-------|----------|
| small/OBQA     | 742  | 120           | 131          | 219      | 114    | 159.91       | 1.370        | 470   | 590      |
| small/ARC      | 299  | 45            | 60           | 100      | 54     | 77.59        | 1.289        | 205   | 231      |
| medium/OBQA    | 742  | 113           | 70           | 61       | 37     | 30.72        | 1.986        | 244   | 253      |
| medium/ARC     | 299  | 29            | 25           | 23       | 13     | 8.35         | 2.755        | 77    | 73       |
| large/OBQA     | 742  | 55            | 43           | 17       | 13     | 5.82         | 2.920        | 115   | 166      |
| large/ARC      | 299  | 11            | 8            | 4        | 3      | 0.60         | 6.644        | 23    | 27       |
| large/MMLU-Pro | 2641 | 277           | 472          | 284      | 126    | 160.59       | 1.768        | 1033  | 1115     |

## 4. Receiver confidence on changed answers (descriptive)

`u` = ProbeMax on the development split; the split point is the median of `u` on that population's fit split (`results/e9a_receiver_confidence.csv`).

| setting             | N dev | changed | fit-median u | median u (changed) | share u<=cut (changed) | median u (all dev) | share u<=cut (all dev) |
|---------------------|-------|---------|--------------|--------------------|------------------------|--------------------|------------------------|
| small/OBQA/Text     | 742   | 339     | 0.0233409    | 0.0402899          | 0.404                  | 0.0210935          | 0.511                  |
| small/OBQA/C2C      | 742   | 350     | 0.0233409    | 0.0484325          | 0.357                  | 0.0210935          | 0.511                  |
| small/ARC/Text      | 299   | 145     | 0.0300193    | 0.0761465          | 0.359                  | 0.0431347          | 0.455                  |
| small/ARC/C2C       | 299   | 160     | 0.0300193    | 0.0602286          | 0.362                  | 0.0431347          | 0.455                  |
| medium/OBQA/Text    | 742   | 174     | 2.98023e-07  | 0.0015012          | 0.149                  | 4.76837e-07        | 0.478                  |
| medium/OBQA/C2C     | 742   | 131     | 2.98023e-07  | 0.00669789         | 0.053                  | 4.76837e-07        | 0.478                  |
| medium/ARC/Text     | 299   | 52      | 0            | 0.00145984         | 0.269                  | 0                  | 0.582                  |
| medium/ARC/C2C      | 299   | 48      | 0            | 0.0125625          | 0.021                  | 0                  | 0.582                  |
| large/OBQA/Text     | 742   | 72      | 1.19209e-07  | 0.0294045          | 0.028                  | 1.19209e-07        | 0.512                  |
| large/OBQA/C2C      | 742   | 60      | 1.19209e-07  | 0.0262082          | 0.017                  | 1.19209e-07        | 0.512                  |
| large/ARC/Text      | 299   | 15      | 0            | 0.00858754         | 0.000                  | 0                  | 0.726                  |
| large/ARC/C2C       | 299   | 12      | 0            | 0.0268734          | 0.083                  | 0                  | 0.726                  |
| large/MMLU-Pro/Text | 2641  | 561     | 0.000740498  | 0.126435           | 0.130                  | 0.000637233        | 0.508                  |
| large/MMLU-Pro/C2C  | 2641  | 756     | 0.000740498  | 0.0953497          | 0.112                  | 0.000637233        | 0.508                  |

## 5. Validation

- **Exact expectations.** Every null design has a closed-form expected gain by linearity of expectation. Across all 28 (population x design) cells the 1000-draw Monte-Carlo mean agrees with the exact value to within 1.38% relative (`results/e9a_validation_exact_vs_mc.csv`).
- **E5-c reproduction.** The independent design reproduces the saved E5-c `rho` to within 0.003 in every population, and the median matches at 0.738 (`results/e9a_validation_vs_e5c.csv`).
- **Real gains.** The real gain over R of the oracle over {R, Text, C2C} matches the saved E5-c `gain_over_R_questions` exactly in all 7 populations.
- **V1/V2 coverage.** No V1 or V2 answer is missing in any population (0 of 5,764 development questions).

## 6. Files

| path                                     | contents                                                                                                 |
|------------------------------------------|----------------------------------------------------------------------------------------------------------|
| `PREREG_E9A.md`                          | the pre-registered rules block, verbatim                                                                 |
| `results/e9a_prereg_record.json`         | its SHA-256 and the UTC time it was recorded                                                             |
| `results/e9a_ratios.csv`                 | task 1 + 2: per-reference, independent and joint-matched ratios, forced-same counts, under-matched flags |
| `results/e9a_null_draw_distribution.csv` | mean/SD/percentiles of the 1,000 null gains per population and design                                    |
| `results/e9a_overlap.csv`                | task 4: a, b, c, c_same and (a+c)(b+c)/N                                                                 |
| `results/e9a_bootstrap_intervals.csv`    | task 3: 2,000-resample 95% intervals, per population and for the median of 7                             |
| `results/e9a_bootstrap_ratios.npy`       | the raw (2000, 7, 4) bootstrap ratio array                                                               |
| `results/e9a_receiver_confidence.csv`    | task 5: the 14 main settings                                                                             |
| `results/e9a_validation_exact_vs_mc.csv` | closed-form vs Monte-Carlo check                                                                         |
| `results/e9a_validation_vs_e5c.csv`      | independent design vs the saved E5-c rho                                                                 |
| `scripts/e9a_common.py`                  | data loading and the four null designs                                                                   |
| `scripts/e9a_main.py`                    | tasks 1, 2, 4                                                                                            |
| `scripts/e9a_boot.py`                    | task 3                                                                                                   |
| `scripts/e9a_conf.py`                    | task 5                                                                                                   |
| `scripts/e9a_validate.py`                | validation                                                                                               |
| `scripts/e9a_summary.py`                 | this file                                                                                                |

## 7. Notes and anomalies

**1. One population is under-matched in the joint design.** `medium/ARC` needs `a + b + c = 77` distinct eligible
questions but only 73 have a nonempty pool. Following the E5-c convention (`take = min(m, len(elig))`), all 73 eligible
questions are drawn and the roles are scaled to the same a : b : c shape by largest remainder: a = 27, b = 24, c = 22,
c_same = 13. The flag is carried in `under_matched_joint` in `e9a_ratios.csv` and `e9a_overlap.csv`. Because the null is
given 4 fewer changed questions than the real pair of references, its gain is if anything understated, so the reported
`medium/ARC` joint ratio of 0.845 is a lower bound for that population. No other population is under-matched, and no
population is under-matched in the per-reference or independent designs.

**2. The per-reference C2C ratio exceeds 1 in 4 of 7 populations** (medium/OBQA 1.125, medium/ARC 1.705, large/OBQA
1.313, large/MMLU-Pro 1.246; median 1.125, interval [0.895, 1.349]). A rate-matched random reassignment of the same
number of receiver answers therefore adds more oracle headroom over R than C2C itself does in those populations: the
questions C2C changes are worse than randomly chosen ones for the purpose of covering questions R gets wrong. The
per-reference Text ratios stay below 1 in all 7 (median 0.742). This asymmetry between the two references is the
reason the per-reference design is reported separately rather than averaged.

**3. The joint-matched ratio is larger than the independent one in 5 of 7 populations.** The mechanism is the number of
*distinct* questions each null changes. Two independent rate-matched draws change
`E * (1 - (1 - m_T/E)(1 - m_C/E))` distinct eligible questions in expectation, while the joint design changes exactly
`a + b + c`. Those two numbers are 487.9 vs 470 (small/OBQA), 204.6 vs 205 (small/ARC), 214.9 vs 244 (medium/OBQA),
65.8 vs 73 (medium/ARC), 106.0 vs 115 (large/OBQA), 20.3 vs 23 (large/ARC) and 936.6 vs 1033 (large/MMLU-Pro). The
joint ratio is the larger of the two exactly where `a + b + c` is the larger number, with the single exception of
small/ARC, where the two coverages differ by 0.4 questions and the two ratios differ by 0.001, i.e. by less than the
Monte-Carlo noise. The independent design under-covers because it lets the two null references collide at random,
whereas the real references, despite overlapping more than independence predicts, still spread over more distinct
questions than random collision allows.

**4. The two references overlap more than independence predicts in all 7 populations.** `c / [(a+c)(b+c)/N]` runs from
1.289 (small/ARC) to 6.644 (large/ARC), and is largest in the population where the references change fewest answers
(large/ARC, a + b + c = 23). `c_same`, the both-questions where Text and C2C return the *same* answer, is 44% to 76%
of `c` (44.4% large/MMLU-Pro, 76.5% large/OBQA).

**5. Forced-same cases are common** because the pool is small. `|P(x)| <= 2` by construction, and in every population
most eligible questions have `|P(x)| = 1`, so on a both-question drawn into the "two different answers" role the two
draws are frequently forced to coincide. The mean number of forced cases per draw is reported per population in the
ratios table and ranges from 1.00 (large/ARC, where every such case is forced) to 133.30 (large/MMLU-Pro). This makes
the joint null slightly weaker than a design with a larger pool would be, so the joint ratios are, again, conservative.

**6. The `u <= fit-median` share is not near 0.5 on all development questions in three settings,** because `u` has a
large tie block exactly at the split point: the fit-split median of `u` is 0 for medium/ARC and large/ARC and
1.19e-07 for large/OBQA, and 174, 217 and 26 development questions respectively sit exactly at that value. Since the
share is defined as "at or below", those ties are all counted in, which is why the all-development share reaches 0.582
(medium/ARC) and 0.726 (large/ARC) rather than roughly one half. The tie counts are carried in
`n_dev_u_tied_at_cut` so the share can be recomputed under a strict inequality if the paper prefers that.

**7. The direction of the confidence result is the same in all 14 settings.** The median `u` on the questions a
reference changes is higher than the median `u` over all development questions, and the share at or below the
fit-split median is lower on changed questions than on all questions, in 14 of 14 settings. References change answers
the receiver was *more* confident about, not less. This is descriptive only, as pre-registered, and is not adjusted for
the routing rule, which is not applied here: these are unconditional development-split numbers.

**8. Scope and reproducibility.** No model was run and nothing was queued; this stage reads only saved outputs, and
the GPU lane is untouched. The whole pipeline was re-run end to end from a clean state and all seven result CSVs came
back byte-identical, so every number here is reproducible from the scripts in `scripts/`.

**9. One incidental write into an input folder, since reverted.** An early exploratory run imported `r2_common`
without `sys.dont_write_bytecode` set, which made CPython create
`P2_R2_CPU_20260919T220412Z/scripts/__pycache__/r2_common.cpython-310.pyc`. That directory had not existed before. It
was deleted, and the pipeline was then re-run with `PYTHONDONTWRITEBYTECODE=1`. No source or result file in any input
folder was created, modified or removed at any point: a check for input files newer than this stage's start time
returns nothing, and the pre-existing `P2_R1_CPU_20260919T045556Z/src/__pycache__` (dated 2026-09-19) was left alone.

