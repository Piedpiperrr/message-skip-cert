# E19 summary (P2_R8_E19_20260921T224942Z)

This stage re-analyzed stored outputs on the ClusterA login node, CPU only. No model weights were loaded and no GPU or PBS job was used; tokenizers were loaded from local files.
Label: POST-HOC re-analysis (E19); it does not change any deployed policy. Deviations are in `DEVIATIONS.md`.

| | |
|---|---|
| Step 0 | `REPRO.md`: 49/49 PASS ((a) 12/12, (b) 8 Qwen + 2 Llama + Text+fact, (c) 10/10), 22:53:19Z–22:54:28Z |
| PREREG | `PREREG_E19.md` SHA-256 `60519cfeb40fd308770a145e87619c1901606a7c746701ffa65a423ca4c85241`, hashed 2026-09-21T22:59:37Z |
| First new computation | 2026-09-21T23:03:55Z (`scripts/e19_1.py`) |
| Scripts | `scripts/e19_common.py` (loaders; E17/E15/E11 modules imported unchanged), `step0_repro.py`, `e19_1.py` … `e19_7.py` |
| Hashes | `MANIFEST.sha256` (every file in this stage except the manifest itself) |

## E19-1 Saving decomposition (`results/E19_1_decomposition.csv`, `E19_1_u0_coverage_change.csv`, `E19_1_writing_rule.csv`)

Sources:
- u = the policy request's logged online `probe.ProbeMax`.
- Route = the logged `selected` field (omitted iff `R`).
- Route mismatches vs 1[u <= tau]: **0 in every row**.
- probe_i = the logged per-request probe stage time. It is available in every replay, so the median fallback was never used.
- Parts are in ms, as (1/N)·sum over the group; question counts in parentheses. Intervals: paired bootstrap, seed 0, 2,000 resamples.

| policy (replay) | u=0 omitted | u>0 omitted | routed | net [95%] | gross share | u>0 / net | recomposed "omit only if u=0" [95%] |
|---|---|---|---|---|---|---|---|
| large OBQA Text (Table 2) | 332.9 (60) | 194.5 (37) | −10.3 (31) | 517.1 [447.8, 583.6] | .369 | .376 | 294.9 [211.5, 372.4] |
| large OBQA C2C (Table 2) | 29.1 (60) | 17.7 (37) | −10.2 (31) | 36.6 [18.0, 56.8] | .378 | .484 | 6.7 [−9.5, 24.8] |
| large ARC Text (Table 2) | 557.3 (93) | 163.1 (27) | −2.8 (8) | 717.6 [670.6, 763.2] | .226 | .227 | 545.6 [476.1, 614.0] |
| large ARC C2C (Table 2) | 94.7 (93) | 20.5 (22) | −4.2 (13) | 110.9 [82.0, 142.8] | .178 | .185 | 83.2 [55.2, 111.0] |
| large MMLU-Pro Text (Table 2) | 204.5 (30) | 144.0 (18) | −2.2 (80) | 346.3 [249.8, 443.0] | .413 | .416 | 196.0 [113.6, 287.0] |
| large MMLU-Pro C2C (Table 2) | 23.2 (30) | 11.6 (18) | −26.6 (80) | 8.2 [−20.5, 44.0] | .334 | 1.413 | −9.8 [−33.7, 17.9] |
| medium OBQA C2C q=.55 (Table 2) | 67.0 (55) | 9.4 (11) | 3.2 (62) | 79.7 [48.1, 129.1] | .123 | .118 | 67.4 [35.6, 115.2] |
| medium ARC C2C (Table 2) | 105.6 (70) | 8.3 (7) | −13.3 (51) | 100.7 [74.5, 133.1] | .073 | .083 | 90.5 [63.5, 123.1] |
| large OBQA Text+fact (2nd config.) | 224.5 (60) | 124.3 (32) | −5.3 (36) | 343.4 [297.7, 386.0] | .356 | .362 | 211.2 [162.0, 258.0] |
| Llama-3.1-8B OBQA Text (2nd config.) | 0.0 (0) | 337.6 (76) | −19.0 (52) | 318.6 [261.1, 372.1] | 1.000 | 1.060 | −37.7 [−48.3, −31.7] |
| Llama-3.1-8B ARC Text (2nd config.) | 0.0 (0) | 427.3 (88) | −8.4 (40) | 418.9 [361.7, 473.7] | 1.000 | 1.020 | −30.8 [−33.4, −27.8] |
| large MMLU-Pro C2C, full 2,641 (2nd config.) | 35.9 (645) | 12.1 (424) | −24.6 (1572) | 23.3 [14.5, 32.2] | .252 | .517 | 4.5 [−2.9, 12.1] |

