# P2_R1_XFAM feasibility check (2026-09-19, login node only; no GPU jobs)

Planned post-hoc cross-family settings:
- **X1:** helper Llama-3.2-1B-Instruct → receiver Qwen3-0.6B. References Text and C2C; fuser `nics-efc/C2C_Fuser/qwen3_0.6b+llam3.2_1b_Fuser`.
- **X2:** helper Qwen2.5-7B-Instruct → receiver Llama-3.1-8B-Instruct, with fallback OLMo-2-1124-7B-Instruct. Reference Text only.

Evidence files:
- `logs/access_check.{log,json}`
- `manifests/DOWNLOAD_MANIFEST.json`
- `notes/check_code_support.py` → `notes/code_support_checks.json`
- `notes/arc_prompt_official_vs_ours.json`

## 1. Access (HF token user `user`, via the the-cluster proxy)

| repo | model_info | config.json download | revision (main) |
|---|---|---|---|
| meta-llama/Llama-3.2-1B-Instruct | ok; gated = manual | **DENIED**: GatedRepoError 403, "Cannot access gated repo … Access to model … is restricted" | 9213176726f5 |
| meta-llama/Llama-3.1-8B-Instruct | ok; gated = manual | **DENIED**: GatedRepoError 403 (same) | 0e9e39f249a1 |
| allenai/OLMo-2-1124-7B-Instruct | ok; not gated | ok (Olmo2ForCausalLM, 32 layers, vocab 100352) | 470b1fba1ae0 |
| nics-efc/C2C_Fuser | ok | subfolder `qwen3_0.6b+llam3.2_1b_Fuser` exists at main | f01fc3258b30 (same revision as the medium/large fusers) |

No Llama copy exists under this user's shared filesystem area.

## 2. Downloads

- shared filesystem quota: 15.17 TB used of 50 TB (`<quota-tool>`).
- Llama access was denied, so X2 uses the fallback receiver. Downloaded to `$DATA_ROOT/hf_cache/hub` (the layout of the large receiver):
  - `allenai/OLMo-2-1124-7B-Instruct@470b1fba…`: 13 files, 14.61 GB, 96 s.
  - Only `qwen3_0.6b+llam3.2_1b_Fuser/config.json` from the X1 fuser. The weights are unusable without the Llama helper and were not downloaded.
- Per-file SHA-256 manifest: `manifests/DOWNLOAD_MANIFEST.json`.

## 3. Code support

**a. Non-Qwen3 receiver (checked with the OLMo-2 tokenizer; the Llama tokenizers are gated and could not be loaded).**
- **R path (`protocol_min.receiver_prompt_tensors`): CONFIG-ONLY.**
  - The chat template renders, and `enable_thinking=False` is ignored (rendered text is identical with and without it).
  - Retokenizing the rendered text gives the same IDs as `apply_chat_template(tokenize=True)`: 0 extra BOS tokens.
  - A new frozen config is still needed: receiver path, revision, chat-template SHA and generation config. `generation_config`: eos 100257, pad 100277.
- **Text path (`T2TReceiverBundle`, three-message conversation): CONFIG-ONLY.** It renders with the OLMo template.
- **ProbeMax: SMALL CHANGE.**
  - The label rule is tokenizer-generic: non-special single tokens whose stripped decode equals the label. With OLMo, the sets for A–E are non-empty and disjoint (3 tokens each), and the prefix "The correct answer is" round-trips.
  - What needs changing: `run_boundaries.py` hard-codes Qwen role markers (`<|im_start|>assistant\n`, `<|im_end|>`) in its role-boundary asserts. They must become template-specific (OLMo uses `<|user|>`/`<|assistant|>`).
  - The probe also needs a receiver-only driver, like the E4 driver.
- **Parser: CONFIG-ONLY.** It is text-based and tokenizer-independent. OLMo's answer style is unmeasured, so the INVALID rate should be checked in a pilot.
- **Llama (unverified, from the public templates).**
  - Llama tokenizers add BOS when called, so `tokenizer(rendered)` would produce a double `<|begin_of_text|>` in the R and probe paths. SMALL CHANGE: `add_special_tokens=False` for that receiver.
  - The Llama-3.2 template inserts today's date via `strftime_now` unless a `date_string` is passed. SMALL CHANGE: fix `date_string` so prompts don't depend on the run date.

**b. Helper Text prompt: independent of the receiver.**
- `legacy_methods.T2THelperBundle.prepare` uses only `BACKGROUND_PROMPT.format(question=format_openbook(example, use_template=False))` (ARC: `arc_protocol.helper_body`) and the helper's own chat template and tokenizer.
- The large pair's saved Text records cover every X2 row: OBQA train 3,466 + dev 742; ARC train 1,119 + dev 299. Each has `helper_message`, `helper_generated_token_ids` and `helper_input_tokens`.
- Three-example check:

  | example | saved record | rebuilt / saved helper input tokens | X2 byte-identical to large | message decodes from saved IDs |
  |---|---|---|---|---|
  | OBQA 10 | P2_6 train_cases:2 | 88 / 88 | true | true |
  | OBQA 10-100 | P2_6 train_cases:4 | 86 / 86 | true | true |
  | ARC Mercury_SC_415702 | P2_9 large train_cases:2 | 103 / 103 | true | true |

