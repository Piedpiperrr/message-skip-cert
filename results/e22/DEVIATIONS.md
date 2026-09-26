# E22 DEVIATIONS

Choices made after an E22 statistic existed (PREREG R6). Each is disclosed in the appendix.

## D1 — 2026-09-22T19:56Z — E22-1 stopped by the preregistered identity check, and what was done next

The preregistered check "mean null gain == min(n_-, elig_-) * g_- within 3 Monte Carlo standard errors" **failed on
one of the fourteen cells**: medium/ARC, C2C, where the mean null gain over the 1,000 preregistered draws is 14.7530
against an expectation of 14.5854, a deviation of **+3.277 MC standard errors** (MC SE 0.0512). The other thirteen
cells pass (largest other deviation 1.571 SE). Per the PREREG, **E22-1 is STOPPED and reported**; no E22-1 number is
released for the paper until the authors decide.

Diagnostic run after the failure (`logs/e22_1_mc_diagnostic.log`), which is why it is recorded here:

* The expectation is exact and the sampler is E9-a's own `Inst.per_reference`, used unchanged.
* Running the identical design on that cell under 400 different seeds gives a mean deviation of **-0.026 SE**
  (sd 0.926) and a grand mean gain of 14.5840 against the expectation 14.5854, so the sampler is unbiased.
* Exactly **1 of those 400 seeds** exceeds 3 SE, and it is seed 0 itself: the preregistered seed (E9-a's stored seed)
  happens to be the most extreme of the 400 tried. With 14 cells the chance that at least one exceeds 3 SE is ~1.5%.
* At 200,000 draws the same cell reproduces the expectation to within 0.03-1.55 SE for every seed tried, seed 0
  included (+0.763 SE).

The evidence is that the failure is a Monte Carlo fluctuation of the preregistered draw, not a bias in the design or
an error in the code. The PREREG gives no rule for reinstating a stopped item, so the decision is the authors'
(see NEEDS FROM US in the report).

## D2 — 2026-09-22T19:57Z — the E22-1 bootstrap and summary quantities were computed although the item is stopped

To let the authors decide in one round trip before the R5 deadline (2026-09-23 18:00 CDT), the E22-1 bootstrap
intervals and the summary quantities M, K, T_sig and C_sig were computed anyway, exactly as preregistered. They are
labelled throughout as belonging to a **stopped** item and must not be used in the paper unless the authors lift the
stop. Nothing about the design, the seed or the draws was changed. E22-2 is unaffected: it is complete, and its
preregistered reproduction gate (large/OBQA Text 46/18, C2C 16/35, V1 48/66) passes.

## D3 — 2026-09-22T20:48:54Z — the authors lifted the E22-1 stop

The preregistered Monte Carlo identity check flagged medium/ARC C2C at +3.28 SE (threshold 3 SE; the other 13 cells
<= 1.57 SE). A diagnostic over 400 seeds of the identical design gave a mean deviation of -0.026 SE and a grand mean
gain of 14.5840 against the expectation 14.5854; seed 0, E9a's stored seed, is the most extreme of the 400, and at
200,000 draws it gives +0.76 SE. With 14 cells, a 3-SE two-sided check raises a false alarm with probability about
3.7%. The authors lifted the stop after seeing all E22-1 numbers; the reported numbers are the preregistered ones,
unchanged.

Consequences recorded at the same time:

* **Ranges and medians** stay as preregistered: over all seven populations for Text, with large/ARC Text flagged as
  undetermined (its ratio 0.900 is a lower bound; the appendix scaled ratio * n_-/elig_- is 0.990). M, K, T_sig and
  C_sig exclude it, as preregistered.
* E22-1 is now a completed item under PREREG R5 (manifest last output 2026-09-22T19:57:40Z, before the
  2026-09-23 18:00 CDT deadline), so its numbers may be used in the paper.

## D4 — 2026-09-22T20:48:54Z — descriptive quantity added at the authors' request

`results/E22_2_share_minus_g.csv`: the wrong->right share minus g_- in percentage points, one decimal, for every
population and every action, computed by subtraction from the stored `results/E22_2_directions.csv` values (no
recomputation of any statistic). Descriptive only; it adds no new design and changes no E22 number.
