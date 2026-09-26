# historical_large_obqa_screen — the earlier large/OBQA/Text screen

The exploratory screen that ran on the large pair, OpenBookQA, receiver-vs-Text, before the
declared certification family. It is included because the Reproducibility statement promises
every calibration test.

Contents: `summary/calibration_100.csv` (the 100 prespecified tests), the frozen configuration
and protocol freezes, the split freeze, receipts and the per-question inputs. **Not** included:
the hidden-state feature dumps (`features/`, 27 MB), the fitted head files (`models/`), the
scheduler evidence and the internal working documents.

## What the 100 tests are

100 = **5 families x 20 fit-quantile grid points**, all on the same large/OBQA split
(fit 2,100 / calibration 1,366 / development 742), alpha = 0.05, p_cutoff = 0.001,
Clopper-Pearson quantile 0.999 — the same rule as the later stages.

| family | score | later use |
|---|---|---|
| `D` | Disagreement head | **reused** in the declared family |
| `R` | Correctness-R head (`1 - p(correct_R)`) | **reused** in the declared family (as `R2100`) |
| `Diff` | Correctness difference (`p(correct_T) - p(correct_R)`) | not reused |
| `H` | Harm head | not reused |
| `Random` | Uniform random control | not reused |

## Relation to the declared 100-test family

The declared family for large/OBQA/Text is in
[`../zero_gold_controls/summary/`](../zero_gold_controls/summary/):

| file | rows | families |
|---|---:|---|
| `calibration_new_60.csv` | 60 | `ProbeMax`, `ProbeEntropy`, `WordD` — 20 each, the new score families |
| `calibration_reused_40_original.csv` | 40 | `D`, `R` — 20 each, carried over from this screen |
| `calibration_comparison_100.csv` | 100 | all five: `D`, `R2100`, `ProbeMax`, `ProbeEntropy`, `WordD` |

Matching the 40 reused rows against this screen's families on `(q, n_R, changed)`:

| declared family | screen family | result |
|---|---|---|
| `D` (20 rows) | `D` | identical on all 20 rows |
| `R` (20 rows) | `R` | identical on all 20 rows |

So the correctness-trained head that was reused is **`R` (Correctness-R)**, not `Diff`, and the
counts are **40 reused + 60 new**. This screen's other three families — `Diff`, `H` and `Random`,
60 tests — are the tests that stayed outside the declared family.

The declared stage's own code records the same thing: it selects the reused rows with
`[r for r in csv.DictReader(OLD/'summary/calibration_100.csv') if r['family'] in ['D','R']]`.

## The full lineage on these 1,366 calibration questions

All three parts are in this release. 460 distinct tests were run on the same 1,366 large/OBQA/Text
calibration questions, against the same answer-change label `d`:

| part | tests | families | where |
|---|---:|---|---|
| the declared family | **100** | 60 new: `ProbeMax`, `ProbeEntropy`, `WordD`; 40 reused: `D`, `R` | [`../zero_gold_controls/summary/calibration_comparison_100.csv`](../zero_gold_controls/summary/calibration_comparison_100.csv) (and `calibration_new_60.csv`, `calibration_reused_40_original.csv`) |
| this screen's other families | **60** | `Diff`, `H`, `Random` | `summary/calibration_100.csv` (the other 60 of its 100 rows) |
| correctness-trained heads under label budgets | **300** | `R32`, `R128`, `R512` x `r0`–`r4` | [`../historical_large_obqa_gold_budget/summary/calibration_new_300.csv`](../historical_large_obqa_gold_budget/summary/calibration_new_300.csv) |

100 + 60 + 300 = 460. The 40 reused `D` and `R` rows are stored twice — once here in this screen's
ledger, where they were first run, and once in the declared family's ledger, which took them over —
so they are counted once in the 460.