- **So X2 Text = reuse the saved messages, plus receiver-side Text-reading only. CONFIG-ONLY data reuse.**

**c. X1 C2C with different tokenizers.**
- Our port (`C2CSharerHelperBundle`) runs the helper on receiver token IDs, which assumes a shared vocabulary. Llama-3.2 has a 128k-token vocabulary; Qwen has 151k.
- The vendored `runtime_source/rosetta/model/aligner.py` (TokenAligner, strategies first/longest) is byte-identical to the official clone's. But `runtime.py`, `legacy_methods.py` and `protocol_min.py` never call it: it is only used by the official evaluator (`is_do_alignment` → `align_chat_messages`).
- The fuser config sets `is_do_alignment: true`, `alignment_strategy: "longest"`, `mapping: "last_aligned"`.
- **Our runtime therefore needs NEW CODE.**
- Options:
  - **(A) NEW CODE in our runtime.**
    - Wire TokenAligner into the C2C helper path, plus the official aligned KV mapping (`last_aligned`) in the fuser step.
    - Then validate against the official evaluator on the 500 OBQA test questions, E1-style.
  - **(B) Clean official evaluator, config-only for the model, on our populations.**
    - OBQA: E1 showed its OBQA prompts are byte-identical to ours. Our rows would need to be fed via the runtime-patch clone's `local_openbookqa_parquet` (a harness data file; the evaluator reads `answerKey` internally, as in E1).
    - ARC: it has no local-data option, so this needs a SMALL CHANGE (local ARC loader). Its `ai2-arc` prompt equals ours for 4-option questions. For K≠4 its instruction line keeps "A/B/C/D" (ours: "A/B/C" or "A/B/C/D/E"), which affects 6 of 1,418 rows.
  - **(C) Run X1 with Text only.**
  - All X1 options also require Llama-3.2-1B access.

**d. X1 reuse of the small pair's receiver-only records: CONFIG-ONLY (reuse).**
- The receiver is the same local checkpoint `c2c_reproduction_assets/models/Qwen--Qwen3-0.6B`: download metadata, P2_10 frozen config and boundaries config all give revision c1899de289a0, with the chat-template SHA matching.
- ProbeMax records: recomputing all 5,626 small fit/cal/dev probe inputs gives rendered SHA 5,626/5,626, probe-input SHA 5,626/5,626 and generation-prefix SHA 5,626/5,626. The probe prompt equals the runtime R prompt on 5,626/5,626.
- Saved R outputs (P2_5 OBQA train/dev, P2_9 small ARC train/validation): `receiver_input_tokens` match 5,626/5,626.

## 4. Plan (5,626 questions = OBQA 4,208 + ARC 1,418)

**Timing bases**
- ClusterA E4 records (`P2_R1_EXP…/results/e4`), means:
  - receiver-only Qwen3-8B: 202 ms (OBQA), 213 ms (ARC);
  - V2 Text-reading: 204 / 202 ms;
  - receiver-only small: 235 ms; medium: 166 ms.
- ClusterA wall per V2 request including logging: about 0.25 s (100 rows / 25.3 s).
- ClusterB ProbeMax `probe_core_ms` (boundary records): large 51 ms, small 33 ms.
- ClusterB Text with helper generation (dev means): small 710/1238 ms, medium 859/1076 ms.
- ClusterB C2C small: 282/430 ms. task7 official small C2C: 0.54 s/question.
- OLMo and Llama speeds and answer lengths are assumed equal to their Qwen counterparts. These are estimates, not measurements.

**X2 (OLMo-2-7B receiver; Llama-3.1-8B if access is later granted)**
- Requests: R 5,626 + ProbeMax 5,626 + Text-reading 5,626 = 16,878; the helper is not run.
- Estimate ≈ 0.25 + 0.07 + 0.25 s per question ≈ 53 GPU-min.
- Split over 4 single-GPU chains of about 1,407 rows each: about 13.5 min of requests plus about 4 min cold start and load, ≈ 18 min per chain.
- **One 1-node job** (debug-2 or debug), 30-min walltime.
- Memory: OLMo-2-7B bf16 is 14.6 GB on one A100-40GB.

**X1 (only if Llama-3.2-1B access is granted)**
- Requests: Text 5,626 + C2C 5,626 = 11,252. R and ProbeMax are reused.
- Text with the helper generating: medium-pair proxy, 4,208×0.86 + 1,418×1.08 s ≈ 86 min, or ≈ 95 min with I/O.
- C2C:
  - via option A: 4,208×0.28 + 1,418×0.43 s ≈ 30 min (≈ 33 with I/O; alignment overhead unknown);
  - via option B: 5,626 × 0.54 s ≈ 51 min, split in two.
- **One 2-node debug job** with 4 helper/receiver GPU-pair chains: 3 Text shards of about 32 min + 3 min, and 1 C2C chain of about 36 min. Each chain ≤ 36 min.
- Memory: Llama-1B (≈2.5 GB) on one GPU and Qwen3-0.6B (≈1.2 GB) plus the fuser on the other. All fit easily.