Coverage and change rates of the u = 0 part and the u > 0 increment are in `E19_1_u0_coverage_change.csv` (dev, held-out and sealed from
E14-2; Llama from E17-1 and E16). For example, dev large OBQA Text: u = 0 part covers 354/742 of dev with 2/354 changes, and the u > 0
increment covers 218/742 with 17/218 changes.

**Writing rule:**
- 8 of the 9 Qwen-receiver policies have a net-saving interval that excludes 0.
- Across those 8, the gross share ranges from **7.3% (medium ARC C2C) to 41.3% (large MMLU-Pro Text)**.
- No policy reaches 50%, so the main text names no policy.
- Reported separately: large MMLU-Pro C2C, whose interval includes 0 (gross share 33.4%).

## E19-2 INVALID among certified changes (`results/E19_2_invalid_changes.csv`, `E19_2_writing_rule.csv`)

Every n and k equals its stored count (E9B_RESULTS.json, primary_sealed.csv, OOS_PRE_GOLD.json; see `E19_2_checks.csv`). Rows with any
exactly-one-INVALID change:

| policy | split | k | both parse | only R INVALID | only ref INVALID |
|---|---|---|---|---|---|
| large MMLU-Pro Text | dev | 40 | 38 | 1 | 1 |
| large MMLU-Pro C2C | dev | 37 | 34 | 1 | 2 |
| medium OBQA C2C q=.55 | dev / held-out / pooled OOS | 11 / 8 / 8 | 9 / 6 / 6 | 0 | 2 / 2 / 2 |
| medium OBQA C2C q=.50 | dev / held-out | 7 / 6 | 5 / 4 | 0 | 2 / 2 |
| **medium ARC C2C** | **dev** / E16-2 ARC test = pooled OOS | **4** / 15 | **2** / 8 | 0 | **2** / 7 |
| large OBQA Text | held-out = pooled OOS | 12 | 11 | 1 | 0 |
| large OBQA C2C | held-out = pooled OOS | 13 | 11 | 0 | 2 |

Every other policy × split has 0 INVALID-involving changes. That covers large OBQA Text/C2C (dev), large ARC Text/C2C (dev and sealed),
Text+fact (dev and held-out), and Llama OBQA/ARC (dev and E16-1).

**Writing rule triggered:** medium ARC C2C on dev has exactly-one-INVALID share 2/4 = 50%; both are C2C-reference INVALID. The main text
names it next to the C2C redundancy sentence. On pooled out-of-sample data the same policy has 7/15 = 46.7%. The range over the 11
deployed policies (dev and pooled out-of-sample) is 0%–50%.

## E19-3 Panel representativeness (`results/E19_3_panel_vs_full.csv`, `E19_3_eq4.csv`, `E19_3_latency_full_mmlu_c2c.csv`)

| policy | coverage panel vs full (pts) | max \|SMD\| (length vars) | u=0 share panel vs full | Eq. 4 (i) panel κ vs (ii) full κ (ms) |
|---|---|---|---|---|
| large OBQA Text | .758 vs .771 (−1.3) | .136 helper msg | .469 vs .477 | 517.2 vs 527.1 |
| large OBQA C2C | .758 vs .771 (−1.3) | .115 ref output | .469 vs .477 | 36.6 vs 38.0 |
| large ARC Text | .938 vs .950 (−1.2) | .053 question | .727 vs .726 | 717.8 vs 727.8 |
| large ARC C2C | .898 vs .903 (−0.5) | .057 ref output | .727 vs .726 | 110.9 vs 111.7 |
| large MMLU-Pro Text | .375 vs .405 (−3.0) | **.212 R output** | .234 vs .244 | 317.0 vs 346.0 |
| large MMLU-Pro C2C | .375 vs .405 (−3.0) | **.212 R output** | .234 vs .244 | 5.6 vs 9.7 |
| medium OBQA C2C q=.55 | .516 vs .526 (−1.0) | .107 R output | .430 vs .433 | 56.8 vs 58.6 |
| medium ARC C2C | .602 vs .632 (−3.1) | .053 question | .547 vs .582 | 100.6 vs 107.4 |
| large OBQA Text+fact | .719 vs .722 (−0.4) | .123 helper msg | .469 vs .477 | 339.5 vs 341.4 |
| Llama OBQA Text | .594 vs .590 (+0.3) | .136 helper msg | 0 vs 0 | 322.4 vs 320.3 |
| Llama ARC Text | .688 vs .689 (−0.1) | .069 R output | 0 vs 0 | 417.2 vs 418.2 |

