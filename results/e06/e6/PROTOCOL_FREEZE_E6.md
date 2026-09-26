# PROTOCOL FREEZE — E6 "Text+fact" (large pair, OpenBookQA)

Frozen 2026-09-19 on the ClusterA login node, before any E6 model output existed.
Work directory: `P2_R2_GPU_20260919T220941Z/e6/`. Paper A (reference-preserving communication omission).

This file is frozen. Any later change is a deviation, recorded in `e6/DEVIATIONS.md` with a UTC
timestamp **before** any calibration or development result of E6 is read.

## 1. Setting under test: "Text+fact"

Large pair, OpenBookQA: helper `Qwen2.5-7B-Instruct` (cuda:0) → receiver `Qwen3-8B` (cuda:1).

Text+fact is the frozen large-pair **Text** action with exactly one change: the helper's user message
gets one extra line

```text
Useful fact: <fact1>
```

inserted **immediately before the question text**, i.e. as the first line of the question block that
`arc_protocol.helper_body()` passes to `protocol_min.build_prompt(..., use_template=False)`. The
inserted line is terminated by a single `\n` and `<fact1>` is the `fact1` string of
`allenai/openbookqa`, config `additional`, verbatim and unmodified.

Everything else is byte-identical to the frozen large-pair Text action:

