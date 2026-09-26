# P2_R1_XFAM — X1 protocol freeze (post-hoc cross-family breadth extension)

Frozen before any X1 output exists (including the smoke test). After freezing, this file is read-only and is not changed after seeing any output; any unavoidable change goes in `../DEVIATIONS.md`. Hashes of its inputs are at the end. Pre-registration: the requester's X1 specification of 2026-09-19 (Llama 3.2 access granted to user, Sep 19).

## 1. Setting X1

- **Helper:** meta-llama/Llama-3.2-1B-Instruct @ 9213176726f574b556790deb65791e0c5aa438b6 (`$DATA_ROOT/hf_cache/hub`; files and SHA-256 in `manifests/X1_DOWNLOAD_MANIFEST.json`; the `original/` Meta-format files were not downloaded).
- **Receiver:** Qwen/Qwen3-0.6B @ c1899de289a04d12100db370d81485cdf75e47ca, the small pair's receiver checkpoint.
- **References:** Text and C2C.
  - C2C uses the official fuser nics-efc/C2C_Fuser @ f01fc3258b305e280e04c7238f4f2cf31b7dc70d, subfolder `qwen3_0.6b+llam3.2_1b_Fuser/final`.
  - Its config sets `is_do_alignment: true`, `alignment_strategy: "longest"` and `mapping: "last_aligned"`. The mapping is materialized in `final/projector_config.json`.
- **Benchmarks:** OBQA and ARC only, 5,626 rows (`records/populations/`), the same splits, IDs and representatives as the paper and X2:

  | benchmark | fit | cal | dev |
  |---|---|---|---|
  | OBQA | 2,100 | 1,366 | 742 |
  | ARC | 671 rows (670 representatives) | 448 | 299 |

  Certification and development units are the representatives. Every row is run.
- **Reuse (B).** X1's R answers and ProbeMax scores are the small pair's saved records:
  - R: `P2_SCORING_V2` labels `o_R`/`valid_R`, source P2_5 / P2_9 small cases.
  - ProbeMax: `P2_CONFIDENCE_REFERENCE_BOUNDARIES/records/small_{obqa,arc}_{fit,cal,dev}_probes.jsonl`.
  - Check (`notes/prepare_checks.json`): 5,626/5,626 probe rendered-prompt and input hashes and R input token counts reproduce with the same receiver checkpoint.

## 2. Text reference (two stages)