- Latency comparison: only one run qualifies, the full 2,641-question MMLU-Pro C2C replay.
  - The 128 panel rows inside it: mean fixed 287.5 ms, mean policy 283.0 ms, mean saving 4.5 ms, median −35.9 ms.
  - All 2,641 rows: mean saving 23.3 ms, median −37.3 ms.
  - Saving SMD −0.08.
  - Every other policy: lengths only.
- **Writing rule triggered.** Large MMLU-Pro Text and C2C have receiver-only output-length SMD +0.212 (mean 5.70 vs 5.54 tokens; medians
  6 vs 6). The appendix names them and Sec. 4.4 adds a caveat. No coverage difference exceeds 10 points (max 3.1).

## E19-4 Prospective prediction (`results/E19_4_prospective.csv`, `E19_4_summary.csv`, `E19_4_checks.csv`)

The frozen `e15_1.py` (SHA-256 d6bfc055…ab485) was re-run with the same harness on E15's 25 settings and reproduces E15's four stored
CSVs exactly. The E15 PREREG was hashed at 07:23:54Z; the E17 PREREG at 18:31:26Z.

| setting | actual | E15-1 predicted | q steps | coverage error | first output | prospective |
|---|---|---|---|---|---|---|
| Llama OBQA Text | deploy .60 | deploy .65 | +1 | .060 | 06:42:22Z (X3 smoke) | no |
| Llama ARC Text | deploy .70 | deploy .65 | −1 | .038 | 06:42:22Z | no |
| strong-helper OBQA Text (E16-5) | fallback | fallback | – | – | 18:58:58Z | yes |
| strong-helper ARC Text (E16-5) | fallback | fallback | – | – | 18:58:58Z | yes |
| Text+fact, GSM8K | – | N/A (no fit reference outputs) | | | | N/A |

- **Sec. 5, E15-1: 2 of 2 prospective predictions correct** (E16-5 OBQA and ARC). Reported separately: 2 of 2 non-prospective (Llama).
- **E17-5 binormal: 2 of 2 prospective predictions correct**: E16-5 P(certify) .040 and .0485, predicted fallback, observed fallback.
- Llama saving model: predicted −32.2 / −36.7 ms vs measured 318.6 / 418.9 ms. The X3 component latencies exclude helper generation (X3
  reused stored helper messages; `run_x3.py` times only the receiver), so this saving error is not meaningful (reported as an anomaly).

## E19-5 Pass criteria (`results/E19_5_quotes.csv`, `E19_5_ten_tests.csv`, `E19_5_protocol_line_scan.csv`)

Each protocol's SHA-256 matches its stored hash.
- **E9b** (`P2_R3_E9BC.../PROTOCOL_FREEZE_E9B.md`, d211e4ad…bbe, 2026-09-20T06:21:01Z): "Statistics per policy: omitted n, changed k,
  conditional change rate with a two-sided Clopper-Pearson 95% interval, and the exact binomial p-value of the single prespecified test
  H0: rho >= .05 at the frozen threshold; …"
  - Neither the freeze nor the amendment (bd951a3f…506, 06:44:34Z) contains a sentence defining "pass".
  - There is no separate p <= .001 sentence for large OBQA Text. The amendment's only "p<=.001" (line 83) names the calibration design
    artifact searched by check C2.
- **Sealed ARC** (`USER_PROMPT_ZH.md`, 4dcdff63…05fa93b8, frozen 2026-09-14T21:31:36Z, §9):
  - Verbatim: "本轮不重新做 calibration，也不在 test 上“通过/拒绝”新 threshold。 … `conditional answer-change ≤ 5%` … 冻结 policy 的
    empirical conditional answer-change 是否仍处于预先指定的5%风险目标附近/以内？ … 可以提供预先指定的描述性 binomial interval…".
  - In English: no pass/reject; the question is whether the change rate stays near or within the 5% target; a descriptive interval is allowed.