- helper prompt wrapper `BACKGROUND_PROMPT` ("In one clear sentence, describe the most essential
  background knowledge needed to answer the question:\n\n{question}\n\nDo NOT directly solve or give
  answer to the question."), unchanged;
- receiver prompt reading the helper message: unchanged
  (`legacy_methods.T2TReceiverBundle.consume`, receiver user message = frozen `receiver_prompt()`);
- chat templates of both models, `enable_thinking=False`, `add_generation_prompt=True`, unchanged;
- greedy decoding (`do_sample=False`), bf16, `attn_implementation='sdpa'`, TF32 off, batch size 1;
- 256 helper `max_new_tokens`, 64 receiver `max_new_tokens`;
- answer parsing by frozen parser V2 (`P2_SCORING_V2_20260912T191445Z/scoring_v2.py`,
  SHA-256 `d05978f400cf69aa6bddc56168a260ac3ea9158abaa640e9331602dc9bfcc2f9`).

### 1.0 Who sees the fact

`fact1` is an input to the **helper only**. The frozen receiver conversation built by
`legacy_methods.T2TReceiverBundle.consume` has three turns: (i) a user turn that repeats the helper's
question block, (ii) the helper's message, (iii) the receiver's own question. Turn (i) is built with
the **original, fact-free** question block, so the receiver's prompt is byte-identical to the frozen
Text receiver prompt and the fact can reach the receiver only through the helper's generated message.
This keeps E6 a test of the helper's message, not a test of handing the receiver a gold-adjacent fact.
The receiver-prompt path (`use_template=True`) is never touched by the flag; this is checked on the
login node before any run (checked 2026-09-19: receiver prompt identical with the flag on).

Implementation rule: the fact line is added by a **new flag** on the helper prompt builder, default
**off**. With the flag off the rendered helper prompt is byte-identical to the frozen Text prompt;
this is verified on 5 fit rows before any run (verified 2026-09-19, result recorded in
`e6/E6_PROMPT_EXAMPLES.json`, field `flag_off_is_byte_identical_on_5_fit_rows`).

### 1.1 Dataset

- `allenai/openbookqa`, config `additional`, revision `388097ea7776314e93a529163e0fea805b8a6454`,
  local copy `$DATA_DIR/c2c_reproduction_assets/datasets/allenai--openbookqa/additional/`.
- `train-00000-of-00001.parquet` SHA-256 `d16d719e87efb86ed0a2ac4c8cdf380f7bfb94b602088393674c0a64ce9ed3d3`.
- Coverage verified 2026-09-19 before the freeze (`e6/E6_COVERAGE.json`): `fact1` present and
  non-empty for **1366/1366** calibration, **742/742** development and **16/16** first fit questions;
  `question_stem` of the local `additional` rows equals the frozen query text on every one of these
  rows (0 mismatches).

## 2. Fully rendered example helper prompts

#### Example 14-1371 (OBQA fit question, frozen fit order)

`fact1` = `metal is a nonrenewable resource`

Frozen Text helper user message (unchanged, SHA-256 `51cbf1c18ff59ead6a80902f0dcf59e88d47c7eee9a0de8e77dcdab855b124cd`):

```text
In one clear sentence, describe the most essential background knowledge needed to answer the question:

Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Do NOT directly solve or give answer to the question.
```

Text+fact helper user message (SHA-256 `d1cfa3a07e496b1f53b04d111e69e0a9338df92b82617461b98e814f9964d7b4`):

```text
In one clear sentence, describe the most essential background knowledge needed to answer the question:

Useful fact: metal is a nonrenewable resource
Which relationship is true?

Choices:
A. wind is renewable; metal is nonrenewable
B. wind is recyclable, metal is other
C. wind is happy, metal is other
D. wind is nonrenewable; metal is renewable


Do NOT directly solve or give answer to the question.
```

#### Example 14-97 (OBQA fit question, frozen fit order)

`fact1` = `seed dispersal is when the seeds of a plant are moved from the plant to a new environment`

Frozen Text helper user message (unchanged, SHA-256 `6df5c4ef37121b1c3e80d61c39d89a1983d2ad8b467f19f560dc906fd3f7eed6`):

```text
In one clear sentence, describe the most essential background knowledge needed to answer the question:

If the source of a bean is very far away, and the bean becomes a source for another, separate bean, then the original bean was

Choices:
A. a bad seed
B. a dispersed seed
C. a fresh shell
D. a meaty liver


Do NOT directly solve or give answer to the question.
```

Text+fact helper user message (SHA-256 `94fb3a9132a98ffd6cf3a13ef402e1a52e2d3b6f9f82790185c9d7aafafe1de2`):

```text
In one clear sentence, describe the most essential background knowledge needed to answer the question:

Useful fact: seed dispersal is when the seeds of a plant are moved from the plant to a new environment
If the source of a bean is very far away, and the bean becomes a source for another, separate bean, then the original bean was

Choices:
A. a bad seed
B. a dispersed seed
C. a fresh shell
D. a meaty liver


Do NOT directly solve or give answer to the question.
```
## 3. Reuse without recomputation

The following are **read, never recomputed**. Before use, the SHA-256 of each source file is verified,
and the per-row input identity is verified on **every used row** (not a sample): for each row the
`probe_ids_sha256` of the reused ProbeMax record must equal the hash recomputed from the frozen query,
and the reused answer record must carry the same `id` and `legal_labels` as the frozen query.

| Reused artefact | Path | SHA-256 |
|---|---|---|
| Receiver-only (R) answers, fit+cal | `P2_SCORING_V2_20260912T191445Z/labels/full_train_P2_SCORING_V2.jsonl` | `a26986635c944974a5263e08457cb181489a32aec84da450fd514f9155dbf911` |
| Receiver-only (R) answers, dev | `P2_SCORING_V2_20260912T191445Z/labels/full_development_P2_SCORING_V2.jsonl` | `6fde2e0a58f9be88ef14edf7aeab0ac7202b594a17b94d1d18f034f8984d9aa8` |
| ProbeMax scores + label distributions (all 4208 OBQA rows) | `P2_ZERO_GOLD_CONTROLS_20260914T065145Z/records/probe_records.jsonl` | `2ecc6bd323be2868415042ff346c1d500ff98b796c25ea0f73ad755d234f1a7b` |
| Frozen fit-quantile thresholds (large/OBQA) | `P2_CONFIDENCE_REFERENCE_BOUNDARIES_20260914T165012Z/thresholds/large_obqa.json` | `e874e2d8aeb5d10450d4110725e09b5652a5c4d53e874739d16fd526ce735268` |
| Calibration representatives (1366) | `.../splits/obqa_cal_representatives.json` | `8b33a4d168131c5a0095c5eabcdea2f2b3bb272dfae8a41ab2a7e0e05d5ebaed` |
| Development representatives (742) | `.../splits/obqa_dev_representatives.json` | `80d1bbdd9148df3037401881533a2137b0d4ce9ee90a8ebb424fb413440bfbab` |
| Fit representatives (2100) | `.../splits/obqa_fit_representatives.json` | `1559bc9668d88a986df0967b96fdf14c995f02f622b126f396819b69b58c4028` |
| Frozen queries, train (fit+cal) | `.../inputs/obqa_train_queries.jsonl` | `56a89982c5fbf8fc08edc322d08a11eaba5ef05ac3b0dfeb662ddb96477ea767` |
| Frozen queries, dev | `.../inputs/obqa_dev_queries.jsonl` | `23c6a8039b63d176a63c820114a20def2ce6a785d8b8cd86a3b510ed68928094` |
| Frozen 128-question OBQA panel | `P2_R1_E3POL_REPEAT1_20260919T075315Z/large/inputs/obqa_queries.jsonl` | `cbaee992cee5b5b956d2ae439fd3ce730dc90e73ad8e1b04cda407fabc04ce14` |
| Frozen panel ids | `.../large/inputs/obqa_panel_ids.json` | `6ebbd7604ce342d43219288b4235053026449b1d9684cff73044be356b3263ac` |
| Parser V2 | `P2_SCORING_V2_20260912T191445Z/scoring_v2.py` | `d05978f400cf69aa6bddc56168a260ac3ea9158abaa640e9331602dc9bfcc2f9` |

**Newly computed by E6:** only the Text+fact helper message and the receiver answer that reads it, for
the 1366 calibration and 742 development rows (2108 rows), plus the 16 smoke rows. No new R output, no
new probe, no new threshold.

## 4. Splits, test family and deployment rule

- Calibration: the frozen OBQA calibration split, **1366** group representatives.
- Development: the frozen OBQA development split, **742** group representatives.
- The 20 candidate thresholds are the **frozen** fit quantiles of ProbeMax over the 2100 fit
  representatives (rank `ceil(j*N_fit/20)`, `j=1..19`; `j=20` is `Infinity`), read from
  `thresholds/large_obqa.json`. They are **not** refitted.
- Test family: a **separate** family of 20 tests for the single stratum large/OBQA/Text+fact.
  It is not merged with, and does not reuse, any earlier family.
- `alpha = .05`; per-candidate acceptance `p <= .001`; `p` is the one-sided binomial CDF
  `binom.cdf(k, n, .05)` where `n` is the number of calibration questions with `ProbeMax <= t` and
  `k` the number of those on which the receiver-only answer differs from the Text+fact answer.
  The Clopper–Pearson `.999` upper bound on the conditional change rate is reported as a diagnostic.
- Deployment: the **largest** accepted `q`; if no candidate is accepted, fall back to the fixed
  reference (`q = 0`, no omission).
- Labels: the calibration disagreement vector is `1[o_R != o_{Text+fact}]`. Gold is **not** read at
  any point of calibration or deployment selection.

## 5. Reporting — whatever the outcome

Reported regardless of whether Text+fact is deployable or falls back:

1. calibration and development disagreement rate between R and Text+fact (count and rate);
2. AUROC of ProbeMax as a ranking of those disagreements, on calibration and on development;
3. the certified `q` (0 if fallback) and the 20-row test ledger;
4. development coverage at the deployed `q`, and changed/omitted on development;
5. accuracy of R, of the frozen Text, and of Text+fact on calibration and development;
6. INVALID rates of R, Text and Text+fact (parser V2), reported separately from runtime failures;
7. corrective and harmful change counts of Text+fact relative to R (omitted questions only, and over
   the whole split), counted with gold **after** all E6 outputs are complete.

A fallback outcome is a result and is reported in the same detail as a deployable one.

## 6. End-to-end replay (conditional)

If, and only if, the certified `q > 0`: one end-to-end replay on the **frozen 128-question OBQA
panel** on this hardware (ClusterA, 2 A100-40GB of one node, helper cuda:0, receiver cuda:1), two arms —
**fixed Text+fact** and **Text+fact policy** — with the same protocol as E3: arm rotation by question
ordinal, no warm-up, cold requests kept, one outer synchronised timer per request, batch size 1, zero
retries, and analysis versions (a) all requests and (b) cold questions excluded, with 2000 seed-0
paired bootstrap resamples. The replay is **classification only** (above zero / crosses zero / below
zero); no cross-hardware comparison is made. If `q = 0`, there is **no replay**.

## 7. Smoke test (before the main run)

16 fit questions, in frozen fit order, Text+fact only. **No gold is read.** Checks:

- every one of the 16 produces a helper message and a receiver answer without a runtime error;
- parser V2 INVALID count over the 16 receiver answers is `<= 2`.

Stop conditions: more than 2 of 16 INVALID, or any runtime error. On a stop, nothing else is
submitted and the failure is reported.

## 8. Resources

ClusterA `debug`, account `project`, `-l fsreq=<fs>`. Main run: 2 nodes,
4 GPU pairs, 2108 rows split into 4 shards of 527 rows, walltime `00:50:00`. Estimated GPU time from
the frozen Text action: ~0.80 s/row measured on ClusterA (large/OBQA Text reference arm, job 7635399),
~1.00 s/row measured on the historical full-population run, i.e. ~28–35 min for 2108 rows on one GPU
pair and ~7–9 min per shard plus ~1.5–2 min model load.
