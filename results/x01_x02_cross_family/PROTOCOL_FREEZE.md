# P2_R1_XFAM — X2 protocol freeze (post-hoc cross-family breadth extension)

Frozen before any OLMo output exists (including the smoke test). After freezing, this file is read-only and is not changed after seeing any output; any unavoidable change goes in DEVIATIONS.md. The hashes of this file's inputs are listed at the end. Pre-registration: the requester's "Chat A" specification (2026-09-19), reproduced below.

## 1. Setting X2

- **Receiver:** allenai/OLMo-2-1124-7B-Instruct @ 470b1fba1ae01581f270116362ee4aa1b97f4c84, local snapshot `$DATA_ROOT/hf_cache/hub/models--allenai--OLMo-2-1124-7B-Instruct/snapshots/470b1fba…` (file SHA-256 in `manifests/DOWNLOAD_MANIFEST.json`).
- **Helper:** Qwen/Qwen2.5-7B-Instruct @ a09a35458c702b33eeacc393d103063234e8bc28 (the paper's large-pair helper). It is not run. Its saved Text messages from the paper's large-pair development records are reused:
  - OBQA/ARC: `P2_SCORING_V2` labels `source_T` → `P2_6…/results/{train,dev}_cases.jsonl`, `P2_9…/results/large/{train,validation}_cases.jsonl`.
  - MMLU-Pro: `P2_MMLU_PRO_BREADTH_STAGE1…/shards/*/actions/{fit,cal,dev}.jsonl`, action T.
  - Source-file hashes are in `records/populations/POPULATION_MANIFEST.json`.
  - Check (`notes/A3_checks.json`): for every row, the rebuilt helper input has the saved token count, and the saved message decodes from the saved token IDs (OBQA 4,208/4,208, ARC 1,418/1,418, MMLU-Pro 11,641/11,641). The helper input does not depend on the receiver.
- **Reference:** Text only. Actions: R (receiver-only) and Text.
- **Populations:** gold-free files in `records/populations/`, same splits and IDs as the paper.

  | benchmark | fit | cal | dev | source |
  |---|---|---|---|---|
  | OBQA | 2,100 | 1,366 | 742 | P2_CONFIDENCE_REFERENCE_BOUNDARIES `splits/obqa_*_ids.json` = representatives |
  | ARC | 671 rows (670 representatives) | 448 | 299 | 1,418 rows, grouped as in the paper: `splits/arc_*_ids.json` and `arc_*_representatives.json` |
  | MMLU-Pro | 3,000 | 6,000 | 2,641 | normalized-question group representatives from stage-1 `splits/{fit,cal,dev}_groups.json` |

  Certification and development units are the representatives. Every row, including the one ARC non-representative, is run.

## 2. Prompts

- **Message lists:** exactly the paper's receiver message lists (roles and contents), rendered with OLMo's own chat template (chat_template SHA-256 below). Receiver prompt formatters:
  - OBQA: P2_10 `protocol_min.format_openbook`;
  - ARC: P2_10 `arc_runtime_adapter` (P2-8 v2);
  - MMLU-Pro: stage-1 `native_runtime.format_mmlu`.
- **R:** `[user: receiver prompt]` with the generation prompt.
- **Text-reading:** `[user: BACKGROUND_PROMPT(helper body), assistant: saved helper message, user: receiver prompt]` with the generation prompt, as in the paper's `T2TReceiverBundle.consume`.
- **No system prompt:** the paper's receiver prompts have none, and OLMo's rendering adds none (`notes/freeze_inputs.json`).
- **No thinking flag:** the paper code passes `enable_thinking=False`, which OLMo's template ignores; the rendered text is identical with and without it.
- **ProbeMax input (approved change A1):** `apply_chat_template([user: receiver prompt], add_generation_prompt=True)` with OLMo's tokenizer, then the unchanged prefix IDs of "The correct answer is" (`add_special_tokens=False`).
- **Label tokens:** every non-special token whose stand-alone decoded string, stripped, equals the displayed label. For OLMo, A–J each have 3 tokens, non-empty and disjoint (`notes/A3_checks.json`).
- **Score:** FP32 label logsumexp, softmax over the item's K displayed labels, u = 1 − max p. This is the paper's rule and is unchanged.

## 3. Decoding

- Greedy (`do_sample=False`), bf16, SDPA, batch 1, TF32 off, seed 0. Receiver `max_new_tokens=64`, applied with the paper's `apply_generation_config`.
- EOS and pad come from the checkpoint's generation config: eos_token_id 100257, pad_token_id 100277. The full resulting generation config is in `notes/freeze_inputs.json`.
- One independent request per (question, action). No retries; a failed request is recorded and counts as INVALID. The probe is one independent full prefill (`use_cache=False`).
- **Driver (approved change A2):** `src/run_x2.py` loads the receiver only, then runs:
  - R via the paper's `runtime.Runner.request(q, 'receiver_only')`;
  - Text-reading via `T2TReceiverBundle.consume(q, format(q, use_template=False), saved message)`;
  - then the probe.
- **Validation required before any OLMo output:** the driver, with receiver Qwen3-8B, must reproduce bit for bit the saved large-pair probe inputs, ProbeMax scores and label probabilities, R raw outputs and Text raw outputs on 16 fit questions (8 OBQA, 8 ARC). The same comparison is also run on 4 MMLU-Pro fit questions. Any difference stops the work.

## 4. Parser

Frozen P2_SCORING_V2 `parse_answer(raw, legal labels)` (SHA-256 d05978f4…), unchanged. INVALID is its own label: it counts as wrong for accuracy, and as an ordinary symbol when comparing R with Text.

## 5. Certification (per setting: OBQA/Text, ARC/Text, MMLU-Pro/Text)

- **Candidate thresholds:** 20 candidates from fit-split ProbeMax order statistics. t_j = sorted_fit[ceil(j·N_fit/20) − 1] for j = 1..19 (q = .05…95); q = 1 routes every question to R. A question routes to R iff u ≤ t_j, so ties route to R.
- **Calibration test:** on the cal split, n = number routed to R and k = number routed with o_R ≠ o_Text. p = P[Bin(n, .05) ≤ k] (exact binomial, α = .05). A candidate is accepted if p ≤ .001. UCB = Clopper–Pearson .999 upper bound of k/n.
- **Deployment:** the largest accepted q; if none is accepted, fall back to fixed Text (q = 0).
- **Test family:** these 60 tests (3 settings × 20) form a separate family from the paper's 280.

## 6. Development metrics (per setting, dev representatives)

- **Table 5 columns:**
  - Dis./N: o_R ≠ o_Text.
  - ProbeMax AUROC for ranking those disagreements.
  - Min UCB over the 20 calibration candidates.
  - q.
  - Coverage (% routed to R, i.e., communication omitted).
  - Changed/omitted: routed questions with o_R ≠ o_Text; N/A when nothing is routed.
  - Correct policy / reference: the policy answer is o_R if routed, else o_Text; the fixed reference is o_Text.
- **Also:** R and Text accuracy, and R and Text INVALID rates, per split (fit/cal/dev representatives).
- **Order:**
  1. All outputs are written and hashed.
  2. Scores, thresholds, certification and routes are computed, written and hashed, without gold.
  3. Only then is gold read: OBQA/ARC from the `gold` field of the P2_SCORING_V2 labels; MMLU-Pro from the paper's MMLU-Pro test parquet `answer`.

## 7. Commitment

All three settings are reported whatever the outcome. End-to-end replay happens only for settings that deploy, decided later under a separate rule.

## 8. Execution (harness; not protocol content)

- Job 1: ClusterA debug, 1 node. Validation (Qwen3-8B, `records/work/validate_rows.jsonl`), then, only on PASS, the OLMo smoke test on 16 fit questions (`records/work/smoke_rows.jsonl`: 6 OBQA, 6 ARC, 4 MMLU-Pro). Gold is not read.
- Smoke stop rule: any runtime error, or more than 2 of 16 INVALID for R or for Text.
- Full runs: single-GPU chains, each ≤ 50 min including load. Shards are sized from the smoke latencies; the plan is recorded in DEVIATIONS.md/README before submission. The driver stops cleanly at a deadline and keeps its outputs.

## 9. Hashes (appended by `src/freeze_hashes.py`)

| item | SHA-256 |
|---|---|
| `src/xfam_common.py` | 6150428bfbc4cb58d5fc718abbf610437038726342ae20747cc119f9c9dc4b12 |
| `src/prepare_populations.py` | f6087f485efc36d2ec5f6b5046a88a4952c07e53483996867c11324c92f1e6aa |
| `src/run_x2.py` | 91f145e2f2849061fc1d2a6d9a41e040e47f98c89c48ab7ebd4a3618dec5a078 |
| `src/make_worklists.py` | 13ade40f4a2c72b2e1168733076ade46c57924c80b83f1218bb2053a24945125 |
| `records/populations/POPULATION_MANIFEST.json` | f54c4a26b903373a69087de316234384b2ebb4c66e5740651a1ba742d128592e |
| `records/work/validate_rows.jsonl` | 0c0f4ee88d2c040240814f84e04b51c1957694c8c7c87b852303e4cc5180655e |
| `records/work/smoke_rows.jsonl` | 4abfe7b21bf3581771ec71b72523724dc34c5a936e09eb6a7d154304d8d81168 |
| `notes/A3_checks.json` | 9cc16dd41761633657c8e897c0efe618ae71bf88f19d4d8f2338844ebe46f12b |
| `notes/freeze_inputs.json` | f4a40269317c8fc91ab045cc1d3f0e79704049d151e5f08ea33750fa644fa8aa |
| `manifests/DOWNLOAD_MANIFEST.json` | 4bd8c8572b3f36d301ca3c3e8c3789c7b3d9452eb6064d803ce07b78fac3070f |
| `records/populations/arc_cal.jsonl` | 039b23dde7db04f36c3aee0996316831b8c358eb1e626616aeca88333efb8bc5 |
| `records/populations/arc_dev.jsonl` | 97d8449a4fc42e1a7fe12456ae4d783eacc4c62804a3c3f1b8cc3276404afdba |
| `records/populations/arc_fit.jsonl` | 0caf16b66f502a079c9ce9770657d984448bcb25578424037bb684593b3a1a3f |
| `records/populations/mmlu_pro_cal.jsonl` | 87af491e01cb8ca8ba1421f749d2022d3ec205a4b6a04590309beb441095138e |
| `records/populations/mmlu_pro_dev.jsonl` | 0fbe2f175a5ffc9069cf68ba02c55a0083848a59e64df2a14283ee2aa9804b04 |
| `records/populations/mmlu_pro_fit.jsonl` | 6f768418d246ad150cc3a4736577e455b505161f697201d4a1bdf6583099fa09 |
| `records/populations/obqa_cal.jsonl` | 23f6356348737b9f83ca87826ed39578f10dd0fe9b6c4a9b3b9b8667f4574d60 |
| `records/populations/obqa_dev.jsonl` | 38ab089008f979061c014637f725ce4e6a42fbddec6198990cc4950e4eea21c6 |
| `records/populations/obqa_fit.jsonl` | 6ad1b27f49e444d0102646c042d8bf20353cedace34fd44c46ae26830afcafd0 |
| OLMo chat_template | fe689ffbd6a4e2d0532d7480696b065b10e0e1eff3f9b9fc4bea415761e4bf4a |
| parser P2_SCORING_V2/scoring_v2.py | d05978f400cf69aa6bddc56168a260ac3ea9158abaa640e9331602dc9bfcc2f9 |