- **E16** (`PREREG.md`, 17ca4713…c02a, 18:44:07Z): "CP upper < 5% -> '… passes an out-of-sample test …'; CP lower > 5% -> 'fails …';
  otherwise -> 'inconclusive …'. Also state whether p <= .001 and p <= .025."

| test | n | k | p | CP upper | p ≤ .001 | CP up < 5% | own criterion |
|---|---|---|---|---|---|---|---|
| held-out large OBQA Text | 595 | 12 | 1.47e-4 | .0350 | yes | yes | none stated |
| held-out large OBQA C2C | 595 | 13 | 3.65e-4 | .0371 | yes | yes | none stated |
| held-out medium OBQA C2C q=.55 | 388 | 8 | 2.52e-3 | .0402 | **no** | yes | none stated |
| held-out medium OBQA C2C q=.50 | 346 | 6 | 1.38e-3 | .0374 | **no** | yes | none stated |
| held-out Text+fact | 558 | 16 | 9.20e-3 | .0461 | **no** | yes | none stated |
| sealed ARC Text | 1100 | 20 | 2.95e-8 | .0279 | yes | yes | no pass/reject (1.82% ≤ 5%) |
| sealed ARC C2C | 1047 | 11 | 2.0e-12 | .0187 | yes | yes | no pass/reject (1.05% ≤ 5%) |
| E16-1 Llama OBQA (744) | 440 | 3 | 3.71e-7 | .0198 | yes | yes | CP upper < 5%: pass |
| E16-1 Llama ARC (1,172) | 794 | 15 | 4.40e-6 | .0310 | yes | yes | CP upper < 5%: pass |
| E16-2 medium ARC C2C (1,172) | 733 | 15 | 3.13e-5 | .0335 | yes | yes | CP upper < 5%: pass |

**Writing rule.** The condition is met: E9b states no pass criterion, and the sealed protocol says there is no pass/reject; both are "other
than CP upper < 5%". No test fails its own protocol's criterion. Sec. 4.5 states each criterion as quoted. The abstract's out-of-sample
sentence must be amended so that it does not present "CP upper < 5%" as the prespecified criterion of the seven E9b/sealed tests. All 10
have CP upper < 5%; 7/10 have p ≤ .001.

## E19-6 Prompts (`PROMPTS_FOR_APPENDIX.md`, 1,052 lines; `results/E19_6_*.csv`)

- 25/25 checks PASS. The E13 file's templates, renderings and parser rules match the frozen code; parser V2 SHA-256 d05978f4…c2f9.
  Code hashes are in `E19_6_code_hashes.csv`.
- Added templates:
  - the general K-label receiver template (MMLU-Pro A–J);
  - the helper instruction and helper body;
  - the Text+fact line (already in E13; re-verified);
  - the E9c helper-aware prefill (rendered with Qwen2.5-7B);
  - GSM8K (E10) helper, receiver and three-turn prompts.
- Rendered examples: helper Text prompt (Qwen2.5-7B), and receiver-only / receiver-with-message / probe for each of Qwen3-8B, Llama-3.1-8B
  and OLMo-2. Token counts equal the saved records (132/258/136; 155/281/159; 132/260/136). The Llama and OLMo rendered sha256 equal the
  saved probe `rendered_sha256`.
- Anonymity scan: no match.

## E19-7 Other receivers (`results/E19_7_*.csv`)

**None.**
- There is no Mistral or Granite model output anywhere in the project.
  - Mistral-7B-Instruct-v0.3: download manifest/log and X3 Step 0 tokenizer/template checks.
  - Granite-3.1-8B-Instruct: config/tokenizer files only (no weights) and X3 Step 0 checks.
  - X3 `DEVIATIONS.md` says neither was used.
- `receiver` field values in all records: Qwen3-0.6B/1.7B/8B, `olmo2_7b`, `llama31_8b`, plus `llama`/`qwen3` in the concurrent E20P
  stage's `notes/dryrun/` records. Its README marks those as FAKE; E20P's real receivers are Qwen3-8B and Llama-3.1-8B.
- Appendix N: no other receiver produced outputs.