**C1: helper messages.** The paper's helper code, `legacy_methods.T2THelperBundle.run`, unchanged:
- The prompt is `[user: BACKGROUND_PROMPT(format_openbook(q, use_template=False))]` (ARC: P2-8 v2 helper body), rendered with Llama's own chat template, `add_generation_prompt=True`.
- **Fixed date:** `date_string="26 Jul 2024"` (Llama chat-template SHA-256 5816fce10444e03c2e9ee1ef8a4a1ea61ae7e69e438613f3b17b69d0426223a4). It is the only change, injected as a fixed keyword argument.
- **Exactly one BOS (128000):** checked on 3 examples before freezing (`notes/prepare_checks.json`), and recorded per row at run time.
- **Decoding:** greedy, bf16, SDPA, batch 1, `max_new_tokens=256` (the paper's helper call). The helper is loaded as `runtime.Runner` loads it (`apply_generation_config` do_sample=False). EOS comes from the checkpoint's generation config: eos_token_id [128001, 128008, 128009]; pad_token_id None, so generate() pads with EOS.

**C2: receiver reads the messages.** `src/run_x1_receiver.py`, the same calls as the validated X2 driver:
- The paper's Text receiver conversation `[user: BACKGROUND_PROMPT(helper body), assistant: message, user: receiver prompt]`.
- Qwen3-0.6B, thinking disabled, `max_new_tokens=64`, greedy.
- The generation config is asserted equal to the paper's frozen small-pair config.
- On 3 examples, this prompt equals the small pair's Text prompt except for the message text.

## 3. C2C reference: option B

- The official evaluator runs on our rows: `../x1_optionB/unified_evaluator_xfam.py`, i.e. the clean clone 113c3a9 plus the local-rows loader plus the ARC K≠4 label patch (diff `../diffs/X1B_unified_evaluator_local_rows_and_arc_labels.diff`).
- Changes to the official recipe `unified_eval.yaml` are configuration-only: `model_name` Rosetta; base/teacher/checkpoints; `is_do_alignment` true; `alignment_strategy` "longest"; dataset; `gpu_ids`; `local_rows_jsonl`; output_dir.
- Its receiver prompts are byte-identical to ours for 4,208/4,208 OBQA and 1,418/1,418 ARC rows, including 6/6 K≠4 rows (`../x1_optionB/PROMPT_IDENTITY.json`; overlay SHA-256 341b2bb9…, unchanged).
- The raw `cot_output` is saved per row and parsed with frozen V2.
- **Required validation before any X1 C2C run (D2):** with the SMALL pair's helper (Qwen2.5-0.5B) and fuser (8704f555) and no alignment, the evaluator must reproduce bit for bit the saved small-pair C2C raw outputs on 16 fit rows (8 OBQA, 8 ARC).
- **Also validated in the same job:**
  - `run_x1_helper.py` with the small pair's helper must reproduce the saved small-pair helper messages;
  - `run_x1_receiver.py` reading those saved messages must reproduce the saved small-pair Text raw outputs.
  - Both on the same 16 rows. Any failure stops the work.

## 4. Parser

Frozen P2_SCORING_V2 `parse_answer(raw, legal labels)` (d05978f4…), unchanged. INVALID is its own label: it counts as wrong, and as a symbol when comparing with R. A failed request counts as INVALID.

## 5. Certification (the paper's rule)

- **Settings:** four, OBQA/Text, OBQA/C2C, ARC/Text and ARC/C2C. For each:
  - 20 candidates from the fit-split ProbeMax quantiles: t_j = sorted_fit[ceil(j·N/20) − 1] for j = 1..19, plus q = 1. A question routes to R iff u ≤ t_j (ties route to R).
  - On the cal split: n routed, k routed with o_R ≠ o_ref. p = P[Bin(n, .05) ≤ k] (α = .05). A candidate is accepted if p ≤ .001.
  - Deploy the largest accepted q; else fall back to the fixed reference (q = 0).
- **Test family:** a separate 80-test family (4 settings × 20).

## 6. Development metrics (dev representatives)

- **Table 5:** Dis./N (o_R ≠ o_ref); ProbeMax AUROC for those disagreements; min UCB (smallest Clopper–Pearson .999 upper bound over the 20 calibration candidates); q; coverage (% routed to R); changed/omitted (N/A if none); correct policy/reference.
- **Also:** Text and C2C accuracy and INVALID rates per split (R shown for reference).
- **Order:**
  1. All outputs are written and hashed.
  2. Certification and routes are computed without gold, written and hashed.
  3. Only then is gold read (`gold` field of the P2_SCORING_V2 labels).
- **Code:** `src/analyze_x1.py`, hashed below. Rule functions are imported unchanged from P2_R1_CPU.

## 7. Commitment

All four settings are reported whatever the outcome. End-to-end replay happens only for settings that deploy, under a later rule. A deployed C2C setting would need our runtime to support alignment; that is not built now.

## 8. Execution (harness)

- **Job X1-1:** validation (helper, receiver, D2), then, only if all pass, a smoke test on the same 16 fit rows: Llama helper → receiver reading → X1 C2C evaluator. Gold is not read.
- **Smoke stop rule:** any runtime error, or more than 2 of 16 INVALID for Text or for C2C.
- **Full runs:** on free queues, without delaying X2; chains of at most 50 min including load, sized from the smoke timings; the plan is recorded in DEVIATIONS.md before submission.

## 9. Hashes

| item | SHA-256 |
|---|---|
| `src/x1_common.py` | 9d6dfbe688121a42107ac2a15a7955cd6f1a57acbc22d4b92d70042274d3f9f1 |
| `src/prepare_x1.py` | b583c98bf6874d90a48abcc62867c10ddcc3788fd79ff42b4c2e765131ec0e4d |
| `src/run_x1_helper.py` | a26b983530f3e6951a5d7ba1e430e247c66a2ee49b643ab857d7b84a2dbc5c8f |
| `src/run_x1_receiver.py` | 61125253f9d504a21dacf6c73bf4e862394b7cf7d86596ec2bad75279a84ee96 |
| `src/run_x1_c2c.py` | f540ce468f45ffb1d771caf144e23af788f2a996fda6c0b1b562144ccc412741 |
| `src/analyze_x1.py` | 70469553f4a6c494bdb50ac0d73bc0c12f91a495753adfc435912a207321bb75 |
| `../src/xfam_common.py` | 6150428bfbc4cb58d5fc718abbf610437038726342ae20747cc119f9c9dc4b12 |
| `../x1_optionB/unified_evaluator_xfam.py` | 341b2bb9ed3b68c68338a9a8a20db9e907027b449d12003df45be15d453cc27c |
| `records/populations/POPULATION_MANIFEST.json` | b91ee7fcc6bbafeef12a9ce356d09eb01b9924469ca11e9e8a45608c0517e4c5 |
| `records/work/sample16_all.jsonl` | d884026c2cd75b9d0c836f9c8327eedd847674f9515c9836f19076f7e74e11bc |
| `records/work/sample16_obqa.jsonl` | f4140378cd1ea8e65f70bfc363d93acf64deb30d30ba2bbd5fc333f0013b58fd |
| `records/work/sample16_arc.jsonl` | a12d2c40c9e1426666cef76c5ffa99e6aa15050ce5e3edca7f09f35b7a4d6ca6 |
| `notes/prepare_checks.json` | 5dfd2d12731912ad2357d0724599ddf329b8abf1d21b76eaf1179452650ab5a8 |
| `manifests/X1_DOWNLOAD_MANIFEST.json` | 89462d9866f69f16b69ab30d43879d172af20b5bea20f8aad234dc61b0602ac5 |
| `../../P2_SCORING_V2_20260912T191445Z/scoring_v2.py` | d05978f400cf69aa6bddc56168a260ac3ea9158abaa640e9331602dc9bfcc2f9 |
| `records/populations/arc_cal.jsonl` | 19075a48f40703315111b369b5a5a65716baae05b86ed71c12d3179c3b3fb0cd |
| `records/populations/arc_dev.jsonl` | c12ae23dfb9d0c7de034cf5da5f048ee228887f04a2753bab93d830d66ddfa7b |
| `records/populations/arc_fit.jsonl` | 989e41698dcfe1c9dbac1e7bbb5abfae3421ed5556abbd9d54aea3f799125717 |
| `records/populations/obqa_cal.jsonl` | d267fcb1237628a2d374d0e3ae8ec06a17bf8009d421d2c1ce5b2c649f86707e |
| `records/populations/obqa_dev.jsonl` | 8264a8e350722ba67bee8a179c52ccd5e231c84d8089029015779d87a4b78771 |
| `records/populations/obqa_fit.jsonl` | 3177e29c8ebe56c5af781f841ea8e4b6a508027a81936c601046ac1268664aea |
